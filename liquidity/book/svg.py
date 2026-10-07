"""Мини-библиотека SVG для методички: свечи с уровнями, сгруппированные столбики, кривые, схемы."""
import html
C = dict(ink='#16202b', ink2='#4a5562', muted='#8a94a0', line='#d9dee4', grid='#eef1f4', real='#1f5fbf', ctrl='#a9b3bf',
         up='#178066', down='#c4443a', zone='#c98a12', accent='#7a4fc9', paper='#ffffff', soft='#f4f6f8')
def esc(s): return html.escape(str(s))
def text(x, y, s, size=11, color=None, anchor='start', weight=400, family='sans', italic=False):
    fam = "'Liberation Sans','DejaVu Sans',sans-serif" if family == 'sans' else "'DejaVu Sans Mono',monospace"
    st = ' font-style="italic"' if italic else ''
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{color or C["ink"]}" text-anchor="{anchor}" font-weight="{weight}" font-family="{fam}"{st}>{esc(s)}</text>'
def svg(w, h, body): return f'<svg viewBox="0 0 {w} {h}" width="100%" xmlns="http://www.w3.org/2000/svg" role="img">{body}</svg>'

def candles(bars, levels, w=760, h=330, title=None, date_fmt=None, marks=()):
    """bars: [(label, o,h,l,c)], levels: [(price, label, color, dash)]"""
    pl, pr, pt, pb = 12, 150, 26 if title else 10, 26
    lo = min(min(b[3] for b in bars), min(l[0] for l in levels)); hi = max(max(b[2] for b in bars), max(l[0] for l in levels))
    pad = (hi - lo) * .05; lo -= pad; hi += pad
    X = lambda i: pl + (i + .5) * (w - pl - pr) / len(bars)
    Y = lambda p: pt + (hi - p) / (hi - lo) * (h - pt - pb)
    bw = max(2, (w - pl - pr) / len(bars) * .62)
    o = [f'<rect width="{w}" height="{h}" fill="{C["paper"]}"/>']
    if title: o.append(text(pl, 16, title, 12, C['ink2'], weight=700))
    for k in range(5):
        p = lo + (hi - lo) * k / 4
        o.append(f'<line x1="{pl}" x2="{w-pr}" y1="{Y(p):.1f}" y2="{Y(p):.1f}" stroke="{C["grid"]}"/>')
    for i, (lab, op, hh, ll, cl) in enumerate(bars):
        col = C['up'] if cl >= op else C['down']
        o.append(f'<line x1="{X(i):.1f}" x2="{X(i):.1f}" y1="{Y(hh):.1f}" y2="{Y(ll):.1f}" stroke="{col}" stroke-width="1.2"/>')
        y1, y2 = sorted((Y(op), Y(cl)))
        o.append(f'<rect x="{X(i)-bw/2:.1f}" y="{y1:.1f}" width="{bw:.1f}" height="{max(1, y2-y1):.1f}" fill="{col}"/>')
        if lab and (i % max(1, len(bars) // 8) == 0): o.append(text(X(i), h - 8, lab, 9.5, C['muted'], 'middle'))
    used = []
    for p, lab, col, dash in sorted(levels, key=lambda z: -z[0]):
        y = Y(p); ty = y + 3.5
        for u in used:
            if abs(ty - u) < 11: ty = u + 11
        used.append(ty)
        da = ' stroke-dasharray="5 4"' if dash else ''
        o.append(f'<line x1="{pl}" x2="{w-pr+4}" y1="{y:.1f}" y2="{y:.1f}" stroke="{C[col]}" stroke-width="1.3"{da}/>')
        o.append(text(w - pr + 8, ty, f'{lab} {p:,.0f}'.replace(',', ' '), 10, C[col], weight=600))
    for i, s, col in marks:
        o.append(text(X(i), pt + 10, s, 10, C[col], 'middle', 700))
    return svg(w, h, ''.join(o))

def grouped_bars(groups, series, w=760, h=300, ymax=100, ylabel='%', ref=None, title=None, fmt='{:.0f}%'):
    """groups: [label], series: [(name, color, [values])]; ref: (value, label) горизонтальная линия — в легенде"""
    pl, pr, pb = 40, 10, 46
    pt = 52 if title else 34
    n, k = len(groups), len(series)
    gw = (w - pl - pr) / n; bw = gw * .7 / k
    Y = lambda v: pt + (1 - v / ymax) * (h - pt - pb)
    o = [f'<rect width="{w}" height="{h}" fill="{C["paper"]}"/>']
    if title: o.append(text(pl - 28, 16, title, 12, C['ink2'], weight=700))
    for t in range(0, ymax + 1, 25 if ymax >= 75 else 10):
        o.append(f'<line x1="{pl}" x2="{w-pr}" y1="{Y(t):.1f}" y2="{Y(t):.1f}" stroke="{C["grid"]}"/>' + text(pl - 6, Y(t) + 4, t, 9.5, C['muted'], 'end'))
    if ref:
        o.append(f'<line x1="{pl}" x2="{w-pr}" y1="{Y(ref[0]):.1f}" y2="{Y(ref[0]):.1f}" stroke="{C["down"]}" stroke-dasharray="4 3"/>')
    for gi, g in enumerate(groups):
        x0 = pl + gi * gw + gw * .15
        for si, (nm, col, vals) in enumerate(series):
            v = vals[gi]
            if v is None: continue
            x = x0 + si * bw
            o.append(f'<rect x="{x:.1f}" y="{Y(v):.1f}" width="{bw-2:.1f}" height="{Y(0)-Y(v):.1f}" fill="{C[col]}" rx="1.5"/>')
            o.append(text(x + (bw - 2) / 2, Y(v) - 4, fmt.format(v), 9.5, C['ink2'], 'middle', 600))
        for li, ln in enumerate(g.split('\n')):
            o.append(text(pl + gi * gw + gw / 2, h - pb + 16 + li * 12, ln, 10, C['ink2'], 'middle'))
    lx, ly = pl - 28, (34 if title else 14)
    for nm, col, _ in series:
        o.append(f'<rect x="{lx}" y="{ly-9}" width="10" height="10" fill="{C[col]}" rx="2"/>' + text(lx + 14, ly, nm, 10.5, C['ink2'])); lx += 7 * len(nm) + 40
    if ref:
        o.append(f'<line x1="{lx}" x2="{lx+16}" y1="{ly-4}" y2="{ly-4}" stroke="{C["down"]}" stroke-dasharray="4 3"/>' + text(lx + 22, ly, ref[1], 10.5, C['down']))
    return svg(w, h, ''.join(o))

def curves(xs, series, w=760, h=300, xlabel='', ylabel='', title=None, diag=True):
    pl, pr, pt, pb = 46, 14, 34 if title else 18, 40
    X = lambda v: pl + v * (w - pl - pr); Y = lambda v: pt + (1 - v) * (h - pt - pb)
    o = [f'<rect width="{w}" height="{h}" fill="{C["paper"]}"/>']
    if title: o.append(text(pl, 16, title, 12, C['ink2'], weight=700))
    for t in (0, .25, .5, .75, 1):
        o.append(f'<line x1="{pl}" x2="{w-pr}" y1="{Y(t):.1f}" y2="{Y(t):.1f}" stroke="{C["grid"]}"/>' + text(pl - 6, Y(t) + 4, f'{t*100:.0f}%', 9.5, C['muted'], 'end'))
        o.append(text(X(t), h - pb + 14, f'{t*100:.0f}%', 9.5, C['muted'], 'middle'))
    if diag: o.append(f'<line x1="{X(0)}" y1="{Y(0)}" x2="{X(1)}" y2="{Y(1)}" stroke="{C["muted"]}" stroke-dasharray="3 3"/>')
    o.append(text((pl + w - pr) / 2, h - 6, xlabel, 10.5, C['ink2'], 'middle'))
    for nm, col, ys, wd in series:
        pts = ' '.join(f'{X(x):.1f},{Y(y):.1f}' for x, y in zip(xs, ys))
        o.append(f'<polyline points="{pts}" fill="none" stroke="{C[col]}" stroke-width="{wd}"/>')
        o.extend(f'<circle cx="{X(x):.1f}" cy="{Y(y):.1f}" r="3.2" fill="{C[col]}"/>' for x, y in zip(xs, ys))
    lx = pl + 10; ly = pt + 8
    for nm, col, _, _ in series:
        o.append(f'<rect x="{lx}" y="{ly}" width="14" height="3" fill="{C[col]}"/>' + text(lx + 20, ly + 5, nm, 10.5, C['ink2'])); ly += 16
    return svg(w, h, ''.join(o))

def box(x, y, w, h, title, sub='', fill=None, stroke=None, tcol=None, size=12):
    o = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="7" fill="{fill or C["soft"]}" stroke="{stroke or C["line"]}" stroke-width="1.2"/>'
    o += text(x + w / 2, y + (h / 2 if not sub else h / 2 - 5) + 4, title, size, tcol or C['ink'], 'middle', 700)
    if sub:
        for i, s in enumerate(sub.split('\n')):
            o += text(x + w / 2, y + h / 2 + 12 + i * 12, s, 10, C['ink2'], 'middle')
    return o
def arrow(x1, y1, x2, y2, col=None, label=None):
    col = col or C['muted']
    o = f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{col}" stroke-width="1.5" marker-end="url(#ah)"/>'
    if label: o += text((x1 + x2) / 2 + 6, (y1 + y2) / 2 + 4, label, 10, C['ink2'])
    return o
DEFS = f'<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{C["muted"]}"/></marker></defs>'
