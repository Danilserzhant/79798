"""Лонг от снятия последнего H4 фрактального лоя с целью в низ зоны H4 FVG.
Окно: от первого снятия лоя матери, 4 недели, пока зона не тронута. Каждый раз, когда 15m лой пробивает последний подтверждённый
H4 фрактальный лой (2+2), ищем бычий шифт M15: закрытие выше последнего M15 фрактального хая перед локальным лоем (локальный лой
пересчитывается). Поиск — 24 ч после снятия. Вход по закрытию, стоп под локальным лоем −0,1%, цель — низ зоны. Издержки 0,1%.
Позиции не пересекаются. python h4low_long.py <dir_pkl> <events.csv> <out.csv> [X]  (X — только события с выносом >= X·R)"""
import sys, numpy as np, pandas as pd
SRC, EV, OUT = sys.argv[1:4]
X = float(sys.argv[4]) if len(sys.argv) > 4 else None
E = pd.read_csv(EV); E = E[~E.open]
cache = {}; rows = []
def zone_at(b4, L, ext_t, now):
    B = b4.loc[:now - pd.Timedelta('4h')]; xb = B.index.searchsorted(ext_t, side='right') - 1
    hv, lv, cv = B.h.values, B.l.values, B.c.values
    for k in range(min(xb, len(B) - 1), max(2, xb - 84), -1):
        if hv[k] < lv[k - 2] and lv[k - 2] >= L and not (cv[k + 1:xb + 1] > lv[k - 2]).any():
            return lv[k - 2], hv[k]
    return None
for e in E.itertuples():
    if (e.sym, e.side) not in cache:
        raw = pd.read_pickle(f'{SRC}/{e.sym}.pkl')
        m = raw if e.side == 'low' else pd.DataFrame({'h': -raw.l, 'l': -raw.h, 'c': -raw.c}, index=raw.index)
        b4 = m.resample('4h').agg(h=('h', 'max'), l=('l', 'min'), c=('c', 'last')).dropna()
        hv, lv = b4.h.values, b4.l.values
        frac = [(b4.index[k] + pd.Timedelta('12h'), lv[k]) for k in range(2, len(b4) - 2)
                if lv[k] < lv[k - 1] and lv[k] < lv[k - 2] and lv[k] <= lv[k + 1] and lv[k] <= lv[k + 2]]
        cache[(e.sym, e.side)] = (m, b4, pd.DataFrame(frac, columns=['conf', 'low']).set_index('conf'))
    m, b4, FR = cache[(e.sym, e.side)]
    sg = 1 if e.side == 'low' else -1
    L, H, R = sg * e.L, sg * e.H, e.R; t0 = pd.Timestamp(e.t0)
    if X is not None:
        a = m.loc[t0:t0 + pd.Timedelta(weeks=1)]
        if not ((a.l.min() <= L - X * R)): continue
    seg = m.loc[t0 - pd.Timedelta('1D'):t0 + pd.Timedelta(weeks=4)]
    T, h, l, c = seg.index, seg.h.values, seg.l.values, seg.c.values
    i = int(np.searchsorted(T, t0)); busy_until = -1
    while i < len(T):
        # последний подтверждённый H4 фрактальный лой на момент i
        fr = FR.loc[:T[i]]
        if not len(fr): i += 1; continue
        flow = fr.low.iloc[-1]
        if not (l[i] < flow) or i <= busy_until: i += 1; continue
        ext_t = m.loc[t0:T[i]].l.idxmin()
        z = zone_at(b4, L, ext_t, T[i])
        if z is None or m.loc[t0:T[i]].h.max() >= z[1]: i += 1; continue    # нет зоны или уже тронута
        top, bot = z
        # бычий шифт M15 в течение 24 ч
        lo, lo_i = l[i], i; sig = None
        for j in range(i + 1, min(len(T), i + 96)):
            if l[j] < lo: lo, lo_i = l[j], j
            if j <= lo_i: continue
            fh = None
            for k in range(lo_i - 1, max(i - 200, 2), -1):
                if k + 2 >= j: continue
                if h[k] > h[k - 1] and h[k] > h[k - 2] and h[k] >= h[k + 1] and h[k] >= h[k + 2]:
                    if (c[k + 1:lo_i + 1] > h[k]).any(): continue
                    fh = h[k]; break
            if fh is not None and c[j] > fh: sig = j; break
        if sig is None: i += 1; continue
        entry, stop = c[sig], lo - 0.001 * abs(lo); risk = entry - stop
        if entry >= bot or risk <= 0: i = sig + 1; continue
        f = m.loc[T[sig] + pd.Timedelta('15min'):T[sig] + pd.Timedelta(weeks=2)]
        def first(mk):
            q = np.nonzero(mk)[0]; return q[0] if len(q) else 10**9
        iS, iT = first(f.l.values <= stop), first(f.h.values >= bot)
        rr = (bot - entry) / risk; cost = 0.001 * abs(entry) / risk
        win = iT < iS
        rows.append(dict(sym=e.sym, side=e.side, ib_week=e.ib_week, t=str(T[sig]), depth=(L - m.loc[t0:T[sig]].l.min()) / R,
                         entry=sg * entry, stop=sg * stop, target=sg * bot, rr=rr, win=win, net=(rr if win else -1) - cost,
                         hours=(f.index[min(iT, iS, len(f) - 1)] - T[sig]).total_seconds() / 3600))
        end = min(iT, iS)
        busy_until = sig + (end if end < 10**9 else len(f)) + 1
        i = busy_until + 1
D = pd.DataFrame(rows); D.to_csv(OUT, index=False)
def show(nm, g):
    if not len(g): print(f'{nm:28s} 0'); return
    print(f'{nm:28s} сделок {len(g):3d} | цель (низ зоны) раньше стопа {g.win.mean()*100:3.0f}% | RR мед {g.rr.median():.1f} | ср. {g.net.mean():+.2f}R  сумма {g.net.sum():+.1f}R  без лучшей {np.sort(g.net.values)[:-1].mean() if len(g)>1 else float("nan"):+.2f}R')
for nm, g in (('ETH снятие лоя', D[(D.sym == 'ETHUSDT') & (D.side == 'low')]), ('ETH обе', D[D.sym == 'ETHUSDT']),
              ('9 монет снятие лоя', D[D.side == 'low']), ('9 монет обе', D)):
    show(nm, g); show('  …RR >= 1.5', g[g.rr >= 1.5]); show('  …вынос >= 0.4', g[g.depth >= 0.4])
