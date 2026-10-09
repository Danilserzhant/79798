"""Какие метрики предсказывают силу альтов. python alt_strength.py <daily.pkl> <out_dir>
daily.pkl: dict(close, qv, funding) — дневные ряды 9 монет (Binance USDT-M perp).
1) Время: индекс 7 альтов (равные веса). Цель — доходность индекса в следующие 1 и 4 недели, в USD и относительно BTC.
   Метрика -> скользящий процентиль за прошлые 52 недели (без заглядывания вперёд): высоко (> 0.67) против низко (< 0.33);
   для бинарных — да/нет. t по Ньюи–Уэсту (лаг 3 для 4 недель). Устойчивость: 1-я и 2-я половины периода.
2) Поперечный срез: каждую неделю 8 альтов (7 + ETH) ранжируются по метрике; доходность следующей недели
   у 3 лучших минус 3 худших (в USD), средняя, t, доля плюсовых недель, по половинам."""
import sys, os, numpy as np, pandas as pd
D = pd.read_pickle(sys.argv[1]); OUT = sys.argv[2]; os.makedirs(OUT, exist_ok=True)
ALTS = ['SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'LTCUSDT', 'LINKUSDT']; X8 = ALTS + ['ETHUSDT']
cl, qv, fu = D['close'], D['qv'], D['funding']
wk = lambda i: i - pd.to_timedelta(i.dayofweek, unit='D')
W = cl.groupby(wk(cl.index)).last(); Q = qv.groupby(wk(qv.index)).sum(); FU = fu.groupby(wk(fu.index)).sum()   # funding за неделю
W = W.iloc[:-1]; Q = Q.reindex(W.index); FU = FU.reindex(W.index)                                                # последняя неделя неполная
R = np.log(W).diff()
alt = R[ALTS].mean(axis=1)                                 # индекс альтов (лог-доходность за неделю)
btc = R.BTCUSDT
fwd1 = alt.shift(-1); fwd1r = (alt - btc).shift(-1)
fwd4 = alt.rolling(4).sum().shift(-4); fwd4r = (alt - btc).rolling(4).sum().shift(-4)
dvol = np.log(cl).diff()
bvol = dvol.BTCUSDT.rolling(28).std().reindex(W.index, method='ffill')
altidx = (alt - btc).cumsum()                              # альты/BTC
M = pd.DataFrame(index=W.index)
M['BTC: рост за 1 неделю'] = btc
M['BTC: рост за 4 недели'] = btc.rolling(4).sum()
M['BTC: рост за 12 недель'] = btc.rolling(12).sum()
M['BTC выше 20-нед средней'] = (W.BTCUSDT > W.BTCUSDT.rolling(20).mean()).astype(float)
M['BTC: волатильность 4 недели'] = bvol
M['ETH/BTC: рост за 4 недели'] = (R.ETHUSDT - btc).rolling(4).sum()
M['Альты/BTC: рост за 4 недели (доминация падает)'] = altidx.diff(4)
M['Альты/BTC: рост за 12 недель'] = altidx.diff(12)
M['Альты: рост за 4 недели'] = alt.rolling(4).sum()
M['Ширина: доля альтов выше 20-нед средней'] = (W[ALTS] > W[ALTS].rolling(20).mean()).mean(axis=1)
M['Объём альтов / объём BTC (к среднему за 26 нед)'] = (Q[ALTS].sum(axis=1) / Q.BTCUSDT) / (Q[ALTS].sum(axis=1) / Q.BTCUSDT).rolling(26).mean()
M['Общий объём (4 нед к 26 нед)'] = Q[X8 + ['BTCUSDT']].sum(axis=1).rolling(4).mean() / Q[X8 + ['BTCUSDT']].sum(axis=1).rolling(26).mean()
M['Funding альтов (средний за неделю)'] = FU[ALTS].mean(axis=1)
M['Funding BTC'] = FU.BTCUSDT
M['Funding альтов минус BTC'] = FU[ALTS].mean(axis=1) - FU.BTCUSDT
BIN = {'BTC выше 20-нед средней'}
def nw_t(x, lag):
    x = x.dropna(); n = len(x); u = x - x.mean()
    g0 = (u * u).sum() / n; s = g0 + 2 * sum((1 - k / (lag + 1)) * (u[k:].values * u[:-k].values).sum() / n for k in range(1, lag + 1))
    return x.mean() / np.sqrt(s / n) if s > 0 else np.nan
def rank52(x): return x.rolling(52, min_periods=26).apply(lambda a: (a[:-1] < a[-1]).mean() if len(a) > 1 else np.nan, raw=True)
half = W.index[len(W) // 2]
lines = []
P = lambda v: f'{100*v:+5.1f}%'
for nm in M.columns:
    x = M[nm]
    if nm in BIN: hi, lo = x == 1, x == 0
    else:
        r = rank52(x); hi, lo = r > 2 / 3, r < 1 / 3
    res = []
    for tgt, tn, lag in ((fwd1, 'альты 1 нед', 0), (fwd1r, 'альты−BTC 1 нед', 0), (fwd4, 'альты 4 нед', 3), (fwd4r, 'альты−BTC 4 нед', 3)):
        d = pd.Series(np.where(hi, 1, np.where(lo, -1, np.nan)), index=W.index)
        a, b = tgt[d == 1], tgt[d == -1]
        diff = a.mean() - b.mean()
        # t разности: регрессия цели на индикатор (+1/−1) с NW
        z = (tgt * d).dropna() / 2
        t = nw_t(pd.concat([a - b.mean(), -(b - a.mean())]), lag) if lag == 0 else nw_t((tgt - tgt.mean()) * d, lag) * 1
        if lag == 0:
            se = np.sqrt(a.var() / a.count() + b.var() / b.count()); t = diff / se
        h1 = a[a.index < half].mean() - b[b.index < half].mean(); h2 = a[a.index >= half].mean() - b[b.index >= half].mean()
        res.append((tn, a.mean(), b.mean(), diff, t, h1, h2, a.count(), b.count()))
    lines.append((nm, res))
with open(f'{OUT}/alt_strength_time.txt', 'w') as f:
    hdr = f'Период {W.index[0].date()} — {W.index[-1].date()}, недель {len(W)}; половины: до {half.date()} и после'
    print(hdr); f.write(hdr + '\n')
    for nm, res in lines:
        s = f'\n{nm}'; print(s); f.write(s + '\n')
        for tn, a, b, diff, t, h1, h2, na, nb in res:
            flag = '  ◀' if abs(t) >= 2 and np.sign(h1) == np.sign(h2) else ''
            s = f'   {tn:16s} высоко {P(a)} (n={na:3d}) | низко {P(b)} (n={nb:3d}) | разница {P(diff)}, t={t:+.1f} | 1-я пол. {P(h1)}, 2-я пол. {P(h2)}{flag}'
            print(s); f.write(s + '\n')
# 2) поперечный срез
RX = R[X8]; FX = FU[X8]; QX = Q[X8]
CS = {'Импульс 4 недели': RX.rolling(4).sum(), 'Импульс 12 недель': RX.rolling(12).sum(), 'Импульс 1 неделя (разворот?)': RX,
      'Сила к BTC за 4 недели': RX.rolling(4).sum().sub(btc.rolling(4).sum(), axis=0),
      'Funding за неделю': FX, 'Изменение funding (неделя к 4 нед)': FX - FX.rolling(4).mean(),
      'Рост объёма (4 нед к 26 нед)': QX.rolling(4).mean() / QX.rolling(26).mean(),
      'Волатильность 4 недели': RX.rolling(4).std()}
nxt = RX.shift(-1)
with open(f'{OUT}/alt_strength_cross.txt', 'w') as f:
    s = '\n==== Какой альт сильнее других: 3 лучших по метрике минус 3 худших, доходность следующей недели ===='; print(s); f.write(s + '\n')
    for nm, x in CS.items():
        rk = x.rank(axis=1); n = x.notna().sum(axis=1)
        top = nxt.where(rk.gt(n - 3, axis=0)).mean(axis=1); bot = nxt.where(rk.le(3, axis=0)).mean(axis=1)
        sp = (top - bot)[n >= 6].dropna()
        t = sp.mean() / (sp.std() / np.sqrt(len(sp)))
        h1, h2 = sp[sp.index < half].mean(), sp[sp.index >= half].mean()
        flag = '  ◀' if abs(t) >= 2 and np.sign(h1) == np.sign(h2) else ''
        s = f'   {nm:38s} разница в неделю {P(sp.mean())}, t={t:+.1f}, плюсовых недель {100*(sp>0).mean():.0f}% | 1-я пол. {P(h1)}, 2-я пол. {P(h2)} | недель {len(sp)}{flag}'
        print(s); f.write(s + '\n')
