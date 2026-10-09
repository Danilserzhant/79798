"""Типы недель и как их узнать по дням. python week_types.py <dir_pkl_15m> <out_csv> [SYM ...]
Тип недели (задним числом), cp — где закрылась неделя в своём диапазоне (0 — лой, 1 — хай):
  cp ≥ 2/3: «бычья трендовая» (лой пн–вт) / «бычий разворот» (лой ср–чт) / «бычья поздняя» (лой пт–вс);
  cp ≤ 1/3: то же для медвежьих по дню хая; середина: «сжатие» (диапазон < 0,8 среднего за 10 недель) или «пила».
Признаки на закрытие дня k (0=пн…3=чт): pos — где цена в диапазоне недели-до-k (терции), ext — что сделал день k с диапазоном
(новый хай / новый лой / оба / инсайд; для пн — относительно воскресенья), pw — сняты ли хай/лой прошлой недели к дню k, above — выше открытия недели."""
import sys, numpy as np, pandas as pd
SRC, OUT = sys.argv[1:3]
SYMS = sys.argv[3:] or ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'LTCUSDT', 'LINKUSDT']
def wtype(cp, lo_day, hi_day, small):
    if cp >= 2 / 3: return 'бычья трендовая' if lo_day <= 1 else 'бычий разворот' if lo_day <= 3 else 'бычья поздняя'
    if cp <= 1 / 3: return 'медвежья трендовая' if hi_day <= 1 else 'медвежий разворот' if hi_day <= 3 else 'медвежья поздняя'
    return 'сжатие' if small else 'пила'
rows = []
for s in SYMS:
    m = pd.read_pickle(f'{SRC}/{s}.pkl')[['o', 'h', 'l', 'c']]
    g = m.groupby(m.index.normalize())
    D = g.agg(o=('o', 'first'), h=('h', 'max'), l=('l', 'min'), c=('c', 'last'), n=('c', 'size')); D = D[D.n >= 90]
    W = {k: x for k, x in D.groupby(D.index - pd.to_timedelta(D.index.dayofweek, unit='D'))}; ks = sorted(W)
    rng_hist = []
    for i in range(1, len(ks)):
        w, pw = W[ks[i]], W[ks[i - 1]]
        if len(w) < 7 or len(pw) < 7 or ks[i] - ks[i - 1] != pd.Timedelta(days=7): rng_hist = []; continue
        O, H, L, C = w.o.iloc[0], w.h.max(), w.l.min(), w.c.iloc[-1]; R = H - L
        avg = np.mean(rng_hist[-10:]) if len(rng_hist) >= 5 else np.nan
        rng_hist.append(R)
        if not avg == avg or R <= 0: continue
        cp = (C - L) / R; lo_day, hi_day = int(np.argmin(w.l.values)), int(np.argmax(w.h.values))
        PH, PL = pw.h.max(), pw.l.min(); prev_sun = pw.iloc[-1]
        r = dict(sym=s, t=ks[i], type=wtype(cp, lo_day, hi_day, R < .8 * avg), cp=cp, lo_day=lo_day, hi_day=hi_day, rng_rel=R / avg,
                 bull=C > O, took_PH=H > PH, took_PL=L < PL, prev_inside=pw.h.max() <= W[ks[i - 2]].h.max() and pw.l.min() >= W[ks[i - 2]].l.min() if i >= 2 and len(W[ks[i - 2]]) == 7 else np.nan)
        for k in range(4):
            hs, ls = w.h.iloc[:k + 1].max(), w.l.iloc[:k + 1].min(); ck = w.c.iloc[k]
            pos = (ck - ls) / (hs - ls) if hs > ls else .5
            r[f'pos{k}'] = 'верх' if pos >= 2 / 3 else 'низ' if pos <= 1 / 3 else 'середина'
            ref_h, ref_l = (prev_sun.h, prev_sun.l) if k == 0 else (w.h.iloc[:k].max(), w.l.iloc[:k].min())
            nh, nl = w.h.iloc[k] > ref_h, w.l.iloc[k] < ref_l
            r[f'ext{k}'] = 'оба' if nh and nl else 'новый хай' if nh else 'новый лой' if nl else 'инсайд'
            th, tl = hs > PH, ls < PL
            r[f'pw{k}'] = 'сняты оба' if th and tl else 'снят PWH' if th else 'снят PWL' if tl else 'внутри PW'
            r[f'above{k}'] = ck > O
            r[f'path{k}'] = (ck - L) / R                                       # где цена на закрытии дня k в итоговом диапазоне недели
        for k in range(4, 7): r[f'path{k}'] = (w.c.iloc[k] - L) / R
        rows.append(r)
    print(s, len(rows), flush=True)
pd.DataFrame(rows).to_csv(OUT, index=False)
