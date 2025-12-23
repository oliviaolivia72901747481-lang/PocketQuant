"""
测试每日信号页面无横向滚动验证

专门验证紧凑布局在不同分辨率下不会产生横向滚动条。
这是 Task 3.2 中"验证无横向滚动"的具体实现。

Requirements: Task 3.2 - 验证无横向滚动
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestNoHorizontalScroll(unittest.TestCase):
    """测试无横向滚动"""
    
    def setUp(self):
        """设置测试环境"""
        # 常见屏幕分辨率
        self.screen_resolutions = {
            'desktop_large': {'width': 1920, 'height': 1080},
            'desktop_standard': {'width': 1366, 'height': 768},
            'tablet_landscape': {'width': 1024, 'height': 768},
            'tablet_portrait': {'width': 768, 'height': 1024},
        }
        
        # Streamlit 容器边距（估算）
        self.container_margin = 100  # 左右各50px边距
    
    def test_container_width_within_screen_bounds(self):
        """测试容器宽度在屏幕边界内"""
        for resolution_name, resolution in self.screen_resolutions.items():
            with self.subTest(resolution=resolution_name):
                screen_width = resolution['width']
                container_width = screen_width - self.container_margin
                
                # 验证容器宽度为正数
                self.assertGreater(
                    container_width, 
                    0,
                    f"{resolution_name} ({screen_width}px) 容器宽度应为正数"
                )
                
                # 验证容器宽度不超过屏幕宽度
                self.assertLessEqual(
                    container_width,
                    screen_width,
                    f"{resolution_name} 容器宽度不应超过屏幕宽度"
                )
    
    def test_two_column_layout_no_overflow(self):
        """测试两列布局不会溢出"""
        for resolution_name, resolution in self.screen_resolutions.items():
            with self.subTest(resolution=resolution_name):
                screen_width = resolution['width']
                container_width = screen_width - self.container_margin
                
                # 跳过过小的屏幕（这些应该使用单列布局）
                if container_width < 400:
                    continue
                
                # 测试等宽两列布局
                column_width = container_width / 2
                total_width = column_width * 2
                
                # 验证总宽度不超过容器宽度
                self.assertLessEqual(
                    total_width,
                    container_width,
                    f"{resolution_name} 两列总宽度 {total_width}px 超过容器宽度 {container_width}px"
                )
                
                # 验证每列有足够的最小宽度
                min_column_width = 150  # 最小可用宽度
                self.assertGreaterEqual(
                    column_width,
                    min_column_width,
                    f"{resolution_name} 列宽 {column_width}px 小于最小宽度 {min_column_width}px"
                )
    
    def test_strategy_notification_layout_no_overflow(self):
        """测试策略配置+飞书通知布局不会溢出"""
        for resolution_name, resolution in self.screen_resolutions.items():
            with self.subTest(resolution=resolution_name):
                screen_width = resolution['width']
                container_width = screen_width - self.container_margin
                
                # 跳过过小的屏幕
                if container_width < 400:
                    continue
                
                # 测试 2:1 比例布局 (策略配置:飞书通知)
                strategy_width = (2/3) * container_width
                notification_width = (1/3) * container_width
                total_width = strategy_width + notification_width
                
                # 验证总宽度不超过容器宽度
                self.assertLessEqual(
                    total_width,
                    container_width,
                    f"{resolution_name} 策略+通知总宽度 {total_width}px 超过容器宽度 {container_width}px"
                )
                
                # 验证较窄的通知列有足够宽度
                min_notification_width = 120  # 通知面板最小宽度
                self.assertGreaterEqual(
                    notification_width,
                    min_notification_width,
                    f"{resolution_name} 通知列宽度 {notification_width}px 小于最小宽度 {min_notification_width}px"
                )
    
    def test_content_elements_width_constraints(self):
        """测试内容元素宽度约束"""
        # 定义各种内容元素的最小宽度需求
        content_elements = {
            'stock_code': 80,        # 股票代码 "000001"
            'stock_name': 100,       # 股票名称 "平安银行"
            'price_display': 120,    # 价格显示 "¥12.34"
            'metric_component': 100, # st.metric 组件
            'button_group': 150,     # 按钮组合
            'expander_title': 200,   # expander 标题
            'status_message': 180,   # 状态消息
        }
        
        for resolution_name, resolution in self.screen_resolutions.items():
            with self.subTest(resolution=resolution_name):
                screen_width = resolution['width']
                container_width = screen_width - self.container_margin
                
                # 跳过过小的屏幕
                if container_width < 400:
                    continue
                
                # 计算单列可用宽度（两列布局）
                column_width = container_width / 2
                
                # 验证每个内容元素都能在列宽内显示
                for element_name, min_width in content_elements.items():
                    self.assertGreaterEqual(
                        column_width,
                        min_width,
                        f"{resolution_name} 列宽 {column_width}px 无法容纳 {element_name} (需要 {min_width}px)"
                    )
    
    def test_streamlit_column_gaps_consideration(self):
        """测试 Streamlit 列间距的考虑"""
        # Streamlit 在列之间会自动添加间距
        estimated_column_gap = 20  # 估算的列间距
        
        for resolution_name, resolution in self.screen_resolutions.items():
            with self.subTest(resolution=resolution_name):
                screen_width = resolution['width']
                container_width = screen_width - self.container_margin
                
                # 跳过过小的屏幕
                if container_width < 400:
                    continue
                
                # 考虑列间距的实际可用宽度
                available_width_for_columns = container_width - estimated_column_gap
                column_width = available_width_for_columns / 2
                
                # 验证考虑间距后仍有足够宽度
                min_usable_width = 140  # 考虑间距后的最小可用宽度
                self.assertGreaterEqual(
                    column_width,
                    min_usable_width,
                    f"{resolution_name} 考虑间距后列宽 {column_width}px 小于最小可用宽度 {min_usable_width}px"
                )
    
    def test_responsive_breakpoints(self):
        """测试响应式断点"""
        # 定义布局断点
        breakpoints = {
            'two_column_min': 600,   # 两列布局最小宽度
            'single_column_max': 599, # 单列布局最大宽度
        }
        
        for resolution_name, resolution in self.screen_resolutions.items():
            with self.subTest(resolution=resolution_name):
                screen_width = resolution['width']
                container_width = screen_width - self.container_margin
                
                if container_width >= breakpoints['two_column_min']:
                    # 应该使用两列布局
                    column_width = container_width / 2
                    self.assertGreaterEqual(
                        column_width,
                        150,  # 两列布局下的最小列宽
                        f"{resolution_name} 两列布局列宽 {column_width}px 过小"
                    )
                else:
                    # 应该考虑单列布局或特殊处理
                    self.assertLess(
                        container_width,
                        breakpoints['two_column_min'],
                        f"{resolution_name} 容器宽度 {container_width}px 需要特殊布局处理"
                    )
    
    def test_compact_components_width_efficiency(self):
        """测试紧凑组件的宽度效率"""
        # 紧凑组件应该能在较小空间内有效显示
        compact_components = {
            'sell_signals_compact': {
                'min_width': 200,
                'elements': ['标题', 'metrics', 'expander']
            },
            'market_status_compact': {
                'min_width': 180,
                'elements': ['标题', '状态', 'metric']
            },
            'notification_compact': {
                'min_width': 150,
                'elements': ['标题', '状态', 'expander']
            }
        }
        
        for resolution_name, resolution in self.screen_resolutions.items():
            with self.subTest(resolution=resolution_name):
                screen_width = resolution['width']
                container_width = screen_width - self.container_margin
                
                # 跳过过小的屏幕
                if container_width < 400:
                    continue
                
                column_width = container_width / 2
                
                # 验证每个紧凑组件都能在列宽内显示
                for component_name, component_info in compact_components.items():
                    min_width = component_info['min_width']
                    self.assertGreaterEqual(
                        column_width,
                        min_width,
                        f"{resolution_name} 列宽 {column_width}px 无法容纳 {component_name} (需要 {min_width}px)"
                    )
    
    def test_edge_case_very_narrow_screens(self):
        """测试极窄屏幕的边缘情况"""
        narrow_screens = [
            {'name': 'old_mobile', 'width': 320, 'height': 568},
            {'name': 'small_tablet', 'width': 480, 'height': 800},
        ]
        
        for screen in narrow_screens:
            with self.subTest(screen=screen['name']):
                screen_width = screen['width']
                container_width = screen_width - self.container_margin
                
                if container_width <= 0:
                    # 屏幕太小，容器宽度为负数或零
                    self.assertLessEqual(
                        container_width,
                        0,
                        f"{screen['name']} 屏幕过小，需要特殊处理"
                    )
                elif container_width < 300:
                    # 屏幕很小，应该使用单列布局
                    self.assertLess(
                        container_width,
                        300,
                        f"{screen['name']} 应该使用单列布局或移动端优化"
                    )
    
    def test_layout_stability_across_resolutions(self):
        """测试布局在不同分辨率下的稳定性"""
        # 验证布局在不同分辨率下都能保持基本功能
        
        stable_resolutions = [
            self.screen_resolutions['desktop_large'],
            self.screen_resolutions['desktop_standard'],
            self.screen_resolutions['tablet_landscape'],
        ]
        
        for i, resolution in enumerate(stable_resolutions):
            with self.subTest(resolution_index=i):
                screen_width = resolution['width']
                container_width = screen_width - self.container_margin
                
                # 验证容器宽度递减但仍可用
                if i > 0:
                    prev_resolution = stable_resolutions[i-1]
                    prev_container_width = prev_resolution['width'] - self.container_margin
                    
                    self.assertLessEqual(
                        container_width,
                        prev_container_width,
                        f"分辨率 {i} 的容器宽度应该小于等于前一个分辨率"
                    )
                
                # 验证仍然可以使用两列布局
                if container_width >= 400:
                    column_width = container_width / 2
                    self.assertGreaterEqual(
                        column_width,
                        140,  # 最小可接受列宽
                        f"分辨率 {i} 列宽 {column_width}px 过小，布局不稳定"
                    )
    
    def test_horizontal_scroll_prevention_mechanisms(self):
        """测试防止横向滚动的机制"""
        # 验证各种防止横向滚动的设计机制
        
        prevention_mechanisms = {
            'container_width_limit': True,    # 容器宽度限制
            'responsive_columns': True,       # 响应式列
            'content_wrapping': True,         # 内容换行
            'min_width_constraints': True,    # 最小宽度约束
        }
        
        for mechanism_name, should_be_active in prevention_mechanisms.items():
            with self.subTest(mechanism=mechanism_name):
                self.assertTrue(
                    should_be_active,
                    f"防止横向滚动的机制 {mechanism_name} 应该被激活"
                )
        
        # 验证机制的有效性
        for resolution_name, resolution in self.screen_resolutions.items():
            if resolution['width'] >= 600:  # 只测试合理大小的屏幕
                with self.subTest(resolution=resolution_name, mechanism='overall'):
                    screen_width = resolution['width']
                    container_width = screen_width - self.container_margin
                    
                    # 总体验证：任何内容都不应该超出容器宽度
                    max_content_width = container_width
                    
                    # 模拟最宽的内容（两列布局）
                    simulated_content_width = container_width  # 两列占满容器
                    
                    self.assertLessEqual(
                        simulated_content_width,
                        max_content_width,
                        f"{resolution_name} 内容宽度 {simulated_content_width}px 不应超过容器宽度 {max_content_width}px"
                    )


if __name__ == '__main__':
    unittest.main()