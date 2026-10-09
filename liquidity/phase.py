"""Фаза рынка и продолжение недельной фрактальной ножки. python phase.py <dir_pkl_15m> <retrace_W.csv>
Метрики на открытие недели после подтверждения фрактала (t + 2 недели), только по закрытым неделям."""
import sys, numpy as np, pandas as pd
SRC, RW = sys.argv[1:3]
SYMS = ['ETHUSDT', 'BTCUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'LTCUSDT', 'LINKUSDT']
ALTS = ['SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'LTCUSDT', 'LINKUSDT']
W = {}
for s in SYMS:
    m = pd.read_pickle(f'{SRC}/{s}.pkl').c
    k = m.index.normalize() - pd.to_timedelta(m.index.dayofweek, unit='D')
    W[s] = m.groupby(k).last()
P = pd.DataFrame(W)
btc = P.BTCUSDT
rel = np.log(P[ALTS + ['ETHUSDT']].div(btc, axis=0))                 # альты в BTC
idx = rel.sub(rel.bfill().iloc[0]).mean(axis=1, skipna=True)         # индекс альты/BTC (лог, среднее по доступным)
F = pd.DataFrame(index=P.index)
F['btc_ma20'] = btc > btc.rolling(20).mean()
F['btc_ma50'] = btc > btc.rolling(50).mean()
F['btc_mom4'] = btc > btc.shift(4)
F['altbtc_up'] = idx > idx.rolling(20).mean()                        # доминация BTC падает
F['altbtc_mom10'] = idx > idx.shift(10)
F = F.shift(0)                                                        # значение на закрытии недели
D = pd.read_csv(RW); D['t'] = pd.to_datetime(D.t)
for c in ('cont', 'confirmed_ok'): D[c] = D[c].astype(str).eq('True')
D = D[D.confirmed_ok]
D['wk'] = D.t + pd.Timedelta(weeks=1)                                 # закрытие недели подтверждения = известно на открытие t+2
rows = []
for r in D.itertuples():
    if r.wk not in F.index: continue
    f = F.loc[r.wk].to_dict(); p = P[r.sym]
    hist = p.loc[:r.wk]
    f['coin_ma20'] = hist.iloc[-1] > hist.tail(20).mean() if len(hist) >= 20 else np.nan
    f['coin_ma50'] = hist.iloc[-1] > hist.tail(50).mean() if len(hist) >= 50 else np.nan
    cb = (p / btc).loc[:r.wk]
    f['coin_vs_btc10'] = cb.iloc[-1] > cb.iloc[-11] if len(cb) > 11 else np.nan
    rows.append(dict(sym=r.sym, side=r.side, t=r.t, cont=r.cont, **f))
X = pd.DataFrame(rows)
NAMES = {'btc_ma20': 'BTC выше 20-нед средней', 'btc_ma50': 'BTC выше 50-нед средней', 'btc_mom4': 'BTC вырос за 4 недели',
         'altbtc_up': 'Альты/BTC выше 20-нед средней (доминация BTC падает)', 'altbtc_mom10': 'Альты/BTC выросли за 10 недель',
         'coin_ma20': 'Монета выше своей 20-нед средней', 'coin_ma50': 'Монета выше своей 50-нед средней', 'coin_vs_btc10': 'Монета сильнее BTC за 10 недель'}
for grp, gf in (('Альты (7)', X.sym.isin(ALTS)), ('Все 9', X.sym.notna())):
    for side, snm in (('bull', 'ВОСХОДЯЩИЕ ножки (лой → хай): хай раньше лоя'), ('bear', 'НИСХОДЯЩИЕ ножки (хай → лой): лой раньше хая')):
        x = X[gf & (X.side == side)]
        print(f'\n######## {grp} · {snm} · после подтверждения · n={len(x)} · база {100*x.cont.mean():.0f}%')
        for k, nm in NAMES.items():
            y = x.dropna(subset=[k]); a, b = y[y[k] == True], y[y[k] == False]
            if len(a) < 10 or len(b) < 10: continue
            p1, p0 = a.cont.mean(), b.cont.mean(); se = np.sqrt(p1 * (1 - p1) / len(a) + p0 * (1 - p0) / len(b))
            # стабильность: в скольких годах «да» лучше «нет»
            yy = y.assign(yr=y.t.dt.year).groupby(['yr', k]).cont.mean().unstack()
            stab = f'{int((yy[True] > yy[False]).sum())}/{int(yy.dropna().shape[0])}' if True in yy and False in yy else '—'
            print(f'  {nm:55s} да: {100*p1:3.0f}% (n={len(a):3d}) | нет: {100*p0:3.0f}% (n={len(b):3d}) | разница {100*(p1-p0):+4.0f} п.п. = {(p1-p0)/se:+.1f} ст.ош. | лет, где «да» лучше: {stab}')
X.to_csv(sys.argv[2].replace('retrace_W.csv', 'phase_legs.csv'), index=False)
