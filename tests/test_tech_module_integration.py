"""
Integration tests for tech stock module interfaces
验证核心模块间接口正确性
"""
import pytest
from datetime import datetime, date
from core.tech_stock.market_filter import MarketFilter, MarketStatus
from core.tech_stock.sector_ranker import SectorRanker, SectorRank
from core.tech_stock.hard_filter import HardFilter, HardFilterResult
from core.tech_stock.signal_generator import TechSignalGenerator, TechBuySignal
from core.tech_stock.exit_manager import TechExitManager, TechExitSignal, SignalPriority
from core.tech_stock.backtester import TechBacktester, TechBacktestResult, PeriodPerformance
from core.data_feed import DataFeed


class TestModuleInterfaces:
    """测试模块间接口兼容性"""
    
    def test_market_filter_interface(self):
        """测试 MarketFilter 接口"""
        market_filter = MarketFilter()
        status = market_filter.check_market_status()
        
        # 验证返回类型
        assert isinstance(status, MarketStatus)
        
        # 验证必需字段
        assert hasattr(status, 'is_green')
        assert hasattr(status, 'gem_close')
        assert hasattr(status, 'gem_ma20')
        assert hasattr(status, 'macd_status')
        assert hasattr(status, 'check_date')
        assert hasattr(status, 'reason')
        
        # 验证字段类型
        assert isinstance(status.is_green, bool)
        assert isinstance(status.macd_status, str)
        assert isinstance(status.check_date, date)
        assert isinstance(status.reason, str)
    
    def test_sector_ranker_interface(self):
        """测试 SectorRanker 接口"""
        ranker = SectorRanker()
        rankings = ranker.get_sector_rankings(use_proxy_stocks=True)
        
        # 验证返回类型
        assert isinstance(rankings, list)
        
        if rankings:
            # 验证列表元素类型
            assert all(isinstance(r, SectorRank) for r in rankings)
            
            # 验证必需字段
            first_rank = rankings[0]
            assert hasattr(first_rank, 'sector_name')
            assert hasattr(first_rank, 'index_code')
            assert hasattr(first_rank, 'return_20d')
            assert hasattr(first_rank, 'rank')
            assert hasattr(first_rank, 'is_tradable')
            assert hasattr(first_rank, 'data_source')
            
            # 验证字段类型
            assert isinstance(first_rank.sector_name, str)
            assert isinstance(first_rank.rank, int)
            assert isinstance(first_rank.is_tradable, bool)
            assert isinstance(first_rank.data_source, str)
    
    def test_hard_filter_interface(self):
        """测试 HardFilter 接口"""
        hard_filter = HardFilter()
        
        # 测试单个检查方法
        passed, reason = hard_filter._check_price(50.0)
        assert isinstance(passed, bool)
        assert reason is None or isinstance(reason, str)
        
        passed, reason = hard_filter._check_market_cap(100.0)
        assert isinstance(passed, bool)
        assert reason is None or isinstance(reason, str)
        
        passed, reason = hard_filter._check_turnover(2.0)
        assert isinstance(passed, bool)
        assert reason is None or isinstance(reason, str)
    
    def test_signal_generator_interface(self):
        """测试 TechSignalGenerator 接口"""
        generator = TechSignalGenerator()
        
        # 测试时间相关方法
        is_confirmed = generator.is_signal_confirmed()
        assert isinstance(is_confirmed, bool)
        
        status = generator.get_signal_status()
        assert isinstance(status, str)
        
        window_status = generator.get_trading_window_status()
        assert isinstance(window_status, dict)
        assert 'is_trading_window' in window_status
        assert 'minutes_remaining' in window_status
        assert 'status_message' in window_status
    
    def test_exit_manager_interface(self):
        """测试 TechExitManager 接口"""
        exit_manager = TechExitManager()
        
        # 验证优先级枚举
        assert SignalPriority.EMERGENCY == 1
        assert SignalPriority.STOP_LOSS == 2
        assert SignalPriority.TAKE_PROFIT == 3
        assert SignalPriority.TREND_BREAK == 4
        
        # 验证优先级颜色映射
        assert exit_manager.PRIORITY_COLORS[SignalPriority.EMERGENCY] == "red"
        assert exit_manager.PRIORITY_COLORS[SignalPriority.STOP_LOSS] == "orange"
        assert exit_manager.PRIORITY_COLORS[SignalPriority.TAKE_PROFIT] == "yellow"
        assert exit_manager.PRIORITY_COLORS[SignalPriority.TREND_BREAK] == "blue"


