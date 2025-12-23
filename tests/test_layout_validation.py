"""
测试每日信号页面布局实现验证

验证实际的 Streamlit 布局代码是否遵循无横向滚动的设计原则。
这是对 Task 3.2 "验证无横向滚动" 的实际代码验证。

Requirements: Task 3.2 - 验证无横向滚动
"""

import unittest
import sys
import os
import ast
import inspect

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入要测试的模块
try:
    from app.pages import Daily_Signal as daily_signal_module
except ImportError:
    # 如果直接导入失败，尝试通过文件路径导入
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "daily_signal", 
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "app", "pages", "3_Daily_Signal.py")
    )
    daily_signal_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(daily_signal_module)


class TestLayoutValidation(unittest.TestCase):
    """测试布局实现验证"""
    
    def setUp(self):
        """设置测试环境"""
        self.module = daily_signal_module
    
    def test_compact_functions_exist(self):
        """测试紧凑版函数是否存在"""
        required_compact_functions = [
            'render_sell_signals_section_compact',
            'render_market_status_compact', 
            'render_notification_settings_compact'
        ]
        
        for func_name in required_compact_functions:
            with self.subTest(function=func_name):
                self.assertTrue(
                    hasattr(self.module, func_name),
                    f"紧凑版函数 {func_name} 不存在"
                )
                
                func = getattr(self.module, func_name)
                self.assertTrue(
                    callable(func),
                    f"{func_name} 不是可调用函数"
                )
    
    def test_main_function_uses_columns(self):
        """测试 main 函数是否使用了列布局"""
        main_func = getattr(self.module, 'main', None)
        self.assertIsNotNone(main_func, "main 函数不存在")
        
        # 获取函数源码
        source = inspect.getsource(main_func)
        
        # 验证使用了 st.columns
        self.assertIn(
            'st.columns',
            source,
            "main 函数应该使用 st.columns 创建列布局"
        )
        
        # 验证使用了紧凑版函数
        compact_functions = [
            'render_sell_signals_section_compact',
            'render_market_status_compact',
            'render_notification_settings_compact'
        ]
        
        for func_name in compact_functions:
            self.assertIn(
                func_name,
                source,
                f"main 函数应该调用 {func_name}"
            )
    
    def test_column_layout_structure(self):
        """测试列布局结构"""
        main_func = getattr(self.module, 'main', None)
        source = inspect.getsource(main_func)
        
        # 验证两列布局的存在
        # 第一组：持仓卖出信号 + 大盘状态
        self.assertIn(
            'col_sell, col_market = st.columns(2)',
            source,
            "应该有持仓卖出信号和大盘状态的两列布局"
        )
        
        # 第二组：策略配置 + 飞书通知
        column_patterns = [
            'col_strategy, col_notification = st.columns([2, 1])',
            'col_strategy, col_notification = st.columns(2)'
        ]
        
        has_strategy_layout = any(pattern in source for pattern in column_patterns)
        self.assertTrue(
            has_strategy_layout,
            "应该有策略配置和飞书通知的列布局"
        )
    
    def test_compact_functions_use_appropriate_components(self):
        """测试紧凑版函数使用了合适的组件"""
        compact_functions = {
            'render_sell_signals_section_compact': [
                'st.markdown',  # 标题
                'st.metric',    # 指标显示
                'st.expander',  # 可展开内容
                'st.success',   # 状态显示
            ],
            'render_market_status_compact': [
                'st.markdown',  # 标题
                'st.metric',    # 指标显示
                'st.success',   # 健康状态
                'st.error',     # 不健康状态
            ],
            'render_notification_settings_compact': [
                'st.markdown',  # 标题
                'st.success',   # 已启用状态
                'st.info',      # 未配置状态
                'st.expander',  # 配置面板
                'st.columns',   # 按钮布局
            ]
        }
        
        for func_name, expected_components in compact_functions.items():
            with self.subTest(function=func_name):
                func = getattr(self.module, func_name, None)
                self.assertIsNotNone(func, f"函数 {func_name} 不存在")
                
                source = inspect.getsource(func)
                
                for component in expected_components:
                    self.assertIn(
                        component,
                        source,
                        f"{func_name} 应该使用 {component} 组件"
                    )
    
    def test_no_fixed_width_usage(self):
        """测试没有使用固定宽度"""
        # 检查所有紧凑版函数是否避免了固定宽度设置
        compact_functions = [
            'render_sell_signals_section_compact',
            'render_market_status_compact',
            'render_notification_settings_compact',
            'main'
        ]
        
        # 可能导致横向滚动的固定宽度模式
        problematic_patterns = [
            'width=',           # 固定宽度参数
            'min_width=',       # 最小宽度参数
            'max_width=',       # 最大宽度参数
            'style="width:',    # CSS 固定宽度
            'px',               # 像素单位（可能表示固定尺寸）
        ]
        
        for func_name in compact_functions:
            with self.subTest(function=func_name):
                func = getattr(self.module, func_name, None)
                if func is None:
                    continue
                
                source = inspect.getsource(func)
                
                for pattern in problematic_patterns:
                    # 允许一些例外情况
                    if pattern == 'px' and ('100px' in source or '50px' in source):
                        # 小的像素值可能是边距，可以接受
                        continue
                    
                    self.assertNotIn(
                        pattern,
                        source,
                        f"{func_name} 不应该使用可能导致横向滚动的固定宽度模式: {pattern}"
                    )
    
    def test_responsive_design_principles(self):
        """测试响应式设计原则"""
        main_func = getattr(self.module, 'main', None)
        source = inspect.getsource(main_func)
        
        # 验证使用了响应式组件
        responsive_components = [
            'use_container_width=True',  # 使用容器宽度
            'st.columns',                # 响应式列
        ]
        
        for component in responsive_components:
            self.assertIn(
                component,
                source,
                f"main 函数应该使用响应式组件: {component}"
            )
    
    def test_layout_hierarchy_depth(self):
        """测试布局层次深度"""
        # 验证布局嵌套不会过深（避免复杂的嵌套导致布局问题）
        compact_functions = [
            'render_sell_signals_section_compact',
            'render_market_status_compact',
            'render_notification_settings_compact'
        ]
        
        for func_name in compact_functions:
            with self.subTest(function=func_name):
                func = getattr(self.module, func_name, None)
                if func is None:
                    continue
                
                source = inspect.getsource(func)
                
                # 计算 with 语句的嵌套层次（简单估算）
                lines = source.split('\n')
                max_indent = 0
                current_indent = 0
                
                for line in lines:
                    stripped = line.lstrip()
                    if stripped.startswith('with '):
                        indent_level = len(line) - len(stripped)
                        current_indent = indent_level
                        max_indent = max(max_indent, current_indent)
                
                # 验证嵌套层次不会过深
                max_acceptable_indent = 16  # 4个缩进级别
                self.assertLessEqual(
                    max_indent,
                    max_acceptable_indent,
                    f"{func_name} 的嵌套层次过深 (缩进: {max_indent})"
                )
    
    def test_column_ratio_reasonableness(self):
        """测试列比例的合理性"""
        main_func = getattr(self.module, 'main', None)
        source = inspect.getsource(main_func)
        
        # 查找列比例定义
        lines = source.split('\n')
        
        for line in lines:
            if 'st.columns(' in line and '[' in line:
                # 提取比例数组
                start = line.find('[')
                end = line.find(']')
                if start != -1 and end != -1:
                    ratio_str = line[start+1:end]
                    try:
                        # 解析比例
                        ratios = [int(x.strip()) for x in ratio_str.split(',')]
                        
                        # 验证比例合理性
                        total_ratio = sum(ratios)
                        self.assertGreater(total_ratio, 0, "列比例总和应该大于0")
                        
                        # 验证没有过小的列
                        min_ratio = min(ratios)
                        min_acceptable_ratio = total_ratio * 0.15  # 最小列不应小于总比例的15%
                        
                        self.assertGreaterEqual(
                            min_ratio,
                            min_acceptable_ratio,
                            f"列比例 {ratios} 中最小比例 {min_ratio} 过小，可能导致内容显示问题"
                        )
                        
                    except (ValueError, IndexError):
                        # 如果解析失败，跳过这行
                        continue
    
    def test_container_usage_patterns(self):
        """测试容器使用模式"""
        # 验证使用了合适的容器模式
        functions_to_check = [
            'render_sell_signals_section_compact',
            'render_market_status_compact',
            'render_notification_settings_compact'
        ]
        
        for func_name in functions_to_check:
            with self.subTest(function=func_name):
                func = getattr(self.module, func_name, None)
                if func is None:
                    continue
                
                source = inspect.getsource(func)
                
                # 验证使用了适当的容器组件
                container_components = [
                    'st.markdown',   # 标题和文本
                    'st.metric',     # 指标显示
                    'st.expander',   # 可展开内容
                ]
                
                # 至少应该使用其中一些组件
                used_components = [comp for comp in container_components if comp in source]
                
                self.assertGreater(
                    len(used_components),
                    0,
                    f"{func_name} 应该使用至少一个容器组件"
                )
    
    def test_streamlit_best_practices(self):
        """测试 Streamlit 最佳实践"""
        main_func = getattr(self.module, 'main', None)
        source = inspect.getsource(main_func)
        
        # 验证页面配置
        self.assertIn(
            'st.set_page_config',
            source,
            "应该设置页面配置"
        )
        
        # 验证使用了 layout="wide"（如果需要更多空间）
        if 'layout=' in source:
            self.assertIn(
                'layout="wide"',
                source,
                "如果设置了布局，应该使用 wide 布局以获得更多空间"
            )
        
        # 验证使用了分隔符
        self.assertIn(
            'st.divider()',
            source,
            "应该使用分隔符来组织内容"
        )


if __name__ == '__main__':
    unittest.main()