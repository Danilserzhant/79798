"""Собирает report.html из results.json (python build_report.py <dir>)."""
import json, sys, html
D = sys.argv[1] if len(sys.argv) > 1 else '.'
o = json.load(open(f'{D}/results.json'))
S, T = o['sweep'], o['trades']
DAYS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
e = html.escape

def f(x, d=1): return '—' if x is None else f'{x:.{d}f}'.replace('.', ',')

def pair_bars(title, a, b, la='Максимум', lb='Минимум', unit='%', mx=None):
    mx = mx or max(max(a), max(b))
    rows = ''
    for i, d in enumerate(DAYS):
        rows += f'''<div class="pb-row"><span class="pb-lab">{d}</span><div class="pb-bars">
<div class="bar s1" style="width:{a[i]/mx*100:.1f}%" title="{la}, {d}: {f(a[i]) if unit else a[i]}{unit}"></div><span class="bv">{f(a[i]) if unit else a[i]}{unit}</span>
<div class="bar s2" style="width:{b[i]/mx*100:.1f}%" title="{lb}, {d}: {f(b[i]) if unit else b[i]}{unit}"></div><span class="bv">{f(b[i]) if unit else b[i]}{unit}</span>
</div></div>'''
    return f'''<figure class="chart"><figcaption>{title}</figcaption>
<div class="legend"><span><i class="sw s1"></i>{la}</span><span><i class="sw s2"></i>{lb}</span></div>{rows}</figure>'''

def race_table():
    head = '<tr><th>Уровень</th><th>Порог</th><th>Продолжение</th><th>Разворот</th><th></th></tr>'
    body = ''
    groups = [('PWH — хай прошлой недели', 'h', S), ('PWL — лой прошлой недели', 'l', S)]
    for name, sd, src in groups:
        for i, k in enumerate(('0.5', '1.0', '2.0')):
            r = src[f'{sd}_race{k}']
            body += f'<tr><td>{name if i == 0 else ""}</td><td class="num">±{k.replace(".", ",")}%</td><td class="num">{f(r["cont"])}%</td><td class="num">{f(r["rev"])}%</td><td class="split"><span class="c" style="width:{r["cont"]}%"></span><span class="r" style="width:{r["rev"]}%"></span></td></tr>'
    for name, sd in (('Старый «голый» хай', 'hi'), ('Старый «голый» лой', 'lo')):
        for i, k in enumerate(('0.5', '1.0', '2.0')):
            r = o['old_race'][f'{sd}_{k}']
            body += f'<tr><td>{name + f" <small>n={r[chr(110)]}</small>" if i == 0 else ""}</td><td class="num">±{k.replace(".", ",")}%</td><td class="num">{f(r["cont"])}%</td><td class="num">{f(r["rev"])}%</td><td class="split"><span class="c" style="width:{r["cont"]}%"></span><span class="r" style="width:{r["rev"]}%"></span></td></tr>'
    return f'<div class="tw"><table>{head}{body}</table></div>'

base = T['all']
def trade_table(title, d, note=''):
    rows = ''
    for k, v in d.items():
        if not v['n']: continue
        small = v['n'] < 40
        def cell(key, better_high=True):
            val = v[key]; b = base[key]
            diff = (val - b) if better_high else (b - val)
            cls = '' if small or abs(diff) < 3 else (' up' if diff > 0 else ' down')
            return f'<td class="num{cls}">{f(val)}%</td>'
        ar = v['avgR']; cls = '' if small or abs(ar - base['avgR']) < 0.15 else (' up' if ar > base['avgR'] else ' down')
        rows += f'<tr{" class=small" if small else ""}><td>{e(k)}</td><td class="num">{v["n"]}</td>{cell("win")}{cell("sl", False)}{cell("tp2")}{cell("tp5")}<td class="num{cls}">{f(ar, 2)}</td></tr>'
    return f'''<h3>{title}</h3>{f"<p class=note>{note}</p>" if note else ""}<div class="tw"><table class="tt">
<tr><th>Группа</th><th>n</th><th>Win</th><th>SL</th><th>≥TP2</th><th>TP4 (5R)</th><th>Ср. R</th></tr>
<tr class="base"><td>Все сделки</td><td class="num">{base["n"]}</td><td class="num">{f(base["win"])}%</td><td class="num">{f(base["sl"])}%</td><td class="num">{f(base["tp2"])}%</td><td class="num">{f(base["tp5"])}%</td><td class="num">{f(base["avgR"], 2)}</td></tr>{rows}</table></div>'''

