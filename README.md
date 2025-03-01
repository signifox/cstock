# 量化回测框架 (Stock Market Framework Tester)

这是一个基于Python的量化交易回测框架，用于测试和评估不同的交易策略。

## 功能特点

- 支持多股票回测
- 内置SMA交叉策略
- 完整的回测分析报告
- 可视化交易结果
- 风险管理模块

## 项目结构

```
- cstock/            # 核心代码目录
  - strategies/      # 交易策略
  - analyzer.py      # 分析模块
  - backtest_engine.py # 回测引擎
  - data_fetcher.py  # 数据获取
  - risk_manager.py  # 风险管理
- main.py            # 主程序
```

## 使用方法

1. 安装依赖：
```bash
pip install backtrader pandas numpy matplotlib
```

2. 运行回测：
```bash
python main.py
```

## 回测结果

程序会输出以下分析指标：
- 总收益率
- 年化收益率
- 夏普比率
- 最大回撤
- 交易次数统计
- 胜率分析

同时会生成交易结果的可视化图表。