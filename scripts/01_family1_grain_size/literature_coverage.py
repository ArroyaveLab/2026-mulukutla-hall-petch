#!/usr/bin/env python3
"""
Literature coverage of the four measured properties (SI Table S13)
==================================================================
How many published FCC alloys report chemistry, grain size, yield strength and
hardness together? This script answers that from the largest curated
compilation of multi-principal element alloy properties, and is the provenance
record for the counts quoted in the Introduction.

Source
------
Borg et al., "Expanded dataset of mechanical properties and observed phases of
multi-principal element alloys", Sci. Data 7, 430 (2020). Distributed by
Citrine Informatics under Apache-2.0. Vendored at
data/derived/citrine_mpea_dataset.csv so this runs offline.

Why this compilation
--------------------
It is the only large MPEA property compilation that records grain size at all.
Gorsse et al. (2018, 370 alloys) and the Chemical Data Collections database
(2023) carry hardness and yield strength but no grain-size column. COD'HEM
(Comput. Mater. Sci. 248, 113588, 2025) is larger still -- >4000 compositions
from >400 papers -- and records neither grain size nor hardness; its
per-composition schema is uid, composition, doi, phases, density, tensile
strength at 23 and 1000 C, atomic composition, ductility.

Caveat on the per-study rows
----------------------------
Borg's extraction is not always complete for a given paper, so the
largest-single-study figures below are lower bounds on what that study
reported. The aggregate rows do not depend on per-study completeness.

Outputs
-------
  results/literature_coverage.csv
"""
import warnings
warnings.filterwarnings('ignore')

import os
import pandas as pd

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _config import RESULTS_DIR, DATA_DIR

URL = ('https://raw.githubusercontent.com/CitrineInformatics/'
       'MPEA_dataset/master/MPEA_dataset.csv')
LOCAL = f'{DATA_DIR}/citrine_mpea_dataset.csv'

GRAIN = 'PROPERTY: grain size ($\\mu$m)'
HV    = 'PROPERTY: HV'
YS    = 'PROPERTY: YS (MPa)'
STRUC = 'PROPERTY: BCC/FCC/other'
DOI   = 'REFERENCE: doi'

# This work, recomputed by tests/test_canonical_values.py from data/derived.
OURS_CONDITIONS   = 94
OURS_COMPOSITIONS = 82
OURS_ALL_FOUR_REC = 93   # chemistry + grain size + YS + HV on the same specimen
OURS_ALL_FOUR_CMP = 81

df = pd.read_csv(LOCAL) if os.path.exists(LOCAL) else pd.read_csv(URL)
fcc = df[STRUC].astype(str).str.upper().str.strip().eq('FCC')

def summarise(mask, label):
    sub = df[mask]
    by_study = sub.groupby(DOI)['FORMULA'].nunique().sort_values(ascending=False)
    return {
        'set': label,
        'records': len(sub),
        'compositions': sub['FORMULA'].nunique(),
        'source_studies': sub[DOI].nunique(),
        'largest_single_study_compositions': int(by_study.iloc[0]) if len(by_study) else 0,
        'largest_single_study_doi': by_study.index[0] if len(by_study) else '',
    }

rows = [
    summarise(fcc & df[GRAIN].notna() & df[YS].notna(),
              'FCC, grain size + yield strength'),
    summarise(fcc & df[GRAIN].notna() & df[YS].notna() & df[HV].notna(),
              'FCC, grain size + yield strength + hardness'),
    {'set': 'This work (single study, one protocol)',
     'records': OURS_ALL_FOUR_REC,
     'compositions': OURS_ALL_FOUR_CMP,
     'source_studies': 1,
     'largest_single_study_compositions': OURS_ALL_FOUR_CMP,
     'largest_single_study_doi': 'this_work'},
]

out = pd.DataFrame(rows)
out.to_csv(f'{RESULTS_DIR}/literature_coverage.csv', index=False)
print(f"Wrote {RESULTS_DIR}/literature_coverage.csv\n")
print(out.to_string(index=False))

lit4 = rows[1]
lit2 = rows[0]
print(f"\nNumbers quoted in the Introduction:")
print(f"  Borg compilation total          : {len(df)} records, {df['FORMULA'].nunique()} formulas")
print(f"  FCC with grain size + YS        : {lit2['compositions']} compositions "
      f"from {lit2['source_studies']} studies")
print(f"  FCC with all three measured     : {lit4['compositions']} compositions "
      f"from {lit4['source_studies']} studies")
print(f"  this work                       : {OURS_ALL_FOUR_CMP} compositions from 1 study")
print(f"\n  ratio, all three properties     : "
      f"{OURS_ALL_FOUR_CMP / lit4['compositions']:.0f}x the entire compilation")
print(f"  ratio, grain size + YS          : "
      f"{OURS_ALL_FOUR_CMP / lit2['compositions']:.0f}x the entire compilation")

assert lit4['compositions'] < OURS_ALL_FOUR_CMP, \
    "Introduction claims this is the largest such set; the compilation now says otherwise"
