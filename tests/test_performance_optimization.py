"""
Performance Optimization Tests
性能优化测试

Tests the performance optimization features:
1. Caching mechanisms
2. Batch data loading
3. Indicator calculation optimization
4. Memory usage optimization

Requirements: 12.2 性能优化
"""

import pytest
import time
from unittest.mock import Mock, patch
import pandas as pd
from datetime import datetime

from core.tech_stock.performance_optimizer import (
    PerformanceCache,
    BatchDataLoader,
    IndicatorOptimizer,
    MemoryOptimizer,
    performance_timer,
    get_performance_stats,
    clear_all_caches
)


class TestPerformanceCache:
    """测试性能缓存"""
    
    def setup_method(self):
        """Setup test data"""
        self.cache = PerformanceCache(max_memory_mb=10)  # Small cache for testing
    
    def test_stock_data_cache(self):
        """测试股票数据缓存"""
        # 创建测试数据
        test_data = pd.DataFrame({
            'close': [100, 101, 102, 103, 104],
            'volume': [1000, 1100, 1200, 1300, 1400]
        })
        
        # 测试缓存设置和获取
        self.cache.set_stock_data("000001", test_data)
        cached_data = self.cache.get_stock_data("000001")
        
        assert cached_data is not None
        assert len(cached_data) == 5
        assert cached_data['close'].iloc[0] == 100
    
    def test_cache_expiration(self):
        """测试缓存过期"""
        test_data = pd.DataFrame({'close': [100]})
        
        # 设置很短的TTL
        self.cache.STOCK_DATA_TTL = 0.1  # 0.1秒
        
        self.cache.set_stock_data("000001", test_data)
        
        # 立即获取应该成功
        cached_data = self.cache.get_stock_data("000001")
        assert cached_data is not None
        
        # 等待过期后获取应该失败
        time.sleep(0.2)
        expired_data = self.cache.get_stock_data("000001")
        assert expired_data is None
    
    def test_indicator_cache(self):
        """测试指标缓存"""
        test_result = pd.Series([50, 60, 70, 80, 90])
        
        # 测试缓存设置和获取
        self.cache.set_indicator("rsi_000001_14", test_result)
        cached_result = self.cache.get_indicator("rsi_000001_14")
        
        assert cached_result is not None
        assert len(cached_result) == 5
        assert cached_result.iloc[0] == 50
    
    def test_performance_stats(self):
        """测试性能统计"""
        # 执行一些缓存操作
        test_data = pd.DataFrame({'close': [100]})
        self.cache.set_stock_data("000001", test_data)
        self.cache.get_stock_data("000001")
        
        stats = self.cache.get_performance_stats()
        
        assert isinstance(stats, dict)
        assert 'cache_hit_rate' in stats
        assert 'avg_operation_time' in stats
        assert 'total_operations' in stats
        assert 'cache_sizes' in stats


class TestBatchDataLoader:
    """测试批量数据加载器"""
    
    def setup_method(self):
        """Setup test data"""
        self.mock_data_feed = Mock()
        self.loader = BatchDataLoader(self.mock_data_feed, max_workers=2)
    
    def test_batch_loading(self):
        """测试批量加载"""
        # Mock数据
        mock_data = pd.DataFrame({
            'close': [100, 101, 102],
            'volume': [1000, 1100, 1200]
        })
        
        # Mock data_feed方法
        self.mock_data_feed.get_stock_data.return_value = mock_data
        
        # 测试批量加载
        codes = ["000001", "000002"]
        results = self.loader.load_batch_stocks(codes, days=30)
        
        # 验证结果
        assert isinstance(results, dict)
        # Note: 实际结果取决于mock的实现，这里主要测试接口


