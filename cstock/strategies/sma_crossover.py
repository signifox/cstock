import backtrader as bt
from cstock import config
from cstock.strategies.base_strategy import BaseStrategy


class SMACrossoverStrategy(BaseStrategy):
    """
    简单的移动平均线交叉策略
    当短期移动平均线上穿长期移动平均线时买入
    当短期移动平均线下穿长期移动平均线时卖出
    """

    params = (
        ("sma_period_short", config.STRATEGY_PARAMS["sma_period_short"]),
        ("sma_period_long", config.STRATEGY_PARAMS["sma_period_long"]),
    )

    def __init__(self):
        # 首先调用父类的初始化方法
        super().__init__()

        # 为每个数据源创建指标
        self.indicators = {}
        for data in self.datas:
            # 计算短期和长期移动平均线
            sma_short = bt.indicators.SimpleMovingAverage(
                data.close, period=self.params.sma_period_short
            )
            sma_long = bt.indicators.SimpleMovingAverage(
                data.close, period=self.params.sma_period_long
            )

            # 定义交叉信号
            crossover = bt.indicators.CrossOver(sma_short, sma_long)

            # 存储该数据源的指标
            self.indicators[data._name] = {
                "sma_short": sma_short,
                "sma_long": sma_long,
                "crossover": crossover,
            }

    def next(self):
        # 首先检查止盈止损
        super().next()

        # 遍历所有股票检查交易信号
        for data in self.datas:
            # 如果有未完成的订单，跳过该股票
            if self.orders.get(data._name):
                continue

            # 获取该股票的指标
            indicators = self.indicators[data._name]
            crossover = indicators["crossover"][0]

            # 检查是否持仓
            if not self.getposition(data).size:
                # 没有持仓，检查是否有买入信号
                if crossover == 1:  # 短期均线上穿长期均线
                    # 使用风险管理器计算建仓数量
                    size = self.get_position_size(data)
                    self.orders[data._name] = self.buy(data=data, size=size)
                else:
                    # 有持仓，检查是否有卖出信号
                    if crossover == -1:  # 短期均线下穿长期均线
                        # 卖出信号，清仓
                        self.orders[data._name] = self.sell(
                            data=data, size=self.getposition(data).size
                        )
