"""Подтверждение «инверсия последнего FVG перед экстремумом манипуляции».
Для снятия лоя: последний медвежий FVG (h[k] < l[k-2]) на ТФ, завершённый не позже бара экстремума
(минимум с момента снятия) и не перекрытый закрытием выше его верха до экстремума. Сигнал — первое закрытие
бара ТФ выше верха FVG после экстремума (экстремум пересчитывается на каждом баре — без заглядывания вперёд).
Для снятия хая — зеркально.
python ifvg_signals.py <dir_pkl> <events.csv> <out.csv> [state_X]   (state_X — отсчёт от текущего состояния)"""
import sys, numpy as np, pandas as pd
SRC, EV, OUT = sys.argv[1:4]
X = float(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4] != '-' else None
# SELECT: last — последний FVG; ib — последний FVG, у которого верх >= лоя инсайда (на уровне или выше);
#         mother — то же относительно лоя матери
SELECT = sys.argv[5] if len(sys.argv) > 5 else 'last'
# wkinval: сетап отменяется закрытием недели ниже лоя инсайда до сигнала; иначе ждём до 4 недель
WKINVAL = len(sys.argv) > 6 and sys.argv[6] == 'wkinval'
E = pd.read_csv(EV)
TFS = {'H4': '4h', 'H1': '1h', 'D1': '1D'}
LOOKBACK = {'H4': 42, 'H1': 168, 'D1': 10}       # ≈7 дней (D1 — 10 дней)
if SELECT != 'last': LOOKBACK = {'H4': 84, 'H1': 336, 'D1': 14}   # уровень мог сформироваться раньше
WIN = pd.Timedelta(days=7)
def agg(df, rule):
    return df.resample(rule, label='left', closed='left').agg(h=('h', 'max'), l=('l', 'min'), c=('c', 'last')).dropna()
cache, rows, current, status = {}, [], [], []
for e in E.itertuples():
    if (e.sym, e.side) not in cache:
        raw = pd.read_pickle(f'{SRC}/{e.sym}.pkl')
        m = raw if e.side == 'low' else pd.DataFrame({'h': -raw.l, 'l': -raw.h, 'c': -raw.c}, index=raw.index)
        cache[(e.sym, e.side)] = (m, {k: agg(m, r) for k, r in TFS.items()})
    m, fr = cache[(e.sym, e.side)]
    sg = 1 if e.side == 'low' else -1
    L, H, R = sg * e.L, sg * e.H, e.R
    t0 = pd.Timestamp(e.t0)
    ibw = pd.Timestamp(e.ib_week)
    ib_l = m.loc[ibw:ibw + pd.Timedelta(weeks=1) - pd.Timedelta('15min')].l.min()
    lvl_sel = {'ib': ib_l, 'mother': L}.get(SELECT)
    anchor = t0
    if X is not None:
        a1 = m.loc[t0:t0 + pd.Timedelta(weeks=1)]
        ok = np.nonzero((np.minimum.accumulate(a1.l.values) <= L - X * R) & (np.maximum.accumulate(a1.h.values) < H))[0]
        if not len(ok): continue
        anchor = a1.index[ok[0]]
    win_end = anchor + WIN; inval = None
    if WKINVAL:
        win_end = anchor + pd.Timedelta(weeks=4)
        wk = t0.normalize() - pd.Timedelta(days=t0.dayofweek)
        while wk + pd.Timedelta(weeks=1) <= m.index[-1] + pd.Timedelta('15min'):
            we = wk + pd.Timedelta(weeks=1)
            if we > anchor and m.c.loc[:we - pd.Timedelta('15min')].iloc[-1] < ib_l:
                inval = we; break
            wk = we
            if wk > win_end: break
        if inval is not None: win_end = min(win_end, inval)
    for tf, b in fr.items():
        off = pd.Timedelta(TFS[tf])
        hv, lv, cv, idx = b.h.values, b.l.values, b.c.values, b.index
        j0 = idx.searchsorted(t0, side='right') - 1           # бар, в котором случилось снятие
        sig = None; last_info = None
        for j in range(max(j0, 2), len(b)):
            tclose = idx[j] + off
            if tclose <= anchor: continue
            if tclose > win_end: break
            x = j0 + int(np.argmin(lv[j0:j + 1]))                # бар экстремума на текущий момент
            if x == j: last_info = None; continue                 # экстремум только что обновлён
            top = None
            for k in range(x, max(1, x - LOOKBACK[tf]), -1):
                if k < 2: break
                if hv[k] < lv[k - 2]:                            # медвежий FVG: верх = l[k-2], низ = h[k]
                    t_top = lv[k - 2]
                    if (cv[k + 1:x + 1] > t_top).any(): continue   # уже инвертирован до экстремума
                    if lvl_sel is not None and t_top < lvl_sel: continue   # нужен FVG на уровне или выше
                    top = t_top; kk = k; break
            if top is None: continue
            last_info = (top, idx[kk], hv[kk])
            if cv[j] > top and (cv[x + 1:j] <= top).all():
                sig = tclose; break
        if e.open and X is not None:
            current.append(dict(sym=e.sym, side=e.side, tf=tf, fvg_top=sg * last_info[0] if last_info else None,
                                fvg_bar=str(last_info[1]) if last_info else None, signal=str(sig)))
        if tf == 'H4':
            status.append(dict(sym=e.sym, side=e.side, ib_week=e.ib_week, open=bool(e.open), t0=str(t0), inval=str(inval), sig=str(sig),
                               status='signal' if sig is not None else ('invalidated' if inval is not None else ('open' if e.open else 'expired'))))
        if sig is not None:
            if SELECT == 'ib':
                where = 'FVG на уровне инсайда' if last_info[2] <= ib_l else 'FVG выше лоя инсайда'
            else:
                where = 'верх FVG выше L' if last_info[0] > L else 'верх FVG ниже L'
            rows.append(dict(sym=e.sym, side=e.side, ib_week=e.ib_week, conf=f'Инверсия {tf} FVG' + {'last': ' (последний)', 'ib': ' на уровне/выше лоя инсайда', 'mother': ' на уровне/выше лоя матери'}[SELECT], where=where,
                             kind='rev', t_entry=str(sig), open=bool(e.open)))
D = pd.DataFrame(rows); D.to_csv(OUT, index=False)
pd.DataFrame(status).to_csv(OUT.replace('.csv', '_status.csv'), index=False)
D2 = D.copy(); D2['conf'] = D2.conf + ' · ' + D2['where']; D2.to_csv(OUT.replace('.csv', '_split.csv'), index=False)
if current: print(pd.DataFrame(current).to_string())
print(len(rows))
