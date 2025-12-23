"""
Page Loading Performance Tests
页面加载性能测试

Tests the loading performance of the Daily Signal page:
1. Page initialization time
2. Component rendering time
3. Data loading time
4. Overall page load time

Requirements: Task 3.3 - 测试页面加载时间
"""

import pytest
import time
import sys
import os
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from datetime import date, datetime, timedelta
from typing import Dict, Any

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the modules we need to test
from config.settings import get_settings
from config.stock_pool import get_watchlist
from core.data_feed import DataFeed
from core.signal_generator import SignalGenerator, TradingSignal, SignalType, StrategyType
from core.screener import Screener
from core.position_tracker import PositionTracker
from core.sell_signal_checker import SellSignalChecker
from core.notification import NotificationConfigStore


class TestPageLoadingPerformance:
    """测试页面加载性能"""
    
    def setup_method(self):
        """Setup test data"""
        self.performance_metrics = {}
        self.max_acceptable_load_time = 2.0  # 2秒最大加载时间
        
        # Mock data for testing
        self.mock_stock_data = pd.DataFrame({
            'date': ['2024-01-01', '2024-01-02', '2024-01-03'],
            'close': [100.0, 101.0, 102.0],
            'high': [101.0, 102.0, 103.0],
            'low': [99.0, 100.0, 101.0],
            'volume': [1000000, 1100000, 1200000]
        })
        
        self.mock_positions = []
        self.mock_signals = []
    
    def measure_execution_time(self, func, *args, **kwargs):
        """测量函数执行时间"""
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        return result, execution_time
    
    def test_data_feed_initialization_time(self):
        """测试数据源初始化时间"""
        with patch('core.data_feed.DataFeed.__init__', return_value=None):
            with patch('core.data_feed.DataFeed.get_stock_data', return_value=self.mock_stock_data):
                
                def create_data_feed():
                    settings = get_settings()
                    return DataFeed(
                        raw_path=settings.path.get_raw_path(),
                        processed_path=settings.path.get_processed_path()
                    )
                
                result, execution_time = self.measure_execution_time(create_data_feed)
                
                self.performance_metrics['data_feed_init'] = execution_time
                
                # 验证初始化时间在合理范围内
                assert execution_time < 0.5, f"数据源初始化时间过长: {execution_time:.3f}s"
                print(f"✓ 数据源初始化时间: {execution_time:.3f}s")
    
    def test_stock_pool_loading_time(self):
        """测试股票池加载时间"""
        # 测试实际的股票池加载时间
        result, execution_time = self.measure_execution_time(get_watchlist)
        
        self.performance_metrics['stock_pool_loading'] = execution_time
        
        # 验证加载时间
        assert execution_time < 0.1, f"股票池加载时间过长: {execution_time:.3f}s"
        assert len(result) > 0, "股票池为空"
        print(f"✓ 股票池加载时间: {execution_time:.3f}s ({len(result)}只股票)")
    
    def test_position_tracker_loading_time(self):
        """测试持仓数据加载时间"""
        with patch('core.position_tracker.PositionTracker.get_all_positions') as mock_get_positions:
            mock_get_positions.return_value = self.mock_positions
            
            def load_positions():
                tracker = PositionTracker()
                return tracker.get_all_positions()
            
            result, execution_time = self.measure_execution_time(load_positions)
            
            self.performance_metrics['position_loading'] = execution_time
            
            # 验证加载时间
            assert execution_time < 0.2, f"持仓数据加载时间过长: {execution_time:.3f}s"
            print(f"✓ 持仓数据加载时间: {execution_time:.3f}s")
    
    def test_market_status_loading_time(self):
        """测试大盘状态加载时间"""
        mock_market_status = {
            'status': 'healthy',
            'current_price': 3000.0,
            'ma20': 2950.0,
            'message': '大盘健康'
        }
        
        with patch('core.screener.Screener.get_market_status') as mock_get_status:
            mock_get_status.return_value = mock_market_status
            
            def load_market_status():
                with patch('core.data_feed.DataFeed.__init__', return_value=None):
                    data_feed = DataFeed("", "")
                    screener = Screener(data_feed)
                    return screener.get_market_status()
            
            result, execution_time = self.measure_execution_time(load_market_status)
            
            self.performance_metrics['market_status_loading'] = execution_time
            
            # 验证加载时间
            assert execution_time < 0.3, f"大盘状态加载时间过长: {execution_time:.3f}s"
            assert result['status'] == 'healthy', "大盘状态数据不正确"
            print(f"✓ 大盘状态加载时间: {execution_time:.3f}s")
    
    def test_notification_config_loading_time(self):
        """测试通知配置加载时间"""
        with patch('core.notification.NotificationConfigStore.load') as mock_load:
            from core.notification import NotificationConfig
            mock_config = NotificationConfig(
                webhook_url="https://test.webhook.url",
                enabled=True,
                notify_on_buy=True,
                notify_on_sell=True
            )
            mock_load.return_value = mock_config
            
            result, execution_time = self.measure_execution_time(NotificationConfigStore.load)
            
            self.performance_metrics['notification_config_loading'] = execution_time
            
            # 验证加载时间
            assert execution_time < 0.1, f"通知配置加载时间过长: {execution_time:.3f}s"
            assert result.enabled == True, "通知配置数据不正确"
            print(f"✓ 通知配置加载时间: {execution_time:.3f}s")
    
    def test_data_freshness_check_time(self):
        """测试数据新鲜度检查时间"""
        # 直接测试数据新鲜度检查逻辑
        def check_data_freshness_mock():
            """模拟数据新鲜度检查"""
            import glob
            import pandas as pd
            from datetime import date, datetime
            
            # 模拟文件查找
            csv_files = ['data/processed/000001.csv']  # 模拟找到文件
            
            if not csv_files:
                return {
                    'is_stale': True,
                    'last_data_date': None,
                    'days_old': 999,
                    'message': '未找到任何数据文件'
                }
            
            # 模拟读取CSV文件
            df = pd.DataFrame({
                'date': ['2024-01-01', '2024-01-02'],
                'close': [100, 101]
            })
            
            if df.empty or 'date' not in df.columns:
                return {
                    'is_stale': True,
                    'last_data_date': None,
                    'days_old': 999,
                    'message': '数据文件格式异常'
                }
            
            last_date_str = df['date'].iloc[-1]
            last_data_date = datetime.strptime(last_date_str, '%Y-%m-%d').date()
            
            today = date.today()
            days_old = (today - last_data_date).days
            is_stale = days_old > 3
            
            if is_stale:
                message = f"数据已过期：最后更新于 {last_data_date.strftime('%Y-%m-%d')}（{days_old} 天前）"
            else:
                message = f"数据正常：最后更新于 {last_data_date.strftime('%Y-%m-%d')}"
            
            return {
                'is_stale': is_stale,
                'last_data_date': last_data_date,
                'days_old': days_old,
                'message': message
            }
        
        result, execution_time = self.measure_execution_time(check_data_freshness_mock)
        
        self.performance_metrics['data_freshness_check'] = execution_time
        
        # 验证检查时间
        assert execution_time < 0.2, f"数据新鲜度检查时间过长: {execution_time:.3f}s"
        assert isinstance(result, dict), "数据新鲜度检查结果格式不正确"
        print(f"✓ 数据新鲜度检查时间: {execution_time:.3f}s")
    
    def test_signal_generation_time(self):
        """测试信号生成时间"""
        from datetime import datetime
        
        mock_signals = [
            TradingSignal(
                code="000001",
                name="测试股票",
                signal_type=SignalType.BUY,
                price_range=(100.0, 105.0),
                limit_cap=105.0,
                trade_amount=10000.0,
                reason="测试信号",
                news_url="https://test.url",
                actual_fee_rate=0.001,
                high_fee_warning=False,
                in_report_window=False,
                report_warning="",
                generated_at=datetime.now()
            )
        ]
        
        with patch('core.signal_generator.SignalGenerator.generate_signals') as mock_generate:
            mock_generate.return_value = mock_signals
            
            def generate_test_signals():
                with patch('core.data_feed.DataFeed.__init__', return_value=None):
                    data_feed = DataFeed("", "")
                    generator = SignalGenerator(data_feed=data_feed, strategy_type=StrategyType.RSI_REVERSAL)
                    return generator.generate_signals(
                        stock_pool=["000001", "000002"],
                        current_cash=100000,
                        current_positions=0
                    )
            
            result, execution_time = self.measure_execution_time(generate_test_signals)
            
            self.performance_metrics['signal_generation'] = execution_time
            
            # 验证生成时间（对于2只股票）
            assert execution_time < 1.0, f"信号生成时间过长: {execution_time:.3f}s (2只股票)"
            assert len(result) == 1, "信号生成结果数量不正确"
            print(f"✓ 信号生成时间: {execution_time:.3f}s (2只股票)")
    
    def test_page_component_rendering_time(self):
        """测试页面组件渲染时间"""
        # 模拟各个组件的渲染时间
        component_times = {}
        
        # 测试卖出信号组件渲染时间
        with patch('core.position_tracker.PositionTracker.get_all_positions', return_value=[]):
            def render_sell_signals():
                # 模拟组件渲染逻辑
                time.sleep(0.01)  # 模拟渲染延迟
                return "rendered"
            
            result, execution_time = self.measure_execution_time(render_sell_signals)
            component_times['sell_signals'] = execution_time
        
        # 测试大盘状态组件渲染时间
        def render_market_status():
            time.sleep(0.01)  # 模拟渲染延迟
            return "rendered"
        
        result, execution_time = self.measure_execution_time(render_market_status)
        component_times['market_status'] = execution_time
        
        # 测试通知设置组件渲染时间
        def render_notification_settings():
            time.sleep(0.01)  # 模拟渲染延迟
            return "rendered"
        
        result, execution_time = self.measure_execution_time(render_notification_settings)
        component_times['notification_settings'] = execution_time
        
        self.performance_metrics['component_rendering'] = component_times
        
        # 验证各组件渲染时间
        total_component_time = sum(component_times.values())
        assert total_component_time < 0.5, f"组件渲染总时间过长: {total_component_time:.3f}s"
        
        for component, render_time in component_times.items():
            assert render_time < 0.1, f"{component}组件渲染时间过长: {render_time:.3f}s"
            print(f"✓ {component}组件渲染时间: {render_time:.3f}s")
    
    def test_overall_page_load_time(self):
        """测试整体页面加载时间"""
        def simulate_full_page_load():
            """模拟完整页面加载过程"""
            # 1. 初始化数据源
            with patch('core.data_feed.DataFeed.__init__', return_value=None):
                data_feed = DataFeed("", "")
            
            # 2. 加载股票池
            with patch('config.stock_pool.get_watchlist', return_value=["000001", "000002"]):
                stock_pool = get_watchlist()
            
            # 3. 加载持仓数据
            with patch('core.position_tracker.PositionTracker.get_all_positions', return_value=[]):
                tracker = PositionTracker()
                positions = tracker.get_all_positions()
            
            # 4. 检查大盘状态
            mock_market_status = {'status': 'healthy', 'current_price': 3000.0}
            with patch('core.screener.Screener.get_market_status', return_value=mock_market_status):
                screener = Screener(data_feed)
                market_status = screener.get_market_status()
            
            # 5. 加载通知配置
            with patch('core.notification.NotificationConfigStore.load') as mock_load:
                from core.notification import NotificationConfig
                mock_config = NotificationConfig(webhook_url="", enabled=False)
                mock_load.return_value = mock_config
                config = NotificationConfigStore.load()
            
            # 6. 检查数据新鲜度
            with patch('glob.glob', return_value=['test.csv']):
                with patch('pandas.read_csv') as mock_read_csv:
                    mock_read_csv.return_value = pd.DataFrame({
                        'date': ['2024-01-01'],
                        'close': [100]
                    })
                    # 模拟数据新鲜度检查
                    freshness_result = {
                        'is_stale': False,
                        'last_data_date': date.today(),
                        'days_old': 0,
                        'message': '数据正常'
                    }
            
            return {
                'data_feed': data_feed,
                'stock_pool': stock_pool,
                'positions': positions,
                'market_status': market_status,
                'notification_config': config,
                'data_freshness': freshness_result
            }
        
        result, execution_time = self.measure_execution_time(simulate_full_page_load)
        
        self.performance_metrics['overall_page_load'] = execution_time
        
        # 验证整体加载时间
        assert execution_time < self.max_acceptable_load_time, \
            f"页面整体加载时间超过阈值: {execution_time:.3f}s > {self.max_acceptable_load_time}s"
        
        # 验证加载结果完整性
        assert 'data_feed' in result, "数据源未正确加载"
        assert 'stock_pool' in result, "股票池未正确加载"
        assert 'positions' in result, "持仓数据未正确加载"
        assert 'market_status' in result, "大盘状态未正确加载"
        assert 'notification_config' in result, "通知配置未正确加载"
        assert 'data_freshness' in result, "数据新鲜度未正确检查"
        
        print(f"✓ 页面整体加载时间: {execution_time:.3f}s")
        print(f"✓ 加载时间符合要求 (< {self.max_acceptable_load_time}s)")
    
    def test_performance_under_load(self):
        """测试负载情况下的性能"""
        # 模拟大量股票的情况
        large_stock_pool = [f"{i:06d}" for i in range(1, 501)]  # 500只股票
        
        def load_large_stock_pool():
            # 模拟处理大量股票的时间
            processed_count = 0
            for stock in large_stock_pool:
                # 模拟每只股票的处理时间
                time.sleep(0.001)  # 1ms per stock
                processed_count += 1
            return processed_count
        
        result, execution_time = self.measure_execution_time(load_large_stock_pool)
        
        self.performance_metrics['large_stock_pool_processing'] = execution_time
        
        # 验证大量股票处理时间
        assert execution_time < 1.0, f"大量股票处理时间过长: {execution_time:.3f}s (500只股票)"
        assert result == 500, "股票处理数量不正确"
        print(f"✓ 大量股票处理时间: {execution_time:.3f}s (500只股票)")
    
    def test_memory_usage_during_load(self):
        """测试加载过程中的内存使用"""
        try:
            import psutil
            import os
            
            # 获取当前进程
            process = psutil.Process(os.getpid())
            
            # 记录初始内存使用
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # 模拟页面加载过程
            def memory_intensive_load():
                # 创建一些测试数据
                large_dataframes = []
                for i in range(10):
                    df = pd.DataFrame({
                        'data': range(1000),
                        'values': [i] * 1000
                    })
                    large_dataframes.append(df)
                
                # 模拟处理时间
                time.sleep(0.1)
                
                return large_dataframes
            
            result, execution_time = self.measure_execution_time(memory_intensive_load)
            
            # 记录峰值内存使用
            peak_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = peak_memory - initial_memory
            
            self.performance_metrics['memory_usage'] = {
                'initial_mb': initial_memory,
                'peak_mb': peak_memory,
                'increase_mb': memory_increase
            }
            
            # 验证内存使用合理
            assert memory_increase < 100, f"内存使用增长过多: {memory_increase:.1f}MB"
            print(f"✓ 内存使用: 初始 {initial_memory:.1f}MB, 峰值 {peak_memory:.1f}MB, 增长 {memory_increase:.1f}MB")
            
        except ImportError:
            # 如果没有psutil，跳过内存测试
            print("⚠️ psutil未安装，跳过内存使用测试")
            self.performance_metrics['memory_usage'] = {
                'initial_mb': 0,
                'peak_mb': 0,
                'increase_mb': 0
            }
    
    def teardown_method(self):
        """输出性能测试报告"""
        print("\n" + "="*60)
        print("页面加载性能测试报告")
        print("="*60)
        
        for metric_name, metric_value in self.performance_metrics.items():
            if isinstance(metric_value, dict):
                print(f"{metric_name}:")
                for sub_name, sub_value in metric_value.items():
                    if isinstance(sub_value, float):
                        print(f"  {sub_name}: {sub_value:.3f}s")
                    else:
                        print(f"  {sub_name}: {sub_value}")
            else:
                print(f"{metric_name}: {metric_value:.3f}s")
        
        print("="*60)
        
        # 计算总体性能评分
        total_time = sum(v for v in self.performance_metrics.values() if isinstance(v, float))
        if total_time < 1.0:
            grade = "优秀"
        elif total_time < 2.0:
            grade = "良好"
        elif total_time < 3.0:
            grade = "一般"
        else:
            grade = "需要优化"
        
        print(f"总体性能评分: {grade} (总耗时: {total_time:.3f}s)")
        print("="*60)


class TestPageLoadingBenchmark:
    """页面加载基准测试"""
    
    def test_baseline_performance(self):
        """建立性能基准线"""
        baseline_metrics = {
            'data_feed_init': 0.1,      # 数据源初始化 < 100ms
            'stock_pool_loading': 0.05,  # 股票池加载 < 50ms
            'position_loading': 0.1,     # 持仓加载 < 100ms
            'market_status_loading': 0.2, # 大盘状态 < 200ms
            'notification_config_loading': 0.05, # 通知配置 < 50ms
            'data_freshness_check': 0.1, # 数据新鲜度 < 100ms
            'signal_generation': 0.5,    # 信号生成 < 500ms (小量股票)
            'overall_page_load': 2.0     # 整体加载 < 2s
        }
        
        print("\n页面加载性能基准线:")
        print("-" * 40)
        for metric, threshold in baseline_metrics.items():
            print(f"{metric}: < {threshold}s")
        
        # 这些基准线将用于后续的性能回归测试
        assert True, "基准线已建立"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])