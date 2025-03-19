import backtrader as bt


class PortfolioValue(bt.Analyzer):
    """分析器：记录每日账户总价值

    该分析器用于记录每个交易日的账户总价值（现金 + 持仓价值），
    可用于后续分析策略的收益表现和风险特征。
    """

    def start(self):
        # 初始化返回字典，用于存储每日账户价值
        self.rets = {}

    def notify_cashvalue(self, cash, value):
        # 记录日期和账户总价值（现金 + 持仓价值）
        self.rets[self.strategy.datetime.datetime()] = value

    def get_analysis(self):
        # 返回完整的账户价值序列
        return self.rets
