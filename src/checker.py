"""Sąveikų tikrinimo logika (nepriklauso nuo UI – naudojama programėlėje ir testuose)."""
from __future__ import annotations

import gzip
import itertools
import json
import os
from dataclasses import dataclass, field

import lightgbm as lgb
import numpy as np
import pandas as pd

from . import features as F
from . import knowledge as K
from .matching import Matcher, Resolution, split_input

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEVEL_RANK = {"Minor": 0, "Moderate": 1, "Major": 2}
LEVEL_LT = {"Major": "Didelė rizika", "Moderate": "Vidutinė rizika", "Minor": "Maža rizika"}
AI_CONFIDENCE_MIN = 0.60


def display_name(sub: str) -> str:
    lt = K.LT_NAMES.get(sub)
    if not lt or lt.lower() == sub.lower():
        return sub
    return f"{lt} · {sub}" if "(" in lt else f"{lt} ({sub})"


@dataclass
class Entry:
    """Vienas vartotojo įvestas įrašas ir jo atpažinimas."""
    query: str
    res: Resolution
    override: str | None = None  # vartotojo pasirinktas pasiūlymas

    @property
    def substances(self) -> list[str]:
        return self.res.substances


@dataclass
class PairResult:
    a: str
    b: str
    from_a: str
    from_b: str
    level: str | None              # Major/Moderate/Minor arba None
    source: str                    # DDInter | DDInter + AI | Literatūra | Taisyklės | Nėra duomenų
    rules: list[dict] = field(default_factory=list)
    ai_probs: dict | None = None
    ai_explain: list[tuple[str, float]] | None = None
    cautions: list[str] = field(default_factory=list)
    extra: dict | None = None

    @property
    def rank(self) -> int:
        return LEVEL_RANK.get(self.level, -1)


@dataclass
class GroupWarning:
    title: str
    level: str
    substances: list[str]
    text: str
    advice: str


