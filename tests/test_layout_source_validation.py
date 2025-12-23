"""
测试每日信号页面布局源码验证

通过分析源码验证布局实现是否遵循无横向滚动的设计原则。
这是对 Task 3.2 "验证无横向滚动" 的源码级验证。

Requirements: Task 3.2 - 验证无横向滚动
"""

import unittest
import os
import re


class TestLayoutSourceValidation(unittest.TestCase):
    """测试布局源码验证"""
    
    def setUp(self):
        """设置测试环境"""
        # 获取每日信号页面的源码路径
        self.daily_signal_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "app", "pages", "3_Daily_Signal.py"
        )
        
        # 读取源码
        with open(self.daily_signal_path, 'r', encoding='utf-8') as f:
            self.source_code = f.read()
    
    def test_source_file_exists(self):
        """测试源文件是否存在"""
        self.assertTrue(
            os.path.exists(self.daily_signal_path),
            f"每日信号页面源文件不存在: {self.daily_signal_path}"
        )
    
    def test_compact_functions_defined(self):
        """测试紧凑版函数是否已定义"""
        required_compact_functions = [
            'render_sell_signals_section_compact',
            'render_market_status_compact',
            'render_notification_settings_compact'
        ]
        
        for func_name in required_compact_functions:
            with self.subTest(function=func_name):
                pattern = rf'def {func_name}\('
                self.assertRegex(
                    self.source_code,
                    pattern,
                    f"紧凑版函数 {func_name} 未定义"
                )
    
    def test_main_function_uses_column_layout(self):
        """测试 main 函数使用了列布局"""
        # 查找 main 函数
        main_match = re.search(r'def main\(\):.*?(?=\ndef|\nif __name__|$)', self.source_code, re.DOTALL)
        self.assertIsNotNone(main_match, "main 函数未找到")
        
        main_source = main_match.group(0)
        
        # 验证使用了 st.columns
        self.assertIn(
            'st.columns',
            main_source,
            "main 函数应该使用 st.columns 创建列布局"
        )
        
        # 验证调用了紧凑版函数
        compact_functions = [
            'render_sell_signals_section_compact',
            'render_market_status_compact',
            'render_notification_settings_compact'
        ]
        
        for func_name in compact_functions:
            self.assertIn(
                func_name,
                main_source,
                f"main 函数应该调用 {func_name}"
            )
    
    def test_two_column_layouts_exist(self):
        """测试两列布局的存在"""
        # 查找 main 函数
        main_match = re.search(r'def main\(\):.*?(?=\ndef|\nif __name__|$)', self.source_code, re.DOTALL)
        main_source = main_match.group(0)
        
        # 验证第一组两列布局：持仓卖出信号 + 大盘状态
        pattern1 = r'col_sell,\s*col_market\s*=\s*st\.columns\(2\)'
        self.assertRegex(
            main_source,
            pattern1,
            "应该有持仓卖出信号和大盘状态的两列布局"
        )
        
        # 验证第二组列布局：策略配置 + 飞书通知
        pattern2 = r'col_strategy,\s*col_notification\s*=\s*st\.columns\(\[2,\s*1\]\)'
        self.assertRegex(
            main_source,
            pattern2,
            "应该有策略配置和飞书通知的列布局"
        )
    
    def test_compact_functions_use_appropriate_components(self):
        """测试紧凑版函数使用了合适的组件"""
        compact_functions = {
            'render_sell_signals_section_compact': [
                r'st\.markdown\(',
                r'st\.metric\(',
                r'st\.expander\(',
                r'st\.success\(',
            ],
            'render_market_status_compact': [
                r'st\.markdown\(',
                r'st\.metric\(',
                r'st\.success\(',
                r'st\.error\(',
            ],
            'render_notification_settings_compact': [
                r'st\.markdown\(',
                r'st\.success\(',
                r'st\.info\(',
                r'st\.expander\(',
                r'st\.columns\(',
            ]
        }
        
        for func_name, expected_patterns in compact_functions.items():
            with self.subTest(function=func_name):
                # 提取函数源码
                func_pattern = rf'def {func_name}\(.*?\n(?=def|\nif __name__|\Z)'
                func_match = re.search(func_pattern, self.source_code, re.DOTALL)
                
                if func_match:
                    func_source = func_match.group(0)
                    
                    for pattern in expected_patterns:
                        self.assertRegex(
                            func_source,
                            pattern,
                            f"{func_name} 应该使用组件: {pattern}"
                        )
    
    def test_no_fixed_width_patterns(self):
        """测试没有使用固定宽度模式"""
        # 可能导致横向滚动的固定宽度模式
        problematic_patterns = [
            r'width\s*=\s*\d+',           # width=数字
            r'min_width\s*=\s*\d+',       # min_width=数字
            r'max_width\s*=\s*\d+',       # max_width=数字
            r'style\s*=\s*["\'].*width:\s*\d+px',  # CSS 固定宽度
        ]
        
        for pattern in problematic_patterns:
            with self.subTest(pattern=pattern):
                matches = re.findall(pattern, self.source_code, re.IGNORECASE)
                self.assertEqual(
                    len(matches),
                    0,
                    f"发现可能导致横向滚动的固定宽度模式: {pattern}, 匹配: {matches}"
                )
    
    def test_responsive_design_usage(self):
        """测试响应式设计的使用"""
        # 查找 main 函数
        main_match = re.search(r'def main\(\):.*?(?=\ndef|\nif __name__|$)', self.source_code, re.DOTALL)
        main_source = main_match.group(0)
        
        # 验证使用了响应式组件
        responsive_patterns = [
            r'use_container_width\s*=\s*True',  # 使用容器宽度
            r'st\.columns\(',                   # 响应式列
        ]
        
        for pattern in responsive_patterns:
            with self.subTest(pattern=pattern):
                self.assertRegex(
                    main_source,
                    pattern,
                    f"main 函数应该使用响应式模式: {pattern}"
                )
    
    def test_page_config_uses_wide_layout(self):
        """测试页面配置使用了宽布局"""
        # 查找页面配置
        config_pattern = r'st\.set_page_config\([^)]*\)'
        config_match = re.search(config_pattern, self.source_code, re.DOTALL)
        
        if config_match:
            config_source = config_match.group(0)
            
            # 验证使用了 wide 布局
            self.assertIn(
                'layout="wide"',
                config_source,
                "页面配置应该使用 wide 布局以获得更多空间"
            )
    
    def test_column_with_statements_structure(self):
        """测试列的 with 语句结构"""
        # 查找 main 函数
        main_match = re.search(r'def main\(\):.*?(?=\ndef|\nif __name__|$)', self.source_code, re.DOTALL)
        main_source = main_match.group(0)
        
        # 验证列的使用模式
        column_usage_patterns = [
            r'with\s+col_sell:',
            r'with\s+col_market:',
            r'with\s+col_strategy:',
            r'with\s+col_notification:',
        ]
        
        for pattern in column_usage_patterns:
            with self.subTest(pattern=pattern):
                self.assertRegex(
                    main_source,
                    pattern,
                    f"应该有列的使用模式: {pattern}"
                )
    
    def test_divider_usage_for_layout_separation(self):
        """测试分隔符的使用"""
        # 查找 main 函数
        main_match = re.search(r'def main\(\):.*?(?=\ndef|\nif __name__|$)', self.source_code, re.DOTALL)
        main_source = main_match.group(0)
        
        # 验证使用了分隔符来组织布局
        divider_count = len(re.findall(r'st\.divider\(\)', main_source))
        
        self.assertGreaterEqual(
            divider_count,
            3,  # 至少应该有几个分隔符来组织内容
            f"应该使用足够的分隔符来组织布局，当前只有 {divider_count} 个"
        )
    
    def test_compact_function_structure(self):
        """测试紧凑版函数的结构"""
        compact_functions = [
            'render_sell_signals_section_compact',
            'render_market_status_compact',
            'render_notification_settings_compact'
        ]
        
        for func_name in compact_functions:
            with self.subTest(function=func_name):
                # 提取函数源码
                func_pattern = rf'def {func_name}\(.*?\n(?=def|\nif __name__|\Z)'
                func_match = re.search(func_pattern, self.source_code, re.DOTALL)
                
                self.assertIsNotNone(
                    func_match,
                    f"函数 {func_name} 未找到"
                )
                
                func_source = func_match.group(0)
                
                # 验证函数有适当的标题
                title_pattern = r'st\.markdown\(["\'].*?#{1,4}.*?["\']'
                self.assertRegex(
                    func_source,
                    title_pattern,
                    f"{func_name} 应该有标题"
                )
    
    def test_no_hardcoded_pixel_values(self):
        """测试没有硬编码的像素值"""
        # 查找可能的硬编码像素值（除了很小的值）
        pixel_pattern = r'(\d{3,})px'  # 3位数以上的像素值
        matches = re.findall(pixel_pattern, self.source_code)
        
        self.assertEqual(
            len(matches),
            0,
            f"发现硬编码的大像素值，可能导致布局问题: {matches}"
        )
    
    def test_layout_comments_and_documentation(self):
        """测试布局相关的注释和文档"""
        # 验证有布局相关的注释
        layout_comment_patterns = [
            r'#.*紧凑布局',
            r'#.*两列布局',
            r'#.*列布局',
        ]
        
        comment_found = False
        for pattern in layout_comment_patterns:
            if re.search(pattern, self.source_code, re.IGNORECASE):
                comment_found = True
                break
        
        self.assertTrue(
            comment_found,
            "应该有布局相关的注释说明"
        )
    
    def test_function_docstrings_mention_compact(self):
        """测试函数文档字符串提到了紧凑版"""
        compact_functions = [
            'render_sell_signals_section_compact',
            'render_market_status_compact',
            'render_notification_settings_compact'
        ]
        
        for func_name in compact_functions:
            with self.subTest(function=func_name):
                # 查找函数及其文档字符串
                func_pattern = rf'def {func_name}\(.*?\n\s*""".*?"""'
                func_match = re.search(func_pattern, self.source_code, re.DOTALL)
                
                if func_match:
                    func_source = func_match.group(0)
                    
                    # 验证文档字符串提到了紧凑版
                    compact_keywords = ['紧凑', 'compact', '紧凑版']
                    has_compact_mention = any(
                        keyword in func_source.lower() 
                        for keyword in compact_keywords
                    )
                    
                    self.assertTrue(
                        has_compact_mention,
                        f"{func_name} 的文档字符串应该提到紧凑版"
                    )


if __name__ == '__main__':
    unittest.main()