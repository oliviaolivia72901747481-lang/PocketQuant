"""
情绪周期预判器 (SentimentCyclePredictor) 测试

测试内容:
1. 基础框架测试
2. 今日情绪分析测试 (Requirements 9.1, 9.3)
3. 明日情绪预判测试 (Requirements 9.1-9.4)
4. 情绪周期位置测试 (Requirements 9.5)
5. 情绪报告生成测试 (Requirements 9.6)
"""

import pytest
from core.overnight_picker import (
    SentimentCyclePredictor,
    SentimentPhase,
    SentimentLevel,
    SentimentAnalysisResult,
    TomorrowPrediction,
    create_sentiment_predictor,
    quick_sentiment_prediction,
)


class TestSentimentPredictorBasics:
    """基础框架测试"""
    
    def test_create_predictor(self):
        """测试创建情绪预判器"""
        predictor = SentimentCyclePredictor()
        assert predictor is not None
        assert len(predictor.history) == 0
        assert predictor.last_analysis is None
        assert predictor.last_prediction is None
    
    def test_create_predictor_helper(self):
        """测试便捷创建函数"""
        predictor = create_sentiment_predictor()
        assert predictor is not None
        assert isinstance(predictor, SentimentCyclePredictor)
    
    def test_cycle_phases_defined(self):
        """测试周期阶段定义"""
        predictor = SentimentCyclePredictor()
        assert len(predictor.CYCLE_PHASES) == 6
        assert SentimentPhase.FREEZING in predictor.CYCLE_PHASES
        assert SentimentPhase.CLIMAX in predictor.CYCLE_PHASES


class TestTodaySentimentAnalysis:
    """今日情绪分析测试 (Requirements 9.1, 9.3)"""
    
    def test_analyze_climax_sentiment(self):
        """测试分析高潮情绪"""
        predictor = SentimentCyclePredictor()
        result = predictor.analyze_today_sentiment(
            limit_up_count=120,      # 涨停多
            limit_down_count=5,      # 跌停少
            broken_board_rate=0.1,   # 炸板率低
            continuous_board_count=12,  # 连板多
            market_profit_rate=0.75  # 赚钱效应好
        )
        
        assert result.phase == SentimentPhase.CLIMAX
        assert result.level == SentimentLevel.EXTREME_GREED
        assert result.score >= 85
    
    def test_analyze_freezing_sentiment(self):
        """测试分析冰点情绪"""
        predictor = SentimentCyclePredictor()
        result = predictor.analyze_today_sentiment(
            limit_up_count=8,        # 涨停少
            limit_down_count=60,     # 跌停多
            broken_board_rate=0.5,   # 炸板率高
            continuous_board_count=0,  # 无连板
            market_profit_rate=0.2   # 赚钱效应差
        )
        
        assert result.phase == SentimentPhase.FREEZING
        assert result.level == SentimentLevel.EXTREME_FEAR
        assert result.score < 35
    
    def test_analyze_divergence_sentiment(self):
        """测试分析分歧情绪"""
        predictor = SentimentCyclePredictor()
        result = predictor.analyze_today_sentiment(
            limit_up_count=60,       # 涨停中等
            limit_down_count=15,     # 跌停中等
            broken_board_rate=0.35,  # 炸板率高 - 关键特征
            continuous_board_count=5,
            market_profit_rate=0.5
        )
        
        assert result.phase == SentimentPhase.DIVERGENCE
    
    def test_analyze_warming_sentiment(self):
        """测试分析升温情绪"""
        predictor = SentimentCyclePredictor()
        result = predictor.analyze_today_sentiment(
            limit_up_count=80,
            limit_down_count=10,
            broken_board_rate=0.15,
            continuous_board_count=6,
            market_profit_rate=0.65
        )
        
        assert result.phase == SentimentPhase.WARMING
        assert result.level == SentimentLevel.GREED
    
    def test_sentiment_score_range(self):
        """测试情绪分数范围"""
        predictor = SentimentCyclePredictor()
        
        # 极端好
        result1 = predictor.analyze_today_sentiment(
            limit_up_count=150,
            limit_down_count=0,
            broken_board_rate=0.0,
            continuous_board_count=20,
            market_profit_rate=0.9
        )
        assert 0 <= result1.score <= 100
        
        # 极端差
        result2 = predictor.analyze_today_sentiment(
            limit_up_count=0,
            limit_down_count=100,
            broken_board_rate=0.8,
            continuous_board_count=0,
            market_profit_rate=0.1
        )
        assert 0 <= result2.score <= 100
    
    def test_analysis_saved_to_history(self):
        """测试分析结果保存到历史"""
        predictor = SentimentCyclePredictor()
        
        result = predictor.analyze_today_sentiment(
            limit_up_count=50,
            limit_down_count=10,
            broken_board_rate=0.2,
            continuous_board_count=5,
            market_profit_rate=0.5
        )
        
        assert len(predictor.history) == 1
        assert predictor.last_analysis == result