class Checker:
    def __init__(self, root: str = ROOT):
        proc = os.path.join(root, "data", "processed")
        self.drugs = pd.read_csv(os.path.join(proc, "drugs.csv"))
        pairs = pd.read_csv(os.path.join(proc, "pairs.csv.gz"))
        self.pair_level = {frozenset((a, b)): l for a, b, l in
                           zip(pairs.drug_a, pairs.drug_b, pairs.level)}
        self.known = set(self.drugs.name)
        self.curated = {frozenset((p["a"], p["b"])): p for p in K.CURATED_PAIRS}
        names = list(self.drugs.name) + list(K.EXTRA_SUBSTANCES)
        self.matcher = Matcher(names)
        self.all_names = names
        mdir = os.path.join(root, "models")
        self.model = None
        mpath = os.path.join(mdir, "lightgbm_severity.txt.gz")
        if os.path.exists(mpath):
            with gzip.open(mpath, "rt", encoding="utf-8") as f:
                self.model = lgb.Booster(model_str=f.read())
            self.stats = pd.read_csv(os.path.join(mdir, "drug_stats.csv"), index_col=0)
            with open(os.path.join(mdir, "model_meta.json"), encoding="utf-8") as f:
                self.meta = json.load(f)

    # ------------------------------------------------------------------
    def resolve(self, text: str, overrides: dict[str, str] | None = None,
                picked: list[str] | None = None) -> list[Entry]:
        overrides = overrides or {}
        entries = []
        for q in split_input(text):
            r = self.matcher.resolve(q)
            if r.status == "suggest" and overrides.get(q):
                lab = overrides[q]
                r = Resolution(q, "approx", self.matcher.substances_for_suggestion(lab), lab,
                               "Pasirinkta iš pasiūlymų.", r.suggestions, r.score)
            entries.append(Entry(q, r))
        for p in picked or []:
            entries.append(Entry(display_name(p), Resolution(p, "exact", [p], display_name(p))))
        return entries

    # ------------------------------------------------------------------
    def ai_predict(self, a: str, b: str):
        if self.model is None:
            return None, None
        df = pd.DataFrame({"drug_a": [a], "drug_b": [b]})
        X = F.build_features(df, self.drugs, self.stats)[self.meta["features"]]
        probs = self.model.predict(X)[0]
        k = int(np.argmax(probs))
        contrib = self.model.predict(X, pred_contrib=True)[0]
        nf = X.shape[1]
        c = contrib.reshape(3, nf + 1)[k, :nf]
        top = np.argsort(-np.abs(c))[:6]
        explain = [(F.shap_label(X.columns[i]), float(c[i])) for i in top if abs(c[i]) > 1e-3]
        return dict(zip(F.LEVELS, map(float, probs))), explain

    # ------------------------------------------------------------------
    def check_pair(self, a: str, b: str, from_a: str, from_b: str) -> PairResult:
        key = frozenset((a, b))
        rules = F.rule_hits(a, b)
        rule_level = max((r["level"] for r in rules), key=LEVEL_RANK.get, default=None)
        supp = (a in K.SUPPLEMENTS) or (b in K.SUPPLEMENTS)
        pr = PairResult(a, b, from_a, from_b, None, "Nėra duomenų", rules)

        if key in self.curated:
            c = self.curated[key]
            pr.level, pr.source = c["level"], "Literatūra"
            pr.extra = c
            pr.cautions.append("Įrašas papildytas rankiniu būdu iš literatūros (ne DDInter).")
        elif key in self.pair_level:
            lvl = self.pair_level[key]
            if lvl in LEVEL_RANK:
                pr.level, pr.source = lvl, "DDInter"
                if rule_level and LEVEL_RANK[rule_level] > LEVEL_RANK[lvl]:
                    pr.cautions.append(
                        f"Taisyklės šią porą vertina griežčiau ({LEVEL_LT[rule_level].lower()}) nei "
                        "DDInter – rizika gali priklausyti nuo dozės ir paciento būklės.")
            else:  # DDInter: sąveika yra, bet sunkumas nenurodytas
                pr.source = "DDInter + AI"
                probs, expl = self.ai_predict(a, b)
                pr.ai_probs, pr.ai_explain = probs, expl
                if probs:
                    pr.level = max(probs, key=probs.get)
                    pr.cautions.append(
                        "DDInter sąveiką užfiksavo, bet sunkumo nenurodė. Sunkumas PROGNOZUOTAS "
                        "AI modelio – naudokite atsargiai.")
                    if max(probs.values()) < AI_CONFIDENCE_MIN:
                        pr.cautions.append(
                            f"Modelis nėra tikras (didžiausia tikimybė {max(probs.values()):.0%}).")
                    if rule_level and LEVEL_RANK[rule_level] > LEVEL_RANK[pr.level]:
                        pr.level = rule_level
                        pr.cautions.append("Taisyklės rodo didesnę riziką nei AI prognozė – "
                                           "rodomas griežtesnis įvertinimas.")
                else:
                    pr.level = rule_level or "Moderate"
                    pr.cautions.append("Sunkumas nežinomas – AI modelis neįkeltas.")
        elif rules:
            pr.level, pr.source = rule_level, "Taisyklės"
            pr.cautions.append("DDInter šios poros neturi, bet abi medžiagos priklauso rizikos "
                               "grupėms. Įspėjimas sugeneruotas taisyklėmis – tai GALIMA, o ne "
                               "patvirtinta sąveika.")
        else:
            unknown_side = [s for s in (a, b) if s not in self.known and s not in K.EXTRA_SUBSTANCES]
            if unknown_side:
                pr.cautions.append("Bent vienos medžiagos duomenų bazėje nėra.")
            extra = [s for s in (a, b) if s in K.EXTRA_SUBSTANCES]
            if extra:
                pr.cautions.append(
                    f"{display_name(extra[0])}: turime tik nedidelį literatūros įrašų rinkinį, todėl "
                    "„duomenų nėra“ NEreiškia, kad sąveikos nėra.")

        if pr.level and pr.source in ("DDInter", "DDInter + AI") and not rules:
            pr.cautions.append("Mechanizmo aprašymo šiame duomenų rinkinyje nėra – detales "
                               "pasitikslinkite pakuotės lapelyje arba pas vaistininką.")
        if pr.level and supp:
            pr.cautions.append("Papildų ir augalinių preparatų sąveikų įrodymai dažnai riboti, o "
                               "sudėtis tarp gamintojų skiriasi.")
        return pr

    # ------------------------------------------------------------------
    def check(self, entries: list[Entry]):
        # medžiaga -> iš kurių įrašų ji atėjo
        origin: dict[str, list[str]] = {}
        for e in entries:
            for s in e.substances:
                origin.setdefault(s, []).append(e.query)

        group: list[GroupWarning] = []
        for s, qs in origin.items():
            if len(qs) > 1:
                group.append(GroupWarning(
                    "Ta pati veiklioji medžiaga kartojasi", "Major", [s],
                    f"{display_name(s)} yra keliuose įvestuose preparatuose: " + ", ".join(qs) + ".",
                    "Dvigubas dozavimas gali sukelti perdozavimą. Patikrinkite, ar tikrai reikia "
                    "vartoti abu preparatus, ir neviršykite bendros paros dozės."))
        tw = F.triple_whammy(list(origin))
        if tw:
            group.append(GroupWarning("„Trigubas smūgis“ inkstams", K.TRIPLE_WHAMMY["level"], tw,
                                      K.TRIPLE_WHAMMY["effect"] + " " + K.TRIPLE_WHAMMY["mechanism"],
                                      K.TRIPLE_WHAMMY["advice"]))

        results = []
        subs = list(origin)
        for a, b in itertools.combinations(subs, 2):
            # Komponentai iš to paties sudėtinio preparato (pvz., Augmentin) netikrinami tarpusavyje
            if set(origin[a]) == set(origin[b]) and len(origin[a]) == 1:
                continue
            results.append(self.check_pair(a, b, ", ".join(origin[a]), ", ".join(origin[b])))
        results.sort(key=lambda r: (-r.rank, r.source == "Nėra duomenų"))
        return results, group
