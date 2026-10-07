"""Глубокий разбор недельных инсайдов ETH: SMT с BTC, стоп, сценарий провала, цели, время, качество IB,
контекст, объём, дневные и месячные инсайды. python eth_deep.py <dir_with_ETH_BTC_vol_pkl> <events.csv> <out.json>"""
import sys, os, json, numpy as np, pandas as pd
SRC, EV, OUT = sys.argv[1:4]
eth, btc = pd.read_pickle(f'{SRC}/ETHUSDT.pkl'), pd.read_pickle(f'{SRC}/BTCUSDT.pkl')
E = pd.read_csv(EV); E = E[E.sym == 'ETHUSDT']
NEVER = pd.Timestamp.max; W4 = pd.Timedelta(weeks=4)
def mirror(df, side):
    return df if side == 'low' else pd.DataFrame({'o': -df.o, 'h': -df.l, 'l': -df.h, 'c': -df.c, 'qv': df.qv}, index=df.index)
def wagg(df):
    return df.resample('W-MON', label='left', closed='left').agg(o=('o', 'first'), h=('h', 'max'), l=('l', 'min'), c=('c', 'last'), qv=('qv', 'sum')).dropna()
def first(f, mk):
    i = np.nonzero(mk)[0]; return f.index[i[0]] if len(i) else NEVER
def sess(h):
    return 'Азия 00–08' if h < 8 else ('Лондон 08–13' if h < 13 else ('Нью-Йорк 13–21' if h < 21 else 'Поздний 21–24'))
rows = []; cur = None
DQ = {sd: eth.resample('1D').agg(qv=('qv', 'sum')) for sd in ('low', 'high')}
for e in E.itertuples():
    m, b = mirror(eth, e.side), mirror(btc, e.side)
    W, WB = wagg(m), wagg(b)
    sg = 1 if e.side == 'low' else -1
    L, H, R = sg * e.L, sg * e.H, e.R
    t0 = pd.Timestamp(e.t0); ibw = pd.Timestamp(e.ib_week); mow = ibw - pd.Timedelta(weeks=1)
    ib, mo = W.loc[ibw], W.loc[mow]
    LV = L if os.environ.get('LEVEL') == 'mother' else ib.l   # уровень подтверждения/отмены
    we = t0.normalize() - pd.Timedelta(days=t0.dayofweek) + pd.Timedelta(weeks=1)
    closed = we <= m.index[-1] + pd.Timedelta('15min')
    wk = m.loc[t0.normalize() - pd.Timedelta(days=t0.dayofweek):we - pd.Timedelta('15min')]
    wkc = wk.c.iloc[-1]
    ext_t = m.loc[t0:we - pd.Timedelta('15min')].l.idxmin(); sweep_low = m.loc[t0:we - pd.Timedelta('15min')].l.min()
    depth = (L - sweep_low) / R
    # исходы от первого снятия
    f0 = m.loc[t0:t0 + W4]
    tH0, tE0 = first(f0, f0.h.values >= H), first(f0, f0.l.values <= L - R)
    # SMT: BTC снял свой лой IB-недели / матери с начала недели снятия до её закрытия
    bwk = b.loc[t0.normalize() - pd.Timedelta(days=t0.dayofweek):min(we, b.index[-1] + pd.Timedelta('15min')) - pd.Timedelta('15min')]
    b_ib, b_mo = WB.loc[ibw], WB.loc[mow]
    btc_took_ib = bool(bwk.l.min() < b_ib.l); btc_took_mo = bool(bwk.l.min() < b_mo.l)
    btc_ib_inside = bool(b_ib.h <= b_mo.h and b_ib.l >= b_mo.l)
    # реклейм: первый час с закрытием выше лоя инсайда после экстремума
    hh = m.loc[ext_t:we].resample('1h').agg(c=('c', 'last')).dropna()
    rc = hh.index[hh.c.values > LV]; rec_t = rc[0] if len(rc) else None
    # от недельного закрытия
    r = dict(side=e.side, ib_week=e.ib_week, yr=t0.year, open=bool(e.open) or not closed, depth=depth,
             wk_ok=bool(wkc > LV), H0=tH0 < tE0, E10=tE0 < NEVER, reachH0=tH0 < NEVER,
             smt=not (btc_took_mo if os.environ.get('LEVEL') == 'mother' else btc_took_ib), btc_took_mo=btc_took_mo, btc_ib_inside=btc_ib_inside,
             dow=t0.dayofweek, ext_dow=ext_t.dayofweek, ext_sess=sess(ext_t.hour), rec_sess=sess(rec_t.hour) if rec_t is not None else None,
             ib_ratio=(ib.h - ib.l) / R, ib_close_pos=(ib.c - mo.l) / R, ib_green=bool(ib.c > ib.o),
             double_ib=bool(mow - pd.Timedelta(weeks=1) in W.index and mo.h <= W.loc[mow - pd.Timedelta(weeks=1)].h and mo.l >= W.loc[mow - pd.Timedelta(weeks=1)].l),
             mom4=(lambda p: (mo.c - p.c.iloc[-4]) / abs(p.c.iloc[-4]) * 100 if len(p) >= 4 else np.nan)(W.loc[:mow - pd.Timedelta(days=1)]),
             pos26=(mo.c - W.loc[:mow].l.tail(26).min()) / (W.loc[:mow].h.tail(26).max() - W.loc[:mow].l.tail(26).min()),
             vol_ratio=wk.qv.sum() / mo.qv * (7 / max(0.5, (wk.index[-1] - wk.index[0]).total_seconds() / 86400)),
             ext_day_vol=(lambda d: d.qv.loc[ext_t.normalize()] / d.qv.loc[:ext_t.normalize() - pd.Timedelta('1D')].tail(20).mean())(DQ[e.side]))
    if closed:
        f = m.loc[we:we + pd.Timedelta(weeks=8)]; f4 = m.loc[we:we + W4]
        tH, tN = first(f4, f4.h.values >= H), first(f4, f4.l.values < sweep_low)
        r.update(H_wk=tH < tN)
        if r['wk_ok']:                                    # цели и стоп после подтверждения
            for k, lv in (('mid', L + R / 2), ('ibh', ib.h), ('H', H), ('H05', H + R / 2), ('H1', H + R)):
                r[f'tg4_{k}'] = bool((f4.h >= lv).any()); r[f'tg8_{k}'] = bool((f.h >= lv).any())
            wkH = W.loc[we:we + pd.Timedelta(weeks=4)]
            r['wkclose_above_H'] = bool((wkH.c > H).any())
            pre = f4.loc[:tH] if tH < NEVER else f4
            r['dd_below_sweep_R'] = max(0, (sweep_low - pre.l.min()) / R)        # насколько обновили лой до хая
            r['dd_below_wkclose_R'] = (wkc - pre.l.min()) / R
        else:                                             # сценарий провала
            nxt = W.loc[we:we + pd.Timedelta(weeks=1)]
            r['next_wk_back'] = bool(len(nxt) and nxt.c.iloc[0] > LV) if len(nxt) else None
            for k in (0.5, 1, 1.5, 2):
                r[f'fail_E{k}'] = bool((f4.l <= L - k * R).any())
            r['fail_reachH'] = bool((f4.h >= H).any())
            r['fail_low_R'] = (L - f4.l.min()) / R
            r['fail_days_to_low'] = (f4.l.idxmin() - we).total_seconds() / 86400
    if e.open and e.side == 'low': cur = r
    rows.append(r)
