"""Недельный dealing range от 3-свечного фрактала до фрактала: насколько глубоко цена откатывает перед реакцией.
Ножка: последний подтверждённый 3-свечной фрактальный лой (L[k] < L[k-1], L[k] < L[k+1]) до фрактального хая FH;
между ними нет хая выше FH и лоя ниже FL. R = FH − FL. Медвежьи ножки — зеркально.
Отсчёт — с открытия недели после FH (FH подтверждён закрытием следующей недели — берём и эту неделю, откат обычно начинается в ней).
По 15m: running min после FH.
  react05 — первый отскок на 0.5R от текущего минимума (до слома FL); глубина отката = (FH − min) / R в этот момент.
  cont    — FH обновлён раньше, чем сломан FL; глубина = max откат до обновления.
  reach_d — дошла ли глубина до d; cont_after_d — при достижении d: FH раньше FL.
python retrace_w.py <dir_pkl_15m> <out_csv> [SYM ...]"""
import sys, numpy as np, pandas as pd
SRC, OUT = sys.argv[1:3]
SYMS = sys.argv[3:] or ['ETHUSDT', 'BTCUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'LTCUSDT', 'LINKUSDT']
import os
LEVELS = [round(x, 3) for x in np.arange(.1, .96, .05)] + [.382, .618, .705, .79, 1.0]
PER = os.environ.get('PER', 'W')                             # W — недели, D — дни
BARS = 672 if PER == 'W' else 96; HOR = 26 if PER == 'W' else 40
INF = 10**12
def first(mask, off=0):
    j = np.flatnonzero(mask); return off + j[0] if len(j) else INF
rows = []
for s in SYMS:
    raw = pd.read_pickle(f'{SRC}/{s}.pkl')[['o', 'h', 'l', 'c']]
    for side in ('bull', 'bear'):
        m = raw if side == 'bull' else pd.DataFrame({'o': -raw.o, 'h': -raw.l, 'l': -raw.h, 'c': -raw.c}, index=raw.index)
        h, l = m.h.values, m.l.values
        k = (m.index.normalize() - pd.to_timedelta(m.index.dayofweek, unit='D')) if PER == 'W' else m.index.normalize()
        b = pd.DataFrame({'h': h, 'l': l, 'p': np.arange(len(m))}, index=m.index).groupby(k).agg(h=('h', 'max'), l=('l', 'min'), i0=('p', 'first'), n=('p', 'size'))
        b = b[b.n >= .9 * BARS]
        H, L, I0 = b.h.values, b.l.values, b.i0.values.astype(int)
        fH = [j for j in range(1, len(b) - 1) if H[j] > H[j - 1] and H[j] > H[j + 1]]
        fL = [j for j in range(1, len(b) - 1) if L[j] < L[j - 1] and L[j] < L[j + 1]]
        for jb in fH:
            lows = [a for a in fL if a < jb and a + 1 <= jb]           # фрактальный лой подтверждён не позже недели FH
            if not lows: continue
            ja = lows[-1]
            FH, FL = H[jb], L[ja]
            if H[ja:jb].max() > FH or L[ja + 1:jb + 1].min() < FL: continue
            R = FH - FL
            if jb + 1 >= len(b): continue
            s0 = I0[jb + 1]; e0 = min(len(h), s0 + HOR * BARS)
            hh, ll = h[s0:e0], l[s0:e0]
            iFL = first(ll < FL); iFH = first(hh > FH)
            cm = np.minimum.accumulate(ll)
            r = dict(per=PER, sym=s, side=side, t=b.index[jb], R_pct=R / abs(FL), legs_weeks=jb - ja,
                     cont=iFH < iFL, broke=iFL < iFH, resolved=min(iFH, iFL) < INF)
            # глубина до исхода
            end = min(iFH, iFL, len(ll))
            r['depth_before_cont'] = (FH - cm[min(iFH, len(ll)) - 1]) / R if iFH < iFL and iFH > 0 else (0.0 if iFH == 0 else np.nan)
            # первая реакция 0.5R от текущего минимума
            bounce = (hh - cm) >= .5 * R
            ib = first(bounce)
            if ib < iFL and ib < INF:
                r['react05'] = True; r['depth_react05'] = (FH - cm[ib]) / R
                r['react05_weeks'] = ib / BARS
            else:
                r['react05'] = False
            # вероятности от уровней — только с момента подтверждения фрактала (открытие недели jb+2), без заглядывания вперёд
            if jb + 2 < len(b):
                c0 = I0[jb + 2] - s0                                          # смещение начала в окне
                known_min = cm[c0 - 1]; r['confirmed_ok'] = bool(known_min >= FL and hh[:c0].max() <= FH)
                r['depth_at_confirm'] = (FH - known_min) / R
                for d in LEVELS:
                    lvl = FH - d * R
                    if not r['confirmed_ok'] or known_min <= lvl:
                        r[f'reach_{d}'] = np.nan; continue                    # уровень уже пройден до подтверждения
                    iA, iBr = first(hh[c0:] > FH, c0), first(ll[c0:] < FL, c0)
                    id_ = first(ll[c0:] <= lvl, c0)
                    hit = id_ < iA and id_ < INF
                    r[f'reach_{d}'] = hit
                    if hit and d < 1:
                        if ll[id_] < FL: r[f'cont_after_{d}'] = False; continue  # уровень и слом лоя в одной свече — стоп
                        a2, z2 = first(hh[id_ + 1:] > FH), first(ll[id_ + 1:] < FL)
                        r[f'cont_after_{d}'] = (a2 < z2) if min(a2, z2) < INF else np.nan
            rows.append(r)
    print(s, len(rows), flush=True)
pd.DataFrame(rows).to_csv(OUT, index=False)
