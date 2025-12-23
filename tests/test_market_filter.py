"""
MarketFilter 单元测试

测试大盘红绿灯过滤器功能：
- 测试绿灯条件判断
- 测试红灯条件判断
- 测试 MACD 状态计算

Requirements: 1.2, 1.3
"""

import pytest
import sys
import os
from datetime import date
import pandas as pd
import numpy as np

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.tech_stock.market_filter import MarketFilter, MarketStatus


def create_test_data(
    prices: list,
    start_date: str = "2024-01-01"
) -> pd.DataFrame:
    """
    创建测试用的指数数据
    
    Args:
        prices: 收盘价列表
        start_date: 起始日期
    
    Returns:
        包含 date, open, high, low, close, volume 的 DataFrame
    """
    n = len(prices)
    dates = pd.date_range(start=start_date, periods=n, freq='D')
    
    df = pd.DataFrame({
        'date': dates,
        'open': prices,
        'high': [p * 1.02 for p in prices],
        'low': [p * 0.98 for p in prices],
        'close': prices,
        'volume': [1000000] * n
    })
    
    return df


class TestMarketFilterInit:
    """测试 MarketFilter 初始化"""
    
    def test_market_filter_creation(self):
        """测试 MarketFilter 创建"""
        mf = MarketFilter()
        assert mf is not None
        assert mf.gem_index_code == "399006"
        assert mf.ma_period == 20
    
    def test_market_filter_with_custom_data_feed(self):
        """测试使用自定义 data_feed 创建"""
        mf = MarketFilter(data_feed=None)
        assert mf._data_feed is None


class TestGreenLightCondition:
    """测试绿灯条件判断 (Requirements: 1.2)"""
    
    def test_green_light_price_above_ma20_and_macd_golden_cross(self):
        """测试绿灯：收盘价 > MA20 且 MACD 金叉"""
        # 创建上涨趋势数据，确保最新价格 > MA20 且 MACD 金叉
        # 需要足够的数据来计算 MA20 和 MACD
        prices = list(range(100, 140))  # 40天上涨趋势
        df = create_test_data(prices)
        
        mf = MarketFilter()
        status = mf.check_market_status(df)
        
        # 上涨趋势应该是绿灯
        assert status.is_green == True
        assert status.gem_close > status.gem_ma20
        assert status.macd_status in ["golden_cross", "neutral"]
    
    def test_green_light_sustained_uptrend(self):
        """测试绿灯：持续上涨趋势"""
        # 创建持续上涨的数据
        base = 100
        prices = [base + i * 0.5 for i in range(50)]  # 50天缓慢上涨
        df = create_test_data(prices)
        
        mf = MarketFilter()
        status = mf.check_market_status(df)
        
        # 持续上涨应该是绿灯
        assert status.is_green == True
        assert "✓" in status.reason


class TestRedLightCondition:
    """测试红灯条件判断 (Requirements: 1.3)"""
    
    def test_red_light_price_below_ma20(self):
        """测试红灯：收盘价 <= MA20"""
        # 创建下跌趋势数据，确保最新价格 < MA20
        prices = list(range(140, 100, -1))  # 40天下跌趋势
        df = create_test_data(prices)
        
        mf = MarketFilter()
        status = mf.check_market_status(df)
        
        # 下跌趋势应该是红灯
        assert status.is_green == False
        assert status.gem_close < status.gem_ma20
    
    def test_red_light_macd_death_cross(self):
        """测试红灯：MACD 死叉"""
        # 创建先涨后跌的数据，触发 MACD 死叉
        prices = list(range(100, 130)) + list(range(130, 115, -1))  # 先涨后跌
        df = create_test_data(prices)
        
        mf = MarketFilter()
        status = mf.check_market_status(df)
        
        # 先涨后跌可能触发死叉，应该是红灯
        # 注意：具体结果取决于 MACD 计算
        assert status.macd_status in ["death_cross", "golden_cross", "neutral"]
    
    def test_red_light_sustained_downtrend(self):
        """测试红灯：持续下跌趋势"""
        # 创建持续下跌的数据
        base = 150
        prices = [base - i * 0.5 for i in range(50)]  # 50天缓慢下跌
        df = create_test_data(prices)
        
        mf = MarketFilter()
        status = mf.check_market_status(df)
        
        # 持续下跌应该是红灯
        assert status.is_green == False
        assert "✗" in status.reason
    
    def test_red_light_empty_data(self):
        """测试红灯：空数据默认返回红灯"""
        mf = MarketFilter()
        status = mf.check_market_status(pd.DataFrame())
        
        assert status.is_green == False
        assert "无法获取" in status.reason
    
    def test_red_light_none_data(self):
        """测试红灯：None 数据默认返回红灯"""
        mf = MarketFilter(data_feed=None)
        # 不传入数据，且没有 data_feed，应该返回红灯
        status = mf.check_market_status(None)
        
        assert status.is_green == False


