# Agent instructions for `2026-mulukutla-hall-petch`

Read this before changing anything. It records the project state, the
conventions, and the traps. `README.md` covers navigation;
`docs/reproducing.md` covers the run order.

## 1. What this is

Companion repository for the *Acta Materialia* manuscript on best practices
for building and auditing ML strength models, demonstrated on 94 FCC alloy
conditions in Al–Co–Cr–Cu–Fe–Mn–Ni–V (93 with YS, 94 with HV).

Four artifacts must stay consistent with each other and with `results/`:

- **Paper** — `paper/main.tex` + `paper/supplementary.tex`. **These are copies.**
  The canonical source is Overleaf, at
  `~/Dropbox/apps/Overleaf/Revisiting_Hall_Petch/main3.tex` and
  `supplemental2.tex` (note the different filenames). Edit there, then
  re-copy. A stale in-repo paper that contradicts the submitted manuscript is
  the single easiest way to embarrass this project in front of a referee —
  `make verify` checks the two are in sync.
- **Report** — `report/Comprehensive_Analysis_Report.docx`, regenerated from
  live results by `report/generate_report.py`
- **Notebook** — `notebook/Hall_Petch_MPEA_Analysis.ipynb` (generated; edit the
  generator, never the `.ipynb`)
- **Tests** — `tests/test_canonical_values.py`, which recomputes the headline
  values and fails if the manuscript drifts

If you change one, run `make test` and check the others.

## 2. Family order is canonical

```
Family 1  Classical Hall–Petch
Family 2  Physics descriptors (SSS, Wen, PCA-OLS)
Family 3  Composition / processing (M-model hierarchy, incl. M15)
Family 4  Non-linear ML at matched inputs
Family 5  Symbolic regression
```

A higher family number means more flexibility, **not** more physical fidelity.
Script folders under `scripts/` mirror this order, and so do the manuscript's
Methods and Results sections. Keep all three aligned.

## 3. Canonical numbers

All are pooled out-of-fold Q², recomputed by `make test` from
`data/derived/data_with_vlc.csv`. If a run disagrees by more than 0.002, stop
and investigate before editing the paper.

**Dataset**

- 94 conditions; 93 YS, 94 HV; 82 unique compositions (81 in the YS subset)
- 9 chemistries recur across 21 records; 1 composition spans CBB and CBC
- CBB04 / CBB12 share composition *and* processing — the only same-condition
  replicate, and the only direct read on repeatability (32 MPa YS spread)
- *d* 14.66–211.75 µm, SD_grain 8.32–321.06 µm, YS 151.5–544.5 MPa, HV 57.6–227.5
- *r*(*d*, SD_grain) = 0.801

**Batch codes.** `data/raw` stores these in a column named `Iteration`; the
paper calls them batches, because LOBO is defined over them. The code is three
letters: **the first two name the design campaign, the third the batch within
it.** AA, BB and CB are the first, second and third BIRDSHOT campaigns.

| Campaign | Batches | In this dataset |
|---|---|---|
| AA | AAA–AAE | no — different processing route, see `Hastings2025FCC` |
| BB | BBA, BBB, BBC | yes, 35 candidates (34 with YS) |
| CB | CBA, CBB, CBC | yes, 59 candidates |

Two codes in the HTMDEC Drive are **not** part of this study and should not be
reintroduced: `BAA`, a processing route that was discontinued, and `BZZ`/`ZZZ`.
Note the second letter is not an echo of the first — it is CB, never CC — so a
find-and-replace that doubles single letters will produce the wrong code. Both
documents were single-lettered in places until 2026-09-10; if you see "the B
campaign" or "Campaign C" anywhere, it is stale.

**Family 1** — YS 0.405 / 0.406 / 0.373 (5-fold / LOO / LOBO);
HV 0.086 / 0.136 / −0.077. Five two-parameter laws inside ΔBIC < 2.

