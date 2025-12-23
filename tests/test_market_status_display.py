"""
测试大盘状态显示功能

测试 render_market_status_compact() 函数的 Streamlit UI 组件调用：
- 测试 Streamlit 组件的正确调用
- 测试不同大盘状态下的 UI 渲染
- 测试异常情况的处理

Requirements: 测试大盘状态显示
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import date

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock streamlit before importing the module
sys.modules['streamlit'] = Mock()

# 导入要测试的模块
import importlib.util

# 动态导入包含数字的模块
spec = importlib.util.spec_from_file_location(
    "daily_signal_module", 
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "pages", "3_Daily_Signal.py")
)
daily_signal_module = importlib.util.module_from_spec(spec)
sys.modules["daily_signal_module"] = daily_signal_module
spec.loader.exec_module(daily_signal_module)

from core.data_feed import DataFeed
from core.screener import Screener


class TestMarketStatusDisplayHealthy:
    """测试大盘健康状态的显示"""
    
    def test_render_market_status_compact_healthy(self):
        """测试大盘健康状态的紧凑显示"""
        with patch.object(daily_signal_module, 'get_data_feed') as mock_get_data_feed, \
             patch.object(daily_signal_module, 'Screener') as mock_screener_class, \
             patch('streamlit.markdown') as mock_markdown, \
             patch('streamlit.success') as mock_success, \
             patch('streamlit.metric') as mock_metric:
            
            # 模拟数据
            mock_data_feed = Mock(spec=DataFeed)
            mock_get_data_feed.return_value = mock_data_feed
            
            mock_screener = Mock()
            mock_screener.market_filter = Mock()
            mock_screener.market_filter.ma_period = 20
            mock_screener.get_market_status.return_value = {
                'status': 'healthy',
                'current_price': 3500.50,
                'ma20': 3450.25,
                'message': '大盘环境健康'
            }
            mock_screener_class.return_value = mock_screener
            
            # 执行函数
            daily_signal_module.render_market_status_compact()
            
            # 验证调用
            mock_markdown.assert_called_with("#### 📊 大盘状态")
            mock_success.assert_called_with("✅ 大盘健康，允许交易")
            mock_metric.assert_called_with(
                "沪深300", 
                "3500.50",
                delta="MA20: 3450.25"
            )
            
            # 验证数据获取
            mock_get_data_feed.assert_called_once()
            mock_screener_class.assert_called_once_with(mock_data_feed)
            mock_screener.get_market_status.assert_called_once()


class TestMarketStatusDisplayUnhealthy:
    """测试大盘不健康状态的显示"""
    
    def test_render_market_status_compact_unhealthy(self):
        """测试大盘不健康状态的紧凑显示"""
        with patch.object(daily_signal_module, 'get_data_feed') as mock_get_data_feed, \
             patch.object(daily_signal_module, 'Screener') as mock_screener_class, \
             patch('streamlit.markdown') as mock_markdown, \
             patch('streamlit.error') as mock_error, \
             patch('streamlit.metric') as mock_metric, \
             patch('streamlit.caption') as mock_caption:
            
            # 模拟数据
            mock_data_feed = Mock(spec=DataFeed)
            mock_get_data_feed.return_value = mock_data_feed
            
            mock_screener = Mock()
            mock_screener.market_filter = Mock()
            mock_screener.market_filter.ma_period = 20
            mock_screener.get_market_status.return_value = {
                'status': 'unhealthy',
                'current_price': 3400.25,
                'ma20': 3450.50,
                'message': '大盘滤网生效，建议空仓观望'
            }
            mock_screener_class.return_value = mock_screener
            
            # 执行函数
            daily_signal_module.render_market_status_compact()
            
            # 验证调用
            mock_markdown.assert_called_with("#### 📊 大盘状态")
            mock_error.assert_called_with("⚠️ 大盘滤网生效，建议空仓")
            mock_metric.assert_called_with(
                "沪深300", 
                "3400.25",
                delta="< MA20",
                delta_color="inverse"
            )
            mock_caption.assert_called_with('大盘滤网生效，建议空仓观望')
            
            # 验证数据获取
            mock_get_data_feed.assert_called_once()
            mock_screener_class.assert_called_once_with(mock_data_feed)
            mock_screener.get_market_status.assert_called_once()


class TestMarketStatusDisplayUnknown:
    """测试大盘未知状态的显示"""
    
    def test_render_market_status_compact_unknown(self):
        """测试大盘未知状态的紧凑显示"""
        with patch.object(daily_signal_module, 'get_data_feed') as mock_get_data_feed, \
             patch.object(daily_signal_module, 'Screener') as mock_screener_class, \
             patch('streamlit.markdown') as mock_markdown, \
             patch('streamlit.warning') as mock_warning:
            
            # 模拟数据
            mock_data_feed = Mock(spec=DataFeed)
            mock_get_data_feed.return_value = mock_data_feed
            
            mock_screener = Mock()
            mock_screener.get_market_status.return_value = {
                'status': 'unknown',
                'message': '无法获取大盘数据'
            }
            mock_screener_class.return_value = mock_screener
            
            # 执行函数
            daily_signal_module.render_market_status_compact()
            
            # 验证调用
            mock_markdown.assert_called_with("#### 📊 大盘状态")
            mock_warning.assert_called_with("大盘状态: 无法获取大盘数据")
            
            # 验证数据获取
            mock_get_data_feed.assert_called_once()
            mock_screener_class.assert_called_once_with(mock_data_feed)
            mock_screener.get_market_status.assert_called_once()


class TestMarketStatusDisplayException:
    """测试大盘状态显示异常处理"""
    
    def test_render_market_status_compact_exception(self):
        """测试大盘状态显示异常处理"""
        with patch.object(daily_signal_module, 'get_data_feed') as mock_get_data_feed, \
             patch.object(daily_signal_module, 'Screener') as mock_screener_class, \
             patch('streamlit.markdown') as mock_markdown, \
             patch('streamlit.warning') as mock_warning:
            
            # 模拟数据
            mock_data_feed = Mock(spec=DataFeed)
            mock_get_data_feed.return_value = mock_data_feed
            
            # 模拟异常
            mock_screener = Mock()
            mock_screener.get_market_status.side_effect = Exception("网络连接失败")
            mock_screener_class.return_value = mock_screener
            
            # 执行函数
            daily_signal_module.render_market_status_compact()
            
            # 验证调用
            mock_markdown.assert_called_with("#### 📊 大盘状态")
            mock_warning.assert_called_with("无法获取大盘状态: 网络连接失败")
            
            # 验证数据获取
            mock_get_data_feed.assert_called_once()
            mock_screener_class.assert_called_once_with(mock_data_feed)
            mock_screener.get_market_status.assert_called_once()


class TestMarketStatusDisplayDataFeedException:
    """测试数据源异常处理"""
    
    def test_render_market_status_compact_data_feed_exception(self):
        """测试数据源异常处理"""
        with patch.object(daily_signal_module, 'get_data_feed') as mock_get_data_feed, \
             patch('streamlit.markdown') as mock_markdown, \
             patch('streamlit.warning') as mock_warning:
            
            # 模拟数据源异常
            mock_get_data_feed.side_effect = Exception("数据源初始化失败")
            
            # 执行函数
            daily_signal_module.render_market_status_compact()
            
            # 验证调用
            mock_markdown.assert_called_with("#### 📊 大盘状态")
            mock_warning.assert_called_with("无法获取大盘状态: 数据源初始化失败")
            
            # 验证数据获取
            mock_get_data_feed.assert_called_once()


class TestMarketStatusDisplayEdgeCases:
    """测试边界情况"""
    
    def test_render_market_status_compact_zero_prices(self):
        """测试价格为零的边界情况"""
        with patch.object(daily_signal_module, 'get_data_feed') as mock_get_data_feed, \
             patch.object(daily_signal_module, 'Screener') as mock_screener_class, \
             patch('streamlit.markdown') as mock_markdown, \
             patch('streamlit.success') as mock_success, \
             patch('streamlit.metric') as mock_metric:
            
            # 模拟数据
            mock_data_feed = Mock(spec=DataFeed)
            mock_get_data_feed.return_value = mock_data_feed
            
            mock_screener = Mock()
            mock_screener.market_filter = Mock()
            mock_screener.market_filter.ma_period = 20
            mock_screener.get_market_status.return_value = {
                'status': 'healthy',
                'current_price': 0.0,
                'ma20': 0.0,
                'message': '测试零价格'
            }
            mock_screener_class.return_value = mock_screener
            
            # 执行函数
            daily_signal_module.render_market_status_compact()
            
            # 验证调用
            mock_markdown.assert_called_with("#### 📊 大盘状态")
            mock_success.assert_called_with("✅ 大盘健康，允许交易")
            mock_metric.assert_called_with(
                "沪深300", 
                "0.00",
                delta="MA20: 0.00"
            )
    
    def test_render_market_status_compact_missing_ma_period(self):
        """测试缺少 MA 周期的情况"""
        with patch.object(daily_signal_module, 'get_data_feed') as mock_get_data_feed, \
             patch.object(daily_signal_module, 'Screener') as mock_screener_class, \
             patch('streamlit.markdown') as mock_markdown, \
             patch('streamlit.warning') as mock_warning:
            
            # 模拟数据
            mock_data_feed = Mock(spec=DataFeed)
            mock_get_data_feed.return_value = mock_data_feed
            
            mock_screener = Mock()
            # 不设置 market_filter.ma_period，模拟缺少属性的情况
            mock_screener.market_filter = Mock()
            # 模拟访问 ma_period 时抛出 AttributeError
            type(mock_screener.market_filter).ma_period = Mock(side_effect=AttributeError("no attribute 'ma_period'"))
            mock_screener.get_market_status.return_value = {
                'status': 'healthy',
                'current_price': 3500.50,
                'ma20': 3450.25,
                'message': '大盘环境健康'
            }
            mock_screener_class.return_value = mock_screener
            
            # 执行函数
            daily_signal_module.render_market_status_compact()
            
            # 验证调用
            mock_markdown.assert_called_with("#### 📊 大盘状态")
            # 由于 AttributeError，应该显示警告
            mock_warning.assert_called_once()
            # 检查警告消息包含预期内容
            warning_call_args = mock_warning.call_args[0][0]
            assert "无法获取大盘状态" in warning_call_args


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])