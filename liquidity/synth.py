"""Синтетический контроль: перемешиваем дни (блоки по 96 свечей 15m) в случайном порядке, цепляя относительно прошлого close.
Волатильность, внутридневная форма и общий дрейф сохраняются, реальные уровни/структура — нет.
python synth.py <src_dir> <out_dir> <seed> [SYM ...]"""
import sys, os, numpy as np, pandas as pd
SRC, OUT, SEED = sys.argv[1], sys.argv[2], int(sys.argv[3])
SYMS = sys.argv[4:] or ['ETHUSDT', 'BTCUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'LTCUSDT', 'LINKUSDT']
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(SEED)
for s in SYMS:
    m = pd.read_pickle(f'{SRC}/{s}.pkl')[['o', 'h', 'l', 'c']]
    pc = m.c.shift(1).fillna(m.o).values
    rel = np.log(m[['o', 'h', 'l', 'c']].values / pc[:, None])          # всё относительно прошлого close
    n = len(m) // 96 * 96; blocks = rel[:n].reshape(-1, 96, 4)
    sh = blocks[rng.permutation(len(blocks))].reshape(-1, 4)
    lc = np.cumsum(sh[:, 3]); prev = np.concatenate([[0], lc[:-1]])
    px = m.o.values[0] * np.exp(prev[:, None] + sh)
    pd.DataFrame(px, index=m.index[:n], columns=['o', 'h', 'l', 'c']).to_pickle(f'{OUT}/{s}.pkl')
