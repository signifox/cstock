import backtrader as bt
from cstock.data_fetcher import DataFetcher
from cstock.analyzer import Analyzer
from cstock.backtest_engine import BacktestEngine
from cstock.config import config

from cstock.strategies.macd_rsi_strategy import MACDRSIStrategy
from cstock.strategies.sma_crossover import SMACrossoverStrategy


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
        strategy_class=MACDRSIStrategy,
        initial_cash=config.INITIAL_CASH,
        commission=config.COMMISSION_RATE,
    )

    # 运行回测
    engine.run_backtest()

    # 创建分析器并打印结果摘要
    analyzer = Analyzer(engine)
    analyzer.print_summary()
    
    # 绘制回测结果图表
    analyzer.plot_results()


if __name__ == "__main__":
    main()
