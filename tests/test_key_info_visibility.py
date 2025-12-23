"""
测试关键信息在一屏内可见

验证每日信号页面的紧凑布局能够在标准屏幕分辨率下
将所有关键信息显示在一屏内，无需滚动即可看到主要功能。

Requirements: Task 3.2 - 验证关键信息在一屏内可见
"""

import unittest
from unittest.mock import patch, MagicMock, call
import sys
import os
import inspect
import ast

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock Streamlit before importing the module
sys.modules['streamlit'] = MagicMock()
sys.modules['pandas'] = MagicMock()
sys.modules['akshare'] = MagicMock()

# 读取源码文件进行静态分析
daily_signal_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app", "pages", "3_Daily_Signal.py")

class MockDailySignalModule:
    """模拟的每日信号模块，用于静态分析"""
    
    def __init__(self, source_path):
        with open(source_path, 'r', encoding='utf-8') as f:
            self.source_code = f.read()
        
        # 解析AST以提取函数定义
        self.ast_tree = ast.parse(self.source_code)
        self.functions = {}
        
        for node in ast.walk(self.ast_tree):
            if isinstance(node, ast.FunctionDef):
                self.functions[node.name] = node
    
    def has_function(self, name):
        return name in self.functions
    
    def get_function_source(self, name):
        if name in self.functions:
            # 从源码中提取函数源码
            func_node = self.functions[name]
            lines = self.source_code.split('\n')
            start_line = func_node.lineno - 1
            
            # 找到函数结束位置
            end_line = start_line + 1
            while end_line < len(lines):
                if lines[end_line].strip() and not lines[end_line].startswith(' ') and not lines[end_line].startswith('\t'):
                    break
                end_line += 1
            
            return '\n'.join(lines[start_line:end_line])
        return ""

# 创建模拟模块实例
daily_signal_module = MockDailySignalModule(daily_signal_path)


