"""Сводка fvg_inv_w по глубине отката. python fvg_inv_sum.py <real.csv> <s1,s2,s3>"""
import sys, numpy as np, pandas as pd
R = pd.read_csv(sys.argv[1]); Ss = [pd.read_csv(f) for f in sys.argv[2].split(',')]
ALTS = ['SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'LTCUSDT', 'LINKUSDT']
BK = [0, .382, .5, .618, .705, .79, 1.0001]; BN = ['0–0.382', '0.382–0.5', '0.5–0.618', '0.618–0.705', '0.705–0.79', '0.79–1']
for d in [R] + Ss:
    d['win'] = d.win.astype(str).eq('True'); d['hit1R'] = d.hit1R.astype(str).eq('True'); d['bk'] = pd.cut(d.depth, BK, labels=BN, right=False)
    d['R1'] = np.where(d.hit1R, 1.0, -1.0)                                      # вариант: цель 1R
def st(x):
    x = x.dropna(subset=['R'])
    return len(x), x.win.mean(), x.rr.median(), x.R.mean(), x.R.std() / np.sqrt(max(1, len(x))), x.hit1R.mean()
for u, f in (('Альты (7)', lambda d: d[d.sym.isin(ALTS)]), ('Все 9', lambda d: d), ('ETH', lambda d: d[d.sym == 'ETHUSDT'])):
    for body, bn in (('strict', 'тела не заходили в FVG'), ('half', 'тела не доходили до середины FVG'), ('none', 'без фильтра тел')):
        r = f(R[R.body == body]); cs = [f(x[x.body == body]) for x in Ss]
        a = st(r); c = [st(x) for x in cs]
        print(f'\n######## {u} · {bn} · сделок {a[0]} | хай ножки раньше стопа {100*a[1]:.0f}% (контроль {100*np.mean([q[1] for q in c]):.0f}%) | RR мед {a[2]:.2f} | '
              f'итог {a[3]:+.2f}R ±{2*a[4]:.2f} (контроль {np.mean([q[3] for q in c]):+.2f}R) | 1R раньше стопа {100*a[5]:.0f}% (контроль {100*np.mean([q[5] for q in c]):.0f}%)')
        print('   глубина отката     n  | цель-хай  контр | RR мед | итог R   контр | 1R раньше стопа  контр')
        for b in BN:
            g = st(r[r.bk == b]); gc = [st(x[x.bk == b]) for x in cs]
            if g[0] == 0: print(f'   {b:12s}    0'); continue
            print(f'   {b:12s} {g[0]:5d}  |   {100*g[1]:3.0f}%   {100*np.nanmean([q[1] for q in gc]):3.0f}% | {g[2]:5.2f} | {g[3]:+.2f}±{2*g[4]:.2f}  {np.nanmean([q[3] for q in gc]):+.2f} |      {100*g[5]:3.0f}%       {100*np.nanmean([q[5] for q in gc]):3.0f}%')
