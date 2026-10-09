"""Графики глубины отката: python retrace_fig.py <retrace_curve.json> <out.html>"""
import sys, json, numpy as np
from svg import grouped_bars, curves, text, C
J = json.load(open(sys.argv[1]))
GR = list(np.round(np.arange(.1, .96, .05), 3))
def hist_fig(k, title):
    j = J[k]; labels = [(f'{i*0.05:.1f}' if i % 2 == 0 else '') for i in range(20)]
    return grouped_bars(labels, [('факт', 'real', [100 * v for v in j['hist']]), ('контроль', 'ctrl', [100 * v for v in j['hist_c']])], ymax=10, h=290, title=title, fmt='{:.0f}')
def curve_fig(k, title):
    j = J[k]; X, Y, Yc = [], [], []
    for x, y, n, c in zip(GR, j['curve'], j['curve_n'], j['curve_c']):
        if y == y and n >= 10: X.append(x); Y.append(y); Yc.append(c)
    s = curves(X, [('факт', 'real', Y, 2.6), ('контроль', 'ctrl', Yc, 2)], title=title, xlabel='насколько глубоко откатила цена (доля диапазона ножки)', diag=False)
    px = lambda x: 46 + x * 700; py = lambda v: 34 + (1 - v) * 226
    extra = [f'<line x1="{px(.2)}" y1="{py(.8)}" x2="{px(.95)}" y2="{py(.05)}" stroke="{C["muted"]}" stroke-dasharray="3 3"/>',
             f'<line x1="{px(.5)}" y1="34" x2="{px(.5)}" y2="260" stroke="{C["down"]}" stroke-dasharray="5 4"/>', text(px(.5) + 6, 48, 'граница 0,5', 10.5, C['down'], weight=700),
             f'<line x1="{px(.79)}" y1="34" x2="{px(.79)}" y2="260" stroke="{C["zone"]}" stroke-dasharray="5 4"/>', text(px(.79) + 6, 48, '0,79', 10.5, C['zone'], weight=700),
             f'<line x1="46" y1="{py(.5)}" x2="746" y2="{py(.5)}" stroke="{C["line"]}"/>', text(px(.66), py(.25), 'пунктир — случайное блуждание', 10, C['muted'], italic=True)]
    return s.replace('</svg>', ''.join(extra) + '</svg>')
html = f'''<!doctype html><html><head><meta charset="utf-8"><style>body{{margin:0;padding:18px;background:#fff;font:14px 'Liberation Sans',sans-serif;color:#16202b;width:780px}}h2{{margin:6px 0 4px;font-size:17px}}p{{margin:0 0 8px;color:#4a5562;font-size:12.5px}}svg{{border:1px solid #d9dee4;border-radius:6px;margin-bottom:12px}}</style></head><body>
<h2>Откуда стартует реакция на обновление хая</h2><p>Недельные ножки от 3-свечного фрактала до фрактала, альты: {J['W_alts']['n']} ножек, обновивших хай. Столбик — доля ножек, у которых самый глубокий откат перед обновлением хая попал в эту корзину (шаг 0,05).</p>
{hist_fig('W_alts', 'Неделя, альты: глубина отката перед обновлением хая, %')}
<h2>Граница отката: шанс обновить хай раньше слома лоя</h2><p>Если откат уже дошёл до уровня (считается после подтверждения фрактала).</p>
{curve_fig('W_alts', 'Неделя, альты')}
{curve_fig('D_all', 'День, 9 монет ({} ножек)'.format(J['D_all']['legs']))}
</body></html>'''
open(sys.argv[2], 'w').write(html)