**Family 2** — SSS standalone LOO: Labusch 0.274, Toda-Caraballo 0.091,
VLC 0.030, all below the 0.406 baseline. Appending an SSS estimate to a
composition model moves LOO by ≤ 0.002; all partial |r| < 0.10.
Fold-contained PCA-OLS 0.462 / 0.480 / 0.362 against 0.525 / 0.516 / 0.441
with global preprocessing.

**Family 3** — the headline result.

| Model | 5-fold | LOO | LOBO | ΔBIC vs M3 |
|---|---|---|---|---|
| M0 baseline | — | 0.406 | 0.373 | +36.5 |
| M3 σ₀(all 7) | 0.666 | 0.652 | 0.625 | 0.0 |
| M13 M3 + additive SD | 0.658 | 0.668 | 0.595 | −2.3 |
| **M15 M3 + SD + SD·d^−1/2** | **0.731** | **0.694** | **0.694** | **−20.1** |

M3: k_HP = 765.8, α_V = +291.3 MPa. M15 interaction coefficient t = 4.71.
**M13 is the control, not a competitor** — it gains at LOO and loses at LOBO,
which is what shows the gain comes from the interaction and not from measuring
grain width. Do not delete it from the analysis even though the figure shows
only M15.

**Family 4** — fixed-settings panel: Lasso S2 0.683 / 0.674 / 0.621;
LightGBM S2 0.632 / 0.574 / 0.615. Bootstrap intervals overlap, so there is no
evidence non-linearity helps at matched inputs. Nested ARMOTE-CV panel:
Bayesian ridge S2 0.685 / 0.666 / 0.613 (see §7 — verified, not archival).

**Family 5** — HV fixed form 0.725 / 0.727 / 0.636 after fold-wise constant
refitting, post-selected structure.

**Literature stress test** — every direct-measurement R² is negative:
M3 −0.508 (RMSE 149.5), SISSO Robust −0.726 (160.0), SISSO Full −5.084 (300.3).

**Tabor** — C_eff = 5.13 ± 1.36 across 93 paired records.

## 4. Traps

**The HV equation signs.** The reported form is

    HV = 222.3 + 84.5 (6.93 − d)/SD_grain − 1.005 ΔH_mix / t_hold²

with R² = 0.744. An earlier draft printed `−83.95` and `+1`, which evaluates to
**R² = −29.8** and predicts HV in 239–389 against an observed 58–228. If you
ever see those signs, they are wrong.

**t_hold is confounded with campaign.** The B campaign has a single hold time
(0.5 h); C has {1, 2, 4, 8}. Raw hold time separates the campaigns perfectly
(AUC = 1.000) and ΔH_mix/t² nearly so (AUC = 0.970). Any model term in
t_hold is partly a campaign indicator. The grain-width ratio is *not*
(AUC = 0.533).

**"Grain only" means two different things.** The Family 1 baseline is
*d*^−1/2 alone; the S1 matrix also contains SD_grain. A Family-1-vs-S1
comparison mixes a change of estimator with a change of inputs. For HV the
extra feature actively hurts transfer (LOBO −0.077 → −0.176 for a linear fit).

**SD_grain is not uncertainty.** It is the within-map standard deviation of
the grain-size distribution — a microstructure descriptor, and a model input.
`SD_YS` and `SD_HV` are measurement scatter on the targets and are **never**
used as features.

**One PySR equation hides a pole.** The descriptor-based accuracy form
contains `SD_grain/√|ΔS_mix − 8.2739|`. The internal minimum is 8.3637, only
0.0898 above the pole. The protected square root keeps it real, so it diverges
silently rather than erroring.

**Hardness does not convert to yield strength.** Tabor's relation assumes a
rigid-plastic, non-hardening solid; indentation samples flow stress at a
representative strain, not the offset yield point. The ratio therefore carries
the work-hardening response, and this dataset measures it as
C_eff = HV/σ_y = 5.13 ± 1.36, not 3. Treat HV and YS as separate targets with
separate models and separate validation. Two consequences to preserve:

- `results/literature_kHP_table.csv` (SI Table S12) admits only coefficients
  fitted to a *measured* yield strength. `literature_kHP_table.py` asserts
  this. In particular no pure metal appears, because the standard survey
  values pool Vickers and nanoindentation hardness divided by a Tabor factor
  of 3 with tension and compression data in one fit.
- The 25 E3 literature points are HV proxies converted with C_eff inferred
  from *this* dataset. They are model-derived evidence, never independent
  external measurements, and are never pooled with E1 to inflate the external
  count.

**Do not edit the `.ipynb`.** Edit `notebook/_generate_notebook.py` and re-run.

## 4a. Two-column typesetting

`paper/main.tex` is `\documentclass[5p,times,twocolumn]{elsarticle}` — the
Elsevier journal layout, not a preprint. Other group papers write
`[final,5p,times,twocolumn]`; `final` is a no-op once `5p` is given (tested:
identical page count, identical text layer, no "Preprint submitted to" footer),
so either spelling is fine. The supplement is plain `article`, single column.

Rules the layout imposes, all currently satisfied:

- **A graphic's width unit must match its float.** `\columnwidth` inside
  `figure`, `\textwidth` inside `figure*`. Putting a `\textwidth` graphic in an
  unstarred float in two-column mode overflows the column by roughly a factor
  of two.
- **Wide content goes in `figure*` / `table*`**, which span both columns and
  can only be placed at the top of a page. Currently 4 `figure*` and 3
  `table*`; the rest are single-column.
- **Long equations need explicit breaks.** Eq. 8 uses `\begin{split}`; without
  it the HV form runs past the column. There is no automatic line breaking in
  display maths.
- **`[H]` is fragile here.** Two tables use it (`tab:families`, `tab:inputs`).
  It renders correctly today, but `[H]` forbids float migration, so inserted
  text can push a table into a bad break instead of letting it float. Prefer
  `[t]` if either one starts misbehaving.

Check before shipping a build: `Overfull \hbox` and `Overfull \vbox` must both
be **zero** in `paper/main.log`. They are today. A few `Underfull` warnings are
loose inter-word spacing and are cosmetic. Note the shell aliases `grep` to
`ugrep`, whose `-c` prints nothing here — count with Python, not `grep -c`.

**Never build in the Overleaf folder.** `~/Dropbox/apps/Overleaf/Revisiting_Hall_Petch`
is synced against a live Overleaf project that co-authors edit. Every
`pdflatex` run there writes `.aux/.log/.out/.bbl` against names Overleaf also
writes, and Dropbox resolves the collision by forking a "conflicted copy" —
that is where six of them came from in one session. Copy the sources to a
scratch directory, build there, and copy only the PDFs back.

**Clean up after every successful compile**, wherever it ran:

```bash
find . -maxdepth 1 -type f \( -name "*.aux" -o -name "*.log" -o -name "*.out" \
  -o -name "*.bbl" -o -name "*.blg" -o -name "*.toc" -o -name "*.synctex.gz" \
  -o -name "*.fls" -o -name "*.fdb_latexmk" -o -name "*.spl" \) -delete
```

Use `find`, not a glob: zsh aborts the whole command when a pattern like
`*.synctex.gz` matches nothing.

## 4b. Submission package

`scripts/make_submission.py` builds the review-format package at
`~/Dropbox/TAMU/Submissions/2026_Mulukutla_HallPetch`. That folder is
**outside this repository on purpose** — it is derived, it duplicates every
figure, and it ships to the publisher as a unit.

**main3.tex and supplemental2.tex are the only sources of truth.** To change
anything in the submission, edit the Overleaf source and re-run the script.
Never hand-edit a file in the submission folder; the next build discards it.

```bash
python3 scripts/make_submission.py           # build + verify
python3 scripts/make_submission.py --check   # drift check, writes nothing
```

What the build does, and why each step exists:

- **Review format.** elsarticle's `review` option gives a single column at 1.5
  spacing but does *not* number lines — the class never loads `lineno`, so the
  script adds it. The supplement gets line numbers too; reviewers cite them.