D = pd.DataFrame(rows); D.to_csv(OUT.replace('.json', '_rows.csv'), index=False)
C = D[~D.open].copy()
for c_ in ('mom4', 'pos26', 'vol_ratio', 'ext_day_vol'): C[c_] = C[c_].astype(float)
P = lambda x: None if len(x) == 0 else round(float(np.mean(x)) * 100)
def grp(mask_dict, base=C):
    out = {}
    for k, mk in mask_dict.items():
        g = base[mk]; gl = g[g.side == 'low']
        out[k] = dict(n=int(len(g)), wk_ok=P(g.wk_ok), H0=P(g.H0), E10=P(g.E10), n_low=int(len(gl)), wk_ok_low=P(gl.wk_ok), H0_low=P(gl.H0))
    return out
res = {'n': int(len(C)), 'n_low': int((C.side == 'low').sum()), 'base': grp({'все': C.side == C.side})['все'], 'current': {k: (v if not isinstance(v, (np.floating, np.bool_)) else v.item()) for k, v in (cur or {}).items()}}
q3 = lambda c: C[c].quantile([1 / 3, 2 / 3]).values
def terc(c):
    a, b = q3(c); return {f'< {a:.2f}': C[c] < a, f'{a:.2f}–{b:.2f}': (C[c] >= a) & (C[c] < b), f'≥ {b:.2f}': C[c] >= b}
res['smt'] = grp({'SMT: BTC не снял свой лой инсайда': C.smt, 'BTC тоже снял лой инсайда': ~C.smt,
                  'BTC не снял даже лой матери': ~C.btc_took_mo, 'BTC снял лой матери': C.btc_took_mo})
