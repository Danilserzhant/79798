"""Сборка методички «Нарратив, BIAS и контекст» в HTML -> PDF.
python build_book.py <results_dir> <synth_res_dir1,dir2,dir3> <eth_pkl> <synth_eth_pkl> <out.html>"""
import sys, numpy as np, pandas as pd
from svg import candles, grouped_bars, curves, svg, text, box, arrow, DEFS, C
RES, SYN, ETH, SETH, OUT = sys.argv[1], sys.argv[2].split(','), sys.argv[3], sys.argv[4], sys.argv[5]

def rd(d, f):
    x = pd.read_csv(f'{d}/{f}.csv')
    for c in x.columns:
        if x[c].dtype == object and set(x[c].dropna().unique()) <= {'True', 'False'}: x[c] = x[c] == 'True'
    return x
def both(f): return rd(RES, f), [rd(d, f) for d in SYN]
def pc(v): return f'{100 * v:.0f}%'
def RC(fn, real, syn):
    """(факт, контроль, n)"""
    v, n = fn(real); s = np.nanmean([fn(x)[0] for x in syn]); return v, s, n
ETHf = lambda d: d[d.sym == 'ETHUSDT']

# ---------------- данные ----------------
A, As = both('A_prev_range'); B, Bs = both('B_pools'); Cc, Cs = both('C_pool_to_pool'); Z, Zs = both('Z_zones'); PR, PRs = both('P_premium')
ST, STs = both('bias_states')
ORDER = ['принятие выше', 'отказ снизу', 'внутри', 'обе сняты', 'отказ сверху', 'принятие ниже']
def state_tab(d, P):
    d = d[d.P == P]
    g = d.groupby('state').agg(n=('up', 'size'), nH=('nH', 'mean'), nL=('nL', 'mean'), firstH=('firstH', 'mean'), up=('up', 'mean'))
    g['share'] = g.n / g.n.sum(); return g.reindex(ORDER)
def state_rc(P, f=lambda d: d):
    r = state_tab(f(ST), P); s = sum(state_tab(f(x), P) for x in STs) / len(STs); return r, s

# A-метрики
def a_metrics(d, P):
    a = d[d.P == P]; up, dn = a[a.opn == 'верх. половина'], a[a.opn == 'нижн. половина']
    b = a[a.tH & a.tL]; one = a[(a.tH ^ a.tL) & a['after'].isin(['opp', 'cont'])]
    acc = np.where(one.tH, one.closeAbovePH, one.closeBelowPL)
    return {'up_H': (up.tH.mean(), len(up)), 'dn_L': (dn.tL.mean(), len(dn)), 'both': ((a.tH & a.tL).mean(), len(a)),
            'none': ((~a.tH & ~a.tL).mean(), len(a)),
            'both_second': (np.where(b['first'] == 'H', ~b.closeUpper, b.closeUpper).mean(), len(b)),
            'rej_mid': ((one[~acc].after_mid == 'opp').mean(), (~acc).sum()), 'rej_opp': ((one[~acc]['after'] == 'opp').mean(), (~acc).sum()),
            'acc_mid': ((one[acc].after_mid == 'opp').mean(), acc.sum()), 'acc_opp': ((one[acc]['after'] == 'opp').mean(), acc.sum())}
def a_rc(P, f=lambda d: d):
    r = a_metrics(f(A), P); s = [a_metrics(f(x), P) for x in As]
    return {k: (r[k][0], np.mean([q[k][0] for q in s]), r[k][1]) for k in r}
AW, AM, AWe = a_rc('W'), a_rc('M'), a_rc('W', ETHf)

# B: ближний пул и кривая
def near(d, P):
    b = d[d.P == P].dropna(subset=['up_first'])
    return (np.where(b.du < b.dd, b.up_first, 1 - b.up_first).mean(), len(b))
NEAR_D = RC(lambda d: near(d, 'D'), B, Bs); NEAR_W = RC(lambda d: near(d, 'W'), B, Bs)
edges = np.linspace(0, 1, 11); mids = (edges[1:] + edges[:-1]) / 2
def bucket_curve(d, P='D'):
    b = d[d.P == P].dropna(subset=['up_first']); k = np.clip(np.digitize(b.p_rw, edges) - 1, 0, 9)
    return [b.up_first[k == i].mean() for i in range(10)]
CUR_R = bucket_curve(B); CUR_S = np.nanmean([bucket_curve(x) for x in Bs], axis=0)
# EQ
def eq_dev(d, P, col, side):
    b = d[(d.P == P)].dropna(subset=['up_first']); g = b[b[col] == 1]
    hit = g.up_first if side else 1 - g.up_first; exp = g.p_rw if side else 1 - g.p_rw
    g0 = b[b[col] == 0]; hit0 = g0.up_first if side else 1 - g0.up_first; exp0 = g0.p_rw if side else 1 - g0.p_rw
    return hit.mean() - exp.mean(), hit0.mean() - exp0.mean(), len(g)
EQ = {(P, nm): eq_dev(B, P, col, sd) for P in ('W', 'D') for nm, col, sd in (('EQH', 'eq_up', 1), ('EQL', 'eq_dn', 0))}
# C: пул->пул
def c_m(d, P, acc):
    c = d[(d.P == P) & (d.accept == acc)].dropna(subset=['opp_first']); return (c.opp_first.mean(), len(c))
POOL = {(P, acc): RC(lambda d, P=P, acc=acc: c_m(d, P, acc), Cc, Cs) for P in ('W', 'D') for acc in (False, True)}
# зоны
def z_m(d, P, typ, col, side=None):
    z = d[(d.P == P) & (d.typ == typ)]
    if side: z = z[z.side == side]
    z = z.dropna(subset=[col]); return (z[col].mean(), len(z))
ZT = {(P, typ, col, sd): RC(lambda d, P=P, typ=typ, col=col, sd=sd: z_m(d, P, typ, col, sd), Z, Zs)
      for P in ('M', 'W', 'D') for typ in ('FVG', 'OB') for col in ('rr1', 'rr2', 'inv_down1') for sd in (None, 'bear')}
# премиум
PB = [(-9, 0, 'ниже\nдиапазона'), (0, .25, 'дискаунт\n0–25%'), (.25, .5, 'дискаунт\n25–50%'), (.5, .75, 'премиум\n50–75%'), (.75, 1, 'премиум\n75–100%'), (1, 9, 'выше\nдиапазона')]
def p_m(d, P, a, b): x = d[(d.P == P) & (d.pos >= a) & (d.pos < b)].dropna(subset=['atr_up']); return (x.atr_up.mean(), len(x))
PREM = {P: [RC(lambda d, P=P, a=a, b=b: p_m(d, P, a, b), PR, PRs) for a, b, _ in PB] for P in ('W', 'D')}
# совмещение M+W
def align(d):
    d = d[(d.P == 'W') & d.mstate.notna()].copy()
    f = lambda x: 'бычье' if x in ('принятие выше', 'отказ снизу') else 'медвежье' if x in ('принятие ниже', 'отказ сверху') else 'нейтральное'
    d['M'] = d.mstate.map(f); d['W'] = d.state.map(f)
    return d.groupby(['M', 'W']).agg(n=('up', 'size'), firstH=('firstH', 'mean'), up=('up', 'mean'))
