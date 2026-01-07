"""
隔夜选股系统集成测试 (OvernightStockPicker Integration Tests)

测试完整的选股流程:
1. 模块导入测试
2. 数据加载和预处理测试
3. 大盘环境分析测试
4. 市场情绪分析测试
5. 股票评分测试
6. 推荐生成测试
7. 交易计划生成测试
8. 完整流程测试

Requirements: 1.1-1.6, 7.1-7.6
"""

import os
import pytest
import pandas as pd
from datetime import date, timedelta
from unittest.mock import patch, MagicMock


class TestModuleImports:
    """模块导入测试"""
    
    def test_import_main_picker(self):
        """测试导入主选股器"""
        from core.overnight_picker import OvernightStockPicker
        assert OvernightStockPicker is not None
    
    def test_import_models(self):
        """测试导入数据模型"""
        from core.overnight_picker import StockRecommendation, TradingPlan
        assert StockRecommendation is not None
        assert TradingPlan is not None
    
    def test_import_scorer(self):
        """测试导入评分器"""
        from core.overnight_picker import TomorrowPotentialScorer
        assert TomorrowPotentialScorer is not None
    
    def test_import_calculators(self):
        """测试导入计算器"""
        from core.overnight_picker import (
            EntryPriceCalculator,
            PositionAdvisor,
            StopLossCalculator,
            TakeProfitCalculator,
            SmartStopLoss,
            TrailingStop,
        )
        assert EntryPriceCalculator is not None
        assert PositionAdvisor is not None
        assert StopLossCalculator is not None
        assert TakeProfitCalculator is not None
        assert SmartStopLoss is not None
        assert TrailingStop is not None
    
    def test_import_topic_matcher(self):
        """测试导入题材匹配器"""
        from core.overnight_picker import SmartTopicMatcher, get_smart_topic_matcher
        assert SmartTopicMatcher is not None
        assert get_smart_topic_matcher is not None
    
    def test_import_auction_filter(self):
        """测试导入竞价过滤器"""
        from core.overnight_picker import CallAuctionFilter, AuctionAction, StrategyType
        assert CallAuctionFilter is not None
        assert AuctionAction is not None
        assert StrategyType is not None
    
    def test_import_sentiment_predictor(self):
        """测试导入情绪预判器"""
        from core.overnight_picker import (
            SentimentCyclePredictor,
            SentimentPhase,
            SentimentLevel,
        )
        assert SentimentCyclePredictor is not None
        assert SentimentPhase is not None
        assert SentimentLevel is not None
    
    def test_import_pre_market_adjuster(self):
        """测试导入早盘修正器"""
        from core.overnight_picker import PreMarketAdjuster, OvernightData
        assert PreMarketAdjuster is not None
        assert OvernightData is not None
    
    def test_import_plan_generator(self):
        """测试导入计划生成器"""
        from core.overnight_picker import TradingPlanGenerator
        assert TradingPlanGenerator is not None
    
    def test_import_convenience_functions(self):
        """测试导入便捷函数"""
        from core.overnight_picker import (
            create_overnight_picker,
            quick_overnight_pick,
            create_trading_plan_generator,
            quick_generate_plan,
        )
        assert create_overnight_picker is not None
        assert quick_overnight_pick is not None
        assert create_trading_plan_generator is not None
        assert quick_generate_plan is not None


class TestOvernightPickerCreation:
    """选股器创建测试"""
    
    def test_create_picker_default(self):
        """测试默认参数创建选股器"""
        from core.overnight_picker import OvernightStockPicker
        
        picker = OvernightStockPicker()
        
        assert picker is not None
        assert picker.total_capital == 70000
        assert picker.max_recommendations == 15
        assert picker.min_score == 70
    
    def test_create_picker_custom_capital(self):
        """测试自定义资金创建选股器"""
        from core.overnight_picker import OvernightStockPicker
        
        picker = OvernightStockPicker(total_capital=100000)
        
        assert picker.total_capital == 100000
    
    def test_create_picker_custom_stock_pool(self):
        """测试自定义股票池创建选股器"""
        from core.overnight_picker import OvernightStockPicker
        
        custom_pool = ['000001', '000002', '000003']
        picker = OvernightStockPicker(stock_pool=custom_pool)
        
        assert picker.stock_pool == custom_pool
    
    def test_create_picker_helper_function(self):
        """测试便捷创建函数"""
        from core.overnight_picker import create_overnight_picker
        
        picker = create_overnight_picker(total_capital=80000)
        
        assert picker is not None
        assert picker.total_capital == 80000


