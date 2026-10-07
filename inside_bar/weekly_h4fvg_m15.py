"""После недельного подтверждения (неделя снятия лоя матери закрылась выше лоя матери) — восходящий H4 FVG
(последний незаполненный после лоя манипуляции; если нет — первый новый после закрытия недели) → тест → инверсия M15
(закрытие выше верха последнего медвежьего M15 FVG перед локальным лоем отката). Отмена — закрытие H4 ниже низа FVG.
Окно 2 недели, хай матери не взят. Цели: хай матери / середина / 2R; горизонт 3 недели; издержки 0,1%.
Варианты: A — стоп под локальным лоем; B — стоп под низом H4 FVG; C — лимит на верх H4 FVG, стоп под низом FVG.
python weekly_h4fvg_m15.py <dir_pkl> <mother_events.csv> <weekly_confirmed_signals_wk.csv> <out.csv>"""
import sys, numpy as np, pandas as pd
SRC, EV, WC, OUT = sys.argv[1:5]
E = pd.read_csv(EV); E = E[(E.side == 'low') & (~E.open)]
WCx = pd.read_csv(WC); WCx = WCx[(WCx.side == 'low') & WCx.conf.str.startswith('Инверсия H4')]
strict = {(r.sym, r.ib_week) for r in WCx.itertuples()}
cache = {}; rows = []
def outcome(m, entry, stop, t_start, L, H, pref, r):
    risk = entry - stop
    if risk <= 0: return
    f = m.loc[t_start:t_start + pd.Timedelta(weeks=3)]; fh, fl = f.h.values, f.l.values
    def first(mk):
        q = np.nonzero(mk)[0]; return q[0] if len(q) else 10**9
    iS = first(fl <= stop); cost = 0.001 * entry / risk
    r[f'{pref}risk'] = risk / entry * 100
    for nm, tgt in (('mH', H), ('mid', (L + H) / 2), ('2R', entry + 2 * risk)):
        if tgt <= entry: r[f'{pref}{nm}'] = np.nan; continue
        rr = (tgt - entry) / risk; r[f'{pref}{nm}'] = (rr if first(fh >= tgt) < iS else -1) - cost; r[f'{pref}rr_{nm}'] = rr