AL_R = align(ST); AL_S = sum(align(x) for x in STs) / len(STs)

# ---------------- ETH: текущая ситуация ----------------
m = pd.read_pickle(ETH)[['o', 'h', 'l', 'c']]
def agg(P):
    k = (m.index.normalize() - pd.to_timedelta(m.index.dayofweek, unit='D')) if P == 'W' else m.index.to_period('M').to_timestamp() if P == 'M' else m.index.normalize()
    return m.groupby(k).agg(o=('o', 'first'), h=('h', 'max'), l=('l', 'min'), c=('c', 'last'))
EW, ED, EM = agg('W'), agg('D'), agg('M')
LAST_T = m.index[-1] + pd.Timedelta('15min'); PRICE = m.c.iloc[-1]
def state_of(cur, prev):
    if cur.c > prev.h: return 'принятие выше'
    if cur.c < prev.l: return 'принятие ниже'
    if cur.h > prev.h and cur.l < prev.l: return 'обе сняты'
    if cur.h > prev.h: return 'отказ сверху'
    if cur.l < prev.l: return 'отказ снизу'
    return 'внутри'
M_SEP, M_AUG = EM.loc['2026-09-01'], EM.loc['2026-08-01']; W_IB, W_MO = EW.loc['2026-09-28'], EW.loc['2026-09-21']; W_NOW = EW.loc['2026-10-05']
D_Y, D_YY, D_T = ED.loc['2026-10-06'], ED.loc['2026-10-05'], ED.loc['2026-10-07']
ST_M, ST_W, ST_D = state_of(M_SEP, M_AUG), state_of(W_IB, W_MO), state_of(D_Y, D_YY)
rM, sM = state_rc('M'); rW, sW = state_rc('W'); rD, sD = state_rc('D'); rWe, sWe = state_rc('W', ETHf)
f0 = lambda v: f'{v:,.2f}'.replace(',', ' ').replace('.', ',')

