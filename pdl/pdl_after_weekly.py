"""PDL NY AM + инверсия H1 FVG (SEL=pdl) как вход ПОСЛЕ подтверждённого недельного сетапа.
Подтверждение: (a) неделя снятия лоя матери закрылась выше лоя матери; (b) строго — был сигнал H4 (инверсия H4 FVG у лоя матери) и неделя выше.
Окно: 2 недели после недельного закрытия; хай матери ещё не взят. Цели: хай/середина матери, PDH, 1R; горизонт 10 дней; издержки 0,1%.
python pdl_after_weekly.py <dir_pkl> <pdl_trades.csv> <mother_events.csv> <weekly_confirmed_signals_wk.csv>"""
import sys, numpy as np, pandas as pd
SRC, TR, EV, WC = sys.argv[1:5]
T = pd.read_csv(TR); T = T[(T.status == 'сделка') & (T.side == 'low') & (T.sym != 'BTCUSDT')].copy()
E = pd.read_csv(EV); E = E[(E.side == 'low') & (E.sym != 'BTCUSDT') & (~E.open)]
WCx = pd.read_csv(WC); WCx = WCx[(WCx.side == 'low') & WCx.conf.str.startswith('Инверсия H4')]
strict = {(r.sym, r.ib_week): pd.Timestamp(r.t_entry) for r in WCx.itertuples()}
cache = {}; rows = []
for e in E.itertuples():
    if e.sym not in cache: cache[e.sym] = pd.read_pickle(f'{SRC}/{e.sym}.pkl')
    m = cache[e.sym]; L, H = e.L, e.H; t0 = pd.Timestamp(e.t0)
    we = t0.normalize() - pd.Timedelta(days=t0.dayofweek) + pd.Timedelta(weeks=1)
    if we > m.index[-1]: continue
    if m.c.loc[:we - pd.Timedelta('15min')].iloc[-1] <= L: continue          # неделя не закрылась выше лоя матери
    if m.loc[t0:we - pd.Timedelta('15min')].h.max() >= H: continue          # хай матери уже взят
    is_strict = (e.sym, e.ib_week) in strict
    cand = T[(T.sym == e.sym) & (pd.to_datetime(T.t_entry) >= we) & (pd.to_datetime(T.t_entry) < we + pd.Timedelta(weeks=2))].sort_values('t_entry')
    for c in cand.itertuples():
        tE = pd.Timestamp(c.t_entry)
        if m.loc[we:tE].h.max() >= H: break                                   # хай матери уже достигнут
        entry = c.entry; stop = m.loc[pd.Timestamp(c.t_sweep):tE - pd.Timedelta('15min')].l.min() * 0.999; risk = entry - stop
        if risk <= 0: continue
        f = m.loc[tE:tE + pd.Timedelta('10D')]; fh, fl = f.h.values, f.l.values
        def first(mk):
            q = np.nonzero(mk)[0]; return q[0] if len(q) else 10**9
        iS = first(fl <= stop); cost = 0.001 * entry / risk
        D = m.resample('1D').agg(h=('h', 'max')); PDH = D.h.loc[:pd.Timestamp(c.day) - pd.Timedelta('1D')].iloc[-1]
        r = dict(sym=e.sym, ib_week=e.ib_week, day=c.day, yr=tE.year, strict=is_strict, risk_pct=risk / entry * 100)
        for nm, tgt in (('1R', entry + risk), ('PDH', PDH), ('mid', (L + H) / 2), ('mH', H)):
            if tgt <= entry: r[f'n_{nm}'] = np.nan; r[f'rr_{nm}'] = np.nan; continue
            rr = (tgt - entry) / risk; r[f'n_{nm}'] = (rr if first(fh >= tgt) < iS else -1) - cost; r[f'rr_{nm}'] = rr
        rows.append(r)
        break                                                                 # одна сделка на недельный сетап
X = pd.DataFrame(rows); X.to_csv(TR.replace('.csv', '_after_weekly.csv'), index=False)
n_setups = sum(1 for e in E.itertuples())
for nm, g in (('ETH', X[X.sym == 'ETHUSDT']), ('Альты вместе (вкл. ETH)', X)):
    for lab, gg in (('неделя выше лоя матери', g), ('строго: + сигнал H4', g[g.strict])):
        if not len(gg): print(f'{nm} | {lab}: 0'); continue
        print(f'\n== {nm} | {lab}: сделок {len(gg)} | риск мед {gg.risk_pct.median():.2f}%')
        for k, lab2 in (('1R', '1R'), ('PDH', 'PDH'), ('mid', 'середина матери'), ('mH', 'хай матери')):
            v = gg[f'n_{k}'].dropna()
            if not len(v): continue
            yrs = gg.loc[v.index, 'yr']
            print(f'   {lab2:16s} (n={len(v):3d}, RR мед {gg[f"rr_{k}"].dropna().median():4.1f}): до цели {(v>0).mean()*100:3.0f}% | ср. {v.mean():+.2f}R итого {v.sum():+6.1f}R | 2020–23 {v[yrs<=2023].mean():+.2f}R 2024–26 {v[yrs>2023].mean():+.2f}R')
