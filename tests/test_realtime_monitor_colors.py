"""
Realtime Monitor Color Mapping Tests

测试颜色映射函数，包括信号强度颜色和资金流向颜色。
Property 12: Signal Strength Color Mapping
Property 13: Fund Flow Color Mapping
Validates: Requirements 6.2, 7.3, 7.4
"""

import pytest
import sys
import os
from hypothesis import given, strategies as st, settings

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.realtime_monitor.config import MONITOR_CONFIG


# ==========================================
# 颜色映射函数（从Streamlit页面复制，用于测试）
# ==========================================

def get_signal_strength_color(strength: int) -> str:
    """
    获取信号强度对应的颜色
    
    Property 12: Signal Strength Color Mapping
    For any signal strength S:
    - S >= 80: color = "green"
    - 60 <= S < 80: color = "yellow"
    - S < 60: color = "red"
    
    Requirements: 6.2
    
    Args:
        strength: 信号强度 0-100
        
    Returns:
        str: 颜色名称
    """
    if strength >= MONITOR_CONFIG.signal_strength_high:  # 80
        return "green"
    elif strength >= MONITOR_CONFIG.signal_strength_medium:  # 60
        return "yellow"
    else:
        return "red"


def get_fund_flow_color(fund_flow: float) -> str:
    """
    获取资金流向对应的颜色
    
    Property 13: Fund Flow Color Mapping
    For any fund flow value F:
    - F > 0: color = "green" (inflow)
    - F < 0: color = "red" (outflow)
    - F = 0: color = "gray" (neutral)
    
    Requirements: 7.3, 7.4
    
    Args:
        fund_flow: 资金流向值
        
    Returns:
        str: 颜色名称
    """
    if fund_flow > 0:
        return "green"
    elif fund_flow < 0:
        return "red"
    else:
        return "gray"


# ==========================================
# Property 12: Signal Strength Color Mapping Tests
# ==========================================

class TestSignalStrengthColorMapping:
    """信号强度颜色映射测试"""
    
    def test_strong_signal_green(self):
        """测试强信号（>=80）显示绿色"""
        assert get_signal_strength_color(80) == "green"
        assert get_signal_strength_color(90) == "green"
        assert get_signal_strength_color(100) == "green"
    
    def test_medium_signal_yellow(self):
        """测试中等信号（60-79）显示黄色"""
        assert get_signal_strength_color(60) == "yellow"
        assert get_signal_strength_color(70) == "yellow"
        assert get_signal_strength_color(79) == "yellow"
    
    def test_weak_signal_red(self):
        """测试弱信号（<60）显示红色"""
        assert get_signal_strength_color(0) == "red"
        assert get_signal_strength_color(30) == "red"
        assert get_signal_strength_color(59) == "red"
    
    def test_boundary_values(self):
        """测试边界值"""
        # 80是绿色的边界
        assert get_signal_strength_color(80) == "green"
        assert get_signal_strength_color(79) == "yellow"
        
        # 60是黄色的边界
        assert get_signal_strength_color(60) == "yellow"
        assert get_signal_strength_color(59) == "red"
    
    # Property 12: Signal Strength Color Mapping
    # Feature: realtime-monitor, Property 12: Signal Strength Color Mapping
    @given(strength=st.integers(min_value=0, max_value=100))
    @settings(max_examples=100)
    def test_signal_strength_color_property(self, strength: int):
        """
        Property 12: Signal Strength Color Mapping
        
        For any signal strength S:
        - S >= 80: color = "green"
        - 60 <= S < 80: color = "yellow"
        - S < 60: color = "red"
        
        **Validates: Requirements 6.2**
        """
        color = get_signal_strength_color(strength)
        
        if strength >= 80:
            assert color == "green", f"Expected green for strength {strength}, got {color}"
        elif strength >= 60:
            assert color == "yellow", f"Expected yellow for strength {strength}, got {color}"
        else:
            assert color == "red", f"Expected red for strength {strength}, got {color}"
    
    @given(strength=st.integers(min_value=80, max_value=100))
    @settings(max_examples=50)
    def test_high_strength_always_green(self, strength: int):
        """测试高强度信号始终为绿色"""
        assert get_signal_strength_color(strength) == "green"
    
    @given(strength=st.integers(min_value=60, max_value=79))
    @settings(max_examples=50)
    def test_medium_strength_always_yellow(self, strength: int):
        """测试中等强度信号始终为黄色"""
        assert get_signal_strength_color(strength) == "yellow"
    
    @given(strength=st.integers(min_value=0, max_value=59))
    @settings(max_examples=50)
    def test_low_strength_always_red(self, strength: int):
        """测试低强度信号始终为红色"""
        assert get_signal_strength_color(strength) == "red"


