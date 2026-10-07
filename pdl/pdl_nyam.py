"""Снятие PDL в NY AM (09:30–12:00 America/New_York) + инверсия последнего медвежьего H1 FVG до экстремума снятия.
Инвалидация — дневная свеча (UTC) закрылась ниже PDL до сигнала; окно максимум 48 ч от снятия.
Вход — закрытие H1 выше верха FVG; стоп — под лоем снятия −0,1%; цели 1R / 2R / PDH; издержки 0,1%; удержание до 5 дней.
Снятие PDH (шорт) — зеркально. python pdl_nyam.py <dir_pkl> <out.csv> [SYM ...]"""
import sys, os, numpy as np, pandas as pd
SRC, OUT = sys.argv[1], sys.argv[2]
SYMS = sys.argv[3:] or [f[:-4] for f in sorted(os.listdir(SRC)) if f.endswith('.pkl')]
COST = 0.001; rows = []
# SEL=pdl: берём последний медвежий H1 FVG, у которого верх >= PDL (пересекает PDL или выше него)
SEL = os.environ.get('SEL', 'last')
FTF = os.environ.get('FTF', '1h')    # ТФ FVG: 1h или 4h
STF = os.environ.get('STF', FTF)     # ТФ закрытия-сигнала (выше верха FVG): 1h или 4h
LB = int(os.environ.get('LB', '48'))  # сколько баров FVG-ТФ искать назад от экстремума
def ny_am(ts):
    t = ts.tz_localize('UTC').tz_convert('America/New_York')
    mins = t.hour * 60 + t.minute
    return 9 * 60 + 30 <= mins < 12 * 60
for sym in SYMS:
    raw = pd.read_pickle(f'{SRC}/{sym}.pkl')
    for side in ('low', 'high'):
        m = raw if side == 'low' else pd.DataFrame({'o': -raw.o, 'h': -raw.l, 'l': -raw.h, 'c': -raw.c}, index=raw.index)
        D = m.resample('1D').agg(h=('h', 'max'), l=('l', 'min'), c=('c', 'last')).dropna()
        H1 = m.resample(FTF).agg(h=('h', 'max'), l=('l', 'min'), c=('c', 'last')).dropna()
        hv, lv, cv, hi = H1.h.values, H1.l.values, H1.c.values, H1.index
        SG = m.resample(STF).agg(c=('c', 'last')).dropna(); sgc, sgi = SG.c.values, SG.index
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
            j0 = hi.searchsorted(t_sw.floor(FTF)); sig = None
            s0 = sgi.searchsorted(t_sw.floor(STF))
            for js in range(s0, len(SG)):
                tclose = sgi[js] + pd.Timedelta(STF)
                if tclose > end: break
                # бары FVG-ТФ, полностью закрытые к tclose
                jf = hi.searchsorted(tclose - pd.Timedelta(FTF), side='right') - 1
                if jf < j0: continue
                lo_seg = ql[qi.searchsorted(t_sw):qi.searchsorted(tclose)]
                x = j0 + int(np.argmin(lv[j0:jf + 1]))
                top = None
                for k in range(min(x, jf), max(2, x - LB), -1):
                    if hv[k] < lv[k - 2] and not (cv[k + 1:x + 1] > lv[k - 2]).any():
                        if SEL == 'pdl' and lv[k - 2] < PDL: continue
                        top = lv[k - 2]; kk = k; break
                if top is None: continue
                # экстремум должен быть до сигнала: лой после экстремума не обновлялся
                t_ext = qi[qi.searchsorted(t_sw) + int(np.argmin(lo_seg))]
                if t_ext >= sgi[js]: continue
                prev = sgc[s0:js][sgi[s0:js] >= t_ext]
                if sgc[js] > top and not (prev > top).any():
                    sig = js; fvg_top, fvg_bot, fvg_t = top, hv[kk], hi[kk]; break
            if sig is None:
                r['status'] = 'инвалидация' if 'inval_t' in r else 'нет сигнала'; rows.append(r); continue
            tE = sgi[sig] + pd.Timedelta(STF); entry = sgc[sig]
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
            # диагностика
            pre = D.iloc[max(0, d - 6):d]
            r.update(pos_in_pd=(entry - PDL) / (PDH - PDL) if PDH > PDL else np.nan,
                     entry_vs_pdl_R=(entry - PDL) / risk, fvg_top_vs_pdl_pct=(fvg_top - PDL) / abs(PDL) * 100,
                     fvg_size_pct=(fvg_top - fvg_bot) / abs(PDL) * 100, fvg_age_h=(t_ext - fvg_t).total_seconds() / 3600,
                     prev_day_bull=bool(D.c.iloc[d - 1] > D.c.iloc[d - 2]) if d >= 2 else None,
                     trend5=float((D.c.iloc[d - 1] - D.c.iloc[d - 6]) / abs(D.c.iloc[d - 6]) * 100) if d >= 6 else np.nan,
                     pd_range_pct=(PDH - PDL) / abs(PDL) * 100, sig_same_day=bool(tE <= day + pd.Timedelta('1D')),
                     sig_ny=bool(ny_am(sgi[sig])), fvg_cross=bool(fvg_bot <= PDL), sig_hour_et=int(sgi[sig].tz_localize('UTC').tz_convert('America/New_York').hour))
            iS_ = iS if iS < 10**9 else len(fh) - 1
            r['mfe_R'] = (fh[:iS_ + 1].max() - entry) / risk if iS_ >= 0 and len(fh) else np.nan
            r['new_low_after'] = bool(len(fl) and fl.min() < sweep_low)
            # после стопа: ушла ли цена ниже ещё на 1R (продолжение) и вернулась ли к PDH
            if iS < 10**9:
                ah, al = fh[iS:], fl[iS:]
                r['after_stop_down1R'] = bool((al <= stop - risk).any()); r['after_stop_pdh'] = bool((ah >= PDH).any())
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
