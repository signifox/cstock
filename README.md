# Stock Market Framework Tester (SMFT)

A Python-based quantitative trading backtesting framework for testing and evaluating different trading strategies.

## Features
- Built-in SMA Crossover Strategy

## Project Structure
```
- cstock/            # Core code directory
  - strategies/      # Trading strategies
  - analyzer.py      # Analysis module
  - backtest_engine.py # Backtest engine
  - data_fetcher.py  # Data fetcher
  - risk_manager.py  # Risk manager
- main.py            # Main program
```

## Getting Started

1. Install dependencies:
```bash
pip install backtrader pandas numpy matplotlib
```

2. Run backtest:
```bash
python main.py
```