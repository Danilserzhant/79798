"""Сводка по level1: python summary1.py results"""
import sys, numpy as np, pandas as pd
R = sys.argv[1]
A = pd.read_csv(f'{R}/A_prev_range.csv'); B = pd.read_csv(f'{R}/B_pools.csv'); C = pd.read_csv(f'{R}/C_pool_to_pool.csv')
for d in (A, B, C):
    for col in d.columns:
        if d[col].dtype == object and set(d[col].dropna().unique()) <= {'True', 'False', True, False}: d[col] = d[col].astype(str) == 'True'
pc = lambda x: f'{100 * np.mean(x):3.0f}%'
U = {'ETH': lambda d: d[d.sym == 'ETHUSDT'], '9 монет': lambda d: d}

print('=== A. Прошлый хай/лой периода ===')
for P, nm in (('W', 'PWH/PWL'), ('M', 'PMH/PML')):
    for u, f in U.items():
        a = f(A[A.P == P])
        print(f'\n{nm} · {u} · n={len(a)}: снят хай {pc(a.tH)} | лой {pc(a.tL)} | обе {pc(a.tH & a.tL)} | ни одной {pc(~a.tH & ~a.tL)}')
        for o, g in a.groupby('opn'):
            both = g[g.tH & g.tL]
            print(f'   открытие {o:15s} n={len(g):4d}: хай {pc(g.tH)} лой {pc(g.tL)} обе {pc(g.tH & g.tL)}')
        both = a[a.tH & a.tL]
        if len(both):
            sec = np.where(both['first'] == 'H', ~both.closeUpper, both.closeUpper)
            print(f'   когда сняты обе (n={len(both)}): закрылся в половине ВТОРОГО снятия {pc(sec)}')
        for side, cond, acc in (('хай', a.tH & ~a.tL, 'closeAbovePH'), ('лой', a.tL & ~a.tH, 'closeBelowPL')):
            g = a[cond & a['after'].isin(['opp', 'cont'])]
            for nm2, gg in (('закрытие ЗА уровнем', g[g[acc]]), ('возврат внутрь', g[~g[acc]])):
                mo, op = (gg.after_mid == 'opp').mean(), (gg.after == 'opp').mean()
                if len(gg): print(f'   снят только {side}, {nm2:20s} n={len(gg):4d}: дальше сначала середина прошлого диапазона {100*mo:3.0f}%, '
                                  f'противоп. сторона {100*op:3.0f}% (иначе новый экстремум)')

print('\n=== B. Пулы ликвидности (несснятые свинги 2+2): какой снимется первым ===')
print('   p_rw — ожидание случайного блуждания по расстояниям; факт > p_rw = цену «тянет» вверх сильнее расстояния')
for P in ('W', 'D'):
    for u, f in U.items():
        b = f(B[B.P == P]).dropna(subset=['up_first'])
        print(f'\n{P}-свинги · {u} · n={len(b)}: верхний первым {pc(b.up_first)} при ожидании {pc(b.p_rw)} | ближний пул первым {pc(np.where(b.du < b.dd, b.up_first, 1 - b.up_first))}')
        b = b.assign(bk=pd.cut(b.p_rw, [0, .2, .35, .5, .65, .8, 1]))
        print('   по положению между пулами (p_rw): ' + ' | '.join(f'{k}: {pc(g.up_first)} vs {pc(g.p_rw)} n={len(g)}' for k, g in b.groupby('bk', observed=True)))
        for fl, g in b.groupby('flow'):
            print(f'   последний снятый пул = {fl}: верхний первым {pc(g.up_first)} vs ожидание {pc(g.p_rw)} (n={len(g)})')
        for nm, col, dcol, dirv in (('верхний EQH', 'eq_up', 'du', 1), ('нижний EQL', 'eq_dn', 'dd', 0)):
            for v, g in b.groupby(col):
                hit = g.up_first if dirv else 1 - g.up_first; exp = g.p_rw if dirv else 1 - g.p_rw
                print(f'   {nm}={v}: снят первым {pc(hit)} vs ожидание {pc(exp)} (n={len(g)}), перевес {100 * (hit.mean() - exp.mean()):+.1f} п.п.')

print('\n=== C. Пул -> пул: после снятия пула противоположный пул раньше следующего? (с закрытия периода) ===')
for P in ('W', 'D'):
    for u, f in U.items():
        cdf = f(C[C.P == P]).dropna(subset=['opp_first'])
        print(f'\n{P} · {u} · n={len(cdf)}: противоположный первым {pc(cdf.opp_first)} vs ожидание {pc(cdf.p_rw)}')
        for (acc, eq), g in cdf.groupby(['accept', 'eq']):
            print(f'   {"закрытие ЗА уровнем" if acc else "возврат (отказ)":20s} {"EQ" if eq else "одиночный":9s} n={len(g):4d}: противоположный первым {pc(g.opp_first)} vs ожидание {pc(g.p_rw)} ({100*(g.opp_first.mean()-g.p_rw.mean()):+.1f} п.п.)')