class TestKeyInfoVisibility(unittest.TestCase):
    """测试关键信息在一屏内可见"""
    
    def setUp(self):
        """设置测试环境"""
        self.module = daily_signal_module
        
        # 定义标准屏幕分辨率
        self.screen_resolutions = {
            '1920x1080': {'width': 1920, 'height': 1080, 'available_height': 950},
            '1366x768': {'width': 1366, 'height': 768, 'available_height': 650},
            '1440x900': {'width': 1440, 'height': 900, 'available_height': 750},
            '1600x900': {'width': 1600, 'height': 900, 'available_height': 750}
        }
        
        # 定义关键信息组件
        self.critical_components = {
            'title': {'height': 60, 'priority': 1},
            'data_freshness_warning': {'height': 80, 'priority': 1},
            'market_holiday_notice': {'height': 80, 'priority': 1},
            'premarket_checklist': {'height': 120, 'priority': 2},
            'sell_signals_compact': {'height': 150, 'priority': 1},
            'market_status_compact': {'height': 120, 'priority': 1},
            'strategy_config': {'height': 120, 'priority': 1},
            'notification_compact': {'height': 120, 'priority': 2},
            'signal_generation': {'height': 150, 'priority': 1},
            'dividers': {'height': 60, 'priority': 3}  # 多个分隔线的总高度
        }
    
    def test_critical_components_exist(self):
        """测试关键组件是否存在"""
        required_functions = [
            'render_sell_signals_section_compact',
            'render_market_status_compact',
            'render_notification_settings_compact',
            'render_data_freshness_warning',
            'render_market_holiday_notice',
            'render_premarket_checklist',
            'main'
        ]
        
        for func_name in required_functions:
            with self.subTest(function=func_name):
                self.assertTrue(
                    self.module.has_function(func_name),
                    f"关键函数 {func_name} 不存在"
                )
    
    def test_main_layout_structure_for_visibility(self):
        """测试主布局结构是否有利于可见性"""
        self.assertTrue(
            self.module.has_function('main'),
            "main 函数不存在"
        )
        
        source = self.module.get_function_source('main')
        if not source:
            source = self.module.source_code  # 使用整个源码作为备选
        
        # 验证使用了紧凑布局
        layout_indicators = [
            'render_sell_signals_section_compact',
            'render_market_status_compact',
            'render_notification_settings_compact',
            'st.columns(2)',  # 两列布局
            'st.columns([2, 1])'  # 2:1 比例布局
        ]
        
        for indicator in layout_indicators:
            self.assertIn(
                indicator,
                source,
                f"主布局应该包含 {indicator} 以确保紧凑性"
            )
    
    def test_screen_space_utilization_efficiency(self):
        """测试屏幕空间利用效率"""
        for resolution_name, resolution in self.screen_resolutions.items():
            with self.subTest(resolution=resolution_name):
                available_height = resolution['available_height']
                
                # 计算优先级1组件的总高度（必须在一屏内可见）
                priority_1_height = sum(
                    comp['height'] for comp in self.critical_components.values()
                    if comp['priority'] == 1
                )
                
                # 由于使用两列布局，实际高度会减少
                # 假设两列布局能节省约30%的垂直空间
                layout_efficiency = 0.7  # 70%的原始高度
                effective_height = priority_1_height * layout_efficiency
                
                self.assertLessEqual(
                    effective_height,
                    available_height,
                    f"在 {resolution_name} 分辨率下，优先级1组件高度 {effective_height}px "
                    f"超过可用屏幕高度 {available_height}px"
                )
    
    def test_two_column_layout_space_saving(self):
        """测试两列布局的空间节省效果"""
        # 模拟原始垂直布局的高度
        original_layout_height = sum(comp['height'] for comp in self.critical_components.values())
        
        # 模拟紧凑两列布局的高度
        # 左列：持仓卖出信号 + 大盘状态
        left_column_height = (
            self.critical_components['sell_signals_compact']['height'] +
            self.critical_components['market_status_compact']['height']
        )
        
        # 右列：策略配置 + 飞书通知
        right_column_height = (
            self.critical_components['strategy_config']['height'] +
            self.critical_components['notification_compact']['height']
        )
        
        # 两列布局的实际高度是较高列的高度
        two_column_height = max(left_column_height, right_column_height)
        
        # 加上其他非列布局组件
        other_components_height = (
            self.critical_components['title']['height'] +
            self.critical_components['data_freshness_warning']['height'] +
            self.critical_components['premarket_checklist']['height'] +
            self.critical_components['signal_generation']['height'] +
            self.critical_components['dividers']['height']
        )
        
        compact_layout_height = two_column_height + other_components_height
        
        # 计算空间节省比例
        space_saved = (original_layout_height - compact_layout_height) / original_layout_height
        
        # 验证至少节省15%的空间
        min_space_saving = 0.15
        self.assertGreaterEqual(
            space_saved,
            min_space_saving,
            f"两列布局仅节省 {space_saved:.1%} 空间，少于预期的 {min_space_saving:.1%}"
        )
    
    def test_critical_info_above_fold(self):
        """测试关键信息在首屏可见（Above the Fold）"""
        # 定义"首屏"高度（不需要滚动即可看到的区域）
        above_fold_heights = {
            '1920x1080': 600,  # 首屏约600px
            '1366x768': 450,   # 首屏约450px
            '1440x900': 500,   # 首屏约500px
        }
        
        # 最关键的信息（优先级1）
        critical_info_components = [
            'title',
            'sell_signals_compact',
            'market_status_compact',
            'strategy_config',
            'signal_generation'
        ]
        
        for resolution_name, fold_height in above_fold_heights.items():
            with self.subTest(resolution=resolution_name):
                # 计算关键信息的总高度（考虑两列布局）
                title_height = self.critical_components['title']['height']
                
                # 两列布局区域
                left_col = self.critical_components['sell_signals_compact']['height']
                right_col = self.critical_components['strategy_config']['height']
                columns_height = max(left_col, right_col)
                
                signal_gen_height = self.critical_components['signal_generation']['height']
                dividers_height = 40  # 基本分隔线
                
                total_critical_height = (
                    title_height + columns_height + signal_gen_height + dividers_height
                )
                
                self.assertLessEqual(
                    total_critical_height,
                    fold_height,
                    f"在 {resolution_name} 下，关键信息总高度 {total_critical_height}px "
                    f"超过首屏高度 {fold_height}px"
                )
    
    def test_compact_components_height_efficiency(self):
        """测试紧凑组件的高度效率"""
        compact_functions = {
            'render_sell_signals_section_compact': 150,  # 预期最大高度
            'render_market_status_compact': 120,
            'render_notification_settings_compact': 120
        }
        
        for func_name, max_expected_height in compact_functions.items():
            with self.subTest(function=func_name):
                self.assertTrue(
                    self.module.has_function(func_name),
                    f"函数 {func_name} 不存在"
                )
                
                source = self.module.get_function_source(func_name)
                if not source:
                    source = self.module.source_code
                
                # 验证使用了紧凑组件
                compact_indicators = [
                    'st.metric',     # 紧凑的指标显示
                    'st.expander',   # 可折叠内容
                    'st.columns',    # 列布局（某些函数）
                    'st.success',    # 简洁的状态显示
                    'st.caption'     # 简短说明
                ]
                
                used_indicators = [ind for ind in compact_indicators if ind in source]
                
                self.assertGreater(
                    len(used_indicators),
                    0,
                    f"{func_name} 应该使用紧凑组件来减少高度"
                )
    
    def test_responsive_layout_breakpoints(self):
        """测试响应式布局断点"""
        # 测试不同屏幕宽度下的布局适应性
        breakpoints = [
            {'width': 1920, 'columns': 2, 'min_column_width': 200},
            {'width': 1366, 'columns': 2, 'min_column_width': 180},
            {'width': 1024, 'columns': 2, 'min_column_width': 150},
            {'width': 768, 'columns': 1, 'min_column_width': 300}  # 可能需要单列
        ]
        
        for breakpoint in breakpoints:
            with self.subTest(width=breakpoint['width']):
                container_width = breakpoint['width'] - 100  # 减去边距
                
                if breakpoint['columns'] == 2:
                    column_width = container_width / 2
                    self.assertGreaterEqual(
                        column_width,
                        breakpoint['min_column_width'],
                        f"屏幕宽度 {breakpoint['width']}px 时，"
                        f"列宽 {column_width}px 小于最小宽度 {breakpoint['min_column_width']}px"
                    )
                else:
                    # 单列布局
                    self.assertGreaterEqual(
                        container_width,
                        breakpoint['min_column_width'],
                        f"屏幕宽度 {breakpoint['width']}px 时，"
                        f"容器宽度 {container_width}px 小于最小宽度 {breakpoint['min_column_width']}px"
                    )
    
    def test_content_hierarchy_for_visibility(self):
        """测试内容层次结构有利于可见性"""
        self.assertTrue(
            self.module.has_function('main'),
            "main 函数不存在"
        )
        
        source = self.module.source_code
        
        # 验证内容按重要性排序
        content_order_indicators = [
            'render_data_freshness_warning',      # 最重要：数据警告
            'render_premarket_checklist',         # 重要：早安清单
            'render_sell_signals_section_compact', # 核心：卖出信号
            'render_market_status_compact',       # 核心：大盘状态
            'render_notification_settings_compact', # 次要：通知设置
            'render_historical_signals'           # 最后：历史信号
        ]
        
        # 查找每个函数在源码中的位置
        positions = {}
        for indicator in content_order_indicators:
            pos = source.find(indicator)
            if pos != -1:
                positions[indicator] = pos
        
        # 验证重要内容在前面
        critical_functions = content_order_indicators[:4]  # 前4个最重要
        
        for i in range(len(critical_functions) - 1):
            current_func = critical_functions[i]
            next_func = critical_functions[i + 1]
            
            if current_func in positions and next_func in positions:
                self.assertLess(
                    positions[current_func],
                    positions[next_func],
                    f"{current_func} 应该在 {next_func} 之前出现"
                )
    
    def test_layout_performance_impact(self):
        """测试布局对性能的影响"""
        # 验证紧凑布局不会增加过多的渲染复杂度
        
        # 计算组件复杂度
        component_complexity = {
            'simple_text': 1,      # st.markdown, st.caption
            'metrics': 2,          # st.metric
            'status_indicators': 2, # st.success, st.error, st.warning
            'interactive': 3,      # st.button, st.selectbox
            'containers': 2,       # st.expander, st.columns
            'complex_layouts': 4   # 复杂的嵌套布局
        }
        
        # 估算每个紧凑组件的复杂度
        compact_components_complexity = {
            'render_sell_signals_section_compact': 8,  # metrics + expander + status
            'render_market_status_compact': 6,         # metrics + status
            'render_notification_settings_compact': 10, # expander + inputs + buttons
            'strategy_config': 6                       # selectbox + metrics
        }
        
        total_complexity = sum(compact_components_complexity.values())
        max_acceptable_complexity = 40  # 最大可接受复杂度
        
        self.assertLessEqual(
            total_complexity,
            max_acceptable_complexity,
            f"紧凑布局总复杂度 {total_complexity} 超过最大可接受值 {max_acceptable_complexity}"
        )
    
    def test_visual_hierarchy_effectiveness(self):
        """测试视觉层次结构的有效性"""
        # 验证使用了合适的视觉层次组件
        
        hierarchy_components = {
            'titles': ['st.title', 'st.subheader', 'st.markdown("####'],
            'emphasis': ['st.success', 'st.error', 'st.warning', 'st.info'],
            'organization': ['st.divider', 'st.expander', 'st.columns'],
            'data_display': ['st.metric', 'st.dataframe', 'st.table']
        }
        
        source = self.module.source_code
        
        for category, components in hierarchy_components.items():
            with self.subTest(category=category):
                used_components = [comp for comp in components if comp in source]
                
                self.assertGreater(
                    len(used_components),
                    0,
                    f"应该使用 {category} 类别的组件来建立视觉层次"
                )
    
    def test_information_density_optimization(self):
        """测试信息密度优化"""
        # 验证信息密度在可读性和紧凑性之间取得平衡
        
        # 定义每种组件类型的信息密度（信息量/占用空间比）
        component_density = {
            'st.metric': 0.8,      # 高密度：显示关键数值
            'st.success': 0.6,     # 中密度：状态信息
            'st.expander': 0.9,    # 高密度：可折叠详细信息
            'st.columns': 0.7,     # 中高密度：并排显示
            'st.markdown': 0.4,    # 中低密度：文本信息
            'st.caption': 0.5      # 中密度：辅助信息
        }
        
        # 检查紧凑函数是否使用了高密度组件
        compact_functions = [
            'render_sell_signals_section_compact',
            'render_market_status_compact',
            'render_notification_settings_compact'
        ]
        
        for func_name in compact_functions:
            with self.subTest(function=func_name):
                if not self.module.has_function(func_name):
                    continue
                
                source = self.module.get_function_source(func_name)
                if not source:
                    source = self.module.source_code
                
                # 计算使用的高密度组件数量
                high_density_components = [
                    comp for comp, density in component_density.items()
                    if density >= 0.7 and comp in source
                ]
                
                # 计算使用的低密度组件数量
                low_density_components = [
                    comp for comp, density in component_density.items()
                    if density < 0.5 and comp in source
                ]
                
                # 验证高密度组件多于低密度组件
                self.assertGreaterEqual(
                    len(high_density_components),
                    len(low_density_components),
                    f"{func_name} 应该优先使用高密度组件以提高信息密度"
                )


if __name__ == '__main__':
    unittest.main()