"""
竞价过滤器 (CallAuctionFilter) 测试

测试内容:
1. 基础框架测试
2. 核按钮检测测试 (Requirements 8.1)
3. 抢筹确认测试 (Requirements 8.2)
4. 策略类型判断测试 (Requirements 8.3-8.5)
5. 竞价报告生成测试 (Requirements 8.6)
"""

import pytest
from core.overnight_picker import (
    CallAuctionFilter,
    AuctionAction,
    AuctionResult,
    RiskLevel,
    StrategyType,
)


class TestCallAuctionFilterBasics:
    """基础框架测试"""
    
    def test_create_filter(self):
        """测试创建竞价过滤器"""
        filter = CallAuctionFilter()
        assert filter is not None
        assert filter.nuclear_threshold == -0.04  # -4%
        assert filter.chase_threshold == 0.03     # +3%
        assert filter.volume_ratio_threshold == 5.0
    
    def test_custom_thresholds(self):
        """测试自定义阈值"""
        filter = CallAuctionFilter(
            nuclear_threshold=-0.05,
            chase_threshold=0.04,
            volume_ratio_threshold=6.0
        )
        assert filter.nuclear_threshold == -0.05
        assert filter.chase_threshold == 0.04
        assert filter.volume_ratio_threshold == 6.0


class TestNuclearButtonDetection:
    """核按钮检测测试 (Requirements 8.1)"""
    
    def test_nuclear_button_triggered(self):
        """测试核按钮触发 - 低开>4%"""
        filter = CallAuctionFilter()
        result = filter.analyze_auction(
            stock_code='000001',
            prev_close=10.0,
            auction_price=9.5,  # 低开5%
            auction_volume=1000000,
            avg_volume=5000000,
            leader_index=50,
            strategy_type='low_buy'
        )
        
        assert result.action == AuctionAction.CANCEL
        assert result.risk_level == RiskLevel.EXTREME
        assert '核按钮' in result.reason
        assert result.open_change < -0.04
    
    def test_nuclear_button_boundary(self):
        """测试核按钮边界 - 低开略小于4%"""
        filter = CallAuctionFilter()
        result = filter.analyze_auction(
            stock_code='000001',
            prev_close=10.0,
            auction_price=9.61,  # 低开3.9%，略小于4%阈值
            auction_volume=1000000,
            avg_volume=5000000,
            leader_index=50,
            strategy_type='low_buy'
        )
        
        # 低开3.9%不触发核按钮
        assert result.risk_level != RiskLevel.EXTREME
    
    def test_nuclear_button_not_triggered(self):
        """测试核按钮未触发 - 低开3%"""
        filter = CallAuctionFilter()
        result = filter.analyze_auction(
            stock_code='000001',
            prev_close=10.0,
            auction_price=9.7,  # 低开3%
            auction_volume=1000000,
            avg_volume=5000000,
            leader_index=50,
            strategy_type='low_buy'
        )
        
        assert result.risk_level != RiskLevel.EXTREME
    
    def test_is_nuclear_button_helper(self):
        """测试核按钮判断辅助函数"""
        filter = CallAuctionFilter()
        
        assert filter.is_nuclear_button(-0.05) == True   # 低开5%
        assert filter.is_nuclear_button(-0.04) == False  # 刚好4%
        assert filter.is_nuclear_button(-0.03) == False  # 低开3%
        assert filter.is_nuclear_button(0.01) == False   # 高开1%


