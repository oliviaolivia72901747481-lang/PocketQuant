"""
MiniQuant-Lite 布林带均值回归策略 (Bollinger Reversion) - 优化版 v2.0

核心理念：
- 利用布林带识别超买超卖区域
- 价格触及下轨时买入（超卖反弹）
- 价格回归中轨或触及上轨时卖出
- 适合震荡市，小资金快进快出

优化内容（v2.0，借鉴科技股策略成功经验）：
- 添加移动止盈机制：盈利达到 +8% 后，回撤超过 3% 则卖出
- 优化止损参数：硬止损从 -8% 调整为 -5%
- 添加止盈参数：+18%
- 优化最大持仓天数：从 10 天调整为 12 天
- 放宽 RSI 买入阈值：从 35 调整为 45
- 成交量过滤改为可选（默认关闭以增加交易机会）
- 添加趋势反转卖出条件：MA5 < MA20 且亏损时卖出

买入条件（全部满足）:
1. 收盘价 < 布林带下轨（超卖区）
2. RSI < 45（确认超卖，放宽阈值）
3. 成交量 > 5日均量（有资金介入，可选）
4. MA5 > MA20（趋势过滤，可选）

卖出条件（任一满足）:
1. 收盘价 >= 布林带中轨（均值回归完成）
2. 收盘价 >= 布林带上轨（超买区止盈）
3. 硬止损：亏损达到 -5%
4. 止盈：盈利达到 +18%
5. 移动止盈：盈利 >8% 后回撤 >3%
6. 持仓超过 12 个交易日（时间止损）
7. 趋势反转：MA5 < MA20 且亏损
8. ATR 动态止损

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
    ATR_STOP_LOSS = "ATR动态止损"
    HARD_STOP_LOSS = "硬止损"
    TRAILING_STOP = "移动止盈"
    TAKE_PROFIT = "止盈"
    TIME_STOP = "持仓超时"
    TREND_BREAK = "趋势反转"
    MANUAL = "手动卖出"


@dataclass
class BollingerPositionTracker:
    """持仓跟踪器"""
    entry_price: float           # 买入价格
    entry_bar: int               # 买入时的 bar 索引
    highest_price: float         # 持仓期间最高价
    current_profit_pct: float    # 当前盈亏百分比
    atr_stop_price: float        # ATR 动态止损价（买入价 - 2倍ATR）
    max_profit_pct: float = 0.0  # 历史最高盈利百分比（用于移动止盈）


class BollingerReversionStrategy(BaseStrategy):
    """
    布林带均值回归策略（优化版 v2.0）
    
    核心理念：
    - 利用布林带识别超买超卖区域
    - 价格触及下轨时买入（超卖反弹）
    - 价格回归中轨或触及上轨时卖出
    - 适合震荡市，小资金快进快出
    
    优化内容（借鉴科技股策略成功经验）：
    - 添加移动止盈机制：盈利达到触发点后，回撤超过阈值则卖出
    - 优化止损止盈参数：止损 -5%，止盈 +18%
    - 优化最大持仓天数：12天
    - 添加趋势过滤：MA5 < MA20 时不买入
    - 放宽 RSI 买入阈值：40（原30太严格）
    
    买入条件（全部满足）:
    1. 收盘价 < 布林带下轨（超卖区）
    2. RSI < 40（确认超卖，放宽阈值）
    3. 成交量 > 5日均量（有资金介入）
    4. MA5 > MA20（趋势过滤，可选）
    
    卖出条件（任一满足）:
    1. 收盘价 >= 布林带中轨（均值回归完成）
    2. 收盘价 >= 布林带上轨（超买区止盈）
    3. 硬止损：亏损达到 -5%
    4. 止盈：盈利达到 +18%
    5. 移动止盈：盈利 >8% 后回撤 >3%
    6. 持仓超过 12 个交易日（时间止损）
    7. 趋势反转：MA5 < MA20 且亏损
    """
    
    params = (
        ('bb_period', 20),           # 布林带周期
        ('bb_devfactor', 2.0),       # 布林带标准差倍数
        ('rsi_period', 14),          # RSI 周期
        ('rsi_buy_threshold', 45),   # RSI 买入阈值（放宽，原40）
        ('volume_period', 5),        # 成交量均线周期
        ('atr_period', 14),          # ATR 周期
        ('atr_multiplier', 2.0),     # ATR 止损倍数
        ('hard_stop_loss', -0.05),   # 硬止损比例（-5%）
        ('take_profit', 0.18),       # 止盈比例（+18%）
        ('trailing_stop_trigger', 0.08),  # 移动止盈触发点（+8%）
        ('trailing_stop_pct', 0.03),      # 移动止盈回撤比例（3%）
        ('max_hold_days', 12),       # 最大持仓天数
        ('trend_filter', False),     # 关闭趋势过滤（增加交易机会）
        ('ma_short', 5),             # 短期均线周期
        ('ma_long', 20),             # 长期均线周期
        ('volume_filter', False),    # 关闭成交量过滤（增加交易机会）
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
        
        # ATR 指标（用于动态止损）
        self.atr = bt.indicators.ATR(
            self.data, period=self.params.atr_period
        )
        
        # 成交量均线
        self.volume_ma = bt.indicators.SimpleMovingAverage(
            self.data.volume, period=self.params.volume_period
        )
        
        # 均线指标（用于趋势过滤）
        self.ma_short = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.ma_short
        )
        self.ma_long = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.ma_long
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
        2. RSI < 45（确认超卖，放宽阈值）
        3. 成交量 > 5日均量（有资金介入，可选）
        4. MA5 > MA20（趋势过滤，可选）
        
        Returns:
            True 表示满足买入条件
        """
        # 条件1: 价格低于布林带下轨
        if self.data.close[0] >= self.boll.lines.bot[0]:
            return False
        
        # 条件2: RSI 确认超卖
        if self.rsi[0] >= self.params.rsi_buy_threshold:
            return False
        
        # 条件3: 成交量放大（有资金介入，可选）
        if self.params.volume_filter:
            if self.data.volume[0] <= self.volume_ma[0]:
                return False
        
        # 条件4: 趋势过滤（可选）
        if self.params.trend_filter:
            if self.ma_short[0] <= self.ma_long[0]:
                return False
        
        self.log(
            f'买入信号: 价格{self.data.close[0]:.2f} < 下轨({self.boll.lines.bot[0]:.2f}), '
            f'RSI={self.rsi[0]:.1f}'
        )
        return True
    
    def _check_exit_conditions(self) -> Optional[BollingerExitReason]:
        """
        检查退出条件
        
        优先级：
        1. 硬止损（-5%）- 最后防线，最高优先级
        2. ATR 动态止损（2倍ATR）- 适应不同波动率
        3. 止盈（+18%）
        4. 移动止盈（盈利 >8% 后回撤 >3%）
        5. 持仓超时（12天）
        6. 趋势反转（MA5 < MA20 且亏损）
        7. 触及上轨（超买止盈）
        8. 回归中轨（均值回归完成）
        
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
        
        # 2. ATR 动态止损检查
        if current_price <= self.position_tracker.atr_stop_price:
            return BollingerExitReason.ATR_STOP_LOSS
        
        # 3. 止盈检查
        if profit_pct >= self.params.take_profit:
            return BollingerExitReason.TAKE_PROFIT
        
        # 4. 移动止盈检查
        max_profit = self.position_tracker.max_profit_pct
        if max_profit >= self.params.trailing_stop_trigger:
            # 从最高点回撤超过阈值
            if (max_profit - profit_pct) >= self.params.trailing_stop_pct:
                return BollingerExitReason.TRAILING_STOP
        
        # 5. 持仓超时检查
        hold_days = self.bar_count - self.position_tracker.entry_bar
        if hold_days >= self.params.max_hold_days:
            return BollingerExitReason.TIME_STOP
        
        # 6. 趋势反转检查（MA5 < MA20 且亏损）
        if profit_pct < 0 and self.ma_short[0] < self.ma_long[0]:
            return BollingerExitReason.TREND_BREAK
        
        # 7. 触及上轨（超买止盈）
        if current_price >= self.boll.lines.top[0]:
            return BollingerExitReason.UPPER_BAND
        
        # 8. 回归中轨（均值回归完成）
        if current_price >= self.boll.lines.mid[0]:
            return BollingerExitReason.MEAN_REVERSION
        
        return None
    
    def _init_position_tracker(self) -> None:
        """
        初始化持仓跟踪器
        
        计算 ATR 动态止损价：
        - 止损价 = 买入价 - ATR × 倍数
        - 默认使用 2 倍 ATR，适应不同波动率的股票
        """
        entry_price = self.data.close[0]
        current_atr = self.atr[0]
        
        # 计算 ATR 止损价（买入价 - 2倍ATR）
        atr_stop = entry_price - (current_atr * self.params.atr_multiplier)
        
        self.position_tracker = BollingerPositionTracker(
            entry_price=entry_price,
            entry_bar=self.bar_count,
            highest_price=entry_price,
            current_profit_pct=0.0,
            atr_stop_price=atr_stop,
            max_profit_pct=0.0
        )
        
        self.log(
            f'建仓: 买入价={entry_price:.2f}, ATR={current_atr:.2f}, '
            f'ATR止损价={atr_stop:.2f} ({(atr_stop/entry_price - 1)*100:.1f}%)'
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
        profit_pct = (current_price - entry_price) / entry_price
        self.position_tracker.current_profit_pct = profit_pct
        
        # 更新历史最高盈利（用于移动止盈）
        if profit_pct > self.position_tracker.max_profit_pct:
            self.position_tracker.max_profit_pct = profit_pct
    
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
