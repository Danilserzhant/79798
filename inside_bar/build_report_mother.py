"""report.html: ETH, диапазон материнской недели (python build_report_mother.py)."""
import json, html, pandas as pd
e = html.escape
css = open('_css.txt').read().replace('{{', '{').replace('}}', '}')
now = json.load(open('results/mother/now.json')); now_ib = json.load(open('results/now.json'))
S = pd.read_csv('results/mother/conf_state_low.csv'); F = pd.read_csv('results/mother/conf_first_low.csv')
Ev = pd.read_csv('results/mother/events.csv'); Ev = Ev[~Ev.open]; El = Ev[Ev.side == 'low']
def f(x, d=1):
    if pd.isna(x): return '—'
    t = f'{x:.{d}f}'
    if float(t) == 0: t = t.lstrip('-')
    return t.replace('.', ',').replace('-', '−')
L, H, R = 2626.01, 2806.76, 180.75
LOW, LAST = 2552.26, 2566.63
TPN = {'H': 'хай матери', 'mid': 'середина матери', '2R': '2R', 'ext1': 'L − 1R'}

def table(df, top=None):
    df = df[df.n >= 40]
    if top: df = df.head(top)
    rows = ''
    for _, r in df.iterrows():
        sig = r.lo5 > 0
        cls = 'up' if sig else ('down' if r.exp < 0 else '')
        kind = '<span class="pill rev">разворот</span>' if r.kind == 'rev' else '<span class="pill cont">продолжение</span>'
        rows += (f'<tr><td>{kind} {e(r.conf)}</td><td>{TPN[r.tp]}</td><td class="num">{int(r.n)}</td><td class="num">{f(r.win)}%</td><td class="num">{f(r.rr,2)}</td>'
                 f'<td class="num {cls}">{f(r.exp,2)}</td><td class="num">{f(r.lo5,2)} … {f(r.hi95,2)}</td><td class="num">{f(r.trim,2)}</td>'
                 f'<td class="num">{f(r.expA,2)}</td><td class="num">{f(r.expB,2)}</td><td class="num">{r.yrs}</td><td class="num">{r.syms}</td></tr>')
    return f'''<div class="tw"><table><tr><th>Подтверждение</th><th>Цель</th><th>n</th><th>Тейк</th><th>RR</th><th>Ср. R</th><th>90% интервал</th><th>Без топ-5%</th><th>2020–23</th><th>2024–26</th><th>Годы в +</th><th>Монеты в +</th></tr>{rows}</table></div>'''

def prow(label, key, price=''):
    return (f'<tr><td>{label}</td><td class="num">{price}</td><td class="num big">{f(now["low_side"][key])}%</td><td class="num">{f(now["midweek_low"][key])}%</td>'
            f'<td class="num">{f(now["all"][key])}%</td><td class="num">{f(now["ETH"][key])}%</td></tr>')

lv = [(H, 'Хай матери (21.09) — H', 'h'), (2779, 'Хай инсайда (28.09)', 'muted'), (L + R / 2, 'Середина матери', ''),
      (L, 'Лой матери — L, снят 07.10 (лой инсайда 2634 рядом)', 'l'),
      (LOW, 'Лой сегодня', 'now'), (L - R, 'L − 1R', 'tgt'), (L - 1.5 * R, 'L − 1,5R', 'tgt')]
lo_p, hi_p = 2330, 2830
def y(p): return (hi_p - p) / (hi_p - lo_p) * 100
ladder = ''.join(f'<div class="lv {c}" style="top:{y(p):.2f}%"><span class="lp">{p:,.2f}</span><span class="ll">{e(t)}</span></div>'.replace(',', ' ', 1) for p, t, c in lv)
best = F.iloc[[i for i, r in F.iterrows() if r.conf.startswith('Реклейм: закрытие D1') and r.tp == '2R'][0]]
h1 = S[(S.conf == 'Реклейм: закрытие H1 обратно выше L') & (S.tp == '2R')].iloc[0]
m15c = S[(S.conf == 'CHoCH M15: закрытие выше свинг-хая') & (S.tp == 'H')].iloc[0]
shortnow = S[S.conf.str.contains('шорт по рынку')].iloc[0]
stop = LOW - 0.001 * LOW; ent = L + 4; tgt2 = ent + 2 * (ent - stop)


