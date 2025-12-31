"""
Realtime Monitor Indicators Tests

测试技术指标计算模块，包括MA、RSI、量比、斜率等指标计算。
Requirements: 8.1
"""

import pytest
import pandas as pd
import numpy as np
from hypothesis import given, strategies as st, settings

from core.realtime_monitor.indicators import TechIndicators
from core.realtime_monitor.config import V114G_STRATEGY_PARAMS


class TestMACalculation:
    """移动平均线计算测试"""
    
    def test_ma_basic_calculation(self):
        """测试基本MA计算"""
        prices = pd.Series([10.0, 11.0, 12.0, 13.0, 14.0])
        ma5 = TechIndicators.calculate_ma(prices, 5)
        
        # MA5 = (10+11+12+13+14) / 5 = 12.0
        assert abs(ma5.iloc[-1] - 12.0) < 0.0001
    
    def test_ma_insufficient_data(self):
        """测试数据不足时的MA计算"""
        prices = pd.Series([10.0, 11.0, 12.0])
        ma5 = TechIndicators.calculate_ma(prices, 5)
        
        # 数据不足时应返回NaN
        assert all(pd.isna(ma5))
    
    def test_ma_value_basic(self):
        """测试MA值计算"""
        prices = pd.Series([10.0, 11.0, 12.0, 13.0, 14.0])
        ma5_value = TechIndicators.calculate_ma_value(prices, 5)
        
        assert abs(ma5_value - 12.0) < 0.0001
    
    def test_ma_value_insufficient_data(self):
        """测试数据不足时的MA值"""
        prices = pd.Series([10.0, 11.0])
        ma5_value = TechIndicators.calculate_ma_value(prices, 5)
        
        assert np.isnan(ma5_value)
    
    @given(
        values=st.lists(
            st.floats(min_value=1.0, max_value=100.0, allow_nan=False, allow_infinity=False),
            min_size=10, max_size=50
        )
    )
    @settings(max_examples=100)
    def test_ma_property_average(self, values: list):
        """测试MA计算属性：结果应等于窗口内数据的平均值"""
        prices = pd.Series(values)
        period = 5
        
        if len(prices) >= period:
            ma_value = TechIndicators.calculate_ma_value(prices, period)
            expected = sum(values[-period:]) / period
            assert abs(ma_value - expected) < 1e-6


