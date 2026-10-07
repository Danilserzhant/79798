"""После инверсии H4 FVG у лоя матери (лонг-сигнал недельного сетапа) → восходящий H4 FVG (центр — свеча инверсии или позже, до 12 H4)
→ тест → инверсия M15 (закрытие выше верха последнего медвежьего M15 FVG перед локальным лоем; лой пересчитывается).
Отмена — закрытие H4 ниже низа восходящего FVG; окно 2 недели; хай матери не взят до теста. Горизонт 3 недели. Издержки 0,1%.
Стопы: A — под локальным лоем M15; B — под низом H4 FVG; D — под лоем манипуляции. E — лимит на верх FVG, стоп под лоем манипуляции.
python inv_h4fvg_m15.py <dir_pkl> <mother_events.csv> <ifvg_signals.csv> <out.csv>"""
import sys, numpy as np, pandas as pd
SRC, EV, SG, OUT = sys.argv[1:5]
E = pd.read_csv(EV); ev = {(r.sym, r.side, r.ib_week): r for r in E.itertuples()}
Sg = pd.read_csv(SG); Sg = Sg[(Sg.side == 'low') & Sg.conf.str.startswith('Инверсия H4') & (~Sg.open)]
cache = {}; rows = []
def outcome(m, entry, stop, t_start, L, H, pref, r):
    risk = entry - stop
    if risk <= 0: return
    f = m.loc[t_start:t_start + pd.Timedelta(weeks=3)]; fh, fl = f.h.values, f.l.values
    def first(mk):
        q = np.nonzero(mk)[0]; return q[0] if len(q) else 10**9
    iS = first(fl <= stop); cost = 0.001 * entry / risk; r[f'{pref}risk'] = risk / entry * 100
    for nm, tgt in (('mH', H), ('mid', (L + H) / 2), ('2R', entry + 2 * risk)):
        if tgt <= entry: r[f'{pref}{nm}'] = np.nan; continue
        rr = (tgt - entry) / risk; r[f'{pref}{nm}'] = (rr if first(fh >= tgt) < iS else -1) - cost; r[f'{pref}rr_{nm}'] = rr
for s in Sg.itertuples():
    e = ev[(s.sym, s.side, s.ib_week)]
    if s.sym not in cache:
        m = pd.read_pickle(f'{SRC}/{s.sym}.pkl')
        cache[s.sym] = (m, m.resample('4h').agg(h=('h', 'max'), l=('l', 'min'), c=('c', 'last')).dropna())
    m, b4 = cache[s.sym]; L, H, R = e.L, e.H, e.R; t0 = pd.Timestamp(e.t0)
    tsig = pd.Timestamp(s.t_entry); tinv = tsig - pd.Timedelta('4h'); j = b4.index.get_loc(tinv)
    manip_low = m.loc[t0:tsig - pd.Timedelta('15min')].l.min(); manip = manip_low * 0.999
    we = tsig.normalize() - pd.Timedelta(days=tsig.dayofweek) + pd.Timedelta(weeks=1)
    wk_ok = m.c.loc[:we - pd.Timedelta('15min')].iloc[-1] > L if we <= m.index[-1] else None
    r = dict(sym=s.sym, ib_week=s.ib_week, yr=tsig.year, depth=(L - manip_low) / R, wk_ok=wk_ok, stage='нет H4 FVG')
    h4h, h4l, h4c, h4i = b4.h.values, b4.l.values, b4.c.values, b4.index
    kf = next((k for k in range(j + 1, min(len(b4), j + 13)) if k - 1 >= j and h4l[k] > h4h[k - 2]), None)
    if kf is None: rows.append(r); continue
    bot, top = h4h[kf - 2], h4l[kf]; tf = h4i[kf] + pd.Timedelta('4h'); end = tf + pd.Timedelta(weeks=2)
    seg = m.loc[tf:end]
    touch = np.nonzero(seg.l.values <= top)[0]; hiH = np.nonzero(seg.h.values >= H)[0]
    if len(hiH) and (not len(touch) or hiH[0] < touch[0]): r['stage'] = 'хай матери раньше теста'; rows.append(r); continue
    if not len(touch): r['stage'] = 'нет теста'; rows.append(r); continue
    t_touch = seg.index[touch[0]]; r['stage'] = 'тест без сигнала'
    outcome(m, top, manip, t_touch, L, H, 'E_', r)
    pre = m.loc[t_touch - pd.Timedelta('12h'):end]; P_h, P_l, P_c, P_i = pre.h.values, pre.l.values, pre.c.values, pre.index
    i0 = int(np.searchsorted(P_i, t_touch)); lo, lo_i = P_l[i0], i0; sig = None
    for i in range(i0, len(pre)):
        tc = P_i[i] + pd.Timedelta('15min')
        if tc.hour % 4 == 0 and tc.minute == 0:
            hb = h4i.searchsorted(tc - pd.Timedelta('4h'))
            if hb < len(b4) and h4i[hb] + pd.Timedelta('4h') == tc and h4c[hb] < bot: r['stage'] = 'отмена (H4 ниже FVG)'; break
        if P_l[i] < lo: lo, lo_i = P_l[i], i
        if i <= lo_i: continue
        q_top = None
        for q in range(lo_i, max(2, lo_i - 200), -1):
            if P_h[q] < P_l[q - 2] and not (P_c[q + 1:lo_i + 1] > P_l[q - 2]).any(): q_top = P_l[q - 2]; break
        if q_top is None: continue
        if P_c[i] > q_top and not (P_c[lo_i + 1:i] > q_top).any(): sig = i; break
    if sig is not None:
        r['stage'] = 'сделка'; entry = P_c[sig]; ts = P_i[sig] + pd.Timedelta('15min')
        outcome(m, entry, lo * 0.999, ts, L, H, 'A_', r); outcome(m, entry, bot * 0.999, ts, L, H, 'B_', r); outcome(m, entry, manip, ts, L, H, 'D_', r)
    rows.append(r)
X = pd.DataFrame(rows); X.to_csv(OUT, index=False)
def show(nm, g):
    print(f'\n######## {nm}: инверсий H4 {len(g)} | {g.stage.value_counts().to_dict()}')
    for pref, lab in (('A_', 'A: инверсия M15, стоп под локальным лоем'), ('B_', 'B: инверсия M15, стоп под низом H4 FVG'),
                      ('D_', 'D: инверсия M15, стоп под лоем манипуляции'), ('E_', 'E: лимит на верх H4 FVG, стоп под лоем манипуляции')):
        if f'{pref}risk' not in g: continue
        s = g[g[f'{pref}risk'].notna()]
        if not len(s): continue
        print(f'   {lab}: сделок {len(s)} | риск мед {s[f"{pref}risk"].median():.2f}%')
        for k, l2 in (('mH', 'хай матери'), ('mid', 'середина матери'), ('2R', '2R')):
            v = s[f'{pref}{k}'].dropna()
            if not len(v): continue
            yrs = s.loc[v.index, 'yr']
            print(f'      {l2:16s} (n={len(v):3d}, RR мед {s[f"{pref}rr_{k}"].dropna().median():5.1f}): до цели {(v>0).mean()*100:3.0f}% | ср. {v.mean():+.2f}R итого {v.sum():+6.1f}R | 2020–23 {v[yrs<=2023].mean():+.2f}R 2024–26 {v[yrs>2023].mean():+.2f}R')
show('ETH, снятие лоя матери', X[X.sym == 'ETHUSDT']); show('9 монет', X); show('9 монет, вынос ≥ 0,40', X[X.depth >= 0.4])
