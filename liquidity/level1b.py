"""Уровень 1, часть 2: премиум/дискаунт и HTF PD arrays (W, M; D — для сравнения).
P) Dealing range = последний подтверждённый свинг-хай и свинг-лой (2+2). Положение открытия периода в нём ->
   кто первым: +1 ATR или −1 ATR; и кто первым: хай или лой диапазона.
Z) Зоны: FVG (бычий: L[k] > H[k-2]) и OB (последняя медвежья свеча k, свеча k+1 закрылась выше H[k]; зона O[k]..L[k]).
   Медвежьи — зеркально (цены с минусом), всё считается как для бычьих.
   Первое касание верха зоны: лимит на верхе, стоп под низом -> цель +1 и +2 размера зоны (как RR1/RR2);
   и с касания: +1 ATR раньше −1 ATR?
   Закрытие периода касания: выше зоны / внутри / сквозь (ниже низа) -> с закрытия: +1 ATR раньше −1 ATR?
   Инверсия: первое закрытие периода ниже низа зоны (до или после касания) -> с закрытия: −1 ATR раньше +1 ATR?
python level1b.py <dir_pkl> <out_dir> [SYM ...]"""
import sys, os, numpy as np, pandas as pd
SRC, OUT = sys.argv[1:3]
SYMS = sys.argv[3:] or ['ETHUSDT', 'BTCUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'LTCUSDT', 'LINKUSDT']
os.makedirs(OUT, exist_ok=True)
INF = 10**9
HOR = {'D': 60, 'W': 52, 'M': 24}                        # горизонт поиска касания, в периодах

def first(mask):
    j = np.flatnonzero(mask); return j[0] if len(j) else INF

def bars(m, P):
    idx = m.index
    k = (idx.normalize() - pd.to_timedelta(idx.dayofweek, unit='D')) if P == 'W' else idx.to_period('M').to_timestamp() if P == 'M' else idx.normalize()
    pos = np.arange(len(m))
    g = pd.DataFrame({'o': m.o.values, 'h': m.h.values, 'l': m.l.values, 'c': m.c.values, 'p': pos}, index=idx).groupby(k)
    b = g.agg(o=('o', 'first'), h=('h', 'max'), l=('l', 'min'), c=('c', 'last'), i0=('p', 'first'), n=('p', 'size'))
    return b[b.n >= 0.9 * b.n.median()] if P != 'M' else b[b.n >= 2600]

def race(h, l, t, up, dn, hz):
    """с бара t (включительно): кто первым — h >= up или l <= dn; одновременно -> dn (консервативно)"""
    iu, idn = first(h[t:t + hz] >= up), first(l[t:t + hz] <= dn)
    if iu == INF and idn == INF: return np.nan
    return 1.0 if iu < idn else 0.0

def run(sym, m, P, side):
    if side == 'bear':
        m = pd.DataFrame({'o': -m.o, 'h': -m.l, 'l': -m.h, 'c': -m.c}, index=m.index)
    b = bars(m, P); h, l, c = m.h.values, m.l.values, m.c.values
    O, H, L, C = b.o.values, b.h.values, b.l.values, b.c.values
    i0 = b.i0.values.astype(int); nb = b.n.values.astype(int)
    atr = pd.Series(H - L).rolling(14).mean().shift(1).values
    per = int(np.median(nb)); hzA = 26 * per if P != 'M' else 12 * per
    zones, prem = [], []
    for k in range(14, len(b) - 2):
        A = atr[k]
        if np.isnan(A): continue
        cands = []
        if L[k] > H[k - 2]: cands.append(('FVG', L[k], H[k - 2], k + 1))
        if C[k - 1] < O[k - 1] and C[k] > H[k - 1] and k >= 15: cands.append(('OB', O[k - 1], L[k - 1], k + 1))
        for typ, top, bot, jv in cands:
            if jv >= len(b): continue
            s = i0[jv]; e = min(len(h), s + HOR[P] * per)
            it = first(l[s:e] <= top)
            # инверсия: первое закрытие периода ниже низа (в пределах горизонта)
            jj = np.arange(jv, min(len(b), jv + HOR[P]))
            inv = jj[C[jj] < bot]
            r = dict(sym=sym, P=P, side=side, typ=typ, t=b.index[k], size_atr=(top - bot) / A, touched=it < INF)
            if len(inv):
                ji = inv[0]; tc = i0[ji] + nb[ji]; Ai = atr[ji]
                if tc < len(h) and not np.isnan(Ai):
                    r['inv_before_touch'] = bool(it == INF or s + it >= tc)
                    r['inv_down1'] = 1 - race(h, l, tc, C[ji] + Ai, C[ji] - Ai, hzA)       # 1 = вниз первым
            if it < INF:
                t = s + it; sz = top - bot
                gap_through = l[t] < bot
                r['rr1'] = 0.0 if gap_through else race(h, l, t + 1, top + sz, bot - 1e-12, hzA)
                r['rr2'] = 0.0 if gap_through else race(h, l, t + 1, top + 2 * sz, bot - 1e-12, hzA)
                A_t = atr[np.searchsorted(i0, t, side='right') - 1]
                r['atr_up_touch'] = race(h, l, t + 1, top + A_t, top - A_t, hzA)
                jt = np.searchsorted(i0, t, side='right') - 1; tc = i0[jt] + nb[jt]
                if tc < len(h):
                    cl = C[jt]; r['close'] = 'выше зоны' if cl > top else 'сквозь (ниже низа)' if cl < bot else 'внутри'
                    r['atr_up_close'] = race(h, l, tc, cl + atr[jt], cl - atr[jt], hzA)
            zones.append(r)
    # премиум/дискаунт: только для бычьей стороны (зеркало не нужно — диапазон симметричен)
    if side == 'bull':
        sh, sl = [], []
        for k in range(2, len(b) - 3):
            if H[k] > H[k - 1] and H[k] > H[k - 2] and H[k] >= H[k + 1] and H[k] >= H[k + 2]: sh.append((k + 3, H[k]))
            if L[k] < L[k - 1] and L[k] < L[k - 2] and L[k] <= L[k + 1] and L[k] <= L[k + 2]: sl.append((k + 3, L[k]))
        sh, sl = np.array(sh), np.array(sl)
        for j in range(20, len(b)):
            if np.isnan(atr[j]) or not len(sh) or not len(sl): continue
            a_, b_ = sh[sh[:, 0] <= j], sl[sl[:, 0] <= j]
            if not len(a_) or not len(b_): continue
            SH, SL = a_[-1, 1], b_[-1, 1]
            if SH <= SL: continue
            t = i0[j]; o = c[t - 1]; pos = (o - SL) / (SH - SL)
            r = dict(sym=sym, P=P, t=b.index[j], pos=pos, rng_atr=(SH - SL) / atr[j],
                     atr_up=race(h, l, t, o + atr[j], o - atr[j], hzA))
            if 0 <= pos <= 1: r['hi_first'] = race(h, l, t, SH + 1e-12, SL - 1e-12, hzA * 4)
            prem.append(r)
    return zones, prem

Z, PR = [], []
for s in SYMS:
    m = pd.read_pickle(f'{SRC}/{s}.pkl')[['o', 'h', 'l', 'c']]
    for P in ('D', 'W', 'M'):
        for side in ('bull', 'bear'):
            z, p = run(s, m, P, side); Z += z; PR += p
    print(s, 'ok', flush=True)
pd.DataFrame(Z).to_csv(f'{OUT}/Z_zones.csv', index=False); pd.DataFrame(PR).to_csv(f'{OUT}/P_premium.csv', index=False)
