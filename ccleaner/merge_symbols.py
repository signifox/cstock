import os
import pandas as pd
from typing import List


import argparse


class CCleaner:
    def __init__(self, input_dir: str, output_dir: str):
        self.input_dir = input_dir
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def load_data(self, symbols: List[str]) -> dict:
        """
        从inputs目录加载所有CSV数据到内存，并只保留指定symbols的数据

        Args:
            symbols (List[str]): 要处理的symbol列表

        Returns:
            dict: 包含所有symbol数据的字典
        """
        data = {}
        for year_month in os.listdir(self.input_dir):
            year_month_dir = os.path.join(self.input_dir, year_month)
            if not os.path.isdir(year_month_dir):
                continue

            for filename in os.listdir(year_month_dir):
                if not filename.endswith(".csv"):
                    continue

                file_path = os.path.join(year_month_dir, filename)
                df = pd.read_csv(file_path)
                if not df.empty:
                    # 只保留指定symbols的数据
                    df = df[df["ticker"].isin(symbols)]
                    if not df.empty:
                        data[filename] = df
        return data

    def preprocess_data(self, data: dict, symbols: List[str]) -> dict:
        """
        预处理数据，包括过滤指定symbols和添加新列

        Args:
            data (dict): 原始数据字典
            symbols (List[str]): 要处理的symbol列表

        Returns:
            dict: 处理后的数据字典
        """
        processed_data = {symbol: pd.DataFrame() for symbol in symbols}

        for df in data.values():
            for symbol in symbols:
                symbol_data = df[df["ticker"] == symbol]
                # Convert window_start from nanoseconds to seconds and format as datetime
                symbol_data["window_start"] = pd.to_datetime(
                    symbol_data["window_start"] // 1000000000, unit="s"
                )
                symbol_data = symbol_data.rename(
                    columns={
                        "window_start": "date",
                        "open": "Open",
                        "high": "High",
                        "low": "Low",
                        "close": "Close",
                        "volume": "Volume",
                        "transactions": "Transactions",
                    }
                )
                if not symbol_data.empty:
                    symbol_data = symbol_data[
                        [
                            "date",
                            "Open",
                            "High",
                            "Low",
                            "Close",
                            "Volume",
                            "Transactions",
                        ]
                    ]
                    symbol_data = symbol_data.set_index("date")
                processed_data[symbol] = pd.concat(
                    [processed_data[symbol], symbol_data]
                )
        # 对每个symbol的数据进行排序
        for symbol in symbols:
            if not processed_data[symbol].empty:
                processed_data[symbol] = processed_data[symbol].sort_index(
                    ascending=True
                )
        return processed_data

    def save_data(self, data: dict) -> None:
        """
        将处理后的数据保存到outputs目录

        Args:
            data (dict): 处理后的数据字典
        """
        for symbol, df in data.items():
            if not df.empty:
                output_path = os.path.join(self.output_dir, f"{symbol}.min.csv")
                df.to_csv(output_path, index=True)
                print(f"Saved {symbol} data to {output_path}")

    def process_raw_data(self, raw_dir: str, symbols: List[str]) -> None:
        """处理raws目录下的分钟级交易数据

        Args:
            raw_dir (str): 包含原始CSV数据的目录
            symbols (List[str]): 要处理的symbol列表
        """
        for filename in os.listdir(raw_dir):
            if not filename.endswith(".csv"):
                continue

            symbol = filename.replace(".csv", "")
            if symbol not in symbols:
                continue

            file_path = os.path.join(raw_dir, filename)
            df = pd.read_csv(file_path)
            if not df.empty:
                # Convert window_start to datetime and set as index
                df["window_start"] = pd.to_datetime(df["window_start"])
                df = df.rename(
                    columns={
                        "window_start": "date",
                        "open": "Open",
                        "high": "High",
                        "low": "Low",
                        "close": "Close",
                        "volume": "Volume",
                        "transactions": "Transactions",
                    }
                )
                df = df[
                    [
                        "date",
                        "Open",
                        "High",
                        "Low",
                        "Close",
                        "Volume",
                        "Transactions",
                    ]
                ]
                df = df.set_index("date").sort_index(ascending=True)
                output_path = os.path.join(self.output_dir, f"{symbol}.min.csv")
                df.to_csv(output_path, index=True)
                print(f"Saved {symbol} data to {output_path}")


def parse_args():
    parser = argparse.ArgumentParser(description="合并指定symbol的CSV数据")
    parser.add_argument(
        "-i", "--input_dir", default="inputs", help="包含年月文件夹的输入目录"
    )
    parser.add_argument("-o", "--output_dir", default="output", help="输出目录")
    parser.add_argument(
        "-s",
        "--symbols",
        nargs="+",
        default=["SPY", "QQQ"],
        help="要合并的symbol列表",
    )
    parser.add_argument(
        "-r",
        "--raw_dir",
        help="包含原始CSV数据的目录，如果指定此参数，将处理raw目录下的数据而不是input目录",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    cleaner = CCleaner(args.input_dir, args.output_dir)

    if args.raw_dir:
        cleaner.process_raw_data(args.raw_dir, args.symbols)
    else:
        raw_data = cleaner.load_data(args.symbols)
        processed_data = cleaner.preprocess_data(raw_data, args.symbols)
        cleaner.save_data(processed_data)
