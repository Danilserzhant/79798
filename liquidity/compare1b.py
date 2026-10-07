"""Реальный рынок vs синтетика для level1b. python compare1b.py <real_dir> <synth_dir> [...] [--eth]"""
import sys, numpy as np, pandas as pd
args = [a for a in sys.argv[1:] if not a.startswith('--')]; ETH = '--eth' in sys.argv
def load(d):
    z, p = pd.read_csv(f'{d}/Z_zones.csv'), pd.read_csv(f'{d}/P_premium.csv')
    if ETH: z, p = z[z.sym == 'ETHUSDT'], p[p.sym == 'ETHUSDT']
    return z, p
real = load(args[0]); syn = [load(d) for d in args[1:]]
def line(name, f):
    v, n = f(real)
    sv = np.nanmean([f(s)[0] for s in syn])
    se = np.sqrt(max(sv * (1 - sv), 1e-6) / max(n, 1)) if 0 <= sv <= 1 else np.nan
    flag = ' <<' if n >= 30 and abs(v - sv) > 2 * se else ''
    print(f'  {name:62s} {100*v:4.0f}% | {100*sv:4.0f}% | {100*(v-sv):+4.0f} п.п. n={n}{flag}')
def mean(col, cond=lambda d: d):
    def f(x):
        d = cond(x); d = d.dropna(subset=[col]); return (d[col].mean() if len(d) else np.nan), len(d)
    return f
print('факт | контроль | разница  (<< — разница больше 2 стандартных ошибок)')
print('\n=== Премиум/дискаунт: положение открытия в dealing range (последние свинг-хай и свинг-лой) ===')
BK = [(-9, 0, 'ниже диапазона'), (0, .25, 'глубокий дискаунт 0–25%'), (.25, .5, 'дискаунт 25–50%'), (.5, .75, 'премиум 50–75%'),
      (.75, 1, 'глубокий премиум 75–100%'), (1, 9, 'выше диапазона')]
for P in ('W', 'D'):
    print(f'--- {P}')
    for a, b, nm in BK:
        sel = lambda x, a=a, b=b: x[1][(x[1].P == P) & (x[1].pos >= a) & (x[1].pos < b)]
        line(f'{nm}: +1 ATR раньше −1 ATR', lambda x, s=sel: (s(x).atr_up.mean(), s(x).atr_up.notna().sum()))
        if 0 <= a < 1:
            line(f'{nm}: хай диапазона раньше лоя', lambda x, s=sel: (s(x).hi_first.mean(), s(x).hi_first.notna().sum()))
print('\n=== Зоны HTF: FVG и OB (медвежьи считаются зеркально; «вверх» = в сторону реакции) ===')
for P in ('M', 'W', 'D'):
    for typ in ('FVG', 'OB'):
        for side in ('bull', 'bear', 'all'):
            sel = lambda x, P=P, typ=typ, side=side: x[0][(x[0].P == P) & (x[0].typ == typ) & ((x[0].side == side) if side != 'all' else True)]
            print(f'--- {P} {typ} {side}')
            line('касание: цель +1 размер раньше стопа под зоной', lambda x, s=sel: (s(x).rr1.mean(), s(x).rr1.notna().sum()))
            line('касание: цель +2 размера раньше стопа под зоной', lambda x, s=sel: (s(x).rr2.mean(), s(x).rr2.notna().sum()))
            line('касание: +1 ATR раньше −1 ATR', lambda x, s=sel: (s(x).atr_up_touch.mean(), s(x).atr_up_touch.notna().sum()))
            for cl in ('выше зоны', 'внутри', 'сквозь (ниже низа)'):
                line(f'закрытие периода касания {cl}: доля', lambda x, s=sel, cl=cl: ((s(x).close == cl).mean(), s(x).close.notna().sum()))
                line(f'   ...после него +1 ATR раньше −1 ATR', lambda x, s=sel, cl=cl: (s(x)[s(x).close == cl].atr_up_close.mean(), s(x)[s(x).close == cl].atr_up_close.notna().sum()))
            line('инверсия (закрытие сквозь зону): дальше −1 ATR раньше +1 ATR', lambda x, s=sel: (s(x).inv_down1.mean(), s(x).inv_down1.notna().sum()))
