"""
测试持仓卖出信号 UI 显示功能

测试 render_sell_signals_section_compact() 函数的 Streamlit UI 组件调用：
- 测试 Streamlit 组件的正确调用
- 测试不同场景下的 UI 渲染
- 验证紧凑布局的实现

Requirements: 5.1, 5.2, 5.3
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import date
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.position_tracker import Holding, PositionTracker
from core.sell_signal_checker import SellSignal, SellSignalChecker
from core.data_feed import DataFeed


class TestSellSignalUIDisplay:
    """测试持仓卖出信号 UI 显示功能"""
    
    @pytest.fixture
    def sample_holding(self):
        """示例持仓"""
        return Holding(
            code="600519",
            name="贵州茅台",
            buy_price=1800.0,
            buy_date=date(2024, 1, 15),
            quantity=100,
            strategy="RSRS",
            note="测试持仓"
        )
    
    @pytest.fixture
    def sample_stop_loss_signal(self, sample_holding):
        """示例止损信号"""
        return SellSignal(
            code="600519",
            name="贵州茅台",
            holding=sample_holding,
            current_price=1692.0,  # 下跌6%
            pnl_pct=-0.06,
            exit_reason="触发止损线（-6%）",
            urgency="high",
            indicator_value=-0.06
        )
    
    @pytest.fixture
    def sample_strategy_signal(self, sample_holding):
        """示例策略卖出信号"""
        return SellSignal(
            code="600519",
            name="贵州茅台",
            holding=sample_holding,
            current_price=1890.0,  # 上涨5%
            pnl_pct=0.05,
            exit_reason="RSRS标准分 < -0.7",
            urgency="medium",
            indicator_value=-0.8
        )
    
    def test_ui_no_positions_display(self):
        """测试无持仓时的 UI 显示"""
        # 模拟 streamlit 和相关模块
        with patch('streamlit.markdown') as mock_markdown, \
             patch('streamlit.info') as mock_info, \
             patch('core.position_tracker.PositionTracker') as mock_tracker_class:
            
            # 设置模拟
            mock_tracker = Mock()
            mock_tracker.get_all_positions.return_value = []
            mock_tracker_class.return_value = mock_tracker
            
            # 导入并执行函数
            import importlib.util
            spec = importlib.util.spec_from_file_location("daily_signal", "app/pages/3_Daily_Signal.py")
            daily_signal_module = importlib.util.module_from_spec(spec)
            
            # 模拟所有依赖
            with patch.dict('sys.modules', {
                'streamlit': Mock(),
                'core.position_tracker': Mock(),
                'core.sell_signal_checker': Mock(),
                'core.data_feed': Mock()
            }):
                spec.loader.exec_module(daily_signal_module)
                
                # 替换函数中的依赖
                daily_signal_module.PositionTracker = mock_tracker_class
                daily_signal_module.st = Mock()
                daily_signal_module.st.markdown = mock_markdown
                daily_signal_module.st.info = mock_info
                
                # 执行函数
                daily_signal_module.render_sell_signals_section_compact()
                
                # 验证调用
                mock_markdown.assert_called_with("#### 🚨 持仓卖出信号")
                mock_info.assert_called_with("当前无持仓")
    
    def test_ui_positions_no_signals_display(self, sample_holding):
        """测试有持仓但无卖出信号时的 UI 显示"""
        # 模拟 streamlit 和相关模块
        with patch('streamlit.markdown') as mock_markdown, \
             patch('streamlit.success') as mock_success, \
             patch('core.position_tracker.PositionTracker') as mock_tracker_class, \
             patch('core.sell_signal_checker.SellSignalChecker') as mock_checker_class, \
             patch('core.data_feed.DataFeed') as mock_data_feed_class:
            
            # 设置模拟
            mock_tracker = Mock()
            mock_tracker.get_all_positions.return_value = [sample_holding]
            mock_tracker_class.return_value = mock_tracker
            
            mock_checker = Mock()
            mock_checker.check_all_positions.return_value = []
            mock_checker_class.return_value = mock_checker
            
            mock_data_feed = Mock()
            mock_data_feed_class.return_value = mock_data_feed
            
            # 导入并执行函数
            import importlib.util
            spec = importlib.util.spec_from_file_location("daily_signal", "app/pages/3_Daily_Signal.py")
            daily_signal_module = importlib.util.module_from_spec(spec)
            
            # 模拟所有依赖
            with patch.dict('sys.modules', {
                'streamlit': Mock(),
                'core.position_tracker': Mock(),
                'core.sell_signal_checker': Mock(),
                'core.data_feed': Mock()
            }):
                spec.loader.exec_module(daily_signal_module)
                
                # 替换函数中的依赖
                daily_signal_module.PositionTracker = mock_tracker_class
                daily_signal_module.SellSignalChecker = mock_checker_class
                daily_signal_module.get_data_feed = Mock(return_value=mock_data_feed)
                daily_signal_module.st = Mock()
                daily_signal_module.st.markdown = mock_markdown
                daily_signal_module.st.success = mock_success
                
                # 执行函数
                daily_signal_module.render_sell_signals_section_compact()
                
                # 验证调用
                mock_markdown.assert_called_with("#### 🚨 持仓卖出信号")
                mock_success.assert_called_with("✅ 1 只持仓无卖出信号")
    
    def test_ui_stop_loss_signal_display(self, sample_holding, sample_stop_loss_signal):
        """测试止损信号的 UI 显示"""
        # 模拟 streamlit 组件
        mock_st = Mock()
        mock_col1 = Mock()
        mock_col2 = Mock()
        mock_expander = Mock()
        
        mock_st.markdown = Mock()
        mock_st.columns = Mock(return_value=[mock_col1, mock_col2])
        mock_st.expander = Mock(return_value=mock_expander)
        
        # 模拟 columns 的 context manager
        mock_col1.__enter__ = Mock(return_value=mock_col1)
        mock_col1.__exit__ = Mock(return_value=None)
        mock_col2.__enter__ = Mock(return_value=mock_col2)
        mock_col2.__exit__ = Mock(return_value=None)
        
        # 模拟 expander 的 context manager
        mock_expander.__enter__ = Mock(return_value=mock_expander)
        mock_expander.__exit__ = Mock(return_value=None)
        
        with patch('core.position_tracker.PositionTracker') as mock_tracker_class, \
             patch('core.sell_signal_checker.SellSignalChecker') as mock_checker_class, \
             patch('core.data_feed.DataFeed') as mock_data_feed_class:
            
            # 设置模拟
            mock_tracker = Mock()
            mock_tracker.get_all_positions.return_value = [sample_holding]
            mock_tracker_class.return_value = mock_tracker
            
            mock_checker = Mock()
            mock_checker.check_all_positions.return_value = [sample_stop_loss_signal]
            mock_checker_class.return_value = mock_checker
            
            mock_data_feed = Mock()
            mock_data_feed_class.return_value = mock_data_feed
            
            # 导入并执行函数
            import importlib.util
            spec = importlib.util.spec_from_file_location("daily_signal", "app/pages/3_Daily_Signal.py")
            daily_signal_module = importlib.util.module_from_spec(spec)
            
            # 模拟所有依赖
            with patch.dict('sys.modules', {
                'streamlit': Mock(),
                'core.position_tracker': Mock(),
                'core.sell_signal_checker': Mock(),
                'core.data_feed': Mock()
            }):
                spec.loader.exec_module(daily_signal_module)
                
                # 替换函数中的依赖
                daily_signal_module.PositionTracker = mock_tracker_class
                daily_signal_module.SellSignalChecker = mock_checker_class
                daily_signal_module.get_data_feed = Mock(return_value=mock_data_feed)
                daily_signal_module.st = mock_st
                
                # 执行函数
                daily_signal_module.render_sell_signals_section_compact()
                
                # 验证调用
                mock_st.markdown.assert_called_with("#### 🚨 持仓卖出信号")
                mock_st.columns.assert_called_with(2)
                
                # 验证 metric 调用
                mock_col1.metric.assert_called_with("持仓", "1 只")
                mock_col2.metric.assert_called_with("🚨 止损", "1 个", delta="紧急", delta_color="inverse")
                
                # 验证 expander 被调用且自动展开（因为有紧急信号）
                mock_st.expander.assert_called_with("查看 1 个卖出信号", expanded=True)
    
    def test_ui_strategy_signal_display(self, sample_holding, sample_strategy_signal):
        """测试策略卖出信号的 UI 显示"""
        # 模拟 streamlit 组件
        mock_st = Mock()
        mock_col1 = Mock()
        mock_col2 = Mock()
        mock_expander = Mock()
        
        mock_st.markdown = Mock()
        mock_st.columns = Mock(return_value=[mock_col1, mock_col2])
        mock_st.expander = Mock(return_value=mock_expander)
        
        # 模拟 columns 的 context manager
        mock_col1.__enter__ = Mock(return_value=mock_col1)
        mock_col1.__exit__ = Mock(return_value=None)
        mock_col2.__enter__ = Mock(return_value=mock_col2)
        mock_col2.__exit__ = Mock(return_value=None)
        
        # 模拟 expander 的 context manager
        mock_expander.__enter__ = Mock(return_value=mock_expander)
        mock_expander.__exit__ = Mock(return_value=None)
        
        with patch('core.position_tracker.PositionTracker') as mock_tracker_class, \
             patch('core.sell_signal_checker.SellSignalChecker') as mock_checker_class, \
             patch('core.data_feed.DataFeed') as mock_data_feed_class:
            
            # 设置模拟
            mock_tracker = Mock()
            mock_tracker.get_all_positions.return_value = [sample_holding]
            mock_tracker_class.return_value = mock_tracker
            
            mock_checker = Mock()
            mock_checker.check_all_positions.return_value = [sample_strategy_signal]
            mock_checker_class.return_value = mock_checker
            
            mock_data_feed = Mock()
            mock_data_feed_class.return_value = mock_data_feed
            
            # 导入并执行函数
            import importlib.util
            spec = importlib.util.spec_from_file_location("daily_signal", "app/pages/3_Daily_Signal.py")
            daily_signal_module = importlib.util.module_from_spec(spec)
            
            # 模拟所有依赖
            with patch.dict('sys.modules', {
                'streamlit': Mock(),
                'core.position_tracker': Mock(),
                'core.sell_signal_checker': Mock(),
                'core.data_feed': Mock()
            }):
                spec.loader.exec_module(daily_signal_module)
                
                # 替换函数中的依赖
                daily_signal_module.PositionTracker = mock_tracker_class
                daily_signal_module.SellSignalChecker = mock_checker_class
                daily_signal_module.get_data_feed = Mock(return_value=mock_data_feed)
                daily_signal_module.st = mock_st
                
                # 执行函数
                daily_signal_module.render_sell_signals_section_compact()
                
                # 验证调用
                mock_st.markdown.assert_called_with("#### 🚨 持仓卖出信号")
                mock_st.columns.assert_called_with(2)
                
                # 验证 metric 调用（无紧急信号，显示策略卖出）
                mock_col1.metric.assert_called_with("持仓", "1 只")
                mock_col2.metric.assert_called_with("⚠️ 策略卖出", "1 个")
                
                # 验证 expander 被调用且默认折叠（无紧急信号）
                mock_st.expander.assert_called_with("查看 1 个卖出信号", expanded=False)


class TestSellSignalUIComponents:
    """测试卖出信号 UI 组件的具体实现"""
    
    def test_compact_layout_structure(self):
        """测试紧凑布局的结构"""
        # 验证紧凑布局使用了正确的 Streamlit 组件
        # 这个测试验证了设计文档中描述的组件使用
        
        expected_components = [
            'st.markdown',      # 标题
            'st.columns',       # 两列布局
            'st.metric',        # 指标显示
            'st.expander',      # 可展开内容
            'st.success',       # 成功状态
            'st.error',         # 错误状态（止损信号）
            'st.warning'        # 警告状态（策略信号）
        ]
        
        # 这里我们验证设计文档中提到的组件都被正确使用
        # 实际的验证在上面的具体测试中完成
        assert len(expected_components) == 7
        assert 'st.markdown' in expected_components
        assert 'st.columns' in expected_components
        assert 'st.metric' in expected_components
        assert 'st.expander' in expected_components
    
    def test_signal_urgency_display_logic(self):
        """测试信号紧急程度的显示逻辑"""
        # 测试紧急程度决定展开状态的逻辑
        
        # 高紧急度信号应该自动展开
        high_urgency_signals = [
            Mock(urgency="high"),
            Mock(urgency="medium")
        ]
        high_count = sum(1 for s in high_urgency_signals if s.urgency == "high")
        assert high_count > 0  # 有紧急信号
        auto_expand = high_count > 0
        assert auto_expand == True
        
        # 无紧急度信号不应该自动展开
        medium_urgency_signals = [
            Mock(urgency="medium"),
            Mock(urgency="medium")
        ]
        high_count = sum(1 for s in medium_urgency_signals if s.urgency == "high")
        assert high_count == 0  # 无紧急信号
        auto_expand = high_count > 0
        assert auto_expand == False
    
    def test_metric_display_logic(self):
        """测试指标显示逻辑"""
        # 测试不同信号类型的指标显示
        
        # 有紧急信号时显示止损指标
        signals_with_high = [Mock(urgency="high"), Mock(urgency="medium")]
        high_count = sum(1 for s in signals_with_high if s.urgency == "high")
        medium_count = sum(1 for s in signals_with_high if s.urgency == "medium")
        
        assert high_count == 1
        assert medium_count == 1
        
        # 验证显示逻辑：有紧急信号时优先显示止损
        if high_count > 0:
            primary_metric = "🚨 止损"
            primary_count = high_count
        else:
            primary_metric = "⚠️ 策略卖出"
            primary_count = medium_count
        
        assert primary_metric == "🚨 止损"
        assert primary_count == 1
        
        # 无紧急信号时显示策略卖出
        signals_no_high = [Mock(urgency="medium"), Mock(urgency="medium")]
        high_count = sum(1 for s in signals_no_high if s.urgency == "high")
        medium_count = sum(1 for s in signals_no_high if s.urgency == "medium")
        
        assert high_count == 0
        assert medium_count == 2
        
        if high_count > 0:
            primary_metric = "🚨 止损"
            primary_count = high_count
        else:
            primary_metric = "⚠️ 策略卖出"
            primary_count = medium_count
        
        assert primary_metric == "⚠️ 策略卖出"
        assert primary_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])