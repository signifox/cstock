import os
import pandas as pd
import akshare as ak
import logging
import argparse
from typing import Dict, List, Optional

# 配置日志记录
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Fetch daily stock data for specified symbols"
    )
    parser.add_argument(
        "symbols",
        nargs="+",
        help="List of stock symbols to fetch data for",
    )
    parser.add_argument(
        "-s",
        "--start-date",
        help=f"Start date in YYYY-MM-DD format",
    )
    parser.add_argument(
        "-e",
        "--end-date",
        help=f"End date in YYYY-MM-DD format",
    )
    parser.add_argument(
        "-d",
        "--data-dir",
        help=f"Directory to store data files",
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Force update data even if cache exists",
    )

    return parser.parse_args()


def fetch_stock_data(
    symbol: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    force_update: bool = False,
) -> Optional[pd.DataFrame]:
    """
    获取指定日期范围的股票数据

    Args:
        symbol (str): 股票代码
        start_date (str, optional): 开始日期，格式为YYYY-MM-DD
        end_date (str, optional): 结束日期，格式为YYYY-MM-DD
        force_update (bool): 是否强制更新数据，默认为False

    Returns:
        Optional[pd.DataFrame]: 股票数据，如果获取失败则返回None
    """
    try:
        # 构建缓存文件路径
        cache_dir = "data"
        os.makedirs(cache_dir, exist_ok=True)
        cache_file = os.path.join(cache_dir, f"{symbol}.day.csv")

        # 如果缓存文件存在且不强制更新，则从缓存加载数据
        if os.path.exists(cache_file) and not force_update:
            logger.info(f"从本地文件加载{symbol}数据")
            stock_data = pd.read_csv(cache_file, index_col=0, parse_dates=True)
        else:
            # 从akshare获取未复权和前复权数据
            logger.info(f"从AKShare获取{symbol}数据")
            stock_data = ak.stock_us_daily(symbol=symbol)
            qfq_data = ak.stock_us_daily(symbol=symbol, adjust="qfq")

            # 转换日期列为索引
            stock_data["date"] = pd.to_datetime(stock_data["date"])
            qfq_data["date"] = pd.to_datetime(qfq_data["date"])
            stock_data = stock_data.set_index("date")
            qfq_data = qfq_data.set_index("date")

            # 重命名列
            stock_data = stock_data.rename(
                columns={
                    "volume": "Volume",
                }
            )
            qfq_data = qfq_data.rename(
                columns={
                    "open": "adjOpen",
                    "high": "adjHigh",
                    "low": "adjLow",
                    "close": "adjClose",
                }
            )

            # 合并前复权数据
            stock_data = pd.concat(
                [stock_data, qfq_data[["adjOpen", "adjHigh", "adjLow", "adjClose"]]],
                axis=1,
            )

            # 根据日期范围过滤数据
            if start_date:
                logger.info(f"过滤数据，从{start_date}开始")
                stock_data = stock_data[stock_data.index >= pd.to_datetime(start_date)]
            if end_date:
                logger.info(f"过滤数据，到{end_date}结束")
                stock_data = stock_data[stock_data.index <= pd.to_datetime(end_date)]

            # 保存到缓存文件
            stock_data.to_csv(cache_file)

        return stock_data

    except Exception as e:
        logger.error(f"获取{symbol}数据时发生错误: {str(e)}")
        return None


def fetch_multiple_stocks(
    symbols: List[str],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    force_update: bool = False,
) -> Dict[str, pd.DataFrame]:
    """
    批量获取多个股票的数据

    Args:
        symbols (List[str]): 股票代码列表
        start_date (str, optional): 开始日期，格式为YYYY-MM-DD
        end_date (str, optional): 结束日期，格式为YYYY-MM-DD
        force_update (bool): 是否强制更新数据，默认为False

    Returns:
        Dict[str, pd.DataFrame]: 股票代码到数据的映射字典
    """
    data_dict = {}
    for symbol in symbols:
        data = fetch_stock_data(symbol, start_date, end_date, force_update)
        if data is not None:
            data_dict[symbol] = data
        else:
            logger.warning(f"跳过{symbol}，因为获取数据失败")

    return data_dict


def main():
    args = parse_args()

    # 确保数据目录存在
    os.makedirs(args.data_dir, exist_ok=True)

    # 获取股票数据
    data_dict = fetch_multiple_stocks(
        symbols=args.symbols,
        start_date=args.start_date,
        end_date=args.end_date,
        force_update=args.force,
    )

    # 打印获取结果
    for symbol, data in data_dict.items():
        if data is not None:
            print(f"Successfully fetched data for {symbol}")
            print(f"Data shape: {data.shape}")
            print(f"Date range: {data.index.min()} to {data.index.max()}")
            print("---")


if __name__ == "__main__":
    main()
    # python ccleaner/day_fetcher.py AAPL BRK.B MSFT QQQ SPY TSLA -s 2015-03-09 -e 2025-03-21 -d ./data -f
