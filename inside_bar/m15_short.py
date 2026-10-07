"""Шорт от H4 FVG (того же, что для лонг-сетапа: последний медвежий H4 FVG с верхом >= лоя матери перед экстремумом).
Цена заходит в зону -> отслеживаем локальный хай отката -> последний восходящий M15 FVG до этого хая (сформирован
после лоя манипуляции, не перекрыт) -> сигнал: закрытие M15 ниже его низа. Перестаём смотреть после закрытия H4 выше
верха зоны. Новый лой ниже экстремума — сброс (зона и FVG пересчитываются). Окно 4 недели от снятия.
Выход: стоп над локальным хаем; цели — лой манипуляции и L−1R; если стоп и цель в одной 15m — стоп.
python m15_short.py <dir_pkl> <events.csv> <out.csv> [SYM]"""
import sys, os, numpy as np, pandas as pd
# TRIGGER=shift: сигнал — закрытие M15 ниже последнего фрактального минимума (2+2 свечи) перед локальным хаем
TRIGGER = os.environ.get('TRIGGER', 'fvg')
SRC, EV, OUT = sys.argv[1:4]
SYM = sys.argv[4] if len(sys.argv) > 4 else None
E = pd.read_csv(EV); E = E[~E.open] if 'open' in E else E
if SYM: E = E[E.sym == SYM]
cache, rows = {}, []
for e in E.itertuples():
    if (e.sym, e.side) not in cache:
        raw = pd.read_pickle(f'{SRC}/{e.sym}.pkl')
        m = raw if e.side == 'low' else pd.DataFrame({'o': -raw.o, 'h': -raw.l, 'l': -raw.h, 'c': -raw.c}, index=raw.index)
        b4 = m.resample('4h', label='left', closed='left').agg(h=('h', 'max'), l=('l', 'min'), c=('c', 'last')).dropna()
        cache[(e.sym, e.side)] = (m, b4)
    m, b4 = cache[(e.sym, e.side)]
    sg = 1 if e.side == 'low' else -1
    L, H, R = sg * e.L, sg * e.H, e.R
    t0 = pd.Timestamp(e.t0)
    seg = m.loc[t0:t0 + pd.Timedelta(weeks=4)]
    if len(seg) < 10: continue
    T, h, l, c = seg.index, seg.h.values, seg.l.values, seg.c.values
    H4t = b4.index.values; H4h, H4l, H4c = b4.h.values, b4.l.values, b4.c.values
    off4 = np.timedelta64(4, 'h'); q = np.timedelta64(15, 'm')
    ext, ext_i = np.inf, -1
    zone = None; armed = False; lh, lh_i = -np.inf, -1
    res = dict(sym=e.sym, side=e.side, ib_week=e.ib_week, zone_hit=False, signal=False, killed=False)
    def select_zone(now_close):
        # последний медвежий H4 FVG: бар k закрыт к now_close, k <= бар экстремума, верх >= L, не перекрыт до экстремума
        xb = np.searchsorted(H4t, np.datetime64(T[ext_i]), side='right') - 1
        for k in range(xb, max(2, xb - 84), -1):
            if H4t[k] + off4 > now_close: continue
            if H4h[k] < H4l[k - 2]:
                top, bot = H4l[k - 2], H4h[k]
                if top < L: continue
                if (H4c[k + 1:xb + 1] > top).any(): continue
                return (top, bot)
        return None
    for i in range(len(T)):
        tclose = np.datetime64(T[i]) + q
        if l[i] < ext:
            ext, ext_i = l[i], i; armed = False; lh, lh_i = -np.inf, -1
            zone = select_zone(tclose)
        elif (tclose - np.datetime64('1970-01-01T00:00')) % off4 == np.timedelta64(0):   # закрылась H4
            if zone is None: zone = select_zone(tclose)
            elif c[i] > zone[0]:
                res['killed'] = True; break                                   # H4 закрылась выше зоны — смотрим лонг
        if zone is None: continue
        if not armed and h[i] >= zone[1]:
            armed = True; res['zone_hit'] = True
        if not armed: continue
        if h[i] > lh: lh, lh_i = h[i], i
        if i <= lh_i: continue
        # последний восходящий M15 FVG до локального хая, сформирован после лоя, не перекрыт до хая
        bot = None
        if TRIGGER == 'shift':
            for k in range(lh_i - 1, max(ext_i + 1, lh_i - 400), -1):
                if k + 2 >= i or k - 2 < 0: continue                       # фрактал должен быть подтверждён
                if l[k] < l[k - 1] and l[k] < l[k - 2] and l[k] <= l[k + 1] and l[k] <= l[k + 2]:
                    if (c[k + 1:lh_i + 1] < l[k]).any(): continue           # уже пробит до хая
                    bot = l[k]; kbot = k + 2; break
        else:
          for k in range(lh_i, max(ext_i + 2, lh_i - 400), -1):
            if l[k] > h[k - 2]:
                if (c[k + 1:lh_i + 1] < h[k - 2]).any(): continue
                bot = h[k - 2]; kbot = k; break
        if bot is None or c[i] >= bot: continue
        # сигнал на шорт
        entry, stop = c[i], lh
        f = m.loc[T[i] + pd.Timedelta('15min'):t0 + pd.Timedelta(weeks=6)]
        fh, fl = f.h.values, f.l.values
        def first(mk):
            j = np.nonzero(mk)[0]; return j[0] if len(j) else 10**9
        iS, i1, i2 = first(fh >= stop), first(fl < ext), first(fl <= L - R)
        risk = stop - entry
        res.update(lh_t=str(T[lh_i]), ext_t=str(T[ext_i]), fvg15_bot=sg * bot, fvg15_top=sg * l[kbot], fvg15_t=str(T[kbot - 2]),
                   stop_t=str(f.index[iS]) if iS < 10**9 else None, low_t=str(f.index[i1]) if i1 < 10**9 else None)
        res.update(signal=True, t=str(T[i]), entry=sg * entry, stop=sg * stop, sweep=sg * ext, zone_top=sg * zone[0], zone_bot=sg * zone[1],
                   win_low=i1 < iS, win_E1=i2 < iS, reach_E1=i2 < 10**9, stopped=iS < 10**9,
                   rr_low=(entry - ext) / risk if risk > 0 else np.nan, rr_E1=(entry - (L - R)) / risk if risk > 0 else np.nan)
        # H4 выше зоны раньше нового лоя?
        b4f = b4.loc[T[i]:]; up = b4f.index[b4f.c.values > zone[0]]
        res['h4_above_before_low'] = bool(len(up) and (i1 == 10**9 or up[0] < f.index[min(i1, len(f) - 1)]))
        break
    rows.append(res)
