import os
import pandas as pd
import akshare as ak
from datetime import datetime
from cstock import config


class DataFetcher:
    def __init__(self, data_dir=config.DATA_DIR):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)

    def fetch_stock_data(
        self,
        symbol,
        start_date=config.START_DATE,
        end_date=config.END_DATE,
        force_update=False,
    ):
        """
        获取美股历史数据并保存到本地

        参数:
            symbol (str): 股票代码
            start_date (str): 开始日期，格式：YYYY-MM-DD
            end_date (str): 结束日期，格式：YYYY-MM-DD
            force_update (bool): 是否强制更新数据

        返回:
            pandas.DataFrame: 股票历史数据
        """
        file_path = os.path.join(self.data_dir, f"{symbol}.csv")

        # 如果文件存在且不强制更新，则直接读取本地文件
        if os.path.exists(file_path) and not force_update:
            print(f"从本地加载 {symbol} 的数据")
            return pd.read_csv(file_path, index_col=0, parse_dates=True)

        print(f"从AKShare获取 {symbol} 的数据")
        try:
            # 使用akshare获取美股数据
            stock_data = ak.stock_us_daily(symbol=symbol, adjust="qfq")

            # 处理日期格式
            stock_data["date"] = pd.to_datetime(stock_data["date"])
            stock_data = stock_data.set_index("date")

            # 筛选日期范围
            start_date = pd.to_datetime(start_date)
            end_date = pd.to_datetime(end_date)
            stock_data = stock_data[
                (stock_data.index >= start_date) & (stock_data.index <= end_date)
            ]

            # 重命名列以适配backtrader
            stock_data = stock_data.rename(
                columns={
                    "open": "Open",
                    "high": "High",
                    "low": "Low",
                    "close": "Close",
                    "volume": "Volume",
                }
            )

            # 保存到本地
            stock_data.to_csv(file_path)

            return stock_data

        except Exception as e:
            print(f"获取 {symbol} 数据时出错: {e}")
            return None

    def fetch_multiple_stocks(
        self,
        symbols=None,
        start_date=config.START_DATE,
        end_date=config.END_DATE,
        force_update=False,
    ):
        """
        批量获取多只股票的数据

        参数:
            symbols (list): 股票代码列表，默认为配置文件中的股票列表
            start_date (str): 开始日期
            end_date (str): 结束日期
            force_update (bool): 是否强制更新数据

        返回:
            dict: 股票代码到数据的映射
        """
        if symbols is None:
            symbols = config.STOCK_LIST

        data_dict = {}
        for symbol in symbols:
            data = self.fetch_stock_data(symbol, start_date, end_date, force_update)
            if data is not None:
                data_dict[symbol] = data

        return data_dict
