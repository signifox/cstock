import pandas as pd
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
        self.analysis = backtest_engine.get_analysis()

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
        for exit_type, count in self.analysis['出场类型统计'].items():
            print(f"{exit_type}: {count}次")
