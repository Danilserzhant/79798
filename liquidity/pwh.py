"""PWH / PWL: хай и лой прошлой недели. python3.13 pwh.py <dir_pkl_15m> <out_prefix> [SYM ...]
WEEK=utc — неделя с понедельника 00:00 UTC (Binance); WEEK=ny — неделя с воскресенья 18:00 по Нью-Йорку (ICT).
Событие — первое снятие PWH за неделю (PWL — то же на зеркальных ценах). От момента снятия (15m свеча с хаем > PWH), горизонт — до конца следующей недели:
  rev_mid  — раньше середина прошлой недели (PM), чем столько же за уровень (PWH + (PWH − PM)); случайно ≈50%;
  rev_atr  — −0,5 недельного ATR раньше +0,5 ATR от уровня; week_back — неделя закрылась обратно ниже PWH;
  day_back — день снятия закрылся обратно ниже PWH; h4_back — 4h свеча снятия закрылась обратно ниже PWH;
  exc_atr  — максимальный вынос над PWH (в недельном ATR) до возврата к PM.
Turtle soup: первое закрытие 4h обратно ниже PWH в течение 12 свечей 4h (2 суток) после снятия -> шорт, стоп над хаем с момента снятия, цели PM / 1R / 2R.
Пробой: вход на PWH, стоп на PM, цель 1:1 (выигрыш = 1 − rev_mid), brk_cost — комиссия 0,1% в R.
Фильтры: день недели снятия, прошлая неделя узкая/инсайд, состояние прошлой недели, другая сторона уже снята, тренд (выше 20-нед. средней)."""
import sys, os, numpy as np, pandas as pd
SRC, OUT = sys.argv[1:3]
SYMS = sys.argv[3:] or ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'LTCUSDT', 'LINKUSDT']
WEEK = os.environ.get('WEEK', 'utc'); INF = 10**12; COST = 0.001
DN = ['пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс']
def first(mask):
    j = np.flatnonzero(mask); return j[0] if len(j) else INF
def state(H, L, C, PH, PL):
    return ('принятие выше' if C > PH else 'принятие ниже' if C < PL else 'обе сняты' if (H > PH and L < PL)
            else 'отказ сверху' if H > PH else 'отказ снизу' if L < PL else 'внутри')
