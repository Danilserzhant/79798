"""report.html из results/ (python build_report.py)."""
import json, html, pandas as pd
now = json.load(open('results/now.json'))
A = pd.read_csv('results/conf_from_first_sweep.csv'); B = pd.read_csv('results/conf_from_current_state.csv')
E = pd.read_csv('results/events.csv'); Ec = E[~E.open]
e = html.escape
def f(x, d=1):
    if pd.isna(x): return '—'
    t = f'{x:.{d}f}'
    if float(t) == 0: t = t.lstrip('-')
    return t.replace('.', ',').replace('-', '−')
L, H, R, ML, MH = 2634.00, 2779.00, 145.00, 2626.01, 2806.76
TPN = {'H': 'хай IB', 'mid': 'середина IB', '2R': '2R', 'ext1': 'L − 1 диапазон'}

def conf_table(df, top=None, note=''):
    df = df[df.n >= 50].sort_values('exp', ascending=False)
    if top: df = df.head(top)
    rows = ''
    for _, r in df.iterrows():
        cls = 'up' if r.exp >= 0.1 and r.expA > 0 and r.expB > 0 else ('down' if r.exp < 0 else '')
        kind = '<span class="pill rev">разворот</span>' if r.kind == 'rev' else '<span class="pill cont">продолжение</span>'
        rows += (f'<tr><td>{kind} {e(r.conf)}</td><td>{TPN[r.tp]}</td><td class="num">{int(r.n)}</td><td class="num">{f(r.win)}%</td>'
                 f'<td class="num">{f(r.rr, 2)}</td><td class="num {cls}">{f(r.exp, 2)}</td><td class="num">{f(r.pf, 2)}</td>'
                 f'<td class="num">{f(r.expA, 2)}</td><td class="num">{f(r.expB, 2)}</td><td class="num">{r.yrs}</td><td class="num">{int(r.syms_pos)}/9</td></tr>')
    return f'''{f"<p class=note>{note}</p>" if note else ""}<div class="tw"><table>
<tr><th>Подтверждение</th><th>Цель</th><th>n</th><th>Тейк</th><th>RR</th><th>Ср. R</th><th>PF</th><th>2020–23</th><th>2024–26</th><th>Годы в +</th><th>Монеты в +</th></tr>{rows}</table></div>'''

def prob_row(label, key, price=None):
    a, eth, lo, mw = now['all'][key], now['ETH'][key], now['low_side'][key], now['midweek_low'][key]
    return f'<tr><td>{label}</td><td class="num">{price or ""}</td><td class="num big">{f(a)}%</td><td class="num">{f(eth)}%</td><td class="num">{f(lo)}%</td><td class="num">{f(mw)}%</td></tr>'

# лестница уровней
lv = [(MH, 'Хай матери (21.09)', 'muted'), (H, 'Хай IB (28.09) — H', 'h'), (L + R / 2, 'Середина IB', ''), (L, 'Лой IB — L (и лой матери 2626) — сняты 07.10', 'l'), (2565.01, 'Лой сегодня (Binance spot)', 'now'), (L - R, 'L − 1 диапазон IB', 'tgt'), (L - 1.5 * R, 'L − 1,5 диапазона', 'tgt')]
lo_p, hi_p = 2400, 2830
def y(p): return (hi_p - p) / (hi_p - lo_p) * 100
ladder = ''.join(f'<div class="lv {c}" style="top:{y(p):.2f}%"><span class="lp">{p:,.2f}</span><span class="ll">{e(t)}</span></div>'.replace(',', ' ', 1) for p, t, c in lv)
cur = 2573.07

