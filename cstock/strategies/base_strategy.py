import backtrader as bt
from cstock.risk_manager import RiskManager


class BaseStrategy(bt.Strategy):
    """
    策略基类，提供通用的功能和辅助方法
    所有自定义策略都应该继承这个基类
    """

    params = (
        ("max_position_size", 0.8),  # 最大仓位比例
        ("stop_loss_pct", 0.1),  # 止损比例
        ("take_profit_pct", 0.5),  # 止盈比例
        ("max_drawdown_pct", 0.1),  # 最大回撤限制
        ("volatility_window", 20),  # 波动率计算窗口
        ("observation_position_pct", 0.1),  # 观察仓位比例
        ("keep_observation_position", False),  # 是否保留观察仓位
    )

    def __init__(self):
        self.risk_manager = RiskManager(
            max_position_size=self.params.max_position_size,
            stop_loss_pct=self.params.stop_loss_pct,
            take_profit_pct=self.params.take_profit_pct,
            max_drawdown_pct=self.params.max_drawdown_pct,
        )

        # 记录每个交易的入场价格
        self.entry_prices = {}
        # 记录订单
        self.orders = {}
        # 记录持仓状态
        self.position_status = {}

        # 初始化价值历史记录
        self._portfolio_value_history = []
        self._value_history = {}
        self._portfolio_drawdown_history = []
        self._drawdown_history = {}
        self._highest_portfolio_value = 0
        self._highest_values = {}

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

        # 获取当前股票的回撤
        stock_drawdown = 0
        if data._name in self._drawdown_history and self._drawdown_history[data._name]:
            stock_drawdown = self._drawdown_history[data._name][-1] / 100  # 转换为小数

        return self.risk_manager.calculate_position_size(
            cash, price, volatility, data._name, stock_drawdown=stock_drawdown
        )

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
            stop_loss_info = self.risk_manager.should_stop_loss(
                entry_price, current_price, symbol=data._name
            )
            if stop_loss_info["should_stop"]:
                stop_type = stop_loss_info["stop_type"]
                loss_pct = stop_loss_info["loss_pct"]
                drop_from_high = stop_loss_info["drop_from_high"]

                stop_type_str = "追踪止损" if stop_type == "trailing" else "固定止损"
                self.log(
                    f"触发{stop_type_str}: {data._name}, 入场价: {entry_price:.2f}, 当前价: {current_price:.2f}, "
                    f"亏损: {loss_pct:.2f}%, 回撤: {drop_from_high:.2f}%"
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
        self.check_exit_signals()
        self._update_history()

    def _update_history(self):
        """更新价值历史和回撤历史"""
        # 更新投资组合价值历史（包含现金和所有持仓市值）
        portfolio_value = self.broker.getvalue()
        self._portfolio_value_history.append(portfolio_value)

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

        # 更新个股价值历史和回撤
        total_stock_value = 0  # 用于验证所有持仓市值之和
        for data in self.datas:
            symbol = data._name
            position = self.getposition(data)
            current_value = position.size * data.close[0] if position.size != 0 else 0

            # 更新个股价值历史（使用实际市值）
            if symbol not in self._value_history:
                self._value_history[symbol] = []
                self._highest_values[symbol] = 0
                self._drawdown_history[symbol] = []

            # 计算个股价值时考虑投资组合总价值的限制
            current_value = min(
                current_value,  # 使用之前计算的current_value
                portfolio_value,
            )
            total_stock_value += current_value  # 只累加一次
            self._value_history[symbol].append(current_value)

            # 更新个股最高价值和回撤
            if current_value > 0:  # 只在有持仓时更新最高价值
                if self._highest_values[symbol] == 0:  # 新开仓或重新开仓
                    self._highest_values[symbol] = current_value
                else:  # 持续持仓中
                    self._highest_values[symbol] = max(
                        self._highest_values[symbol], current_value
                    )
                # 计算回撤
                stock_drawdown = (
                    (self._highest_values[symbol] - current_value)
                    / self._highest_values[symbol]
                    * 100
                )
                # 打印个股持仓信息
                # print(
                #     f"股票: {symbol}, 持仓数量: {position.size}, "
                #     f"持仓市值: {current_value:.2f}, 最高市值: {self._highest_values[symbol]:.2f}, "
                #     f"回撤: {stock_drawdown:.2f}%"
                # )
            else:  # 无持仓时
                stock_drawdown = 0
                self._highest_values[symbol] = 0  # 重置最高价值

            self._drawdown_history[symbol].append(stock_drawdown)

        # 验证总持仓市值与投资组合价值的关系
        cash = self.broker.getcash()
        if abs((total_stock_value + cash) - portfolio_value) > 0.01:  # 允许0.01的误差
            self.log(
                f"警告：投资组合价值计算可能有误：总市值={total_stock_value:.2f}, 现金={cash:.2f}, 组合价值={portfolio_value:.2f}"
            )

    def start(self):
        """策略开始时调用"""
        self.log("策略启动")

    def sell_position(self, data):
        """卖出持仓，根据盈亏幅度决定卖出比例
        1. 止损：根据亏损幅度逐步加大卖出比例
        2. 止盈：根据盈利幅度分批卖出，保留部分仓位追踪趋势
        3. 其他信号：可选择保留观察仓位
        """
        position = self.getposition(data)
        if not position.size:
            return

        # 获取当前价格和入场价格
        current_price = data.close[0]
        entry_price = self.entry_prices.get(data._name)
        if not entry_price:
            return

        # 计算盈亏幅度
        pnl_pct = (current_price - entry_price) / entry_price

        # 止损逻辑（亏损超过止损线）
        if pnl_pct < -self.params.stop_loss_pct:
            # 根据亏损幅度计算卖出比例
            # 当亏损达到止损线时卖出50%，每增加1%亏损多卖出10%
            loss_pct = abs(pnl_pct)
            sell_ratio = min(0.5 + (loss_pct - self.params.stop_loss_pct) * 10, 1.0)
            sell_size = int(position.size * sell_ratio)
            if sell_size > 0:
                self.sell(data=data, size=sell_size)
                self.log(
                    f"止损部分减仓: {data._name}, 减仓比例: {sell_ratio:.2%}, 数量: {sell_size}"
                )

        # 止盈逻辑（盈利超过止盈线）
        elif pnl_pct > self.params.take_profit_pct:
            # 根据盈利幅度动态计算卖出比例
            # 1. 基础止盈比例从20%开始
            # 2. 每超过1%止盈线增加5%卖出比例
            # 3. 最大卖出比例限制在90%，保留部分仓位追踪趋势
            # 4. 考虑波动率因素，高波动率时提高卖出比例
            prices = [
                data.close[-i]
                for i in range(self.params.volatility_window)
                if len(data.close) > i
            ]
            volatility = self.risk_manager.calculate_volatility(prices)
            volatility_factor = min(1.5, 1 + volatility) if volatility else 1.0

            base_ratio = 0.2  # 基础卖出比例
            increment_per_pct = 0.05  # 每1%增加的卖出比例
            excess_profit = pnl_pct - self.params.take_profit_pct  # 超出止盈线的收益
            dynamic_ratio = base_ratio + (excess_profit * increment_per_pct)

            # 应用波动率因子并限制最大卖出比例
            sell_ratio = min(0.9, dynamic_ratio * volatility_factor)
            sell_size = int(position.size * sell_ratio)

            if sell_size > 0:
                self.sell(data=data, size=sell_size)
                self.log(
                    f"止盈部分减仓: {data._name}, 减仓比例: {sell_ratio:.2%}, 数量: {sell_size}, "
                    f"盈利: {pnl_pct:.2%}, 波动率系数: {volatility_factor:.2f}"
                )

        # 其他信号触发的卖出
        else:
            if self.params.keep_observation_position:
                # 计算观察仓位的数量（确保至少保留1股作为观察仓位）
                observation_size = max(
                    1, int(position.size * self.params.observation_position_pct)
                )
                # 卖出主要仓位，保留观察仓位
                sell_size = position.size - observation_size
                if sell_size > 0:
                    self.sell(data=data, size=sell_size)
                    self.log(f"保留观察仓位: {data._name}, 数量: {observation_size}")
            else:
                # 一次性清空所有仓位
                self.sell(data=data, size=position.size)

    def stop(self):
        """策略结束时调用"""
        self.log("策略结束")
