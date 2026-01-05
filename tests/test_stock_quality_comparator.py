"""
股票质量比较器测试

测试新增股票与现有股票质量比较功能
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from core.stock_screener import (
    StockQualityComparator,
    StockQualityMetrics,
    QualityComparisonResult,
    QualityComparisonStatus,
    ORIGINAL_STOCK_CODES,
    get_stock_quality_comparator,
    reset_stock_quality_comparator,
)


# ============== 测试数据 ==============

def create_test_stock_data(
    n_existing: int = 10,
    n_new: int = 20,
    existing_quality: str = "medium",
    new_quality: str = "medium"
) -> pd.DataFrame:
    """
    创建测试股票数据
    
    Args:
        n_existing: 现有股票数量
        n_new: 新增股票数量
        existing_quality: 现有股票质量 (low/medium/high)
        new_quality: 新增股票质量 (low/medium/high)
    """
    np.random.seed(42)
    
    # 质量参数映射
    quality_params = {
        "low": {"roe": (2, 8), "growth": (-10, 10), "market_cap": (20, 50)},
        "medium": {"roe": (8, 15), "growth": (5, 20), "market_cap": (50, 150)},
        "high": {"roe": (15, 25), "growth": (15, 40), "market_cap": (150, 500)},
    }
    
    existing_params = quality_params[existing_quality]
    new_params = quality_params[new_quality]
    
    # 使用原始股票代码的前n_existing个作为现有股票
    existing_codes = list(ORIGINAL_STOCK_CODES)[:n_existing]
    # 生成新增股票代码
    new_codes = [f"{600100 + i:06d}" for i in range(n_new)]
    
    all_codes = existing_codes + new_codes
    n_total = len(all_codes)
    
    # 生成sector数据，确保长度匹配
    sectors = ['半导体', '人工智能', '算力', '消费电子', '新能源科技']
    sector_list = [sectors[i % len(sectors)] for i in range(n_total)]
    
    # 生成数据
    data = {
        'code': all_codes,
        'name': [f"股票{i}" for i in range(n_total)],
        'sector': sector_list,
    }
    
    # 为现有股票和新增股票分别生成质量数据
    roe_values = []
    growth_values = []
    market_cap_values = []
    
    for i in range(n_total):
        if i < n_existing:
            params = existing_params
        else:
            params = new_params
        
        roe_values.append(np.random.uniform(*params["roe"]))
        growth_values.append(np.random.uniform(*params["growth"]))
        market_cap_values.append(np.random.uniform(*params["market_cap"]))
    
    data['roe'] = roe_values
    data['debt_ratio'] = list(np.random.uniform(20, 60, n_total))
    data['gross_margin'] = list(np.random.uniform(20, 50, n_total))
    data['net_margin'] = list(np.random.uniform(5, 20, n_total))
    data['revenue_growth_1y'] = growth_values
    data['profit_growth_1y'] = [g * 1.2 for g in growth_values]
    data['rd_ratio'] = list(np.random.uniform(3, 10, n_total))
    data['total_market_cap'] = market_cap_values
    data['daily_turnover'] = list(np.random.uniform(1, 10, n_total))
    data['turnover_rate'] = list(np.random.uniform(0.5, 3, n_total))
    
    return pd.DataFrame(data)


# ============== 单元测试 ==============

class TestStockQualityComparator:
    """股票质量比较器测试"""
    
    def test_initialization(self):
        """测试初始化"""
        comparator = StockQualityComparator()
        assert comparator.original_codes == ORIGINAL_STOCK_CODES
        assert comparator.quality_threshold_ratio == 0.95
    
    def test_custom_initialization(self):
        """测试自定义初始化"""
        custom_codes = {"000001", "000002"}
        comparator = StockQualityComparator(
            original_codes=custom_codes,
            quality_threshold_ratio=0.90
        )
        assert comparator.original_codes == custom_codes
        assert comparator.quality_threshold_ratio == 0.90
    
    def test_calculate_stock_quality(self):
        """测试单只股票质量计算"""
        comparator = StockQualityComparator()
        
        row = pd.Series({
            'code': '000001',
            'name': '测试股票',
            'sector': '半导体',
            'roe': 15.0,
            'debt_ratio': 40.0,
            'gross_margin': 35.0,
            'net_margin': 12.0,
            'revenue_growth_1y': 20.0,
            'profit_growth_1y': 25.0,
            'rd_ratio': 6.0,
            'total_market_cap': 200.0,
            'daily_turnover': 5.0,
            'turnover_rate': 2.0,
        })
        
        metrics = comparator.calculate_stock_quality(row, is_new=False)
        
        assert isinstance(metrics, StockQualityMetrics)
        assert metrics.code == '000001'
        assert metrics.name == '测试股票'
        assert 0 <= metrics.financial_health_score <= 100
        assert 0 <= metrics.growth_score <= 100
        assert 0 <= metrics.liquidity_score <= 100
        assert 0 <= metrics.overall_quality_score <= 100
        assert metrics.is_new_stock == False
    
    def test_compare_quality_empty_data(self):
        """测试空数据比较"""
        comparator = StockQualityComparator()
        result = comparator.compare_quality(pd.DataFrame())
        
        assert result.status == QualityComparisonStatus.INSUFFICIENT_DATA
        assert "数据为空" in result.warnings
    
    def test_compare_quality_no_existing_stocks(self):
        """测试无现有股票数据"""
        comparator = StockQualityComparator(original_codes={"999999"})
        df = create_test_stock_data(n_existing=0, n_new=10)
        
        result = comparator.compare_quality(df)
        
        assert result.status == QualityComparisonStatus.INSUFFICIENT_DATA
    
    def test_compare_quality_no_new_stocks(self):
        """测试无新增股票数据"""
        comparator = StockQualityComparator()
        # 只包含现有股票
        existing_codes = list(ORIGINAL_STOCK_CODES)[:5]
        df = pd.DataFrame({
            'code': existing_codes,
            'name': [f"股票{i}" for i in range(5)],
            'roe': [15.0] * 5,
        })
        
        result = comparator.compare_quality(df)
        
        assert result.status == QualityComparisonStatus.INSUFFICIENT_DATA
        assert result.existing_stock_count == 5
    
    def test_compare_quality_new_higher_quality(self):
        """测试新增股票质量更高的情况"""
        comparator = StockQualityComparator()
        df = create_test_stock_data(
            n_existing=10,
            n_new=20,
            existing_quality="medium",
            new_quality="high"
        )
        
        result = comparator.compare_quality(df)
        
        assert result.status == QualityComparisonStatus.PASSED
        assert result.passed_overall == True
        assert result.overall_diff > 0
    
    def test_compare_quality_new_lower_quality(self):
        """测试新增股票质量更低的情况"""
        comparator = StockQualityComparator()
        df = create_test_stock_data(
            n_existing=10,
            n_new=20,
            existing_quality="high",
            new_quality="low"
        )
        
        result = comparator.compare_quality(df)
        
        assert result.status == QualityComparisonStatus.FAILED
        assert result.passed_overall == False
        assert result.overall_diff < 0
    
    def test_compare_quality_similar_quality(self):
        """测试新增股票质量相近的情况"""
        comparator = StockQualityComparator()
        df = create_test_stock_data(
            n_existing=10,
            n_new=20,
            existing_quality="medium",
            new_quality="medium"
        )
        
        result = comparator.compare_quality(df)
        
        # 相近质量应该通过（在95%阈值内）
        assert result.status in [QualityComparisonStatus.PASSED, QualityComparisonStatus.FAILED]
        assert result.existing_stock_count == 10
        assert result.new_stock_count == 20
    
    def test_generate_comparison_report(self):
        """测试生成比较报告"""
        comparator = StockQualityComparator()
        df = create_test_stock_data(n_existing=10, n_new=20)
        
        result = comparator.compare_quality(df)
        report = comparator.generate_comparison_report(result)
        
        assert "股票质量比较报告" in report
        assert "现有股票统计" in report
        assert "新增股票统计" in report
        assert "质量差异分析" in report
        assert "验证结论" in report
    
    def test_validate_new_stock_quality(self):
        """测试验证新增股票质量"""
        comparator = StockQualityComparator()
        df = create_test_stock_data(
            n_existing=10,
            n_new=20,
            existing_quality="medium",
            new_quality="high"
        )
        
        passed, message, result = comparator.validate_new_stock_quality(df)
        
        assert passed == True
        assert "✅" in message
        assert result.status == QualityComparisonStatus.PASSED


class TestStockQualityMetrics:
    """股票质量指标测试"""
    
    def test_metrics_creation(self):
        """测试指标创建"""
        metrics = StockQualityMetrics(
            code="000001",
            name="测试股票",
            sector="半导体",
            financial_health_score=80.0,
            growth_score=75.0,
            liquidity_score=85.0,
            overall_quality_score=80.0,
            is_new_stock=True
        )
        
        assert metrics.code == "000001"
        assert metrics.financial_health_score == 80.0
        assert metrics.is_new_stock == True


class TestQualityComparisonResult:
    """质量比较结果测试"""
    
    def test_result_creation(self):
        """测试结果创建"""
        result = QualityComparisonResult(
            timestamp=datetime.now(),
            status=QualityComparisonStatus.PASSED,
            existing_stock_count=10,
            new_stock_count=20,
            existing_avg_overall=75.0,
            new_avg_overall=78.0,
            overall_diff=3.0,
            passed_overall=True
        )
        
        assert result.status == QualityComparisonStatus.PASSED
        assert result.existing_stock_count == 10
        assert result.new_stock_count == 20
        assert result.passed_overall == True


class TestSingletonPattern:
    """单例模式测试"""
    
    def test_get_stock_quality_comparator(self):
        """测试获取单例实例"""
        reset_stock_quality_comparator()
        
        comparator1 = get_stock_quality_comparator()
        comparator2 = get_stock_quality_comparator()
        
        assert comparator1 is comparator2
    
    def test_reset_stock_quality_comparator(self):
        """测试重置单例实例"""
        comparator1 = get_stock_quality_comparator()
        reset_stock_quality_comparator()
        comparator2 = get_stock_quality_comparator()
        
        assert comparator1 is not comparator2


class TestOriginalStockCodes:
    """原始股票代码测试"""
    
    def test_original_codes_count(self):
        """测试原始股票代码数量"""
        # 原始27只股票
        assert len(ORIGINAL_STOCK_CODES) == 27
    
    def test_original_codes_format(self):
        """测试原始股票代码格式"""
        for code in ORIGINAL_STOCK_CODES:
            assert len(code) == 6
            assert code.isdigit()
            # 主板和中小板代码前缀
            assert code[:3] in ['000', '001', '002', '600', '601', '603']


# ============== 集成测试 ==============

class TestQualityComparisonIntegration:
    """质量比较集成测试"""
    
    def test_full_comparison_workflow(self):
        """测试完整比较流程"""
        # 1. 创建测试数据
        df = create_test_stock_data(
            n_existing=15,
            n_new=30,
            existing_quality="medium",
            new_quality="medium"
        )
        
        # 2. 获取比较器
        comparator = get_stock_quality_comparator()
        
        # 3. 执行比较
        result = comparator.compare_quality(df)
        
        # 4. 验证结果
        assert result.existing_stock_count > 0
        assert result.new_stock_count > 0
        assert result.status in QualityComparisonStatus
        
        # 5. 生成报告
        report = comparator.generate_comparison_report(result)
        assert len(report) > 0
        
        # 6. 验证质量
        passed, message, _ = comparator.validate_new_stock_quality(df)
        assert isinstance(passed, (bool, np.bool_))
        assert len(message) > 0
    
    def test_quality_threshold_sensitivity(self):
        """测试质量阈值敏感性"""
        df = create_test_stock_data(
            n_existing=10,
            n_new=20,
            existing_quality="high",
            new_quality="medium"
        )
        
        # 严格阈值
        strict_comparator = StockQualityComparator(quality_threshold_ratio=0.99)
        strict_result = strict_comparator.compare_quality(df)
        
        # 宽松阈值
        lenient_comparator = StockQualityComparator(quality_threshold_ratio=0.80)
        lenient_result = lenient_comparator.compare_quality(df)
        
        # 宽松阈值更容易通过
        assert lenient_result.passed_overall or not strict_result.passed_overall
