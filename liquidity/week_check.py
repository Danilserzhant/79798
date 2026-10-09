"""Разбор одной недели по правилам начала недели (UTC). python week_check.py <pkl_15m> <понедельник YYYY-MM-DD>
Печатает уровни прошлой недели, дни недели и какие правила срабатывали в вс / пн / вт / ср (вероятности — из week_early, monday, tue_sweep)."""
import sys, numpy as np, pandas as pd
m = pd.read_pickle(sys.argv[1]); W0 = pd.Timestamp(sys.argv[2])
d = m.groupby(m.index.normalize()).agg(o=('o', 'first'), h=('h', 'max'), l=('l', 'min'), c=('c', 'last'))
d['atr'] = (d.h - d.l).rolling(14).mean().shift(1)
N = ['пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс']
f = lambda v: f'{v:,.2f}'.replace(',', ' ').replace('.', ',')
wk = lambda a: d.loc[a:a + pd.Timedelta(days=6)]
ppw, pw, w = wk(W0 - pd.Timedelta(days=14)), wk(W0 - pd.Timedelta(days=7)), wk(W0)
def state(cur, prev):
    H, L, C = cur.h.max(), cur.l.min(), cur.c.iloc[-1]; PH, PL = prev.h.max(), prev.l.min()
    return ('принятие выше' if C > PH else 'принятие ниже' if C < PL else 'обе сняты' if (H > PH and L < PL)
            else 'отказ сверху' if H > PH else 'отказ снизу' if L < PL else 'внутри')
PH, PL = pw.h.max(), pw.l.min(); O = w.o.iloc[0]; A = w.atr.iloc[0]; MID = (PH + PL) / 2
pst = state(pw, ppw)
print(f'Прошлая неделя {pw.index[0]:%d.%m}–{pw.index[-1]:%d.%m}: PWH {f(PH)} ({N[int(np.argmax(pw.h.values))]}), PWL {f(PL)} ({N[int(np.argmin(pw.l.values))]}), '
      f'середина {f(MID)}, закрытие {f(pw.c.iloc[-1])} → «{pst}», {"бычья" if pw.c.iloc[-1] > pw.o.iloc[0] else "медвежья"}')
pos = (O - PL) / (PH - PL)
print(f'Неделя {w.index[0]:%d.%m}–{w.index[-1]:%d.%m}: открытие {f(O)} (положение в прошлой неделе {pos:.2f}), дневной ATR {f(A)}\n')
for i, (t, r) in enumerate(w.iterrows()):
    tg = (['СНЯЛ PWL'] if r.l < PL else []) + (['СНЯЛ PWH'] if r.h > PH else []) + ['выше открытия' if r.c > O else 'ниже открытия']
    print(f'  {N[i]} {t:%d.%m}  h {f(r.h):>9}  l {f(r.l):>9}  c {f(r.c):>9}  {(r.h - r.l) / A:4.2f} ATR | ' + ', '.join(tg))
