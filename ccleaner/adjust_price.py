import os
import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging
import pytz
import argparse


# 配置日志记录
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_daily_close(
    symbol: str,
    date: datetime,
    daily_data: pd.DataFrame,
) -> Optional[float]:
    """
    从天级数据中获取指定日期的收盘价

    Args:
        symbol (str): 股票代码
        date (datetime): 日期

    Returns:
        float: 收盘价，如果获取失败则返回None
    """
    try:
        # 确保日期格式为YYYY-MM-DD
        if not isinstance(date.date(), str):
            date_str = date.date().strftime("%Y-%m-%d")
        else:
            date_str = date.date()
        close_price = daily_data.loc[date_str, "Close"]
        return float(close_price)
    except KeyError:
        logger.warning(f"未找到{symbol}在{date}的收盘价数据")
        return None
    except Exception as e:
        logger.error(f"获取{symbol}在{date}的收盘价时发生错误: {str(e)}")
        return None


class PriceAdjuster:
    def __init__(self, symbols: List[str], daily_data_dir: str = "data"):
        self.daily_data_dir = daily_data_dir
        self.symbols = symbols
        self.file_paths = {
            symbol: os.path.join(self.daily_data_dir, f"{symbol}.day.csv")
            for symbol in symbols
        }
        # 初始化时一次性加载所有symbol的daily_data
        self.daily_data = {
            symbol: pd.read_csv(path, index_col=0, parse_dates=True)
            for symbol, path in self.file_paths.items()
            if os.path.exists(path)
        }

    def load_adjust_data(
        self, dividends_file: str, splits_file: str
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        加载分红派息和拆股并股数据，并过滤出指定symbols的记录

        Args:
            dividends_file (str): 分红派息数据文件路径
            splits_file (str): 拆股并股数据文件路径

        Returns:
            tuple[pd.DataFrame, pd.DataFrame]: 过滤后的分红派息和拆股并股数据
        """
        # 读取分红派息数据
        dividends_df = pd.read_csv(dividends_file)
        # 过滤出指定symbols和USD货币的记录
        dividends_df = dividends_df[
            (dividends_df["ticker"].isin(self.symbols))
            & (dividends_df["currency"] == "USD")
        ]
        # 转换日期列
        date_columns = [
            "declaration_date",
            "ex_dividend_date",
            "pay_date",
            "record_date",
        ]
        for col in date_columns:
            dividends_df[col] = pd.to_datetime(dividends_df[col])

        # 读取拆股并股数据
        splits_df = pd.read_csv(splits_file)
        # 过滤出指定symbols的记录
        splits_df = splits_df[splits_df["ticker"].isin(self.symbols)]
        # 转换日期列
        splits_df["execution_date"] = pd.to_datetime(splits_df["execution_date"])

        return dividends_df, splits_df

    def calculate_adjustment_factors(
        self,
        price_data: pd.DataFrame,
        dividends: pd.DataFrame,
        splits: pd.DataFrame,
        symbol: str,
    ) -> pd.DataFrame:
        """计算前复权因子

        Args:
            price_data (pd.DataFrame): 价格数据，index为UTC时间
            dividends (pd.DataFrame): 分红派息数据
            splits (pd.DataFrame): 拆股并股数据
            symbol (str): 股票代码

        Returns:
            pd.DataFrame: 添加了复权因子的价格数据
        """
        # 检查数据是否为空
        if price_data.empty:
            logger.warning(f"{symbol}的价格数据为空，无法计算复权因子")
            return price_data

        # 过滤出当前symbol的调整数据
        symbol_dividends = dividends[dividends["ticker"] == symbol]
        symbol_splits = splits[splits["ticker"] == symbol]

        # 初始化复权因子
        price_data["adjust_factor"] = 1.0

        # 确保price_data的索引是UTC时区
        utc_tz = pytz.UTC
        if price_data.index.tz is None:
            price_data.index = price_data.index.tz_localize(utc_tz)

        # 处理分红派息
        for _, div in symbol_dividends.iterrows():
            try:
                ex_date = div["ex_dividend_date"]
                cash_amount = div["cash_amount"]

                # 跳过无效记录
                if pd.isna(ex_date) or pd.isna(cash_amount):
                    logger.warning(f"跳过无效的分红记录: {div['ticker']}")
                    continue

                # 确保ex_date是UTC时区
                if ex_date.tzinfo is None:
                    ex_date = utc_tz.localize(ex_date)
                elif ex_date.tzinfo != utc_tz:
                    ex_date = ex_date.astimezone(utc_tz)

                # 检查ex_date是否在数据范围内
                if (
                    ex_date < price_data.index[0].to_pydatetime()
                    or ex_date > price_data.index[-1].to_pydatetime()
                ):
                    logger.warning(
                        f"除权日{ex_date}超出数据范围({price_data.index[0]} - {price_data.index[-1]})，跳过该分红记录"
                    )
                    continue

                # 获取除权日当天的收盘价
                ex_close = get_daily_close(symbol, ex_date, self.daily_data[symbol])
                print(f"===================>{symbol}在{ex_date}的收盘价为{ex_close}")
                # 获取除权日的收盘时间（UTC 21:00）
                et_tz = pytz.timezone("America/New_York")
                et_close = et_tz.localize(
                    datetime.combine(
                        ex_date.date(),
                        datetime.strptime("16:00", "%H:%M").time(),
                    )
                )
                utc_close = et_close.astimezone(utc_tz)

                # 计算分红调整因子
                div_factor = (ex_close - cash_amount) / ex_close

                # 更新复权因子
                price_data.loc[
                    price_data.index <= utc_close, "adjust_factor"
                ] *= div_factor

            except Exception as e:
                logger.error(f"处理分红记录时出错 {div['ticker']}: {str(e)}")

        # 处理拆股并股
        for _, split in symbol_splits.iterrows():
            try:
                execution_date = split["execution_date"]

                # 确保execution_date是UTC时区
                if execution_date.tzinfo is None:
                    execution_date = utc_tz.localize(execution_date)
                elif execution_date.tzinfo != utc_tz:
                    execution_date = execution_date.astimezone(utc_tz)

                # 检查执行日期是否在数据范围内
                if (
                    execution_date < price_data.index[0].to_pydatetime()
                    or execution_date > price_data.index[-1].to_pydatetime()
                ):
                    logger.warning(
                        f"拆股日期{execution_date}超出数据范围({price_data.index[0]} - {price_data.index[-1]})，结束后续复权因子计算"
                    )
                    return price_data

                # 计算拆股因子
                split_factor = split["split_from"] / split["split_to"]
                print(
                    f"===================>{symbol}在{execution_date}的拆股因子为{split_factor}"
                )
                # 更新复权因子
                # 初始化时区变量
                et_tz = pytz.timezone("America/New_York")
                # 获取执行日的开盘时间（UTC 9:30）
                et_open = et_tz.localize(
                    datetime.combine(
                        execution_date.date(),
                        datetime.strptime("09:30", "%H:%M").time(),
                    )
                )
                utc_open = et_open.astimezone(utc_tz)

                price_data.loc[
                    price_data.index <= utc_open, "adjust_factor"
                ] *= split_factor

            except Exception as e:
                logger.error(f"处理拆股记录时出错 {split['ticker']}: {str(e)}")

        return price_data

    def adjust_price(
        self, price_data: pd.DataFrame, adjust_factor: pd.Series
    ) -> pd.DataFrame:
        """
        使用复权因子调整价格数据

        Args:
            price_data (pd.DataFrame): 原始价格数据
            adjust_factor (pd.Series): 复权因子，与price_data索引对应

        Returns:
            pd.DataFrame: 调整后的价格数据
        """
        # 一次性调整所有OHLC价格列
        price_columns = ["Open", "High", "Low", "Close"]
        for col in price_columns:
            price_data[col] = price_data[col] * adjust_factor
        return price_data

    def process_data(
        self, data: Dict[str, pd.DataFrame], dividends_file: str, splits_file: str
    ) -> Dict[str, pd.DataFrame]:
        """
        处理所有symbol的数据

        Args:
            data (Dict[str, pd.DataFrame]): 原始价格数据字典
            dividends_file (str): 分红派息数据文件路径
            splits_file (str): 拆股并股数据文件路径

        Returns:
            Dict[str, pd.DataFrame]: 处理后的价格数据字典
        """
        # 加载调整数据
        dividends_df, splits_df = self.load_adjust_data(dividends_file, splits_file)

        # 处理每个symbol的数据
        adjusted_data = {}
        for symbol, price_data in data.items():
            if price_data.empty:
                logger.warning(f"{symbol}的价格数据为空，跳过处理")
                continue

            try:
                # 确保时区一致性
                if price_data.index.tz is None:
                    price_data.index = price_data.index.tz_localize(pytz.UTC)

                # 计算复权因子
                price_data = self.calculate_adjustment_factors(
                    price_data, dividends_df, splits_df, symbol
                )
                # 应用复权因子并创建新的DataFrame避免修改原始数据
                adjusted_price_data = price_data.copy()
                adjusted_data[symbol] = self.adjust_price(
                    adjusted_price_data, price_data["adjust_factor"]
                )
                logger.info(f"成功处理 {symbol} 的数据")
            except Exception as e:
                logger.error(f"处理 {symbol} 数据时出错: {str(e)}")
                adjusted_data[symbol] = price_data

        return adjusted_data


def load_price_data(input_dir: str, symbols: List[str]) -> Dict[str, pd.DataFrame]:
    data = {}
    for symbol in symbols:
        file_path = os.path.join(input_dir, f"{symbol}.min.csv")
        try:
            if os.path.exists(file_path):
                # 使用更高效的数据类型推断和解析日期列
                df = pd.read_csv(
                    file_path,
                    parse_dates=["date"],  # 直接解析日期列
                    dtype={  # 指定数据类型以提高性能
                        "Open": float,
                        "High": float,
                        "Low": float,
                        "Close": float,
                        "Volume": float,
                    },
                )
                # 设置UTC时区
                df["date"] = df["date"].dt.tz_localize(pytz.UTC)
                df = df.set_index("date")
                data[symbol] = df
            else:
                logger.warning(f"找不到 {symbol} 的数据文件: {file_path}")
                data[symbol] = pd.DataFrame()
        except Exception as e:
            logger.error(f"加载 {symbol} 数据时出错: {str(e)}")
            data[symbol] = pd.DataFrame()

    return data


def save_adjusted_data(data: Dict[str, pd.DataFrame], output_dir: str) -> None:
    """
    保存调整后的数据

    Args:
        data (Dict[str, pd.DataFrame]): 调整后的数据字典
        output_dir (str): 输出目录路径
    """
    try:
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)

        # 记录处理的统计信息
        total_symbols = len(data)
        saved_symbols = 0
        empty_symbols = 0

        for symbol, df in data.items():
            try:
                if not df.empty:
                    # 格式化数据
                    # 对数值列保留4位小数
                    numeric_columns = [
                        "Open",
                        "High",
                        "Low",
                        "Close",
                        "Volume",
                        "adjust_factor",
                    ]
                    df[numeric_columns] = df[numeric_columns].round(4)

                    # 格式化日期列
                    df.index = df.index.strftime("%Y-%m-%d %H:%M:%S")

                    output_path = os.path.join(output_dir, f"{symbol}.min.csv")
                    df.to_csv(output_path, index=True)
                    logger.info(
                        f"保存 {symbol} 的调整后数据到 {output_path}，共 {len(df)} 条记录"
                    )
                    saved_symbols += 1
                else:
                    logger.warning(f"{symbol} 的数据为空，跳过保存")
                    empty_symbols += 1
            except Exception as e:
                logger.error(f"保存 {symbol} 数据时出错: {str(e)}")

        # 输出总体统计信息
        logger.info(
            f"数据保存完成: 总计 {total_symbols} 个symbol，成功保存 {saved_symbols} 个，{empty_symbols} 个为空"
        )
    except Exception as e:
        logger.error(f"保存数据时出错: {str(e)}")
        raise


def parse_args():
    parser = argparse.ArgumentParser(description="对分钟级数据进行前复权处理")
    parser.add_argument(
        "-i", "--input_dir", default="../output", help="包含原始价格数据的输入目录"
    )
    parser.add_argument(
        "-o", "--output_dir", default="data", help="调整后数据的输出目录"
    )
    parser.add_argument(
        "-s",
        "--symbols",
        nargs="+",
        default=["SPY", "QQQ", "TSLA", "AAPL", "BRK.B", "MSFT"],
        help="要处理的symbol列表",
    )
    parser.add_argument(
        "-d",
        "--dividends_file",
        default="../adjust_config/dividends_data.csv",
        help="分红派息数据文件路径",
    )
    parser.add_argument(
        "-p",
        "--splits_file",
        default="../adjust_config/splits_data.csv",
        help="拆股并股数据文件路径",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    # 加载原始价格数据
    price_data = load_price_data(args.input_dir, args.symbols)

    # 创建PriceAdjuster实例并处理数据
    adjuster = PriceAdjuster(args.symbols)
    adjusted_data = adjuster.process_data(
        price_data, args.dividends_file, args.splits_file
    )

    # 保存调整后的数据
    save_adjusted_data(adjusted_data, args.output_dir)
