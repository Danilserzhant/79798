"""Сводка opens.py против контроля. python opens_sum.py <real.csv> <s1,s2,s3> <out_txt>"""
import sys, numpy as np, pandas as pd
R = pd.read_csv(sys.argv[1]); Ss = [pd.read_csv(f) for f in sys.argv[2].split(',')]; OUT = sys.argv[3]
for d in [R] + Ss:
    for c in ('bull', 'away', 'away_up', 'revisit', 'bounce', 'up_q1', 'up_q2', 'up_q3', 'prev_open_hit'):
        d[c] = d[c].map({True: 1.0, False: 0.0, 'True': 1.0, 'False': 0.0})
MAJ = ['BTCUSDT', 'ETHUSDT']
PN = {'D_UTC': 'ДЕНЬ, открытие 00:00 UTC', 'D_NY': 'ДЕНЬ, открытие в полночь Нью-Йорка', 'W': 'НЕДЕЛЯ', 'M': 'МЕСЯЦ'}
pc = lambda v: f'{100*v:3.0f}%' if v == v else '  — '
L = []
def row(nm, f, P, grp):
    r = f(R[(R.P == P) & grp(R)]); cs = [f(s[(s.P == P) & grp(s)]) for s in Ss]
    return r, cs
for P, pn in PN.items():
    for gnm, grp in (('BTC + ETH', lambda d: d.sym.isin(MAJ)), ('альты (7)', lambda d: ~d.sym.isin(MAJ))):
        x = R[(R.P == P) & grp(R)]; cs = [s[(s.P == P) & grp(s)] for s in Ss]
        if len(x) < 30: continue
        L.append(f'\n######## {pn} · {gnm} · свечей {len(x)}')
        def m(col, f=lambda d: d, nm=''):
            v = f(x)[col].dropna(); vc = [f(c)[col].dropna() for c in cs]
            q = np.mean([c.mean() for c in vc]); se = np.sqrt(max(q * (1 - q), .01) / max(1, len(v)))
            L.append(f'  {nm:66s} {pc(v.mean())} (контроль {pc(q)}) {(v.mean() - q) / se:+.1f} ст.ош. n={len(v)}')
        m('away', nm='цена ушла от открытия хотя бы на 0,25 ATR')
        m('revisit', nm='…и вернулась к открытию в том же периоде')
        m('bounce', nm='при первом возврате ОТБОЙ (а не пробой) на 0,25 ATR')
        m('bounce', lambda d: d[d.away_up == 1], 'отбой сверху (открытие как поддержка)')
        m('bounce', lambda d: d[d.away_up == 0], 'отбой снизу (открытие как сопротивление)')
        m('prev_open_hit', nm='цена коснулась открытия ПРОШЛОГО периода')
        for q, qn in (('up_q1', '1/4'), ('up_q2', '1/2'), ('up_q3', '3/4')):
            a = x[x[q] == 1].bull.mean(); b = x[x[q] == 0].bull.mean()
            ac = np.mean([c[c[q] == 1].bull.mean() for c in cs]); bc = np.mean([c[c[q] == 0].bull.mean() for c in cs])
            L.append(f'  через {qn} периода выше открытия → закрылась выше {pc(a)} (контроль {pc(ac)}) | ниже → закрылась ниже {pc(1-b)} (контроль {pc(1-bc)})')
        for side, nm in ((1, 'бычья'), (0, 'медвежья')):
            y = x[x.bull == side]; yc = [c[c.bull == side] for c in cs]
            jm = y.judas.median(); jc = np.mean([c.judas.median() for c in yc]); z0 = (y.judas < .05).mean(); z0c = np.mean([(c.judas < .05).mean() for c in yc])
            e = y.ext_frac; ec = pd.concat([c.ext_frac for c in yc])
            L.append(f'  {nm} свеча: ложный ход против неё до экстремума — медиана {jm:.2f} ATR (контроль {jc:.2f}); почти без него (< 0,05 ATR) {pc(z0)} ({pc(z0c)}) | '
                     f'{"лой" if side else "хай"} в 1-й четверти периода {pc((e < .25).mean())} ({pc((ec < .25).mean())}), в последней {pc((e >= .75).mean())} ({pc((ec >= .75).mean())})')
txt = '\n'.join(L); print(txt); open(OUT, 'w').write(txt + '\n')
