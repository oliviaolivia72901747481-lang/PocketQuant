"""
MiniQuant-Lite RSRS 策略 (Resistance Support Relative Strength)

核心理念：
- 阻力位和支撑位的变化关系，比价格本身更能反映市场情绪
- 最高价 = 多头进攻极限 = 阻力位
- 最低价 = 空头打压极限 = 支撑位
- 通过斜率的标准化分数判断市场情绪

计算步骤：
1. 取过去 N 天的 High/Low 数据，做线性回归，得到斜率 Beta
2. 将 Beta 标准化（Z-Score），与过去 M 天的历史比较
3. RSRS 标准分 > 0.7 买入，< -0.7 卖出

买入条件：
- RSRS 标准分 > 0.7（市场情绪处于历史最好的 25%）

卖出条件：
- RSRS 标准分 < -0.7（市场情绪处于历史最差的 25%）
- 或硬止损 -6%

Requirements: 策略替换
"""

import backtrader as bt
import numpy as np
from dataclasses import dataclass
from typing import Optional, List
from enum import Enum

from strategies.base_strategy import BaseStrategy


class RSRSExitReason(Enum):
    """退出原因"""
    RSRS_SELL_SIGNAL = "RSRS卖出信号"
    ATR_STOP_LOSS = "ATR动态止损"
    HARD_STOP_LOSS = "硬止损(-8%)"
    MANUAL = "手动卖出"


@dataclass
class RSRSPositionTracker:
    """持仓跟踪器"""
    entry_price: float           # 买入价格
    highest_price: float         # 持仓期间最高价
    current_profit_pct: float    # 当前盈亏百分比
    atr_stop_price: float        # ATR 动态止损价（买入价 - 2倍ATR）


class RSRSIndicator(bt.Indicator):
    """
    RSRS 指标
    
    计算阻力支撑相对强度的标准化分数
    
    注意：m_period=600 是理想值，但实际会使用可用的历史数据
    """
    lines = ('rsrs', 'beta',)
    
    params = (
        ('n_period', 18),      # 计算斜率的窗口期
        ('m_period', 600),     # 标准化的历史窗口期（理想值，实际使用可用数据）
        ('min_history', 50),   # 最小历史数据要求（用于标准化）
    )
    
    def __init__(self):
        # 只需要 n_period 天数据即可开始计算
        self.addminperiod(self.p.n_period)
        self.betas = []  # 存储历史 beta 值
    
    def next(self):
        try:
            # 使用 get() 方法安全获取数据，避免 index out of range
            highs = self.data.high.get(ago=0, size=self.p.n_period)
            lows = self.data.low.get(ago=0, size=self.p.n_period)
            
            # 检查数据是否足够
            if len(highs) < self.p.n_period or len(lows) < self.p.n_period:
                self.lines.rsrs[0] = 0
                self.lines.beta[0] = 1.0
                return
            
            # 线性回归计算斜率 Beta
            # Y = High, X = Low
            x = np.array(lows)
            y = np.array(highs)
            
            # 使用最小二乘法计算斜率
            x_mean = np.mean(x)
            y_mean = np.mean(y)
            
            numerator = np.sum((x - x_mean) * (y - y_mean))
            denominator = np.sum((x - x_mean) ** 2)
            
            if denominator != 0:
                beta = numerator / denominator
            else:
                beta = 1.0
            
            self.lines.beta[0] = beta
            self.betas.append(beta)
            
            # 标准化（Z-Score）
            # 使用可用的历史数据，最多 m_period 天
            if len(self.betas) >= self.p.min_history:
                # 取最近 m_period 个 beta（或全部可用的）
                history_len = min(len(self.betas), self.p.m_period)
                recent_betas = self.betas[-history_len:]
                mean_beta = np.mean(recent_betas)
                std_beta = np.std(recent_betas)
                
                if std_beta > 0:
                    z_score = (beta - mean_beta) / std_beta
                else:
                    z_score = 0
            else:
                # 历史数据不足最小要求时，不产生信号
                z_score = 0
            
            self.lines.rsrs[0] = z_score
            
        except Exception:
            # 任何错误都返回中性值
            self.lines.rsrs[0] = 0
            self.lines.beta[0] = 1.0