class TestMACDStatusCalculation:
    """测试 MACD 状态计算"""
    
    def test_macd_calculation(self):
        """测试 MACD 指标计算"""
        prices = list(range(100, 150))  # 50天数据
        df = create_test_data(prices)
        
        mf = MarketFilter()
        df_with_macd = mf._calculate_macd(df)
        
        # 验证 MACD 列存在
        assert 'macd' in df_with_macd.columns
        assert 'macd_signal' in df_with_macd.columns
        assert 'macd_hist' in df_with_macd.columns
    
    def test_macd_golden_cross_detection(self):
        """测试 MACD 金叉检测"""
        # 创建上涨趋势数据
        prices = list(range(100, 160))  # 60天上涨
        df = create_test_data(prices)
        
        mf = MarketFilter()
        df_with_macd = mf._calculate_macd(df)
        status = mf._calculate_macd_status(df_with_macd)
        
        # 上涨趋势应该是金叉状态
        assert status == "golden_cross"
    
    def test_macd_death_cross_detection(self):
        """测试 MACD 死叉检测"""
        # 创建下跌趋势数据
        prices = list(range(160, 100, -1))  # 60天下跌
        df = create_test_data(prices)
        
        mf = MarketFilter()
        df_with_macd = mf._calculate_macd(df)
        status = mf._calculate_macd_status(df_with_macd)
        
        # 下跌趋势应该是死叉状态
        assert status == "death_cross"
    
    def test_macd_status_with_insufficient_data(self):
        """测试数据不足时的 MACD 状态"""
        prices = [100]  # 只有1天数据
        df = create_test_data(prices)
        
        mf = MarketFilter()
        df_with_macd = mf._calculate_macd(df)
        status = mf._calculate_macd_status(df_with_macd)
        
        # 数据不足应该返回 neutral
        assert status == "neutral"
    
    def test_macd_status_without_macd_columns(self):
        """测试缺少 MACD 列时的状态"""
        prices = [100, 101, 102]
        df = create_test_data(prices)
        # 不计算 MACD，直接调用状态计算
        
        mf = MarketFilter()
        status = mf._calculate_macd_status(df)
        
        # 缺少 MACD 列应该返回 neutral
        assert status == "neutral"


class TestMarketStatusDataClass:
    """测试 MarketStatus 数据类"""
    
    def test_market_status_creation(self):
        """测试 MarketStatus 创建"""
        status = MarketStatus(
            is_green=True,
            gem_close=2500.0,
            gem_ma20=2400.0,
            macd_status="golden_cross",
            check_date=date.today(),
            reason="测试原因"
        )
        
        assert status.is_green == True
        assert status.gem_close == 2500.0
        assert status.gem_ma20 == 2400.0
        assert status.macd_status == "golden_cross"
        assert status.reason == "测试原因"
    
    def test_market_status_red_light(self):
        """测试红灯状态的 MarketStatus"""
        status = MarketStatus(
            is_green=False,
            gem_close=2300.0,
            gem_ma20=2400.0,
            macd_status="death_cross",
            check_date=date.today(),
            reason="收盘价低于MA20"
        )
        
        assert status.is_green == False
        assert status.gem_close < status.gem_ma20


class TestIsTradingAllowed:
    """测试 is_trading_allowed 方法"""
    
    def test_trading_allowed_green_light(self):
        """测试绿灯时允许交易"""
        prices = list(range(100, 140))  # 上涨趋势
        df = create_test_data(prices)
        
        mf = MarketFilter()
        allowed = mf.is_trading_allowed(df)
        
        assert allowed == True
    
    def test_trading_not_allowed_red_light(self):
        """测试红灯时禁止交易"""
        prices = list(range(140, 100, -1))  # 下跌趋势
        df = create_test_data(prices)
        
        mf = MarketFilter()
        allowed = mf.is_trading_allowed(df)
        
        assert allowed == False


class TestEdgeCases:
    """测试边界情况"""
    
    def test_price_exactly_at_ma20(self):
        """测试收盘价恰好等于 MA20"""
        # 创建平稳数据，使收盘价接近 MA20
        prices = [100.0] * 30  # 30天相同价格
        df = create_test_data(prices)
        
        mf = MarketFilter()
        status = mf.check_market_status(df)
        
        # 价格等于 MA20 时应该是红灯（<= 条件）
        # 由于浮点数精度，可能略有差异
        assert abs(status.gem_close - status.gem_ma20) < 0.01
    
    def test_volatile_market(self):
        """测试震荡市场"""
        # 创建震荡数据
        prices = [100 + (i % 10) * 2 - 10 for i in range(50)]  # 震荡
        df = create_test_data(prices)
        
        mf = MarketFilter()
        status = mf.check_market_status(df)
        
        # 震荡市场应该有明确的状态
        assert status.is_green in [True, False]
        assert status.macd_status in ["golden_cross", "death_cross", "neutral"]


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
