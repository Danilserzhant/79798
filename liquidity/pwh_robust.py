"""Устойчивость кандидатов PWH/PWL. python3.13 pwh_robust.py <real_ev.csv> <syn_ev1,...> <out_txt>"""
import sys, numpy as np, pandas as pd
B = {True: 1.0, False: 0.0, 'True': 1.0, 'False': 0.0}
def load(f):
    e = pd.read_csv(f, parse_dates=['t'])
    for c in ('ts', 'narrow', 'day_back', 'above_sma'):
        e[c] = e[c].map(B) if e[c].dtype == object else e[c].astype(float)
    e['brk_R'] = np.where(e.rev_mid == 0, 1.0, np.where(e.rev_mid == 1, -1.0, np.nan)) - e.brk_cost
    e['yr'] = e.t.dt.year; return e
R = load(sys.argv[1]); Ss = [load(f) for f in sys.argv[2].split(',')]; OUT = sys.argv[3]
MAJ = ['BTCUSDT', 'ETHUSDT']; half = R.t.sort_values().iloc[len(R) // 2]
early = lambda d: d.dow.isin(['пн', 'вт'])
C = [('TS→середина: PWH снят в пн–вт', 'ts_R_mid', lambda d: d[(d.side == 'PWH') & early(d) & (d.ts == 1)]),
     ('TS→середина: PWL снят в пн–вт', 'ts_R_mid', lambda d: d[(d.side == 'PWL') & early(d) & (d.ts == 1)]),
     ('TS→середина: любой уровень в пн–вт', 'ts_R_mid', lambda d: d[early(d) & (d.ts == 1)]),
     ('ПРОБОЙ: PWH снят в ср–вс', 'brk_R', lambda d: d[(d.side == 'PWH') & ~early(d)]),
     ('ПРОБОЙ: PWL снят в ср–вс', 'brk_R', lambda d: d[(d.side == 'PWL') & ~early(d)]),
     ('ПРОБОЙ: любой уровень в ср–вс', 'brk_R', lambda d: d[~early(d)]),
     ('ПРОБОЙ: прошлая неделя узкая', 'brk_R', lambda d: d[d.narrow == 1]),
     ('ПРОБОЙ: ср–вс и прошлая узкая', 'brk_R', lambda d: d[~early(d) & (d.narrow == 1)])]
L = []
for nm, col, f in C:
    x = f(R).dropna(subset=[col]); cs = [f(s).dropna(subset=[col]) for s in Ss]
    q = np.mean([c[col].mean() for c in cs]); se = x[col].std() / np.sqrt(len(x))
    yrs = x.groupby('yr')[col].agg(['size', 'mean'])
    pos_years = int((yrs['mean'] > 0).sum())
    L.append(f'{nm:40s} n={len(x):4d} | итог {x[col].mean():+.3f}R ±{2*se:.3f} (контроль {q:+.3f}) | половины {x[x.t<half][col].mean():+.2f}/{x[x.t>=half][col].mean():+.2f} | '
             f'BTC+ETH {x[x.sym.isin(MAJ)][col].mean():+.2f} (n={int(x.sym.isin(MAJ).sum())}), альты {x[~x.sym.isin(MAJ)][col].mean():+.2f} | лет в плюсе {pos_years}/{len(yrs)} | '
             + ' '.join(f'{y}:{m:+.2f}' for y, m in yrs['mean'].items()))
txt = '\n'.join(L); print(txt); open(OUT, 'w').write(txt + '\n')
