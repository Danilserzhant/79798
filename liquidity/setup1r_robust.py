"""Устойчивость лучших вариантов setup1r: хвосты, годы, стороны, монеты, просадка. python3.13 setup1r_robust.py <real_csv> <syn_csv1,...> <out_txt>"""
import sys, numpy as np, pandas as pd
RP, SP, OUT = sys.argv[1], sys.argv[2].split(','), sys.argv[3]
R = pd.read_csv(RP, parse_dates=['t']); SS = [pd.read_csv(p, parse_dates=['t']) for p in SP]
CFG = [('stop', 1, 1.0, 0, 0), ('stop', 2, 1.0, 0, 0), ('stop', 1, 0.5, 0, 0), ('stop', 2, 0.5, 0, 0), ('stop', 1, 0.25, 0, 0),
       ('stop', 1, 1.0, 5, 0), ('stop', 1, 0.5, 5, 0), ('stop', 1, 1.0, 3, 0), ('retest', 2, 1.0, 0, 0)]
FL = {'ср–вс': lambda d: d[d.dowi >= 2], 'ср–вс + узкая': lambda d: d[(d.dowi >= 2) & (d.narrow == 1)],
      'ср–вс + BTC импульс': lambda d: d[(d.dowi >= 2) & (d.btc_mom == 1)], 'ср–вс + узкая + BTC': lambda d: d[(d.dowi >= 2) & (d.narrow == 1) & (d.btc_mom == 1)]}
sel = lambda d, c: d[(d['mode'] == c[0]) & (d.hz == c[1]) & (d.f == c[2]) & (d.k == c[3]) & (d.be == c[4])]
L = []
for c in CFG:
    x0 = sel(R, c); cs0 = [sel(s, c) for s in SS]
    for fn, ff in FL.items():
        x = ff(x0).sort_values('t'); cs = [ff(s) for s in cs0]; v = x.R.values
        if len(v) < 60: continue
        srt = np.sort(v)[::-1]; top10 = srt[:10].sum() / v.sum() if v.sum() > 0 else np.nan
        cap = lambda a, m: np.minimum(a, m).mean()
        eq = np.cumsum(v); dd = (np.maximum.accumulate(eq) - eq).max()
        yrs = x.groupby(x.t.dt.year).R.mean(); sides = x.groupby('side').R.mean(); syms = x.groupby('sym').R.mean()
        pf = v[v > 0].sum() / -v[v < 0].sum()
        kk = 'время' if c[3] == 0 else f'{c[3]}R'
        L.append(f'{c[0]} hz{c[1]} стоп {c[2]:.2f}D цель {kk} | {fn} | n={len(v)} ({len(v)/6.8:.0f}/год) | E={v.mean():+.2f}R (контроль {np.mean([s.R.mean() for s in cs]):+.2f}) | медиана {np.median(v):+.2f}R '
                 f'| PF {pf:.2f} | E с потолком 10R {cap(v,10):+.2f} (контр. {np.mean([cap(s.R.values,10) for s in cs]):+.2f}), 5R {cap(v,5):+.2f} (контр. {np.mean([cap(s.R.values,5) for s in cs]):+.2f}) '
                 f'| без топ-1% {np.sort(v)[:-max(1,len(v)//100)].mean():+.2f} | топ-10 сделок = {100*top10:.0f}% прибыли | макс. сделка {srt[0]:+.1f}R | макс. просадка {dd:.1f}R')
        L.append('     годы: ' + ' '.join(f'{y}:{m:+.2f}' for y, m in yrs.items()) + ' | ' + ' '.join(f'{k}:{m:+.2f}' for k, m in sides.items())
                 + ' | монеты в плюсе ' + f'{(syms > 0).sum()}/{len(syms)}: ' + ' '.join(f'{k[:-4]}:{m:+.2f}' for k, m in syms.items()))
    L.append('')
txt = '\n'.join(L); print(txt); open(OUT, 'w').write(txt + '\n')
