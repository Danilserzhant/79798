"""Сводка setup1r.py: матожидание в R (с комиссией) против контроля. python3.13 setup1r_sum.py <real_csv> <syn_csv1,...> <out_txt>"""
import sys, numpy as np, pandas as pd
RP, SP, OUT = sys.argv[1], sys.argv[2].split(','), sys.argv[3]
R = pd.read_csv(RP, parse_dates=['t']); SS = [pd.read_csv(p, parse_dates=['t']) for p in SP]
MAJ = ['BTCUSDT', 'ETHUSDT']; half = R.t.sort_values().iloc[len(R) // 2]
FL = {'ср–вс': lambda d: d[d.dowi >= 2], 'ср–вс + узкая': lambda d: d[(d.dowi >= 2) & (d.narrow == 1)],
      'ср–вс + тренд': lambda d: d[(d.dowi >= 2) & (d.trend == 1)], 'ср–вс + BTC импульс': lambda d: d[(d.dowi >= 2) & (d.btc_mom == 1)],
      'ср–вс + узкая + тренд': lambda d: d[(d.dowi >= 2) & (d.narrow == 1) & (d.trend == 1)],
      'ср–вс + узкая + BTC': lambda d: d[(d.dowi >= 2) & (d.narrow == 1) & (d.btc_mom == 1)],
      'все дни': lambda d: d}
def stat(x):
    v = x.R.values; n = len(v)
    if n < 60: return None
    yrs = x.groupby(x.t.dt.year).R.mean(); 
    return dict(n=n, m=v.mean(), se=v.std() / np.sqrt(n), win=(v > 0).mean(), h1=x[x.t < half].R.mean(), h2=x[x.t >= half].R.mean(),
                mj=x[x.sym.isin(MAJ)].R.mean(), al=x[~x.sym.isin(MAJ)].R.mean(), yp=(yrs > 0).sum(), yn=len(yrs), cost=x.cost.mean())
rows = []
for (mode, hz, f, k, be), x in R.groupby(['mode', 'hz', 'f', 'k', 'be']):
    cs = [s[(s['mode'] == mode) & (s.hz == hz) & (s.f == f) & (s.k == k) & (s.be == be)] for s in SS]
    for fn, ff in FL.items():
        st = stat(ff(x))
        if st is None: continue
        q = np.mean([ff(c).R.mean() for c in cs])
        rows.append(dict(mode=mode, hz=hz, f=f, k=k, be=be, filt=fn, ctrl=q, **st))
T = pd.DataFrame(rows); T['z'] = (T.m - T.ctrl) / T.se
T['robust'] = (T.h1 > 0) & (T.h2 > 0) & (T.mj > 0) & (T.al > 0) & (T.yp >= T.yn - 1) & (T.z >= 2.5)
def fmt(r):
    kk = 'время' if r.k == 0 else f'{r.k}R'
    return (f'{r["mode"]:6s} hz{r.hz} стоп {r.f:.2f}D цель {kk:5s} BE{r.be} | {r.filt:22s} n={r.n:5d} | E={r.m:+.2f}R ±{2*r.se:.2f} (контроль {r.ctrl:+.2f}, z {r.z:+.1f}) '
            f'| побед {100*r.win:3.0f}% | половины {r.h1:+.2f}/{r.h2:+.2f} | BTC+ETH {r.mj:+.2f} альты {r.al:+.2f} | лет в плюсе {r.yp}/{r.yn} | комиссия {r.cost:.2f}R {"★" if r.robust else ""}')
L = ['ТОП-40 по матожиданию среди устойчивых (★: z≥2.5 к контролю, обе половины, BTC+ETH и альты в плюсе, все годы кроме ≤1 в плюсе):']
L += [fmt(r) for _, r in T[T.robust].sort_values('m', ascending=False).head(40).iterrows()]
L.append('\nТОП-25 по матожиданию вообще (включая неустойчивые):')
L += [fmt(r) for _, r in T.sort_values('m', ascending=False).head(25).iterrows()]
L.append('\nСетка для фильтра «ср–вс + узкая»:')
L += [fmt(r) for _, r in T[T.filt == 'ср–вс + узкая'].sort_values(['mode', 'hz', 'f', 'k', 'be']).iterrows()]
L.append('\nСетка для фильтра «ср–вс»:')
L += [fmt(r) for _, r in T[T.filt == 'ср–вс'].sort_values(['mode', 'hz', 'f', 'k', 'be']).iterrows()]
txt = '\n'.join(L); print(txt); open(OUT, 'w').write(txt + '\n')
T.to_csv(OUT.replace('.txt', '.csv'), index=False)
