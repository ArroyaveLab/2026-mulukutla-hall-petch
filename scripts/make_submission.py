#!/usr/bin/env python3
"""
Build the journal submission package
====================================
Generates self-contained review-format documents from the canonical Overleaf
sources. The submission folder deliberately lives OUTSIDE this repository: it
is a derived artifact, it duplicates every figure, and it is handed to the
publisher as a unit.

What "self-contained" means here
--------------------------------
Each emitted .tex compiles with nothing beside it but its figure files:

  - no \\bibliography{references}  -- the .bbl is spliced in as a
    thebibliography environment, so no .bib and no bibtex pass are needed
  - no \\graphicspath              -- figures sit next to the .tex and are
    referenced by bare filename, with no subdirectory
  - figures renamed fig<N>_<description>.<ext> for the manuscript and
    figS<N>_<description>.<ext> for the supplement, numbered in order of first
    appearance, so figure 3 in the PDF is fig3_*.png on disk

Review formatting
-----------------
elsarticle's `review` option gives a single column at 1.5 line spacing but does
NOT number lines -- the class never loads lineno. Line numbers are added here
explicitly, for the supplement as well as the manuscript, because reviewers
cite supplement lines too.

Synchronisation
---------------
main3.tex and supplemental2.tex are the only sources of truth. This script
always regenerates from them, and `--check` verifies nothing has drifted
without writing. Never hand-edit anything in the submission folder; the next
build silently discards it.

Usage
-----
  python3 scripts/make_submission.py            # build
  python3 scripts/make_submission.py --check    # verify sync, exit 1 on drift
"""
import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

OVERLEAF = Path.home() / "Dropbox/apps/Overleaf/Revisiting_Hall_Petch"
FIGDIR = OVERLEAF / "figures"
SUBMISSION = Path.home() / "Dropbox/TAMU/Submissions/2026_Mulukutla_HallPetch"
REPO_PAPER = Path(__file__).resolve().parent.parent / "paper"

MANUSCRIPT_PREAMBLE = r"""\documentclass[review,12pt]{elsarticle}

%% Review format: single column, 1.5 line spacing (elsarticle "review"),
%% with line numbers added here because the class does not load lineno.
\usepackage{lineno}
\linenumbers
"""

DESCRIPTIONS = {
    # manuscript
    "fig00_framework_overview": "framework_overview",
    "composition_microstructure": "composition_microstructure",
    "fig_provenance": "campaign_provenance",
    "fig01_hall_petch": "hall_petch_baseline",
    "fig_scaling_fits_ys": "scaling_law_fits",
    "fig_sss_parity": "solid_solution_parity",
    "fig_comp_hp_models_ab": "composition_hall_petch",
    "fair_comparison_LOBO_heatmap": "matched_input_lobo",
    "fig08_pysr_pareto": "symbolic_pareto_front",
    "fig_hv_ys_rank": "hardness_yield_rank",
    # supplement
    "fig_property_histograms": "property_histograms",
    "tensile_tests": "tensile_curves",
    "fig02_correlation_matrix": "correlation_matrix",
    "fig_premodel_hulls_heatmap": "composition_hulls",
    "fig_scaling_deltabic": "scaling_law_deltabic",
    "fig_scaling_fits_hv": "scaling_fits_hardness",
    "fig_bayesian_n": "bayesian_exponent",
    "fig_bayesian_bma": "bayesian_model_averaging",
    "fig07_shap_summary": "shap_summary",
}

DOCS = [
    # (source stem, output stem, figure prefix)
    ("main3", "main", "fig"),
    ("supplemental2", "supplementary", "figS"),
]


def figure_order(tex):
    seen = []
    for m in re.finditer(r"\\includegraphics\[[^\]]*\]\{([^}]+)\}", tex):
        if m.group(1) not in seen:
            seen.append(m.group(1))
    return seen


def rename_map(files, prefix):
    out = {}
    for i, f in enumerate(files, 1):
        stem, _, ext = f.rpartition(".")
        if not stem:
            stem, ext = f, "png"
        desc = DESCRIPTIONS.get(stem, re.sub(r"[^a-z0-9]+", "_", stem.lower()).strip("_"))
        out[f] = f"{prefix}{i}_{desc}.{ext}"
    return out


def build_bbl(stem, workdir):
    """Compile a canonical source once to obtain its .bbl."""
    for name in (f"{stem}.tex", "references.bib"):
        shutil.copy(OVERLEAF / name, workdir / name)
    if FIGDIR.is_dir():
        shutil.copytree(FIGDIR, workdir / "figures", dirs_exist_ok=True)
    env = {**os.environ, "BIBINPUTS": f"{workdir}:"}
    for cmd in (["pdflatex", "-interaction=nonstopmode", f"{stem}.tex"],
                ["bibtex", stem]):
        subprocess.run(cmd, cwd=workdir, capture_output=True, env=env)
    bbl = workdir / f"{stem}.bbl"
    if not bbl.exists():
        sys.exit(f"ERROR: bibtex produced no .bbl for {stem}; cannot inline the bibliography.")
    return bbl.read_text(errors="ignore")