# ==========================================
# Property 13: Fund Flow Color Mapping Tests
# ==========================================

class TestFundFlowColorMapping:
    """资金流向颜色映射测试"""
    
    def test_positive_flow_green(self):
        """测试正资金流向（净流入）显示绿色"""
        assert get_fund_flow_color(100.0) == "green"
        assert get_fund_flow_color(0.01) == "green"
        assert get_fund_flow_color(1000000.0) == "green"
    
    def test_negative_flow_red(self):
        """测试负资金流向（净流出）显示红色"""
        assert get_fund_flow_color(-100.0) == "red"
        assert get_fund_flow_color(-0.01) == "red"
        assert get_fund_flow_color(-1000000.0) == "red"
    
    def test_zero_flow_gray(self):
        """测试零资金流向显示灰色"""
        assert get_fund_flow_color(0.0) == "gray"
        assert get_fund_flow_color(0) == "gray"
    
    # Property 13: Fund Flow Color Mapping
    # Feature: realtime-monitor, Property 13: Fund Flow Color Mapping
    @given(fund_flow=st.floats(min_value=-1e10, max_value=1e10, allow_nan=False, allow_infinity=False))
    @settings(max_examples=100)
    def test_fund_flow_color_property(self, fund_flow: float):
        """
        Property 13: Fund Flow Color Mapping
        
        For any fund flow value F:
        - F > 0: color = "green" (inflow)
        - F < 0: color = "red" (outflow)
        - F = 0: color = "gray" (neutral)
        
        **Validates: Requirements 7.3, 7.4**
        """
        color = get_fund_flow_color(fund_flow)
        
        if fund_flow > 0:
            assert color == "green", f"Expected green for positive flow {fund_flow}, got {color}"
        elif fund_flow < 0:
            assert color == "red", f"Expected red for negative flow {fund_flow}, got {color}"
        else:
            assert color == "gray", f"Expected gray for zero flow {fund_flow}, got {color}"
    
    @given(fund_flow=st.floats(min_value=0.001, max_value=1e10, allow_nan=False, allow_infinity=False))
    @settings(max_examples=50)
    def test_positive_flow_always_green(self, fund_flow: float):
        """测试正资金流向始终为绿色"""
        assert get_fund_flow_color(fund_flow) == "green"
    
    @given(fund_flow=st.floats(min_value=-1e10, max_value=-0.001, allow_nan=False, allow_infinity=False))
    @settings(max_examples=50)
    def test_negative_flow_always_red(self, fund_flow: float):
        """测试负资金流向始终为红色"""
        assert get_fund_flow_color(fund_flow) == "red"


# ==========================================
# 综合测试
# ==========================================

class TestColorMappingIntegration:
    """颜色映射综合测试"""
    
    def test_color_values_are_valid(self):
        """测试颜色值是有效的"""
        valid_colors = {"green", "yellow", "red", "gray"}
        
        # 测试信号强度颜色
        for strength in range(0, 101, 10):
            color = get_signal_strength_color(strength)
            assert color in valid_colors, f"Invalid color {color} for strength {strength}"
        
        # 测试资金流向颜色
        for flow in [-100, -1, 0, 1, 100]:
            color = get_fund_flow_color(flow)
            assert color in valid_colors, f"Invalid color {color} for flow {flow}"
    
    def test_config_thresholds_used(self):
        """测试使用配置中的阈值"""
        # 验证配置值
        assert MONITOR_CONFIG.signal_strength_high == 80
        assert MONITOR_CONFIG.signal_strength_medium == 60
        
        # 验证阈值被正确使用
        assert get_signal_strength_color(MONITOR_CONFIG.signal_strength_high) == "green"
        assert get_signal_strength_color(MONITOR_CONFIG.signal_strength_medium) == "yellow"
        assert get_signal_strength_color(MONITOR_CONFIG.signal_strength_medium - 1) == "red"
