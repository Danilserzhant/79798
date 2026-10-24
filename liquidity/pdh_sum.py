"""Сводка pdh.py против контроля. python3.13 pdh_sum.py <real_prefix> <syn_prefix1,...> <out_txt>"""
import sys, numpy as np, pandas as pd
RP, SP, OUT = sys.argv[1], sys.argv[2].split(','), sys.argv[3]
def load(p):
    d, e = pd.read_csv(f'{p}_days.csv', parse_dates=['t']), pd.read_csv(f'{p}_ev.csv', parse_dates=['t'])
    for x in (d, e):
        for c in x.columns:
            if x[c].dtype == bool: x[c] = x[c].astype(float)
            elif x[c].dtype == object and set(x[c].dropna().unique()) <= {'True', 'False'}: x[c] = x[c].map({'True': 1.0, 'False': 0.0})
    return d, e
(RD, RE), SS = load(RP), [load(p) for p in SP]
MAJ = ['BTCUSDT', 'ETHUSDT']; pc = lambda v: f'{100*v:3.0f}%' if v == v else ' — '
half = RE.t.sort_values().iloc[len(RE) // 2]
L = []
# 1. дни
L.append('=== 1. КАК ЧАСТО СНИМАЮТ PDH / PDL (в скобках контроль)')
def dline(nm, f):
    x = f(RD); cs = [f(s[0]) for s in SS]
    v = lambda d, col: d[col].mean()
    both = lambda d: ((d.tH == 1) & (d.tL == 1)).mean(); none = lambda d: ((d.tH == 0) & (d.tL == 0)).mean()
    L.append(f'  {nm:40s} n={len(x):5d} | PDH {pc(v(x,"tH"))} ({pc(np.mean([v(c,"tH") for c in cs]))}) | PDL {pc(v(x,"tL"))} ({pc(np.mean([v(c,"tL") for c in cs]))}) | '
             f'обе {pc(both(x))} ({pc(np.mean([both(c) for c in cs]))}) | ни одной {pc(none(x))} ({pc(np.mean([none(c) for c in cs]))})')
dline('все дни', lambda d: d)
for nm, a, b in (('открытие выше PDH', 1, 99), ('открытие в верхней половине вчера', .5, 1), ('открытие в нижней половине вчера', 0, .5), ('открытие ниже PDL', -99, 0)):
    dline(nm, lambda d, a=a, b=b: d[(d.pos >= a) & (d.pos < b)])
for st in ('принятие выше', 'отказ сверху', 'внутри', 'обе сняты', 'отказ снизу', 'принятие ниже'):
    dline(f'вчера: {st}', lambda d, st=st: d[d.prev_state == st])
L.append('  Когда снимают (сессия первого снятия, NY-время):')
for col, nm in (('sessH', 'PDH'), ('sessL', 'PDL')):
    vc = RD[col].value_counts(normalize=True); vcc = pd.concat([s[0][col] for s in SS]).value_counts(normalize=True)
    L.append(f'    {nm}: ' + ' | '.join(f'{k} {pc(vc.get(k, 0))} ({pc(vcc.get(k, 0))})' for k in ('Азия', 'Лондон', 'NY утро', 'NY день')))
# следующий день после принятия/отказа
L.append('\n  Сегодня закрылись ЗА уровнем или вернулись → что завтра (первым снимут…)')
def nxt(d):
    d = d.sort_values(['sym', 't']).copy(); d['n_first'] = d.groupby('sym')['first'].shift(-1); d['n_tH'] = d.groupby('sym').tH.shift(-1); d['n_tL'] = d.groupby('sym').tL.shift(-1)
    d['gap'] = d.groupby('sym').t.shift(-1) - d.t; return d[d.gap == pd.Timedelta(days=1)]
RN = nxt(RD); SN = [nxt(s[0]) for s in SS]
for nm, f in (('сняли PDH и закрылись выше (принятие)', lambda d: d[(d.tH == 1) & (d.close_pos > 1)]),
              ('сняли PDH и закрылись обратно ниже (отказ)', lambda d: d[(d.tH == 1) & (d.tL == 0) & (d.close_pos <= 1)]),
              ('сняли PDL и закрылись ниже (принятие)', lambda d: d[(d.tL == 1) & (d.close_pos < 0)]),
              ('сняли PDL и закрылись обратно выше (отказ)', lambda d: d[(d.tL == 1) & (d.tH == 0) & (d.close_pos >= 0)])):
    x = f(RN); cs = [f(c) for c in SN]
    fh = (x.n_first == 'H').mean(); fhc = np.mean([(c.n_first == 'H').mean() for c in cs])
    L.append(f'    {nm:46s} n={len(x):5d} | завтра первым хай сегодняшнего дня {pc(fh)} ({pc(fhc)}) | лой {pc((x.n_first=="L").mean())} ({pc(np.mean([(c.n_first=="L").mean() for c in cs]))})')
# 2. события
L.append('\n=== 2. В МОМЕНТ СНЯТИЯ PDH/PDL: разворот или продолжение (PDL посчитан зеркально)')
L.append('   разворот = раньше середина вчерашнего дня, чем столько же за уровень (случайно ≈50%); ±0,5 ATR = раньше −0,5 ATR от уровня, чем +0,5 ATR; день вернулся = закрытие дня обратно за уровнем')
TG = [('rev_mid', 'разворот к середине'), ('rev_atr', '±0,5 ATR против'), ('day_back', 'день вернулся')]
def eline(nm, f, base=None):
    x = f(RE); cs = [f(s[1]) for s in SS]
    if len(x) < 50: return
    parts = []
    for t, tn in TG:
        v = x[t].dropna(); q = np.mean([c[t].dropna().mean() for c in cs]); se = np.sqrt(max(q * (1 - q), .01) / len(v)); z = (v.mean() - q) / se
        h1, h2 = x[x.t < half][t].mean(), x[x.t >= half][t].mean(); mj, al = x[x.sym.isin(MAJ)][t].mean(), x[~x.sym.isin(MAJ)][t].mean()
        star = '★' if abs(z) >= 3 and (h1 - q) * (h2 - q) > 0 and (mj - q) * (al - q) > 0 else ''
        parts.append(f'{tn} {pc(v.mean())} ({pc(q)}, {z:+.1f}{star})')
    L.append(f'  {nm:50s} n={len(x):5d} | ' + ' | '.join(parts))
eline('все снятия', lambda d: d)
for sd in ('PDH', 'PDL'): eline(f'снят {sd}', lambda d, sd=sd: d[d.side == sd])
L.append('  -- по сессии снятия')
for ss in ('Азия', 'Лондон', 'NY утро', 'NY день'):
    for sd in ('PDH', 'PDL'): eline(f'{sd} в сессию {ss}', lambda d, ss=ss, sd=sd: d[(d.sess == ss) & (d.side == sd)])
L.append('  -- фитиль или тело')
for sd in ('PDH', 'PDL'):
    eline(f'{sd}: свеча снятия закрылась обратно (фитиль)', lambda d, sd=sd: d[(d.wick == 1) & (d.side == sd)])
    eline(f'{sd}: свеча снятия закрылась за уровнем (тело)', lambda d, sd=sd: d[(d.wick == 0) & (d.side == sd)])
L.append('  -- другая сторона уже снята сегодня')
for sd in ('PDH', 'PDL'):
    eline(f'{sd} снят вторым (другая сторона уже снята)', lambda d, sd=sd: d[(d.other_first == 1) & (d.side == sd)])
    eline(f'{sd} снят первым', lambda d, sd=sd: d[(d.other_first == 0) & (d.side == sd)])
L.append('  -- вчерашний день (BIAS дня)')
for st in ('принятие выше', 'отказ сверху', 'внутри', 'обе сняты', 'отказ снизу', 'принятие ниже'):
    for sd in ('PDH', 'PDL'): eline(f'{sd} снят, вчера «{st}»', lambda d, st=st, sd=sd: d[(d.prev_state == st) & (d.side == sd)])
L.append('  -- тренд (цена выше / ниже 20-дневной средней)')
for sd in ('PDH', 'PDL'):
    eline(f'{sd} снят по тренду', lambda d, sd=sd: d[(d.above_sma == 1) & (d.side == sd)] if sd == 'PDH' else d[(d.above_sma == 1) & (d.side == sd)])
    eline(f'{sd} снят против тренда', lambda d, sd=sd: d[(d.above_sma == 0) & (d.side == sd)])
L.append('     (для PDL «по тренду» = цена ниже средней: зеркальные цены)')
L.append('  -- узкий / широкий вчерашний день')
eline('вчерашний диапазон < 0,7 ATR', lambda d: d[d.rng_atr < .7]); eline('вчерашний диапазон > 1,3 ATR', lambda d: d[d.rng_atr > 1.3])
# 3. вынос до разворота
L.append('\n=== 3. НАСКОЛЬКО ГЛУБОКО ЦЕНА ВЫНОСИТ УРОВЕНЬ ПЕРЕД РАЗВОРОТОМ К СЕРЕДИНЕ (в долях дневного ATR)')
for sd in ('PDH', 'PDL'):
    x = RE[RE.side == sd].exc_atr.dropna(); xc = pd.concat([s[1][s[1].side == sd].exc_atr.dropna() for s in SS])
    L.append(f'  {sd}: медиана {x.median():.2f} ({xc.median():.2f}) | 75% {x.quantile(.75):.2f} ({xc.quantile(.75):.2f}) | 90% {x.quantile(.9):.2f} ({xc.quantile(.9):.2f}) | n={len(x)}')
# 4. turtle soup
L.append('\n=== 4. СДЕЛКА TURTLE SOUP: закрытие 15m обратно за уровень (≤ 4 ч после выноса), стоп за экстремумом выноса, комиссия 0,1%')
def tline(nm, f):
    x = f(RE[RE.ts == 1]); cs = [f(s[1][s[1].ts == 1]) for s in SS]
    if len(x) < 50: return
    parts = []
    for t, tn in (('ts_R_mid', 'цель середина'), ('ts_R_1', 'цель 1R'), ('ts_R_2', 'цель 2R')):
        v = x[t].dropna(); q = np.mean([c[t].dropna().mean() for c in cs]); se = v.std() / np.sqrt(len(v))
        parts.append(f'{tn} {v.mean():+.2f}R ±{2*se:.2f} ({q:+.2f})')
    L.append(f'  {nm:46s} n={len(x):5d} | риск {x.ts_risk_atr.median():.2f} ATR | ' + ' | '.join(parts))
tline('все', lambda d: d)
for sd in ('PDH', 'PDL'): tline(f'вынос {sd}', lambda d, sd=sd: d[d.side == sd])
for ss in ('Азия', 'Лондон', 'NY утро', 'NY день'): tline(f'вынос в сессию {ss}', lambda d, ss=ss: d[d.sess == ss])
tline('вынос вторым (другая сторона уже снята)', lambda d: d[d.other_first == 1])
tline('вынос PDH, вчера «отказ сверху»', lambda d: d[(d.side == 'PDH') & (d.prev_state == 'отказ сверху')])
tline('риск < 0,25 ATR', lambda d: d[d.ts_risk_atr < .25]); tline('риск > 0,5 ATR', lambda d: d[d.ts_risk_atr > .5])
txt = '\n'.join(L); print(txt); open(OUT, 'w').write(txt + '\n')
