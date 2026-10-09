"""Сводка fvg_new_w по глубине отката. python fvg_new_sum.py <res_dir> <s1,s2,s3>"""
import sys, numpy as np, pandas as pd
RES, SY = sys.argv[1], sys.argv[2].split(',')
ALTS = ['SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'LTCUSDT', 'LINKUSDT']
BK = [('0–0.5', 0, .5), ('0.5–0.618', .5, .618), ('0.618–0.79', .618, .79), ('0.79–1', .79, 1.01)]
def prep(d):
    for c in ('winT', 'win1'): d[c] = d[c].map({True: 1.0, False: 0.0, 'True': 1.0, 'False': 0.0})
    d['RT'] = np.where(d.winT == 1, d.rr, np.where(d.winT == 0, -1.0, np.nan)) - d.cost_R
    d['R1'] = np.where(d.win1 == 1, 1.0, np.where(d.win1 == 0, -1.0, np.nan)) - d.cost_R
    return d
for L in ('W', 'D'):
    R = prep(pd.read_csv(f'{RES}/fvg_new_{L}.csv')); C = pd.concat([prep(pd.read_csv(f'{s}/fvg_new_{L}.csv')) for s in SY])
    for u, f in (('альты', lambda d: d[d.sym.isin(ALTS)]), ('все 9', lambda d: d)):
        for et, en in (('A', 'вход на закрытии свечи FVG'), ('B', 'лимитка на верхе FVG')):
            r = f(R[R.entry_type == et]); c = f(C[C.entry_type == et])
            print(f'\n### {"Неделя + D1 FVG" if L=="W" else "День + H4 FVG"} · {u} · {en} · сделок {len(r)} · RR до хая мед {r.rr.median():.2f} · комиссия {r.cost_R.mean():.2f}R')
            print('   откат          n  | 1R раньше стопа  контр  итог 1R  контр  ст.ош | хай ножки  контр  итог   контр')
            for nm, a, b in [('все', 0, 9)] + BK:
                g = r[(r.depth >= a) & (r.depth < b)]; gc = c[(c.depth >= a) & (c.depth < b)]
                g1, gc1 = g.R1.dropna(), gc.R1.dropna(); gT, gcT = g.RT.dropna(), gc.RT.dropna()
                if len(g1) < 5: print(f'   {nm:11s} {len(g):5d}'); continue
                z = (g1.mean() - gc1.mean()) / np.sqrt(g1.var() / len(g1) + gc1.var() / len(gc1))
                print(f'   {nm:11s} {len(g):5d}  |   {100*g.win1.mean():3.0f}%        {100*gc.win1.mean():3.0f}%   {g1.mean():+.2f}   {gc1.mean():+.2f}  {z:+.1f} |   {100*g.winT.mean():3.0f}%    {100*gc.winT.mean():3.0f}%  {gT.mean():+.2f}  {gcT.mean():+.2f}')