class TestModuleDataFlow:
    """测试模块间数据流"""
    
    def test_market_filter_to_signal_generator_flow(self):
        """测试 MarketFilter -> SignalGenerator 数据流"""
        # 获取市场状态
        market_filter = MarketFilter()
        market_status = market_filter.check_market_status()
        
        # 验证市场状态可以传递给信号生成器
        assert isinstance(market_status, MarketStatus)
        assert hasattr(market_status, 'is_green')
        
        # 信号生成器应该能够使用这个状态
        # (实际生成信号需要更多数据，这里只验证接口)
        generator = TechSignalGenerator()
        assert generator is not None
    
    def test_hard_filter_results_structure(self):
        """测试 HardFilter 结果结构"""
        hard_filter = HardFilter()
        
        # 创建测试结果
        result = HardFilterResult(
            code="000001",
            name="测试股票",
            passed=True,
            price=50.0,
            market_cap=100.0,
            avg_turnover=2.0,
            reject_reasons=[]
        )
        
        # 验证结果可以被其他模块使用
        assert result.passed is True
        assert result.code == "000001"
        assert len(result.reject_reasons) == 0
    
    def test_exit_signal_priority_sorting(self):
        """测试卖出信号优先级排序"""
        exit_manager = TechExitManager()
        
        # 创建不同优先级的信号
        signals = [
            TechExitSignal(
                code="000001",
                name="股票1",
                exit_type="trend_break",
                priority=SignalPriority.TREND_BREAK,
                current_price=50.0,
                stop_loss_price=45.0,
                cost_price=47.5,  # 添加 cost_price
                pnl_pct=0.05,
                rsi=70.0,
                ma5=49.0,
                ma20=48.0,
                ma20_break_days=2,
                shares=200,
                is_min_position=False,
                suggested_action="趋势断裂",
                urgency_color="blue"
            ),
            TechExitSignal(
                code="000002",
                name="股票2",
                exit_type="emergency",
                priority=SignalPriority.EMERGENCY,
                current_price=40.0,
                stop_loss_price=36.0,
                cost_price=42.0,  # 添加 cost_price
                pnl_pct=-0.05,
                rsi=45.0,
                ma5=41.0,
                ma20=42.0,
                ma20_break_days=0,
                shares=100,
                is_min_position=True,
                suggested_action="紧急避险",
                urgency_color="red"
            ),
        ]
        
        # 排序
        sorted_signals = exit_manager.sort_signals_by_priority(signals)
        
        # 验证排序正确（紧急避险应该在前）
        assert sorted_signals[0].priority == SignalPriority.EMERGENCY
        assert sorted_signals[1].priority == SignalPriority.TREND_BREAK


