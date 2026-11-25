"""Paleidimas:  python -m pytest -q"""
import pandas as pd
import pytest

from src import knowledge as K
from src.checker import Checker
from src.features import rule_hits


@pytest.fixture(scope="module")
def checker():
    return Checker()


def test_knowledge_names_exist(checker):
    names = set(checker.all_names)
    for c in K.RISK_CLASSES.values():
        assert set(c["members"]) <= names
    for subs in K.BRANDS.values():
        assert set(subs) <= names
    assert set(K.LT_NAMES) <= names


@pytest.mark.parametrize("q,expected", [
    ("Nurofen 400 mg", ["Ibuprofen"]), ("varfarinas", ["Warfarin"]),
    ("Žuvų taukai", ["Omega-3 fatty acids"]), ("jonažolė", ["St. John's Wort"]),
    ("paracetamolis", ["Acetaminophen"]), ("ciprofloksacinas", ["Ciprofloxacin"]),
    ("Augmentin", ["Amoxicillin", "Clavulanic acid"]), ("kava", ["Caffeine"]),
    ("varfrinas", ["Warfarin"]),  # rašybos klaida
])
def test_resolution(checker, q, expected):
    assert checker.matcher.resolve(q).substances == expected


def test_not_in_db_and_unknown(checker):
    assert checker.matcher.resolve("Analginas").status == "not_in_db"
    assert checker.matcher.resolve("xyzabc").status == "unknown"


@pytest.mark.parametrize("a,b,level", [
    ("Warfarin", "Ibuprofen", "Major"), ("Clarithromycin", "Simvastatin", "Major"),
    ("Sildenafil", "Nitroglycerin", "Major"), ("Grapefruit juice", "Simvastatin", "Major"),
])
def test_known_interactions(checker, a, b, level):
    assert checker.check_pair(a, b, a, b).level == level


def test_rules():
    assert {h["id"] for h in rule_hits("Oxycodone", "Alprazolam")} == {"opioid_benzo"}
    assert rule_hits("Diclofenac (topical)", "Warfarin") == []


def test_group_warnings(checker):
    entries = checker.resolve("Nurofen\nIbumetin\nRamiprilis\nFurozemidas")
    _, groups = checker.check(entries)
    titles = " ".join(g.title for g in groups)
    assert "kartojasi" in titles and "Trigubas" in titles


def test_ai_prediction_has_caution(checker):
    pairs = pd.read_csv("data/processed/pairs.csv.gz")
    row = pairs[pairs.level == "Unknown"].iloc[0]
    r = checker.check_pair(row.drug_a, row.drug_b, "a", "b")
    assert r.source == "DDInter + AI" and r.ai_probs
    assert any("atsargiai" in c for c in r.cautions)
