"""
测试持仓卖出信号显示功能

测试持仓卖出信号的核心逻辑：
- 无持仓情况
- 有持仓但无卖出信号
- 有紧急止损信号
- 有策略卖出信号
- 混合信号情况

Requirements: 5.1, 5.2, 5.3
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import date
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.position_tracker import Holding, PositionTracker
from core.sell_signal_checker import SellSignal, SellSignalChecker
from core.data_feed import DataFeed


def get_sell_signal_display_data(positions, signals):
    """
    获取卖出信号显示数据（从 render_sell_signals_section_compact 提取的核心逻辑）
    
    Args:
        positions: 持仓列表
        signals: 卖出信号列表
    
    Returns:
        dict: 包含显示数据的字典
    """
    if not positions:
        return {
            'status': 'no_positions',
            'message': '当前无持仓'
        }
    
    if not signals:
        return {
            'status': 'no_signals',
            'message': f'✅ {len(positions)} 只持仓无卖出信号',
            'position_count': len(positions)
        }
    
    # 统计信号类型
    high_count = sum(1 for s in signals if s.urgency == "high")
    medium_count = sum(1 for s in signals if s.urgency == "medium")
    
    return {
        'status': 'has_signals',
        'position_count': len(positions),
        'high_urgency_count': high_count,
        'medium_urgency_count': medium_count,
        'total_signals': len(signals),
        'auto_expand': high_count > 0,  # 有紧急信号时自动展开
        'signals': signals
    }


class TestSellSignalDisplayLogic:
    """测试持仓卖出信号显示逻辑"""
    
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
    
    def test_no_positions_display(self):
        """测试无持仓时的显示数据"""
        result = get_sell_signal_display_data([], [])
        
        assert result['status'] == 'no_positions'
        assert result['message'] == '当前无持仓'
    
    def test_positions_no_signals_display(self, sample_holding):
        """测试有持仓但无卖出信号时的显示数据"""
        positions = [sample_holding]
        signals = []
        
        result = get_sell_signal_display_data(positions, signals)
        
        assert result['status'] == 'no_signals'
        assert result['message'] == '✅ 1 只持仓无卖出信号'
        assert result['position_count'] == 1
    
    def test_stop_loss_signal_display(self, sample_holding, sample_stop_loss_signal):
        """测试止损信号显示数据"""
        positions = [sample_holding]
        signals = [sample_stop_loss_signal]
        
        result = get_sell_signal_display_data(positions, signals)
        
        assert result['status'] == 'has_signals'
        assert result['position_count'] == 1
        assert result['high_urgency_count'] == 1
        assert result['medium_urgency_count'] == 0
        assert result['total_signals'] == 1
        assert result['auto_expand'] == True  # 紧急信号自动展开
    
    def test_strategy_signal_display(self, sample_holding, sample_strategy_signal):
        """测试策略卖出信号显示数据"""
        positions = [sample_holding]
        signals = [sample_strategy_signal]
        
        result = get_sell_signal_display_data(positions, signals)
        
        assert result['status'] == 'has_signals'
        assert result['position_count'] == 1
        assert result['high_urgency_count'] == 0
        assert result['medium_urgency_count'] == 1
        assert result['total_signals'] == 1
        assert result['auto_expand'] == False  # 非紧急信号不自动展开
    
    def test_mixed_signals_display(self, sample_holding, sample_stop_loss_signal, sample_strategy_signal):
        """测试混合信号显示数据"""
        # 创建第二个持仓
        second_holding = Holding(
            code="000858",
            name="五粮液",
            buy_price=150.0,
            buy_date=date(2024, 1, 20),
            quantity=200,
            strategy="RSI",
            note="测试持仓2"
        )
        
        # 修改策略信号的持仓信息
        sample_strategy_signal.code = "000858"
        sample_strategy_signal.name = "五粮液"
        sample_strategy_signal.holding = second_holding
        
        positions = [sample_holding, second_holding]
        signals = [sample_stop_loss_signal, sample_strategy_signal]
        
        result = get_sell_signal_display_data(positions, signals)
        
        assert result['status'] == 'has_signals'
        assert result['position_count'] == 2
        assert result['high_urgency_count'] == 1
        assert result['medium_urgency_count'] == 1
        assert result['total_signals'] == 2
        assert result['auto_expand'] == True  # 有紧急信号时自动展开
    
    def test_multiple_positions_no_signals(self):
        """测试多个持仓但无信号的情况"""
        positions = [
            Holding("600519", "贵州茅台", 1800.0, date(2024, 1, 15), 100, "RSRS"),
            Holding("000858", "五粮液", 150.0, date(2024, 1, 20), 200, "RSI"),
            Holding("000001", "平安银行", 12.0, date(2024, 1, 25), 500, "RSRS")
        ]
        signals = []
        
        result = get_sell_signal_display_data(positions, signals)
        
        assert result['status'] == 'no_signals'
        assert result['message'] == '✅ 3 只持仓无卖出信号'
        assert result['position_count'] == 3


class TestSellSignalContent:
    """测试卖出信号内容格式"""
    
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
    
    def test_stop_loss_signal_content(self, sample_holding):
        """测试止损信号内容"""
        signal = SellSignal(
            code="600519",
            name="贵州茅台",
            holding=sample_holding,
            current_price=1692.0,
            pnl_pct=-0.06,
            exit_reason="触发止损线（-6%）",
            urgency="high",
            indicator_value=-0.06
        )
        
        # 验证信号属性
        assert signal.code == "600519"
        assert signal.name == "贵州茅台"
        assert signal.current_price == 1692.0
        assert signal.pnl_pct == -0.06
        assert signal.urgency == "high"
        assert "止损" in signal.exit_reason
    
    def test_strategy_signal_content(self, sample_holding):
        """测试策略信号内容"""
        signal = SellSignal(
            code="600519",
            name="贵州茅台",
            holding=sample_holding,
            current_price=1890.0,
            pnl_pct=0.05,
            exit_reason="RSRS标准分 < -0.7",
            urgency="medium",
            indicator_value=-0.8
        )
        
        # 验证信号属性
        assert signal.code == "600519"
        assert signal.name == "贵州茅台"
        assert signal.current_price == 1890.0
        assert signal.pnl_pct == 0.05
        assert signal.urgency == "medium"
        assert "RSRS" in signal.exit_reason


class TestPositionTrackerIntegration:
    """测试与 PositionTracker 的集成"""
    
    @patch('core.position_tracker.os.path.exists')
    @patch('core.position_tracker.pd.read_csv')
    def test_position_tracker_get_all_positions(self, mock_read_csv, mock_exists):
        """测试 PositionTracker.get_all_positions() 方法"""
        # 模拟 CSV 文件存在
        mock_exists.return_value = True
        
        # 模拟 CSV 数据
        import pandas as pd
        mock_df = pd.DataFrame({
            'code': ['600519', '000858'],
            'name': ['贵州茅台', '五粮液'],
            'buy_price': [1800.0, 150.0],
            'buy_date': ['2024-01-15', '2024-01-20'],
            'quantity': [100, 200],
            'strategy': ['RSRS', 'RSI'],
            'note': ['测试1', '测试2']
        })
        mock_read_csv.return_value = mock_df
        
        # 创建 PositionTracker 实例
        tracker = PositionTracker()
        positions = tracker.get_all_positions()
        
        # 验证结果
        assert len(positions) == 2
        assert positions[0].code == '600519'
        assert positions[0].name == '贵州茅台'
        assert positions[1].code == '000858'
        assert positions[1].name == '五粮液'


class TestSellSignalCheckerIntegration:
    """测试与 SellSignalChecker 的集成"""
    
    def test_sell_signal_checker_no_signals(self):
        """测试 SellSignalChecker 无信号情况"""
        # 创建模拟数据源
        mock_data_feed = Mock(spec=DataFeed)
        
        # 创建检查器
        checker = SellSignalChecker(mock_data_feed)
        
        # 模拟无信号情况
        with patch.object(checker, 'check_single_position', return_value=None):
            positions = [
                Holding("600519", "贵州茅台", 1800.0, date(2024, 1, 15), 100, "RSRS")
            ]
            signals = checker.check_all_positions(positions)
            
            assert signals == []
    
    def test_sell_signal_checker_with_signals(self):
        """测试 SellSignalChecker 有信号情况"""
        # 创建模拟数据源
        mock_data_feed = Mock(spec=DataFeed)
        
        # 创建检查器
        checker = SellSignalChecker(mock_data_feed)
        
        # 创建示例持仓和信号
        holding = Holding("600519", "贵州茅台", 1800.0, date(2024, 1, 15), 100, "RSRS")
        expected_signal = SellSignal(
            code="600519",
            name="贵州茅台",
            holding=holding,
            current_price=1692.0,
            pnl_pct=-0.06,
            exit_reason="触发止损线（-6%）",
            urgency="high",
            indicator_value=-0.06
        )
        
        # 模拟有信号情况
        with patch.object(checker, 'check_single_position', return_value=expected_signal):
            positions = [holding]
            signals = checker.check_all_positions(positions)
            
            assert len(signals) == 1
            assert signals[0].code == "600519"
            assert signals[0].urgency == "high"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])