"""Taisyklių variklis ir porų požymiai AI modeliui.

Požymiai simetriški (A,B) == (B,A): naudojamos sumos / min / max.
"""
from __future__ import annotations

import math
import re

import numpy as np
import pandas as pd

from . import knowledge as K

LEVELS = ["Minor", "Moderate", "Major"]
LEVEL_TO_INT = {"Minor": 0, "Moderate": 1, "Major": 2}
ATC_LETTERS = list("ABCDGHJLMNPRSV")
CLASS_KEYS = list(K.RISK_CLASSES)
RULE_IDS = [r["id"] for r in K.RULES]
_TOPICAL_RE = re.compile(r"\((topical|ophthalmic|nasal|otic|topiclal|topical ophthalmic)\)", re.I)

# Taisyklės, kurias „uždengia“ griežtesnė tos pačios šeimos taisyklė
SUPERSEDES = {
    "bleeding_major": {"bleeding_moderate", "bleeding_supp"},
    "serotonin_major": {"serotonin"},
    "opioid_benzo": {"cns"},
}

_MEMBERSHIP: dict[str, set[str]] = {}
for _c, _v in K.RISK_CLASSES.items():
    for _m in _v["members"]:
        _MEMBERSHIP.setdefault(_m, set()).add(_c)


def classes_of(substance: str) -> set[str]:
    base = re.sub(r"\s*\(.*?\)", "", substance)
    if _TOPICAL_RE.search(substance):  # vietinio vartojimo formoms sisteminių klasių netaikome
        return set()
    return _MEMBERSHIP.get(substance, set()) | _MEMBERSHIP.get(base, set())


def rule_hits(a: str, b: str) -> list[dict]:
    if a == b:
        return []
    ca, cb = classes_of(a), classes_of(b)
    hits = []
    for r in K.RULES:
        ra, rb = set(r["a"]), set(r["b"])
        if (ca & ra and cb & rb) or (cb & ra and ca & rb):
            hits.append(r)
    ids = {h["id"] for h in hits}
    drop = set().union(*[SUPERSEDES.get(i, set()) for i in ids]) if ids else set()
    return [h for h in hits if h["id"] not in drop]


def triple_whammy(substances: list[str]) -> list[str] | None:
    """Grąžina NVNU + AKFI/ARB + diuretiko trejetą, jei jis yra sąraše."""
    found = {}
    for c in K.TRIPLE_WHAMMY["classes"]:
        for s in substances:
            if c in classes_of(s) and s not in found.values():
                found[c] = s
                break
    if len(found) == 3:
        return list(found.values())
    return None


# --------------------------------------------------------------------------
# Vaistų statistika (skaičiuojama TIK iš mokymo duomenų – kad nebūtų nutekėjimo)
# --------------------------------------------------------------------------
def drug_stats(pairs: pd.DataFrame) -> pd.DataFrame:
    """pairs: stulpeliai drug_a, drug_b, y (0/1/2)."""
    long = pd.concat([pairs[["drug_a", "y"]].rename(columns={"drug_a": "drug"}),
                      pairs[["drug_b", "y"]].rename(columns={"drug_b": "drug"})])
    g = long.groupby("drug").y
    return pd.DataFrame({
        "deg": np.log1p(g.size()),
        "p_major": g.apply(lambda s: (s == 2).mean()),
        "p_minor": g.apply(lambda s: (s == 0).mean()),
        "score": g.mean(),
    })


def build_features(pairs: pd.DataFrame, drugs: pd.DataFrame,
                   stats: pd.DataFrame | None) -> pd.DataFrame:
    """pairs: drug_a, drug_b. drugs: name, atc1. stats: drug_stats() rezultatas arba None."""
    atc = dict(zip(drugs.name, drugs.atc1.fillna("")))
    rows = []
    for a, b in zip(pairs.drug_a, pairs.drug_b):
        f: dict[str, float] = {}
        aa, ab = atc.get(a, ""), atc.get(b, "")
        for L in ATC_LETTERS:
            f[f"atc_{L}"] = (L in aa) + (L in ab)
        f["atc_none"] = (aa == "") + (ab == "")
        f["atc_same"] = float(bool(set(aa) & set(ab)))
        ca, cb = classes_of(a), classes_of(b)
        for c in CLASS_KEYS:
            f[f"cls_{c}"] = (c in ca) + (c in cb)
        hits = rule_hits(a, b)
        hit_ids = {h["id"] for h in hits}
        for r in RULE_IDS:
            f[f"rule_{r}"] = float(r in hit_ids)
        f["rule_max_level"] = max([LEVEL_TO_INT[h["level"]] for h in hits], default=-1)
        f["topical"] = bool(_TOPICAL_RE.search(a)) + bool(_TOPICAL_RE.search(b))
        f["supplement"] = (a in K.SUPPLEMENTS) + (b in K.SUPPLEMENTS)
        rows.append(f)
    X = pd.DataFrame(rows, index=pairs.index)
    for col in ["deg", "p_major", "p_minor", "score"]:
        if stats is not None:
            va = pairs.drug_a.map(stats[col])
            vb = pairs.drug_b.map(stats[col])
        else:
            va = vb = pd.Series(np.nan, index=pairs.index)
        X[f"{col}_min"] = np.fmin(va, vb)
        X[f"{col}_max"] = np.fmax(va, vb)
    return X


def oof_drug_stats_features(pairs: pd.DataFrame, drugs: pd.DataFrame, n_folds: int = 5,
                            seed: int = 42) -> pd.DataFrame:
    """Mokymo eilutėms: vaisto statistika skaičiuojama iš KITŲ fold'ų (out-of-fold)."""
    rng = np.random.default_rng(seed)
    fold = rng.integers(0, n_folds, len(pairs))
    parts = []
    for k in range(n_folds):
        tr, va = pairs[fold != k], pairs[fold == k]
        parts.append(build_features(va, drugs, drug_stats(tr)))
    return pd.concat(parts).loc[pairs.index]


def shap_label(name: str) -> str:
    """Žmogui suprantamas požymio pavadinimas lietuviškai."""
    if name.startswith("atc_") and len(name) == 5:
        return f"ATC grupė {name[-1]}"
    if name.startswith("cls_"):
        return "Klasė: " + K.RISK_CLASSES[name[4:]]["lt"]
    if name.startswith("rule_") and name != "rule_max_level":
        return "Taisyklė: " + name[5:]
    return {
        "atc_none": "ATC grupė nežinoma", "atc_same": "Ta pati ATC grupė",
        "rule_max_level": "Taisyklių numatytas sunkumas", "topical": "Vietinio vartojimo forma",
        "supplement": "Papildas / maistas", "deg_min": "Mažiau sąveikaujančio vaisto sąveikų sk.",
        "deg_max": "Daugiau sąveikaujančio vaisto sąveikų sk.",
        "p_major_min": "Major dalis (min.)", "p_major_max": "Major dalis (maks.)",
        "p_minor_min": "Minor dalis (min.)", "p_minor_max": "Minor dalis (maks.)",
        "score_min": "Vid. sunkumas (min.)", "score_max": "Vid. sunkumas (maks.)",
    }.get(name, name)


def finite(x) -> bool:
    return x is not None and not (isinstance(x, float) and math.isnan(x))
