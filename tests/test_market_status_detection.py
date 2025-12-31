"""
Market Status Detection Tests

测试市场状态检测功能。
Property 11: Market Status Detection
Validates: Requirements 5.2
"""

import pytest
from datetime import datetime, time, date
from hypothesis import given, strategies as st, settings, assume

from core.realtime_monitor.data_fetcher import DataFetcher, MarketStatus, get_market_status, is_trading_time
from core.realtime_monitor.config import MONITOR_CONFIG


class TestMarketStatusBasic:
    """市场状态基本测试"""
    
    def test_morning_trading_session(self):
        """测试上午交易时段"""
        fetcher = DataFetcher()
        
        # 上午交易时段 9:30-11:30
        test_time = datetime(2025, 12, 29, 10, 0, 0)  # 周一 10:00
        status = fetcher.get_market_status(test_time)
        
        assert status.is_open is True
        assert status.status == MarketStatus.STATUS_OPEN
    
    def test_afternoon_trading_session(self):
        """测试下午交易时段"""
        fetcher = DataFetcher()
        
        # 下午交易时段 13:00-15:00
        test_time = datetime(2025, 12, 29, 14, 0, 0)  # 周一 14:00
        status = fetcher.get_market_status(test_time)
        
        assert status.is_open is True
        assert status.status == MarketStatus.STATUS_OPEN
    
    def test_pre_market(self):
        """测试盘前时段"""
        fetcher = DataFetcher()
        
        # 盘前 9:30之前
        test_time = datetime(2025, 12, 29, 9, 0, 0)  # 周一 9:00
        status = fetcher.get_market_status(test_time)
        
        assert status.is_open is False
        assert status.status == MarketStatus.STATUS_PRE_MARKET
    
    def test_lunch_break(self):
        """测试午休时段"""
        fetcher = DataFetcher()
        
        # 午休 11:30-13:00
        test_time = datetime(2025, 12, 29, 12, 0, 0)  # 周一 12:00
        status = fetcher.get_market_status(test_time)
        
        assert status.is_open is False
        assert status.status == MarketStatus.STATUS_LUNCH_BREAK
    
    def test_after_hours(self):
        """测试盘后时段"""
        fetcher = DataFetcher()
        
        # 盘后 15:00之后
        test_time = datetime(2025, 12, 29, 16, 0, 0)  # 周一 16:00
        status = fetcher.get_market_status(test_time)
        
        assert status.is_open is False
        assert status.status == MarketStatus.STATUS_AFTER_HOURS
    
    def test_weekend_saturday(self):
        """测试周六休市"""
        fetcher = DataFetcher()
        
        # 周六
        test_time = datetime(2025, 12, 27, 10, 0, 0)  # 周六 10:00
        status = fetcher.get_market_status(test_time)
        
        assert status.is_open is False
        assert status.status == MarketStatus.STATUS_CLOSED
    
    def test_weekend_sunday(self):
        """测试周日休市"""
        fetcher = DataFetcher()
        
        # 周日
        test_time = datetime(2025, 12, 28, 10, 0, 0)  # 周日 10:00
        status = fetcher.get_market_status(test_time)
        
        assert status.is_open is False
        assert status.status == MarketStatus.STATUS_CLOSED


