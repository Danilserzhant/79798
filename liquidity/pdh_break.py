"""Сделка на пробой PDH/PDL. python3.13 pdh_break.py <real_ev.csv> <syn_ev1,...> <out_txt>
Вход на снятии уровня (стоп-ордер на PDH/PDL), стоп — середина вчерашнего дня, цель — столько же за уровнем (1:1).
Итог в R = (выигрыш ? +1 : −1) − комиссия 0,1% в R. Фильтры — только известные в момент входа."""
import sys, numpy as np, pandas as pd
R = pd.read_csv(sys.argv[1], parse_dates=['t']); Ss = [pd.read_csv(f, parse_dates=['t']) for f in sys.argv[2].split(',')]; OUT = sys.argv[3]
for d in [R] + Ss:
    for c in ('other_first', 'above_sma', 'prev_inside'):
        if d[c].dtype == object: d[c] = d[c].map({True: 1.0, False: 0.0, 'True': 1.0, 'False': 0.0})
        else: d[c] = d[c].astype(float)
    d['R'] = np.where(d.rev_mid == 0, 1.0, np.where(d.rev_mid == 1, -1.0, np.nan)) - d.brk_cost
MAJ = ['BTCUSDT', 'ETHUSDT']; half = R.t.sort_values().iloc[len(R) // 2]
narrow = lambda d: d.rng_atr < .7
F = [('все пробои', lambda d: d),
     ('пробой PDH', lambda d: d[d.side == 'PDH']), ('пробой PDL', lambda d: d[d.side == 'PDL']),
     ('вчера узкий (< 0,7 ATR)', lambda d: d[narrow(d)]), ('вчера узкий (< 0,5 ATR)', lambda d: d[d.rng_atr < .5]),
     ('вчера инсайд-день', lambda d: d[d.prev_inside == 1]), ('вчера «внутри» (не снял ни одной стороны позавчера)', lambda d: d[d.prev_state == 'внутри']),
     ('сессия Лондон', lambda d: d[d.sess == 'Лондон']), ('сессия NY утро', lambda d: d[d.sess == 'NY утро']), ('сессия Азия', lambda d: d[d.sess == 'Азия']),
     ('по тренду (PDH над 20-дн. средней / PDL под)', lambda d: d[d.above_sma == 1]),
     ('уровень снят первым за день', lambda d: d[d.other_first == 0]),
     ('узкий вчера + Лондон/NY утро', lambda d: d[narrow(d) & d.sess.isin(['Лондон', 'NY утро'])]),
     ('узкий вчера + по тренду', lambda d: d[narrow(d) & (d.above_sma == 1)]),
     ('узкий вчера + снят первым', lambda d: d[narrow(d) & (d.other_first == 0)]),
     ('узкий вчера + по тренду + Лондон/NY утро', lambda d: d[narrow(d) & (d.above_sma == 1) & d.sess.isin(['Лондон', 'NY утро'])]),
     ('вчера «внутри» + узкий', lambda d: d[narrow(d) & (d.prev_state == 'внутри')])]
L = ['Пробой: вход на уровне, стоп — середина вчерашнего дня, цель 1:1; комиссия 0,1% вычтена. В скобках — контроль.']
for nm, f in F:
    x = f(R).dropna(subset=['R']); cs = [f(s).dropna(subset=['R']) for s in Ss]
    q = np.mean([c.R.mean() for c in cs]); w = (x.R > 0).mean(); wc = np.mean([(c.R > 0).mean() for c in cs])
    se = np.sqrt(x.R.var() / len(x) + np.mean([c.R.var() / len(c) for c in cs]) / len(cs))
    L.append(f'  {nm:52s} n={len(x):5d} | цель раньше стопа {100*w:3.0f}% ({100*wc:3.0f}%) | комиссия {x.brk_cost.median():.2f}R | итог {x.R.mean():+.3f}R ({q:+.3f}) '
             f'разница {(x.R.mean()-q)/se:+.1f} ст.ош. | половины {x[x.t<half].R.mean():+.2f}/{x[x.t>=half].R.mean():+.2f} | BTC+ETH {x[x.sym.isin(MAJ)].R.mean():+.2f}, альты {x[~x.sym.isin(MAJ)].R.mean():+.2f}')
txt = '\n'.join(L); print(txt); open(OUT, 'w').write(txt + '\n')
