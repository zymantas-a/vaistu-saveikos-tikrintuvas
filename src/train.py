"""AI modelio mokymas ir eksperimentai (Baseline vs Proposed).

Užduotis: pagal vaistų poros požymius prognozuoti sąveikos sunkumą
(Minor / Moderate / Major). Programėlėje modelis naudojamas toms DDInter poroms,
kurių sunkumas nenurodytas („Unknown“, ~42 tūkst. porų).

Paleidimas:  python -m src.train
Rezultatai:  models/, reports/metrics.json, reports/metrics_table.md, reports/figures/*.png
"""
from __future__ import annotations

import gzip
import json
import os
import time

import lightgbm as lgb
import matplotlib
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, classification_report, confusion_matrix,
                             f1_score, precision_score, recall_score)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from . import features as F

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC = os.path.join(ROOT, "data", "processed")
MODELS = os.path.join(ROOT, "models")
REPORTS = os.path.join(ROOT, "reports")
FIGS = os.path.join(REPORTS, "figures")
SEED = 42
LEVEL_LT = {"Minor": "Maža", "Moderate": "Vidutinė", "Major": "Didelė"}
COLORS = {"Minor": "#4C9F70", "Moderate": "#E0A100", "Major": "#C8382C", "Unknown": "#8C8C8C"}

LGB_PARAMS = dict(objective="multiclass", num_class=3, learning_rate=0.05, num_leaves=63,
                  min_child_samples=30, feature_fraction=0.8, bagging_fraction=0.8,
                  bagging_freq=1, lambda_l2=1.0, verbose=-1, seed=SEED)


def metrics(y_true, y_pred) -> dict:
    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision_macro": precision_score(y_true, y_pred, average="macro", zero_division=0),
        "recall_macro": recall_score(y_true, y_pred, average="macro", zero_division=0),
        "f1_macro": f1_score(y_true, y_pred, average="macro"),
        "f1_weighted": f1_score(y_true, y_pred, average="weighted"),
        "f1_per_class": dict(zip(F.LEVELS, f1_score(y_true, y_pred, average=None,
                                                    labels=[0, 1, 2]).round(4).tolist())),
    }


def class_weights(y) -> np.ndarray:
    counts = np.bincount(y, minlength=3)
    w = len(y) / (3 * counts)
    return w[y]


def train_lgb(Xtr, ytr, Xva, yva, balanced: bool, rounds: int | None = None):
    dtr = lgb.Dataset(Xtr, ytr, weight=class_weights(ytr) if balanced else None)
    evals = {}
    if rounds is None:
        dva = lgb.Dataset(Xva, yva, weight=class_weights(yva) if balanced else None, reference=dtr)
        booster = lgb.train(LGB_PARAMS, dtr, num_boost_round=2000, valid_sets=[dtr, dva],
                            valid_names=["mokymo", "validacijos"],
                            callbacks=[lgb.early_stopping(50, verbose=False),
                                       lgb.record_evaluation(evals)])
    else:
        booster = lgb.train(LGB_PARAMS, dtr, num_boost_round=rounds)
    return booster, evals


def rule_predict(X: pd.DataFrame) -> np.ndarray:
    r = X["rule_max_level"].to_numpy()
    return np.where(r >= 0, r, 1)  # jei taisyklė nesuveikė – „Moderate“


