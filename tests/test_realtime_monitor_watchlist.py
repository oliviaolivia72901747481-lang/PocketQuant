"""
Realtime Monitor Watchlist Tests

测试监控列表管理功能，包括股票代码验证和监控列表大小限制。
Property 1: Stock Code Validation
Property 2: Watchlist Size Limit
Validates: Requirements 1.1, 1.3
"""

import pytest
from hypothesis import given, strategies as st, settings, assume

from core.realtime_monitor.monitor import RealtimeMonitor
from core.realtime_monitor.config import MONITOR_CONFIG


class TestStockCodeValidation:
    """股票代码验证测试"""
    
    def test_valid_code_000001(self):
        """测试有效代码 000001"""
        monitor = RealtimeMonitor()
        assert monitor.validate_stock_code('000001') is True
    
    def test_valid_code_300001(self):
        """测试有效代码 300001"""
        monitor = RealtimeMonitor()
        assert monitor.validate_stock_code('300001') is True
    
    def test_valid_code_600001(self):
        """测试有效代码 600001"""
        monitor = RealtimeMonitor()
        assert monitor.validate_stock_code('600001') is True
    
    def test_invalid_code_wrong_prefix(self):
        """测试无效前缀"""
        monitor = RealtimeMonitor()
        assert monitor.validate_stock_code('100001') is False
        assert monitor.validate_stock_code('200001') is False
        assert monitor.validate_stock_code('400001') is False
        assert monitor.validate_stock_code('500001') is False
        assert monitor.validate_stock_code('700001') is False
        assert monitor.validate_stock_code('800001') is False
        assert monitor.validate_stock_code('900001') is False
    
    def test_invalid_code_wrong_length(self):
        """测试无效长度"""
        monitor = RealtimeMonitor()
        assert monitor.validate_stock_code('00001') is False   # 5位
        assert monitor.validate_stock_code('0000001') is False # 7位
        assert monitor.validate_stock_code('') is False        # 空
    
    def test_invalid_code_non_digit(self):
        """测试非数字字符"""
        monitor = RealtimeMonitor()
        assert monitor.validate_stock_code('00000a') is False
        assert monitor.validate_stock_code('abcdef') is False
        assert monitor.validate_stock_code('000 01') is False
    
    def test_invalid_code_non_string(self):
        """测试非字符串输入"""
        monitor = RealtimeMonitor()
        assert monitor.validate_stock_code(None) is False
        assert monitor.validate_stock_code(123456) is False
        assert monitor.validate_stock_code(['000001']) is False
    
    # Property 1: Stock Code Validation
    # Feature: realtime-monitor, Property 1: Stock Code Validation
    @given(
        prefix=st.sampled_from(['0', '3', '6']),
        suffix=st.text(alphabet='0123456789', min_size=5, max_size=5)
    )
    @settings(max_examples=100)
    def test_valid_stock_code_property(self, prefix: str, suffix: str):
        """
        Property 1: Stock Code Validation (Valid Codes)
        
        For any input string that is 6 digits starting with 0, 3, or 6,
        the validation should return True.
        
        **Validates: Requirements 1.1**
        """
        code = prefix + suffix
        monitor = RealtimeMonitor()
        assert monitor.validate_stock_code(code) is True
    
    # Property 1: Stock Code Validation (Invalid Codes)
    # Feature: realtime-monitor, Property 1: Stock Code Validation
    @given(
        prefix=st.sampled_from(['1', '2', '4', '5', '7', '8', '9']),
        suffix=st.text(alphabet='0123456789', min_size=5, max_size=5)
    )
    @settings(max_examples=100)
    def test_invalid_prefix_stock_code_property(self, prefix: str, suffix: str):
        """
        Property 1: Stock Code Validation (Invalid Prefix)
        
        For any input string that is 6 digits but NOT starting with 0, 3, or 6,
        the validation should return False.
        
        **Validates: Requirements 1.1**
        """
        code = prefix + suffix
        monitor = RealtimeMonitor()
        assert monitor.validate_stock_code(code) is False
    
    # Property 1: Stock Code Validation (Wrong Length)
    # Feature: realtime-monitor, Property 1: Stock Code Validation
    @given(
        length=st.integers(min_value=1, max_value=10).filter(lambda x: x != 6)
    )
    @settings(max_examples=100)
    def test_invalid_length_stock_code_property(self, length: int):
        """
        Property 1: Stock Code Validation (Invalid Length)
        
        For any input string that is NOT 6 characters long,
        the validation should return False.
        
        **Validates: Requirements 1.1**
        """
        code = '0' * length
        monitor = RealtimeMonitor()
        assert monitor.validate_stock_code(code) is False


