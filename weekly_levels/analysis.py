"""Статистика взаимодействия цены BTCUSDT с максимумами/минимумами недельных свечей
и связь этих уровней с результатами сделок из скриншотов репозитория.

Вход:  m5.pkl     — 5m свечи BTCUSDT (Binance spot, UTC), см. fetch_data.py
       trades.pkl — сделки, распознанные со скриншотов (ocr_trades.py)
Выход: results.json + печать таблиц.
Неделя = Пн 00:00 UTC … Вс 23:59 UTC (как недельная свеча Binance/TradingView).
"""
import json, sys
import numpy as np, pandas as pd

D = sys.argv[1] if len(sys.argv) > 1 else '.'
m5 = pd.read_pickle(f'{D}/m5.pkl')
trades = pd.read_pickle(f'{D}/trades.pkl')
DAYS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']

m5['wk'] = m5.index.normalize() - pd.to_timedelta(m5.index.dayofweek, unit='D')
W = m5.groupby('wk').agg(o=('o', 'first'), h=('h', 'max'), l=('l', 'min'), c=('c', 'last'), n=('o', 'size'))
W = W[W.n >= 2000]                      # только полные недели (2016 баров)
W['pwh'] = W.h.shift(1); W['pwl'] = W.l.shift(1)
W = W.loc['2020-01-06':].dropna()       # период сделок
W['hi_t'] = W.h > W.pwh
W['lo_t'] = W.l < W.pwl
out = {'period': [str(W.index[0].date()), str((W.index[-1] + pd.Timedelta('6D')).date())], 'weeks': int(len(W))}


def race(t0, lvl, up, ks=(0.5, 1.0, 2.0), hours=72):
    """Первое касание уровня в баре t0. Что раньше: продолжение на k% за уровень
    или разворот на k% обратно? Бар касания учитывается только для продолжения
    (иначе открытие бара «с той стороны» даёт ложный разворот)."""
    a = m5.loc[t0:t0 + pd.Timedelta(hours=hours)]
    a2 = a.iloc[1:]
    res = {}
    for k in ks:
        c = a.index[(a.h >= lvl * (1 + k / 100)) if up else (a.l <= lvl * (1 - k / 100))]
        v = a2.index[(a2.l <= lvl * (1 - k / 100)) if up else (a2.h >= lvl * (1 + k / 100))]
        c0 = c[0] if len(c) else None; v0 = v[0] if len(v) else None
        res[k] = 'cont' if c0 is not None and (v0 is None or c0 <= v0) else ('rev' if v0 is not None else 'none')
    return res

# ---------- 1. Снятие PWH / PWL ----------
def pct(x): return round(100 * float(np.mean(x)), 1) if len(x) else None
def q(x, p=(25, 50, 75)): return [round(float(np.percentile(x, i)), 2) for i in p] if len(x) else None

first = []
for wk, r in W.iterrows():
    b = m5.loc[wk:wk + pd.Timedelta('7D') - pd.Timedelta('5min')]
    th = b.index[b.h > r.pwh]; tl = b.index[b.l < r.pwl]
    fh = th[0] if len(th) else None; fl = tl[0] if len(tl) else None
    # что было после первого касания: закрытие недели, возврат к середине прошлой недели и т.п.
    rec = dict(wk=wk, fh=fh, fl=fl)
    mid = (r.pwh + r.pwl) / 2
    for side, t0, lvl in (('h', fh, r.pwh), ('l', fl, r.pwl)):
        if t0 is None: continue
        after = b.loc[t0:]
        sgn = 1 if side == 'h' else -1
        rec[f'{side}_ext'] = 100 * sgn * ((after.h.max() if side == 'h' else after.l.min()) - lvl) / lvl
        rec[f'{side}_mid'] = bool((after.l <= mid).any() if side == 'h' else (after.h >= mid).any())
        # гонка: что раньше — продолжение на k% за уровень или разворот на k% обратно (в пределах 72ч)
        for k, v in race(t0, lvl, side == 'h').items(): rec[f'{side}_race{k}'] = v
    first.append(rec)
