"""PDL NY AM → инверсия H4 FVG (закрытие H4) → восходящий H4 FVG, сформированный свечой инверсии или после неё (до 12 H4) →
тест этого FVG → инверсия M15: закрытие M15 выше верха последнего медвежьего M15 FVG перед локальным лоем отката (лой пересчитывается).
Отмена — закрытие H4 ниже низа восходящего H4 FVG; окно 5 дней после формирования FVG. Стоп — под локальным лоем −0,1%.
Цели: 1R/2R/3R, PDH, хай движения после инверсии. Издержки 0,1%.
python pdl_h4_m15.py <dir_pkl> <pdl_h4_trades.csv> <out.csv>"""
import sys, numpy as np, pandas as pd
SRC, TR, OUT = sys.argv[1:4]
T = pd.read_csv(TR); T = T[(T.status == 'сделка') & (T.side == 'low') & (T.sym != 'BTCUSDT')]
cache = {}; rows = []
for t in T.itertuples():
    if t.sym not in cache:
        m = pd.read_pickle(f'{SRC}/{t.sym}.pkl')
        cache[t.sym] = (m, m.resample('4h').agg(h=('h', 'max'), l=('l', 'min'), c=('c', 'last')).dropna(),
                        m.resample('1D').agg(h=('h', 'max'), l=('l', 'min')).dropna())
    m, b4, D = cache[t.sym]
    day = pd.Timestamp(t.day); di = D.index.get_loc(day); PDH = D.h.iloc[di - 1]
    tinv = pd.Timestamp(t.t_entry) - pd.Timedelta('4h'); j = b4.index.get_loc(tinv)
    h4h, h4l, h4c, h4i = b4.h.values, b4.l.values, b4.c.values, b4.index
    r = dict(sym=t.sym, day=t.day, yr=day.year, stage='нет H4 FVG')
    kf = next((k for k in range(j + 1, min(len(b4), j + 13)) if k - 1 >= j and h4l[k] > h4h[k - 2]), None)
    if kf is None: rows.append(r); continue
    fb, ft = h4h[kf - 2], h4l[kf]; tf = h4i[kf] + pd.Timedelta('4h')
    swing_hi = m.loc[tinv:tf - pd.Timedelta('15min')].h.max()
    seg = m.loc[tf:tf + pd.Timedelta('5D')]
    q_h, q_l, q_c, q_i = seg.h.values, seg.l.values, seg.c.values, seg.index
    touch = np.nonzero(q_l <= ft)[0]
    if not len(touch): r['stage'] = 'нет теста'; rows.append(r); continue
    it = touch[0]; swing_hi = max(swing_hi, q_h[:it + 1].max()) if it > 0 else swing_hi
    def outcome(entry, stop, start_t, pref):
        risk = entry - stop
        if risk <= 0: return
        f = m.loc[start_t:start_t + pd.Timedelta('5D')]; fh, fl = f.h.values, f.l.values
        def first(mk):
            q = np.nonzero(mk)[0]; return q[0] if len(q) else 10**9
        iS = first(fl <= stop); cost = 0.001 * entry / risk
        r[f'{pref}risk_pct'] = risk / entry * 100
        for nm, tgt in (('1R', entry + risk), ('2R', entry + 2 * risk), ('PDH', PDH), ('SH', swing_hi)):
            if tgt <= entry: r[f'{pref}n_{nm}'] = np.nan; continue
            rr = (tgt - entry) / risk; w = first(fh >= tgt) < iS
            r[f'{pref}n_{nm}'] = (rr if w else -1) - cost; r[f'{pref}rr_{nm}'] = rr
    # B: лимит на верх FVG; в свече касания стоп проверяется сразу (консервативно)
    outcome(ft, fb * 0.999, q_i[it], 'B_')
    r['stage'] = 'тест без сигнала'
    # M15 данные с запасом назад для поиска FVG
    pre = m.loc[q_i[it] - pd.Timedelta('12h'):q_i[-1]]
    P_h, P_l, P_c, P_i = pre.h.values, pre.l.values, pre.c.values, pre.index
    i0 = int(np.searchsorted(P_i, q_i[it])); lo, lo_i = P_l[i0], i0; sig = None
    for i in range(i0, len(pre)):
        tclose = P_i[i] + pd.Timedelta('15min')
        # отмена: закрытие H4 ниже низа восходящего FVG
        if tclose.hour % 4 == 0 and tclose.minute == 0:
            hb = b4.index.searchsorted(tclose - pd.Timedelta('4h'))
            if hb < len(b4) and h4i[hb] + pd.Timedelta('4h') == tclose and h4c[hb] < fb:
                r['stage'] = 'отмена (H4 ниже FVG)'; break
        if P_l[i] < lo: lo, lo_i = P_l[i], i
        if i <= lo_i: continue
        top = None
        for q in range(lo_i, max(2, lo_i - 200), -1):
            if P_h[q] < P_l[q - 2] and not (P_c[q + 1:lo_i + 1] > P_l[q - 2]).any():
                top = P_l[q - 2]; break
        if top is None: continue
        if P_c[i] > top and not (P_c[lo_i + 1:i] > top).any():
            sig = i; break
    if sig is None: rows.append(r); continue
    entry = P_c[sig]; stop = lo * 0.999; risk = entry - stop
    if risk <= 0: rows.append(r); continue
    f = m.loc[P_i[sig] + pd.Timedelta('15min'):P_i[sig] + pd.Timedelta('5D')]; fh, fl = f.h.values, f.l.values
    def first(mk):
        q = np.nonzero(mk)[0]; return q[0] if len(q) else 10**9
    iS = first(fl <= stop); cost = 0.001 * entry / risk
    r.update(stage='сделка', t=str(P_i[sig]), entry=entry, risk_pct=risk / entry * 100, fvg_size_pct=(ft - fb) / fb * 100)
    outcome(entry, fb * 0.999, P_i[sig] + pd.Timedelta('15min'), 'A_')
    for nm, tgt in (('1R', entry + risk), ('2R', entry + 2 * risk), ('3R', entry + 3 * risk), ('PDH', PDH), ('SH', swing_hi)):
        if tgt <= entry: r[f'n_{nm}'] = np.nan; r[f'rr_{nm}'] = np.nan; continue
        rr = (tgt - entry) / risk; w = first(fh >= tgt) < iS
        r[f'n_{nm}'] = (rr if w else -1) - cost; r[f'rr_{nm}'] = rr
    rows.append(r)
