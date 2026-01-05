"""
财务健康度筛选模块

提供股票财务指标的计算和筛选功能，包括：
- ROE、ROA、毛利率等盈利能力指标
- 营收增长率、净利润增长率等成长性指标
- 负债率、流动比率等财务稳健性指标
- PE、PB、PEG等估值合理性指标

Requirements: 3.1, 3.2, 3.4, 3.5
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class FinancialHealthLevel(Enum):
    """财务健康等级"""
    EXCELLENT = "excellent"    # 优秀 (85-100分)
    GOOD = "good"              # 良好 (70-84分)
    ACCEPTABLE = "acceptable"  # 可接受 (55-69分)
    POOR = "poor"              # 较差 (40-54分)
    RISKY = "risky"            # 高风险 (<40分)


@dataclass
class FinancialIndicators:
    """财务指标数据"""
    code: str
    name: str
    
    # 盈利能力指标
    roe: Optional[float] = None           # 净资产收益率 (%)
    roa: Optional[float] = None           # 总资产收益率 (%)
    gross_margin: Optional[float] = None  # 毛利率 (%)
    net_margin: Optional[float] = None    # 净利率 (%)
    
    # 成长性指标
    revenue_growth_1y: Optional[float] = None   # 1年营收增长率 (%)
    revenue_growth_3y: Optional[float] = None   # 3年营收复合增长率 (%)
    profit_growth_1y: Optional[float] = None    # 1年净利润增长率 (%)
    profit_growth_3y: Optional[float] = None    # 3年净利润复合增长率 (%)
    rd_ratio: Optional[float] = None            # 研发投入占比 (%)
    
    # 财务稳健性指标
    debt_ratio: Optional[float] = None          # 资产负债率 (%)
    current_ratio: Optional[float] = None       # 流动比率
    quick_ratio: Optional[float] = None         # 速动比率
    cash_flow_ratio: Optional[float] = None     # 现金流量比率
    
    # 估值指标
    pe_ratio: Optional[float] = None            # 市盈率
    pb_ratio: Optional[float] = None            # 市净率
    peg_ratio: Optional[float] = None           # 市盈增长比
    ps_ratio: Optional[float] = None            # 市销率


@dataclass
class FinancialScreeningResult:
    """财务筛选结果"""
    code: str
    name: str
    indicators: FinancialIndicators
    
    # 各维度得分
    profitability_score: float = 0.0      # 盈利能力得分
    growth_score: float = 0.0             # 成长性得分
    stability_score: float = 0.0          # 财务稳健性得分
    valuation_score: float = 0.0          # 估值合理性得分
    
    # 综合得分
    total_score: float = 0.0
    health_level: FinancialHealthLevel = FinancialHealthLevel.POOR
    
    # 筛选状态
    passed: bool = False
    failed_criteria: List[str] = field(default_factory=list)


@dataclass
class FinancialCriteriaConfig:
    """财务筛选标准配置"""
    # 盈利能力标准
    min_roe: float = 8.0              # 最小ROE (%)
    min_roa: float = 4.0              # 最小ROA (%)
    min_gross_margin: float = 20.0    # 最小毛利率 (%)
    min_net_margin: float = 5.0       # 最小净利率 (%)
    
    # 成长性标准
    min_revenue_growth_1y: float = 5.0    # 最小1年营收增长率 (%)
    min_revenue_growth_3y: float = 10.0   # 最小3年营收复合增长率 (%)
    min_profit_growth_1y: float = 10.0    # 最小1年净利润增长率 (%)
    min_profit_growth_3y: float = 15.0    # 最小3年净利润复合增长率 (%)
    min_rd_ratio: float = 3.0             # 最小研发投入占比 (%)
    
    # 财务稳健性标准
    max_debt_ratio: float = 60.0          # 最大负债率 (%)
    min_current_ratio: float = 1.2        # 最小流动比率
    min_quick_ratio: float = 0.8          # 最小速动比率
    min_cash_flow_ratio: float = 0.1      # 最小现金流量比率
    
    # 估值标准
    max_pe: float = 50.0                  # 最大PE
    max_pb: float = 8.0                   # 最大PB
    max_peg: float = 2.0                  # 最大PEG
    max_ps: float = 10.0                  # 最大PS


class FinancialIndicatorCalculator:
    """
    财务指标计算引擎
    
    计算各类财务指标
    
    Requirements: 3.1, 3.2
    """
    
    def __init__(self):
        """初始化计算引擎"""
        pass
    
    def calculate_roe(
        self, 
        net_profit: float, 
        shareholders_equity: float
    ) -> Optional[float]:
        """
        计算净资产收益率 (ROE)
        
        ROE = 净利润 / 股东权益 * 100
        """
        if shareholders_equity is None or shareholders_equity <= 0:
            return None
        if net_profit is None:
            return None
        return (net_profit / shareholders_equity) * 100
    
    def calculate_roa(
        self, 
        net_profit: float, 
        total_assets: float
    ) -> Optional[float]:
        """
        计算总资产收益率 (ROA)
        
        ROA = 净利润 / 总资产 * 100
        """
        if total_assets is None or total_assets <= 0:
            return None
        if net_profit is None:
            return None
        return (net_profit / total_assets) * 100
    
    def calculate_gross_margin(
        self, 
        revenue: float, 
        cost: float
    ) -> Optional[float]:
        """
        计算毛利率
        
        毛利率 = (营收 - 成本) / 营收 * 100
        """
        if revenue is None or revenue <= 0:
            return None
        if cost is None:
            return None
        return ((revenue - cost) / revenue) * 100
    
    def calculate_net_margin(
        self, 
        net_profit: float, 
        revenue: float
    ) -> Optional[float]:
        """
        计算净利率
        
        净利率 = 净利润 / 营收 * 100
        """
        if revenue is None or revenue <= 0:
            return None
        if net_profit is None:
            return None
        return (net_profit / revenue) * 100
    
    def calculate_growth_rate(
        self, 
        current_value: float, 
        previous_value: float
    ) -> Optional[float]:
        """
        计算增长率
        
        增长率 = (当前值 - 前期值) / |前期值| * 100
        """
        if previous_value is None or previous_value == 0:
            return None
        if current_value is None:
            return None
        return ((current_value - previous_value) / abs(previous_value)) * 100
    
    def calculate_cagr(
        self, 
        start_value: float, 
        end_value: float, 
        years: int
    ) -> Optional[float]:
        """
        计算复合年增长率 (CAGR)
        
        CAGR = (终值/初值)^(1/年数) - 1
        """
        if start_value is None or start_value <= 0:
            return None
        if end_value is None or end_value <= 0:
            return None
        if years <= 0:
            return None
        
        return ((end_value / start_value) ** (1 / years) - 1) * 100
    
    def calculate_debt_ratio(
        self, 
        total_liabilities: float, 
        total_assets: float
    ) -> Optional[float]:
        """
        计算资产负债率
        
        负债率 = 总负债 / 总资产 * 100
        """
        if total_assets is None or total_assets <= 0:
            return None
        if total_liabilities is None:
            return None
        return (total_liabilities / total_assets) * 100
    
    def calculate_current_ratio(
        self, 
        current_assets: float, 
        current_liabilities: float
    ) -> Optional[float]:
        """
        计算流动比率
        
        流动比率 = 流动资产 / 流动负债
        """
        if current_liabilities is None or current_liabilities <= 0:
            return None
        if current_assets is None:
            return None
        return current_assets / current_liabilities
    
    def calculate_quick_ratio(
        self, 
        current_assets: float, 
        inventory: float, 
        current_liabilities: float
    ) -> Optional[float]:
        """
        计算速动比率
        
        速动比率 = (流动资产 - 存货) / 流动负债
        """
        if current_liabilities is None or current_liabilities <= 0:
            return None
        if current_assets is None:
            return None
        inventory = inventory or 0
        return (current_assets - inventory) / current_liabilities
    
    def calculate_peg(
        self, 
        pe_ratio: float, 
        profit_growth: float
    ) -> Optional[float]:
        """
        计算PEG比率
        
        PEG = PE / 盈利增长率
        """
        if profit_growth is None or profit_growth <= 0:
            return None
        if pe_ratio is None or pe_ratio <= 0:
            return None
        return pe_ratio / profit_growth


class FinancialScorer:
    """
    财务评分系统
    
    对各类财务指标进行评分
    
    Requirements: 3.5
    """
    
    def __init__(self, config: Optional[FinancialCriteriaConfig] = None):
        """初始化评分系统"""
        self.config = config or FinancialCriteriaConfig()
    
    def score_profitability(self, indicators: FinancialIndicators) -> float:
        """
        计算盈利能力得分 (0-100)
        
        权重分配:
        - ROE: 30%
        - ROA: 20%
        - 毛利率: 25%
        - 净利率: 25%
        """
        scores = []
        weights = []
        
        # ROE评分
        if indicators.roe is not None:
            if indicators.roe >= 20:
                roe_score = 100
            elif indicators.roe >= 15:
                roe_score = 85
            elif indicators.roe >= 10:
                roe_score = 70
            elif indicators.roe >= self.config.min_roe:
                roe_score = 55
            elif indicators.roe >= 0:
                roe_score = max(0, indicators.roe * 5)
            else:
                roe_score = 0
            scores.append(roe_score)
            weights.append(0.30)
        
        # ROA评分
        if indicators.roa is not None:
            if indicators.roa >= 10:
                roa_score = 100
            elif indicators.roa >= 7:
                roa_score = 85
            elif indicators.roa >= 5:
                roa_score = 70
            elif indicators.roa >= self.config.min_roa:
                roa_score = 55
            elif indicators.roa >= 0:
                roa_score = max(0, indicators.roa * 10)
            else:
                roa_score = 0
            scores.append(roa_score)
            weights.append(0.20)
        
        # 毛利率评分
        if indicators.gross_margin is not None:
            if indicators.gross_margin >= 50:
                gm_score = 100
            elif indicators.gross_margin >= 40:
                gm_score = 85
            elif indicators.gross_margin >= 30:
                gm_score = 70
            elif indicators.gross_margin >= self.config.min_gross_margin:
                gm_score = 55
            elif indicators.gross_margin >= 0:
                gm_score = max(0, indicators.gross_margin * 2)
            else:
                gm_score = 0
            scores.append(gm_score)
            weights.append(0.25)
        
        # 净利率评分
        if indicators.net_margin is not None:
            if indicators.net_margin >= 20:
                nm_score = 100
            elif indicators.net_margin >= 15:
                nm_score = 85
            elif indicators.net_margin >= 10:
                nm_score = 70
            elif indicators.net_margin >= self.config.min_net_margin:
                nm_score = 55
            elif indicators.net_margin >= 0:
                nm_score = max(0, indicators.net_margin * 8)
            else:
                nm_score = 0
            scores.append(nm_score)
            weights.append(0.25)
        
        if not scores:
            return 0.0
        
        # 归一化权重
        total_weight = sum(weights)
        normalized_weights = [w / total_weight for w in weights]
        
        return sum(s * w for s, w in zip(scores, normalized_weights))
    
    def score_growth(self, indicators: FinancialIndicators) -> float:
        """
        计算成长性得分 (0-100)
        
        权重分配:
        - 3年营收增长率: 30%
        - 3年净利润增长率: 35%
        - 研发投入占比: 20%
        - 1年营收增长率: 15%
        """
        scores = []
        weights = []
        
        # 3年营收增长率评分
        if indicators.revenue_growth_3y is not None:
            if indicators.revenue_growth_3y >= 30:
                rg3_score = 100
            elif indicators.revenue_growth_3y >= 20:
                rg3_score = 85
            elif indicators.revenue_growth_3y >= 15:
                rg3_score = 70
            elif indicators.revenue_growth_3y >= self.config.min_revenue_growth_3y:
                rg3_score = 55
            elif indicators.revenue_growth_3y >= 0:
                rg3_score = max(0, indicators.revenue_growth_3y * 4)
            else:
                rg3_score = 0
            scores.append(rg3_score)
            weights.append(0.30)
        
        # 3年净利润增长率评分
        if indicators.profit_growth_3y is not None:
            if indicators.profit_growth_3y >= 40:
                pg3_score = 100
            elif indicators.profit_growth_3y >= 30:
                pg3_score = 85
            elif indicators.profit_growth_3y >= 20:
                pg3_score = 70
            elif indicators.profit_growth_3y >= self.config.min_profit_growth_3y:
                pg3_score = 55
            elif indicators.profit_growth_3y >= 0:
                pg3_score = max(0, indicators.profit_growth_3y * 2.5)
            else:
                pg3_score = 0
            scores.append(pg3_score)
            weights.append(0.35)
        
        # 研发投入占比评分
        if indicators.rd_ratio is not None:
            if indicators.rd_ratio >= 10:
                rd_score = 100
            elif indicators.rd_ratio >= 7:
                rd_score = 85
            elif indicators.rd_ratio >= 5:
                rd_score = 70
            elif indicators.rd_ratio >= self.config.min_rd_ratio:
                rd_score = 55
            elif indicators.rd_ratio >= 0:
                rd_score = max(0, indicators.rd_ratio * 15)
            else:
                rd_score = 0
            scores.append(rd_score)
            weights.append(0.20)
        
        # 1年营收增长率评分
        if indicators.revenue_growth_1y is not None:
            if indicators.revenue_growth_1y >= 25:
                rg1_score = 100
            elif indicators.revenue_growth_1y >= 15:
                rg1_score = 85
            elif indicators.revenue_growth_1y >= 10:
                rg1_score = 70
            elif indicators.revenue_growth_1y >= self.config.min_revenue_growth_1y:
                rg1_score = 55
            elif indicators.revenue_growth_1y >= 0:
                rg1_score = max(0, indicators.revenue_growth_1y * 8)
            else:
                rg1_score = 0
            scores.append(rg1_score)
            weights.append(0.15)
        
        if not scores:
            return 0.0
        
        total_weight = sum(weights)
        normalized_weights = [w / total_weight for w in weights]
        
        return sum(s * w for s, w in zip(scores, normalized_weights))
    
    def score_stability(self, indicators: FinancialIndicators) -> float:
        """
        计算财务稳健性得分 (0-100)
        
        权重分配:
        - 负债率: 35%
        - 流动比率: 25%
        - 速动比率: 20%
        - 现金流量比率: 20%
        """
        scores = []
        weights = []
        
        # 负债率评分 (越低越好)
        if indicators.debt_ratio is not None:
            if indicators.debt_ratio <= 30:
                dr_score = 100
            elif indicators.debt_ratio <= 40:
                dr_score = 85
            elif indicators.debt_ratio <= 50:
                dr_score = 70
            elif indicators.debt_ratio <= self.config.max_debt_ratio:
                dr_score = 55
            elif indicators.debt_ratio <= 80:
                dr_score = 30
            else:
                dr_score = 0
            scores.append(dr_score)
            weights.append(0.35)
        
        # 流动比率评分
        if indicators.current_ratio is not None:
            if indicators.current_ratio >= 2.5:
                cr_score = 100
            elif indicators.current_ratio >= 2.0:
                cr_score = 85
            elif indicators.current_ratio >= 1.5:
                cr_score = 70
            elif indicators.current_ratio >= self.config.min_current_ratio:
                cr_score = 55
            elif indicators.current_ratio >= 1.0:
                cr_score = 40
            else:
                cr_score = max(0, indicators.current_ratio * 30)
            scores.append(cr_score)
            weights.append(0.25)
        
        # 速动比率评分
        if indicators.quick_ratio is not None:
            if indicators.quick_ratio >= 2.0:
                qr_score = 100
            elif indicators.quick_ratio >= 1.5:
                qr_score = 85
            elif indicators.quick_ratio >= 1.0:
                qr_score = 70
            elif indicators.quick_ratio >= self.config.min_quick_ratio:
                qr_score = 55
            elif indicators.quick_ratio >= 0.5:
                qr_score = 40
            else:
                qr_score = max(0, indicators.quick_ratio * 50)
            scores.append(qr_score)
            weights.append(0.20)
        
        # 现金流量比率评分
        if indicators.cash_flow_ratio is not None:
            if indicators.cash_flow_ratio >= 0.5:
                cf_score = 100
            elif indicators.cash_flow_ratio >= 0.3:
                cf_score = 85
            elif indicators.cash_flow_ratio >= 0.2:
                cf_score = 70
            elif indicators.cash_flow_ratio >= self.config.min_cash_flow_ratio:
                cf_score = 55
            elif indicators.cash_flow_ratio >= 0:
                cf_score = max(0, indicators.cash_flow_ratio * 400)
            else:
                cf_score = 0
            scores.append(cf_score)
            weights.append(0.20)
        
        if not scores:
            return 0.0
        
        total_weight = sum(weights)
        normalized_weights = [w / total_weight for w in weights]
        
        return sum(s * w for s, w in zip(scores, normalized_weights))
    
    def score_valuation(self, indicators: FinancialIndicators) -> float:
        """
        计算估值合理性得分 (0-100)
        
        权重分配:
        - PE: 35%
        - PB: 25%
        - PEG: 25%
        - PS: 15%
        """
        scores = []
        weights = []
        
        # PE评分 (越低越好，但不能为负)
        if indicators.pe_ratio is not None and indicators.pe_ratio > 0:
            if indicators.pe_ratio <= 15:
                pe_score = 100
            elif indicators.pe_ratio <= 25:
                pe_score = 85
            elif indicators.pe_ratio <= 35:
                pe_score = 70
            elif indicators.pe_ratio <= self.config.max_pe:
                pe_score = 55
            elif indicators.pe_ratio <= 80:
                pe_score = 30
            else:
                pe_score = 10
            scores.append(pe_score)
            weights.append(0.35)
        
        # PB评分 (越低越好)
        if indicators.pb_ratio is not None and indicators.pb_ratio > 0:
            if indicators.pb_ratio <= 2:
                pb_score = 100
            elif indicators.pb_ratio <= 4:
                pb_score = 85
            elif indicators.pb_ratio <= 6:
                pb_score = 70
            elif indicators.pb_ratio <= self.config.max_pb:
                pb_score = 55
            elif indicators.pb_ratio <= 15:
                pb_score = 30
            else:
                pb_score = 10
            scores.append(pb_score)
            weights.append(0.25)
        
        # PEG评分 (越低越好)
        if indicators.peg_ratio is not None and indicators.peg_ratio > 0:
            if indicators.peg_ratio <= 0.5:
                peg_score = 100
            elif indicators.peg_ratio <= 1.0:
                peg_score = 85
            elif indicators.peg_ratio <= 1.5:
                peg_score = 70
            elif indicators.peg_ratio <= self.config.max_peg:
                peg_score = 55
            elif indicators.peg_ratio <= 3.0:
                peg_score = 30
            else:
                peg_score = 10
            scores.append(peg_score)
            weights.append(0.25)
        
        # PS评分 (越低越好)
        if indicators.ps_ratio is not None and indicators.ps_ratio > 0:
            if indicators.ps_ratio <= 2:
                ps_score = 100
            elif indicators.ps_ratio <= 5:
                ps_score = 85
            elif indicators.ps_ratio <= 8:
                ps_score = 70
            elif indicators.ps_ratio <= self.config.max_ps:
                ps_score = 55
            elif indicators.ps_ratio <= 20:
                ps_score = 30
            else:
                ps_score = 10
            scores.append(ps_score)
            weights.append(0.15)
        
        if not scores:
            return 50.0  # 无估值数据时给中等分数
        
        total_weight = sum(weights)
        normalized_weights = [w / total_weight for w in weights]
        
        return sum(s * w for s, w in zip(scores, normalized_weights))


class FinancialScreener:
    """
    财务健康度筛选器
    
    综合评估股票的财务健康状况
    
    Requirements: 3.1, 3.2, 3.4, 3.5
    """
    
    def __init__(
        self, 
        config: Optional[FinancialCriteriaConfig] = None,
        weights: Optional[Dict[str, float]] = None
    ):
        """
        初始化财务筛选器
        
        Args:
            config: 财务筛选标准配置
            weights: 各维度权重配置
        """
        self.config = config or FinancialCriteriaConfig()
        self.calculator = FinancialIndicatorCalculator()
        self.scorer = FinancialScorer(self.config)
        
        # 默认权重
        self.weights = weights or {
            'profitability': 0.30,   # 盈利能力
            'growth': 0.30,          # 成长性
            'stability': 0.25,       # 财务稳健性
            'valuation': 0.15        # 估值合理性
        }
    
    def evaluate_stock(
        self, 
        indicators: FinancialIndicators
    ) -> FinancialScreeningResult:
        """
        评估单只股票的财务健康状况
        
        Args:
            indicators: 财务指标数据
        
        Returns:
            FinancialScreeningResult: 筛选结果
        """
        # 计算各维度得分
        profitability_score = self.scorer.score_profitability(indicators)
        growth_score = self.scorer.score_growth(indicators)
        stability_score = self.scorer.score_stability(indicators)
        valuation_score = self.scorer.score_valuation(indicators)
        
        # 计算综合得分
        total_score = (
            profitability_score * self.weights['profitability'] +
            growth_score * self.weights['growth'] +
            stability_score * self.weights['stability'] +
            valuation_score * self.weights['valuation']
        )
        
        # 确定健康等级
        health_level = self._determine_health_level(total_score)
        
        # 检查是否通过筛选
        passed, failed_criteria = self._check_criteria(indicators)
        
        return FinancialScreeningResult(
            code=indicators.code,
            name=indicators.name,
            indicators=indicators,
            profitability_score=profitability_score,
            growth_score=growth_score,
            stability_score=stability_score,
            valuation_score=valuation_score,
            total_score=total_score,
            health_level=health_level,
            passed=passed,
            failed_criteria=failed_criteria
        )
    
    def _determine_health_level(self, score: float) -> FinancialHealthLevel:
        """确定财务健康等级"""
        if score >= 85:
            return FinancialHealthLevel.EXCELLENT
        elif score >= 70:
            return FinancialHealthLevel.GOOD
        elif score >= 55:
            return FinancialHealthLevel.ACCEPTABLE
        elif score >= 40:
            return FinancialHealthLevel.POOR
        else:
            return FinancialHealthLevel.RISKY
    
    def _check_criteria(
        self, 
        indicators: FinancialIndicators
    ) -> Tuple[bool, List[str]]:
        """检查是否满足筛选标准"""
        failed_criteria = []
        
        # 检查盈利能力
        if indicators.roe is not None and indicators.roe < self.config.min_roe:
            failed_criteria.append(f"ROE({indicators.roe:.1f}%) < {self.config.min_roe}%")
        
        if indicators.gross_margin is not None and indicators.gross_margin < self.config.min_gross_margin:
            failed_criteria.append(f"毛利率({indicators.gross_margin:.1f}%) < {self.config.min_gross_margin}%")
        
        # 检查成长性
        if indicators.revenue_growth_3y is not None and indicators.revenue_growth_3y < self.config.min_revenue_growth_3y:
            failed_criteria.append(f"3年营收增长率({indicators.revenue_growth_3y:.1f}%) < {self.config.min_revenue_growth_3y}%")
        
        # 检查财务稳健性
        if indicators.debt_ratio is not None and indicators.debt_ratio > self.config.max_debt_ratio:
            failed_criteria.append(f"负债率({indicators.debt_ratio:.1f}%) > {self.config.max_debt_ratio}%")
        
        # 检查估值
        if indicators.pe_ratio is not None and indicators.pe_ratio > self.config.max_pe:
            failed_criteria.append(f"PE({indicators.pe_ratio:.1f}) > {self.config.max_pe}")
        
        if indicators.pb_ratio is not None and indicators.pb_ratio > self.config.max_pb:
            failed_criteria.append(f"PB({indicators.pb_ratio:.1f}) > {self.config.max_pb}")
        
        passed = len(failed_criteria) == 0
        return passed, failed_criteria
    
    def screen_stocks(
        self, 
        df: pd.DataFrame,
        min_score: float = 55.0,
        strict_mode: bool = False
    ) -> Tuple[pd.DataFrame, List[FinancialScreeningResult]]:
        """
        批量筛选股票
        
        Args:
            df: 股票数据DataFrame
            min_score: 最低综合得分
            strict_mode: 严格模式（必须通过所有标准）
        
        Returns:
            Tuple[筛选后的DataFrame, 筛选结果列表]
        """
        if df is None or df.empty:
            return pd.DataFrame(), []
        
        results: List[FinancialScreeningResult] = []
        passed_indices = []
        
        for idx, row in df.iterrows():
            # 构建财务指标
            indicators = self._extract_indicators(row)
            
            # 评估股票
            result = self.evaluate_stock(indicators)
            results.append(result)
            
            # 判断是否通过筛选
            if result.total_score >= min_score:
                if strict_mode and not result.passed:
                    continue
                passed_indices.append(idx)
        
        # 筛选通过的股票
        passed_df = df.loc[passed_indices].copy()
        
        # 添加评分列
        if len(passed_df) > 0:
            score_map = {r.code: r.total_score for r in results if r.code in passed_df['code'].values}
            level_map = {r.code: r.health_level.value for r in results if r.code in passed_df['code'].values}
            
            passed_df['financial_score'] = passed_df['code'].map(score_map)
            passed_df['financial_health'] = passed_df['code'].map(level_map)
        
        logger.info(f"财务筛选: 从 {len(df)} 只股票中筛选出 {len(passed_df)} 只")
        
        return passed_df, results
    
    def _extract_indicators(self, row: pd.Series) -> FinancialIndicators:
        """从DataFrame行提取财务指标"""
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
    
    def _safe_float(self, value: Any) -> Optional[float]:
        """安全转换为浮点数"""
        if value is None or pd.isna(value):
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def get_screening_summary(
        self, 
        results: List[FinancialScreeningResult]
    ) -> Dict[str, Any]:
        """
        获取筛选结果摘要
        
        Args:
            results: 筛选结果列表
        
        Returns:
            摘要字典
        """
        if not results:
            return {'total': 0}
        
        passed_count = sum(1 for r in results if r.passed)
        scores = [r.total_score for r in results]
        
        # 按健康等级统计
        level_counts = {}
        for level in FinancialHealthLevel:
            level_counts[level.value] = sum(1 for r in results if r.health_level == level)
        
        return {
            'total': len(results),
            'passed': passed_count,
            'failed': len(results) - passed_count,
            'pass_rate': passed_count / len(results) * 100,
            'avg_score': np.mean(scores),
            'max_score': max(scores),
            'min_score': min(scores),
            'level_distribution': level_counts
        }


# 全局财务筛选器实例
_financial_screener: Optional[FinancialScreener] = None


def get_financial_screener() -> FinancialScreener:
    """
    获取财务筛选器实例（单例模式）
    
    Returns:
        FinancialScreener: 财务筛选器实例
    """
    global _financial_screener
    if _financial_screener is None:
        _financial_screener = FinancialScreener()
    return _financial_screener
