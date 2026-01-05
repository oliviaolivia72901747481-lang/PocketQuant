"""
质量验证系统

提供数据质量监控和筛选结果验证功能，包括：
- 数据完整性实时监控
- 数据异常自动检测
- 数据质量报告生成
- 历史回测验证机制
- 风险指标监控

Requirements: 6.1, 6.4, 7.2, 7.5
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from datetime import datetime
import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class DataQualityStatus(Enum):
    """数据质量状态"""
    EXCELLENT = "excellent"    # 优秀 (95%+)
    GOOD = "good"              # 良好 (85-95%)
    ACCEPTABLE = "acceptable"  # 可接受 (70-85%)
    POOR = "poor"              # 较差 (50-70%)
    CRITICAL = "critical"      # 严重问题 (<50%)


class AnomalyType(Enum):
    """异常类型"""
    MISSING_DATA = "missing_data"
    OUTLIER = "outlier"
    INCONSISTENT = "inconsistent"
    STALE_DATA = "stale_data"
    INVALID_VALUE = "invalid_value"


@dataclass
class DataAnomalyReport:
    """数据异常报告"""
    anomaly_type: AnomalyType
    field_name: str
    affected_count: int
    affected_codes: List[str]
    severity: str  # low, medium, high, critical
    description: str
    suggested_action: str


@dataclass
class DataQualityMetrics:
    """数据质量指标"""
    completeness: float = 0.0      # 完整性 (0-100)
    accuracy: float = 0.0          # 准确性 (0-100)
    consistency: float = 0.0       # 一致性 (0-100)
    timeliness: float = 0.0        # 时效性 (0-100)
    validity: float = 0.0          # 有效性 (0-100)
    
    @property
    def overall_score(self) -> float:
        """计算综合质量得分"""
        weights = {
            'completeness': 0.30,
            'accuracy': 0.25,
            'consistency': 0.20,
            'timeliness': 0.15,
            'validity': 0.10
        }
        return (
            self.completeness * weights['completeness'] +
            self.accuracy * weights['accuracy'] +
            self.consistency * weights['consistency'] +
            self.timeliness * weights['timeliness'] +
            self.validity * weights['validity']
        )
    
    @property
    def status(self) -> DataQualityStatus:
        """获取质量状态"""
        score = self.overall_score
        if score >= 95:
            return DataQualityStatus.EXCELLENT
        elif score >= 85:
            return DataQualityStatus.GOOD
        elif score >= 70:
            return DataQualityStatus.ACCEPTABLE
        elif score >= 50:
            return DataQualityStatus.POOR
        else:
            return DataQualityStatus.CRITICAL


@dataclass
class QualityValidationResult:
    """质量验证结果"""
    timestamp: datetime
    total_records: int
    valid_records: int
    metrics: DataQualityMetrics
    anomalies: List[DataAnomalyReport] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    passed: bool = True
    
    @property
    def validation_rate(self) -> float:
        """验证通过率"""
        if self.total_records == 0:
            return 0.0
        return self.valid_records / self.total_records * 100


class DataQualityMonitor:
    """
    数据质量监控器
    
    实现数据完整性实时监控、异常自动检测、质量报告生成
    
    Requirements: 7.2, 7.5
    """
    
    # 必需字段及其类型
    REQUIRED_FIELDS = {
        'code': str,
        'name': str,
    }
    
    # 财务字段
    FINANCIAL_FIELDS = [
        'roe', 'roa', 'gross_margin', 'net_margin',
        'revenue_growth_1y', 'profit_growth_1y',
        'debt_ratio', 'current_ratio', 'pe_ratio', 'pb_ratio'
    ]
    
    # 市场字段
    MARKET_FIELDS = [
        'total_market_cap', 'float_market_cap',
        'daily_turnover', 'turnover_rate', 'close'
    ]
    
    # 异常值阈值
    OUTLIER_THRESHOLDS = {
        'roe': (-100, 200),
        'roa': (-50, 100),
        'gross_margin': (-50, 100),
        'net_margin': (-100, 100),
        'debt_ratio': (0, 200),
        'pe_ratio': (-1000, 10000),
        'pb_ratio': (0, 100),
    }
    
    def __init__(self, min_quality_score: float = 70.0):
        """
        初始化数据质量监控器
        
        Args:
            min_quality_score: 最低质量得分阈值
        """
        self.min_quality_score = min_quality_score
    
    def validate(self, df: pd.DataFrame) -> QualityValidationResult:
        """
        验证数据质量
        
        Args:
            df: 待验证的数据
        
        Returns:
            QualityValidationResult: 验证结果
        """
        if df is None or df.empty:
            return QualityValidationResult(
                timestamp=datetime.now(),
                total_records=0,
                valid_records=0,
                metrics=DataQualityMetrics(),
                passed=False,
                warnings=["数据为空"]
            )
        
        anomalies = []
        warnings = []
        
        # 1. 检查完整性
        completeness, missing_anomalies = self._check_completeness(df)
        anomalies.extend(missing_anomalies)
        
        # 2. 检查准确性（异常值检测）
        accuracy, outlier_anomalies = self._check_accuracy(df)
        anomalies.extend(outlier_anomalies)
        
        # 3. 检查一致性
        consistency, inconsistent_anomalies = self._check_consistency(df)
        anomalies.extend(inconsistent_anomalies)
        
        # 4. 检查时效性
        timeliness = self._check_timeliness(df)
        
        # 5. 检查有效性
        validity, invalid_anomalies = self._check_validity(df)
        anomalies.extend(invalid_anomalies)
        
        # 构建质量指标
        metrics = DataQualityMetrics(
            completeness=completeness,
            accuracy=accuracy,
            consistency=consistency,
            timeliness=timeliness,
            validity=validity
        )
        
        # 生成警告
        if metrics.overall_score < self.min_quality_score:
            warnings.append(f"数据质量得分({metrics.overall_score:.1f})低于阈值({self.min_quality_score})")
        
        if len(anomalies) > 0:
            critical_count = sum(1 for a in anomalies if a.severity == 'critical')
            if critical_count > 0:
                warnings.append(f"发现{critical_count}个严重异常")
        
        # 计算有效记录数
        valid_records = self._count_valid_records(df)
        
        return QualityValidationResult(
            timestamp=datetime.now(),
            total_records=len(df),
            valid_records=valid_records,
            metrics=metrics,
            anomalies=anomalies,
            warnings=warnings,
            passed=metrics.overall_score >= self.min_quality_score
        )
    
    def _check_completeness(self, df: pd.DataFrame) -> Tuple[float, List[DataAnomalyReport]]:
        """检查数据完整性"""
        anomalies = []
        all_fields = list(self.REQUIRED_FIELDS.keys()) + self.FINANCIAL_FIELDS + self.MARKET_FIELDS
        
        total_cells = 0
        missing_cells = 0
        
        for field in all_fields:
            if field in df.columns:
                total_cells += len(df)
                field_missing = df[field].isna().sum()
                missing_cells += field_missing
                
                if field_missing > 0:
                    missing_rate = field_missing / len(df) * 100
                    severity = 'critical' if missing_rate > 50 else 'high' if missing_rate > 30 else 'medium' if missing_rate > 10 else 'low'
                    
                    if missing_rate > 10:  # 只报告缺失率>10%的字段
                        anomalies.append(DataAnomalyReport(
                            anomaly_type=AnomalyType.MISSING_DATA,
                            field_name=field,
                            affected_count=field_missing,
                            affected_codes=df[df[field].isna()]['code'].tolist()[:10],
                            severity=severity,
                            description=f"字段'{field}'缺失率{missing_rate:.1f}%",
                            suggested_action=f"补充{field}数据或使用默认值"
                        ))
        
        completeness = (1 - missing_cells / max(total_cells, 1)) * 100
        return completeness, anomalies
    
    def _check_accuracy(self, df: pd.DataFrame) -> Tuple[float, List[DataAnomalyReport]]:
        """检查数据准确性（异常值检测）"""
        anomalies = []
        total_checks = 0
        outlier_count = 0
        
        for field, (min_val, max_val) in self.OUTLIER_THRESHOLDS.items():
            if field in df.columns:
                total_checks += len(df)
                outliers = df[(df[field] < min_val) | (df[field] > max_val)]
                outlier_count += len(outliers)
                
                if len(outliers) > 0:
                    severity = 'high' if len(outliers) > len(df) * 0.1 else 'medium'
                    anomalies.append(DataAnomalyReport(
                        anomaly_type=AnomalyType.OUTLIER,
                        field_name=field,
                        affected_count=len(outliers),
                        affected_codes=outliers['code'].tolist()[:10] if 'code' in outliers.columns else [],
                        severity=severity,
                        description=f"字段'{field}'存在{len(outliers)}个异常值(范围:{min_val}~{max_val})",
                        suggested_action=f"检查{field}数据来源或调整阈值"
                    ))
        
        accuracy = (1 - outlier_count / max(total_checks, 1)) * 100
        return accuracy, anomalies
    
    def _check_consistency(self, df: pd.DataFrame) -> Tuple[float, List[DataAnomalyReport]]:
        """检查数据一致性"""
        anomalies = []
        inconsistent_count = 0
        
        # 检查代码格式一致性
        if 'code' in df.columns:
            invalid_codes = df[~df['code'].astype(str).str.match(r'^\d{6}$', na=False)]
            if len(invalid_codes) > 0:
                inconsistent_count += len(invalid_codes)
                anomalies.append(DataAnomalyReport(
                    anomaly_type=AnomalyType.INCONSISTENT,
                    field_name='code',
                    affected_count=len(invalid_codes),
                    affected_codes=invalid_codes['code'].tolist()[:10],
                    severity='high',
                    description=f"股票代码格式不一致: {len(invalid_codes)}条",
                    suggested_action="标准化股票代码格式为6位数字"
                ))
        
        # 检查逻辑一致性：流通市值不应大于总市值
        if 'total_market_cap' in df.columns and 'float_market_cap' in df.columns:
            invalid = df[df['float_market_cap'] > df['total_market_cap'] * 1.01]  # 允许1%误差
            if len(invalid) > 0:
                inconsistent_count += len(invalid)
                anomalies.append(DataAnomalyReport(
                    anomaly_type=AnomalyType.INCONSISTENT,
                    field_name='market_cap',
                    affected_count=len(invalid),
                    affected_codes=invalid['code'].tolist()[:10] if 'code' in invalid.columns else [],
                    severity='medium',
                    description=f"流通市值大于总市值: {len(invalid)}条",
                    suggested_action="检查市值数据来源"
                ))
        
        consistency = (1 - inconsistent_count / max(len(df), 1)) * 100
        return max(consistency, 0), anomalies
    
    def _check_timeliness(self, df: pd.DataFrame) -> float:
        """检查数据时效性"""
        # 简化实现：假设数据是最新的
        # 实际应用中应检查数据更新时间
        return 90.0
    
    def _check_validity(self, df: pd.DataFrame) -> Tuple[float, List[DataAnomalyReport]]:
        """检查数据有效性"""
        anomalies = []
        invalid_count = 0
        
        # 检查必需字段
        for field, expected_type in self.REQUIRED_FIELDS.items():
            if field not in df.columns:
                invalid_count += len(df)
                anomalies.append(DataAnomalyReport(
                    anomaly_type=AnomalyType.INVALID_VALUE,
                    field_name=field,
                    affected_count=len(df),
                    affected_codes=[],
                    severity='critical',
                    description=f"缺少必需字段'{field}'",
                    suggested_action=f"添加{field}字段"
                ))
        
        # 检查数值字段的有效性
        numeric_fields = self.FINANCIAL_FIELDS + self.MARKET_FIELDS
        for field in numeric_fields:
            if field in df.columns:
                # 检查是否为数值类型
                non_numeric = df[pd.to_numeric(df[field], errors='coerce').isna() & df[field].notna()]
                if len(non_numeric) > 0:
                    invalid_count += len(non_numeric)
                    anomalies.append(DataAnomalyReport(
                        anomaly_type=AnomalyType.INVALID_VALUE,
                        field_name=field,
                        affected_count=len(non_numeric),
                        affected_codes=non_numeric['code'].tolist()[:10] if 'code' in non_numeric.columns else [],
                        severity='medium',
                        description=f"字段'{field}'包含非数值数据",
                        suggested_action=f"转换{field}为数值类型"
                    ))
        
        validity = (1 - invalid_count / max(len(df) * len(self.REQUIRED_FIELDS), 1)) * 100
        return max(validity, 0), anomalies
    
    def _count_valid_records(self, df: pd.DataFrame) -> int:
        """计算有效记录数"""
        if df.empty:
            return 0
        
        # 必需字段都存在且非空的记录
        valid_mask = pd.Series([True] * len(df))
        for field in self.REQUIRED_FIELDS.keys():
            if field in df.columns:
                valid_mask &= df[field].notna()
        
        return valid_mask.sum()
    
    def generate_quality_report(self, result: QualityValidationResult) -> str:
        """生成质量报告"""
        lines = [
            "=" * 60,
            "数据质量验证报告",
            "=" * 60,
            f"验证时间: {result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            f"总记录数: {result.total_records}",
            f"有效记录: {result.valid_records}",
            f"验证通过率: {result.validation_rate:.1f}%",
            "",
            "质量指标:",
            f"  - 完整性: {result.metrics.completeness:.1f}%",
            f"  - 准确性: {result.metrics.accuracy:.1f}%",
            f"  - 一致性: {result.metrics.consistency:.1f}%",
            f"  - 时效性: {result.metrics.timeliness:.1f}%",
            f"  - 有效性: {result.metrics.validity:.1f}%",
            f"  - 综合得分: {result.metrics.overall_score:.1f}%",
            f"  - 质量状态: {result.metrics.status.value}",
            "",
        ]
        
        if result.anomalies:
            lines.append(f"发现异常: {len(result.anomalies)}个")
            for anomaly in result.anomalies[:5]:  # 只显示前5个
                lines.append(f"  [{anomaly.severity}] {anomaly.description}")
        
        if result.warnings:
            lines.append("")
            lines.append("警告:")
            for warning in result.warnings:
                lines.append(f"  - {warning}")
        
        lines.append("")
        lines.append(f"验证结果: {'通过' if result.passed else '未通过'}")
        lines.append("=" * 60)
        
        return "\n".join(lines)


class ScreeningResultValidator:
    """
    筛选结果验证器
    
    验证筛选结果的有效性和可靠性
    
    Requirements: 2.1, 6.1, 6.4
    - 2.1: THE 系统 SHALL 覆盖至少8个科技细分行业
    """
    
    # 行业覆盖要求常量
    MIN_INDUSTRY_COVERAGE = 8   # 最少行业数量要求
    MAX_INDUSTRY_COVERAGE = 10  # 目标行业数量上限
    
    def __init__(
        self,
        min_stocks: int = 50,
        max_stocks: int = 150,
        min_industries: int = 8,  # 更新为8以满足Requirements 2.1
        max_single_industry_ratio: float = 0.30
    ):
        """
        初始化筛选结果验证器
        
        Args:
            min_stocks: 最少股票数量
            max_stocks: 最多股票数量
            min_industries: 最少行业数量
            max_single_industry_ratio: 单一行业最大占比
        """
        self.min_stocks = min_stocks
        self.max_stocks = max_stocks
        self.min_industries = min_industries
        self.max_single_industry_ratio = max_single_industry_ratio
    
    def validate_screening_result(
        self,
        df: pd.DataFrame,
        scores: Optional[List[Any]] = None
    ) -> Tuple[bool, List[str], List[str]]:
        """
        验证筛选结果
        
        Args:
            df: 筛选结果DataFrame
            scores: 评分结果列表
        
        Returns:
            Tuple[是否通过, 警告列表, 建议列表]
        """
        warnings = []
        suggestions = []
        passed = True
        
        if df is None or df.empty:
            return False, ["筛选结果为空"], ["检查筛选条件是否过于严格"]
        
        # 1. 检查数量
        stock_count = len(df)
        if stock_count < self.min_stocks:
            warnings.append(f"股票数量({stock_count})低于最低要求({self.min_stocks})")
            suggestions.append("考虑放宽筛选条件")
            passed = False
        elif stock_count > self.max_stocks:
            warnings.append(f"股票数量({stock_count})超过最大限制({self.max_stocks})")
            suggestions.append("考虑提高筛选标准")
        
        # 2. 检查行业分布
        if 'tech_industry' in df.columns or 'industry' in df.columns:
            industry_col = 'tech_industry' if 'tech_industry' in df.columns else 'industry'
            industry_counts = df[industry_col].value_counts()
            
            # 检查行业数量
            industry_count = len(industry_counts)
            if industry_count < self.min_industries:
                warnings.append(f"行业覆盖({industry_count})低于要求({self.min_industries})")
                suggestions.append("扩大行业筛选范围")
            
            # 检查单一行业集中度
            if len(industry_counts) > 0:
                max_ratio = industry_counts.iloc[0] / stock_count
                if max_ratio > self.max_single_industry_ratio:
                    top_industry = industry_counts.index[0]
                    warnings.append(f"行业'{top_industry}'占比({max_ratio:.1%})过高")
                    suggestions.append("增加其他行业股票以分散风险")
        
        # 3. 检查评分分布
        if 'comprehensive_score' in df.columns:
            avg_score = df['comprehensive_score'].mean()
            if avg_score < 60:
                warnings.append(f"平均评分({avg_score:.1f})偏低")
                suggestions.append("提高评分筛选阈值")
        
        # 4. 检查评级分布
        if 'rating' in df.columns:
            rating_counts = df['rating'].value_counts()
            low_ratings = rating_counts.get('C', 0) + rating_counts.get('B', 0)
            if low_ratings > stock_count * 0.2:
                warnings.append(f"低评级股票占比({low_ratings/stock_count:.1%})过高")
                suggestions.append("移除低评级股票")
        
        return passed, warnings, suggestions
    
    def validate_risk_metrics(
        self,
        df: pd.DataFrame
    ) -> Tuple[bool, Dict[str, float], List[str]]:
        """
        验证风险指标
        
        Args:
            df: 筛选结果DataFrame
        
        Returns:
            Tuple[是否通过, 风险指标字典, 风险警告列表]
        """
        risk_metrics = {}
        risk_warnings = []
        passed = True
        
        if df is None or df.empty:
            return False, {}, ["数据为空"]
        
        # 1. 计算行业集中度风险
        if 'tech_industry' in df.columns or 'industry' in df.columns:
            industry_col = 'tech_industry' if 'tech_industry' in df.columns else 'industry'
            industry_counts = df[industry_col].value_counts()
            
            # HHI指数（赫芬达尔指数）
            if len(industry_counts) > 0:
                shares = industry_counts / len(df)
                hhi = (shares ** 2).sum()
                risk_metrics['industry_hhi'] = hhi
                
                if hhi > 0.25:  # HHI > 0.25 表示高度集中
                    risk_warnings.append(f"行业集中度过高(HHI={hhi:.3f})")
                    passed = False
        
        # 2. 计算市值分布风险
        if 'total_market_cap' in df.columns:
            market_caps = df['total_market_cap'].dropna()
            if len(market_caps) > 0:
                # 小市值股票占比
                small_cap_ratio = (market_caps < 100).sum() / len(market_caps)
                risk_metrics['small_cap_ratio'] = small_cap_ratio
                
                if small_cap_ratio > 0.5:
                    risk_warnings.append(f"小市值股票占比({small_cap_ratio:.1%})过高")
        
        # 3. 计算财务风险
        if 'debt_ratio' in df.columns:
            high_debt = (df['debt_ratio'] > 70).sum()
            high_debt_ratio = high_debt / len(df)
            risk_metrics['high_debt_ratio'] = high_debt_ratio
            
            if high_debt_ratio > 0.3:
                risk_warnings.append(f"高负债股票占比({high_debt_ratio:.1%})过高")
        
        return passed, risk_metrics, risk_warnings


# 全局实例
_quality_monitor: Optional[DataQualityMonitor] = None
_result_validator: Optional[ScreeningResultValidator] = None


def get_quality_monitor() -> DataQualityMonitor:
    """获取数据质量监控器实例"""
    global _quality_monitor
    if _quality_monitor is None:
        _quality_monitor = DataQualityMonitor()
    return _quality_monitor


def get_result_validator() -> ScreeningResultValidator:
    """获取筛选结果验证器实例"""
    global _result_validator
    if _result_validator is None:
        _result_validator = ScreeningResultValidator()
    return _result_validator
