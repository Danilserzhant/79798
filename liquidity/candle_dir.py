"""Направление недельной и месячной свечи BTC и ETH: что его предсказывает.
python candle_dir.py <dir_daily_real> <dir_daily_syn1,...> <out_txt>
Данные — дневные свечи (спот Binance с 2017). Бычья свеча: close > open. Неделя с понедельника, месяц календарный, UTC.
A) До открытия: прошлая свеча (направление, серия, состояние закрытия, где закрылась в диапазоне, тело, размер, инсайд/аутсайд),
   тренд (выше средней, импульс), месяц года.
B) Внутри свечи: где цена к открытию после 1/2/3 дней недели (для месяца — после 7/14 дней); какую сторону прошлой свечи сняли первой.
C) Описательно: в какой день недели (неделе месяца) формируется лой бычьей и хай медвежьей свечи.
Контроль — те же дни в случайном порядке (5 перемешиваний)."""
import sys, numpy as np, pandas as pd
REAL, SYN, OUT = sys.argv[1], sys.argv[2].split(','), sys.argv[3]
SYMS = ['BTCUSDT', 'ETHUSDT']
def state(h, l, c, PH, PL):
    if c > PH: return 'принятие выше'
    if c < PL: return 'принятие ниже'
    if h > PH and l < PL: return 'обе сняты'
    if h > PH: return 'отказ сверху'
    if l < PL: return 'отказ снизу'
    return 'внутри'
def table(d, sym, P):
    k = (d.index - pd.to_timedelta(d.index.dayofweek, unit='D')) if P == 'W' else d.index.to_period('M').to_timestamp()
    g = d.groupby(k)
    b = g.agg(o=('o', 'first'), h=('h', 'max'), l=('l', 'min'), c=('c', 'last'), n=('o', 'size'))
    full = 7 if P == 'W' else 28
    b = b[b.n >= full]
    rows = []
    days = {kk: v for kk, v in g}
    O, H, L, C = b.o.values, b.h.values, b.l.values, b.c.values
    bull = C > O
    rng = H - L
    for j in range(14, len(b)):
        dd = days[b.index[j]]
        r = dict(sym=sym, P=P, t=b.index[j], bull=bool(bull[j]))
        r['prev_bull'] = bool(bull[j - 1])
        s = 1
        while j - 1 - s >= 0 and bull[j - 1 - s] == bull[j - 1]: s += 1
        r['streak'] = s * (1 if bull[j - 1] else -1)
        r['prev_state'] = state(H[j - 1], L[j - 1], C[j - 1], H[j - 2], L[j - 2])
        r['prev_clv'] = (C[j - 1] - L[j - 1]) / rng[j - 1] if rng[j - 1] > 0 else .5
        r['prev_body'] = abs(C[j - 1] - O[j - 1]) / rng[j - 1] if rng[j - 1] > 0 else 0
        r['prev_range'] = rng[j - 1] / rng[j - 11:j - 1].mean()
        r['prev_inside'] = bool(H[j - 1] <= H[j - 2] and L[j - 1] >= L[j - 2])
        r['prev_outside'] = bool(H[j - 1] > H[j - 2] and L[j - 1] < L[j - 2])
        n_ma = 20 if P == 'W' else 12
        r['above_ma'] = bool(C[j - 1] > C[max(0, j - n_ma):j].mean()) if j >= n_ma else np.nan
        r['mom3'] = bool(C[j - 1] > C[j - 4])
        r['mom12'] = bool(C[j - 1] > C[j - 13]) if j >= 13 else np.nan
        r['month'] = b.index[j].month
        # внутри свечи
        oc = dd.c.values; ohh = dd.h.values; oll = dd.l.values
        marks = (1, 2, 3) if P == 'W' else (7, 14)
        for mk in marks:
            if len(oc) > mk: r[f'up_after_{mk}'] = bool(oc[mk - 1] > O[j])
        fs = 'нет'
        for x in range(len(oc)):
            hh, ll = ohh[x] > H[j - 1], oll[x] < L[j - 1]
            if hh and ll: fs = 'обе в один день'; break
            if hh: fs = 'хай'; r['first_day'] = x; break
            if ll: fs = 'лой'; r['first_day'] = x; break
        r['first_swept'] = fs
        # где сформировался экстремум
        r['low_day'] = int(np.argmin(oll)); r['high_day'] = int(np.argmax(ohh))
        rows.append(r)
    return pd.DataFrame(rows)
