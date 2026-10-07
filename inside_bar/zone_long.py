"""Лонг из зоны H4 FVG: вход A — лимит на низ зоны при первом касании, B — середина зоны, C — закрытие H4 выше верха зоны.
Стоп — под лоем манипуляции на момент входа (−0,1%), цели — хай матери / середина матери. Если стоп и цель в одной 15m — стоп.
Издержки 0,1%. Отсчёт от «текущего состояния» (вынос >= X·R) или от первого снятия. Окно поиска входа 4 недели, удержание до 4 недель.
python zone_long.py <dir_pkl> <events.csv> <out.csv> [X]"""
import sys, numpy as np, pandas as pd
SRC, EV, OUT = sys.argv[1:4]
X = float(sys.argv[4]) if len(sys.argv) > 4 else None
E = pd.read_csv(EV); E = E[~E.open]
NEVER = 10**9; cache = {}; rows = []
for e in E.itertuples():
    if (e.sym, e.side) not in cache:
        raw = pd.read_pickle(f'{SRC}/{e.sym}.pkl')
        m = raw if e.side == 'low' else pd.DataFrame({'h': -raw.l, 'l': -raw.h, 'c': -raw.c}, index=raw.index)
        cache[(e.sym, e.side)] = (m, m.resample('4h').agg(h=('h', 'max'), l=('l', 'min'), c=('c', 'last')).dropna())
    m, b4 = cache[(e.sym, e.side)]
    sg = 1 if e.side == 'low' else -1
    L, H, R = sg * e.L, sg * e.H, e.R
    t0 = pd.Timestamp(e.t0); ts = t0
    if X is not None:
        a = m.loc[t0:t0 + pd.Timedelta(weeks=1)]
        ok = np.nonzero((np.minimum.accumulate(a.l.values) <= L - X * R) & (np.maximum.accumulate(a.h.values) < H))[0]
        if not len(ok): continue
        ts = a.index[ok[0]]
    pre = m.loc[t0:ts]; ext_t = pre.l.idxmin()
    B = b4.loc[:ts - pd.Timedelta('4h')]; xb = B.index.searchsorted(ext_t, side='right') - 1
    hv, lv, cv = B.h.values, B.l.values, B.c.values; zone = None
    for k in range(min(xb, len(B) - 1), max(2, xb - 84), -1):
        if hv[k] < lv[k - 2] and lv[k - 2] >= L and not (cv[k + 1:xb + 1] > lv[k - 2]).any():
            zone = (lv[k - 2], hv[k]); break
    if zone is None: continue
    top, bot = zone
    f = m.loc[ts + pd.Timedelta('15min'):ts + pd.Timedelta(weeks=8)]
    fh, fl, fc, fi = f.h.values, f.l.values, f.c.values, f.index
    win_end = fi.searchsorted(ts + pd.Timedelta(weeks=4))
    res = dict(sym=e.sym, side=e.side, ib_week=e.ib_week, yr=ts.year)
    def trade(name, j, entry):
        if j >= win_end: res[name] = None; return
        low_since = m.loc[t0:fi[j]].l.min()
        stop = low_since - 0.001 * abs(low_since)
        risk = entry - stop
        if risk <= 0: res[name] = None; return
        g = slice(j + 1, min(len(f), j + 1 + 2688))
        def first(mk):
            k = np.nonzero(mk)[0]; return k[0] if len(k) else NEVER
        iS = first(fl[g] <= stop); iH = first(fh[g] >= H); iM = first(fh[g] >= L + R / 2)
        cost = 0.001 * abs(entry) / risk
        rrH, rrM = (H - entry) / risk, (L + R / 2 - entry) / risk
        res[name] = dict(winH=iH < iS, winM=iM < iS, rrH=rrH, rrM=rrM,
                         netH=(rrH if iH < iS else -1) - cost, netM=(rrM if iM < iS else -1) - cost)
    # A: лимит на низ зоны
    jA = next((j for j in range(win_end) if fh[j] >= bot), NEVER)
    trade('A', jA, bot)
    jB = next((j for j in range(win_end) if fh[j] >= (bot + top) / 2), NEVER)
    trade('B', jB, (bot + top) / 2)
    # C: закрытие H4 выше верха зоны
    f4 = b4.loc[ts:ts + pd.Timedelta(weeks=4)]; up = f4.index[f4.c.values > top]
    if len(up):
        tC = up[0] + pd.Timedelta('4h'); jC = fi.searchsorted(tC); trade('C', jC, f4.loc[up[0]].c) if jC < len(f) else None
    else: res['C'] = None
    rows.append(res)
D = pd.DataFrame(rows); D.to_pickle(OUT)
def show(nm, g):
    out = [f'{nm:20s} случаев {len(g):3d}']
    for k, lab in (('A', 'низ зоны'), ('B', 'середина'), ('C', 'H4 выше')):
        t = [x for x in g[k] if isinstance(x, dict)] if k in g else []
        if not t: out.append(f'{lab}: —'); continue
        T = pd.DataFrame(t)
        out.append(f'{lab}: вход {len(t)/len(g)*100:3.0f}% | хай раньше стопа {T.winH.mean()*100:3.0f}% RR {T.rrH.median():.1f} ср. {T.netH.mean():+.2f}R | середина раньше стопа {T.winM.mean()*100:3.0f}% ср. {T.netM.mean():+.2f}R')
    print('\n   '.join(out))
for nm, g in (('ETH снятие лоя', D[(D.sym == 'ETHUSDT') & (D.side == 'low')]), ('ETH обе', D[D.sym == 'ETHUSDT']),
              ('9 монет снятие лоя', D[D.side == 'low']), ('9 монет обе', D)):
    show(nm, g)
