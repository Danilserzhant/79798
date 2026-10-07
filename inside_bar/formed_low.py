"""Сформированный лой: после первого снятия лоя матери берём первый подтверждённый H4 фрактальный лой (2+2) ниже лоя матери,
при этом зона H4 FVG (последний медвежий H4 FVG с верхом >= лоя матери до этого лоя) ещё не тронута.
От момента подтверждения фрактала (закрытие 2-й свечи справа), горизонт 4 недели: что раньше — касание зоны или пробой лоя, и что потом.
python formed_low.py <dir_pkl> <events.csv> [TF=4h]"""
import sys, numpy as np, pandas as pd
SRC, EV = sys.argv[1], sys.argv[2]
TF = sys.argv[3] if len(sys.argv) > 3 else '4h'
E = pd.read_csv(EV); E = E[~E.open]
cache = {}; rows = []
for e in E.itertuples():
    if (e.sym, e.side) not in cache:
        raw = pd.read_pickle(f'{SRC}/{e.sym}.pkl')
        m = raw if e.side == 'low' else pd.DataFrame({'h': -raw.l, 'l': -raw.h, 'c': -raw.c}, index=raw.index)
        cache[(e.sym, e.side)] = (m, m.resample('4h').agg(h=('h', 'max'), l=('l', 'min'), c=('c', 'last')).dropna(),
                                  m.resample(TF).agg(h=('h', 'max'), l=('l', 'min'), c=('c', 'last')).dropna())
    m, b4, bf = cache[(e.sym, e.side)]
    sg = 1 if e.side == 'low' else -1
    L, H, R = sg * e.L, sg * e.H, e.R; t0 = pd.Timestamp(e.t0)
    off = pd.Timedelta(TF)
    F = bf.loc[t0.floor(TF):t0 + pd.Timedelta(weeks=2)]
    fh, fl, fi = F.h.values, F.l.values, F.index
    k_found = None
    for k in range(2, len(F) - 2):
        if fl[k] < L and fl[k] < fl[k - 1] and fl[k] < fl[k - 2] and fl[k] <= fl[k + 1] and fl[k] <= fl[k + 2]:
            # фрактал должен быть минимумом с начала снятия (это и есть «лой манипуляции»)
            if fl[k] > m.loc[t0:fi[k] + off - pd.Timedelta('15min')].l.min() + 1e-12: continue
            k_found = k; break
    if k_found is None: continue
    k = k_found; low = fl[k]; tc = fi[k + 2] + off                # подтверждение
    if m.loc[fi[k]:tc - pd.Timedelta('15min')].l.min() < low: continue
    # зона H4 FVG на момент лоя
    B = b4.loc[:fi[k]]; xb = len(B) - 1
    hv, lv, cv = B.h.values, B.l.values, B.c.values; zone = None
    for kk in range(xb, max(2, xb - 84), -1):
        if hv[kk] < lv[kk - 2] and lv[kk - 2] >= L and not (cv[kk + 1:xb + 1] > lv[kk - 2]).any():
            zone = (lv[kk - 2], hv[kk]); break
    if zone is None: continue
    top, bot = zone
    if m.loc[fi[k]:tc - pd.Timedelta('15min')].h.max() >= bot: continue   # зона уже тронута до подтверждения
    f = m.loc[tc:tc + pd.Timedelta(weeks=4)]
    gh, gl, gi = f.h.values, f.l.values, f.index
    def first(mk, s=0):
        j = np.nonzero(mk[s:])[0]; return s + j[0] if len(j) else None
    iz, inl = first(gh >= bot), first(gl < low)
    f4 = b4.loc[tc:tc + pd.Timedelta(weeks=4)]; up = f4.index[f4.c.values > top]; t_up = up[0] + pd.Timedelta('4h') if len(up) else None
    r = dict(sym=e.sym, side=e.side, depth=(L - low) / R, zone_first=iz is not None and (inl is None or iz < inl),
             newlow=inl is not None, h4_above=t_up is not None, bounce_at_conf=(f.c.iloc[0] - low) / R if len(f) else np.nan)
    if r['zone_first']:
        tz = gi[iz]
        r['h4_before_nl'] = t_up is not None and (inl is None or t_up < gi[inl])
        r['H_before_nl'] = (first(gh >= H, iz) or 10**9) < (inl if inl is not None else 10**9)
        r['mid_before_nl'] = (first(gh >= L + R / 2, iz) or 10**9) < (inl if inl is not None else 10**9)
        r['nl_after_zone'] = inl is not None
        r['full_zone_before_nl'] = (first(gh >= top, iz) or 10**9) < (inl if inl is not None else 10**9)
        r['days_to_zone'] = (tz - tc).total_seconds() / 86400
        # если после зоны всё же новый лой — насколько глубоко и что потом
        if inl is not None:
            g2 = f.iloc[inl:]; r['nl_depth_after_zone_R'] = (low - g2.l.min()) / R
            r['E1_after'] = bool((g2.l <= L - R).any())
            r['h4_after_nl'] = t_up is not None and t_up > gi[inl]
    rows.append(r)
D = pd.DataFrame(rows)
P = lambda x: f'{np.nanmean(pd.Series(x).astype(float)) * 100:3.0f}%' if len(x) else '—'
for nm, g in (('ETH снятие лоя', D[(D.sym == 'ETHUSDT') & (D.side == 'low')]), ('ETH обе', D[D.sym == 'ETHUSDT']),
              ('9 монет снятие лоя', D[D.side == 'low']), ('9 монет обе', D)):
    z = g[g.zone_first]
    print(f'== {nm}: случаев {len(g)} | глубина лоя мед {g.depth.median():.2f}R')
    print(f'   коррекция в зону РАНЬШЕ пробоя лоя: {P(g.zone_first)} (через {z.days_to_zone.median():.1f} дн.) | пробой лоя раньше зоны: {P(~g.zone_first & g.newlow)} | ни того ни другого: {P(~g.zone_first & ~g.newlow)}')
    if len(z):
        print(f'   после коррекции в зону (n={len(z)}): H4 выше зоны раньше нового лоя {P(z.h4_before_nl)} | середина матери раньше нового лоя {P(z.mid_before_nl)} | хай матери раньше нового лоя {P(z.H_before_nl)} | '
              f'потом всё-таки новый лой {P(z.nl_after_zone)}')
        zn = z[z.nl_after_zone]
        if len(zn): print(f'   если после зоны новый лой (n={len(zn)}): глубина мед {zn.nl_depth_after_zone_R.median():.2f}R | до L-1R {P(zn.E1_after)} | потом H4 выше зоны {P(zn.h4_after_nl)}')
