"""Недельная ножка (3-свечной фрактальный лой -> фрактальный хай), откат -> инверсия последнего медвежьего D1 FVG.
FVG: медвежий на D1 (H[k] < L[k-2]), верх = L[k-2], низ = H[k], сформирован в откате (k-2 >= день хая ножки).
Выбор: на каждом новом экстремуме отката (новый дневной лой) — самый свежий валидный FVG с k <= день экстремума;
если свежего нет — остаётся прошлый. Валидность (BODY): strict — ни одно тело (max(o,c)) после k не заходило выше низа FVG;
half — ни одно тело не доходило до середины; none — без фильтра.
Сигнал: дневное закрытие выше верха текущего FVG, только после подтверждения фрактала (с открытия недели jb+2),
пока хай ножки не обновлён и лой ножки не сломан. Вход на закрытии, стоп под экстремумом отката, цель — хай ножки.
Исход по 15m до 26 недель; одновременно стоп и цель — стоп. Медвежьи ножки — зеркально. Одна сделка на ножку.
python fvg_inv_w.py <dir_pkl_15m> <out_csv> [SYM ...]"""
import sys, numpy as np, pandas as pd
SRC, OUT = sys.argv[1:3]
SYMS = sys.argv[3:] or ['ETHUSDT', 'BTCUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'LTCUSDT', 'LINKUSDT']
import os
INF = 10**12; COST = 0.001
LEG = os.environ.get('LEG', 'W')                     # ТФ ножки: W (FVG на D1) или D (FVG на H4)
FV = {'W': '1D', 'D': '4h'}[LEG]; LEGBARS = {'W': 672, 'D': 96}[LEG]; PERFV = {'W': 7, 'D': 6}[LEG]
def first(mask, off=0):
    j = np.flatnonzero(mask); return off + j[0] if len(j) else INF
rows = []
for s in SYMS:
    raw = pd.read_pickle(f'{SRC}/{s}.pkl')[['o', 'h', 'l', 'c']]
    for side in ('bull', 'bear'):
        m = raw if side == 'bull' else pd.DataFrame({'o': -raw.o, 'h': -raw.l, 'l': -raw.h, 'c': -raw.c}, index=raw.index)
        h, l = m.h.values, m.l.values; pos = np.arange(len(m))
        d = pd.DataFrame({'o': m.o.values, 'h': h, 'l': l, 'c': m.c.values, 'p': pos}, index=m.index).resample(FV, label='left', closed='left').agg(
            o=('o', 'first'), h=('h', 'max'), l=('l', 'min'), c=('c', 'last'), i0=('p', 'first'), n=('p', 'size')).dropna()
        d = d[d.n >= .9 * d.n.median()]
        DO, DH, DL, DC, DI = d.o.values, d.h.values, d.l.values, d.c.values, d.i0.values.astype(int)
        DT = d.index; BH = np.maximum(DO, DC)
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
            dFH = WD0[jb] + int(np.argmax(DH[WD0[jb]:WD0[jb] + WND[jb]]))      # день хая ножки
            dconf = WD0[jb + 2]                                                 # первый день после подтверждения фрактала
            dend = min(len(d), dconf + 26 * PERFV)
            for BODY in ('strict', 'half', 'none'):
                ext, ext_d = np.inf, -1; cur = None; trade = None
                for di in range(dFH + 1, dend):
                    if DH[di] > FH or DL[di] < FL: break
                    # сигнал по закрытию дня di (FVG выбран по данным до di)
                    if cur is not None and cur[2] < di and DC[di] > cur[0]:
                        if di >= dconf: trade = (di, cur, min(ext, DL[di])); break
                        cur = None                                            # инверсия до подтверждения фрактала — не торгуем, ищем дальше
                    if DL[di] < ext:
                        ext, ext_d = DL[di], di
                        # свежий валидный FVG с k <= di
                        best = None
                        for k in range(di, max(dFH + 2, di - 60) - 1, -1):
                            if not (DH[k] < DL[k - 2]): continue
                            top, bot = DL[k - 2], DH[k]
                            if k - 2 < dFH: break
                            seg = BH[k + 1:di + 1]
                            if BODY == 'strict' and (seg > bot).any(): continue
                            if BODY == 'half' and (seg >= (top + bot) / 2).any(): continue
                            if (DC[k + 1:di + 1] > top).any(): continue        # уже инвертирован
                            best = (top, bot, k); break
                        if best is not None and (cur is None or best[2] > cur[2]): cur = best
                    # валидность текущего после свечи di
                    if cur is not None:
                        top, bot, k = cur
                        if BODY == 'strict' and BH[di] > bot and DC[di] <= top: cur = None
                        elif BODY == 'half' and BH[di] >= (top + bot) / 2 and DC[di] <= top: cur = None
                if trade is None: continue
                di, (top, bot, k), ext = trade
                entry, stop = DC[di], ext
                risk = entry - stop
                if risk <= 0 or FH <= entry: continue
                t0 = DI[di] + int(d.n.iloc[di]); e0 = min(len(h), t0 + 26 * LEGBARS)
                iS, iT = first(l[t0:e0] <= stop), first(h[t0:e0] >= FH)
                iM = first(h[t0:e0] >= entry + risk)
                rr = (FH - entry) / risk
                res = rr if iT < iS else -1.0 if iS < INF else np.nan
                rows.append(dict(leg=LEG, sym=s, side=side, body=BODY, t=DT[di], depth=(FH - ext) / R, depth_entry=(FH - entry) / R,
                                 rr=rr, win=iT < iS, R=res - COST * abs(entry) / risk if res == res else np.nan,
                                 hit1R=iM < iS, fvg_size_R=(top - bot) / R, days_after_conf=di - dconf))
    print(s, len(rows), flush=True)
pd.DataFrame(rows).to_csv(OUT, index=False)
