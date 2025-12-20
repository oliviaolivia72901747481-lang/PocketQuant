"""
MiniQuant-Lite 趋势滤网 MACD 策略

核心理念：
- 5.5 万本金亏不起，必须放弃"抄底"幻想，只做"右侧交易"
- 趋势确立后的上涨段才是小资金的安全区
- 趋势策略主要靠几笔大赚来覆盖小亏，让利润多奔跑

买入条件（全部满足）:
1. 股价 > MA60（趋势滤网，只做右侧交易）
2. MACD 金叉（DIF 上穿 DEA）
3. RSI < 80（避免追高，RSI > 90 绝对不追）

卖出条件（任一满足）:
1. 硬止损：亏损达到 -8%，无条件市价止损（给高波动股留活路）
2. 移动止盈：盈利超过 15% 后，从最高点回撤 5% 止盈（让利润多奔跑）
3. MACD 死叉（DIF 下穿 DEA）

Requirements: 5.2, 5.3, 5.4, 5.6, 5.7, 5.8, 5.9, 5.10
"""

import backtrader as bt
from dataclasses import dataclass
from typing import Optional
from enum import Enum

from strategies.base_strategy import BaseStrategy


class ExitReason(Enum):
    """退出原因"""
    MACD_DEATH_CROSS = "MACD死叉"
    HARD_STOP_LOSS = "硬止损(-8%)"
    TRAILING_STOP = "移动止盈"
    MANUAL = "手动卖出"


@dataclass
class PositionTracker:
    """
    持仓跟踪器
    
    跟踪每笔持仓的关键信息，用于止损止盈判断。
    """
    entry_price: float           # 买入价格
    highest_price: float         # 持仓期间最高价
    current_profit_pct: float    # 当前盈亏百分比
    trailing_activated: bool     # 移动止盈是否激活