class TestModuleConstants:
    """测试模块常量定义"""
    
    def test_hard_filter_constants(self):
        """测试 HardFilter 常量"""
        hard_filter = HardFilter()
        assert hard_filter.MAX_PRICE == 80.0
        assert hard_filter.MIN_MARKET_CAP == 50.0
        assert hard_filter.MAX_MARKET_CAP == 500.0
        assert hard_filter.MIN_AVG_TURNOVER == 1.0
    
    def test_signal_generator_constants(self):
        """测试 TechSignalGenerator 常量"""
        generator = TechSignalGenerator()
        assert generator.RSI_MIN == 55
        assert generator.RSI_MAX == 80
        assert generator.VOLUME_RATIO_MIN == 1.5
    
    def test_exit_manager_constants(self):
        """测试 TechExitManager 常量"""
        assert TechExitManager.HARD_STOP_LOSS == -0.10
        assert TechExitManager.PROFIT_THRESHOLD_1 == 0.05
        assert TechExitManager.PROFIT_THRESHOLD_2 == 0.15
        assert TechExitManager.RSI_OVERBOUGHT == 85
        assert TechExitManager.MA20_BREAK_DAYS == 2
        assert TechExitManager.MIN_POSITION_SHARES == 100
    
    def test_sector_ranker_constants(self):
        """测试 SectorRanker 常量"""
        ranker = SectorRanker()
        
        # 验证行业指数映射
        assert "半导体" in ranker.SECTOR_INDICES
        assert "AI应用" in ranker.SECTOR_INDICES
        assert "算力" in ranker.SECTOR_INDICES
        assert "消费电子" in ranker.SECTOR_INDICES
        
        # 验证龙头股映射
        assert "半导体" in ranker.SECTOR_PROXY_STOCKS
        assert "AI应用" in ranker.SECTOR_PROXY_STOCKS
        assert "算力" in ranker.SECTOR_PROXY_STOCKS
        assert "消费电子" in ranker.SECTOR_PROXY_STOCKS
    
    def test_backtester_constants(self):
        """测试 TechBacktester 常量"""
        backtester = TechBacktester()
        
        # 验证默认测试标的
        assert "002600" in backtester.DEFAULT_STOCKS
        assert "300308" in backtester.DEFAULT_STOCKS
        assert "002371" in backtester.DEFAULT_STOCKS
        
        # 验证时间段常量
        assert backtester.DEFAULT_START == "2022-01-01"
        assert backtester.DEFAULT_END == "2024-12-01"
        assert backtester.BEAR_MARKET_START == "2022-01-01"
        assert backtester.BEAR_MARKET_END == "2023-12-31"
        
        # 验证阈值常量
        assert backtester.MAX_DRAWDOWN_THRESHOLD == -0.15


