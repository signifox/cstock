#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2025/3/16 09:18
# @Author  : signifox
# @File    : DualThrustStrategy.py
# @Desc    : Optimized DualThrust Strategy (Long & Short)

import backtrader as bt
import pytz
from datetime import datetime, time


class DualThrustStrategy(bt.Strategy):
    params = (
        ("lookback", 2),
        ("k1", 0.5),
        ("k2", 0.5),  # 调整为与 k1 对称
        ("risk_per_trade", 0.01),
        ("commission", 0.001),
        ("slippage", 0.001),
    )

    def __init__(self):
        self.minute_data = self.datas[0]
        self.day_data = self.datas[1]
        self.commission = self.params.commission
        self.slippage = self.params.slippage

        self.hh = bt.indicators.Highest(self.day_data.high, period=self.params.lookback)
        self.ll = bt.indicators.Lowest(self.day_data.low, period=self.params.lookback)
        self.sma_fast = bt.indicators.SimpleMovingAverage(
            self.minute_data.close, period=20
        )
        self.sma_slow = bt.indicators.SimpleMovingAverage(
            self.minute_data.close, period=50
        )
        self.adx = bt.indicators.ADX(self.minute_data, period=14)
        self.atr = bt.indicators.ATR(self.minute_data, period=14)

        self.order = None
        self.buy_line = None
        self.sell_line = None
        self.current_day = None
        self.range_val = None
        self.highest_price = None
        self.lowest_price = None  # 用于空头追踪止盈
        self.last_trade_time = None
        self.cooldown_minutes = 60
        self.buy_signal_count = 0
        self.sell_signal_count = 0  # 用于空头信号确认

    def log(self, txt, dt=None):
        dt = dt or self.minute_data.datetime.datetime(0)
        print(f"{dt}: {txt}")

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    f"买入成交: {order.executed.price}, 数量: {order.executed.size}"
                )
            elif order.issell():
                self.log(
                    f"卖出成交: {order.executed.price}, 数量: {order.executed.size}"
                )
            self.order = None
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f"订单未完成: {order.status}")
            self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        self.log(f"交易完成: 毛收益 {trade.pnl:.2f}, 净收益 {trade.pnlcomm:.2f}")

    def next(self):
        current_time = self.minute_data.datetime.datetime(0)
        current_day = current_time.date()
        hour, minute = current_time.hour, current_time.minute

        if self.current_day != current_day:
            self.current_day = current_day
            cc = self.day_data.close[0]
            self.range_val = max(self.hh[0] - cc, cc - self.ll[0])
            if self.range_val < 1.0:
                self.range_val = 1.0
            self.buy_line = self.minute_data.open[0] + self.params.k1 * self.range_val
            self.sell_line = self.minute_data.open[0] - self.params.k2 * self.range_val
            # self.log(
            #     f"New day: Buy Line={self.buy_line:.2f}, Sell Line={self.sell_line:.2f}, Range={self.range_val:.2f}"
            # )

        if (hour == 9 and minute < 35) or (hour == 15 and minute >= 55):
            return

        if len(self.day_data) < self.params.lookback or len(self.minute_data) < 14:
            self.log("等待数据预热...")
            return

        if self.order:
            return

        if (
            self.last_trade_time
            and (current_time - self.last_trade_time).total_seconds() / 60
            < self.cooldown_minutes
        ):
            return

        sma_fast_val = self.sma_fast[0]
        sma_slow_val = self.sma_slow[0]
        current_price = self.minute_data.close[0]
        cash = self.broker.getcash()
        size1 = int((cash * self.params.risk_per_trade * 2) / (self.atr[0] * 2))
        size2 = int(cash / (current_price * (1 + self.commission + self.slippage)))
        size = min(size1, size2)
        if size < 1:
            size = 1

        if self.position:
            if self.position.size > 0:  # 多头
                entry_price = self.position.price
                stop_loss = entry_price - self.atr[0] * 3.5
                if self.highest_price is None or current_price > self.highest_price:
                    self.highest_price = current_price
                trailing_stop = self.highest_price - self.atr[0] * 4
                profit = current_price - entry_price
                if current_price <= stop_loss:
                    self.order = self.close(data=self.minute_data)
                    self.log(f"止损平多: {current_price}, 止损: {stop_loss}")
                    self.highest_price = None
                    self.last_trade_time = current_time
                elif current_price <= trailing_stop and profit > self.atr[0] * 2:
                    self.order = self.close(data=self.minute_data)
                    self.log(
                        f"追踪止盈平多: {current_price}, 追踪止盈: {trailing_stop}"
                    )
                    self.highest_price = None
                    self.last_trade_time = current_time
                elif self.adx[0] < 15 and profit <= self.atr[0] * 1:
                    self.order = self.close(data=self.minute_data)
                    self.log(f"趋势过弱平多: {current_price}")
                    self.highest_price = None
                    self.last_trade_time = current_time
            elif self.position.size < 0:  # 空头
                entry_price = self.position.price
                stop_loss = entry_price + self.atr[0] * 3.5
                if self.lowest_price is None or current_price < self.lowest_price:
                    self.lowest_price = current_price
                trailing_stop = self.lowest_price + self.atr[0] * 4
                profit = entry_price - current_price
                if current_price >= stop_loss:
                    self.order = self.close(data=self.minute_data)
                    self.log(f"止损平空: {current_price}, 止损: {stop_loss}")
                    self.lowest_price = None
                    self.last_trade_time = current_time
                elif current_price >= trailing_stop and profit > self.atr[0] * 2:
                    self.order = self.close(data=self.minute_data)
                    self.log(
                        f"追踪止盈平空: {current_price}, 追踪止盈: {trailing_stop}"
                    )
                    self.lowest_price = None
                    self.last_trade_time = current_time
                elif self.adx[0] < 15 and profit <= self.atr[0] * 1:
                    self.order = self.close(data=self.minute_data)
                    self.log(f"趋势过弱平空: {current_price}")
                    self.lowest_price = None
                    self.last_trade_time = current_time
        else:
            if (
                current_price > self.buy_line
                and sma_fast_val > sma_slow_val
                and self.adx[0] > 25
                and self.adx[0] > self.adx[-1]
            ):
                self.buy_signal_count += 1
                if self.buy_signal_count >= 3:
                    self.order = self.buy(data=self.minute_data, size=size)
                    self.log(
                        f"买入: {current_price}, 上轨: {self.buy_line}, 数量: {size}"
                    )
                    self.highest_price = current_price
                    self.last_trade_time = current_time
                    self.buy_signal_count = 0
            elif (
                current_price < self.sell_line
                and sma_fast_val < sma_slow_val
                and self.adx[0] > 25
                and self.adx[0] > self.adx[-1]
            ):
                self.sell_signal_count += 1
                if self.sell_signal_count >= 3:
                    short_size = int(size * 0.5)  # 空头头寸减半
                    if short_size < 1:
                        short_size = 1
                    self.order = self.sell(data=self.minute_data, size=short_size)
                    self.log(
                        f"卖空: {current_price}, 下轨: {self.sell_line}, 数量: {short_size}"
                    )
                    self.lowest_price = current_price
                    self.last_trade_time = current_time
                    self.sell_signal_count = 0
            else:
                self.buy_signal_count = 0
                self.sell_signal_count = 0


