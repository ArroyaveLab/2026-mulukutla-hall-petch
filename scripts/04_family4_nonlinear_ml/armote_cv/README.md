# ARMOTE-CV nested tuning panel

Author: **Shakti Prasad Padhy**. Vendored here so this repository is
self-contained; the upstream project is the primary record.

- Upstream: <https://github.com/Shakti-95/ARMOTE-CV-MPEA-Hall-Petch>
- Commit:   `1fdc804a20986bd8c0153f3fd4e047e89e130355` (2026-09-07)
- Licence:  MIT (`LICENSE`, carried over)

Mrinalini's earlier repository referenced this project as a git submodule.
A submodule breaks the moment the target moves or changes visibility, and a
referee following the data-availability link would be the one to find out, so
the artifacts are copied in as ordinary files instead.

## What this supports

The manuscript reports the nested ARMOTE-CV panel as **verified rather than
assumed** (SI §Family 4). Everything needed to check that claim without
re-running anything is here:

| Reported | Value | Where |
|---|---|---|
| YS Bayesian ridge S2, 5-fold | 0.685 | `S2_YS_Results_5_Fold_CV/` |
| YS Bayesian ridge S2, LOBO (pooled Q²) | 0.613 | `S2_YS_Results_LOBO_CV/` |
| RMSE, LOBO | 50.5 MPa | same |

To re-verify:

```bash
python3 - <<'PY'
import pandas as pd, ast, numpy as np
d = pd.read_csv('S2_YS_Results_LOBO_CV/YS_results_6_fold_CV.csv')
r = d[d['Model'] == 'BayesianRidge'].iloc[0]
print('pooled Q2 :', round(r['Avg Test R2'], 4))          # 0.6131
folds = ast.literal_eval(r['All Fold Test R2'])
print('fold mean :', round(float(np.mean(folds)), 4))      # 0.5221
params = ast.literal_eval(r['Best Params Per Fold'])
print('folds     :', len(params), '  distinct param sets:', len({str(p) for p in params}))
PY
```

Two traps that column layout sets:

- **`Avg Test R2` is the pooled Q², not the mean of the fold scores.** For this
  model the pooled value is 0.613 and the fold mean is 0.522. The manuscript
  reports the pooled value and says so; do not quote the column as an average.
- **Five hyperparameters are tuned**, not four: `max_iter`, `alpha_1`,
  `alpha_2`, `lambda_1`, `lambda_2` (`run_lobo.py`, `param_spaces`). All six
  LOBO folds select distinct sets, which is what shows the search really is
  nested inside each training split.

## What was kept, and what was not

Upstream is ~2.7 GB. Kept here (~23 MB): the LOBO and 5-fold protocols for
S1/S2 × YS/HV, their Optuna studies, their scalers, the per-protocol score
CSVs, and the fitted models for every estimator except the seven large
ensembles. Also the generator itself — `armote_cv.py`, `run_lobo.py`,
`run_5fold.py`, `run_loo.py`, `build_summary.py`.

Left upstream:

| Excluded | Size | Why |
|---|---|---|
| `S*_Results_LOO_CV/` | 2383 MB | the LOO protocol's per-fold objects; the verification claim rests on LOBO |
| `**/plots/` | 603 MB | 26,108 per-fold parity PNGs, regenerable from the CSVs |
| ExtraTrees, CatBoost, Stacking, RandomForest, GradientBoosting, LightGBM, XGBoost `.pkl` | 1840 MB | refit-able from the stored per-fold hyperparameters; their scores are already in the CSVs, and the manuscript excludes CatBoost and the decision tree outright |

Nothing the manuscript reports depends on an excluded file. `run_loo.py` is
included, so the LOO protocol can be regenerated if it is ever needed.