def transform(tex, bbl, renames, manuscript):
    # NOTE: every replacement below goes through a lambda. LaTeX is full of
    # backslashes and re.sub reads them as escapes in a replacement string --
    # "\documentclass" raises "bad escape \d", and a .bbl full of \bibitem
    # would be mangled silently.
    if manuscript:
        tex = re.sub(r"^\\documentclass\[[^\]]*\]\{elsarticle\}\s*\n",
                     lambda m: MANUSCRIPT_PREAMBLE, tex, count=1, flags=re.M)
    else:
        # supplement keeps its article class; add line numbers for review
        tex = re.sub(r"^(\\documentclass\[[^\]]*\]\{article\}\s*\n)",
                     lambda m: m.group(1) + "\n\\usepackage{lineno}\n\\linenumbers\n",
                     tex, count=1, flags=re.M)
    tex = re.sub(r"^\\graphicspath\{[^\n]*\}\s*\n", "", tex, count=1, flags=re.M)
    for old, new in renames.items():
        tex = tex.replace("{" + old + "}", "{" + new + "}")
    tex, n = re.subn(r"\\bibliographystyle\{[^}]*\}\s*\n\\bibliography\{[^}]*\}",
                     lambda m: bbl.strip(), tex, count=1)
    if n != 1:
        sys.exit("ERROR: could not find the \\bibliography block to splice the .bbl into.")
    return tex


def render(stem, out_stem, prefix):
    tex = (OVERLEAF / f"{stem}.tex").read_text(errors="ignore")
    renames = rename_map(figure_order(tex), prefix)
    with tempfile.TemporaryDirectory() as td:
        bbl = build_bbl(stem, Path(td))
    return transform(tex, bbl, renames, manuscript=(prefix == "fig")), renames


def doi_status():
    """Warn if the data-availability statement still has no archival DOI.

    The Zenodo concept DOI only exists once the first GitHub release is cut, so
    it cannot be written in advance. The intended order at submission time is:
    enable the Zenodo webhook, cut the release, paste the concept DOI into
    main3.tex and CITATION.cff, rebuild, then submit. This check exists so the
    package cannot be handed over with that step skipped.
    """
    tex = (OVERLEAF / "main3.tex").read_text(errors="ignore")
    avail = tex.split(r"\section*{Data and code availability}", 1)
    if len(avail) < 2:
        return
    block = avail[1][:1200]
    if re.search(r"10\.5281/zenodo\.\d+", block):
        m = re.search(r"10\.5281/zenodo\.\d+", block)
        print(f"\nArchival DOI present in the data-availability statement: {m.group(0)}")
    else:
        print("\n" + "-" * 72)
        print("NOTE: the data-availability statement carries no Zenodo DOI yet.")
        print("Before submitting: cut the GitHub release, wait for Zenodo to mint")
        print("the DOI, put the CONCEPT DOI (not the version DOI) into main3.tex")
        print("and CITATION.cff, then re-run this script.")
        print("-" * 72)


def emit(check_only=False):
    rendered = {out: render(src, out, pre) for src, out, pre in DOCS}

    if check_only:
        drift = False
        for out_stem, (text, _) in rendered.items():
            target = SUBMISSION / f"{out_stem}.tex"
            if not target.exists():
                print(f"DRIFT: {out_stem}.tex missing from the submission folder.")
                drift = True
                continue
            a = hashlib.sha256(text.encode()).hexdigest()
            b = hashlib.sha256(target.read_text(errors="ignore").encode()).hexdigest()
            if a != b:
                print(f"DRIFT: {out_stem}.tex differs from what the Overleaf source now generates.")
                drift = True
        if drift:
            print("       Rebuild with: python3 scripts/make_submission.py")
            return 1
        print("submission is in sync with the Overleaf sources")
        return 0

    SUBMISSION.mkdir(parents=True, exist_ok=True)
    total = 0
    for out_stem, (text, renames) in rendered.items():
        (SUBMISSION / f"{out_stem}.tex").write_text(text)
        print(f"\nWrote {out_stem}.tex  ({len(renames)} figures)")
        for old, new in renames.items():
            src = FIGDIR / old
            if not src.exists():
                sys.exit(f"ERROR: figure not found: {src}")
            shutil.copy(src, SUBMISSION / new)
            print(f"  {old:34s} -> {new}")
            total += 1
    print(f"\n{SUBMISSION}")
    print(f"{total} figures copied flat, no subdirectory.")
    rc = verify()
    rc = rc or build_repo_pdfs()
    doi_status()
    return rc


