# Взаимодействие цены с хаями/лоями недельных свечей (BTCUSDT)

Статистика по 338 неделям (2020-01-06 … 2026-08-30) и связь недельных уровней с 863 сделками со скриншотов в корне репозитория.

- `report.html` — отчёт с выводами и таблицами
- `results.json` — все посчитанные цифры
- `trades_weekly.csv` — каждая сделка с признаками: результат (R), позиция в диапазоне прошлой недели, свип PWH/PWL, расстояние до ближайшего недельного экстремума в R и т.д.

Воспроизвести (нужны `pandas`, `pillow`, `tesseract`):

```bash
python fetch_data.py data          # 5m свечи Binance -> data/m5.pkl
OMP_THREAD_LIMIT=1 python ocr_trades.py data   # скриншоты -> data/trades.pkl
python analysis.py data            # -> data/results.json, data/trades_weekly.csv
python build_report.py data        # -> data/report.html
```

Неделя = понедельник 00:00 UTC. PWH/PWL — хай/лой прошлой недели. Результат сделки — максимальная достигнутая цель со скриншота: SL = −1R, TP1 = 1R, TP2 = 2R, TP3 = 4R, TP4 = 5R.