def plot_confusion(cm, title, path):
    fig, ax = plt.subplots(figsize=(4.6, 4))
    cmn = cm / cm.sum(axis=1, keepdims=True)
    ax.imshow(cmn, cmap="Blues", vmin=0, vmax=1)
    labels = [LEVEL_LT[l] for l in F.LEVELS]
    ax.set_xticks(range(3), labels)
    ax.set_yticks(range(3), labels)
    ax.set_xlabel("Prognozė")
    ax.set_ylabel("Tikroji klasė (DDInter)")
    for i in range(3):
        for j in range(3):
            ax.text(j, i, f"{cm[i, j]}\n{cmn[i, j]:.0%}", ha="center", va="center",
                    color="white" if cmn[i, j] > 0.55 else "#222", fontsize=9)
    ax.set_title(title, fontsize=11)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def run_split(train_df, test_df, drugs, name):
    """Visi modeliai vienam padalijimui. Grąžina rezultatus ir geriausią LightGBM."""
    t0 = time.time()
    tr_in, va_in = train_test_split(train_df, test_size=0.1, random_state=SEED,
                                    stratify=train_df.y)
    Xtr = F.oof_drug_stats_features(tr_in, drugs)
    Xva = F.build_features(va_in, drugs, F.drug_stats(tr_in))
    Xte = F.build_features(test_df, drugs, F.drug_stats(train_df))
    ytr, yva, yte = tr_in.y.to_numpy(), va_in.y.to_numpy(), test_df.y.to_numpy()
    print(f"[{name}] požymiai paruošti per {time.time() - t0:.0f} s; "
          f"mokymo {len(Xtr)}, valid. {len(Xva)}, testo {len(Xte)}")

    res, preds = {}, {}
    dummy = DummyClassifier(strategy="most_frequent").fit(Xtr, ytr)
    preds["B0: dažniausia klasė"] = dummy.predict(Xte)
    preds["B1: taisyklės"] = rule_predict(Xte)
    simple_cols = [c for c in Xtr.columns if c.startswith(("atc_", "cls_", "rule_"))] + \
        ["topical", "supplement"]
    logreg = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000,
                                                                class_weight="balanced"))
    logreg.fit(Xtr[simple_cols], ytr)
    preds["B2: logistinė regresija"] = logreg.predict(Xte[simple_cols])

    boosters = {}
    for balanced in (False, True):
        b, ev = train_lgb(Xtr, ytr, Xva, yva, balanced)
        f1v = f1_score(yva, b.predict(Xva).argmax(1), average="macro")
        key = "P: LightGBM" + (" (subalansuoti svoriai)" if balanced else "")
        boosters[key] = (b, ev, f1v, balanced)
        preds[key] = b.predict(Xte).argmax(1)
    for k, p in preds.items():
        res[k] = metrics(yte, p)
    best_key = max(boosters, key=lambda k: boosters[k][2])
    print(f"[{name}] geriausias pagal validacijos macro-F1: {best_key}")
    return res, preds, boosters, best_key, (Xtr, Xte, yte)


