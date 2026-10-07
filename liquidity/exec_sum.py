"""Сводка exec1: факт vs контроль. python exec_sum.py <real.csv> <synth1.csv,...>"""
import sys, numpy as np, pandas as pd
R = pd.read_csv(sys.argv[1]); Ss = [pd.read_csv(f) for f in sys.argv[2].split(',')]
def st(d):
    if not len(d): return dict(n=0, win=np.nan, stop=np.nan, rr=np.nan, R=np.nan, se=np.nan)
    return dict(n=len(d), win=d.win.mean(), stop=d.stopped.mean(), rr=d.rr.median(), R=d.R.mean(), se=d.R.std() / np.sqrt(len(d)))
FILT = {'все сигналы': lambda d: d,
        'RR 1–5, риск ≥ 0,3%': lambda d: d[(d.rr >= 1) & (d.rr <= 5) & (d.risk_pct >= .003)],
        '+ лой после Азии ниже лоя Азии (D)': lambda d: d[(d.rr >= 1) & (d.rr <= 5) & (d.risk_pct >= .003) & d.asia_swept],
        '+ сигнал в киллзону 07–10 / 12–16 UTC (D)': lambda d: d[(d.rr >= 1) & (d.rr <= 5) & (d.risk_pct >= .003) & d.hour.isin([7, 8, 9, 12, 13, 14, 15])]}
for u, f in (('ETH', lambda d: d[d.sym == 'ETHUSDT']), ('9 монет', lambda d: d)):
    for P in ('D', 'W'):
        print(f'\n######## {u} · BIAS {"дня, триггер M15, цель PDH/PDL" if P=="D" else "недели, триггер H1, цель PWH/PWL"}')
        for fn, ff in FILT.items():
            if P == 'W' and '(D)' in fn: continue
            print(f'--- {fn}')
            for g in ('with', 'none', 'against'):
                a = st(ff(f(R[(R.P == P) & (R.group == g)])))
                c = [st(ff(f(x[(x.P == P) & (x.group == g)]))) for x in Ss]
                cR = np.nanmean([q['R'] for q in c]); cw = np.nanmean([q['win'] for q in c])
                nm = {'with': 'по BIAS    ', 'none': 'без BIAS   ', 'against': 'против BIAS'}[g]
                print(f'  {nm} n={a["n"]:5d} | цель {100*a["win"]:3.0f}% (контр {100*cw:3.0f}%) | стоп {100*a["stop"]:3.0f}% | RR мед {a["rr"]:.2f} | '
                      f'итог {a["R"]:+.3f}R ±{2*a["se"]:.3f} (контроль {cR:+.3f}R)')
