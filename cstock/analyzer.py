import pandas as pd
import backtrader as bt
import numpy as np


class Analyzer:
    def __init__(self, backtest_engine):
        """
        初始化结果分析器

        参数:
            backtest_engine: 回测引擎实例
        """
        self.backtest_engine = backtest_engine
        self.analysis = self._get_analysis()

    def _get_analysis(self):
        """获取回测分析结果"""
        if not hasattr(self.backtest_engine, "strategy_instance"):
            raise ValueError("请先运行回测")

        # 获取各种分析结果
        sharpe = self.backtest_engine.strategy_instance.analyzers.sharpe.get_analysis()
        trade_analyzer = (
            self.backtest_engine.strategy_instance.analyzers.trade.get_analysis()
        )
        returns = (
            self.backtest_engine.strategy_instance.analyzers.returns.get_analysis()
        )
        drawdown = (
            self.backtest_engine.strategy_instance.analyzers.drawdown.get_analysis()
        )

        # 获取回测周期
        data = self.backtest_engine.strategy_instance.datas[0]
        start_date = bt.num2date(data.datetime.array[0])
        end_date = bt.num2date(data.datetime.array[-1])
        days = (end_date - start_date).days

        # 获取交易统计数据
        analysis = {
            "开始日期": start_date.strftime("%Y-%m-%d"),
            "结束日期": end_date.strftime("%Y-%m-%d"),
            "回测天数": days,
            "夏普比率": sharpe.get("sharperatio", 0.0),
            "最大回撤": drawdown.get("max", {}).get("drawdown", 0.0),
            "最大回撤期间": drawdown.get("max", {}).get("len", 0),
            "总收益率": returns.get("rtot", 0.0),
            "年化收益率": (1 + returns.get("rtot", 0.0)) ** (365 / days) - 1 if days > 0 else 0.0,
            "总交易次数": trade_analyzer.get("total", {}).get("total", 0),
            "盈利交易次数": trade_analyzer.get("won", {}).get("total", 0),
            "亏损交易次数": trade_analyzer.get("lost", {}).get("total", 0),
            "胜率": (
                trade_analyzer.get("won", {}).get("total", 0)
                / trade_analyzer.get("total", {}).get("total", 1)
                if trade_analyzer.get("total", {}).get("total", 0) > 0
                else 0.0
            ),
            "平均每笔收益": trade_analyzer.get("pnl", {}).get("net", {}).get("average", 0.0),
            "最大单笔收益": trade_analyzer.get("won", {}).get("pnl", {}).get("max", 0.0),
            "最大单笔亏损": abs(trade_analyzer.get("lost", {}).get("pnl", {}).get("max", 0.0)),
        }
        return analysis

    def print_summary(self):
        print("\n=== 回测结果摘要 ===\n")
        for key, value in self.analysis.items():
            if isinstance(value, float):
                print(f"{key}: {value:.2%}" if "率" in key else f"{key}: {value:.2f}")
            else:
                print(f"{key}: {value}")
