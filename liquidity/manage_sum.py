"""Сопровождение: варианты A–F на сигналах exec2, факт против контроля. python manage_sum.py <real.csv> <s1,s2,s3>"""
import sys, numpy as np, pandas as pd
R = pd.read_csv(sys.argv[1]); Ss = [pd.read_csv(f) for f in sys.argv[2].split(',')]
V = {'mA': 'A: всё до цели', 'mB': 'B: 50% на 1R, остаток БУ → цель', 'mC': 'C: 50% на 2R, остаток БУ → цель',
     'mD': 'D: 1/3 на 1R, 1/3 на 2R, 1/3 → цель, БУ после 1R', 'mE': 'E: всё на 1R', 'mF': 'F: всё на 2R'}
base = lambda d: d[(d.rr >= 1) & (d.rr <= 5) & (d.risk_pct >= .003)]
for u, f in (('ETH', lambda d: d[d.sym == 'ETHUSDT']), ('9 монет', lambda d: d)):
    for P in ('D', 'W'):
        for g in ('with', 'none'):
            for fn, ff in (('все сигналы', lambda d: d), ('RR 1–5, риск ≥ 0,3%', base)):
                a = ff(f(R[(R.P == P) & (R.group == g)])); cs = [ff(f(x[(x.P == P) & (x.group == g)])) for x in Ss]
                cost = (0.001 / a.risk_pct).mean()
                print(f'\n### {u} · {"день" if P=="D" else "неделя"} · {"по BIAS" if g=="with" else "без BIAS"} · {fn} · n={len(a)} · комиссия в среднем {cost:.2f}R')
                for k, nm in V.items():
                    se = a[k].std() / np.sqrt(len(a)); c = np.mean([x[k].mean() for x in cs])
                    pos = (a[k] > 0).mean()
                    print(f'  {nm:48s} итог {a[k].mean():+.3f}R ±{2*se:.3f} | до комиссий {a[k].mean()+cost:+.3f}R | контроль {c:+.3f}R | плюсовых сделок {100*pos:3.0f}%')
