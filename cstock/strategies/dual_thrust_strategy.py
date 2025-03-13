import backtrader as bt
import numpy as np
from cstock.strategies.base_strategy import BaseStrategy


class DualThrustStrategy(BaseStrategy):
    params = (
        ("n_days", 5),
        ("k1", 0.5),
        ("k2", 0.5),
    )

    def __init__(self):
        super().__init__()
        self.high_n = {}
        self.low_n = {}
        self.close_n = {}
        for data in self.datas:
            self.high_n[data._name] = bt.indicators.Highest(
                data.high, period=self.params.n_days
            )
            self.low_n[data._name] = bt.indicators.Lowest(
                data.low, period=self.params.n_days
            )
            self.close_n[data._name] = data.close

    def next(self):
        super().next()

        if len(self) < self.params.n_days:
            return

        for data in self.datas:
            if self.orders.get(data._name):
                continue

            range = max(
                self.high_n[data._name][0] - self.close_n[data._name][0],
                self.close_n[data._name][0] - self.low_n[data._name][0],
            )
            buy_threshold = data.open[0] + self.params.k1 * range
            sell_threshold = data.open[0] - self.params.k2 * range

            if not self.getposition(data).size:
                if data.high[0] > buy_threshold:
                    size = self.get_position_size(data)
                    self.buy(data=data, size=size)
            else:
                if data.low[0] < sell_threshold:
                    self.sell_position(data)
