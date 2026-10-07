"""Вероятности исходов после подтверждения (без стопов и RR).
python conf_prob.py <dir_pkl> <events.csv> <trades.csv> <out.csv>
Для каждого события и подтверждения берётся момент подтверждения te (первое на этом ТФ).
Разворот (лонг): что раньше — середина / хай матери или обновление лоя свипа; дойдёт ли до хая вообще.
Продолжение (шорт): что раньше — L−1R или возврат к середине матери; дойдёт ли до L−1R / L−1,5R.
Горизонт 4 недели. Частота: в скольких событиях подтверждение вообще появилось за 7 дней."""
import sys, numpy as np, pandas as pd
SRC, EV, TR, OUT = sys.argv[1:5]
E = pd.read_csv(EV); E = E[~E.open]
T = pd.read_csv(TR); T = T[~T.open]
T = T.drop_duplicates(['sym', 'side', 'ib_week', 'conf'])
HOLD = pd.Timedelta(weeks=4); NEVER = pd.Timestamp.max
cache = {}
def mframe(sym, side):
    if (sym, side) not in cache:
        raw = pd.read_pickle(f'{SRC}/{sym}.pkl')
        cache[(sym, side)] = raw if side == 'low' else pd.DataFrame({'h': -raw.l, 'l': -raw.h, 'c': -raw.c}, index=raw.index)
    return cache[(sym, side)]
ev = {(r.sym, r.side, r.ib_week): r for r in E.itertuples()}
rows = []
for t in T.itertuples():
    e = ev.get((t.sym, t.side, t.ib_week))
    if e is None: continue
    sg = 1 if t.side == 'low' else -1
    m = mframe(t.sym, t.side)
    L, H, R = sg * e.L, sg * e.H, e.R; mid = L + R / 2
    t0, te = pd.Timestamp(e.t0), pd.Timestamp(t.t_entry)
    sweep_low = m.loc[t0:te - pd.Timedelta('15min')].l.min()
    f = m.loc[te:te + HOLD]
    def first(mask):
        i = np.nonzero(mask)[0]; return f.index[i[0]] if len(i) else NEVER
    tH, tM, tLow, tE1, tE15, tL = (first(f.h.values >= H), first(f.h.values >= mid), first(f.l.values < sweep_low),
                                    first(f.l.values <= L - R), first(f.l.values <= L - 1.5 * R), first(f.h.values >= L))
    wk_end = te.normalize() - pd.Timedelta(days=te.dayofweek) + pd.Timedelta(weeks=1)
    wkc = m.c.loc[:wk_end - pd.Timedelta('15min')].iloc[-1]
    rows.append(dict(sym=t.sym, side=t.side, ib_week=t.ib_week, conf=t.conf, kind=t.kind, yr=te.year,
                     mid_before_newlow=tM < tLow, H_before_newlow=tH < tLow, reach_H=tH < NEVER, reach_mid=tM < NEVER,
                     newlow=tLow < NEVER, E1_before_mid=tE1 < tM, reach_E1=tE1 < NEVER, reach_E15=tE15 < NEVER,
                     back_L=tL < NEVER, wk_close_inside=bool(wkc > L)))
D = pd.DataFrame(rows)
n_ev = E.groupby('side').size().to_dict()
out = []
for side_f, nm in ((None, 'all'), ('low', 'low')):
    d = D if side_f is None else D[D.side == side_f]
    nev = len(E) if side_f is None else n_ev.get(side_f, 0)
    for (k, c), g in d.groupby(['kind', 'conf']):
        r = {kk: round(float(g[kk].mean() * 100), 1) for kk in ['mid_before_newlow', 'H_before_newlow', 'reach_mid', 'reach_H', 'newlow',
                                                                 'E1_before_mid', 'reach_E1', 'reach_E15', 'back_L', 'wk_close_inside']}
        out.append(dict(sample=nm, kind=k, conf=c, n=len(g), **r))
pd.DataFrame(out).to_csv(OUT, index=False)
D.to_csv(OUT.replace('.csv', '_rows.csv'), index=False)
print(pd.DataFrame(out).to_string())
