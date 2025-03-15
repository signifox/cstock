import backtrader as bt
from datetime import datetime
import pandas as pd


class SingleStockAnalyzer:
    """Single stock analyzer for recording and analyzing individual stock trading performance"""

    def __init__(self, stock_name):
        self.stock_name = stock_name
        self.reset()

    def reset(self):
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_profit = 0.0
        self.total_commission = 0.0
        self.returns = []
        self.trades_history = []
        self.current_position = 0
        self.entry_price = 0.0
        self.last_trade_time = None

    def update_trade(self, trade):
        if trade.isclosed:
            self.total_trades += 1
            profit = trade.pnl
            self.total_profit += profit
            self.total_commission += trade.commission

            if profit > 0:
                self.winning_trades += 1
            else:
                self.losing_trades += 1

            trade_record = {
                "time": bt.num2date(trade.dtclose),
                "type": "SELL" if trade.size < 0 else "BUY",
                "size": abs(trade.size),
                "price": trade.price,
                "profit": profit,
                "commission": trade.commission,
            }
            self.trades_history.append(trade_record)
            self.last_trade_time = trade_record["time"]

    def get_summary(self):
        win_rate = (
            self.winning_trades / self.total_trades if self.total_trades > 0 else 0
        )
        avg_profit = (
            self.total_profit / self.total_trades if self.total_trades > 0 else 0
        )

        return {
            "Symbol": self.stock_name,
            "Total Trades": self.total_trades,
            "Winning Trades": self.winning_trades,
            "Losing Trades": self.losing_trades,
            "Win Rate": win_rate,
            "Total Profit": self.total_profit,
            "Average Trade Profit": avg_profit,
            "Total Commission": self.total_commission,
            "Current Position": self.current_position,
        }

    @staticmethod
    def print_all_summaries(analyzers):
        """Print summary statistics for all stocks in a unified table format

        Parameters:
            analyzers (list): List of SingleStockAnalyzer objects
        """
        if not analyzers:
            return

        # Get summary data for all stocks
        all_summaries = [analyzer.get_summary() for analyzer in analyzers]

        # Convert to DataFrame
        df = pd.DataFrame(all_summaries)

        # Set display options
        pd.set_option("display.float_format", lambda x: "{:.2f}".format(x))
        pd.set_option("display.max_columns", None)
        pd.set_option("display.width", None)

        # Format specific columns
        if not df.empty:
            df["Win Rate"] = df["Win Rate"].map("{:.2%}".format)
            df["Total Profit"] = df["Total Profit"].map("${:.2f}".format)
            df["Average Trade Profit"] = df["Average Trade Profit"].map(
                "${:.2f}".format
            )
            df["Total Commission"] = df["Total Commission"].map("${:.2f}".format)

        # Print the formatted DataFrame
        print("\n" + str(df.to_string(index=False)) + "\n")

        # Reset display options
        pd.reset_option("display.float_format")
        pd.reset_option("display.max_columns")
        pd.reset_option("display.width")
