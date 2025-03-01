import backtrader as bt
from cstock.data_fetcher import DataFetcher
from cstock.strategies.sma_crossover import SMACrossoverStrategy
from cstock.analyzer import Analyzer
from cstock.backtest_engine import BacktestEngine
from cstock.config import config


def main():
    # 初始化数据获取器
    data_fetcher = DataFetcher()

    # 获取所有股票的回测数据
    data_dict = data_fetcher.fetch_multiple_stocks(
        symbols=config.STOCK_LIST,
        start_date=config.START_DATE,
        end_date=config.END_DATE,
    )

    # 初始化回测引擎
    engine = BacktestEngine(
        data_dict=data_dict,
        strategy_class=SMACrossoverStrategy,
        strategy_params=config.STRATEGY_PARAMS,
        initial_cash=config.INITIAL_CASH,
        commission=config.COMMISSION_RATE,
    )

    # 运行回测
    results = engine.run_backtest()

    # 分析结果
    analysis = engine.get_analysis()
    print("\n回测结果分析:")

    # 打印回测结果摘要
    print(f"\n总收益率: {analysis['总收益率']:.2f}%")
    print(f"年化收益率: {analysis['年化收益率']:.2f}%")
    print(f"夏普比率: {analysis['夏普比率']:.4f}")
    print(f"最大回撤: {analysis['最大回撤']:.2f}%")
    print(f"交易次数: {analysis['交易次数']}")
    print(f"盈利交易: {analysis['盈利交易']}")
    print(f"亏损交易: {analysis['亏损交易']}")
    print(f"胜率: {analysis['胜率']:.2f}%")

    # 绘制回测结果
    engine.plot_results()


if __name__ == "__main__":
    main()