class TrendFilteredMACDStrategy(BaseStrategy):
    """
    趋势滤网 MACD 策略（默认策略）
    
    核心理念：
    - 5.5 万本金亏不起，必须放弃"抄底"幻想，只做"右侧交易"
    - 趋势确立后的上涨段才是小资金的安全区
    - 趋势策略主要靠几笔大赚来覆盖小亏，让利润多奔跑
    
    买入条件（全部满足）:
    1. 股价 > MA60（趋势滤网，只做右侧交易）
    2. MACD 金叉（DIF 上穿 DEA）
    3. RSI < 80（避免追高，RSI > 90 绝对不追）
    
    卖出条件（任一满足）:
    1. 硬止损：亏损达到 -8%，无条件市价止损（给高波动股留活路）
    2. 移动止盈：盈利超过 15% 后，从最高点回撤 5% 止盈（让利润多奔跑）
    3. MACD 死叉（DIF 下穿 DEA）
    """
    
    params = (
        ('fast_period', 12),         # MACD 快线周期
        ('slow_period', 26),         # MACD 慢线周期
        ('signal_period', 9),        # MACD 信号线周期
        ('ma_period', 60),           # 趋势均线周期（MA60 生命线）
        ('rsi_period', 14),          # RSI 周期
        ('rsi_upper', 80),           # RSI 上限（从70上调至80，防止漏掉大牛股）
        ('rsi_extreme', 90),         # RSI 极端值（绝对不追）
        ('hard_stop_loss', -0.08),   # 硬止损比例（-8%，给高波动股留活路）
        ('trailing_start', 0.15),    # 移动止盈启动阈值（+15%，让利润多奔跑）
        ('trailing_stop', 0.05),     # 移动止盈回撤比例（5%）
    )
    
    def __init__(self):
        """初始化指标"""
        super().__init__()
        
        # MACD 指标
        self.macd = bt.indicators.MACD(
            self.data.close,
            period_me1=self.params.fast_period,
            period_me2=self.params.slow_period,
            period_signal=self.params.signal_period
        )
        
        # MA60 趋势均线（生命线）
        self.ma60 = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.ma_period
        )
        
        # RSI 指标
        self.rsi = bt.indicators.RSI(
            self.data.close, period=self.params.rsi_period
        )
        
        # MACD 金叉/死叉信号
        self.macd_crossover = bt.indicators.CrossOver(
            self.macd.macd, self.macd.signal
        )
        
        # 持仓跟踪
        self.position_tracker: Optional[PositionTracker] = None
        
        # 退出原因记录
        self.exit_reasons = []
    
    def next(self) -> None:
        """每个交易日执行的逻辑"""
        # 如果有未完成的订单，等待
        if self.order:
            return
        
        # 更新持仓跟踪
        if self.position:
            self._update_position_tracker()
            
            # 检查止损止盈条件
            exit_reason = self._check_exit_conditions()
            if exit_reason:
                self.log(f'触发{exit_reason.value}，卖出')
                self.order = self.close()
                self._record_exit(exit_reason)
                return
        
        # 检查买入条件
        if not self.position:
            if self._check_buy_conditions():
                self.order = self.buy()
                self._init_position_tracker()
    
    def _check_buy_conditions(self) -> bool:
        """
        检查买入条件
        
        必须同时满足：
        1. 股价 > MA60（趋势滤网）
        2. MACD 金叉
        3. RSI < 80（RSI > 90 绝对不追）
        
        Returns:
            True 表示满足买入条件
        """
        # 条件1: 趋势滤网 - 股价必须在 MA60 之上
        if self.data.close[0] <= self.ma60[0]:
            return False
        
        # 条件2: MACD 金叉
        if self.macd_crossover[0] <= 0:
            return False
        
        # 条件3: RSI 过滤 - 避免追高
        if self.rsi[0] >= self.params.rsi_extreme:
            self.log(f'RSI={self.rsi[0]:.1f} >= 90，超买区，放弃买入')
            return False
        if self.rsi[0] >= self.params.rsi_upper:
            self.log(f'RSI={self.rsi[0]:.1f} >= 80，谨慎区，放弃买入')
            return False
        
        self.log(
            f'买入信号: 价格{self.data.close[0]:.2f} > MA60({self.ma60[0]:.2f}), '
            f'MACD金叉, RSI={self.rsi[0]:.1f}'
        )
        return True
    
    def _check_exit_conditions(self) -> Optional[ExitReason]:
        """
        检查退出条件
        
        优先级：
        1. 硬止损（-8%）- 最高优先级，保本第一
        2. 移动止盈（盈利15%后回撤5%）
        3. MACD 死叉
        
        Returns:
            退出原因，None 表示不需要退出
        """
        if not self.position_tracker:
            return None
        
        current_price = self.data.close[0]
        entry_price = self.position_tracker.entry_price
        profit_pct = (current_price - entry_price) / entry_price
        
        # 1. 硬止损检查 - 小资金第一要务是保本
        if profit_pct <= self.params.hard_stop_loss:
            return ExitReason.HARD_STOP_LOSS
        
        # 2. 移动止盈检查
        if self.position_tracker.trailing_activated:
            highest = self.position_tracker.highest_price
            drawdown_from_high = (highest - current_price) / highest
            if drawdown_from_high >= self.params.trailing_stop:
                return ExitReason.TRAILING_STOP
        
        # 3. MACD 死叉检查
        if self.macd_crossover[0] < 0:
            return ExitReason.MACD_DEATH_CROSS
        
        return None
    
    def _init_position_tracker(self) -> None:
        """初始化持仓跟踪器"""
        self.position_tracker = PositionTracker(
            entry_price=self.data.close[0],
            highest_price=self.data.close[0],
            current_profit_pct=0.0,
            trailing_activated=False
        )
    
    def _update_position_tracker(self) -> None:
        """更新持仓跟踪器"""
        if not self.position_tracker:
            return
        
        current_price = self.data.close[0]
        entry_price = self.position_tracker.entry_price
        
        # 更新最高价
        if current_price > self.position_tracker.highest_price:
            self.position_tracker.highest_price = current_price
        
        # 更新当前盈亏
        self.position_tracker.current_profit_pct = (current_price - entry_price) / entry_price
        
        # 检查是否激活移动止盈
        if (not self.position_tracker.trailing_activated and 
            self.position_tracker.current_profit_pct >= self.params.trailing_start):
            self.position_tracker.trailing_activated = True
            self.log(f'移动止盈激活: 盈利 {self.position_tracker.current_profit_pct:.1%}')
    
    def _record_exit(self, reason: ExitReason) -> None:
        """
        记录退出原因
        
        Args:
            reason: 退出原因
        """
        if self.position_tracker:
            self.log(
                f'退出原因: {reason.value}, '
                f'买入价: {self.position_tracker.entry_price:.2f}, '
                f'卖出价: {self.data.close[0]:.2f}, '
                f'盈亏: {self.position_tracker.current_profit_pct:.1%}'
            )
            
            # 记录到退出原因列表
            self.exit_reasons.append({
                'datetime': self.datas[0].datetime.date(0),
                'reason': reason.value,
                'entry_price': self.position_tracker.entry_price,
                'exit_price': self.data.close[0],
                'profit_pct': self.position_tracker.current_profit_pct,
                'highest_price': self.position_tracker.highest_price,
            })
        
        self.position_tracker = None
