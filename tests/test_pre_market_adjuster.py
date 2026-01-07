"""
早盘修正器 (PreMarketAdjuster) 测试

测试内容:
1. 基础框架测试
2. 隔夜数据获取测试
3. 交易计划调整测试
4. 早盘修正报告生成测试
"""

import pytest
from core.overnight_picker import (
    PreMarketAdjuster,
    OvernightData,
    USMarketData,
    StockAnnouncement,
    AdjustmentReport,
    Adjustment,
    AdjustmentType,
    MarketSeverity,
    create_pre_market_adjuster,
    quick_pre_market_check,
)


class TestPreMarketAdjusterBasics:
    """基础框架测试"""
    
    def test_create_adjuster(self):
        """测试创建早盘修正器"""
        adjuster = PreMarketAdjuster()
        assert adjuster is not None
        assert adjuster.a50_threshold_mild == -0.01
        assert adjuster.a50_threshold_severe == -0.02
    
    def test_create_adjuster_helper(self):
        """测试便捷创建函数"""
        adjuster = create_pre_market_adjuster()
        assert adjuster is not None
        assert isinstance(adjuster, PreMarketAdjuster)
    
    def test_thresholds(self):
        """测试阈值设置"""
        adjuster = PreMarketAdjuster()
        # A50阈值
        assert adjuster.a50_threshold_mild == -0.01  # -1%
        assert adjuster.a50_threshold_severe == -0.02  # -2%
        # 美股阈值
        assert adjuster.us_threshold_mild == -0.01
        assert adjuster.us_threshold_severe == -0.02
        # 调整比例
        assert adjuster.price_adjust_ratio == 0.02  # 2%
        assert adjuster.position_reduce_ratio == 0.70  # 70%


class TestOvernightDataFetch:
    """隔夜数据获取测试"""
    
    def test_fetch_overnight_data_default(self):
        """测试默认隔夜数据获取"""
        adjuster = PreMarketAdjuster()
        data = adjuster.fetch_overnight_data()
        
        assert data is not None
        assert isinstance(data, OvernightData)
        assert data.fetch_time != ""
    
    def test_fetch_overnight_data_with_values(self):
        """测试指定值的隔夜数据获取"""
        adjuster = PreMarketAdjuster()
        data = adjuster.fetch_overnight_data_with_values(
            sp500_change=-0.01,
            nasdaq_change=-0.015,
            dow_change=-0.008,
            a50_change=-0.02,
        )
        
        assert data.us_market.sp500_change == -0.01
        assert data.us_market.nasdaq_change == -0.015
        assert data.us_market.dow_change == -0.008
        assert data.a50_change == -0.02
    
    def test_fetch_overnight_data_with_announcements(self):
        """测试带公告的隔夜数据获取"""
        adjuster = PreMarketAdjuster()
        announcements = [
            {
                'code': '000001',
                'name': '平安银行',
                'title': '重大利空公告',
                'type': 'negative',
                'severity': 'high',
            }
        ]
        data = adjuster.fetch_overnight_data_with_values(
            a50_change=-0.01,
            announcements=announcements,
        )
        
        assert len(data.announcements) == 1
        assert data.announcements[0].code == '000001'
        assert data.announcements[0].announcement_type == 'negative'
    
    def test_overnight_data_to_dict(self):
        """测试隔夜数据转字典"""
        adjuster = PreMarketAdjuster()
        data = adjuster.fetch_overnight_data_with_values(
            sp500_change=-0.01,
            a50_change=-0.02,
        )
        
        data_dict = data.to_dict()
        assert 'us_market' in data_dict
        assert 'a50_change' in data_dict
        assert data_dict['a50_change'] == -0.02