for e in E.itertuples():
    if e.sym not in cache:
        m = pd.read_pickle(f'{SRC}/{e.sym}.pkl')
        cache[e.sym] = (m, m.resample('4h').agg(h=('h', 'max'), l=('l', 'min'), c=('c', 'last')).dropna())
    m, b4 = cache[e.sym]; L, H = e.L, e.H; t0 = pd.Timestamp(e.t0)
    we = t0.normalize() - pd.Timedelta(days=t0.dayofweek) + pd.Timedelta(weeks=1)
    if we + pd.Timedelta(weeks=2) > m.index[-1]: continue
    if m.c.loc[:we - pd.Timedelta('15min')].iloc[-1] <= L: continue
    if m.loc[t0:we - pd.Timedelta('15min')].h.max() >= H: continue
    r = dict(sym=e.sym, ib_week=e.ib_week, yr=we.year, strict=(e.sym, e.ib_week) in strict, stage='нет H4 FVG')
    ext_t = m.loc[t0:we - pd.Timedelta('15min')].l.idxmin(); manip = m.loc[t0:we - pd.Timedelta('15min')].l.min() * 0.999
    h4h, h4l, h4c, h4i = b4.h.values, b4.l.values, b4.c.values, b4.index
    kx = b4.index.searchsorted(ext_t.floor('4h')); kw = b4.index.searchsorted(we) - 1
    fvg = None
    for k in range(kw, kx + 1, -1):                       # последний незаполненный восходящий FVG до закрытия недели
        if h4l[k] > h4h[k - 2] and k - 2 >= kx:
            bot, top = h4h[k - 2], h4l[k]
            if not (h4l[k + 1:kw + 1] <= top).any(): fvg = (bot, top, h4i[k] + pd.Timedelta('4h')); break
    if fvg is None:
        for k in range(kw + 1, min(len(b4), kw + 1 + 84)):
            if h4l[k] > h4h[k - 2]: fvg = (h4h[k - 2], h4l[k], h4i[k] + pd.Timedelta('4h')); break
    if fvg is None: rows.append(r); continue
    bot, top, tf = fvg; start = max(we, tf); end = we + pd.Timedelta(weeks=2)
    seg = m.loc[start:end]
    if seg.h.max() >= H and (seg.l.values <= top).any():
        # хай матери раньше теста?
        iH = np.nonzero(seg.h.values >= H)[0][0]; iT = np.nonzero(seg.l.values <= top)[0][0]
        if iH < iT: r['stage'] = 'хай матери раньше теста'; rows.append(r); continue
    touch = np.nonzero(seg.l.values <= top)[0]
    if not len(touch): r['stage'] = 'нет теста'; rows.append(r); continue
    it = touch[0]; t_touch = seg.index[it]
    r['stage'] = 'тест без сигнала'
    outcome(m, top, bot * 0.999, t_touch, L, H, 'C_', r)                       # C: лимит на верх FVG
    outcome(m, top, manip, t_touch, L, H, 'E_', r)                             # E: лимит, стоп под лоем манипуляции
    pre = m.loc[t_touch - pd.Timedelta('12h'):end]
    P_h, P_l, P_c, P_i = pre.h.values, pre.l.values, pre.c.values, pre.index
    i0 = int(np.searchsorted(P_i, t_touch)); lo, lo_i = P_l[i0], i0; sig = None
    for i in range(i0, len(pre)):
        tc = P_i[i] + pd.Timedelta('15min')
        if tc.hour % 4 == 0 and tc.minute == 0:
            hb = h4i.searchsorted(tc - pd.Timedelta('4h'))
            if hb < len(b4) and h4i[hb] + pd.Timedelta('4h') == tc and h4c[hb] < bot:
                r['stage'] = 'отмена (H4 ниже FVG)'; break
        if P_l[i] < lo: lo, lo_i = P_l[i], i
        if i <= lo_i: continue
        q_top = None
        for q in range(lo_i, max(2, lo_i - 200), -1):
            if P_h[q] < P_l[q - 2] and not (P_c[q + 1:lo_i + 1] > P_l[q - 2]).any():
                q_top = P_l[q - 2]; break
        if q_top is None: continue
        if P_c[i] > q_top and not (P_c[lo_i + 1:i] > q_top).any(): sig = i; break
    if sig is not None:
        r['stage'] = 'сделка'; entry = P_c[sig]; ts = P_i[sig] + pd.Timedelta('15min')
        outcome(m, entry, lo * 0.999, ts, L, H, 'A_', r)
        outcome(m, entry, bot * 0.999, ts, L, H, 'B_', r)
        outcome(m, entry, manip, ts, L, H, 'D_', r)
    rows.append(r)
X = pd.DataFrame(rows); X.to_csv(OUT, index=False)
def show(nm, g):
    print(f'\n######## {nm}: подтверждённых недельных сетапов {len(g)} | стадии {g.stage.value_counts().to_dict()}')
    for pref, lab in (('D_', 'D: инверсия M15, стоп под лоем манипуляции'), ('E_', 'E: лимит на верх H4 FVG, стоп под лоем манипуляции')):
        s = g[g[f'{pref}risk'].notna()] if f'{pref}risk' in g else g.iloc[0:0]
        if not len(s): continue
        print(f'   {lab}: сделок {len(s)} | риск мед {s[f"{pref}risk"].median():.2f}%')
        for k, l2 in (('mH', 'хай матери'), ('mid', 'середина матери'), ('2R', '2R')):
            if f'{pref}{k}' not in s: continue
            v = s[f'{pref}{k}'].dropna()
            if not len(v): continue
            yrs = s.loc[v.index, 'yr']
            print(f'      {l2:16s} (n={len(v):3d}, RR мед {s[f"{pref}rr_{k}"].dropna().median():4.1f}): до цели {(v>0).mean()*100:3.0f}% | ср. {v.mean():+.2f}R итого {v.sum():+6.1f}R | 2020–23 {v[yrs<=2023].mean():+.2f}R 2024–26 {v[yrs>2023].mean():+.2f}R')
show('ETH', X[X.sym == 'ETHUSDT']); show('9 монет', X); show('9 монет, строго (+сигнал H4)', X[X.strict])
