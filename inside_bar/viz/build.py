"""Собирает eth_short_cases.html: python viz_data.py ... cases.json && python viz/build.py cases.json eth_short_cases.html"""
import sys, os
D = os.path.dirname(os.path.abspath(__file__))
data = open(sys.argv[1]).read()
html = open(f'{D}/head.html').read() + open(f'{D}/body.html').read().replace('__DATA__', data)
open(sys.argv[2], 'w').write(html); print('ok', len(html))