page = f'''<title>ETH: недельный инсайд-бар</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Onest:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
:root{{--bg:#f3f5f9;--surface:#fff;--ink:#101521;--ink2:#465061;--muted:#7a8496;--line:#dde2ea;--hi:#2a78d6;--lo:#eb6834;--tgt:#4a3aa7;--up:#0b7a3e;--down:#c0342f;--upbg:#e3f4ea;--downbg:#fbe6e4;--zone:#e9eef8;
--f:"Onest",system-ui,-apple-system,"Segoe UI",sans-serif;--m:"JetBrains Mono",ui-monospace,Menlo,Consolas,monospace}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{color-scheme:dark;--bg:#0e1218;--surface:#161b23;--ink:#eef2f7;--ink2:#b2bccb;--muted:#8490a2;--line:#29313d;--hi:#3987e5;--lo:#d95926;--tgt:#9085e9;--up:#4cc27f;--down:#ef7a73;--upbg:#153324;--downbg:#3a1c1b;--zone:#1d2533}}}}
:root[data-theme="dark"]{{color-scheme:dark;--bg:#0e1218;--surface:#161b23;--ink:#eef2f7;--ink2:#b2bccb;--muted:#8490a2;--line:#29313d;--hi:#3987e5;--lo:#d95926;--tgt:#9085e9;--up:#4cc27f;--down:#ef7a73;--upbg:#153324;--downbg:#3a1c1b;--zone:#1d2533}}
body{{background:var(--bg);color:var(--ink);font:15px/1.6 var(--f);padding-inline:16px;padding-block:32px 64px}}
main{{max-width:1000px;margin:0 auto;display:grid;gap:40px}}
header{{display:grid;gap:10px}} .eyebrow{{font:600 12px var(--m);letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}}
h1{{font-size:clamp(28px,5vw,42px);line-height:1.1;margin:0;text-wrap:balance}} h2{{font-size:22px;margin:0;text-wrap:balance}} h3{{font-size:16px;margin:8px 0 0}}
p{{margin:0;max-width:70ch;color:var(--ink2)}} .lead{{font-size:17px}} section{{display:grid;gap:14px}}
.now{{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.1fr);gap:16px}} @media (max-width:760px){{.now{{grid-template-columns:1fr}}}}
.panel{{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:18px}}
.ladder{{position:relative;height:420px;margin:6px 0 4px 0}}
.ladder .zone{{position:absolute;left:0;right:0;background:var(--zone);border-radius:4px}}
.lv{{position:absolute;left:0;right:0;border-top:1px solid var(--line);display:flex;gap:10px;align-items:center;transform:translateY(-50%);font-size:13px}}
.lv .lp{{font:600 12.5px var(--m);background:var(--surface);padding-right:6px;min-width:76px}} .lv .ll{{color:var(--ink2);background:var(--surface);padding-inline:4px}}
.lv.h{{border-top:2px solid var(--hi)}} .lv.l{{border-top:2px solid var(--lo)}} .lv.tgt{{border-top:1px dashed var(--tgt)}} .lv.muted .ll{{color:var(--muted)}}
.lv.now{{border-top:2px dotted var(--ink)}} .lv.now .ll{{color:var(--ink);font-weight:600}}
.verdict{{display:grid;gap:12px}} .verdict b{{color:var(--ink)}}
.big3{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}} @media (max-width:520px){{.big3{{grid-template-columns:1fr}}}}
.kpi{{border:1px solid var(--line);border-radius:10px;padding:12px 14px;display:grid;gap:2px;background:var(--surface)}} .kpi b{{font:600 26px var(--m)}} .kpi span{{font-size:13px;color:var(--ink2);line-height:1.35}}
.tw{{overflow-x:auto;background:var(--surface);border:1px solid var(--line);border-radius:10px}}
table{{border-collapse:collapse;width:100%;font-size:14px;min-width:640px}}
th{{text-align:left;font:600 11px var(--m);letter-spacing:.05em;text-transform:uppercase;color:var(--muted);padding:10px 12px;border-bottom:1px solid var(--line);white-space:nowrap}} th:not(:first-child){{text-align:right}}
td{{padding:8px 12px;border-bottom:1px solid var(--line)}} tr:last-child td{{border-bottom:0}}
.num{{font-family:var(--m);font-variant-numeric:tabular-nums;text-align:right;white-space:nowrap}} td.big{{font-weight:600;font-size:15px}}
td.up{{color:var(--up);background:var(--upbg);font-weight:600}} td.down{{color:var(--down);background:var(--downbg)}}
.pill{{display:inline-block;font:600 10.5px var(--m);letter-spacing:.04em;text-transform:uppercase;padding:1px 6px;border-radius:4px;margin-right:4px;border:1px solid var(--line)}}
.pill.rev{{color:var(--hi)}} .pill.cont{{color:var(--lo)}}
.note{{font-size:13.5px;color:var(--muted)}} ol.steps{{margin:0;padding-left:20px;display:grid;gap:8px;color:var(--ink2)}} ol.steps b{{color:var(--ink)}}
code{{font-family:var(--m);font-size:.9em}}
</style>
<main>
<header>
<div class="eyebrow">ETHUSDT Perp · Binance · 1W · данные по 07.10.2026 12:45 UTC</div>
<h1>Недельный инсайд-бар ETH: лой снят</h1>
<p class="lead">Неделя 28.09 — инсайд внутри недели 21.09. В среду 07.10 в 02:00 UTC цена ушла под лой инсайда 2634, затем под лой матери 2626 и дошла до 2565. Сейчас около 2573: это 0,43 диапазона инсайда под его лоем. Хай инсайда 2779 на этой неделе не трогали.</p>
</header>

<section class="now">
<div class="panel"><h3>Уровни</h3><div class="ladder"><div class="zone" style="top:{y(H):.2f}%;height:{y(L)-y(H):.2f}%"></div>{ladder}</div>
<p class="note">Диапазон инсайда R = 145 (5,5%). Сегодняшние цены взяты со спота Binance: архив перпа за 07.10 ещё не выложен, расхождение с перпом несколько долларов.</p></div>
<div class="verdict">
<div class="big3">
<div class="kpi"><b>{f(now["all"]["reach_E1"],0)}%</b><span>дойдёт до 2489 (L − 1R) за 4 недели</span></div>
<div class="kpi"><b>{f(now["all"]["H_first"],0)}%</b><span>сначала вернётся к хаю 2779, а не к 2489</span></div>
<div class="kpi"><b>{f(now["all"]["wk_close_inside"],0)}%</b><span>неделя закроется обратно выше 2634</span></div>
</div>
<div class="panel verdict">
<p><b>Базовый сценарий — продолжение вниз.</b> В похожих случаях ({now["all"]["n"]} случаев на 9 монетах, из них {now["ETH"]["n"]} на ETH) цена в {f(now["all"]["E1_first"],0)}% случаев сначала доходила до L − 1R, а не до хая инсайда. При этом к самому уровню 2634 цена возвращается в {f(now["all"]["back_L"],0)}% случаев за 4 недели. Чаще это ретест снизу, а не возврат в диапазон.</p>
<p><b>Шортить отсюда без подтверждения бессмысленно.</b> Шорт по рынку из такого состояния со стопом за L дал {f(B[B.conf.str.contains("шорт по рынку")].exp.iloc[0],2)}R в среднем. Почти весь ход до цели уже пройден, а стоп далеко.</p>
<p><b>Лонг — только после возврата цены выше 2634.</b> Лучшее подтверждение отсюда — закрытие H4 (или H1/M15) обратно выше L, стоп под лоем свипа, цель 2R: +0,13…+0,17R на сделку. Лонг «на ноже» без подтверждения или по слому структуры на M15/H1 ниже уровня — в минусе.</p>
</div></div>
</section>

<section>
<h2>Вероятности из текущего состояния</h2>
<p>Отбирались случаи с той же картиной: первым снят лой инсайда (для хая — зеркально), лой матери тоже снят, вынос под L уже не меньше 0,476 R, хай инсайда не тронут. Отсчёт идёт от момента, когда все условия впервые выполнились; горизонт — 4 недели.</p>
<div class="tw"><table>
<tr><th>Исход</th><th>Цена ETH</th><th>Все 9 монет</th><th>ETH</th><th>Только снятие лоя</th><th>Лой, середина недели</th></tr>
<tr><td>n случаев</td><td></td><td class="num big">{now["all"]["n"]}</td><td class="num">{now["ETH"]["n"]}</td><td class="num">{now["low_side"]["n"]}</td><td class="num">{now["midweek_low"]["n"]}</td></tr>
{prob_row("Дойдёт до L − 1R", "reach_E1", "2489")}
{prob_row("Дойдёт до L − 1,5R", "reach_E15", "2416")}
{prob_row("L − 1R раньше хая IB", "E1_first")}
{prob_row("Хай IB раньше L − 1R", "H_first", "2779")}
{prob_row("Середина IB раньше L − 1R", "mid_first", "2706")}
{prob_row("Вернётся к L (касание)", "back_L", "2634")}
{prob_row("Вернётся к L раньше, чем дойдёт до L − 1R", "L_before_E1")}
{prob_row("Неделя закроется выше L (ложный пробой)", "wk_close_inside")}
{prob_row("Неделя закроется ниже лоя матери", "wk_close_below_mother", "2626")}
</table></div>
<p class="note">«Лой, середина недели» (вт–чт, n = {now["midweek_low"]["n"]}) — самый близкий аналог по форме, но выборка маленькая: ±12 п.п. Там хай IB раньше L − 1R в {f(now["midweek_low"]["H_first"],0)}% случаев, а неделя закрывается обратно в диапазоне в {f(now["midweek_low"]["wk_close_inside"],0)}%. Разумный коридор для ETH сейчас: L − 1R первым — 55–75%, возврат к хаю первым — 23–41%.</p>
</section>

<section>
<h2>Какое подтверждение работает лучше: из текущего состояния</h2>
{conf_table(B, note="Подтверждение ищется в течение 7 дней. Лонг: вход по закрытию подтверждающей свечи, стоп под лоем свипа −0,1%. Шорт: стоп над хаем свечи (не ниже L). Если стоп и тейк в одной 15m свече — считается стоп. Издержки 0,1% на сделку. Удержание до 4 недель. Показаны варианты с n ≥ 50; зелёным — средний R ≥ 0,1 и плюс в обоих периодах.")}
</section>

<section>
<h2>Какое подтверждение лучше в целом: от первого снятия стороны IB</h2>
<p>То же самое для всех {len(Ec)} снятий стороны недельного инсайда с 2020 года. Отсчёт от первого касания уровня, без условия про мать и глубину выноса.</p>
{conf_table(A, top=18)}
<ol class="steps">
<li><b>Самые устойчивые — закрытие D1 обратно за уровень и слом структуры на H4.</b> D1-реклейм с целью в противоположный край IB: тейк в 50% сделок, +0,19R, плюс на 7 из 9 монет. H4 CHoCH с целью 2R или хай IB: около +0,15R, плюс в 6 из 7 лет, в обоих периодах и на 7–8 из 9 монет.</li>
<li><b>Младшие таймфреймы не работают.</b> Реклейм и CHoCH на M15 и реклейм на H1 — около нуля или в минусе: шум и ложные возвраты.</li>
<li><b>Лимитка прямо на уровне без подтверждения убыточна</b> (−0,03…−0,08R). Шорт пробоя без подтверждения — около нуля.</li>
<li><b>Ставки на продолжение слабые.</b> Лучшее — закрытие M15 за уровнем с целью 2R: +0,09R, нестабильно по монетам. D1-закрытие за уровнем как сигнал на шорт в минусе: к закрытию дня ход часто уже сделан.</li>
</ol>
</section>

<section>
<h2>Методика и оговорки</h2>
<p>Данные: 15m свечи USDT-M перпов Binance (data.binance.vision), 2020-01 … 2026-10-06, плюс 07.10 со спота Binance. Монеты: ETH, BTC, SOL, BNB, XRP, ADA, DOGE, LTC, LINK. Неделя начинается в понедельник 00:00 UTC. Инсайд: H ≤ H матери и L ≥ L матери. Пробой ждём до 8 недель после закрытия инсайда; в 90% случаев он происходит уже в следующую неделю. Снятие хая считается зеркально к снятию лоя. Перебрано 35 вариантов подтверждения на общей выборке и 34 на выборке из текущего состояния. Разница в 0,05R между вариантами — шум. Эффект порядка +0,15R на 400–500 сделках значим примерно на уровне 2,5σ. Это статистика, а не гарантия; уровни стопа и размер позиции — на твоё усмотрение.</p>
</section>
</main>'''
open('report.html', 'w').write(page); print('ok')
