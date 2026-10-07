"""Уровень 1 top-down: ликвидность месяца и недели.
A) PWH/PWL и PMH/PML: как часто снимаются, что первым, что после снятия (принятие vs возврат).
B) Старые хаи/лои (несснятые свинг-фракталы 2+2 на W и D) как пулы: к какому пулу цена идёт первой,
   и отличается ли это от случайного блуждания (p_up = d_dn / (d_up + d_dn)).
C) Пул -> пул: после снятия пула — противоположный пул раньше следующего в ту же сторону?
D) Равные хаи/лои (EQH/EQL): притягивают ли сильнее одиночных.
Время — UTC, неделя с понедельника. python level1.py <dir_pkl> <out_dir> [SYM ...]"""
import sys, os, numpy as np, pandas as pd
SRC, OUT = sys.argv[1:3]
SYMS = sys.argv[3:] or ['ETHUSDT', 'BTCUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'LTCUSDT', 'LINKUSDT']
os.makedirs(OUT, exist_ok=True)
INF = 10**9

def first(mask):
    j = np.flatnonzero(mask); return j[0] if len(j) else INF

def period_key(idx, P):
    if P == 'W': return idx.normalize() - pd.to_timedelta(idx.dayofweek, unit='D')
    if P == 'M': return idx.to_period('M').to_timestamp()
    return idx.normalize()

def bars(m, P):
    k = period_key(m.index, P)
    g = m.groupby(k)
    b = g.agg(o=('o', 'first'), h=('h', 'max'), l=('l', 'min'), c=('c', 'last'))
    b['i0'] = g.apply(lambda x: m.index.get_loc(x.index[0])).values
    b['n'] = g.size().values
    return b

# ---------- A: прошлый хай/лой периода ----------
def prev_range(sym, m, P):
    b = bars(m, P); h, l, c = m.h.values, m.l.values, m.c.values
    rows = []
    for j in range(1, len(b)):
        p, cu = b.iloc[j - 1], b.iloc[j]
        if cu.n < (600 if P == 'W' else 2600): continue                      # неполный период
        PH, PL, R = p.h, p.l, p.h - p.l
        s, e = int(cu.i0), int(cu.i0 + cu.n)
        iH, iL = first(h[s:e] > PH), first(l[s:e] < PL)
        pos = (cu.o - PL) / R
        opn = 'выше PH' if pos > 1 else 'ниже PL' if pos < 0 else 'верх. половина' if pos >= .5 else 'нижн. половина'
        r = dict(sym=sym, P=P, t=b.index[j], opn=opn, pos=pos, tH=iH < INF, tL=iL < INF,
                 first='H' if iH < iL else 'L' if iL < iH else ('-' if iH == INF else 'same'),
                 closeAbovePH=cu.c > PH, closeBelowPL=cu.c < PL, closeUpper=cu.c > (PH + PL) / 2)
        # после периода: противоположная сторона прошлого диапазона раньше нового экстремума этого периода?
        if j + 1 < len(b):
            f = slice(e, min(len(h), e + (8 if P == 'W' else 3) * (e - s)))
            if r['tH'] and not r['tL']:
                a, z = first(l[f] < PL), first(h[f] > cu.h)
                r['after'] = 'opp' if a < z else 'cont' if z < a else '-'
                r['after_mid'] = 'opp' if first(l[f] < (PH + PL) / 2) < z else 'cont'
            elif r['tL'] and not r['tH']:
                a, z = first(h[f] > PH), first(l[f] < cu.l)
                r['after'] = 'opp' if a < z else 'cont' if z < a else '-'
                r['after_mid'] = 'opp' if first(h[f] > (PH + PL) / 2) < z else 'cont'
        rows.append(r)
    return rows

# ---------- B/C/D: пулы на свингах ----------
def swings(b, m):
    """фрактал 2+2 по барам периода; подтверждение — открытие бара k+3; снятие — первый 15m бар за уровнем."""
    H, L = b.h.values, b.l.values; h, l = m.h.values, m.l.values; i0 = b.i0.values.astype(int)
    out = []
    for k in range(2, len(b) - 3):
        conf = i0[k + 3]
        if H[k] > H[k - 1] and H[k] > H[k - 2] and H[k] >= H[k + 1] and H[k] >= H[k + 2]:
            out.append(('H', H[k], k, conf, conf + first(h[conf:] > H[k])))
        if L[k] < L[k - 1] and L[k] < L[k - 2] and L[k] <= L[k + 1] and L[k] <= L[k + 2]:
            out.append(('L', L[k], k, conf, conf + first(l[conf:] < L[k])))
    return pd.DataFrame(out, columns=['side', 'lvl', 'k', 'conf', 'taken'])

def pools(sym, m, P, HOR, TOL=0.15):
    b = bars(m, P); h, l, c = m.h.values, m.l.values, m.c.values
    atr = (b.h - b.l).rolling(14).mean().shift(1).values
    sw = swings(b, m); i0 = b.i0.values.astype(int)
    hz = HOR * int(np.median(b.n))
    def active(t):
        a = sw[(sw.conf <= t) & (sw.taken > t)]
        return a[a.side == 'H'].lvl.values, a[a.side == 'L'].lvl.values
    def is_eq(lv, arr, A): return int((np.abs(arr - lv) <= TOL * A).sum() > 1)
    def last_taken(t):
        tk = sw[sw.taken <= t]
        return '-' if not len(tk) else tk.loc[tk.taken.idxmax(), 'side']
    def race(t, up, dn):
        iu, idn = first(h[t:t + hz] > up), first(l[t:t + hz] < dn)
        return 1 if iu < idn else 0 if idn < iu else np.nan
    rowsB, rowsC = [], []
    for j in range(20, len(b)):
        t = i0[j]; A = atr[j]
        if np.isnan(A): continue
        His, Los = active(t)
        up_all, dn_all = His[His > c[t - 1]], Los[Los < c[t - 1]]
        if not len(up_all) or not len(dn_all): continue
        up, dn = up_all.min(), dn_all.max(); o = c[t - 1]
        du, dd = (up - o) / A, (o - dn) / A
        rowsB.append(dict(sym=sym, P=P, t=b.index[j], du=du, dd=dd, p_rw=dd / (du + dd), up_first=race(t, up, dn),
                          eq_up=is_eq(up, His, A), eq_dn=is_eq(dn, Los, A), flow=last_taken(t),
                          age_up=j - sw[(sw.side == 'H') & (sw.lvl == up)].k.max(), age_dn=j - sw[(sw.side == 'L') & (sw.lvl == dn)].k.max()))
    # C: событие снятия пула -> с закрытия периода: противоположный пул раньше следующего в ту же сторону?
    per_of = np.searchsorted(i0, np.arange(len(h)), side='right') - 1
    for r in sw.itertuples():
        if r.taken >= len(h): continue
        jp = per_of[r.taken]
        if jp + 1 >= len(b): continue
        A = atr[jp]
        if np.isnan(A): continue
        tc = i0[jp + 1]; cl = c[tc - 1]
        His, Los = active(tc)
        eq = is_eq(r.lvl, sw[(sw.side == r.side) & (sw.conf <= r.taken) & (sw.taken >= r.taken)].lvl.values, A)
        if r.side == 'H':
            nxt, opp = His[His > cl], Los[Los < cl]
            accept = cl > r.lvl
            if not len(nxt) or not len(opp): continue
            nx, op = nxt.min(), opp.max(); dn_, dx = (cl - op) / A, (nx - cl) / A
            w = race(tc, nx, op); opp_first = np.nan if np.isnan(w) else 1 - w
        else:
            nxt, opp = Los[Los < cl], His[His > cl]
            accept = cl < r.lvl
            if not len(nxt) or not len(opp): continue
            nx, op = nxt.max(), opp.min(); dn_, dx = (op - cl) / A, (cl - nx) / A
            opp_first = race(tc, op, nx)
        rowsC.append(dict(sym=sym, P=P, side=r.side, t=b.index[jp], accept=accept, eq=eq, d_opp=dn_, d_next=dx,
                          p_rw=dx / (dn_ + dx), opp_first=opp_first))
    return rowsB, rowsC

A, B, C = [], [], []
for s in SYMS:
    m = pd.read_pickle(f'{SRC}/{s}.pkl')[['o', 'h', 'l', 'c']]
    for P in ('W', 'M'): A += prev_range(s, m, P)
    for P, HOR in (('W', 26), ('D', 40)):
        rb, rc = pools(s, m, P, HOR); B += rb; C += rc
    print(s, 'ok', flush=True)
A, B, C = pd.DataFrame(A), pd.DataFrame(B), pd.DataFrame(C)
A.to_csv(f'{OUT}/A_prev_range.csv', index=False); B.to_csv(f'{OUT}/B_pools.csv', index=False); C.to_csv(f'{OUT}/C_pool_to_pool.csv', index=False)