class TestMarketStatusBoundary:
    """市场状态边界测试"""
    
    def test_morning_open_exact(self):
        """测试上午开盘时刻 9:30"""
        fetcher = DataFetcher()
        test_time = datetime(2025, 12, 29, 9, 30, 0)  # 周一 9:30
        status = fetcher.get_market_status(test_time)
        
        assert status.is_open is True
        assert status.status == MarketStatus.STATUS_OPEN
    
    def test_morning_close_exact(self):
        """测试上午收盘时刻 11:30"""
        fetcher = DataFetcher()
        test_time = datetime(2025, 12, 29, 11, 30, 0)  # 周一 11:30
        status = fetcher.get_market_status(test_time)
        
        assert status.is_open is True
        assert status.status == MarketStatus.STATUS_OPEN
    
    def test_afternoon_open_exact(self):
        """测试下午开盘时刻 13:00"""
        fetcher = DataFetcher()
        test_time = datetime(2025, 12, 29, 13, 0, 0)  # 周一 13:00
        status = fetcher.get_market_status(test_time)
        
        assert status.is_open is True
        assert status.status == MarketStatus.STATUS_OPEN
    
    def test_afternoon_close_exact(self):
        """测试下午收盘时刻 15:00"""
        fetcher = DataFetcher()
        test_time = datetime(2025, 12, 29, 15, 0, 0)  # 周一 15:00
        status = fetcher.get_market_status(test_time)
        
        assert status.is_open is True
        assert status.status == MarketStatus.STATUS_OPEN
    
    def test_just_before_morning_open(self):
        """测试上午开盘前一秒 9:29:59"""
        fetcher = DataFetcher()
        test_time = datetime(2025, 12, 29, 9, 29, 59)  # 周一 9:29:59
        status = fetcher.get_market_status(test_time)
        
        assert status.is_open is False
        assert status.status == MarketStatus.STATUS_PRE_MARKET
    
    def test_just_after_afternoon_close(self):
        """测试下午收盘后一秒 15:00:01"""
        fetcher = DataFetcher()
        test_time = datetime(2025, 12, 29, 15, 0, 1)  # 周一 15:00:01
        status = fetcher.get_market_status(test_time)
        
        assert status.is_open is False
        assert status.status == MarketStatus.STATUS_AFTER_HOURS


class TestMarketStatusProperty:
    """市场状态属性测试"""
    
    # Property 11: Market Status Detection
    # Feature: realtime-monitor, Property 11: Market Status Detection
    @given(
        weekday=st.integers(min_value=0, max_value=4),  # 周一到周五
        hour=st.integers(min_value=9, max_value=11),
        minute=st.integers(min_value=0, max_value=59)
    )
    @settings(max_examples=100)
    def test_morning_trading_hours_property(self, weekday: int, hour: int, minute: int):
        """
        Property 11: Market Status Detection (Morning Session)
        
        For any time T within morning trading hours (9:30-11:30) on a weekday,
        market status should be "open".
        
        **Validates: Requirements 5.2**
        """
        # 构造时间：确保在9:30-11:30之间
        if hour == 9 and minute < 30:
            minute = 30  # 调整到9:30
        if hour == 11 and minute > 30:
            minute = 30  # 调整到11:30
        
        # 使用2025年1月的工作日作为基准（避免月末溢出）
        # 2025-01-06 是周一 (weekday=0)
        test_date = date(2025, 1, 6 + weekday)  # 6=周一, 10=周五
        
        # 确保不是周末
        if test_date.weekday() >= 5:
            return  # 跳过周末
        
        test_time = datetime(test_date.year, test_date.month, test_date.day, hour, minute, 0)
        
        fetcher = DataFetcher()
        status = fetcher.get_market_status(test_time)
        
        # 检查是否在交易时间内
        current_time = test_time.time()
        morning_start = time(9, 30)
        morning_end = time(11, 30)
        
        if morning_start <= current_time <= morning_end:
            assert status.is_open is True, f"Should be open at {test_time}"
            assert status.status == MarketStatus.STATUS_OPEN
    
    # Property 11: Market Status Detection (Afternoon Session)
    # Feature: realtime-monitor, Property 11: Market Status Detection
    @given(
        weekday=st.integers(min_value=0, max_value=4),  # 周一到周五
        hour=st.integers(min_value=13, max_value=15),
        minute=st.integers(min_value=0, max_value=59)
    )
    @settings(max_examples=100)
    def test_afternoon_trading_hours_property(self, weekday: int, hour: int, minute: int):
        """
        Property 11: Market Status Detection (Afternoon Session)
        
        For any time T within afternoon trading hours (13:00-15:00) on a weekday,
        market status should be "open".
        
        **Validates: Requirements 5.2**
        """
        # 构造时间：确保在13:00-15:00之间
        if hour == 15 and minute > 0:
            minute = 0  # 调整到15:00
        
        # 使用2025年1月的工作日作为基准（避免月末溢出）
        # 2025-01-06 是周一 (weekday=0)
        test_date = date(2025, 1, 6 + weekday)
        
        # 确保不是周末
        if test_date.weekday() >= 5:
            return
        
        test_time = datetime(test_date.year, test_date.month, test_date.day, hour, minute, 0)
        
        fetcher = DataFetcher()
        status = fetcher.get_market_status(test_time)
        
        # 检查是否在交易时间内
        current_time = test_time.time()
        afternoon_start = time(13, 0)
        afternoon_end = time(15, 0)
        
        if afternoon_start <= current_time <= afternoon_end:
            assert status.is_open is True, f"Should be open at {test_time}"
            assert status.status == MarketStatus.STATUS_OPEN
    
    # Property 11: Market Status Detection (Weekend)
    # Feature: realtime-monitor, Property 11: Market Status Detection
    @given(
        weekday=st.integers(min_value=5, max_value=6),  # 周六或周日
        hour=st.integers(min_value=0, max_value=23),
        minute=st.integers(min_value=0, max_value=59)
    )
    @settings(max_examples=100)
    def test_weekend_closed_property(self, weekday: int, hour: int, minute: int):
        """
        Property 11: Market Status Detection (Weekend)
        
        For any time T on a weekend (Saturday or Sunday),
        market status should be "closed".
        
        **Validates: Requirements 5.2**
        """
        # 2025-12-27 是周六, 2025-12-28 是周日
        if weekday == 5:
            test_date = date(2025, 12, 27)  # 周六
        else:
            test_date = date(2025, 12, 28)  # 周日
        
        test_time = datetime(test_date.year, test_date.month, test_date.day, hour, minute, 0)
        
        fetcher = DataFetcher()
        status = fetcher.get_market_status(test_time)
        
        assert status.is_open is False, f"Should be closed on weekend at {test_time}"
        assert status.status == MarketStatus.STATUS_CLOSED
    
    # Property 11: Market Status Detection (Non-trading hours)
    # Feature: realtime-monitor, Property 11: Market Status Detection
    @given(
        weekday=st.integers(min_value=0, max_value=4),  # 周一到周五
        hour=st.sampled_from([0, 1, 2, 3, 4, 5, 6, 7, 8, 16, 17, 18, 19, 20, 21, 22, 23])
    )
    @settings(max_examples=100)
    def test_non_trading_hours_closed_property(self, weekday: int, hour: int):
        """
        Property 11: Market Status Detection (Non-trading hours)
        
        For any time T outside trading hours on a weekday,
        market status should NOT be "open".
        
        **Validates: Requirements 5.2**
        """
        # 使用2025年1月的工作日作为基准（避免月末溢出）
        # 2025-01-06 是周一 (weekday=0)
        test_date = date(2025, 1, 6 + weekday)
        
        # 确保不是周末
        if test_date.weekday() >= 5:
            return
        
        test_time = datetime(test_date.year, test_date.month, test_date.day, hour, 0, 0)
        
        fetcher = DataFetcher()
        status = fetcher.get_market_status(test_time)
        
        assert status.is_open is False, f"Should be closed at {test_time}"
        assert status.status != MarketStatus.STATUS_OPEN


