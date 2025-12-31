"""
Technical Indicators Module

技术指标计算模块，提供MA、RSI、量比、斜率等指标计算函数。
Requirements: 8.1
"""

import pandas as pd
import numpy as np
from typing import Optional, Union

from .config import V114G_STRATEGY_PARAMS


class TechIndicators:
    """
    技术指标计算器
    
    提供v11.4g策略所需的各类技术指标计算方法。
    """
    
    @staticmethod
    def calculate_ma(prices: pd.Series, period: int) -> pd.Series:
        """
        计算移动平均线
        
        Args:
            prices: 价格序列
            period: 计算周期
            
        Returns:
            pd.Series: 移动平均线序列
        """
        if len(prices) < period:
            return pd.Series([np.nan] * len(prices), index=prices.index)
        return prices.rolling(window=period, min_periods=period).mean()
    
    @staticmethod
    def calculate_ma_value(prices: pd.Series, period: int) -> float:
        """
        计算最新的移动平均值
        
        Args:
            prices: 价格序列
            period: 计算周期
            
        Returns:
            float: 最新MA值，数据不足时返回NaN
        """
        if len(prices) < period:
            return np.nan
        return prices.iloc[-period:].mean()
    
    @staticmethod
    def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        """
        计算RSI (Relative Strength Index)
        
        使用Wilder平滑方法计算RSI。
        
        Args:
            prices: 价格序列
            period: RSI周期，默认14
            
        Returns:
            pd.Series: RSI序列
        """
        if len(prices) < period + 1:
            return pd.Series([np.nan] * len(prices), index=prices.index)
        
        # 计算价格变化
        delta = prices.diff()
        
        # 分离涨跌
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)
        
        # 使用简单移动平均计算初始平均涨跌
        avg_gain = gain.rolling(window=period, min_periods=period).mean()
        avg_loss = loss.rolling(window=period, min_periods=period).mean()
        
        # 计算RS和RSI
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        # 处理除零情况
        rsi = rsi.replace([np.inf, -np.inf], np.nan)
        
        return rsi
    
    @staticmethod
    def calculate_rsi_value(prices: pd.Series, period: int = 14) -> float:
        """
        计算最新的RSI值
        
        Args:
            prices: 价格序列
            period: RSI周期，默认14
            
        Returns:
            float: 最新RSI值，数据不足时返回50.0（中性值）
        """
        if len(prices) < period + 1:
            return 50.0
        
        rsi_series = TechIndicators.calculate_rsi(prices, period)
        latest_rsi = rsi_series.iloc[-1]
        
        if pd.isna(latest_rsi):
            return 50.0
        
        return float(latest_rsi)
    
    @staticmethod
    def calculate_volume_ratio(volumes: pd.Series, period: int = 5) -> float:
        """
        计算量比
        
        量比 = 当日成交量 / 过去N日平均成交量
        
        Args:
            volumes: 成交量序列（最后一个为当日成交量）
            period: 平均成交量计算周期，默认5日
            
        Returns:
            float: 量比值，数据不足时返回1.0（中性值）
        """
        if len(volumes) < period + 1:
            return 1.0
        
        # 当日成交量
        current_volume = volumes.iloc[-1]
        
        # 过去N日平均成交量（不包含当日）
        avg_volume = volumes.iloc[-(period + 1):-1].mean()
        
        if avg_volume <= 0 or pd.isna(avg_volume):
            return 1.0
        
        return float(current_volume / avg_volume)
    
    @staticmethod
    def calculate_ma_slope(ma_series: pd.Series, days: int = 5) -> float:
        """
        计算MA斜率（百分比变化率）
        
        斜率 = (当前MA - N日前MA) / N日前MA * 100
        
        Args:
            ma_series: MA序列
            days: 斜率计算天数，默认5日
            
        Returns:
            float: MA斜率（百分比），数据不足时返回0.0
        """
        if len(ma_series) < days:
            return 0.0
        
        current_ma = ma_series.iloc[-1]
        past_ma = ma_series.iloc[-days]
        
        if pd.isna(current_ma) or pd.isna(past_ma) or past_ma <= 0:
            return 0.0
        
        return float((current_ma - past_ma) / past_ma * 100)
    
    @staticmethod
    def calculate_ma_slope_from_prices(prices: pd.Series, ma_period: int = 20, slope_days: int = 5) -> float:
        """
        从价格序列直接计算MA斜率
        
        Args:
            prices: 价格序列
            ma_period: MA周期，默认20
            slope_days: 斜率计算天数，默认5
            
        Returns:
            float: MA斜率（百分比）
        """
        if len(prices) < ma_period + slope_days:
            return 0.0
        
        ma_series = TechIndicators.calculate_ma(prices, ma_period)
        return TechIndicators.calculate_ma_slope(ma_series, slope_days)
    
    @staticmethod
    def calculate_all_indicators(
        prices: pd.Series,
        volumes: pd.Series,
        params: Optional[object] = None
    ) -> dict:
        """
        计算所有v11.4g策略所需的技术指标
        
        Args:
            prices: 价格序列
            volumes: 成交量序列
            params: 策略参数，默认使用V114G_STRATEGY_PARAMS
            
        Returns:
            dict: 包含所有指标的字典
        """
        if params is None:
            params = V114G_STRATEGY_PARAMS
        
        # 计算各周期MA
        ma5 = TechIndicators.calculate_ma_value(prices, params.MA5_PERIOD)
        ma10 = TechIndicators.calculate_ma_value(prices, params.MA10_PERIOD)
        ma20 = TechIndicators.calculate_ma_value(prices, params.MA20_PERIOD)
        ma60 = TechIndicators.calculate_ma_value(prices, params.MA60_PERIOD)
        
        # 计算RSI
        rsi = TechIndicators.calculate_rsi_value(prices, params.RSI_PERIOD)
        
        # 计算量比
        volume_ratio = TechIndicators.calculate_volume_ratio(volumes, params.VOLUME_RATIO_PERIOD)
        
        # 计算MA20斜率
        ma20_slope = TechIndicators.calculate_ma_slope_from_prices(
            prices, params.MA20_PERIOD, params.MA_SLOPE_PERIOD
        )
        
        return {
            'ma5': ma5,
            'ma10': ma10,
            'ma20': ma20,
            'ma60': ma60,
            'rsi': rsi,
            'volume_ratio': volume_ratio,
            'ma20_slope': ma20_slope,
            'current_price': prices.iloc[-1] if len(prices) > 0 else np.nan,
        }