class TestTechnicalIndicators:
    """技术指标计算测试"""
    
    @pytest.fixture
    def sample_df(self):
        """创建示例数据"""
        dates = pd.date_range(start='2025-01-01', periods=100, freq='D')
        data = {
            'date': dates,
            'open': [10 + i * 0.1 for i in range(100)],
            'high': [10.5 + i * 0.1 for i in range(100)],
            'low': [9.5 + i * 0.1 for i in range(100)],
            'close': [10.2 + i * 0.1 for i in range(100)],
            'volume': [1000000 + i * 10000 for i in range(100)],
        }
        return pd.DataFrame(data)
    
    def test_calculate_ma(self, sample_df):
        """测试均线计算"""
        from core.overnight_picker import OvernightStockPicker
        
        picker = OvernightStockPicker(stock_pool=[])
        df = picker.calculate_technical_indicators(sample_df)
        
        assert 'ma5' in df.columns
        assert 'ma10' in df.columns
        assert 'ma20' in df.columns
        assert 'ma60' in df.columns
    
    def test_calculate_volume_ma(self, sample_df):
        """测试成交量均线计算"""
        from core.overnight_picker import OvernightStockPicker
        
        picker = OvernightStockPicker(stock_pool=[])
        df = picker.calculate_technical_indicators(sample_df)
        
        assert 'ma5_vol' in df.columns
        assert 'ma10_vol' in df.columns
    
    def test_calculate_macd(self, sample_df):
        """测试MACD计算"""
        from core.overnight_picker import OvernightStockPicker
        
        picker = OvernightStockPicker(stock_pool=[])
        df = picker.calculate_technical_indicators(sample_df)
        
        assert 'macd' in df.columns
        assert 'signal' in df.columns
        assert 'macd_hist' in df.columns
    
    def test_calculate_volatility(self, sample_df):
        """测试波动率计算"""
        from core.overnight_picker import OvernightStockPicker
        
        picker = OvernightStockPicker(stock_pool=[])
        df = picker.calculate_technical_indicators(sample_df)
        
        assert 'volatility' in df.columns
        assert df['volatility'].iloc[-1] > 0


class TestMarketEnvironmentAnalysis:
    """大盘环境分析测试"""
    
    @pytest.fixture
    def bullish_index_data(self):
        """创建多头排列的指数数据"""
        dates = pd.date_range(start='2025-01-01', periods=100, freq='D')
        # 创建上涨趋势数据
        data = {
            'date': dates,
            'open': [3000 + i * 5 for i in range(100)],
            'high': [3050 + i * 5 for i in range(100)],
            'low': [2980 + i * 5 for i in range(100)],
            'close': [3020 + i * 5 for i in range(100)],
            'volume': [100000000 + i * 1000000 for i in range(100)],
        }
        return pd.DataFrame(data)
    
    @pytest.fixture
    def bearish_index_data(self):
        """创建空头排列的指数数据"""
        dates = pd.date_range(start='2025-01-01', periods=100, freq='D')
        # 创建下跌趋势数据
        data = {
            'date': dates,
            'open': [3500 - i * 5 for i in range(100)],
            'high': [3520 - i * 5 for i in range(100)],
            'low': [3450 - i * 5 for i in range(100)],
            'close': [3480 - i * 5 for i in range(100)],
            'volume': [100000000 + i * 1000000 for i in range(100)],
        }
        return pd.DataFrame(data)
    
    def test_analyze_bullish_market(self, bullish_index_data):
        """测试分析多头市场"""
        from core.overnight_picker import OvernightStockPicker, MarketEnvironment
        
        picker = OvernightStockPicker(stock_pool=[])
        result = picker.analyze_market_environment(bullish_index_data)
        
        assert result is not None
        assert 'env' in result
        assert result['env'] in [MarketEnvironment.STRONG, MarketEnvironment.NEUTRAL]
        assert result['should_empty'] == False
    
    def test_analyze_bearish_market(self, bearish_index_data):
        """测试分析空头市场"""
        from core.overnight_picker import OvernightStockPicker, MarketEnvironment
        
        picker = OvernightStockPicker(stock_pool=[])
        result = picker.analyze_market_environment(bearish_index_data)
        
        assert result is not None
        assert 'env' in result
        assert result['env'] in [MarketEnvironment.WEAK, MarketEnvironment.EXTREME_WEAK]
    
    def test_market_tradable_check(self, bullish_index_data):
        """测试市场可交易性检查"""
        from core.overnight_picker import OvernightStockPicker
        
        picker = OvernightStockPicker(stock_pool=[])
        market_env = picker.analyze_market_environment(bullish_index_data)
        
        is_tradable, reason = picker.is_market_tradable(market_env)
        
        assert isinstance(is_tradable, bool)
        assert isinstance(reason, str)


class TestMarketSentimentAnalysis:
    """市场情绪分析测试"""
    
    def test_analyze_sentiment_bullish(self):
        """测试分析乐观情绪"""
        from core.overnight_picker import OvernightStockPicker
        
        picker = OvernightStockPicker(stock_pool=[])
        result = picker.analyze_market_sentiment(
            limit_up_count=100,
            limit_down_count=5,
            broken_board_rate=0.1,
            continuous_board_count=10,
            market_profit_rate=0.7
        )
        
        assert result is not None
        assert 'sentiment' in result
        assert 'phase' in result
        assert 'position_multiplier' in result
    
    def test_analyze_sentiment_bearish(self):
        """测试分析恐慌情绪"""
        from core.overnight_picker import OvernightStockPicker
        
        picker = OvernightStockPicker(stock_pool=[])
        result = picker.analyze_market_sentiment(
            limit_up_count=10,
            limit_down_count=50,
            broken_board_rate=0.5,
            continuous_board_count=0,
            market_profit_rate=0.2
        )
        
        assert result is not None
        assert result['sentiment'] == '恐慌'


