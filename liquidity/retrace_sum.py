"""Сводка retrace_w против контроля. python retrace_sum.py <real.csv> <s1,s2,s3>"""
import sys, numpy as np, pandas as pd
R = pd.read_csv(sys.argv[1]); Ss = [pd.read_csv(f) for f in sys.argv[2].split(',')]
for d in [R] + Ss:
    for c in d.columns:
        if d[c].dtype == object and set(d[c].dropna().unique()) <= {'True', 'False'}: d[c] = d[c].map({'True': True, 'False': False})
ALTS = ['SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'LTCUSDT', 'LINKUSDT']
U = {'Альты (7)': lambda d: d[d.sym.isin(ALTS)], 'ETH': lambda d: d[d.sym == 'ETHUSDT'], 'BTC': lambda d: d[d.sym == 'BTCUSDT'], 'Все 9': lambda d: d}
BK = [0, .382, .5, .618, .705, .79, 1.0001]; BN = ['< 0.382', '0.382–0.5', '0.5–0.618', '0.618–0.705', '0.705–0.79', '0.79–1']
LV = [.382, .5, .618, .705, .79]
pc = lambda v: f'{100*v:3.0f}%' if pd.notna(v) else '  — '
def dist(x, col):
    v = x[col].dropna(); c = pd.cut(v, BK, labels=BN, right=False).value_counts(normalize=True).reindex(BN); return c, v.median(), len(v)
for u, f in U.items():
    r = f(R); cs = [f(x) for x in Ss]
    print(f'\n################ {u}: ножек {len(r)} (бычьих {int((r.side=="bull").sum())}, медвежьих {int((r.side=="bear").sum())})')
    print(f'  хай ножки обновлён раньше слома лоя: {pc(r.cont.mean())} (контроль {pc(np.mean([c.cont.mean() for c in cs]))}) | лой сломан раньше: {pc(r.broke.mean())} (контроль {pc(np.mean([c.broke.mean() for c in cs]))})')
    print(f'  отскок на 0.5R до слома лоя: {pc(r.react05.mean())} (контроль {pc(np.mean([c.react05.mean() for c in cs]))})')
    for col, nm in (('depth_before_cont', 'Глубина отката перед ОБНОВЛЕНИЕМ ХАЯ'), ('depth_react05', 'Глубина отката перед ОТСКОКОМ 0.5R')):
        d0, med, n = dist(r, col); dc = [dist(c, col)[0] for c in cs]; mc = np.mean([dist(c, col)[1] for c in cs])
        print(f'  {nm} (n={n}): медиана {med:.2f} (контроль {mc:.2f})')
        print('     ' + ' | '.join(f'{b}: {pc(d0[b])} ({pc(np.nanmean([q[b] for q in dc]))})' for b in BN))
    dc0 = r.depth_at_confirm.dropna(); print(f'  Откат уже к моменту подтверждения фрактала (закрытие следующей недели): медиана {dc0.median():.2f}; уже ниже 0.5 — {pc((dc0>=.5).mean())}, ниже 0.618 — {pc((dc0>=.618).mean())}, лой сломан — {pc((~r.confirmed_ok.astype(bool)).mean())}')
    print('  После подтверждения: если откат дошёл до уровня → хай обновят раньше слома лоя (лимитка на уровне, стоп под лоем, цель хай):')
    for d in LV:
        reach = r[f'reach_{d}'].dropna().astype(float).mean(); g = r[r[f'reach_{d}'] == True][f'cont_after_{d}'].dropna().astype(float); p = g.mean(); rr = d / (1 - d)
        pcs = [c[c[f'reach_{d}'] == True][f'cont_after_{d}'].dropna().astype(float).mean() for c in cs]
        ev = p * rr - (1 - p); evc = np.mean([q * rr - (1 - q) for q in pcs])
        print(f'     {d:5.3f}: доходит (если ещё не пройден) {pc(reach)} | дальше хай раньше лоя {pc(p)} (контроль {pc(np.mean(pcs))}) | RR {rr:.2f} | итог {ev:+.2f}R (контроль {evc:+.2f}R, случайное блуждание {rr*(1-d)-d:+.2f}R) n={len(g)}')
r = U['Альты (7)'](R)
print('\nАльты по сторонам:')
for sd, g in r.groupby('side'):
    print(f'  {sd}: n={len(g)} обновление хая {pc(g.cont.mean())}, медиана отката перед ним {g.depth_before_cont.median():.2f}, перед отскоком 0.5R {g.depth_react05.median():.2f}')
