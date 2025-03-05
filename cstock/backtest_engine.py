import os
import backtrader as bt
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from cstock import config


class BacktestEngine:
    def __init__(
        self,
        data_dict,
        strategy_class,
        strategy_params=None,
        initial_cash=config.INITIAL_CASH,
        commission=config.COMMISSION_RATE,
    ):
        """
        初始化回测引擎

        参数:
            data_dict (dict): 股票代码到数据的映射
            strategy_class: 策略类
            strategy_params (dict): 策略参数
            initial_cash (float): 初始资金
            commission (float): 手续费率
        """
        self.data_dict = data_dict
        self.strategy_class = strategy_class
        self.strategy_params = strategy_params or {}
        self.initial_cash = initial_cash
        self.commission = commission
        self.cerebro = None

    def setup_cerebro(self):
        """设置backtrader的cerebro引擎"""
        cerebro = bt.Cerebro()

        # 添加数据
        for symbol, data in self.data_dict.items():
            # 转换为backtrader的数据格式
            data_feed = bt.feeds.PandasData(dataname=data, name=symbol)
            cerebro.adddata(data_feed)

        # 设置初始资金
        cerebro.broker.setcash(self.initial_cash)

        # 设置手续费
        cerebro.broker.setcommission(commission=self.commission)

        # 添加策略
        cerebro.addstrategy(self.strategy_class, **self.strategy_params)

        # 添加分析器
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe")
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trade")

        self.cerebro = cerebro
        return cerebro

    def run_backtest(self):
        """运行回测"""
        if self.cerebro is None:
            self.setup_cerebro()

        print("开始回测...")
        results = self.cerebro.run()
        # 保存策略实例
        self.strategy_instance = results[0]

        # self.cerebro.plot(style="candlestick")  # 画图
        return results

    def get_analysis(self):
        """获取回测分析结果"""
        if not hasattr(self, "strategy_instance"):
            raise ValueError("请先运行回测")

        # 获取各种分析结果
        sharpe = self.strategy_instance.analyzers.sharpe.get_analysis()
        trade_analyzer = self.strategy_instance.analyzers.trade.get_analysis()

        # 获取回测周期
        data = self.strategy_instance.datas[0]

        # 获取实际的开始和结束日期
        start_date = data.lines.datetime.array[0]
        end_date = data.lines.datetime.array[-1]

        start_date = bt.num2date(start_date)
        end_date = bt.num2date(end_date)
        days = (end_date - start_date).days

        print(
            f"回测周期: {days}天 ({start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')})"
        )

        # 计算总收益率和年化收益率
        total_return = (
            self.cerebro.broker.getvalue() / self.initial_cash - 1
        ) * 100  # 转换为百分比

        # 确保天数大于0，避免除零错误
        days = max(days, 1)
        # 使用更安全的年化收益率计算方法
        annual_return = ((1 + total_return / 100) ** (365.0 / days) - 1) * 100
        # 限制年化收益率的范围
        annual_return = min(max(annual_return, -100), 1000)

        # 获取交易统计数据
        trade_stats = self._get_trade_stats(trade_analyzer)

        # 计算最大回撤
        max_drawdown = self._calculate_max_drawdown()

        # 整理投资组合分析结果
        analysis = {
            "总收益率": total_return,
            "年化收益率": annual_return,
            "夏普比率": sharpe.get("sharperatio", 0.0),
            "最大回撤": max_drawdown,
            "交易次数": trade_stats["total"],
            "盈利交易": trade_stats["won"],
            "亏损交易": trade_stats["lost"],
            "胜率": trade_stats["win_rate"],
        }

        return analysis

    def _get_trade_stats(self, trade_analyzer):
        """获取交易统计数据"""
        total = getattr(trade_analyzer, "total", None)
        total_trades = total.total if total else 0

        won = getattr(trade_analyzer, "won", None)
        won_trades = won.total if won else 0

        lost = getattr(trade_analyzer, "lost", None)
        lost_trades = lost.total if lost else 0

        win_rate = (won_trades / total_trades * 100) if total_trades > 0 else 0.0

        return {
            "total": total_trades,
            "won": won_trades,
            "lost": lost_trades,
            "win_rate": win_rate,
        }

    def _calculate_max_drawdown(self):
        """计算最大回撤"""
        if not self.strategy_instance._portfolio_drawdown_history:
            return 0.0

        return max(self.strategy_instance._portfolio_drawdown_history)
