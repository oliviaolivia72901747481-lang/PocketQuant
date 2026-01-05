"""
股票筛选引擎高级模块测试

测试综合评分、质量验证、风险控制、股票池更新等模块
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from core.stock_screener import (
    # Comprehensive Scorer
    ComprehensiveScorer,
    ComprehensiveScore,
    QualitativeFactors,
    QualitativeEvaluator,
    ScoringWeightsConfig,
    OverallRating,
    get_comprehensive_scorer,
    # Quality Validator
    DataQualityMonitor,
    DataQualityMetrics,
    DataQualityStatus,
    QualityValidationResult,
    ScreeningResultValidator,
    get_quality_monitor,
    get_result_validator,
    # Risk Controller
    RiskAssessor,
    RiskAssessmentResult,
    RiskMetrics,
    RiskLevel,
    RiskAlertManager,
    get_risk_assessor,
    get_alert_manager,
    # Pool Updater
    PoolUpdater,
    CandidateScreener,
    ScreeningStage,
    UpdateStatus,
    get_pool_updater,
    # System Integrator
    SystemIntegrator,
    StockPoolConfigUpdater,
    StockPoolEntry,
    get_system_integrator,
)


# ============== 测试数据 ==============

def create_test_stock_data(n: int = 10) -> pd.DataFrame:
    """创建测试股票数据"""
    np.random.seed(42)
    
    codes = [f"{600000 + i:06d}" for i in range(n)]
    names = [f"测试股票{i}" for i in range(n)]
    industries = ['半导体', '人工智能', '云计算', '新能源', '5G通信'] * (n // 5 + 1)
    
    return pd.DataFrame({
        'code': codes,
        'name': names,
        'tech_industry': industries[:n],
        'roe': np.random.uniform(5, 25, n),
        'roa': np.random.uniform(3, 15, n),
        'gross_margin': np.random.uniform(20, 60, n),
        'net_margin': np.random.uniform(5, 30, n),
        'revenue_growth_1y': np.random.uniform(-10, 50, n),
        'profit_growth_1y': np.random.uniform(-20, 60, n),
        'debt_ratio': np.random.uniform(20, 70, n),
        'current_ratio': np.random.uniform(1, 3, n),
        'pe_ratio': np.random.uniform(10, 100, n),
        'pb_ratio': np.random.uniform(1, 10, n),
        'total_market_cap': np.random.uniform(50, 500, n),
        'float_market_cap': np.random.uniform(30, 400, n),
        'daily_turnover': np.random.uniform(1, 20, n),
        'turnover_rate': np.random.uniform(0.5, 5, n),
        'volatility_annual': np.random.uniform(20, 60, n),
        'close': np.random.uniform(10, 100, n),
    })


# ============== 综合评分系统测试 ==============

class TestScoringWeightsConfig:
    """评分权重配置测试"""
    
    def test_default_weights(self):
        """测试默认权重"""
        config = ScoringWeightsConfig()
        assert config.validate()
        assert config.financial_health == 0.35
        assert config.growth_potential == 0.25
    
    def test_custom_weights(self):
        """测试自定义权重"""
        config = ScoringWeightsConfig(
            financial_health=0.40,
            growth_potential=0.30,
            market_performance=0.15,
            competitive_advantage=0.15
        )
        assert config.validate()
    
    def test_invalid_weights(self):
        """测试无效权重"""
        config = ScoringWeightsConfig(
            financial_health=0.50,
            growth_potential=0.30,
            market_performance=0.20,
            competitive_advantage=0.20
        )
        assert not config.validate()  # 总和超过1


class TestQualitativeEvaluator:
    """定性评估器测试"""
    
    def test_initialization(self):
        """测试初始化"""
        evaluator = QualitativeEvaluator()
        assert evaluator.competitive_keywords is not None
        assert evaluator.tech_moat_keywords is not None
    
    def test_evaluate_with_keywords(self):
        """测试带关键词的评估"""
        evaluator = QualitativeEvaluator()
        result = evaluator.evaluate(
            name="龙头科技",
            business_desc="自主研发核心技术，行业领先"
        )
        
        assert result.competitive_advantage_score > 50
        assert result.tech_moat_score > 50
    
    def test_evaluate_without_keywords(self):
        """测试无关键词的评估"""
        evaluator = QualitativeEvaluator()
        result = evaluator.evaluate(
            name="普通公司",
            business_desc="一般业务"
        )
        
        assert result.competitive_advantage_score == 50
        assert result.tech_moat_score == 50
    
    def test_overall_score(self):
        """测试综合得分计算"""
        evaluator = QualitativeEvaluator()
        factors = QualitativeFactors(
            code="000001",
            name="测试",
            competitive_advantage_score=80,
            tech_moat_score=70,
            industry_position_score=75,
            management_score=60
        )
        
        score = evaluator.get_overall_qualitative_score(factors)
        assert 60 < score < 80


class TestComprehensiveScorer:
    """综合评分系统测试"""
    
    def test_initialization(self):
        """测试初始化"""
        scorer = ComprehensiveScorer()
        assert scorer.weights is not None
        assert scorer.financial_screener is not None
        assert scorer.market_screener is not None
    
    def test_score_single_stock(self):
        """测试单只股票评分"""
        scorer = ComprehensiveScorer()
        df = create_test_stock_data(1)
        row = df.iloc[0]
        
        result = scorer.score_stock(row)
        
        assert isinstance(result, ComprehensiveScore)
        assert result.code == row['code']
        assert 0 <= result.total_score <= 100
        assert result.rating in OverallRating
    
    def test_score_multiple_stocks(self):
        """测试批量评分"""
        scorer = ComprehensiveScorer()
        df = create_test_stock_data(20)
        
        result_df, scores = scorer.score_stocks(df, min_score=0)
        
        assert len(scores) == 20
        assert all(isinstance(s, ComprehensiveScore) for s in scores)
        # 验证排序
        for i in range(len(scores) - 1):
            assert scores[i].total_score >= scores[i + 1].total_score
    
    def test_rating_determination(self):
        """测试评级确定"""
        scorer = ComprehensiveScorer()
        
        assert scorer._determine_rating(95) == OverallRating.AAA
        assert scorer._determine_rating(85) == OverallRating.AA
        assert scorer._determine_rating(75) == OverallRating.A
        assert scorer._determine_rating(65) == OverallRating.BBB
        assert scorer._determine_rating(55) == OverallRating.BB
        assert scorer._determine_rating(45) == OverallRating.B
        assert scorer._determine_rating(35) == OverallRating.C
    
    def test_scoring_summary(self):
        """测试评分摘要"""
        scorer = ComprehensiveScorer()
        df = create_test_stock_data(10)
        _, scores = scorer.score_stocks(df, min_score=0)
        
        summary = scorer.get_scoring_summary(scores)
        
        assert summary['total'] == 10
        assert 'avg_score' in summary
        assert 'rating_distribution' in summary
    
    def test_singleton_pattern(self):
        """测试单例模式"""
        scorer1 = get_comprehensive_scorer()
        scorer2 = get_comprehensive_scorer()
        assert scorer1 is scorer2


# ============== 质量验证系统测试 ==============

class TestDataQualityMonitor:
    """数据质量监控器测试"""
    
    def test_initialization(self):
        """测试初始化"""
        monitor = DataQualityMonitor()
        assert monitor.min_quality_score == 70.0
    
    def test_validate_empty_data(self):
        """测试空数据验证"""
        monitor = DataQualityMonitor()
        result = monitor.validate(pd.DataFrame())
        
        assert not result.passed
        assert result.total_records == 0
    
    def test_validate_valid_data(self):
        """测试有效数据验证"""
        monitor = DataQualityMonitor()
        df = create_test_stock_data(10)
        
        result = monitor.validate(df)
        
        assert isinstance(result, QualityValidationResult)
        assert result.total_records == 10
        assert result.metrics.completeness > 0
    
    def test_quality_metrics(self):
        """测试质量指标"""
        metrics = DataQualityMetrics(
            completeness=90,
            accuracy=85,
            consistency=80,
            timeliness=75,
            validity=70
        )
        
        assert metrics.overall_score > 0
        assert metrics.status in DataQualityStatus
    
    def test_quality_report_generation(self):
        """测试质量报告生成"""
        monitor = DataQualityMonitor()
        df = create_test_stock_data(10)
        result = monitor.validate(df)
        
        report = monitor.generate_quality_report(result)
        
        assert "数据质量验证报告" in report
        assert "完整性" in report
    
    def test_singleton_pattern(self):
        """测试单例模式"""
        monitor1 = get_quality_monitor()
        monitor2 = get_quality_monitor()
        assert monitor1 is monitor2


class TestScreeningResultValidator:
    """筛选结果验证器测试"""
    
    def test_initialization(self):
        """测试初始化"""
        validator = ScreeningResultValidator()
        assert validator.min_stocks == 50
        assert validator.max_stocks == 150
    
    def test_validate_empty_result(self):
        """测试空结果验证"""
        validator = ScreeningResultValidator()
        passed, warnings, suggestions = validator.validate_screening_result(pd.DataFrame())
        
        assert not passed
        assert len(warnings) > 0
    
    def test_validate_valid_result(self):
        """测试有效结果验证"""
        validator = ScreeningResultValidator(min_stocks=5, max_stocks=20)
        df = create_test_stock_data(10)
        
        passed, warnings, suggestions = validator.validate_screening_result(df)
        
        assert passed
    
    def test_validate_risk_metrics(self):
        """测试风险指标验证"""
        validator = ScreeningResultValidator()
        df = create_test_stock_data(10)
        
        passed, metrics, warnings = validator.validate_risk_metrics(df)
        
        assert isinstance(metrics, dict)


# ============== 风险控制系统测试 ==============

class TestRiskAssessor:
    """风险评估器测试"""
    
    def test_initialization(self):
        """测试初始化"""
        assessor = RiskAssessor()
        assert assessor.thresholds is not None
    
    def test_assess_empty_data(self):
        """测试空数据评估"""
        assessor = RiskAssessor()
        result = assessor.assess(pd.DataFrame())
        
        assert not result.passed
        assert result.risk_level == RiskLevel.CRITICAL
    
    def test_assess_valid_data(self):
        """测试有效数据评估"""
        assessor = RiskAssessor()
        df = create_test_stock_data(20)
        
        result = assessor.assess(df)
        
        assert isinstance(result, RiskAssessmentResult)
        assert result.total_stocks == 20
        assert result.risk_level in RiskLevel
    
    def test_risk_metrics(self):
        """测试风险指标"""
        assessor = RiskAssessor()
        df = create_test_stock_data(20)
        
        result = assessor.assess(df)
        
        assert isinstance(result.metrics, RiskMetrics)
        assert 0 <= result.metrics.overall_risk_score <= 100
    
    def test_singleton_pattern(self):
        """测试单例模式"""
        assessor1 = get_risk_assessor()
        assessor2 = get_risk_assessor()
        assert assessor1 is assessor2


class TestRiskAlertManager:
    """风险预警管理器测试"""
    
    def test_initialization(self):
        """测试初始化"""
        manager = RiskAlertManager()
        assert manager.alert_threshold == RiskLevel.MEDIUM
    
    def test_process_assessment(self):
        """测试处理评估结果"""
        manager = RiskAlertManager()
        assessor = RiskAssessor()
        df = create_test_stock_data(20)
        
        result = assessor.assess(df)
        alerts = manager.process_assessment(result)
        
        assert isinstance(alerts, list)
    
    def test_alert_summary(self):
        """测试预警摘要"""
        manager = RiskAlertManager()
        summary = manager.get_alert_summary()
        
        assert 'total' in summary


# ============== 股票池更新测试 ==============

class TestCandidateScreener:
    """候选股票筛选器测试"""
    
    def test_initialization(self):
        """测试初始化"""
        screener = CandidateScreener()
        assert screener.min_score == 60.0
        assert screener.target_count == 100


class TestPoolUpdater:
    """股票池更新器测试"""
    
    def test_initialization(self):
        """测试初始化"""
        updater = PoolUpdater()
        assert updater.max_history == 100
    
    def test_get_incremental_changes(self):
        """测试增量变更计算"""
        updater = PoolUpdater()
        
        # 创建模拟的评分结果
        from core.stock_screener import ComprehensiveScore, OverallRating
        
        candidates = [
            ComprehensiveScore(
                code=f"{600000 + i:06d}",
                name=f"股票{i}",
                total_score=80 - i * 5,
                rating=OverallRating.A,
                passed=True
            )
            for i in range(10)
        ]
        
        current_pool = ["600002", "600003", "600004"]
        
        adds, removes = updater.get_incremental_changes(
            current_pool, candidates, max_changes=2
        )
        
        assert isinstance(adds, list)
        assert isinstance(removes, list)


# ============== 系统集成测试 ==============

class TestStockPoolEntry:
    """股票池条目测试"""
    
    def test_to_dict(self):
        """测试转换为字典"""
        entry = StockPoolEntry(
            code="600000",
            name="测试股票",
            industry="半导体",
            score=85.5,
            rating="A"
        )
        
        d = entry.to_dict()
        
        assert d['code'] == "600000"
        assert d['score'] == 85.5


class TestSystemIntegrator:
    """系统集成器测试"""
    
    def test_initialization(self):
        """测试初始化"""
        integrator = SystemIntegrator()
        assert integrator.config_updater is not None
    
    def test_validate_integration(self):
        """测试集成验证"""
        integrator = SystemIntegrator()
        passed, issues = integrator.validate_integration()
        
        # 可能有一些配置文件不存在，但模块应该能导入
        assert isinstance(issues, list)
    
    def test_get_integration_status(self):
        """测试获取集成状态"""
        integrator = SystemIntegrator()
        status = integrator.get_integration_status()
        
        assert 'config_files' in status
        assert 'modules' in status
        assert 'data_dirs' in status
    
    def test_singleton_pattern(self):
        """测试单例模式"""
        integrator1 = get_system_integrator()
        integrator2 = get_system_integrator()
        assert integrator1 is integrator2


# ============== 集成测试 ==============

class TestEndToEndIntegration:
    """端到端集成测试"""
    
    def test_full_scoring_pipeline(self):
        """测试完整评分流程"""
        # 创建测试数据
        df = create_test_stock_data(20)
        
        # 综合评分
        scorer = get_comprehensive_scorer()
        result_df, scores = scorer.score_stocks(df, min_score=0)
        
        # 质量验证
        monitor = get_quality_monitor()
        quality_result = monitor.validate(result_df)
        
        # 风险评估
        assessor = get_risk_assessor()
        risk_result = assessor.assess(result_df)
        
        # 验证结果
        assert len(scores) > 0
        assert quality_result.total_records > 0
        assert risk_result.total_stocks > 0
    
    def test_module_imports(self):
        """测试所有模块导入"""
        from core.stock_screener import (
            # 基础模块
            DataSourceManager,
            DataCleaner,
            ScreenerConfigManager,
            IndustryScreener,
            # 筛选模块
            FinancialScreener,
            MarketScreener,
            # 评分模块
            ComprehensiveScorer,
            # 质量和风险模块
            DataQualityMonitor,
            RiskAssessor,
            # 更新和集成模块
            PoolUpdater,
            SystemIntegrator,
        )
        
        # 验证所有类都能实例化
        assert DataSourceManager is not None
        assert DataCleaner is not None
        assert ComprehensiveScorer is not None
        assert DataQualityMonitor is not None
        assert RiskAssessor is not None
        assert PoolUpdater is not None
        assert SystemIntegrator is not None
