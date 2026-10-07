"""Исполнение по BIAS: младший ТФ в сторону первого снятия.
BIAS периода P (D или W) = состояние закрытия прошлого периода относительно позапрошлого.
Бычий (принятие выше / отказ снизу) -> цель = хай прошлого периода; медвежьи считаются зеркально (цены с минусом).
Группы: with — BIAS бычий; none — внутри / обе сняты; against — BIAS медвежий (тот же лонг к хаю — проверка, что BIAS что-то даёт).
Триггер на TF: новый лой периода -> закрытие выше последнего подтверждённого фрактального хая (FR+FR), сформированного до этого лоя.
Вход на закрытии, стоп под лоем периода, цель = хай прошлого периода. Отмена: снят лой прошлого периода раньше сигнала.
Одна сделка за период. Нет исхода к концу периода -> выход по закрытию. Стоп и цель в одной свече -> стоп. Комиссия 0.1% на круг.
python exec1.py <dir_pkl> <out_csv> [SYM ...]"""
import sys, os, numpy as np, pandas as pd
SRC, OUT = sys.argv[1:3]
SYMS = sys.argv[3:] or ['ETHUSDT', 'BTCUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'LTCUSDT', 'LINKUSDT']
FR = int(os.environ.get('FR', 2)); COST = 0.001
CFG = [('D', '15min'), ('W', '1h')]
BULL, BEAR = {'принятие выше', 'отказ снизу'}, {'принятие ниже', 'отказ сверху'}
def state(h, l, c, PH, PL):
    if c > PH: return 'принятие выше'
    if c < PL: return 'принятие ниже'
    if h > PH and l < PL: return 'обе сняты'
    if h > PH: return 'отказ сверху'
    if l < PL: return 'отказ снизу'
    return 'внутри'
def pkey(idx, P): return (idx.normalize() - pd.to_timedelta(idx.dayofweek, unit='D')) if P == 'W' else idx.normalize()
rows = []
for s in SYMS:
    raw = pd.read_pickle(f'{SRC}/{s}.pkl')[['o', 'h', 'l', 'c']]
    for mirror in (False, True):
        m = raw if not mirror else pd.DataFrame({'o': -raw.o, 'h': -raw.l, 'l': -raw.h, 'c': -raw.c}, index=raw.index)
        for P, TF in CFG:
            t = m if TF == '15min' else m.resample(TF, label='left', closed='left').agg(o=('o', 'first'), h=('h', 'max'), l=('l', 'min'), c=('c', 'last')).dropna()
            k = pkey(t.index, P)
            b = t.groupby(k).agg(h=('h', 'max'), l=('l', 'min'), c=('c', 'last'), n=('c', 'size'))
            full = b.n.median()
            pos = np.r_[0, np.cumsum(b.n.values)]
            H, L, Cl = t.h.values, t.l.values, t.c.values; T = t.index
            hrs = T.hour.values
            for j in range(2, len(b)):
                if b.n.iloc[j] < .9 * full or b.n.iloc[j - 1] < .9 * full: continue
                st = state(b.h.iloc[j - 1], b.l.iloc[j - 1], b.c.iloc[j - 1], b.h.iloc[j - 2], b.l.iloc[j - 2])
                grp = 'with' if st in BULL else 'against' if st in BEAR else 'none'
                TGT, INV = b.h.iloc[j - 1], b.l.iloc[j - 1]
                s0, e0 = pos[j], pos[j + 1]
                lo, lo_i = np.inf, -1; asia_lo = np.inf; trade = None
                for i in range(s0, e0):
                    if H[i] >= TGT: break                                # цель BIAS достигнута до сигнала — BIAS исчерпан
                    if L[i] < INV: break                                 # снят противоположный край — сценарий отменён
                    if P == 'D' and hrs[i] < 6: asia_lo = min(asia_lo, L[i])
                    if L[i] < lo:
                        lo, lo_i = L[i], i; continue
                    # последний подтверждённый фрактальный хай перед лоем (не раньше 40 баров)
                    sh = None
                    for q in range(lo_i - 1, max(s0 - 8, lo_i - 40, FR) - 1, -1):
                        if q + FR > i - 0: continue
                        if all(H[q] > H[q - r] for r in range(1, FR + 1)) and all(H[q] >= H[q + r] for r in range(1, FR + 1)):
                            sh = H[q]; break
                    if sh is None or Cl[i] <= sh: continue
                    entry, stop = Cl[i], lo
                    risk = entry - stop
                    if risk <= 0 or TGT <= entry: break
                    rr = (TGT - entry) / risk
                    res = None
                    for q in range(i + 1, e0):
                        if L[q] <= stop: res = -1.0; break
                        if H[q] >= TGT: res = rr; break
                    if res is None: res = (Cl[e0 - 1] - entry) / risk
                    trade = dict(sym=s, P=P, mirror=mirror, group=grp, state=st, t=T[i], hour=int(hrs[i]), rr=rr,
                                 R=res - COST * abs(entry) / risk, win=res == rr, stopped=res == -1.0,
                                 risk_pct=risk / abs(entry), asia_swept=bool(P == 'D' and hrs[i] >= 6 and lo < asia_lo and lo_i >= s0 and hrs[lo_i] >= 6),
                                 bars_from_open=i - s0)
                    break
                if trade: rows.append(trade)
    print(s, len(rows), flush=True)
pd.DataFrame(rows).to_csv(OUT, index=False)