def build_repo_pdfs():
    """Compile the canonical two-column PDFs and refresh paper/ in the repo.

    The submission package is the single-column review format, which is the
    wrong artifact to browse or to link from the publications index. The
    two-column build is the readable one, so it is what the repository and the
    index carry. Built in scratch, never in the Overleaf folder.
    """
    print("\nBuilding the canonical two-column PDFs for the repository:")
    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        for name in ("main3.tex", "supplemental2.tex", "references.bib"):
            shutil.copy(OVERLEAF / name, work / name)
        if FIGDIR.is_dir():
            shutil.copytree(FIGDIR, work / "figures", dirs_exist_ok=True)
        env = {**os.environ, "BIBINPUTS": f"{work}:"}
        ok = True
        for stem, out in (("main3", "main"), ("supplemental2", "supplementary")):
            subprocess.run(["pdflatex", "-interaction=nonstopmode", f"{stem}.tex"],
                           cwd=work, capture_output=True, env=env)
            subprocess.run(["bibtex", stem], cwd=work, capture_output=True, env=env)
            for _ in range(2):
                subprocess.run(["pdflatex", "-interaction=nonstopmode", f"{stem}.tex"],
                               cwd=work, capture_output=True, env=env)
            log = (work / f"{stem}.log").read_text(errors="ignore").splitlines()
            errs = [l for l in log if l.startswith("!")]
            undef = [l for l in log if "undefined" in l.lower() and "warning" in l.lower()
                     and "There were" not in l]
            pages = next((re.search(r"\((\d+) pages", l).group(1) for l in log
                          if "Output written" in l and re.search(r"\((\d+) pages", l)), "?")
            status = "OK " if not (errs or undef) else "FAIL"
            print(f"  {status} {out+'.pdf':20s} {pages:>3s} pages  "
                  f"errors={len(errs)} undefined={len(undef)}")
            for l in (errs + undef)[:3]:
                print(f"        {l[:105]}")
            ok = ok and not (errs or undef)
            if (work / f"{stem}.pdf").exists():
                shutil.copy(work / f"{stem}.pdf", REPO_PAPER / f"{out}.pdf")
            shutil.copy(OVERLEAF / f"{stem}.tex", REPO_PAPER / f"{out}.tex")
        shutil.copy(OVERLEAF / "references.bib", REPO_PAPER / "references.bib")
    if not ok:
        print("\nTwo-column build is NOT clean.")
        return 1
    print(f"\npaper/ refreshed in the repository (sources + two-column PDFs).")
    return 0


def verify():
    """Compile the emitted package in isolation and insist it is clean.

    Copies only what the submission folder contains into an empty directory and
    runs pdflatex alone -- no bibtex, no .bib, no figures/ subdirectory. Any
    undefined reference fails the build. Cross-document references are the trap
    here: \\ref{} resolves happily while both documents share an Overleaf
    project and silently becomes "??" once they are compiled separately.
    """
    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        for f in SUBMISSION.iterdir():
            if f.is_file() and f.suffix.lower() in {".tex", ".png", ".jpg", ".pdf", ".eps"}:
                shutil.copy(f, work / f.name)
        # the cover letter rides along so it is verified and rendered too
        cover = SUBMISSION / "cover_letter.tex"
        stems = [d[1] for d in DOCS] + (["cover_letter"] if cover.exists() else [])
        ok = True
        print("\nVerifying in isolation (pdflatex only, no bibtex, no .bib):")
        for stem in stems:
            for _ in range(3):
                subprocess.run(["pdflatex", "-interaction=nonstopmode", f"{stem}.tex"],
                               cwd=work, capture_output=True)
            log = (work / f"{stem}.log").read_text(errors="ignore").splitlines()
            errs = [l for l in log if l.startswith("!")]
            undef = [l for l in log if "undefined" in l.lower() and "warning" in l.lower()
                     and "There were" not in l]
            missing = [l for l in log if "not found" in l]
            pages = ""
            for l in log:
                m = re.search(r"Output written .*\((\d+) pages", l)
                if m:
                    pages = m.group(1)
            status = "OK " if not (errs or undef or missing) else "FAIL"
            print(f"  {status} {stem+'.tex':20s} {pages:>3s} pages  "
                  f"errors={len(errs)} undefined={len(undef)} missing={len(missing)}")
            for l in (errs + undef + missing)[:4]:
                print(f"        {l[:105]}")
            ok = ok and not (errs or undef or missing)
            # ship the rendered PDF alongside the sources
            built = work / f"{stem}.pdf"
            if built.exists():
                shutil.copy(built, SUBMISSION / f"{stem}.pdf")
    if not ok:
        print("\nSubmission is NOT clean. Fix the source, then rebuild.")
        return 1
    print("\nSubmission compiles standalone with no undefined references.")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--check", action="store_true",
                   help="verify the submission matches the Overleaf sources; write nothing")
    sys.exit(emit(check_only=p.parse_args().check))
