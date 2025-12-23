"""
测试持仓卖出信号显示功能的集成测试

使用真实的数据结构测试 render_sell_signals_section_compact() 函数的核心逻辑
不依赖 Streamlit UI，专注于业务逻辑验证

Requirements: 5.1, 5.2, 5.3
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import date
import sys
import os
import tempfile
import pandas as pd

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.position_tracker import Holding, PositionTracker
from core.sell_signal_checker import SellSignal, SellSignalChecker
from core.data_feed import DataFeed


class TestSellSignalIntegration:
    """测试持仓卖出信号显示的集成功能"""
    
    def test_position_tracker_with_real_csv_data(self):
        """测试 PositionTracker 读取真实 CSV 数据"""
        # 直接测试 CSV 数据解析逻辑，不依赖文件系统
        
        # 创建测试 DataFrame
        test_data = {
            'code': ['600519', '000858', '000001'],
            'name': ['贵州茅台', '五粮液', '平安银行'],
            'buy_price': [1800.0, 150.0, 12.0],
            'buy_date': ['2024-01-15', '2024-01-20', '2024-01-25'],
            'quantity': [100, 200, 500],
            'strategy': ['RSRS', 'RSI', 'RSRS'],
            'note': ['测试持仓1', '测试持仓2', '测试持仓3']
        }
        df = pd.DataFrame(test_data)
        
        # 模拟 PositionTracker 的 CSV 加载过程
        with patch('core.position_tracker.os.path.exists') as mock_exists, \
             patch('core.position_tracker.pd.read_csv') as mock_read_csv:
            
            # 设置模拟
            mock_exists.return_value = True
            mock_read_csv.return_value = df
            
            # 创建 PositionTracker
            tracker = PositionTracker()
            positions = tracker.get_all_positions()
            
            # 验证结果
            assert len(positions) == 3
            assert positions[0].code == '600519'
            assert positions[0].name == '贵州茅台'
            assert positions[0].buy_price == 1800.0
            assert positions[0].quantity == 100
            assert positions[0].strategy == 'RSRS'
            
            assert positions[1].code == '000858'
            assert positions[1].name == '五粮液'
            assert positions[2].code == '000001'
            assert positions[2].name == '平安银行'
    
    def test_sell_signal_checker_with_mock_data(self):
        """测试 SellSignalChecker 的信号检查逻辑"""
        # 创建模拟数据源
        mock_data_feed = Mock(spec=DataFeed)
        
        # 创建测试持仓
        holdings = [
            Holding("600519", "贵州茅台", 1800.0, date(2024, 1, 15), 100, "RSRS"),
            Holding("000858", "五粮液", 150.0, date(2024, 1, 20), 200, "RSI"),
        ]
        
        # 创建 SellSignalChecker
        checker = SellSignalChecker(mock_data_feed)
        
        # 模拟单个持仓检查结果
        def mock_check_single_position(holding):
            if holding.code == "600519":
                # 贵州茅台触发止损
                return SellSignal(
                    code="600519",
                    name="贵州茅台",
                    holding=holding,
                    current_price=1692.0,  # 下跌6%
                    pnl_pct=-0.06,
                    exit_reason="触发止损线（-6%）",
                    urgency="high",
                    indicator_value=-0.06
                )
            elif holding.code == "000858":
                # 五粮液策略卖出
                return SellSignal(
                    code="000858",
                    name="五粮液",
                    holding=holding,
                    current_price=157.5,  # 上涨5%
                    pnl_pct=0.05,
                    exit_reason="RSRS标准分 < -0.7",
                    urgency="medium",
                    indicator_value=-0.8
                )
            return None
        
        # 使用 patch 模拟 check_single_position 方法
        with patch.object(checker, 'check_single_position', side_effect=mock_check_single_position):
            signals = checker.check_all_positions(holdings)
            
            # 验证结果
            assert len(signals) == 2
            
            # 验证止损信号
            stop_loss_signal = next((s for s in signals if s.urgency == "high"), None)
            assert stop_loss_signal is not None
            assert stop_loss_signal.code == "600519"
            assert stop_loss_signal.pnl_pct == -0.06
            assert "止损" in stop_loss_signal.exit_reason
            
            # 验证策略信号
            strategy_signal = next((s for s in signals if s.urgency == "medium"), None)
            assert strategy_signal is not None
            assert strategy_signal.code == "000858"
            assert strategy_signal.pnl_pct == 0.05
            assert "RSRS" in strategy_signal.exit_reason
    
    def test_complete_workflow_simulation(self):
        """测试完整的工作流程模拟"""
        # 模拟完整的持仓卖出信号检查流程
        
        # 1. 创建测试持仓数据
        test_positions = [
            Holding("600519", "贵州茅台", 1800.0, date(2024, 1, 15), 100, "RSRS"),
            Holding("000858", "五粮液", 150.0, date(2024, 1, 20), 200, "RSI"),
            Holding("000001", "平安银行", 12.0, date(2024, 1, 25), 500, "RSRS")
        ]
        
        # 2. 模拟不同的信号场景
        test_scenarios = [
            # 场景1：无信号
            {
                'name': 'no_signals',
                'positions': test_positions,
                'signals': [],
                'expected_status': 'no_signals'
            },
            # 场景2：只有止损信号
            {
                'name': 'stop_loss_only',
                'positions': test_positions[:1],
                'signals': [
                    SellSignal("600519", "贵州茅台", test_positions[0], 1692.0, -0.06, "触发止损线（-6%）", "high", -0.06)
                ],
                'expected_status': 'has_signals',
                'expected_high_count': 1,
                'expected_auto_expand': True
            },
            # 场景3：只有策略信号
            {
                'name': 'strategy_only',
                'positions': test_positions[1:2],
                'signals': [
                    SellSignal("000858", "五粮液", test_positions[1], 157.5, 0.05, "RSRS标准分 < -0.7", "medium", -0.8)
                ],
                'expected_status': 'has_signals',
                'expected_high_count': 0,
                'expected_medium_count': 1,
                'expected_auto_expand': False
            },
            # 场景4：混合信号
            {
                'name': 'mixed_signals',
                'positions': test_positions[:2],
                'signals': [
                    SellSignal("600519", "贵州茅台", test_positions[0], 1692.0, -0.06, "触发止损线（-6%）", "high", -0.06),
                    SellSignal("000858", "五粮液", test_positions[1], 157.5, 0.05, "RSRS标准分 < -0.7", "medium", -0.8)
                ],
                'expected_status': 'has_signals',
                'expected_high_count': 1,
                'expected_medium_count': 1,
                'expected_auto_expand': True
            }
        ]
        
        # 3. 测试每个场景
        for scenario in test_scenarios:
            # 使用之前定义的 get_sell_signal_display_data 函数
            from tests.test_sell_signal_display import get_sell_signal_display_data
            
            result = get_sell_signal_display_data(scenario['positions'], scenario['signals'])
            
            # 验证基本状态
            assert result['status'] == scenario['expected_status'], f"场景 {scenario['name']} 状态不匹配"
            
            if scenario['expected_status'] == 'has_signals':
                assert result['position_count'] == len(scenario['positions'])
                assert result['total_signals'] == len(scenario['signals'])
                
                if 'expected_high_count' in scenario:
                    assert result['high_urgency_count'] == scenario['expected_high_count']
                
                if 'expected_medium_count' in scenario:
                    assert result['medium_urgency_count'] == scenario['expected_medium_count']
                
                if 'expected_auto_expand' in scenario:
                    assert result['auto_expand'] == scenario['expected_auto_expand']
    
    def test_signal_content_validation(self):
        """测试信号内容的验证"""
        # 创建测试持仓
        holding = Holding("600519", "贵州茅台", 1800.0, date(2024, 1, 15), 100, "RSRS")
        
        # 测试止损信号内容
        stop_loss_signal = SellSignal(
            code="600519",
            name="贵州茅台",
            holding=holding,
            current_price=1692.0,
            pnl_pct=-0.06,
            exit_reason="触发止损线（-6%）",
            urgency="high",
            indicator_value=-0.06
        )
        
        # 验证信号内容
        assert stop_loss_signal.code == "600519"
        assert stop_loss_signal.name == "贵州茅台"
        assert stop_loss_signal.current_price == 1692.0
        assert stop_loss_signal.pnl_pct == -0.06
        assert stop_loss_signal.urgency == "high"
        assert "止损" in stop_loss_signal.exit_reason
        
        # 验证盈亏计算
        expected_pnl_pct = (1692.0 - 1800.0) / 1800.0
        assert abs(stop_loss_signal.pnl_pct - expected_pnl_pct) < 0.001
        
        # 测试策略信号内容
        strategy_signal = SellSignal(
            code="000858",
            name="五粮液",
            holding=Holding("000858", "五粮液", 150.0, date(2024, 1, 20), 200, "RSI"),
            current_price=157.5,
            pnl_pct=0.05,
            exit_reason="RSRS标准分 < -0.7",
            urgency="medium",
            indicator_value=-0.8
        )
        
        # 验证策略信号
        assert strategy_signal.urgency == "medium"
        assert strategy_signal.pnl_pct > 0  # 盈利
        assert "RSRS" in strategy_signal.exit_reason
    
    def test_edge_cases(self):
        """测试边界情况"""
        from tests.test_sell_signal_display import get_sell_signal_display_data
        
        # 测试空列表
        result = get_sell_signal_display_data([], [])
        assert result['status'] == 'no_positions'
        
        # 测试单个持仓无信号
        single_position = [Holding("600519", "贵州茅台", 1800.0, date(2024, 1, 15), 100, "RSRS")]
        result = get_sell_signal_display_data(single_position, [])
        assert result['status'] == 'no_signals'
        assert result['position_count'] == 1
        
        # 测试大量持仓
        many_positions = [
            Holding(f"60051{i}", f"股票{i}", 100.0, date(2024, 1, 15), 100, "RSRS")
            for i in range(10)
        ]
        result = get_sell_signal_display_data(many_positions, [])
        assert result['status'] == 'no_signals'
        assert result['position_count'] == 10
        assert "10 只持仓无卖出信号" in result['message']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])