class TestTomorrowPrediction:
    """明日情绪预判测试 (Requirements 9.1-9.4)"""
    
    def test_predict_divergence_after_climax(self):
        """测试高潮后预判分歧 (Requirements 9.1)"""
        predictor = SentimentCyclePredictor()
        
        # 先分析今日为高潮
        today = predictor.analyze_today_sentiment(
            limit_up_count=120,
            limit_down_count=5,
            broken_board_rate=0.1,
            continuous_board_count=12,
            market_profit_rate=0.75
        )
        
        # 预判明日
        tomorrow = predictor.predict_tomorrow(today)
        
        assert tomorrow.predicted_phase == "分歧"
        assert tomorrow.position_multiplier == 0.5  # 仓位×0.5
        assert '减半仓位' in tomorrow.strategy_advice
        assert '核心龙头' in tomorrow.focus_stocks
    
    def test_predict_recovery_after_freezing(self):
        """测试冰点后预判修复 (Requirements 9.3)"""
        predictor = SentimentCyclePredictor()
        
        # 先分析今日为冰点
        today = predictor.analyze_today_sentiment(
            limit_up_count=8,
            limit_down_count=60,
            broken_board_rate=0.5,
            continuous_board_count=0,
            market_profit_rate=0.2
        )
        
        # 预判明日
        tomorrow = predictor.predict_tomorrow(today)
        
        assert tomorrow.predicted_phase == "修复"
        assert tomorrow.position_multiplier == 1.2  # 仓位×1.2
        assert '加仓' in tomorrow.strategy_advice
        assert '反包' in tomorrow.focus_stocks
    
    def test_predict_after_warming(self):
        """测试升温后预判"""
        predictor = SentimentCyclePredictor()
        
        today = predictor.analyze_today_sentiment(
            limit_up_count=80,
            limit_down_count=10,
            broken_board_rate=0.15,
            continuous_board_count=6,
            market_profit_rate=0.65
        )
        
        tomorrow = predictor.predict_tomorrow(today)
        
        assert '高潮' in tomorrow.predicted_phase or '升温' in tomorrow.predicted_phase
        assert tomorrow.position_multiplier == 1.0
    
    def test_predict_after_divergence(self):
        """测试分歧后预判"""
        predictor = SentimentCyclePredictor()
        
        today = predictor.analyze_today_sentiment(
            limit_up_count=60,
            limit_down_count=15,
            broken_board_rate=0.35,
            continuous_board_count=5,
            market_profit_rate=0.5
        )
        
        tomorrow = predictor.predict_tomorrow(today)
        
        assert '退潮' in tomorrow.predicted_phase or '修复' in tomorrow.predicted_phase
        assert tomorrow.position_multiplier == 0.7
    
    def test_predict_without_today_data(self):
        """测试无今日数据时的预判"""
        predictor = SentimentCyclePredictor()
        
        tomorrow = predictor.predict_tomorrow(None)
        
        assert tomorrow.predicted_phase == "未知"
        assert tomorrow.position_multiplier == 1.0
        assert tomorrow.confidence == 0.3
    
    def test_extreme_greed_forces_divergence_prediction(self):
        """测试极度乐观强制预判分歧 (Requirements 9.1)"""
        predictor = SentimentCyclePredictor()
        
        # 创建极度乐观的情绪结果
        today = SentimentAnalysisResult(
            phase=SentimentPhase.WARMING,  # 即使是升温
            level=SentimentLevel.EXTREME_GREED,  # 但情绪极度乐观
            score=90,
            description="测试"
        )
        
        tomorrow = predictor.predict_tomorrow(today)
        
        # 应该预判分歧
        assert tomorrow.predicted_phase == "分歧"
        assert tomorrow.position_multiplier == 0.5
    
    def test_extreme_fear_forces_recovery_prediction(self):
        """测试极度恐慌强制预判修复 (Requirements 9.3)"""
        predictor = SentimentCyclePredictor()
        
        # 创建极度恐慌的情绪结果
        today = SentimentAnalysisResult(
            phase=SentimentPhase.RETREAT,  # 即使是退潮
            level=SentimentLevel.EXTREME_FEAR,  # 但情绪极度恐慌
            score=20,
            description="测试"
        )
        
        tomorrow = predictor.predict_tomorrow(today)
        
        # 应该预判修复
        assert tomorrow.predicted_phase == "修复"
        assert tomorrow.position_multiplier == 1.2