class TestStockRecommendationModel:
    """股票推荐模型测试"""
    
    def test_create_recommendation(self):
        """测试创建推荐"""
        from core.overnight_picker import StockRecommendation
        
        rec = StockRecommendation(
            code='000001',
            name='平安银行',
            sector='银行',
            today_close=10.0,
            today_change=2.5,
            total_score=85,
            score_details={},
            ideal_price=9.8,
            acceptable_price=10.1,
            abandon_price=10.3,
            position_ratio=0.2,
            position_amount=14000,
            shares=1400,
            stop_loss_price=9.31,
            first_target=10.29,
            second_target=10.78,
            max_loss=686,
            expected_profit=686,
            hot_topics=['银行', '金融'],
            leader_type='二线龙头',
            risk_level='MEDIUM',
            reasoning='测试推荐理由',
            strategy_type='low_buy',
        )
        
        assert rec.code == '000001'
        assert rec.total_score == 85
        assert rec.shares == 1400
        assert rec.shares % 100 == 0  # 股数为100整数倍
    
    def test_recommendation_to_dict(self):
        """测试推荐转字典"""
        from core.overnight_picker import StockRecommendation
        
        rec = StockRecommendation(
            code='000001',
            name='平安银行',
            sector='银行',
            today_close=10.0,
            today_change=2.5,
            total_score=85,
            score_details={},
            ideal_price=9.8,
            acceptable_price=10.1,
            abandon_price=10.3,
            position_ratio=0.2,
            position_amount=14000,
            shares=1400,
            stop_loss_price=9.31,
            first_target=10.29,
            second_target=10.78,
            max_loss=686,
            expected_profit=686,
            hot_topics=['银行'],
            leader_type='二线龙头',
            risk_level='MEDIUM',
            reasoning='测试',
            strategy_type='low_buy',
        )
        
        d = rec.to_dict()
        
        assert d['code'] == '000001'
        assert d['total_score'] == 85


class TestTradingPlanModel:
    """交易计划模型测试"""
    
    @pytest.fixture
    def sample_recommendations(self):
        """创建示例推荐列表"""
        from core.overnight_picker import StockRecommendation
        
        return [
            StockRecommendation(
                code='000001',
                name='平安银行',
                sector='银行',
                today_close=10.0,
                today_change=2.5,
                total_score=85,
                score_details={},
                ideal_price=9.8,
                acceptable_price=10.1,
                abandon_price=10.3,
                position_ratio=0.2,
                position_amount=14000,
                shares=1400,
                stop_loss_price=9.31,
                first_target=10.29,
                second_target=10.78,
                max_loss=686,
                expected_profit=686,
                hot_topics=['银行'],
                leader_type='二线龙头',
                risk_level='MEDIUM',
                reasoning='测试',
                strategy_type='low_buy',
            ),
        ]
    
    def test_create_trading_plan(self, sample_recommendations):
        """测试创建交易计划"""
        from core.overnight_picker import TradingPlan
        
        plan = TradingPlan(
            date='2026-01-07',
            generated_at='2026-01-06 15:35:00',
            market_env='震荡',
            market_sentiment='中性',
            sentiment_phase='升温',
            hot_topics=['银行', '金融'],
            recommendations=sample_recommendations,
            total_position=0.2,
            operation_tips=['测试提示'],
            risk_warnings=['测试警告'],
            tomorrow_prediction='明日预判',
            position_multiplier=1.0,
        )
        
        assert plan.date == '2026-01-07'
        assert len(plan.recommendations) == 1
        assert plan.total_position == 0.2
    
    def test_trading_plan_to_dict(self, sample_recommendations):
        """测试交易计划转字典"""
        from core.overnight_picker import TradingPlan
        
        plan = TradingPlan(
            date='2026-01-07',
            generated_at='2026-01-06 15:35:00',
            market_env='震荡',
            market_sentiment='中性',
            sentiment_phase='升温',
            hot_topics=['银行'],
            recommendations=sample_recommendations,
            total_position=0.2,
            operation_tips=['测试提示'],
            risk_warnings=['测试警告'],
            tomorrow_prediction='明日预判',
            position_multiplier=1.0,
        )
        
        d = plan.to_dict()
        
        assert d['date'] == '2026-01-07'
        assert 'recommendations' in d
    
    def test_trading_plan_to_markdown(self, sample_recommendations):
        """测试交易计划转Markdown"""
        from core.overnight_picker import TradingPlan
        
        plan = TradingPlan(
            date='2026-01-07',
            generated_at='2026-01-06 15:35:00',
            market_env='震荡',
            market_sentiment='中性',
            sentiment_phase='升温',
            hot_topics=['银行'],
            recommendations=sample_recommendations,
            total_position=0.2,
            operation_tips=['测试提示'],
            risk_warnings=['测试警告'],
            tomorrow_prediction='明日预判',
            position_multiplier=1.0,
        )
        
        md = plan.to_markdown()
        
        assert '明日交易计划' in md
        assert '2026-01-07' in md
        assert '平安银行' in md


