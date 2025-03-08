from dataclasses import dataclass, field
from typing import Dict, List
from datetime import datetime


@dataclass
class TradeRecord:
    """单笔交易记录"""
    symbol: str  # 交易标的
    entry_time: datetime  # 入场时间
    entry_price: float  # 入场价格
    size: int  # 交易数量
    direction: str  # 交易方向 ('buy' 或 'sell')
    commission: float  # 手续费
    exit_time: datetime = None  # 出场时间
    exit_price: float = 0.0  # 出场价格
    pnl: float = 0.0  # 交易盈亏
    exit_type: str = ''  # 出场类型 ('stop_loss', 'take_profit', 'signal', 等)


class OrderMetric:
    """订单度量统计类，用于记录和分析交易数据"""

    def __init__(self):
        self.trades: List[TradeRecord] = []  # 所有交易记录
        self.active_trades: Dict[str, TradeRecord] = {}  # 当前活跃的交易
        
        # 统计指标
        self.total_trades = 0  # 总交易次数
        self.winning_trades = 0  # 盈利交易次数
        self.losing_trades = 0  # 亏损交易次数
        self.total_pnl = 0.0  # 总盈亏
        self.max_profit = 0.0  # 最大单笔盈利
        self.max_loss = 0.0  # 最大单笔亏损
        self.total_commission = 0.0  # 总手续费
        
        # 持仓相关统计
        self.holding_periods: List[int] = []  # 持仓周期列表（以天为单位）
        self.exit_types: Dict[str, int] = {  # 出场类型统计
            'stop_loss': 0,
            'take_profit': 0,
            'signal': 0
        }

    def on_trade_entry(self, symbol: str, entry_time: datetime, entry_price: float,
                      size: int, direction: str, commission: float):
        """记录交易入场"""
        trade = TradeRecord(
            symbol=symbol,
            entry_time=entry_time,
            entry_price=entry_price,
            size=size,
            direction=direction,
            commission=commission
        )
        self.active_trades[symbol] = trade

    def on_trade_exit(self, symbol: str, exit_time: datetime, exit_price: float,
                     commission: float, exit_type: str = 'signal'):
        """记录交易出场"""
        if symbol not in self.active_trades:
            return

        trade = self.active_trades[symbol]
        trade.exit_time = exit_time
        trade.exit_price = exit_price
        trade.commission += commission
        trade.exit_type = exit_type

        # 计算交易盈亏
        if trade.direction == 'buy':
            trade.pnl = (exit_price - trade.entry_price) * trade.size - trade.commission
        else:  # sell
            trade.pnl = (trade.entry_price - exit_price) * trade.size - trade.commission

        # 更新统计指标
        self.total_trades += 1
        self.total_pnl += trade.pnl
        self.total_commission += trade.commission

        if trade.pnl > 0:
            self.winning_trades += 1
            self.max_profit = max(self.max_profit, trade.pnl)
        else:
            self.losing_trades += 1
            self.max_loss = min(self.max_loss, trade.pnl)

        # 更新持仓周期
        holding_days = (exit_time - trade.entry_time).days
        self.holding_periods.append(holding_days)

        # 更新出场类型统计
        if exit_type in self.exit_types:
            self.exit_types[exit_type] += 1

        # 保存交易记录并清理活跃交易
        self.trades.append(trade)
        del self.active_trades[symbol]

    def get_metrics(self) -> dict:
        """获取统计指标"""
        if not self.total_trades:
            return {
                'total_trades': 0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'avg_holding_period': 0.0
            }

        win_rate = (self.winning_trades / self.total_trades) * 100
        avg_holding_period = sum(self.holding_periods) / len(self.holding_periods)

        return {
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': win_rate,
            'total_pnl': self.total_pnl,
            'max_profit': self.max_profit,
            'max_loss': self.max_loss,
            'total_commission': self.total_commission,
            'avg_holding_period': avg_holding_period,
            'exit_types': self.exit_types
        }