"""Поиск сетапа с матожиданием +1R на базе пробоя PWH / PWL. python3.13 setup1r.py <dir_pkl_15m> <out_csv> [SYM ...]
Событие — первое снятие PWH за неделю (PWL — то же на зеркальных ценах). D = PWH − середина прошлой недели (PM).
Вход: stop — стоп-ордер на PWH в момент снятия; retest — после закрытия 4h выше PWH лимит на PWH (ретест) до конца недели.
Стоп: PWH − f·D, f = 1 / 0.5 / 0.25. Цель: k·риск, k = 1 / 2 / 3 / 5, или 0 — без цели, выход по закрытию горизонта.
Горизонт: hz = 1 — до конца следующей недели, hz = 2 — ещё неделя. be — после +1R стоп в безубыток (только k ≥ 2 и k = 0).
В свече входа стоп-ордера проверяется только закрытие (порядок внутри 15m неизвестен), цель — со следующей свечи.
Стоп и цель в одной свече — стоп. Комиссия 0,1% от цены входа, в R. Пишет по строке на (событие × вариант)."""
import sys, os, numpy as np, pandas as pd
SRC, OUT = sys.argv[1:3]
SYMS = sys.argv[3:] or ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'LTCUSDT', 'LINKUSDT']
WEEK = os.environ.get('WEEK', 'utc'); INF = 10**12; COST = 0.001
DN = ['пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс']
FS, KS = (1.0, 0.5, 0.25), (1, 2, 3, 5, 0)
def first(mask):
    j = np.flatnonzero(mask); return j[0] if len(j) else INF
def sim(h, l, c, j0, entry, stop, k, be, only_close_first):
    """Лонг с входом в свече j0. Возвращает R без комиссии."""
    risk = entry - stop
    if only_close_first and c[0] <= stop: return -1.0
    if not only_close_first and l[0] <= stop: return -1.0
    hh, ll, cc = h[1:], l[1:], c[1:]
    tgt = entry + k * risk if k else np.inf
    s_, g_ = first(ll <= stop), first(hh >= tgt)
    if be and (k == 0 or k >= 2):
        b = first(hh >= entry + risk)
        if b < min(s_, g_):                      # дошли до +1R раньше стопа и цели -> стоп в безубыток после этой свечи
            s2 = first(ll[b + 1:] <= entry); s2 = b + 1 + s2 if s2 < INF else INF
            g2 = g_
            if s2 == g2 == INF: return (cc[-1] - entry) / risk if not k else (cc[-1] - entry) / risk
            return 0.0 if s2 <= g2 else k
    if s_ == g_ == INF: return (cc[-1] - entry) / risk if len(cc) else 0.0
    return -1.0 if s_ <= g_ else float(k)
ROWS = []
btc = None
for s in SYMS:
    raw = pd.read_pickle(f'{SRC}/{s}.pkl')[['o', 'h', 'l', 'c']]
    if WEEK == 'ny':
        loc = pd.DatetimeIndex((raw.index.tz_localize('UTC').tz_convert('America/New_York') + pd.Timedelta(hours=6)).tz_localize(None))
    else:
        loc = raw.index
    dayk = loc.normalize(); wk = (dayk - pd.to_timedelta(dayk.dayofweek, unit='D')).values; dow = dayk.dayofweek.values
    h4k = loc.floor('4h').values; idx = np.arange(len(raw))
    h4_end = pd.Series(idx).groupby(h4k).transform('max').values
    wc = pd.Series(raw.c.values).groupby(wk).last()
    if s == 'BTCUSDT' or btc is None and s == SYMS[0]: btc = wc
    for side in ('PWH', 'PWL'):
        sg = 1 if side == 'PWH' else -1
        h, l, c = (raw.h.values, raw.l.values, raw.c.values) if sg == 1 else (-raw.l.values, -raw.h.values, -raw.c.values)
        g = pd.Series(idx).groupby(wk); i0 = g.first().values; nn = g.size().values; ks = g.first().index
        H = np.array([h[a:a + b].max() for a, b in zip(i0, nn)]); L = np.array([l[a:a + b].min() for a, b in zip(i0, nn)])
        Cl = c[i0 + nn - 1]
        rng = pd.Series(H - L); atr = rng.rolling(14).mean().shift(1).values; avg10 = rng.rolling(10).mean().shift(1).values
        sma = pd.Series(Cl).rolling(20).mean().shift(1).values
        full = np.median(nn); seven = pd.Timedelta(days=7)
        bt = btc.reindex(ks).values if btc is not None else np.full(len(ks), np.nan)
        for j in range(5, len(ks) - 2):
            if nn[j] < .9 * full or nn[j - 1] < .9 * full or not atr[j] == atr[j]: continue
            if pd.Timestamp(ks[j]) - pd.Timestamp(ks[j - 1]) != seven: continue
            PH, PL = H[j - 1], L[j - 1]; PM = (PH + PL) / 2; D = PH - PM
            if D <= 0: continue
            a, e = i0[j], i0[j] + nn[j]
            ends = [e]
            for q in (1, 2):
                ok = pd.Timestamp(ks[j + q]) - pd.Timestamp(ks[j + q - 1]) == seven
                ends.append(i0[j + q] + nn[j + q] if ok else ends[-1])
            iH = first(h[a:e] > PH)
            if iH == INF: continue
            t = a + iH
            bm = (bt[j - 1] / bt[j - 5] - 1) if bt[j - 5] == bt[j - 5] else np.nan
            base = dict(sym=s, side=side, t=ks[j], dow=DN[dow[t]], dowi=int(dow[t]),
                        narrow=float((PH - PL) < .7 * avg10[j]) if avg10[j] == avg10[j] else np.nan,
                        trend=float(Cl[j - 1] > sma[j]) if sma[j] == sma[j] else np.nan,
                        btc_mom=float(sg * bm > 0) if bm == bm else np.nan, other=float(first(l[a:e] < PL) < iH),
                        D_atr=D / atr[j])
            # ретест: первое закрытие 4h выше PWH после снятия, затем первое касание PWH до конца недели
            conf = next((x for x in np.unique(h4_end[t:e]) if c[x] > PH), None)
            rt = None
            if conf is not None and conf + 1 < e:
                f_ = first(l[conf + 1:e] <= PH); rt = conf + 1 + f_ if f_ < INF else None
            for hz in (1, 2):
                E = ends[hz]
                for f in FS:
                    stop = PH - f * D
                    for mode, j0, oc in (('stop', t, True), ('retest', rt, False)):
                        if j0 is None: continue
                        cost = COST * abs(PH) / (f * D)
                        for k in KS:
                            for be in ((0, 1) if (k == 0 or k >= 2) else (0,)):
                                r = sim(h[j0:E], l[j0:E], c[j0:E], 0, PH, stop, k, be, oc)
                                ROWS.append(dict(base, mode=mode, hz=hz, f=f, k=k, be=be, R=r - cost, cost=cost))
    print(s, len(ROWS), flush=True)
pd.DataFrame(ROWS).to_csv(OUT, index=False)