WR, EV = [], []
for s in SYMS:
    raw = pd.read_pickle(f'{SRC}/{s}.pkl')[['o', 'h', 'l', 'c']]
    if WEEK == 'ny':
        ny = raw.index.tz_localize('UTC').tz_convert('America/New_York') + pd.Timedelta(hours=6)   # вс 18:00 NY -> пн 00:00
        loc = pd.DatetimeIndex(ny.tz_localize(None))
    else:
        loc = raw.index
    dayk = loc.normalize(); wk = (dayk - pd.to_timedelta(dayk.dayofweek, unit='D')).values
    dow = dayk.dayofweek.values
    h4k = loc.floor('4h').values
    for side in ('PWH', 'PWL'):
        m = raw if side == 'PWH' else pd.DataFrame({'o': -raw.o, 'h': -raw.l, 'l': -raw.h, 'c': -raw.c}, index=raw.index)
        h, l, c, o = m.h.values, m.l.values, m.c.values, m.o.values
        idx = np.arange(len(m))
        g = pd.Series(idx).groupby(wk); i0 = g.first().values; nn = g.size().values; ks = g.first().index
        H = np.array([h[a:a + b].max() for a, b in zip(i0, nn)]); L = np.array([l[a:a + b].min() for a, b in zip(i0, nn)])
        Cl = c[i0 + nn - 1]
        rng = pd.Series(H - L); atr = rng.rolling(14).mean().shift(1).values; avg10 = rng.rolling(10).mean().shift(1).values
        sma = pd.Series(Cl).rolling(20).mean().shift(1).values
        full = np.median(nn)
        # конец дня и конец 4h для каждого 15m бара
        day_end = pd.Series(idx).groupby(dayk.values).transform('max').values
        h4_end = pd.Series(idx).groupby(h4k).transform('max').values
        for j in range(3, len(ks) - 1):
            if nn[j] < .9 * full or nn[j - 1] < .9 * full or not atr[j] == atr[j]: continue
            if pd.Timestamp(ks[j]) - pd.Timestamp(ks[j - 1]) != pd.Timedelta(days=7): continue
            A = atr[j]; PH, PL = H[j - 1], L[j - 1]; PM = (PH + PL) / 2
            a, e = i0[j], i0[j] + nn[j]
            e2 = i0[j + 1] + nn[j + 1] if pd.Timestamp(ks[j + 1]) - pd.Timestamp(ks[j]) == pd.Timedelta(days=7) else e
            iH = first(h[a:e] > PH); iL = first(l[a:e] < PL)
            pst = state(H[j - 1], L[j - 1], Cl[j - 1], H[j - 2], L[j - 2])
            if side == 'PWH':
                WR.append(dict(sym=s, t=ks[j], tH=iH < INF, tL=iL < INF, first='H' if iH < iL else 'L' if iL < iH else '-', prev_state=pst,
                               pos=(o[a] - PL) / (PH - PL) if PH > PL else .5, close_pos=(Cl[j] - PL) / (PH - PL) if PH > PL else .5,
                               dowH=DN[dow[a + iH]] if iH < INF else None, dowL=DN[dow[a + iL]] if iL < INF else None))
            if iH == INF: continue
            t = a + iH
            hh, ll = h[t:e2], l[t:e2]
            r1, r2 = first(ll <= PM), first(hh >= PH + (PH - PM))
            a1, a2 = first(ll <= PH - .5 * A), first(hh >= PH + .5 * A)
            run_hi = np.maximum.accumulate(hh)
            ev = dict(sym=s, side=side, t=ks[j], dow=DN[dow[t]], prev_state=pst, other_first=bool(iL < iH),
                      week_back=bool(Cl[j] < PH), day_back=bool(c[day_end[t]] < PH), h4_back=bool(c[h4_end[t]] < PH),
                      above_sma=bool(Cl[j - 1] > sma[j]) if sma[j] == sma[j] else np.nan,
                      narrow=bool((PH - PL) < .7 * avg10[j]) if avg10[j] == avg10[j] else np.nan,
                      prev_inside=bool(H[j - 1] <= H[j - 2] and L[j - 1] >= L[j - 2]),
                      rev_mid=np.nan if r1 == r2 == INF else float(r1 < r2), rev_atr=np.nan if a1 == a2 == INF else float(a1 < a2),
                      exc_atr=(run_hi[r1] - PH) / A if r1 < INF else np.nan, brk_cost=COST * abs(PH) / (PH - PM) if PH > PM else np.nan)
            # turtle soup по 4h
            ends = np.unique(h4_end[t:e])[:12]
            k = next((x for x in ends if c[x] < PH), None)
            if k is not None:
                entry = c[k]; stop = h[t:k + 1].max(); risk = stop - entry
                if risk > 0:
                    def outcome(tgt):
                        s_, g_ = first(h[k + 1:e2] >= stop), first(l[k + 1:e2] <= tgt)
                        if s_ == g_ == INF: return (entry - c[e2 - 1]) / risk
                        return -1.0 if s_ <= g_ else (entry - tgt) / risk
                    cost = COST * abs(entry) / risk
                    ev.update(ts=True, ts_R_mid=(outcome(PM) - cost) if PM < entry else np.nan, ts_R_1=outcome(entry - risk) - cost,
                              ts_R_2=outcome(entry - 2 * risk) - cost, ts_risk_atr=risk / A)
            EV.append(ev)
    print(s, len(EV), flush=True)
pd.DataFrame(WR).to_csv(f'{OUT}_weeks.csv', index=False); pd.DataFrame(EV).to_csv(f'{OUT}_ev.csv', index=False)
