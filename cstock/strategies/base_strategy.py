import backtrader as bt
from cstock.risk_manager import RiskManager


class BaseStrategy(bt.Strategy):
    """
    策略基类，提供通用的功能和辅助方法
    所有自定义策略都应该继承这个基类
    """

    params = (
        ("max_position_size", 0.3),  # 最大仓位比例
        ("stop_loss_pct", 0.1),  # 止损比例
        ("take_profit_pct", 0.4),  # 止盈比例
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
        # 记录当日已使用的资金
        self._today_used_cash = 0

        # 初始化价值历史记录
        self._portfolio_drawdown_history = []
        self._highest_portfolio_value = 0

    def log(self, txt, dt=None):
        """记录策略信息"""
        dt = dt or self.datas[0].datetime.date(0)
        print(f"{dt.isoformat()}, {txt}")

    def notify_order(self, order):
        """订单状态更新通知"""
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            # 获取当前持仓状态
            position = self.getposition(order.data)

            if order.isbuy():
                # 获取当前投资组合状态
                cash = self.broker.getcash()
                value = self.broker.getvalue()
                position_value = position.size * order.executed.price

                self.log(
                    f"买入执行: {order.data._name}, 价格: {order.executed.price:.2f}, "
                    f"数量: {order.executed.size}, 金额: {order.executed.value:.2f}, "
                    f"手续费: {order.executed.comm:.2f}"
                )
                self.entry_prices[order.data._name] = order.executed.price
            else:  # 卖出订单
                # 验证卖出后的持仓状态
                if position.size < 0:
                    self.log(f"警告：{order.data._name} 出现负持仓，尝试修正")
                    # 取消之前的卖出订单
                    self.cancel(order)
                    return

                self.log(
                    f"卖出执行: {order.data._name}, 价格: {order.executed.price:.2f}, "
                    f"数量: {order.executed.size}, 金额: {abs(order.executed.value):.2f}, "
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
        """计算建仓数量，根据可用现金和最大仓位比例"""
        # 计算当前总持仓市值
        total_position_value = 0
        for d in self.datas:
            position = self.getposition(d)
            if position.size:
                total_position_value += position.size * d.close[0]

        # 计算当前总资产
        total_value = self.broker.getvalue()
        # 计算最大允许的总仓位市值
        max_total_position = total_value * self.params.max_position_size
        # 计算还可以使用的仓位市值
        remaining_position = max_total_position - total_position_value

        # 如果已经达到或超过最大仓位，不再开新仓
        if remaining_position <= 0:
            return 0

        # 计算可用现金（考虑当日已使用资金）
        available_cash = min(
            self.broker.getcash() - self._today_used_cash, remaining_position
        )

        price = data.close[0]

        # 使用风险管理器计算建议的仓位大小
        suggested_size = self.risk_manager.calculate_position_size(
            available_cash, price, data._name
        )

        # 更新当日已使用资金
        if suggested_size > 0:
            self._today_used_cash += price * suggested_size

        return suggested_size

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
                self.sell_position(data)

            # 检查止盈
            elif self.risk_manager.should_take_profit(entry_price, current_price):
                self.log(
                    f"触发止盈: {data._name}, 入场价: {entry_price:.2f}, 当前价: {current_price:.2f}"
                )
                self.sell_position(data)

    def next(self):
        """主要的策略逻辑应该在子类中实现"""
        # 每天开始时重置当日已使用资金
        self._today_used_cash = 0
        self.check_exit_signals()
        self._update_history()

    def _update_history(self):
        """更新投资组合价值历史和回撤历史"""
        # 更新投资组合价值历史（包含现金和所有持仓市值）
        portfolio_value = self.broker.getvalue()
        cash = self.broker.getcash()

        # 更新投资组合最高价值和回撤
        self._highest_portfolio_value = max(
            self._highest_portfolio_value, portfolio_value
        )

        if self._highest_portfolio_value > 0:
            drawdown = (
                (self._highest_portfolio_value - portfolio_value)
                / self._highest_portfolio_value
                * 100
            )
        else:
            drawdown = 0
        self._portfolio_drawdown_history.append(drawdown)

    def start(self):
        """策略开始时调用"""
        self.log("策略启动")

    def sell_position(self, data):
        """卖出持仓
        1. 止损：亏损超过阈值时卖出全部仓位
        2. 止盈：达到止盈目标时卖出全部仓位
        """
        position = self.getposition(data)
        if not position.size:
            return

        # 获取当前价格和入场价格
        current_price = data.close[0]
        entry_price = self.entry_prices.get(data._name)
        if not entry_price:
            return

        # 如果该标的已经在当前bar执行过卖出操作，则跳过
        if data._name in self.orders and self.orders[data._name] is not None:
            return

        # 计算盈亏幅度
        pnl_pct = (current_price - entry_price) / entry_price

        # 确保卖出数量不超过当前持仓
        sell_size = min(abs(position.size), position.size)

        # 止损逻辑（亏损超过止损线）
        if pnl_pct < -self.params.stop_loss_pct:
            # 达到止损线时全部卖出
            self.orders[data._name] = self.sell(data=data, size=sell_size)
            self.log(f"止损: {data._name}, 亏损: {abs(pnl_pct):.2%}, 数量: {sell_size}")

        # 止盈逻辑（盈利超过止盈线）
        elif pnl_pct > self.params.take_profit_pct:
            # 达到止盈目标时全部卖出
            self.orders[data._name] = self.sell(data=data, size=sell_size)
            self.log(f"止盈: {data._name}, 盈利: {pnl_pct:.2%}, 数量: {sell_size}")

        # 其他信号触发的卖出
        else:
            # 一次性清空所有仓位
            self.orders[data._name] = self.sell(data=data, size=sell_size)

    def check_exit_signals(self):
        """检查是否需要止盈止损"""
        for data in self.datas:
            position = self.getposition(data)
            if not position.size:
                continue

            if data._name not in self.entry_prices:
                continue

            # 如果该标的已经在当前bar执行过卖出操作，则跳过
            if data._name in self.orders and self.orders[data._name] is not None:
                continue

            entry_price = self.entry_prices[data._name]
            current_price = data.close[0]

            # 检查止损
            if self.risk_manager.should_stop_loss(entry_price, current_price):
                self.log(
                    f"触发止损: {data._name}, 入场价: {entry_price:.2f}, 当前价: {current_price:.2f}"
                )
                self.sell_position(data)

            # 检查止盈
            elif self.risk_manager.should_take_profit(entry_price, current_price):
                self.log(
                    f"触发止盈: {data._name}, 入场价: {entry_price:.2f}, 当前价: {current_price:.2f}"
                )
                self.sell_position(data)

    def stop(self):
        """策略结束时调用"""
        self.log("策略结束")
