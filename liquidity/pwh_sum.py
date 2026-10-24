"""Сводка pwh.py против контроля. python3.13 pwh_sum.py <real_prefix> <syn_prefix1,...> <out_txt>"""
import sys, numpy as np, pandas as pd
RP, SP, OUT = sys.argv[1], sys.argv[2].split(','), sys.argv[3]
B = {True: 1.0, False: 0.0, 'True': 1.0, 'False': 0.0}
def load(p):
    w, e = pd.read_csv(f'{p}_weeks.csv', parse_dates=['t']), pd.read_csv(f'{p}_ev.csv', parse_dates=['t'])
    for x in (w, e):
        for c in x.columns:
            if x[c].dtype == bool: x[c] = x[c].astype(float)
            elif x[c].dtype == object and set(x[c].dropna().unique()) <= set(B): x[c] = x[c].map(B)
    e['brk_R'] = np.where(e.rev_mid == 0, 1.0, np.where(e.rev_mid == 1, -1.0, np.nan)) - e.brk_cost
    return w, e
(RW, RE), SS = load(RP), [load(p) for p in SP]
MAJ = ['BTCUSDT', 'ETHUSDT']; pc = lambda v: f'{100*v:3.0f}%' if v == v else ' — '
half = RE.t.sort_values().iloc[len(RE) // 2]
L = ['=== 1. КАК ЧАСТО СНИМАЮТ PWH / PWL (в скобках контроль)']
def wline(nm, f):
    x = f(RW); cs = [f(s[0]) for s in SS]
    both = lambda d: ((d.tH == 1) & (d.tL == 1)).mean(); none = lambda d: ((d.tH == 0) & (d.tL == 0)).mean()
    L.append(f'  {nm:40s} n={len(x):5d} | PWH {pc(x.tH.mean())} ({pc(np.mean([c.tH.mean() for c in cs]))}) | PWL {pc(x.tL.mean())} ({pc(np.mean([c.tL.mean() for c in cs]))}) | '
             f'обе {pc(both(x))} ({pc(np.mean([both(c) for c in cs]))}) | ни одной {pc(none(x))} ({pc(np.mean([none(c) for c in cs]))})')
wline('все недели', lambda d: d)
wline('открытие в верхней половине прошлой', lambda d: d[(d.pos >= .5) & (d.pos <= 1)]); wline('открытие в нижней половине прошлой', lambda d: d[(d.pos < .5) & (d.pos >= 0)])
for st in ('принятие выше', 'отказ сверху', 'внутри', 'обе сняты', 'отказ снизу', 'принятие ниже'): wline(f'прошлая: {st}', lambda d, st=st: d[d.prev_state == st])
L.append('  В какой день недели снимают (первое снятие):')
for col, nm in (('dowH', 'PWH'), ('dowL', 'PWL')):
    vc = RW[col].value_counts(normalize=True); vcc = pd.concat([s[0][col] for s in SS]).value_counts(normalize=True)
    L.append(f'    {nm}: ' + ' | '.join(f'{k} {pc(vc.get(k, 0))} ({pc(vcc.get(k, 0))})' for k in ('пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс')))
L.append('\n=== 2. ПОСЛЕ СНЯТИЯ: разворот к середине прошлой недели (случайно ≈50%) / −0,5 ATR раньше +0,5 ATR / неделя закрылась обратно')
TG = [('rev_mid', 'разворот к середине'), ('rev_atr', '±0,5 нед. ATR против'), ('week_back', 'неделя вернулась')]
def eline(nm, f):
    x = f(RE); cs = [f(s[1]) for s in SS]
    if len(x) < 40: return
    parts = []
    for t, tn in TG:
        v = x[t].dropna(); q = np.mean([c[t].dropna().mean() for c in cs]); se = np.sqrt(max(q * (1 - q), .01) / len(v)); z = (v.mean() - q) / se
        h1, h2 = x[x.t < half][t].mean(), x[x.t >= half][t].mean(); mj, al = x[x.sym.isin(MAJ)][t].mean(), x[~x.sym.isin(MAJ)][t].mean()
        star = '★' if abs(z) >= 2.5 and (h1 - q) * (h2 - q) > 0 and (mj - q) * (al - q) > 0 else ''
        parts.append(f'{tn} {pc(v.mean())} ({pc(q)}, {z:+.1f}{star})')
    L.append(f'  {nm:52s} n={len(x):5d} | ' + ' | '.join(parts))
eline('все снятия', lambda d: d)
for sd in ('PWH', 'PWL'): eline(f'снят {sd}', lambda d, sd=sd: d[d.side == sd])
L.append('  -- день недели снятия')
for sd in ('PWH', 'PWL'):
    for dd, ds in ((['пн'], 'пн'), (['вт'], 'вт'), (['ср'], 'ср'), (['чт', 'пт'], 'чт–пт'), (['сб', 'вс'], 'сб–вс')):
        eline(f'{sd} снят в {ds}', lambda d, sd=sd, dd=dd: d[(d.side == sd) & d.dow.isin(dd)])
L.append('  -- подтверждение возврата')
for sd in ('PWH', 'PWL'):
    eline(f'{sd}: 4h свеча снятия закрылась обратно', lambda d, sd=sd: d[(d.side == sd) & (d.h4_back == 1)])
    eline(f'{sd}: 4h свеча снятия закрылась за уровнем', lambda d, sd=sd: d[(d.side == sd) & (d.h4_back == 0)])
    eline(f'{sd}: день снятия закрылся обратно', lambda d, sd=sd: d[(d.side == sd) & (d.day_back == 1)])
    eline(f'{sd}: день снятия закрылся за уровнем', lambda d, sd=sd: d[(d.side == sd) & (d.day_back == 0)])
L.append('  -- контекст')
for sd in ('PWH', 'PWL'):
    eline(f'{sd} снят вторым (другая сторона уже снята)', lambda d, sd=sd: d[(d.side == sd) & (d.other_first == 1)])
    eline(f'{sd}: прошлая неделя узкая (< 0,7 среднего)', lambda d, sd=sd: d[(d.side == sd) & (d.narrow == 1)])
    eline(f'{sd}: прошлая неделя — инсайд', lambda d, sd=sd: d[(d.side == sd) & (d.prev_inside == 1)])
    eline(f'{sd}: по тренду (выше/ниже 20-нед. средней)', lambda d, sd=sd: d[(d.side == sd) & (d.above_sma == 1)])
    eline(f'{sd}: против тренда', lambda d, sd=sd: d[(d.side == sd) & (d.above_sma == 0)])
    for st in ('принятие выше', 'отказ сверху', 'внутри', 'отказ снизу', 'принятие ниже'):
        eline(f'{sd}: прошлая «{st}»', lambda d, sd=sd, st=st: d[(d.side == sd) & (d.prev_state == st)])
L.append('  -- сочетания')
for sd in ('PWH', 'PWL'):
    eline(f'{sd} снят в пн–вт, день закрылся обратно', lambda d, sd=sd: d[(d.side == sd) & d.dow.isin(['пн', 'вт']) & (d.day_back == 1)])
    eline(f'{sd} снят в пн–вт, день закрылся за уровнем', lambda d, sd=sd: d[(d.side == sd) & d.dow.isin(['пн', 'вт']) & (d.day_back == 0)])
    eline(f'{sd} снят в ср–вс, день закрылся обратно', lambda d, sd=sd: d[(d.side == sd) & ~d.dow.isin(['пн', 'вт']) & (d.day_back == 1)])
L.append('\n=== 3. НАСКОЛЬКО ГЛУБОКО ВЫНОСЯТ УРОВЕНЬ ПЕРЕД РАЗВОРОТОМ К СЕРЕДИНЕ (в долях недельного ATR)')
for sd in ('PWH', 'PWL'):
    x = RE[RE.side == sd].exc_atr.dropna(); xc = pd.concat([s[1][s[1].side == sd].exc_atr.dropna() for s in SS])
    L.append(f'  {sd}: медиана {x.median():.2f} ({xc.median():.2f}) | 75% {x.quantile(.75):.2f} ({xc.quantile(.75):.2f}) | 90% {x.quantile(.9):.2f} ({xc.quantile(.9):.2f}) | n={len(x)}')
L.append('\n=== 4. TURTLE SOUP (закрытие 4h обратно ≤ 2 суток после выноса, стоп за экстремумом выноса) и ПРОБОЙ (вход на уровне, стоп — середина, цель 1:1); комиссия 0,1%')
def tline(nm, f):
    x = f(RE); cs = [f(s[1]) for s in SS]
    xt = x[x.ts == 1]; ct = [c[c.ts == 1] for c in cs]
    if len(x) < 40: return
    parts = []
    for t, tn in (('ts_R_mid', 'TS→середина'), ('ts_R_1', 'TS 1R'), ('ts_R_2', 'TS 2R')):
        v = xt[t].dropna(); q = np.mean([c[t].dropna().mean() for c in ct]); parts.append(f'{tn} {v.mean():+.2f}R ({q:+.2f})')
    v = x.brk_R.dropna(); q = np.mean([c.brk_R.dropna().mean() for c in cs]); se = np.sqrt(v.var() / len(v))
    parts.append(f'ПРОБОЙ {v.mean():+.2f}R ±{2*se:.2f} ({q:+.2f})')
    L.append(f'  {nm:46s} n={len(x):5d} | риск TS {xt.ts_risk_atr.median():.2f} ATR | ' + ' | '.join(parts))
tline('все', lambda d: d)
for sd in ('PWH', 'PWL'): tline(f'{sd}', lambda d, sd=sd: d[d.side == sd])
for sd in ('PWH', 'PWL'):
    tline(f'{sd} снят в пн–вт', lambda d, sd=sd: d[(d.side == sd) & d.dow.isin(['пн', 'вт'])])
    tline(f'{sd} снят в ср–вс', lambda d, sd=sd: d[(d.side == sd) & ~d.dow.isin(['пн', 'вт'])])
    tline(f'{sd}: прошлая узкая', lambda d, sd=sd: d[(d.side == sd) & (d.narrow == 1)])
    tline(f'{sd}: по тренду', lambda d, sd=sd: d[(d.side == sd) & (d.above_sma == 1)])
    tline(f'{sd}: против тренда', lambda d, sd=sd: d[(d.side == sd) & (d.above_sma == 0)])
txt = '\n'.join(L); print(txt); open(OUT, 'w').write(txt + '\n')
