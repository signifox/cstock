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
        
        # 单只股票回撤统计
        self.stock_metrics: Dict[str, Dict] = {}  # 每只股票的度量数据
        # 单只股票统计数据
        self.stock_stats: Dict[str, Dict] = {}  # 每只股票的统计数据
        
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
        
        # 初始化或更新股票度量数据
        if symbol not in self.stock_metrics:
            self.stock_metrics[symbol] = {
                'highest_value': entry_price * size,
                'max_drawdown': 0.0,
                'current_drawdown': 0.0
            }

    def on_trade_exit(self, symbol: str, exit_time: datetime, exit_price: float,
                     commission: float, exit_type: str = 'signal'):
        """记录交易出场"""
        if symbol not in self.active_trades:
            return
            
        # 更新股票回撤数据
        if symbol in self.stock_metrics:
            current_value = exit_price * self.active_trades[symbol].size
            metrics = self.stock_metrics[symbol]
            
            # 只在持仓期间更新最高价值
            metrics['highest_value'] = max(metrics['highest_value'], current_value)
            
            if metrics['highest_value'] > 0:
                current_drawdown = ((metrics['highest_value'] - current_value) / metrics['highest_value']) * 100
                metrics['current_drawdown'] = current_drawdown
                metrics['max_drawdown'] = max(metrics['max_drawdown'], current_drawdown)
                
                print(f"[回撤计算] {symbol} - 当前价值: {current_value:.2f}, 最高价值: {metrics['highest_value']:.2f}, "
                      f"当前回撤: {current_drawdown:.2f}%, 最大回撤: {metrics['max_drawdown']:.2f}%")
            
            # 清仓时重置最高价值，为下次建仓做准备
            metrics['highest_value'] = 0.0
            metrics['current_drawdown'] = 0.0

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

        # 初始化或更新股票统计数据
        if symbol not in self.stock_stats:
            self.stock_stats[symbol] = {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'total_pnl': 0.0,
                'max_profit': 0.0,
                'max_loss': 0.0,
                'total_commission': 0.0
            }

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
            
        # 更新股票统计数据
        stats = self.stock_stats[symbol]
        stats['total_trades'] += 1
        stats['total_pnl'] += trade.pnl
        stats['total_commission'] += trade.commission
        
        if trade.pnl > 0:
            stats['winning_trades'] += 1
            stats['max_profit'] = max(stats['max_profit'], trade.pnl)
        else:
            stats['losing_trades'] += 1
            stats['max_loss'] = min(stats['max_loss'], trade.pnl)

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
                'avg_holding_period': 0.0,
                'stock_drawdowns': {}
            }

        win_rate = (self.winning_trades / self.total_trades) * 100
        avg_holding_period = sum(self.holding_periods) / len(self.holding_periods)

        # 整理每只股票的回撤数据
        stock_drawdowns = {}
        for symbol, metrics in self.stock_metrics.items():
            stock_drawdowns[symbol] = {
                'max_drawdown': metrics['max_drawdown'],
                'current_drawdown': metrics['current_drawdown']
            }

        # 整理每只股票的统计数据
        stock_statistics = {}
        for symbol, stats in self.stock_stats.items():
            total_trades = stats['total_trades']
            win_rate = (stats['winning_trades'] / total_trades * 100) if total_trades > 0 else 0.0
            stock_statistics[symbol] = {
                'total_trades': total_trades,
                'winning_trades': stats['winning_trades'],
                'losing_trades': stats['losing_trades'],
                'win_rate': win_rate,
                'total_pnl': stats['total_pnl'],
                'max_profit': stats['max_profit'],
                'max_loss': stats['max_loss'],
                'total_commission': stats['total_commission']
            }

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
            'exit_types': self.exit_types,
            'stock_drawdowns': stock_drawdowns,
            'stock_statistics': stock_statistics
        }