class TestTradingPlanAdjustment:
    """交易计划调整测试"""
    
    @pytest.fixture
    def sample_plan(self):
        """创建示例交易计划"""
        return {
            'date': '2026-01-07',
            'recommendations': [
                {
                    'code': '000001',
                    'name': '平安银行',
                    'leader_type': '真龙头',
                    'ideal_price': 10.0,
                    'acceptable_price': 10.2,
                },
                {
                    'code': '000002',
                    'name': '万科A',
                    'leader_type': '二线龙头',
                    'ideal_price': 15.0,
                    'acceptable_price': 15.3,
                },
                {
                    'code': '000003',
                    'name': '测试股',
                    'leader_type': '跟风股',
                    'ideal_price': 20.0,
                    'acceptable_price': 20.4,
                },
            ],
            'total_position': 0.8,
        }
    
    def test_no_adjustment_normal_market(self, sample_plan):
        """测试正常市场无需调整"""
        adjuster = PreMarketAdjuster()
        overnight_data = adjuster.fetch_overnight_data_with_values(
            a50_change=0.005,  # A50涨0.5%
            nasdaq_change=0.01,  # 纳指涨1%
        )
        
        adjusted_plan, adjustments = adjuster.adjust_trading_plan(sample_plan, overnight_data)
        
        # 无调整
        assert len(adjustments) == 0
        # 股票数量不变
        assert len(adjusted_plan['recommendations']) == 3
        # 价格不变
        assert adjusted_plan['recommendations'][0]['ideal_price'] == 10.0
    
    def test_mild_adjustment_a50_down_1_percent(self, sample_plan):
        """测试A50跌1%时的轻度调整"""
        adjuster = PreMarketAdjuster()
        overnight_data = adjuster.fetch_overnight_data_with_values(
            a50_change=-0.015,  # A50跌1.5%
        )
        
        adjusted_plan, adjustments = adjuster.adjust_trading_plan(sample_plan, overnight_data)
        
        # 有价格调整
        assert len(adjustments) == 1
        assert adjustments[0].adjustment_type == AdjustmentType.PRICE_ADJUST
        
        # 股票数量不变
        assert len(adjusted_plan['recommendations']) == 3
        
        # 价格下调2%
        assert adjusted_plan['recommendations'][0]['ideal_price'] == pytest.approx(9.8, rel=0.01)
        assert adjusted_plan['recommendations'][0]['acceptable_price'] == pytest.approx(9.996, rel=0.01)
    
    def test_severe_adjustment_a50_down_2_percent(self, sample_plan):
        """测试A50跌2%时的严重调整"""
        adjuster = PreMarketAdjuster()
        overnight_data = adjuster.fetch_overnight_data_with_values(
            a50_change=-0.025,  # A50跌2.5%
        )
        
        adjusted_plan, adjustments = adjuster.adjust_trading_plan(sample_plan, overnight_data)
        
        # 有取消和价格调整
        assert len(adjustments) == 2
        
        # 只保留真龙头
        assert len(adjusted_plan['recommendations']) == 1
        assert adjusted_plan['recommendations'][0]['leader_type'] == '真龙头'
        
        # 价格下调2%
        assert adjusted_plan['recommendations'][0]['ideal_price'] == pytest.approx(9.8, rel=0.01)
    
    def test_cancel_stock_with_negative_announcement(self, sample_plan):
        """测试利空公告取消买入"""
        adjuster = PreMarketAdjuster()
        announcements = [
            {
                'code': '000002',
                'name': '万科A',
                'title': '重大利空公告',
                'type': 'negative',
                'severity': 'high',
            }
        ]
        overnight_data = adjuster.fetch_overnight_data_with_values(
            a50_change=0.0,
            announcements=announcements,
        )
        
        adjusted_plan, adjustments = adjuster.adjust_trading_plan(sample_plan, overnight_data)
        
        # 有取消调整
        cancel_adjustments = [a for a in adjustments if a.adjustment_type == AdjustmentType.CANCEL_STOCK]
        assert len(cancel_adjustments) == 1
        
        # 000002被取消
        codes = [r['code'] for r in adjusted_plan['recommendations']]
        assert '000002' not in codes
        assert len(adjusted_plan['recommendations']) == 2
    
    def test_position_reduce_nasdaq_down(self, sample_plan):
        """测试纳指大跌降低仓位"""
        adjuster = PreMarketAdjuster()
        overnight_data = adjuster.fetch_overnight_data_with_values(
            a50_change=0.0,
            nasdaq_change=-0.025,  # 纳指跌2.5%
        )
        
        adjusted_plan, adjustments = adjuster.adjust_trading_plan(sample_plan, overnight_data)
        
        # 有仓位调整
        position_adjustments = [a for a in adjustments if a.adjustment_type == AdjustmentType.POSITION_REDUCE]
        assert len(position_adjustments) == 1
        
        # 总仓位降低到70%
        assert adjusted_plan['total_position'] == pytest.approx(0.56, rel=0.01)  # 0.8 * 0.7