class TestChaseConfirmation:
    """抢筹确认测试 (Requirements 8.2)"""
    
    def test_chase_confirmed(self):
        """测试抢筹确认 - 龙头高开爆量"""
        filter = CallAuctionFilter()
        result = filter.analyze_auction(
            stock_code='000001',
            prev_close=10.0,
            auction_price=10.4,  # 高开4%
            auction_volume=2000000,  # 大量
            avg_volume=1000000,  # 日均量较小，使量比>5
            leader_index=80,  # 龙头指数>70
            strategy_type='breakout'
        )
        
        assert result.action == AuctionAction.BUY
        assert result.risk_level == RiskLevel.HIGH
        assert '抢筹' in result.reason
        assert result.adjusted_price is not None
    
    def test_chase_not_confirmed_low_leader_index(self):
        """测试抢筹未确认 - 龙头指数不足"""
        filter = CallAuctionFilter()
        result = filter.analyze_auction(
            stock_code='000001',
            prev_close=10.0,
            auction_price=10.4,  # 高开4%
            auction_volume=2000000,
            avg_volume=1000000,
            leader_index=60,  # 龙头指数<70
            strategy_type='breakout'
        )
        
        # 不应该触发抢筹确认
        assert result.risk_level != RiskLevel.HIGH or '抢筹' not in result.reason
    
    def test_chase_not_confirmed_low_volume(self):
        """测试抢筹未确认 - 量比不足"""
        filter = CallAuctionFilter()
        result = filter.analyze_auction(
            stock_code='000001',
            prev_close=10.0,
            auction_price=10.4,  # 高开4%
            auction_volume=100000,  # 量小
            avg_volume=5000000,  # 日均量大，使量比<5
            leader_index=80,
            strategy_type='breakout'
        )
        
        # 不应该触发抢筹确认
        assert result.risk_level != RiskLevel.HIGH or '抢筹' not in result.reason
    
    def test_is_chase_confirmed_helper(self):
        """测试抢筹确认辅助函数"""
        filter = CallAuctionFilter()
        
        # 满足所有条件
        assert filter.is_chase_confirmed(0.04, 6.0, 80) == True
        
        # 高开不足
        assert filter.is_chase_confirmed(0.02, 6.0, 80) == False
        
        # 量比不足
        assert filter.is_chase_confirmed(0.04, 4.0, 80) == False
        
        # 龙头指数不足
        assert filter.is_chase_confirmed(0.04, 6.0, 60) == False


class TestStrategyTypeJudgment:
    """策略类型判断测试 (Requirements 8.3-8.5)"""
    
    def test_determine_breakout_strategy(self):
        """测试判断突破型策略"""
        filter = CallAuctionFilter()
        strategy = filter.determine_strategy_type(
            leader_index=70,
            ma_position='多头排列',
            pattern='突破前高'
        )
        
        assert strategy == StrategyType.BREAKOUT
    
    def test_determine_low_buy_strategy(self):
        """测试判断低吸型策略"""
        filter = CallAuctionFilter()
        strategy = filter.determine_strategy_type(
            leader_index=40,
            ma_position='空头排列',
            pattern='底部放量'
        )
        
        assert strategy == StrategyType.LOW_BUY
    
    def test_low_buy_strategy_strict_abandon(self):
        """测试低吸型策略严格遵守放弃价 (Requirements 8.4)"""
        filter = CallAuctionFilter()
        result = filter.analyze_auction(
            stock_code='000001',
            prev_close=10.0,
            auction_price=10.35,  # 高开3.5%
            auction_volume=1000000,
            avg_volume=5000000,
            leader_index=50,
            strategy_type='low_buy'  # 低吸型
        )
        
        assert result.action == AuctionAction.CANCEL
        assert '低吸策略' in result.reason
    
    def test_breakout_strategy_requires_volume(self):
        """测试突破型策略要求量比 (Requirements 8.5)"""
        filter = CallAuctionFilter()
        result = filter.analyze_auction(
            stock_code='000001',
            prev_close=10.0,
            auction_price=10.35,  # 高开3.5%
            auction_volume=100000,  # 量小
            avg_volume=5000000,  # 量比不足
            leader_index=50,
            strategy_type='breakout'  # 突破型
        )
        
        assert result.action == AuctionAction.CANCEL
        assert '突破策略' in result.reason
        assert '量比' in result.reason


class TestNormalAuction:
    """正常竞价测试"""
    
    def test_normal_auction_buy(self):
        """测试正常竞价可买入"""
        filter = CallAuctionFilter()
        result = filter.analyze_auction(
            stock_code='000001',
            prev_close=10.0,
            auction_price=10.1,  # 高开1%
            auction_volume=500000,
            avg_volume=5000000,
            leader_index=50,
            strategy_type='low_buy'
        )
        
        assert result.action == AuctionAction.BUY
        assert result.risk_level == RiskLevel.LOW
        assert result.adjusted_price == 10.1
    
    def test_invalid_prev_close(self):
        """测试无效昨收价"""
        filter = CallAuctionFilter()
        result = filter.analyze_auction(
            stock_code='000001',
            prev_close=0,  # 无效
            auction_price=10.0,
            auction_volume=500000,
            avg_volume=5000000,
            leader_index=50,
            strategy_type='low_buy'
        )
        
        assert result.action == AuctionAction.CANCEL
        assert result.risk_level == RiskLevel.EXTREME


