"""Недельные инсайд-бары на перпетуалах Binance: что происходит после снятия одной из сторон
и какое подтверждение (D1 / H4 / H1 / M15) лучше работает для входа.

python ib_study.py <dir_with_SYMBOL.pkl> <out_dir>
Неделя: Пн 00:00 UTC. IB = неделя, у которой H <= H пред. недели и L >= L пред. недели (мать).
Событие: после закрытия IB первая сделка за его хаем или лоем (по 15m). Ждём пробоя до 8 недель.
Сторона «хай» зеркалится в «лой», чтобы считать одну и ту же логику для обеих сторон.
"""
import sys, os, json
import numpy as np, pandas as pd

SRC, OUT = sys.argv[1], sys.argv[2]
# опционально: X — искать подтверждения не от первого касания L, а от момента, когда
# вынос под L >= X·R, снят лой матери и хай IB не тронут (как сейчас на ETH)
STATE_X = float(sys.argv[3]) if len(sys.argv) > 3 else None
# RANGE=mother: уровни берутся с материнской недели (L/H матери), иначе — с самого инсайда
MODE = os.environ.get('RANGE', 'ib')
os.makedirs(OUT, exist_ok=True)
COST = 0.001          # 0,1% цены на сделку туда-обратно (комиссия taker x2 + проскальзывание)
MAXWAIT_BREAK = pd.Timedelta(weeks=8)
CONF_WINDOW = pd.Timedelta(days=7)    # подтверждение должно появиться в течение 7 дней после снятия
HOLD = pd.Timedelta(weeks=4)          # максимум удержания сделки
TFS = {'D1': '1D', 'H4': '4h', 'H1': '1h', 'M15': '15min'}

def agg(df, rule):
    return df.resample(rule, label='left', closed='left').agg(o=('o', 'first'), h=('h', 'max'), l=('l', 'min'), c=('c', 'last')).dropna()

def fractal_highs(h, n=2):
    """Индексы подтверждённых фракталов: (индекс бара фрактала, индекс бара подтверждения)."""
    out = []
    for i in range(n, len(h) - n):
        if h[i] > h[i - n:i].max() and h[i] >= h[i + 1:i + n + 1].max():
            out.append((i, i + n))
    return out

def simulate(m, t_entry, entry, sl, tp, direction):
    """direction: +1 лонг (в «нормализованной» системе цен); проверка по 15m начиная с бара после входа.
    Если в одном баре и стоп, и тейк — стоп. Возвращает R нетто и исход."""
    seg = m.loc[t_entry:t_entry + HOLD]
    seg = seg.iloc[1:] if len(seg) and seg.index[0] == t_entry else seg
    risk = abs(entry - sl)
    if risk <= 0 or len(seg) == 0: return None
    if direction > 0:
        hit_sl = np.nonzero(seg.l.values <= sl)[0]; hit_tp = np.nonzero(seg.h.values >= tp)[0]
    else:
        hit_sl = np.nonzero(seg.h.values >= sl)[0]; hit_tp = np.nonzero(seg.l.values <= tp)[0]
    i_sl = hit_sl[0] if len(hit_sl) else 10**9; i_tp = hit_tp[0] if len(hit_tp) else 10**9
    cost_R = COST * abs(entry) / risk
    if i_sl == 10**9 and i_tp == 10**9:
        ex = seg.c.values[-1]; g = (ex - entry) / risk * direction; res = 'time'
    elif i_sl <= i_tp: g = -1.0; res = 'sl'
    else: g = abs(tp - entry) / risk; res = 'tp'
    return g - cost_R, res, g

