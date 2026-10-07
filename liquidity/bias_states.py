"""BIAS по закрытию периода относительно диапазона прошлого периода (D, W, M) и что делает следующий период.
Состояния: принятие выше (close > PH) / отказ сверху (снят PH, close внутри) / внутри / обе сняты, close внутри /
отказ снизу / принятие ниже. Следующий период относительно диапазона текущего: снят хай / лой / какой первым / закрытие выше.
Плюс совмещение W+M: состояние последнего закрытого месяца и последней закрытой недели -> следующая неделя.
python bias_states.py <dir_pkl> <out_csv> [SYM ...]"""
import sys, numpy as np, pandas as pd
SRC, OUT = sys.argv[1:3]
SYMS = sys.argv[3:] or ['ETHUSDT', 'BTCUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'LTCUSDT', 'LINKUSDT']
INF = 10**9
def first(mask):
    j = np.flatnonzero(mask); return j[0] if len(j) else INF
def bars(m, P):
    idx = m.index
    k = (idx.normalize() - pd.to_timedelta(idx.dayofweek, unit='D')) if P == 'W' else idx.to_period('M').to_timestamp() if P == 'M' else idx.normalize()
    g = pd.DataFrame({'o': m.o.values, 'h': m.h.values, 'l': m.l.values, 'c': m.c.values, 'p': np.arange(len(m))}, index=idx).groupby(k)
    b = g.agg(o=('o', 'first'), h=('h', 'max'), l=('l', 'min'), c=('c', 'last'), i0=('p', 'first'), n=('p', 'size'))
    return b[b.n >= (0.9 * b.n.median() if P != 'M' else 2600)]
def state(h, l, c, PH, PL):
    if c > PH: return 'принятие выше'
    if c < PL: return 'принятие ниже'
    if h > PH and l < PL: return 'обе сняты'
    if h > PH: return 'отказ сверху'
    if l < PL: return 'отказ снизу'
    return 'внутри'
rows = []
for s in SYMS:
    m = pd.read_pickle(f'{SRC}/{s}.pkl')[['o', 'h', 'l', 'c']]
    hh, ll = m.h.values, m.l.values
    B = {P: bars(m, P) for P in ('D', 'W', 'M')}
    for P, b in B.items():
        H, L, C, I0, N = b.h.values, b.l.values, b.c.values, b.i0.values.astype(int), b.n.values.astype(int)
        mst = None
        if P == 'W':                                  # состояние последнего закрытого месяца на начало недели
            bm = B['M']; ms = [None] + [state(bm.h.iloc[j], bm.l.iloc[j], bm.c.iloc[j], bm.h.iloc[j - 1], bm.l.iloc[j - 1]) for j in range(1, len(bm))]
            mend = (bm.i0 + bm.n).values
        for j in range(1, len(b) - 1):
            if b.index[j + 1] - b.index[j] > pd.Timedelta(days=40 if P == 'M' else 8 if P == 'W' else 2): continue
            st = state(H[j], L[j], C[j], H[j - 1], L[j - 1])
            s0, e0 = I0[j + 1], I0[j + 1] + N[j + 1]
            iH, iL = first(hh[s0:e0] > H[j]), first(ll[s0:e0] < L[j])
            r = dict(sym=s, P=P, t=b.index[j], state=st, nH=iH < INF, nL=iL < INF,
                     firstH=np.nan if iH == INF and iL == INF else float(iH < iL), up=C[j + 1] > C[j],
                     upper=C[j + 1] > (H[j] + L[j]) / 2)
            if P == 'W':
                k = np.searchsorted(mend, s0, side='right') - 1
                r['mstate'] = ms[k] if k >= 1 else None
            rows.append(r)
pd.DataFrame(rows).to_csv(OUT, index=False)
