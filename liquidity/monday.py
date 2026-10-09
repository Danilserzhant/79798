"""Понедельник как экстремум недели. python monday.py <dir_daily_real> <syn1,...> <out_txt>
Для каждой недели: лой и хай понедельника (UTC). Держится ли лой/хай понедельника до конца вторника/среды; итог недели."""
import sys, numpy as np, pandas as pd
REAL, SYN, OUT = sys.argv[1], sys.argv[2].split(','), sys.argv[3]
def tab(src):
    rows = []
    for s in ('BTCUSDT', 'ETHUSDT'):
        d = pd.read_pickle(f'{src}/{s}.pkl')
        for k, w in d.groupby(d.index - pd.to_timedelta(d.index.dayofweek, unit='D')):
            if len(w) < 7: continue
            o, c = w.o.iloc[0], w.c.iloc[-1]; mL, mH = w.l.iloc[0], w.h.iloc[0]
            r = dict(sym=s, t=k, bull=c > o, monday_bull=w.c.iloc[0] > o)
            for dd, nm in ((2, 'tue'), (3, 'wed')):
                r[f'mL_hold_{nm}'] = w.l.iloc[1:dd].min() > mL; r[f'mH_hold_{nm}'] = w.h.iloc[1:dd].max() < mH
                r[f'above_{nm}'] = w.c.iloc[dd - 1] > o
            r['mL_week'] = w.l.iloc[1:].min() > mL; r['mH_week'] = w.h.iloc[1:].max() < mH
            rows.append(r)
    return pd.DataFrame(rows)
R = tab(REAL); Ss = [tab(s) for s in SYN]
pc = lambda v: f'{100*v:3.0f}%'
L = [f'Недель {len(R)} (BTC + ETH, 2017–2026). Бычьих {pc(R.bull.mean())}']
L.append(f'Лой понедельника = лой всей недели: {pc(R.mL_week.mean())} (контроль {pc(np.mean([s.mL_week.mean() for s in Ss]))}); '
         f'хай понедельника = хай недели: {pc(R.mH_week.mean())} (контроль {pc(np.mean([s.mH_week.mean() for s in Ss]))}); '
         f'хотя бы один из них: {pc((R.mL_week | R.mH_week).mean())} (контроль {pc(np.mean([(s.mL_week | s.mH_week).mean() for s in Ss]))})')
def line(nm, f):
    x = f(R); cs = [f(s) for s in Ss]; p = x.bull.mean(); q = np.mean([c.bull.mean() for c in cs])
    lw = x.mL_week.mean(); lwc = np.mean([c.mL_week.mean() for c in cs]); hw = x.mH_week.mean(); hwc = np.mean([c.mH_week.mean() for c in cs])
    h = x.t.sort_values().iloc[len(x) // 2]
    L.append(f'  {nm:62s} n={len(x):3d} | неделя бычья {pc(p)} (контроль {pc(q)}) | лой пн устоял всю неделю {pc(lw)} ({pc(lwc)}) | хай пн устоял {pc(hw)} ({pc(hwc)}) | половины {pc(x[x.t<h].bull.mean())}/{pc(x[x.t>=h].bull.mean())}')
L.append('\nЕсли к концу вторника / среды:')
line('лой пн не обновлён до конца вторника, пн бычий', lambda d: d[d.mL_hold_tue & d.monday_bull])
line('лой пн не обновлён до конца среды, цена выше открытия', lambda d: d[d.mL_hold_wed & d.above_wed])
line('хай пн не обновлён до конца вторника, пн медвежий', lambda d: d[d.mH_hold_tue & ~d.monday_bull])
line('хай пн не обновлён до конца среды, цена ниже открытия', lambda d: d[d.mH_hold_wed & ~d.above_wed])
line('пн бычий (без других условий)', lambda d: d[d.monday_bull])
line('пн медвежий (без других условий)', lambda d: d[~d.monday_bull])
print('\n'.join(L)); open(OUT, 'w').write('\n'.join(L) + '\n')