rv = o['revisit']
hz = ['1', '2', '4', '8', '13', '26', '52']
rv_rows = ''.join(f'<tr><td class="num">{h} нед.</td><td class="num">{f(rv["hi"][h])}%</td><td class="num">{f(rv["lo"][h])}%</td><td class="split"><span class="c1" style="width:{rv["hi"][h]/2}%"></span><span class="gap" style="width:{50 - rv["hi"][h]/2}%"></span><span class="c2" style="width:{rv["lo"][h]/2}%"></span></td></tr>' for h in hz)

comp = [('Сняли только PWH', S['only_hi'], 's1'), ('Сняли только PWL', S['only_lo'], 's2'), ('Сняли обе стороны', S['both'], 's3'), ('Inside week — ни одной', S['inside'], 's4')]
comp_bar = ''.join(f'<span class="{c}" style="width:{v}%" title="{e(l)}: {f(v)}%"></span>' for l, v, c in comp)
comp_leg = ''.join(f'<li><i class="sw {c}"></i><b>{f(v)}%</b> {e(l)}</li>' for l, v, c in comp)

page = f'''<title>Недельные экстремумы BTC</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Onest:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
:root{{--bg:#f4f6f8;--surface:#ffffff;--ink:#0f1720;--ink2:#4a5563;--muted:#7a8594;--line:#dfe4ea;--s1:#2a78d6;--s2:#eb6834;--s3:#4a3aa7;--s4:#b9c1cb;--up:#0b7a3e;--down:#c0342f;--upbg:#e3f4ea;--downbg:#fbe6e4;
--f:"Onest",system-ui,-apple-system,"Segoe UI",sans-serif;--m:"JetBrains Mono",ui-monospace,Menlo,Consolas,monospace}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{color-scheme:dark;--bg:#0f1318;--surface:#171c22;--ink:#eef2f6;--ink2:#b3bdc9;--muted:#8591a0;--line:#2a323c;--s1:#3987e5;--s2:#d95926;--s3:#9085e9;--s4:#4b5561;--up:#4cc27f;--down:#ef7a73;--upbg:#153324;--downbg:#3a1c1b}}}}
:root[data-theme="dark"]{{color-scheme:dark;--bg:#0f1318;--surface:#171c22;--ink:#eef2f6;--ink2:#b3bdc9;--muted:#8591a0;--line:#2a323c;--s1:#3987e5;--s2:#d95926;--s3:#9085e9;--s4:#4b5561;--up:#4cc27f;--down:#ef7a73;--upbg:#153324;--downbg:#3a1c1b}}
body{{background:var(--bg);color:var(--ink);font:15px/1.6 var(--f);padding-inline:16px;padding-block:32px 64px}}
main{{max-width:980px;margin:0 auto;display:grid;gap:40px}}
header{{display:grid;gap:10px}}
.eyebrow{{font:600 12px var(--m);letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}}
h1{{font-size:clamp(28px,5vw,42px);line-height:1.1;margin:0;text-wrap:balance;letter-spacing:-.01em}}
h2{{font-size:22px;margin:0 0 4px;text-wrap:balance}} h3{{font-size:16px;margin:24px 0 8px}}
p{{margin:0;max-width:68ch;color:var(--ink2)}} .lead{{font-size:17px}}
section{{display:grid;gap:14px}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px}}
.kpi{{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:14px 16px;display:grid;gap:4px}}
.kpi b{{font:600 28px var(--m);letter-spacing:-.02em}} .kpi span{{color:var(--ink2);font-size:13.5px;line-height:1.4}}
.panel{{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:18px}}
.comp{{display:flex;height:26px;gap:2px;border-radius:5px;overflow:hidden}} .comp span{{display:block}}
.s1{{background:var(--s1)}} .s2{{background:var(--s2)}} .s3{{background:var(--s3)}} .s4{{background:var(--s4)}}
ul.leg{{list-style:none;padding:0;margin:12px 0 0;display:flex;flex-wrap:wrap;gap:8px 20px;font-size:14px}} ul.leg b{{font-family:var(--m)}}
.sw{{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:6px;vertical-align:0}}
.grid2{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px}}
.chart{{margin:0;background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:16px;display:grid;gap:6px}}
figcaption{{font-weight:600}} .legend{{display:flex;gap:16px;font-size:13px;color:var(--ink2);margin-bottom:4px}}
.pb-row{{display:grid;grid-template-columns:28px 1fr;align-items:center;gap:8px}} .pb-lab{{font:13px var(--m);color:var(--ink2)}}
.pb-bars{{display:grid;grid-template-columns:1fr 52px;row-gap:2px;align-items:center}}
.bar{{height:9px;border-radius:0 3px 3px 0;min-width:2px}} .bv{{font:12px var(--m);color:var(--ink2);text-align:right}}
.tw{{overflow-x:auto;background:var(--surface);border:1px solid var(--line);border-radius:10px}}
table{{border-collapse:collapse;width:100%;font-size:14px;min-width:560px}}
th{{text-align:left;font:600 11.5px var(--m);letter-spacing:.05em;text-transform:uppercase;color:var(--muted);padding:10px 12px;border-bottom:1px solid var(--line)}}
td{{padding:8px 12px;border-bottom:1px solid var(--line)}} tr:last-child td{{border-bottom:0}}
.num{{font-family:var(--m);font-variant-numeric:tabular-nums;text-align:right;white-space:nowrap}} th:not(:first-child){{text-align:right}}
td.up{{color:var(--up);background:var(--upbg)}} td.down{{color:var(--down);background:var(--downbg)}}
tr.base td{{font-weight:600;background:color-mix(in srgb,var(--line) 35%,transparent)}} tr.small td{{color:var(--muted)}}
td small{{color:var(--muted);font-family:var(--m)}}
.split{{width:30%;min-width:120px}} .split span{{display:inline-block;height:8px;vertical-align:middle}}
.split .c,.split .c1{{background:var(--s1)}} .split .r,.split .c2{{background:var(--s2)}} .split .gap{{background:transparent}}
.note{{font-size:13.5px;color:var(--muted)}}
.take{{display:grid;gap:10px;padding:0;margin:0;list-style:none;counter-reset:t}}
.take li{{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:12px 14px;color:var(--ink2)}} .take li b{{color:var(--ink)}}
code{{font-family:var(--m);font-size:.9em}}
</style>
<main>
<header>
<div class="eyebrow">BTCUSDT · Binance spot · {o["period"][0]} — {o["period"][1]} · {o["weeks"]} недель · 863 сделки</div>
<h1>Как цена работает с хаями и лоями недельных свечей</h1>
<p class="lead">Неделя считается с понедельника 00:00 UTC. PWH/PWL — максимум и минимум прошлой недели. Котировки: 5-минутки Binance. Сделки распознаны со скриншотов репозитория (направление, вход, стоп, достигнутая цель) и сверены с котировками: все 863 входа попали в диапазон свечей.</p>
</header>

<section>
<h2>Главное</h2>
<div class="kpis">
<div class="kpi"><b>{f(S["hi_taken"])}%</b><span>недель обновляют хай прошлой недели</span></div>
<div class="kpi"><b>{f(S["lo_taken"])}%</b><span>недель обновляют лой прошлой недели</span></div>
<div class="kpi"><b>{f(S["both"])}%</b><span>недель снимают обе стороны. Сняли одну — вторую добирают лишь в {f(S["hi_first_then_lo"])}–{f(S["lo_first_then_hi"])}%</span></div>
<div class="kpi"><b>~50%</b><span>пробоев удерживаются к закрытию недели: выше PWH {f(S["hi_close_above"])}%, ниже PWL {f(S["lo_close_below"])}%</span></div>
</div>
<ol class="take">
<li><b>Уровень прошлой недели снимается рано.</b> Больше половины первых касаний PWH приходится на понедельник ({o["touch_dow"]["hi"][0]} из {sum(o["touch_dow"]["hi"])}). Если к утру пятницы уровень не тронут, шанс снять его до конца недели около {f(o["touch_cond"]["hi"][4])}% для хая и {f(o["touch_cond"]["lo"][4])}% для лоя.</li>
<li><b>Первое касание чаще продолжается, чем разворачивается.</b> После касания PWH цена в {f(S["h_race0.5"]["cont"])}% случаев сначала уходит ещё на 0,5% выше, и лишь в {f(S["h_race0.5"]["rev"])}% сначала откатывает на 0,5% вниз. По PWL картина та же. Типичный вынос за уровень — медиана {f(S["hi_ext_q"][1],2)}% над PWH и {f(S["lo_ext_q"][1],2)}% под PWL.</li>
<li><b>Недельные хаи возвращаются быстрее лоев.</b> Медиана до повторного касания: {f(rv["hi"]["median_weeks"],2)} нед. для хаев и {f(rv["lo"]["median_weeks"],2)} нед. для лоев. За 26 недель перебивают {f(rv["hi"]["26"])}% хаев и {f(rv["lo"]["26"])}% лоев. Лои, не тронутые полгода, почти не возвращаются: {rv["lo"]["never"]} из {rv["lo"]["n"]} остаются голыми до сих пор.</li>
<li><b>Для ваших сделок недельный уровень на пути к цели мешает.</b> Если хай/лой прошлой или текущей недели стоит в 1–2R от входа, винрейт {f(T["dist"]["1–2R"]["win"])}% (выборка {T["dist"]["1–2R"]["n"]}) против {f(base["win"])}% в среднем; при уровне в 2–5R до TP4 доходит только 24–27% сделок (209 сделок) против {f(T["dist"]["5–8R"]["tp5"])}%, когда уровень дальше 5R.</li>
<li><b>Свип, который впервые за неделю снимает PWL/PWH, — лучший сетап, но их мало.</b> 12 сделок: винрейт {f(T["pw_cat"]["Свип PWL/PWH — первое снятие за неделю"]["win"])}%, TP4 в {f(T["pw_cat"]["Свип PWL/PWH — первое снятие за неделю"]["tp5"])}%, ср. {f(T["pw_cat"]["Свип PWL/PWH — первое снятие за неделю"]["avgR"],2)}R. Входы, когда цена уже давно торгуется за уровнем, хуже среднего: {f(T["pw_cat"]["Цена уже торгуется за PWL/PWH"]["avgR"],2)}R.</li>
</ol>
</section>

<section>
<h2>1. Снятие уровней прошлой недели</h2>
<div class="panel"><div class="comp" role="img" aria-label="Структура недель">{comp_bar}</div><ul class="leg">{comp_leg}</ul></div>
<div class="tw"><table>
<tr><th>Метрика</th><th>PWH (хай)</th><th>PWL (лой)</th></tr>
<tr><td>Неделя сняла уровень</td><td class="num">{f(S["hi_taken"])}%</td><td class="num">{f(S["lo_taken"])}%</td></tr>
<tr><td>…и закрылась за уровнем (пробой принят)</td><td class="num">{f(S["hi_close_above"])}%</td><td class="num">{f(S["lo_close_below"])}%</td></tr>
<tr><td>…и закрылась обратно внутри (ложный пробой)</td><td class="num">{f(100-S["hi_close_above"])}%</td><td class="num">{f(100-S["lo_close_below"])}%</td></tr>
<tr><td>Вынос за уровень, квартили 25 / 50 / 75</td><td class="num">{" / ".join(f(x,2) for x in S["hi_ext_q"])}%</td><td class="num">{" / ".join(f(x,2) for x in S["lo_ext_q"])}%</td></tr>
<tr><td>После касания вернулась к середине прошлой недели</td><td class="num">{f(S["hi_mid"])}%</td><td class="num">{f(S["lo_mid"])}%</td></tr>
<tr><td>Сняли первой — затем в ту же неделю сняли и вторую сторону</td><td class="num">{f(S["hi_first_then_lo"])}%</td><td class="num">{f(S["lo_first_then_hi"])}%</td></tr>
</table></div>
<p class="note">Когда за неделю снимают обе стороны, хай снимается первым в {f(S["both_hi_first"])}% случаев.</p>
</section>

<section>
<h2>2. Реакция после первого касания</h2>
<p>Гонка в пределах 72 часов от первого касания: что наступит раньше — продолжение на N% за уровень или разворот на N% обратно. Для случайной точки обе стороны близки к 50/50.</p>
{race_table()}
<p class="note">Синим — продолжение, оранжевым — разворот. «Голые» уровни — хай/лой недели, который никто не перебивал как минимум неделю после её закрытия (то есть не PWH/PWL, а более старые уровни).</p>
</section>

<section>
<h2>3. Когда это происходит</h2>
<div class="grid2">
{pair_bars("Первое касание PWH / PWL, число недель", o["touch_dow"]["hi"], o["touch_dow"]["lo"], "PWH", "PWL", unit="")}
{pair_bars("В какой день ставится хай / лой недели, %", o["extreme_dow"]["hi"], o["extreme_dow"]["lo"])}
</div>
{pair_bars("Если к началу дня уровень ещё не тронут — шанс снять его до конца недели, %", o["touch_cond"]["hi"], o["touch_cond"]["lo"], "PWH", "PWL")}
</section>

<section>
<h2>4. Возврат к старым недельным экстремумам</h2>
<p>Доля недельных хаев и лоев, которые цена перебила в течение N недель после закрытия недели (учтены только уровни, у которых было хотя бы N недель).</p>
<div class="tw"><table><tr><th>Горизонт</th><th>Хай перебит</th><th>Лой перебит</th><th>Хай ← → лой</th></tr>{rv_rows}</table></div>
<p class="note">Асимметрия — следствие бычьего тренда BTC за период: 2020–2026 рост с ~7 тыс. до ~80–120 тыс.</p>
</section>

<section>
<h2>5. Сделки и недельные уровни</h2>
<p>Результат — максимальная цель со скриншота: SL = −1R, TP1 = 1R, TP2 = 2R, TP3 = 4R, TP4 = 5R. Средний R посчитан по этой шкале без учёта частичных фиксаций. Зелёным и красным отмечены отклонения от среднего (≥3 п.п., ≥0,15R) в группах от 40 сделок; серые строки — выборка меньше 40, это ориентир, не вывод.</p>
{trade_table("Свип и уровень прошлой недели", T["pw_cat"], "Свип — окно 3 часа до входа. Лонг смотрит на PWL, шорт на PWH.")}
{trade_table("Ближайший недельный экстремум на пути к цели", T["dist"], "Расстояние в R от входа до хая/лоя прошлой недели или уже поставленного экстремума текущей недели по направлению сделки.")}
{trade_table("Контекст недели на момент входа", T["ctx"])}
{trade_table("Позиция входа в диапазоне прошлой недели", T["pos"], "0% — уровень «своей» стороны (PWL для лонга, PWH для шорта), 100% — противоположный.")}
{trade_table("Свип обновил экстремум текущей недели", T["new_wk_ext"])}
{trade_table("Свип снял «голый» старый недельный экстремум", T["naked_swept"])}
{trade_table("День недели входа", T["dow"])}
</section>

<section>
<h2>Методика</h2>
<p>Данные: 5-минутные свечи BTCUSDT с data.binance.vision, время UTC; время на скриншотах с ним совпадает. Сделки распознаны OCR из заголовков и подписей уровней на графиках, пять нечитаемых графиков разобраны вручную. Разница в 3–5 п.п. винрейта на группах в 100–300 сделок лежит в пределах статистического шума (±4–6 п.п.), поэтому уверенно можно говорить только о крупных отклонениях. Скрипты и таблица всех сделок с признаками лежат в папке <code>weekly_levels/</code> репозитория.</p>
</section>
</main>'''
open(f'{D}/report.html', 'w').write(page)
print('ok')