class TestBatchAnalyze:
    """批量分析测试"""
    
    def test_batch_analyze(self):
        """测试批量分析多只股票"""
        filter = CallAuctionFilter()
        stocks = [
            {
                'code': '000001',
                'prev_close': 10.0,
                'auction_price': 9.5,  # 低开5% - 核按钮
                'auction_volume': 1000000,
                'avg_volume': 5000000,
                'leader_index': 50,
                'strategy_type': 'low_buy'
            },
            {
                'code': '000002',
                'prev_close': 20.0,
                'auction_price': 20.2,  # 高开1% - 正常
                'auction_volume': 500000,
                'avg_volume': 5000000,
                'leader_index': 60,
                'strategy_type': 'low_buy'
            },
        ]
        
        results = filter.batch_analyze(stocks)
        
        assert len(results) == 2
        assert results[0][0] == '000001'
        assert results[0][1].action == AuctionAction.CANCEL  # 核按钮
        assert results[1][0] == '000002'
        assert results[1][1].action == AuctionAction.BUY  # 正常


class TestAuctionReport:
    """竞价报告生成测试 (Requirements 8.6)"""
    
    def test_generate_report(self):
        """测试生成竞价报告"""
        filter = CallAuctionFilter()
        
        results = [
            ('000001', AuctionResult(
                action=AuctionAction.CANCEL,
                reason='核按钮警报',
                adjusted_price=None,
                risk_level=RiskLevel.EXTREME,
                open_change=-0.05,
                volume_ratio=1.0
            )),
            ('000002', AuctionResult(
                action=AuctionAction.BUY,
                reason='竞价正常',
                adjusted_price=10.0,
                risk_level=RiskLevel.LOW,
                open_change=0.01,
                volume_ratio=2.0
            )),
        ]
        
        report = filter.generate_auction_report(results)
        
        assert '竞价修正报告' in report
        assert '可执行买入: 1只' in report
        assert '取消买入: 1只' in report
        assert '000001' in report
        assert '000002' in report
    
    def test_report_with_nuclear_warning(self):
        """测试报告包含核按钮警告"""
        filter = CallAuctionFilter()
        
        results = [
            ('000001', AuctionResult(
                action=AuctionAction.CANCEL,
                reason='核按钮警报! 低开-5%',
                adjusted_price=None,
                risk_level=RiskLevel.EXTREME,
                open_change=-0.05,
                volume_ratio=1.0
            )),
        ]
        
        report = filter.generate_auction_report(results)
        
        assert '核按钮警报' in report
    
    def test_report_with_chase_confirmation(self):
        """测试报告包含抢筹确认"""
        filter = CallAuctionFilter()
        
        results = [
            ('000001', AuctionResult(
                action=AuctionAction.BUY,
                reason='抢筹确认! 龙头高开',
                adjusted_price=10.5,
                risk_level=RiskLevel.HIGH,
                open_change=0.04,
                volume_ratio=6.0
            )),
        ]
        
        report = filter.generate_auction_report(results)
        
        assert '抢筹确认' in report


class TestAuctionResultDataclass:
    """AuctionResult数据类测试"""
    
    def test_to_dict(self):
        """测试转换为字典"""
        result = AuctionResult(
            action=AuctionAction.BUY,
            reason='测试原因',
            adjusted_price=10.0,
            risk_level=RiskLevel.LOW,
            open_change=0.01,
            volume_ratio=2.0
        )
        
        d = result.to_dict()
        
        assert d['action'] == 'BUY'
        assert d['reason'] == '测试原因'
        assert d['adjusted_price'] == 10.0
        assert d['risk_level'] == 'LOW'
        assert d['open_change'] == 0.01
        assert d['volume_ratio'] == 2.0
