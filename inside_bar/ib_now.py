"""Вероятности из ТЕКУЩЕГО состояния: снят лой IB, снят лой матери, вынос под L >= X·R, хай IB не тронут.
Считаем от момента t*, когда все условия впервые выполнились (без заглядывания вперёд).
python ib_now.py <dir_pkl> <events.csv> <ext_R> <out.json>"""
import sys, json, numpy as np, pandas as pd
SRC, EV, X, OUT = sys.argv[1], sys.argv[2], float(sys.argv[3]), sys.argv[4]
E = pd.read_csv(EV); E = E[~E.open]
HOLD = pd.Timedelta(weeks=4)
rows = []
cache = {}
for _, e in E.iterrows():
    if e.sym not in cache: cache[e.sym] = pd.read_pickle(f'{SRC}/{e.sym}.pkl')
    raw = cache[e.sym]
    sg = 1 if e.side == 'low' else -1
    m = raw if sg == 1 else pd.DataFrame({'h': -raw.l, 'l': -raw.h, 'c': -raw.c}, index=raw.index)
    L, H, R = sg * e.L, sg * e.H, e.R
    t0 = pd.Timestamp(e.t0)
    ibw = pd.Timestamp(e.ib_week)
    mo_l = m.loc[ibw - pd.Timedelta(weeks=1):ibw - pd.Timedelta('15min')].l.min()
    a = m.loc[t0:t0 + pd.Timedelta(weeks=1)]
    runmin = np.minimum.accumulate(a.l.values); runmax = np.maximum.accumulate(a.h.values)
    ok = (runmin <= L - X * R) & (runmin < mo_l) & (runmax < H)
    idx = np.nonzero(ok)[0]
    if not len(idx): continue
    ts = a.index[idx[0]]
    lvl_now = L - X * R
    f = m.loc[ts + pd.Timedelta('15min'):ts + HOLD]
    def first(mask):
        i = np.nonzero(mask)[0]; return f.index[i[0]] if len(i) else pd.Timestamp.max
    tH, tM, tL, tE1, tE15 = first(f.h.values >= H), first(f.h.values >= L + R / 2), first(f.h.values >= L), first(f.l.values <= L - R), first(f.l.values <= L - 1.5 * R)
    wk_end = ts.normalize() - pd.Timedelta(days=ts.dayofweek) + pd.Timedelta(weeks=1)
    wkc = m.c.loc[:wk_end - pd.Timedelta('15min')].iloc[-1]
    rows.append(dict(sym=e.sym, side=e.side, ib_week=e.ib_week, ts=str(ts), dow=ts.dayofweek,
                     back_L=tL < pd.Timestamp.max, mid_first=tM < tE1, H_first=tH < tE1, E1_first=tE1 < tH,
                     reach_E1=tE1 < pd.Timestamp.max, reach_E15=tE15 < pd.Timestamp.max, reach_H=tH < pd.Timestamp.max,
                     L_before_E1=tL < tE1, wk_close_inside=bool(wkc > L), wk_close_below_mother=bool(wkc < mo_l)))
D = pd.DataFrame(rows)
def st(g):
    return {k: round(float(g[k].mean() * 100), 1) for k in ['back_L', 'L_before_E1', 'mid_first', 'H_first', 'E1_first', 'reach_H', 'reach_E1', 'reach_E15', 'wk_close_inside', 'wk_close_below_mother']} | {'n': int(len(g))}
res = {'all': st(D), 'ETH': st(D[D.sym == 'ETHUSDT']), 'low_side': st(D[D.side == 'low']),
       'midweek': st(D[D.dow.between(1, 3)]), 'midweek_low': st(D[D.dow.between(1, 3) & (D.side == 'low')])}
json.dump(res, open(OUT, 'w'), ensure_ascii=False, indent=1)
D.to_csv(OUT.replace('.json', '.csv'), index=False)
print(json.dumps(res, ensure_ascii=False, indent=1))
