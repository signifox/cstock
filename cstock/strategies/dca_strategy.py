import backtrader as bt
from datetime import datetime
from cstock.strategies.base_strategy import BaseStrategy


class DCAStrategy(BaseStrategy):
    """Dollar-Cost Averaging Strategy

    A strategy that invests a fixed amount of money at regular intervals,
    executing buy operations on specified dates with predetermined investment amounts.
    """

    params = (
        ("invest_date", 1),  # Monthly investment date (1-31)
        ("invest_amount", 5000),  # Investment amount per transaction
        ("max_position_size", 0.8),  # Maximum position size ratio
        ("stop_loss_pct", 0.1),  # Stop loss percentage
        ("take_profit_pct", 0.4),  # Take profit percentage
    )

    def __init__(self):
        super().__init__()
        # Record last investment date
        self.last_invest_date = None

    def is_invest_day(self):
        """Check if current day is investment day"""
        current_date = self.data.datetime.date(0)

        # If this is the first run of the strategy, return True for initial investment
        if self.last_invest_date is None:
            return True

        # Skip if already invested this month
        if (
            current_date.year == self.last_invest_date.year
            and current_date.month == self.last_invest_date.month
        ):
            return False

        # Check if reached specified investment date
        return current_date.day >= self.params.invest_date

    def calculate_buy_size(self, data):
        """Calculate buy quantity"""
        available_cash = self.broker.get_cash()
        invest_amount = min(self.params.invest_amount, available_cash)

        if invest_amount <= 0:
            return 0

        # Calculate buyable shares using current closing price
        current_price = data.close[0]
        # Round down to ensure not exceeding available funds
        size = int(invest_amount / current_price)

        # Validate position size using risk manager
        max_size = self.get_position_size(data)
        return min(size, max_size) if max_size > 0 else size

    def next(self):
        super().next()

        # Iterate through all data sources (stocks)
        for data in self.datas:
            # Check for pending orders
            if self.orders.get(data._name):
                continue

            # Check if it's investment day
            if not self.is_invest_day():
                continue

            # Calculate buy quantity
            buy_size = self.calculate_buy_size(data)

            if buy_size > 0:
                self.log(f"DCA Buy {data._name}, Quantity: {buy_size}")
                self.orders[data._name] = self.buy(data=data, size=buy_size)
                # Update last investment date
                self.last_invest_date = self.data.datetime.date(0)
