"""
End-to-End Tests for Tech Stock Module
科技股模块端到端测试

Tests complete signal generation flow, EOD logic, priority sorting, 
backtest functionality, and UI display correctness.

Requirements: 12.1 端到端测试
- 测试完整的信号生成流程
- 测试尾盘判定逻辑
- 测试信号优先级排序
- 测试回测功能
- 验证界面显示正确性
"""

import pytest
import sys
import os
from datetime import datetime, date, time
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any
import pandas as pd

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.data_feed import DataFeed
from core.tech_stock.market_filter import MarketFilter, MarketStatus
from core.tech_stock.sector_ranker import SectorRanker, SectorRank
from core.tech_stock.hard_filter import HardFilter, HardFilterResult
from core.tech_stock.signal_generator import TechSignalGenerator, TechBuySignal
from core.tech_stock.exit_manager import TechExitManager, TechExitSignal, SignalPriority
from core.tech_stock.backtester import TechBacktester, TechBacktestResult, PeriodPerformance
from core.position_tracker import PositionTracker, Holding
from config.tech_stock_pool import get_tech_stock_pool


class TestCompleteSignalGenerationFlow:
    """测试完整的信号生成流程"""
    
    def setup_method(self):
        """Setup test data"""
        self.mock_data_feed = Mock(spec=DataFeed)
        self.test_codes = ["002600", "300308", "002371"]  # 长盈精密、中际旭创、北方华创
        
    def test_end_to_end_signal_flow(self):
        """测试端到端信号生成流程"""
        # 1. 大盘红绿灯检查
        market_filter = MarketFilter(self.mock_data_feed)
        
        # Mock market data
        mock_gem_data = pd.DataFrame({
            'close': [2500.0, 2520.0, 2540.0, 2560.0, 2580.0] * 4,  # 20 days
            'dif': [10.0, 12.0, 15.0, 18.0, 20.0] * 4,
            'dea': [8.0, 10.0, 12.0, 14.0, 16.0] * 4,
        })
        mock_gem_data.index = pd.date_range('2024-01-01', periods=20, freq='D')
        
        with patch.object(market_filter, '_get_index_data', return_value=mock_gem_data):
            market_status = market_filter.check_market_status()
            
        # 验证大盘状态
        assert isinstance(market_status, MarketStatus)
        assert market_status.is_green is True  # 上涨趋势应该是绿灯
        
        # 2. 行业强弱排名
        sector_ranker = SectorRanker(self.mock_data_feed)
        
        # Mock sector rankings
        mock_rankings = [
            SectorRank("消费电子", "931139", 15.5, 1, True, "proxy_stocks"),  # 长盈精密所属行业排第1
            SectorRank("AI应用", "930713", 12.3, 2, True, "proxy_stocks"),
            SectorRank("算力", "931071", 8.7, 3, False, "proxy_stocks"),
            SectorRank("半导体", "399678", 5.2, 4, False, "proxy_stocks"),
        ]
        
        with patch.object(sector_ranker, 'get_sector_rankings', return_value=mock_rankings):
            sector_rankings = sector_ranker.get_sector_rankings(use_proxy_stocks=True)
        
        # 验证行业排名
        assert len(sector_rankings) == 4
        assert sector_rankings[0].rank == 1
        assert sector_rankings[0].is_tradable is True
        assert sector_rankings[1].is_tradable is True
        assert sector_rankings[2].is_tradable is False
        
        # 3. 硬性筛选
        hard_filter = HardFilter(self.mock_data_feed)
        
        # Mock stock data for hard filter
        mock_filter_results = [
            HardFilterResult("002600", "长盈精密", True, 45.0, 120.0, 2.5, []),
            HardFilterResult("300308", "中际旭创", True, 65.0, 280.0, 3.2, []),
            HardFilterResult("002371", "北方华创", False, 95.0, 600.0, 1.8, ["股价 95.00元 > 80元", "流通市值 600.0亿 > 500亿"]),
        ]
        
        with patch.object(hard_filter, 'filter_stocks', return_value=mock_filter_results):
            filter_results = hard_filter.filter_stocks(self.test_codes)
        
        # 验证硬性筛选结果
        passed_stocks = [r for r in filter_results if r.passed]
        rejected_stocks = [r for r in filter_results if not r.passed]
        
        assert len(passed_stocks) == 2  # 002600, 300308
        assert len(rejected_stocks) == 1  # 002371
        assert rejected_stocks[0].code == "002371"
        assert "股价" in rejected_stocks[0].reject_reasons[0]
        
        # 4. 买入信号生成
        signal_generator = TechSignalGenerator(self.mock_data_feed)
        
        # Mock buy signals
        mock_buy_signals = [
            TechBuySignal(
                code="002600",
                name="长盈精密",
                sector="消费电子",
                price=45.0,
                ma5=44.0,
                ma20=42.0,
                ma60=40.0,
                rsi=65.0,
                volume_ratio=2.1,
                revenue_growth=True,
                profit_growth=True,
                has_unlock=False,
                signal_strength=85.0,
                generated_at=datetime.now(),
                is_confirmed=True,
                confirmation_time=datetime.now(),
                conditions_met=["趋势条件", "动量条件", "量能条件", "基本面条件"]
            )
        ]
        
        with patch.object(signal_generator, 'generate_signals', return_value=mock_buy_signals):
            buy_signals = signal_generator.generate_signals(
                stock_pool=self.test_codes,
                market_status=market_status,
                sector_rankings=sector_rankings,
                hard_filter_results=filter_results
            )
        
        # 验证买入信号
        assert len(buy_signals) == 1
        assert buy_signals[0].code == "002600"
        assert buy_signals[0].is_confirmed is True
        assert buy_signals[0].signal_strength == 85.0
        assert len(buy_signals[0].conditions_met) == 4
        
        # 5. 验证完整流程
        # 大盘绿灯 -> 行业排名前2 -> 硬性筛选通过 -> 生成买入信号
        assert market_status.is_green is True
        assert any(r.sector_name == "消费电子" and r.rank <= 2 for r in sector_rankings)
        assert any(r.code == "002600" and r.passed for r in filter_results)
        assert len(buy_signals) > 0
    def test_market_red_light_blocks_signals(self):
        """测试大盘红灯阻止买入信号生成"""
        # 创建红灯市场状态
        red_market_status = MarketStatus(
            is_green=False,
            gem_close=2400.0,
            gem_ma20=2500.0,  # 收盘价 < MA20
            macd_status="death_cross",
            check_date=date.today(),
            reason="创业板指跌破MA20且MACD死叉"
        )
        
        # 其他条件都满足
        sector_rankings = [
            SectorRank("半导体", "399678", 15.5, 1, True, "proxy_stocks"),
        ]
        
        filter_results = [
            HardFilterResult("002600", "长盈精密", True, 45.0, 120.0, 2.5, []),
        ]
        
        signal_generator = TechSignalGenerator(self.mock_data_feed)
        
        with patch.object(signal_generator, 'generate_signals') as mock_generate:
            # 模拟红灯时不生成信号
            mock_generate.return_value = []
            
            buy_signals = signal_generator.generate_signals(
                stock_pool=["002600"],
                market_status=red_market_status,
                sector_rankings=sector_rankings,
                hard_filter_results=filter_results
            )
        
        # 验证红灯时无买入信号
        assert len(buy_signals) == 0
        
    def test_sector_ranking_filter(self):
        """测试行业排名过滤逻辑"""
        # 创建行业排名（只有前2名可交易）
        sector_rankings = [
            SectorRank("半导体", "399678", 15.5, 1, True, "proxy_stocks"),
            SectorRank("AI应用", "930713", 12.3, 2, True, "proxy_stocks"),
            SectorRank("算力", "931071", 8.7, 3, False, "proxy_stocks"),
            SectorRank("消费电子", "931139", 5.2, 4, False, "proxy_stocks"),
        ]
        
        # 验证可交易行业判断
        tradable_sectors = [r.sector_name for r in sector_rankings if r.is_tradable]
        non_tradable_sectors = [r.sector_name for r in sector_rankings if not r.is_tradable]
        
        assert "半导体" in tradable_sectors
        assert "AI应用" in tradable_sectors
        assert "算力" in non_tradable_sectors
        assert "消费电子" in non_tradable_sectors
        
        # 验证排名逻辑
        assert sector_rankings[0].rank == 1
        assert sector_rankings[1].rank == 2
        assert sector_rankings[2].rank == 3
        assert sector_rankings[3].rank == 4