F = pd.DataFrame(first).set_index('wk')
W = W.join(F)
both = W[W.hi_t & W.lo_t]
out['sweep'] = {
    'hi_taken': pct(W.hi_t), 'lo_taken': pct(W.lo_t), 'both': pct(W.hi_t & W.lo_t),
    'only_hi': pct(W.hi_t & ~W.lo_t), 'only_lo': pct(~W.hi_t & W.lo_t), 'inside': pct(~W.hi_t & ~W.lo_t),
    'hi_close_above': pct(W[W.hi_t].c > W[W.hi_t].pwh), 'lo_close_below': pct(W[W.lo_t].c < W[W.lo_t].pwl),
    'hi_ext_q': q(W[W.hi_t].h_ext), 'lo_ext_q': q(W[W.lo_t].l_ext),
    'hi_mid': pct(W[W.hi_t].h_mid), 'lo_mid': pct(W[W.lo_t].l_mid),
    'both_hi_first': pct(both.fh < both.fl),
    # если сначала сняли одну сторону — вероятность, что в ту же неделю снимут и вторую
    'hi_first_then_lo': pct(W[W.hi_t & (W.fl.isna() | (W.fh < W.fl))].lo_t),
    'lo_first_then_hi': pct(W[W.lo_t & (W.fh.isna() | (W.fl < W.fh))].hi_t),
}
for side in ('h', 'l'):
    s = W[W[f'{side}i_t' if side == 'h' else 'lo_t']]
    for k in (0.5, 1.0, 2.0):
        vc = s[f'{side}_race{k}'].value_counts(normalize=True) * 100
        out['sweep'][f'{side}_race{k}'] = {kk: round(float(vc.get(kk, 0)), 1) for kk in ('cont', 'rev', 'none')}

# день недели первого касания
out['touch_dow'] = {
    'hi': [int(x) for x in pd.Series([t.dayofweek for t in W.fh.dropna()]).value_counts().reindex(range(7), fill_value=0)],
    'lo': [int(x) for x in pd.Series([t.dayofweek for t in W.fl.dropna()]).value_counts().reindex(range(7), fill_value=0)],
}
# после N дней без касания — шанс, что уровень всё же снимут до конца недели
cond = {}
for side, col, tcol in (('hi', 'hi_t', 'fh'), ('lo', 'lo_t', 'fl')):
    arr = []
    for d in range(7):
        cut = W.index + pd.Timedelta(days=d)
        alive = W[W[tcol].isna() | (W[tcol] >= cut)]
        arr.append(pct(alive[col]) if len(alive) else None)
    cond[side] = arr
out['touch_cond'] = cond

# ---------- 2. В какой день формируется хай/лой недели ----------
hd, ld = [], []
for wk, r in W.iterrows():
    b = m5.loc[wk:wk + pd.Timedelta('7D') - pd.Timedelta('5min')]
    hd.append(b.h.idxmax().dayofweek); ld.append(b.l.idxmin().dayofweek)
out['extreme_dow'] = {'hi': [pct(np.array(hd) == d) for d in range(7)], 'lo': [pct(np.array(ld) == d) for d in range(7)]}

# ---------- 3. Возврат к старым недельным экстремумам ----------
Wall = m5.groupby('wk').agg(h=('h', 'max'), l=('l', 'min'), n=('o', 'size'))
Wall = Wall[Wall.n >= 2000]
hh = m5.h.resample('1h').max(); ll = m5.l.resample('1h').min()
rv = {'hi': [], 'lo': []}
old_race = {}
for wk, r in Wall.loc['2020-01-06':].iterrows():
    st = wk + pd.Timedelta('7D')
    for side, ser, lvl in (('hi', hh, r.h), ('lo', ll, r.l)):
        f = ser.loc[st:]
        hit = f.index[(f > lvl) if side == 'hi' else (f < lvl)]
        rv[side].append((hit[0] - st).total_seconds() / 604800 if len(hit) else np.inf)
        if len(hit) and hit[0] - st >= pd.Timedelta('7D'):     # старые (не прошлой недели) уровни
            b = m5.loc[hit[0]:hit[0] + pd.Timedelta('55min')]
            t0 = b.index[(b.h > lvl) if side == 'hi' else (b.l < lvl)][0]
            for k, v in race(t0, lvl, side == 'hi').items(): old_race.setdefault((side, k), []).append(v)
