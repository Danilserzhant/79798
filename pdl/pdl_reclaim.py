"""Альтернативный вход на ВСЕХ снятиях PDL в NY AM: первое закрытие H1 (или M15) выше PDL после снятия.
Инвалидация — дневное закрытие ниже PDL до входа; окно 48 ч. Стоп под лоем с момента снятия −0,1%; цели 0,5R/1R/1,5R/2R/PDH;
издержки 0,1%. Для сравнения — инверсия H1 FVG (из файла сделок SEL=pdl). python pdl_reclaim.py <dir_pkl> <pdl_trades.csv> [TF=1h]"""
import sys, numpy as np, pandas as pd
SRC, TR = sys.argv[1], sys.argv[2]
TF = sys.argv[3] if len(sys.argv) > 3 else '1h'
A = pd.read_csv(TR); A = A[(A.side == 'low') & (A.sym != 'BTCUSDT')]
cache = {}; rows = []
for a in A.itertuples():
    if a.sym not in cache:
        m = pd.read_pickle(f'{SRC}/{a.sym}.pkl')
        cache[a.sym] = (m, m.resample('1D').agg(h=('h', 'max'), l=('l', 'min'), c=('c', 'last')).dropna())
    m, D = cache[a.sym]
    day = pd.Timestamp(a.day); di = D.index.get_loc(day); PDL, PDH = D.l.iloc[di - 1], D.h.iloc[di - 1]
    tS = pd.Timestamp(a.t_sweep); end = tS + pd.Timedelta('48h')
    for dd in range(di, min(di + 3, len(D))):
        dc = D.index[dd] + pd.Timedelta('1D')
        if dc > end: break
        if D.c.iloc[dd] < PDL: end = dc; break
    bars = m.loc[tS.floor(TF):end].resample(TF).agg(c=('c', 'last')).dropna()
    bars = bars[bars.index + pd.Timedelta(TF) > tS]; bars = bars[bars.index + pd.Timedelta(TF) <= end]
    up = bars.index[bars.c.values > PDL]
    r = dict(sym=a.sym, day=a.day, yr=day.year, ifvg=a.status == 'сделка', ifvg_net=a.net_1R)
    if not len(up): r['entered'] = False; rows.append(r); continue
    tE = up[0] + pd.Timedelta(TF); e = bars.loc[up[0]].c
    lo = m.loc[tS:tE - pd.Timedelta('15min')].l.min(); stop = lo * 0.999; risk = e - stop
    f = m.loc[tE:tE + pd.Timedelta('5D')]; fh, fl = f.h.values, f.l.values
    def first(mk):
        q = np.nonzero(mk)[0]; return q[0] if len(q) else 10**9
    iS = first(fl <= stop); cost = 0.001 * e / risk
    r.update(entered=True, hours=(tE - tS).total_seconds() / 3600, risk_pct=risk / e * 100, same_day=tE <= day + pd.Timedelta('1D'))
    for k in (0.5, 1, 1.5, 2):
        w = first(fh >= e + k * risk) < iS; r[f'n{k}'] = (k if w else -1) - cost; r[f'w{k}'] = w
    if PDH > e:
        rr = (PDH - e) / risk; w = first(fh >= PDH) < iS; r['nP'] = (rr if w else -1) - cost; r['wP'] = w; r['rrP'] = rr
    rows.append(r)
X = pd.DataFrame(rows)
for nm, g in (('Альты (вкл. ETH)', X), ('ETH', X[X.sym == 'ETHUSDT'])):
    e = g[g.entered == True]
    print(f'\n== {nm}: снятий PDL в NY AM {len(g)} | вход (закрытие {TF} выше PDL до инвалидации) {len(e)} ({len(e)/len(g)*100:.0f}%) | до входа мед {e.hours.median():.1f} ч | риск мед {e.risk_pct.median():.2f}%')
    for k in (0.5, 1, 1.5, 2):
        n = e[f'n{k}']; print(f'   цель {k}R: {e[f"w{k}"].mean()*100:3.0f}% | ср. {n.mean():+.2f}R итого {n.sum():+6.1f}R | 2020–23 {n[e.yr<=2023].mean():+.2f}R  2024–26 {n[e.yr>2023].mean():+.2f}R')
    p = e[e.nP.notna()]; print(f'   цель PDH (RR мед {p.rrP.median():.1f}): {p.wP.astype(bool).mean()*100:3.0f}% | ср. {p.nP.mean():+.2f}R итого {p.nP.sum():+6.1f}R | 2024–26 {p.nP[p.yr>2023].mean():+.2f}R')
    sd = e[e.same_day == True]; nd = e[e.same_day == False]
    print(f'   вход в день снятия: 1R ср. {sd.n1.mean():+.2f}R (n={len(sd)}) | на следующий день: {nd.n1.mean():+.2f}R (n={len(nd)})')
    iv = g[g.ifvg]; print(f'   для сравнения инверсия H1 FVG: n={len(iv)} 1R ср. {iv.ifvg_net.astype(float).mean():+.2f}R итого {iv.ifvg_net.astype(float).sum():+.1f}R')