P = pd.read_csv('results/mother/conf_prob_state.csv')
NLOW = now["low_side"]["n"]
def pc(x, base=None):
    cls = ''
    if base is not None and not pd.isna(x):
        cls = ' up' if x - base >= 10 else (' down' if base - x >= 10 else '')
    return f'<td class="num{cls}">{f(x,0)}%</td>'
def prob_table(sample, kind):
    d = P[(P['sample'] == sample) & (P.kind == kind)].copy()
    base = d[d.conf.str.startswith('Без подтверждения')].iloc[0]
    d = d[~d.conf.str.startswith('Без подтверждения')]
    nev = NLOW if sample == 'low' else now['all']['n']
    rows = ''
    order = d.sort_values('mid_before_newlow' if kind == 'rev' else 'E1_before_mid', ascending=False)
    if kind == 'rev':
        hdr = '<tr><th>Подтверждение</th><th>Сработало</th><th>n</th><th>Середина 2716 раньше нового лоя</th><th>Хай 2807 раньше нового лоя</th><th>Дойдёт до хая 2807</th><th>Дойдёт до 2445</th><th>Неделя закроется выше 2626</th></tr>'
        rows += (f'<tr class="base"><td>Без подтверждения — база из текущего состояния</td><td class="num">—</td><td class="num">{nev}</td><td class="num">—</td><td class="num">—</td>'
                 f'<td class="num">{f(base.reach_H,0)}%</td><td class="num">{f(base.reach_E1,0)}%</td><td class="num">{f(base.wk_close_inside,0)}%</td></tr>')
        for _, r in order.iterrows():
            small = ' class="small"' if r.n < 30 else ''
            rows += (f'<tr{small}><td>{e(r.conf)}</td><td class="num">{f(r.n/nev*100,0)}%</td><td class="num">{int(r.n)}</td>{pc(r.mid_before_newlow)}{pc(r.H_before_newlow)}'
                     f'{pc(r.reach_H, base.reach_H)}{pc(r.reach_E1, None)}{pc(r.wk_close_inside, base.wk_close_inside)}</tr>')
    else:
        hdr = '<tr><th>Подтверждение</th><th>Сработало</th><th>n</th><th>2445 раньше середины 2716</th><th>Дойдёт до 2445</th><th>Дойдёт до 2355</th><th>Вернётся к 2626</th><th>Неделя закроется выше 2626</th></tr>'
        rows += (f'<tr class="base"><td>Без подтверждения — база из текущего состояния</td><td class="num">—</td><td class="num">{nev}</td><td class="num">{f(base.E1_before_mid,0)}%</td>'
                 f'<td class="num">{f(base.reach_E1,0)}%</td><td class="num">{f(base.reach_E15,0)}%</td><td class="num">{f(base.back_L,0)}%</td><td class="num">{f(base.wk_close_inside,0)}%</td></tr>')
        for _, r in order.iterrows():
            rows += (f'<tr><td>{e(r.conf)}</td><td class="num">{f(r.n/nev*100,0)}%</td><td class="num">{int(r.n)}</td>{pc(r.E1_before_mid, base.E1_before_mid)}'
                     f'{pc(r.reach_E1, base.reach_E1)}{pc(r.reach_E15, base.reach_E15)}{pc(r.back_L, base.back_L)}{pc(r.wk_close_inside, base.wk_close_inside)}</tr>')
    return f'<div class="tw"><table>{hdr}{rows}</table></div>'
