"""Сводка week_early против контроля. python week_early_sum.py <real.csv> <s1,s2,s3> <out_txt>"""
import sys, numpy as np, pandas as pd
R = pd.read_csv(sys.argv[1], parse_dates=['t']); Ss = [pd.read_csv(f, parse_dates=['t']) for f in sys.argv[2].split(',')]; OUT = sys.argv[3]
B = ['week_bull', 'prev_bull', 'weekend_up', 'weekend_small', 'rest_up', 'mon_up', 'mon_took_PH', 'mon_took_PL', 'tue_up', 'tue_broke_mh', 'tue_broke_ml',
     'tue_close_above_mh', 'tue_close_below_ml', 'above_open', 'took_PH', 'took_PL']
for d in [R] + Ss:
    for c in B:
        if c in d: d[c] = d[c].map({True: 1.0, False: 0.0, 'True': 1.0, 'False': 0.0})
MAJ = ['BTCUSDT', 'ETHUSDT']
half = R.t.sort_values().iloc[len(R) // 2]
F = {'mon': [
        ('пн бычий (закрылся выше открытия недели)', lambda d: d.mon_up == 1), ('пн медвежий', lambda d: d.mon_up == 0),
        ('пн большой (диапазон > 1,3 ATR)', lambda d: d.mon_range > 1.3), ('пн маленький (< 0,6 ATR)', lambda d: d.mon_range < .6),
        ('пн снял хай прошлой недели', lambda d: d.mon_took_PH == 1), ('пн снял лой прошлой недели', lambda d: d.mon_took_PL == 1),
        ('пн снял хай прошлой недели и закрылся НИЖЕ него', lambda d: (d.mon_took_PH == 1) & (d.mon_close_pos < .5)),
        ('пн снял лой прошлой недели и закрылся в верхней половине дня', lambda d: (d.mon_took_PL == 1) & (d.mon_close_pos > .5)),
        ('пн закрылся у хая дня (верхние 20%)', lambda d: d.mon_close_pos > .8), ('пн закрылся у лоя дня (нижние 20%)', lambda d: d.mon_close_pos < .2),
        ('неделя открылась в верхней трети прошлой', lambda d: d.open_pos > 2 / 3), ('неделя открылась в нижней трети прошлой', lambda d: d.open_pos < 1 / 3),
        ('открылась выше хая прошлой недели', lambda d: d.open_pos > 1), ('открылась ниже лоя прошлой недели', lambda d: d.open_pos < 0),
        ('выходные росли (вс к пт)', lambda d: d.weekend_up == 1), ('выходные падали', lambda d: d.weekend_up == 0),
        ('выходные узкие (< 0,6 ATR)', lambda d: d.weekend_small == 1),
        ('прошлая неделя бычья', lambda d: d.prev_bull == 1), ('прошлая неделя медвежья', lambda d: d.prev_bull == 0)] +
       [(f'прошлая неделя: {st}', lambda d, st=st: d.prev_state == st) for st in ('принятие выше', 'отказ снизу', 'внутри', 'обе сняты', 'отказ сверху', 'принятие ниже')],
     'tue': [
        ('вт пробил хай пн', lambda d: d.tue_broke_mh == 1), ('вт пробил лой пн', lambda d: d.tue_broke_ml == 1),
        ('вт — инсайд пн (не пробил ни хай, ни лой)', lambda d: (d.tue_broke_mh == 0) & (d.tue_broke_ml == 0)),
        ('вт пробил хай пн и закрылся выше него', lambda d: d.tue_close_above_mh == 1),
        ('вт пробил лой пн и закрылся ниже него', lambda d: d.tue_close_below_ml == 1),
        ('вт пробил хай пн, но закрылся обратно ниже (ложный вынос вверх)', lambda d: (d.tue_broke_mh == 1) & (d.tue_close_above_mh == 0) & (d.tue_broke_ml == 0)),
        ('вт пробил лой пн, но закрылся обратно выше (ложный вынос вниз)', lambda d: (d.tue_broke_ml == 1) & (d.tue_close_below_ml == 0) & (d.tue_broke_mh == 0)),
        ('пн и вт оба бычьи', lambda d: (d.mon_up == 1) & (d.tue_up == 1)), ('пн и вт оба медвежьи', lambda d: (d.mon_up == 0) & (d.tue_up == 0)),
        ('пн бычий, вт медвежий', lambda d: (d.mon_up == 1) & (d.tue_up == 0)), ('пн медвежий, вт бычий', lambda d: (d.mon_up == 0) & (d.tue_up == 1)),
        ('к концу вт выше открытия недели', lambda d: d.above_open == 1), ('к концу вт ниже открытия недели', lambda d: d.above_open == 0),
        ('пн–вт сняли хай прошлой недели, лой — нет', lambda d: (d.took_PH == 1) & (d.took_PL == 0)),
        ('пн–вт сняли лой прошлой недели, хай — нет', lambda d: (d.took_PL == 1) & (d.took_PH == 0)),
        ('пн–вт не сняли ни хай, ни лой прошлой недели', lambda d: (d.took_PL == 0) & (d.took_PH == 0)),
        ('сняли лой прош. недели, к концу вт выше открытия', lambda d: (d.took_PL == 1) & (d.above_open == 1)),
        ('сняли хай прош. недели, к концу вт ниже открытия', lambda d: (d.took_PH == 1) & (d.above_open == 0))]}
T = [('rest_up', 'до конца недели вверх'), ('exp_up', 'первым пробит ХАЙ недели-до-сейчас'), ('atr_up', '+1 ATR раньше −1 ATR')]
pc = lambda v: f'{100*v:3.0f}%' if v == v else '  — '
L = []
for dp, dn in (('mon', 'РЕШЕНИЕ НА ЗАКРЫТИИ ПОНЕДЕЛЬНИКА'), ('tue', 'РЕШЕНИЕ НА ЗАКРЫТИИ ВТОРНИКА')):
    x0 = R[R.dp == dp]; c0 = [s[s.dp == dp] for s in Ss]
    L.append(f'\n################ {dn} · 9 монет · недель {len(x0)} · база: ' + ' | '.join(f'{tn} {pc(x0[t].mean())}' for t, tn in T))
    for nm, f in F[dp]:
        x = x0[f(x0)]
        if len(x) < 40: continue
        parts = []; flags = 0
        for t, tn in T:
            v = x[t].dropna(); q = np.mean([c[f(c)][t].dropna().mean() for c in c0]); se = np.sqrt(max(q * (1 - q), .01) / len(v)); z = (v.mean() - q) / se
            mj = x[x.sym.isin(MAJ)][t].mean(); al = x[~x.sym.isin(MAJ)][t].mean()
            h1, h2 = x[x.t < half][t].mean(), x[x.t >= half][t].mean()
            ok = abs(z) >= 2.5 and (h1 - q) * (h2 - q) > 0 and (mj - q) * (al - q) > 0
            flags += ok
            parts.append(f'{pc(v.mean())} (к {pc(q)}, {z:+.1f}{"★" if ok else ""})')
        L.append(f'  {nm:62s} n={len(x):4d} | ' + ' | '.join(parts))
    L.append('  (порядок колонок: ' + ' | '.join(tn for _, tn in T) + '; к — контроль; ★ — |z| ≥ 2,5, одинаково в обеих половинах и на BTC+ETH и альтах)')
txt = '\n'.join(L); print(txt); open(OUT, 'w').write(txt + '\n')
