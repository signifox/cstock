import backtrader as bt
from cstock import config
from cstock.strategies.base_strategy import BaseStrategy


class SMACrossoverStrategy(BaseStrategy):
    params = (
        ("sma_period_short", config.STRATEGY_PARAMS["sma_period_short"]),
        ("sma_period_long", config.STRATEGY_PARAMS["sma_period_long"]),
        ("rsi_period", 14),  # RSI指标周期
        ("rsi_upper", 70),  # RSI超买阈值
        ("rsi_lower", 30),  # RSI超卖阈值
    )

    def __init__(self):
        super().__init__()

        self.indicators = {}
        for data in self.datas:
            # 均线指标
            sma_short = bt.indicators.SimpleMovingAverage(
                data.close, period=self.params.sma_period_short
            )
            sma_long = bt.indicators.SimpleMovingAverage(
                data.close, period=self.params.sma_period_long
            )
            crossover = bt.indicators.CrossOver(sma_short, sma_long)

            # RSI指标
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

            # 检查是否满足买入条件
            if not self.getposition(data).size and sma_short > sma_long:
                # 计算建仓数量
                size = self.get_position_size(data)
                if size > 0:
                    self.orders[data._name] = self.buy(data=data, size=size)
                    self.log(f"买入{data._name}, 价格: {data.close[0]}, 数量: {size}")

            # 检查是否满足卖出条件
            elif self.getposition(data).size and sma_short < sma_long:
                size = self.sell_position(data)
                self.log(f"卖出{data._name}, 价格: {data.close[0]},数量: {size}")