end_weeks = (m5.index[-1] - pd.Timestamp('2020-01-13')).total_seconds() / 604800
out['revisit'] = {}
for side, a in rv.items():
    a = np.array(a); n = len(a)
    ages = np.array([(m5.index[-1] - (wk + pd.Timedelta('7D'))).total_seconds() / 604800 for wk in Wall.loc['2020-01-06':].index])
    res = {}
    for k in (1, 2, 4, 8, 13, 26, 52):
        ok = ages >= k   # только уровни, у которых было хотя бы k недель
        res[k] = pct(a[ok] <= k)
    res['never'] = int(np.isinf(a).sum()); res['n'] = n
    res['median_weeks'] = round(float(np.median(a[np.isfinite(a)])), 2)
    out['revisit'][side] = res
out['old_race'] = {f'{sd}_{k}': {x: pct(np.array(v) == x) for x in ('cont', 'rev', 'none')} | {'n': len(v)}
                   for (sd, k), v in old_race.items()}

# ---------- 4. Сделки vs недельные уровни ----------
T = trades.copy()
T['R'] = T.res.astype(float)
T['win'] = T.res > 0
rows = []
for _, t in T.iterrows():
    wk = t.time.normalize() - pd.Timedelta(days=t.time.dayofweek)
    pw = Wall.loc[:wk - pd.Timedelta('1D')].iloc[-1]
    pre = m5.loc[wk:t.time - pd.Timedelta('5min')]               # неделя до входа
    lg = t.dir == 'LONG'
    pwh, pwl = pw.h, pw.l
    rng = pwh - pwl
    pos = (t.entry - pwl) / rng
    # снятие недельного уровня самим свипом сделки
    w3 = m5.loc[t.time - pd.Timedelta('3h'):t.time]
    lvl_pw = pwl if lg else pwh
    beyond = lambda x: (x < lvl_pw) if lg else (x > lvl_pw)
    before_close = m5.c.loc[:t.time - pd.Timedelta('3h') - pd.Timedelta('5min')].iloc[-1]
    swept_now = (not beyond(before_close)) and bool(beyond(w3.l if lg else w3.h).any())
    pre3 = m5.loc[wk:t.time - pd.Timedelta('3h') - pd.Timedelta('5min')]
    taken_earlier = bool(len(pre3)) and bool(beyond(pre3.l if lg else pre3.h).any())
    if swept_now and not taken_earlier: pw_cat = 'Свип PWL/PWH — первое снятие за неделю'
    elif swept_now: pw_cat = 'Свип PWL/PWH — повторный (уже снимали на неделе)'
    elif beyond(before_close): pw_cat = 'Цена уже торгуется за PWL/PWH'
    else: pw_cat = 'Свип не касался PWL/PWH'
    new_wk_ext = bool(len(pre3)) and ((w3.l.min() < pre3.l.min()) if lg else (w3.h.max() > pre3.h.max()))
    # уровень против сделки (цель): ближайший недельный экстремум по направлению TP
    if lg:
        cands = [x for x in (pwh, pre.h.max() if len(pre) else np.nan) if x > t.entry]
        dist = (min(cands) - t.entry) / t.risk if cands else np.inf
    else:
        cands = [x for x in (pwl, pre.l.min() if len(pre) else np.nan) if x < t.entry]
        dist = (t.entry - max(cands)) / t.risk if cands else np.inf
    # на момент входа уже снята противоположная / та же сторона прошлой недели?
    # «голые» (ещё не протестированные) недельные экстремумы последних 26 недель на момент свипа
    st3 = t.time - pd.Timedelta('3h')
    hist = Wall.loc[wk - pd.Timedelta(weeks=26):wk - pd.Timedelta('1D')]
    naked_swept, naked_path = [], []
    for wk2, r2 in hist.iterrows():
        lvl = r2.l if lg else r2.h
        seg = m5.loc[wk2 + pd.Timedelta('7D'):st3 - pd.Timedelta('5min')]
        tested = ((seg.l < lvl) if lg else (seg.h > lvl)).any()
        if tested: continue
        w3 = m5.loc[st3:t.time]
        if ((w3.l < lvl) if lg else (w3.h > lvl)).any(): naked_swept.append(lvl)
        # голый уровень противоположной стороны — потенциальная цель/стена
        lvl2 = r2.h if lg else r2.l
        seg2 = m5.loc[wk2 + pd.Timedelta('7D'):t.time]
        if not (((seg2.h > lvl2) if lg else (seg2.l < lvl2)).any()):
            naked_path.append(lvl2)
    naked_R = min((abs(x - t.entry) / t.risk for x in naked_path), default=np.inf)
    took_hi = bool(len(pre)) and pre.h.max() > pwh; took_lo = bool(len(pre)) and pre.l.min() < pwl
    rows.append(dict(n=t.n, pos=pos, pw_cat=pw_cat, new_wk_ext=new_wk_ext, dist_R=dist,
                     took_hi=took_hi, took_lo=took_lo, dow=t.time.dayofweek,
                     naked_swept=len(naked_swept) > 0, naked_R=naked_R))
