"""Vaistų pavadinimų atpažinimas (lietuviški, angliški, prekiniai pavadinimai).

Žingsniai:
 1. Valymas: mažosios raidės, be diakritikų, be dozių („400 mg“) ir formų („tabletės“).
 2. Tikslus atitikmuo indekse (EN, LT, prekiniai, buitiniai pavadinimai).
 3. Lietuviško INN „kamieno“ atitikmuo (ibuprofenAS -> ibuprofen, varfarinAS -> warfarin).
 4. Neraiškusis (fuzzy) palyginimas su rapidfuzz – grąžinami pasiūlymai su patikimumu.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from rapidfuzz import fuzz, process

from . import knowledge as K

DOSE_RE = re.compile(
    r"\b\d+([.,]\d+)?\s*(mg|g|mcg|µg|μg|ug|ml|tv|iu|vv|%|mmol|mg/ml|mg/g)?\b", re.I)
FORM_WORDS = {
    "tabletes", "tabletė", "tablete", "tabl", "tab", "kapsules", "kaps", "kapsule", "tirpalas",
    "sirupas", "lasai", "purskalas", "milteliai", "forte", "retard", "mite", "plevele",
    "dengtos", "sl", "sr", "xr", "xl", "cr", "mr", "tablets", "capsules", "tablet", "capsule",
    "kramtomosios", "putojancios", "injekcinis", "ampules", "kremas", "gelis", "tepalas",
}
FUZZY_ACCEPT = 90      # >= : priimame automatiškai (pažymime kaip „apytikslis“)
FUZZY_SUGGEST = 75     # >= : siūlome kaip galimą variantą


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def clean(text: str) -> str:
    t = strip_accents(text.lower())
    t = t.replace("®", " ").replace("™", " ")
    t = DOSE_RE.sub(" ", t)
    t = re.sub(r"[^a-z0-9\-\s'.]", " ", t)
    words = [w for w in t.replace(".", " ").split() if w not in FORM_WORDS]
    return " ".join(words).strip(" -'")


_LT_ENDINGS = ("iai", "ai", "as", "is", "ys", "us", "os", "es", "e", "a")


def lt_stem(word_phrase: str) -> str:
    """Nuima lietuviškas galūnes kiekvienam žodžiui."""
    out = []
    for w in word_phrase.split():
        for e in _LT_ENDINGS:
            if len(w) > len(e) + 3 and w.endswith(e):
                w = w[: -len(e)]
                break
        out.append(w)
    return " ".join(out)


def en_to_lt_stem(name: str) -> str:
    """Angliškas INN -> tikėtinas lietuviškas kamienas (warfarin -> varfarin)."""
    s = strip_accents(name.lower())
    s = re.sub(r"\(.*?\)", " ", s)
    for a, b in [("ph", "f"), ("th", "t"), ("qu", "kv"), ("ck", "k"), ("x", "ks"),
                 ("w", "v"), ("y", "i")]:
        s = s.replace(a, b)
    s = re.sub(r"c(?=[aoulrt])", "k", s)
    s = " ".join(w.rstrip("e") if len(w) > 4 else w for w in s.split())
    return " ".join(s.split())


@dataclass
class Resolution:
    query: str
    status: str                 # exact | approx | suggest | not_in_db | unknown
    substances: list[str] = field(default_factory=list)
    label: str = ""             # kaip atpažinta (rodymui)
    note: str | None = None
    suggestions: list[tuple[str, float]] = field(default_factory=list)
    score: float = 100.0


class Matcher:
    def __init__(self, substance_names: list[str]):
        self.names = list(substance_names)
        self.index: dict[str, tuple[list[str], str, str | None]] = {}
        self.stem_index: dict[str, str] = {}

        def add(key: str, subs: list[str], label: str, note: str | None = None) -> None:
            k = clean(key)
            if k and k not in self.index:
                self.index[k] = (subs, label, note)

        # Buitiniai pavadinimai turi pirmenybę (pvz., „kava“ = gėrimas, ne augalas).
        for key, (subs, note) in K.GENERIC_ALIASES.items():
            add(key, subs, key.capitalize() + " → " + " + ".join(subs), note)
        for n in self.names:
            add(n, [n], n)
            base = re.sub(r"\s*\(.*?\)", "", n)
            # „(topical)“ ir pan. formų nepriskiriame paprastam pavadinimui
            if base != n and clean(base) not in self.index and base in self.names:
                add(base, [base], base)
            self.stem_index.setdefault(en_to_lt_stem(n), n)
        for en, lt in K.LT_NAMES.items():
            add(lt, [en], f"{lt} ({en})")
            add(re.sub(r"\s*\(.*?\)", "", lt), [en], f"{lt} ({en})")
        for brand, subs in K.BRANDS.items():
            add(brand, subs, f"{brand} → " + " + ".join(subs), K.BRAND_NOTES.get(brand))
        self._choices = list(self.index.keys())

    def resolve(self, query: str) -> Resolution:
        q = clean(query)
        if not q:
            return Resolution(query, "unknown", note="Tuščias įrašas.")
        if q in K.NOT_IN_DB:
            return Resolution(query, "not_in_db", label=K.NOT_IN_DB[q],
                              note="Medžiaga atpažinta, bet DDInter duomenų bazėje jos nėra – "
                                   "sąveikos NETIKRINAMOS.")
        if q in self.index:
            subs, label, note = self.index[q]
            return Resolution(query, "exact", subs, label, note)
        stem = lt_stem(q)
        if stem in self.stem_index:
            n = self.stem_index[stem]
            return Resolution(query, "exact", [n], f"{query.strip()} → {n}", None)
        # Neraiškusis palyginimas
        cands = process.extract(q, self._choices, scorer=fuzz.WRatio, limit=5)
        stem_cands = process.extract(stem, list(self.stem_index), scorer=fuzz.ratio, limit=3)
        merged: dict[str, float] = {}
        for key, sc, _ in cands:
            lab = self.index[key][1]
            merged[lab] = max(merged.get(lab, 0), sc)
        for key, sc, _ in stem_cands:
            lab = self.stem_index[key]
            merged[lab] = max(merged.get(lab, 0), sc)
        # Sujungiame pasiūlymus, rodančius į tą pačią medžiagą.
        by_subs: dict[tuple, tuple[str, float]] = {}
        for lab, sc in merged.items():
            key = tuple(self._subs_for_label(lab))
            if key not in by_subs or sc > by_subs[key][1]:
                by_subs[key] = (lab, sc)
        ranked = sorted(by_subs.values(), key=lambda x: -x[1])
        for nb, lab in K.NOT_IN_DB.items():
            if fuzz.ratio(q, nb) >= FUZZY_ACCEPT:
                return Resolution(query, "not_in_db", label=lab,
                                  note="Medžiaga atpažinta (apytiksliai), bet DDInter jos nėra – "
                                       "sąveikos NETIKRINAMOS.")
        if ranked and ranked[0][1] >= FUZZY_ACCEPT and (
                len(ranked) == 1 or ranked[0][1] - ranked[1][1] >= 3):
            lab, sc = ranked[0]
            subs = self._subs_for_label(lab)
            return Resolution(query, "approx", subs, lab,
                              f"Atpažinta apytiksliai ({sc:.0f} % panašumas) – patikrinkite, ar teisingai.",
                              ranked[:3], sc)
        sugg = [(lab, sc) for lab, sc in ranked if sc >= FUZZY_SUGGEST][:4]
        if len(q) <= 5:  # trumpiems įrašams pirmenybė pavadinimams, prasidedantiems taip pat
            seen, pref = set(), []
            for k in self._choices:
                if k.startswith(q) and tuple(self.index[k][0]) not in seen:
                    seen.add(tuple(self.index[k][0]))
                    pref.append((self.index[k][1], 100.0))
            sugg = pref[:4] or sugg
        if sugg:
            return Resolution(query, "suggest", [], "", "Nepavyko vienareikšmiškai atpažinti.", sugg,
                              sugg[0][1])
        return Resolution(query, "unknown", note="Pavadinimas neatpažintas – šios medžiagos sąveikos "
                                                 "netikrinamos.")

    def _subs_for_label(self, label: str) -> list[str]:
        if label in self.names:
            return [label]
        for subs, lab, _ in self.index.values():
            if lab == label:
                return subs
        return []

    def substances_for_suggestion(self, label: str) -> list[str]:
        return self._subs_for_label(label)


def split_input(text: str) -> list[str]:
    parts = re.split(r"[\n,;+]|\bir\b|\band\b", text)
    return [p.strip() for p in parts if p and p.strip()]
