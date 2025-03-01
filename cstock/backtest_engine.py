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
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
        cerebro.addanalyzer(bt.analyzers.Returns, _name="returns")
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trade")

        self.cerebro = cerebro
        return cerebro

    def run_backtest(self):
        """运行回测"""
        if self.cerebro is None:
            self.setup_cerebro()

        print("开始回测...")
        results = self.cerebro.run()
        self.strategy_instance = results[0]

        # 初始化每个股票的价值历史和回撤历史
        self.strategy_instance._value_history = {}
        self.strategy_instance._drawdown_history = {}
        self.strategy_instance._portfolio_value_history = []
        self.strategy_instance._portfolio_drawdown_history = []

        # 为每个股票初始化历史记录
        for data in self.strategy_instance.datas:
            symbol = data._name
            self.strategy_instance._value_history[symbol] = []
            self.strategy_instance._drawdown_history[symbol] = []

        # 计算投资组合的最高价值
        portfolio_peak = self.initial_cash

        # 模拟回测过程中的价值变化
        for i in range(len(self.strategy_instance.datas[0])):
            # 计算当前投资组合价值
            portfolio_value = self.cerebro.broker.getvalue()
            self.strategy_instance._portfolio_value_history.append(portfolio_value)

            # 更新投资组合峰值和计算回撤
            portfolio_peak = max(portfolio_peak, portfolio_value)
            portfolio_drawdown = ((portfolio_peak - portfolio_value) / portfolio_peak * 100) if portfolio_peak > 0 else 0
            self.strategy_instance._portfolio_drawdown_history.append(portfolio_drawdown)

            # 计算每个股票的价值和回撤
            for data in self.strategy_instance.datas:
                symbol = data._name
                position = self.strategy_instance.getposition(data)
                # 计算当前持仓的市值
                current_value = position.size * data.close[0] if position.size != 0 else 0
                self.strategy_instance._value_history[symbol].append(current_value)

                # 计算该股票的历史最高价值
                peak_value = max(self.strategy_instance._value_history[symbol]) if self.strategy_instance._value_history[symbol] else current_value
                # 计算该股票的回撤（避免分母为0）
                drawdown = ((peak_value - current_value) / peak_value * 100) if peak_value > 0 else 0
                self.strategy_instance._drawdown_history[symbol].append(drawdown)

        return results

    def plot_results(self, filename=None):
        """绘制回测结果"""
        if self.cerebro is None:
            raise ValueError("请先运行回测")

        # 设置中文字体
        plt.rcParams["font.sans-serif"] = [
            "Arial Unicode MS"
        ]  # macOS系统预装的支持中文的字体
        plt.rcParams["axes.unicode_minus"] = False  # 用来正常显示负号

        # 创建多个子图
        fig = plt.figure(figsize=(15, 10))

        # 绘制投资组合价值曲线
        ax1 = plt.subplot(2, 1, 1)
        ax1.plot(self.strategy_instance._portfolio_value_history, label="投资组合价值")
        ax1.set_title("投资组合表现")
        ax1.set_xlabel("交易日")
        ax1.set_ylabel("价值")
        ax1.legend()
        ax1.grid(True)

        # 绘制个股价值曲线
        ax2 = plt.subplot(2, 1, 2)
        for symbol in self.strategy_instance._value_history:
            ax2.plot(self.strategy_instance._value_history[symbol], label=symbol)
        ax2.set_title("个股持仓价值")
        ax2.set_xlabel("交易日")
        ax2.set_ylabel("价值")
        ax2.legend()
        ax2.grid(True)

        plt.tight_layout()

        if filename:
            plt.savefig(filename)

        plt.show()

        # 绘制回撤图
        fig = plt.figure(figsize=(15, 10))

        # 绘制投资组合回撤
        ax1 = plt.subplot(2, 1, 1)
        ax1.plot(
            self.strategy_instance._portfolio_drawdown_history,
            label="投资组合回撤",
            color="red",
        )
        ax1.set_title("投资组合回撤")
        ax1.set_xlabel("交易日")
        ax1.set_ylabel("回撤 (%)")
        ax1.legend()
        ax1.grid(True)

        # 绘制个股回撤
        ax2 = plt.subplot(2, 1, 2)
        for symbol in self.strategy_instance._drawdown_history:
            ax2.plot(
                self.strategy_instance._drawdown_history[symbol], label=f"{symbol}回撤"
            )
        ax2.set_title("个股回撤")
        ax2.set_xlabel("交易日")
        ax2.set_ylabel("回撤 (%)")
        ax2.legend()
        ax2.grid(True)

        plt.tight_layout()

        if filename:
            plt.savefig(filename + "_drawdown")

        plt.show()

    def get_analysis(self):
        """获取回测分析结果"""
        if not hasattr(self, "strategy_instance"):
            raise ValueError("请先运行回测")

        # 获取各种分析结果
        sharpe = self.strategy_instance.analyzers.sharpe.get_analysis()
        drawdown = self.strategy_instance.analyzers.drawdown.get_analysis()
        returns = self.strategy_instance.analyzers.returns.get_analysis()
        trade_analyzer = self.strategy_instance.analyzers.trade.get_analysis()

        # 计算年化收益率
        total_return = (self.cerebro.broker.getvalue() / self.initial_cash - 1) * 100
        # 获取回测天数
        start_date = self.strategy_instance.datas[0].datetime.date(0)
        end_date = self.strategy_instance.datas[0].datetime.date(-1)
        days = (end_date - start_date).days
        # 计算年化收益率
        annual_return = (pow((1 + total_return / 100), 365/days) - 1) * 100 if days > 0 else 0.0

        # 从trade分析器获取交易统计数据
        total_trades = trade_analyzer.total.total if hasattr(trade_analyzer, 'total') else 0
        won_trades = trade_analyzer.won.total if hasattr(trade_analyzer, 'won') else 0
        lost_trades = trade_analyzer.lost.total if hasattr(trade_analyzer, 'lost') else 0

        # 整理投资组合分析结果
        analysis = {
            "总收益率": total_return,  # 已转换为百分比
            "年化收益率": annual_return,  # 使用更准确的年化计算方法
            "夏普比率": sharpe.get("sharperatio", 0.0),
            "最大回撤": max(self.strategy_instance._portfolio_drawdown_history) if self.strategy_instance._portfolio_drawdown_history else 0.0,
            "交易次数": total_trades,
            "盈利交易": won_trades,
            "亏损交易": lost_trades,
            "胜率": 0.0,  # 默认值，稍后更新
        }

        # 计算胜率
        if analysis["交易次数"] > 0:
            analysis["胜率"] = (analysis["盈利交易"] / analysis["交易次数"]) * 100

        return analysis
