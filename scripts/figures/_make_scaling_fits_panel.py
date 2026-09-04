#!/usr/bin/env python3
"""Single-panel versions of the Family 1 scaling-law figure.

The main paper carries the YS panel and the SI carries the HV panel, so the
two documents no longer share a figure. Both are built from the exact fit
logic, palette, and typography of make_restyled_figures.py, so they are
identical in construction to the original two-panel figure.

Usage:  TARGET=YS|HV  SCALING_OUT=<dir>  python3 _make_scaling_fits_panel.py
"""
import os
import sys

import numpy as np
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import _figstyle as S
import make_restyled_figures as M

S.apply()

TARGET = os.environ.get('TARGET', 'YS').upper()
OUT = os.environ.get('SCALING_OUT', '/tmp')

FRAME = {'YS': M.YS, 'HV': M.HV}[TARGET]
YLAB = {'YS': 'Yield strength (MPa)', 'HV': 'Vickers hardness'}[TARGET]

tab = M._fit_laws(FRAME, TARGET)

fig, ax = plt.subplots(figsize=(S.W_COL, 3.30))
M.scatter_by_batch(ax, FRAME.GrainSize.values, FRAME[TARGET].values, FRAME, s=20)

grid = np.linspace(FRAME.GrainSize.min() * 0.92, FRAME.GrainSize.max() * 1.05, 300)
law_fn = dict((l, f) for l, f in M.LAWS)
law_handles = []
for name, ls in zip(list(tab.law[:3]), ['-', '--', ':']):
    fn = law_fn.get(name)
    if fn is None:
        continue
    Xf = np.column_stack([np.ones(len(FRAME))] + fn(FRAME.GrainSize.values))
    beta, *_ = np.linalg.lstsq(Xf, FRAME[TARGET].values, rcond=None)
    Xg = np.column_stack([np.ones(len(grid))] + fn(grid))
    ln, = ax.plot(grid, Xg @ beta, ls, color='#111111', lw=2.6, zorder=5,
                  label=name)
    law_handles.append(ln)

ax.set_xlabel(r'mean grain size $d$  ($\mu$m)')
ax.set_ylabel(YLAB)
ax.margins(x=0.02)

law_leg = ax.legend(handles=law_handles, loc='upper right',
                    fontsize=S.FS_ANNOT - 0.7, handlelength=1.6,
                    borderpad=0.3, labelspacing=0.25)
ax.add_artist(law_leg)          # a second ax.legend() would otherwise replace it

batch_handles = [plt.Line2D([], [], color=c, marker=m, ls='', ms=4.5,
                            mec='white', mew=0.5, label=b)
                 for b, (c, m) in S.BATCH.items()]
ax.legend(handles=batch_handles, ncol=6, loc='upper center',
          bbox_to_anchor=(0.5, -0.16), frameon=False,
          fontsize=S.FS_ANNOT - 0.7, handletextpad=0.3, columnspacing=0.7)

fig.tight_layout()
name = f'fig_scaling_fits_{TARGET.lower()}.png'
fig.savefig(os.path.join(OUT, name), dpi=400, bbox_inches='tight',
            facecolor='white')
print('wrote', os.path.join(OUT, name))
print(tab[['law', 'LOO_R2', 'dBIC']].head(4).to_string(index=False))
