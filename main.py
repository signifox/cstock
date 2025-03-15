import backtrader as bt
from cstock.data_fetcher import DataFetcher
from cstock.analyzer import Analyzer
from cstock.backtest_engine import BacktestEngine
from cstock.config import config

from cstock.strategies.macd_rsi_strategy import MACDRSIStrategy
from cstock.strategies.sma_crossover import SMACrossoverStrategy
from cstock.strategies.dual_thrust_strategy import DualThrustStrategy
from cstock.strategies.dca_strategy import DCAStrategy


def main():
    # Initialize data fetcher
    data_fetcher = DataFetcher()

    # Fetch backtest data for all stocks
    data_dict = data_fetcher.fetch_multiple_stocks(
        symbols=config.STOCK_LIST,
        start_date=config.START_DATE,
        end_date=config.END_DATE,
    )

    # Initialize backtest engine
    engine = BacktestEngine(
        data_dict=data_dict,
        strategy_class=DCAStrategy,
        initial_cash=config.INITIAL_CASH,
        commission=config.COMMISSION_RATE,
    )

    # Run backtest
    engine.run_backtest()

    # Create analyzer and print summary
    analyzer = Analyzer(engine)
    analyzer.print_summary()

    # Plot backtest results
    # analyzer.plot_results()


if __name__ == "__main__":
    main()
