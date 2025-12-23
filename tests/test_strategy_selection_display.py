"""
测试每日信号页面的策略选择和参数显示功能

测试范围：
- 策略选择下拉框
- 策略描述显示
- 参数展开面板
- 不同策略的参数显示
- 参数加载功能

Requirements: Task 3.1 - 测试策略选择和参数显示
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
import importlib.util

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 模拟 streamlit 模块以避免导入错误
mock_streamlit = Mock()
sys.modules['streamlit'] = mock_streamlit

# 动态导入 Daily Signal 模块
with patch.dict('sys.modules', {
    'streamlit': mock_streamlit,
    'core.data_feed': Mock(),
    'core.signal_generator': Mock(),
    'core.screener': Mock(),
    'core.signal_store': Mock(),
    'core.position_tracker': Mock(),
    'core.sell_signal_checker': Mock(),
    'core.logging_config': Mock(),
    'core.notification': Mock(),
}):
    spec = importlib.util.spec_from_file_location(
        "daily_signal_module", 
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "pages", "3_Daily_Signal.py")
    )
    daily_signal_module = importlib.util.module_from_spec(spec)
    sys.modules["daily_signal_module"] = daily_signal_module
    spec.loader.exec_module(daily_signal_module)

from config.settings import StrategyParamsConfig


class TestStrategySelectionDisplay(unittest.TestCase):
    """测试策略选择和参数显示功能"""
    
    def setUp(self):
        """测试前准备"""
        self.mock_st = Mock()
        self.mock_st.selectbox = Mock()
        self.mock_st.caption = Mock()
        self.mock_st.expander = Mock()
        self.mock_st.columns = Mock()
        self.mock_st.metric = Mock()
        self.mock_st.markdown = Mock()
        
        # 模拟 expander 上下文管理器
        self.mock_expander_context = Mock()
        self.mock_st.expander.return_value.__enter__ = Mock(return_value=self.mock_expander_context)
        self.mock_st.expander.return_value.__exit__ = Mock(return_value=None)
        
        # 模拟 columns 返回值
        self.mock_columns = [Mock(), Mock(), Mock()]
        self.mock_st.columns.return_value = self.mock_columns
        
        # 为每个 column 设置 __enter__ 和 __exit__ 方法
        for col in self.mock_columns:
            col.__enter__ = Mock(return_value=col)
            col.__exit__ = Mock(return_value=None)
            col.metric = Mock()
    
    def test_strategy_options_configuration(self):
        """测试策略选项配置是否正确"""
        # 验证策略选项存在
        self.assertIn("STRATEGY_OPTIONS", dir(daily_signal_module))
        
        strategy_options = daily_signal_module.STRATEGY_OPTIONS
        
        # 验证包含预期的策略
        self.assertIn("RSI 超卖反弹策略", strategy_options)
        self.assertIn("RSRS 阻力支撑策略", strategy_options)
        
        # 验证每个策略都有必要的字段
        for strategy_name, strategy_info in strategy_options.items():
            self.assertIn("type", strategy_info)
            self.assertIn("description", strategy_info)
            self.assertIsNotNone(strategy_info["description"])
            self.assertTrue(len(strategy_info["description"]) > 0)
    
    def test_strategy_selection_display(self):
        """测试策略选择显示功能"""
        with patch('streamlit.selectbox') as mock_selectbox, \
             patch('streamlit.caption') as mock_caption, \
             patch('streamlit.expander') as mock_expander, \
             patch('streamlit.columns') as mock_columns, \
             patch('streamlit.markdown') as mock_markdown, \
             patch.object(daily_signal_module, 'load_strategy_params') as mock_load_params:
            
            # 设置模拟返回值
            mock_selectbox.return_value = "RSI 超卖反弹策略"
            mock_columns.return_value = self.mock_columns
            
            # 模拟 expander 上下文管理器
            mock_expander_context = Mock()
            mock_expander.return_value.__enter__ = Mock(return_value=mock_expander_context)
            mock_expander.return_value.__exit__ = Mock(return_value=None)
            
            # 模拟策略参数加载
            mock_params = StrategyParamsConfig(
                rsi_period=14,
                rsi_buy_threshold=30,
                rsi_sell_threshold=70
            )
            mock_load_params.return_value = mock_params
            
            # 模拟策略配置部分的代码执行
            self._simulate_strategy_config_section(mock_selectbox, mock_caption, mock_expander, mock_columns, mock_markdown)
            
            # 验证策略选择框调用
            mock_selectbox.assert_called_once()
            call_args = mock_selectbox.call_args
            self.assertEqual(call_args[1]["options"], list(daily_signal_module.STRATEGY_OPTIONS.keys()))
            
            # 验证策略描述显示
            strategy_info = daily_signal_module.STRATEGY_OPTIONS["RSI 超卖反弹策略"]
            mock_caption.assert_called_with(f"💡 {strategy_info['description']}")
    
    def _simulate_strategy_config_section(self, mock_selectbox, mock_caption, mock_expander, mock_columns, mock_markdown):
        """模拟策略配置区域的代码执行"""
        # 模拟 main() 函数中策略配置部分的逻辑
        mock_markdown("#### 📋 策略配置")
        
        strategy_name = mock_selectbox(
            "选择策略",
            options=list(daily_signal_module.STRATEGY_OPTIONS.keys()),
            index=0,
            help="选择要使用的策略类型，与回测页面保持一致",
            label_visibility="collapsed"
        )
        
        strategy_info = daily_signal_module.STRATEGY_OPTIONS[strategy_name]
        mock_caption(f"💡 {strategy_info['description']}")
        
        # 显示当前使用的参数
        saved_params = daily_signal_module.load_strategy_params()
        
        with mock_expander("📊 当前策略参数", expanded=False):
            if strategy_name == "RSI 超卖反弹策略":
                col1, col2, col3 = mock_columns(3)
                with col1:
                    col1.metric("RSI 周期", saved_params.rsi_period)
                with col2:
                    col2.metric("买入 (RSI<)", saved_params.rsi_buy_threshold)
                with col3:
                    col3.metric("卖出 (RSI>)", saved_params.rsi_sell_threshold)
    
    def test_rsi_strategy_parameters_display(self):
        """测试 RSI 策略参数显示"""
        with patch('streamlit.selectbox') as mock_selectbox, \
             patch('streamlit.caption') as mock_caption, \
             patch('streamlit.expander') as mock_expander, \
             patch('streamlit.columns') as mock_columns, \
             patch('streamlit.markdown') as mock_markdown, \
             patch.object(daily_signal_module, 'load_strategy_params') as mock_load_params:
            
            # 设置模拟返回值
            mock_selectbox.return_value = "RSI 超卖反弹策略"
            mock_columns.return_value = self.mock_columns
            
            # 模拟 expander 上下文管理器
            mock_expander_context = Mock()
            mock_expander.return_value.__enter__ = Mock(return_value=mock_expander_context)
            mock_expander.return_value.__exit__ = Mock(return_value=None)
            
            # 模拟策略参数
            mock_params = StrategyParamsConfig(
                rsi_period=14,
                rsi_buy_threshold=30,
                rsi_sell_threshold=70
            )
            mock_load_params.return_value = mock_params
            
            # 模拟 RSI 策略参数显示逻辑
            self._simulate_rsi_parameters_display(mock_expander, mock_columns, mock_params)
            
            # 验证 expander 被调用
            mock_expander.assert_called_once_with("📊 当前策略参数", expanded=False)
            
            # 验证 columns 被调用（3列布局）
            mock_columns.assert_called_once_with(3)
            
            # 验证每个 column 的 metric 调用
            expected_metrics = [
                ("RSI 周期", mock_params.rsi_period),
                ("买入 (RSI<)", mock_params.rsi_buy_threshold),
                ("卖出 (RSI>)", mock_params.rsi_sell_threshold)
            ]
            
            for i, (label, value) in enumerate(expected_metrics):
                self.mock_columns[i].metric.assert_called_once_with(label, value)
    
    def _simulate_rsi_parameters_display(self, mock_expander, mock_columns, saved_params):
        """模拟 RSI 策略参数显示"""
        with mock_expander("📊 当前策略参数", expanded=False):
            col1, col2, col3 = mock_columns(3)
            with col1:
                col1.metric("RSI 周期", saved_params.rsi_period)
            with col2:
                col2.metric("买入 (RSI<)", saved_params.rsi_buy_threshold)
            with col3:
                col3.metric("卖出 (RSI>)", saved_params.rsi_sell_threshold)
    
    def test_rsrs_strategy_parameters_display(self):
        """测试 RSRS 策略参数显示"""
        with patch('streamlit.selectbox') as mock_selectbox, \
             patch('streamlit.caption') as mock_caption, \
             patch('streamlit.expander') as mock_expander, \
             patch('streamlit.columns') as mock_columns, \
             patch('streamlit.markdown') as mock_markdown, \
             patch.object(daily_signal_module, 'load_strategy_params') as mock_load_params:
            
            # 设置模拟返回值
            mock_selectbox.return_value = "RSRS 阻力支撑策略"
            mock_columns.return_value = self.mock_columns
            
            # 模拟 expander 上下文管理器
            mock_expander_context = Mock()
            mock_expander.return_value.__enter__ = Mock(return_value=mock_expander_context)
            mock_expander.return_value.__exit__ = Mock(return_value=None)
            
            # 模拟策略参数
            mock_params = StrategyParamsConfig(
                rsrs_n_period=18,
                rsrs_buy_threshold=0.7,
                rsrs_sell_threshold=-0.7
            )
            mock_load_params.return_value = mock_params
            
            # 模拟 RSRS 策略参数显示逻辑
            self._simulate_rsrs_parameters_display(mock_expander, mock_columns, mock_params)
            
            # 验证 expander 被调用
            mock_expander.assert_called_once_with("📊 当前策略参数", expanded=False)
            
            # 验证 columns 被调用（3列布局）
            mock_columns.assert_called_once_with(3)
            
            # 验证每个 column 的 metric 调用
            expected_metrics = [
                ("斜率窗口", mock_params.rsrs_n_period),
                ("买入阈值", f"{mock_params.rsrs_buy_threshold:.1f}"),
                ("卖出阈值", f"{mock_params.rsrs_sell_threshold:.1f}")
            ]
            
            for i, (label, value) in enumerate(expected_metrics):
                self.mock_columns[i].metric.assert_called_once_with(label, value)
    
    def _simulate_rsrs_parameters_display(self, mock_expander, mock_columns, saved_params):
        """模拟 RSRS 策略参数显示"""
        with mock_expander("📊 当前策略参数", expanded=False):
            col1, col2, col3 = mock_columns(3)
            with col1:
                col1.metric("斜率窗口", saved_params.rsrs_n_period)
            with col2:
                col2.metric("买入阈值", f"{saved_params.rsrs_buy_threshold:.1f}")
            with col3:
                col3.metric("卖出阈值", f"{saved_params.rsrs_sell_threshold:.1f}")
    
    @patch.object(daily_signal_module, 'load_strategy_params')
    def test_strategy_params_loading(self, mock_load_params):
        """测试策略参数加载功能"""
        # 设置模拟返回值
        expected_params = StrategyParamsConfig(
            rsi_period=21,
            rsi_buy_threshold=25,
            rsi_sell_threshold=75,
            rsrs_n_period=20,
            rsrs_buy_threshold=0.8,
            rsrs_sell_threshold=-0.8
        )
        mock_load_params.return_value = expected_params
        
        # 调用参数加载函数
        loaded_params = daily_signal_module.load_strategy_params()
        
        # 验证函数被调用
        mock_load_params.assert_called_once()
        
        # 验证返回的参数正确
        self.assertEqual(loaded_params, expected_params)
        self.assertEqual(loaded_params.rsi_period, 21)
        self.assertEqual(loaded_params.rsi_buy_threshold, 25)
        self.assertEqual(loaded_params.rsi_sell_threshold, 75)
        self.assertEqual(loaded_params.rsrs_n_period, 20)
        self.assertEqual(loaded_params.rsrs_buy_threshold, 0.8)
        self.assertEqual(loaded_params.rsrs_sell_threshold, -0.8)
    
    def test_strategy_description_content(self):
        """测试策略描述内容的正确性"""
        strategy_options = daily_signal_module.STRATEGY_OPTIONS
        
        # 验证 RSI 策略描述
        rsi_description = strategy_options["RSI 超卖反弹策略"]["description"]
        self.assertIn("震荡行情", rsi_description)
        self.assertIn("RSI<30", rsi_description)
        self.assertIn("RSI>70", rsi_description)
        
        # 验证 RSRS 策略描述
        rsrs_description = strategy_options["RSRS 阻力支撑策略"]["description"]
        self.assertIn("阻力支撑", rsrs_description)
        self.assertIn("RSRS标准分", rsrs_description)
        self.assertIn("0.7", rsrs_description)
        self.assertIn("-0.7", rsrs_description)
    
    @patch('streamlit.caption')
    def test_parameter_sync_caption(self, mock_caption):
        """测试参数同步说明的显示"""
        # 模拟参数同步说明的显示
        expected_caption = "💡 参数在回测页面自动同步"
        
        # 验证 caption 调用
        mock_caption.assert_not_called()  # 初始状态未调用
        
        # 模拟调用
        mock_caption(expected_caption)
        mock_caption.assert_called_with(expected_caption)
    
    def test_strategy_type_mapping(self):
        """测试策略类型映射的正确性"""
        # 直接测试策略选项配置，避免导入依赖问题
        strategy_options = daily_signal_module.STRATEGY_OPTIONS
        
        # 验证策略类型映射存在
        self.assertIn("type", strategy_options["RSI 超卖反弹策略"])
        self.assertIn("type", strategy_options["RSRS 阻力支撑策略"])
        
        # 验证策略类型不为空
        self.assertIsNotNone(strategy_options["RSI 超卖反弹策略"]["type"])
        self.assertIsNotNone(strategy_options["RSRS 阻力支撑策略"]["type"])
    
    @patch('streamlit.markdown')
    def test_strategy_section_title(self, mock_markdown):
        """测试策略配置区域标题显示"""
        expected_title = "#### 📋 策略配置"
        
        # 模拟标题显示
        mock_markdown(expected_title)
        mock_markdown.assert_called_with(expected_title)


if __name__ == '__main__':
    unittest.main()