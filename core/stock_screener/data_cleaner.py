"""
数据清洗和验证系统

提供股票数据的清洗和验证功能，包括：
- 数据完整性检查
- 异常值检测和处理
- 数据质量评分机制

Requirements: 7.2, 7.3
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from datetime import datetime
import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class DataQualityLevel(Enum):
    """数据质量等级"""
    EXCELLENT = "excellent"  # 优秀 (90-100分)
    GOOD = "good"           # 良好 (75-89分)
    ACCEPTABLE = "acceptable"  # 可接受 (60-74分)
    POOR = "poor"           # 较差 (40-59分)
    UNACCEPTABLE = "unacceptable"  # 不可接受 (<40分)


@dataclass
class DataValidationResult:
    """数据验证结果"""
    is_valid: bool
    field_name: str
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    original_value: Any = None
    corrected_value: Any = None


@dataclass
class DataQualityReport:
    """数据质量报告"""
    total_records: int
    valid_records: int
    invalid_records: int
    quality_score: float
    quality_level: DataQualityLevel
    completeness_score: float  # 完整性得分
    accuracy_score: float      # 准确性得分
    consistency_score: float   # 一致性得分
    validation_results: List[DataValidationResult] = field(default_factory=list)
    field_quality: Dict[str, float] = field(default_factory=dict)
    issues_summary: Dict[str, int] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


class DataCleaner:
    """
    数据清洗器
    
    提供股票数据的清洗和验证功能
    
    Requirements: 7.2, 7.3
    """
    
    # 必需字段定义
    REQUIRED_FIELDS = ['code', 'name', 'price']
    
    # 数值字段定义及其有效范围
    NUMERIC_FIELDS = {
        'price': {'min': 0.01, 'max': 10000},
        'change_pct': {'min': -20, 'max': 20},  # 涨跌停限制
        'turnover_rate': {'min': 0, 'max': 100},
        'pe_ratio': {'min': -1000, 'max': 10000},
        'pb_ratio': {'min': 0, 'max': 1000},
        'total_market_cap': {'min': 0, 'max': 1e14},  # 最大10万亿
        'float_market_cap': {'min': 0, 'max': 1e14},
        'volume': {'min': 0, 'max': 1e12},
        'turnover': {'min': 0, 'max': 1e14},
    }
    
    # 股票代码格式
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
    
    def __init__(self):
        """初始化数据清洗器"""
        self._validation_results: List[DataValidationResult] = []
        self._issues_count: Dict[str, int] = {}
    
    def clean_stock_data(
        self, 
        df: pd.DataFrame,
        remove_invalid: bool = True,
        fill_missing: bool = True
    ) -> Tuple[pd.DataFrame, DataQualityReport]:
        """
        清洗股票数据
        
        Args:
            df: 原始数据DataFrame
            remove_invalid: 是否移除无效记录
            fill_missing: 是否填充缺失值
        
        Returns:
            Tuple[清洗后的DataFrame, 数据质量报告]
        """
        if df is None or df.empty:
            return pd.DataFrame(), self._create_empty_report()
        
        self._validation_results = []
        self._issues_count = {}
        
        original_count = len(df)
        cleaned_df = df.copy()
        
        # 1. 检查必需字段
        cleaned_df = self._check_required_fields(cleaned_df)
        
        # 2. 清洗股票代码
        cleaned_df = self._clean_stock_codes(cleaned_df)
        
        # 3. 清洗数值字段
        cleaned_df = self._clean_numeric_fields(cleaned_df, fill_missing)
        
        # 4. 检测和处理异常值
        cleaned_df = self._handle_outliers(cleaned_df)
        
        # 5. 移除ST股票（可选）
        cleaned_df = self._filter_st_stocks(cleaned_df)
        
        # 6. 移除无效记录
        if remove_invalid:
            cleaned_df = self._remove_invalid_records(cleaned_df)
        
        # 7. 生成质量报告
        report = self._generate_quality_report(
            original_count=original_count,
            cleaned_df=cleaned_df
        )
        
        logger.info(
            f"数据清洗完成: 原始 {original_count} 条, "
            f"有效 {report.valid_records} 条, "
            f"质量得分 {report.quality_score:.1f}"
        )
        
        return cleaned_df, report
    
    def _check_required_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """检查必需字段"""
        for field in self.REQUIRED_FIELDS:
            if field not in df.columns:
                self._add_issue('missing_required_field', field)
                df[field] = None
        
        return df
    
    def _clean_stock_codes(self, df: pd.DataFrame) -> pd.DataFrame:
        """清洗股票代码"""
        if 'code' not in df.columns:
            return df
        
        import re
        
        def validate_code(code):
            if pd.isna(code):
                return False
            code_str = str(code).strip()
            for pattern in self.VALID_CODE_PATTERNS:
                if re.match(pattern, code_str):
                    return True
            return False
        
        # 标准化代码格式
        df['code'] = df['code'].astype(str).str.strip()
        df['code'] = df['code'].str.zfill(6)  # 补齐6位
        
        # 标记无效代码
        invalid_mask = ~df['code'].apply(validate_code)
        invalid_count = invalid_mask.sum()
        
        if invalid_count > 0:
            self._add_issue('invalid_stock_code', count=invalid_count)
            df.loc[invalid_mask, '_invalid'] = True
        
        return df
    
    def _clean_numeric_fields(
        self, 
        df: pd.DataFrame, 
        fill_missing: bool
    ) -> pd.DataFrame:
        """清洗数值字段"""
        for field, limits in self.NUMERIC_FIELDS.items():
            if field not in df.columns:
                continue
            
            # 转换为数值类型
            df[field] = pd.to_numeric(df[field], errors='coerce')
            
            # 统计缺失值
            missing_count = df[field].isna().sum()
            if missing_count > 0:
                self._add_issue(f'missing_{field}', count=missing_count)
            
            # 填充缺失值
            if fill_missing and missing_count > 0:
                if field in ['pe_ratio', 'pb_ratio']:
                    # 估值指标使用中位数填充
                    median_val = df[field].median()
                    df[field] = df[field].fillna(median_val)
                elif field in ['price', 'total_market_cap', 'float_market_cap']:
                    # 价格和市值不填充，标记为无效
                    pass
                else:
                    # 其他字段使用0填充
                    df[field] = df[field].fillna(0)
            
            # 检查范围
            out_of_range = (
                (df[field] < limits['min']) | 
                (df[field] > limits['max'])
            ) & df[field].notna()
            
            out_of_range_count = out_of_range.sum()
            if out_of_range_count > 0:
                self._add_issue(f'out_of_range_{field}', count=out_of_range_count)
        
        return df
    
    def _handle_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        """检测和处理异常值"""
        outlier_fields = ['turnover_rate', 'volume_ratio', 'change_pct']
        
        for field in outlier_fields:
            if field not in df.columns:
                continue
            
            # 使用IQR方法检测异常值
            Q1 = df[field].quantile(0.25)
            Q3 = df[field].quantile(0.75)
            IQR = Q3 - Q1
            
            lower_bound = Q1 - 3 * IQR
            upper_bound = Q3 + 3 * IQR
            
            outliers = (
                (df[field] < lower_bound) | 
                (df[field] > upper_bound)
            ) & df[field].notna()
            
            outlier_count = outliers.sum()
            if outlier_count > 0:
                self._add_issue(f'outlier_{field}', count=outlier_count)
                # 标记异常值但不移除
                df.loc[outliers, f'_outlier_{field}'] = True
        
        return df
    
    def _filter_st_stocks(self, df: pd.DataFrame) -> pd.DataFrame:
        """过滤ST股票"""
        if 'name' not in df.columns:
            return df
        
        st_mask = df['name'].str.contains('ST', na=False, case=False)
        st_count = st_mask.sum()
        
        if st_count > 0:
            self._add_issue('st_stocks', count=st_count)
            df.loc[st_mask, '_is_st'] = True
        
        return df
    
    def _remove_invalid_records(self, df: pd.DataFrame) -> pd.DataFrame:
        """移除无效记录"""
        # 移除缺少必需字段的记录
        for field in self.REQUIRED_FIELDS:
            if field in df.columns:
                df = df[df[field].notna()]
        
        # 移除标记为无效的记录
        if '_invalid' in df.columns:
            df = df[df['_invalid'] != True]
            df = df.drop(columns=['_invalid'], errors='ignore')
        
        return df
    
    def _add_issue(self, issue_type: str, field: str = None, count: int = 1):
        """添加问题记录"""
        key = f"{issue_type}:{field}" if field else issue_type
        self._issues_count[key] = self._issues_count.get(key, 0) + count
    
    def _generate_quality_report(
        self, 
        original_count: int, 
        cleaned_df: pd.DataFrame
    ) -> DataQualityReport:
        """生成数据质量报告"""
        valid_count = len(cleaned_df)
        invalid_count = original_count - valid_count
        
        # 计算各维度得分
        completeness_score = self._calculate_completeness_score(cleaned_df)
        accuracy_score = self._calculate_accuracy_score(cleaned_df)
        consistency_score = self._calculate_consistency_score(cleaned_df)
        
        # 综合质量得分
        quality_score = (
            completeness_score * 0.4 +
            accuracy_score * 0.35 +
            consistency_score * 0.25
        )
        
        # 确定质量等级
        quality_level = self._determine_quality_level(quality_score)
        
        # 字段质量评估
        field_quality = self._calculate_field_quality(cleaned_df)
        
        # 生成建议
        recommendations = self._generate_recommendations(
            quality_score, 
            completeness_score, 
            accuracy_score
        )
        
        return DataQualityReport(
            total_records=original_count,
            valid_records=valid_count,
            invalid_records=invalid_count,
            quality_score=quality_score,
            quality_level=quality_level,
            completeness_score=completeness_score,
            accuracy_score=accuracy_score,
            consistency_score=consistency_score,
            validation_results=self._validation_results,
            field_quality=field_quality,
            issues_summary=self._issues_count,
            recommendations=recommendations
        )
    
    def _calculate_completeness_score(self, df: pd.DataFrame) -> float:
        """计算完整性得分"""
        if df.empty:
            return 0.0
        
        total_cells = len(df) * len(df.columns)
        missing_cells = df.isna().sum().sum()
        
        completeness = (total_cells - missing_cells) / total_cells * 100
        return min(100, completeness)
    
    def _calculate_accuracy_score(self, df: pd.DataFrame) -> float:
        """计算准确性得分"""
        if df.empty:
            return 0.0
        
        # 基于异常值和范围外数据计算
        total_issues = sum(
            count for key, count in self._issues_count.items()
            if 'outlier' in key or 'out_of_range' in key
        )
        
        total_records = len(df)
        if total_records == 0:
            return 100.0
        
        accuracy = max(0, 100 - (total_issues / total_records * 100))
        return accuracy
    
    def _calculate_consistency_score(self, df: pd.DataFrame) -> float:
        """计算一致性得分"""
        if df.empty:
            return 0.0
        
        # 检查数据一致性（如市值与价格的关系）
        consistency_issues = 0
        
        if 'total_market_cap' in df.columns and 'float_market_cap' in df.columns:
            # 流通市值不应大于总市值
            inconsistent = df['float_market_cap'] > df['total_market_cap']
            consistency_issues += inconsistent.sum()
        
        total_records = len(df)
        if total_records == 0:
            return 100.0
        
        consistency = max(0, 100 - (consistency_issues / total_records * 100))
        return consistency
    
    def _determine_quality_level(self, score: float) -> DataQualityLevel:
        """确定质量等级"""
        if score >= 90:
            return DataQualityLevel.EXCELLENT
        elif score >= 75:
            return DataQualityLevel.GOOD
        elif score >= 60:
            return DataQualityLevel.ACCEPTABLE
        elif score >= 40:
            return DataQualityLevel.POOR
        else:
            return DataQualityLevel.UNACCEPTABLE
    
    def _calculate_field_quality(self, df: pd.DataFrame) -> Dict[str, float]:
        """计算各字段质量得分"""
        field_quality = {}
        
        for col in df.columns:
            if col.startswith('_'):
                continue
            
            missing_rate = df[col].isna().sum() / len(df) if len(df) > 0 else 0
            field_quality[col] = max(0, 100 - missing_rate * 100)
        
        return field_quality
    
    def _generate_recommendations(
        self, 
        quality_score: float,
        completeness_score: float,
        accuracy_score: float
    ) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        if completeness_score < 80:
            recommendations.append("建议检查数据源，存在较多缺失值")
        
        if accuracy_score < 80:
            recommendations.append("建议验证数据准确性，存在异常值或范围外数据")
        
        if quality_score < 60:
            recommendations.append("数据质量较差，建议使用备用数据源或人工审核")
        
        if 'st_stocks' in self._issues_count:
            recommendations.append(f"发现 {self._issues_count['st_stocks']} 只ST股票，已标记")
        
        return recommendations
    
    def _create_empty_report(self) -> DataQualityReport:
        """创建空报告"""
        return DataQualityReport(
            total_records=0,
            valid_records=0,
            invalid_records=0,
            quality_score=0.0,
            quality_level=DataQualityLevel.UNACCEPTABLE,
            completeness_score=0.0,
            accuracy_score=0.0,
            consistency_score=0.0,
            recommendations=["无数据可供分析"]
        )
    
    def validate_single_record(
        self, 
        record: Dict[str, Any]
    ) -> List[DataValidationResult]:
        """
        验证单条记录
        
        Args:
            record: 股票数据记录
        
        Returns:
            验证结果列表
        """
        results = []
        
        # 检查必需字段
        for field in self.REQUIRED_FIELDS:
            if field not in record or record[field] is None:
                results.append(DataValidationResult(
                    is_valid=False,
                    field_name=field,
                    error_type='missing_required',
                    error_message=f"缺少必需字段: {field}"
                ))
        
        # 检查数值范围
        for field, limits in self.NUMERIC_FIELDS.items():
            if field in record and record[field] is not None:
                value = record[field]
                if value < limits['min'] or value > limits['max']:
                    results.append(DataValidationResult(
                        is_valid=False,
                        field_name=field,
                        error_type='out_of_range',
                        error_message=f"{field} 值 {value} 超出有效范围 [{limits['min']}, {limits['max']}]",
                        original_value=value
                    ))
        
        return results
    
    def filter_mainboard_stocks(
        self, 
        df: pd.DataFrame,
        include_sme: bool = True
    ) -> pd.DataFrame:
        """
        过滤主板和中小板股票
        
        Args:
            df: 股票数据DataFrame
            include_sme: 是否包含中小板(002)
        
        Returns:
            过滤后的DataFrame
        """
        if df is None or df.empty or 'code' not in df.columns:
            return pd.DataFrame()
        
        # 主板代码模式
        patterns = [
            r'^000\d{3}$',  # 深圳主板
            r'^001\d{3}$',  # 深圳主板
            r'^600\d{3}$',  # 上海主板
            r'^601\d{3}$',  # 上海主板
            r'^603\d{3}$',  # 上海主板
            r'^605\d{3}$',  # 上海主板
        ]
        
        if include_sme:
            patterns.append(r'^002\d{3}$')  # 中小板
        
        import re
        combined_pattern = '|'.join(f'({p})' for p in patterns)
        
        mask = df['code'].str.match(combined_pattern, na=False)
        filtered_df = df[mask].copy()
        
        logger.info(f"过滤后保留 {len(filtered_df)} 只主板/中小板股票")
        return filtered_df
    
    def remove_st_stocks(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        移除ST股票
        
        Args:
            df: 股票数据DataFrame
        
        Returns:
            移除ST后的DataFrame
        """
        if df is None or df.empty or 'name' not in df.columns:
            return df
        
        st_mask = df['name'].str.contains('ST|\\*ST|S\\*ST', na=False, case=False, regex=True)
        removed_count = st_mask.sum()
        
        if removed_count > 0:
            logger.info(f"移除 {removed_count} 只ST股票")
        
        return df[~st_mask].copy()
    
    def remove_new_stocks(
        self, 
        df: pd.DataFrame, 
        min_days: int = 60
    ) -> pd.DataFrame:
        """
        移除上市时间不足的新股
        
        Args:
            df: 股票数据DataFrame
            min_days: 最小上市天数
        
        Returns:
            移除新股后的DataFrame
        """
        if df is None or df.empty:
            return df
        
        # 如果有上市日期字段
        if 'list_date' in df.columns:
            from datetime import datetime, timedelta
            cutoff_date = datetime.now() - timedelta(days=min_days)
            
            df['list_date'] = pd.to_datetime(df['list_date'], errors='coerce')
            mask = df['list_date'] <= cutoff_date
            removed_count = (~mask).sum()
            
            if removed_count > 0:
                logger.info(f"移除 {removed_count} 只上市不足 {min_days} 天的新股")
            
            return df[mask].copy()
        
        return df
    
    def get_quality_summary(self, report: DataQualityReport) -> str:
        """
        生成数据质量摘要文本
        
        Args:
            report: 数据质量报告
        
        Returns:
            摘要文本
        """
        summary_lines = [
            f"数据质量报告摘要",
            f"=" * 40,
            f"总记录数: {report.total_records}",
            f"有效记录: {report.valid_records}",
            f"无效记录: {report.invalid_records}",
            f"",
            f"质量得分: {report.quality_score:.1f}/100 ({report.quality_level.value})",
            f"  - 完整性: {report.completeness_score:.1f}",
            f"  - 准确性: {report.accuracy_score:.1f}",
            f"  - 一致性: {report.consistency_score:.1f}",
        ]
        
        if report.issues_summary:
            summary_lines.append("")
            summary_lines.append("发现的问题:")
            for issue, count in report.issues_summary.items():
                summary_lines.append(f"  - {issue}: {count}")
        
        if report.recommendations:
            summary_lines.append("")
            summary_lines.append("建议:")
            for rec in report.recommendations:
                summary_lines.append(f"  - {rec}")
        
        return "\n".join(summary_lines)


# 全局数据清洗器实例
_data_cleaner: Optional[DataCleaner] = None


def get_data_cleaner() -> DataCleaner:
    """
    获取数据清洗器实例（单例模式）
    
    Returns:
        DataCleaner: 数据清洗器实例
    """
    global _data_cleaner
    if _data_cleaner is None:
        _data_cleaner = DataCleaner()
    return _data_cleaner
