import backtrader as bt
from datetime import datetime


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

        # Calculate maximum length for each field for alignment
        max_lengths = {}
        for summary in all_summaries:
            for key, value in summary.items():
                value_str = str(value)
                if isinstance(value, float):
                    if "Rate" in key:
                        value_str = f"{value:.2%}"
                    else:
                        value_str = f"{value:.2f}"
                max_lengths[key] = max(max_lengths.get(key, len(key)), len(value_str))

        # Print header
        header = ""
        separator = ""
        for key in all_summaries[0].keys():
            width = max_lengths[key] + 2  # Add 2 spaces padding
            header += f"{key:^{width}}"
            separator += "-" * width

        print("\n" + header)
        print(separator)

        # Print data row for each stock
        for summary in all_summaries:
            row = ""
            for key, value in summary.items():
                width = max_lengths[key] + 2  # Add 2 spaces padding
                if isinstance(value, float):
                    if "Rate" in key:
                        row += f"{value:>{width}.2%}"
                    else:
                        row += f"{value:>{width}.2f}"
                else:
                    row += f"{value:^{width}}"
            print(row)

        print("\n")
