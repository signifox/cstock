import backtrader as bt
from cstock.strategies.base_strategy import BaseStrategy


class MACDRSIStrategy(BaseStrategy):
    params = (
        ("macd_fast", 12),  # MACD Fast Period
        ("macd_slow", 26),  # MACD Slow Period
        ("macd_signal", 9),  # MACD Signal Period
        ("rsi_period", 14),  # RSI Period
        ("rsi_upper", 70),  # RSI Overbought Threshold
        ("rsi_lower", 30),  # RSI Oversold Threshold
    )

    def __init__(self):
        super().__init__()

        self.indicators = {}
        for data in self.datas:
            # MACD Indicator
            macd = bt.indicators.MACD(
                data.close,
                period_me1=self.params.macd_fast,
                period_me2=self.params.macd_slow,
                period_signal=self.params.macd_signal,
            )

            # RSI Indicator
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

            # MACD Golden Cross
            macd_crossover = (
                macd.macd[0] > macd.signal[0] and macd.macd[-1] <= macd.signal[-1]
            )
            # MACD Death Cross
            macd_crossunder = (
                macd.macd[0] < macd.signal[0] and macd.macd[-1] >= macd.signal[-1]
            )

            position = self.getposition(data)

            # Buy condition: MACD Golden Cross and RSI not overbought
            if not position.size and macd_crossover and rsi[0] < self.params.rsi_upper:
                size = self.get_position_size(data)
                self.buy(data=data, size=size)

            # Sell condition: MACD Death Cross or RSI overbought
            elif position.size and (macd_crossunder or rsi[0] > self.params.rsi_upper):
                self.sell_position(data)
