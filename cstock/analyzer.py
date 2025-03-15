import pandas as pd
import backtrader as bt
import numpy as np
from datetime import datetime


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
        sqn = self.backtest_engine.strategy_instance.analyzers.sqn.get_analysis()
        annual_returns = (
            self.backtest_engine.strategy_instance.analyzers.annual_return.get_analysis()
        )
        vwr = self.backtest_engine.strategy_instance.analyzers.vwr.get_analysis()

        # Get backtest period
        data = self.backtest_engine.strategy_instance.datas[0]
        start_date = bt.num2date(data.datetime.array[0])
        end_date = bt.num2date(data.datetime.array[-1])
        days = (end_date - start_date).days

        # Get trading statistics
        total_profit = returns.get("rtot", 0.0) * self.backtest_engine.initial_cash
        total_return = returns.get("rtot", 0.0)
        annual_return = returns.get("rnorm", 0.0)  # Use backtrader's annualized return

        # Get streak information
        streak_won_longest = (
            trade_analyzer.get("streak", {}).get("won", {}).get("longest", 0)
        )
        streak_lost_longest = (
            trade_analyzer.get("streak", {}).get("lost", {}).get("longest", 0)
        )
        open_trades = trade_analyzer.get("total", {}).get("open", 0)

        analysis = {
            "Total Profit": total_profit,
            "Open Positions": open_trades,
            "Start Date": start_date.strftime("%Y-%m-%d"),
            "End Date": end_date.strftime("%Y-%m-%d"),
            "Backtest Days": days,
            "Annual Returns": annual_returns,  # Add annual returns data
            "Sharpe Ratio": sharpe.get("sharperatio", 0.0),
            "VWR Score": vwr.get("vwr", 0.0),
            "Max Drawdown": drawdown.get("max", {}).get("drawdown", 0.0),
            "Max Drawdown Period": drawdown.get("max", {}).get("len", 0),
            "SQN Score": sqn.get("sqn", 0.0),
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
            "Longest Winning Streak": streak_won_longest,
            "Longest Losing Streak": streak_lost_longest,
        }
        return analysis

    def print_summary(self):
        print("\n=== Backtest Results Summary ===\n")
        format_str = "  {:<24} : {:<24}"

        # Print basic statistics
        print("Basic Statistics:")
        for key, value in self.analysis.items():
            if key == "Annual Returns":
                continue
            elif isinstance(value, float):
                if "Rate" in key or key in [
                    "Total Return",
                    "Annual Return",
                    "Max Drawdown",
                ]:
                    formatted_value = f"{value:.2%}"
                elif "Profit" in key or "Loss" in key:
                    formatted_value = f"${value:.2f}"
                else:
                    formatted_value = f"{value:.2f}"
            else:
                formatted_value = str(value)
            print(format_str.format(key, formatted_value))

        # Print annual returns
        if "Annual Returns" in self.analysis:
            print("\nAnnual Returns:")
            for year, ret in self.analysis["Annual Returns"].items():
                print(format_str.format(str(year), f"{ret:.2%}"))

        # Print transactions if available
        if hasattr(self.backtest_engine.strategy_instance.analyzers, "transactions"):
            print("\nTransactions:")
            txn_format = "  {:<24} {:<12} {:<10} {:<8} {:<16}"
            print(txn_format.format("Date", "Amount", "Price", "Type", "Value"))

            transactions = (
                self.backtest_engine.strategy_instance.analyzers.transactions.get_analysis()
            )
            for date, txns in transactions.items():
                for txn in txns:
                    txn_type = "BUY" if txn[0] > 0 else "SELL"
                    print(
                        txn_format.format(
                            date.strftime("%Y-%m-%d %H:%M:%S"),
                            f"{abs(txn[0]):.0f}",
                            f"${txn[1]:.2f}",
                            txn_type,
                            f"${abs(txn[0] * txn[1]):.2f}",
                        )
                    )

    def plot_results(self):
        """Plot backtest result charts"""
        self.backtest_engine.cerebro.plot(style="candlestick")
