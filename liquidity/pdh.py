"""PDH / PDL: как цена ведёт себя у хая и лоя вчерашнего дня. python3.13 pdh.py <dir_pkl_15m> <out_prefix> [SYM ...]
DAY=utc — дневная свеча 00:00 UTC (Binance); DAY=ny — день от полуночи Нью-Йорка. Сессия снятия — по нью-йоркскому часу:
Азия 18:00–02:00, Лондон 02:00–07:00, NY утро 07:00–12:00, NY день 12:00–18:00.
Событие — первое снятие PDH за день (PDL — то же на зеркальных ценах, side=PDL). От момента снятия (15m свеча с хаем > PDH):
  rev_mid  — раньше середина вчерашнего дня (PM), чем продолжение на ту же дистанцию за PDH (PDH + (PDH − PM)) — у случайного графика ≈50%;
  rev_atr  — −0,5 ATR раньше +0,5 ATR от PDH; day_back — день закрылся обратно ниже PDH; wick — свеча снятия закрылась обратно ниже PDH;
  exc_atr  — максимальный вынос над PDH (в ATR) до возврата к PM (только если PM достигнут).
Сделка turtle soup: первое закрытие 15m обратно ниже PDH в течение 16 свечей (4 ч) после снятия -> шорт на закрытии, стоп над хаем с момента снятия,
цели PM / 1R / 2R; исход до конца следующего дня; стоп и цель в одной свече — стоп; комиссия 0,1%.
Пробой (brk): вход на снятии PDH, стоп на PM, цель PDH + (PDH − PM) — выигрыш = 1 − rev_mid; brk_cost — комиссия в R.
Пишет <out_prefix>_days.csv (по дням) и <out_prefix>_ev.csv (события)."""
import sys, os, numpy as np, pandas as pd
SRC, OUT = sys.argv[1:3]
SYMS = sys.argv[3:] or ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'LTCUSDT', 'LINKUSDT']
DAY = os.environ.get('DAY', 'utc'); INF = 10**12; COST = 0.001
def first(mask):
    j = np.flatnonzero(mask); return j[0] if len(j) else INF
def sess(hny):
    return 'Азия' if (hny >= 18 or hny < 2) else 'Лондон' if hny < 7 else 'NY утро' if hny < 12 else 'NY день'
def state(H, L, C, PH, PL):
    return ('принятие выше' if C > PH else 'принятие ниже' if C < PL else 'обе сняты' if (H > PH and L < PL)
            else 'отказ сверху' if H > PH else 'отказ снизу' if L < PL else 'внутри')
DR, EV = [], []
for s in SYMS:
    raw = pd.read_pickle(f'{SRC}/{s}.pkl')[['o', 'h', 'l', 'c']]
    nyi = raw.index.tz_localize('UTC').tz_convert('America/New_York')
    hny_all = nyi.hour.values
    key = (nyi.normalize().tz_localize(None) if DAY == 'ny' else raw.index.normalize())
    for side in ('PDH', 'PDL'):
        m = raw if side == 'PDH' else pd.DataFrame({'o': -raw.o, 'h': -raw.l, 'l': -raw.h, 'c': -raw.c}, index=raw.index)
        h, l, c, o = m.h.values, m.l.values, m.c.values, m.o.values
        g = pd.Series(np.arange(len(m))).groupby(np.asarray(key))
        i0 = g.first().values; nn = g.size().values; days = g.first().index
        H = np.array([h[a:a + b].max() for a, b in zip(i0, nn)]); L = np.array([l[a:a + b].min() for a, b in zip(i0, nn)])
        Cl = c[i0 + nn - 1]; Op = o[i0]
        atr = pd.Series(H - L).rolling(14).mean().shift(1).values
        sma = pd.Series(Cl).rolling(20).mean().shift(1).values
        full = np.median(nn)
        for j in range(3, len(days) - 1):
            if nn[j] < .9 * full or nn[j - 1] < .9 * full or (days[j] - days[j - 1]) != pd.Timedelta(days=1) or not atr[j] == atr[j]: continue
            A = atr[j]; PH, PL = H[j - 1], L[j - 1]; PM = (PH + PL) / 2; O = Op[j]
            a, e = i0[j], i0[j] + nn[j]; e2 = i0[j + 1] + nn[j + 1] if (days[j + 1] - days[j]) == pd.Timedelta(days=1) else e
            iH = first(h[a:e] > PH); iL = first(l[a:e] < PL)
            pst = state(H[j - 1], L[j - 1], Cl[j - 1], H[j - 2], L[j - 2])
            pos = (O - PL) / (PH - PL) if PH > PL else .5
            if side == 'PDH':
                DR.append(dict(sym=s, t=days[j], tH=iH < INF, tL=iL < INF, first='H' if iH < iL else 'L' if iL < iH else '-',
                               pos=pos, prev_state=pst, close_pos=(Cl[j] - PL) / (PH - PL) if PH > PL else .5,
                               sessH=sess(hny_all[a + iH]) if iH < INF else None, sessL=sess(hny_all[a + iL]) if iL < INF else None))
            if iH == INF: continue
            t = a + iH                                                         # свеча снятия
            other_first = iL < iH                                              # другая сторона уже снята сегодня
            hh, ll = h[t:e2], l[t:e2]
            ext = PH + (PH - PM)
            r1, r2 = first(ll <= PM), first(hh >= ext)
            a1, a2 = first(ll <= PH - .5 * A), first(hh >= PH + .5 * A)
            run_hi = np.maximum.accumulate(hh)
            ev = dict(sym=s, side=side, t=days[j], sess=sess(hny_all[t]), hny=int(hny_all[t]), pos=pos, prev_state=pst, other_first=other_first,
                      wick=c[t] < PH, day_back=Cl[j] < PH, above_sma=Cl[j - 1] > sma[j] if sma[j] == sma[j] else np.nan,
                      rng_atr=(PH - PL) / A, rev_mid=np.nan if r1 == r2 == INF else float(r1 < r2), rev_atr=np.nan if a1 == a2 == INF else float(a1 < a2),
                      exc_atr=(run_hi[r1] - PH) / A if r1 < INF else np.nan, sweep_bar_frac=iH / nn[j],
                      brk_cost=COST * abs(PH) / (PH - PM) if PH > PM else np.nan, prev_inside=bool(H[j - 1] <= H[j - 2] and L[j - 1] >= L[j - 2]))
            # turtle soup
            k = first(c[t:min(t + 16, e)] < PH)
            if k < INF:
                ti = t + k; entry = c[ti]; stop = h[t:ti + 1].max(); risk = stop - entry
                if risk > 0:
                    def outcome(tgt):
                        s_, g_ = first(h[ti + 1:e2] >= stop), first(l[ti + 1:e2] <= tgt)
                        if s_ == g_ == INF: return (entry - c[e2 - 1]) / risk
                        return -1.0 if s_ <= g_ else (entry - tgt) / risk
                    cost = COST * abs(entry) / risk
                    ev.update(ts=True, ts_rr_mid=(entry - PM) / risk, ts_R_mid=(outcome(PM) - cost) if PM < entry else np.nan,
                              ts_R_1=outcome(entry - risk) - cost, ts_R_2=outcome(entry - 2 * risk) - cost, ts_risk_atr=risk / A, ts_wait=k)
            EV.append(ev)
    print(s, len(EV), flush=True)
pd.DataFrame(DR).to_csv(f'{OUT}_days.csv', index=False); pd.DataFrame(EV).to_csv(f'{OUT}_ev.csv', index=False)
