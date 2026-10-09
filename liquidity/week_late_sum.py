"""Сводка week_late против контроля. python week_late_sum.py <prefix_real> <prefix_s1,...> <out_txt>"""
import sys, numpy as np, pandas as pd
PR, PS, OUT = sys.argv[1], sys.argv[2].split(','), sys.argv[3]
def load(p):
    a, b = pd.read_csv(f'{p}_days.csv', parse_dates=['t']), pd.read_csv(f'{p}_weeks.csv', parse_dates=['t'])
    for d in (a, b):
        for c in d.columns:
            if d[c].dtype == bool: d[c] = d[c].astype(float)
            elif d[c].dtype == object and set(d[c].dropna().unique()) <= {'True', 'False'}: d[c] = d[c].map({'True': 1.0, 'False': 0.0})
    return a, b
(RD, RW), SS = load(PR), [load(p) for p in PS]
MAJ = ['BTCUSDT', 'ETHUSDT']; N = ['пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс']
pc = lambda v: f'{100*v:3.0f}%' if v == v else ' — '
half = RW.t.sort_values().iloc[len(RW) // 2]
L = ['=== 1. Профиль дней недели (9 монет; в скобках контроль — дни в случайном порядке)',
     '  день | диапазон, ATR | пробил хай вчера | пробил лой вчера | инсайд | бычий']
for k in range(7):
    x = RD[RD.dow == k]; cs = [s[0][s[0].dow == k] for s in SS]
    L.append(f'  {N[k]}   |  {x.rng.mean():.2f} ({np.mean([c.rng.mean() for c in cs]):.2f})  |   {pc(x.bh.mean())} ({pc(np.mean([c.bh.mean() for c in cs]))})    |   {pc(x.bl.mean())} ({pc(np.mean([c.bl.mean() for c in cs]))})    | {pc(x.inside.mean())} ({pc(np.mean([c.inside.mean() for c in cs]))}) | {pc(x.up.mean())} ({pc(np.mean([c.up.mean() for c in cs]))})')
def block(title, x0, cs0, cases, targets):
    L.append(f'\n=== {title}')
    for nm, f in cases:
        x = f(x0); cs = [f(c) for c in cs0]
        if len(x) < 40: continue
        parts = []
        for t, tn in targets:
            v = x[t].dropna(); q = np.mean([c[t].dropna().mean() for c in cs]); se = np.sqrt(max(q * (1 - q), .01) / max(1, len(v)))
            z = (v.mean() - q) / se
            h1, h2 = x[x.t < half][t].mean(), x[x.t >= half][t].mean(); mj, al = x[x.sym.isin(MAJ)][t].mean(), x[~x.sym.isin(MAJ)][t].mean()
            star = '★' if abs(z) >= 2.5 and (h1 - q) * (h2 - q) > 0 and (mj - q) * (al - q) > 0 else ''
            parts.append(f'{tn} {pc(v.mean())} ({pc(q)}{star})')
        L.append(f'  {nm:52s} n={len(x):4d} ({pc(len(x)/len(x0))}) | ' + ' | '.join(parts))
for pre, dn, rn in (('thu', 'ЧЕТВЕРГ', 'пн–ср'), ('fri', 'ПЯТНИЦА', 'пн–чт')):
    cases = [(f'{dn.lower()} внутри диапазона {rn}', lambda d, p=pre: d[(d[f'{p}_bh'] == 0) & (d[f'{p}_bl'] == 0)]),
             (f'пробил хай {rn} и закрылся ВЫШЕ', lambda d, p=pre: d[(d[f'{p}_acc_up'] == 1)]),
             (f'пробил хай {rn}, закрылся ОБРАТНО внутри', lambda d, p=pre: d[(d[f'{p}_bh'] == 1) & (d[f'{p}_acc_up'] == 0) & (d[f'{p}_bl'] == 0)]),
             (f'пробил лой {rn} и закрылся НИЖЕ', lambda d, p=pre: d[(d[f'{p}_acc_dn'] == 1)]),
             (f'пробил лой {rn}, закрылся ОБРАТНО внутри', lambda d, p=pre: d[(d[f'{p}_bl'] == 1) & (d[f'{p}_acc_dn'] == 0) & (d[f'{p}_bh'] == 0)]),
             (f'закрылся в верхней трети {rn}', lambda d, p=pre: d[(d[f'{p}_pos'] > 2 / 3) & (d[f'{p}_pos'] <= 1)]),
             (f'закрылся в нижней трети {rn}', lambda d, p=pre: d[(d[f'{p}_pos'] < 1 / 3) & (d[f'{p}_pos'] >= 0)]),
             (f'к закрытию выше открытия недели', lambda d, p=pre: d[d[f'{p}_above_open'] == 1]),
             (f'к закрытию ниже открытия недели', lambda d, p=pre: d[d[f'{p}_above_open'] == 0])]
    tg = [(f'{pre}_rest_up', 'до конца нед. вверх'), (f'{pre}_atr_up', '+1ATR раньше'), (f'{pre}_hit_H', 'новый хай'), (f'{pre}_hit_L', 'новый лой')]
    block(f'{"2" if pre=="thu" else "3"}. {dn}: от его закрытия до конца недели (новый хай/лой = за пределами диапазона пн–{"чт" if pre=="thu" else "пт"})', RW, [s[1] for s in SS], cases, tg)
cases = [('выходные сняли хай пт, вс закрылось внутри диапазона пт', lambda d: d[(d.we_bh == 1) & (d.we_bl == 0) & (d.we_close_in_fri == 1)]),
         ('выходные сняли лой пт, вс закрылось внутри диапазона пт', lambda d: d[(d.we_bl == 1) & (d.we_bh == 0) & (d.we_close_in_fri == 1)]),
         ('выходные сняли хай пт и закрылись выше', lambda d: d[(d.we_bh == 1) & (d.we_bl == 0) & (d.we_close_in_fri == 0)]),
         ('выходные сняли лой пт и закрылись ниже', lambda d: d[(d.we_bl == 1) & (d.we_bh == 0) & (d.we_close_in_fri == 0)]),
         ('выходные внутри пятницы', lambda d: d[(d.we_bl == 0) & (d.we_bh == 0)]),
         ('выходные росли (вс к пт)', lambda d: d[d.we_up == 1]), ('выходные падали', lambda d: d[d.we_up == 0]),
         ('выходные узкие (< 0,5 ATR)', lambda d: d[d.we_rng < .5]), ('пятница большая (> 1,5 ATR)', lambda d: d[d.fri_rng > 1.5])]
tg = [('nmon_up', 'след. пн бычий'), ('nmon_hit_fri_close', 'пн вернулся к закрытию пт'), ('nmon_bh_we', 'пн пробил хай выходных'), ('nmon_bl_we', 'пн пробил лой выходных'), ('nweek_up', 'след. неделя бычья')]
block('4. ВЫХОДНЫЕ -> следующий понедельник и неделя', RW, [s[1] for s in SS], cases, tg)
L.append('\n=== 5. В какой день ставится хай и лой недели (все недели)')
for col, nm in (('hi_day', 'хай недели'), ('lo_day', 'лой недели')):
    dr = RW[col].value_counts(normalize=True).reindex(range(7)).fillna(0); dc = np.mean([s[1][col].value_counts(normalize=True).reindex(range(7)).fillna(0).values for s in SS], axis=0)
    L.append(f'  {nm:10s}: ' + ' | '.join(f'{N[k]} {pc(dr[k])} ({pc(dc[k])})' for k in range(7)))
L.append('  ★ — |z| ≥ 2,5 против контроля, одинаково в обеих половинах периода и на BTC+ETH и альтах')
txt = '\n'.join(L); print(txt); open(OUT, 'w').write(txt + '\n')