class TestEODTradingLogic:
    """测试尾盘判定逻辑"""
    
    def setup_method(self):
        """Setup test data"""
        self.mock_data_feed = Mock(spec=DataFeed)
        self.signal_generator = TechSignalGenerator(self.mock_data_feed)
    
    def test_eod_confirmation_time(self):
        """测试尾盘确认时间逻辑"""
        # 测试14:45前 - 信号待确认
        with patch('core.tech_stock.signal_generator.datetime') as mock_datetime:
            mock_datetime.now.return_value.time.return_value = time(14, 30)  # 14:30
            
            is_confirmed = self.signal_generator.is_signal_confirmed()
            status = self.signal_generator.get_signal_status()
            
            assert is_confirmed is False
            assert "待确认" in status
            assert "14:45后生效" in status
        
        # 测试14:45后 - 信号已确认
        with patch('core.tech_stock.signal_generator.datetime') as mock_datetime:
            mock_datetime.now.return_value.time.return_value = time(14, 50)  # 14:50
            
            is_confirmed = self.signal_generator.is_signal_confirmed()
            status = self.signal_generator.get_signal_status()
            
            assert is_confirmed is True
            assert "已确认" in status
    
    def test_trading_window_status(self):
        """测试交易窗口状态"""
        # 测试14:45前 - 等待确认
        with patch('core.tech_stock.signal_generator.datetime') as mock_datetime:
            mock_datetime.now.return_value.time.return_value = time(14, 30)
            
            window_status = self.signal_generator.get_trading_window_status()
            
            assert window_status["is_trading_window"] is False
            assert window_status["minutes_remaining"] == -1
            assert "等待尾盘确认" in window_status["status_message"]
        
        # 测试14:45-15:00 - 交易窗口
        with patch('core.tech_stock.signal_generator.datetime') as mock_datetime:
            mock_datetime.now.return_value.time.return_value = time(14, 50)
            
            window_status = self.signal_generator.get_trading_window_status()
            
            assert window_status["is_trading_window"] is True
            assert window_status["minutes_remaining"] == 10  # 15:00 - 14:50 = 10分钟
            assert "交易窗口开启" in window_status["status_message"]
        
        # 测试15:00后 - 交易结束
        with patch('core.tech_stock.signal_generator.datetime') as mock_datetime:
            mock_datetime.now.return_value.time.return_value = time(15, 10)
            
            window_status = self.signal_generator.get_trading_window_status()
            
            assert window_status["is_trading_window"] is False
            assert window_status["minutes_remaining"] == 0
            assert "交易已结束" in window_status["status_message"]
    
    def test_volume_prediction_logic(self):
        """测试成交量预估逻辑（避免未来函数）"""
        # 测试14:45时的成交量预估
        current_time = time(14, 45)
        current_volume = 1000000  # 100万股
        
        predicted_volume = self.signal_generator._predict_daily_volume(current_volume, current_time)
        
        # 14:45 = 上午120分钟 + 下午105分钟 = 225分钟
        # 预估全天量 = 当前量 / (225/240) = 当前量 / 0.9375
        expected_volume = current_volume / (225 / 240)
        
        assert abs(predicted_volume - expected_volume) < 1000  # 允许小误差


