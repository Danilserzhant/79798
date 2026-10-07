"""Снятие PDL в NY AM + инверсия H1 FVG (SEL=pdl) в недельном контексте инсайда.
Контексты: (1) день в окне 4 недель после закрытия инсайда, хай матери ещё не пробит; (2) лой снятия ниже лоя матери;
(3) день первого снятия лоя матери. python pdl_weekly_ctx.py <dir_pkl> <pdl_trades.csv> <mother_events.csv>"""
import sys, numpy as np, pandas as pd
SRC, TR, EV = sys.argv[1:4]
T = pd.read_csv(TR); T = T[(T.side == 'low') & (T.sym != 'BTCUSDT')].copy()
E = pd.read_csv(EV); E = E[E.side == 'low']
cache = {}
def ctx(row):
    if row.sym not in cache:
        m = pd.read_pickle(f'{SRC}/{row.sym}.pkl')
        W = m.resample('W-MON', label='left', closed='left').agg(h=('h', 'max'), l=('l', 'min')).dropna()
        cache[row.sym] = (m, W)
    m, W = cache[row.sym]
    day = pd.Timestamp(row.day); res = dict(in_ib=False, below_mother=False, first_mother=False, mother_L=np.nan, mother_H=np.nan)
    ev = E[E.sym == row.sym]
    for e in ev.itertuples():
        ibw = pd.Timestamp(e.ib_week); start = ibw + pd.Timedelta(weeks=1)
        if not (start <= day < start + pd.Timedelta(weeks=4)): continue
        L, H = e.L, e.H
        if m.loc[start:day - pd.Timedelta('15min')].h.max() > H: continue        # хай матери уже пробит
        tS = pd.Timestamp(row.t_sweep); tE = pd.Timestamp(row.t_entry) if isinstance(row.t_entry, str) else tS + pd.Timedelta('2D')
        sweep_low = m.loc[tS:tE].l.min()
        res.update(in_ib=True, mother_L=L, mother_H=H, below_mother=bool(sweep_low < L),
                   first_mother=bool(pd.Timestamp(e.t0).normalize() == day))
        break
    return pd.Series(res)
C = T.apply(ctx, axis=1); T = pd.concat([T, C], axis=1)
T['yr'] = pd.to_datetime(T.day).dt.year
tr = T[T.status == 'сделка'].copy()
for c in ('net_1R', 'net_PDH', 'net_2R'): tr[c] = pd.to_numeric(tr[c], errors='coerce')
# цель — середина / хай матери
def mother_targets(r):
    if not r.in_ib or r.status != 'сделка': return pd.Series(dict(n_mid=np.nan, n_mH=np.nan))
    m, _ = cache[r.sym]; e = r.entry; tE = pd.Timestamp(r.t_entry)
    stop = m.loc[pd.Timestamp(r.t_sweep):tE - pd.Timedelta('15min')].l.min() * 0.999; risk = e - stop
    f = m.loc[tE:tE + pd.Timedelta('10D')]
    def first(mk):
        q = np.nonzero(mk)[0]; return q[0] if len(q) else 10**9
    iS = first(f.l.values <= stop); out = {}
    for nm, tgt in (('n_mid', (r.mother_L + r.mother_H) / 2), ('n_mH', r.mother_H)):
        if tgt <= e: out[nm] = np.nan; continue
        rr = (tgt - e) / risk; out[nm] = (rr if first(f.h.values >= tgt) < iS else -1) - 0.001 * e / risk
    return pd.Series(out)
tr = pd.concat([tr, tr.apply(mother_targets, axis=1)], axis=1)
def show(lab, g, allg):
    n_all = len(allg); s = g
    if not len(s): print(f'{lab:52s} 0'); return
    yrs = s.yr
    line = (f'{lab:52s} снятий {n_all:4d} → сделок {len(s):3d} | 1R: {(s.net_1R>0).mean()*100:3.0f}% ср. {s.net_1R.mean():+.2f}R итого {s.net_1R.sum():+6.1f}R '
            f'(24–26 {s.net_1R[yrs>2023].mean():+.2f}) | PDH: ср. {s.net_PDH.mean():+.2f}R')
    if s.n_mid.notna().any(): line += f' | середина матери: {(s.n_mid>0).mean()*100:3.0f}% ср. {s.n_mid.mean():+.2f}R | хай матери: {(s.n_mH>0).mean()*100:3.0f}% ср. {s.n_mH.mean():+.2f}R'
    print(line)
for nm, msk in (('ETH', lambda d: d.sym == 'ETHUSDT'), ('Альты вместе (вкл. ETH)', lambda d: d.sym == d.sym)):
    print(f'\n######## {nm}')
    A = T[msk(T)]; X = tr[msk(tr)]
    show('Все снятия PDL в NY AM', X, A)
    show('Вне недельного контекста инсайда', X[~X.in_ib], A[~A.in_ib])
    show('(1) После инсайда, хай матери не пробит', X[X.in_ib], A[A.in_ib])
    show('    …снятие внутри диапазона матери', X[X.in_ib & ~X.below_mother], A[A.in_ib & ~A.below_mother])
    show('(2) …снятие ниже лоя матери', X[X.in_ib & X.below_mother], A[A.in_ib & A.below_mother])
    show('(3) …день первого снятия лоя матери', X[X.first_mother], A[A.first_mother])
T.to_csv(TR.replace('.csv', '_ctx.csv'), index=False)
