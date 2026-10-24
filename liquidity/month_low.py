"""В какую неделю месяца формируется лой и хай месяца. python3.13 month_low.py <dir_pkl_15m> <syn_dir1,...> <out_txt>
Неделя месяца по числам (UTC): 1–7, 8–14, 15–21, 22–конец. Бычий месяц — закрытие выше открытия.
Плюс: «лой первых N дней устоит до конца месяца» — для N = 7, 14, 21, и в зависимости от того, где цена на день N."""
import sys, numpy as np, pandas as pd
SRC, SYN, OUT = sys.argv[1], sys.argv[2].split(','), sys.argv[3]
SYMS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'LTCUSDT', 'LINKUSDT']
WN = ['1–7', '8–14', '15–21', '22+']
wom = lambda day: 0 if day <= 7 else 1 if day <= 14 else 2 if day <= 21 else 3
def table(src):
    rows = []
    for s in SYMS:
        m = pd.read_pickle(f'{src}/{s}.pkl')[['o', 'h', 'l', 'c']]
        d = m.groupby(m.index.normalize()).agg(o=('o', 'first'), h=('h', 'max'), l=('l', 'min'), c=('c', 'last'), n=('c', 'size'))
        d = d[d.n >= 90]
        for k, x in d.groupby(d.index.to_period('M')):
            if len(x) < k.days_in_month - 1: continue
            O, C = x.o.iloc[0], x.c.iloc[-1]
            r = dict(sym=s, t=k.to_timestamp(), bull=C > O, lo_w=wom(x.l.idxmin().day), hi_w=wom(x.h.idxmax().day),
                     lo_day=x.l.idxmin().day, hi_day=x.h.idxmax().day)
            for N in (7, 14, 21):
                a = x[x.index.day <= N]; b = x[x.index.day > N]
                r[f'lo{N}_holds'] = bool(b.l.min() > a.l.min()) if len(b) else np.nan
                r[f'hi{N}_holds'] = bool(b.h.max() < a.h.max()) if len(b) else np.nan
                r[f'up{N}'] = bool(a.c.iloc[-1] > O)
            rows.append(r)
    return pd.DataFrame(rows)
R = table(SRC); Ss = [table(s) for s in SYN]
pc = lambda v: f'{100*v:3.0f}%' if v == v else ' — '
def dist(d, col): return d[col].value_counts(normalize=True).reindex(range(4)).fillna(0).values
L = [f'Месяцев {len(R)} (9 монет, {R.t.min():%Y-%m} — {R.t.max():%Y-%m}), бычьих {pc(R.bull.mean())}. В скобках — контроль (дни в случайном порядке).']
for nm, f in (('ВСЕ месяцы', lambda d: d), ('БЫЧЬИ месяцы', lambda d: d[d.bull]), ('МЕДВЕЖЬИ месяцы', lambda d: d[~d.bull]),
              ('BTC + ETH, все', lambda d: d[d.sym.isin(['BTCUSDT', 'ETHUSDT'])])):
    x = f(R); cs = [f(s) for s in Ss]
    for col, cn in (('lo_w', 'ЛОЙ месяца'), ('hi_w', 'ХАЙ месяца')):
        a = dist(x, col); b = np.mean([dist(c, col) for c in cs], axis=0)
        L.append(f'  {nm:18s} {cn:10s} n={len(x):3d} | ' + ' | '.join(f'дни {WN[i]}: {pc(a[i])} ({pc(b[i])})' for i in range(4)))
L.append('\nПо числам месяца (все месяцы): лой месяца')
dd = R.lo_day.value_counts(normalize=True).sort_index(); dc = pd.concat([s.lo_day for s in Ss]).value_counts(normalize=True).sort_index()
L.append('  ' + ' '.join(f'{d}:{100*dd.get(d,0):.0f}({100*dc.get(d,0):.0f})' for d in range(1, 32)))
L.append('\nЕсли к дню N лой (хай) ещё не обновлялся — устоит ли он до конца месяца:')
for N in (7, 14, 21):
    for side, col, upc, txt in (('лой', f'lo{N}_holds', f'up{N}', 'цена ВЫШЕ открытия месяца'), ('хай', f'hi{N}_holds', f'up{N}', 'цена НИЖЕ открытия месяца')):
        x = R; cs = Ss
        base = x[col].mean(); bc = np.mean([c[col].mean() for c in cs])
        sel = (lambda d: d[d[upc]]) if side == 'лой' else (lambda d: d[~d[upc]])
        y = sel(x); yc = [sel(c) for c in cs]
        L.append(f'  {side} первых {N} дней = {side} месяца: {pc(base)} (контроль {pc(bc)}) | если на {N}-й день {txt}: {pc(y[col].mean())} ({pc(np.mean([c[col].mean() for c in yc]))}) n={len(y)}')
txt = '\n'.join(L); print(txt); open(OUT, 'w').write(txt + '\n')
