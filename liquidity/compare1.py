"""Реальный рынок vs синтетика (перемешанные дни). python compare1.py <real_dir> <synth_dir1> [<synth_dir2> ...]"""
import sys, numpy as np, pandas as pd
def load(d):
    out = []
    for f in ('A_prev_range', 'B_pools', 'C_pool_to_pool'):
        x = pd.read_csv(f'{d}/{f}.csv')
        for col in x.columns:
            if x[col].dtype == object and set(x[col].dropna().unique()) <= {'True', 'False'}: x[col] = x[col] == 'True'
        out.append(x)
    return out
def metrics(A, B, C):
    r = {}
    for P, nm in (('W', 'Неделя'), ('M', 'Месяц')):
        a = A[A.P == P]
        up, dn = a[a.opn == 'верх. половина'], a[a.opn == 'нижн. половина']
        r[(nm, 'открытие в верх. половине → снят хай')] = (up.tH.mean(), len(up))
        r[(nm, 'открытие в нижн. половине → снят лой')] = (dn.tL.mean(), len(dn))
        r[(nm, 'снят хай (любое открытие)')] = (a.tH.mean(), len(a))
        r[(nm, 'снят лой (любое открытие)')] = (a.tL.mean(), len(a))
        r[(nm, 'сняты обе стороны')] = ((a.tH & a.tL).mean(), len(a))
        b = a[a.tH & a.tL]
        r[(nm, 'обе сняты → закрытие в половине второго снятия')] = (np.where(b['first'] == 'H', ~b.closeUpper, b.closeUpper).mean(), len(b))
        one = a[(a.tH ^ a.tL) & a['after'].isin(['opp', 'cont'])]
        acc = np.where(one.tH, one.closeAbovePH, one.closeBelowPL)
        for nm2, g in (('снята одна сторона, ВОЗВРАТ внутрь', one[~acc]), ('снята одна сторона, закрытие ЗА уровнем', one[acc])):
            r[(nm, nm2 + ' → середина раньше нового экстр.')] = ((g.after_mid == 'opp').mean(), len(g))
            r[(nm, nm2 + ' → противоп. сторона раньше нового экстр.')] = ((g['after'] == 'opp').mean(), len(g))
    for P, nm in (('W', 'W-свинги'), ('D', 'D-свинги')):
        b = B[B.P == P].dropna(subset=['up_first'])
        near = np.where(b.du < b.dd, b.up_first, 1 - b.up_first)
        r[(nm, 'ближний пул снят первым')] = (near.mean(), len(b))
        r[(nm, 'верхний пул первым')] = (b.up_first.mean(), len(b))
        for col, side in (('eq_up', 1), ('eq_dn', 0)):
            for v in (0, 1):
                g = b[b[col] == v]; hit = g.up_first if side else 1 - g.up_first
                r[(nm, f'{"верхний" if side else "нижний"} пул {"EQ" if v else "одиночный"} снят первым')] = (hit.mean(), len(g))
        c = C[C.P == P].dropna(subset=['opp_first'])
        for acc in (False, True):
            g = c[c.accept == acc]
            r[(nm, f'снят пул, {"закрытие ЗА" if acc else "возврат"} → противоположный пул первым')] = (g.opp_first.mean(), len(g))
    return r
real = load(sys.argv[1]); syn = [load(d) for d in sys.argv[2:]]
for u, f in (('ETH', lambda x: x[x.sym == 'ETHUSDT']), ('9 монет', lambda x: x)):
    R = metrics(*[f(x) for x in real]); Ss = [metrics(*[f(x) for x in s]) for s in syn]
    print(f'\n######## {u}: факт | синтетика (без уровней) | разница')
    last = None
    for k, (v, n) in R.items():
        if k[0] != last: print(f'--- {k[0]}'); last = k[0]
        sv = np.nanmean([s[k][0] for s in Ss])
        flag = '  <<' if abs(v - sv) >= .08 and n >= 30 else ''
        print(f'  {k[1]:70s} {100*v:4.0f}% | {100*sv:4.0f}% | {100*(v-sv):+5.0f} п.п.  n={n}{flag}')
