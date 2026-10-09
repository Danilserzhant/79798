"""Направление недели по понедельнику/вторнику: куда цена идёт ОТ момента решения (закрытие пн или вт, UTC) до конца недели.
python week_early.py <dir_pkl_15m> <out_csv> [SYM ...]
Цели от точки решения t: rest_up — закрытие недели выше цены в t; exp_up — после t первым пробит хай недели-до-t (а не лой);
atr_up — +1 дневной ATR раньше −1 ATR (до конца недели). Признаки — только то, что известно к t."""
import sys, numpy as np, pandas as pd
SRC, OUT = sys.argv[1:3]
SYMS = sys.argv[3:] or ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'LTCUSDT', 'LINKUSDT']
INF = 10**12
def first(mask, off=0):
    j = np.flatnonzero(mask); return off + j[0] if len(j) else INF
def race(h, l, up, dn):
    a, b = first(h >= up), first(l <= dn)
    return np.nan if a == b == INF else float(a < b)
rows = []
for s in SYMS:
    m = pd.read_pickle(f'{SRC}/{s}.pkl')[['o', 'h', 'l', 'c']]
    h, l, c, o = m.h.values, m.l.values, m.c.values, m.o.values
    day = m.index.normalize()
    dg = pd.Series(np.arange(len(m)), index=m.index).groupby(day)
    dst, dn = dg.first(), dg.size()
    D = pd.DataFrame({'i0': dst.values, 'n': dn.values}, index=dst.index)
    D['h'] = [h[a:a + b].max() for a, b in zip(D.i0, D.n)]; D['l'] = [l[a:a + b].min() for a, b in zip(D.i0, D.n)]
    D['o'] = o[D.i0.values]; D['c'] = c[(D.i0 + D.n - 1).values]
    D['atr'] = (D.h - D.l).rolling(14).mean().shift(1)
    D = D[D.n >= 90]
    wk = D.index - pd.to_timedelta(D.index.dayofweek, unit='D')
    weeks = {k: g for k, g in D.groupby(wk)}
    keys = sorted(weeks)
    for wi in range(1, len(keys)):
        w, pw = weeks[keys[wi]], weeks[keys[wi - 1]]
        if len(w) < 7 or len(pw) < 7 or keys[wi] - keys[wi - 1] != pd.Timedelta(days=7): continue
        A = w.atr.iloc[0]
        if not A == A: continue
        O = w.o.iloc[0]; PH, PL, PC, PO = pw.h.max(), pw.l.min(), pw.c.iloc[-1], pw.o.iloc[0]
        e_end = int(w.i0.iloc[-1] + w.n.iloc[-1])
        WC = c[e_end - 1]
        base = dict(sym=s, t=keys[wi], week_bull=WC > O)
        # прошлая неделя
        ppw = weeks.get(keys[wi - 1] - pd.Timedelta(days=7))
        if ppw is not None and len(ppw) == 7:
            pph, ppl = ppw.h.max(), ppw.l.min()
            base['prev_state'] = ('принятие выше' if PC > pph else 'принятие ниже' if PC < ppl else 'обе сняты' if (PH > pph and PL < ppl)
                                  else 'отказ сверху' if PH > pph else 'отказ снизу' if PL < ppl else 'внутри')
        base['prev_bull'] = PC > PO
        base['open_pos'] = (O - PL) / (PH - PL) if PH > PL else .5
        wkd = pw.iloc[5:7]                                               # сб–вс прошлой недели
        base['weekend_up'] = wkd.c.iloc[-1] > pw.c.iloc[4]
        base['weekend_small'] = (wkd.h.max() - wkd.l.min()) < .6 * A
        for dpt, nm in ((0, 'mon'), (1, 'tue')):
            sofar = w.iloc[:dpt + 1]
            t_end = int(sofar.i0.iloc[-1] + sofar.n.iloc[-1])
            Ct = c[t_end - 1]; Hs, Ls = sofar.h.max(), sofar.l.min()
            r = dict(base, dp=nm)
            hh, ll = h[t_end:e_end], l[t_end:e_end]
            r['rest_up'] = WC > Ct
            r['exp_up'] = race(hh, ll, Hs + 1e-12, Ls - 1e-12)
            r['atr_up'] = race(hh, ll, Ct + A, Ct - A)
            mon = w.iloc[0]
            r['mon_up'] = mon.c > O; r['mon_range'] = (mon.h - mon.l) / A
            r['mon_took_PH'] = mon.h > PH; r['mon_took_PL'] = mon.l < PL
            r['mon_close_pos'] = (mon.c - mon.l) / (mon.h - mon.l) if mon.h > mon.l else .5
            if dpt == 1:
                tue = w.iloc[1]
                r['tue_up'] = tue.c > tue.o
                r['tue_broke_mh'] = tue.h > mon.h; r['tue_broke_ml'] = tue.l < mon.l
                r['tue_close_above_mh'] = tue.c > mon.h; r['tue_close_below_ml'] = tue.c < mon.l
                r['above_open'] = tue.c > O
                r['took_PH'] = Hs > PH; r['took_PL'] = Ls < PL
            else:
                r['above_open'] = mon.c > O; r['took_PH'] = mon.h > PH; r['took_PL'] = mon.l < PL
            rows.append(r)
    print(s, len(rows), flush=True)
pd.DataFrame(rows).to_csv(OUT, index=False)
