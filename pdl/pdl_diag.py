"""Диагностика сетапа PDL NY AM + инверсия H1 FVG (SEL=pdl): выходы (кривая R), стоп (MAE), контекст старшего ТФ, SMT с BTC.
python pdl_diag.py <dir_pkl> <trades.csv> <out.csv>"""
import sys, numpy as np, pandas as pd
SRC, TR, OUT = sys.argv[1:4]
T = pd.read_csv(TR); T = T[(T.status == 'сделка') & (T.side == 'low') & (T.sym != 'BTCUSDT')].copy()
btc = pd.read_pickle(f'{SRC}/BTCUSDT.pkl'); BD = btc.resample('1D').agg(h=('h', 'max'), l=('l', 'min'), c=('c', 'last'))
cache = {}; rows = []
KS = [0.5, 0.75, 1, 1.5, 2, 3]
for t in T.itertuples():
    if t.sym not in cache:
        m = pd.read_pickle(f'{SRC}/{t.sym}.pkl')
        cache[t.sym] = (m, m.resample('1D').agg(o=('o', 'first'), h=('h', 'max'), l=('l', 'min'), c=('c', 'last')).dropna(),
                        m.resample('W-MON', label='left', closed='left').agg(h=('h', 'max'), l=('l', 'min'), c=('c', 'last')).dropna())
    m, D, W = cache[t.sym]
    day = pd.Timestamp(t.day); di = D.index.get_loc(day)
    PDL, PDH = D.l.iloc[di - 1], D.h.iloc[di - 1]
    tS, tE = pd.Timestamp(t.t_sweep), pd.Timestamp(t.t_entry)
    entry = t.entry; sweep_low = m.loc[tS:tE - pd.Timedelta('15min')].l.min(); stop = sweep_low * 0.999; risk = entry - stop
    f = m.loc[tE:tE + pd.Timedelta('5D')]; fh, fl = f.h.values, f.l.values
    def first(mk):
        q = np.nonzero(mk)[0]; return q[0] if len(q) else 10**9
    iS = first(fl <= stop)
    r = dict(sym=t.sym, day=t.day, yr=tE.year, risk_pct=risk / entry * 100)
    for k in KS: r[f'k{k}'] = first(fh >= entry + k * risk) < iS
    # MAE до достижения +1R (для выигрышных по 1R)
    i1 = first(fh >= entry + risk)
    r['mae_R'] = (entry - fl[:min(i1, len(fl) - 1) + 1].min()) / risk if len(fl) else np.nan
    # стоп шире: под лоем −0,25R / −0,5R
    for b in (0.25, 0.5):
        st2 = stop - b * risk; rk2 = entry - st2
        r[f'wide{b}'] = first(fh >= entry + rk2) < first(fl <= st2)
    # контекст
    lows = D.l.iloc[:di]
    r['took_3d'] = sweep_low < lows.iloc[-3:].min(); r['took_5d'] = sweep_low < lows.iloc[-5:].min(); r['took_10d'] = sweep_low < lows.iloc[-10:].min()
    wk = day - pd.Timedelta(days=day.dayofweek); pwW = W.loc[:wk - pd.Timedelta('1D')]
    if len(pwW):
        pw = pwW.iloc[-1]; r['took_pwl'] = sweep_low < pw.l
        r['pos_pw'] = (entry - pw.l) / (pw.h - pw.l) if pw.h > pw.l else np.nan
    sma20 = D.c.iloc[di - 20:di].mean() if di >= 20 else np.nan
    r['above_sma20'] = D.c.iloc[di - 1] > sma20 if sma20 == sma20 else None
    rng = (D.h - D.l).iloc[di - 20:di].mean() if di >= 20 else np.nan
    r['pd_vs_atr'] = (PDH - PDL) / rng if rng == rng else np.nan
    r['dow'] = day.dayofweek
    # SMT: BTC снял свой PDL до момента входа?
    if day in BD.index:
        bpdl = BD.l.iloc[BD.index.get_loc(day) - 1]
        r['btc_took_pdl'] = btc.loc[day:tE - pd.Timedelta('15min')].l.min() < bpdl
    # простые альтернативные входы при том же снятии
    seg = m.loc[tS:tS + pd.Timedelta('48h')]
    # A) первое закрытие H1 выше PDL
    h1 = seg.resample('1h').agg(l=('l', 'min'), c=('c', 'last')).dropna(); up = h1.index[h1.c.values > PDL]
    if len(up):
        tA = up[0] + pd.Timedelta('1h'); eA = h1.loc[up[0]].c; sA = m.loc[tS:tA - pd.Timedelta('15min')].l.min() * 0.999; rA = eA - sA
        fA = m.loc[tA:tA + pd.Timedelta('5D')]
        r['A_win'] = first(fA.h.values >= eA + rA) < first(fA.l.values <= sA) if rA > 0 else None
    # B) закрытие дня снятия выше PDL -> вход на закрытии дня
    if D.c.iloc[di] > PDL:
        tB = day + pd.Timedelta('1D'); eB = D.c.iloc[di]; sB = D.l.iloc[di] * 0.999; rB = eB - sB
        fB = m.loc[tB:tB + pd.Timedelta('5D')]
        r['B_win'] = first(fB.h.values >= eB + rB) < first(fB.l.values <= sB)
        r['B_risk'] = rB / eB * 100
    else: r['B_win'] = None
    rows.append(r)
