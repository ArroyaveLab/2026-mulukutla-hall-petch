#!/usr/bin/env python3
"""
Literature k_HP comparison table (SI Table S12)
===============================================
Published Hall-Petch coefficients for concentrated FCC alloys, juxtaposed with
the Family 3 M3 shared slope. This script is the provenance record for SI
Table S12: the rows below are the table, and the table is generated from them.

Inclusion rule
--------------
Every row is fitted to a *measured* yield strength. Coefficients obtained by
converting hardness to strength are excluded, because that conversion depends
on the work-hardening response rather than on a fixed factor -- the present
dataset gives C_eff = HV/sigma_y = 5.13 +/- 1.36 across 93 paired records, not
the Tabor value of 3. This rule also excludes survey values for pure metals
that pool indentation and tensile data in a single fit (Cordero et al. 2016
divide Vickers and nanoindentation hardness by a Tabor factor of 3 and fit
those points together with tension and compression data), which is why no pure
metal appears here.

Comparison is meaningful only at matched test temperature: Otto et al. report
k_HP for CoCrFeMnNi falling from 538 at 77 K to 127 at 1073 K. All rows below
are room temperature.

Provenance
----------
Every value was read from the source's own results table, not from a secondary
compilation, except WuGaoBei2016, which is itself a compilation and is flagged
as such. An earlier version of this file attributed 538 to Yoshida 2017 for
CoCrFeMnNi; Yoshida et al. 2017 study CoCrNi and report 265, while 538 is Otto
et al.'s 77 K value. Do not reintroduce that row.

Outputs
-------
  results/literature_kHP_table.csv
  analysis_plots/88_literature_kHP.png
"""
import warnings
warnings.filterwarnings('ignore')

import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # scripts/ (for _config)
from _config import RESULTS_DIR, PLOTS_DIR

M3_K_HP = 766  # Family 3 M3 shared slope, MPa*um^(1/2)

# (alloy, k_HP, d_min_um, d_max_um, test_mode, citation_key, provenance)
LITERATURE = [
    ('CoCrNi',                          265,  0.29, 111.0, 'tension',     'Yoshida2017',         'primary'),
    ('CoCrFeNi',                        276,  0.55,  32.2, 'tension',     'Yoshida2019acta',     'primary'),
    ('CoCrFeMnNi',                      494,  4.4,  155.0, 'tension',     'Otto2013',            'primary'),
    ('CoCrFeNi',                        506, 25.0,  110.0, 'tension',     'LiKHP2024',           'primary'),
    ('CoCrFeNi',                        684, 23.0,  150.0, 'tension',     'Jagetia2021',         'primary'),
    ('This work, Family 3 M3',      M3_K_HP, 14.7,  212.0, 'tension',     'this_work',           'fitted'),
    ('CoCrFeNi',                        855,  2.5,   59.0, 'tension',     'WuGaoBei2016',        'compiled'),
    ('CrFeNi',                          966, 10.0,  327.0, 'compression', 'SchneiderCrFeNi2021', 'primary'),
    ('Al0.3CoCrFeNi',                  1014, 29.0,  199.0, 'tension',     'Jagetia2021',         'primary'),
    ('Co0.95Cr0.8Fe0.25Ni1.8Mo0.475',  1100, 25.0,  110.0, 'tension',     'LiKHP2024',           'primary'),
    ('Al0.3CoFeNi',                    1244, 38.0,  179.0, 'tension',     'Jagetia2021',         'primary'),
]

COLS = ['Alloy', 'k_HP_MPa_um_half', 'd_min_um', 'd_max_um',
        'test_mode', 'Citation', 'Provenance']
df = pd.DataFrame(LITERATURE, columns=COLS).sort_values('k_HP_MPa_um_half')

# The inclusion rule is an invariant, not a comment.
assert not df['test_mode'].str.contains('hardness').any(), \
    "hardness-derived coefficients must not enter this table"

df.to_csv(f'{RESULTS_DIR}/literature_kHP_table.csv', index=False)
print(f"Wrote {RESULTS_DIR}/literature_kHP_table.csv")
print(df.to_string(index=False))

lit = df[df['Citation'] != 'this_work']
print(f"\nReported range, concentrated FCC alloys: "
      f"{lit['k_HP_MPa_um_half'].min()}-{lit['k_HP_MPa_um_half'].max()} MPa*um^(1/2)")
print(f"M3 = {M3_K_HP}, which lies inside that range.")

fig, ax = plt.subplots(figsize=(9, 5))
labels = [f"{a}  [{c}]" if c != 'this_work' else a
          for a, c in zip(df['Alloy'], df['Citation'])]
colors = ['#dd8452' if c == 'this_work' else '#4c72b0' for c in df['Citation']]
ax.barh(labels[::-1], df['k_HP_MPa_um_half'][::-1],
        color=colors[::-1], edgecolor='black')
ax.axvline(M3_K_HP, color='#dd8452', linestyle='--',
           label=f'this work (M3) = {M3_K_HP}')
ax.set_xlabel(r'$k_{\mathrm{HP}}$  (MPa $\cdot\ \mu$m$^{1/2}$)')
ax.set_title('Hall-Petch coefficient, concentrated FCC alloys\n'
             '(measured yield strength only; room temperature)')
ax.legend()
plt.tight_layout()
plt.savefig(f'{PLOTS_DIR}/88_literature_kHP.png', dpi=150)
plt.close()
print(f"Wrote {PLOTS_DIR}/88_literature_kHP.png")
