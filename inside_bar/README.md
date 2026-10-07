# Недельные инсайд-бары: снятие стороны и подтверждения (Binance USDT-M perp)

Повод: ETHUSDT, неделя 28.09.2026 — инсайд внутри недели 21.09; 07.10 снят его лой (2634) и лой матери (2626).

- `report.html` — отчёт: текущая картина, вероятности из текущего состояния, сравнение подтверждений
- `results/now.json`, `results/now_cases.csv` — вероятности и случаи, похожие на текущий
- `results/events.csv` — все снятия стороны недельного IB (9 монет, 2020–2026)
- `results/conf_*.csv`, `results/trades_*.csv` — подтверждения D1/H4/H1/M15 и все сделки

```bash
python ib_study.py <dir_with_SYMBOL.pkl> out            # от первого снятия
python ib_study.py <dir_with_SYMBOL.pkl> out_state 0.476 # от текущего состояния (вынос ≥0,476R, мать снята)
python ib_now.py <dir_with_SYMBOL.pkl> out/events.csv 0.476 out/now.json
python conf_stats.py out/trades.csv out/conf.pkl
python build_report.py                                    # из results/
```
15m свечи: data.binance.vision `futures/um/{monthly,daily}/klines/<SYM>/15m` (загрузка аналогична `weekly_levels/fetch_data.py`).