lr = P[(P['sample'] == 'low') & (P.conf == 'Реклейм: закрытие D1 обратно выше L')].iloc[0]
lh = P[(P['sample'] == 'low') & (P.conf == 'Реклейм: закрытие H1 обратно выше L')].iloc[0]
l4 = P[(P['sample'] == 'low') & (P.conf == 'Реклейм: закрытие H4 обратно выше L')].iloc[0]
conf_prob_section = f'''<section>
<h2>Вероятности после подтверждения: разворот вверх</h2>
<p>Те же {NLOW} снятий лоя матери из текущего состояния. «Сработало» — в какой доле случаев подтверждение вообще появилось за 7 дней. Дальнейшие проценты считаются среди случаев, где оно появилось; отсчёт от закрытия подтверждающей свечи, горизонт 4 недели. «Новый лой» — цена ниже минимума свипа, который был до подтверждения. Зелёным и красным — отличие от базы на 10 п.п. и больше.</p>
{prob_table('low', 'rev')}
<ol class="steps">
<li><b>Реклейм — закрытие обратно выше 2626 — заметно меняет вероятности.</b> На H1 он появляется в {f(lh.n/NLOW*100,0)}% случаев. После него цена доходит до середины матери раньше нового лоя в {f(lh.mid_before_newlow,0)}% случаев, до хая — в {f(lh.H_before_newlow,0)}%. Шанс дойти до 2445 падает с {f(P[(P['sample']=='low')&(P.conf.str.contains('лонг по рынку'))].reach_E1.iloc[0],0)}% до {f(lh.reach_E1,0)}%.</li>
<li><b>Лучшие вероятности даёт D1-реклейм</b>: середина раньше нового лоя {f(lr.mid_before_newlow,0)}%, хай раньше нового лоя {f(lr.H_before_newlow,0)}%, неделя закрывается выше 2626 в {f(lr.wk_close_inside,0)}%. Но он появляется реже — в {f(lr.n/NLOW*100,0)}% случаев — и позже по цене. H4-реклейм ({f(l4.mid_before_newlow,0)}% / {f(l4.H_before_newlow,0)}%) — почти то же, что H1.</li>
<li><b>Слом структуры (CHoCH) на M15/H1/H4 почти ничего не добавляет.</b> Он срабатывает в 88–100% случаев, то есть фильтрует мало: середина раньше нового лоя только в 25–39%. CHoCH на D1 даёт 82%, но таких случаев всего 11.</li>
</ol>
</section>

<section>
<h2>Вероятности после подтверждения: продолжение вниз</h2>
{prob_table('low', 'cont')}
<p class="note">Закрытие ниже 2626 на любом таймфрейме вероятностей почти не меняет: цена и так уже под уровнем. Продолжение до 2445 остаётся около 50/50, до 2355 — около 25%.</p>
</section>'''