- **Bibliography inlined.** The `.bbl` is spliced in as a `thebibliography`
  environment replacing `\bibliography{references}`, so the package needs no
  `.bib` and no bibtex pass.
- **Figures flattened.** `\graphicspath` is dropped and figures are renamed
  `fig<N>_<desc>.png` / `figS<N>_<desc>.png` in order of first appearance,
  living beside the `.tex` with no subdirectory.
- **Verified in isolation.** The emitted package is copied to an empty
  directory and compiled with pdflatex alone. Any undefined reference fails
  the build.

That last check exists because of a real failure. `\ref` across the two
documents resolves fine while they share an Overleaf project and silently
becomes `??` once they compile separately — the manuscript referenced
`tab:khplit` (in the SI) and the SI referenced `fig:fair` (in the manuscript).
Cross-document references must be written out literally ("Table S12 of the
Supplementary Information", "Fig. 8 of the main text"). Note also that grepping
a LaTeX log for `Citation.*undefined` will **not** catch these; they are
`Reference ... undefined`.

Anything else already in the submission folder is left alone — the script only
writes files it generates.

## 5. Figure conventions

`scripts/_figstyle.py` is the single source of truth for colour and type.
Every figure script imports it. `fig00_framework_overview.png`,
`composition_microstructure.png` and `tensile_tests.png` are deliberately
exempt.

- Okabe–Ito palette; verified under simulated deuteranopia, protanopia and
  tritanopia
- Colour is never the only channel: batches carry distinct markers, model
  families are separated by position, signed values print their number
- Figures are authored at their **final printed width** (`S.W_COL` = 3.45 in,
  `S.W_FULL` = 7.16 in) so a point size in the script is the same point size on
  the page. A wide figure placed at `\columnwidth` renders its text at half
  size — match the authored width to the `\includegraphics` width.
- Constrained layout is on globally; do not add `tight_layout` or
  `subplots_adjust`
- Titles go through `S.title()` so they are uniformly bold

## 6. Before committing

| Changed | Run | Expect |
|---|---|---|
| any analysis script | `make test` | 18 passed |
| a figure script | that script, then `make paper` | 0 errors |
| the notebook generator | `make notebook` | "Total cells" printed |
| the paper | `make paper` | main 16 pp., supplementary 26 pp., 0 undefined |
| results feeding the report | `make report` | "Report saved" |
| anything at all | `make verify` | no drift reported |

Delete LaTeX aux files before committing (`make clean` does it).

## 7. Archival vs reproducible

The manuscript separates these deliberately, and so should you:

- **Reproducible here** — the M-model hierarchy including M15, Family 1
  baselines, fold-contained PCA-OLS, matched-input Family 4, the literature
  stress test, Tabor, the dataset audit.
- **Verified from stored artifacts** — the nested ARMOTE-CV panel. Its
  generator stores one Optuna study, one selected parameter set, and one pair
  of feature and target scalers per fold. Across the six LOBO folds the five
  tuned Bayesian-ridge hyperparameters (`max_iter`, `alpha_1`, `alpha_2`,
  `lambda_1`, `lambda_2`; see `armote_cv/run_lobo.py`) take six distinct
  values, and the scalers are fitted on each training split alone. Note that
  the generator's `Avg Test R2` column holds the **pooled** Q², not the mean of
  the fold scores — for this model the fold mean is 0.522 against a pooled
  0.613. Reloading those objects and predicting
  each held-out batch reproduces the six fold scores exactly and gives a pooled
  LOBO Q² of 0.613 with RMSE 50.5 MPa. The manuscript therefore reports the
  nesting as verified, not assumed — do not downgrade it to archival.
- **Archival** — Bayesian PSIS-LOO stacking weights (PyMC draws not retained)
  and outer-loop PySR performance (structures were selected on complete-data
  fronts). Report these as archival.

## 8. When in doubt

Read the relevant section of `paper/main.tex`, then `docs/reproducing.md`,
then `docs/validation_protocol.md`. Prefer recomputing a number over trusting
a printed one.