class TestRSICalculation:
    """RSI计算测试"""
    
    def test_rsi_uptrend(self):
        """测试上涨趋势的RSI"""
        # 连续上涨的价格序列
        prices = pd.Series([10.0 + i * 0.5 for i in range(20)])
        rsi = TechIndicators.calculate_rsi_value(prices, 14)
        
        # 连续上涨时RSI应该较高
        assert rsi > 70
    
    def test_rsi_downtrend(self):
        """测试下跌趋势的RSI"""
        # 连续下跌的价格序列
        prices = pd.Series([20.0 - i * 0.5 for i in range(20)])
        rsi = TechIndicators.calculate_rsi_value(prices, 14)
        
        # 连续下跌时RSI应该较低
        assert rsi < 30
    
    def test_rsi_insufficient_data(self):
        """测试数据不足时的RSI"""
        prices = pd.Series([10.0, 11.0, 12.0])
        rsi = TechIndicators.calculate_rsi_value(prices, 14)
        
        # 数据不足时返回中性值50
        assert rsi == 50.0
    
    def test_rsi_range(self):
        """测试RSI值范围"""
        # 随机价格序列
        np.random.seed(42)
        prices = pd.Series(np.random.uniform(10, 20, 50))
        rsi = TechIndicators.calculate_rsi_value(prices, 14)
        
        # RSI应在0-100范围内
        assert 0 <= rsi <= 100
    
    @given(
        base_price=st.floats(min_value=10.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        changes=st.lists(
            st.floats(min_value=-0.05, max_value=0.05, allow_nan=False, allow_infinity=False),
            min_size=20, max_size=50
        )
    )
    @settings(max_examples=100)
    def test_rsi_range_property(self, base_price: float, changes: list):
        """测试RSI范围属性：RSI应始终在0-100之间"""
        # 生成价格序列
        prices = [base_price]
        for change in changes:
            new_price = prices[-1] * (1 + change)
            if new_price > 0:
                prices.append(new_price)
        
        if len(prices) >= 15:
            rsi = TechIndicators.calculate_rsi_value(pd.Series(prices), 14)
            assert 0 <= rsi <= 100


class TestVolumeRatioCalculation:
    """量比计算测试"""
    
    def test_volume_ratio_basic(self):
        """测试基本量比计算"""
        # 过去5日平均成交量100万，今日成交量150万
        volumes = pd.Series([100, 100, 100, 100, 100, 150]) * 10000
        volume_ratio = TechIndicators.calculate_volume_ratio(volumes, 5)
        
        # 量比 = 150 / 100 = 1.5
        assert abs(volume_ratio - 1.5) < 0.0001
    
    def test_volume_ratio_insufficient_data(self):
        """测试数据不足时的量比"""
        volumes = pd.Series([100, 150]) * 10000
        volume_ratio = TechIndicators.calculate_volume_ratio(volumes, 5)
        
        # 数据不足时返回中性值1.0
        assert volume_ratio == 1.0
    
    def test_volume_ratio_zero_average(self):
        """测试平均成交量为0的边界情况"""
        volumes = pd.Series([0, 0, 0, 0, 0, 100])
        volume_ratio = TechIndicators.calculate_volume_ratio(volumes, 5)
        
        # 平均成交量为0时返回中性值1.0
        assert volume_ratio == 1.0
    
    @given(
        past_volumes=st.lists(
            st.floats(min_value=1000.0, max_value=10000000.0, allow_nan=False, allow_infinity=False),
            min_size=5, max_size=5
        ),
        current_volume=st.floats(min_value=1000.0, max_value=10000000.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_volume_ratio_property(self, past_volumes: list, current_volume: float):
        """测试量比计算属性：量比 = 当日成交量 / 过去N日平均成交量"""
        volumes = pd.Series(past_volumes + [current_volume])
        volume_ratio = TechIndicators.calculate_volume_ratio(volumes, 5)
        
        expected = current_volume / (sum(past_volumes) / 5)
        assert abs(volume_ratio - expected) < 1e-6


class TestMASlopeCalculation:
    """MA斜率计算测试"""
    
    def test_ma_slope_positive(self):
        """测试正斜率计算"""
        # MA序列：从10上涨到11
        ma_series = pd.Series([10.0, 10.2, 10.4, 10.6, 10.8, 11.0])
        slope = TechIndicators.calculate_ma_slope(ma_series, 5)
        
        # 斜率 = (11 - 10.2) / 10.2 * 100 ≈ 7.84%
        expected = (11.0 - 10.2) / 10.2 * 100
        assert abs(slope - expected) < 0.01
    
    def test_ma_slope_negative(self):
        """测试负斜率计算"""
        # MA序列：从11下跌到10
        ma_series = pd.Series([11.0, 10.8, 10.6, 10.4, 10.2, 10.0])
        slope = TechIndicators.calculate_ma_slope(ma_series, 5)
        
        # 斜率应为负
        assert slope < 0
    
    def test_ma_slope_insufficient_data(self):
        """测试数据不足时的斜率"""
        ma_series = pd.Series([10.0, 11.0])
        slope = TechIndicators.calculate_ma_slope(ma_series, 5)
        
        # 数据不足时返回0
        assert slope == 0.0
    
    def test_ma_slope_from_prices(self):
        """测试从价格序列计算MA斜率"""
        # 生成上涨趋势的价格序列
        prices = pd.Series([10.0 + i * 0.1 for i in range(30)])
        slope = TechIndicators.calculate_ma_slope_from_prices(prices, ma_period=20, slope_days=5)
        
        # 上涨趋势斜率应为正
        assert slope > 0
    
    @given(
        start_value=st.floats(min_value=10.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        end_value=st.floats(min_value=10.0, max_value=100.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_ma_slope_direction_property(self, start_value: float, end_value: float):
        """测试斜率方向属性：上涨为正，下跌为负"""
        # 生成线性变化的MA序列
        ma_series = pd.Series(np.linspace(start_value, end_value, 6))
        slope = TechIndicators.calculate_ma_slope(ma_series, 5)
        
        if end_value > start_value:
            assert slope > 0
        elif end_value < start_value:
            assert slope < 0
        else:
            assert abs(slope) < 1e-6


class TestCalculateAllIndicators:
    """综合指标计算测试"""
    
    def test_calculate_all_indicators(self):
        """测试计算所有指标"""
        # 生成足够长的价格和成交量序列
        np.random.seed(42)
        prices = pd.Series([10.0 + i * 0.05 + np.random.uniform(-0.1, 0.1) for i in range(100)])
        volumes = pd.Series([1000000 + np.random.uniform(-100000, 100000) for _ in range(100)])
        
        indicators = TechIndicators.calculate_all_indicators(prices, volumes)
        
        # 验证所有指标都存在
        assert 'ma5' in indicators
        assert 'ma10' in indicators
        assert 'ma20' in indicators
        assert 'ma60' in indicators
        assert 'rsi' in indicators
        assert 'volume_ratio' in indicators
        assert 'ma20_slope' in indicators
        assert 'current_price' in indicators
        
        # 验证指标值合理
        assert not np.isnan(indicators['ma5'])
        assert not np.isnan(indicators['ma20'])
        assert not np.isnan(indicators['ma60'])
        assert 0 <= indicators['rsi'] <= 100
        assert indicators['volume_ratio'] > 0
    
    def test_calculate_all_indicators_insufficient_data(self):
        """测试数据不足时的综合指标计算"""
        prices = pd.Series([10.0, 11.0, 12.0])
        volumes = pd.Series([1000000, 1100000, 1200000])
        
        indicators = TechIndicators.calculate_all_indicators(prices, volumes)
        
        # MA60应为NaN（数据不足）
        assert np.isnan(indicators['ma60'])
        # RSI应为中性值
        assert indicators['rsi'] == 50.0
        # 量比应为中性值
        assert indicators['volume_ratio'] == 1.0


class TestEdgeCases:
    """边界条件测试"""
    
    def test_empty_series(self):
        """测试空序列"""
        empty_series = pd.Series([], dtype=float)
        
        ma = TechIndicators.calculate_ma(empty_series, 5)
        assert len(ma) == 0
        
        ma_value = TechIndicators.calculate_ma_value(empty_series, 5)
        assert np.isnan(ma_value)
    
    def test_single_value(self):
        """测试单值序列"""
        single_series = pd.Series([10.0])
        
        ma_value = TechIndicators.calculate_ma_value(single_series, 5)
        assert np.isnan(ma_value)
        
        rsi = TechIndicators.calculate_rsi_value(single_series, 14)
        assert rsi == 50.0
    
    def test_constant_prices(self):
        """测试价格不变的情况"""
        constant_prices = pd.Series([10.0] * 20)
        
        # RSI应为中性值（无涨跌）
        rsi = TechIndicators.calculate_rsi_value(constant_prices, 14)
        # 当价格不变时，RSI可能为NaN或50
        assert np.isnan(rsi) or rsi == 50.0
        
        # MA斜率应为0
        ma_series = TechIndicators.calculate_ma(constant_prices, 5)
        slope = TechIndicators.calculate_ma_slope(ma_series, 5)
        assert abs(slope) < 0.0001
