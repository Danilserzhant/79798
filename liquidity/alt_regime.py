"""Оценка фазы риска для альтов (0–4) и сила альтов дальше. python alt_regime.py <daily.pkl> <out_txt>
Условия на закрытие недели: BTC вырос за 12 недель; funding BTC за неделю выше медианы за прошлые 52 недели;
общий объём (4 нед) выше среднего за 26 недель; больше половины 7 альтов выше своей 20-нед средней."""
import sys, numpy as np, pandas as pd
D = pd.read_pickle(sys.argv[1])
ALTS = ['SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'LTCUSDT', 'LINKUSDT']
wk = lambda i: i - pd.to_timedelta(i.dayofweek, unit='D')
W = D['close'].groupby(wk(D['close'].index)).last().iloc[:-1]
Q = D['qv'].groupby(wk(D['qv'].index)).sum().reindex(W.index); FU = D['funding'].groupby(wk(D['funding'].index)).sum().reindex(W.index)
R = np.log(W).diff(); alt = R[ALTS].mean(axis=1); btc = R.BTCUSDT
fb = FU.BTCUSDT
c1 = btc.rolling(12).sum() > 0
c2 = fb > fb.rolling(52, min_periods=26).median().shift(1)
tv = Q.sum(axis=1); c3 = tv.rolling(4).mean() > tv.rolling(26).mean()
c4 = (W[ALTS] > W[ALTS].rolling(20).mean()).mean(axis=1) > .5
score = (c1.astype(int) + c2.astype(int) + c3.astype(int) + c4.astype(int)).where(btc.rolling(26).count() >= 26)
f1, f4, f4r = alt.shift(-1), alt.rolling(4).sum().shift(-4), (alt - btc).rolling(4).sum().shift(-4)
f4btc = btc.rolling(4).sum().shift(-4)
half = W.index[len(W) // 2]
out = []
P = lambda v: f'{100*v:+6.1f}%'
out.append('Оценка  недель | альты след. 1 нед | альты след. 4 нед | альты−BTC 4 нед | BTC 4 нед | альты 4 нед в плюсе | 4 нед: 1-я пол. / 2-я пол.')
for sc in range(5):
    m = score == sc
    a1, a4, ar, b4 = f1[m].mean(), f4[m].mean(), f4r[m].mean(), f4btc[m].mean()
    pos = (f4[m] > 0).mean(); h1 = f4[m & (W.index < half)].mean(); h2 = f4[m & (W.index >= half)].mean()
    out.append(f'   {sc}    {int(m.sum()):4d}  |      {P(a1)}       |      {P(a4)}       |    {P(ar)}     | {P(b4)} |        {100*pos:3.0f}%        | {P(h1)} / {P(h2)}')
cur = score.dropna().iloc[-1]
out.append(f'\nСейчас (неделя {score.dropna().index[-1].date()}): оценка {int(cur)} из 4 — BTC за 12 нед {"растёт" if c1.iloc[-1] else "падает"}, funding BTC {"выше" if c2.iloc[-1] else "ниже"} медианы, '
           f'объём {"выше" if c3.iloc[-1] else "ниже"} среднего, альтов выше 20-нед средней {100*(W[ALTS] > W[ALTS].rolling(20).mean()).mean(axis=1).iloc[-1]:.0f}%')
print('\n'.join(out)); open(sys.argv[2], 'w').write('\n'.join(out) + '\n')
