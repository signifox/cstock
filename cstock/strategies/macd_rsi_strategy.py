import backtrader as bt
from cstock.strategies.base_strategy import BaseStrategy


class MACDRSIStrategy(BaseStrategy):
    params = (
        ("macd_fast", 12),  # MACD快线周期
        ("macd_slow", 26),  # MACD慢线周期
        ("macd_signal", 9),  # MACD信号线周期
        ("rsi_period", 14),  # RSI周期
        ("rsi_upper", 70),  # RSI超买阈值
        ("rsi_lower", 30),  # RSI超卖阈值
    )

    def __init__(self):
        super().__init__()

        self.indicators = {}
        for data in self.datas:
            # MACD指标
            macd = bt.indicators.MACD(
                data.close,
                period_me1=self.params.macd_fast,
                period_me2=self.params.macd_slow,
                period_signal=self.params.macd_signal,
            )

            # RSI指标
            rsi = bt.indicators.RSI(data.close, period=self.params.rsi_period)

            self.indicators[data._name] = {"macd": macd, "rsi": rsi}

    def next(self):
        super().next()

        for data in self.datas:
            if self.orders.get(data._name):
                continue

            indicators = self.indicators[data._name]
            macd = indicators["macd"]
            rsi = indicators["rsi"]

            # MACD金叉
            macd_crossover = (
                macd.macd[0] > macd.signal[0] and macd.macd[-1] <= macd.signal[-1]
            )
            # MACD死叉
            macd_crossunder = (
                macd.macd[0] < macd.signal[0] and macd.macd[-1] >= macd.signal[-1]
            )

            position = self.getposition(data)

            # 买入条件：MACD金叉且RSI未超买
            if not position.size and macd_crossover and rsi[0] < self.params.rsi_upper:
                size = self.get_position_size(data)
                self.buy(data=data, size=size)

            # 卖出条件：MACD死叉或RSI超买
            elif position.size and (macd_crossunder or rsi[0] > self.params.rsi_upper):
                self.sell_position(data)
