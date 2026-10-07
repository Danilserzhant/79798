"""Как часто цена возвращается в зону H4 FVG (последний медвежий H4 FVG с верхом >= лоя матери перед лоем манипуляции).
Отсчёт: от первого снятия лоя матери или от «текущего состояния» (вынос >= X·R, хай матери не тронут). Горизонт 4 недели.
python zone_retrace.py <dir_pkl> <events.csv> <out.csv> [X]"""
import sys, numpy as np, pandas as pd
SRC, EV, OUT = sys.argv[1:4]
X = float(sys.argv[4]) if len(sys.argv) > 4 else None
E = pd.read_csv(EV); E = E[~E.open]
NEVER = pd.Timestamp.max; cache = {}; rows = []
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
    pre = m.loc[t0:ts]; ext_t = pre.l.idxmin(); ext = pre.l.min()
    # зона на момент ts: только закрытые H4
    B = b4.loc[:ts - pd.Timedelta('4h')]
    xb = B.index.searchsorted(ext_t, side='right') - 1
    zone = None
    hv, lv, cv = B.h.values, B.l.values, B.c.values
    for k in range(min(xb, len(B) - 1), max(2, xb - 84), -1):
        if hv[k] < lv[k - 2] and lv[k - 2] >= L and not (cv[k + 1:xb + 1] > lv[k - 2]).any():
            zone = (lv[k - 2], hv[k]); break
    if zone is None:
        rows.append(dict(sym=e.sym, side=e.side, has_zone=False)); continue
    top, bot = zone
    f = m.loc[ts + pd.Timedelta('15min'):ts + pd.Timedelta(weeks=4)]
    def first(mk):
        i = np.nonzero(mk)[0]; return f.index[i[0]] if len(i) else NEVER
    t_bot, t_mid, t_top, t_E1, t_new = first(f.h.values >= bot), first(f.h.values >= (bot + top) / 2), first(f.h.values >= top), first(f.l.values <= L - R), first(f.l.values < ext)
    f4 = b4.loc[ts:ts + pd.Timedelta(weeks=4)]; up = f4.index[f4.c.values > top]
    t_h4 = up[0] + pd.Timedelta('4h') if len(up) else NEVER
    pen = (f.h.loc[:t_E1].max() - bot) / (top - bot) if t_bot < NEVER else np.nan   # насколько глубоко зашла в зону до L-1R
    rows.append(dict(sym=e.sym, side=e.side, has_zone=True, zone_pct=(top - bot) / R, dist_R=(bot - f.c.iloc[0]) / R if len(f) else np.nan,
                     touch=t_bot < NEVER, mid=t_mid < NEVER, full=t_top < NEVER, h4_above=t_h4 < NEVER,
                     touch_before_E1=t_bot < t_E1, touch_before_newlow=t_bot < t_new, E1=t_E1 < NEVER,
                     days_touch=(t_bot - ts).total_seconds() / 86400 if t_bot < NEVER else np.nan,
                     touch_1w=t_bot < ts + pd.Timedelta(weeks=1), touch_wk=t_bot < (ts.normalize() - pd.Timedelta(days=ts.dayofweek) + pd.Timedelta(weeks=1)),
                     h4_above_given_touch=(t_h4 < NEVER) if t_bot < NEVER else np.nan))
D = pd.DataFrame(rows); D.to_csv(OUT, index=False)
P = lambda x: f'{np.nanmean(x.astype(float)) * 100:3.0f}%'
for nm, g in (('ETH снятие лоя', D[(D.sym == 'ETHUSDT') & (D.side == 'low')]), ('ETH обе', D[D.sym == 'ETHUSDT']),
              ('9 монет снятие лоя', D[D.side == 'low']), ('9 монет обе', D)):
    z = g[g.has_zone]
    if not len(z): print(nm, 'нет'); continue
    t = z[z.touch]
    print(f'{nm:20s} случаев {len(g):3d} (с зоной {len(z)}) | до зоны {z.dist_R.median():.2f}R | откат в зону: до этой недели {P(z.touch_wk)}  за неделю {P(z.touch_1w)}  за 4 нед. {P(z.touch)} '
          f'(медиана {t.days_touch.median():.1f} дн.) | середина зоны {P(z.mid)}  вся зона {P(z.full)}  H4 выше {P(z.h4_above)} | откат раньше нового лоя {P(z.touch_before_newlow)}  раньше L-1R {P(z.touch_before_E1)} | после касания H4 выше {P(t.h4_above)}')