mon, tue, wed = w.iloc[0], w.iloc[1], w.iloc[2]
sig = []
# воскресенье
if pst == 'обе сняты': sig.append(('вс', 'прошлая неделя «обе сняты»', 'остаток недели ВНИЗ ~70% (контроль 46%)', 'down'))
if pst == 'внутри': sig.append(('вс', 'прошлая неделя «внутри»', 'остаток недели вверх 57% (52%)', 'up'))
if pst == 'отказ снизу': sig.append(('вс', 'прошлая неделя «отказ снизу»', 'остаток недели вверх 47% (53%) — лёгкий медвежий перекос', 'down'))
if pos > 2 / 3: sig.append(('вс', 'открытие в верхней трети прошлой недели', '+1 ATR раньше −1 ATR 45% (51%)', 'down'))
if pos < 1 / 3: sig.append(('вс', 'открытие в нижней трети прошлой недели', 'первый пробой края пн вверх 60% (54%)', 'up'))
# понедельник
if mon.l < PL and mon.h <= PH: sig.append(('пн', 'пн снял PWL', 'остаток недели вверх 59% (47%)', 'up'))
if mon.h > PH and mon.l >= PL: sig.append(('пн', 'пн снял PWH', '+1 ATR раньше −1 ATR 44% (51%)', 'down'))
if (mon.h - mon.l) / A < .6: sig.append(('пн', 'пн маленький (< 0,6 ATR)', 'остаток недели вниз 56%', 'down'))
# вторник
tPH, tPL = max(mon.h, tue.h) > PH, min(mon.l, tue.l) < PL
if tue.h <= mon.h and tue.l >= mon.l: sig.append(('вт', 'вт — инсайд пн', 'первый пробой края пн–вт вверх 57% (49%)', 'up'))
if tue.l < mon.l: sig.append(('вт', 'вт пробил лой пн', 'первый пробой края пн–вт вниз 71% (64%)', 'down'))
if tPH and not tPL and tue.c < O: sig.append(('вт', 'к вт снят PWH, цена ниже открытия', 'первый пробой вниз 88% (77%), −1 ATR раньше 62%', 'down'))
if mon.l >= PL and mon.h <= PH and tue.l < PL and tue.h <= PH: sig.append(('вт', 'пн внутри, вт снял PWL', 'НЕ разворот: неделя бычья 25% (33%)', 'down'))
if mon.l >= PL and mon.h <= PH and tue.h > PH and tue.l >= PL and tue.c < PH: sig.append(('вт', 'пн внутри, вт снял PWH и закрылся ниже', 'хай вт = хай недели 43% (31%)', 'down'))
# среда
if w.h.iloc[1:3].max() < mon.h and wed.c < O: sig.append(('ср', 'хай пн не обновлён до ср, цена ниже открытия', 'неделя медвежья 80%, хай пн = хай недели 75%', 'down'))
if w.l.iloc[1:3].min() > mon.l and wed.c > O: sig.append(('ср', 'лой пн не обновлён до ср, цена выше открытия', 'неделя бычья 79% (контроль 77%)', 'up'))
if tPL and not tPH and wed.c > PL and wed.l >= min(mon.l, tue.l): sig.append(('ср', 'PWL снят в пн/вт, ср выше PWL, лой пн–вт не обновлён', 'лой пн–вт = лой недели 76%, но рост слабый (PWH 24%)', 'up'))
if tPL and not tPH and wed.c > PL and wed.l < min(mon.l, tue.l): sig.append(('ср', 'PWL снят в пн/вт, ср обновила лой пн–вт, но закрылась выше PWL', 'от ср до конца недели вверх 65% (57%), n=60 — мало', 'up'))
if mon.l >= PL and mon.h <= PH and tue.l < PL and tue.h <= PH and tue.c > PL: sig.append(('вт', 'пн внутри, вт снял PWL и закрылся обратно выше', '+1 ATR раньше −1 ATR 38% (53%), PWH снимают 13% (30%)', 'down'))
if tPH and not tPL and wed.c < PH and wed.h <= max(mon.h, tue.h): sig.append(('ср', 'PWH снят в пн/вт, ср ниже PWH, хай пн–вт не обновлён', 'хай пн–вт = хай недели 76%, вниз до конца недели 57%', 'down'))
print('\nСигналы по ходу недели:')
for day, nm, exp, dr in sig or [('—', 'нет сигналов', '', '')]:
    print(f'  {day}: {nm} → {exp}')
WC = w.c.iloc[-1]; bull = WC > O
print(f'\nИтог: хай недели {f(w.h.max())} ({N[int(np.argmax(w.h.values))]}), лой {f(w.l.min())} ({N[int(np.argmin(w.l.values))]}), закрытие {f(WC)} → '
      f'{"бычья" if bull else "медвежья"} ({100 * (WC / O - 1):+.1f}%), состояние «{state(w, pw)}»')
print(f'От закрытия пн: {100 * (WC / mon.c - 1):+.1f}%, от закрытия вт: {100 * (WC / tue.c - 1):+.1f}%, от закрытия ср: {100 * (WC / wed.c - 1):+.1f}%')
ups = sum(s[3] == 'up' for s in sig); dns = sum(s[3] == 'down' for s in sig)
print(f'Сигналов вверх {ups}, вниз {dns} → неделя {"совпала" if (ups > dns) == bull and ups != dns else "не совпала" if ups != dns else "без перевеса"} с большинством сигналов')