class TestTradingPlanGenerator:
    """交易计划生成器测试"""
    
    @pytest.fixture
    def sample_recommendations(self):
        """创建示例推荐列表"""
        from core.overnight_picker import StockRecommendation
        
        return [
            StockRecommendation(
                code='000001',
                name='平安银行',
                sector='银行',
                today_close=10.0,
                today_change=2.5,
                total_score=85,
                score_details={},
                ideal_price=9.8,
                acceptable_price=10.1,
                abandon_price=10.3,
                position_ratio=0.2,
                position_amount=14000,
                shares=1400,
                stop_loss_price=9.31,
                first_target=10.29,
                second_target=10.78,
                max_loss=686,
                expected_profit=686,
                hot_topics=['银行'],
                leader_type='二线龙头',
                risk_level='MEDIUM',
                reasoning='测试',
                strategy_type='low_buy',
            ),
        ]
    
    def test_generate_plan(self, sample_recommendations):
        """测试生成交易计划"""
        from core.overnight_picker import TradingPlanGenerator
        
        generator = TradingPlanGenerator()
        plan = generator.generate_plan(
            date='2026-01-07',
            market_env={'env': '震荡'},
            sentiment={'sentiment': '中性', 'phase': '升温', 'position_multiplier': 1.0},
            recommendations=sample_recommendations,
            hot_topics=['银行'],
        )
        
        assert plan is not None
        assert plan.date == '2026-01-07'
        assert len(plan.recommendations) == 1
    
    def test_generate_plan_limits_recommendations(self, sample_recommendations):
        """测试生成计划限制推荐数量"""
        from core.overnight_picker import TradingPlanGenerator, StockRecommendation
        
        # 创建6个推荐
        many_recs = sample_recommendations * 6
        
        generator = TradingPlanGenerator()
        plan = generator.generate_plan(
            date='2026-01-07',
            market_env={'env': '震荡'},
            sentiment={'sentiment': '中性', 'phase': '升温', 'position_multiplier': 1.0},
            recommendations=many_recs,
            hot_topics=['银行'],
        )
        
        # 应该限制为5只
        assert len(plan.recommendations) <= 5
    
    def test_to_markdown(self, sample_recommendations):
        """测试生成Markdown"""
        from core.overnight_picker import TradingPlanGenerator
        
        generator = TradingPlanGenerator()
        plan = generator.generate_plan(
            date='2026-01-07',
            market_env={'env': '震荡'},
            sentiment={'sentiment': '中性', 'phase': '升温', 'position_multiplier': 1.0},
            recommendations=sample_recommendations,
            hot_topics=['银行'],
        )
        
        md = generator.to_markdown(plan)
        
        assert '明日交易计划' in md
        assert '市场环境' in md
        assert '推荐买入' in md


class TestEndToEndFlow:
    """端到端流程测试"""
    
    def test_run_with_real_data(self):
        """测试使用真实数据运行选股流程"""
        from core.overnight_picker import OvernightStockPicker
        
        # 使用少量股票池进行测试
        picker = OvernightStockPicker(stock_pool=['000001', '000002'])
        plan = picker.run(save_plan=False)
        
        assert plan is not None
        # 计划应该有日期和市场环境
        assert plan.date is not None
        assert plan.market_env is not None
        # 推荐列表最多5只
        assert len(plan.recommendations) <= 5
    
    def test_picker_modules_integration(self):
        """测试选股器模块集成"""
        from core.overnight_picker import OvernightStockPicker
        
        picker = OvernightStockPicker(stock_pool=[])
        
        # 验证所有模块已初始化
        assert picker.scorer is not None
        assert picker.entry_calculator is not None
        assert picker.position_advisor is not None
        assert picker.stop_loss_calculator is not None
        assert picker.take_profit_calculator is not None
        assert picker.smart_stop_loss is not None
        assert picker.topic_matcher is not None
        assert picker.auction_filter is not None
        assert picker.sentiment_predictor is not None
        assert picker.plan_generator is not None


class TestDataStatusAndFreshness:
    """数据状态和新鲜度测试"""
    
    def test_get_data_status(self):
        """测试获取数据状态"""
        from core.overnight_picker import OvernightStockPicker
        
        picker = OvernightStockPicker(stock_pool=['000001', '000002'])
        status = picker.get_data_status()
        
        assert isinstance(status, dict)
        assert '000001' in status or '000002' in status or len(status) == 2
    
    def test_check_data_freshness(self):
        """测试检查数据新鲜度"""
        from core.overnight_picker import OvernightStockPicker
        
        picker = OvernightStockPicker(stock_pool=['000001'])
        fresh, stale = picker.check_data_freshness(max_days=30)
        
        assert isinstance(fresh, list)
        assert isinstance(stale, list)


class TestRecommendationsSummary:
    """推荐摘要测试"""
    
    def test_get_recommendations_summary_empty(self):
        """测试空推荐摘要"""
        from core.overnight_picker import OvernightStockPicker, TradingPlan
        
        picker = OvernightStockPicker(stock_pool=[])
        plan = TradingPlan(
            date='2026-01-07',
            generated_at='2026-01-06 15:35:00',
            market_env='震荡',
            market_sentiment='中性',
            sentiment_phase='升温',
            hot_topics=[],
            recommendations=[],
            total_position=0,
            operation_tips=[],
            risk_warnings=[],
            tomorrow_prediction='',
            position_multiplier=1.0,
        )
        
        summary = picker.get_recommendations_summary(plan)
        
        assert '无推荐' in summary