class TestPositionAdjustment:
    """仓位调整测试 (Requirements 9.2, 9.4)"""
    
    def test_position_reduce_after_climax(self):
        """测试高潮后仓位减半 (Requirements 9.2)"""
        predictor = SentimentCyclePredictor()
        
        today = predictor.analyze_today_sentiment(
            limit_up_count=120,
            limit_down_count=5,
            broken_board_rate=0.1,
            continuous_board_count=12,
            market_profit_rate=0.75
        )
        
        base_position = 0.8
        adjusted, reason = predictor.get_position_adjustment(base_position, today)
        
        assert adjusted == pytest.approx(0.4, rel=0.01)  # 0.8 * 0.5
        assert '下调' in reason
    
    def test_position_increase_after_freezing(self):
        """测试冰点后仓位上调 (Requirements 9.4)"""
        predictor = SentimentCyclePredictor()
        
        today = predictor.analyze_today_sentiment(
            limit_up_count=8,
            limit_down_count=60,
            broken_board_rate=0.5,
            continuous_board_count=0,
            market_profit_rate=0.2
        )
        
        base_position = 0.5
        adjusted, reason = predictor.get_position_adjustment(base_position, today)
        
        assert adjusted == pytest.approx(0.6, rel=0.01)  # 0.5 * 1.2
        assert '上调' in reason
    
    def test_position_capped_at_80_percent(self):
        """测试仓位上限80%"""
        predictor = SentimentCyclePredictor()
        
        today = predictor.analyze_today_sentiment(
            limit_up_count=8,
            limit_down_count=60,
            broken_board_rate=0.5,
            continuous_board_count=0,
            market_profit_rate=0.2
        )
        
        base_position = 0.8  # 已经80%
        adjusted, reason = predictor.get_position_adjustment(base_position, today)
        
        # 即使×1.2也不应超过80%
        assert adjusted <= 0.8


