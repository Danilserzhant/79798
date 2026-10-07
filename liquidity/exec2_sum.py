"""Сводка exec2 против контроля. python exec2_sum.py <real.csv> <s1,s2,s3>"""
import sys, numpy as np, pandas as pd
R = pd.read_csv(sys.argv[1]); Ss = [pd.read_csv(f) for f in sys.argv[2].split(',')]
for d in [R] + Ss: d['gross'] = d.R + 0.001 / d.risk_pct
def st(d):
    if not len(d): return dict(n=0, win=np.nan, rr=np.nan, R=np.nan, se=np.nan, g=np.nan)
    return dict(n=len(d), win=d.win.mean(), rr=d.rr.median(), R=d.R.mean(), g=d.gross.mean(), se=d.R.std() / np.sqrt(len(d)))
base = lambda d: d[(d.rr >= 1) & (d.rr <= 5) & (d.risk_pct >= .003)]
FILT = {'все сигналы': lambda d: d,
        'RR 1–5, риск ≥ 0,3%': base,
        '+ экстремум внутри FVG (не пробил низ)': lambda d: base(d)[base(d).ext_in_fvg],
        '+ FVG в дискаунте вчерашнего диапазона': lambda d: base(d)[base(d).fvg_pos < .5],
        '+ сигнал в киллзону 07–10 / 12–16 UTC': lambda d: base(d)[base(d).hour.isin([7, 8, 9, 12, 13, 14, 15])]}
for u, f in (('ETH', lambda d: d[d.sym == 'ETHUSDT']), ('9 монет', lambda d: d)):
    for P in ('D', 'W'):
        print(f'\n######## {u} · BIAS {"дня → цель PDH/PDL" if P=="D" else "недели → цель PWH/PWL"} · H1 FVG + M5 фрактал')
        for fn, ff in FILT.items():
            print(f'--- {fn}')
            for g in ('with', 'none', 'against'):
                a = st(ff(f(R[(R.P == P) & (R.group == g)]))); c = [st(ff(f(x[(x.P == P) & (x.group == g)]))) for x in Ss]
                nm = {'with': 'по BIAS    ', 'none': 'без BIAS   ', 'against': 'против BIAS'}[g]
                print(f'  {nm} n={a["n"]:5d} | цель {100*a["win"]:3.0f}% (контр {100*np.nanmean([q["win"] for q in c]):3.0f}%) | RR мед {a["rr"]:.2f} | '
                      f'до комиссий {a["g"]:+.3f}R | итог {a["R"]:+.3f}R ±{2*a["se"]:.3f} (контроль {np.nanmean([q["R"] for q in c]):+.3f}R)')
