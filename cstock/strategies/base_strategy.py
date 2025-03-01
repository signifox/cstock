import backtrader as bt
from cstock.risk_manager import RiskManager


class BaseStrategy(bt.Strategy):
    """
    策略基类，提供通用的功能和辅助方法
    所有自定义策略都应该继承这个基类
    """

    params = (
        ("max_position_size", 0.2),  # 最大仓位比例
        ("stop_loss_pct", 0.02),  # 止损比例
        ("take_profit_pct", 0.05),  # 止盈比例
        ("volatility_window", 20),  # 波动率计算窗口
    )

    def __init__(self):
        self.risk_manager = RiskManager(
            max_position_size=self.params.max_position_size,
            stop_loss_pct=self.params.stop_loss_pct,
            take_profit_pct=self.params.take_profit_pct,
        )

        # 记录每个交易的入场价格
        self.entry_prices = {}
        # 记录订单
        self.orders = {}
        # 记录持仓状态
        self.position_status = {}

    def log(self, txt, dt=None):
        """记录策略信息"""
        dt = dt or self.datas[0].datetime.date(0)
        print(f"{dt.isoformat()}, {txt}")

    def notify_order(self, order):
        """订单状态更新通知"""
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    f"买入执行: {order.data._name}, 价格: {order.executed.price:.2f}, "
                    f"数量: {order.executed.size}, 成本: {order.executed.value:.2f}, "
                    f"手续费: {order.executed.comm:.2f}"
                )
                self.entry_prices[order.data._name] = order.executed.price
            else:
                self.log(
                    f"卖出执行: {order.data._name}, 价格: {order.executed.price:.2f}, "
                    f"数量: {order.executed.size}, 成本: {order.executed.value:.2f}, "
                    f"手续费: {order.executed.comm:.2f}"
                )
                if order.data._name in self.entry_prices:
                    del self.entry_prices[order.data._name]

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f"订单取消/保证金不足/拒绝: {order.data._name}")
            # 记录失败的交易
            self.position_status[order.data._name] = "lost"

        self.orders[order.data._name] = None

    def notify_trade(self, trade):
        """交易状态更新通知"""
        if not trade.isclosed:
            return

        # 更新交易状态
        if trade.pnl >= 0:
            self.position_status[trade.data._name] = "won"
        else:
            self.position_status[trade.data._name] = "lost"

        self.log(
            f"交易利润: {trade.data._name}, 毛利润: {trade.pnl:.2f}, "
            f"净利润: {trade.pnlcomm:.2f}"
        )

    def get_position_size(self, data):
        """计算建仓数量"""
        cash = self.broker.getcash()
        price = data.close[0]

        # 计算波动率
        prices = [
            data.close[-i]
            for i in range(self.params.volatility_window)
            if len(data.close) > i
        ]
        volatility = self.risk_manager.calculate_volatility(prices)

        return self.risk_manager.calculate_position_size(cash, price, volatility)

    def check_exit_signals(self):
        """检查是否需要止盈止损"""
        for data in self.datas:
            if not self.getposition(data).size:
                continue

            if data._name not in self.entry_prices:
                continue

            entry_price = self.entry_prices[data._name]
            current_price = data.close[0]

            # 检查止损
            if self.risk_manager.should_stop_loss(entry_price, current_price):
                self.log(
                    f"触发止损: {data._name}, 入场价: {entry_price:.2f}, 当前价: {current_price:.2f}"
                )
                self.sell(data=data)

            # 检查止盈
            elif self.risk_manager.should_take_profit(entry_price, current_price):
                self.log(
                    f"触发止盈: {data._name}, 入场价: {entry_price:.2f}, 当前价: {current_price:.2f}"
                )
                self.sell(data=data)

    def next(self):
        """主要的策略逻辑应该在子类中实现"""
        self.check_exit_signals()

    def start(self):
        """策略开始时调用"""
        self.log("策略启动")

    def stop(self):
        """策略结束时调用"""
        self.log("策略结束")