class TestCyclePosition:
    """情绪周期位置测试 (Requirements 9.5)"""
    
    def test_get_cycle_position(self):
        """测试获取周期位置"""
        predictor = SentimentCyclePredictor()
        
        assert predictor.get_cycle_position(SentimentPhase.FREEZING) == 0
        assert predictor.get_cycle_position(SentimentPhase.RECOVERY) == 1
        assert predictor.get_cycle_position(SentimentPhase.WARMING) == 2
        assert predictor.get_cycle_position(SentimentPhase.CLIMAX) == 3
        assert predictor.get_cycle_position(SentimentPhase.DIVERGENCE) == 4
        assert predictor.get_cycle_position(SentimentPhase.RETREAT) == 5
    
    def test_get_next_phase(self):
        """测试获取下一阶段"""
        predictor = SentimentCyclePredictor()
        
        assert predictor.get_next_phase(SentimentPhase.FREEZING) == SentimentPhase.RECOVERY
        assert predictor.get_next_phase(SentimentPhase.CLIMAX) == SentimentPhase.DIVERGENCE
        assert predictor.get_next_phase(SentimentPhase.RETREAT) == SentimentPhase.FREEZING  # 循环


class TestSentimentReport:
    """情绪报告生成测试 (Requirements 9.6)"""
    
    def test_generate_report(self):
        """测试生成情绪报告"""
        predictor = SentimentCyclePredictor()
        
        today = predictor.analyze_today_sentiment(
            limit_up_count=80,
            limit_down_count=10,
            broken_board_rate=0.15,
            continuous_board_count=6,
            market_profit_rate=0.65
        )
        
        report = predictor.generate_sentiment_report(today)
        
        assert '情绪周期分析' in report
        assert '今日情绪' in report
        assert '明日预判' in report
        assert '市场数据' in report
    
    def test_report_without_data(self):
        """测试无数据时的报告"""
        predictor = SentimentCyclePredictor()
        
        report = predictor.generate_sentiment_report(None)
        
        assert '暂无情绪数据' in report


class TestQuickSentimentPrediction:
    """快速情绪预判测试"""
    
    def test_quick_prediction(self):
        """测试快速预判函数"""
        result = quick_sentiment_prediction(
            limit_up_count=80,
            limit_down_count=10,
            broken_board_rate=0.15,
            continuous_board_count=6,
            market_profit_rate=0.65
        )
        
        assert 'today' in result
        assert 'tomorrow' in result
        assert 'report' in result
        
        assert 'phase' in result['today']
        assert 'predicted_phase' in result['tomorrow']


class TestSentimentDataclasses:
    """数据类测试"""
    
    def test_sentiment_analysis_result_to_dict(self):
        """测试SentimentAnalysisResult转字典"""
        result = SentimentAnalysisResult(
            phase=SentimentPhase.WARMING,
            level=SentimentLevel.GREED,
            score=75,
            description="测试描述",
            limit_up_count=80,
            limit_down_count=10,
            broken_board_rate=0.15,
            continuous_board_count=6,
            market_profit_rate=0.65
        )
        
        d = result.to_dict()
        
        assert d['phase'] == '升温'
        assert d['level'] == '乐观'
        assert d['score'] == 75
        assert d['limit_up_count'] == 80
    
    def test_tomorrow_prediction_to_dict(self):
        """测试TomorrowPrediction转字典"""
        prediction = TomorrowPrediction(
            predicted_phase="分歧",
            position_multiplier=0.5,
            strategy_advice="减半仓位",
            focus_stocks="核心龙头",
            confidence=0.8
        )
        
        d = prediction.to_dict()
        
        assert d['predicted_phase'] == '分歧'
        assert d['position_multiplier'] == 0.5
        assert d['confidence'] == 0.8


class TestClearHistory:
    """历史记录清理测试"""
    
    def test_clear_history(self):
        """测试清空历史记录"""
        predictor = SentimentCyclePredictor()
        
        # 添加一些数据
        predictor.analyze_today_sentiment(
            limit_up_count=50,
            limit_down_count=10,
            broken_board_rate=0.2,
            continuous_board_count=5,
            market_profit_rate=0.5
        )
        
        assert len(predictor.history) == 1
        assert predictor.last_analysis is not None
        
        # 清空
        predictor.clear_history()
        
        assert len(predictor.history) == 0
        assert predictor.last_analysis is None
        assert predictor.last_prediction is None