class TestAdjustmentReport:
    """早盘修正报告测试"""
    
    @pytest.fixture
    def sample_plan(self):
        """创建示例交易计划"""
        return {
            'date': '2026-01-07',
            'recommendations': [
                {
                    'code': '000001',
                    'name': '平安银行',
                    'leader_type': '真龙头',
                    'ideal_price': 10.0,
                    'acceptable_price': 10.2,
                },
            ],
            'total_position': 0.8,
        }
    
    def test_generate_report_no_adjustment(self, sample_plan):
        """测试无调整时的报告生成"""
        adjuster = PreMarketAdjuster()
        overnight_data = adjuster.fetch_overnight_data_with_values(a50_change=0.0)
        
        adjusted_plan, adjustments = adjuster.adjust_trading_plan(sample_plan, overnight_data)
        report = adjuster.generate_adjustment_report(
            sample_plan, adjusted_plan, overnight_data, adjustments
        )
        
        assert report is not None
        assert isinstance(report, AdjustmentReport)
        assert report.market_severity == MarketSeverity.NORMAL
        assert len(report.adjustments) == 0
    
    def test_generate_report_with_adjustments(self, sample_plan):
        """测试有调整时的报告生成"""
        adjuster = PreMarketAdjuster()
        overnight_data = adjuster.fetch_overnight_data_with_values(a50_change=-0.025)
        
        adjusted_plan, adjustments = adjuster.adjust_trading_plan(sample_plan, overnight_data)
        report = adjuster.generate_adjustment_report(
            sample_plan, adjusted_plan, overnight_data, adjustments
        )
        
        assert report is not None
        assert report.market_severity == MarketSeverity.SEVERE
        assert len(report.adjustments) > 0
    
    def test_report_to_markdown(self, sample_plan):
        """测试报告转Markdown"""
        adjuster = PreMarketAdjuster()
        overnight_data = adjuster.fetch_overnight_data_with_values(
            sp500_change=-0.01,
            nasdaq_change=-0.015,
            a50_change=-0.02,
        )
        
        adjusted_plan, adjustments = adjuster.adjust_trading_plan(sample_plan, overnight_data)
        report = adjuster.generate_adjustment_report(
            sample_plan, adjusted_plan, overnight_data, adjustments
        )
        
        markdown = report.to_markdown()
        
        assert '早盘修正报告' in markdown
        assert '隔夜市场情况' in markdown
        assert '调整内容' in markdown
        assert '总结' in markdown


class TestMarketSeverity:
    """市场严重程度评估测试"""
    
    def test_normal_market(self):
        """测试正常市场"""
        adjuster = PreMarketAdjuster()
        overnight_data = adjuster.fetch_overnight_data_with_values(
            a50_change=0.005,
            nasdaq_change=0.01,
        )
        
        severity = adjuster._assess_market_severity(overnight_data)
        assert severity == MarketSeverity.NORMAL
    
    def test_mild_market(self):
        """测试轻度风险市场"""
        adjuster = PreMarketAdjuster()
        overnight_data = adjuster.fetch_overnight_data_with_values(
            a50_change=-0.015,  # -1.5%
        )
        
        severity = adjuster._assess_market_severity(overnight_data)
        assert severity == MarketSeverity.MILD
    
    def test_severe_market(self):
        """测试严重风险市场"""
        adjuster = PreMarketAdjuster()
        overnight_data = adjuster.fetch_overnight_data_with_values(
            a50_change=-0.025,  # -2.5%
        )
        
        severity = adjuster._assess_market_severity(overnight_data)
        assert severity == MarketSeverity.SEVERE
    
    def test_extreme_market(self):
        """测试极端风险市场"""
        adjuster = PreMarketAdjuster()
        overnight_data = adjuster.fetch_overnight_data_with_values(
            a50_change=-0.035,  # -3.5%
        )
        
        severity = adjuster._assess_market_severity(overnight_data)
        assert severity == MarketSeverity.EXTREME


class TestQuickPreMarketCheck:
    """快速早盘检查测试"""
    
    def test_quick_check(self):
        """测试快速检查函数"""
        original_plan = {
            'date': '2026-01-07',
            'recommendations': [
                {
                    'code': '000001',
                    'name': '测试股',
                    'leader_type': '真龙头',
                    'ideal_price': 10.0,
                    'acceptable_price': 10.2,
                },
            ],
            'total_position': 0.8,
        }
        
        adjusted_plan, report_markdown = quick_pre_market_check(
            original_plan,
            a50_change=-0.015,
            nasdaq_change=-0.01,
        )
        
        assert adjusted_plan is not None
        assert report_markdown is not None
        assert '早盘修正报告' in report_markdown


class TestRunPreMarketAdjustment:
    """完整早盘修正流程测试"""
    
    def test_run_full_adjustment(self):
        """测试完整修正流程"""
        adjuster = PreMarketAdjuster()
        
        original_plan = {
            'date': '2026-01-07',
            'recommendations': [
                {
                    'code': '000001',
                    'name': '测试股',
                    'leader_type': '真龙头',
                    'ideal_price': 10.0,
                    'acceptable_price': 10.2,
                },
            ],
            'total_position': 0.8,
        }
        
        overnight_data = adjuster.fetch_overnight_data_with_values(a50_change=-0.015)
        
        adjusted_plan, report = adjuster.run_pre_market_adjustment(
            original_plan, overnight_data
        )
        
        assert adjusted_plan is not None
        assert report is not None
        assert isinstance(report, AdjustmentReport)
