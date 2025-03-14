class RiskManager:
    """
    Risk Manager responsible for managing trading risk control, including position management,
    take profit and stop loss functionality.
    """

    def __init__(self, stop_loss_pct=0.1, take_profit_pct=0.2, max_position_size=0.3):
        """
        Initialize Risk Manager

        Parameters:
            stop_loss_pct (float): Stop loss percentage, default 10%
            take_profit_pct (float): Base take profit percentage, default 20%
            max_position_size (float): Maximum position size ratio, default 30%
        """
        self.stop_loss_pct = stop_loss_pct
        self.base_take_profit_pct = take_profit_pct  # Base take profit percentage
        self.max_position_size = max_position_size
        self.positions = {}
        self._today_used_cash = 0.0  # Track daily used cash

        # Dynamic take profit parameters
        self.rsi_threshold = 70  # RSI overbought threshold
        self.trend_bonus = 0.1  # Trend strength bonus for take profit (10%)

    def reset_daily_cash(self):
        """Reset daily used cash statistics"""
        self._today_used_cash = 0.0

    def add_position(self, symbol, entry_price):
        """
        Add new position record

        Parameters:
            symbol (str): Stock symbol
            entry_price (float): Entry price
        """
        self.positions[symbol] = {
            "entry_price": entry_price,
            "stop_loss_price": entry_price * (1 - self.stop_loss_pct),
            "take_profit_price": entry_price * (1 + self.base_take_profit_pct),
        }

    def remove_position(self, symbol):
        """
        Remove position record

        Parameters:
            symbol (str): Stock symbol
        """
        if symbol in self.positions:
            del self.positions[symbol]

    def check_exit_signals(self, symbol, current_price, rsi=None, volume_ratio=None):
        """
        Check if take profit or stop loss signals are triggered, supports dynamic take profit

        Parameters:
            symbol (str): Stock symbol
            current_price (float): Current price
            rsi (float): Current RSI value for trend strength evaluation
            volume_ratio (float): Current volume ratio relative to moving average

        Returns:
            tuple: (should_exit, exit_type)
            - should_exit (bool): Whether to exit the position
            - exit_type (str): Exit type ('stop_loss' or 'take_profit')
        """
        if symbol not in self.positions:
            return False, None

        position = self.positions[symbol]
        entry_price = position["entry_price"]

        # Calculate current return
        current_return = (current_price - entry_price) / entry_price

        # Check stop loss condition
        if current_price <= position["stop_loss_price"]:
            return True, "stop_loss"

        # Dynamically adjust take profit percentage
        take_profit_pct = self.base_take_profit_pct

        # Evaluate trend strength based on RSI and volume
        if rsi is not None and volume_ratio is not None:
            trend_strength = 0

            # Strong trend indicated by RSI
            if rsi > self.rsi_threshold:
                trend_strength += 1

            # Increase take profit target based on trend strength
            take_profit_pct += trend_strength * self.trend_bonus

            # Update take profit price
            position["take_profit_price"] = entry_price * (1 + take_profit_pct)

        # Check take profit condition
        if current_price >= position["take_profit_price"]:
            return True, "take_profit"

        return False, None

    def update_position_params(self, symbol, stop_loss_pct=None, take_profit_pct=None):
        """
        Update stop loss and take profit parameters for specific position

        Parameters:
            symbol (str): Stock symbol
            stop_loss_pct (float): New stop loss percentage
            take_profit_pct (float): New take profit percentage
        """
        if symbol not in self.positions:
            return

        position = self.positions[symbol]
        entry_price = position["entry_price"]

        if stop_loss_pct is not None:
            position["stop_loss_price"] = entry_price * (1 - stop_loss_pct)

        if take_profit_pct is not None:
            position["take_profit_price"] = entry_price * (1 + take_profit_pct)

    def get_position_size(self, data, broker):
        """Calculate position size based on available cash and maximum position ratio

        Parameters:
            data: Trading data object
            broker: Broker object

        Returns:
            int: Recommended position size
        """
        symbol = data._name
        current_time = data.datetime.datetime(0)
        current_price = data.close[0]

        # Calculate total value of current positions
        total_position_value = 0
        # Get strategy instance through data object
        strategy = data._owner
        if strategy and hasattr(strategy, "datas"):
            for d in strategy.datas:
                position = broker.getposition(d)
                if position.size:
                    # Calculate market value using current price
                    current_price = d.close[0]
                    total_position_value += position.size * current_price

        # Calculate total assets
        total_value = broker.getvalue()
        # Calculate maximum allowed position value
        max_total_position = total_value * self.max_position_size
        # Calculate remaining available position value
        remaining_position = max_total_position - total_position_value

        # If maximum position reached, no new positions
        if remaining_position <= 0:
            return 0

        # Calculate available cash
        available_cash = min(broker.getcash(), remaining_position)
        price = data.close[0]

        # Check if enough cash for at least 1 share
        if available_cash < price:
            return 0

        # Calculate number of shares to buy
        return int(available_cash // price)
