"""Доп. подтверждения разворота после снятия стороны матери: первый восходящий FVG, поглощение,
ордерблок (+ретест), импульсная свеча. Правила как у основного сетапа: окно до закрытия недели ниже лоя
инсайда (отмена), максимум 4 недели; вариант «+неделя» — неделя сигнала закрылась выше лоя инсайда.
Экстремум пересчитывается на каждом баре, сигнал только после него. Снятие хая — зеркально.
python confirm2.py <dir_pkl> <events.csv> <out.csv> [SYM]"""
import sys, os, numpy as np, pandas as pd
SRC, EV, OUT = sys.argv[1:4]
SYM = sys.argv[4] if len(sys.argv) > 4 else None
E = pd.read_csv(EV); E = E[~E.open]
if SYM: E = E[E.sym == SYM]
TFS = {'H1': '1h', 'H4': '4h', 'D1': '1D'}
HOLD = pd.Timedelta(weeks=4); NEVER = pd.Timestamp.max
def agg(df, rule):
    return df.resample(rule, label='left', closed='left').agg(o=('o', 'first'), h=('h', 'max'), l=('l', 'min'), c=('c', 'last')).dropna()
cache, rows = {}, []
for e in E.itertuples():
    if (e.sym, e.side) not in cache:
        raw = pd.read_pickle(f'{SRC}/{e.sym}.pkl')
        m = raw if e.side == 'low' else pd.DataFrame({'o': -raw.o, 'h': -raw.l, 'l': -raw.h, 'c': -raw.c}, index=raw.index)
        cache[(e.sym, e.side)] = (m, {k: agg(m, r) for k, r in TFS.items()})
    m, fr = cache[(e.sym, e.side)]
    sg = 1 if e.side == 'low' else -1
    L, H, R = sg * e.L, sg * e.H, e.R
    t0 = pd.Timestamp(e.t0); ibw = pd.Timestamp(e.ib_week)
    ib_l = m.loc[ibw:ibw + pd.Timedelta(weeks=1) - pd.Timedelta('15min')].l.min()
    if os.environ.get('LEVEL') == 'mother': ib_l = L   # уровни только от матери
    # окно: до первого недельного закрытия ниже лоя инсайда, максимум 4 недели
    end = t0 + pd.Timedelta(weeks=4)
    wk = t0.normalize() - pd.Timedelta(days=t0.dayofweek)
    while wk + pd.Timedelta(weeks=1) <= min(end, m.index[-1]):
        we = wk + pd.Timedelta(weeks=1)
        if m.c.loc[:we - pd.Timedelta('15min')].iloc[-1] < ib_l: end = we; break
        wk = we
    sigs = {}
    def put(name, t):
        if name not in sigs: sigs[name] = t
    for tf, b in fr.items():
        off = pd.Timedelta(TFS[tf])
        o, h, l, c, idx = b.o.values, b.h.values, b.l.values, b.c.values, b.index
        body = np.abs(c - o); avgb = pd.Series(body).rolling(20, min_periods=5).mean().shift(1).values
        j0 = idx.searchsorted(t0, side='right') - 1
        ob_sig = None
        for j in range(max(j0, 2), len(b)):
            tc = idx[j] + off
            if tc <= t0: continue
            if tc > end: break
            x = j0 + int(np.argmin(l[j0:j + 1]))
            if x == j: ob_sig = None; continue
            # 1. первый восходящий FVG после экстремума (свечи j-2..j, j-2 >= x)
            if j - 2 >= x and l[j] > h[j - 2]:
                put(f'Первый восходящий {tf} FVG', tc)
                if h[j - 2] >= ib_l: put(f'Восходящий {tf} FVG выше лоя инсайда', tc)
            # 2. бычье поглощение
            if c[j] > o[j] and c[j - 1] < o[j - 1] and c[j] >= o[j - 1] and o[j] <= c[j - 1] and j - 1 >= x:
                if j - x <= 3: put(f'Поглощение {tf} у лоя', tc)
                if c[j] > ib_l: put(f'Поглощение {tf} с закрытием выше лоя инсайда', tc)
            # 3. ордерблок: последняя медвежья свеча у экстремума, закрытие выше её хая
            obk = next((k for k in range(x, max(j0 - 1, x - 5), -1) if c[k] < o[k]), None)
            if obk is not None and c[j] > h[obk] and (c[obk + 1:j] <= h[obk]).all():
                put(f'Ордерблок {tf}: закрытие выше OB', tc)
                if f'_ob_{tf}' not in sigs: sigs[f'_ob_{tf}'] = (tc, l[obk], h[obk])
            # 4. импульсная свеча выше лоя инсайда
            if avgb[j] == avgb[j] and c[j] > o[j] and body[j] >= 2 * avgb[j] and c[j] > ib_l:
                put(f'Импульсная свеча {tf} выше лоя инсайда', tc)
    # ретест OB после сигнала (касание хая OB раньше нового лоя), в пределах окна
    for tf in TFS:
        if f'_ob_{tf}' in sigs:
            tc, obl, obh = sigs.pop(f'_ob_{tf}')
            seg = m.loc[tc:end]
            low_now = m.loc[t0:tc - pd.Timedelta('15min')].l.min()
            hit = seg.index[seg.l.values <= obh]; brk = seg.index[seg.l.values < low_now]
            if len(hit) and (not len(brk) or hit[0] <= brk[0]): put(f'Ордерблок {tf}: вход на ретесте OB', hit[0])
    for name, ts in sigs.items():
        sweep_low = m.loc[t0:ts - pd.Timedelta('15min')].l.min()
        f = m.loc[ts:ts + HOLD]
        fi = lambda mk: f.index[np.nonzero(mk)[0][0]] if mk.any() else NEVER
        tH, tN, tE = fi(f.h.values >= H), fi(f.l.values < sweep_low), fi(f.l.values <= L - R)
        we = ts.normalize() - pd.Timedelta(days=ts.dayofweek) + pd.Timedelta(weeks=1)
        wk_ok = m.c.loc[:we - pd.Timedelta('15min')].iloc[-1] > ib_l
        rows.append(dict(sym=e.sym, side=e.side, ib_week=e.ib_week, conf=name, t=str(ts), wk_ok=bool(wk_ok),
                         H_first=tH < tN, reach_H=tH < NEVER, reach_E1=tE < NEVER))
D = pd.DataFrame(rows); D.to_csv(OUT, index=False)
NE = {'both': len(E), 'low': int((E.side == 'low').sum())}
res = []
for nm in ('low', 'both'):
    d = D if nm == 'both' else D[D.side == 'low']
    for cname, g in d.groupby('conf'):
        for var, gg in (('', g), (' +неделя', g[g.wk_ok])):
            res.append(dict(side=nm, conf=cname + var, fired=round(len(gg) / NE[nm] * 100), n=len(gg),
                            H_first=round(gg.H_first.mean() * 100) if len(gg) else None,
                            reach_H=round(gg.reach_H.mean() * 100) if len(gg) else None,
                            reach_E1=round(gg.reach_E1.mean() * 100) if len(gg) else None))
Rz = pd.DataFrame(res); Rz.to_csv(OUT.replace('.csv', '_summary.csv'), index=False)
pd.set_option('display.width', 200)
for nm in ('low', 'both'):
    print(f'\n== {nm}: событий {NE[nm]}'); print(Rz[Rz.side == nm].sort_values('H_first', ascending=False).drop(columns='side').to_string(index=False))
