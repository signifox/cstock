import numpy as np


class RiskManager:
    def __init__(
        self,
        max_position_size,
        stop_loss_pct,
        take_profit_pct,
    ):
        """
        初始化风险管理器

        参数:
            max_position_size (float): 单个头寸最大仓位比例（占总资金的比例）
            stop_loss_pct (float): 止损百分比
            take_profit_pct (float): 止盈百分比
        """
        self.max_position_size = max_position_size
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.highest_price = {}

    def calculate_position_size(self, cash, price, symbol=None):
        """
        计算建仓数量，考虑风险因素动态调整仓位

        参数:
            cash (float): 当前可用资金
            price (float): 当前价格
            symbol (str, optional): 交易标的代码

        返回:
            int: 建议的建仓数量
        """
        # 计算基础仓位
        max_cash = cash * self.max_position_size
        base_size = int(max_cash / price)

        return max(0, base_size)

    def should_stop_loss(self, entry_price, current_price, direction="long"):
        """
        检查是否应该止损

        参数:
            entry_price (float): 入场价格
            current_price (float): 当前价格
            direction (str): 交易方向，'long'或'short'

        返回:
            bool: 是否应该止损
        """
        if direction == "long":
            pnl_pct = (current_price - entry_price) / entry_price
            return pnl_pct < -self.stop_loss_pct
        else:  # short
            pnl_pct = (entry_price - current_price) / entry_price
            return pnl_pct < -self.stop_loss_pct

    def should_take_profit(self, entry_price, current_price, direction="long"):
        """
        检查是否应该止盈

        参数:
            entry_price (float): 入场价格
            current_price (float): 当前价格
            direction (str): 交易方向，'long'或'short'

        返回:
            bool: 是否应该止盈
        """
        if direction == "long":
            return current_price > entry_price * (1 + self.take_profit_pct)
        else:  # short
            return current_price < entry_price * (1 - self.take_profit_pct)
