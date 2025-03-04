import numpy as np


class RiskManager:
    def __init__(
        self,
        max_position_size=0.2,
        stop_loss_pct=0.05,
        take_profit_pct=0.15,
        trailing_stop_loss_pct=0.05,
        trailing_take_profit_pct=0.05,
        max_drawdown_pct=0.1,
    ):
        """
        初始化风险管理器

        参数:
            max_position_size (float): 单个头寸最大仓位比例（占总资金的比例）
            stop_loss_pct (float): 止损百分比
            take_profit_pct (float): 止盈百分比
            trailing_stop_loss_pct (float): 追踪止损百分比
            trailing_take_profit_pct (float): 追踪止盈百分比
            max_drawdown_pct (float): 最大回撤限制
        """
        self.max_position_size = max_position_size
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.trailing_stop_loss_pct = trailing_stop_loss_pct
        self.trailing_take_profit_pct = trailing_take_profit_pct
        self.max_drawdown_pct = max_drawdown_pct
        self.highest_price = {}
        self.lowest_price = {}
        self.initial_equity = None
        self.current_drawdown = 0

    def calculate_position_size(self, cash, price, volatility=None, symbol=None):
        """
        计算建仓数量，考虑风险因素动态调整仓位

        参数:
            cash (float): 当前可用资金
            price (float): 当前价格
            volatility (float, optional): 波动率
            symbol (str, optional): 交易标的代码

        返回:
            int: 建议的建仓数量
        """
        # 初始化账户权益
        if self.initial_equity is None:
            self.initial_equity = cash

        # 计算当前回撤
        self.current_drawdown = max(
            0, (self.initial_equity - cash) / self.initial_equity
        )

        # 如果超过最大回撤限制，不开新仓
        if self.current_drawdown >= self.max_drawdown_pct:
            return 0

        # 基础仓位计算
        position_factor = 1 - (self.current_drawdown / self.max_drawdown_pct)
        max_cash = cash * self.max_position_size * position_factor

        base_size = int(max_cash / price)

        # 根据波动率调整仓位
        if volatility is not None:
            risk_factor = 1 / (1 + volatility)
            base_size = int(base_size * risk_factor)

        return max(0, base_size)

    def should_stop_loss(
        self, entry_price, current_price, direction="long", symbol=None
    ):
        """
        检查是否应该止损

        参数:
            entry_price (float): 入场价格
            current_price (float): 当前价格
            direction (str): 交易方向，'long'或'short'
            symbol (str, optional): 交易标的代码

        返回:
            dict: 包含止损信息的字典，包括：
                - should_stop (bool): 是否应该止损
                - stop_type (str): 止损类型（'fixed'或'trailing'）
                - loss_pct (float): 当前亏损百分比
                - drop_from_high (float): 从最高点的回撤百分比
        """
        # 初始化变量
        loss_pct = 0
        fixed_stop = False
        drop_from_high = 0

        if direction == "long":
            # 计算当前盈亏百分比（正值表示盈利，负值表示亏损）
            pnl_pct = (current_price - entry_price) / entry_price
            
            # 检查固定止损（只在亏损时判断）
            if pnl_pct < 0:  # 只在亏损时检查固定止损
                loss_pct = abs(pnl_pct)
                fixed_stop = loss_pct > self.stop_loss_pct
            
            # 更新最高价格并计算回撤
            if symbol not in self.highest_price:
                self.highest_price[symbol] = current_price
            else:
                self.highest_price[symbol] = max(self.highest_price[symbol], current_price)
            
            if self.highest_price[symbol] > 0:
                drop_from_high = ((self.highest_price[symbol] - current_price) / self.highest_price[symbol]) * 100
            
            return {
                "should_stop": fixed_stop,
                "stop_type": "fixed" if fixed_stop else None,
                "loss_pct": loss_pct * 100,  # 转换为百分比
                "drop_from_high": drop_from_high  # 从最高点的回撤百分比
            }
        else:  # short
            # 计算当前盈亏百分比（正值表示盈利，负值表示亏损）
            pnl_pct = (entry_price - current_price) / entry_price
            
            # 检查固定止损（只在亏损时判断）
            if pnl_pct < 0:  # 只在亏损时检查固定止损
                loss_pct = abs(pnl_pct)
                fixed_stop = loss_pct > self.stop_loss_pct
            
            return {
                "should_stop": fixed_stop,
                "stop_type": "fixed" if fixed_stop else None,
                "loss_pct": loss_pct * 100  # 转换为百分比
            }

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

    def calculate_volatility(self, prices, window=20):
        """
        计算价格波动率

        参数:
            prices (list): 历史价格列表
            window (int): 计算窗口

        返回:
            float: 波动率
        """
        if len(prices) < window:
            return None

        # 将价格列表转换为numpy数组并计算对数收益率
        prices_array = np.array(prices)
        returns = np.log(prices_array[1:] / prices_array[:-1])

        # 计算波动率（标准差）
        volatility = np.std(returns[-window:]) * np.sqrt(252)  # 年化波动率

        return volatility