def build(src):
    return pd.concat([table(pd.read_pickle(f'{src}/{s}.pkl'), s, P) for s in SYMS for P in ('W', 'M')], ignore_index=True)
R = build(REAL); Ss = [build(s) for s in SYN]
half = {P: R[R.P == P].t.sort_values().iloc[len(R[R.P == P]) // 2] for P in ('W', 'M')}
L = []
pc = lambda v: f'{100*v:3.0f}%' if v == v else '  — '
def line(nm, f, P):
    r = R[R.P == P]; x = f(r)
    if len(x) < 8: return
    p = x.bull.mean(); base = r.bull.mean()
    cs = [f(s[s.P == P]) for s in Ss]; pcn = np.nanmean([c.bull.mean() for c in cs if len(c)])
    se = np.sqrt(max(pcn * (1 - pcn), .01) / len(x)); z = (p - pcn) / se
    h1 = x[x.t < half[P]].bull.mean(); h2 = x[x.t >= half[P]].bull.mean()
    pb, pe = x[x.sym == 'BTCUSDT'].bull.mean(), x[x.sym == 'ETHUSDT'].bull.mean()
    flag = '  ◀' if abs(z) >= 2 and (h1 - base) * (h2 - base) > 0 and (pb - base) * (pe - base) > 0 else ''
    L.append(f'  {nm:58s} n={len(x):4d} | бычьих {pc(p)} (контроль {pc(pcn)}, база {pc(base)}) {z:+.1f} | BTC {pc(pb)} ETH {pc(pe)} | 1-я пол. {pc(h1)} 2-я {pc(h2)}{flag}')
for P, nm in (('W', 'НЕДЕЛЬНЫЕ'), ('M', 'МЕСЯЧНЫЕ')):
    r = R[R.P == P]
    L.append(f'\n################ {nm} свечи BTC + ETH: {len(r)} шт., {r.t.min().date()} — {r.t.max().date()}, бычьих {pc(r.bull.mean())}')
    L.append('--- A. Известно до открытия')
    line('прошлая свеча бычья', lambda d: d[d.prev_bull], P); line('прошлая свеча медвежья', lambda d: d[~d.prev_bull.astype(bool)], P)
    for s_ in (2, 3, 4):
        line(f'{s_}+ бычьих подряд', lambda d, s_=s_: d[d.streak >= s_], P); line(f'{s_}+ медвежьих подряд', lambda d, s_=s_: d[d.streak <= -s_], P)
    for st in ('принятие выше', 'отказ снизу', 'внутри', 'обе сняты', 'отказ сверху', 'принятие ниже'):
        line(f'прошлая: {st}', lambda d, st=st: d[d.prev_state == st], P)
    line('прошлая закрылась в верхней трети диапазона', lambda d: d[d.prev_clv > 2 / 3], P)
    line('прошлая закрылась в нижней трети диапазона', lambda d: d[d.prev_clv < 1 / 3], P)
    line('прошлая — доджи (тело < 30% диапазона)', lambda d: d[d.prev_body < .3], P)
    line('прошлая — сильное тело (> 70% диапазона)', lambda d: d[d.prev_body > .7], P)
    line('прошлая бычья с сильным телом', lambda d: d[(d.prev_body > .7) & d.prev_bull], P)
    line('прошлая медвежья с сильным телом', lambda d: d[(d.prev_body > .7) & ~d.prev_bull.astype(bool)], P)
    line('прошлая — большой диапазон (> 1,5 среднего)', lambda d: d[d.prev_range > 1.5], P)
    line('прошлая — маленький диапазон (< 0,6 среднего)', lambda d: d[d.prev_range < .6], P)
    line('прошлая — инсайд-бар', lambda d: d[d.prev_inside.astype(bool)], P)
    line('прошлая — аутсайд-бар', lambda d: d[d.prev_outside.astype(bool)], P)
    line('цена выше средней (20 нед / 12 мес)', lambda d: d[d.above_ma == True], P)
    line('цена ниже средней', lambda d: d[d.above_ma == False], P)
    line('выросла за 3 свечи', lambda d: d[d.mom3], P); line('упала за 3 свечи', lambda d: d[~d.mom3.astype(bool)], P)
    line('выросла за 12 свечей', lambda d: d[d.mom12 == True], P); line('упала за 12 свечей', lambda d: d[d.mom12 == False], P)
    if P == 'M':
        for mo, mn in enumerate(['январь', 'февраль', 'март', 'апрель', 'май', 'июнь', 'июль', 'август', 'сентябрь', 'октябрь', 'ноябрь', 'декабрь'], 1):
            line(f'месяц: {mn}', lambda d, mo=mo: d[d.month == mo], P)
    L.append('--- B. Внутри свечи')
    for mk in ((1, 2, 3) if P == 'W' else (7, 14)):
        u = f'up_after_{mk}'; lab = {1: 'понедельника', 2: 'вторника', 3: 'среды', 7: '1-й недели', 14: '2-х недель'}[mk]
        line(f'после {lab} цена ВЫШЕ открытия', lambda d, u=u: d[d[u] == True], P)
        line(f'после {lab} цена НИЖЕ открытия', lambda d, u=u: d[d[u] == False], P)
    line('первой снята сторона: хай прошлой свечи', lambda d: d[d.first_swept == 'хай'], P)
    line('первой снята сторона: лой прошлой свечи', lambda d: d[d.first_swept == 'лой'], P)
    line('ни одна сторона прошлой свечи не снята', lambda d: d[d.first_swept == 'нет'], P)
    if P == 'W':
        line('лой прошлой недели снят в пн–вт, после среды цена выше открытия', lambda d: d[(d.first_swept == 'лой') & (d.first_day <= 1) & (d.up_after_3 == True)], P)
        line('хай прошлой недели снят в пн–вт, после среды цена ниже открытия', lambda d: d[(d.first_swept == 'хай') & (d.first_day <= 1) & (d.up_after_3 == False)], P)
    L.append('--- C. Когда формируется экстремум (описательно; контроль — в скобках)')
    names = ['пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс'] if P == 'W' else None
    def dist(x, col):
        if P == 'W': return x[col].value_counts(normalize=True).reindex(range(7)).fillna(0).values
        bins = pd.cut(x[col], [-1, 6, 13, 20, 40], labels=False); return pd.Series(bins).value_counts(normalize=True).reindex(range(4)).fillna(0).values
    lab = names if P == 'W' else ['дни 1–7', '8–14', '15–21', '22+']
    for col, cond, nm in (('low_day', True, 'лой бычьей свечи'), ('high_day', False, 'хай медвежьей свечи')):
        x = r[r.bull == cond]; dr = dist(x, col); dc = np.mean([dist(s[(s.P == P) & (s.bull == cond)], col) for s in Ss], axis=0)
        L.append(f'  {nm:22s}: ' + ' | '.join(f'{lab[i]} {pc(dr[i])} ({pc(dc[i])})' for i in range(len(lab))) + f'  · первые 3 {"дня" if P=="W" else "недели"}: {pc(dr[:3].sum())} ({pc(dc[:3].sum())})')
print('\n'.join(L)); open(OUT, 'w').write('\n'.join(L) + '\n')
R.to_csv(OUT.replace('.txt', '.csv'), index=False)
