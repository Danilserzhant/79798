"""Правило направления недели на закрытие вторника (UTC). python week_rule.py <week_early.csv> <s1,s2,s3> <out_txt>
МЕДВЕДЬ, если: прошлая неделя «обе сняты» ИЛИ (пн–вт сняли хай прошлой недели, но не лой, и к концу вт цена ниже открытия недели)
              ИЛИ (вт закрылся ниже лоя пн).
БЫК, если (не медведь): пн снял лой прошлой недели, а хай — нет ИЛИ вт — инсайд пн при открытии недели в нижней половине прошлой."""
import sys, numpy as np, pandas as pd
R = pd.read_csv(sys.argv[1], parse_dates=['t']); Ss = [pd.read_csv(f, parse_dates=['t']) for f in sys.argv[2].split(',')]; OUT = sys.argv[3]
def prep(d):
    d = d[d.dp == 'tue'].copy()
    for c in ('rest_up', 'took_PH', 'took_PL', 'above_open', 'mon_took_PL', 'mon_took_PH', 'tue_close_below_ml', 'tue_broke_mh', 'tue_broke_ml'):
        d[c] = d[c].map({True: 1.0, False: 0.0, 'True': 1.0, 'False': 0.0})
    bear = (d.prev_state == 'обе сняты') | ((d.took_PH == 1) & (d.took_PL == 0) & (d.above_open == 0)) | (d.tue_close_below_ml == 1)
    bull = ~bear & (((d.mon_took_PL == 1) & (d.mon_took_PH == 0)) | ((d.tue_broke_mh == 0) & (d.tue_broke_ml == 0) & (d.open_pos < .5)))
    d['sig'] = np.where(bear, 'МЕДВЕДЬ', np.where(bull, 'БЫК', 'нет сигнала'))
    return d
R = prep(R); Ss = [prep(s) for s in Ss]
half = R.t.sort_values().iloc[len(R) // 2]; MAJ = ['BTCUSDT', 'ETHUSDT']
pc = lambda v: f'{100*v:3.0f}%'
L = [f'Недель {len(R)} (9 монет). Цели от закрытия вторника. Для «МЕДВЕДЬ» показано, как часто цена шла ВНИЗ.']
for sg in ('МЕДВЕДЬ', 'БЫК', 'нет сигнала'):
    x = R[R.sig == sg]; cs = [s[s.sig == sg] for s in Ss]; inv = sg == 'МЕДВЕДЬ'
    def v(d, col): q = d[col].dropna(); return (1 - q.mean()) if inv else q.mean()
    line = f'{sg:12s} недель {len(x):4d} ({pc(len(x)/len(R))}) |'
    for col, nm in (('rest_up', 'до конца недели'), ('exp_up', 'первым пробит край пн–вт'), ('atr_up', '1 ATR раньше')):
        line += f' {nm} в сторону сигнала {pc(v(x, col))} (контроль {pc(np.mean([v(c, col) for c in cs]))}) |'
    L.append(line)
    if sg != 'нет сигнала':
        L.append(f'      по половинам (до конца недели): {pc(v(x[x.t < half], "rest_up"))} / {pc(v(x[x.t >= half], "rest_up"))} | BTC+ETH {pc(v(x[x.sym.isin(MAJ)], "rest_up"))}, альты {pc(v(x[~x.sym.isin(MAJ)], "rest_up"))} | '
                 f'1 ATR: BTC+ETH {pc(v(x[x.sym.isin(MAJ)], "atr_up"))}, альты {pc(v(x[~x.sym.isin(MAJ)], "atr_up"))}')
txt = '\n'.join(L); print(txt); open(OUT, 'w').write(txt + '\n')
