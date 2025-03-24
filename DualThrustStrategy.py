#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2023/10/14 16:55
# @Author  : signifox
# @File    : DualThrustStrategy.py
# @Desc    :


import backtrader as bt
import pytz
from datetime import datetime, time


# 定义 DualThrust 策略
class DualThrustStrategy(bt.Strategy):
    params = (
        ("lookback", 1),  # 回溯天数，默认 1 天
        ("k1", 0.5),  # 上轨参数
        ("k2", 0.5),  # 下轨参数
        ("risk_per_trade", 0.01),  # 每次交易风险比例，默认 1%
        ("risk_factor", 1.0),  # 风险因子，默认 1.0
        ("commission", 0.001),  # 手续费比例
        ("slippage", 0.002),  # 滑点比例
    )

    def __init__(self):
        self.minute_data = self.datas[0]
        self.day_data = self.datas[1]
        self.commission = self.params.commission
        self.slippage = self.params.slippage

        # 计算 N 天回溯的 HH 和 LL
        self.hh = bt.indicators.Highest(self.day_data.high, period=self.params.lookback)
        self.ll = bt.indicators.Lowest(self.day_data.low, period=self.params.lookback)
        self.sma_fast = bt.indicators.SimpleMovingAverage(
            self.minute_data.close, period=20
        )
        self.sma_slow = bt.indicators.SimpleMovingAverage(
            self.minute_data.close, period=50
        )

        self.order = None
        self.buy_line = None
        self.sell_line = None

        self.current_day = None
        self.range_val = None  # 保存 Range 用于 size 计算

    def log(self, txt, dt=None):
        dt = dt or self.minute_data.datetime.datetime(0)
        print(f"{dt}: {txt}")

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # 订单已提交或接受，等待处理
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
            # 订单完成后清空
            self.order = None
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f"订单未完成: {order.status}")
            self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        self.log(f"交易完成: 毛收益 {trade.pnl:.2f}, 净收益 {trade.pnlcomm:.2f}")

    def next(self):
        # 获取当前分钟时间
        current_time = self.minute_data.datetime.datetime(0)
        current_day = current_time.date()
        hour, minute = current_time.hour, current_time.minute

        if self.current_day != current_day:
            self.current_day = current_day
            # 使用前一天的收盘价作为 CC
            cc = self.day_data.close[0]
            self.range_val = max(self.hh[0] - cc, cc - self.ll[0])
            self.buy_line = self.minute_data.open[0] + self.params.k1 * self.range_val
            self.sell_line = self.minute_data.open[0] - self.params.k2 * self.range_val
            self.log(
                f"New day: Buy Line={self.buy_line:.2f}, Sell Line={self.sell_line:.2f}, Range={self.range_val:.2f}"
            )

        # 跳过开盘后5分钟（9:30:00-9:34:59）和收盘前5分钟（15:55:00-15:59:59）
        if (hour == 9 and minute < 35) or (hour == 15 and minute >= 55):
            # self.log("跳过开盘后15分钟或收盘前15分钟的交易处理")
            return

        # 确保有足够的日数据（至少 lookback天）
        if len(self.day_data) < self.params.lookback:
            self.log(f"等待日数据预热，至少需要 {self.params.lookback} 天...")
            return

        if self.order:
            return

        sma_fast_val = self.sma_fast[0]
        sma_slow_val = self.sma_slow[0]

        current_price = self.minute_data.close[0]

        cash = self.broker.getcash()
        # 计算风险调整的交易数量
        size1 = int(
            (cash * self.params.risk_per_trade)
            / (self.range_val * self.params.risk_factor)
        )
        size2 = int(cash / (current_price * (1 + self.commission + self.slippage)))
        size = min(size1, size2)
        if size < 1:
            size = 1

        if self.position:
            if self.position.size > 0:
                entry_price = self.position.price
                stop_loss = entry_price - self.range_val * 0.3
                take_profit = entry_price + self.range_val * 1.5
                if current_price <= stop_loss:
                    self.order = self.close(data=self.minute_data)
                    self.log(f"止损平多: {current_price}, 止损: {stop_loss}")
                elif current_price >= take_profit:
                    self.order = self.close(data=self.minute_data)
                    self.log(f"止盈平多: {current_price}, 目标: {take_profit}")
        else:
            if current_price > self.buy_line and sma_fast_val > sma_slow_val:
                self.order = self.buy(data=self.minute_data, size=size)
                self.log(f"买入: {current_price}, 上轨: {self.buy_line}, 数量: {size}")


# 主程序
if __name__ == "__main__":
    # 初始化 cerebro
    cerebro = bt.Cerebro()

    # 添加策略
    cerebro.addstrategy(DualThrustStrategy, lookback=2, k1=0.2, k2=0.2)

    tz = pytz.timezone("US/Eastern")  # 设置美东时区
    utc_tz = pytz.utc  # UTC时区

    # 加载本地 CSV 数据
    data = bt.feeds.GenericCSVData(
        dataname="data/SPY.min.stand.csv",  # 替换为你的 CSV 文件路径
        fromdate=datetime(2025, 1, 5),  # 数据起始日期
        todate=datetime(2025, 12, 31),  # 数据结束日期
        timeframe=bt.TimeFrame.Minutes,  # 分钟级别数据
        compression=1,  # 每根K线代表1分钟
        dtformat="%Y-%m-%d %H:%M:%S",  # CSV 中的日期时间格式
        open=1,
        high=2,
        low=3,
        close=4,
        volume=5,  # 根据你的 CSV 列顺序调整
        datetime=0,  # 时间戳在第0列
        sessionstart=time(9, 30),
        sessionend=time(16, 0),
        sessionfilter=True,  # 过滤非交易时段数据
        tzinput=utc_tz,  # 输入数据为UTC时间
        tz=tz,  # 输出为美东时间
    )

    # 添加数据到 cerebro
    cerebro.adddata(data, name="minute")
    # 将分钟数据重采样为天级数据
    cerebro.resampledata(data, timeframe=bt.TimeFrame.Days, compression=1)

    # 设置初始资金
    cerebro.broker.setcash(100000.0)
    # 设置手续费（可选）
    cerebro.broker.setcommission(commission=0.001)  # 0.1% 手续费
    # 设置滑点（可选）
    cerebro.broker.set_slippage_perc(0.002)  # 0.2% 滑点

    # 运行回测
    print("初始资金: %.2f" % cerebro.broker.getvalue())
    cerebro.run()
    print("最终资金: %.2f" % cerebro.broker.getvalue())

    # 可视化结果（可选）
    cerebro.plot()