events, trades = [], []
for f in sorted(os.listdir(SRC)):
    if not f.endswith('.pkl'): continue
    sym = f[:-4]
    raw = pd.read_pickle(f'{SRC}/{f}')
    W = agg(raw, 'W-MON')
    W = W[W.index >= raw.index[0].normalize()]
    for side in ('low', 'high'):
        # зеркалим цены для стороны «хай»: работаем с -цена, тогда хай становится лоем
        m = raw if side == 'low' else pd.DataFrame({'o': -raw.o, 'h': -raw.l, 'l': -raw.h, 'c': -raw.c}, index=raw.index)
        Wm = agg(m, 'W-MON')
        frames = {k: agg(m, r) for k, r in TFS.items() if k != 'M15'}
        frames['M15'] = m
        fr = {k: (v, None) for k, v in frames.items()}
        conf_arr = {}
        for k, v in frames.items():
            fh = fractal_highs(v.h.values)
            off = pd.Timedelta(TFS[k])
            # время, с которого фрактал известен = открытие бара после подтверждающего
            conf_arr[k] = (np.array([(v.index[c] + off).value for a, c in fh]), np.array([v.h.values[a] for a, c in fh]))
        for i in range(1, len(Wm) - 1):
            mo, ib = Wm.iloc[i - 1], Wm.iloc[i]
            if not (ib.h <= mo.h and ib.l >= mo.l): continue
            t_ib_end = Wm.index[i] + pd.Timedelta(weeks=1)
            L, H = (mo.l, mo.h) if MODE == 'mother' else (ib.l, ib.h); R = H - L
            if R <= 0: continue
            fut = m.loc[t_ib_end:t_ib_end + MAXWAIT_BREAK]
            bl = np.nonzero(fut.l.values < L)[0]; bh = np.nonzero(fut.h.values > H)[0]
            if not len(bl) and not len(bh): continue
            first_low = len(bl) and (not len(bh) or bl[0] < bh[0])
            if not first_low: continue          # для этой стороны нужен первый пробой именно лоя
            t0 = fut.index[bl[0]]
            after = m.loc[t0:t0 + HOLD]
            # исходы «гонки» от уровня L
            def first(mask):
                idx = np.nonzero(mask)[0]; return after.index[idx[0]] if len(idx) else None
            t_H = first(after.h.values >= H); t_mid = first(after.h.values >= L + R / 2)
            t_ext1 = first(after.l.values <= L - R); t_ext05 = first(after.l.values <= L - R / 2)
            t_back = first(after.c.values > L)                                   # 15m закрытие обратно в диапазон
            wk_end = t0.normalize() - pd.Timedelta(days=t0.dayofweek) + pd.Timedelta(weeks=1)
            wk_close = m.c.loc[:wk_end - pd.Timedelta('15min')].iloc[-1]
            mother_broken = (m.loc[t0:wk_end].l.min() < mo.l)
            # максимальное продление за L до первого возврата к середине IB
            stop_t = t_mid or after.index[-1]
            ext = (L - m.loc[t0:stop_t].l.min()) / R
            sgn = 1 if side == 'low' else -1
            is_open = t0 + HOLD > m.index[-1]
            ev = dict(sym=sym, side=side, ib_week=str(Wm.index[i].date()), t0=str(t0), L=sgn * L, H=sgn * H, R=R,
                      R_pct=R / abs(L) * 100, weeks_to_break=(t0 - t_ib_end).days / 7,
                      same_week_break=t0 < t_ib_end + pd.Timedelta(weeks=1), mother_broken=bool(mother_broken),
                      wk_close_inside=bool(wk_close > L), wk_close_pos=(wk_close - L) / R,
                      back_inside_15m=t_back is not None,
                      mid_before_ext1=(t_mid is not None) and (t_ext1 is None or t_mid < t_ext1),
                      H_before_ext1=(t_H is not None) and (t_ext1 is None or t_H < t_ext1),
                      ext1_before_H=(t_ext1 is not None) and (t_H is None or t_ext1 < t_H),
                      reach_H=t_H is not None, reach_ext05=t_ext05 is not None, reach_ext1=t_ext1 is not None,
                      max_ext_R=ext, open=bool(is_open))
            events.append(ev)

            # ---------- подтверждения ----------
            anchor = t0
            if STATE_X is not None:
                a1 = m.loc[t0:t0 + pd.Timedelta(weeks=1)]
                rmin = np.minimum.accumulate(a1.l.values); rmax = np.maximum.accumulate(a1.h.values)
                okk = np.nonzero((rmin <= L - STATE_X * R) & (rmin < mo.l) & (rmax < H))[0]
                if not len(okk): continue
                anchor = a1.index[okk[0]]
            def add(conf, tf, kind, t_e, entry, sl, tp, d, tp_name):
                r = simulate(m, t_e, entry, sl, tp, d)
                if r is None: return
                mb_entry = bool(m.loc[t0:t_e - pd.Timedelta('15min')].l.min() < mo.l)
                trades.append(dict(mb_entry=mb_entry, sym=sym, side=side, ib_week=ev['ib_week'], conf=conf, tf=tf, kind=kind, tp=tp_name,
                                   t_entry=str(t_e), entry=sgn * entry, sl=sgn * sl, target=sgn * tp,
                                   rr=abs(tp - entry) / abs(entry - sl), net_R=r[0], gross_R=r[2], res=r[1],
                                   mother_broken=ev['mother_broken'], open=ev['open']))
            # 0) без подтверждения: лимит на L при касании, стоп L-0.5R
            if STATE_X is None:
                add('Без подтверждения: лимит на L', '-', 'rev', t0, L, L - R / 2, H, 1, 'H')
                add('Без подтверждения: лимит на L', '-', 'rev', t0, L, L - R / 2, L + R / 2, 1, 'mid')
                add('Без подтверждения: шорт пробоя на L', '-', 'cont', t0, L, L + R / 2, L - R, -1, 'ext1')
            else:
                pa = m.loc[anchor:].iloc[0]
                add('Без подтверждения: шорт по рынку сейчас', '-', 'cont', anchor, pa.c, L, L - R, -1, 'ext1')
                add('Без подтверждения: лонг по рынку сейчас', '-', 'rev', anchor, pa.c, pa.c - (L - pa.c), L + R / 2, 1, 'mid')
            for tf, (bars, frs) in fr.items():
                b = bars.loc[anchor.floor('15min'):]
                # бар, содержащий t0, начался раньше/в t0: подтверждение — со следующих закрытых баров
                tf_off = pd.Timedelta(TFS[tf])
                b = b[b.index + tf_off > anchor]
                win = b[b.index + tf_off <= anchor + CONF_WINDOW]
                if not len(win): continue
                # (а) реклейм: первое закрытие TF выше L
                rc = win.index[win.c.values > L]
                if len(rc):
                    tb = rc[0]; te = tb + tf_off
                    low_since = m.loc[t0:te - pd.Timedelta('15min')].l.min()
                    sl = low_since - 0.001 * abs(low_since); e = win.loc[tb].c
                    for tpn, tpv in (('H', H), ('mid', L + R / 2), ('2R', e + 2 * (e - sl))):
                        if tpv > e: add(f'Реклейм: закрытие {tf} обратно выше L', tf, 'rev', te, e, sl, tpv, 1, tpn)
                # (б) CHoCH: закрытие выше последнего фрактального хая, подтверждённого до этого бара
                ctimes, cprices = conf_arr[tf]
                for tb in win.index:
                    k = np.searchsorted(ctimes, tb.value, side='right') - 1
                    if k < 0: continue
                    lvl = cprices[k]
                    if win.loc[tb].c > lvl:
                        te = tb + tf_off
                        low_since = m.loc[t0:te - pd.Timedelta('15min')].l.min()
                        sl = low_since - 0.001 * abs(low_since); e = win.loc[tb].c
                        for tpn, tpv in (('H', H), ('mid', L + R / 2), ('2R', e + 2 * (e - sl))):
                            if tpv > e: add(f'CHoCH {tf}: закрытие выше свинг-хая', tf, 'rev', te, e, sl, tpv, 1, tpn)
                        break
                # (в) принятие: первое закрытие TF ниже L -> шорт, стоп над хаем бара (не ниже L)
                ac = win.index[win.c.values < L]
                if len(ac):
                    tb = ac[0]; te = tb + tf_off; e = win.loc[tb].c
                    sl = max(win.loc[tb].h, L); sl = sl + 0.001 * abs(sl)
                    for tpn, tpv in (('ext1', L - R), ('2R', e - 2 * (sl - e))):
                        if tpv < e: add(f'Принятие: закрытие {tf} ниже L', tf, 'cont', te, e, sl, tpv, -1, tpn)
    print(sym, len(events), len(trades), flush=True)

E = pd.DataFrame(events); T = pd.DataFrame(trades)
E.to_csv(f'{OUT}/events.csv', index=False); T.to_csv(f'{OUT}/trades.csv', index=False)
print(len(E), len(T))
