import backtrader as bt
from cstock.risk_manager import RiskManager


class BaseStrategy(bt.Strategy):
    """Base strategy class providing common functionality and helper methods.
    All custom strategies should inherit from this base class.
    """

    params = (
        ("max_position_size", 0.4),  # Maximum position size ratio
        ("stop_loss_pct", 0.1),  # Stop loss percentage
        ("take_profit_pct", 0.2),  # Take profit percentage
    )

    def __init__(self):
        # Track orders
        self.orders = {}
        # Track stock symbols
        self._symbol_map = {}
        self._next_symbol_id = 0

        # Initialize risk manager
        self.risk_manager = RiskManager(
            stop_loss_pct=self.params.stop_loss_pct,
            take_profit_pct=self.params.take_profit_pct,
            max_position_size=self.params.max_position_size,
        )

    def _get_symbol_id(self, symbol):
        """Get numeric ID for stock symbol"""
        if symbol not in self._symbol_map:
            self._symbol_map[symbol] = self._next_symbol_id
            self._next_symbol_id += 1
        return self._symbol_map[symbol]

    def log(self, txt, dt=None):
        """Log strategy information"""
        dt = dt or self.datas[0].datetime.date(0)
        # Replace stock symbols with numeric IDs
        for symbol, symbol_id in self._symbol_map.items():
            txt = txt.replace(symbol, str(symbol_id))
        print(f"{dt.isoformat()}, {txt}")

    def notify_order(self, order):
        """Order status update notification"""
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            position = self.getposition(order.data)

            if order.isbuy():
                self.log(
                    f"买入: {order.data._name}, 价格: {order.executed.price:.2f}, "
                    f"数量: {order.executed.size}, 金额: {order.executed.value:.2f}, "
                    f"手续费: {order.executed.comm:.2f}"
                )
                # Add new position to risk manager
                self.risk_manager.add_position(order.data._name, order.executed.price)

            else:  # Sell order
                if position.size < 0:
                    self.log(
                        f"WARNING: {order.data._name} has negative position, attempting to fix"
                    )
                    self.cancel(order)
                    return

                self.log(
                    f"卖出: {order.data._name}, 价格: {order.executed.price:.2f}, "
                    f"数量: {order.executed.size}, 金额: {abs(order.executed.value):.2f}, "
                    f"手续费: {order.executed.comm:.2f}"
                )
                # Remove position from risk manager
                self.risk_manager.remove_position(order.data._name)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            error_type = {
                order.Canceled: "订单已取消",
                order.Margin: "保证金不足",
                order.Rejected: "订单被拒绝",
            }.get(order.status)
            error_detail = f"{error_type}: {order.data._name}"
            if hasattr(order, "info") and order.info:
                error_detail += f", Reason: {order.info}"
            self.log(error_detail)

        self.orders[order.data._name] = None

    def notify_trade(self, trade):
        """Trade status update notification"""
        if not trade.isclosed:
            return

        self.log(
            f"交易利润: {trade.data._name}, 毛利: {trade.pnl:.2f}, "
            f"净利: {trade.pnlcomm:.2f}"
        )

    def get_position_size(self, data):
        """Calculate position size using risk manager for position management"""
        return self.risk_manager.get_position_size(data, self.broker)

    def check_exit_signals(self):
        """Check if positions need to be exited"""
        for data in self.datas:
            if not self.getposition(data).size:
                continue

            # Check if stop loss or take profit is triggered
            # Get current RSI value
            indicators = getattr(self, "indicators", {})
            rsi = None
            if data._name in indicators:
                rsi = indicators[data._name]["rsi"][0]

            should_exit, exit_type = self.risk_manager.check_exit_signals(
                data._name, data.close[0], rsi
            )

            if should_exit:
                exit_type_cn = "触发止损" if exit_type == "stop_loss" else "触发止盈"
                self.log(f"{exit_type_cn}: {data._name}")
                self.sell_position(data)

    def next(self):
        """Main strategy logic should be implemented in subclasses"""
        # Check stop loss and take profit signals
        self.check_exit_signals()

    def start(self):
        """Called when strategy starts"""
        self.log("策略启动")

    def sell_position(self, data):
        """Sell position"""
        position = self.getposition(data)
        if not position.size:
            return 0

        # Skip if the symbol has already executed a sell operation in current bar
        if data._name in self.orders and self.orders[data._name] is not None:
            print(f"警告: {data._name} 在当前周期已经卖出")
            return 0

        # Clear all positions at once
        sell_size = position.size
        self.orders[data._name] = self.sell(data=data, size=sell_size)
        return sell_size

    def stop(self):
        """Called when strategy ends"""
        self.log("策略结束")
