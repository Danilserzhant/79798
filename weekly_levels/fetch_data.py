"""Скачивает 5m свечи BTCUSDT (Binance spot, UTC) с data.binance.vision и сохраняет m5.pkl.
python fetch_data.py <dir> [последний месяц YYYY-MM]"""
import io, sys, zipfile, urllib.request
import pandas as pd
D = sys.argv[1] if len(sys.argv) > 1 else '.'
last = sys.argv[2] if len(sys.argv) > 2 else '2026-08'
dfs = []
for p in pd.period_range('2019-12', last, freq='M'):
    url = f'https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/5m/BTCUSDT-5m-{p}.zip'
    z = zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(url).read()))
    d = pd.read_csv(z.open(z.namelist()[0]), header=None, usecols=[0, 1, 2, 3, 4])
    d = d[pd.to_numeric(d[0], errors='coerce').notna()].astype(float)
    t = d[0].astype('int64'); t = t.where(t < 1e14, t // 1000)   # с 2025 года метки в микросекундах
    d.index = pd.to_datetime(t, unit='ms'); d = d[[1, 2, 3, 4]]; d.columns = ['o', 'h', 'l', 'c']
    dfs.append(d)
df = pd.concat(dfs).sort_index(); df = df[~df.index.duplicated()]
df.to_pickle(f'{D}/m5.pkl'); print(df.index[0], df.index[-1], len(df))
