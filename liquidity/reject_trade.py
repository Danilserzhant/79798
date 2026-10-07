"""Сделка от контекста без триггера: после отказа (снят край прошлого периода, закрытие внутри) —
вход на открытии следующего периода, стоп за экстремумом свечи отказа, цель — противоположный край свечи отказа.
Медвежий отказ — зеркально. Держим до исхода (макс. 10 периодов). Комиссия 0.1%. python reject_trade.py <dir> <out_csv>"""
import sys, numpy as np, pandas as pd
SRC, OUT = sys.argv[1:3]
SYMS = ['ETHUSDT', 'BTCUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'LTCUSDT', 'LINKUSDT']
rows = []
for s in SYMS:
    raw = pd.read_pickle(f'{SRC}/{s}.pkl')[['o', 'h', 'l', 'c']]
    for mirror in (False, True):
        m = raw if not mirror else pd.DataFrame({'o': -raw.o, 'h': -raw.l, 'l': -raw.h, 'c': -raw.c}, index=raw.index)
        h, l, c = m.h.values, m.l.values, m.c.values
        for P in ('D', 'W'):
            k = (m.index.normalize() - pd.to_timedelta(m.index.dayofweek, unit='D')) if P == 'W' else m.index.normalize()
            g = pd.DataFrame({'h': h, 'l': l, 'c': c, 'p': np.arange(len(m))}, index=m.index).groupby(k)
            b = g.agg(h=('h', 'max'), l=('l', 'min'), c=('c', 'last'), i0=('p', 'first'), n=('p', 'size'))
            per = int(b.n.median())
            for j in range(1, len(b) - 1):
                H, L, C, PH, PL = b.h.iloc[j], b.l.iloc[j], b.c.iloc[j], b.h.iloc[j - 1], b.l.iloc[j - 1]
                if not (L < PL and C >= PL and H <= PH): continue          # отказ снизу (без снятия хая)
                t0 = int(b.i0.iloc[j + 1]); e = c[t0 - 1]; risk = e - L
                if risk <= 0 or H <= e: continue
                rr = (H - e) / risk
                fh, fl = h[t0:t0 + 10 * per], l[t0:t0 + 10 * per]
                iu = np.flatnonzero(fh >= H); idn = np.flatnonzero(fl <= L)
                iu = iu[0] if len(iu) else 10**9; idn = idn[0] if len(idn) else 10**9
                res = rr if iu < idn else -1.0 if idn < 10**9 else (c[min(len(c) - 1, t0 + 10 * per - 1)] - e) / risk
                rows.append(dict(sym=s, P=P, mirror=mirror, t=b.index[j + 1], rr=rr, win=iu < idn, R=res - 0.001 * abs(e) / risk,
                                 close_pos=(C - L) / (H - L), depth=(PL - L) / (PH - PL)))
pd.DataFrame(rows).to_csv(OUT, index=False)
