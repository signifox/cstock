import os
import pandas as pd
import akshare as ak
from cstock import config


class DataFetcher:
    def __init__(self, data_dir=config.DATA_DIR):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)

    def load_local_data(
        self, symbol: str, data_type: str = config.DATA_TYPE
    ) -> pd.DataFrame:
        """
        Load stock data from local file

        Parameters:
            symbol (str): Stock symbol
            data_type (str): Data type, either 'day' or 'min'

        Returns:
            pandas.DataFrame: Stock data from local file, or None if file not found
        """
        file_path = os.path.join(self.data_dir, f"{symbol}.{data_type}.csv")
        if os.path.exists(file_path):
            print(f"Loading {symbol} {data_type} data from local file")
            data = pd.read_csv(file_path, index_col=0, parse_dates=True)
            if data_type == "day":
                # 重命名前复权列名
                rename_map = {
                    "adjOpen": "Open",
                    "adjHigh": "High",
                    "adjLow": "Low",
                    "adjClose": "Close",
                }
                data = data.rename(columns=rename_map)
            return data
        return None

    def fetch_stock_data(
        self,
        symbol,
        start_date=config.START_DATE,
        end_date=config.END_DATE,
        data_type=config.DATA_TYPE,
    ):
        """
        Load historical stock data from local file

        Parameters:
            symbol (str): Stock symbol
            start_date (str): Start date in YYYY-MM-DD format
            end_date (str): End date in YYYY-MM-DD format
            data_type (str): Data type, either 'day' or 'min'

        Returns:
            pandas.DataFrame: Historical stock data
        """
        local_data = self.load_local_data(symbol, data_type)
        if local_data is not None:
            # 根据日期范围过滤数据
            start_date = pd.to_datetime(start_date)
            end_date = pd.to_datetime(end_date)
            local_data = local_data[
                (local_data.index >= start_date) & (local_data.index <= end_date)
            ]
            return local_data
        return None

    def fetch_multiple_stocks(
        self,
        symbols=None,
        start_date=config.START_DATE,
        end_date=config.END_DATE,
        data_type=config.DATA_TYPE,
    ):
        """
        Fetch data for multiple stocks

        Parameters:
            symbols (list): List of stock symbols, defaults to config stock list
            start_date (str): Start date
            end_date (str): End date
            data_type (str): Data type, either 'day' or 'min'

        Returns:
            dict: Mapping from stock symbols to data
        """
        if symbols is None:
            symbols = config.STOCK_LIST

        data_dict = {}
        for symbol in symbols:
            data = self.fetch_stock_data(symbol, start_date, end_date, data_type)
            if data is not None:
                data_dict[symbol] = data

        return data_dict
