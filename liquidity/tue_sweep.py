"""Пн внутри прошлой недели, вт снимает лой прошлой недели (PWL). Что дальше — от закрытия вт (UTC).
Зеркально (side=bear в данных с минусом): вт снимает хай прошлой недели. python tue_sweep.py <dir_pkl_15m> <out_csv> [SYM ...]
Поля: reclaim — вт закрылся обратно выше PWL; above_open — вт закрылся выше открытия недели; rest_up — закрытие недели выше закрытия вт;
atr_up — +1 дн. ATR раньше −1 ATR; low_holds — лой вт не обновлён до конца недели; opp_taken — до конца недели снят хай прошлой недели;
mid_taken — дошли до середины прошлой недели; depth — насколько вт ушёл ниже PWL (в ATR)."""
import sys, numpy as np, pandas as pd
SRC, OUT = sys.argv[1:3]
SYMS = sys.argv[3:] or ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'LTCUSDT', 'LINKUSDT']
INF = 10**12
def first(mask):
    j = np.flatnonzero(mask); return j[0] if len(j) else INF
rows = []
for s in SYMS:
    raw = pd.read_pickle(f'{SRC}/{s}.pkl')[['o', 'h', 'l', 'c']]
    for side in ('bull', 'bear'):
        m = raw if side == 'bull' else pd.DataFrame({'o': -raw.o, 'h': -raw.l, 'l': -raw.h, 'c': -raw.c}, index=raw.index)
        h, l, c, o = m.h.values, m.l.values, m.c.values, m.o.values
        dg = pd.Series(np.arange(len(m)), index=m.index).groupby(m.index.normalize())
        D = pd.DataFrame({'i0': dg.first().values, 'n': dg.size().values}, index=dg.first().index)
        D['h'] = [h[a:a + b].max() for a, b in zip(D.i0, D.n)]; D['l'] = [l[a:a + b].min() for a, b in zip(D.i0, D.n)]
        D['o'] = o[D.i0.values]; D['c'] = c[(D.i0 + D.n - 1).values]; D['atr'] = (D.h - D.l).rolling(14).mean().shift(1)
        D = D[D.n >= 90]
        W = {k: g for k, g in D.groupby(D.index - pd.to_timedelta(D.index.dayofweek, unit='D'))}
        ks = sorted(W)
        for i in range(1, len(ks)):
            w, pw = W[ks[i]], W[ks[i - 1]]
            if len(w) < 7 or len(pw) < 7 or ks[i] - ks[i - 1] != pd.Timedelta(days=7): continue
            PH, PL = pw.h.max(), pw.l.min(); O = w.o.iloc[0]; A = w.atr.iloc[0]
            mon, tue = w.iloc[0], w.iloc[1]
            if not (A == A) or mon.h > PH or mon.l < PL: continue          # пн внутри прошлой недели
            if not (tue.l < PL and tue.h <= PH): continue                    # вт снял только лой
            t_end = int(tue.i0 + tue.n); e_end = int(w.i0.iloc[-1] + w.n.iloc[-1])
            Ct = c[t_end - 1]; hh, ll = h[t_end:e_end], l[t_end:e_end]
            a, b = first(hh >= Ct + A), first(ll <= Ct - A)
            rows.append(dict(sym=s, side=side, t=ks[i], reclaim=Ct > PL, above_open=Ct > O, depth=(PL - tue.l) / A,
                             rest_up=c[e_end - 1] > Ct, atr_up=np.nan if a == b == INF else float(a < b),
                             low_holds=bool(ll.min() > tue.l) if len(ll) else np.nan, opp_taken=bool((hh > PH).any()),
                             mid_taken=bool((hh >= (PH + PL) / 2).any()), week_bull=c[e_end - 1] > O))
    print(s, len(rows), flush=True)
pd.DataFrame(rows).to_csv(OUT, index=False)
