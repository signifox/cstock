import backtrader as bt
from cstock.risk_manager import RiskManager
from cstock.single_stock_analyzer import SingleStockAnalyzer


class BaseStrategy(bt.Strategy):
    """Base strategy class providing common functionality and helper methods.
    All custom strategies should inherit from this base class.
    """

    params = (
        ("max_position_size", 0.3),  # Maximum position size ratio
        ("stop_loss_pct", 0.1),  # Stop loss percentage
        ("take_profit_pct", 0.2),  # Take profit percentage
    )

    def __init__(self):
        # Track orders
        self.orders = {}

        # Initialize risk manager
        self.risk_manager = RiskManager(
            stop_loss_pct=self.params.stop_loss_pct,
            take_profit_pct=self.params.take_profit_pct,
            max_position_size=self.params.max_position_size,
        )

        # Initialize analyzer for each data source
        self.stock_analyzers = {}
        for data in self.datas:
            self.stock_analyzers[data._name] = SingleStockAnalyzer(data._name)

    def log(self, txt, dt=None):
        """Log strategy information"""
        dt = dt or self.datas[0].datetime.date(0)
        print(f"{dt.isoformat()}, {txt}")

    def notify_order(self, order):
        """Order status update notification"""
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            position = self.getposition(order.data)

            if order.isbuy():
                self.log(
                    f"BUY EXECUTED: {order.data._name}, Price: {order.executed.price:.2f}, "
                    f"Size: {order.executed.size}, Value: {order.executed.value:.2f}, "
                    f"Commission: {order.executed.comm:.2f}"
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
                    f"SELL EXECUTED: {order.data._name}, Price: {order.executed.price:.2f}, "
                    f"Size: {order.executed.size}, Value: {abs(order.executed.value):.2f}, "
                    f"Commission: {order.executed.comm:.2f}"
                )
                # Remove position from risk manager
                self.risk_manager.remove_position(order.data._name)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            error_type = {
                order.Canceled: "Order Canceled",
                order.Margin: "Margin Insufficient",
                order.Rejected: "Order Rejected",
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
            f"TRADE PROFIT: {trade.data._name}, Gross: {trade.pnl:.2f}, "
            f"Net: {trade.pnlcomm:.2f}"
        )

        # Update stock analyzer
        if trade.data._name in self.stock_analyzers:
            self.stock_analyzers[trade.data._name].update_trade(trade)

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
                rsi = indicators[data._name].get("rsi", [None])[0]

            should_exit, exit_type = self.risk_manager.check_exit_signals(
                data._name, data.close[0], rsi
            )

            if should_exit:
                self.log(f"{exit_type.upper()} TRIGGERED: {data._name}")
                self.sell_position(data)

    def next(self):
        """Main strategy logic should be implemented in subclasses"""
        self.risk_manager.reset_daily_cash()
        # Check stop loss and take profit signals
        self.check_exit_signals()

    def start(self):
        """Called when strategy starts"""
        self.log("Strategy Started")

    def sell_position(self, data):
        """Sell position"""
        position = self.getposition(data)
        if not position.size:
            return 0

        # Skip if the symbol has already executed a sell operation in current bar
        if data._name in self.orders and self.orders[data._name] is not None:
            print(f"Warning, {data._name} has already been sold in this bar")
            return 0

        # Clear all positions at once
        sell_size = position.size
        self.orders[data._name] = self.sell(data=data, size=sell_size)
        return sell_size

    def stop(self):
        """Called when strategy ends"""
        self.log("Strategy Ended")

        # Print statistics for all stocks using unified table format
        SingleStockAnalyzer.print_all_summaries(self.stock_analyzers.values())