def main():
    os.makedirs(FIGS, exist_ok=True)
    os.makedirs(MODELS, exist_ok=True)
    drugs = pd.read_csv(os.path.join(PROC, "drugs.csv"))
    pairs = pd.read_csv(os.path.join(PROC, "pairs.csv.gz"))
    lab = pairs[pairs.level.isin(F.LEVELS)].copy()
    lab["y"] = lab.level.map(F.LEVEL_TO_INT)
    lab = lab.reset_index(drop=True)

    # ---------------- Duomenų vizualizacija ----------------
    fig, ax = plt.subplots(figsize=(6, 3.4))
    vc = pairs.level.value_counts().reindex(["Major", "Moderate", "Minor", "Unknown"])
    ax.bar([LEVEL_LT.get(i, "Nežinoma") for i in vc.index], vc.values,
           color=[COLORS[i] for i in vc.index])
    for i, v in enumerate(vc.values):
        ax.text(i, v, f"{v:,}".replace(",", " "), ha="center", va="bottom", fontsize=9)
    ax.set_ylabel("Porų skaičius")
    ax.set_title("DDInter sąveikų pasiskirstymas pagal sunkumą")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGS, "01_klasiu_pasiskirstymas.png"), dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 3.4))
    ax.hist(drugs.n_interactions, bins=60, color="#3B6EA8")
    ax.set_xlabel("Sąveikų skaičius vienam vaistui")
    ax.set_ylabel("Vaistų skaičius")
    ax.set_title("Kiek sąveikų turi vienas vaistas (DDInter)")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGS, "02_saveiku_skaicius.png"), dpi=150)
    plt.close(fig)

    # ---------------- 1 eksperimentas: atsitiktinis porų padalijimas ----------------
    train_df, test_df = train_test_split(lab, test_size=0.2, random_state=SEED, stratify=lab.y)
    res, preds, boosters, best_key, (Xtr, Xte, yte) = run_split(train_df, test_df, drugs,
                                                                 "atsitiktinis")
    best_booster, best_evals, _, best_bal = boosters[best_key]

    plot_confusion(confusion_matrix(yte, preds["B2: logistinė regresija"]),
                   "Baseline: logistinė regresija", os.path.join(FIGS, "03_konfuzija_baseline.png"))
    plot_confusion(confusion_matrix(yte, preds[best_key]), "Proposed: LightGBM",
                   os.path.join(FIGS, "04_konfuzija_lightgbm.png"))

    fig, ax = plt.subplots(figsize=(6, 3.4))
    for nm, c in [("mokymo", "#3B6EA8"), ("validacijos", "#C8382C")]:
        ax.plot(best_evals[nm]["multi_logloss"], label=f"{nm} imtis", color=c)
    ax.axvline(best_booster.best_iteration, ls="--", color="#666", lw=1)
    ax.text(best_booster.best_iteration, ax.get_ylim()[1] * 0.98, " ankstyvas sustabdymas",
            fontsize=8, va="top")
    ax.set_xlabel("Iteracija (medžių skaičius)")
    ax.set_ylabel("Multi-logloss")
    ax.set_title("LightGBM mokymosi kreivė")
    ax.legend()
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGS, "05_mokymosi_kreive.png"), dpi=150)
    plt.close(fig)

    names = list(res)
    fig, ax = plt.subplots(figsize=(8, 3.8))
    x = np.arange(len(names))
    for i, (m, c) in enumerate([("accuracy", "#9DB4D3"), ("f1_macro", "#3B6EA8"),
                                ("f1_weighted", "#1F3B5C")]):
        ax.bar(x + (i - 1) * 0.27, [res[n][m] for n in names], 0.27, label=m, color=c)
    ax.axhline(0.70, ls="--", color="#C8382C", lw=1)
    ax.text(len(names) - 0.5, 0.71, "0,70 riba", color="#C8382C", fontsize=8, ha="right")
    ax.set_xticks(x, [n.replace(": ", ":\n") for n in names], fontsize=8)
    ax.set_ylim(0, 1)
    ax.legend(fontsize=8, loc="upper left")
    ax.set_title("Modelių palyginimas (testo imtis, atsitiktinis padalijimas)")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGS, "06_modeliu_palyginimas.png"), dpi=150)
    plt.close(fig)

    # SHAP (LightGBM integruotas TreeSHAP: pred_contrib=True)
    sample = Xte.sample(min(5000, len(Xte)), random_state=SEED)
    contrib = best_booster.predict(sample, pred_contrib=True)
    nf = sample.shape[1]
    contrib = contrib.reshape(len(sample), 3, nf + 1)[:, :, :nf]
    imp = np.abs(contrib).mean(axis=0)  # (3, nf)
    total = imp.sum(0)
    order = np.argsort(total)[::-1][:15][::-1]
    fig, ax = plt.subplots(figsize=(7, 5))
    left = np.zeros(len(order))
    for k, lvl in enumerate(F.LEVELS):
        ax.barh(range(len(order)), imp[k, order], left=left, color=COLORS[lvl], label=LEVEL_LT[lvl])
        left += imp[k, order]
    ax.set_yticks(range(len(order)), [F.shap_label(sample.columns[i]) for i in order], fontsize=8)
    ax.set_xlabel("Vidutinė |SHAP| reikšmė")
    ax.set_title("Svarbiausi požymiai (SHAP, LightGBM)")
    ax.legend(title="Klasė", fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGS, "07_shap_svarbiausi.png"), dpi=150)
    plt.close(fig)

    # ---------------- 2 eksperimentas: nauji (nematyti) vaistai ----------------
    rng = np.random.default_rng(SEED)
    all_drugs = pd.unique(pd.concat([lab.drug_a, lab.drug_b]))
    held = set(rng.choice(all_drugs, size=int(0.1 * len(all_drugs)), replace=False))
    is_cold = lab.drug_a.isin(held) | lab.drug_b.isin(held)
    res_cold, preds_cold, b_cold, best_cold, _ = run_split(lab[~is_cold], lab[is_cold], drugs,
                                                            "nauji vaistai")

    # ---------------- Galutinis modelis (visi pažymėti duomenys) ----------------
    X_all = F.oof_drug_stats_features(lab, drugs)
    final, _ = train_lgb(X_all, lab.y.to_numpy(), None, None, best_bal,
                         rounds=max(50, int(best_booster.best_iteration * 1.1)))
    # Modelis saugomas suspaustas, kad tilptų į GitHub (naršyklės įkėlimo riba 25 MB)
    with gzip.open(os.path.join(MODELS, "lightgbm_severity.txt.gz"), "wt", encoding="utf-8") as f:
        f.write(final.model_to_string())
    stats_all = F.drug_stats(lab)
    stats_all.to_csv(os.path.join(MODELS, "drug_stats.csv"))
    with open(os.path.join(MODELS, "model_meta.json"), "w", encoding="utf-8") as f:
        json.dump({"features": list(X_all.columns), "levels": F.LEVELS, "balanced": best_bal,
                   "best_iteration": int(best_booster.best_iteration),
                   "trained_on_pairs": int(len(lab)), "model_choice": best_key}, f,
                  ensure_ascii=False, indent=2)

    # ---------------- Ataskaita ----------------
    report = {
        "dataset": {"pairs_total": int(len(pairs)), "labeled": int(len(lab)),
                    "unknown": int((pairs.level == "Unknown").sum()),
                    "drugs": int(len(drugs)),
                    "class_counts": lab.level.value_counts().to_dict()},
        "experiment_random_split": res, "best_model": best_key,
        "experiment_cold_drugs": res_cold, "best_model_cold": best_cold,
        "classification_report": classification_report(
            yte, preds[best_key], target_names=F.LEVELS, output_dict=True),
    }
    with open(os.path.join(REPORTS, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    def table(r):
        lines = ["| Modelis | Accuracy | Precision (macro) | Recall (macro) | F1 (macro) | "
                 "F1 (weighted) | F1 Minor | F1 Moderate | F1 Major |",
                 "|---|---|---|---|---|---|---|---|---|"]
        for k, v in r.items():
            pc = v["f1_per_class"]
            lines.append(f"| {k} | {v['accuracy']:.3f} | {v['precision_macro']:.3f} | "
                         f"{v['recall_macro']:.3f} | {v['f1_macro']:.3f} | {v['f1_weighted']:.3f} | "
                         f"{pc['Minor']:.3f} | {pc['Moderate']:.3f} | {pc['Major']:.3f} |")
        return "\n".join(lines)

    md = ("## 1 eksperimentas – atsitiktinis porų padalijimas (80/20)\n\n" + table(res) +
          f"\n\nGeriausias modelis: **{best_key}**\n\n"
          "## 2 eksperimentas – nauji vaistai (10 % vaistų neįtraukta į mokymą)\n\n" +
          table(res_cold) + f"\n\nGeriausias modelis: **{best_cold}**\n")
    with open(os.path.join(REPORTS, "metrics_table.md"), "w", encoding="utf-8") as f:
        f.write(md)
    print(md)


if __name__ == "__main__":
    main()
