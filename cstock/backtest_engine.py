import os
import backtrader as bt
import pandas as pd
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
            # 为每只股票单独添加DrawDown分析器
            cerebro.addanalyzer(bt.analyzers.DrawDown, _name=f"drawdown_{symbol}")

        # 设置初始资金
        cerebro.broker.setcash(self.initial_cash)

        # 设置手续费
        cerebro.broker.setcommission(commission=self.commission)

        # 添加策略
        cerebro.addstrategy(self.strategy_class, **self.strategy_params)

        # 设置无风险利率（年化利率，例如3%）
        risk_free_rate = 0.04  # 年化无风险利率
        # 添加 SharpeRatio 分析器并传入自定义参数
        cerebro.addanalyzer(
            bt.analyzers.SharpeRatio,
            riskfreerate=risk_free_rate,
            timeframe=bt.TimeFrame.Days,  # 时间周期（日线）
            annualize=True,  # 是否年化
            factor=252,  # 年化因子（一年252个交易日）
            _name="sharpe",
        )

        # 添加分析器
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trade")
        # 添加回撤分析器
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")

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
