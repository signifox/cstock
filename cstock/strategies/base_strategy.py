import backtrader as bt
from cstock.risk_manager import RiskManager
from cstock.order_metric import OrderMetric


class BaseStrategy(bt.Strategy):
    """策略基类，提供通用的功能和辅助方法
    所有自定义策略都应该继承这个基类
    """

    params = (
        ("max_position_size", 0.3),  # 最大仓位比例
        ("stop_loss_pct", 0.1),  # 止损比例
        ("take_profit_pct", 0.2),  # 止盈比例
    )

    def __init__(self):
        # 记录订单
        self.orders = {}
        # 记录持仓状态
        self.position_status = {}

        # 初始化风险管理器
        self.risk_manager = RiskManager(
            stop_loss_pct=self.params.stop_loss_pct,
            take_profit_pct=self.params.take_profit_pct,
            max_position_size=self.params.max_position_size,
        )

        # 初始化订单度量统计
        self.order_metric = OrderMetric()

    def log(self, txt, dt=None):
        """记录策略信息"""
        dt = dt or self.datas[0].datetime.date(0)
        print(f"{dt.isoformat()}, {txt}")

    def notify_order(self, order):
        """订单状态更新通知"""
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            position = self.getposition(order.data)

            if order.isbuy():
                self.log(
                    f"买入执行: {order.data._name}, 价格: {order.executed.price:.2f}, "
                    f"数量: {order.executed.size}, 金额: {order.executed.value:.2f}, "
                    f"手续费: {order.executed.comm:.2f}"
                )
                # 添加新持仓到风险管理器
                self.risk_manager.add_position(order.data._name, order.executed.price)
                # 记录交易入场
                self.order_metric.on_trade_entry(
                    symbol=order.data._name,
                    entry_time=self.datas[0].datetime.datetime(0),
                    entry_price=order.executed.price,
                    size=order.executed.size,
                    direction="buy",
                    commission=order.executed.comm,
                )
            else:  # 卖出订单
                if position.size < 0:
                    self.log(f"警告：{order.data._name} 出现负持仓，尝试修正")
                    self.cancel(order)
                    return

                self.log(
                    f"卖出执行: {order.data._name}, 价格: {order.executed.price:.2f}, "
                    f"数量: {order.executed.size}, 金额: {abs(order.executed.value):.2f}, "
                    f"手续费: {order.executed.comm:.2f}"
                )
                # 从风险管理器中移除持仓
                self.risk_manager.remove_position(order.data._name)
                # 记录交易出场
                self.order_metric.on_trade_exit(
                    symbol=order.data._name,
                    exit_time=self.datas[0].datetime.datetime(0),
                    exit_price=order.executed.price,
                    commission=order.executed.comm,
                    exit_type="signal",
                )

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
        """计算建仓数量，使用风险管理器进行仓位管理"""
        return self.risk_manager.get_position_size(data, self.broker)

    def check_exit_signals(self):
        """检查是否需要退出仓位"""
        for data in self.datas:
            if not self.getposition(data).size:
                continue

            # 检查是否触发止盈止损
            should_exit, exit_type = self.risk_manager.check_exit_signals(
                data._name, data.close[0]
            )

            if should_exit:
                self.log(f"{exit_type.upper()} 触发: {data._name}")
                # 记录交易出场
                self.order_metric.on_trade_exit(
                    symbol=data._name,
                    exit_time=self.datas[0].datetime.datetime(0),
                    exit_price=data.close[0],
                    commission=0.0,  # 手续费将在notify_order中更新
                    exit_type=exit_type,
                )
                self.sell_position(data)

    def next(self):
        """主要的策略逻辑应该在子类中实现"""
        # 每天开始时重置风险管理器的当日已使用资金
        self.risk_manager.reset_daily_cash()
        # 检查止盈止损信号
        self.check_exit_signals()

    def start(self):
        """策略开始时调用"""
        self.log("策略启动")

    def sell_position(self, data):
        """卖出持仓"""
        position = self.getposition(data)
        if not position.size:
            return

        # 如果该标的已经在当前bar执行过卖出操作，则跳过
        if data._name in self.orders and self.orders[data._name] is not None:
            return

        # 一次性清空所有仓位
        sell_size = position.size
        self.orders[data._name] = self.sell(data=data, size=sell_size)
        self.log(f"卖出: {data._name}, 数量: {sell_size}")

    def stop(self):
        """策略结束时调用"""
        self.log("策略结束")
