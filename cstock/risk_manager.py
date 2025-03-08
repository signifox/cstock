class RiskManager:
    """
    风险管理器，负责管理交易的风险控制，包括仓位管理、止盈和止损功能
    """
    def __init__(self, stop_loss_pct=0.1, take_profit_pct=0.2, max_position_size=0.3, cooling_days=3, price_retracement=0.02):
        """
        初始化风险管理器

        参数:
            stop_loss_pct (float): 止损百分比，默认为10%
            take_profit_pct (float): 基础止盈百分比，默认为20%
            max_position_size (float): 最大仓位比例，默认为30%
            cooling_days (int): 止盈后的冷却天数，默认为3天
            price_retracement (float): 价格回调比例，默认为2%
        """
        self.stop_loss_pct = stop_loss_pct
        self.base_take_profit_pct = take_profit_pct  # 基础止盈比例
        self.max_position_size = max_position_size
        self.cooling_days = cooling_days
        self.price_retracement = price_retracement
        self.positions = {}
        self._today_used_cash = 0.0  # 记录当日已使用的资金
        self.cooling_stocks = {}  # 记录处于冷却期的股票信息
        
        # 动态止盈参数
        self.rsi_threshold = 70  # RSI超买阈值
        self.volume_mult_threshold = 1.5  # 成交量放大倍数阈值
        self.trend_bonus = 0.1  # 强势趋势额外止盈加成（10%）

    def reset_daily_cash(self):
        """重置每日已使用资金统计"""
        self._today_used_cash = 0.0

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
            'take_profit_price': entry_price * (1 + self.base_take_profit_pct)
        }

    def remove_position(self, symbol):
        """
        移除持仓记录

        参数:
            symbol (str): 股票代码
        """
        if symbol in self.positions:
            del self.positions[symbol]

    def check_exit_signals(self, symbol, current_price, rsi=None, volume_ratio=None):
        """
        检查是否触发止盈止损信号，支持动态止盈

        参数:
            symbol (str): 股票代码
            current_price (float): 当前价格
            rsi (float): 当前RSI值，用于判断趋势强度
            volume_ratio (float): 当前成交量相对均线倍数

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

        # 动态调整止盈比例
        take_profit_pct = self.base_take_profit_pct
        
        # 根据RSI和成交量判断趋势强度
        if rsi is not None and volume_ratio is not None:
            trend_strength = 0
            
            # RSI指标显示强势
            if rsi > self.rsi_threshold:
                trend_strength += 1
                
            # 成交量显著放大
            if volume_ratio > self.volume_mult_threshold:
                trend_strength += 1
                
            # 根据趋势强度增加止盈目标
            take_profit_pct += trend_strength * self.trend_bonus
            
            # 更新止盈价格
            position['take_profit_price'] = entry_price * (1 + take_profit_pct)

        # 检查止盈条件
        if current_price >= position['take_profit_price']:
            # 记录止盈信息，包括时间和价格
            self.cooling_stocks[symbol] = {
                'exit_price': current_price
            }
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
        symbol = data._name
        current_time = data.datetime.datetime(0)
        current_price = data.close[0]

        # 检查是否在冷却期
        if symbol in self.cooling_stocks:
            cooling_info = self.cooling_stocks[symbol]
            days_passed = (current_time - cooling_info['exit_time']).days
            price_drop = (cooling_info['exit_price'] - current_price) / cooling_info['exit_price']

            # 如果未满足冷却条件（天数和价格回调），则不允许建仓
            if days_passed < self.cooling_days and price_drop < self.price_retracement:
                return 0
            else:
                # 满足条件后，移除冷却记录
                del self.cooling_stocks[symbol]
        # 计算当前所有持仓的总市值
        total_position_value = 0
        # 通过data对象获取策略实例
        strategy = data._owner
        if strategy and hasattr(strategy, 'datas'):
            for d in strategy.datas:
                position = broker.getposition(d)
                if position.size:
                    # 使用当前价格计算市值
                    current_price = d.close[0]
                    total_position_value += position.size * current_price

        # 计算当前总资产
        total_value = broker.getvalue()
        # 计算最大允许的总仓位市值
        max_total_position = total_value * self.max_position_size
        # 计算还可以使用的仓位市值
        remaining_position = max_total_position - total_position_value

        # 如果已经达到或超过最大仓位，不再开新仓
        if remaining_position <= 0:
            return 0

        # 计算可用现金
        available_cash = min(broker.getcash(), remaining_position)
        price = data.close[0]

        # 检查是否有足够资金购买至少1股
        if available_cash < price:
            return 0

        # 计算可以购买的股票数量
        return int(available_cash // price)