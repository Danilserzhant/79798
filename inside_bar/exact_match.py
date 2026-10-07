"""Точные аналоги: первое снятие лоя матери после инсайда, вынос >= X·R, хай матери не тронут,
медвежий H4 FVG (последний до лоя манипуляции, не перекрыт) пересекает лой матери (низ <= L <= верх) или выше него (низ > L),
и зона не тронута с момента формирования лоя. Исходы — 4 недели от момента совпадения.
python exact_match.py <dir_pkl> <events.csv> <out.csv> [X=0.40]"""
import sys, numpy as np, pandas as pd
SRC, EV, OUT = sys.argv[1:4]
X = float(sys.argv[4]) if len(sys.argv) > 4 else 0.40
E = pd.read_csv(EV); E = E[~E.open]
cache = {}; rows = []
for e in E.itertuples():
    if (e.sym, e.side) not in cache:
        raw = pd.read_pickle(f'{SRC}/{e.sym}.pkl')
        m = raw if e.side == 'low' else pd.DataFrame({'h': -raw.l, 'l': -raw.h, 'c': -raw.c}, index=raw.index)
        cache[(e.sym, e.side)] = (m, m.resample('4h').agg(h=('h', 'max'), l=('l', 'min'), c=('c', 'last')).dropna(),
                                  m.resample('W-MON', label='left', closed='left').agg(c=('c', 'last')))
    m, b4, wk = cache[(e.sym, e.side)]
    sg = 1 if e.side == 'low' else -1
    L, H, R = sg * e.L, sg * e.H, e.R; t0 = pd.Timestamp(e.t0)
    a = m.loc[t0:t0 + pd.Timedelta(weeks=1)]
    ok = np.nonzero((np.minimum.accumulate(a.l.values) <= L - X * R) & (np.maximum.accumulate(a.h.values) < H))[0]
    if not len(ok): continue
    ts = a.index[ok[0]]; pre = m.loc[t0:ts]; ext_t = pre.l.idxmin()
    B = b4.loc[:ts - pd.Timedelta('4h')]; xb = B.index.searchsorted(ext_t, side='right') - 1
    hv, lv, cv = B.h.values, B.l.values, B.c.values; zone = None
    for k in range(min(xb, len(B) - 1), max(2, xb - 84), -1):
        if hv[k] < lv[k - 2] and lv[k - 2] >= L and not (cv[k + 1:xb + 1] > lv[k - 2]).any():
            zone = (lv[k - 2], hv[k], B.index[k]); break
    if zone is None: continue
    top, bot, zt = zone
    if m.loc[zt + pd.Timedelta('4h'):ts].h.max() >= bot: continue          # зона уже тронута после формирования
    kind = 'пересекает лой матери' if bot <= L else 'выше лоя матери'
    f = m.loc[ts + pd.Timedelta('15min'):ts + pd.Timedelta(weeks=4)]
    ext = pre.l.min()
    def first(mk):
        i = np.nonzero(mk)[0]; return f.index[i[0]] if len(i) else pd.Timestamp.max
    tz, tn, tE, tHm, tM = first(f.h.values >= bot), first(f.l.values < ext), first(f.l.values <= L - R), first(f.h.values >= H), first(f.h.values >= L + R / 2)
    f4 = b4.loc[ts:ts + pd.Timedelta(weeks=4)]; up = f4.index[f4.c.values > top]; tU = up[0] + pd.Timedelta('4h') if len(up) else pd.Timestamp.max
    we = ts.normalize() - pd.Timedelta(days=ts.dayofweek)
    wkc = wk.c.loc[we] if we in wk.index else np.nan
    newlow_depth = (ext - f.l.min()) / R if len(f) else np.nan
    sgp = lambda v: round(float(sg * v), 4)
    rows.append(dict(sym=e.sym, side=e.side, mother=str((pd.Timestamp(e.ib_week) - pd.Timedelta(weeks=1)).date()), t=str(ts),
                     mother_low=sgp(L), mother_high=sgp(H), zone_bot=sgp(bot), zone_top=sgp(top), kind=kind, depth=round((L - ext) / R, 2),
                     zone_first=tz < tn, zone_4w=tz < pd.Timestamp.max, h4_above=tU < pd.Timestamp.max, h4_before_nl=tU < tn,
                     newlow=tn < pd.Timestamp.max, newlow_depth=round(newlow_depth, 2) if newlow_depth > 0 else 0.0,
                     E1=tE < pd.Timestamp.max, mid=tM < pd.Timestamp.max, H=tHm < pd.Timestamp.max, H_before_E1=tHm < tE,
                     wk_close_above=bool(wkc > L) if wkc == wkc else None))
D = pd.DataFrame(rows); D.to_csv(OUT, index=False)
P = lambda x: f'{x.astype(float).mean()*100:3.0f}%'
for nm, g in (('ETH, снятие лоя', D[(D.sym == 'ETHUSDT') & (D.side == 'low')]), ('9 монет, снятие лоя', D[D.side == 'low']), ('9 монет, обе стороны', D)):
    print(f'\n== {nm}')
    for kd in ('пересекает лой матери', 'выше лоя матери', None):
        g2 = g if kd is None else g[g.kind == kd]
        if not len(g2): continue
        print(f'  {kd or "все":24s} n={len(g2):3d} | зона раньше нового лоя {P(g2.zone_first)}  зона за 4 нед {P(g2.zone_4w)}  H4 выше зоны {P(g2.h4_above)} (раньше нового лоя {P(g2.h4_before_nl)}) | '
              f'новый лой {P(g2.newlow)} (глубина мед {g2[g2.newlow].newlow_depth.median():.2f}R) | до L-1R {P(g2.E1)} | середина {P(g2.mid)}  хай матери {P(g2.H)} (раньше L-1R {P(g2.H_before_E1)}) | неделя закрылась выше лоя {P(g2.wk_close_above.dropna())}')
