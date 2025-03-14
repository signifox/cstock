# Configuration File


class Config:
    def __init__(self):
        # Data Configuration
        self.DATA_DIR = "data"
        self.START_DATE = "2022-06-01"
        self.END_DATE = "2024-12-31"

        # Backtest Configuration
        self.INITIAL_CASH = 100000  # Initial Capital
        self.COMMISSION_RATE = 0.001  # Commission Rate

        # Stock Pool Configuration
        self.STOCK_LIST = [
            # "AAPL",  # Apple Inc.
            # "MSFT",  # Microsoft Corporation
            # "AMZN",  # Amazon.com Inc.
            # "GOOGL",  # Alphabet Inc.
            "TSLA",  # Tesla Inc.
            # "META",  # Meta Platforms Inc.
        ]


# Create global configuration instance
config = Config()

# Export global variables for backward compatibility
DATA_DIR = config.DATA_DIR
START_DATE = config.START_DATE
END_DATE = config.END_DATE
INITIAL_CASH = config.INITIAL_CASH
COMMISSION_RATE = config.COMMISSION_RATE
STOCK_LIST = config.STOCK_LIST
