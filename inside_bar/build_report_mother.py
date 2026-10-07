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

page = f'''<title>ETH: материнская неделя</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Onest:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
{css}
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
<p><b>Шорт отсюда без подтверждения — минус</b> ({f(shortnow.exp,2)}R в среднем). Ставки на продолжение после снятия лоя матери не дали ничего ни на одном таймфрейме.</p>
<p><b>Лонг — только после закрытия H1 обратно выше 2626.</b> Стоп под лоем свипа (сейчас ≈{f(stop,0)}), цель 2R. При входе около {f(ent,0)} это ≈{f(tgt2,0)} — практически хай матери. Из текущего состояния это лучший устойчивый вариант: {f(h1.exp,2)}R, но выборка {int(h1.n)} сделок и интервал захватывает ноль. Свежий период 2024–26 по этому входу в минусе.</p>
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

<section>
<h2>Подтверждения из текущего состояния (снятие лоя матери)</h2>
<p>Лонг: вход по закрытию подтверждающей свечи, стоп под лоем свипа −0,1%. Шорт: стоп над хаем свечи (не ниже L). Если стоп и тейк в одной 15m свече — стоп. Издержки 0,1% на сделку. «Без топ-5%» — средний R без 5% лучших сделок: проверка, не держится ли результат на паре выбросов. Зелёным — 90% интервал выше нуля.</p>
{table(S, top=16)}
<p class="note">Ни один вариант из текущего состояния не значим: 90% интервалы у всех захватывают ноль. CHoCH на M15 с целью в хай матери выглядит лучшим ({f(m15c.exp,2)}R), но без 5% лучших сделок даёт {f(m15c.trim,2)}R — держится на нескольких выносах. Реклеймы на H1/M15/H4 с целью 2R остаются в плюсе и без выбросов (+0,03…+0,14R), поэтому они надёжнее.</p>
</section>

<section>
<h2>Подтверждения от первого снятия лоя матери</h2>
<p>Все {len(El)} случаев, когда после инсайда первым снимался лой материнской недели. Подтверждение ищется 7 дней от первого касания.</p>
{table(F, top=14)}
<ol class="steps">
<li><b>Единственный статистически устойчивый вход — закрытие D1 обратно выше лоя матери, цель 2R.</b> {f(best.exp,2)}R на сделку, 90% интервал {f(best.lo5,2)}…{f(best.hi95,2)}, без топ-5% всё ещё {f(best.trim,2)}R. Плюс в {best.yrs} лет и на {best.syms} монет.</li>
<li><b>Реклейм на M15 с целью в хай матери — ловушка.</b> Средний R высокий за счёт редких огромных выносов (RR около 13), без них результат сильно отрицательный.</li>
<li><b>Продолжение вниз после снятия лоя матери почти не работает.</b> Лучшее — закрытие M15 ниже L с целью 2R: +0,15R, нестабильно. Закрытие D1 ниже лоя как сигнал на шорт — в минусе.</li>
</ol>
</section>

<section>
<h2>Методика и оговорки</h2>
<p>15m свечи USDT-M перпов Binance, 2020-01 … 2026-10-06; 07.10 — спот Binance. Монеты: ETH, BTC, SOL, BNB, XRP, ADA, DOGE, LTC, LINK. Неделя начинается в понедельник 00:00 UTC. Мать — неделя перед инсайдом; пробой её стороны ждём до 8 недель после закрытия инсайда. 90% интервал посчитан бутстрапом по сделкам. Перебрано 35 вариантов подтверждения: если что-то выглядит хорошо только в одной строке, скорее всего это случайность. Вся статистика — про частоты в прошлом, не прогноз; размер позиции и стопы на твоё усмотрение.</p>
</section>
</main>'''
open('report.html', 'w').write(page); print('ok')
