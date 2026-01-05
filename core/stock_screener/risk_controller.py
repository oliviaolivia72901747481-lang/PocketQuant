"""
风险控制机制

提供风险评估和预警功能，包括：
- 单一行业集中度风险评估
- 个股权重分布风险评估
- 整体风险指标监控
- 风险预警通知机制
- 风险处置建议生成

Requirements: 6.1, 6.3, 6.4, 6.5
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from datetime import datetime
import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """风险等级"""
    LOW = "low"           # 低风险
    MEDIUM = "medium"     # 中等风险
    HIGH = "high"         # 高风险
    CRITICAL = "critical" # 严重风险


class RiskType(Enum):
    """风险类型"""
    CONCENTRATION = "concentration"     # 集中度风险
    LIQUIDITY = "liquidity"             # 流动性风险
    VOLATILITY = "volatility"           # 波动性风险
    FINANCIAL = "financial"             # 财务风险
    MARKET = "market"                   # 市场风险


@dataclass
class RiskWarning:
    """风险预警"""
    risk_type: RiskType
    risk_level: RiskLevel
    title: str
    description: str
    affected_stocks: List[str] = field(default_factory=list)
    suggested_actions: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class RiskMetrics:
    """风险指标"""
    # 集中度风险
    industry_hhi: float = 0.0           # 行业赫芬达尔指数
    top3_industry_ratio: float = 0.0    # 前3大行业占比
    single_stock_max_weight: float = 0.0 # 单只股票最大权重
    
    # 流动性风险
    low_liquidity_ratio: float = 0.0    # 低流动性股票占比
    avg_turnover_rate: float = 0.0      # 平均换手率
    
    # 波动性风险
    high_volatility_ratio: float = 0.0  # 高波动股票占比
    avg_volatility: float = 0.0         # 平均波动率
    
    # 财务风险
    high_debt_ratio: float = 0.0        # 高负债股票占比
    negative_profit_ratio: float = 0.0  # 亏损股票占比
    
    # 综合风险得分 (0-100, 越低越好)
    overall_risk_score: float = 0.0


@dataclass
class RiskAssessmentResult:
    """风险评估结果"""
    timestamp: datetime
    total_stocks: int
    metrics: RiskMetrics
    risk_level: RiskLevel
    warnings: List[RiskWarning] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    passed: bool = True


class RiskAssessor:
    """
    风险评估模块
    
    评估股票池的各类风险
    
    Requirements: 6.1, 6.3, 6.5
    """
    
    # 风险阈值配置
    THRESHOLDS = {
        'industry_hhi_high': 0.25,          # HHI高风险阈值
        'industry_hhi_medium': 0.15,        # HHI中等风险阈值
        'top3_industry_high': 0.60,         # 前3行业高风险阈值
        'single_stock_max': 0.05,           # 单只股票最大权重
        'low_liquidity_threshold': 0.10,    # 低流动性阈值(换手率)
        'high_volatility_threshold': 50,    # 高波动阈值(年化波动率%)
        'high_debt_threshold': 70,          # 高负债阈值(%)
    }
    
    def __init__(self, thresholds: Optional[Dict[str, float]] = None):
        """
        初始化风险评估器
        
        Args:
            thresholds: 自定义风险阈值
        """
        self.thresholds = {**self.THRESHOLDS}
        if thresholds:
            self.thresholds.update(thresholds)
    
    def assess(self, df: pd.DataFrame) -> RiskAssessmentResult:
        """
        评估股票池风险
        
        Args:
            df: 股票数据DataFrame
        
        Returns:
            RiskAssessmentResult: 风险评估结果
        """
        if df is None or df.empty:
            return RiskAssessmentResult(
                timestamp=datetime.now(),
                total_stocks=0,
                metrics=RiskMetrics(),
                risk_level=RiskLevel.CRITICAL,
                warnings=[RiskWarning(
                    risk_type=RiskType.MARKET,
                    risk_level=RiskLevel.CRITICAL,
                    title="数据为空",
                    description="股票池数据为空，无法进行风险评估"
                )],
                passed=False
            )
        
        warnings = []
        
        # 1. 评估集中度风险
        concentration_metrics, concentration_warnings = self._assess_concentration_risk(df)
        warnings.extend(concentration_warnings)
        
        # 2. 评估流动性风险
        liquidity_metrics, liquidity_warnings = self._assess_liquidity_risk(df)
        warnings.extend(liquidity_warnings)
        
        # 3. 评估波动性风险
        volatility_metrics, volatility_warnings = self._assess_volatility_risk(df)
        warnings.extend(volatility_warnings)
        
        # 4. 评估财务风险
        financial_metrics, financial_warnings = self._assess_financial_risk(df)
        warnings.extend(financial_warnings)
        
        # 5. 计算综合风险得分
        overall_score = self._calculate_overall_risk_score(
            concentration_metrics, liquidity_metrics, 
            volatility_metrics, financial_metrics
        )
        
        # 构建风险指标
        metrics = RiskMetrics(
            industry_hhi=concentration_metrics.get('hhi', 0),
            top3_industry_ratio=concentration_metrics.get('top3_ratio', 0),
            single_stock_max_weight=concentration_metrics.get('max_weight', 0),
            low_liquidity_ratio=liquidity_metrics.get('low_liquidity_ratio', 0),
            avg_turnover_rate=liquidity_metrics.get('avg_turnover', 0),
            high_volatility_ratio=volatility_metrics.get('high_vol_ratio', 0),
            avg_volatility=volatility_metrics.get('avg_volatility', 0),
            high_debt_ratio=financial_metrics.get('high_debt_ratio', 0),
            negative_profit_ratio=financial_metrics.get('negative_profit_ratio', 0),
            overall_risk_score=overall_score
        )
        
        # 确定整体风险等级
        risk_level = self._determine_risk_level(overall_score, warnings)
        
        # 生成建议
        recommendations = self._generate_recommendations(metrics, warnings)
        
        return RiskAssessmentResult(
            timestamp=datetime.now(),
            total_stocks=len(df),
            metrics=metrics,
            risk_level=risk_level,
            warnings=warnings,
            recommendations=recommendations,
            passed=risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM]
        )
    
    def _assess_concentration_risk(self, df: pd.DataFrame) -> Tuple[Dict[str, float], List[RiskWarning]]:
        """评估集中度风险"""
        metrics = {}
        warnings = []
        
        # 行业集中度
        industry_col = None
        for col in ['tech_industry', 'industry', 'sector']:
            if col in df.columns:
                industry_col = col
                break
        
        if industry_col:
            industry_counts = df[industry_col].value_counts()
            n = len(df)
            
            if n > 0 and len(industry_counts) > 0:
                # HHI指数
                shares = industry_counts / n
                hhi = (shares ** 2).sum()
                metrics['hhi'] = hhi
                
                # 前3大行业占比
                top3_ratio = industry_counts.head(3).sum() / n
                metrics['top3_ratio'] = top3_ratio
                
                # 检查风险
                if hhi > self.thresholds['industry_hhi_high']:
                    warnings.append(RiskWarning(
                        risk_type=RiskType.CONCENTRATION,
                        risk_level=RiskLevel.HIGH,
                        title="行业集中度过高",
                        description=f"HHI指数({hhi:.3f})超过高风险阈值({self.thresholds['industry_hhi_high']})",
                        affected_stocks=industry_counts.head(1).index.tolist(),
                        suggested_actions=["增加其他行业股票", "减少主导行业持仓"]
                    ))
                elif hhi > self.thresholds['industry_hhi_medium']:
                    warnings.append(RiskWarning(
                        risk_type=RiskType.CONCENTRATION,
                        risk_level=RiskLevel.MEDIUM,
                        title="行业集中度偏高",
                        description=f"HHI指数({hhi:.3f})超过中等风险阈值",
                        suggested_actions=["关注行业分散化"]
                    ))
        
        # 单只股票权重（假设等权重）
        if len(df) > 0:
            max_weight = 1 / len(df)
            metrics['max_weight'] = max_weight
        
        return metrics, warnings
    
    def _assess_liquidity_risk(self, df: pd.DataFrame) -> Tuple[Dict[str, float], List[RiskWarning]]:
        """评估流动性风险"""
        metrics = {}
        warnings = []
        
        if 'turnover_rate' in df.columns:
            turnover = df['turnover_rate'].dropna()
            if len(turnover) > 0:
                avg_turnover = turnover.mean()
                metrics['avg_turnover'] = avg_turnover
                
                # 低流动性股票占比
                low_liquidity = (turnover < self.thresholds['low_liquidity_threshold']).sum()
                low_liquidity_ratio = low_liquidity / len(turnover)
                metrics['low_liquidity_ratio'] = low_liquidity_ratio
                
                if low_liquidity_ratio > 0.3:
                    low_liq_stocks = df[df['turnover_rate'] < self.thresholds['low_liquidity_threshold']]
                    warnings.append(RiskWarning(
                        risk_type=RiskType.LIQUIDITY,
                        risk_level=RiskLevel.HIGH,
                        title="流动性风险较高",
                        description=f"低流动性股票占比({low_liquidity_ratio:.1%})过高",
                        affected_stocks=low_liq_stocks['code'].tolist()[:10] if 'code' in low_liq_stocks.columns else [],
                        suggested_actions=["移除低流动性股票", "提高流动性筛选标准"]
                    ))
        
        return metrics, warnings
    
    def _assess_volatility_risk(self, df: pd.DataFrame) -> Tuple[Dict[str, float], List[RiskWarning]]:
        """评估波动性风险"""
        metrics = {}
        warnings = []
        
        vol_col = None
        for col in ['volatility_annual', 'volatility', 'vol']:
            if col in df.columns:
                vol_col = col
                break
        
        if vol_col:
            volatility = df[vol_col].dropna()
            if len(volatility) > 0:
                avg_vol = volatility.mean()
                metrics['avg_volatility'] = avg_vol
                
                # 高波动股票占比
                high_vol = (volatility > self.thresholds['high_volatility_threshold']).sum()
                high_vol_ratio = high_vol / len(volatility)
                metrics['high_vol_ratio'] = high_vol_ratio
                
                if high_vol_ratio > 0.4:
                    warnings.append(RiskWarning(
                        risk_type=RiskType.VOLATILITY,
                        risk_level=RiskLevel.MEDIUM,
                        title="波动性风险偏高",
                        description=f"高波动股票占比({high_vol_ratio:.1%})较高",
                        suggested_actions=["关注高波动股票的仓位控制"]
                    ))
        
        return metrics, warnings
    
    def _assess_financial_risk(self, df: pd.DataFrame) -> Tuple[Dict[str, float], List[RiskWarning]]:
        """评估财务风险"""
        metrics = {}
        warnings = []
        
        # 高负债风险
        if 'debt_ratio' in df.columns:
            debt = df['debt_ratio'].dropna()
            if len(debt) > 0:
                high_debt = (debt > self.thresholds['high_debt_threshold']).sum()
                high_debt_ratio = high_debt / len(debt)
                metrics['high_debt_ratio'] = high_debt_ratio
                
                if high_debt_ratio > 0.3:
                    warnings.append(RiskWarning(
                        risk_type=RiskType.FINANCIAL,
                        risk_level=RiskLevel.MEDIUM,
                        title="财务杠杆风险",
                        description=f"高负债股票占比({high_debt_ratio:.1%})较高",
                        suggested_actions=["关注高负债股票的财务状况"]
                    ))
        
        # 亏损股票风险
        if 'profit_growth_1y' in df.columns or 'net_margin' in df.columns:
            profit_col = 'net_margin' if 'net_margin' in df.columns else 'profit_growth_1y'
            profit = df[profit_col].dropna()
            if len(profit) > 0:
                negative = (profit < 0).sum()
                negative_ratio = negative / len(profit)
                metrics['negative_profit_ratio'] = negative_ratio
                
                if negative_ratio > 0.2:
                    warnings.append(RiskWarning(
                        risk_type=RiskType.FINANCIAL,
                        risk_level=RiskLevel.HIGH,
                        title="盈利能力风险",
                        description=f"亏损/负增长股票占比({negative_ratio:.1%})过高",
                        suggested_actions=["移除持续亏损股票", "提高盈利能力筛选标准"]
                    ))
        
        return metrics, warnings
    
    def _calculate_overall_risk_score(
        self,
        concentration: Dict[str, float],
        liquidity: Dict[str, float],
        volatility: Dict[str, float],
        financial: Dict[str, float]
    ) -> float:
        """计算综合风险得分 (0-100, 越低越好)"""
        score = 0.0
        
        # 集中度风险 (权重30%)
        hhi = concentration.get('hhi', 0)
        if hhi > 0.25:
            score += 30
        elif hhi > 0.15:
            score += 20
        elif hhi > 0.10:
            score += 10
        
        # 流动性风险 (权重25%)
        low_liq = liquidity.get('low_liquidity_ratio', 0)
        score += min(low_liq * 100, 25)
        
        # 波动性风险 (权重20%)
        high_vol = volatility.get('high_vol_ratio', 0)
        score += min(high_vol * 50, 20)
        
        # 财务风险 (权重25%)
        high_debt = financial.get('high_debt_ratio', 0)
        neg_profit = financial.get('negative_profit_ratio', 0)
        score += min((high_debt + neg_profit) * 50, 25)
        
        return min(score, 100)
    
    def _determine_risk_level(self, score: float, warnings: List[RiskWarning]) -> RiskLevel:
        """确定整体风险等级"""
        # 检查是否有严重警告
        critical_warnings = [w for w in warnings if w.risk_level == RiskLevel.CRITICAL]
        high_warnings = [w for w in warnings if w.risk_level == RiskLevel.HIGH]
        
        if critical_warnings or score >= 70:
            return RiskLevel.CRITICAL
        elif len(high_warnings) >= 2 or score >= 50:
            return RiskLevel.HIGH
        elif high_warnings or score >= 30:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _generate_recommendations(
        self, 
        metrics: RiskMetrics, 
        warnings: List[RiskWarning]
    ) -> List[str]:
        """生成风险处置建议"""
        recommendations = []
        
        if metrics.industry_hhi > 0.20:
            recommendations.append("建议增加行业多样性，降低单一行业依赖")
        
        if metrics.low_liquidity_ratio > 0.20:
            recommendations.append("建议提高流动性筛选标准，确保交易便利性")
        
        if metrics.high_debt_ratio > 0.25:
            recommendations.append("建议关注高负债股票的财务健康状况")
        
        if metrics.overall_risk_score < 30:
            recommendations.append("整体风险可控，可维持当前配置")
        elif metrics.overall_risk_score < 50:
            recommendations.append("风险处于中等水平，建议定期监控")
        else:
            recommendations.append("风险较高，建议调整股票池配置")
        
        return recommendations


class RiskAlertManager:
    """
    风险预警管理器
    
    管理风险预警的生成、存储和通知
    
    Requirements: 6.4
    """
    
    def __init__(self, alert_threshold: RiskLevel = RiskLevel.MEDIUM):
        """
        初始化风险预警管理器
        
        Args:
            alert_threshold: 触发预警的最低风险等级
        """
        self.alert_threshold = alert_threshold
        self.alert_history: List[RiskWarning] = []
    
    def process_assessment(self, result: RiskAssessmentResult) -> List[RiskWarning]:
        """
        处理风险评估结果，生成预警
        
        Args:
            result: 风险评估结果
        
        Returns:
            List[RiskWarning]: 需要发送的预警列表
        """
        alerts_to_send = []
        
        threshold_order = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
        threshold_idx = threshold_order.index(self.alert_threshold)
        
        for warning in result.warnings:
            warning_idx = threshold_order.index(warning.risk_level)
            if warning_idx >= threshold_idx:
                alerts_to_send.append(warning)
                self.alert_history.append(warning)
        
        return alerts_to_send
    
    def format_alert_message(self, warning: RiskWarning) -> str:
        """格式化预警消息"""
        lines = [
            f"⚠️ 风险预警: {warning.title}",
            f"风险等级: {warning.risk_level.value.upper()}",
            f"风险类型: {warning.risk_type.value}",
            f"描述: {warning.description}",
        ]
        
        if warning.affected_stocks:
            lines.append(f"涉及股票: {', '.join(warning.affected_stocks[:5])}")
        
        if warning.suggested_actions:
            lines.append("建议措施:")
            for action in warning.suggested_actions:
                lines.append(f"  - {action}")
        
        return "\n".join(lines)
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """获取预警摘要"""
        if not self.alert_history:
            return {'total': 0}
        
        level_counts = {}
        for level in RiskLevel:
            level_counts[level.value] = sum(1 for a in self.alert_history if a.risk_level == level)
        
        type_counts = {}
        for rtype in RiskType:
            type_counts[rtype.value] = sum(1 for a in self.alert_history if a.risk_type == rtype)
        
        return {
            'total': len(self.alert_history),
            'by_level': level_counts,
            'by_type': type_counts,
            'latest': self.alert_history[-1].title if self.alert_history else None
        }


# 全局实例
_risk_assessor: Optional[RiskAssessor] = None
_alert_manager: Optional[RiskAlertManager] = None


def get_risk_assessor() -> RiskAssessor:
    """获取风险评估器实例"""
    global _risk_assessor
    if _risk_assessor is None:
        _risk_assessor = RiskAssessor()
    return _risk_assessor


def get_alert_manager() -> RiskAlertManager:
    """获取预警管理器实例"""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = RiskAlertManager()
    return _alert_manager
