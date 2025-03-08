class RiskManager:
    """
    风险管理器，负责管理交易的风险控制，包括仓位管理、止盈和止损功能
    """
    def __init__(self, stop_loss_pct=0.1, take_profit_pct=0.2, max_position_size=0.3):
        """
        初始化风险管理器

        参数:
            stop_loss_pct (float): 止损百分比，默认为10%
            take_profit_pct (float): 止盈百分比，默认为20%
            max_position_size (float): 最大仓位比例，默认为30%
        """
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.max_position_size = max_position_size
        self.positions = {}
        self._today_used_cash = 0

    def add_position(self, symbol, entry_price):
        """
        添加新的持仓记录

        参数:
            symbol (str): 股票代码
            entry_price (float): 入场价格
        """
        self.positions[symbol] = {
            'entry_price': entry_price,
            'stop_loss_price': entry_price * (1 - self.stop_loss_pct),
            'take_profit_price': entry_price * (1 + self.take_profit_pct)
        }

    def remove_position(self, symbol):
        """
        移除持仓记录

        参数:
            symbol (str): 股票代码
        """
        if symbol in self.positions:
            del self.positions[symbol]

    def check_exit_signals(self, symbol, current_price):
        """
        检查是否触发止盈止损信号

        参数:
            symbol (str): 股票代码
            current_price (float): 当前价格

        返回:
            tuple: (should_exit, exit_type)
            - should_exit (bool): 是否应该退出
            - exit_type (str): 退出类型 ('stop_loss' 或 'take_profit')
        """
        if symbol not in self.positions:
            return False, None

        position = self.positions[symbol]
        entry_price = position['entry_price']

        # 计算当前收益率
        current_return = (current_price - entry_price) / entry_price

        # 检查止损条件
        if current_price <= position['stop_loss_price']:
            return True, 'stop_loss'

        # 检查止盈条件
        if current_price >= position['take_profit_price']:
            return True, 'take_profit'

        return False, None

    def update_position_params(self, symbol, stop_loss_pct=None, take_profit_pct=None):
        """
        更新特定持仓的止盈止损参数

        参数:
            symbol (str): 股票代码
            stop_loss_pct (float): 新的止损百分比
            take_profit_pct (float): 新的止盈百分比
        """
        if symbol not in self.positions:
            return

        position = self.positions[symbol]
        entry_price = position['entry_price']

        if stop_loss_pct is not None:
            position['stop_loss_price'] = entry_price * (1 - stop_loss_pct)

        if take_profit_pct is not None:
            position['take_profit_price'] = entry_price * (1 + take_profit_pct)

    def get_position_size(self, data, broker):
        """计算建仓数量，根据可用现金和最大仓位比例

        参数:
            data: 交易数据对象
            broker: 交易代理对象

        返回:
            int: 建议的建仓数量
        """
        # 计算当前总持仓市值
        total_position_value = 0
        position = broker.getposition(data)
        if position.size:
            total_position_value += position.size * data.close[0]

        # 计算当前总资产
        total_value = broker.getvalue()
        # 计算最大允许的总仓位市值
        max_total_position = total_value * self.max_position_size
        # 计算还可以使用的仓位市值
        remaining_position = max_total_position - total_position_value

        # 如果已经达到或超过最大仓位，不再开新仓
        if remaining_position <= 0:
            return 0

        # 计算可用现金（考虑当日已使用资金）
        available_cash = min(
            broker.getcash() - self._today_used_cash, remaining_position
        )

        price = data.close[0]

        # 计算可以购买的股票数量
        suggested_size = available_cash // price

        # 更新当日已使用资金
        if suggested_size > 0:
            self._today_used_cash += price * suggested_size

        return suggested_size

    def reset_daily_cash(self):
        """重置当日已使用资金"""
        self._today_used_cash = 0