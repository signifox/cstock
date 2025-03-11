import backtrader as bt
from datetime import datetime


class SingleStockAnalyzer:
    """单只股票分析器，用于记录和分析单只股票的交易表现"""

    def __init__(self, stock_name):
        """初始化分析器

        参数:
            stock_name (str): 股票代码
        """
        self.stock_name = stock_name
        self.reset()

    def reset(self):
        """重置所有统计数据"""
        self.total_trades = 0  # 总交易次数
        self.winning_trades = 0  # 盈利次数
        self.losing_trades = 0  # 亏损次数
        self.total_profit = 0.0  # 总收益
        self.total_commission = 0.0  # 总手续费
        self.max_drawdown = 0.0  # 最大回撤
        self.peak_value = 0.0  # 历史最高值
        self.current_value = 0.0  # 当前市值
        self.returns = []  # 收益率记录
        self.trades_history = []  # 交易历史记录
        self.current_position = 0  # 当前持仓量
        self.entry_price = 0.0  # 开仓价格
        self.last_trade_time = None  # 最后交易时间

    def update_trade(self, trade):
        """更新交易统计信息

        参数:
            trade: Backtrader的Trade对象
        """
        if trade.isclosed:
            self.total_trades += 1
            profit = trade.pnl
            self.total_profit += profit
            self.total_commission += trade.commission

            if profit > 0:
                self.winning_trades += 1
            else:
                self.losing_trades += 1

            # 记录交易历史
            trade_record = {
                'time': bt.num2date(trade.dtclose),
                'type': 'SELL' if trade.size < 0 else 'BUY',
                'size': abs(trade.size),
                'price': trade.price,
                'profit': profit,
                'commission': trade.commission
            }
            self.trades_history.append(trade_record)
            self.last_trade_time = trade_record['time']

    def update_value(self, position_size, current_price, current_time):
        """更新持仓市值和回撤信息

        参数:
            position_size (int): 当前持仓数量
            current_price (float): 当前价格
            current_time (datetime): 当前时间
        """
        self.current_position = position_size
        self.current_value = position_size * current_price

        # 添加调试日志
        print(f"{current_time}: 当前持仓 {position_size}, 当前价格 {current_price:.2f}, 当前市值 {self.current_value:.2f}")

        if self.peak_value == 0:
            self.peak_value = self.current_value
        else:
            self.peak_value = max(self.peak_value, self.current_value)
            print(f"更新峰值: {self.peak_value:.2f}")

        if self.peak_value > 0:
            drawdown = (self.peak_value - self.current_value) / self.peak_value
            self.max_drawdown = max(self.max_drawdown, drawdown)
            print(f"当前回撤: {drawdown:.2%}, 最大回撤: {self.max_drawdown:.2%}")

    def get_summary(self):
        """获取统计摘要"""
        win_rate = self.winning_trades / self.total_trades if self.total_trades > 0 else 0
        avg_profit = self.total_profit / self.total_trades if self.total_trades > 0 else 0

        return {
            '股票代码': self.stock_name,
            '总交易次数': self.total_trades,
            '盈利次数': self.winning_trades,
            '亏损次数': self.losing_trades,
            '胜率': win_rate,
            '总收益': self.total_profit,
            '平均每笔收益': avg_profit,
            '总手续费': self.total_commission,
            '最大回撤': self.max_drawdown,
            '当前持仓': self.current_position
        }

    @staticmethod
    def print_all_summaries(analyzers):
        """打印所有股票的统计摘要，使用统一的表格格式

        参数:
            analyzers (list): SingleStockAnalyzer对象列表
        """
        if not analyzers:
            return

        # 获取所有股票的摘要数据
        all_summaries = [analyzer.get_summary() for analyzer in analyzers]

        # 计算每个字段的最大长度，用于对齐
        max_lengths = {}
        for summary in all_summaries:
            for key, value in summary.items():
                value_str = str(value)
                if isinstance(value, float):
                    if '率' in key:
                        value_str = f"{value:.2%}"
                    else:
                        value_str = f"{value:.2f}"
                max_lengths[key] = max(max_lengths.get(key, len(key)), len(value_str))

        # 打印表头
        header = ""
        separator = ""
        for key in all_summaries[0].keys():
            width = max_lengths[key] + 2  # 添加2个空格的padding
            header += f"{key:^{width}}"
            separator += "-" * width

        print("\n" + header)
        print(separator)

        # 打印每只股票的数据行
        for summary in all_summaries:
            row = ""
            for key, value in summary.items():
                width = max_lengths[key] + 2  # 添加2个空格的padding
                if isinstance(value, float):
                    if '率' in key:
                        row += f"{value:>{width}.2%}"
                    else:
                        row += f"{value:>{width}.2f}"
                else:
                    row += f"{value:^{width}}"
            print(row)

        print("\n")