"""
多源数据交叉验证模块

提供多数据源的交叉验证功能，确保数据一致性和准确性，包括：
- 多源数据获取和对比
- 字段级别的差异检测
- 数据一致性评分
- 差异报告生成
- 数据修正建议

Requirements: 7.4 - 多数据源交叉验证
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Set
from enum import Enum
from datetime import datetime
import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class ValidationStatus(Enum):
    """验证状态"""
    PASSED = "passed"           # 验证通过
    WARNING = "warning"         # 有警告但可接受
    FAILED = "failed"           # 验证失败
    SKIPPED = "skipped"         # 跳过验证


class DiscrepancyType(Enum):
    """差异类型"""
    MISSING_RECORD = "missing_record"       # 记录缺失
    VALUE_MISMATCH = "value_mismatch"       # 值不匹配
    TYPE_MISMATCH = "type_mismatch"         # 类型不匹配
    RANGE_VIOLATION = "range_violation"     # 范围违规
    COUNT_MISMATCH = "count_mismatch"       # 数量不匹配


@dataclass
class FieldDiscrepancy:
    """字段差异"""
    field_name: str
    discrepancy_type: DiscrepancyType
    source1_value: Any
    source2_value: Any
    record_key: str  # 记录标识（如股票代码）
    relative_diff: Optional[float] = None  # 相对差异百分比
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'field_name': self.field_name,
            'discrepancy_type': self.discrepancy_type.value,
            'source1_value': str(self.source1_value),
            'source2_value': str(self.source2_value),
            'record_key': self.record_key,
            'relative_diff': self.relative_diff
        }


@dataclass
class FieldValidationResult:
    """字段验证结果"""
    field_name: str
    total_compared: int
    matched_count: int
    mismatched_count: int
    match_rate: float
    discrepancies: List[FieldDiscrepancy] = field(default_factory=list)
    
    @property
    def is_valid(self) -> bool:
        """是否验证通过（匹配率>=95%）"""
        return self.match_rate >= 95.0


@dataclass
class CrossValidationReport:
    """交叉验证报告"""
    timestamp: datetime
    source1_name: str
    source2_name: str
    source1_record_count: int
    source2_record_count: int
    common_record_count: int
    overall_match_rate: float
    status: ValidationStatus
    field_results: List[FieldValidationResult] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    
    @property
    def is_valid(self) -> bool:
        """是否验证通过"""
        return self.status in [ValidationStatus.PASSED, ValidationStatus.WARNING]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'source1_name': self.source1_name,
            'source2_name': self.source2_name,
            'source1_record_count': self.source1_record_count,
            'source2_record_count': self.source2_record_count,
            'common_record_count': self.common_record_count,
            'overall_match_rate': self.overall_match_rate,
            'status': self.status.value,
            'is_valid': self.is_valid,
            'field_results': [
                {
                    'field_name': r.field_name,
                    'match_rate': r.match_rate,
                    'is_valid': r.is_valid
                }
                for r in self.field_results
            ],
            'summary': self.summary,
            'recommendations': self.recommendations
        }


@dataclass
class CrossValidationConfig:
    """交叉验证配置"""
    # 数值字段容差配置
    numeric_tolerance: float = 0.05  # 5%相对差异容差
    price_tolerance: float = 0.02    # 价格字段2%容差
    market_cap_tolerance: float = 0.05  # 市值字段5%容差
    
    # 验证阈值
    min_match_rate: float = 95.0     # 最低匹配率要求
    warning_match_rate: float = 98.0  # 警告阈值
    
    # 字段配置
    key_field: str = 'code'          # 关联字段
    required_fields: List[str] = field(default_factory=lambda: ['code', 'name'])
    
    # 数值字段及其容差
    numeric_fields: Dict[str, float] = field(default_factory=lambda: {
        'price': 0.02,
        'close': 0.02,
        'open': 0.02,
        'high': 0.02,
        'low': 0.02,
        'change_pct': 0.1,
        'turnover_rate': 0.1,
        'pe_ratio': 0.1,
        'pb_ratio': 0.1,
        'total_market_cap': 0.05,
        'float_market_cap': 0.05,
        'volume': 0.1,
        'turnover': 0.1,
    })
    
    # 最大差异记录数
    max_discrepancy_records: int = 100


class CrossSourceValidator:
    """
    多源数据交叉验证器
    
    提供多数据源的交叉验证功能，确保数据一致性
    
    Requirements: 7.4
    """
    
    def __init__(self, config: Optional[CrossValidationConfig] = None):
        """
        初始化交叉验证器
        
        Args:
            config: 验证配置，None则使用默认配置
        """
        self.config = config or CrossValidationConfig()
    
    def validate(
        self,
        source1_df: pd.DataFrame,
        source2_df: pd.DataFrame,
        source1_name: str = "source1",
        source2_name: str = "source2"
    ) -> CrossValidationReport:
        """
        执行多源数据交叉验证
        
        Args:
            source1_df: 第一个数据源
            source2_df: 第二个数据源
            source1_name: 第一个数据源名称
            source2_name: 第二个数据源名称
        
        Returns:
            CrossValidationReport: 验证报告
        """
        # 处理空数据情况
        if source1_df is None or source1_df.empty:
            return self._create_empty_report(
                source1_name, source2_name,
                "第一个数据源为空"
            )
        
        if source2_df is None or source2_df.empty:
            return self._create_empty_report(
                source1_name, source2_name,
                "第二个数据源为空"
            )
        
        # 检查关联字段
        key_field = self.config.key_field
        if key_field not in source1_df.columns:
            return self._create_empty_report(
                source1_name, source2_name,
                f"第一个数据源缺少关联字段: {key_field}"
            )
        
        if key_field not in source2_df.columns:
            return self._create_empty_report(
                source1_name, source2_name,
                f"第二个数据源缺少关联字段: {key_field}"
            )
        
        # 标准化关联字段
        source1_df = source1_df.copy()
        source2_df = source2_df.copy()
        source1_df[key_field] = source1_df[key_field].astype(str).str.strip()
        source2_df[key_field] = source2_df[key_field].astype(str).str.strip()
        
        # 合并数据
        merged = pd.merge(
            source1_df,
            source2_df,
            on=key_field,
            suffixes=('_s1', '_s2'),
            how='inner'
        )
        
        # 计算记录统计
        source1_count = len(source1_df)
        source2_count = len(source2_df)
        common_count = len(merged)
        
        # 验证各字段
        field_results = []
        all_discrepancies = []
        
        # 获取共同字段
        common_fields = self._get_common_fields(source1_df, source2_df)
        
        for field_name in common_fields:
            if field_name == key_field:
                continue
            
            result = self._validate_field(
                merged, field_name, key_field
            )
            field_results.append(result)
            all_discrepancies.extend(result.discrepancies)
        
        # 计算总体匹配率
        overall_match_rate = self._calculate_overall_match_rate(field_results)
        
        # 确定验证状态
        status = self._determine_status(overall_match_rate, common_count, source1_count, source2_count)
        
        # 生成摘要
        summary = self._generate_summary(
            source1_count, source2_count, common_count,
            field_results, all_discrepancies
        )
        
        # 生成建议
        recommendations = self._generate_recommendations(
            status, field_results, common_count, source1_count, source2_count
        )
        
        return CrossValidationReport(
            timestamp=datetime.now(),
            source1_name=source1_name,
            source2_name=source2_name,
            source1_record_count=source1_count,
            source2_record_count=source2_count,
            common_record_count=common_count,
            overall_match_rate=overall_match_rate,
            status=status,
            field_results=field_results,
            summary=summary,
            recommendations=recommendations
        )

    
    def _get_common_fields(
        self,
        df1: pd.DataFrame,
        df2: pd.DataFrame
    ) -> List[str]:
        """获取两个数据源的共同字段"""
        # 获取原始列名（去除后缀）
        cols1 = set(df1.columns)
        cols2 = set(df2.columns)
        
        # 找出共同字段
        common = cols1.intersection(cols2)
        
        # 按优先级排序：必需字段优先，然后是数值字段
        priority_fields = self.config.required_fields + list(self.config.numeric_fields.keys())
        
        sorted_fields = []
        for f in priority_fields:
            if f in common:
                sorted_fields.append(f)
        
        # 添加其他共同字段
        for f in common:
            if f not in sorted_fields:
                sorted_fields.append(f)
        
        return sorted_fields
    
    def _validate_field(
        self,
        merged: pd.DataFrame,
        field_name: str,
        key_field: str
    ) -> FieldValidationResult:
        """验证单个字段"""
        s1_col = f'{field_name}_s1'
        s2_col = f'{field_name}_s2'
        
        # 检查列是否存在
        if s1_col not in merged.columns or s2_col not in merged.columns:
            return FieldValidationResult(
                field_name=field_name,
                total_compared=0,
                matched_count=0,
                mismatched_count=0,
                match_rate=0.0
            )
        
        total = len(merged)
        discrepancies = []
        
        # 获取容差
        tolerance = self.config.numeric_fields.get(
            field_name, self.config.numeric_tolerance
        )
        
        # 判断是否为数值字段
        is_numeric = field_name in self.config.numeric_fields
        
        if is_numeric:
            matched, mismatched, field_discrepancies = self._compare_numeric_field(
                merged, s1_col, s2_col, key_field, field_name, tolerance
            )
        else:
            matched, mismatched, field_discrepancies = self._compare_string_field(
                merged, s1_col, s2_col, key_field, field_name
            )
        
        # 限制差异记录数
        discrepancies = field_discrepancies[:self.config.max_discrepancy_records]
        
        match_rate = (matched / total * 100) if total > 0 else 0.0
        
        return FieldValidationResult(
            field_name=field_name,
            total_compared=total,
            matched_count=matched,
            mismatched_count=mismatched,
            match_rate=match_rate,
            discrepancies=discrepancies
        )
    
    def _compare_numeric_field(
        self,
        merged: pd.DataFrame,
        s1_col: str,
        s2_col: str,
        key_field: str,
        field_name: str,
        tolerance: float
    ) -> Tuple[int, int, List[FieldDiscrepancy]]:
        """比较数值字段"""
        discrepancies = []
        
        # 转换为数值
        s1_values = pd.to_numeric(merged[s1_col], errors='coerce')
        s2_values = pd.to_numeric(merged[s2_col], errors='coerce')
        
        # 处理空值：两边都为空视为匹配
        both_null = s1_values.isna() & s2_values.isna()
        one_null = s1_values.isna() ^ s2_values.isna()
        both_valid = s1_values.notna() & s2_values.notna()
        
        # 计算相对差异（避免除零）
        with np.errstate(divide='ignore', invalid='ignore'):
            # 使用两个值的平均值作为基准
            base = (np.abs(s1_values) + np.abs(s2_values)) / 2
            relative_diff = np.where(
                base > 0,
                np.abs(s1_values - s2_values) / base,
                0
            )
        
        # 判断是否在容差范围内
        within_tolerance = relative_diff <= tolerance
        
        # 匹配条件：两边都空，或者都有值且在容差内
        matched_mask = both_null | (both_valid & within_tolerance)
        
        matched = matched_mask.sum()
        mismatched = len(merged) - matched
        
        # 记录差异
        mismatch_indices = merged.index[~matched_mask]
        for idx in mismatch_indices[:self.config.max_discrepancy_records]:
            row = merged.loc[idx]
            s1_val = row[s1_col]
            s2_val = row[s2_col]
            
            # 确定差异类型
            if pd.isna(s1_val) or pd.isna(s2_val):
                disc_type = DiscrepancyType.MISSING_RECORD
            else:
                disc_type = DiscrepancyType.VALUE_MISMATCH
            
            discrepancies.append(FieldDiscrepancy(
                field_name=field_name,
                discrepancy_type=disc_type,
                source1_value=s1_val,
                source2_value=s2_val,
                record_key=str(row[key_field]),
                relative_diff=relative_diff[idx] if idx < len(relative_diff) else None
            ))
        
        return matched, mismatched, discrepancies
    
    def _compare_string_field(
        self,
        merged: pd.DataFrame,
        s1_col: str,
        s2_col: str,
        key_field: str,
        field_name: str
    ) -> Tuple[int, int, List[FieldDiscrepancy]]:
        """比较字符串字段"""
        discrepancies = []
        
        # 转换为字符串并标准化
        s1_values = merged[s1_col].fillna('').astype(str).str.strip()
        s2_values = merged[s2_col].fillna('').astype(str).str.strip()
        
        # 精确匹配
        matched_mask = s1_values == s2_values
        
        matched = matched_mask.sum()
        mismatched = len(merged) - matched
        
        # 记录差异
        mismatch_indices = merged.index[~matched_mask]
        for idx in mismatch_indices[:self.config.max_discrepancy_records]:
            row = merged.loc[idx]
            discrepancies.append(FieldDiscrepancy(
                field_name=field_name,
                discrepancy_type=DiscrepancyType.VALUE_MISMATCH,
                source1_value=row[s1_col],
                source2_value=row[s2_col],
                record_key=str(row[key_field])
            ))
        
        return matched, mismatched, discrepancies
    
    def _calculate_overall_match_rate(
        self,
        field_results: List[FieldValidationResult]
    ) -> float:
        """计算总体匹配率"""
        if not field_results:
            return 0.0
        
        # 使用加权平均，数值字段权重更高
        weights = {}
        for field in self.config.required_fields:
            weights[field] = 2.0
        for field in self.config.numeric_fields:
            weights[field] = 1.5
        
        total_weight = 0
        weighted_sum = 0
        
        for result in field_results:
            if result.total_compared > 0:
                weight = weights.get(result.field_name, 1.0)
                weighted_sum += result.match_rate * weight
                total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0
    
    def _determine_status(
        self,
        match_rate: float,
        common_count: int,
        source1_count: int,
        source2_count: int
    ) -> ValidationStatus:
        """确定验证状态"""
        # 检查记录覆盖率
        coverage_rate = common_count / max(source1_count, source2_count) * 100 if max(source1_count, source2_count) > 0 else 0
        
        if coverage_rate < 50:
            return ValidationStatus.FAILED
        
        if match_rate >= self.config.warning_match_rate:
            return ValidationStatus.PASSED
        elif match_rate >= self.config.min_match_rate:
            return ValidationStatus.WARNING
        else:
            return ValidationStatus.FAILED
    
    def _generate_summary(
        self,
        source1_count: int,
        source2_count: int,
        common_count: int,
        field_results: List[FieldValidationResult],
        discrepancies: List[FieldDiscrepancy]
    ) -> Dict[str, Any]:
        """生成验证摘要"""
        # 统计差异类型
        discrepancy_counts = {}
        for d in discrepancies:
            disc_type = d.discrepancy_type.value
            discrepancy_counts[disc_type] = discrepancy_counts.get(disc_type, 0) + 1
        
        # 统计字段匹配情况
        field_stats = {
            'total_fields': len(field_results),
            'passed_fields': sum(1 for r in field_results if r.is_valid),
            'failed_fields': sum(1 for r in field_results if not r.is_valid)
        }
        
        # 计算覆盖率
        coverage_rate = common_count / max(source1_count, source2_count) * 100 if max(source1_count, source2_count) > 0 else 0
        
        return {
            'record_coverage_rate': round(coverage_rate, 2),
            'only_in_source1': source1_count - common_count,
            'only_in_source2': source2_count - common_count,
            'field_stats': field_stats,
            'discrepancy_counts': discrepancy_counts,
            'total_discrepancies': len(discrepancies)
        }
    
    def _generate_recommendations(
        self,
        status: ValidationStatus,
        field_results: List[FieldValidationResult],
        common_count: int,
        source1_count: int,
        source2_count: int
    ) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        # 覆盖率建议
        coverage_rate = common_count / max(source1_count, source2_count) * 100 if max(source1_count, source2_count) > 0 else 0
        if coverage_rate < 90:
            recommendations.append(
                f"记录覆盖率较低({coverage_rate:.1f}%)，建议检查数据源的股票代码格式是否一致"
            )
        
        # 字段匹配建议
        for result in field_results:
            if not result.is_valid:
                recommendations.append(
                    f"字段'{result.field_name}'匹配率({result.match_rate:.1f}%)未达标，"
                    f"建议检查该字段的数据来源和计算方式"
                )
        
        # 状态相关建议
        if status == ValidationStatus.FAILED:
            recommendations.append(
                "交叉验证失败，建议优先使用主数据源，并排查数据差异原因"
            )
        elif status == ValidationStatus.WARNING:
            recommendations.append(
                "交叉验证有警告，建议关注差异较大的字段"
            )
        
        return recommendations
    
    def _create_empty_report(
        self,
        source1_name: str,
        source2_name: str,
        reason: str
    ) -> CrossValidationReport:
        """创建空报告"""
        return CrossValidationReport(
            timestamp=datetime.now(),
            source1_name=source1_name,
            source2_name=source2_name,
            source1_record_count=0,
            source2_record_count=0,
            common_record_count=0,
            overall_match_rate=0.0,
            status=ValidationStatus.SKIPPED,
            recommendations=[reason]
        )
    
    def generate_report_text(self, report: CrossValidationReport) -> str:
        """生成报告文本"""
        lines = [
            "=" * 70,
            "多源数据交叉验证报告",
            "=" * 70,
            f"验证时间: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            f"数据源1: {report.source1_name} ({report.source1_record_count}条记录)",
            f"数据源2: {report.source2_name} ({report.source2_record_count}条记录)",
            f"共同记录: {report.common_record_count}条",
            "",
            f"总体匹配率: {report.overall_match_rate:.2f}%",
            f"验证状态: {report.status.value}",
            f"是否通过: {'是' if report.is_valid else '否'}",
            "",
        ]
        
        if report.field_results:
            lines.append("字段验证详情:")
            for result in report.field_results:
                status_icon = "✓" if result.is_valid else "✗"
                lines.append(
                    f"  {status_icon} {result.field_name}: {result.match_rate:.2f}% "
                    f"({result.matched_count}/{result.total_compared})"
                )
        
        if report.summary:
            lines.append("")
            lines.append("验证摘要:")
            lines.append(f"  记录覆盖率: {report.summary.get('record_coverage_rate', 0):.2f}%")
            lines.append(f"  仅在数据源1: {report.summary.get('only_in_source1', 0)}条")
            lines.append(f"  仅在数据源2: {report.summary.get('only_in_source2', 0)}条")
            
            if report.summary.get('discrepancy_counts'):
                lines.append("  差异类型统计:")
                for disc_type, count in report.summary['discrepancy_counts'].items():
                    lines.append(f"    - {disc_type}: {count}")
        
        if report.recommendations:
            lines.append("")
            lines.append("改进建议:")
            for rec in report.recommendations:
                lines.append(f"  - {rec}")
        
        lines.append("=" * 70)
        
        return "\n".join(lines)


class MultiSourceCrossValidator:
    """
    多数据源交叉验证管理器
    
    支持同时验证多个数据源的一致性
    """
    
    def __init__(self, config: Optional[CrossValidationConfig] = None):
        """
        初始化多源验证管理器
        
        Args:
            config: 验证配置
        """
        self.config = config or CrossValidationConfig()
        self.validator = CrossSourceValidator(config)
    
    def validate_all_sources(
        self,
        sources: Dict[str, pd.DataFrame]
    ) -> Dict[str, CrossValidationReport]:
        """
        验证所有数据源对
        
        Args:
            sources: 数据源字典 {名称: DataFrame}
        
        Returns:
            验证报告字典 {源对名称: 报告}
        """
        reports = {}
        source_names = list(sources.keys())
        
        # 两两比较
        for i in range(len(source_names)):
            for j in range(i + 1, len(source_names)):
                name1 = source_names[i]
                name2 = source_names[j]
                
                report = self.validator.validate(
                    sources[name1],
                    sources[name2],
                    name1,
                    name2
                )
                
                pair_key = f"{name1}_vs_{name2}"
                reports[pair_key] = report
        
        return reports
    
    def get_consensus_data(
        self,
        sources: Dict[str, pd.DataFrame],
        strategy: str = "majority"
    ) -> pd.DataFrame:
        """
        获取共识数据
        
        Args:
            sources: 数据源字典
            strategy: 共识策略 ("majority", "primary", "average")
        
        Returns:
            共识数据DataFrame
        """
        if not sources:
            return pd.DataFrame()
        
        source_list = list(sources.values())
        source_names = list(sources.keys())
        
        if len(source_list) == 1:
            return source_list[0].copy()
        
        # 使用第一个数据源作为基准
        key_field = self.config.key_field
        base_df = source_list[0].copy()
        
        if strategy == "primary":
            return base_df
        
        # 合并所有数据源
        merged = base_df
        for i, df in enumerate(source_list[1:], 1):
            merged = pd.merge(
                merged,
                df,
                on=key_field,
                suffixes=('', f'_src{i}'),
                how='outer'
            )
        
        if strategy == "average":
            # 对数值字段取平均
            for field in self.config.numeric_fields:
                cols = [c for c in merged.columns if c == field or c.startswith(f'{field}_src')]
                if cols:
                    merged[field] = merged[cols].mean(axis=1)
                    # 删除临时列
                    for c in cols[1:]:
                        if c in merged.columns:
                            merged = merged.drop(columns=[c])
        
        return merged
    
    def generate_summary_report(
        self,
        reports: Dict[str, CrossValidationReport]
    ) -> str:
        """生成汇总报告"""
        lines = [
            "=" * 70,
            "多源数据交叉验证汇总报告",
            "=" * 70,
            f"验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"验证对数: {len(reports)}",
            "",
        ]
        
        passed_count = sum(1 for r in reports.values() if r.is_valid)
        lines.append(f"通过验证: {passed_count}/{len(reports)}")
        lines.append("")
        
        for pair_name, report in reports.items():
            status_icon = "✓" if report.is_valid else "✗"
            lines.append(
                f"{status_icon} {pair_name}: {report.overall_match_rate:.2f}% "
                f"({report.status.value})"
            )
        
        lines.append("=" * 70)
        
        return "\n".join(lines)


# 全局实例
_cross_validator: Optional[CrossSourceValidator] = None
_multi_validator: Optional[MultiSourceCrossValidator] = None


def get_cross_validator() -> CrossSourceValidator:
    """获取交叉验证器实例（单例模式）"""
    global _cross_validator
    if _cross_validator is None:
        _cross_validator = CrossSourceValidator()
    return _cross_validator


def get_multi_source_validator() -> MultiSourceCrossValidator:
    """获取多源验证管理器实例（单例模式）"""
    global _multi_validator
    if _multi_validator is None:
        _multi_validator = MultiSourceCrossValidator()
    return _multi_validator


def cross_validate_sources(
    source1_df: pd.DataFrame,
    source2_df: pd.DataFrame,
    source1_name: str = "source1",
    source2_name: str = "source2"
) -> CrossValidationReport:
    """
    便捷函数：执行多源数据交叉验证
    
    Args:
        source1_df: 第一个数据源
        source2_df: 第二个数据源
        source1_name: 第一个数据源名称
        source2_name: 第二个数据源名称
    
    Returns:
        CrossValidationReport: 验证报告
    """
    validator = get_cross_validator()
    return validator.validate(source1_df, source2_df, source1_name, source2_name)
