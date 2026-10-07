"""Таблица подтверждений с бутстрап-интервалом. python conf_ci.py trades.csv out.csv [side]"""
import sys, numpy as np, pandas as pd
T = pd.read_csv(sys.argv[1]); T = T[~T.open]
if len(sys.argv) > 3: T = T[T.side == sys.argv[3]]
T['yr'] = pd.to_datetime(T.t_entry).dt.year
rng = np.random.default_rng(0); out = []
for (k, c, tp), g in T.groupby(['kind', 'conf', 'tp']):
    x = g.net_R.values
    bs = [rng.choice(x, len(x)).mean() for _ in range(2000)]
    w = x[x > 0].sum() / max(1e-9, -x[x < 0].sum())
    out.append(dict(kind=k, conf=c, tp=tp, n=len(x), win=(g.res == 'tp').mean() * 100, rr=g.rr.median(), exp=x.mean(),
                    lo5=np.percentile(bs, 5), hi95=np.percentile(bs, 95), trim=np.sort(x)[:int(len(x) * .95)].mean(), pf=w,
                    expA=g[g.yr <= 2023].net_R.mean(), expB=g[g.yr > 2023].net_R.mean(),
                    yrs=f"{(g.groupby('yr').net_R.sum() > 0).sum()}/{g.yr.nunique()}", syms=f"{(g.groupby('sym').net_R.mean() > 0).sum()}/{g.sym.nunique()}"))
pd.DataFrame(out).sort_values('exp', ascending=False).to_csv(sys.argv[2], index=False)
