"""Открытия как уровни: день (00:00 UTC), день (полночь Нью-Йорка), неделя, месяц. python opens.py <dir_pkl_15m> <out_csv> [SYM ...]
Для каждого периода (ATR = средний диапазон 14 прошлых периодов, k = 0.25 ATR):
  away     — цена ушла от открытия хотя бы на k;
  revisit  — после этого вернулась к открытию в том же периоде;
  bounce   — при первом возврате: снова ушла на k в исходную сторону раньше, чем на k за открытие (отбой) — иначе пробой;
  judas    — для бычьей свечи: насколько глубоко ниже открытия (в ATR) цена была до хая свечи; для медвежьей — выше открытия до лоя;
  ext_frac — когда (доля периода) сформировался лой бычьей / хай медвежьей свечи;
  side_at_x — по какую сторону открытия цена в моменты 1/4, 1/2, 3/4 периода, и закрытие;
  prev_open_hit — коснулась ли цена открытия прошлого периода."""
import sys, numpy as np, pandas as pd
SRC, OUT = sys.argv[1:3]
SYMS = sys.argv[3:] or ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'LTCUSDT', 'LINKUSDT']
INF = 10**12
def first(mask, off=0):
    j = np.flatnonzero(mask); return off + j[0] if len(j) else INF
rows = []
for s in SYMS:
    m = pd.read_pickle(f'{SRC}/{s}.pkl')[['o', 'h', 'l', 'c']]
    h, l, c, o = m.h.values, m.l.values, m.c.values, m.o.values
    ny = m.index.tz_localize('UTC').tz_convert('America/New_York')
    keys = {'D_UTC': m.index.normalize(), 'D_NY': pd.DatetimeIndex(ny.normalize().tz_localize(None)),
            'W': m.index.normalize() - pd.to_timedelta(m.index.dayofweek, unit='D'), 'M': m.index.to_period('M').to_timestamp()}
    for P, k in keys.items():
        g = pd.Series(np.arange(len(m)), index=m.index).groupby(k.values)
        st = g.first().values; n = g.size().values; lab = g.first().index
        full = np.median(n)
        rng = np.array([h[a:a + b].max() - l[a:a + b].min() for a, b in zip(st, n)])
        for j in range(15, len(st)):
            if n[j] < .9 * full: continue
            a, e = st[j], st[j] + n[j]; O = o[a]; A = rng[j - 14:j].mean(); K = .25 * A
            hh, ll, cc = h[a:e], l[a:e], c[a:e]
            C = cc[-1]; bull = C > O
            r = dict(sym=s, P=P, t=lab[j], bull=bull, ret_atr=(C - O) / A)
            iu, idn = first(hh >= O + K), first(ll <= O - K)
            i0 = min(iu, idn)
            r['away'] = i0 < INF
            if i0 < INF:
                up = iu < idn
                ir = first(ll[i0 + 1:] <= O, i0 + 1) if up else first(hh[i0 + 1:] >= O, i0 + 1)
                r['away_up'] = up; r['revisit'] = ir < INF
                if ir < INF:
                    if up: b1, b2 = first(hh[ir + 1:] >= O + K), first(ll[ir:] <= O - K)
                    else: b1, b2 = first(ll[ir + 1:] <= O - K), first(hh[ir:] >= O + K)
                    r['bounce'] = (b1 + 1 < b2) if min(b1 + 1, b2) < INF else np.nan
                    r['revisit_frac'] = ir / len(cc)
            if bull:
                ix = int(np.argmax(hh)); r['judas'] = max(0, O - ll[:ix + 1].min()) / A; r['ext_frac'] = int(np.argmin(ll)) / len(cc)
            else:
                ix = int(np.argmin(ll)); r['judas'] = max(0, hh[:ix + 1].max() - O) / A; r['ext_frac'] = int(np.argmax(hh)) / len(cc)
            for q, nm in ((.25, 'q1'), (.5, 'q2'), (.75, 'q3')):
                r[f'up_{nm}'] = cc[int(len(cc) * q) - 1] > O
            Op = o[st[j - 1]]
            r['prev_open_dist'] = abs(Op - O) / A
            r['prev_open_hit'] = bool((ll <= Op).any() and (hh >= Op).any())
            rows.append(r)
    print(s, len(rows), flush=True)
pd.DataFrame(rows).to_csv(OUT, index=False)
