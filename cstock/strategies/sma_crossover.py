import backtrader as bt
from cstock import config
from cstock.strategies.base_strategy import BaseStrategy


class SMACrossoverStrategy(BaseStrategy):
    params = (
        ("sma_period_short", config.STRATEGY_PARAMS["sma_period_short"]),
        ("sma_period_long", config.STRATEGY_PARAMS["sma_period_long"]),
    )

    def __init__(self):
        super().__init__()

        self.indicators = {}
        for data in self.datas:
            sma_short = bt.indicators.SimpleMovingAverage(
                data.close, period=self.params.sma_period_short
            )
            sma_long = bt.indicators.SimpleMovingAverage(
                data.close, period=self.params.sma_period_long
            )

            crossover = bt.indicators.CrossOver(sma_short, sma_long)

            self.indicators[data._name] = {
                "sma_short": sma_short,
                "sma_long": sma_long,
                "crossover": crossover,
            }

    def next(self):
        super().next()

        for data in self.datas:
            if self.orders.get(data._name):
                continue

            indicators = self.indicators[data._name]
            crossover = indicators["crossover"][0]

            if not self.getposition(data).size:
                if crossover == 1:
                    size = self.get_position_size(data)
                    self.orders[data._name] = self.buy(data=data, size=size)
            else:
                if crossover == -1:
                    self.orders[data._name] = self.sell(
                        data=data, size=self.getposition(data).size
                    )