X = pd.DataFrame(rows); X.to_csv(OUT, index=False)
def show2(lab, s, pref):
    s = s[s[f'{pref}risk_pct'].notna()] if f'{pref}risk_pct' in s else s.iloc[0:0]
    if not len(s): return
    print(f'   {lab}: сделок {len(s)} | риск мед {s[f"{pref}risk_pct"].median():.2f}%')
    for k in ('1R', '2R', 'PDH', 'SH'):
        v = s[f'{pref}n_{k}'].dropna()
        if not len(v): continue
        yrs = s.loc[v.index, 'yr']
        print(f'      цель {k:3s} (n={len(v):3d}, RR мед {s[f"{pref}rr_{k}"].dropna().median():4.1f}): до цели {(v > 0).mean()*100:3.0f}% | ср. {v.mean():+.2f}R итого {v.sum():+6.1f}R | 2020–23 {v[yrs<=2023].mean():+.2f}R 2024–26 {v[yrs>2023].mean():+.2f}R')
for nm, g in (('ETH', X[X.sym == 'ETHUSDT']), ('Альты вместе (вкл. ETH)', X)):
    print(f'\n#### {nm}')
    show2('A: инверсия M15, стоп под низом H4 FVG', g[g.stage == 'сделка'], 'A_')
    show2('B: лимит на верх H4 FVG при тесте, стоп под низом FVG', g, 'B_')
for nm, g in (('ETH', X[X.sym == 'ETHUSDT']), ('Альты вместе (вкл. ETH)', X)):
    s = g[g.stage == 'сделка']
    print(f'\n== {nm}: инверсий H4 {len(g)} | стадии: {g.stage.value_counts().to_dict()}')
    if not len(s): continue
    print(f'   сделок {len(s)} | риск мед {s.risk_pct.median():.2f}%')
    for k in ('1R', '2R', '3R', 'PDH', 'SH'):
        v = s[f'n_{k}'].dropna()
        if not len(v): continue
        rr = s[f'rr_{k}'].dropna().median()
        yrs = s.loc[v.index, 'yr']
        print(f'   цель {k:3s} (n={len(v):3d}, RR мед {rr:4.1f}): до цели {(v > 0).mean()*100:3.0f}% | ср. {v.mean():+.2f}R итого {v.sum():+6.1f}R | 2020–23 {v[yrs<=2023].mean():+.2f}R 2024–26 {v[yrs>2023].mean():+.2f}R')
