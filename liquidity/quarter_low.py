"""В каком месяце (и полумесяце) квартала формируется лой и хай квартала. python3.13 quarter_low.py <dir_pkl_15m> <syn_dir1,...> <out_txt>
Квартал календарный (UTC). Отрезки: месяц 1/2/3 квартала и его половина (числа 1–15 / 16–конец). Бычий квартал — закрытие выше открытия.
Плюс: «лой первого месяца (первых двух) устоит до конца квартала» — всего и если цена на конец месяца выше открытия квартала."""
import sys, numpy as np, pandas as pd
SRC, SYN, OUT = sys.argv[1], sys.argv[2].split(','), sys.argv[3]
SYMS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'LTCUSDT', 'LINKUSDT']
SEG = ['м1 1–15', 'м1 16+', 'м2 1–15', 'м2 16+', 'м3 1–15', 'м3 16+']
def seg(ts):
    mq = (ts.month - 1) % 3; return mq * 2 + (0 if ts.day <= 15 else 1)
def table(src):
    rows = []
    for s in SYMS:
        m = pd.read_pickle(f'{src}/{s}.pkl')[['o', 'h', 'l', 'c']]
        d = m.groupby(m.index.normalize()).agg(o=('o', 'first'), h=('h', 'max'), l=('l', 'min'), c=('c', 'last'), n=('c', 'size'))
        d = d[d.n >= 90]
        for q, x in d.groupby(d.index.to_period('Q')):
            if len(x) < (q.end_time - q.start_time).days - 2: continue
            O, C = x.o.iloc[0], x.c.iloc[-1]; lo_t, hi_t = x.l.idxmin(), x.h.idxmax()
            r = dict(sym=s, q=str(q), bull=C > O, lo_s=seg(lo_t), hi_s=seg(hi_t), lo_m=(lo_t.month - 1) % 3, hi_m=(hi_t.month - 1) % 3)
            mq = (x.index.month - 1) % 3
            for k in (1, 2):
                a, b = x[mq < k], x[mq >= k]
                r[f'lo{k}_holds'] = bool(b.l.min() > a.l.min()); r[f'hi{k}_holds'] = bool(b.h.max() < a.h.max())
                r[f'up{k}'] = bool(a.c.iloc[-1] > O)
            rows.append(r)
    return pd.DataFrame(rows)
R = table(SRC); Ss = [table(s) for s in SYN]
pc = lambda v: f'{100*v:3.0f}%' if v == v else ' — '
def dist(d, col, n): return d[col].value_counts(normalize=True).reindex(range(n)).fillna(0).values
L = [f'Кварталов {len(R)} (9 монет), бычьих {pc(R.bull.mean())}. В скобках — контроль (дни в случайном порядке).']
for nm, f in (('ВСЕ кварталы', lambda d: d), ('БЫЧЬИ', lambda d: d[d.bull]), ('МЕДВЕЖЬИ', lambda d: d[~d.bull]), ('BTC + ETH', lambda d: d[d.sym.isin(['BTCUSDT', 'ETHUSDT'])])):
    x = f(R); cs = [f(s) for s in Ss]
    for col, cn in (('lo', 'ЛОЙ'), ('hi', 'ХАЙ')):
        a = dist(x, f'{col}_m', 3); b = np.mean([dist(c, f'{col}_m', 3) for c in cs], axis=0)
        a6 = dist(x, f'{col}_s', 6); b6 = np.mean([dist(c, f'{col}_s', 6) for c in cs], axis=0)
        L.append(f'  {nm:13s} {cn} n={len(x):3d} | по месяцам: ' + ' | '.join(f'{i+1}-й {pc(a[i])} ({pc(b[i])})' for i in range(3)))
        L.append(f'  {"":13s}          по полумесяцам: ' + ' | '.join(f'{SEG[i]} {pc(a6[i])} ({pc(b6[i])})' for i in range(6)))
L.append('\nУстоит ли экстремум первых месяцев до конца квартала:')
for k, nm in ((1, 'первого месяца'), (2, 'первых двух месяцев')):
    for side, col, cond, ct in (('лой', f'lo{k}_holds', True, 'выше'), ('хай', f'hi{k}_holds', False, 'ниже')):
        y = R[R[f'up{k}'] == cond]; yc = [c[c[f'up{k}'] == cond] for c in Ss]
        L.append(f'  {side} {nm} = {side} квартала: {pc(R[col].mean())} (контроль {pc(np.mean([c[col].mean() for c in Ss]))}) | '
                 f'если в конце периода цена {ct} открытия квартала: {pc(y[col].mean())} ({pc(np.mean([c[col].mean() for c in yc]))}) n={len(y)}')
txt = '\n'.join(L); print(txt); open(OUT, 'w').write(txt + '\n')
