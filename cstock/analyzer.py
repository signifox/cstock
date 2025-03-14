import pandas as pd
import backtrader as bt
import numpy as np


class Analyzer:
    def __init__(self, backtest_engine):
        """
        Initialize result analyzer

        Parameters:
            backtest_engine: Backtest engine instance
        """
        self.backtest_engine = backtest_engine
        self.analysis = self._get_analysis()

    def _get_analysis(self):
        """Get backtest analysis results"""
        if not hasattr(self.backtest_engine, "strategy_instance"):
            raise ValueError("Please run backtest first")

        # Get analysis results
        sharpe = self.backtest_engine.strategy_instance.analyzers.sharpe.get_analysis()
        trade_analyzer = (
            self.backtest_engine.strategy_instance.analyzers.trade.get_analysis()
        )

        returns = (
            self.backtest_engine.strategy_instance.analyzers.returns.get_analysis()
        )
        drawdown = (
            self.backtest_engine.strategy_instance.analyzers.drawdown.get_analysis()
        )

        # Get backtest period
        data = self.backtest_engine.strategy_instance.datas[0]
        start_date = bt.num2date(data.datetime.array[0])
        end_date = bt.num2date(data.datetime.array[-1])
        days = (end_date - start_date).days

        # Get trading statistics
        total_profit = returns.get("rtot", 0.0) * self.backtest_engine.initial_cash
        total_return = returns.get("rtot", 0.0)
        annual_return = returns.get("rnorm", 0.0)  # Use backtrader's annualized return

        analysis = {
            "Total Profit": total_profit,
            "Start Date": start_date.strftime("%Y-%m-%d"),
            "End Date": end_date.strftime("%Y-%m-%d"),
            "Backtest Days": days,
            "Sharpe Ratio": sharpe.get("sharperatio", 0.0),
            "Max Drawdown": drawdown.get("max", {}).get("drawdown", 0.0),
            "Max Drawdown Period": drawdown.get("max", {}).get("len", 0),
            "Total Return": total_return,
            "Annual Return": annual_return,
            "Total Trades": trade_analyzer.get("total", {}).get("total", 0),
            "Winning Trades": trade_analyzer.get("won", {}).get("total", 0),
            "Losing Trades": trade_analyzer.get("lost", {}).get("total", 0),
            "Win Rate": (
                trade_analyzer.get("won", {}).get("total", 0)
                / trade_analyzer.get("total", {}).get("total", 1)
                if trade_analyzer.get("total", {}).get("total", 0) > 0
                else 0.0
            ),
            "Average Trade Profit": trade_analyzer.get("pnl", {})
            .get("net", {})
            .get("average", 0.0),
            "Max Single Win": trade_analyzer.get("won", {})
            .get("pnl", {})
            .get("max", 0.0),
            "Max Single Loss": abs(
                trade_analyzer.get("lost", {}).get("pnl", {}).get("max", 0.0)
            ),
        }
        return analysis

    def print_summary(self):
        print("\n=== Backtest Results Summary ===\n")
        for key, value in self.analysis.items():
            if isinstance(value, float):
                print(f"{key}: {value:.2%}" if "Rate" in key else f"{key}: {value:.2f}")
            else:
                print(f"{key}: {value}")

    def plot_results(self):
        """Plot backtest result charts"""
        self.backtest_engine.cerebro.plot(style="candlestick")
