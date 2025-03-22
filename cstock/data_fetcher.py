import os
import pandas as pd
import akshare as ak
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
        Fetch historical stock data

        Parameters:
            symbol (str): Stock symbol
            start_date (str): Start date in YYYY-MM-DD format
            end_date (str): End date in YYYY-MM-DD format
            force_update (bool): Whether to force update data

        Returns:
            pandas.DataFrame: Historical stock data
        """
        file_path = os.path.join(self.data_dir, f"{symbol}.csv")

        # Load from local file if exists and not force update
        if os.path.exists(file_path) and not force_update:
            print(f"Loading {symbol} data from local file")
            return pd.read_csv(file_path, index_col=0, parse_dates=True)

        print(f"Fetching {symbol} data from AKShare")
        try:
            # Get US stock data using akshare
            stock_data = ak.stock_us_daily(symbol=symbol, adjust="qfq")

            # Convert date to datetime
            stock_data["date"] = pd.to_datetime(stock_data["date"])
            stock_data = stock_data.set_index("date")

            # Filter data by date range
            start_date = pd.to_datetime(start_date)
            end_date = pd.to_datetime(end_date)

            # Rename columns to match backtrader
            stock_data = stock_data.rename(
                {
                    "open": "Open",
                    "high": "High",
                    "low": "Low",
                    "close": "Close",
                    "volume": "Volume",
                }
            )

            # Save to local file
            stock_data.to_csv(file_path)

            stock_data = stock_data[
                (stock_data.index >= start_date) & (stock_data.index <= end_date)
            ]
            return stock_data

        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            return None

    def fetch_multiple_stocks(
        self,
        symbols=None,
        start_date=config.START_DATE,
        end_date=config.END_DATE,
        force_update=False,
    ):
        """
        Fetch data for multiple stocks

        Parameters:
            symbols (list): List of stock symbols, defaults to config stock list
            start_date (str): Start date
            end_date (str): End date
            force_update (bool): Whether to force update data

        Returns:
            dict: Mapping from stock symbols to data
        """
        if symbols is None:
            symbols = config.STOCK_LIST

        data_dict = {}
        for symbol in symbols:
            data = self.fetch_stock_data(symbol, start_date, end_date, force_update)
            if data is not None:
                data_dict[symbol] = data

        return data_dict
