"""
股票质量比较器

提供新增股票与现有股票质量比较功能，包括：
- 计算现有股票平均质量得分
- 计算新增股票平均质量得分
- 验证新增股票质量是否达标
- 生成质量比较报告

Requirements: 成功标准验证 - 新增股票质量不低于现有股票平均水平
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Set
from enum import Enum
from datetime import datetime
import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class QualityComparisonStatus(Enum):
    """质量比较状态"""
    PASSED = "passed"           # 新增股票质量达标
    FAILED = "failed"           # 新增股票质量未达标
    INSUFFICIENT_DATA = "insufficient_data"  # 数据不足


@dataclass
class StockQualityMetrics:
    """股票质量指标"""
    code: str
    name: str
    sector: str
    
    # 财务健康度指标
    financial_health_score: float = 0.0
    
    # 成长性指标
    growth_score: float = 0.0
    
    # 流动性指标
    liquidity_score: float = 0.0
    
    # 综合质量得分
    overall_quality_score: float = 0.0
    
    # 是否为新增股票
    is_new_stock: bool = False


@dataclass
class QualityComparisonResult:
    """质量比较结果"""
    timestamp: datetime
    status: QualityComparisonStatus
    
    # 现有股票统计
    existing_stock_count: int = 0
    existing_avg_financial_health: float = 0.0
    existing_avg_growth: float = 0.0
    existing_avg_liquidity: float = 0.0
    existing_avg_overall: float = 0.0
    
    # 新增股票统计
    new_stock_count: int = 0
    new_avg_financial_health: float = 0.0
    new_avg_growth: float = 0.0
    new_avg_liquidity: float = 0.0
    new_avg_overall: float = 0.0
    
    # 比较结果
    financial_health_diff: float = 0.0
    growth_diff: float = 0.0
    liquidity_diff: float = 0.0
    overall_diff: float = 0.0
    
    # 验证结果
    passed_financial_health: bool = False
    passed_growth: bool = False
    passed_liquidity: bool = False
    passed_overall: bool = False
    
    # 详细信息
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    # 低于平均水平的新增股票
    below_average_stocks: List[str] = field(default_factory=list)


# 原始27只股票代码（扩充前的股票池）
ORIGINAL_STOCK_CODES: Set[str] = {
    # 半导体 (7只)
    "002371", "002049", "603501", "002185", "600584", "002156", "603986",
    # 人工智能 (3只)
    "002415", "002230", "002410",
    # 算力 (5只)
    "000977", "603019", "002439", "002916", "603703",
    # 消费电子 (9只)
    "002600", "002475", "601138", "002241", "002456", "002008", "002273", "002044", "002228",
    # 新能源科技 (3只)
    "000063", "603169", "603528",
}


class StockQualityComparator:
    """
    股票质量比较器
    
    比较新增股票与现有股票的质量水平
    
    Requirements: 成功标准验证 - 新增股票质量不低于现有股票平均水平
    """
    
    # 质量评分权重
    QUALITY_WEIGHTS = {
        'financial_health': 0.40,  # 财务健康度权重
        'growth': 0.35,            # 成长性权重
        'liquidity': 0.25,         # 流动性权重
    }
    
    # 质量达标阈值（新增股票平均得分不低于现有股票平均得分的比例）
    QUALITY_THRESHOLD_RATIO = 0.95  # 95%
    
    def __init__(
        self,
        original_codes: Optional[Set[str]] = None,
        quality_threshold_ratio: float = 0.95
    ):
        """
        初始化股票质量比较器
        
        Args:
            original_codes: 原始股票代码集合（扩充前的股票）
            quality_threshold_ratio: 质量达标阈值比例
        """
        self.original_codes = original_codes or ORIGINAL_STOCK_CODES
        self.quality_threshold_ratio = quality_threshold_ratio
    
    def calculate_stock_quality(
        self,
        row: pd.Series,
        is_new: bool = False
    ) -> StockQualityMetrics:
        """
        计算单只股票的质量指标
        
        Args:
            row: 股票数据行
            is_new: 是否为新增股票
        
        Returns:
            StockQualityMetrics: 股票质量指标
        """
        code = str(row.get('code', ''))
        name = str(row.get('name', ''))
        sector = str(row.get('sector', row.get('tech_industry', '未知')))
        
        # 计算财务健康度得分
        financial_health_score = self._calculate_financial_health_score(row)
        
        # 计算成长性得分
        growth_score = self._calculate_growth_score(row)
        
        # 计算流动性得分
        liquidity_score = self._calculate_liquidity_score(row)
        
        # 计算综合质量得分
        overall_quality_score = (
            financial_health_score * self.QUALITY_WEIGHTS['financial_health'] +
            growth_score * self.QUALITY_WEIGHTS['growth'] +
            liquidity_score * self.QUALITY_WEIGHTS['liquidity']
        )
        
        return StockQualityMetrics(
            code=code,
            name=name,
            sector=sector,
            financial_health_score=financial_health_score,
            growth_score=growth_score,
            liquidity_score=liquidity_score,
            overall_quality_score=overall_quality_score,
            is_new_stock=is_new
        )
    
    def _calculate_financial_health_score(self, row: pd.Series) -> float:
        """计算财务健康度得分 (0-100)"""
        scores = []
        weights = []
        
        # ROE评分 (30%)
        roe = self._safe_float(row.get('roe'))
        if roe is not None:
            if roe >= 20:
                roe_score = 100
            elif roe >= 15:
                roe_score = 85
            elif roe >= 10:
                roe_score = 70
            elif roe >= 8:
                roe_score = 55
            elif roe >= 0:
                roe_score = max(0, roe * 5)
            else:
                roe_score = 0
            scores.append(roe_score)
            weights.append(0.30)
        
        # 负债率评分 (25%) - 越低越好
        debt_ratio = self._safe_float(row.get('debt_ratio'))
        if debt_ratio is not None:
            if debt_ratio <= 30:
                debt_score = 100
            elif debt_ratio <= 40:
                debt_score = 85
            elif debt_ratio <= 50:
                debt_score = 70
            elif debt_ratio <= 60:
                debt_score = 55
            elif debt_ratio <= 80:
                debt_score = 30
            else:
                debt_score = 0
            scores.append(debt_score)
            weights.append(0.25)
        
        # 毛利率评分 (25%)
        gross_margin = self._safe_float(row.get('gross_margin'))
        if gross_margin is not None:
            if gross_margin >= 50:
                gm_score = 100
            elif gross_margin >= 40:
                gm_score = 85
            elif gross_margin >= 30:
                gm_score = 70
            elif gross_margin >= 20:
                gm_score = 55
            elif gross_margin >= 0:
                gm_score = max(0, gross_margin * 2)
            else:
                gm_score = 0
            scores.append(gm_score)
            weights.append(0.25)
        
        # 净利率评分 (20%)
        net_margin = self._safe_float(row.get('net_margin'))
        if net_margin is not None:
            if net_margin >= 20:
                nm_score = 100
            elif net_margin >= 15:
                nm_score = 85
            elif net_margin >= 10:
                nm_score = 70
            elif net_margin >= 5:
                nm_score = 55
            elif net_margin >= 0:
                nm_score = max(0, net_margin * 8)
            else:
                nm_score = 0
            scores.append(nm_score)
            weights.append(0.20)
        
        if not scores:
            return 50.0  # 无数据时返回中等分数
        
        # 归一化权重
        total_weight = sum(weights)
        normalized_weights = [w / total_weight for w in weights]
        
        return sum(s * w for s, w in zip(scores, normalized_weights))
    
    def _calculate_growth_score(self, row: pd.Series) -> float:
        """计算成长性得分 (0-100)"""
        scores = []
        weights = []
        
        # 营收增长率评分 (40%)
        revenue_growth = self._safe_float(row.get('revenue_growth_1y', row.get('revenue_growth_3y')))
        if revenue_growth is not None:
            if revenue_growth >= 30:
                rg_score = 100
            elif revenue_growth >= 20:
                rg_score = 85
            elif revenue_growth >= 10:
                rg_score = 70
            elif revenue_growth >= 5:
                rg_score = 55
            elif revenue_growth >= 0:
                rg_score = max(0, revenue_growth * 8)
            else:
                rg_score = max(0, 40 + revenue_growth)  # 负增长扣分
            scores.append(rg_score)
            weights.append(0.40)
        
        # 净利润增长率评分 (40%)
        profit_growth = self._safe_float(row.get('profit_growth_1y', row.get('profit_growth_3y')))
        if profit_growth is not None:
            if profit_growth >= 40:
                pg_score = 100
            elif profit_growth >= 25:
                pg_score = 85
            elif profit_growth >= 15:
                pg_score = 70
            elif profit_growth >= 5:
                pg_score = 55
            elif profit_growth >= 0:
                pg_score = max(0, profit_growth * 6)
            else:
                pg_score = max(0, 40 + profit_growth * 0.5)
            scores.append(pg_score)
            weights.append(0.40)
        
        # 研发投入占比评分 (20%)
        rd_ratio = self._safe_float(row.get('rd_ratio'))
        if rd_ratio is not None:
            if rd_ratio >= 10:
                rd_score = 100
            elif rd_ratio >= 7:
                rd_score = 85
            elif rd_ratio >= 5:
                rd_score = 70
            elif rd_ratio >= 3:
                rd_score = 55
            elif rd_ratio >= 0:
                rd_score = max(0, rd_ratio * 15)
            else:
                rd_score = 0
            scores.append(rd_score)
            weights.append(0.20)
        
        if not scores:
            return 50.0
        
        total_weight = sum(weights)
        normalized_weights = [w / total_weight for w in weights]
        
        return sum(s * w for s, w in zip(scores, normalized_weights))
    
    def _calculate_liquidity_score(self, row: pd.Series) -> float:
        """计算流动性得分 (0-100)"""
        scores = []
        weights = []
        
        # 市值评分 (40%)
        market_cap = self._safe_float(row.get('total_market_cap', row.get('market_cap')))
        if market_cap is not None:
            # 市值单位可能是亿元或元，进行标准化
            if market_cap > 1e10:  # 可能是元
                market_cap = market_cap / 1e8  # 转换为亿元
            
            if market_cap >= 500:
                mc_score = 100
            elif market_cap >= 200:
                mc_score = 85
            elif market_cap >= 100:
                mc_score = 70
            elif market_cap >= 50:
                mc_score = 55
            elif market_cap >= 30:
                mc_score = 40
            else:
                mc_score = max(0, market_cap)
            scores.append(mc_score)
            weights.append(0.40)
        
        # 日均成交额评分 (35%)
        daily_turnover = self._safe_float(row.get('daily_turnover', row.get('turnover')))
        if daily_turnover is not None:
            # 成交额单位可能是亿元或元
            if daily_turnover > 1e8:
                daily_turnover = daily_turnover / 1e8
            
            if daily_turnover >= 10:
                dt_score = 100
            elif daily_turnover >= 5:
                dt_score = 85
            elif daily_turnover >= 2:
                dt_score = 70
            elif daily_turnover >= 0.5:
                dt_score = 55
            elif daily_turnover >= 0.1:
                dt_score = 40
            else:
                dt_score = max(0, daily_turnover * 200)
            scores.append(dt_score)
            weights.append(0.35)
        
        # 换手率评分 (25%)
        turnover_rate = self._safe_float(row.get('turnover_rate'))
        if turnover_rate is not None:
            if turnover_rate >= 3:
                tr_score = 100
            elif turnover_rate >= 2:
                tr_score = 85
            elif turnover_rate >= 1:
                tr_score = 70
            elif turnover_rate >= 0.5:
                tr_score = 55
            elif turnover_rate >= 0.2:
                tr_score = 40
            else:
                tr_score = max(0, turnover_rate * 100)
            scores.append(tr_score)
            weights.append(0.25)
        
        if not scores:
            return 50.0
        
        total_weight = sum(weights)
        normalized_weights = [w / total_weight for w in weights]
        
        return sum(s * w for s, w in zip(scores, normalized_weights))
    
    def _safe_float(self, value: Any) -> Optional[float]:
        """安全转换为浮点数"""
        if value is None or pd.isna(value):
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def compare_quality(
        self,
        df: pd.DataFrame,
        existing_codes: Optional[Set[str]] = None
    ) -> QualityComparisonResult:
        """
        比较新增股票与现有股票的质量
        
        Args:
            df: 包含所有股票数据的DataFrame
            existing_codes: 现有股票代码集合（可选，默认使用原始27只）
        
        Returns:
            QualityComparisonResult: 质量比较结果
        """
        if df is None or df.empty:
            return QualityComparisonResult(
                timestamp=datetime.now(),
                status=QualityComparisonStatus.INSUFFICIENT_DATA,
                warnings=["数据为空"]
            )
        
        existing_codes = existing_codes or self.original_codes
        
        # 分离现有股票和新增股票
        existing_metrics: List[StockQualityMetrics] = []
        new_metrics: List[StockQualityMetrics] = []
        
        for _, row in df.iterrows():
            code = str(row.get('code', ''))
            is_new = code not in existing_codes
            
            metrics = self.calculate_stock_quality(row, is_new=is_new)
            
            if is_new:
                new_metrics.append(metrics)
            else:
                existing_metrics.append(metrics)
        
        # 检查数据充足性
        if len(existing_metrics) == 0:
            return QualityComparisonResult(
                timestamp=datetime.now(),
                status=QualityComparisonStatus.INSUFFICIENT_DATA,
                warnings=["没有找到现有股票数据"]
            )
        
        if len(new_metrics) == 0:
            return QualityComparisonResult(
                timestamp=datetime.now(),
                status=QualityComparisonStatus.INSUFFICIENT_DATA,
                existing_stock_count=len(existing_metrics),
                warnings=["没有找到新增股票数据"]
            )
        
        # 计算现有股票平均质量
        existing_avg_financial = np.mean([m.financial_health_score for m in existing_metrics])
        existing_avg_growth = np.mean([m.growth_score for m in existing_metrics])
        existing_avg_liquidity = np.mean([m.liquidity_score for m in existing_metrics])
        existing_avg_overall = np.mean([m.overall_quality_score for m in existing_metrics])
        
        # 计算新增股票平均质量
        new_avg_financial = np.mean([m.financial_health_score for m in new_metrics])
        new_avg_growth = np.mean([m.growth_score for m in new_metrics])
        new_avg_liquidity = np.mean([m.liquidity_score for m in new_metrics])
        new_avg_overall = np.mean([m.overall_quality_score for m in new_metrics])
        
        # 计算差异
        financial_diff = new_avg_financial - existing_avg_financial
        growth_diff = new_avg_growth - existing_avg_growth
        liquidity_diff = new_avg_liquidity - existing_avg_liquidity
        overall_diff = new_avg_overall - existing_avg_overall
        
        # 验证是否达标（新增股票平均得分 >= 现有股票平均得分 * 阈值比例）
        threshold = self.quality_threshold_ratio
        passed_financial = new_avg_financial >= existing_avg_financial * threshold
        passed_growth = new_avg_growth >= existing_avg_growth * threshold
        passed_liquidity = new_avg_liquidity >= existing_avg_liquidity * threshold
        passed_overall = new_avg_overall >= existing_avg_overall * threshold
        
        # 找出低于平均水平的新增股票
        below_average_stocks = [
            f"{m.code} {m.name} ({m.overall_quality_score:.1f}分)"
            for m in new_metrics
            if m.overall_quality_score < existing_avg_overall * threshold
        ]
        
        # 生成警告和建议
        warnings = []
        recommendations = []
        
        if not passed_financial:
            warnings.append(f"新增股票财务健康度({new_avg_financial:.1f})低于现有股票({existing_avg_financial:.1f})")
            recommendations.append("建议筛选财务指标更优的股票")
        
        if not passed_growth:
            warnings.append(f"新增股票成长性({new_avg_growth:.1f})低于现有股票({existing_avg_growth:.1f})")
            recommendations.append("建议关注成长性更强的科技股")
        
        if not passed_liquidity:
            warnings.append(f"新增股票流动性({new_avg_liquidity:.1f})低于现有股票({existing_avg_liquidity:.1f})")
            recommendations.append("建议选择市值和成交量更大的股票")
        
        if len(below_average_stocks) > 0:
            warnings.append(f"有{len(below_average_stocks)}只新增股票质量低于平均水平")
        
        # 确定最终状态
        status = QualityComparisonStatus.PASSED if passed_overall else QualityComparisonStatus.FAILED
        
        return QualityComparisonResult(
            timestamp=datetime.now(),
            status=status,
            existing_stock_count=len(existing_metrics),
            existing_avg_financial_health=existing_avg_financial,
            existing_avg_growth=existing_avg_growth,
            existing_avg_liquidity=existing_avg_liquidity,
            existing_avg_overall=existing_avg_overall,
            new_stock_count=len(new_metrics),
            new_avg_financial_health=new_avg_financial,
            new_avg_growth=new_avg_growth,
            new_avg_liquidity=new_avg_liquidity,
            new_avg_overall=new_avg_overall,
            financial_health_diff=financial_diff,
            growth_diff=growth_diff,
            liquidity_diff=liquidity_diff,
            overall_diff=overall_diff,
            passed_financial_health=passed_financial,
            passed_growth=passed_growth,
            passed_liquidity=passed_liquidity,
            passed_overall=passed_overall,
            warnings=warnings,
            recommendations=recommendations,
            below_average_stocks=below_average_stocks[:10]  # 只显示前10只
        )
    
    def generate_comparison_report(self, result: QualityComparisonResult) -> str:
        """
        生成质量比较报告
        
        Args:
            result: 质量比较结果
        
        Returns:
            str: 格式化的报告文本
        """
        lines = [
            "=" * 70,
            "股票质量比较报告",
            "=" * 70,
            f"生成时间: {result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            f"比较状态: {result.status.value}",
            "",
            "【现有股票统计】",
            f"  股票数量: {result.existing_stock_count}只",
            f"  平均财务健康度: {result.existing_avg_financial_health:.1f}分",
            f"  平均成长性: {result.existing_avg_growth:.1f}分",
            f"  平均流动性: {result.existing_avg_liquidity:.1f}分",
            f"  平均综合质量: {result.existing_avg_overall:.1f}分",
            "",
            "【新增股票统计】",
            f"  股票数量: {result.new_stock_count}只",
            f"  平均财务健康度: {result.new_avg_financial_health:.1f}分",
            f"  平均成长性: {result.new_avg_growth:.1f}分",
            f"  平均流动性: {result.new_avg_liquidity:.1f}分",
            f"  平均综合质量: {result.new_avg_overall:.1f}分",
            "",
            "【质量差异分析】",
            f"  财务健康度差异: {result.financial_health_diff:+.1f}分 {'✓' if result.passed_financial_health else '✗'}",
            f"  成长性差异: {result.growth_diff:+.1f}分 {'✓' if result.passed_growth else '✗'}",
            f"  流动性差异: {result.liquidity_diff:+.1f}分 {'✓' if result.passed_liquidity else '✗'}",
            f"  综合质量差异: {result.overall_diff:+.1f}分 {'✓' if result.passed_overall else '✗'}",
            "",
        ]
        
        if result.warnings:
            lines.append("【警告】")
            for warning in result.warnings:
                lines.append(f"  ⚠ {warning}")
            lines.append("")
        
        if result.recommendations:
            lines.append("【建议】")
            for rec in result.recommendations:
                lines.append(f"  → {rec}")
            lines.append("")
        
        if result.below_average_stocks:
            lines.append("【低于平均水平的新增股票】")
            for stock in result.below_average_stocks:
                lines.append(f"  - {stock}")
            lines.append("")
        
        # 最终结论
        lines.append("【验证结论】")
        if result.status == QualityComparisonStatus.PASSED:
            lines.append("  ✅ 新增股票质量达标，不低于现有股票平均水平")
        elif result.status == QualityComparisonStatus.FAILED:
            lines.append("  ❌ 新增股票质量未达标，低于现有股票平均水平")
        else:
            lines.append("  ⚠ 数据不足，无法完成质量比较")
        
        lines.append("=" * 70)
        
        return "\n".join(lines)
    
    def validate_new_stock_quality(
        self,
        df: pd.DataFrame,
        min_quality_score: float = 60.0
    ) -> Tuple[bool, str, QualityComparisonResult]:
        """
        验证新增股票质量是否达标
        
        Args:
            df: 包含所有股票数据的DataFrame
            min_quality_score: 最低质量得分要求
        
        Returns:
            Tuple[是否达标, 验证消息, 比较结果]
        """
        result = self.compare_quality(df)
        
        if result.status == QualityComparisonStatus.INSUFFICIENT_DATA:
            return False, "数据不足，无法验证", result
        
        # 检查是否达标
        passed = result.passed_overall
        
        if passed:
            message = (
                f"✅ 新增股票质量验证通过！\n"
                f"   新增股票平均质量: {result.new_avg_overall:.1f}分\n"
                f"   现有股票平均质量: {result.existing_avg_overall:.1f}分\n"
                f"   质量差异: {result.overall_diff:+.1f}分"
            )
        else:
            message = (
                f"❌ 新增股票质量验证未通过！\n"
                f"   新增股票平均质量: {result.new_avg_overall:.1f}分\n"
                f"   现有股票平均质量: {result.existing_avg_overall:.1f}分\n"
                f"   质量差异: {result.overall_diff:+.1f}分\n"
                f"   需要达到: {result.existing_avg_overall * self.quality_threshold_ratio:.1f}分"
            )
        
        return passed, message, result


# 全局实例
_stock_quality_comparator: Optional[StockQualityComparator] = None


def get_stock_quality_comparator() -> StockQualityComparator:
    """获取股票质量比较器实例（单例模式）"""
    global _stock_quality_comparator
    if _stock_quality_comparator is None:
        _stock_quality_comparator = StockQualityComparator()
    return _stock_quality_comparator


def reset_stock_quality_comparator() -> None:
    """重置股票质量比较器实例（主要用于测试）"""
    global _stock_quality_comparator
    _stock_quality_comparator = None
