"""Сводка week_types. python week_types_sum.py <real.csv> <s1,s2,s3> <out_txt>"""
import sys, numpy as np, pandas as pd
R = pd.read_csv(sys.argv[1], parse_dates=['t']); Ss = [pd.read_csv(f, parse_dates=['t']) for f in sys.argv[2].split(',')]; OUT = sys.argv[3]
TY = ['бычья трендовая', 'бычий разворот', 'бычья поздняя', 'медвежья трендовая', 'медвежий разворот', 'медвежья поздняя', 'сжатие', 'пила']
FAM = {'бычья трендовая': 'БЫЧЬЯ', 'бычий разворот': 'БЫЧЬЯ', 'бычья поздняя': 'БЫЧЬЯ', 'медвежья трендовая': 'МЕДВЕЖЬЯ', 'медвежий разворот': 'МЕДВЕЖЬЯ',
       'медвежья поздняя': 'МЕДВЕЖЬЯ', 'сжатие': 'СЕРЕДИНА', 'пила': 'СЕРЕДИНА'}
for d in [R] + Ss:
    d['fam'] = d.type.map(FAM)
    for c in ('took_PH', 'took_PL', 'bull', 'prev_inside'): d[c] = d[c].map({True: 1.0, False: 0.0, 'True': 1.0, 'False': 0.0})
N = ['пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс']; pc = lambda v: f'{100*v:3.0f}%' if v == v else ' — '
L = ['=== 1. ТИПЫ НЕДЕЛЬ: частота (контроль), диапазон к среднему, связь с прошлой неделей, путь цены по дням',
     '   путь = где цена на закрытии дня в итоговом диапазоне недели (0% — лой недели, 100% — хай)']
for ty in TY:
    x = R[R.type == ty]; q = np.mean([(s.type == ty).mean() for s in Ss])
    path = ' → '.join(f'{N[k]} {100*x[f"path{k}"].mean():.0f}' for k in range(4))
    ld = x.lo_day.value_counts(normalize=True).reindex(range(7)).fillna(0); hd = x.hi_day.value_counts(normalize=True).reindex(range(7)).fillna(0)
    L.append(f'\n  {ty.upper()}: {pc(len(x)/len(R))} недель (контроль {pc(q)}) · диапазон ×{x.rng_rel.median():.2f} среднего · снят PWH {pc(x.took_PH.mean())}, PWL {pc(x.took_PL.mean())} · прошлая неделя инсайд {pc(x.prev_inside.mean())}')
    L.append(f'     путь: {path} → вс {100*x.cp.mean():.0f}')
    L.append(f'     лой недели: ' + ' '.join(f'{N[k]} {pc(ld[k])}' for k in range(7)) + '  |  хай недели: ' + ' '.join(f'{N[k]} {pc(hd[k])}' for k in range(7)))
# 2. распознавание по дням: семейство
L.append('\n=== 2. КАК УЗНАТЬ НЕДЕЛЮ ПО ДНЯМ: вероятности семейства (БЫЧЬЯ / МЕДВЕЖЬЯ / СЕРЕДИНА) и самого частого типа')
L.append(f'   база: БЫЧЬЯ {pc((R.fam=="БЫЧЬЯ").mean())}, МЕДВЕЖЬЯ {pc((R.fam=="МЕДВЕЖЬЯ").mean())}, СЕРЕДИНА {pc((R.fam=="СЕРЕДИНА").mean())}')
for k in range(4):
    L.append(f'\n--- на закрытии {N[k].upper()} (где цена в диапазоне недели-до-сейчас · что сделал день · прошлая неделя)')
    g = R.groupby([f'pos{k}', f'ext{k}', f'pw{k}'])
    cs = [s.groupby([f'pos{k}', f'ext{k}', f'pw{k}']) for s in Ss]
    rows = []
    for key, x in g:
        if len(x) < 40: continue
        fb, fm, fs = (x.fam == 'БЫЧЬЯ').mean(), (x.fam == 'МЕДВЕЖЬЯ').mean(), (x.fam == 'СЕРЕДИНА').mean()
        qb = np.mean([c.get_group(key).fam.eq('БЫЧЬЯ').mean() if key in c.groups else np.nan for c in cs])
        qm = np.mean([c.get_group(key).fam.eq('МЕДВЕЖЬЯ').mean() if key in c.groups else np.nan for c in cs])
        top = x.type.value_counts(normalize=True)
        rows.append((max(fb, fm, fs), key, len(x), fb, qb, fm, qm, fs, top.index[0], top.iloc[0]))
    rows.sort(key=lambda r: -r[0])
    for _, key, n, fb, qb, fm, qm, fs, tt, tp in rows:
        L.append(f'   {key[0]:8s} · {key[1]:9s} · {key[2]:9s} n={n:4d} | БЫЧЬЯ {pc(fb)} (к {pc(qb)}) · МЕДВЕЖЬЯ {pc(fm)} (к {pc(qm)}) · СЕРЕДИНА {pc(fs)} | чаще всего: {tt} {pc(tp)}')
# 3. точность: обучение на 1-й половине, проверка на 2-й
L.append('\n=== 3. НАСКОЛЬКО РАНО УЗНАЁТСЯ НЕДЕЛЯ: точность (правило по 1-й половине данных, проверка на 2-й)')
def acc(d, k, target):
    d = d.sort_values('t'); h = d.t.iloc[len(d) // 2]; tr, te = d[d.t < h], d[d.t >= h]
    cols = [f'pos{k}', f'ext{k}', f'pw{k}']
    mp = tr.groupby(cols)[target].agg(lambda v: v.value_counts().index[0])
    base = tr[target].value_counts().index[0]
    pred = te.set_index(cols).index.map(lambda key: mp.get(key, base))
    return (pred == te[target].values).mean(), (te[target] == base).mean()
for target, tn in (('fam', 'семейство (3 варианта)'), ('type', 'тип (8 вариантов)')):
    L.append(f'  {tn}:')
    for k in range(4):
        a, b = acc(R, k, target); cs = [acc(s, k, target)[0] for s in Ss]
        L.append(f'    на закрытии {N[k]}: угадано {pc(a)} | контроль {pc(np.mean(cs))} | «всегда самый частый» {pc(b)}')
txt = '\n'.join(L); print(txt); open(OUT, 'w').write(txt + '\n')
