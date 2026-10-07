"""Доп. правило: после сигнала (инверсия H4 FVG) неделя сигнала должна закрыться выше лоя инсайда.
python wk_confirm.py <dir_pkl> <events.csv> <signals.csv> <out_prefix>
Пишет: <out>_sig.csv (сигналы, прошедшие фильтр, вход в момент сигнала),
       <out>_wk.csv (те же, вход на недельном закрытии), <out>_summary.json"""
import sys, json, numpy as np, pandas as pd
SRC, EV, SIG, OUT = sys.argv[1:5]
E = pd.read_csv(EV); S = pd.read_csv(SIG)
S = S[S.conf.str.startswith('Инверсия H4')]
ev = {(r.sym, r.side, r.ib_week): r for r in E.itertuples()}
cache = {}; a, b, info = [], [], []
for s in S.itertuples():
    e = ev[(s.sym, s.side, s.ib_week)]
    if (s.sym, s.side) not in cache:
        raw = pd.read_pickle(f'{SRC}/{s.sym}.pkl')
        cache[(s.sym, s.side)] = raw if s.side == 'low' else pd.DataFrame({'h': -raw.l, 'l': -raw.h, 'c': -raw.c}, index=raw.index)
    m = cache[(s.sym, s.side)]
    sg = 1 if s.side == 'low' else -1
    L, H, R = sg * e.L, sg * e.H, e.R
    ibw = pd.Timestamp(s.ib_week)
    ib_l = m.loc[ibw:ibw + pd.Timedelta(weeks=1) - pd.Timedelta('15min')].l.min()
    te = pd.Timestamp(s.t_entry)
    we = te.normalize() - pd.Timedelta(days=te.dayofweek) + pd.Timedelta(weeks=1)
    if te == we - pd.Timedelta(weeks=1): we = te            # сигнал ровно на недельном закрытии
    if we > m.index[-1] + pd.Timedelta('15min'): continue   # неделя ещё не закрыта
    wkc = m.c.loc[:we - pd.Timedelta('15min')].iloc[-1]
    seg = m.loc[te:we - pd.Timedelta('15min')]
    ok = bool(wkc > ib_l)
    info.append(dict(side=s.side, ok=ok, hit_H_before_close=bool((seg.h >= H).any()), hit_mid_before_close=bool((seg.h >= L + R / 2).any())))
    if ok:
        d = s._asdict(); d.pop('Index')
        a.append(d)
        d2 = dict(d); d2['t_entry'] = str(we); d2['conf'] = d['conf'] + ' · вход на недельном закрытии'; b.append(d2)
I = pd.DataFrame(info)
summ = {}
for nm, g in (('all', I), ('low', I[I.side == 'low'])):
    gk = g[g.ok]
    summ[nm] = dict(n_signals=int(len(g)), wk_close_above_ib=round(float(g.ok.mean() * 100), 1),
                    of_ok_H_already_before_close=round(float(gk.hit_H_before_close.mean() * 100), 1) if len(gk) else None,
                    of_ok_mid_already_before_close=round(float(gk.hit_mid_before_close.mean() * 100), 1) if len(gk) else None)
pd.DataFrame(a).to_csv(OUT + '_sig.csv', index=False); pd.DataFrame(b).to_csv(OUT + '_wk.csv', index=False)
json.dump(summ, open(OUT + '_summary.json', 'w'), ensure_ascii=False, indent=1); print(json.dumps(summ, ensure_ascii=False))
