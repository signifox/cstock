import pandas as pd
import backtrader as bt
import numpy as np
import quantstats as qs
from datetime import datetime
from cstock.config import config


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

        # 基础统计信息
        print("基础统计信息:")
        basic_stats = [
            "Total Profit",
            "Start Date",
            "End Date",
            "Backtest Days",
            "Total Return",
            "Annual Return",
        ]
        for key in basic_stats:
            value = self.analysis.get(key)
            if isinstance(value, float):
                if key in ["Total Return", "Annual Return"]:
                    formatted_value = f"{value:.2%}"
                elif "Profit" in key:
                    formatted_value = f"${value:.2f}"
                else:
                    formatted_value = f"{value:.2f}"
            else:
                formatted_value = str(value)
            print(format_str.format(key, formatted_value))

        # 风险指标
        print("\n风险指标:")
        risk_stats = [
            "Sharpe Ratio",
            "VWR Score",
            "Max Drawdown",
            "Max Drawdown Period",
            "SQN Score",
        ]
        for key in risk_stats:
            value = self.analysis.get(key)
            if isinstance(value, float):
                if key == "Max Drawdown":
                    formatted_value = f"{value:.2%}"
                else:
                    formatted_value = f"{value:.2f}"
            else:
                formatted_value = str(value)
            print(format_str.format(key, formatted_value))

        # 交易统计
        print("\n交易统计:")
        trade_stats = [
            "Total Trades",
            "Winning Trades",
            "Losing Trades",
            "Win Rate",
            "Average Trade Profit",
            "Max Single Win",
            "Max Single Loss",
            "Open Positions",
        ]
        for key in trade_stats:
            value = self.analysis.get(key)
            if isinstance(value, float):
                if key == "Win Rate":
                    formatted_value = f"{value:.2%}"
                elif "Profit" in key or "Loss" in key or "Win" in key:
                    formatted_value = f"${value:.2f}"
                else:
                    formatted_value = f"{value:.2f}"
            else:
                formatted_value = str(value)
            print(format_str.format(key, formatted_value))

        # 连续交易记录
        print("\n连续交易记录:")
        streak_stats = ["Longest Winning Streak", "Longest Losing Streak"]
        for key in streak_stats:
            value = self.analysis.get(key)
            print(format_str.format(key, str(value)))

        # Print annual returns
        if "Annual Returns" in self.analysis:
            print("\n年度收益:")
            for year, ret in self.analysis["Annual Returns"].items():
                print(format_str.format(str(year), f"{ret:.2%}"))

        # Print transactions if enabled and available
        if config.SHOW_TRANSACTIONS and hasattr(
            self.backtest_engine.strategy_instance.analyzers, "transactions"
        ):
            print("\n交易记录:")
            txn_format = "  {:<24} {:<8} {:<12} {:<10} {:<8} {:<16} {:<10} {:<16}"
            print(
                txn_format.format(
                    "Date",
                    "Symbol",
                    "Amount",
                    "Price",
                    "Type",
                    "Value",
                    "Commission",
                    "Profit",
                )
            )

            transactions = (
                self.backtest_engine.strategy_instance.analyzers.transactions.get_analysis()
            )
            for date, txns in transactions.items():
                for txn in txns:
                    # txn_type = "买入" if txn[0] > 0 else "卖出"
                    txn_type = "BUY" if txn[0] > 0 else "SELL"
                    amount = abs(txn[0])
                    price = txn[1]
                    value = amount * price
                    commission = value * self.backtest_engine.commission
                    profit = -value - commission if txn[0] > 0 else value - commission
                    symbol = txn[3] if len(txn) > 3 else "Unknown"

                    print(
                        txn_format.format(
                            date.strftime("%Y-%m-%d %H:%M:%S"),
                            symbol,
                            f"{amount:.0f}",
                            f"${price:.2f}",
                            txn_type,
                            f"${value:.2f}",
                            f"${commission:.2f}",
                            f"${profit:.2f}",
                        )
                    )

    def _generate_report(self):
        """
        Generate performance report by processing portfolio values and benchmark data
        Returns:
            str: Path to the generated report
        """
        # Get portfolio values
        portfolio_values = (
            self.backtest_engine.strategy_instance.analyzers.portfolio_value.get_analysis()
        )
        df = pd.Series(portfolio_values, name="portfolio_value")
        df.index = pd.to_datetime(df.index)

        # Calculate daily returns
        returns = pd.Series(df.pct_change(), dtype="float64").dropna()
        returns.index = pd.to_datetime(returns.index)
        returns = returns.resample("D").last().dropna()  # Add aggregation function
        # Get benchmark data from data_dict
        benchmark = None
        if "SPY" in self.backtest_engine.data_dict:
            try:
                benchmark_data = self.backtest_engine.data_dict["SPY"]
                benchmark = benchmark_data["Close"].pct_change()
                benchmark.index = pd.to_datetime(benchmark.index)
                benchmark = (
                    benchmark.resample("D").last().dropna()
                )  # Consistent processing
                benchmark = benchmark.reindex(returns.index, method="ffill")
                benchmark.name = "SPY"
            except Exception as e:
                print(f"Error processing benchmark data: {str(e)}")
                benchmark = None
        qs.extend_pandas()
        try:
            qs.reports.html(
                returns,
                benchmark=benchmark,
                output="backtest_report.html",
                title="Strategy",
                download_filename="backtest_report.html",
                rf=0.0,
                grayscale=False,
                figsize=(12, 6),
                display=False,
                compounded=True,
                # periods_per_year=252,
                match_dates=True,
            )
            return "backtest_report.html"
        except Exception as e:
            print(f"Error generating report: {str(e)}")
            return None

    def plot_results(self):
        """Plot backtest result charts using candlestick style"""
        if config.SHOW_PLOT:
            self.backtest_engine.cerebro.plot(style="candlestick")

        # Generate performance report
        if config.ENABLE_REPORT:
            report_path = self._generate_report()
            if report_path:
                print(f"Backtest report generated successfully: {report_path}")
