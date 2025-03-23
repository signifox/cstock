# Configuration File


class Config:
    def __init__(self):
        # Data Configuration
        self.DATA_DIR = "data"
        self.START_DATE = "2015-03-09"
        self.END_DATE = "2025-03-21"
        self.DATA_TYPE = "day"  # Data type, either 'day' or 'min'

        # Backtest Configuration
        self.INITIAL_CASH = 100000  # Initial Capital
        self.COMMISSION_RATE = 0.001  # Commission Rate

        # Output Configuration
        self.SHOW_TRANSACTIONS = (
            False  # Whether to show transaction details in backtest results
        )
        self.SHOW_PLOT = False  # Whether to show plot after backtest
        self.ENABLE_REPORT = False  # Whether to enable report generation

        # Stock Pool Configuration
        self.STOCK_LIST = [
            # "AAPL",  # Apple Inc.
            # "MSFT",  # Microsoft Corporation
            # "BRK.B",  # Berkshire Hathaway Inc.
            # "TSLA",  # Tesla Inc.
            "SPY",
            "QQQ",
        ]


# Create global configuration instance
config = Config()

# Export global variables for backward compatibility
DATA_DIR = config.DATA_DIR
START_DATE = config.START_DATE
END_DATE = config.END_DATE
DATA_TYPE = config.DATA_TYPE
INITIAL_CASH = config.INITIAL_CASH
COMMISSION_RATE = config.COMMISSION_RATE
STOCK_LIST = config.STOCK_LIST
SHOW_TRANSACTIONS = config.SHOW_TRANSACTIONS
SHOW_PLOT = config.SHOW_PLOT
ENABLE_REPORT = config.ENABLE_REPORT