class TestConvenienceFunctions:
    """便捷函数测试"""
    
    def test_get_market_status_function(self):
        """测试 get_market_status 便捷函数"""
        test_time = datetime(2025, 12, 29, 10, 0, 0)  # 周一 10:00
        status = get_market_status(test_time)
        
        assert status.is_open is True
        assert status.status == MarketStatus.STATUS_OPEN
    
    def test_is_trading_time_function_open(self):
        """测试 is_trading_time 便捷函数 - 开盘"""
        test_time = datetime(2025, 12, 29, 10, 0, 0)  # 周一 10:00
        result = is_trading_time(test_time)
        
        assert result is True
    
    def test_is_trading_time_function_closed(self):
        """测试 is_trading_time 便捷函数 - 休市"""
        test_time = datetime(2025, 12, 27, 10, 0, 0)  # 周六 10:00
        result = is_trading_time(test_time)
        
        assert result is False


class TestDataFetcherCache:
    """数据获取器缓存测试"""
    
    def test_should_refresh_initial(self):
        """测试初始状态需要刷新"""
        fetcher = DataFetcher()
        assert fetcher.should_refresh() is True
    
    def test_clear_cache(self):
        """测试清空缓存"""
        fetcher = DataFetcher()
        fetcher._cache['000001'] = None
        fetcher._fund_flow_cache['000001'] = None
        
        fetcher.clear_cache()
        
        assert len(fetcher._cache) == 0
        assert len(fetcher._fund_flow_cache) == 0
        assert fetcher._last_update is None