class TestBacktesterAnalysis:
    """测试回测引擎分析功能"""
    
    def test_analyze_market_filter_effectiveness(self):
        """测试大盘风控有效性分析"""
        backtester = TechBacktester()
        
        # 创建测试回测结果
        result = TechBacktestResult(
            total_return=0.15,
            max_drawdown=-0.08,
            total_trades=100,
            win_rate=0.60,
            trades_by_period={
                "2022": 10,           # 熊市，交易少
                "2023上半年": 30,     # 震荡，交易正常
                "2023下半年": 15,     # 震荡，交易少
                "2024": 45            # 正常，交易多
            },
            period_performances=[],
            drawdown_warning=False,
            market_filter_effective=True,
            bear_market_validated=True,
            bear_market_report="测试报告"
        )
        
        # 调用分析方法
        report = backtester.analyze_market_filter_effectiveness(result)
        
        # 验证返回类型
        assert isinstance(report, str)
        
        # 验证报告包含关键信息
        assert "大盘风控有效性分析" in report
        assert "2022年" in report
        assert "2023上半年" in report
        assert "2023下半年" in report
        assert "2024年" in report
        assert "平均交易次数" in report
        assert "风控有效性" in report
        
        # 验证数字正确
        assert "10 次" in report  # 2022年
        assert "30 次" in report  # 2023上半年
        assert "15 次" in report  # 2023下半年
        assert "45 次" in report  # 2024年
    
    def test_get_period_breakdown(self):
        """测试时间段分解统计"""
        backtester = TechBacktester()
        
        # 创建测试绩效数据
        performances = [
            PeriodPerformance(
                period_name="2022年",
                start_date="2022-01-01",
                end_date="2022-12-31",
                total_return=-0.05,
                max_drawdown=-0.12,
                trade_count=10,
                win_rate=0.50,
                is_bear_market=True
            ),
            PeriodPerformance(
                period_name="2023年上半年",
                start_date="2023-01-01",
                end_date="2023-06-30",
                total_return=0.08,
                max_drawdown=-0.06,
                trade_count=30,
                win_rate=0.65,
                is_bear_market=True
            ),
            PeriodPerformance(
                period_name="2023年下半年",
                start_date="2023-07-01",
                end_date="2023-12-31",
                total_return=0.03,
                max_drawdown=-0.04,
                trade_count=15,
                win_rate=0.55,
                is_bear_market=True
            ),
            PeriodPerformance(
                period_name="2024年",
                start_date="2024-01-01",
                end_date="2024-12-31",
                total_return=0.20,
                max_drawdown=-0.08,
                trade_count=45,
                win_rate=0.70,
                is_bear_market=False
            ),
        ]
        
        # 创建测试回测结果
        result = TechBacktestResult(
            total_return=0.15,
            max_drawdown=-0.08,
            total_trades=100,
            win_rate=0.60,
            trades_by_period={},
            period_performances=performances,
            drawdown_warning=False,
            market_filter_effective=True,
            bear_market_validated=True,
            bear_market_report="测试报告"
        )
        
        # 调用分解方法
        breakdown = backtester.get_period_breakdown(result)
        
        # 验证返回类型
        assert isinstance(breakdown, list)
        assert len(breakdown) == 4
        
        # 验证每个时间段的数据
        for period in breakdown:
            assert isinstance(period, dict)
            assert "period_name" in period
            assert "start_date" in period
            assert "end_date" in period
            assert "total_return" in period
            assert "max_drawdown" in period
            assert "trade_count" in period
            assert "win_rate" in period
            assert "is_bear_market" in period
        
        # 验证具体数据
        assert breakdown[0]["period_name"] == "2022年"
        assert breakdown[0]["trade_count"] == 10
        assert breakdown[0]["is_bear_market"] is True
        
        assert breakdown[1]["period_name"] == "2023年上半年"
        assert breakdown[1]["trade_count"] == 30
        
        assert breakdown[2]["period_name"] == "2023年下半年"
        assert breakdown[2]["trade_count"] == 15
        
        assert breakdown[3]["period_name"] == "2024年"
        assert breakdown[3]["trade_count"] == 45
        assert breakdown[3]["is_bear_market"] is False
    
    def test_market_filter_effectiveness_calculation(self):
        """测试大盘风控有效性判断逻辑"""
        backtester = TechBacktester()
        
        # 测试有效的情况（2022和2023下半年交易少）
        effective_result = TechBacktestResult(
            total_return=0.15,
            max_drawdown=-0.08,
            total_trades=100,
            win_rate=0.60,
            trades_by_period={
                "2022": 10,           # 少于平均值的70%
                "2023上半年": 40,
                "2023下半年": 12,     # 少于平均值的70%
                "2024": 38
            },
            period_performances=[],
            drawdown_warning=False,
            market_filter_effective=True,
            bear_market_validated=True,
            bear_market_report="测试报告"
        )
        
        report = backtester.analyze_market_filter_effectiveness(effective_result)
        assert "✅ 有效" in report
        
        # 测试无效的情况（2022和2023下半年交易多）
        ineffective_result = TechBacktestResult(
            total_return=0.15,
            max_drawdown=-0.08,
            total_trades=100,
            win_rate=0.60,
            trades_by_period={
                "2022": 30,           # 接近平均值
                "2023上半年": 25,
                "2023下半年": 25,     # 接近平均值
                "2024": 20
            },
            period_performances=[],
            drawdown_warning=False,
            market_filter_effective=False,
            bear_market_validated=True,
            bear_market_report="测试报告"
        )
        
        report = backtester.analyze_market_filter_effectiveness(ineffective_result)
        assert "⚠️ 需要优化" in report


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