class TestWatchlistSizeLimit:
    """监控列表大小限制测试"""
    
    def test_add_up_to_max_size(self):
        """测试添加到最大容量"""
        monitor = RealtimeMonitor()
        max_size = monitor.config.max_watchlist_size
        
        # 添加到最大容量
        for i in range(max_size):
            code = f'{i:06d}'
            # 确保代码有效（以0, 3, 6开头）
            if not code.startswith(('0', '3', '6')):
                code = f'0{i:05d}'
            result = monitor.add_to_watchlist(code)
            assert result is True, f"Failed to add code {code} at index {i}"
        
        assert monitor.watchlist_size == max_size
    
    def test_cannot_exceed_max_size(self):
        """测试不能超过最大容量"""
        monitor = RealtimeMonitor()
        max_size = monitor.config.max_watchlist_size
        
        # 添加到最大容量
        for i in range(max_size):
            code = f'0{i:05d}'
            monitor.add_to_watchlist(code)
        
        # 尝试添加第21个
        result = monitor.add_to_watchlist('099999')
        assert result is False
        assert monitor.watchlist_size == max_size
    
    def test_remove_then_add(self):
        """测试移除后可以再添加"""
        monitor = RealtimeMonitor()
        max_size = monitor.config.max_watchlist_size
        
        # 添加到最大容量
        for i in range(max_size):
            code = f'0{i:05d}'
            monitor.add_to_watchlist(code)
        
        # 移除一个
        monitor.remove_from_watchlist('000000')
        assert monitor.watchlist_size == max_size - 1
        
        # 现在可以添加新的
        result = monitor.add_to_watchlist('099999')
        assert result is True
        assert monitor.watchlist_size == max_size
    
    # Property 2: Watchlist Size Limit
    # Feature: realtime-monitor, Property 2: Watchlist Size Limit
    @given(
        extra_codes=st.lists(
            st.text(alphabet='0123456789', min_size=5, max_size=5).map(lambda s: '0' + s),
            min_size=1,
            max_size=10
        )
    )
    @settings(max_examples=100)
    def test_watchlist_size_limit_property(self, extra_codes: list):
        """
        Property 2: Watchlist Size Limit
        
        For any watchlist with 20 stocks, attempting to add another stock 
        should fail and the watchlist size should remain 20.
        
        **Validates: Requirements 1.3**
        """
        monitor = RealtimeMonitor()
        max_size = monitor.config.max_watchlist_size
        
        # 填满监控列表
        for i in range(max_size):
            code = f'0{i:05d}'
            monitor.add_to_watchlist(code)
        
        assert monitor.watchlist_size == max_size
        
        # 尝试添加更多代码
        for code in extra_codes:
            # 确保代码不在列表中
            if code not in monitor.watchlist:
                result = monitor.add_to_watchlist(code)
                assert result is False, f"Should not be able to add {code} when list is full"
                assert monitor.watchlist_size == max_size, "Watchlist size should remain at max"


class TestWatchlistManagement:
    """监控列表管理测试"""
    
    def test_add_valid_code(self):
        """测试添加有效代码"""
        monitor = RealtimeMonitor()
        result = monitor.add_to_watchlist('000001')
        assert result is True
        assert '000001' in monitor.watchlist
    
    def test_add_invalid_code(self):
        """测试添加无效代码"""
        monitor = RealtimeMonitor()
        result = monitor.add_to_watchlist('invalid')
        assert result is False
        assert monitor.watchlist_size == 0
    
    def test_add_duplicate_code(self):
        """测试添加重复代码"""
        monitor = RealtimeMonitor()
        monitor.add_to_watchlist('000001')
        result = monitor.add_to_watchlist('000001')
        assert result is False
        assert monitor.watchlist_size == 1
    
    def test_remove_existing_code(self):
        """测试移除存在的代码"""
        monitor = RealtimeMonitor()
        monitor.add_to_watchlist('000001')
        result = monitor.remove_from_watchlist('000001')
        assert result is True
        assert '000001' not in monitor.watchlist
    
    def test_remove_non_existing_code(self):
        """测试移除不存在的代码"""
        monitor = RealtimeMonitor()
        result = monitor.remove_from_watchlist('000001')
        assert result is False
    
    def test_is_in_watchlist(self):
        """测试检查代码是否在监控列表中"""
        monitor = RealtimeMonitor()
        monitor.add_to_watchlist('000001')
        assert monitor.is_in_watchlist('000001') is True
        assert monitor.is_in_watchlist('000002') is False
    
    def test_clear_watchlist(self):
        """测试清空监控列表"""
        monitor = RealtimeMonitor()
        monitor.add_to_watchlist('000001')
        monitor.add_to_watchlist('000002')
        monitor.clear_watchlist()
        assert monitor.watchlist_size == 0


