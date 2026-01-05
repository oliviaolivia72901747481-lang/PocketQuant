"""
数据准确率验证模块

提供数据准确率验证功能，确保数据准确率达到99%以上，包括：
- 多源数据交叉验证
- 数据准确率计算
- 准确率报告生成
- 数据修正建议

Requirements: 7.2, 7.4, 7.5
成功标准: 数据准确率 ≥ 99%
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from datetime import datetime
import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class AccuracyLevel(Enum):
    """准确率等级"""
    EXCELLENT = "excellent"    # 优秀 (≥99%)
    GOOD = "good"              # 良好 (95-99%)
    ACCEPTABLE = "acceptable"  # 可接受 (90-95%)
    POOR = "poor"              # 较差 (80-90%)
    UNACCEPTABLE = "unacceptable"  # 不可接受 (<80%)


class ValidationMethod(Enum):
    """验证方法"""
    CROSS_SOURCE = "cross_source"      # 多源交叉验证
    RANGE_CHECK = "range_check"        # 范围检查
    CONSISTENCY = "consistency"        # 一致性检查
    FORMAT_CHECK = "format_check"      # 格式检查
    LOGIC_CHECK = "logic_check"        # 逻辑检查


@dataclass
class FieldAccuracyResult:
    """字段准确率结果"""
    field_name: str
    total_records: int
    accurate_records: int
    accuracy_rate: float
    validation_method: ValidationMethod
    issues: List[str] = field(default_factory=list)
    
    @property
    def is_accurate(self) -> bool:
        """是否达到准确率要求"""
        return self.accuracy_rate >= 99.0


@dataclass
class DataAccuracyReport:
    """数据准确率报告"""
    timestamp: datetime
    total_records: int
    total_fields_checked: int
    overall_accuracy: float
    accuracy_level: AccuracyLevel
    field_results: List[FieldAccuracyResult] = field(default_factory=list)
    cross_validation_passed: bool = True
    issues_summary: Dict[str, int] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    
    @property
    def meets_target(self) -> bool:
        """是否达到99%准确率目标"""
        return self.overall_accuracy >= 99.0


class DataAccuracyValidator:
    """
    数据准确率验证器
    
    验证数据准确率是否达到99%以上的目标
    
    Requirements: 7.2, 7.4, 7.5
    """
    
    # 股票代码格式正则
    VALID_CODE_PATTERNS = [
        r'^000\d{3}$',  # 深圳主板
        r'^001\d{3}$',  # 深圳主板
        r'^002\d{3}$',  # 中小板
        r'^003\d{3}$',  # 深圳主板
        r'^300\d{3}$',  # 创业板
        r'^600\d{3}$',  # 上海主板
        r'^601\d{3}$',  # 上海主板
        r'^603\d{3}$',  # 上海主板
        r'^605\d{3}$',  # 上海主板
        r'^688\d{3}$',  # 科创板
    ]
    
    # 数值字段有效范围
    FIELD_RANGES = {
        'price': {'min': 0.01, 'max': 10000, 'allow_null': False},
        'close': {'min': 0.01, 'max': 10000, 'allow_null': False},
        'open': {'min': 0.01, 'max': 10000, 'allow_null': True},
        'high': {'min': 0.01, 'max': 10000, 'allow_null': True},
        'low': {'min': 0.01, 'max': 10000, 'allow_null': True},
        'change_pct': {'min': -20, 'max': 20, 'allow_null': True},
        'turnover_rate': {'min': 0, 'max': 100, 'allow_null': True},
        'pe_ratio': {'min': -10000, 'max': 100000, 'allow_null': True},
        'pb_ratio': {'min': 0, 'max': 1000, 'allow_null': True},
        'total_market_cap': {'min': 0, 'max': 1e15, 'allow_null': True},
        'float_market_cap': {'min': 0, 'max': 1e15, 'allow_null': True},
        'volume': {'min': 0, 'max': 1e13, 'allow_null': True},
        'turnover': {'min': 0, 'max': 1e15, 'allow_null': True},
        'roe': {'min': -500, 'max': 500, 'allow_null': True},
        'roa': {'min': -200, 'max': 200, 'allow_null': True},
        'gross_margin': {'min': -100, 'max': 100, 'allow_null': True},
        'net_margin': {'min': -500, 'max': 500, 'allow_null': True},
        'debt_ratio': {'min': 0, 'max': 300, 'allow_null': True},
        'current_ratio': {'min': 0, 'max': 100, 'allow_null': True},
    }
    
    # 必需字段
    REQUIRED_FIELDS = ['code', 'name']
    
    # 交叉验证容差（允许的差异百分比）
    CROSS_VALIDATION_TOLERANCE = 0.05  # 5%
    
    def __init__(self, target_accuracy: float = 99.0):
        """
        初始化数据准确率验证器
        
        Args:
            target_accuracy: 目标准确率（默认99%）
        """
        self.target_accuracy = target_accuracy
    
    def validate_accuracy(self, df: pd.DataFrame) -> DataAccuracyReport:
        """
        验证数据准确率
        
        Args:
            df: 待验证的数据
        
        Returns:
            DataAccuracyReport: 准确率报告
        """
        if df is None or df.empty:
            return self._create_empty_report()
        
        field_results = []
        issues_summary = {}
        
        # 1. 验证股票代码格式准确率
        if 'code' in df.columns:
            code_result = self._validate_code_accuracy(df)
            field_results.append(code_result)
            if code_result.issues:
                issues_summary['code_format'] = len(code_result.issues)
        
        # 2. 验证必需字段完整性
        for field in self.REQUIRED_FIELDS:
            if field in df.columns:
                result = self._validate_required_field(df, field)
                field_results.append(result)
                if not result.is_accurate:
                    issues_summary[f'{field}_missing'] = result.total_records - result.accurate_records
        
        # 3. 验证数值字段范围准确率
        for field, limits in self.FIELD_RANGES.items():
            if field in df.columns:
                result = self._validate_numeric_range(df, field, limits)
                field_results.append(result)
                if result.issues:
                    issues_summary[f'{field}_range'] = len(result.issues)
        
        # 4. 验证数据一致性
        consistency_result = self._validate_consistency(df)
        field_results.append(consistency_result)
        if consistency_result.issues:
            issues_summary['consistency'] = len(consistency_result.issues)
        
        # 5. 验证逻辑关系
        logic_result = self._validate_logic(df)
        field_results.append(logic_result)
        if logic_result.issues:
            issues_summary['logic'] = len(logic_result.issues)
        
        # 计算总体准确率
        overall_accuracy = self._calculate_overall_accuracy(field_results)
        accuracy_level = self._determine_accuracy_level(overall_accuracy)
        
        # 生成建议
        recommendations = self._generate_recommendations(
            overall_accuracy, field_results, issues_summary
        )
        
        return DataAccuracyReport(
            timestamp=datetime.now(),
            total_records=len(df),
            total_fields_checked=len(field_results),
            overall_accuracy=overall_accuracy,
            accuracy_level=accuracy_level,
            field_results=field_results,
            cross_validation_passed=overall_accuracy >= self.target_accuracy,
            issues_summary=issues_summary,
            recommendations=recommendations
        )
    
    def _validate_code_accuracy(self, df: pd.DataFrame) -> FieldAccuracyResult:
        """验证股票代码格式准确率"""
        import re
        
        total = len(df)
        issues = []
        
        def is_valid_code(code):
            if pd.isna(code):
                return False
            code_str = str(code).strip().zfill(6)
            for pattern in self.VALID_CODE_PATTERNS:
                if re.match(pattern, code_str):
                    return True
            return False
        
        valid_mask = df['code'].apply(is_valid_code)
        accurate_count = valid_mask.sum()
        
        # 记录无效代码
        invalid_codes = df[~valid_mask]['code'].head(10).tolist()
        if invalid_codes:
            issues.extend([f"无效代码: {code}" for code in invalid_codes])
        
        accuracy_rate = (accurate_count / total * 100) if total > 0 else 0
        
        return FieldAccuracyResult(
            field_name='code',
            total_records=total,
            accurate_records=accurate_count,
            accuracy_rate=accuracy_rate,
            validation_method=ValidationMethod.FORMAT_CHECK,
            issues=issues
        )
    
    def _validate_required_field(
        self, 
        df: pd.DataFrame, 
        field: str
    ) -> FieldAccuracyResult:
        """验证必需字段完整性"""
        total = len(df)
        non_null_count = df[field].notna().sum()
        
        # 对于字符串字段，还要检查非空字符串
        if df[field].dtype == object:
            non_empty = df[field].astype(str).str.strip().str.len() > 0
            non_null_count = (df[field].notna() & non_empty).sum()
        
        accuracy_rate = (non_null_count / total * 100) if total > 0 else 0
        
        issues = []
        if non_null_count < total:
            missing_count = total - non_null_count
            issues.append(f"字段'{field}'缺失{missing_count}条记录")
        
        return FieldAccuracyResult(
            field_name=field,
            total_records=total,
            accurate_records=non_null_count,
            accuracy_rate=accuracy_rate,
            validation_method=ValidationMethod.RANGE_CHECK,
            issues=issues
        )
    
    def _validate_numeric_range(
        self, 
        df: pd.DataFrame, 
        field: str,
        limits: Dict[str, Any]
    ) -> FieldAccuracyResult:
        """验证数值字段范围准确率"""
        total = len(df)
        issues = []
        
        # 转换为数值
        numeric_values = pd.to_numeric(df[field], errors='coerce')
        
        # 检查非空值
        non_null_mask = numeric_values.notna()
        
        if limits.get('allow_null', True):
            # 允许空值时，只检查非空值的范围
            valid_range_mask = (
                (numeric_values >= limits['min']) & 
                (numeric_values <= limits['max'])
            ) | numeric_values.isna()
        else:
            # 不允许空值时，空值也算不准确
            valid_range_mask = (
                non_null_mask &
                (numeric_values >= limits['min']) & 
                (numeric_values <= limits['max'])
            )
        
        accurate_count = valid_range_mask.sum()
        
        # 记录范围外的值
        out_of_range = df[~valid_range_mask]
        if len(out_of_range) > 0:
            sample_values = out_of_range[field].head(5).tolist()
            issues.append(
                f"字段'{field}'有{len(out_of_range)}个值超出范围"
                f"[{limits['min']}, {limits['max']}]，示例: {sample_values}"
            )
        
        accuracy_rate = (accurate_count / total * 100) if total > 0 else 0
        
        return FieldAccuracyResult(
            field_name=field,
            total_records=total,
            accurate_records=accurate_count,
            accuracy_rate=accuracy_rate,
            validation_method=ValidationMethod.RANGE_CHECK,
            issues=issues
        )
    
    def _validate_consistency(self, df: pd.DataFrame) -> FieldAccuracyResult:
        """验证数据一致性"""
        total = len(df)
        inconsistent_count = 0
        issues = []
        
        # 检查市值一致性：流通市值不应大于总市值
        if 'total_market_cap' in df.columns and 'float_market_cap' in df.columns:
            # 允许1%的误差
            inconsistent = df[
                (df['float_market_cap'].notna()) & 
                (df['total_market_cap'].notna()) &
                (df['float_market_cap'] > df['total_market_cap'] * 1.01)
            ]
            if len(inconsistent) > 0:
                inconsistent_count += len(inconsistent)
                issues.append(f"流通市值大于总市值: {len(inconsistent)}条")
        
        # 检查价格一致性：最高价应>=最低价
        if 'high' in df.columns and 'low' in df.columns:
            price_inconsistent = df[
                (df['high'].notna()) & 
                (df['low'].notna()) &
                (df['high'] < df['low'])
            ]
            if len(price_inconsistent) > 0:
                inconsistent_count += len(price_inconsistent)
                issues.append(f"最高价低于最低价: {len(price_inconsistent)}条")
        
        # 检查开盘收盘价在高低价范围内
        if all(col in df.columns for col in ['open', 'close', 'high', 'low']):
            price_range_check = df[
                (df['open'].notna()) & (df['close'].notna()) &
                (df['high'].notna()) & (df['low'].notna()) &
                ((df['open'] > df['high']) | (df['open'] < df['low']) |
                 (df['close'] > df['high']) | (df['close'] < df['low']))
            ]
            if len(price_range_check) > 0:
                inconsistent_count += len(price_range_check)
                issues.append(f"开盘/收盘价超出高低价范围: {len(price_range_check)}条")
        
        accurate_count = total - inconsistent_count
        accuracy_rate = (accurate_count / total * 100) if total > 0 else 100
        
        return FieldAccuracyResult(
            field_name='consistency',
            total_records=total,
            accurate_records=accurate_count,
            accuracy_rate=accuracy_rate,
            validation_method=ValidationMethod.CONSISTENCY,
            issues=issues
        )
    
    def _validate_logic(self, df: pd.DataFrame) -> FieldAccuracyResult:
        """验证逻辑关系"""
        total = len(df)
        logic_errors = 0
        issues = []
        
        # 检查PE和PB的逻辑关系
        if 'pe_ratio' in df.columns and 'pb_ratio' in df.columns:
            # 如果PE为正且PB为正，ROE应该可以从PE/PB推算
            # 这里只做基本的逻辑检查
            pass
        
        # 检查换手率逻辑：换手率应该与成交量/流通股本一致
        # 这里简化为检查换手率是否在合理范围
        if 'turnover_rate' in df.columns:
            extreme_turnover = df[
                (df['turnover_rate'].notna()) &
                ((df['turnover_rate'] < 0) | (df['turnover_rate'] > 50))
            ]
            if len(extreme_turnover) > 0:
                logic_errors += len(extreme_turnover)
                issues.append(f"换手率异常: {len(extreme_turnover)}条")
        
        # 检查涨跌幅逻辑：普通股票涨跌幅限制为±10%（ST为±5%）
        if 'change_pct' in df.columns and 'name' in df.columns:
            # 非ST股票涨跌幅超过±11%（允许1%误差）
            non_st = df[~df['name'].str.contains('ST', na=False, case=False)]
            extreme_change = non_st[
                (non_st['change_pct'].notna()) &
                ((non_st['change_pct'] > 11) | (non_st['change_pct'] < -11))
            ]
            if len(extreme_change) > 0:
                # 这可能是正常的（如新股、复牌等），只记录不计入错误
                issues.append(f"涨跌幅超过限制（可能为新股/复牌）: {len(extreme_change)}条")
        
        accurate_count = total - logic_errors
        accuracy_rate = (accurate_count / total * 100) if total > 0 else 100
        
        return FieldAccuracyResult(
            field_name='logic',
            total_records=total,
            accurate_records=accurate_count,
            accuracy_rate=accuracy_rate,
            validation_method=ValidationMethod.LOGIC_CHECK,
            issues=issues
        )
    
    def _calculate_overall_accuracy(
        self, 
        field_results: List[FieldAccuracyResult]
    ) -> float:
        """计算总体准确率"""
        if not field_results:
            return 0.0
        
        # 使用加权平均，必需字段权重更高
        weights = {
            'code': 2.0,
            'name': 2.0,
            'price': 1.5,
            'close': 1.5,
            'consistency': 1.5,
            'logic': 1.0,
        }
        
        total_weight = 0
        weighted_sum = 0
        
        for result in field_results:
            weight = weights.get(result.field_name, 1.0)
            weighted_sum += result.accuracy_rate * weight
            total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0
    
    def _determine_accuracy_level(self, accuracy: float) -> AccuracyLevel:
        """确定准确率等级"""
        if accuracy >= 99:
            return AccuracyLevel.EXCELLENT
        elif accuracy >= 95:
            return AccuracyLevel.GOOD
        elif accuracy >= 90:
            return AccuracyLevel.ACCEPTABLE
        elif accuracy >= 80:
            return AccuracyLevel.POOR
        else:
            return AccuracyLevel.UNACCEPTABLE
    
    def _generate_recommendations(
        self,
        overall_accuracy: float,
        field_results: List[FieldAccuracyResult],
        issues_summary: Dict[str, int]
    ) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        if overall_accuracy < self.target_accuracy:
            recommendations.append(
                f"当前准确率({overall_accuracy:.2f}%)未达到目标({self.target_accuracy}%)，"
                "建议检查数据源质量"
            )
        
        # 针对具体问题给出建议
        for result in field_results:
            if not result.is_accurate:
                if result.field_name == 'code':
                    recommendations.append("建议标准化股票代码格式为6位数字")
                elif result.field_name in self.REQUIRED_FIELDS:
                    recommendations.append(f"建议补充缺失的{result.field_name}字段数据")
                elif result.validation_method == ValidationMethod.RANGE_CHECK:
                    recommendations.append(f"建议检查{result.field_name}字段的数据来源")
        
        if 'consistency' in issues_summary:
            recommendations.append("建议检查数据一致性，确保市值、价格等字段逻辑正确")
        
        return recommendations
    
    def _create_empty_report(self) -> DataAccuracyReport:
        """创建空报告"""
        return DataAccuracyReport(
            timestamp=datetime.now(),
            total_records=0,
            total_fields_checked=0,
            overall_accuracy=0.0,
            accuracy_level=AccuracyLevel.UNACCEPTABLE,
            cross_validation_passed=False,
            recommendations=["无数据可供验证"]
        )
    
    def cross_validate_sources(
        self,
        source1_df: pd.DataFrame,
        source2_df: pd.DataFrame,
        key_field: str = 'code'
    ) -> Tuple[float, List[str]]:
        """
        多源数据交叉验证
        
        Args:
            source1_df: 第一个数据源
            source2_df: 第二个数据源
            key_field: 关联字段
        
        Returns:
            Tuple[匹配率, 差异列表]
        """
        if source1_df is None or source2_df is None:
            return 0.0, ["数据源为空"]
        
        if source1_df.empty or source2_df.empty:
            return 0.0, ["数据源为空"]
        
        discrepancies = []
        
        # 合并两个数据源
        merged = pd.merge(
            source1_df, 
            source2_df, 
            on=key_field, 
            suffixes=('_s1', '_s2'),
            how='inner'
        )
        
        if merged.empty:
            return 0.0, ["两个数据源无匹配记录"]
        
        total_checks = 0
        matching_checks = 0
        
        # 比较共同的数值字段
        numeric_fields = ['price', 'close', 'total_market_cap', 'float_market_cap']
        
        for field in numeric_fields:
            s1_col = f'{field}_s1'
            s2_col = f'{field}_s2'
            
            if s1_col in merged.columns and s2_col in merged.columns:
                # 计算相对差异
                s1_values = pd.to_numeric(merged[s1_col], errors='coerce')
                s2_values = pd.to_numeric(merged[s2_col], errors='coerce')
                
                valid_mask = s1_values.notna() & s2_values.notna() & (s1_values != 0)
                
                if valid_mask.sum() > 0:
                    relative_diff = abs(s1_values - s2_values) / s1_values
                    within_tolerance = relative_diff <= self.CROSS_VALIDATION_TOLERANCE
                    
                    total_checks += valid_mask.sum()
                    matching_checks += (valid_mask & within_tolerance).sum()
                    
                    mismatch_count = valid_mask.sum() - (valid_mask & within_tolerance).sum()
                    if mismatch_count > 0:
                        discrepancies.append(
                            f"字段'{field}'有{mismatch_count}条记录差异超过{self.CROSS_VALIDATION_TOLERANCE*100}%"
                        )
        
        match_rate = (matching_checks / total_checks * 100) if total_checks > 0 else 0
        
        return match_rate, discrepancies
    
    def generate_accuracy_report(self, report: DataAccuracyReport) -> str:
        """生成准确率报告文本"""
        lines = [
            "=" * 60,
            "数据准确率验证报告",
            "=" * 60,
            f"验证时间: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            f"总记录数: {report.total_records}",
            f"检查字段数: {report.total_fields_checked}",
            "",
            f"总体准确率: {report.overall_accuracy:.2f}%",
            f"准确率等级: {report.accuracy_level.value}",
            f"是否达标: {'是' if report.meets_target else '否'} (目标: {self.target_accuracy}%)",
            "",
            "字段准确率详情:",
        ]
        
        for result in report.field_results:
            status = "✓" if result.is_accurate else "✗"
            lines.append(
                f"  {status} {result.field_name}: {result.accuracy_rate:.2f}% "
                f"({result.accurate_records}/{result.total_records})"
            )
        
        if report.issues_summary:
            lines.append("")
            lines.append("问题汇总:")
            for issue_type, count in report.issues_summary.items():
                lines.append(f"  - {issue_type}: {count}")
        
        if report.recommendations:
            lines.append("")
            lines.append("改进建议:")
            for rec in report.recommendations:
                lines.append(f"  - {rec}")
        
        lines.append("=" * 60)
        
        return "\n".join(lines)


# 全局实例
_accuracy_validator: Optional[DataAccuracyValidator] = None


def get_accuracy_validator() -> DataAccuracyValidator:
    """获取数据准确率验证器实例"""
    global _accuracy_validator
    if _accuracy_validator is None:
        _accuracy_validator = DataAccuracyValidator()
    return _accuracy_validator


def validate_data_accuracy(df: pd.DataFrame) -> DataAccuracyReport:
    """
    便捷函数：验证数据准确率
    
    Args:
        df: 待验证的数据
    
    Returns:
        DataAccuracyReport: 准确率报告
    """
    validator = get_accuracy_validator()
    return validator.validate_accuracy(df)
