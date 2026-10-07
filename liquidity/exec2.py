"""Исполнение по BIAS: H1 FVG + M5 слом последнего 3-свечного фрактала перед экстремумом.
BIAS периода P (D/W) = состояние закрытия прошлого периода; бычий -> цель хай прошлого периода, отмена — снят его лой.
Медвежьи — зеркально (цены с минусом). Группы: with / none / against (тот же лонг при медвежьем BIAS).
Зона: бычий H1 FVG (L[k] > H[k-2], 3 свечи H1), первое касание после формирования (не старше AGE периодов),
жива до закрытия H1 ниже низа. После касания: экстремум = минимум с момента касания; сигнал — закрытие M5 выше
последнего 3-свечного фрактального хая (H[q] > H[q-1], H[q] > H[q+1]) до экстремума. Вход на закрытии, стоп под экстремумом,
цель — хай прошлого периода; нет исхода к концу периода — выход по закрытию. Стоп и цель в одной свече — стоп. Комиссия 0.1%.
Одна сделка за период (первый сигнал). python exec2.py <dir_pkl_5m> <out_csv> [SYM ...]"""
import sys, os, numpy as np, pandas as pd
SRC, OUT = sys.argv[1:3]
SYMS = sys.argv[3:] or ['ETHUSDT', 'BTCUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'LTCUSDT', 'LINKUSDT']
COST = 0.001; AGE = {'D': 3, 'W': 2}
BULL, BEAR = {'принятие выше', 'отказ снизу'}, {'принятие ниже', 'отказ сверху'}
INF = 10**12
def state(h, l, c, PH, PL):
    if c > PH: return 'принятие выше'
    if c < PL: return 'принятие ниже'
    if h > PH and l < PL: return 'обе сняты'
    if h > PH: return 'отказ сверху'
    if l < PL: return 'отказ снизу'
    return 'внутри'
def first(mask, off=0):
    j = np.flatnonzero(mask); return off + j[0] if len(j) else INF
rows = []
for s in SYMS:
    raw = pd.read_pickle(f'{SRC}/{s}.pkl')[['o', 'h', 'l', 'c']]
    for mirror in (False, True):
        m = raw if not mirror else pd.DataFrame({'o': -raw.o, 'h': -raw.l, 'l': -raw.h, 'c': -raw.c}, index=raw.index)
        H, L, C = m.h.values, m.l.values, m.c.values; T = m.index.values; N = len(m)
        ar = np.arange(N)
        fh = np.zeros(N, bool); fh[1:-1] = (H[1:-1] > H[:-2]) & (H[1:-1] > H[2:])
        lf = np.maximum.accumulate(np.where(fh, ar, -1))                         # последний фрактал с индексом <= i
        # H1 FVG
        h1 = m.resample('1h', label='left', closed='left').agg(h=('h', 'max'), l=('l', 'min'), c=('c', 'last')).dropna()
        hH, hL, hC, hT = h1.h.values, h1.l.values, h1.c.values, h1.index.values
        h1_end_idx = np.searchsorted(T, hT + np.timedelta64(1, 'h'))            # первый 5m бар после закрытия H1-свечи
        fvgs = []
        for k in range(2, len(h1)):
            if hL[k] > hH[k - 2]:
                top, bot = hL[k], hH[k - 2]; a = h1_end_idx[k]
                if a >= N: continue
                inv = np.flatnonzero(hC[k + 1:] < bot); inv_i = h1_end_idx[k + 1 + inv[0]] if len(inv) else N   # бар после H1-закрытия ниже низа
                tch = first(L[a:inv_i] <= top, a)
                if tch < inv_i: fvgs.append((tch, inv_i, top, bot, a))
        fvgs.sort()
        ft = np.array([f[0] for f in fvgs])
        for P in ('D', 'W'):
            k = (m.index.normalize() - pd.to_timedelta(m.index.dayofweek, unit='D')) if P == 'W' else m.index.normalize()
            g = pd.DataFrame({'h': H, 'l': L, 'c': C, 'p': ar}, index=m.index).groupby(k)
            b = g.agg(h=('h', 'max'), l=('l', 'min'), c=('c', 'last'), i0=('p', 'first'), n=('p', 'size'))
            full = b.n.median(); per = int(full)
            for j in range(2, len(b)):
                if b.n.iloc[j] < .9 * full or b.n.iloc[j - 1] < .9 * full: continue
                st = state(b.h.iloc[j - 1], b.l.iloc[j - 1], b.c.iloc[j - 1], b.h.iloc[j - 2], b.l.iloc[j - 2])
                grp = 'with' if st in BULL else 'against' if st in BEAR else 'none'
                TGT, INV = b.h.iloc[j - 1], b.l.iloc[j - 1]
                s0 = int(b.i0.iloc[j]); e0 = s0 + int(b.n.iloc[j])
                stop_at = min(first(H[s0:e0] >= TGT, s0), first(L[s0:e0] < INV, s0), e0)
                # касания FVG в пределах периода до отмены/достижения цели
                lo_i, hi_i = np.searchsorted(ft, s0), np.searchsorted(ft, stop_at)
                best = None
                for f in fvgs[lo_i:hi_i]:
                    tch, inv_i, top, bot, a = f
                    if s0 - a > AGE[P] * per or top >= TGT: continue
                    w0, w1 = tch, min(inv_i, stop_at)
                    if w1 <= w0: continue
                    if best is not None and w0 >= best[0]: break
                    Lw = L[w0:w1]; cm = np.minimum.accumulate(Lw)
                    ext = np.maximum.accumulate(np.where(Lw == cm, np.arange(len(Lw)), 0)) + w0      # индекс экстремума на каждом баре
                    q = lf[np.maximum(ext - 1, 0)]
                    ok = (q >= 0) & (q < ext)
                    thr = np.where(ok, H[np.maximum(q, 0)], np.inf)
                    sig = np.flatnonzero(C[w0:w1] > thr)
                    if len(sig):
                        i = w0 + sig[0]
                        if best is None or i < best[0]: best = (i, ext[sig[0]], top, bot, a, tch)
                if best is None: continue
                i, ex, top, bot, a, tch = best
                entry, stop = C[i], L[ex]; risk = entry - stop
                if risk <= 0 or TGT <= entry: continue
                rr = (TGT - entry) / risk
                iS, iT = first(L[i + 1:e0] <= stop, i + 1), first(H[i + 1:e0] >= TGT, i + 1)
                res = -1.0 if iS <= iT and iS < INF else rr if iT < INF else (C[e0 - 1] - entry) / risk
                rows.append(dict(sym=s, P=P, mirror=mirror, group=grp, state=st, t=T[i], hour=pd.Timestamp(T[i]).hour, rr=rr,
                                 R=res - COST * abs(entry) / risk, win=res == rr, stopped=res == -1.0, risk_pct=risk / abs(entry),
                                 fvg_pos=(top - INV) / (TGT - INV), fvg_size_pct=(top - bot) / abs(entry),
                                 ext_in_fvg=bool(stop >= bot), wait_bars=i - tch))
    print(s, len(rows), flush=True)
pd.DataFrame(rows).to_csv(OUT, index=False)