class TestPositionManagement:
    """持仓管理测试"""
    
    def test_add_position(self):
        """测试添加持仓"""
        monitor = RealtimeMonitor()
        result = monitor.add_position(
            code='000001',
            name='测试股票',
            cost_price=10.0,
            quantity=100
        )
        assert result is True
        assert monitor.has_position('000001')
        # 添加持仓应自动添加到监控列表
        assert monitor.is_in_watchlist('000001')
    
    def test_add_position_invalid_code(self):
        """测试添加无效代码的持仓"""
        monitor = RealtimeMonitor()
        result = monitor.add_position(
            code='invalid',
            name='测试股票',
            cost_price=10.0,
            quantity=100
        )
        assert result is False
    
    def test_add_position_invalid_price(self):
        """测试添加无效价格的持仓"""
        monitor = RealtimeMonitor()
        result = monitor.add_position(
            code='000001',
            name='测试股票',
            cost_price=0,
            quantity=100
        )
        assert result is False
        
        result = monitor.add_position(
            code='000001',
            name='测试股票',
            cost_price=-10.0,
            quantity=100
        )
        assert result is False
    
    def test_add_position_invalid_quantity(self):
        """测试添加无效数量的持仓"""
        monitor = RealtimeMonitor()
        result = monitor.add_position(
            code='000001',
            name='测试股票',
            cost_price=10.0,
            quantity=0
        )
        assert result is False
        
        result = monitor.add_position(
            code='000001',
            name='测试股票',
            cost_price=10.0,
            quantity=-100
        )
        assert result is False
    
    def test_add_duplicate_position(self):
        """测试添加重复持仓"""
        monitor = RealtimeMonitor()
        monitor.add_position(
            code='000001',
            name='测试股票',
            cost_price=10.0,
            quantity=100
        )
        result = monitor.add_position(
            code='000001',
            name='测试股票2',
            cost_price=12.0,
            quantity=200
        )
        assert result is False
    
    def test_update_position(self):
        """测试更新持仓"""
        monitor = RealtimeMonitor()
        monitor.add_position(
            code='000001',
            name='测试股票',
            cost_price=10.0,
            quantity=100
        )
        
        result = monitor.update_position(
            code='000001',
            cost_price=11.0,
            quantity=200
        )
        assert result is True
        
        position = monitor.get_position('000001')
        assert position.cost_price == 11.0
        assert position.quantity == 200
    
    def test_update_non_existing_position(self):
        """测试更新不存在的持仓"""
        monitor = RealtimeMonitor()
        result = monitor.update_position(
            code='000001',
            cost_price=11.0
        )
        assert result is False
    
    def test_remove_position(self):
        """测试移除持仓"""
        monitor = RealtimeMonitor()
        monitor.add_position(
            code='000001',
            name='测试股票',
            cost_price=10.0,
            quantity=100
        )
        
        result = monitor.remove_position('000001')
        assert result is True
        assert not monitor.has_position('000001')
    
    def test_remove_non_existing_position(self):
        """测试移除不存在的持仓"""
        monitor = RealtimeMonitor()
        result = monitor.remove_position('000001')
        assert result is False