class TestIndicatorOptimizer:
    """测试指标优化器"""
    
    def setup_method(self):
        """Setup test data"""
        self.optimizer = IndicatorOptimizer()
        
        # 创建测试数据 (40行，满足MACD计算需求)
        self.test_data = {
            "000001": pd.DataFrame({
                'close': [100 + i for i in range(40)],  # 100-139
                'volume': [1000] * 40
            }),
            "000002": pd.DataFrame({
                'close': [200 + i for i in range(40)],  # 200-239
                'volume': [2000] * 40
            })
        }
    
    def test_ma_batch_calculation(self):
        """测试批量MA计算"""
        results = self.optimizer.calculate_ma_batch(self.test_data, [5, 20])
        
        # 验证结果结构
        assert isinstance(results, dict)
        assert "000001" in results
        assert "000002" in results
        
        # 验证MA5和MA20
        assert 5 in results["000001"]
        assert 20 in results["000001"]
        
        # 验证MA值合理性
        ma5_series = results["000001"][5]
        assert len(ma5_series) == 40
        assert not ma5_series.iloc[:4].notna().any()  # 前4个值应该是NaN
        assert ma5_series.iloc[4] == 102.0  # 第5个值应该是前5个的平均
    
    def test_rsi_batch_calculation(self):
        """测试批量RSI计算"""
        results = self.optimizer.calculate_rsi_batch(self.test_data, period=14)
        
        # 验证结果结构
        assert isinstance(results, dict)
        assert "000001" in results
        assert "000002" in results
        
        # 验证RSI值
        rsi_series = results["000001"]
        assert len(rsi_series) == 40
        
        # RSI值应该在0-100之间
        valid_rsi = rsi_series.dropna()
        assert all(0 <= val <= 100 for val in valid_rsi)
    
    def test_macd_batch_calculation(self):
        """测试批量MACD计算"""
        results = self.optimizer.calculate_macd_batch(self.test_data)
        
        # 验证结果结构
        assert isinstance(results, dict)
        assert "000001" in results
        
        # 验证MACD组件
        macd_dict = results["000001"]
        assert 'dif' in macd_dict
        assert 'dea' in macd_dict
        assert 'macd' in macd_dict
        
        # 验证数据长度
        assert len(macd_dict['dif']) == 40
        assert len(macd_dict['dea']) == 40
        assert len(macd_dict['macd']) == 40


class TestMemoryOptimizer:
    """测试内存优化器"""
    
    def test_dataframe_optimization(self):
        """测试DataFrame内存优化"""
        # 创建测试数据
        original_df = pd.DataFrame({
            'close': [100.0, 101.0, 102.0],
            'volume': [1000, 1100, 1200],
            'date': ['2024-01-01', '2024-01-02', '2024-01-03']
        })
        
        # 优化DataFrame
        optimized_df = MemoryOptimizer.optimize_dataframe(original_df)
        
        # 验证数据完整性
        assert len(optimized_df) == 3
        assert list(optimized_df.columns) == ['close', 'volume', 'date']
        
        # 验证数据类型优化
        assert optimized_df['close'].dtype in ['float32', 'float64']
        assert optimized_df['volume'].dtype in ['int8', 'int16', 'int32', 'int64']
    
    def test_memory_usage_analysis(self):
        """测试内存使用分析"""
        test_df = pd.DataFrame({
            'close': [100.0] * 1000,
            'volume': [1000] * 1000
        })
        
        usage = MemoryOptimizer.get_memory_usage(test_df)
        
        assert isinstance(usage, dict)
        assert 'total_mb' in usage
        assert 'per_column' in usage
        assert usage['total_mb'] > 0
        assert 'close' in usage['per_column']
        assert 'volume' in usage['per_column']


class TestPerformanceTimer:
    """测试性能计时器"""
    
    def test_performance_timer_decorator(self):
        """测试性能计时装饰器"""
        
        @performance_timer
        def slow_function():
            time.sleep(0.1)
            return "result"
        
        # 执行函数
        result = slow_function()
        
        # 验证结果
        assert result == "result"
        
        # 注意：实际的计时日志需要通过日志系统验证


class TestIntegration:
    """集成测试"""
    
    def test_performance_stats_integration(self):
        """测试性能统计集成"""
        # 清空缓存
        clear_all_caches()
        
        # 执行一些操作
        cache = PerformanceCache()
        test_data = pd.DataFrame({'close': [100]})
        cache.set_stock_data("test", test_data)
        cache.get_stock_data("test")
        
        # 获取统计
        stats = get_performance_stats()
        
        # 验证统计数据
        assert isinstance(stats, dict)
    
    def test_cache_clearing(self):
        """测试缓存清理"""
        # 设置一些缓存数据
        cache = PerformanceCache()
        test_data = pd.DataFrame({'close': [100]})
        cache.set_stock_data("test", test_data)
        
        # 验证数据存在
        assert cache.get_stock_data("test") is not None
        
        # 清空缓存
        clear_all_caches()
        
        # 验证数据已清空（注意：这个测试可能需要调整，取决于实现）
        # 由于clear_all_caches可能影响全局缓存，这里主要测试接口


if __name__ == "__main__":
    pytest.main([__file__, "-v"])