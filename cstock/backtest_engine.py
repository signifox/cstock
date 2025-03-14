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
        Initialize backtest engine

        Parameters:
            data_dict (dict): Mapping from stock symbols to data
            strategy_class: Strategy class
            strategy_params (dict): Strategy parameters
            initial_cash (float): Initial capital
            commission (float): Commission rate
        """
        self.data_dict = data_dict
        self.strategy_class = strategy_class
        self.strategy_params = strategy_params or {}
        self.initial_cash = initial_cash
        self.commission = commission
        self.cerebro = None

    def setup_cerebro(self):
        """Setup backtrader's cerebro engine"""
        cerebro = bt.Cerebro()

        # Add data feeds
        for symbol, data in self.data_dict.items():
            # Convert to backtrader data format
            data_feed = bt.feeds.PandasData(dataname=data, name=symbol)
            cerebro.adddata(data_feed)

        # Set initial capital
        cerebro.broker.setcash(self.initial_cash)

        # Set commission (percentage mode)
        cerebro.broker.setcommission(commission=self.commission)

        # Add strategy
        cerebro.addstrategy(self.strategy_class, **self.strategy_params)

        # Set risk-free rate (annual rate, e.g., 4%)
        risk_free_rate = 0.04  # Annual risk-free rate
        # Add SharpeRatio analyzer with custom parameters
        cerebro.addanalyzer(
            bt.analyzers.SharpeRatio,
            riskfreerate=risk_free_rate,
            timeframe=bt.TimeFrame.Days,  # Time period (daily)
            annualize=True,  # Annualize results
            factor=252,  # Annualization factor (252 trading days per year)
            _name="sharpe",
        )

        # Add analyzers
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trade")
        # Add drawdown analyzer
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
        # Add returns analyzer
        cerebro.addanalyzer(
            bt.analyzers.Returns,
            _name="returns",
            timeframe=bt.TimeFrame.Days,
            tann=252,  # Annualization factor
        )

        self.cerebro = cerebro
        return cerebro

    def run_backtest(self):
        """Run backtest"""
        if self.cerebro is None:
            self.setup_cerebro()

        print("Starting backtest...")
        results = self.cerebro.run()
        # Save strategy instance
        self.strategy_instance = results[0]

        return results
