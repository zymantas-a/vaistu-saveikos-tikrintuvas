## 1 eksperimentas – atsitiktinis porų padalijimas (80/20)

| Modelis | Accuracy | Precision (macro) | Recall (macro) | F1 (macro) | F1 (weighted) | F1 Minor | F1 Moderate | F1 Major |
|---|---|---|---|---|---|---|---|---|
| B0: dažniausia klasė | 0.746 | 0.249 | 0.333 | 0.285 | 0.638 | 0.000 | 0.855 | 0.000 |
| B1: taisyklės | 0.752 | 0.534 | 0.343 | 0.306 | 0.652 | 0.000 | 0.857 | 0.061 |
| B2: logistinė regresija | 0.521 | 0.451 | 0.559 | 0.431 | 0.569 | 0.201 | 0.620 | 0.471 |
| P: LightGBM | 0.888 | 0.855 | 0.751 | 0.789 | 0.885 | 0.654 | 0.928 | 0.787 |
| P: LightGBM (subalansuoti svoriai) | 0.837 | 0.701 | 0.843 | 0.751 | 0.846 | 0.608 | 0.887 | 0.757 |

Geriausias modelis: **P: LightGBM**

## 2 eksperimentas – nauji vaistai (10 % vaistų neįtraukta į mokymą)

| Modelis | Accuracy | Precision (macro) | Recall (macro) | F1 (macro) | F1 (weighted) | F1 Minor | F1 Moderate | F1 Major |
|---|---|---|---|---|---|---|---|---|
| B0: dažniausia klasė | 0.729 | 0.243 | 0.333 | 0.281 | 0.615 | 0.000 | 0.843 | 0.000 |
| B1: taisyklės | 0.738 | 0.551 | 0.348 | 0.310 | 0.637 | 0.000 | 0.848 | 0.084 |
| B2: logistinė regresija | 0.512 | 0.451 | 0.544 | 0.422 | 0.556 | 0.171 | 0.597 | 0.499 |
| P: LightGBM | 0.761 | 0.639 | 0.553 | 0.583 | 0.752 | 0.379 | 0.846 | 0.524 |
| P: LightGBM (subalansuoti svoriai) | 0.682 | 0.516 | 0.605 | 0.532 | 0.705 | 0.276 | 0.784 | 0.536 |

Geriausias modelis: **P: LightGBM**