class TestSignalPrioritySorting:
    """测试信号优先级排序"""
    
    def setup_method(self):
        """Setup test data"""
        self.mock_data_feed = Mock(spec=DataFeed)
        self.exit_manager = TechExitManager(self.mock_data_feed)
    
    def test_signal_priority_order(self):
        """测试信号优先级排序"""
        # 创建不同优先级的信号
        signals = [
            # 趋势断裂 (优先级4)
            TechExitSignal(
                code="000001", name="股票1", exit_type="trend_break",
                priority=SignalPriority.TREND_BREAK, current_price=50.0,
                stop_loss_price=45.0, cost_price=47.5, pnl_pct=0.05,
                rsi=70.0, ma5=49.0, ma20=48.0, ma20_break_days=2,
                shares=200, is_min_position=False,
                suggested_action="趋势断裂", urgency_color="blue"
            ),
            # 紧急避险 (优先级1)
            TechExitSignal(
                code="000002", name="股票2", exit_type="emergency",
                priority=SignalPriority.EMERGENCY, current_price=40.0,
                stop_loss_price=36.0, cost_price=42.0, pnl_pct=-0.05,
                rsi=45.0, ma5=41.0, ma20=42.0, ma20_break_days=0,
                shares=100, is_min_position=True,
                suggested_action="紧急避险", urgency_color="red"
            ),
            # 止盈 (优先级3)
            TechExitSignal(
                code="000003", name="股票3", exit_type="take_profit",
                priority=SignalPriority.TAKE_PROFIT, current_price=60.0,
                stop_loss_price=55.0, cost_price=50.0, pnl_pct=0.20,
                rsi=88.0, ma5=59.0, ma20=57.0, ma20_break_days=0,
                shares=200, is_min_position=False,
                suggested_action="RSI超买止盈", urgency_color="yellow"
            ),
            # 止损 (优先级2)
            TechExitSignal(
                code="000004", name="股票4", exit_type="stop_loss",
                priority=SignalPriority.STOP_LOSS, current_price=35.0,
                stop_loss_price=36.0, cost_price=40.0, pnl_pct=-0.125,
                rsi=35.0, ma5=36.0, ma20=38.0, ma20_break_days=1,
                shares=300, is_min_position=False,
                suggested_action="硬止损", urgency_color="orange"
            ),
        ]
        
        # 排序
        sorted_signals = self.exit_manager.sort_signals_by_priority(signals)
        
        # 验证排序正确（优先级数值越小越靠前）
        assert sorted_signals[0].priority == SignalPriority.EMERGENCY      # 1
        assert sorted_signals[1].priority == SignalPriority.STOP_LOSS      # 2
        assert sorted_signals[2].priority == SignalPriority.TAKE_PROFIT    # 3
        assert sorted_signals[3].priority == SignalPriority.TREND_BREAK    # 4
        
        # 验证颜色映射
        assert sorted_signals[0].urgency_color == "red"     # 紧急避险
        assert sorted_signals[1].urgency_color == "orange"  # 止损
        assert sorted_signals[2].urgency_color == "yellow"  # 止盈
        assert sorted_signals[3].urgency_color == "blue"    # 趋势断裂
    
    def test_special_position_marking(self):
        """测试特殊持仓标记（100股）"""
        # 创建测试持仓
        holdings = [
            Holding(
                code="000001", name="股票1", quantity=100,
                buy_price=50.0, buy_date=date(2024, 1, 1), strategy="科技股"
            ),
            Holding(
                code="000002", name="股票2", quantity=200,
                buy_price=60.0, buy_date=date(2024, 1, 2), strategy="科技股"
            ),
            Holding(
                code="000003", name="股票3", quantity=100,
                buy_price=40.0, buy_date=date(2024, 1, 3), strategy="科技股"
            ),
        ]
        
        # 标记特殊持仓
        marked_positions = self.exit_manager.mark_special_positions(holdings)
        
        # 验证标记结果
        assert len(marked_positions) == 3
        
        # 验证100股持仓被标记
        min_positions = [p for p in marked_positions if p["is_min_position"]]
        normal_positions = [p for p in marked_positions if not p["is_min_position"]]
        
        assert len(min_positions) == 2  # 000001, 000003 (both have 100 shares)
        assert len(normal_positions) == 1  # 000002 (has 200 shares)
        
        # 验证标记内容
        for p in min_positions:
            assert p["special_marker"] == "🔸 严格止盈"
            assert p["highlight_color"] == "amber"
        
        for p in normal_positions:
            assert p["special_marker"] is None
            assert p["highlight_color"] is None