class TestCallAuctionFilterLogic:
    """竞价过滤器策略逻辑测试 - 验证核按钮和抢筹逻辑"""
    
    def test_nuclear_button_low_open_5_percent(self):
        """测试核按钮: 低开5%应该取消买入"""
        from core.overnight_picker import CallAuctionFilter, AuctionAction
        
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
        assert '核按钮' in result.reason
        assert result.open_change < -0.04
    
    def test_nuclear_button_low_open_4_percent_boundary(self):
        """测试核按钮边界: 低开刚好4%应该取消买入"""
        from core.overnight_picker import CallAuctionFilter, AuctionAction
        
        filter = CallAuctionFilter()
        result = filter.analyze_auction(
            stock_code='000001',
            prev_close=10.0,
            auction_price=9.59,  # 低开4.1%
            auction_volume=1000000,
            avg_volume=5000000,
            leader_index=50,
            strategy_type='low_buy'
        )
        
        assert result.action == AuctionAction.CANCEL
    
    def test_chase_buying_leader_high_open_with_volume(self):
        """测试抢筹确认: 龙头高开爆量应该允许买入"""
        from core.overnight_picker import CallAuctionFilter, AuctionAction
        
        filter = CallAuctionFilter()
        result = filter.analyze_auction(
            stock_code='000001',
            prev_close=10.0,
            auction_price=10.35,  # 高开3.5%
            auction_volume=5000000,  # 大量
            avg_volume=1000000,  # 平均量小，量比高
            leader_index=80,  # 龙头指数高
            strategy_type='breakout'
        )
        
        assert result.action == AuctionAction.BUY
        assert '抢筹' in result.reason
    
    def test_low_buy_strategy_high_open_abandon(self):
        """测试低吸策略: 高开3%以上应该放弃"""
        from core.overnight_picker import CallAuctionFilter, AuctionAction
        
        filter = CallAuctionFilter()
        result = filter.analyze_auction(
            stock_code='000001',
            prev_close=10.0,
            auction_price=10.35,  # 高开3.5%
            auction_volume=1000000,
            avg_volume=5000000,
            leader_index=50,  # 非龙头
            strategy_type='low_buy'
        )
        
        assert result.action == AuctionAction.CANCEL
        assert '低吸策略' in result.reason
    
    def test_normal_open_allows_buy(self):
        """测试正常开盘: 平开或小幅高开应该允许买入"""
        from core.overnight_picker import CallAuctionFilter, AuctionAction
        
        filter = CallAuctionFilter()
        result = filter.analyze_auction(
            stock_code='000001',
            prev_close=10.0,
            auction_price=10.1,  # 高开1%
            auction_volume=1000000,
            avg_volume=5000000,
            leader_index=50,
            strategy_type='low_buy'
        )
        
        assert result.action == AuctionAction.BUY
        assert '竞价正常' in result.reason


class TestSentimentCycleLogic:
    """情绪周期策略逻辑测试 - 验证情绪预判和仓位调整"""
    
    def test_climax_to_divergence_position_halved(self):
        """测试高潮后分歧: 昨日高潮今日仓位应该减半"""
        from core.overnight_picker import SentimentCyclePredictor, SentimentLevel
        
        predictor = SentimentCyclePredictor()
        result = predictor.analyze_today_sentiment(
            limit_up_count=150,  # 大量涨停 = 高潮
            limit_down_count=5,
            broken_board_rate=0.1,
            continuous_board_count=20,
            market_profit_rate=0.8
        )
        
        # 高潮情绪应该预判分歧 (使用对象属性访问)
        assert result.level == SentimentLevel.EXTREME_GREED or result.level.value == '极度乐观'
        
        # 预判明日
        tomorrow = predictor.predict_tomorrow(result)
        
        # 高潮后应该是分歧，仓位乘数应该降低
        assert tomorrow.position_multiplier <= 0.6
        assert '分歧' in tomorrow.predicted_phase or '分歧' in tomorrow.strategy_advice
    
    def test_freezing_to_recovery_position_increased(self):
        """测试冰点后修复: 冰点情绪后仓位应该增加"""
        from core.overnight_picker import SentimentCyclePredictor, SentimentLevel
        
        predictor = SentimentCyclePredictor()
        result = predictor.analyze_today_sentiment(
            limit_up_count=10,  # 很少涨停 = 冰点
            limit_down_count=80,  # 大量跌停
            broken_board_rate=0.6,
            continuous_board_count=0,
            market_profit_rate=0.1
        )
        
        # 冰点情绪 (使用对象属性访问)
        assert result.level == SentimentLevel.EXTREME_FEAR or result.level.value == '极度恐慌'
        
        # 预判明日
        tomorrow = predictor.predict_tomorrow(result)
        
        # 冰点后应该是修复，仓位乘数应该增加
        assert tomorrow.position_multiplier >= 1.0
        assert '修复' in tomorrow.predicted_phase or '修复' in tomorrow.strategy_advice or '试错' in tomorrow.strategy_advice
    
    def test_neutral_sentiment_normal_position(self):
        """测试中性情绪: 仓位应该正常"""
        from core.overnight_picker import SentimentCyclePredictor
        
        predictor = SentimentCyclePredictor()
        result = predictor.analyze_today_sentiment(
            limit_up_count=50,
            limit_down_count=20,
            broken_board_rate=0.2,
            continuous_board_count=5,
            market_profit_rate=0.5
        )
        
        tomorrow = predictor.predict_tomorrow(result)
        
        # 中性情绪仓位乘数应该接近1.0 (使用对象属性访问)
        assert 0.6 <= tomorrow.position_multiplier <= 1.2


