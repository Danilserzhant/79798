"""Недельная (LEG=W, FVG на D1) или дневная (LEG=D, FVG на H4) фрактальная ножка; откат -> формирование нового бычьего FVG.
Ножка, подтверждение фрактала и зеркало для медвежьих — как в fvg_inv_w.py.
Сигнал: бычий FVG (L[k] > H[k-2]) на ТФ FVG, первая свеча FVG (k-2) не раньше бара экстремума отката,
сформирован после подтверждения фрактала, пока хай ножки не обновлён и лой не сломан. Первый такой FVG на ножку.
Вход A — закрытие свечи k; вход B — лимитка на верхе FVG (L[k]) в течение 10 баров ТФ FVG, если раньше не обновлён хай ножки.
Стоп под экстремумом отката (минимум до свечи k включительно). Цели: 1R и хай ножки. 15m, до 26 периодов ножки; стоп и цель в одной свече — стоп.
python fvg_new_w.py <dir_pkl_15m> <out_csv> [SYM ...]"""
import sys, os, numpy as np, pandas as pd
SRC, OUT = sys.argv[1:3]
SYMS = sys.argv[3:] or ['ETHUSDT', 'BTCUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'LTCUSDT', 'LINKUSDT']
INF = 10**12; COST = 0.001
LEG = os.environ.get('LEG', 'W')
FV = {'W': '1D', 'D': '4h'}[LEG]; LEGBARS = {'W': 672, 'D': 96}[LEG]; PERFV = {'W': 7, 'D': 6}[LEG]
def first(mask, off=0):
    j = np.flatnonzero(mask); return off + j[0] if len(j) else INF
def outcome(h, l, t0, e0, entry, stop, tgt):
    risk = entry - stop
    iS = first(l[t0:e0] <= stop); iT = first(h[t0:e0] >= tgt); i1 = first(h[t0:e0] >= entry + risk)
    return (iT < iS) if min(iT, iS) < INF else None, (i1 < iS) if min(i1, iS) < INF else None
rows = []
for s in SYMS:
    raw = pd.read_pickle(f'{SRC}/{s}.pkl')[['o', 'h', 'l', 'c']]
    for side in ('bull', 'bear'):
        m = raw if side == 'bull' else pd.DataFrame({'o': -raw.o, 'h': -raw.l, 'l': -raw.h, 'c': -raw.c}, index=raw.index)
        h, l = m.h.values, m.l.values; pos = np.arange(len(m))
        d = pd.DataFrame({'o': m.o.values, 'h': h, 'l': l, 'c': m.c.values, 'p': pos}, index=m.index).resample(FV, label='left', closed='left').agg(
            o=('o', 'first'), h=('h', 'max'), l=('l', 'min'), c=('c', 'last'), i0=('p', 'first'), n=('p', 'size')).dropna()
        d = d[d.n >= .9 * d.n.median()]
        DH, DL, DC, DI, DN = d.h.values, d.l.values, d.c.values, d.i0.values.astype(int), d.n.values.astype(int); DT = d.index
        wk = (DT.normalize() - pd.to_timedelta(DT.dayofweek, unit='D')) if LEG == 'W' else DT.normalize()
        w = pd.DataFrame({'h': DH, 'l': DL, 'di': np.arange(len(d))}, index=DT).groupby(wk).agg(h=('h', 'max'), l=('l', 'min'), d0=('di', 'first'), nd=('di', 'size'))
        w = w[w.nd >= PERFV - 1]
        WH, WL, WD0, WND = w.h.values, w.l.values, w.d0.values.astype(int), w.nd.values.astype(int)
        fH = [j for j in range(1, len(w) - 1) if WH[j] > WH[j - 1] and WH[j] > WH[j + 1]]
        fL = [j for j in range(1, len(w) - 1) if WL[j] < WL[j - 1] and WL[j] < WL[j + 1]]
        for jb in fH:
            lows = [a for a in fL if a < jb]
            if not lows or jb + 2 >= len(w): continue
            ja = lows[-1]; FH, FL = WH[jb], WL[ja]
            if WH[ja:jb].max() > FH or WL[ja + 1:jb + 1].min() < FL: continue
            R = FH - FL
            dFH = WD0[jb] + int(np.argmax(DH[WD0[jb]:WD0[jb] + WND[jb]]))
            dconf = WD0[jb + 2]; dend = min(len(d), dconf + 26 * PERFV)
            ext, ext_d = np.inf, -1; sig = None
            for k in range(dFH + 1, dend):
                if DH[k] > FH or DL[k] < FL: break
                if DL[k] < ext: ext, ext_d = DL[k], k
                if k >= dconf and k - 2 >= ext_d and k - 2 > dFH and DL[k] > DH[k - 2]:
                    sig = k; break
            if sig is None: continue
            k = sig; top, bot = DL[k], DH[k - 2]
            t0 = DI[k] + DN[k]; e0 = min(len(h), t0 + 26 * LEGBARS)
            base = dict(leg=LEG, sym=s, side=side, t=DT[k], depth=(FH - ext) / R, fvg_size_R=(top - bot) / R)
            # A: вход на закрытии
            entry = DC[k]; risk = entry - ext
            if risk > 0 and FH > entry:
                wT, w1 = outcome(h, l, t0, e0, entry, ext, FH)
                rows.append(dict(base, entry_type='A', rr=(FH - entry) / risk, winT=wT, win1=w1, cost_R=COST * abs(entry) / risk))
            # B: лимитка на верхе FVG
            lim_end = min(len(h), t0 + 10 * int(np.median(DN)))
            iF = first(l[t0:lim_end] <= top, t0); iX = first(h[t0:lim_end] > FH, t0)
            if iF < iX and iF < INF:
                entry = top; risk = entry - ext
                if risk > 0 and FH > entry:
                    if l[iF] <= ext: wT, w1 = False, False                         # лимитка и стоп в одной свече
                    else: wT, w1 = outcome(h, l, iF + 1, min(len(h), iF + 26 * LEGBARS), entry, ext, FH)
                    rows.append(dict(base, entry_type='B', rr=(FH - entry) / risk, winT=wT, win1=w1, cost_R=COST * abs(entry) / risk))
    print(s, len(rows), flush=True)
pd.DataFrame(rows).to_csv(OUT, index=False)
