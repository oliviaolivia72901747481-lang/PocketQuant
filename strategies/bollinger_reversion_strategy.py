"""
MiniQuant-Lite 布林带均值回归策略 (Bollinger Reversion)

核心理念：
- 利用布林带识别超买超卖区域
- 价格触及下轨时买入（超卖反弹）
- 价格回归中轨或触及上轨时卖出
- 适合震荡市，小资金快进快出

买入条件（全部满足）:
1. 收盘价 < 布林带下轨（超卖区）
2. RSI < 35（确认超卖）
3. 成交量 > 5日均量（有资金介入）

卖出条件（任一满足）:
1. 收盘价 >= 布林带中轨（均值回归完成）
2. 收盘价 >= 布林带上轨（超买区止盈）
3. 硬止损：亏损达到 -6%
4. 持仓超过 10 个交易日（时间止损）

Requirements: 策略替换
"""

import backtrader as bt
from dataclasses import dataclass
from typing import Optional
from enum import Enum

from strategies.base_strategy import BaseStrategy


class BollingerExitReason(Enum):
    """退出原因"""
    MEAN_REVERSION = "均值回归(中轨)"
    UPPER_BAND = "触及上轨"
    HARD_STOP_LOSS = "硬止损(-6%)"
    TIME_STOP = "时间止损(10日)"
    MANUAL = "手动卖出"


@dataclass
class BollingerPositionTracker:
    """持仓跟踪器"""
    entry_price: float           # 买入价格
    entry_bar: int               # 买入时的 bar 索引
    highest_price: float         # 持仓期间最高价
    current_profit_pct: float    # 当前盈亏百分比


class BollingerReversionStrategy(BaseStrategy):
    """
    布林带均值回归策略
    
    核心理念：
    - 利用布林带识别超买超卖区域
    - 价格触及下轨时买入（超卖反弹）
    - 价格回归中轨或触及上轨时卖出
    - 适合震荡市，小资金快进快出
    
    买入条件（全部满足）:
    1. 收盘价 < 布林带下轨（超卖区）
    2. RSI < 35（确认超卖）
    3. 成交量 > 5日均量（有资金介入）
    
    卖出条件（任一满足）:
    1. 收盘价 >= 布林带中轨（均值回归完成）
    2. 收盘价 >= 布林带上轨（超买区止盈）
    3. 硬止损：亏损达到 -6%
    4. 持仓超过 10 个交易日（时间止损）
    """
    
    params = (
        ('bb_period', 20),           # 布林带周期
        ('bb_devfactor', 2.0),       # 布林带标准差倍数
        ('rsi_period', 14),          # RSI 周期
        ('rsi_buy_threshold', 35),   # RSI 买入阈值（超卖）
        ('volume_period', 5),        # 成交量均线周期
        ('hard_stop_loss', -0.06),   # 硬止损比例（-6%）
        ('max_hold_days', 10),       # 最大持仓天数
    )
    
    def __init__(self):
        """初始化指标"""
        super().__init__()
        
        # 布林带指标
        self.boll = bt.indicators.BollingerBands(
            self.data.close,
            period=self.params.bb_period,
            devfactor=self.params.bb_devfactor
        )
        
        # RSI 指标
        self.rsi = bt.indicators.RSI(
            self.data.close, period=self.params.rsi_period
        )
        
        # 成交量均线
        self.volume_ma = bt.indicators.SimpleMovingAverage(
            self.data.volume, period=self.params.volume_period
        )
        
        # 持仓跟踪
        self.position_tracker: Optional[BollingerPositionTracker] = None
        
        # 退出原因记录
        self.exit_reasons = []
        
        # 当前 bar 计数
        self.bar_count = 0
    
    def next(self) -> None:
        """每个交易日执行的逻辑"""
        self.bar_count += 1
        
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
        1. 收盘价 < 布林带下轨（超卖区）
        2. RSI < 35（确认超卖）
        3. 成交量 > 5日均量（有资金介入）
        
        Returns:
            True 表示满足买入条件
        """
        # 条件1: 价格低于布林带下轨
        if self.data.close[0] >= self.boll.lines.bot[0]:
            return False
        
        # 条件2: RSI 确认超卖
        if self.rsi[0] >= self.params.rsi_buy_threshold:
            return False
        
        # 条件3: 成交量放大（有资金介入）
        if self.data.volume[0] <= self.volume_ma[0]:
            return False
        
        self.log(
            f'买入信号: 价格{self.data.close[0]:.2f} < 下轨({self.boll.lines.bot[0]:.2f}), '
            f'RSI={self.rsi[0]:.1f}, 成交量放大'
        )
        return True
    
    def _check_exit_conditions(self) -> Optional[BollingerExitReason]:
        """
        检查退出条件
        
        优先级：
        1. 硬止损（-6%）- 最高优先级
        2. 时间止损（10日）
        3. 触及上轨（超买止盈）
        4. 回归中轨（均值回归完成）
        
        Returns:
            退出原因，None 表示不需要退出
        """
        if not self.position_tracker:
            return None
        
        current_price = self.data.close[0]
        entry_price = self.position_tracker.entry_price
        profit_pct = (current_price - entry_price) / entry_price
        
        # 1. 硬止损检查
        if profit_pct <= self.params.hard_stop_loss:
            return BollingerExitReason.HARD_STOP_LOSS
        
        # 2. 时间止损检查
        hold_days = self.bar_count - self.position_tracker.entry_bar
        if hold_days >= self.params.max_hold_days:
            return BollingerExitReason.TIME_STOP
        
        # 3. 触及上轨（超买止盈）
        if current_price >= self.boll.lines.top[0]:
            return BollingerExitReason.UPPER_BAND
        
        # 4. 回归中轨（均值回归完成）
        if current_price >= self.boll.lines.mid[0]:
            return BollingerExitReason.MEAN_REVERSION
        
        return None
    
    def _init_position_tracker(self) -> None:
        """初始化持仓跟踪器"""
        self.position_tracker = BollingerPositionTracker(
            entry_price=self.data.close[0],
            entry_bar=self.bar_count,
            highest_price=self.data.close[0],
            current_profit_pct=0.0
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
    
    def _record_exit(self, reason: BollingerExitReason) -> None:
        """记录退出原因"""
        if self.position_tracker:
            self.log(
                f'退出原因: {reason.value}, '
                f'买入价: {self.position_tracker.entry_price:.2f}, '
                f'卖出价: {self.data.close[0]:.2f}, '
                f'盈亏: {self.position_tracker.current_profit_pct:.1%}'
            )
            
            self.exit_reasons.append({
                'datetime': self.datas[0].datetime.date(0),
                'reason': reason.value,
                'entry_price': self.position_tracker.entry_price,
                'exit_price': self.data.close[0],
                'profit_pct': self.position_tracker.current_profit_pct,
                'highest_price': self.position_tracker.highest_price,
            })
        
        self.position_tracker = None
