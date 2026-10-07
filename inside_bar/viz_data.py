"""Данные для графиков: шорт-сигналы ETH (снятие лоя матери) + текущая ситуация. python viz_data.py <eth_pkl> <signals.csv> <events.csv> <out.json>"""
import sys, json, numpy as np, pandas as pd
P, SIG, EV, OUT = sys.argv[1:5]
m = pd.read_pickle(P)[['o', 'h', 'l', 'c']]
S = pd.read_csv(SIG); E = pd.read_csv(EV)
S = S[(S.sym == 'ETHUSDT') & (S.side == 'low') & (S.signal.fillna(False).astype(bool))]
def bars(rule, a, b, cap):
    d = m.loc[a:b].resample(rule, label='left', closed='left').agg(o=('o', 'first'), h=('h', 'max'), l=('l', 'min'), c=('c', 'last')).dropna()
    if len(d) > cap: d = d.iloc[-cap:]
    return [[int(t.timestamp()), round(r.o, 2), round(r.h, 2), round(r.l, 2), round(r.c, 2)] for t, r in d.iterrows()]
def W(t): return t.normalize() - pd.Timedelta(days=t.dayofweek)
cases = []
def add_case(cid, title, ev, sig=None, current=False):
    ibw = pd.Timestamp(ev.ib_week); mow = ibw - pd.Timedelta(weeks=1)
    ib = m.loc[ibw:ibw + pd.Timedelta(weeks=1) - pd.Timedelta('15min')]; mo = m.loc[mow:ibw - pd.Timedelta('15min')]
    L, H = mo.l.min(), mo.h.max(); R = H - L
    t0 = pd.Timestamp(ev.t0)
    lv = dict(moH=H, moL=L, mid=L + R / 2, ibH=ib.h.max(), ibL=ib.l.min(), E1=L - R)
    mk = []
    end = m.index[-1]
    if sig is not None:
        ts, st = pd.Timestamp(sig.t), (pd.Timestamp(sig.stop_t) if isinstance(sig.stop_t, str) else None)
        lt = pd.Timestamp(sig.low_t) if isinstance(sig.low_t, str) else None
        win = lt is not None and (st is None or lt < st)
        lv.update(zt=sig.zone_top, zb=sig.zone_bot, sweep=sig.sweep, entry=sig.entry, stop=sig.stop, f15b=sig.fvg15_bot, f15t=sig.fvg15_top)
        outcome_t = lt if win else st
        mk = [dict(t=int(pd.Timestamp(sig.ext_t).timestamp()), k='sweep'), dict(t=int(pd.Timestamp(sig.lh_t).timestamp()), k='lh'),
              dict(t=int(ts.timestamp()), k='entry')]
        if outcome_t is not None: mk.append(dict(t=int(outcome_t.timestamp()), k='win' if win else 'stop'))
        a_m15 = pd.Timestamp(sig.fvg15_t) - pd.Timedelta(hours=6)
        b_m15 = (outcome_t or ts) + pd.Timedelta(hours=10)
        b_h4 = (outcome_t or ts) + pd.Timedelta(days=4)
        res = dict(win=bool(win), rr=round(float((sig.entry - sig.sweep) / (sig.stop - sig.entry)), 2),
                   depth=round(float((L - sig.sweep) / R), 2), hours=round(float(((outcome_t or ts) - ts).total_seconds() / 3600), 1))
    else:
        ts = end; b_m15 = end; a_m15 = end - pd.Timedelta(hours=36); b_h4 = end
        lv.update(zt=2689.77, zb=2623.83, sweep=float(m.loc[t0:].l.min()))
        mk = [dict(t=int(m.loc[t0:].l.idxmin().timestamp()), k='sweep')]
        res = dict(depth=round(float((L - lv['sweep']) / R), 2))
    cases.append(dict(id=cid, title=title, current=current, group='now' if current else ('deep' if res['depth'] >= 0.2 else 'shallow'),
        ib_week=str(ibw.date()), mo_week=str(mow.date()), t0=str(t0), res=res, lv={k: round(float(v), 2) for k, v in lv.items()}, mk=mk,
        W=bars('W-MON', mow - pd.Timedelta(weeks=10), min(end, W(ts) + pd.Timedelta(weeks=6)), 40),
        D=bars('1D', mow - pd.Timedelta(days=7), min(end, b_h4 + pd.Timedelta(days=6)), 90),
        H4=bars('4h', t0 - pd.Timedelta(days=4), min(end, b_h4), 240),
        M15=bars('15min', a_m15, min(end, b_m15), 420)))
ev = {r.ib_week: r for r in E[(E.sym == 'ETHUSDT') & (E.side == 'low')].itertuples()}
cur = E[(E.sym == 'ETHUSDT') & (E.side == 'low') & (E.ib_week == '2026-09-28')].iloc[0]
add_case('now', 'Сейчас · октябрь 2026', cur, None, True)
for s in S.sort_values('t').itertuples():
    add_case(s.ib_week, pd.Timestamp(s.t).strftime('%d.%m.%Y'), ev[s.ib_week], s)
json.dump(cases, open(OUT, 'w'), ensure_ascii=False, separators=(',', ':'))
print(len(cases), [(c['id'], c['group'], c['res']) for c in cases])
