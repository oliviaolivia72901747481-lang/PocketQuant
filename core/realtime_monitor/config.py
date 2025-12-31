"""
Realtime Monitor Configuration

v11.4g策略参数常量和监控配置定义。
Requirements: 3.1, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6
"""

from dataclasses import dataclass, field
from datetime import time
from typing import List, Tuple


@dataclass(frozen=True)
class V114GStrategyParams:
    """v11.4g科技股策略参数"""
    
    # 止损止盈参数 (Requirements: 4.1, 4.2, 4.3)
    STOP_LOSS_PCT: float = -0.046        # 止损线 -4.6%
    TAKE_PROFIT_PCT: float = 0.22        # 止盈线 +22%
    TRAILING_TRIGGER_PCT: float = 0.09   # 移动止盈触发 +9%
    TRAILING_STOP_PCT: float = 0.028     # 移动止盈回撤 2.8%
    
    # RSI参数 (Requirements: 3.1, 4.4)
    RSI_MIN: int = 44                    # RSI下限（买入条件）
    RSI_MAX: int = 70                    # RSI上限（买入条件）
    RSI_OVERBOUGHT: int = 80             # RSI超买（卖出条件）
    RSI_PERIOD: int = 14                 # RSI计算周期
    
    # 量比参数 (Requirement: 3.1)
    VOLUME_RATIO_MIN: float = 1.1        # 最小量比（买入条件）
    VOLUME_RATIO_PERIOD: int = 5         # 量比计算周期
    
    # 均线参数 (Requirement: 3.1)
    MA5_PERIOD: int = 5                  # MA5周期
    MA10_PERIOD: int = 10                # MA10周期
    MA20_PERIOD: int = 20                # MA20周期
    MA60_PERIOD: int = 60                # MA60周期
    MA_SLOPE_PERIOD: int = 5             # MA斜率计算周期
    
    # 追高限制 (Requirement: 3.1)
    MAX_PRICE_ABOVE_MA5_PCT: float = 0.05  # 价格不超过MA5的5%
    
    # 持仓时间限制 (Requirement: 4.6)
    MAX_HOLDING_DAYS: int = 15           # 最大持仓天数
    
    # 买入信号强度阈值
    MIN_CONDITIONS_FOR_SIGNAL: int = 5   # 最少满足条件数
    TOTAL_BUY_CONDITIONS: int = 6        # 总买入条件数


@dataclass
class MonitorConfig:
    """监控配置"""
    
    # 监控列表限制
    max_watchlist_size: int = 20         # 最大监控股票数
    
    # 刷新间隔
    refresh_interval: int = 30           # 正常刷新间隔（秒）
    retry_interval: int = 60             # 重试间隔（秒）
    
    # 交易时间
    trading_hours: List[Tuple[time, time]] = field(default_factory=lambda: [
        (time(9, 30), time(11, 30)),      # 上午交易时段
        (time(13, 0), time(15, 0))        # 下午交易时段
    ])
    
    # 股票代码验证
    valid_code_prefixes: Tuple[str, ...] = ('0', '3', '6')  # A股代码前缀
    code_length: int = 6                 # 股票代码长度
    
    # 信号强度颜色阈值
    signal_strength_high: int = 80       # 强信号阈值（绿色）
    signal_strength_medium: int = 60     # 中等信号阈值（黄色）


# 全局配置实例
V114G_STRATEGY_PARAMS = V114GStrategyParams()
MONITOR_CONFIG = MonitorConfig()