res['smt_btc_ib'] = grp({'SMT и у BTC тоже инсайд': C.smt & C.btc_ib_inside, 'SMT, у BTC не инсайд': C.smt & ~C.btc_ib_inside})
res['depth'] = grp(terc('depth'))
res['ib_ratio'] = grp(terc('ib_ratio')); res['ib_close_pos'] = grp(terc('ib_close_pos'))
res['ib_green'] = grp({'IB закрылся в сторону от снятой стороны': C.ib_green, 'IB закрылся в сторону снятой стороны': ~C.ib_green})
res['double_ib'] = grp({'Двойной инсайд (мать сама инсайд)': C.double_ib, 'Обычный': ~C.double_ib})
res['mom4'] = grp(terc('mom4')); res['pos26'] = grp(terc('pos26'))
res['vol_ratio'] = grp(terc('vol_ratio')); res['ext_day_vol'] = grp(terc('ext_day_vol'))
res['dow'] = grp({d: C.dow == i for i, d in enumerate(['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'])})
res['ext_sess'] = grp({s: C.ext_sess == s for s in ['Азия 00–08', 'Лондон 08–13', 'Нью-Йорк 13–21', 'Поздний 21–24']})
res['ext_dow_dist'] = {d: int((C.ext_dow == i).sum()) for i, d in enumerate(['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'])}
res['rec_sess_dist'] = C.rec_sess.value_counts().to_dict()
OK, FL = C[C.wk_ok], C[~C.wk_ok]
res['after_confirm'] = dict(n=int(len(OK)), H_wk=P(OK.H_wk), **{k: P(OK[k]) for k in OK.columns if k.startswith('tg') or k == 'wkclose_above_H'},
                            dd_sweep_q=[round(float(x), 2) for x in OK.dd_below_sweep_R.quantile([.5, .8, .9, 1])],
                            dd_wkclose_q=[round(float(x), 2) for x in OK.dd_below_wkclose_R.quantile([.5, .8, .9, 1])],
                            win_dd_wkclose_q=[round(float(x), 2) for x in OK[OK.H_wk].dd_below_wkclose_R.quantile([.5, .8, .9, 1])],
                            win_new_low=P(OK[OK.H_wk].dd_below_sweep_R > 0))
res['after_fail'] = dict(n=int(len(FL)), next_wk_back=P(FL.next_wk_back.dropna().astype(bool)), reachH=P(FL.fail_reachH),
                         **{f'E{k}': P(FL[f'fail_E{k}']) for k in (0.5, 1, 1.5, 2)},
                         low_q=[round(float(x), 2) for x in FL.fail_low_R.quantile([.25, .5, .75])],
                         days_to_low_q=[round(float(x), 1) for x in FL.fail_days_to_low.quantile([.25, .5, .75])],
                         low_side=dict(n=int((FL.side == 'low').sum()), next_wk_back=P(FL[FL.side == 'low'].next_wk_back.dropna().astype(bool)),
                                       reachH=P(FL[FL.side == 'low'].fail_reachH), E1=P(FL[FL.side == 'low'].fail_E1), E2=P(FL[FL.side == 'low'].fail_E2)))
# ---------- дневные инсайды ETH ----------
def tf_ib(df, rule, wait, hold):
    out = []
    for side in ('low', 'high'):
        m = mirror(df, side)
        B = m.resample(rule, label='left', closed='left').agg(o=('o', 'first'), h=('h', 'max'), l=('l', 'min'), c=('c', 'last')).dropna()
        h, l, c = B.h.values, B.l.values, B.c.values
        for i in range(1, len(B) - wait - 1):
            if not (h[i] <= h[i - 1] and l[i] >= l[i - 1]): continue
            Lm, Hm, Rm = l[i - 1], h[i - 1], h[i - 1] - l[i - 1]
            if Rm <= 0: continue
            j = next((k for k in range(i + 1, i + 1 + wait) if l[k] < l[i] or h[k] > h[i]), None)
            if j is None or not (l[j] < l[i] and not h[j] > h[i]): continue
            ok = c[j] > l[i]
            fut = slice(j, min(len(B), j + hold))
            hit_H = np.nonzero(h[fut] >= Hm)[0]; hit_E = np.nonzero(l[fut] <= Lm - Rm)[0]
            tHm = hit_H[0] if len(hit_H) else 10**9; tEm = hit_E[0] if len(hit_E) else 10**9
            out.append(dict(side=side, ok=bool(ok), took_mo=bool(l[j] < Lm), H_first=tHm < tEm, reach_H=tHm < 10**9, E1=tEm < 10**9))
    return pd.DataFrame(out)
Dd = tf_ib(eth, '1D', 5, 20)
res['daily'] = dict(n=int(len(Dd)), close_back=P(Dd.ok), H_first=P(Dd.H_first), H_first_if_close_back=P(Dd[Dd.ok].H_first),
                    H_first_if_close_below=P(Dd[~Dd.ok].H_first), reach_H=P(Dd.reach_H), E1=P(Dd.E1),
                    took_mo=P(Dd.took_mo), H_first_mo_taken_close_back=P(Dd[Dd.took_mo & Dd.ok].H_first), n_mo_taken_close_back=int((Dd.took_mo & Dd.ok).sum()))
Mo = tf_ib(eth, 'MS', 3, 6)
res['monthly'] = dict(n=int(len(Mo)), close_back=P(Mo.ok), H_first=P(Mo.H_first), reach_H=P(Mo.reach_H))
MM = eth.resample('MS').agg(h=('h', 'max'), l=('l', 'min'))
res['monthly_now'] = dict(sep_h=float(MM.h.iloc[-2]), sep_l=float(MM.l.iloc[-2]), oct_h=float(MM.h.iloc[-1]), oct_l=float(MM.l.iloc[-1]),
                          oct_inside_so_far=bool(MM.h.iloc[-1] <= MM.h.iloc[-2] and MM.l.iloc[-1] >= MM.l.iloc[-2]))
json.dump(res, open(OUT, 'w'), ensure_ascii=False, indent=1, default=str)
print(json.dumps(res, ensure_ascii=False, indent=1, default=str))
