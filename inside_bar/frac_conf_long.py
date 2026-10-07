"""Лонг на подтверждении ПЕРВОГО H4 фрактального лоя после пересечения лоя матери (центр фрактала может быть свечой пересечения).
Вход — закрытие 2-й свечи H4 справа от фрактала; стоп — под фрактальным лоем −0,1%; цель — низ зоны H4 FVG (нетронутой).
Издержки 0,1%. python frac_conf_long.py <dir_pkl> <events.csv> <out.csv>"""
import sys, os, numpy as np, pandas as pd
NF = int(os.environ.get('FRAC', '5')) // 2   # 5 — фрактал 2+2, 3 — фрактал 1+1
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
    j0 = b4.index.searchsorted(t0.floor('4h'))
    F = b4.iloc[max(0, j0 - 2):j0 + 84]; fh4, fl4, fc4, fi4 = F.h.values, F.l.values, F.c.values, F.index
    k0 = j0 - max(0, j0 - 2); kf = None
    for k in range(max(NF, k0), len(F) - NF):
        if fl4[k] < L and all(fl4[k] < fl4[k - d] for d in range(1, NF + 1)) and all(fl4[k] <= fl4[k + d] for d in range(1, NF + 1)):
            if fl4[k] > m.loc[t0:fi4[k] + pd.Timedelta('4h') - pd.Timedelta('15min')].l.min() + 1e-12: continue
            kf = k; break
    if kf is None: continue
    k = kf; flow = fl4[k]; tconf = fi4[k + NF] + pd.Timedelta('4h'); entry = fc4[k + NF]
    B = b4.loc[:fi4[k]]; xb = len(B) - 1; hv, lv, cv = B.h.values, B.l.values, B.c.values; zone = None
    for kk in range(xb, max(2, xb - 84), -1):
        if hv[kk] < lv[kk - 2] and lv[kk - 2] >= L and not (cv[kk + 1:xb + 1] > lv[kk - 2]).any():
            zone = (lv[kk - 2], hv[kk]); break
    if zone is None: continue
    top, bot = zone
    if m.loc[fi4[k]:tconf - pd.Timedelta('15min')].h.max() >= bot: continue     # зона тронута до подтверждения
    stop = flow - 0.001 * abs(flow); risk = entry - stop
    if risk <= 0 or entry >= bot: continue
    f = m.loc[tconf:tconf + pd.Timedelta(weeks=4)]
    def first(mk):
        q = np.nonzero(mk)[0]; return q[0] if len(q) else 10**9
    iS, iT, iTop = first(f.l.values <= stop), first(f.h.values >= bot), first(f.h.values >= top)
    rr = (bot - entry) / risk; cost = 0.001 * abs(entry) / risk; win = iT < iS
    rows.append(dict(sym=e.sym, side=e.side, ib_week=e.ib_week, t=str(tconf), depth=(L - flow) / R, rr=rr, win=bool(win),
                     net=(rr if win else -1) - cost, top_before_stop=bool(iTop < iS), risk_pct=risk / abs(entry) * 100,
                     entry=sg * entry, stop=sg * stop, target=sg * bot))
D = pd.DataFrame(rows); D.to_csv(OUT, index=False)
for nm, g in (('ETH снятие лоя', D[(D.sym == 'ETHUSDT') & (D.side == 'low')]), ('ETH обе', D[D.sym == 'ETHUSDT']),
              ('9 монет снятие лоя', D[D.side == 'low']), ('9 монет обе', D)):
    for lab, t in (('все', g), ('вынос < 0.3', g[g.depth < 0.3]), ('вынос >= 0.3', g[g.depth >= 0.3])):
        if not len(t): continue
        print(f'{nm:20s} {lab:12s} сделок {len(t):3d} | цель (низ зоны) раньше стопа {t.win.mean()*100:3.0f}% | вся зона {t.top_before_stop.mean()*100:3.0f}% | RR мед {t.rr.median():.1f} | '
              f'итого {t.net.sum():+6.1f}R ср. {t.net.mean():+.2f}R без лучшей {np.sort(t.net.values)[:-1].mean() if len(t)>1 else float("nan"):+.2f}R | риск мед {t.risk_pct.median():.1f}%')