class TestPeakPriceTracking:
    """峰值价格跟踪测试"""
    
    def test_update_position_price(self):
        """测试更新持仓价格"""
        monitor = RealtimeMonitor()
        monitor.add_position(
            code='000001',
            name='测试股票',
            cost_price=10.0,
            quantity=100
        )
        
        # 价格上涨
        result = monitor.update_position_price('000001', 12.0)
        assert result is True
        
        position = monitor.get_position('000001')
        assert position.current_price == 12.0
        assert position.peak_price == 12.0
    
    def test_peak_price_not_decrease(self):
        """测试峰值价格不会下降"""
        monitor = RealtimeMonitor()
        monitor.add_position(
            code='000001',
            name='测试股票',
            cost_price=10.0,
            quantity=100
        )
        
        # 价格上涨到12
        monitor.update_position_price('000001', 12.0)
        
        # 价格下跌到11
        monitor.update_position_price('000001', 11.0)
        
        position = monitor.get_position('000001')
        assert position.current_price == 11.0
        assert position.peak_price == 12.0  # 峰值保持不变
    
    def test_update_all_position_prices(self):
        """测试批量更新持仓价格"""
        monitor = RealtimeMonitor()
        monitor.add_position('000001', '股票1', 10.0, 100)
        monitor.add_position('000002', '股票2', 20.0, 200)
        
        results = monitor.update_all_position_prices({
            '000001': 12.0,
            '000002': 22.0,
            '000003': 30.0  # 不存在的持仓
        })
        
        assert results['000001'] is True
        assert results['000002'] is True
        assert results['000003'] is False
    
    def test_get_peak_price(self):
        """测试获取峰值价格"""
        monitor = RealtimeMonitor()
        monitor.add_position('000001', '测试股票', 10.0, 100)
        monitor.update_position_price('000001', 15.0)
        
        peak = monitor.get_peak_price('000001')
        assert peak == 15.0
        
        # 不存在的持仓
        peak = monitor.get_peak_price('000002')
        assert peak is None
    
    def test_reset_peak_price(self):
        """测试重置峰值价格"""
        monitor = RealtimeMonitor()
        monitor.add_position('000001', '测试股票', 10.0, 100)
        monitor.update_position_price('000001', 15.0)
        monitor.update_position_price('000001', 12.0)
        
        # 重置峰值
        result = monitor.reset_peak_price('000001')
        assert result is True
        
        position = monitor.get_position('000001')
        assert position.peak_price == 12.0  # 重置为当前价格


class TestPositionSummary:
    """持仓汇总测试"""
    
    def test_total_market_value(self):
        """测试总市值计算"""
        monitor = RealtimeMonitor()
        monitor.add_position('000001', '股票1', 10.0, 100)
        monitor.add_position('000002', '股票2', 20.0, 200)
        
        monitor.update_position_price('000001', 12.0)
        monitor.update_position_price('000002', 22.0)
        
        total = monitor.get_total_market_value()
        expected = 12.0 * 100 + 22.0 * 200  # 1200 + 4400 = 5600
        assert abs(total - expected) < 0.01
    
    def test_total_cost_value(self):
        """测试总成本计算"""
        monitor = RealtimeMonitor()
        monitor.add_position('000001', '股票1', 10.0, 100)
        monitor.add_position('000002', '股票2', 20.0, 200)
        
        total = monitor.get_total_cost_value()
        expected = 10.0 * 100 + 20.0 * 200  # 1000 + 4000 = 5000
        assert abs(total - expected) < 0.01
    
    def test_total_pnl(self):
        """测试总盈亏计算"""
        monitor = RealtimeMonitor()
        monitor.add_position('000001', '股票1', 10.0, 100)
        monitor.add_position('000002', '股票2', 20.0, 200)
        
        monitor.update_position_price('000001', 12.0)
        monitor.update_position_price('000002', 22.0)
        
        total_pnl = monitor.get_total_pnl()
        expected = (12.0 - 10.0) * 100 + (22.0 - 20.0) * 200  # 200 + 400 = 600
        assert abs(total_pnl - expected) < 0.01
    
    def test_total_pnl_pct(self):
        """测试总盈亏百分比计算"""
        monitor = RealtimeMonitor()
        monitor.add_position('000001', '股票1', 10.0, 100)
        monitor.add_position('000002', '股票2', 20.0, 200)
        
        monitor.update_position_price('000001', 12.0)
        monitor.update_position_price('000002', 22.0)
        
        total_pnl_pct = monitor.get_total_pnl_pct()
        # 总盈亏 600，总成本 5000，盈亏比 12%
        expected = 600.0 / 5000.0
        assert abs(total_pnl_pct - expected) < 0.0001
    
    def test_position_summary(self):
        """测试持仓汇总"""
        monitor = RealtimeMonitor()
        monitor.add_position('000001', '股票1', 10.0, 100)
        monitor.update_position_price('000001', 12.0)
        
        summary = monitor.get_position_summary()
        
        assert summary['position_count'] == 1
        assert abs(summary['total_market_value'] - 1200.0) < 0.01
        assert abs(summary['total_cost_value'] - 1000.0) < 0.01
        assert abs(summary['total_pnl'] - 200.0) < 0.01
        assert abs(summary['total_pnl_pct'] - 0.2) < 0.0001
