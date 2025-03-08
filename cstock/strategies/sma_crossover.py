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
        ("volume_mult", 1.5),  # 成交量放大倍数阈值
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
            rsi = bt.indicators.RSI(
                data.close,
                period=self.params.rsi_period
            )

            # 成交量均线
            volume_sma = bt.indicators.SimpleMovingAverage(
                data.volume, period=20
            )

            self.indicators[data._name] = {
                "sma_short": sma_short,
                "sma_long": sma_long,
                "crossover": crossover,
                "rsi": rsi,
                "volume_sma": volume_sma
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
            volume_sma = indicators["volume_sma"][0]
            current_price = data.close[0]
            current_volume = data.volume[0]

            # 记录当前的技术指标状态
            self.log(
                f"技术指标状态 - {data._name}: 价格={current_price:.2f}, "
                f"短期均线={sma_short:.2f}, 长期均线={sma_long:.2f}, "
                f"交叉信号={crossover}, RSI={rsi:.2f}, "
                f"成交量={current_volume}, 成交量均线={volume_sma:.2f}"
            )

            # 数据质量检查
            if not self._validate_data(data):
                continue

            if not self.getposition(data).size:
                # 买入条件：均线金叉
                if crossover == 1:
                    self.log(f"检测到买入信号 - {data._name}: "
                            f"短期均线上穿长期均线, RSI={rsi:.2f}, "
                            f"成交量={current_volume}(均线的{current_volume/volume_sma:.2f}倍)")
                    size = self.get_position_size(data)
                    self.orders[data._name] = self.buy(data=data, size=size)
            else:
                # 卖出条件：均线死叉 或 RSI超买
                if crossover == -1 or rsi > self.params.rsi_upper:
                    reason = "短期均线下穿长期均线" if crossover == -1 else f"RSI超买({rsi:.2f})"
                    self.log(f"检测到卖出信号 - {data._name}: {reason}")
                    self.orders[data._name] = self.sell(
                        data=data, size=self.getposition(data).size
                    )

    def _validate_data(self, data):
        """验证数据质量"""
        current_price = data.close[0]
        current_volume = data.volume[0]

        # 检查是否有异常值
        if current_price <= 0 or current_volume <= 0:
            self.log(f"数据异常 - {data._name}: 价格={current_price:.2f}, 成交量={current_volume}")
            return False

        # 检查价格波动是否异常（如果有前一天的数据）
        if len(data) > 1:
            prev_price = data.close[-1]
            price_change = abs(current_price - prev_price) / prev_price
            if price_change > 0.2:  # 价格变动超过20%
                self.log(f"价格波动异常 - {data._name}: 当前价格={current_price:.2f}, "
                         f"前一日价格={prev_price:.2f}, 变动率={price_change:.2%}")
                return False

        return True