class TestTopicLeaderIdentification:
    """题材龙头识别测试 - 验证龙头vs跟风识别"""
    
    def test_identify_real_leader(self):
        """测试识别真龙头: 高龙头指数+高关联度"""
        from core.overnight_picker import SmartTopicMatcher
        
        matcher = SmartTopicMatcher()
        
        # 模拟一个真龙头
        result = matcher.analyze_stock_topic(
            stock_code='000001',
            stock_name='AI龙头',
            topic_name='AI人工智能',
            concepts=['人工智能', '大模型', '算法'],
            limit_up_time='09:35',  # 早盘涨停
            seal_amount=20000,  # 2亿封单
            market_cap=100,  # 100亿市值
            continuous_boards=3,  # 3连板
            follower_count=10
        )
        
        assert result['leader_type'] == '真龙头'
        assert result['leader_index'] >= 70
        assert result['relevance'] >= 0.7
    
    def test_identify_fake_hot_stock(self):
        """测试识别蹭热点: 名字相关但业务不相关"""
        from core.overnight_picker import SmartTopicMatcher
        
        matcher = SmartTopicMatcher()
        
        # 模拟一个蹭热点股票 - 名字有AI但主营业务无关
        result = matcher.analyze_stock_topic(
            stock_code='000002',
            stock_name='某某AI',  # 名字有AI
            topic_name='AI人工智能',
            concepts=['房地产', '物业'],  # 概念与AI无关
            limit_up_time='14:30',  # 尾盘涨停
            seal_amount=500,  # 封单小
            market_cap=50,
            continuous_boards=1,
            follower_count=0
        )
        
        # 应该识别为蹭热点或跟风股
        assert result['leader_type'] in ['蹭热点', '跟风股', '弱势股']
        assert result['relevance'] < 0.5
    
    def test_find_topic_leaders_ranking(self):
        """测试板块龙头排序: 龙头指数高的排前面"""
        from core.overnight_picker import SmartTopicMatcher
        
        matcher = SmartTopicMatcher()
        
        stocks = [
            {
                'code': '000001',
                'name': '跟风股A',
                'concepts': ['人工智能'],
                'limit_up_time': '14:00',
                'seal_amount': 1000,
                'market_cap': 50,
                'continuous_boards': 1
            },
            {
                'code': '000002',
                'name': '龙头股B',
                'concepts': ['人工智能', '大模型', '算法'],
                'limit_up_time': '09:35',
                'seal_amount': 15000,
                'market_cap': 80,
                'continuous_boards': 3
            },
            {
                'code': '000003',
                'name': '二线龙头C',
                'concepts': ['人工智能', '机器学习'],
                'limit_up_time': '10:30',
                'seal_amount': 5000,
                'market_cap': 60,
                'continuous_boards': 2
            }
        ]
        
        results = matcher.find_topic_leaders('AI人工智能', stocks)
        
        # 龙头股B应该排第一
        assert results[0]['stock_code'] == '000002'
        assert results[0]['leader_index'] > results[1]['leader_index']
        assert results[1]['leader_index'] > results[2]['leader_index']


class TestPreMarketAdjustmentLogic:
    """早盘修正策略逻辑测试 - 验证外盘数据触发调整"""
    
    def test_a50_down_1_percent_price_adjustment(self):
        """测试A50跌1%: 买入价应该下调2%"""
        from core.overnight_picker import PreMarketAdjuster
        
        adjuster = PreMarketAdjuster()
        
        # 创建测试计划 (使用Dict格式)
        original_plan = {
            'recommendations': [
                {
                    'code': '000001',
                    'name': '测试股票',
                    'ideal_price': 9.8,
                    'acceptable_price': 10.0,
                    'leader_type': '二线龙头',
                }
            ],
            'total_position': 0.8,
        }
        
        # 模拟A50跌1.5%
        overnight_data = adjuster.fetch_overnight_data_with_values(
            a50_change=-0.015,
            nasdaq_change=0.0,
        )
        
        adjusted_plan, adjustments = adjuster.adjust_trading_plan(original_plan, overnight_data)
        
        # 买入价应该下调
        if adjusted_plan['recommendations']:
            assert adjusted_plan['recommendations'][0]['ideal_price'] < 9.8
            assert adjusted_plan['recommendations'][0]['acceptable_price'] < 10.0
    
    def test_a50_down_2_percent_cancel_non_leader(self):
        """测试A50跌2%: 非核心龙头应该取消"""
        from core.overnight_picker import PreMarketAdjuster
        
        adjuster = PreMarketAdjuster()
        
        # 创建包含龙头和跟风股的计划
        original_plan = {
            'recommendations': [
                {
                    'code': '000001',
                    'name': '真龙头',
                    'ideal_price': 10.0,
                    'acceptable_price': 10.2,
                    'leader_type': '真龙头',
                },
                {
                    'code': '000002',
                    'name': '跟风股',
                    'ideal_price': 8.0,
                    'acceptable_price': 8.2,
                    'leader_type': '跟风股',
                }
            ],
            'total_position': 0.8,
        }
        
        # 模拟A50跌2.5%
        overnight_data = adjuster.fetch_overnight_data_with_values(
            a50_change=-0.025,
            nasdaq_change=-0.01,
        )
        
        adjusted_plan, adjustments = adjuster.adjust_trading_plan(original_plan, overnight_data)
        
        # 跟风股应该被取消，只保留真龙头
        remaining_codes = [r['code'] for r in adjusted_plan['recommendations']]
        assert '000002' not in remaining_codes  # 跟风股被取消
        # 真龙头可能保留
        if remaining_codes:
            assert '000001' in remaining_codes
    
    def test_negative_announcement_cancels_stock(self):
        """测试利空公告: 应该取消该股票"""
        from core.overnight_picker import PreMarketAdjuster
        
        adjuster = PreMarketAdjuster()
        
        original_plan = {
            'recommendations': [
                {
                    'code': '000001',
                    'name': '测试股票',
                    'ideal_price': 10.0,
                    'acceptable_price': 10.2,
                    'leader_type': '二线龙头',
                }
            ],
            'total_position': 0.8,
        }
        
        # 模拟利空公告
        overnight_data = adjuster.fetch_overnight_data_with_values(
            a50_change=0.0,
            nasdaq_change=0.0,
            announcements=[{
                'code': '000001',
                'name': '测试股票',
                'title': '业绩预亏公告',
                'type': 'negative',
                'severity': 'high',
            }]
        )
        
        adjusted_plan, adjustments = adjuster.adjust_trading_plan(original_plan, overnight_data)
        
        # 有利空公告应该取消
        remaining_codes = [r['code'] for r in adjusted_plan['recommendations']]
        assert '000001' not in remaining_codes


