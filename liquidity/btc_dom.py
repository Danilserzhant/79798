"""Доминация BTC (CoinMarketCap, дневная) и сила альтов. python btc_dom.py <daily.pkl> <cmc_global.pkl> <out_txt>
1) Одновременно: изменение BTC.D за неделю vs доходность индекса 7 альтов и альтов к BTC в ту же неделю; 4 сочетания BTC.D × BTC.
2) Наперёд: изменение BTC.D за прошлые 1/4/12 недель -> альты в следующие 1/4 недели (высоко/низко по процентилю за прошлый год)."""
import sys, numpy as np, pandas as pd
D = pd.read_pickle(sys.argv[1]); G = pd.read_pickle(sys.argv[2]); OUT = sys.argv[3]
G = G[G.btcd > 20]                                        # в начале 2020 у CMC есть дни с доминацией ≈ 0 — сбой данных
ALTS = ['SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'LTCUSDT', 'LINKUSDT']
wk = lambda i: i - pd.to_timedelta(i.dayofweek, unit='D')
W = D['close'].groupby(wk(D['close'].index)).last().iloc[:-1]
R = np.log(W).diff(); alt = R[ALTS].mean(axis=1); btc = R.BTCUSDT
dom = G.btcd.groupby(wk(G.index)).last().reindex(W.index)
altcap = np.log(G.alt.groupby(wk(G.index)).last().reindex(W.index)).diff()
dd = dom.diff()
P = lambda v: f'{100*v:+6.1f}%'
L = []
L.append(f'Недель {int(dd.notna().sum())}, {W.index[1].date()} — {W.index[-1].date()}. BTC.D сейчас {dom.dropna().iloc[-1]:.1f}%')
L.append('\n=== 1. Та же неделя: как связаны BTC.D и альты ===')
L.append(f'Корреляция изменения BTC.D с доходностью альтов: {dd.corr(alt):+.2f}; с альтами к BTC: {dd.corr(alt - btc):+.2f}; с капитализацией альтов (CMC): {dd.corr(altcap):+.2f}')
for nm, m in (('BTC.D упала > 0,5 п.п.', dd < -.5), ('BTC.D почти не изменилась', dd.abs() <= .5), ('BTC.D выросла > 0,5 п.п.', dd > .5)):
    L.append(f'  {nm:28s} недель {int(m.sum()):3d} | альты {P(alt[m].mean())} | альты к BTC {P((alt - btc)[m].mean())} | альты росли {100*(alt[m] > 0).mean():3.0f}% недель | обогнали BTC {100*((alt - btc)[m] > 0).mean():3.0f}%')
L.append('  Сочетания (та же неделя):')
for nm, m in (('BTC.D ↓ и BTC ↑', (dd < 0) & (btc > 0)), ('BTC.D ↓ и BTC ↓', (dd < 0) & (btc < 0)), ('BTC.D ↑ и BTC ↑', (dd > 0) & (btc > 0)), ('BTC.D ↑ и BTC ↓', (dd > 0) & (btc < 0))):
    L.append(f'    {nm:18s} недель {int(m.sum()):3d} | альты {P(alt[m].mean())} | BTC {P(btc[m].mean())} | альты росли {100*(alt[m] > 0).mean():3.0f}%')
L.append('\n=== 2. Наперёд: прошлое изменение BTC.D -> альты дальше ===')
def rank52(x): return x.rolling(52, min_periods=26).apply(lambda a: (a[:-1] < a[-1]).mean(), raw=True)
half = W.index[len(W) // 2]
f1, f1r = alt.shift(-1), (alt - btc).shift(-1); f4, f4r = alt.rolling(4).sum().shift(-4), (alt - btc).rolling(4).sum().shift(-4)
for n in (1, 4, 12):
    ch = dom.diff(n); r = rank52(ch); fall, rise = r < 1 / 3, r > 2 / 3
    L.append(f'BTC.D за прошлые {n} нед: ПАДАЛА сильнее обычного (n={int(fall.sum())}) против РОСЛА (n={int(rise.sum())})')
    for tgt, tn in ((f1, 'альты след. 1 нед'), (f1r, 'альты к BTC 1 нед'), (f4, 'альты след. 4 нед'), (f4r, 'альты к BTC 4 нед')):
        a, b = tgt[fall], tgt[rise]; diff = a.mean() - b.mean(); se = np.sqrt(a.var() / a.count() + b.var() / b.count())
        h1 = a[a.index < half].mean() - b[b.index < half].mean(); h2 = a[a.index >= half].mean() - b[b.index >= half].mean()
        L.append(f'   {tn:20s} падала {P(a.mean())} | росла {P(b.mean())} | разница {P(diff)} (t≈{diff/se:+.1f}{", 4-нед окна пересекаются" if "4" in tn else ""}) | 1-я пол. {P(h1)}, 2-я пол. {P(h2)}')
# уровень доминации
L.append('\nУровень BTC.D (не изменение) -> альты к BTC за следующие 4 недели:')
for lo, hi in ((0, 45), (45, 50), (50, 55), (55, 60), (60, 100)):
    m = (dom >= lo) & (dom < hi)
    if m.sum() < 5: continue
    L.append(f'   BTC.D {lo}–{hi}%: недель {int(m.sum()):3d} | альты 4 нед {P(f4[m].mean())} | к BTC {P(f4r[m].mean())}')
print('\n'.join(L)); open(OUT, 'w').write('\n'.join(L) + '\n')