page = f'''<title>ETH: материнская неделя</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Onest:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
{css}
<style>td:first-child{{min-width:240px}} table{{min-width:880px}}</style>
<main>
<header>
<div class="eyebrow">ETHUSDT Perp · Binance · 1W · данные по 07.10.2026 13:00 UTC</div>
<h1>Материнская неделя ETH: лой снят</h1>
<p class="lead">Мать — неделя 21.09: хай 2806,76, лой 2626,01, диапазон R = 180,75 (6,9%). Неделя 28.09 — инсайд внутри неё. 07.10 цена прошла лой инсайда 2634 и лой матери, дошла до {f(LOW,2)}. Сейчас около {f(LAST,2)}: это {f((L-LOW)/R,2)} R под лоем матери. Хай матери не трогали. Ниже — тест именно уровней материнской недели.</p>
</header>

<section class="now">
<div class="panel"><h3>Уровни</h3><div class="ladder"><div class="zone" style="top:{y(H):.2f}%;height:{y(L)-y(H):.2f}%"></div>{ladder}</div>
<p class="note">Сегодняшние цены — спот Binance: архив перпа за 07.10 ещё не выложен.</p></div>
<div class="verdict">
<div class="big3">
<div class="kpi"><b>{f(now["low_side"]["back_L"],0)}%</b><span>цена вернётся к 2626 в течение 4 недель</span></div>
<div class="kpi"><b>{f(now["low_side"]["E1_first"],0)}%</b><span>дойдёт до 2445 (L − 1R) раньше, чем до хая матери</span></div>
<div class="kpi"><b>{f(now["low_side"]["wk_close_inside"],0)}%</b><span>неделя закроется обратно выше 2626</span></div>
</div>
<div class="panel verdict">
<p><b>Сценарии почти поровну.</b> В {now["low_side"]["n"]} похожих снятиях лоя матери на 9 монетах половина дошла до L − 1R, и только {f(now["low_side"]["H_first"],0)}% сначала вернулись к хаю матери. При этом к 2626 цена возвращается в {f(now["low_side"]["back_L"],0)}% случаев, причём в {f(now["low_side"]["L_before_E1"],0)}% — раньше, чем дойдёт до 2445. Возврат к уровню вероятнее, чем ещё одна полная длина диапазона вниз.</p>
<p><b>Подтверждения вниз ничего не добавляют.</b> После закрытия ниже 2626 на любом ТФ шанс дойти до 2445 остаётся ≈50%.</p>
<p><b>Ключевое подтверждение — закрытие обратно выше 2626.</b> Без него хай матери достигается в 27% случаев. После H1-реклейма хай раньше нового лоя — {f(lh.H_before_newlow,0)}%, после D1-реклейма — {f(lr.H_before_newlow,0)}%. Пока цена под 2626, база — 50/50 между 2445 и возвратом к уровню.</p>
</div></div>
</section>

<section>
<h2>Вероятности из текущего состояния</h2>
<p>Отбор: после инсайда первой снята сторона материнской недели, вынос за неё уже ≥ 0,40 R, противоположная сторона матери не тронута. Отсчёт идёт от момента, когда это впервые выполнилось; горизонт — 4 недели. Главная колонка — только снятия лоя: снятия хая в бычьем 2020–2026 ведут себя иначе и смещают общую цифру.</p>
<div class="tw"><table>
<tr><th>Исход</th><th>Цена ETH</th><th>Снятие лоя, 9 монет</th><th>…лой, вт–чт</th><th>Обе стороны</th><th>ETH, обе стороны</th></tr>
<tr><td>n случаев</td><td></td><td class="num big">{now["low_side"]["n"]}</td><td class="num">{now["midweek_low"]["n"]}</td><td class="num">{now["all"]["n"]}</td><td class="num">{now["ETH"]["n"]}</td></tr>
{prow("Вернётся к лою матери", "back_L", "2626")}
{prow("…и раньше, чем дойдёт до L − 1R", "L_before_E1")}
{prow("Дойдёт до L − 1R", "reach_E1", "2445")}
{prow("Дойдёт до L − 1,5R", "reach_E15", "2355")}
{prow("L − 1R раньше хая матери", "E1_first")}
{prow("Середина матери раньше L − 1R", "mid_first", "2716")}
{prow("Хай матери раньше L − 1R", "H_first", "2807")}
{prow("Неделя закроется обратно выше L", "wk_close_inside")}
</table></div>
<p class="note">Только ETH и только снятие лоя — 10 случаев, для выводов мало. Для сравнения: если мерить от диапазона самого инсайда (2634–2779), «L − 1R первым» выходило в {f(now_ib["low_side"]["E1_first"],0)}% случаев. Диапазон матери шире, поэтому его цель вниз дальше и достигается реже.</p>
</section>

{conf_prob_section}

<section>
<h2>Методика и оговорки</h2>
<p>15m свечи USDT-M перпов Binance, 2020-01 … 2026-10-06; 07.10 — спот Binance. Монеты: ETH, BTC, SOL, BNB, XRP, ADA, DOGE, LTC, LINK. Таблицы с матожиданием в R лежат в <code>results/mother/</code>. Неделя начинается в понедельник 00:00 UTC. Мать — неделя перед инсайдом; пробой её стороны ждём до 8 недель после закрытия инсайда. Выборка 95 случаев: точность каждой вероятности около ±10 п.п., у подтверждений с n ≈ 50 — около ±13 п.п. Вся статистика — про частоты в прошлом, не прогноз; размер позиции и стопы на твоё усмотрение.</p>
</section>
</main>'''
open('report.html', 'w').write(page); print('ok')