# ---------------- рисунки ----------------
def fig_control():
    s = pd.read_pickle(SETH)
    r = m.c.resample('W-MON').last().dropna(); q = s.c.resample('W-MON').last().dropna()
    n = min(len(r), len(q)); r, q = np.log(r.values[:n]), np.log(q.values[:n])
    w, h, pl, pr, pt, pb = 760, 250, 46, 14, 30, 26
    lo, hi = min(r.min(), q.min()), max(r.max(), q.max())
    X = lambda i: pl + i / (n - 1) * (w - pl - pr); Y = lambda v: pt + (hi - v) / (hi - lo) * (h - pt - pb)
    o = [f'<rect width="{w}" height="{h}" fill="#fff"/>', text(pl, 16, 'ETH, недельные закрытия (лог-шкала): реальный график и одна из синтетик', 12, C['ink2'], weight=700)]
    for p in (100, 300, 1000, 3000):
        if lo <= np.log(p) <= hi: o.append(f'<line x1="{pl}" x2="{w-pr}" y1="{Y(np.log(p)):.1f}" y2="{Y(np.log(p)):.1f}" stroke="{C["grid"]}"/>' + text(pl - 6, Y(np.log(p)) + 4, p, 9.5, C['muted'], 'end'))
    for arr, col, wd in ((q, 'ctrl', 1.6), (r, 'real', 1.8)):
        o.append(f'<polyline fill="none" stroke="{C[col]}" stroke-width="{wd}" points="' + ' '.join(f'{X(i):.1f},{Y(v):.1f}' for i, v in enumerate(arr)) + '"/>')
    o.append(f'<rect x="{pl+10}" y="34" width="14" height="3" fill="{C["real"]}"/>' + text(pl + 30, 39, 'реальный ETH', 10.5, C['ink2']))
    o.append(f'<rect x="{pl+10}" y="50" width="14" height="3" fill="{C["ctrl"]}"/>' + text(pl + 30, 55, 'контроль: те же дни в случайном порядке', 10.5, C['ink2']))
    for i in range(0, n, 52): o.append(text(X(i), h - 8, 2020 + i // 52, 9.5, C['muted'], 'middle'))
    return svg(w, h, ''.join(o))

def fig_pyramid():
    w, h = 760, 330; o = [DEFS, f'<rect width="{w}" height="{h}" fill="#fff"/>']
    rows = [('МЕСЯЦ', 'карта: PMH/PML, крупные свинги', '#e7edf6'), ('НЕДЕЛЯ', 'нарратив и BIAS недели', '#dfe8f5'),
            ('ДЕНЬ', 'BIAS дня, сценарий, PDH/PDL', '#d6e2f3'), ('H4 / H1', 'зоны, где искать вход', '#f3ead9'), ('M15 / M5', 'триггер и стоп', '#f1e2c7')]
    for i, (t, s, col) in enumerate(rows):
        bw = 300 + i * 80; x = (w - 260 - bw) / 2 + 10; y = 16 + i * 60
        o.append(box(x, y, bw, 48, t, s, fill=col, stroke='#c9d3df'))
    o.append(f'<line x1="{w-230}" y1="20" x2="{w-230}" y2="186" stroke="{C["real"]}" stroke-width="3"/>')
    o.append(text(w - 218, 80, 'КОНТЕКСТ', 13, C['real'], weight=700) + text(w - 218, 98, 'эта методичка:', 10.5, C['ink2']) + text(w - 218, 112, 'куда, что первым,', 10.5, C['ink2']) + text(w - 218, 126, 'где отмена сценария', 10.5, C['ink2']))
    o.append(f'<line x1="{w-230}" y1="200" x2="{w-230}" y2="306" stroke="{C["zone"]}" stroke-width="3"/>')
    o.append(text(w - 218, 240, 'ИСПОЛНЕНИЕ', 13, C['zone'], weight=700) + text(w - 218, 258, 'следующая методичка:', 10.5, C['ink2']) + text(w - 218, 272, 'вход, стоп, сопровождение', 10.5, C['ink2']))
    return svg(w, h, ''.join(o))

def fig_states():
    w, h = 760, 400; o = [f'<rect width="{w}" height="{h}" fill="#fff"/>']
    pw, ph = 245, 190
    spec = {'принятие выше': (0.55, 1.35, 0.5, 1.25), 'отказ снизу': (0.45, 0.9, -0.3, 0.7), 'внутри': (0.6, 0.85, 0.15, 0.4),
            'обе сняты': (0.5, 1.25, -0.25, 0.55), 'отказ сверху': (0.55, 1.3, 0.1, 0.3), 'принятие ниже': (0.45, 0.5, -0.35, -0.25)}
    for i, st in enumerate(ORDER):
        cx, cy = (i % 3) * (pw + 12) + 4, (i // 3) * (ph + 10) + 4
        o.append(f'<rect x="{cx}" y="{cy}" width="{pw}" height="{ph}" rx="8" fill="{C["soft"]}" stroke="{C["line"]}"/>')
        o.append(text(cx + 12, cy + 20, st.upper(), 11.5, C['ink'], weight=700))
        Y = lambda v: cy + 132 - v * 78
        o.append(f'<rect x="{cx+18}" y="{Y(1):.1f}" width="48" height="{Y(0)-Y(1):.1f}" fill="#e3e8ee" stroke="#c3ccd6"/>')
        o.append(f'<line x1="{cx+18}" x2="{cx+118}" y1="{Y(1):.1f}" y2="{Y(1):.1f}" stroke="{C["muted"]}" stroke-dasharray="3 3"/>')
        o.append(f'<line x1="{cx+18}" x2="{cx+118}" y1="{Y(0):.1f}" y2="{Y(0):.1f}" stroke="{C["muted"]}" stroke-dasharray="3 3"/>')
        op, hh, ll, cl = spec[st]
        col = C['up'] if cl >= op else C['down']
        o.append(f'<line x1="{cx+92}" x2="{cx+92}" y1="{Y(hh):.1f}" y2="{Y(ll):.1f}" stroke="{col}" stroke-width="1.6"/>')
        y1, y2 = sorted((Y(op), Y(cl)))
        o.append(f'<rect x="{cx+82}" y="{y1:.1f}" width="20" height="{max(2,y2-y1):.1f}" fill="{col}"/>')
        fh = rW.loc[st, 'firstH']; fs = sW.loc[st, 'firstH']; up = rW.loc[st, 'up']
        big = fh if fh >= .5 else 1 - fh; side = 'ХАЙ' if fh >= .5 else 'ЛОЙ'
        o.append(text(cx + 182, cy + 56, f'{big*100:.0f}%', 22, C['up'] if fh >= .5 else C['down'], 'middle', 700))
        o.append(text(cx + 182, cy + 72, f'первым снимут {side}', 9.5, C['ink2'], 'middle'))
        o.append(text(cx + 182, cy + 84, 'этой свечи', 9.5, C['ink2'], 'middle'))
        o.append(text(cx + 12, cy + ph - 26, f'контроль: {(fs if fh >= .5 else 1-fs)*100:.0f}%  ·  закрытие выше: {up*100:.0f}%', 9.5, C['muted']))
        o.append(text(cx + 12, cy + ph - 12, f'доля недель {rW.loc[st,"share"]*100:.0f}%  ·  n={int(rW.loc[st,"n"])}', 9.5, C['muted']))
    return svg(w, h, ''.join(o))

def fig_first_vs_close():
    groups = [s.replace(' ', '\n', 1) for s in ORDER]
    return grouped_bars(groups, [('хай этой недели снят первым', 'real', [100 * rW.loc[s, 'firstH'] for s in ORDER]),
                                 ('следующая неделя закрылась выше', 'zone', [100 * rW.loc[s, 'up'] for s in ORDER])],
                        h=290, ref=(50, '50% — монетка'), title='Неделя (9 монет): BIAS говорит, что снимут первым, а не как закроется')

def fig_scen():
    w, h = 760, 300; o = [DEFS, f'<rect width="{w}" height="{h}" fill="#fff"/>']
    o.append(box(250, 10, 260, 46, 'Снят хай/лой прошлого периода', 'смотрим закрытие периода'))
    o.append(arrow(330, 56, 160, 100) + arrow(430, 56, 600, 100))
    o.append(box(30, 102, 260, 52, 'Закрытие ЗА уровнем', 'принятие', fill='#e2f1ec', stroke='#b7dccd'))
    o.append(box(470, 102, 260, 52, 'Закрытие ОБРАТНО внутрь', 'отказ', fill='#f6e6e4', stroke='#e6c1bc'))
    o.append(box(30, 186, 260, 96, f'{(1-AW["acc_opp"][0])*100:.0f}% — новый экстремум', f'раньше противоположной стороны\nсередина раньше: только {AW["acc_mid"][0]*100:.0f}%\nконтроль: {(1-AW["acc_opp"][1])*100:.0f}%', fill='#fff'))
    o.append(box(470, 186, 260, 96, f'{AW["rej_mid"][0]*100:.0f}% — сначала середина', f'прошлого диапазона\nпротивоположная сторона: {AW["rej_opp"][0]*100:.0f}%\nконтроль: {AW["rej_mid"][1]*100:.0f}% / {AW["rej_opp"][1]*100:.0f}%', fill='#fff'))
    o.append(arrow(160, 154, 160, 184) + arrow(600, 154, 600, 184))
    return svg(w, h, ''.join(o))

def fig_curve():
    return curves(list(mids), [('реальный рынок', 'real', CUR_R, 2.4), ('контроль', 'ctrl', list(CUR_S), 2)],
                  title='Какой пул снимут первым: факт против контроля (дневные свинги, 9 монет)',
                  xlabel='ожидание по одному расстоянию: насколько верхний пул ближе нижнего')

def fig_zones():
    keys = [('W', 'FVG'), ('W', 'OB'), ('M', 'FVG'), ('M', 'OB'), ('D', 'FVG'), ('D', 'OB')]
    g = [f'{"Неделя" if P=="W" else "Месяц" if P=="M" else "День"}\n{t}' for P, t in keys]
    return grouped_bars(g, [('факт: цель 1:1 раньше стопа', 'real', [100 * ZT[(P, t, 'rr1', None)][0] for P, t in keys]),
                            ('контроль', 'ctrl', [100 * ZT[(P, t, 'rr1', None)][1] for P, t in keys])],
                        ymax=75, h=270, ref=(50, 'безубыток 1:1'), title='Лимитка от края зоны, стоп за зоной, цель = размер зоны')

def fig_prem():
    g = [x[2] for x in PB]
    return grouped_bars(g, [('факт: +1 ATR раньше −1 ATR', 'real', [100 * v[0] for v in PREM['W']]), ('контроль', 'ctrl', [100 * v[1] for v in PREM['W']])],
                        ymax=75, h=270, ref=(50, '50%'), title='Неделя: положение открытия в dealing range и следующее движение (9 монет)')

def fig_flow():
    steps = [('1. Месяц', 'состояние закрытия прошлого месяца · PMH / PML · середина'), ('2. Неделя', 'состояние закрытия прошлой недели → какую сторону снимут первой'),
             ('3. Карта пулов', 'PWH/PWL, старые свинги W и D · ближний пул = вероятная цель'), ('4. Отмена', 'закрытие за уровнем против сценария = сценарий снят'),
             ('5. День', 'состояние вчерашнего дня → сторона, которую снимут первой сегодня'), ('6. Передача на H4/M15', 'только в сторону первого снятия · цель — пул · стоп — за манипуляцией')]
    w, bh, gap = 760, 50, 22; h = len(steps) * (bh + gap); o = [DEFS, f'<rect width="{w}" height="{h}" fill="#fff"/>']
    for i, (t, sub) in enumerate(steps):
        y = 6 + i * (bh + gap)
        o.append(box(110, y, 540, bh, t, sub, fill=C['soft'] if i < 4 else '#f3ead9'))
        if i < len(steps) - 1: o.append(arrow(380, y + bh, 380, y + bh + gap - 2))
        tag = 'воскресенье' if i < 4 else 'каждый день' if i == 4 else 'сессия'
        o.append(text(100, y + bh / 2 + 4, tag, 10, C['muted'], 'end', 600))
    return svg(w, h, ''.join(o))

def eth_week_chart():
    b = EW.loc['2026-05-04':]
    bars = [(t.strftime('%d.%m'), r.o, r.h, r.l, r.c) for t, r in b.iterrows()]
    lv = [(M_SEP.h, 'PMH сент. / хай матери', 'ink', False), (W_MO.l, 'лой матери 21.09', 'ink', False), (W_IB.h, 'хай IB', 'muted', True),
          (W_IB.l, 'лой IB', 'muted', True), (M_SEP.l, 'PML сент.', 'down', True), (M_AUG.h, 'хай авг.', 'up', True), (PRICE, 'цена', 'real', True)]
    return candles(bars, lv, title=f'ETHUSDT Perp · неделя · данные до {LAST_T:%d.%m %H:%M} UTC')
def eth_day_chart():
    b = ED.loc['2026-09-08':]
    bars = [(t.strftime('%d.%m'), r.o, r.h, r.l, r.c) for t, r in b.iterrows()]
    lv = [(W_MO.h, 'хай матери', 'ink', False), (W_MO.l, 'лой матери', 'ink', False), (W_IB.l, 'лой IB', 'muted', True),
          (D_Y.h, 'PDH 06.10', 'up', True), (D_Y.l, 'PDL 06.10', 'down', True), (W_MO.l + (W_MO.h - W_MO.l) / 2, 'середина матери', 'zone', True)]
    return candles(bars, lv, title='ETHUSDT Perp · день', h=320)

# ---------------- таблицы ----------------
def tr(cells, head=False):
    t = 'th' if head else 'td'; return '<tr>' + ''.join(f'<{t}>{c}</{t}>' for c in cells) + '</tr>'
def state_table(r, s, cap):
    rows = [tr(['Состояние закрытия', 'Доля', 'Хай свечи снят', 'Лой свечи снят', '<b>Хай первым</b>', 'Закрытие выше', 'n'], True)]
    for st in ORDER:
        x, y = r.loc[st], s.loc[st]
        rows.append(tr([st, pc(x.share), f'{pc(x.nH)} <span class=c>({pc(y.nH)})</span>', f'{pc(x.nL)} <span class=c>({pc(y.nL)})</span>',
                        f'<b>{pc(x.firstH)}</b> <span class=c>({pc(y.firstH)})</span>', f'{pc(x.up)} <span class=c>({pc(y.up)})</span>', int(x.n)]))
    return f'<table><caption>{cap}</caption>{"".join(rows)}</table>'
def rc_cell(t): return f'<b>{pc(t[0])}</b> <span class=c>({pc(t[1])})</span>'

def align_table():
    rows = [tr(['Месяц', 'Неделя', 'Хай недели первым', 'Закрытие выше', 'n'], True)]
    for (Mm, Ww), x in AL_R.iterrows():
        y = AL_S.loc[(Mm, Ww)]
        rows.append(tr([Mm, Ww, f'<b>{pc(x.firstH)}</b> <span class=c>({pc(y.firstH)})</span>', f'{pc(x.up)} <span class=c>({pc(y.up)})</span>', int(x.n)]))
    return f'<table class="tight"><caption>Совмещение месяца и недели (9 монет). Бычье = принятие выше или отказ снизу; медвежье — зеркально.</caption>{"".join(rows)}</table>'

def zones_table():
    rows = [tr(['Зона', 'Цель 1:1 раньше стопа', 'Цель 1:2', 'Инверсия → продолжение', 'n касаний'], True)]
    for P, nm in (('M', 'Месяц'), ('W', 'Неделя'), ('D', 'День')):
        for t in ('FVG', 'OB'):
            a, b, c = ZT[(P, t, 'rr1', None)], ZT[(P, t, 'rr2', None)], ZT[(P, t, 'inv_down1', None)]
            rows.append(tr([f'{nm} {t}', rc_cell(a), rc_cell(b), rc_cell(c), a[2]]))
    return f'<table><caption>Зоны HTF, бычьи и медвежьи вместе (9 монет). Безубыток: 1:1 — 50%, 1:2 — 33%.</caption>{"".join(rows)}</table>'

wob = ZT[('W', 'OB', 'rr1', 'bear')]; wob2 = ZT[('W', 'OB', 'rr2', 'bear')]
D_REJ = (rD.loc['отказ снизу', 'nL'], sD.loc['отказ снизу', 'nL']); D_REJ_H = (rD.loc['отказ снизу', 'firstH'], sD.loc['отказ снизу', 'firstH'])

# ---------------- текст ----------------
H = []
H.append(f'''
<section class="cover">
  <div class="kicker">Top-down ICT · проверено на данных</div>
  <h1>Нарратив, BIAS<br>и контекст</h1>
  <p class="lead">Методичка по работе со старшими таймфреймами: что месяц, неделя и день на самом деле говорят о цене, какие вероятности можно закладывать в план и чего от контекста ждать нельзя.</p>
  <div class="cover-fig">{fig_pyramid()}</div>
  <table class="meta">
   <tr><td>Данные</td><td>Binance USDT-M Perp, 15m: ETH, BTC, SOL, BNB, XRP, ADA, DOGE, LTC, LINK</td></tr>
   <tr><td>Период</td><td>январь 2020 — октябрь 2026, время UTC, неделя с понедельника</td></tr>
   <tr><td>Проверка</td><td>каждая цифра сравнена с контролем — тем же рынком без реальных уровней</td></tr>
   <tr><td>Версия</td><td>{pd.Timestamp.today():%d.%m.%Y}</td></tr>
  </table>
</section>

<section class="toc">
  <h2>Содержание</h2>
  <ol>
   <li>Как читать эту методичку: шанс и преимущество</li>
   <li>Роли таймфреймов</li>
   <li>Нарратив: карта ликвидности</li>
   <li>BIAS: состояние закрытия свечи</li>
   <li>Совмещение таймфреймов</li>
   <li>Сценарии после снятия уровня</li>
   <li>Зоны контекста: премиум/дискаунт, FVG, OB</li>
   <li>Алгоритм подготовки: неделя и день</li>
   <li>Передача на младшие таймфреймы</li>
   <li>Разбор: ETH, октябрь 2026</li>
   <li>Мифы и факты</li>
   <li>Ограничения, журнал, что дальше</li>
   <li>Приложение: методика</li>
  </ol>
  <div class="note"><b>Главное в одном абзаце.</b> Старшие таймфреймы не говорят, куда закроется следующая свеча: это около 50% в любом состоянии. Зато они хорошо говорят, <b>какую сторону цена снимет первой</b> (до {pc(rW.loc["принятие выше","firstH"])}) и <b>где сценарий отменяется</b>. Поэтому контекст — это направление первого движения, цель и отмена. Сама точка входа и есть преимущество — её ищем на младших таймфреймах.</div>
</section>

<section>
  <h2><span>1</span>Как читать эту методичку: шанс и преимущество</h2>
  <p>В методичке два вида цифр, и их важно не путать.</p>
  <div class="two">
   <div class="card"><h4>Шанс</h4><p>Как часто событие происходит. Например, «неделя открылась в верхней половине прошлой, PWH снимут в {pc(AW["up_H"][0])} случаев». Это честная вероятность, и её можно закладывать в сценарий.</p></div>
   <div class="card"><h4>Преимущество</h4><p>Насколько шанс <b>лучше контроля</b>, то есть того, что дало бы движение цены без всякой ликвидности. В контроле PWH снимают в {pc(AW["up_H"][1])}. Значит, у правила высокий шанс, но преимущества нет: уровень просто близко.</p></div>
  </div>
  <h3>Что такое контроль</h3>
  <p>Берём реальные 15-минутные свечи, режем их на дни и складываем дни в случайном порядке. Волатильность, внутридневная форма и общий рост рынка остаются теми же. Пропадает только «память» рынка: уровни, к которым цена возвращается, ликвидность, структура. На контроле считаем то же самое, что и на реальном графике, и берём среднее по трём таким перемешиваниям.</p>
  <figure>{fig_control()}<figcaption>Рис. 1. Реальный ETH и контроль. Похожий по характеру график, но без реальных уровней.</figcaption></figure>
  <div class="rule"><b>Правило чтения.</b> В таблицах рядом с фактом в скобках серым стоит контроль. Если цифры близки, это геометрия: свойство любого графика. Если факт заметно лучше, это свойство рынка, то есть преимущество.</div>
  <h3>Почему высокий шанс без преимущества не даёт денег</h3>
  <p>Чем ближе цель, тем чаще её достигают, но тем меньше прибыль к риску. Без преимущества эти два эффекта гасят друг друга: матожидание ≈ 0, а после комиссий минус. Поэтому <b>вход только «от уровня» не работает</b>. Зато для контекста шансы полезны: они говорят, какой сценарий вероятнее и против чего не стоит торговать.</p>
</section>

<section>
  <h2><span>2</span>Роли таймфреймов</h2>
  <p>Старшие таймфреймы отвечают на вопросы «куда», «что первым» и «где отмена». Младшие — на вопрос «когда и где войти». В методичке только первые.</p>
  <table>
   {tr(['ТФ', 'Вопрос', 'Инструменты', 'Результат'], True)}
   {tr(['Месяц', 'В какой фазе рынок, какие крупные цели?', 'PMH/PML, закрытие месяца, крупные свинги', 'Большая карта и цели на 1–3 месяца'])}
   {tr(['Неделя', 'Какую сторону снимут первой на этой неделе?', 'Состояние закрытия недели, PWH/PWL, свинги W', '<b>BIAS недели</b> = сторона первого снятия + уровень отмены'])}
   {tr(['День', 'Какую сторону снимут первой сегодня?', 'Состояние закрытия дня, PDH/PDL, свинги D', '<b>BIAS дня</b> и цель на день'])}
   {tr(['H4 / H1', 'Где ждать реакцию?', 'FVG, OB, IFVG, структура', 'Зона для поиска входа (следующая методичка)'])}
   {tr(['M15 / M5', 'Есть ли триггер?', 'Снятие, MSS/CISD, FVG', 'Вход, стоп (следующая методичка)'])}
  </table>
  <div class="rule"><b>Важно.</b> Решает <b>последнее закрытие ближайшего старшего ТФ</b>. Месяц почти ничего не добавляет к неделе (глава 5), поэтому ждать, пока «всё совпадёт», не нужно. Внутри недели работаем по состоянию недели, внутри дня — по состоянию дня.</div>
</section>

<section>
  <h2><span>3</span>Нарратив: карта ликвидности</h2>
  <p>Нарратив — это история «откуда цена пришла и к какому пулу ликвидности идёт». Пулы — это хаи и лои прошлого периода (PWH/PWL, PMH/PML, PDH/PDL), неснятые свинги и равные хаи и лои.</p>
  <h3>Что подтвердилось</h3>
  <table>
   {tr(['Ситуация', 'Неделя, 9 монет', 'Неделя, ETH', 'Месяц, 9 монет'], True)}
   {tr(['Открылись в верхней половине прошлого периода → снят его хай', rc_cell(AW['up_H']), rc_cell(AWe['up_H']), rc_cell(AM['up_H'])])}
   {tr(['Открылись в нижней половине → снят лой', rc_cell(AW['dn_L']), rc_cell(AWe['dn_L']), rc_cell(AM['dn_L'])])}
   {tr(['Не снята ни одна сторона', rc_cell(AW['none']), rc_cell(AWe['none']), rc_cell(AM['none'])])}
   {tr(['Сняты обе стороны', rc_cell(AW['both']), rc_cell(AWe['both']), rc_cell(AM['both'])])}
   {tr(['Ближний неснятый свинг снимут первым (W / D)', f'{rc_cell(NEAR_W)} / {rc_cell(NEAR_D)}', '—', '—'])}
  </table>
  <figure>{fig_curve()}<figcaption>Рис. 2. По горизонтали — шанс, который дало бы одно расстояние до пулов; по вертикали — как часто верхний пул снимали первым. Факт и контроль почти совпадают: цену «тянет» к пулу ровно настолько, насколько он ближе.</figcaption></figure>
  <h3>Что не подтвердилось</h3>
  <ul>
   <li><b>Равные хаи и лои (EQH/EQL) не сильнее обычных свингов.</b> Отклонение от ожидания: неделя EQH {EQ[("W","EQH")][0]*100:+.0f} п.п. против {EQ[("W","EQH")][1]*100:+.0f} у одиночных; день EQH {EQ[("D","EQH")][0]*100:+.0f} против {EQ[("D","EQH")][1]*100:+.0f}. Отдельного веса им не даём.</li>
   <li><b>«После снятия пула цена идёт к противоположному»</b> — {rc_cell(POOL[("W",False)])} на неделе после возврата внутрь и {rc_cell(POOL[("D",False)])} на дне. Как в контроле.</li>
  </ul>
  <div class="rule"><b>Как использовать.</b> Карта ликвидности даёт <b>цели</b> и <b>ожидание недели</b>. Ближайший пул — самая вероятная цель. Направление сделки одна карта не задаёт: его даёт состояние закрытия (глава 4).</div>
</section>

<section>
  <h2><span>4</span>BIAS: состояние закрытия свечи</h2>
  <p>Каждую закрытую неделю (день, месяц) относим к одному из шести состояний относительно диапазона предыдущей свечи. Дальше смотрим, что делает следующая свеча с диапазоном этой: какую сторону снимает и какую первой.</p>
  <figure>{fig_states()}<figcaption>Рис. 3. Шесть состояний недельного закрытия (9 монет). Серый прямоугольник — диапазон прошлой недели, свеча — закрытая неделя. Крупная цифра — какую сторону <b>этой</b> недели следующая неделя снимет первой.</figcaption></figure>
  {state_table(rW, sW, 'Неделя, 9 монет. Следующая неделя относительно диапазона этой; в скобках — контроль.')}
  <h3>Главный вывод главы</h3>
  <figure>{fig_first_vs_close()}<figcaption>Рис. 4. Сторона первого снятия угадывается хорошо (синие столбики далеко от 50%), направление закрытия — нет (оранжевые около 50%).</figcaption></figure>
  <div class="rule"><b>BIAS = сторона первого снятия, а не направление закрытия.</b>
  <ul>
   <li>Принятие выше → хай этой свечи снимут первым в {pc(rW.loc["принятие выше","firstH"])} случаев. Но закроется следующая неделя выше лишь в {pc(rW.loc["принятие выше","up"])}.</li>
   <li>Принятие ниже → лой первым в {pc(1-rW.loc["принятие ниже","firstH"])}.</li>
   <li>Отказ снизу → хай первым в {pc(rW.loc["отказ снизу","firstH"])}, отказ сверху → лой первым в {pc(1-rW.loc["отказ сверху","firstH"])}.</li>
   <li>«Внутри» и «обе сняты» — около 50/50, BIAS нет.</li>
  </ul>
  После того как цель первого снятия достигнута, <b>BIAS исчерпан</b>: дальше снова монетка, и нужен новый сигнал.</div>
  {state_table(rD, sD, 'День, 9 монет. Следующий день относительно диапазона этого; в скобках — контроль.')}
  <div class="note"><b>Единственное место, где факт заметно лучше контроля, — дневной отказ снизу.</b> Сняли PDL и закрылись обратно внутрь → на следующий день лой этого дня снимают только в {pc(D_REJ[0])} случаев (контроль {pc(D_REJ[1])}), а хай первым — в {pc(D_REJ_H[0])} ({pc(D_REJ_H[1])}). Выборка большая (n={int(rD.loc["отказ снизу","n"])}), так что это реальное свойство: лой дня с отказом держится лучше случайного.</div>
  {state_table(rM, sM, 'Месяц, 9 монет. Выборки маленькие: ориентир, а не правило.')}
  {state_table(rWe, sWe, 'Неделя, только ETH.')}
</section>

<section>
  <h2><span>5</span>Совмещение таймфреймов</h2>
  <p>Популярная идея: «торгуй, только когда месяц и неделя смотрят в одну сторону». Проверяем: делает ли бычий месяц бычью неделю сильнее?</p>
  {align_table()}
  <div class="rule"><b>Вывод.</b> Сторону первого снятия на неделе определяет <b>неделя</b>: бычья неделя даёт {pc(AL_R.xs("бычье", level="W").firstH.min())}–{pc(AL_R.xs("бычье", level="W").firstH.max())} хая первым при любом месяце. Месяц сверху ничего не добавляет. Месяц нужен для <b>карты и крупных целей</b>, а BIAS берём с ближайшего закрытого ТФ.</div>
</section>

<section>
  <h2><span>6</span>Сценарии после снятия уровня</h2>
  <p>Цена сняла хай или лой прошлого периода. Дальше всё решает закрытие периода.</p>
  <figure>{fig_scen()}<figcaption>Рис. 5. Неделя, 9 монет. Месяц ведёт себя так же: принятие → противоположная сторона только в {pc(AM["acc_opp"][0])}, возврат → середина в {pc(AM["rej_mid"][0])}.</figcaption></figure>
  <table>
   {tr(['После снятия одной стороны', 'Неделя, 9 монет', 'Неделя, ETH', 'Месяц, 9 монет'], True)}
   {tr(['Закрытие ЗА уровнем → середина раньше нового экстремума', rc_cell(AW['acc_mid']), rc_cell(AWe['acc_mid']), rc_cell(AM['acc_mid'])])}
   {tr(['Закрытие ЗА уровнем → противоположная сторона раньше', rc_cell(AW['acc_opp']), rc_cell(AWe['acc_opp']), rc_cell(AM['acc_opp'])])}
   {tr(['Возврат внутрь → середина раньше нового экстремума', rc_cell(AW['rej_mid']), rc_cell(AWe['rej_mid']), rc_cell(AM['rej_mid'])])}
   {tr(['Возврат внутрь → противоположная сторона раньше', rc_cell(AW['rej_opp']), rc_cell(AWe['rej_opp']), rc_cell(AM['rej_opp'])])}
   {tr(['Сняты обе → закрытие в половине второго снятия', rc_cell(AW['both_second']), rc_cell(AWe['both_second']), rc_cell(AM['both_second'])])}
  </table>
  <div class="rule"><b>Правила.</b>
  <ol>
   <li><b>Против принятия не торгуем.</b> Закрылись за уровнем → в {pc(1-AW["acc_opp"][0])} случаев сначала будет новый экстремум.</li>
   <li><b>После отказа реальная цель — середина</b> прошлого диапазона ({pc(AW["rej_mid"][0])}), а не противоположная сторона ({pc(AW["rej_opp"][0])}).</li>
   <li>Сняты обе стороны → неделя чаще закрывается в стороне второго снятия ({pc(AW["both_second"][0])} против {pc(AW["both_second"][1])} в контроле). Это небольшое преимущество.</li>
  </ol></div>
</section>

<section>
  <h2><span>7</span>Зоны контекста: премиум/дискаунт, FVG, OB</h2>
  <h3>Премиум и дискаунт</h3>
  <p>Dealing range — между последним подтверждённым свинг-хаем и свинг-лоем. Проверяем, куда цена идёт сначала, в зависимости от того, где открылась неделя.</p>
  <figure>{fig_prem()}<figcaption>Рис. 6. «В дискаунте покупаем» не подтверждается: направление от положения в диапазоне не зависит. Под сломанной структурой (ниже диапазона) цена идёт вверх хуже контроля.</figcaption></figure>
  <h3>FVG и OB старших таймфреймов</h3>
  <figure>{fig_zones()}<figcaption>Рис. 7. Реакция от зон старших ТФ на уровне контроля, то есть на уровне безубытка.</figcaption></figure>
  {zones_table()}
  <div class="note"><b>Кандидат на проверку — медвежий недельный OB.</b> Цена касается его снизу: цель 1:1 раньше стопа в {rc_cell(wob)} случаев, 1:2 — в {rc_cell(wob2)}, n={wob[2]}. По годам нестабильно, на BTC слабо. Пока это гипотеза, а не правило.</div>
  <div class="rule"><b>Как использовать зоны в контексте.</b>
  <ul>
   <li>HTF FVG/OB — это <b>адрес</b>: где искать вход на младших ТФ и где ставить цели. Входить только «от зоны» нельзя.</li>
   <li>Премиум/дискаунт — не фильтр направления. Не покупать «дёшево» под сломанной структурой.</li>
   <li>Инверсия HTF-зоны сама по себе тоже не сигнал: продолжение {rc_cell(ZT[("W","FVG","inv_down1",None)])} на неделях.</li>
  </ul></div>
</section>

<section>
  <h2><span>8</span>Алгоритм подготовки: неделя и день</h2>
  <figure>{fig_flow()}<figcaption>Рис. 8. Порядок подготовки. Шаги 1–4 — в воскресенье, шаг 5 — каждый день перед сессией, шаг 6 — передача на младшие ТФ.</figcaption></figure>
  <h3>Карточка недели (заполнять в воскресенье)</h3>
  <table class="form">
   {tr(['Месяц: состояние закрытия', '☐ принятие выше ☐ отказ снизу ☐ внутри ☐ обе ☐ отказ сверху ☐ принятие ниже'])}
   {tr(['Месяц: PMH / PML / середина', '______ / ______ / ______'])}
   {tr(['Неделя: состояние закрытия', '☐ принятие выше ☐ отказ снизу ☐ внутри ☐ обе ☐ отказ сверху ☐ принятие ниже'])}
   {tr(['BIAS недели: первым снимут', '☐ хай (____) ☐ лой (____) ☐ нет BIAS (50/50)  · шанс по таблице: ___%'])}
   {tr(['Цель после первого снятия', 'середина прошлой недели ______ / следующий пул ______'])}
   {tr(['Ближайшие неснятые свинги W/D', 'сверху ______ ______ · снизу ______ ______'])}
   {tr(['Отмена сценария', 'закрытие дня/недели за ______'])}
   {tr(['Зоны HTF для поиска входа', 'FVG/OB ______–______ · ______–______'])}
  </table>
  <h3>Карточка дня (перед Лондоном или Нью-Йорком)</h3>
  <table class="form">
   {tr(['Вчера: состояние закрытия', '☐ принятие выше ☐ отказ снизу ☐ внутри ☐ обе ☐ отказ сверху ☐ принятие ниже'])}
   {tr(['BIAS дня: первым снимут', '☐ PDH (____) ☐ PDL (____) ☐ нет BIAS  · совпадает с неделей? ☐ да ☐ нет'])}
   {tr(['Цель недели уже достигнута?', '☐ да → BIAS недели исчерпан ☐ нет'])}
   {tr(['Что жду', 'снятие ______ в зоне ______ во время ______'])}
  </table>
</section>

<section>
  <h2><span>9</span>Передача на младшие таймфреймы</h2>
  <p>Контекст передаёт младшим ТФ четыре вещи. Всё остальное решается там.</p>
  <table>
   {tr(['Что передаём', 'Откуда', 'Как применять на H4/M15'], True)}
   {tr(['<b>Направление</b>', 'Сторона первого снятия (гл. 4)', 'Ищем входы только в сторону первого снятия, пока оно не случилось'])}
   {tr(['<b>Цель</b>', 'Хай/лой свечи, середина диапазона, ближний пул (гл. 3, 6)', 'Тейк — у пула, а не «по RR»'])}
   {tr(['<b>Отмена</b>', 'Закрытие за уровнем против сценария (гл. 6)', 'Закрылись против — сценарий снят, не усредняем'])}
   {tr(['<b>Адрес</b>', 'Зоны HTF FVG/OB (гл. 7)', 'Место, где ждать триггер; сама зона — не вход'])}
  </table>
  <div class="rule"><b>Пять правил передачи.</b>
  <ol>
   <li>Нет BIAS (внутри, обе сняты) → на младших ТФ работаем только от явных снятий и с малой целью, или не работаем.</li>
   <li>BIAS есть → младший ТФ ищет вход в его сторону. Против BIAS — только после того, как цель первого снятия достигнута.</li>
   <li>Цель первого снятия достигнута → BIAS исчерпан, ждём новое закрытие.</li>
   <li>Дневной BIAS против недельного → приоритет у дня внутри дня, но цель дня — не дальше недельного уровня.</li>
   <li>Против принятия на старшем ТФ не торгуем (82–86% продолжения).</li>
  </ol></div>
</section>

<section>
  <h2><span>10</span>Разбор: ETH, октябрь 2026</h2>
  <figure>{eth_week_chart()}<figcaption>Рис. 9. Неделя. Сентябрь — материнская неделя 21.09 и инсайд 28.09.</figcaption></figure>
  <figure>{eth_day_chart()}<figcaption>Рис. 10. День. Данные до {LAST_T:%d.%m.%Y %H:%M} UTC, цена {f0(PRICE)}.</figcaption></figure>
  <table class="form">
   {tr(['Месяц', f'Сентябрь закрылся {f0(M_SEP.c)} выше хая августа {f0(M_AUG.h)} → <b>{ST_M}</b>. По таблице октябрь снимает хай сентября {f0(M_SEP.h)} раньше лоя в {pc(rM.loc[ST_M,"firstH"])} случаев (лой сентября {f0(M_SEP.l)} далеко). Пока ни одна сторона не снята.'])}
   {tr(['Неделя', f'Неделя 28.09 ({f0(W_IB.h)} / {f0(W_IB.l)}) — <b>{ST_W}</b> недели 21.09 ({f0(W_MO.h)} / {f0(W_MO.l)}). BIAS нет: {pc(rW.loc[ST_W,"firstH"])} хай / {pc(1-rW.loc[ST_W,"firstH"])} лой. Первым сняли <b>лой</b> ({f0(W_IB.l)}), затем лой матери {f0(W_MO.l)}; минимум недели {f0(W_NOW.l)}.'])}
   {tr(['День', f'06.10 — <b>{ST_D}</b> 05.10, BIAS нет. Сегодня снят PDL {f0(D_Y.l)}, минимум {f0(D_T.l)}.'])}
   {tr(['Сценарий', f'Первое снятие недели (лой) уже случилось → недельный BIAS исчерпан. Решать будет <b>закрытие недели</b>: закрытие ниже лоя матери {f0(W_MO.l)} — принятие ниже, против него лонги не ищем; закрытие обратно выше — отказ снизу, тогда хай этой недели первым в {pc(rW.loc["отказ снизу","firstH"])}, цель — середина матери {f0(W_MO.l+(W_MO.h-W_MO.l)/2)}.'])}
   {tr(['Месячная цель', f'Хай сентября {f0(M_SEP.h)} остаётся главным крупным пулом, пока октябрь не закрылся ниже лоя сентября.'])}
  </table>
</section>

<section>
  <h2><span>11</span>Мифы и факты</h2>
  <table>
   {tr(['Утверждение', 'Что показали данные', 'Вердикт'], True)}
   {tr(['Цена идёт к ближайшему пулу ликвидности', f'Да, {pc(NEAR_D[0])}, но и в контроле {pc(NEAR_D[1])}', '<span class=y>шанс, не преимущество</span>'])}
   {tr(['EQH/EQL — сильные магниты', 'Не сильнее одиночных свингов', '<span class=n>не подтвердилось</span>'])}
   {tr(['После снятия пула цена идёт к противоположному', f'{pc(POOL[("W",False)][0])} при возврате, как в контроле', '<span class=n>не подтвердилось</span>'])}
   {tr(['Закрытие за уровнем = продолжение', f'{pc(1-AW["acc_opp"][0])} новый экстремум раньше противоположной стороны', '<span class=y>шанс, использовать как запрет</span>'])}
   {tr(['Снятие + возврат = разворот', f'Середина {pc(AW["rej_mid"][0])}, противоположная сторона {pc(AW["rej_opp"][0])}', '<span class=y>цель — середина, не дальше</span>'])}
   {tr(['BIAS по закрытию свечи', f'Сторона первого снятия до {pc(rW.loc["принятие выше","firstH"])}, закрытие ≈ 50%', '<span class=g>работает как «что первым»</span>'])}
   {tr(['Дневной отказ снизу держит лой', f'Лой снят {pc(D_REJ[0])} против {pc(D_REJ[1])} в контроле', '<span class=g>есть преимущество</span>'])}
   {tr(['Месяц + неделя в одну сторону — сильнее', 'Месяц ничего не добавляет к неделе', '<span class=n>не подтвердилось</span>'])}
   {tr(['В дискаунте — покупки, в премиуме — продажи', 'Направление от положения не зависит', '<span class=n>не подтвердилось</span>'])}
   {tr(['Вход от HTF FVG/OB', 'Цель 1:1 в 45–55% — около безубытка', '<span class=n>не вход, а адрес</span>'])}
   {tr(['Медвежий недельный OB', f'1:1 в {pc(wob[0])} против {pc(wob[1])}', '<span class=y>гипотеза</span>'])}
  </table>
</section>

<section>
  <h2><span>12</span>Ограничения, журнал, что дальше</h2>
  <h3>Ограничения</h3>
  <ul>
   <li>Только крипта, Binance Perp, 2020–2026. Большая часть периода — бычий рынок. Контроль сохраняет этот рост, поэтому сравнение честное, но абсолютные проценты на другом рынке могут сдвинуться.</li>
   <li>Неделя с понедельника 00:00 UTC; у ICT — открытие в воскресенье по Нью-Йорку. Для крипты 24/7 разница минимальна.</li>
   <li>Свинги — фракталы 2+2; равные хаи/лои — в пределах 0,15 среднего диапазона свечи.</li>
   <li>Сделано около 200 сравнений с контролем. Несколько «находок» на уровне 2 стандартных ошибок могут быть случайными. В выводы взяты только устойчивые результаты с большой выборкой.</li>
   <li>Прошлые результаты по инсайд-барам (вынос лоя матери, подтверждение недельным закрытием) против контроля ещё <b>не проверены</b>.</li>
  </ul>
  <h3>Журнал контекста</h3>
  <table class="journal">
   {tr(['Дата', 'ТФ', 'Состояние', 'BIAS (что первым)', 'Шанс по таблице', 'Что сняли первым', 'Цель достигнута?', 'Комментарий'], True)}
   {''.join(tr(['&nbsp;'] * 8) for _ in range(6))}
  </table>
  <h3>Что дальше</h3>
  <ol>
   <li>Методичка по исполнению: H4/H1 зоны + M15 триггер <b>только в сторону BIAS</b> и с целью у пула. Проверка тоже против контроля.</li>
   <li>Проверить инсайд-бар против контроля.</li>
   <li>Проверить время: киллзоны, день недели, когда формируется хай или лой недели.</li>
  </ol>
</section>

<section>
  <h2><span>13</span>Приложение: методика</h2>
  <table>
   {tr(['Термин', 'Определение в расчётах'], True)}
   {tr(['Состояние закрытия', 'Принятие выше: close &gt; прошлого хая. Принятие ниже: close &lt; прошлого лоя. Обе сняты: оба экстремума пробиты, close внутри. Отказ сверху/снизу: пробит один экстремум, close внутри. Внутри: ничего не пробито.'])}
   {tr(['Снятие', 'Первая 15m свеча с хаем строго выше уровня (с лоем строго ниже).'])}
   {tr(['Что первым', 'Какая сторона диапазона снята раньше по 15m внутри следующего периода; если ни одной — в расчёт не идёт.'])}
   {tr(['Свинг', 'Фрактал 2+2 на барах периода; подтверждён с открытия бара k+3; активен до первого пробоя.'])}
   {tr(['EQH/EQL', 'Два активных свинга одной стороны в пределах 0,15 × ATR(14) периода.'])}
   {tr(['Dealing range', 'Последний подтверждённый свинг-хай и свинг-лой; положение = (open − лой) / (хай − лой).'])}
   {tr(['FVG', 'Бычий: лой бара k &gt; хая бара k−2, зона — от хая k−2 до лоя k. Медвежий — зеркально.'])}
   {tr(['OB', 'Последняя противоположная свеча k−1, бар k закрылся за её экстремумом; зона — open…low (для бычьего).'])}
   {tr(['Касание зоны', 'Лимит на ближнем крае, стоп за дальним, цель — 1 и 2 размера зоны; одновременно стоп и цель — считаем стоп.'])}
   {tr(['±1 ATR', 'Кто раньше: цена +1 ATR(14) периода или −1 ATR от точки отсчёта.'])}
   {tr(['Контроль', 'Дни (96 свечей 15m) переставлены случайно, свечи сцеплены по close. Три перемешивания, берём среднее.'])}
  </table>
  <p class="small">Скрипты: <code>liquidity/level1.py</code>, <code>level1b.py</code>, <code>bias_states.py</code>, <code>synth.py</code>, <code>compare1.py</code>, <code>compare1b.py</code>, сборка: <code>liquidity/book/build_book.py</code>. Полные таблицы — <code>liquidity/results/</code>.</p>
</section>
''')

CSS = open(__file__.replace('build_book.py', 'book.css')).read()
open(OUT, 'w').write(f'<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>Нарратив, BIAS и контекст</title><style>{CSS}</style></head><body>{"".join(H)}</body></html>')
print('ok', OUT)
