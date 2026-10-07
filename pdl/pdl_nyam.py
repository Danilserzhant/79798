"""Снятие PDL в NY AM (09:30–12:00 America/New_York) + инверсия последнего медвежьего H1 FVG до экстремума снятия.
Инвалидация — дневная свеча (UTC) закрылась ниже PDL до сигнала; окно максимум 48 ч от снятия.
Вход — закрытие H1 выше верха FVG; стоп — под лоем снятия −0,1%; цели 1R / 2R / PDH; издержки 0,1%; удержание до 5 дней.
Снятие PDH (шорт) — зеркально. python pdl_nyam.py <dir_pkl> <out.csv> [SYM ...]"""
import sys, os, numpy as np, pandas as pd
SRC, OUT = sys.argv[1], sys.argv[2]
SYMS = sys.argv[3:] or [f[:-4] for f in sorted(os.listdir(SRC)) if f.endswith('.pkl')]
COST = 0.001; rows = []
def ny_am(ts):
    t = ts.tz_localize('UTC').tz_convert('America/New_York')
    mins = t.hour * 60 + t.minute
    return 9 * 60 + 30 <= mins < 12 * 60
for sym in SYMS:
    raw = pd.read_pickle(f'{SRC}/{sym}.pkl')
    for side in ('low', 'high'):
        m = raw if side == 'low' else pd.DataFrame({'o': -raw.o, 'h': -raw.l, 'l': -raw.h, 'c': -raw.c}, index=raw.index)
        D = m.resample('1D').agg(h=('h', 'max'), l=('l', 'min'), c=('c', 'last')).dropna()
        H1 = m.resample('1h').agg(h=('h', 'max'), l=('l', 'min'), c=('c', 'last')).dropna()
        hv, lv, cv, hi = H1.h.values, H1.l.values, H1.c.values, H1.index
        ql, qh, qc, qi = m.l.values, m.h.values, m.c.values, m.index
        for d in range(1, len(D)):
            day = D.index[d]; PDL, PDH = D.l.iloc[d - 1], D.h.iloc[d - 1]
            a, b = qi.searchsorted(day), qi.searchsorted(day + pd.Timedelta('1D'))
            br = np.nonzero(ql[a:b] < PDL)[0]
            if not len(br): continue
            t_sw = qi[a + br[0]]
            if not ny_am(t_sw): continue
            r = dict(sym=sym, side=side, day=str(day.date()), t_sweep=str(t_sw), status='нет сигнала')
            # окно: до 48 ч или до дневного закрытия ниже PDL
            end = t_sw + pd.Timedelta('48h')
            for dd in range(d, min(d + 3, len(D))):
                dc_t = D.index[dd] + pd.Timedelta('1D')
                if dc_t > end: break
                if D.c.iloc[dd] < PDL: end = dc_t; r['inval_t'] = str(dc_t); break
            j0 = hi.searchsorted(t_sw.floor('1h')); sig = None
            for j in range(j0, len(H1)):
                tclose = hi[j] + pd.Timedelta('1h')
                if tclose > end: break
                x = j0 + int(np.argmin(lv[j0:j + 1]))
                if x == j: continue
                top = None
                for k in range(x, max(2, x - 48), -1):
                    if hv[k] < lv[k - 2] and not (cv[k + 1:x + 1] > lv[k - 2]).any():
                        top = lv[k - 2]; kk = k; break
                if top is None: continue
                if cv[j] > top and not (cv[x + 1:j] > top).any():
                    sig = j; break
            if sig is None:
                r['status'] = 'инвалидация' if 'inval_t' in r else 'нет сигнала'; rows.append(r); continue
            tE = hi[sig] + pd.Timedelta('1h'); entry = cv[sig]
            sweep_low = ql[qi.searchsorted(t_sw):qi.searchsorted(tE)].min()
            stop = sweep_low - 0.001 * abs(sweep_low); risk = entry - stop
            if risk <= 0: continue
            s0 = qi.searchsorted(tE); s1 = qi.searchsorted(tE + pd.Timedelta('5D'))
            fh, fl = qh[s0:s1], ql[s0:s1]
            def first(mk):
                q = np.nonzero(mk)[0]; return q[0] if len(q) else 10**9
            iS = first(fl <= stop); cost = COST * abs(entry) / risk
            r.update(status='сделка', t_entry=str(tE), entry=entry * (1 if side == 'low' else -1), risk_pct=risk / abs(entry) * 100,
                     hours_to_signal=(tE - t_sw).total_seconds() / 3600, sweep_depth_pct=(PDL - sweep_low) / abs(PDL) * 100)
            for nm, tgt in (('1R', entry + risk), ('2R', entry + 2 * risk), ('PDH', PDH)):
                if tgt <= entry: r[f'win_{nm}'] = None; r[f'net_{nm}'] = None; r[f'rr_{nm}'] = None; continue
                iT = first(fh >= tgt); rr = (tgt - entry) / risk; win = iT < iS
                r[f'win_{nm}'] = bool(win); r[f'rr_{nm}'] = rr; r[f'net_{nm}'] = (rr if win else -1) - cost
            rows.append(r)
D_ = pd.DataFrame(rows); D_.to_csv(OUT, index=False)
def show(nm, g):
    n = len(g); t = g[g.status == 'сделка']
    if not n: return
    print(f'== {nm}: снятий в NY AM {n} | сигнал {len(t)} ({len(t)/n*100:.0f}%) | инвалидация {(g.status=="инвалидация").mean()*100:.0f}% | нет сигнала за 48ч {(g.status=="нет сигнала").mean()*100:.0f}%')
    if not len(t): return
    print(f'   риск мед {t.risk_pct.median():.2f}% | до сигнала мед {t.hours_to_signal.median():.1f} ч')
    for k in ('1R', '2R', 'PDH'):
        tt = t[t[f'win_{k}'].notna()]
        if not len(tt): continue
        w = tt[f'win_{k}'].astype(bool); net = tt[f'net_{k}'].astype(float)
        yrs = pd.to_datetime(tt.t_entry).dt.year
        extra = f' RR мед {tt[f"rr_{k}"].median():.1f}' if k == 'PDH' else ''
        print(f'   цель {k:3s} (n={len(tt):3d}) раньше стопа {w.mean()*100:3.0f}%{extra} | итого {net.sum():+6.1f}R ср. {net.mean():+.2f}R | 2020–23 {net[yrs<=2023].mean():+.2f}R  2024–26 {net[yrs>2023].mean():+.2f}R')
ALTS = [s for s in D_.sym.unique() if s != 'BTCUSDT']
for nm, g in (('ETH, снятие PDL (лонг)', D_[(D_.sym == 'ETHUSDT') & (D_.side == 'low')]),
              ('ETH, снятие PDH (шорт)', D_[(D_.sym == 'ETHUSDT') & (D_.side == 'high')]),
              ('Альты, снятие PDL (лонг)', D_[D_.sym.isin(ALTS) & (D_.side == 'low')]),
              ('Альты, снятие PDH (шорт)', D_[D_.sym.isin(ALTS) & (D_.side == 'high')])):
    show(nm, g)
