"""Лонг от ПЕРВОГО снятия H4 фрактального лоя, сформированного в первом движении, снявшем лой матери.
Фрактал: первый подтверждённый H4 фрактальный лой (2+2) после снятия лоя матери, ниже лоя матери и являющийся минимумом движения.
Событие: первое снятие этого лоя (15m лой ниже), пока зона H4 FVG не тронута. Затем бычий шифт M15 в течение 24 ч
(закрытие выше последнего M15 фрактального хая перед локальным лоем; лой пересчитывается). Стоп под локальным лоем −0,1%,
цель — низ зоны. Издержки 0,1%. Одна сделка на событие. python first_h4low_long.py <dir_pkl> <events.csv> <out.csv>"""
import sys, numpy as np, pandas as pd
SRC, EV, OUT = sys.argv[1:4]
E = pd.read_csv(EV); E = E[~E.open]
cache = {}; rows = []
for e in E.itertuples():
    if (e.sym, e.side) not in cache:
        raw = pd.read_pickle(f'{SRC}/{e.sym}.pkl')
        m = raw if e.side == 'low' else pd.DataFrame({'h': -raw.l, 'l': -raw.h, 'c': -raw.c}, index=raw.index)
        cache[(e.sym, e.side)] = (m, m.resample('4h').agg(h=('h', 'max'), l=('l', 'min'), c=('c', 'last')).dropna())
    m, b4 = cache[(e.sym, e.side)]
    sg = 1 if e.side == 'low' else -1
    L, H, R = sg * e.L, sg * e.H, e.R; t0 = pd.Timestamp(e.t0)
    F = b4.loc[t0.floor('4h'):t0 + pd.Timedelta(weeks=2)]; fh4, fl4, fi4 = F.h.values, F.l.values, F.index
    k_found = None
    for k in range(2, len(F) - 2):
        if fl4[k] < L and fl4[k] < fl4[k - 1] and fl4[k] < fl4[k - 2] and fl4[k] <= fl4[k + 1] and fl4[k] <= fl4[k + 2]:
            if fl4[k] > m.loc[t0:fi4[k] + pd.Timedelta('4h') - pd.Timedelta('15min')].l.min() + 1e-12: continue
            k_found = k; break
    r = dict(sym=e.sym, side=e.side, ib_week=e.ib_week, stage='нет фрактала')
    if k_found is None: rows.append(r); continue
    k = k_found; flow = fl4[k]; tconf = fi4[k + 2] + pd.Timedelta('4h')
    if m.loc[fi4[k]:tconf - pd.Timedelta('15min')].l.min() < flow: rows.append(r); continue
    # зона на момент фрактала
    B = b4.loc[:fi4[k]]; xb = len(B) - 1; hv, lv, cv = B.h.values, B.l.values, B.c.values; zone = None
    for kk in range(xb, max(2, xb - 84), -1):
        if hv[kk] < lv[kk - 2] and lv[kk - 2] >= L and not (cv[kk + 1:xb + 1] > lv[kk - 2]).any():
            zone = (lv[kk - 2], hv[kk]); break
    if zone is None: r['stage'] = 'нет зоны'; rows.append(r); continue
    top, bot = zone
    r.update(depth_frac=(L - flow) / R, stage='ждём снятия')
    seg = m.loc[tconf:tconf + pd.Timedelta(weeks=4)]
    T, h, l, c = seg.index, seg.h.values, seg.l.values, seg.c.values
    iz = np.nonzero(h >= bot)[0]; isw = np.nonzero(l < flow)[0]
    iz = iz[0] if len(iz) else 10**9; isw = isw[0] if len(isw) else 10**9
    r['zone_before_sweep'] = iz < isw
    if isw == 10**9 or iz < isw:
        r['stage'] = 'зона раньше снятия' if iz < isw else 'снятия не было'; rows.append(r); continue
    i = isw; r['stage'] = 'снятие'; r['sweep_t'] = str(T[i])
    seg2 = m.loc[T[i] - pd.Timedelta('2D'):T[i] + pd.Timedelta(weeks=2)]
    T2, h2, l2, c2 = seg2.index, seg2.h.values, seg2.l.values, seg2.c.values
    i2 = int(np.searchsorted(T2, T[i])); lo, lo_i = l2[i2], i2; sig = None
    for j in range(i2 + 1, min(len(T2), i2 + 96)):
        if h2[j] >= bot: break
        if l2[j] < lo: lo, lo_i = l2[j], j
        if j <= lo_i: continue
        fh = None
        for q in range(lo_i - 1, max(i2 - 200, 2), -1):
            if q + 2 >= j: continue
            if h2[q] > h2[q - 1] and h2[q] > h2[q - 2] and h2[q] >= h2[q + 1] and h2[q] >= h2[q + 2]:
                if (c2[q + 1:lo_i + 1] > h2[q]).any(): continue
                fh = h2[q]; break
        if fh is not None and c2[j] > fh: sig = j; break
    if sig is None: r['stage'] = 'снятие без шифта'; rows.append(r); continue
    entry, stop = c2[sig], lo - 0.001 * abs(lo); risk = entry - stop
    if entry >= bot or risk <= 0: r['stage'] = 'вход выше цели'; rows.append(r); continue
    f = seg2.iloc[sig + 1:]
    def first(mk):
        q = np.nonzero(mk)[0]; return q[0] if len(q) else 10**9
    iS, iT = first(f.l.values <= stop), first(f.h.values >= bot)
    rr = (bot - entry) / risk; cost = 0.001 * abs(entry) / risk; win = iT < iS
    tH = first(f.h.values >= top)
    r.update(stage='сделка', t=str(T2[sig]), entry=sg * entry, stop=sg * stop, target=sg * bot, rr=rr, win=win,
             net=(rr if win else -1) - cost, sweep_depth=(flow - lo) / R, full_zone_before_stop=tH < iS,
             depth_now=(L - lo) / R)
    rows.append(r)
D = pd.DataFrame(rows); D.to_csv(OUT, index=False)
for c_ in ('win', 'full_zone_before_stop'):
    D[c_] = D[c_].map(lambda v: bool(v) if v == v and v is not None else False)
for nm, g in (('ETH снятие лоя', D[(D.sym == 'ETHUSDT') & (D.side == 'low')]), ('ETH обе', D[D.sym == 'ETHUSDT']),
              ('9 монет снятие лоя', D[D.side == 'low']), ('9 монет обе', D)):
    vc = g.stage.value_counts().to_dict(); t = g[g.stage == 'сделка']
    print(f'== {nm}: событий {len(g)} | {vc}')
    if len(t):
        for lab, tt in (('все', t), ('RR >= 1.5', t[t.rr >= 1.5]), ('вынос фрактала >= 0.3', t[t.depth_frac >= 0.3]), ('вынос фрактала < 0.3', t[t.depth_frac < 0.3])):
            if len(tt): print(f'   {lab:22s} сделок {len(tt):3d} | цель раньше стопа {tt.win.mean()*100:3.0f}% | RR мед {tt.rr.median():.1f} | ср. {tt.net.mean():+.2f}R сумма {tt.net.sum():+.1f}R без лучшей {np.sort(tt.net.values)[:-1].mean() if len(tt)>1 else float("nan"):+.2f}R | вся зона раньше стопа {tt.full_zone_before_stop.mean()*100:3.0f}%')
