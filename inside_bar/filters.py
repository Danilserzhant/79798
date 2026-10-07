"""Поиск фильтров, повышающих P(хай матери раньше нового лоя) для подтверждённого сетапа
(инверсия H4 FVG на уровне/выше лоя инсайда + недельное закрытие выше лоя инсайда).
Все признаки известны на момент недельного закрытия; исход считается от него, горизонт 4 недели.
python filters.py <dir_pkl> <events.csv> <confirmed_wk.csv> <out.csv>"""
import sys, numpy as np, pandas as pd
SRC, EV, CF, OUT = sys.argv[1:5]
E = pd.read_csv(EV); C = pd.read_csv(CF)
ev = {(r.sym, r.side, r.ib_week): r for r in E.itertuples()}
HOLD = pd.Timedelta(weeks=4); NEVER = pd.Timestamp.max
cache = {}; rows = []
def wk_agg(m):
    return m.resample('W-MON', label='left', closed='left').agg(h=('h', 'max'), l=('l', 'min'), c=('c', 'last')).dropna()
for s in C.itertuples():
    e = ev[(s.sym, s.side, s.ib_week)]
    if e.open: continue
    if (s.sym, s.side) not in cache:
        raw = pd.read_pickle(f'{SRC}/{s.sym}.pkl')
        m = raw if s.side == 'low' else pd.DataFrame({'h': -raw.l, 'l': -raw.h, 'c': -raw.c}, index=raw.index)
        cache[(s.sym, s.side)] = (m, wk_agg(m))
    m, W = cache[(s.sym, s.side)]
    sg = 1 if s.side == 'low' else -1
    L, H, R = sg * e.L, sg * e.H, e.R
    t0, we = pd.Timestamp(e.t0), pd.Timestamp(s.t_entry)
    ibw = pd.Timestamp(s.ib_week); mow = ibw - pd.Timedelta(weeks=1)
    ib = W.loc[ibw]; mo = W.loc[mow]
    sweep_low = m.loc[t0:we - pd.Timedelta('15min')].l.min()
    t_ext = m.loc[t0:we - pd.Timedelta('15min')].l.idxmin()
    sw_w = W.loc[we - pd.Timedelta(weeks=1)]                     # неделя сигнала (закрылась в we)
    prevW = W.loc[:mow - pd.Timedelta(days=1)]
    sma20 = prevW.c.tail(20).mean() if len(prevW) >= 20 else np.nan
    rng10 = (prevW.h - prevW.l).tail(10).mean() if len(prevW) >= 10 else np.nan
    low8 = W.loc[:ibw + pd.Timedelta(days=1)].l.tail(10).min()  # минимум 10 недель до снятия (вкл. мать и IB)
    f = m.loc[we:we + HOLD]
    def first(mask):
        i = np.nonzero(mask)[0]; return f.index[i[0]] if len(i) else NEVER
    tH, tN = first(f.h.values >= H), first(f.l.values < sweep_low)
    rows.append(dict(sym=s.sym, side=s.side, ib_week=s.ib_week, yr=we.year,
        win=tH < tN, reach_H=tH < NEVER,
        depth_R=(L - sweep_low) / R,
        days_to_close=(we - t0).total_seconds() / 86400,
        hours_ext_to_close=(we - t_ext).total_seconds() / 3600,
        same_week=(we - pd.Timedelta(weeks=1)) <= t0,
        ib_ratio=(ib.h - ib.l) / R,
        mo_vs_avg=R / rng10 if rng10 == rng10 else np.nan,
        trend_up=(mo.c > sma20) if sma20 == sma20 else np.nan,
        mom4=(ib.c - prevW.c.iloc[-3]) / abs(prevW.c.iloc[-3]) * 100 if len(prevW) >= 3 else np.nan,
        wk_close_pos=(sw_w.c - sw_w.l) / (sw_w.h - sw_w.l),
        wk_close_in_mother=(sw_w.c - L) / R,
        wk_close_above_mid=sw_w.c > L + R / 2,
        took_10w_low=sweep_low < low8,
        sweep_dow=t0.dayofweek))
D = pd.DataFrame(rows); D.to_csv(OUT, index=False)
print(len(D), 'base', round(D.win.mean() * 100, 1), '| low', (D.side == 'low').sum(), round(D[D.side == 'low'].win.mean() * 100, 1))
def show(name, mask_dict):
    print(f'\n== {name}')
    for k, mk in mask_dict.items():
        g = D[mk]; gl = g[g.side == 'low']
        print(f'  {k:38s} n={len(g):3d} P={g.win.mean()*100:5.1f}% | low n={len(gl):3d} P={gl.win.mean()*100 if len(gl) else float("nan"):5.1f}% '
              f'| 20-23 {g[g.yr<=2023].win.mean()*100:5.1f}% 24-26 {g[g.yr>2023].win.mean()*100:5.1f}%')
q = lambda c: D[c].quantile([1/3, 2/3]).values
for c in ['depth_R', 'days_to_close', 'hours_ext_to_close', 'ib_ratio', 'mo_vs_avg', 'mom4', 'wk_close_pos', 'wk_close_in_mother']:
    a, b = q(c)
    show(f'{c} (терции {a:.2f} / {b:.2f})', {f'низ  < {a:.2f}': D[c] < a, f'сред {a:.2f}–{b:.2f}': (D[c] >= a) & (D[c] < b), f'верх ≥ {b:.2f}': D[c] >= b})
for c in ['same_week', 'trend_up', 'wk_close_above_mid', 'took_10w_low']:
    show(c, {'да': D[c] == True, 'нет': D[c] == False})
show('sweep_dow', {d: D.sweep_dow == i for i, d in enumerate(['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'])})
