"""Как сводить сигналы начала недели: большинство против «позднего узкого». python week_vote.py <dir_pkl_15m> <out_csv> [SYM ...]
Сигналы — как в week_check.py (с воскресенья по среду, UTC). Решение на закрытии среды; цели считаются от закрытия среды:
rest_up — закрытие недели выше закрытия среды; atr_up — +1 дн. ATR раньше −1 ATR до конца недели.
Методы: A — большинство сигналов; B — сигнал самого позднего дня, при равенстве — самый узкий (spec), противоречие — без решения;
C — только сигналы среды (по тому же правилу, что B)."""
import sys, numpy as np, pandas as pd
SRC, OUT = sys.argv[1:3]
SYMS = sys.argv[3:] or ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'LTCUSDT', 'LINKUSDT']
INF = 10**12
DAY = {'вс': 0, 'пн': 1, 'вт': 2, 'ср': 3}
def first(mask):
    j = np.flatnonzero(mask); return j[0] if len(j) else INF
def state(H, L, C, PH, PL):
    return ('принятие выше' if C > PH else 'принятие ниже' if C < PL else 'обе сняты' if (H > PH and L < PL)
            else 'отказ сверху' if H > PH else 'отказ снизу' if L < PL else 'внутри')
def signals(w, pw, ppw, A):
    """w, pw, ppw — DataFrame дней (o,h,l,c); возвращает [(день, spec, +1/−1, имя)]"""
    S = []
    PH, PL = pw.h.max(), pw.l.min(); O = w.o.iloc[0]; pos = (O - PL) / (PH - PL) if PH > PL else .5
    mon, tue, wed = w.iloc[0], w.iloc[1], w.iloc[2]
    pst = state(pw.h.max(), pw.l.min(), pw.c.iloc[-1], ppw.h.max(), ppw.l.min())
    if pst == 'обе сняты': S.append(('вс', 1, -1, 'прошлая «обе сняты»'))
    if pos < 1 / 3: S.append(('вс', 0, +1, 'открытие в нижней трети'))
    if pos > 2 / 3: S.append(('вс', 0, -1, 'открытие в верхней трети'))
    if mon.l < PL and mon.h <= PH: S.append(('пн', 1, +1, 'пн снял PWL'))
    if mon.h > PH and mon.l >= PL: S.append(('пн', 1, -1, 'пн снял PWH'))
    if tue.h <= mon.h and tue.l >= mon.l: S.append(('вт', 1, +1, 'вт инсайд пн'))
    if tue.l < mon.l: S.append(('вт', 1, -1, 'вт пробил лой пн'))
    tPH, tPL = max(mon.h, tue.h) > PH, min(mon.l, tue.l) < PL
    if tPH and not tPL and tue.c < O: S.append(('вт', 2, -1, 'снят PWH, ниже открытия'))
    inside = mon.l >= PL and mon.h <= PH
    if inside and tue.l < PL and tue.h <= PH and tue.c > PL: S.append(('вт', 3, -1, 'пн внутри, вт снял PWL и вернулся'))
    if inside and tue.h > PH and tue.l >= PL and tue.c < PH: S.append(('вт', 3, -1, 'пн внутри, вт снял PWH и вернулся'))
    if w.h.iloc[1:3].max() < mon.h and wed.c < O: S.append(('ср', 1, -1, 'хай пн устоял, ниже открытия'))
    if w.l.iloc[1:3].min() > mon.l and wed.c > O: S.append(('ср', 1, +1, 'лой пн устоял, выше открытия'))
    if tPL and not tPH and wed.c > PL:
        S.append(('ср', 3, +1, 'PWL снят, ср обновила лой, закрылась выше PWL') if wed.l < min(mon.l, tue.l) else ('ср', 2, +1, 'PWL снят, ср выше PWL, лой устоял'))
    if tPH and not tPL and wed.c < PH:
        S.append(('ср', 3, -1, 'PWH снят, ср обновила хай, закрылась ниже PWH') if wed.h > max(mon.h, tue.h) else ('ср', 2, -1, 'PWH снят, ср ниже PWH, хай устоял'))
    return S
def decide(S, method):
    if method == 'A':
        v = sum(s[2] for s in S); return int(np.sign(v))
    if method == 'C': S = [s for s in S if s[0] == 'ср']
    if not S: return 0
    top = max((DAY[s[0]], s[1]) for s in S)
    dirs = {s[2] for s in S if (DAY[s[0]], s[1]) == top}
    return dirs.pop() if len(dirs) == 1 else 0
rows = []
for s in SYMS:
    m = pd.read_pickle(f'{SRC}/{s}.pkl')[['o', 'h', 'l', 'c']]
    h, l, c = m.h.values, m.l.values, m.c.values
    g = pd.Series(np.arange(len(m)), index=m.index).groupby(m.index.normalize())
    D = pd.DataFrame({'i0': g.first().values, 'n': g.size().values}, index=g.first().index)
    D['o'] = m.o.values[D.i0.values]; D['c'] = c[(D.i0 + D.n - 1).values]
    D['h'] = [h[a:a + b].max() for a, b in zip(D.i0, D.n)]; D['l'] = [l[a:a + b].min() for a, b in zip(D.i0, D.n)]
    D['atr'] = (D.h - D.l).rolling(14).mean().shift(1); D = D[D.n >= 90]
    W = {k: x for k, x in D.groupby(D.index - pd.to_timedelta(D.index.dayofweek, unit='D'))}; ks = sorted(W)
    for i in range(2, len(ks)):
        w, pw, ppw = W[ks[i]], W[ks[i - 1]], W[ks[i - 2]]
        if len(w) < 7 or len(pw) < 7 or len(ppw) < 7 or ks[i] - ks[i - 2] != pd.Timedelta(days=14): continue
        A = w.atr.iloc[0]
        if not A == A: continue
        S = signals(w, pw, ppw, A)
        wed = w.iloc[2]; w_end = int(wed.i0 + wed.n); e_end = int(w.i0.iloc[-1] + w.n.iloc[-1]); Cw = c[w_end - 1]
        a, b = first(h[w_end:e_end] >= Cw + A), first(l[w_end:e_end] <= Cw - A)
        Hs, Ls = w.h.iloc[:3].max(), w.l.iloc[:3].min()
        r = dict(sym=s, t=ks[i], n_sig=len(S), rest_up=float(c[e_end - 1] > Cw), atr_up=np.nan if a == b == INF else float(a < b),
                 hi_holds=float(h[w_end:e_end].max() <= Hs), lo_holds=float(l[w_end:e_end].min() >= Ls), sigs='|'.join(f'{x[2]:+d}{x[3]}' for x in S))
        for mth in 'ABC': r[f'dec_{mth}'] = decide(S, mth)
        rows.append(r)
    print(s, len(rows), flush=True)
pd.DataFrame(rows).to_csv(OUT, index=False)
