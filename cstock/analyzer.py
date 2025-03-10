import pandas as pd
import backtrader as bt
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime


class Analyzer:
    def __init__(self, backtest_engine):
        """
        初始化结果分析器

        参数:
            backtest_engine: 回测引擎实例
        """
        self.backtest_engine = backtest_engine
        self.analysis = self._get_analysis()

    def _get_trade_stats(self, trade_analyzer):
        """获取交易统计数据"""
        if not trade_analyzer:
            return {"total": 0, "won": 0, "lost": 0, "win_rate": 0.0}

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

    def _get_analysis(self):
        """获取回测分析结果"""
        if not hasattr(self.backtest_engine, "strategy_instance"):
            raise ValueError("请先运行回测")

        # 获取各种分析结果
        sharpe = self.backtest_engine.strategy_instance.analyzers.sharpe.get_analysis()
        trade_analyzer = (
            self.backtest_engine.strategy_instance.analyzers.trade.get_analysis()
        )

        # 获取回测周期
        data = self.backtest_engine.strategy_instance.datas[0]

        # 获取回测时间范围
        start_date = bt.num2date(data.datetime.array[0])
        end_date = bt.num2date(data.datetime.array[-1])

        days = (end_date - start_date).days

        print(
            f"回测周期: {days}天 ({start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')})"
        )

        # 计算总收益率和年化收益率
        total_return = (
            self.backtest_engine.cerebro.broker.getvalue()
            / self.backtest_engine.initial_cash
            - 1
        ) * 100  # 转换为百分比

        # 确保天数大于0，避免除零错误
        days = max(days, 1)
        # 使用更安全的年化收益率计算方法
        annual_return = ((1 + total_return / 100) ** (365.0 / days) - 1) * 100
        # 限制年化收益率的范围
        annual_return = min(max(annual_return, -100), 1000)

        # 获取交易统计数据
        trade_stats = self._get_trade_stats(trade_analyzer)

        # 获取回撤分析结果
        drawdown = (
            self.backtest_engine.strategy_instance.analyzers.drawdown.get_analysis()
        )
        max_drawdown = drawdown.get("max", {}).get("drawdown", 0.0)

        # 获取OrderMetric统计数据
        order_metrics = (
            self.backtest_engine.strategy_instance.order_metric.get_metrics()
        )

        # 获取每只股票的最大回撤
        stock_drawdowns = {}
        for symbol in self.backtest_engine.data_dict.keys():
            drawdown_analyzer = getattr(
                self.backtest_engine.strategy_instance.analyzers, f"drawdown_{symbol}"
            )
            drawdown = drawdown_analyzer.get_analysis()
            stock_drawdowns[symbol] = drawdown.get("max", {}).get("drawdown", 0.0)

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
            "总盈亏": order_metrics["total_pnl"],
            "最大单笔盈利": order_metrics["max_profit"],
            "最大单笔亏损": order_metrics["max_loss"],
            "平均持仓天数": order_metrics["avg_holding_period"],
            "总手续费": order_metrics["total_commission"],
            "出场类型统计": order_metrics["exit_types"],
            "个股最大回撤": stock_drawdowns,
            "stock_statistics": order_metrics["stock_statistics"],
        }

        return analysis

    def print_summary(self):
        """打印回测结果摘要"""
        print("\n===== 回测结果摘要 =====")
        print("\n基本指标:")
        print(f"总收益率: {self.analysis['总收益率']:.2f}%")
        print(f"年化收益率: {self.analysis['年化收益率']:.2f}%")
        print(f"夏普比率: {self.analysis['夏普比率']:.4f}")
        print(f"最大回撤: {self.analysis['最大回撤']:.2f}%")

        print("\n交易统计:")
        print(f"交易次数: {self.analysis['交易次数']}")
        print(f"盈利交易: {self.analysis['盈利交易']}")
        print(f"亏损交易: {self.analysis['亏损交易']}")
        print(f"胜率: {self.analysis['胜率']:.2f}%")

        print("\n盈亏分析:")
        print(f"总盈亏: {self.analysis['总盈亏']:.2f}")
        print(f"最大单笔盈利: {self.analysis['最大单笔盈利']:.2f}")
        print(f"最大单笔亏损: {self.analysis['最大单笔亏损']:.2f}")
        print(f"平均持仓天数: {self.analysis['平均持仓天数']:.1f}天")
        print(f"总手续费: {self.analysis['总手续费']:.2f}")

        print("\n出场类型统计:")
        for exit_type, count in self.analysis["出场类型统计"].items():
            print(f"{exit_type}: {count}次")

        print("\n个股交易统计:")
        # 创建个股统计数据的DataFrame
        stock_data = []
        for symbol, stats in self.analysis["stock_statistics"].items():
            stock_data.append(
                {
                    "股票代码": symbol,
                    "最大回撤(%)": self.analysis["个股最大回撤"][symbol],
                    "交易次数": stats["total_trades"],
                    "盈利交易": stats["winning_trades"],
                    "亏损交易": stats["losing_trades"],
                    "胜率(%)": stats["win_rate"],
                    "总盈亏": stats["total_pnl"],
                    "最大盈利": stats["max_profit"],
                    "最大亏损": stats["max_loss"],
                    "总手续费": stats["total_commission"],
                }
            )

        # 创建DataFrame并设置显示格式
        df = pd.DataFrame(stock_data)
        pd.set_option("display.float_format", lambda x: "%.2f" % x)
        pd.set_option("display.max_columns", None)
        pd.set_option("display.width", None)

        # 打印表格
        print(df.to_string(index=False))
