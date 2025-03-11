# 配置文件


class Config:
    def __init__(self):
        # 数据相关配置
        self.DATA_DIR = "data"
        self.START_DATE = "2022-06-01"
        self.END_DATE = "2024-12-31"

        # 回测相关配置
        self.INITIAL_CASH = 100000  # 初始资金
        self.COMMISSION_RATE = 0.001  # 手续费率

        # 股票池配置
        self.STOCK_LIST = [
            "AAPL",  # 苹果
            "MSFT",  # 微软
            "AMZN",  # 亚马逊
            # "GOOGL",  # 谷歌
            # "TSLA",  # 特斯拉
            # "META",  # Meta(Facebook)
        ]


# 创建全局配置实例
config = Config()

# 导出全局变量，保持向后兼容性
DATA_DIR = config.DATA_DIR
START_DATE = config.START_DATE
END_DATE = config.END_DATE
INITIAL_CASH = config.INITIAL_CASH
COMMISSION_RATE = config.COMMISSION_RATE
STOCK_LIST = config.STOCK_LIST