class RSRSStrategy(BaseStrategy):
    """
    RSRS 策略 (阻力支撑相对强度)
    
    核心理念：
    - 通过 High/Low 的线性回归斜率判断市场情绪
    - 斜率标准化后与历史比较，得到 RSRS 标准分
    - 标准分 > 0.7 买入，< -0.7 卖出
    
    买入条件：
    - RSRS 标准分 > buy_threshold（默认 0.7）
    - 表示市场情绪处于历史最好的 25% 阶段
    
    卖出条件：
    - RSRS 标准分 < sell_threshold（默认 -0.7）
    - 或硬止损 -6%
    """
    
    params = (
        ('n_period', 18),            # 计算斜率的窗口期
        ('m_period', 600),           # 标准化的历史窗口期（理想值）
        ('min_history', 50),         # 最小历史数据要求
        ('buy_threshold', 0.7),      # 买入阈值
        ('sell_threshold', -0.7),    # 卖出阈值
        ('atr_period', 14),          # ATR 周期
        ('atr_multiplier', 2.0),     # ATR 止损倍数
        ('hard_stop_loss', -0.08),   # 硬止损比例（-8%，最后防线）
    )
    
    def __init__(self):
        """初始化指标"""
        super().__init__()
        
        # RSRS 指标
        self.rsrs = RSRSIndicator(
            self.data,
            n_period=self.params.n_period,
            m_period=self.params.m_period,
            min_history=self.params.min_history
        )
        
        # ATR 指标（用于动态止损）
        self.atr = bt.indicators.ATR(
            self.data, period=self.params.atr_period
        )
        
        # 持仓跟踪
        self.position_tracker: Optional[RSRSPositionTracker] = None
        
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
        
        买入条件：RSRS 标准分 > buy_threshold
        
        Returns:
            True 表示满足买入条件
        """
        rsrs_score = self.rsrs.rsrs[0]
        
        if rsrs_score > self.params.buy_threshold:
            self.log(
                f'买入信号: RSRS标准分={rsrs_score:.2f} > {self.params.buy_threshold}'
            )
            return True
        
        return False
    
    def _check_exit_conditions(self) -> Optional[RSRSExitReason]:
        """
        检查退出条件
        
        优先级：
        1. 硬止损（-8%，最后防线）
        2. ATR 动态止损（2倍ATR）
        3. RSRS 卖出信号
        
        优化说明：
        - ATR 止损比固定止损更灵活，能适应不同波动率的股票
        - 保留硬止损 -8% 作为最后防线
        
        Returns:
            退出原因，None 表示不需要退出
        """
        if not self.position_tracker:
            return None
        
        current_price = self.data.close[0]
        entry_price = self.position_tracker.entry_price
        profit_pct = (current_price - entry_price) / entry_price
        
        # 1. 硬止损检查（-8%，最后防线）
        if profit_pct <= self.params.hard_stop_loss:
            return RSRSExitReason.HARD_STOP_LOSS
        
        # 2. ATR 动态止损检查
        if current_price <= self.position_tracker.atr_stop_price:
            return RSRSExitReason.ATR_STOP_LOSS
        
        # 3. RSRS 卖出信号
        rsrs_score = self.rsrs.rsrs[0]
        if rsrs_score < self.params.sell_threshold:
            return RSRSExitReason.RSRS_SELL_SIGNAL
        
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
        
        self.position_tracker = RSRSPositionTracker(
            entry_price=entry_price,
            highest_price=entry_price,
            current_profit_pct=0.0,
            atr_stop_price=atr_stop
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
        self.position_tracker.current_profit_pct = (current_price - entry_price) / entry_price
    
    def _record_exit(self, reason: RSRSExitReason) -> None:
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
