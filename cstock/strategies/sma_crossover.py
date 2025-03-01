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

    def select_best_stock(self):
        """选择最佳交易标的
        根据技术指标和风险因素选择最优的交易机会
        """
        best_stock = None
        best_score = float("-inf")

        for data in self.datas:
            # 如果有未完成的订单，跳过该股票
            if self.orders.get(data._name):
                continue

            # 获取该股票的指标
            indicators = self.indicators[data._name]
            crossover = indicators["crossover"][0]
            sma_short = indicators["sma_short"][0]
            sma_long = indicators["sma_long"][0]

            # 计算技术得分
            if not self.getposition(data).size:  # 只检查是否已持仓
                # 如果有交叉信号，优先考虑
                if crossover == 1:  # 买入信号
                    # 计算均线距离百分比
                    distance = (sma_short - sma_long) / sma_long
                    # 计算波动率
                    prices = [
                        data.close[-i]
                        for i in range(self.params.volatility_window)
                        if len(data.close) > i
                    ]
                    volatility = (
                        self.risk_manager.calculate_volatility(prices) or 0.01
                    )  # 避免除以零
                    # 综合得分：均线距离/波动率，距离越大、波动率越小越好
                    score = 100 + distance / (
                        volatility + 0.0001
                    )  # 给有交叉信号的股票更高的基础分
                    if score > best_score:
                        best_score = score
                        best_stock = data
                # 即使没有交叉信号，也计算得分，但基础分较低
                else:
                    # 只有当短期均线高于长期均线时才考虑
                    if sma_short > sma_long:
                        distance = (sma_short - sma_long) / sma_long
                        prices = [
                            data.close[-i]
                            for i in range(self.params.volatility_window)
                            if len(data.close) > i
                        ]
                        volatility = (
                            self.risk_manager.calculate_volatility(prices) or 0.01
                        )
                        score = distance / (volatility + 0.0001)
                        if score > best_score:
                            best_score = score
                            best_stock = data

        return best_stock

    def next(self):
        # 首先检查止盈止损
        super().next()

        # 选择最佳交易标的
        best_stock = self.select_best_stock()

        # 如果有最佳股票，优先交易最佳股票
        if best_stock is not None:
            # 获取该股票的指标
            indicators = self.indicators[best_stock._name]
            crossover = indicators["crossover"][0]

            # 检查是否持仓
            if not self.getposition(best_stock).size:
                # 没有持仓，检查是否有买入信号
                if crossover == 1:  # 短期均线上穿长期均线
                    self.log(
                        f"买入信号 {best_stock._name}, 价格: {best_stock.close[0]:.2f}"
                    )
                    # 使用风险管理器计算建仓数量
                    size = self.get_position_size(best_stock)
                    self.orders[best_stock._name] = self.buy(data=best_stock, size=size)
            else:
                # 有持仓，检查是否有卖出信号
                if crossover == -1:  # 短期均线下穿长期均线
                    self.log(
                        f"卖出信号 {best_stock._name}, 价格: {best_stock.close[0]:.2f}"
                    )
                    # 卖出信号，清仓
                    self.orders[best_stock._name] = self.sell(
                        data=best_stock, size=self.getposition(best_stock).size
                    )
        else:
            # 如果没有最佳股票，则遍历所有股票检查交易信号
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
                        self.log(f"买入信号 {data._name}, 价格: {data.close[0]:.2f}")
                        # 使用风险管理器计算建仓数量
                        size = self.get_position_size(data)
                        self.orders[data._name] = self.buy(data=data, size=size)
                else:
                    # 有持仓，检查是否有卖出信号
                    if crossover == -1:  # 短期均线下穿长期均线
                        self.log(f"卖出信号 {data._name}, 价格: {data.close[0]:.2f}")
                        # 卖出信号，清仓
                        self.orders[data._name] = self.sell(
                            data=data, size=self.getposition(data).size
                        )