T = T.merge(pd.DataFrame(rows), on='n')
T.to_csv(f'{D}/trades_weekly.csv', index=False)

def stat(g):
    return dict(n=int(len(g)), win=pct(g.win), sl=pct(g.res == -1), tp2=pct(g.res >= 2), tp5=pct(g.res == 5),
                avgR=round(float(g.R.mean()), 2) if len(g) else None)

grp = {'all': stat(T)}
grp['dir'] = {d: stat(T[T.dir == d]) for d in ('LONG', 'SHORT')}
grp['pw_cat'] = {k: stat(T[T.pw_cat == k]) for k in ['Свип PWL/PWH — первое снятие за неделю', 'Свип PWL/PWH — повторный (уже снимали на неделе)',
                                                  'Цена уже торгуется за PWL/PWH', 'Свип не касался PWL/PWH']}
grp['new_wk_ext'] = {'Свип обновил экстремум текущей недели': stat(T[T.new_wk_ext]), 'Нет': stat(T[~T.new_wk_ext])}
# позиция входа в диапазоне прошлой недели, в терминах сделки: для лонга 0 = PWL (дискаунт), для шорта 0 = PWH
T['pos_dir'] = np.where(T.dir == 'LONG', T.pos, 1 - T.pos)
bins = [-np.inf, 0, 0.25, 0.5, 0.75, 1, np.inf]
labels = ['за уровнем (<0)', '0–25%', '25–50%', '50–75%', '75–100%', 'за противоп. (>100%)']
T['pos_bin'] = pd.cut(T.pos_dir, bins, labels=labels)
grp['pos'] = {l: stat(T[T.pos_bin == l]) for l in labels}
db = [0, 1, 2, 4, 5, 8, np.inf]; dl = ['<1R', '1–2R', '2–4R', '4–5R', '5–8R', '>8R / нет']
T['dist_bin'] = pd.cut(T.dist_R.replace(np.inf, 1e9), db, labels=dl, right=False)
grp['dist'] = {l: stat(T[T.dist_bin == l]) for l in dl}
# контекст недели: лонг, когда на неделе уже снят PWH (тренд вверх) / PWL (свип вниз)
def ctx(r):
    a, b = (r.took_hi, r.took_lo) if r.dir == 'LONG' else (r.took_lo, r.took_hi)
    return {(False, False): 'Внутри диапазона прошлой недели', (True, False): 'Уже снята сторона ПО направлению',
            (False, True): 'Уже снята сторона ПРОТИВ направления', (True, True): 'Сняты обе'}[(a, b)]
T['ctx'] = T.apply(ctx, axis=1)
grp['ctx'] = {k: stat(T[T.ctx == k]) for k in ['Внутри диапазона прошлой недели', 'Уже снята сторона ПРОТИВ направления',
                                                'Уже снята сторона ПО направлению', 'Сняты обе']}
grp['naked_swept'] = {'Свип снял «голый» недельный экстремум (≤26 нед.)': stat(T[T.naked_swept]), 'Нет': stat(T[~T.naked_swept])}
T['naked_bin'] = pd.cut(T.naked_R.replace(np.inf, 1e9), db, labels=dl, right=False)
grp['naked_dist'] = {l: stat(T[T.naked_bin == l]) for l in dl}
grp['dow'] = {DAYS[d]: stat(T[T.dow == d]) for d in range(7)}
out['trades'] = grp
json.dump(out, open(f'{D}/results.json', 'w'), ensure_ascii=False, indent=1, default=str)
print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
