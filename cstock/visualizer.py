import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
import backtrader as bt
from matplotlib.gridspec import GridSpec
import matplotlib.font_manager as fm


class Visualizer:
    """使用matplotlib库可视化回测结果

    提供K线图、交易信号、资金曲线和回撤分析等可视化功能
    """

    def __init__(self, backtest_engine):
        """
        初始化可视化器

        参数:
            backtest_engine: 回测引擎实例
        """
        self.backtest_engine = backtest_engine
        self.strategy_instance = backtest_engine.strategy_instance
        self.trades = self.strategy_instance.order_metric.trades
        self.analysis = backtest_engine.get_analysis()

        # 设置matplotlib的样式和字体
        plt.style.use("dark_background")
        # 设置中文字体，按优先级尝试不同的字体
        font_list = [f.name for f in fm.fontManager.ttflist]
        chinese_fonts = [
            "PingFang SC",  # macOS 默认中文字体
            "Noto Sans CJK SC",  # Google Noto字体
            "Source Han Sans CN",  # 思源黑体
            "Microsoft YaHei",  # 微软雅黑
            "SimHei",  # 中易黑体
            "WenQuanYi Micro Hei",  # 文泉驿微米黑
            "Hiragino Sans GB",  # 冬青黑体
        ]

        # 查找可用的中文字体
        font_found = False
        for font in chinese_fonts:
            if font in font_list:
                plt.rcParams["font.family"] = [font]
                plt.rcParams["axes.unicode_minus"] = True  # 确保负号能正确显示
                font_found = True
                break

        if not font_found:
            # 如果没有找到中文字体，使用系统默认字体并添加警告
            plt.rcParams["font.sans-serif"] = ["DejaVu Sans"]
            plt.rcParams["axes.unicode_minus"] = True  # 确保负号能正确显示
            print("警告：未找到合适的中文字体，可能会导致中文显示异常。")

    def _prepare_price_data(self, symbol):
        """准备价格数据，用于绘制K线图"""
        # 获取原始数据
        data = None
        for d in self.strategy_instance.datas:
            if d._name == symbol:
                data = d
                break

        if data is None:
            raise ValueError(f"未找到股票 {symbol} 的数据")

        # 获取回测时间范围
        start_date = bt.num2date(data.datetime.array[0])
        end_date = bt.num2date(data.datetime.array[-1])

        # 创建DataFrame
        df = pd.DataFrame()

        df["time"] = [bt.num2date(bt_time) for bt_time in data.datetime.array]
        df["open"] = data.open.array
        df["high"] = data.high.array
        df["low"] = data.low.array
        df["close"] = data.close.array
        df["volume"] = data.volume.array

        # 设置时间索引
        df.set_index("time", inplace=True)

        return df

    def _prepare_equity_curve(self):
        """准备资金曲线数据"""
        # 获取第一个数据源的时间序列作为基准
        data = self.strategy_instance.datas[0]
        # 获取时间序列并转换为日期对象
        dates = [bt.num2date(bt_time) for bt_time in data.datetime.array]

        # 检查回测的起止时间
        start_date = bt.num2date(data.datetime.array[0])
        end_date = bt.num2date(data.datetime.array[-1])

        # 创建资金曲线DataFrame
        df = pd.DataFrame(index=dates)
        df.index.name = "time"

        # 获取每日的资金值
        # 注意：这里简化处理，实际应该从cerebro的observers中获取
        # 由于backtrader不直接提供历史资金曲线，这里使用近似方法
        initial_cash = self.backtest_engine.initial_cash
        final_value = self.backtest_engine.cerebro.broker.getvalue()

        # 线性插值创建资金曲线（简化处理）
        df["equity"] = np.linspace(initial_cash, final_value, len(dates))

        # 计算回撤
        df["drawdown"] = df["equity"].cummax() - df["equity"]
        df["drawdown_pct"] = (df["drawdown"] / df["equity"].cummax()) * 100

        return df

    def _prepare_trade_markers(self, symbol):
        """准备交易标记数据"""
        buy_signals = []
        sell_signals = []

        # 获取股票数据的时间范围
        data = None
        for d in self.strategy_instance.datas:
            if d._name == symbol:
                data = d
                break

        if data is None:
            raise ValueError(f"未找到股票 {symbol} 的数据")

        data_start_time = bt.num2date(data.datetime.array[0])
        data_end_time = bt.num2date(data.datetime.array[-1])

        for trade in self.trades:
            if trade.symbol != symbol:
                continue
            # 验证交易时间是否在数据范围内
            if not (data_start_time <= trade.entry_time <= data_end_time):
                continue

            if trade.direction == "buy":
                buy_signals.append(
                    {
                        "time": trade.entry_time,
                        "price": trade.entry_price,
                        "size": trade.size,
                    }
                )

            if trade.exit_time is not None:
                if not (data_start_time <= trade.exit_time <= data_end_time):
                    continue
                sell_signals.append(
                    {
                        "time": trade.exit_time,
                        "price": trade.exit_price,
                        "size": trade.size,
                        "pnl": trade.pnl,
                        "exit_type": trade.exit_type,
                    }
                )

        return buy_signals, sell_signals

    def plot_single_stock(self, symbol):
        """绘制单只股票的K线图和交易信号

        参数:
            symbol: 股票代码
        """
        # 准备数据
        price_df = self._prepare_price_data(symbol)
        buy_signals, sell_signals = self._prepare_trade_markers(symbol)

        # 创建图表
        fig = plt.figure(figsize=(12, 8))
        gs = GridSpec(2, 1, height_ratios=[3, 1])

        # 绘制K线图
        ax1 = fig.add_subplot(gs[0])
        ax2 = fig.add_subplot(gs[1], sharex=ax1)

        # 绘制K线
        candlestick_data = list(
            zip(
                range(len(price_df)),
                price_df["open"],
                price_df["close"],
                price_df["high"],
                price_df["low"],
            )
        )

        for i, (t, o, c, h, l) in enumerate(candlestick_data):
            color = "lime" if c >= o else "red"
            # 绘制影线
            ax1.plot([t, t], [l, h], color=color, linewidth=0.8, alpha=0.8)
            # 绘制实体
            body_height = abs(c - o)
            if body_height == 0:
                # 十字星
                ax1.plot([t, t], [o - 0.1, o + 0.1], color=color, linewidth=2)
            else:
                ax1.plot([t, t], [min(o, c), max(o, c)], color=color, linewidth=4)

        # 绘制均线
        ax1.plot(
            range(len(price_df)),
            price_df["close"].rolling(20).mean(),
            color="cyan",
            label="MA20",
            linewidth=1,
        )
        ax1.plot(
            range(len(price_df)),
            price_df["close"].rolling(60).mean(),
            color="yellow",
            label="MA60",
            linewidth=1,
        )

        # 绘制成交量
        volume_colors = [
            "lime" if c >= o else "red"
            for o, c in zip(price_df["open"], price_df["close"])
        ]
        ax2.bar(
            range(len(price_df)), price_df["volume"], color=volume_colors, alpha=0.7
        )

        # 添加买入信号
        for signal in buy_signals:
            idx = price_df.index.get_loc(signal["time"])
            ax1.plot(
                idx,
                signal["price"],
                "^",
                color="white",
                markersize=10,
                label=(
                    "买入信号"
                    if "买入信号" not in ax1.get_legend_handles_labels()[1]
                    else ""
                ),
            )
            ax1.plot(idx, signal["price"], "^", color="lime", markersize=8, alpha=0.8)
            ax1.annotate(
                f"买入\n{signal['size']}股",
                (idx, signal["price"]),
                xytext=(10, 20),
                textcoords="offset points",
                bbox=dict(
                    facecolor="black", alpha=0.8, edgecolor="lime", boxstyle="round"
                ),
                color="white",
                fontsize=8,
            )

        # 添加卖出信号
        for signal in sell_signals:
            idx = price_df.index.get_loc(signal["time"])
            color = "lime" if signal["pnl"] > 0 else "red"
            ax1.plot(
                idx,
                signal["price"],
                "v",
                color="white",
                markersize=10,
                label=(
                    "盈利卖出"
                    if signal["pnl"] > 0
                    and "盈利卖出" not in ax1.get_legend_handles_labels()[1]
                    else (
                        "亏损卖出"
                        if signal["pnl"] <= 0
                        and "亏损卖出" not in ax1.get_legend_handles_labels()[1]
                        else ""
                    )
                ),
            )
            ax1.plot(idx, signal["price"], "v", color=color, markersize=8, alpha=0.8)
            ax1.annotate(
                f"卖出\n{signal['size']}股\n{signal['pnl']:.2f}",
                (idx, signal["price"]),
                xytext=(10, -40),
                textcoords="offset points",
                bbox=dict(
                    facecolor="black", alpha=0.8, edgecolor=color, boxstyle="round"
                ),
                color="white",
                fontsize=8,
            )

        # 设置图表
        ax1.set_title(f"{symbol} 交易分析", fontsize=12, pad=10)
        ax1.legend(loc="upper left", fontsize=8)
        ax1.grid(True, alpha=0.2)
        ax2.grid(True, alpha=0.2)

        # 设置y轴格式
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"{x:,.2f}"))
        ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"{x:,.0f}"))

        # 设置x轴刻度
        # 计算合适的日期刻度间隔，根据数据量动态调整
        total_days = len(price_df)
        interval = max(1, total_days // 10)  # 确保至少显示10个日期标签
        
        # 设置x轴刻度位置和标签
        tick_positions = range(0, total_days, interval)
        tick_labels = [price_df.index[i].strftime('%Y-%m-%d') for i in tick_positions]
        
        plt.xticks(tick_positions, tick_labels, rotation=45, ha='right', fontsize=8)
        
        # 调整布局以防止标签被截断
        plt.tight_layout()
        plt.show()

    def plot_portfolio(self):
        """绘制投资组合的资金曲线和回撤"""
        # 准备数据
        equity_df = self._prepare_equity_curve()

        # 创建图表
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), height_ratios=[2, 1])

        # 绘制资金曲线
        ax1.plot(equity_df.index, equity_df["equity"], color="g", label="资金曲线")

        # 绘制回撤
        ax2.fill_between(
            equity_df.index,
            0,
            equity_df["drawdown_pct"],
            color="r",
            alpha=0.3,
            label="回撤百分比",
        )

        # 添加关键指标标注
        ax1.text(
            0.05,
            0.95,
            f"总收益率: {self.analysis['总收益率']:.2f}%",
            transform=ax1.transAxes,
        )
        ax1.text(
            0.05,
            0.90,
            f"年化收益率: {self.analysis['年化收益率']:.2f}%",
            transform=ax1.transAxes,
        )
        ax1.text(
            0.05,
            0.85,
            f"夏普比率: {self.analysis['夏普比率']:.2f}",
            transform=ax1.transAxes,
        )

        ax2.text(
            0.05,
            0.95,
            f"最大回撤: {self.analysis['最大回撤']:.2f}%",
            transform=ax2.transAxes,
        )
        ax2.text(
            0.05, 0.90, f"胜率: {self.analysis['胜率']:.2f}%", transform=ax2.transAxes
        )

        # 设置图表
        ax1.set_title("投资组合分析")
        ax1.legend()
        ax2.legend()
        ax1.grid(True)
        ax2.grid(True)

        plt.tight_layout()
        plt.show()

    def plot_all(self):
        """绘制所有可视化图表"""
        # 绘制投资组合分析
        self.plot_portfolio()

        # 绘制每只股票的分析
        for symbol in self.backtest_engine.data_dict.keys():
            self.plot_single_stock(symbol)
