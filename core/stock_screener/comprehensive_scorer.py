"""
综合评分系统

提供股票的综合评分功能，包括：
- 多维度评分框架
- 定性评估模块
- 综合评分算法
- 评分可解释性机制

Requirements: 3.5, 4.1, 4.3, 4.4
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import logging
import pandas as pd
import numpy as np

from .financial_screener import (
    FinancialScreener, 
    FinancialIndicators, 
    FinancialScreeningResult,
    FinancialHealthLevel
)
from .market_screener import (
    MarketScreener, 
    MarketIndicators, 
    MarketScreeningResult,
    LiquidityLevel
)
from .industry_screener import (
    IndustryScreener, 
    TechIndustry, 
    IndustryMatchResult
)

logger = logging.getLogger(__name__)


class OverallRating(Enum):
    """综合评级"""
    AAA = "AAA"    # 顶级 (90-100)
    AA = "AA"      # 优秀 (80-89)
    A = "A"        # 良好 (70-79)
    BBB = "BBB"    # 中等偏上 (60-69)
    BB = "BB"      # 中等 (50-59)
    B = "B"        # 中等偏下 (40-49)
    C = "C"        # 较差 (<40)


@dataclass
class QualitativeFactors:
    """定性评估因素"""
    code: str
    name: str
    
    # 竞争优势
    competitive_advantage_score: float = 50.0
    competitive_advantage_notes: List[str] = field(default_factory=list)
    
    # 技术护城河
    tech_moat_score: float = 50.0
    tech_moat_notes: List[str] = field(default_factory=list)
    
    # 管理质量
    management_score: float = 50.0
    management_notes: List[str] = field(default_factory=list)
    
    # 行业地位
    industry_position_score: float = 50.0
    industry_position_notes: List[str] = field(default_factory=list)


@dataclass
class ComprehensiveScore:
    """综合评分结果"""
    code: str
    name: str
    
    # 各维度得分
    financial_score: float = 0.0
    market_score: float = 0.0
    industry_score: float = 0.0
    qualitative_score: float = 0.0
    
    # 综合得分
    total_score: float = 0.0
    rating: OverallRating = OverallRating.C
    
    # 详细信息
    tech_industry: Optional[TechIndustry] = None
    financial_health: Optional[FinancialHealthLevel] = None
    liquidity_level: Optional[LiquidityLevel] = None
    
    # 评分解释
    score_breakdown: Dict[str, float] = field(default_factory=dict)
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    # 筛选状态
    passed: bool = False
    rank: int = 0


@dataclass
class ScoringWeightsConfig:
    """评分权重配置"""
    financial_health: float = 0.35      # 财务健康度
    growth_potential: float = 0.25      # 成长潜力
    market_performance: float = 0.20    # 市场表现
    competitive_advantage: float = 0.20 # 竞争优势
    
    def validate(self) -> bool:
        """验证权重总和是否为1"""
        total = (
            self.financial_health + 
            self.growth_potential + 
            self.market_performance + 
            self.competitive_advantage
        )
        return abs(total - 1.0) < 0.001
    
    def to_dict(self) -> Dict[str, float]:
        """转换为字典"""
        return {
            'financial_health': self.financial_health,
            'growth_potential': self.growth_potential,
            'market_performance': self.market_performance,
            'competitive_advantage': self.competitive_advantage
        }


class QualitativeEvaluator:
    """
    定性评估模块
    
    评估企业的竞争优势、技术护城河、管理质量等定性因素
    
    Requirements: 4.1, 4.3, 4.4
    """
    
    def __init__(self):
        """初始化定性评估器"""
        # 竞争优势关键词
        self.competitive_keywords = {
            'high': ['龙头', '领先', '第一', '独家', '垄断', '核心', '专利'],
            'medium': ['优势', '领军', '知名', '品牌', '技术'],
            'low': ['普通', '一般', '竞争']
        }
        
        # 技术护城河关键词
        self.tech_moat_keywords = {
            'high': ['自主研发', '核心技术', '专利', '独创', '突破', '国产替代'],
            'medium': ['研发', '技术', '创新', '升级'],
            'low': ['代工', '组装', '贸易']
        }
    
    def evaluate(
        self, 
        name: str, 
        business_desc: Optional[str] = None,
        industry: Optional[TechIndustry] = None,
        rd_ratio: Optional[float] = None
    ) -> QualitativeFactors:
        """
        评估定性因素
        
        Args:
            name: 股票名称
            business_desc: 主营业务描述
            industry: 所属行业
            rd_ratio: 研发投入占比
        
        Returns:
            QualitativeFactors: 定性评估结果
        """
        text = (name or "") + " " + (business_desc or "")
        
        # 评估竞争优势
        comp_score, comp_notes = self._evaluate_competitive_advantage(text)
        
        # 评估技术护城河
        tech_score, tech_notes = self._evaluate_tech_moat(text, rd_ratio)
        
        # 评估行业地位
        industry_score, industry_notes = self._evaluate_industry_position(text, industry)
        
        # 管理质量（基于可用信息的简化评估）
        mgmt_score, mgmt_notes = self._evaluate_management(text)
        
        return QualitativeFactors(
            code="",
            name=name,
            competitive_advantage_score=comp_score,
            competitive_advantage_notes=comp_notes,
            tech_moat_score=tech_score,
            tech_moat_notes=tech_notes,
            management_score=mgmt_score,
            management_notes=mgmt_notes,
            industry_position_score=industry_score,
            industry_position_notes=industry_notes
        )
    
    def _evaluate_competitive_advantage(self, text: str) -> Tuple[float, List[str]]:
        """评估竞争优势"""
        score = 50.0
        notes = []
        
        # 检查高竞争优势关键词
        high_matches = [kw for kw in self.competitive_keywords['high'] if kw in text]
        if high_matches:
            score = min(100, score + len(high_matches) * 15)
            notes.append(f"具有明显竞争优势: {', '.join(high_matches)}")
        
        # 检查中等竞争优势关键词
        medium_matches = [kw for kw in self.competitive_keywords['medium'] if kw in text]
        if medium_matches:
            score = min(100, score + len(medium_matches) * 8)
        
        return score, notes
    
    def _evaluate_tech_moat(
        self, 
        text: str, 
        rd_ratio: Optional[float]
    ) -> Tuple[float, List[str]]:
        """评估技术护城河"""
        score = 50.0
        notes = []
        
        # 检查技术护城河关键词
        high_matches = [kw for kw in self.tech_moat_keywords['high'] if kw in text]
        if high_matches:
            score = min(100, score + len(high_matches) * 12)
            notes.append(f"技术壁垒: {', '.join(high_matches)}")
        
        # 研发投入加分
        if rd_ratio is not None:
            if rd_ratio >= 10:
                score = min(100, score + 20)
                notes.append(f"高研发投入({rd_ratio:.1f}%)")
            elif rd_ratio >= 5:
                score = min(100, score + 10)
        
        return score, notes
    
    def _evaluate_industry_position(
        self, 
        text: str, 
        industry: Optional[TechIndustry]
    ) -> Tuple[float, List[str]]:
        """评估行业地位"""
        score = 50.0
        notes = []
        
        # 行业龙头关键词
        if any(kw in text for kw in ['龙头', '领先', '第一', '头部']):
            score = min(100, score + 25)
            notes.append("行业龙头地位")
        
        # 科技行业加分
        if industry and industry != TechIndustry.UNKNOWN:
            score = min(100, score + 10)
            notes.append(f"属于{industry.value}行业")
        
        return score, notes
    
    def _evaluate_management(self, text: str) -> Tuple[float, List[str]]:
        """评估管理质量（简化版）"""
        # 由于缺乏详细的管理层信息，使用默认中等评分
        return 50.0, []
    
    def get_overall_qualitative_score(self, factors: QualitativeFactors) -> float:
        """计算定性评估综合得分"""
        weights = {
            'competitive': 0.30,
            'tech_moat': 0.30,
            'industry': 0.25,
            'management': 0.15
        }
        
        return (
            factors.competitive_advantage_score * weights['competitive'] +
            factors.tech_moat_score * weights['tech_moat'] +
            factors.industry_position_score * weights['industry'] +
            factors.management_score * weights['management']
        )


class ComprehensiveScorer:
    """
    综合评分系统
    
    整合财务、市场、行业、定性等多维度评分
    
    Requirements: 3.5, 4.1, 4.3, 4.4
    """
    
    def __init__(
        self, 
        weights: Optional[ScoringWeightsConfig] = None
    ):
        """
        初始化综合评分系统
        
        Args:
            weights: 评分权重配置
        """
        self.weights = weights or ScoringWeightsConfig()
        
        # 初始化各子评分器
        self.financial_screener = FinancialScreener()
        self.market_screener = MarketScreener()
        self.industry_screener = IndustryScreener()
        self.qualitative_evaluator = QualitativeEvaluator()
    
    def score_stock(
        self, 
        row: pd.Series,
        include_qualitative: bool = True
    ) -> ComprehensiveScore:
        """
        对单只股票进行综合评分
        
        Args:
            row: 股票数据行
            include_qualitative: 是否包含定性评估
        
        Returns:
            ComprehensiveScore: 综合评分结果
        """
        code = str(row.get('code', ''))
        name = str(row.get('name', ''))
        
        # 1. 财务评分
        financial_indicators = self._extract_financial_indicators(row)
        financial_result = self.financial_screener.evaluate_stock(financial_indicators)
        financial_score = financial_result.total_score
        
        # 2. 市场表现评分
        market_indicators = self._extract_market_indicators(row)
        market_result = self.market_screener.evaluate_stock(market_indicators)
        market_score = market_result.total_score
        
        # 3. 行业匹配评分
        industry, industry_confidence, _ = self.industry_screener.match_industry(
            name=name,
            business_desc=str(row.get('business_desc', ''))
        )
        industry_score = industry_confidence * 100 if industry != TechIndustry.UNKNOWN else 30
        
        # 4. 定性评估
        if include_qualitative:
            qualitative_factors = self.qualitative_evaluator.evaluate(
                name=name,
                business_desc=str(row.get('business_desc', '')),
                industry=industry,
                rd_ratio=self._safe_float(row.get('rd_ratio'))
            )
            qualitative_score = self.qualitative_evaluator.get_overall_qualitative_score(qualitative_factors)
        else:
            qualitative_score = 50.0
        
        # 5. 计算综合得分
        total_score = (
            financial_score * self.weights.financial_health +
            market_score * self.weights.market_performance +
            industry_score * self.weights.growth_potential +
            qualitative_score * self.weights.competitive_advantage
        )
        
        # 6. 确定评级
        rating = self._determine_rating(total_score)
        
        # 7. 生成评分解释
        score_breakdown = {
            '财务健康度': financial_score,
            '市场表现': market_score,
            '行业匹配度': industry_score,
            '竞争优势': qualitative_score
        }
        
        strengths, weaknesses = self._analyze_strengths_weaknesses(
            financial_score, market_score, industry_score, qualitative_score
        )
        
        recommendations = self._generate_recommendations(
            total_score, financial_result, market_result, industry
        )
        
        return ComprehensiveScore(
            code=code,
            name=name,
            financial_score=financial_score,
            market_score=market_score,
            industry_score=industry_score,
            qualitative_score=qualitative_score,
            total_score=total_score,
            rating=rating,
            tech_industry=industry if industry != TechIndustry.UNKNOWN else None,
            financial_health=financial_result.health_level,
            liquidity_level=market_result.liquidity_level,
            score_breakdown=score_breakdown,
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations,
            passed=total_score >= 60
        )
    
    def _determine_rating(self, score: float) -> OverallRating:
        """确定综合评级"""
        if score >= 90:
            return OverallRating.AAA
        elif score >= 80:
            return OverallRating.AA
        elif score >= 70:
            return OverallRating.A
        elif score >= 60:
            return OverallRating.BBB
        elif score >= 50:
            return OverallRating.BB
        elif score >= 40:
            return OverallRating.B
        else:
            return OverallRating.C
    
    def _analyze_strengths_weaknesses(
        self,
        financial_score: float,
        market_score: float,
        industry_score: float,
        qualitative_score: float
    ) -> Tuple[List[str], List[str]]:
        """分析优势和劣势"""
        strengths = []
        weaknesses = []
        
        # 财务分析
        if financial_score >= 75:
            strengths.append("财务状况优秀")
        elif financial_score < 50:
            weaknesses.append("财务状况需要关注")
        
        # 市场表现分析
        if market_score >= 75:
            strengths.append("市场流动性好")
        elif market_score < 50:
            weaknesses.append("流动性偏弱")
        
        # 行业分析
        if industry_score >= 70:
            strengths.append("科技属性明确")
        elif industry_score < 50:
            weaknesses.append("科技属性不够明显")
        
        # 定性分析
        if qualitative_score >= 70:
            strengths.append("具有竞争优势")
        elif qualitative_score < 50:
            weaknesses.append("竞争优势不明显")
        
        return strengths, weaknesses
    
    def _generate_recommendations(
        self,
        total_score: float,
        financial_result: FinancialScreeningResult,
        market_result: MarketScreeningResult,
        industry: TechIndustry
    ) -> List[str]:
        """生成投资建议"""
        recommendations = []
        
        if total_score >= 80:
            recommendations.append("综合评分优秀，可重点关注")
        elif total_score >= 60:
            recommendations.append("综合评分良好，可纳入观察池")
        else:
            recommendations.append("综合评分偏低，建议谨慎")
        
        # 基于财务状况的建议
        if financial_result.failed_criteria:
            recommendations.append(f"注意: {', '.join(financial_result.failed_criteria[:2])}")
        
        # 基于市场表现的建议
        if market_result.risk_warnings:
            recommendations.append(f"风险提示: {', '.join(market_result.risk_warnings[:2])}")
        
        return recommendations
    
    def _extract_financial_indicators(self, row: pd.Series) -> FinancialIndicators:
        """提取财务指标"""
        return FinancialIndicators(
            code=str(row.get('code', '')),
            name=str(row.get('name', '')),
            roe=self._safe_float(row.get('roe')),
            roa=self._safe_float(row.get('roa')),
            gross_margin=self._safe_float(row.get('gross_margin')),
            net_margin=self._safe_float(row.get('net_margin')),
            revenue_growth_1y=self._safe_float(row.get('revenue_growth_1y')),
            revenue_growth_3y=self._safe_float(row.get('revenue_growth_3y')),
            profit_growth_1y=self._safe_float(row.get('profit_growth_1y')),
            profit_growth_3y=self._safe_float(row.get('profit_growth_3y')),
            rd_ratio=self._safe_float(row.get('rd_ratio')),
            debt_ratio=self._safe_float(row.get('debt_ratio')),
            current_ratio=self._safe_float(row.get('current_ratio')),
            quick_ratio=self._safe_float(row.get('quick_ratio')),
            cash_flow_ratio=self._safe_float(row.get('cash_flow_ratio')),
            pe_ratio=self._safe_float(row.get('pe_ratio')),
            pb_ratio=self._safe_float(row.get('pb_ratio')),
            peg_ratio=self._safe_float(row.get('peg_ratio')),
            ps_ratio=self._safe_float(row.get('ps_ratio')),
        )
    
    def _extract_market_indicators(self, row: pd.Series) -> MarketIndicators:
        """提取市场指标"""
        return MarketIndicators(
            code=str(row.get('code', '')),
            name=str(row.get('name', '')),
            total_market_cap=self._safe_float(row.get('total_market_cap')),
            float_market_cap=self._safe_float(row.get('float_market_cap')),
            daily_turnover=self._safe_float(row.get('daily_turnover', row.get('turnover'))),
            turnover_rate=self._safe_float(row.get('turnover_rate')),
            volume_ratio=self._safe_float(row.get('volume_ratio')),
            volatility_annual=self._safe_float(row.get('volatility_annual')),
            max_drawdown=self._safe_float(row.get('max_drawdown')),
        )
    
    def _safe_float(self, value: Any) -> Optional[float]:
        """安全转换为浮点数"""
        if value is None or pd.isna(value):
            return None
        try:
            result = float(value)
            if result > 1e10:
                result = result / 1e8
            return result
        except (ValueError, TypeError):
            return None
    
    def score_stocks(
        self, 
        df: pd.DataFrame,
        min_score: float = 60.0,
        top_n: Optional[int] = None
    ) -> Tuple[pd.DataFrame, List[ComprehensiveScore]]:
        """
        批量评分股票
        
        Args:
            df: 股票数据DataFrame
            min_score: 最低综合得分
            top_n: 返回前N名
        
        Returns:
            Tuple[筛选后的DataFrame, 评分结果列表]
        """
        if df is None or df.empty:
            return pd.DataFrame(), []
        
        results: List[ComprehensiveScore] = []
        
        for idx, row in df.iterrows():
            score = self.score_stock(row)
            results.append(score)
        
        # 按得分排序
        results.sort(key=lambda x: x.total_score, reverse=True)
        
        # 添加排名
        for i, result in enumerate(results):
            result.rank = i + 1
        
        # 筛选通过的股票
        passed_results = [r for r in results if r.total_score >= min_score]
        
        if top_n:
            passed_results = passed_results[:top_n]
        
        # 构建结果DataFrame
        passed_codes = [r.code for r in passed_results]
        passed_df = df[df['code'].isin(passed_codes)].copy()
        
        # 添加评分列
        if len(passed_df) > 0:
            score_map = {r.code: r.total_score for r in passed_results}
            rating_map = {r.code: r.rating.value for r in passed_results}
            rank_map = {r.code: r.rank for r in passed_results}
            
            passed_df['comprehensive_score'] = passed_df['code'].map(score_map)
            passed_df['rating'] = passed_df['code'].map(rating_map)
            passed_df['rank'] = passed_df['code'].map(rank_map)
            
            # 按得分排序
            passed_df = passed_df.sort_values('comprehensive_score', ascending=False)
        
        logger.info(f"综合评分: 从 {len(df)} 只股票中筛选出 {len(passed_df)} 只")
        
        return passed_df, results
    
    def get_scoring_summary(
        self, 
        results: List[ComprehensiveScore]
    ) -> Dict[str, Any]:
        """获取评分摘要"""
        if not results:
            return {'total': 0}
        
        passed_count = sum(1 for r in results if r.passed)
        scores = [r.total_score for r in results]
        
        # 按评级统计
        rating_counts = {}
        for rating in OverallRating:
            rating_counts[rating.value] = sum(1 for r in results if r.rating == rating)
        
        # 按行业统计
        industry_counts = {}
        for r in results:
            if r.tech_industry:
                industry_name = r.tech_industry.value
                industry_counts[industry_name] = industry_counts.get(industry_name, 0) + 1
        
        return {
            'total': len(results),
            'passed': passed_count,
            'failed': len(results) - passed_count,
            'pass_rate': passed_count / len(results) * 100,
            'avg_score': np.mean(scores),
            'max_score': max(scores),
            'min_score': min(scores),
            'rating_distribution': rating_counts,
            'industry_distribution': industry_counts
        }


# 全局综合评分器实例
_comprehensive_scorer: Optional[ComprehensiveScorer] = None


def get_comprehensive_scorer() -> ComprehensiveScorer:
    """
    获取综合评分器实例（单例模式）
    
    Returns:
        ComprehensiveScorer: 综合评分器实例
    """
    global _comprehensive_scorer
    if _comprehensive_scorer is None:
        _comprehensive_scorer = ComprehensiveScorer()
    return _comprehensive_scorer