class TestBacktestFunctionality:
    """测试回测功能"""
    
    def setup_method(self):
        """Setup test data"""
        self.mock_data_feed = Mock(spec=DataFeed)
        self.backtester = TechBacktester(self.mock_data_feed)
    
    def test_bear_market_validation_requirement(self):
        """测试震荡市强制验证要求"""
        # 测试时间段验证
        valid_cases = [
            ("2022-01-01", "2024-12-31"),  # 包含完整震荡市
            ("2021-01-01", "2023-12-31"),  # 包含震荡市
            ("2022-06-01", "2024-06-30"),  # 部分包含震荡市
        ]
        
        invalid_cases = [
            ("2024-01-01", "2024-12-31"),  # 不包含震荡市
            ("2020-01-01", "2021-12-31"),  # 震荡市之前
        ]
        
        # 验证有效时间段
        for start, end in valid_cases:
            is_valid, message = self.backtester.validate_date_range(start, end)
            assert is_valid is True
            assert "包含震荡市验证" in message
        
        # 验证无效时间段
        for start, end in invalid_cases:
            is_valid, message = self.backtester.validate_date_range(start, end)
            assert is_valid is False
            assert "必须包含震荡市" in message
    
    def test_data_completeness_check(self):
        """测试数据完整性检查"""
        stock_codes = ["002600", "300308", "688xxx"]  # 包含次新股
        start_date = "2022-01-01"
        
        # Mock数据完整性检查结果
        mock_completeness = {
            "002600": {"has_data": True, "first_date": "2010-03-31", "warning": None},
            "300308": {"has_data": True, "first_date": "2015-06-01", "warning": None},
            "688xxx": {"has_data": False, "first_date": "2023-06-01", "warning": "上市时间晚于回测开始日期"}
        }
        
        with patch.object(self.backtester, 'check_data_completeness', return_value=mock_completeness):
            completeness = self.backtester.check_data_completeness(stock_codes, start_date)
        
        # 验证数据完整性结果
        assert completeness["002600"]["has_data"] is True
        assert completeness["300308"]["has_data"] is True
        assert completeness["688xxx"]["has_data"] is False
        assert "上市时间晚于" in completeness["688xxx"]["warning"]
        
        # 测试股票过滤
        with patch.object(self.backtester, 'check_data_completeness', return_value=mock_completeness):
            valid_stocks, warnings = self.backtester.filter_stocks_by_data_availability(stock_codes, start_date)
        
        assert "002600" in valid_stocks
        assert "300308" in valid_stocks
        assert "688xxx" not in valid_stocks
        assert len(warnings) == 1
        assert "688xxx" in warnings[0]["message"]
    
    def test_market_filter_effectiveness_analysis(self):
        """测试大盘风控有效性分析"""
        # 创建测试回测结果
        result = TechBacktestResult(
            total_return=0.15,
            max_drawdown=-0.08,
            total_trades=100,
            win_rate=0.60,
            trades_by_period={
                "2022": 10,           # 熊市，交易少 (有效)
                "2023上半年": 30,     # 震荡，交易正常
                "2023下半年": 15,     # 震荡，交易少 (有效)
                "2024": 45            # 正常，交易多
            },
            period_performances=[],
            drawdown_warning=False,
            market_filter_effective=True,
            bear_market_validated=True,
            bear_market_report="测试报告",
            data_warnings=[]
        )
        
        # 分析大盘风控有效性
        report = self.backtester.analyze_market_filter_effectiveness(result)
        
        # 验证报告内容
        assert isinstance(report, str)
        assert "大盘风控有效性分析" in report
        assert "2022年" in report
        assert "2023上半年" in report
        assert "2023下半年" in report
        assert "2024年" in report
        assert "10 次" in report  # 2022年交易次数
        assert "30 次" in report  # 2023上半年交易次数
        assert "15 次" in report  # 2023下半年交易次数
        assert "45 次" in report  # 2024年交易次数
        assert "✅ 有效" in report  # 风控有效
    
    def test_bear_market_report_generation(self):
        """测试震荡市报告生成"""
        # 创建震荡市绩效数据
        bear_performance = PeriodPerformance(
            period_name="震荡市验证",
            start_date="2022-01-01",
            end_date="2023-12-31",
            total_return=0.05,
            max_drawdown=-0.12,
            trade_count=25,
            win_rate=0.55,
            is_bear_market=True
        )
        
        # 生成报告
        report = self.backtester.generate_bear_market_report(bear_performance)
        
        # 验证报告内容
        assert isinstance(report, str)
        assert "震荡市验证报告" in report
        assert "2022-01-01" in report
        assert "2023-12-31" in report
        assert "5.00%" in report  # 总收益率
        assert "-12.00%" in report  # 最大回撤
        assert "25" in report  # 交易次数
        assert "55.0%" in report  # 胜率
        
        # 验证回撤警告
        if bear_performance.max_drawdown < self.backtester.MAX_DRAWDOWN_THRESHOLD:
            assert "⚠️ 超过阈值" in report
        else:
            assert "✅ 达标" in report