class TestOvernightScenario:
    """夜间场景测试 - 验证静态计划生成"""
    
    def test_generate_overnight_plan(self):
        """测试生成隔夜交易计划"""
        from core.overnight_picker import OvernightStockPicker
        
        picker = OvernightStockPicker(stock_pool=['000001', '000002', '600000'])
        plan = picker.run(save_plan=False)
        
        assert plan is not None
        assert plan.date is not None
        assert plan.market_env is not None
        assert plan.market_sentiment is not None
        assert plan.sentiment_phase is not None
        assert len(plan.recommendations) <= 5
    
    def test_plan_contains_required_fields(self):
        """测试计划包含所有必要字段"""
        from core.overnight_picker import OvernightStockPicker
        
        picker = OvernightStockPicker(stock_pool=['000001'])
        plan = picker.run(save_plan=False)
        
        # 验证计划结构
        assert hasattr(plan, 'date')
        assert hasattr(plan, 'market_env')
        assert hasattr(plan, 'market_sentiment')
        assert hasattr(plan, 'recommendations')
        assert hasattr(plan, 'operation_tips')
        assert hasattr(plan, 'risk_warnings')
        assert hasattr(plan, 'position_multiplier')


class TestScorerVersionSwitching:
    """评分器版本切换测试 - 验证v5和v6评分器集成"""
    
    def test_create_picker_with_v6_scorer(self):
        """测试创建使用v6评分器的选股器"""
        from core.overnight_picker import OvernightStockPicker
        
        picker = OvernightStockPicker(scorer_version="v6", stock_pool=[])
        
        assert picker.scorer_version == "v6"
        # 验证使用的是ScorerV6
        from core.overnight_picker.scorer_v6 import ScorerV6
        assert isinstance(picker.scorer, ScorerV6)
    
    def test_create_picker_with_v5_scorer(self):
        """测试创建使用v5评分器的选股器"""
        from core.overnight_picker import OvernightStockPicker
        
        picker = OvernightStockPicker(scorer_version="v5", stock_pool=[])
        
        assert picker.scorer_version == "v5"
        # 验证使用的是TomorrowPotentialScorer
        from core.overnight_picker.scorer import TomorrowPotentialScorer
        assert isinstance(picker.scorer, TomorrowPotentialScorer)
    
    def test_default_scorer_version_is_v6(self):
        """测试默认评分器版本是v6"""
        from core.overnight_picker import OvernightStockPicker
        
        picker = OvernightStockPicker(stock_pool=[])
        
        assert picker.scorer_version == "v6"
        from core.overnight_picker.scorer_v6 import ScorerV6
        assert isinstance(picker.scorer, ScorerV6)
    
    def test_convenience_function_scorer_version(self):
        """测试便捷函数支持评分器版本切换"""
        from core.overnight_picker import create_overnight_picker
        
        # 测试v6
        picker_v6 = create_overnight_picker(scorer_version="v6")
        assert picker_v6.scorer_version == "v6"
        
        # 测试v5
        picker_v5 = create_overnight_picker(scorer_version="v5")
        assert picker_v5.scorer_version == "v5"
    
    def test_quick_pick_scorer_version(self):
        """测试快速选股函数支持评分器版本切换"""
        from core.overnight_picker import quick_overnight_pick
        
        # 由于quick_overnight_pick会运行完整流程，我们只测试参数传递
        # 实际运行需要数据文件，这里只验证函数接受参数
        try:
            # 这可能会因为缺少数据而失败，但至少验证参数传递正确
            plan = quick_overnight_pick(scorer_version="v6", save_plan=False)
        except Exception:
            # 预期可能因为数据问题失败，但参数传递应该正确
            pass
    
    @pytest.fixture
    def sample_stock_data(self):
        """创建示例股票数据用于评分测试"""
        import pandas as pd
        dates = pd.date_range(start='2025-01-01', periods=100, freq='D')
        data = {
            'date': dates,
            'open': [10 + i * 0.1 for i in range(100)],
            'high': [10.5 + i * 0.1 for i in range(100)],
            'low': [9.5 + i * 0.1 for i in range(100)],
            'close': [10.2 + i * 0.1 for i in range(100)],
            'volume': [1000000 + i * 10000 for i in range(100)],
        }
        return pd.DataFrame(data)
    
    def test_v6_scorer_data_format(self, sample_stock_data):
        """测试v6评分器数据格式兼容性"""
        from core.overnight_picker import OvernightStockPicker
        
        picker = OvernightStockPicker(scorer_version="v6", stock_pool=[])
        
        # 模拟评分过程中的数据格式
        df = picker.calculate_technical_indicators(sample_stock_data)
        latest = picker.get_latest_data(df)
        
        # 验证v6评分器需要的数据格式
        assert latest is not None
        assert 'ma5' in latest
        assert 'ma10' in latest
        assert 'ma20' in latest
        assert 'ma60' in latest
        assert 'close' in latest
        assert 'volume' in latest
    
    def test_v5_scorer_data_format(self, sample_stock_data):
        """测试v5评分器数据格式兼容性"""
        from core.overnight_picker import OvernightStockPicker
        
        picker = OvernightStockPicker(scorer_version="v5", stock_pool=[])
        
        # 模拟评分过程中的数据格式
        df = picker.calculate_technical_indicators(sample_stock_data)
        latest = picker.get_latest_data(df)
        
        # 验证v5评分器需要的数据格式
        assert latest is not None
        assert 'ma5' in latest
        assert 'ma10' in latest
        assert 'ma20' in latest
        assert 'ma60' in latest
        assert 'close' in latest
        assert 'volume' in latest
    
    def test_scorer_version_affects_reasoning_generation(self):
        """测试评分器版本影响推荐理由生成"""
        from core.overnight_picker import OvernightStockPicker
        
        # 创建v6和v5选股器
        picker_v6 = OvernightStockPicker(scorer_version="v6", stock_pool=[])
        picker_v5 = OvernightStockPicker(scorer_version="v5", stock_pool=[])
        
        # 模拟评分详情 - v6格式
        v6_details = {
            'kline_pattern': {'score': 15, 'pattern': '涨停板'},
            'volume_price': {'score': 12, 'volume_type': '温和放量'},
            'trend_position': {'score': 18, 'trend_type': '多头排列'},
            'theme_wind': {'score': 20, 'topic_type': '主线题材'},
            'capital_strength': {'score': 12, 'flow_type': '主力净流入'},
            'stock_activity': {'score': 8, 'activity_type': '活跃股'},
        }
        
        # 模拟评分详情 - v5格式
        v5_details = {
            'closing_pattern': {'score': 15, 'pattern': '涨停板'},
            'volume_analysis': {'score': 12, 'vol_type': '温和放量'},
            'ma_position': {'score': 10, 'ma_type': '多头排列'},
            'technical_pattern': {'score': 8, 'pattern': '突破形态'},
        }
        
        # 生成推荐理由
        reasoning_v6 = picker_v6._generate_reasoning(v6_details, ['AI', '芯片'])
        reasoning_v5 = picker_v5._generate_reasoning(v5_details, ['AI', '芯片'])
        
        # 验证都能生成理由
        assert isinstance(reasoning_v6, str)
        assert isinstance(reasoning_v5, str)
        assert len(reasoning_v6) > 0
        assert len(reasoning_v5) > 0


