"""Последовательность событий из текущего состояния (вынос >= X·R): отскок без зоны / зона / новый лой / пробой зоны H4.
python path_seq.py <dir_pkl> <zone_retrace_state.csv-совместимые events.csv> <X>"""
import sys, numpy as np, pandas as pd
SRC, EV, X = sys.argv[1], sys.argv[2], float(sys.argv[3])
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
    a = m.loc[t0:t0 + pd.Timedelta(weeks=1)]
    ok = np.nonzero((np.minimum.accumulate(a.l.values) <= L - X * R) & (np.maximum.accumulate(a.h.values) < H))[0]
    if not len(ok): continue
    ts = a.index[ok[0]]; pre = m.loc[t0:ts]; ext = pre.l.min(); ext_t = pre.l.idxmin()
    B = b4.loc[:ts - pd.Timedelta('4h')]; xb = B.index.searchsorted(ext_t, side='right') - 1
    hv, lv, cv = B.h.values, B.l.values, B.c.values; zone = None
    for k in range(min(xb, len(B) - 1), max(2, xb - 84), -1):
        if hv[k] < lv[k - 2] and lv[k - 2] >= L and not (cv[k + 1:xb + 1] > lv[k - 2]).any():
            zone = (lv[k - 2], hv[k]); break
    if zone is None: continue
    top, bot = zone
    f = m.loc[ts + pd.Timedelta('15min'):ts + pd.Timedelta(weeks=4)]
    fh, fl, fi = f.h.values, f.l.values, f.index
    nl = np.nonzero(fl < ext)[0]; i_nl = nl[0] if len(nl) else None
    zt = np.nonzero(fh >= bot)[0]; i_z = zt[0] if len(zt) else None
    f4 = b4.loc[ts:ts + pd.Timedelta(weeks=4)]; up = f4.index[f4.c.values > top]
    t_up = up[0] + pd.Timedelta('4h') if len(up) else None
    r = dict(sym=e.sym, side=e.side)
    if i_nl is None or (i_z is not None and i_z < i_nl):
        r['path'] = 'zone_first' if i_z is not None else 'nothing'
    else:
        pre_nl = f.iloc[:i_nl]
        bounce = (pre_nl.h.max() - ext) / R if len(pre_nl) else 0           # отскок от лоя до нового лоя
        r.update(path='newlow_first', bounce_R=bounce, days_to_nl=(fi[i_nl] - ts).total_seconds() / 86400)
        g = f.iloc[i_nl:]
        # глубина нового лоя до первого касания зоны / пробоя
        z2 = np.nonzero(g.h.values >= bot)[0]
        end = z2[0] if len(z2) else len(g) - 1
        r['nl_depth_R'] = (ext - g.l.iloc[:end + 1].min()) / R
        r['zone_after_nl'] = len(z2) > 0
        r['h4_after_nl'] = t_up is not None and t_up > fi[i_nl]
        r['E1_after_nl'] = bool((g.l.values <= L - R).any())
    r['h4_above'] = t_up is not None
    rows.append(r)
D = pd.DataFrame(rows)
for nm, g in (('ETH снятие лоя', D[(D.sym == 'ETHUSDT') & (D.side == 'low')]), ('9 монет снятие лоя', D[D.side == 'low']), ('9 монет обе', D)):
    n = len(g); vc = g.path.value_counts()
    nf = g[g.path == 'newlow_first']; zf = g[g.path == 'zone_first']
    print(f'== {nm}: случаев {n}')
    print(f'   1) сразу в зону, без нового лоя: {vc.get("zone_first",0)/n*100:.0f}%  → из них H4 выше зоны {zf.h4_above.mean()*100 if len(zf) else float("nan"):.0f}%')
    print(f'   2) сначала новый лой: {len(nf)/n*100:.0f}%  (через {nf.days_to_nl.median():.1f} дн.; отскок перед ним: медиана {nf.bounce_R.median():.2f}R, 75% {nf.bounce_R.quantile(.75):.2f}R; до зоны было {0.44:.2f}R)')
    print(f'      глубина нового лоя ниже лоя манипуляции: медиана {nf.nl_depth_R.median():.2f}R, 25–75%: {nf.nl_depth_R.quantile(.25):.2f}–{nf.nl_depth_R.quantile(.75):.2f}R')
    print(f'      после нового лоя: дошла до зоны {nf.zone_after_nl.mean()*100:.0f}%  H4 выше зоны {nf.h4_after_nl.mean()*100:.0f}%  ушла до L-1R {nf.E1_after_nl.mean()*100:.0f}%')
    print(f'   3) ни зоны, ни нового лоя: {vc.get("nothing",0)/n*100:.0f}%')