D = pd.DataFrame(rows); D.to_csv(OUT, index=False)
for c_ in ('zone_hit', 'signal', 'killed', 'win_low', 'win_E1', 'reach_E1', 'stopped', 'h4_above_before_low'):
    D[c_] = D[c_].fillna(False).astype(bool)
def show(nm, g):
    z = g[g.zone_hit]; s = g[g.signal]
    if not len(s): print(nm, 'событий', len(g), 'сигналов 0'); return
    ev_low = (s.win_low * s.rr_low - (~s.win_low)).mean(); ev_e1 = (s.win_E1 * s.rr_E1 - (~s.win_E1)).mean()
    print(f'{nm:22s} событий {len(g):3d} | зашли в зону {len(z):3d} | сигнал {len(s):3d} ({len(s)/max(1,len(z))*100:.0f}% от зашедших) | '
          f'новый лой раньше стопа {s.win_low.mean()*100:3.0f}% (RR мед {s.rr_low.median():.1f}, ср. {ev_low:+.2f}R) | '
          f'L-1R раньше стопа {s.win_E1.mean()*100:3.0f}% (RR мед {s.rr_E1.median():.1f}, ср. {ev_e1:+.2f}R) | дойдёт до L-1R {s.reach_E1.mean()*100:3.0f}% | '
          f'H4 выше зоны раньше нового лоя {s.h4_above_before_low.mean()*100:3.0f}%')
for nm, g in (('ETH снятие лоя', D[(D.sym == 'ETHUSDT') & (D.side == 'low')]), ('ETH обе стороны', D[D.sym == 'ETHUSDT']),
              ('9 монет снятие лоя', D[D.side == 'low']), ('9 монет обе стороны', D)):
    show(nm, g)