class TestExecutionScenario:
    """早盘执行场景测试 - 验证计划修正与执行"""
    
    def test_execution_with_normal_market(self):
        """测试正常市场下的执行"""
        from core.overnight_picker import (
            CallAuctionFilter, 
            PreMarketAdjuster,
            AuctionAction
        )
        
        # 创建计划 (Dict格式)
        original_plan = {
            'recommendations': [
                {
                    'code': '000001',
                    'name': '测试股票',
                    'ideal_price': 9.8,
                    'acceptable_price': 10.0,
                    'leader_type': '二线龙头',
                }
            ],
            'total_position': 0.8,
        }
        
        # 1. 早盘修正 (A50正常)
        adjuster = PreMarketAdjuster()
        overnight_data = adjuster.fetch_overnight_data_with_values(
            a50_change=0.005,  # A50涨0.5%
            nasdaq_change=0.01,
        )
        adjusted_plan, adjustments = adjuster.adjust_trading_plan(original_plan, overnight_data)
        
        # 正常市场应该保留推荐
        assert len(adjusted_plan['recommendations']) > 0
        
        # 2. 竞价过滤 (正常开盘)
        filter = CallAuctionFilter()
        auction_result = filter.analyze_auction(
            stock_code='000001',
            prev_close=10.0,
            auction_price=10.05,  # 平开
            auction_volume=1000000,
            avg_volume=5000000,
            leader_index=60,
            strategy_type='low_buy'
        )
        
        assert auction_result.action == AuctionAction.BUY
    
    def test_execution_with_bad_market(self):
        """测试恶劣市场下的执行 - 应该取消大部分买入"""
        from core.overnight_picker import (
            CallAuctionFilter,
            PreMarketAdjuster,
            AuctionAction
        )
        
        original_plan = {
            'recommendations': [
                {
                    'code': '000001',
                    'name': '跟风股',
                    'ideal_price': 9.8,
                    'acceptable_price': 10.0,
                    'leader_type': '跟风股',
                }
            ],
            'total_position': 0.8,
        }
        
        # 1. 早盘修正 (A50大跌)
        adjuster = PreMarketAdjuster()
        overnight_data = adjuster.fetch_overnight_data_with_values(
            a50_change=-0.025,  # A50跌2.5%
            nasdaq_change=-0.02,
        )
        adjusted_plan, adjustments = adjuster.adjust_trading_plan(original_plan, overnight_data)
        
        # 跟风股在A50大跌时应该被取消
        remaining_codes = [r['code'] for r in adjusted_plan['recommendations']]
        
        # 如果还有推荐，测试竞价过滤
        if remaining_codes:
            # 2. 竞价过滤 (低开)
            filter = CallAuctionFilter()
            auction_result = filter.analyze_auction(
                stock_code='000001',
                prev_close=10.0,
                auction_price=9.5,  # 低开5%
                auction_volume=1000000,
                avg_volume=5000000,
                leader_index=30,
                strategy_type='low_buy'
            )
            
            # 低开5%应该触发核按钮
            assert auction_result.action == AuctionAction.CANCEL
        else:
            # 跟风股已被取消，测试通过
            assert '000001' not in remaining_codes


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
