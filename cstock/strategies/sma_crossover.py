import backtrader as bt
from cstock import config
from cstock.strategies.base_strategy import BaseStrategy


class SMACrossoverStrategy(BaseStrategy):
    params = (
        ("sma_period_short", 5),
        ("sma_period_long", 10),
        ("rsi_period", 14),  # RSI Period
        ("rsi_upper", 70),  # RSI Overbought Threshold
        ("rsi_lower", 30),  # RSI Oversold Threshold
    )

    def __init__(self):
        super().__init__()

        self.indicators = {}
        for data in self.datas:
            # Moving Average Indicators
            sma_short = bt.indicators.SimpleMovingAverage(
                data.close, period=self.params.sma_period_short
            )
            sma_long = bt.indicators.SimpleMovingAverage(
                data.close, period=self.params.sma_period_long
            )
            crossover = bt.indicators.CrossOver(sma_short, sma_long)

            # RSI Indicator
            rsi = bt.indicators.RSI(data.close, period=self.params.rsi_period)

            self.indicators[data._name] = {
                "sma_short": sma_short,
                "sma_long": sma_long,
                "crossover": crossover,
                "rsi": rsi,
            }

    def next(self):
        super().next()

        for data in self.datas:
            if self.orders.get(data._name):
                continue

            indicators = self.indicators[data._name]
            sma_short = indicators["sma_short"][0]
            sma_long = indicators["sma_long"][0]
            crossover = indicators["crossover"][0]
            rsi = indicators["rsi"][0]

            # Check buy conditions
            if not self.getposition(data).size and sma_short > sma_long:
                # Calculate position size
                size = self.get_position_size(data)
                if size > 0:
                    self.orders[data._name] = self.buy(data=data, size=size)
                    self.log(f"买入: {data._name}, 价格: {data.close[0]}, 数量: {size}")

            # Check sell conditions
            elif self.getposition(data).size and sma_short < sma_long:
                size = self.sell_position(data)
                self.log(f"卖出: {data._name}, 价格: {data.close[0]}, 数量: {size}")
