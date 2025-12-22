"""
MiniQuant-Lite 卖出信号检查模块

针对持仓股票检查卖出条件：
- 止损信号（亏损 >= 6%）
- RSRS 卖出信号（标准分 < -0.7）
- RSI 卖出信号（RSI > 70）

Requirements: 3.1, 3.2, 3.3, 3.4, 3.5
"""

import logging
from dataclasses import dataclass
from typing import List, Optional
from datetime import date
import numpy as np
import pandas as pd

from core.position_tracker import Holding, PositionTracker
from core.data_feed import DataFeed

logger = logging.getLogger(__name__)


@dataclass
class SellSignal:
    """
    卖出信号
    
    Attributes:
        code: 股票代码
        name: 股票名称
        holding: 持仓信息
        current_price: 当前价格
        pnl_pct: 盈亏百分比
        exit_reason: 卖出原因
        urgency: 紧急程度（high/medium/low）
        indicator_value: 指标值（RSRS分数或RSI值）
    """
    code: str
    name: str
    holding: Holding
    current_price: float
    pnl_pct: float
    exit_reason: str
    urgency: str  # high, medium, low
    indicator_value: float


class SellSignalChecker:
    """
    卖出信号检查器
    
    针对持仓股票检查卖出条件
    
    优化说明：
    - 止损从固定 -6% 改为 ATR 动态止损（2倍ATR）
    - 保留硬止损 -8% 作为最后防线
    - ATR 止损更适应不同波动率的股票
    
    Requirements: 3.1, 3.2, 3.3, 3.4
    """
    
    # 阈值配置
    ATR_MULTIPLIER = 2.0             # ATR 止损倍数
    ATR_PERIOD = 14                  # ATR 计算周期
    HARD_STOP_LOSS = -0.08           # 硬止损线 -8%（最后防线）
    RSRS_SELL_THRESHOLD = -0.7       # RSRS 卖出阈值
    RSI_SELL_THRESHOLD = 70          # RSI 卖出阈值
    
    # RSRS 参数
    RSRS_N_PERIOD = 18               # 斜率计算窗口
    RSRS_M_PERIOD = 600              # 标准化窗口
    RSRS_MIN_HISTORY = 50            # 最小历史数据
    
    def __init__(self, data_feed: DataFeed):
        """
        初始化卖出信号检查器
        
        Args:
            data_feed: 数据源
        """
        self.data_feed = data_feed
    
    def check_all_positions(self, positions: List[Holding]) -> List[SellSignal]:
        """
        检查所有持仓的卖出信号
        
        Args:
            positions: 持仓列表
        
        Returns:
            卖出信号列表
        """
        signals = []
        
        for holding in positions:
            signal = self.check_single_position(holding)
            if signal:
                signals.append(signal)
        
        # 按紧急程度排序：high > medium > low
        urgency_order = {'high': 0, 'medium': 1, 'low': 2}
        signals.sort(key=lambda s: urgency_order.get(s.urgency, 3))
        
        return signals
    
    def check_single_position(self, holding: Holding) -> Optional[SellSignal]:
        """
        检查单个持仓的卖出信号
        
        优先级：
        1. 硬止损信号（-8%，最后防线）
        2. ATR 动态止损信号
        3. 策略卖出信号
        
        Args:
            holding: 持仓记录
        
        Returns:
            SellSignal 或 None
        """
        # 加载股票数据
        df = self.data_feed.load_processed_data(holding.code)
        if df is None or df.empty:
            logger.warning(f"无法加载股票数据: {holding.code}")
            return None
        
        # 获取当前价格
        current_price = float(df['close'].iloc[-1])
        
        # 计算盈亏
        pnl_pct = (current_price - holding.buy_price) / holding.buy_price
        
        # 1. 检查硬止损（-8%，最后防线）
        hard_stop_signal = self._check_hard_stop_loss(holding, current_price, pnl_pct)
        if hard_stop_signal:
            return hard_stop_signal
        
        # 2. 检查 ATR 动态止损
        atr_stop_signal = self._check_atr_stop_loss(df, holding, current_price, pnl_pct)
        if atr_stop_signal:
            return atr_stop_signal
        
        # 3. 根据策略检查卖出信号
        if holding.strategy == "RSRS":
            return self._check_rsrs_sell(df, holding, current_price, pnl_pct)
        elif holding.strategy == "RSI":
            return self._check_rsi_sell(df, holding, current_price, pnl_pct)
        
        return None
    
    def _check_hard_stop_loss(
        self, 
        holding: Holding, 
        current_price: float,
        pnl_pct: float
    ) -> Optional[SellSignal]:
        """
        检查硬止损条件（-8%，最后防线）
        
        Args:
            holding: 持仓记录
            current_price: 当前价格
            pnl_pct: 盈亏百分比
        
        Returns:
            SellSignal 或 None
        """
        if pnl_pct <= self.HARD_STOP_LOSS:
            return SellSignal(
                code=holding.code,
                name=holding.name,
                holding=holding,
                current_price=current_price,
                pnl_pct=pnl_pct,
                exit_reason=f"🚨 触发硬止损（亏损 {pnl_pct:.1%} <= {self.HARD_STOP_LOSS:.0%}）",
                urgency="high",
                indicator_value=pnl_pct
            )
        return None
    
    def _check_atr_stop_loss(
        self, 
        df: pd.DataFrame,
        holding: Holding, 
        current_price: float,
        pnl_pct: float
    ) -> Optional[SellSignal]:
        """
        检查 ATR 动态止损条件
        
        止损价 = 买入价 - ATR × 倍数（默认2倍）
        
        优点：
        - 高波动股票止损空间大，低波动股票止损空间小
        - 比固定止损更灵活，更适应不同股票特性
        
        Args:
            df: 股票数据
            holding: 持仓记录
            current_price: 当前价格
            pnl_pct: 盈亏百分比
        
        Returns:
            SellSignal 或 None
        """
        if len(df) < self.ATR_PERIOD + 1:
            return None
        
        # 计算 ATR
        atr = self._calculate_atr(df)
        if atr is None or atr <= 0:
            return None
        
        # 计算 ATR 止损价
        atr_stop_price = holding.buy_price - (atr * self.ATR_MULTIPLIER)
        atr_stop_pct = (atr_stop_price / holding.buy_price - 1) * 100
        
        if current_price <= atr_stop_price:
            return SellSignal(
                code=holding.code,
                name=holding.name,
                holding=holding,
                current_price=current_price,
                pnl_pct=pnl_pct,
                exit_reason=f"⚠️ ATR动态止损（价格 {current_price:.2f} <= 止损价 {atr_stop_price:.2f}, {atr_stop_pct:.1f}%）",
                urgency="high",
                indicator_value=atr
            )
        return None
    
    def _calculate_atr(self, df: pd.DataFrame) -> Optional[float]:
        """
        计算 ATR (Average True Range)
        
        TR = max(High - Low, |High - PrevClose|, |Low - PrevClose|)
        ATR = TR 的 N 日移动平均
        
        Args:
            df: 股票数据
        
        Returns:
            ATR 值或 None
        """
        try:
            high = df['high']
            low = df['low']
            close = df['close']
            
            # 计算 True Range
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            
            # 计算 ATR
            atr = tr.rolling(window=self.ATR_PERIOD).mean()
            
            return float(atr.iloc[-1])
            
        except Exception as e:
            logger.error(f"计算 ATR 失败: {e}")
            return None
    
    def _check_rsrs_sell(
        self, 
        df: pd.DataFrame, 
        holding: Holding,
        current_price: float,
        pnl_pct: float
    ) -> Optional[SellSignal]:
        """
        检查 RSRS 卖出条件
        
        当 RSRS 标准分 < -0.7 时生成卖出信号
        
        Args:
            df: 股票数据
            holding: 持仓记录
            current_price: 当前价格
            pnl_pct: 盈亏百分比
        
        Returns:
            SellSignal 或 None
        """
        if len(df) < self.RSRS_MIN_HISTORY:
            return None
        
        # 计算 RSRS 标准分
        rsrs_score = self._calculate_rsrs_score(df)
        
        if rsrs_score is None:
            return None
        
        if rsrs_score < self.RSRS_SELL_THRESHOLD:
            return SellSignal(
                code=holding.code,
                name=holding.name,
                holding=holding,
                current_price=current_price,
                pnl_pct=pnl_pct,
                exit_reason=f"RSRS 卖出信号（标准分 {rsrs_score:.2f} < {self.RSRS_SELL_THRESHOLD}）",
                urgency="medium",
                indicator_value=rsrs_score
            )
        
        return None
    
    def _check_rsi_sell(
        self, 
        df: pd.DataFrame, 
        holding: Holding,
        current_price: float,
        pnl_pct: float
    ) -> Optional[SellSignal]:
        """
        检查 RSI 卖出条件
        
        当 RSI > 70 时生成卖出信号
        
        Args:
            df: 股票数据
            holding: 持仓记录
            current_price: 当前价格
            pnl_pct: 盈亏百分比
        
        Returns:
            SellSignal 或 None
        """
        if len(df) < 20:
            return None
        
        # 计算 RSI
        rsi = self._calculate_rsi(df['close'])
        
        if rsi is None:
            return None
        
        if rsi > self.RSI_SELL_THRESHOLD:
            return SellSignal(
                code=holding.code,
                name=holding.name,
                holding=holding,
                current_price=current_price,
                pnl_pct=pnl_pct,
                exit_reason=f"RSI 超买止盈（RSI {rsi:.1f} > {self.RSI_SELL_THRESHOLD}）",
                urgency="medium",
                indicator_value=rsi
            )
        
        return None
    
    def _calculate_rsrs_score(self, df: pd.DataFrame) -> Optional[float]:
        """
        计算 RSRS 标准分
        
        复用 signal_generator 中的 RSRS 计算逻辑
        """
        try:
            high = df['high'].values
            low = df['low'].values
            
            # 计算所有历史的 beta 值
            betas = []
            for i in range(self.RSRS_N_PERIOD, len(df) + 1):
                h = high[i-self.RSRS_N_PERIOD:i]
                l = low[i-self.RSRS_N_PERIOD:i]
                
                x_mean = np.mean(l)
                y_mean = np.mean(h)
                
                numerator = np.sum((l - x_mean) * (h - y_mean))
                denominator = np.sum((l - x_mean) ** 2)
                
                if denominator != 0:
                    beta = numerator / denominator
                else:
                    beta = 1.0
                
                betas.append(beta)
            
            if len(betas) < self.RSRS_MIN_HISTORY:
                return None
            
            # 当前 beta
            current_beta = betas[-1]
            
            # 标准化（Z-Score）
            history_len = min(len(betas), self.RSRS_M_PERIOD)
            recent_betas = betas[-history_len:]
            mean_beta = np.mean(recent_betas)
            std_beta = np.std(recent_betas)
            
            if std_beta > 0:
                return (current_beta - mean_beta) / std_beta
            
            return 0
            
        except Exception as e:
            logger.error(f"计算 RSRS 失败: {e}")
            return None
    
    def _calculate_rsi(self, close: pd.Series, period: int = 14) -> Optional[float]:
        """计算 RSI"""
        try:
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            
            loss = loss.replace(0, 0.000001)
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            return float(rsi.iloc[-1])
            
        except Exception as e:
            logger.error(f"计算 RSI 失败: {e}")
            return None
