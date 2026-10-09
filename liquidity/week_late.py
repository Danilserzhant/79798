"""Вторая половина недели: чт, пт, сб, вс (UTC). python week_late.py <dir_pkl_15m> <out_prefix> [SYM ...]
Пишет <out_prefix>_days.csv (каждый день: диапазон в ATR, пробой хая/лоя вчерашнего дня, инсайд) и <out_prefix>_weeks.csv (по неделе):
  чт и диапазон пн–ср (H3/L3): пробой, закрытие за краем (принятие) или внутри (возврат); от закрытия чт — пт–вс: закрытие недели выше/ниже,
  ±1 ATR, снят ли противоположный край H3/L3; то же для пт и диапазона пн–чт; выходные и хай/лой пятницы; выходные -> следующий понедельник."""
import sys, numpy as np, pandas as pd
SRC, OUT = sys.argv[1:3]
SYMS = sys.argv[3:] or ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'LTCUSDT', 'LINKUSDT']
INF = 10**12
def first(mask):
    j = np.flatnonzero(mask); return j[0] if len(j) else INF
def race(h, l, up, dn):
    a, b = first(h >= up), first(l <= dn); return np.nan if a == b == INF else float(a < b)
DR, WR = [], []
for s in SYMS:
    m = pd.read_pickle(f'{SRC}/{s}.pkl')[['o', 'h', 'l', 'c']]
    h, l, c = m.h.values, m.l.values, m.c.values
    g = pd.Series(np.arange(len(m)), index=m.index).groupby(m.index.normalize())
    D = pd.DataFrame({'i0': g.first().values, 'n': g.size().values}, index=g.first().index)
    D['o'] = m.o.values[D.i0.values]; D['c'] = c[(D.i0 + D.n - 1).values]
    D['h'] = [h[a:a + b].max() for a, b in zip(D.i0, D.n)]; D['l'] = [l[a:a + b].min() for a, b in zip(D.i0, D.n)]
    D['atr'] = (D.h - D.l).rolling(14).mean().shift(1); D = D[D.n >= 90]
    for j in range(1, len(D)):
        if D.index[j] - D.index[j - 1] != pd.Timedelta(days=1) or not D.atr.iloc[j] == D.atr.iloc[j]: continue
        cur, prv = D.iloc[j], D.iloc[j - 1]
        DR.append(dict(sym=s, t=D.index[j], dow=D.index[j].dayofweek, rng=(cur.h - cur.l) / cur.atr, up=cur.c > cur.o,
                       bh=cur.h > prv.h, bl=cur.l < prv.l, inside=cur.h <= prv.h and cur.l >= prv.l))
    W = {k: x for k, x in D.groupby(D.index - pd.to_timedelta(D.index.dayofweek, unit='D'))}; ks = sorted(W)
    for i in range(1, len(ks) - 1):
        w = W[ks[i]]
        if len(w) < 7: continue
        A = w.atr.iloc[0]
        if not A == A: continue
        O = w.o.iloc[0]; e_end = int(w.i0.iloc[-1] + w.n.iloc[-1]); WC = c[e_end - 1]
        r = dict(sym=s, t=ks[i], week_bull=WC > O)
        r['hi_day'] = int(np.argmax(w.h.values)); r['lo_day'] = int(np.argmin(w.l.values))
        for nd, pre in ((3, 'thu'), (4, 'fri')):                              # день nd против диапазона дней 0..nd-1
            H3, L3 = w.h.iloc[:nd].max(), w.l.iloc[:nd].min(); dd = w.iloc[nd]
            d_end = int(dd.i0 + dd.n); Cd = c[d_end - 1]; hh, ll = h[d_end:e_end], l[d_end:e_end]
            r[f'{pre}_bh'] = dd.h > H3; r[f'{pre}_bl'] = dd.l < L3
            r[f'{pre}_acc_up'] = Cd > H3; r[f'{pre}_acc_dn'] = Cd < L3
            r[f'{pre}_above_open'] = Cd > O; r[f'{pre}_up'] = dd.c > dd.o
            r[f'{pre}_pos'] = (Cd - L3) / (H3 - L3) if H3 > L3 else .5
            r[f'{pre}_rest_up'] = WC > Cd; r[f'{pre}_atr_up'] = race(hh, ll, Cd + A, Cd - A)
            r[f'{pre}_hit_H'] = bool((hh > max(H3, dd.h)).any()); r[f'{pre}_hit_L'] = bool((ll < min(L3, dd.l)).any())
            r[f'{pre}_hit_mid'] = bool(((hh >= (H3 + L3) / 2) & (ll <= (H3 + L3) / 2)).any() or ((ll <= (H3 + L3) / 2).any() if Cd > (H3 + L3) / 2 else (hh >= (H3 + L3) / 2).any()))
        # выходные против пятницы
        fri, sat, sun = w.iloc[4], w.iloc[5], w.iloc[6]
        we_h, we_l = max(sat.h, sun.h), min(sat.l, sun.l)
        r['we_bh'] = we_h > fri.h; r['we_bl'] = we_l < fri.l; r['we_up'] = sun.c > fri.c; r['we_rng'] = (we_h - we_l) / A
        r['we_close_in_fri'] = fri.l <= sun.c <= fri.h
        r['fri_rng'] = (fri.h - fri.l) / A
        # следующий понедельник
        nw = W.get(ks[i + 1])
        if nw is not None and len(nw) >= 1 and ks[i + 1] - ks[i] == pd.Timedelta(days=7):
            mon = nw.iloc[0]
            r['nmon_up'] = mon.c > mon.o; r['nmon_hit_fri_close'] = (mon.l <= fri.c <= mon.h) or (sun.c > fri.c and mon.l <= fri.c) or (sun.c < fri.c and mon.h >= fri.c)
            r['nmon_bh_we'] = mon.h > we_h; r['nmon_bl_we'] = mon.l < we_l
            r['nweek_up'] = nw.c.iloc[-1] > nw.o.iloc[0] if len(nw) == 7 else np.nan
        WR.append(r)
    print(s, len(WR), flush=True)
pd.DataFrame(DR).to_csv(f'{OUT}_days.csv', index=False); pd.DataFrame(WR).to_csv(f'{OUT}_weeks.csv', index=False)
