"""Duomenų paruošimas: DDInter CSV failai -> apdorotos lentelės.

Paleidimas:  python -m src.data_prep

Įvestis:  data/raw/ddinter/ddinter_<ATC>.csv  (DDInter v1 atsisiuntimai pagal ATC grupę)
Išvestis: data/processed/drugs.csv  – vaistų/medžiagų sąrašas su išvestinėmis ATC grupėmis
          data/processed/pairs.csv.gz  – unikalios sąveikų poros su sunkumo lygiu
"""
from __future__ import annotations

import glob
import os
from collections import defaultdict

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(ROOT, "data", "raw", "ddinter")
OUT_DIR = os.path.join(ROOT, "data", "processed")

LEVELS = ["Minor", "Moderate", "Major"]


def load_raw() -> pd.DataFrame:
    frames = []
    for path in sorted(glob.glob(os.path.join(RAW_DIR, "ddinter_*.csv"))):
        letter = os.path.basename(path).split("_")[1][0]
        df = pd.read_csv(path)
        df["atc_file"] = letter
        frames.append(df)
    if not frames:
        raise FileNotFoundError(f"Nerasta DDInter failų kataloge {RAW_DIR}")
    return pd.concat(frames, ignore_index=True)


def infer_atc(raw: pd.DataFrame) -> dict[str, str]:
    """Išveda 1-o lygio ATC grupes.

    DDInter atsisiuntimai suskirstyti pagal ATC grupę: faile X yra visos poros,
    kuriose bent vienas vaistas priklauso grupei X. Todėl jei VISOS vaisto poros
    yra faile X, laikome, kad vaistas priklauso grupei X. Vaistams su labai
    mažai porų tai gali duoti papildomų (klaidingų) raidžių – tai ribotumas.
    """
    pair_files: dict[tuple, set] = defaultdict(set)
    for a, b, f in zip(raw.DDInterID_A, raw.DDInterID_B, raw.atc_file):
        pair_files[(a, b)].add(f)
    drug_pairs: dict[str, list] = defaultdict(list)
    for p in pair_files:
        drug_pairs[p[0]].append(p)
        drug_pairs[p[1]].append(p)
    return {d: "".join(sorted(set.intersection(*[pair_files[p] for p in ps])))
            for d, ps in drug_pairs.items()}


def build() -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = load_raw()
    atc = infer_atc(raw)

    pairs = raw.drop_duplicates(["DDInterID_A", "DDInterID_B"])[
        ["DDInterID_A", "Drug_A", "DDInterID_B", "Drug_B", "Level"]
    ].copy()
    # Simetrija: (A,B) ir (B,A) ta pati pora – normalizuojame tvarką.
    swap = pairs.DDInterID_A > pairs.DDInterID_B
    pairs.loc[swap, ["DDInterID_A", "Drug_A", "DDInterID_B", "Drug_B"]] = pairs.loc[
        swap, ["DDInterID_B", "Drug_B", "DDInterID_A", "Drug_A"]].values
    # Jei ta pati pora pasitaikė su skirtingais lygiais, imame griežčiausią.
    order = {"Unknown": -1, "Minor": 0, "Moderate": 1, "Major": 2}
    pairs["_o"] = pairs.Level.map(order)
    pairs = (pairs.sort_values("_o", ascending=False)
             .drop_duplicates(["DDInterID_A", "DDInterID_B"]).drop(columns="_o"))
    pairs.columns = ["id_a", "drug_a", "id_b", "drug_b", "level"]

    drugs = pd.concat([
        pairs[["id_a", "drug_a"]].set_axis(["id", "name"], axis=1),
        pairs[["id_b", "drug_b"]].set_axis(["id", "name"], axis=1),
    ]).drop_duplicates("id")
    drugs["atc1"] = drugs.id.map(atc).fillna("")
    deg = pd.concat([pairs.id_a, pairs.id_b]).value_counts()
    drugs["n_interactions"] = drugs.id.map(deg).fillna(0).astype(int)
    drugs = drugs.sort_values("name", key=lambda s: s.str.lower()).reset_index(drop=True)
    return drugs, pairs.reset_index(drop=True)


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    drugs, pairs = build()
    drugs.to_csv(os.path.join(OUT_DIR, "drugs.csv"), index=False)
    pairs.to_csv(os.path.join(OUT_DIR, "pairs.csv.gz"), index=False)  # suspausta (GitHub limitas)
    print(f"Vaistų/medžiagų: {len(drugs)}; unikalių porų: {len(pairs)}")
    print(pairs.level.value_counts().to_string())


if __name__ == "__main__":
    main()