X = pd.DataFrame(rows); X.to_csv(OUT, index=False)
def ev(p, k): return p * k - (1 - p)
for nm, g in (('Альты (вкл. ETH)', X), ('ETH', X[X.sym == 'ETHUSDT'])):
    print(f'\n######## {nm}: сделок {len(g)}')
    print('1) Кривая целей (вероятность цели раньше стопа → ожидание без комиссий):')
    for k in KS:
        p = g[f'k{k}'].mean(); print(f'   {k:>4}R: {p*100:3.0f}% → {ev(p,k):+.2f}R')
    w = g[g['k1']]
    print(f'2) Стоп: у выигрышных (1R) откат до цели — медиана {w.mae_R.median():.2f}R, 80% ≤ {w.mae_R.quantile(.8):.2f}R | '
          f'стоп шире на 0,25R: 1R {g["wide0.25"].mean()*100:.0f}% (ожид. {ev(g["wide0.25"].mean(),1):+.2f}R), на 0,5R: {g["wide0.5"].mean()*100:.0f}% ({ev(g["wide0.5"].mean(),1):+.2f}R)')
    print('3) Альтернативные входы при тех же снятиях (цель 1R, стоп под лоем):')
    a = g.A_win.dropna().astype(bool); b = g.B_win.dropna().astype(bool)
    print(f'   инверсия H1 FVG (наш):        {g.k1.mean()*100:3.0f}% → {ev(g.k1.mean(),1):+.2f}R (n={len(g)})')
    print(f'   первое закрытие H1 выше PDL:  {a.mean()*100:3.0f}% → {ev(a.mean(),1):+.2f}R (n={len(a)})')
    print(f'   закрытие дня выше PDL:        {b.mean()*100:3.0f}% → {ev(b.mean(),1):+.2f}R (n={len(b)})')
    print('4) Контекст (цель 1R, без комиссий):')
    for c, lab in (('took_3d', 'снят лой 3 дней'), ('took_5d', 'снят лой 5 дней'), ('took_10d', 'снят лой 10 дней'), ('took_pwl', 'снят лой прошлой недели'),
                   ('above_sma20', 'выше SMA20 дневки'), ('btc_took_pdl', 'BTC тоже снял PDL')):
        gg = g[g[c].notna()]; y = gg[gg[c].astype(bool)]; n_ = gg[~gg[c].astype(bool)]
        print(f'   {lab:26s} да: {y.k1.mean()*100:3.0f}% {ev(y.k1.mean(),1):+.2f}R (n={len(y)}) | нет: {n_.k1.mean()*100:3.0f}% {ev(n_.k1.mean(),1):+.2f}R (n={len(n_)})')
    for c, edges in (('pos_pw', [-9, 0, 0.25, 0.5, 9]), ('pd_vs_atr', [0, 0.7, 1, 1.4, 9]), ('risk_pct', [0, 2, 3, 4.5, 99])):
        q = pd.cut(g[c], edges); print(f'   {c}: ' + ' | '.join(f'{k}: {gg.k1.mean()*100:.0f}% (n={len(gg)})' for k, gg in g.groupby(q, observed=True)))
    print('   день недели: ' + ' | '.join(f'{["Пн","Вт","Ср","Чт","Пт","Сб","Вс"][k]} {gg.k1.mean()*100:.0f}% (n={len(gg)})' for k, gg in g.groupby('dow')))
    print('5) По годам (1R): ' + ' | '.join(f'{k}: {gg.k1.mean()*100:.0f}% (n={len(gg)})' for k, gg in g.groupby('yr')))
