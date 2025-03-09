import backtrader as bt
from cstock.data_fetcher import DataFetcher
from cstock.strategies.sma_crossover import SMACrossoverStrategy
from cstock.analyzer import Analyzer
from cstock.backtest_engine import BacktestEngine
from cstock.visualizer import Visualizer
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

    # 创建分析器并打印结果摘要
    analyzer = Analyzer(engine)
    analyzer.print_summary()
    
    # 使用finplot可视化回测结果
    visualizer = Visualizer(engine)
    
    # 绘制投资组合分析图表
    visualizer.plot_portfolio()
    
    # 绘制每只股票的K线图和交易信号
    for symbol in data_dict.keys():
        visualizer.plot_single_stock(symbol)


if __name__ == "__main__":
    main()