if __name__ == "__main__":
    cash = 100000.0
    cerebro = bt.Cerebro()
    cerebro.addstrategy(DualThrustStrategy)

    tz = pytz.timezone("US/Eastern")
    utc_tz = pytz.utc

    data = bt.feeds.GenericCSVData(
        dataname="data/SPY.min.stand.csv",
        fromdate=datetime(2025, 1, 5),
        todate=datetime(2025, 12, 31),
        timeframe=bt.TimeFrame.Minutes,
        compression=1,
        dtformat="%Y-%m-%d %H:%M:%S",
        open=1,
        high=2,
        low=3,
        close=4,
        volume=5,
        datetime=0,
        sessionstart=time(9, 30),
        sessionend=time(16, 0),
        sessionfilter=True,
        tzinput=utc_tz,
        tz=tz,
    )

    cerebro.adddata(data, name="minute")
    cerebro.resampledata(data, timeframe=bt.TimeFrame.Days, compression=1)

    cerebro.broker.setcash(cash)
    cerebro.broker.setcommission(0.001)
    cerebro.broker.set_slippage_perc(0.001)

    print("初始资金: %.2f" % cerebro.broker.getvalue())
    cerebro.run()
    print("最终资金: %.2f" % cerebro.broker.getvalue())
    cerebro.plot()
