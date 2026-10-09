"""Откуда стартует реакция и где граница отката. python retrace_curve.py <res_dir> <s1,s2,s3> <out_json>"""
import sys, json, numpy as np, pandas as pd
RES, SY, OUTJ = sys.argv[1], sys.argv[2].split(','), sys.argv[3]
ALTS = ['SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'LTCUSDT', 'LINKUSDT']
GR = np.round(np.arange(.1, .96, .05), 3); EDGES = np.round(np.arange(0, 1.0001, .05), 3)
def tf(x): return x.map({True: 1.0, False: 0.0, 'True': 1.0, 'False': 0.0})
def hist(d):
    v = d.depth_before_cont.dropna(); c, _ = np.histogram(v.clip(0, .9999), EDGES); return c / max(1, len(v)), len(v), v.median(), v.quantile(.25), v.quantile(.75), v.quantile(.8)
def curve(d):
    out = []
    for g in GR:
        col = f'reach_{g}'
        x = d[d[col].astype(str) == 'True'][f'cont_after_{g}'] if col in d and f'cont_after_{g}' in d else pd.Series(dtype=float)
        x = tf(x).dropna(); out.append((x.mean() if len(x) else np.nan, len(x)))
    return out
J = {}
for P in ('W', 'D'):
    R = pd.read_csv(f'{RES}/retrace_{P}.csv'); Ss = [pd.read_csv(f'{s}/retrace_{P}.csv') for s in SY]
    for u, f in (('alts', lambda d: d[d.sym.isin(ALTS)]), ('all', lambda d: d)):
        r = f(R); cs = [f(x) for x in Ss]
        h, n, med, q1, q3, q8 = hist(r); hc = np.mean([hist(c)[0] for c in cs], axis=0)
        cr = curve(r); cc = [curve(c) for c in cs]
        J[f'{P}_{u}'] = dict(hist=h.tolist(), hist_c=hc.tolist(), n=n, med=med, q1=q1, q3=q3, q8=q8,
                            curve=[v for v, _ in cr], curve_n=[k for _, k in cr], curve_c=np.nanmean([[v for v, _ in c] for c in cc], axis=0).tolist(),
                            legs=len(r), cont=float(r.cont.astype(str).eq('True').mean()))
        print(f'\n######## {"Неделя" if P=="W" else "День"} · {"альты" if u=="alts" else "все 9"} · ножек {len(r)}, обновили хай {100*J[f"{P}_{u}"]["cont"]:.0f}%')
        print(f'  Откат перед обновлением хая (n={n}): медиана {med:.2f}, половина случаев между {q1:.2f} и {q3:.2f}, 80% — не глубже {q8:.2f}')
        cum = np.cumsum(h)
        print('  корзина     факт  контроль  накопл.')
        for i in range(20):
            star = ' ◀' if h[i] == h.max() else ''
            print(f'  {EDGES[i]:.2f}–{EDGES[i+1]:.2f}  {100*h[i]:4.1f}%  {100*hc[i]:4.1f}%   {100*cum[i]:4.0f}%{star}')
        print('  Откат дошёл до d (после подтверждения) → хай раньше лоя:   факт | контроль | случ. блуждание (1−d) | n')
        for g, (v, k), c in zip(GR, cr, J[f'{P}_{u}']['curve_c']):
            print(f'   {g:.2f}: {100*v:4.0f}% | {100*c:4.0f}% | {100*(1-g):4.0f}% | {k}')
json.dump(J, open(OUTJ, 'w'))
