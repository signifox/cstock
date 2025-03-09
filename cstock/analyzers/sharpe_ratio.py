import backtrader as bt
import numpy as np
import pandas as pd
import akshare as ak
from datetime import datetime, timedelta

class SharpRatioClass(bt.analyzers.Analyzer):
    """自定义夏普比率分析器
    
    计算策略的夏普比率，即超额收益与波动率之比。
    夏普比率 = (策略收益率 - 无风险收益率) / 策略收益率的标准差
    
    参数:
        - timeframe: 计算收益率的时间框架 (默认: bt.TimeFrame.Days)
        - compression: 时间框架的压缩 (默认: 1)
        - riskfreerate: 无风险收益率 (默认: 0.0)，如果use_treasury_rate为True，则此参数被忽略
        - factor: 年化因子 (默认: 252，对应交易日数量)
        - annualize: 是否年化结果 (默认: True)
        - use_treasury_rate: 是否使用国债收益率作为无风险收益率 (默认: True)
        - treasury_period: 使用哪个期限的国债收益率 (默认: '2年')
    """
    
    params = (
        ('timeframe', bt.TimeFrame.Days),
        ('compression', 1),
        ('riskfreerate', 0.0),
        ('factor', 252),  # 252个交易日/年
        ('annualize', True),
        ('use_treasury_rate', True),  # 是否使用国债收益率
        ('treasury_period', '2年'),  # 使用哪个期限的国债收益率
    )
    
    def __init__(self):
        self.returns = list()  # 存储每个周期的收益率
        self.date_returns = list()  # 存储日期和收益率的元组
        self.risk_free_rates = {}  # 存储无风险收益率数据
        self.last_value = None  # 存储上一个周期的投资组合价值
        
    def start(self):
        # 初始化时获取起始资金
        self.initial_value = self.strategy.broker.getvalue()
        
        # 如果使用国债收益率，则获取数据
        if self.p.use_treasury_rate:
            self._fetch_treasury_rate()
        
    def _fetch_treasury_rate(self):
        """获取国债收益率数据"""
        try:
            # 获取美国国债收益率数据
            treasury_data = ak.bond_zh_us_rate()
            
            # 转换日期列为日期类型
            treasury_data['日期'] = pd.to_datetime(treasury_data['日期'])
            
            # 根据参数选择对应期限的国债收益率
            rate_column = f'美国国债收益率{self.p.treasury_period}'
            
            # 创建日期到收益率的映射
            for _, row in treasury_data.iterrows():
                date = row['日期'].date()
                rate = row[rate_column]
                if not pd.isna(rate):  # 确保收益率不是NaN
                    # 将百分比转换为小数
                    self.risk_free_rates[date] = rate / 100.0
            
            print(f"成功获取国债收益率数据，共{len(self.risk_free_rates)}条记录")
        except Exception as e:
            print(f"获取国债收益率数据出错: {e}")
            print("将使用默认无风险收益率")
        
    def _get_risk_free_rate(self, date):
        """获取指定日期的无风险收益率"""
        if not self.p.use_treasury_rate or not self.risk_free_rates:
            return self.p.riskfreerate
        
        # 将datetime转换为date
        if isinstance(date, datetime):
            date = date.date()
        
        # 如果有精确匹配的日期，直接返回
        if date in self.risk_free_rates:
            return self.risk_free_rates[date]
        
        # 如果没有精确匹配，找最近的日期
        nearest_date = None
        min_days_diff = float('inf')
        
        for treasury_date in self.risk_free_rates.keys():
            days_diff = abs((date - treasury_date).days)
            if days_diff < min_days_diff:
                min_days_diff = days_diff
                nearest_date = treasury_date
        
        # 如果找到最近的日期，且相差不超过30天，则使用该日期的收益率
        if nearest_date and min_days_diff <= 30:
            return self.risk_free_rates[nearest_date]
        
        # 否则使用默认值
        return self.p.riskfreerate
        
    def next(self):
        # 计算当前周期的收益率
        current_value = self.strategy.broker.getvalue()
        
        # 修正收益率计算逻辑
        # 使用初始值或上一个周期的实际值作为基准
        if self.last_value is None:
            prev_value = self.initial_value
        else:
            prev_value = self.last_value
        
        # 计算收益率并存储
        r = (current_value / prev_value) - 1.0
        self.returns.append(r)
        
        # 打印调试信息
        print(f"周期收益率: {r:.6f}, 当前值: {current_value:.2f}, 前值: {prev_value:.2f}")
        
        # 更新上一个周期的值
        self.last_value = current_value
        
        # 存储日期和收益率
        dt = self.strategy.datetime.datetime()
        self.date_returns.append((dt, r))
        
    def stop(self):
        # 计算夏普比率
        if not self.returns:
            self.ratio = 0.0
            self.ann_ratio = 0.0
            print("警告: 没有收益率数据，夏普比率设为0")
            return
        
        # 计算平均收益率和标准差
        ret_arr = np.array(self.returns)
        avg_ret = np.mean(ret_arr)
        std_ret = np.std(ret_arr, ddof=1)  # 使用样本标准差
        
        print(f"调试信息 - 收益率数据点数量: {len(self.returns)}")
        print(f"调试信息 - 平均收益率: {avg_ret:.6f}")
        print(f"调试信息 - 收益率标准差: {std_ret:.6f}")
        
        # 避免除零错误
        if std_ret == 0.0:
            self.ratio = 0.0
            self.ann_ratio = 0.0
            print("警告: 收益率标准差为0，夏普比率设为0")
            return
        
        # 获取回测期间的平均无风险收益率
        if self.p.use_treasury_rate and self.date_returns:
            # 计算回测期间的平均无风险收益率
            risk_free_rates = [self._get_risk_free_rate(date) for date, _ in self.date_returns]
            avg_risk_free = np.mean(risk_free_rates) if risk_free_rates else self.p.riskfreerate
            print(f"调试信息 - 使用国债收益率数据点: {len(risk_free_rates)}")
        else:
            avg_risk_free = self.p.riskfreerate
            print(f"调试信息 - 使用默认无风险收益率: {avg_risk_free:.6f}")
        
        # 对齐收益率和无风险收益率的计算口径
        # 将策略的日收益率转换为年化收益率，以匹配无风险收益率的时间尺度
        annual_avg_ret = (1 + avg_ret) ** self.p.factor - 1
        print(f"调试信息 - 平均收益率(日): {avg_ret:.6f}")
        print(f"调试信息 - 平均收益率(年化): {annual_avg_ret:.6f}")
        print(f"调试信息 - 平均无风险收益率(年化): {avg_risk_free:.6f}")
        
        # 计算夏普比率 - 使用相同时间尺度的收益率(年化)
        excess_return = annual_avg_ret - avg_risk_free
        print(f"调试信息 - 超额收益率(年化): {excess_return:.6f}")
        
        self.ratio = excess_return / std_ret
        
        # 年化夏普比率
        if self.p.annualize:
            self.ann_ratio = self.ratio * np.sqrt(self.p.factor)
        else:
            self.ann_ratio = self.ratio
            
        print(f"调试信息 - 非年化夏普比率: {self.ratio:.6f}")
        print(f"调试信息 - 年化夏普比率: {self.ann_ratio:.6f}")
    
    def get_analysis(self):
        """返回分析结果"""
        return {
            'sharperatio': self.ann_ratio,
            'non_annualized_sharperatio': self.ratio,
            'returns': self.returns,
            'date_returns': self.date_returns,
        }