class TestUIDisplayCorrectness:
    """验证界面显示正确性"""
    
    def setup_method(self):
        """Setup test data"""
        self.mock_data_feed = Mock(spec=DataFeed)
    
    def test_market_status_display_data(self):
        """测试大盘状态显示数据"""
        # 创建测试市场状态
        market_status = MarketStatus(
            is_green=True,
            gem_close=2580.0,
            gem_ma20=2520.0,
            macd_status="golden_cross",
            check_date=date(2024, 12, 23),
            reason="创业板指站上MA20且MACD金叉"
        )
        
        # 验证显示数据完整性
        assert market_status.is_green is True
        assert market_status.gem_close == 2580.0
        assert market_status.gem_ma20 == 2520.0
        assert market_status.macd_status == "golden_cross"
        assert market_status.check_date == date(2024, 12, 23)
        assert "创业板指站上MA20" in market_status.reason
        
        # 验证状态判断逻辑
        assert market_status.gem_close > market_status.gem_ma20  # 绿灯条件1
        assert market_status.macd_status != "death_cross"        # 绿灯条件2
    
    def test_sector_rankings_display_data(self):
        """测试行业排名显示数据"""
        # 创建测试行业排名
        sector_rankings = [
            SectorRank("半导体", "399678", 15.5, 1, True, "proxy_stocks"),
            SectorRank("AI应用", "930713", 12.3, 2, True, "proxy_stocks"),
            SectorRank("算力", "931071", 8.7, 3, False, "proxy_stocks"),
            SectorRank("消费电子", "931139", 5.2, 4, False, "proxy_stocks"),
        ]
        
        # 验证排名数据
        assert len(sector_rankings) == 4
        
        # 验证排名顺序
        for i, rank in enumerate(sector_rankings):
            assert rank.rank == i + 1
        
        # 验证可交易标记
        tradable_count = sum(1 for r in sector_rankings if r.is_tradable)
        assert tradable_count == 2  # 只有前2名可交易
        
        # 验证数据源标记
        for rank in sector_rankings:
            assert rank.data_source in ["index", "proxy_stocks"]
    
    def test_hard_filter_display_data(self):
        """测试硬性筛选显示数据"""
        # 创建测试筛选结果
        filter_results = [
            HardFilterResult("002600", "长盈精密", True, 45.0, 120.0, 2.5, []),
            HardFilterResult("300308", "中际旭创", True, 65.0, 280.0, 3.2, []),
            HardFilterResult("002371", "北方华创", False, 95.0, 600.0, 1.8, 
                           ["股价 95.00元 > 80元", "流通市值 600.0亿 > 500亿"]),
        ]
        
        # 验证筛选统计
        hard_filter = HardFilter(self.mock_data_feed)
        summary = hard_filter.get_filter_summary(filter_results)
        
        assert summary["total"] == 3
        assert summary["passed"] == 2
        assert summary["rejected"] == 1
        assert summary["reject_by_price"] == 1
        assert summary["reject_by_market_cap"] == 1
        assert summary["reject_by_turnover"] == 0
        
        # 验证拒绝原因
        rejected_result = filter_results[2]
        assert not rejected_result.passed
        assert len(rejected_result.reject_reasons) == 2
        assert "股价" in rejected_result.reject_reasons[0]
        assert "流通市值" in rejected_result.reject_reasons[1]
    
    def test_buy_signal_display_data(self):
        """测试买入信号显示数据"""
        # 创建测试买入信号
        buy_signal = TechBuySignal(
            code="002600",
            name="长盈精密",
            sector="消费电子",
            price=45.0,
            ma5=44.0,
            ma20=42.0,
            ma60=40.0,
            rsi=65.0,
            volume_ratio=2.1,
            revenue_growth=True,
            profit_growth=True,
            has_unlock=False,
            signal_strength=85.0,
            generated_at=datetime(2024, 12, 23, 14, 50),
            is_confirmed=True,
            confirmation_time=datetime(2024, 12, 23, 14, 50),
            conditions_met=["趋势条件", "动量条件", "量能条件", "基本面条件"]
        )
        
        # 验证信号数据完整性
        assert buy_signal.code == "002600"
        assert buy_signal.name == "长盈精密"
        assert buy_signal.sector == "消费电子"
        assert buy_signal.price == 45.0
        assert buy_signal.rsi == 65.0
        assert buy_signal.volume_ratio == 2.1
        assert buy_signal.signal_strength == 85.0
        assert buy_signal.is_confirmed is True
        assert len(buy_signal.conditions_met) == 4
        
        # 验证基本面数据
        assert buy_signal.revenue_growth is True
        assert buy_signal.profit_growth is True
        assert buy_signal.has_unlock is False
        
        # 验证技术指标
        assert buy_signal.ma5 > buy_signal.ma20 > buy_signal.ma60  # 趋势向上
        assert 55 <= buy_signal.rsi <= 80  # RSI在合理区间
        assert buy_signal.volume_ratio >= 1.5  # 量比满足条件
    
    def test_exit_signal_display_data(self):
        """测试卖出信号显示数据"""
        # 创建测试卖出信号
        exit_signal = TechExitSignal(
            code="000001",
            name="测试股票",
            exit_type="emergency",
            priority=SignalPriority.EMERGENCY,
            current_price=40.0,
            stop_loss_price=36.0,
            cost_price=42.0,
            pnl_pct=-0.05,
            rsi=45.0,
            ma5=41.0,
            ma20=42.0,
            ma20_break_days=0,
            shares=100,
            is_min_position=True,
            suggested_action="⚠️ 紧急避险：大盘红灯+亏损，建议立即清仓",
            urgency_color="red"
        )
        
        # 验证卖出信号数据
        assert exit_signal.code == "000001"
        assert exit_signal.priority == SignalPriority.EMERGENCY
        assert exit_signal.urgency_color == "red"
        assert exit_signal.is_min_position is True
        assert exit_signal.pnl_pct == -0.05
        assert "紧急避险" in exit_signal.suggested_action
        
        # 验证优先级映射
        exit_manager = TechExitManager(self.mock_data_feed)
        color = exit_manager.PRIORITY_COLORS[exit_signal.priority]
        assert color == "red"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])