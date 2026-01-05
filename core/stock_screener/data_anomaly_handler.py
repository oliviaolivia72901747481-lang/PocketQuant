"""
数据异常处理流程模块

提供数据异常的检测、分类、处理和恢复功能，包括：
- 异常类型分类和识别
- 异常处理策略定义
- 自动修复和人工审核流程
- 异常处理历史记录
- 多源数据交叉验证修复

Requirements: 7.2, 7.3, 7.4
风险缓解措施: 建立数据异常处理流程
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Tuple, Union
from enum import Enum
from datetime import datetime, timedelta
import logging
import json
import os
import pandas as pd
import numpy as np
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class AnomalyType(Enum):
    """异常类型"""
    MISSING_VALUE = "missing_value"           # 缺失值
    OUT_OF_RANGE = "out_of_range"             # 超出范围
    INVALID_FORMAT = "invalid_format"         # 格式无效
    INCONSISTENT = "inconsistent"             # 数据不一致
    DUPLICATE = "duplicate"                   # 重复数据
    OUTLIER = "outlier"                       # 异常值/离群点
    STALE_DATA = "stale_data"                 # 过期数据
    SOURCE_MISMATCH = "source_mismatch"       # 多源数据不匹配
    LOGIC_ERROR = "logic_error"               # 逻辑错误


class AnomalySeverity(Enum):
    """异常严重程度"""
    LOW = "low"           # 低 - 可忽略或自动修复
    MEDIUM = "medium"     # 中 - 需要关注，可自动处理
    HIGH = "high"         # 高 - 需要人工审核
    CRITICAL = "critical" # 严重 - 需要立即处理


class HandlingStrategy(Enum):
    """处理策略"""
    IGNORE = "ignore"                     # 忽略
    AUTO_FIX = "auto_fix"                 # 自动修复
    FILL_DEFAULT = "fill_default"         # 填充默认值
    FILL_MEDIAN = "fill_median"           # 填充中位数
    FILL_MEAN = "fill_mean"               # 填充均值
    INTERPOLATE = "interpolate"           # 插值
    REMOVE_RECORD = "remove_record"       # 移除记录
    FLAG_FOR_REVIEW = "flag_for_review"   # 标记待审核
    USE_BACKUP_SOURCE = "use_backup_source"  # 使用备用数据源
    MANUAL_REVIEW = "manual_review"       # 人工审核


class HandlingStatus(Enum):
    """处理状态"""
    PENDING = "pending"           # 待处理
    IN_PROGRESS = "in_progress"   # 处理中
    RESOLVED = "resolved"         # 已解决
    FAILED = "failed"             # 处理失败
    SKIPPED = "skipped"           # 已跳过
    MANUAL_REQUIRED = "manual_required"  # 需人工处理


@dataclass
class DataAnomaly:
    """数据异常记录"""
    anomaly_id: str
    anomaly_type: AnomalyType
    severity: AnomalySeverity
    field_name: str
    record_id: Optional[str] = None  # 股票代码或记录标识
    original_value: Any = None
    expected_range: Optional[Tuple[Any, Any]] = None
    description: str = ""
    detected_at: datetime = field(default_factory=datetime.now)
    handling_strategy: Optional[HandlingStrategy] = None
    handling_status: HandlingStatus = HandlingStatus.PENDING
    corrected_value: Any = None
    handled_at: Optional[datetime] = None
    handler_notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'anomaly_id': self.anomaly_id,
            'anomaly_type': self.anomaly_type.value,
            'severity': self.severity.value,
            'field_name': self.field_name,
            'record_id': self.record_id,
            'original_value': str(self.original_value) if self.original_value is not None else None,
            'expected_range': list(self.expected_range) if self.expected_range else None,
            'description': self.description,
            'detected_at': self.detected_at.isoformat(),
            'handling_strategy': self.handling_strategy.value if self.handling_strategy else None,
            'handling_status': self.handling_status.value,
            'corrected_value': str(self.corrected_value) if self.corrected_value is not None else None,
            'handled_at': self.handled_at.isoformat() if self.handled_at else None,
            'handler_notes': self.handler_notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DataAnomaly':
        """从字典创建"""
        return cls(
            anomaly_id=data['anomaly_id'],
            anomaly_type=AnomalyType(data['anomaly_type']),
            severity=AnomalySeverity(data['severity']),
            field_name=data['field_name'],
            record_id=data.get('record_id'),
            original_value=data.get('original_value'),
            expected_range=tuple(data['expected_range']) if data.get('expected_range') else None,
            description=data.get('description', ''),
            detected_at=datetime.fromisoformat(data['detected_at']),
            handling_strategy=HandlingStrategy(data['handling_strategy']) if data.get('handling_strategy') else None,
            handling_status=HandlingStatus(data['handling_status']),
            corrected_value=data.get('corrected_value'),
            handled_at=datetime.fromisoformat(data['handled_at']) if data.get('handled_at') else None,
            handler_notes=data.get('handler_notes', '')
        )


@dataclass
class AnomalyHandlingResult:
    """异常处理结果"""
    anomaly: DataAnomaly
    success: bool
    strategy_used: HandlingStrategy
    original_value: Any
    corrected_value: Any = None
    error_message: Optional[str] = None
    processing_time_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'anomaly_id': self.anomaly.anomaly_id,
            'success': self.success,
            'strategy_used': self.strategy_used.value,
            'original_value': str(self.original_value),
            'corrected_value': str(self.corrected_value) if self.corrected_value is not None else None,
            'error_message': self.error_message,
            'processing_time_ms': self.processing_time_ms
        }


@dataclass
class AnomalyHandlingConfig:
    """异常处理配置"""
    # 自动处理阈值
    auto_fix_threshold: AnomalySeverity = AnomalySeverity.MEDIUM
    
    # 字段特定策略
    field_strategies: Dict[str, HandlingStrategy] = field(default_factory=dict)
    
    # 类型特定策略
    type_strategies: Dict[AnomalyType, HandlingStrategy] = field(default_factory=dict)
    
    # 默认填充值
    default_values: Dict[str, Any] = field(default_factory=dict)
    
    # 是否启用多源验证修复
    enable_cross_source_fix: bool = True
    
    # 最大自动修复尝试次数
    max_auto_fix_attempts: int = 3
    
    # 是否记录所有处理历史
    log_all_handling: bool = True
    
    # 历史记录保留天数
    history_retention_days: int = 30
    
    def __post_init__(self):
        """初始化默认策略"""
        if not self.type_strategies:
            self.type_strategies = {
                AnomalyType.MISSING_VALUE: HandlingStrategy.FILL_MEDIAN,
                AnomalyType.OUT_OF_RANGE: HandlingStrategy.FLAG_FOR_REVIEW,
                AnomalyType.INVALID_FORMAT: HandlingStrategy.AUTO_FIX,
                AnomalyType.INCONSISTENT: HandlingStrategy.FLAG_FOR_REVIEW,
                AnomalyType.DUPLICATE: HandlingStrategy.REMOVE_RECORD,
                AnomalyType.OUTLIER: HandlingStrategy.FLAG_FOR_REVIEW,
                AnomalyType.STALE_DATA: HandlingStrategy.USE_BACKUP_SOURCE,
                AnomalyType.SOURCE_MISMATCH: HandlingStrategy.FLAG_FOR_REVIEW,
                AnomalyType.LOGIC_ERROR: HandlingStrategy.MANUAL_REVIEW,
            }
        
        if not self.default_values:
            self.default_values = {
                'pe_ratio': 0,
                'pb_ratio': 0,
                'roe': 0,
                'turnover_rate': 0,
            }
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'auto_fix_threshold': self.auto_fix_threshold.value,
            'field_strategies': {k: v.value for k, v in self.field_strategies.items()},
            'type_strategies': {k.value: v.value for k, v in self.type_strategies.items()},
            'default_values': self.default_values,
            'enable_cross_source_fix': self.enable_cross_source_fix,
            'max_auto_fix_attempts': self.max_auto_fix_attempts,
            'log_all_handling': self.log_all_handling,
            'history_retention_days': self.history_retention_days
        }



class AnomalyDetector:
    """
    异常检测器
    
    检测数据中的各类异常
    """
    
    # 数值字段有效范围
    FIELD_RANGES = {
        'price': {'min': 0.01, 'max': 10000},
        'close': {'min': 0.01, 'max': 10000},
        'open': {'min': 0.01, 'max': 10000},
        'high': {'min': 0.01, 'max': 10000},
        'low': {'min': 0.01, 'max': 10000},
        'change_pct': {'min': -20, 'max': 20},
        'turnover_rate': {'min': 0, 'max': 100},
        'pe_ratio': {'min': -10000, 'max': 100000},
        'pb_ratio': {'min': 0, 'max': 1000},
        'total_market_cap': {'min': 0, 'max': 1e15},
        'float_market_cap': {'min': 0, 'max': 1e15},
        'volume': {'min': 0, 'max': 1e13},
        'turnover': {'min': 0, 'max': 1e15},
        'roe': {'min': -500, 'max': 500},
        'roa': {'min': -200, 'max': 200},
        'gross_margin': {'min': -100, 'max': 100},
        'net_margin': {'min': -500, 'max': 500},
        'debt_ratio': {'min': 0, 'max': 300},
        'current_ratio': {'min': 0, 'max': 100},
    }
    
    # 必需字段
    REQUIRED_FIELDS = ['code', 'name']
    
    # 股票代码格式
    VALID_CODE_PATTERNS = [
        r'^000\d{3}$', r'^001\d{3}$', r'^002\d{3}$',
        r'^003\d{3}$', r'^300\d{3}$', r'^600\d{3}$',
        r'^601\d{3}$', r'^603\d{3}$', r'^605\d{3}$',
        r'^688\d{3}$'
    ]
    
    def __init__(self):
        self._anomaly_counter = 0
    
    def _generate_anomaly_id(self) -> str:
        """生成异常ID"""
        self._anomaly_counter += 1
        return f"ANO_{datetime.now().strftime('%Y%m%d%H%M%S')}_{self._anomaly_counter:04d}"
    
    def detect_anomalies(self, df: pd.DataFrame) -> List[DataAnomaly]:
        """
        检测数据中的所有异常
        
        Args:
            df: 待检测的数据
        
        Returns:
            检测到的异常列表
        """
        if df is None or df.empty:
            return []
        
        anomalies = []
        
        # 1. 检测缺失值
        anomalies.extend(self._detect_missing_values(df))
        
        # 2. 检测格式无效
        anomalies.extend(self._detect_invalid_format(df))
        
        # 3. 检测超出范围
        anomalies.extend(self._detect_out_of_range(df))
        
        # 4. 检测数据不一致
        anomalies.extend(self._detect_inconsistencies(df))
        
        # 5. 检测重复数据
        anomalies.extend(self._detect_duplicates(df))
        
        # 6. 检测异常值/离群点
        anomalies.extend(self._detect_outliers(df))
        
        # 7. 检测逻辑错误
        anomalies.extend(self._detect_logic_errors(df))
        
        logger.info(f"检测到 {len(anomalies)} 个数据异常")
        return anomalies
    
    def _detect_missing_values(self, df: pd.DataFrame) -> List[DataAnomaly]:
        """检测缺失值"""
        anomalies = []
        
        for field in self.REQUIRED_FIELDS:
            if field not in df.columns:
                continue
            
            missing_mask = df[field].isna() | (df[field].astype(str).str.strip() == '')
            missing_indices = df[missing_mask].index.tolist()
            
            for idx in missing_indices:
                record_id = df.loc[idx, 'code'] if 'code' in df.columns else str(idx)
                anomalies.append(DataAnomaly(
                    anomaly_id=self._generate_anomaly_id(),
                    anomaly_type=AnomalyType.MISSING_VALUE,
                    severity=AnomalySeverity.HIGH if field in ['code', 'name'] else AnomalySeverity.MEDIUM,
                    field_name=field,
                    record_id=str(record_id),
                    original_value=None,
                    description=f"必需字段 '{field}' 缺失"
                ))
        
        return anomalies
    
    def _detect_invalid_format(self, df: pd.DataFrame) -> List[DataAnomaly]:
        """检测格式无效"""
        import re
        anomalies = []
        
        if 'code' not in df.columns:
            return anomalies
        
        for idx, row in df.iterrows():
            code = row.get('code')
            if pd.isna(code):
                continue
            
            code_str = str(code).strip().zfill(6)
            is_valid = any(re.match(p, code_str) for p in self.VALID_CODE_PATTERNS)
            
            if not is_valid:
                anomalies.append(DataAnomaly(
                    anomaly_id=self._generate_anomaly_id(),
                    anomaly_type=AnomalyType.INVALID_FORMAT,
                    severity=AnomalySeverity.HIGH,
                    field_name='code',
                    record_id=code_str,
                    original_value=code,
                    description=f"股票代码格式无效: {code}"
                ))
        
        return anomalies
    
    def _detect_out_of_range(self, df: pd.DataFrame) -> List[DataAnomaly]:
        """检测超出范围的值"""
        anomalies = []
        
        for field, limits in self.FIELD_RANGES.items():
            if field not in df.columns:
                continue
            
            values = pd.to_numeric(df[field], errors='coerce')
            
            # 检测超出范围
            out_of_range_mask = (
                values.notna() & 
                ((values < limits['min']) | (values > limits['max']))
            )
            
            for idx in df[out_of_range_mask].index:
                record_id = df.loc[idx, 'code'] if 'code' in df.columns else str(idx)
                value = values.loc[idx]
                
                anomalies.append(DataAnomaly(
                    anomaly_id=self._generate_anomaly_id(),
                    anomaly_type=AnomalyType.OUT_OF_RANGE,
                    severity=AnomalySeverity.MEDIUM,
                    field_name=field,
                    record_id=str(record_id),
                    original_value=value,
                    expected_range=(limits['min'], limits['max']),
                    description=f"字段 '{field}' 值 {value} 超出有效范围 [{limits['min']}, {limits['max']}]"
                ))
        
        return anomalies
    
    def _detect_inconsistencies(self, df: pd.DataFrame) -> List[DataAnomaly]:
        """检测数据不一致"""
        anomalies = []
        
        # 检查市值一致性：流通市值不应大于总市值
        if 'total_market_cap' in df.columns and 'float_market_cap' in df.columns:
            inconsistent_mask = (
                df['float_market_cap'].notna() & 
                df['total_market_cap'].notna() &
                (df['float_market_cap'] > df['total_market_cap'] * 1.01)
            )
            
            for idx in df[inconsistent_mask].index:
                record_id = df.loc[idx, 'code'] if 'code' in df.columns else str(idx)
                anomalies.append(DataAnomaly(
                    anomaly_id=self._generate_anomaly_id(),
                    anomaly_type=AnomalyType.INCONSISTENT,
                    severity=AnomalySeverity.MEDIUM,
                    field_name='float_market_cap',
                    record_id=str(record_id),
                    original_value=df.loc[idx, 'float_market_cap'],
                    description=f"流通市值({df.loc[idx, 'float_market_cap']})大于总市值({df.loc[idx, 'total_market_cap']})"
                ))
        
        # 检查价格一致性：最高价应>=最低价
        if 'high' in df.columns and 'low' in df.columns:
            price_inconsistent = (
                df['high'].notna() & 
                df['low'].notna() &
                (df['high'] < df['low'])
            )
            
            for idx in df[price_inconsistent].index:
                record_id = df.loc[idx, 'code'] if 'code' in df.columns else str(idx)
                anomalies.append(DataAnomaly(
                    anomaly_id=self._generate_anomaly_id(),
                    anomaly_type=AnomalyType.INCONSISTENT,
                    severity=AnomalySeverity.HIGH,
                    field_name='high',
                    record_id=str(record_id),
                    original_value=df.loc[idx, 'high'],
                    description=f"最高价({df.loc[idx, 'high']})低于最低价({df.loc[idx, 'low']})"
                ))
        
        return anomalies
    
    def _detect_duplicates(self, df: pd.DataFrame) -> List[DataAnomaly]:
        """检测重复数据"""
        anomalies = []
        
        if 'code' not in df.columns:
            return anomalies
        
        duplicates = df[df.duplicated(subset=['code'], keep='first')]
        
        for idx in duplicates.index:
            record_id = df.loc[idx, 'code']
            anomalies.append(DataAnomaly(
                anomaly_id=self._generate_anomaly_id(),
                anomaly_type=AnomalyType.DUPLICATE,
                severity=AnomalySeverity.LOW,
                field_name='code',
                record_id=str(record_id),
                original_value=record_id,
                description=f"重复的股票代码: {record_id}"
            ))
        
        return anomalies
    
    def _detect_outliers(self, df: pd.DataFrame) -> List[DataAnomaly]:
        """检测异常值/离群点（使用IQR方法）"""
        anomalies = []
        outlier_fields = ['turnover_rate', 'change_pct', 'pe_ratio', 'pb_ratio']
        
        for field in outlier_fields:
            if field not in df.columns:
                continue
            
            values = pd.to_numeric(df[field], errors='coerce')
            valid_values = values.dropna()
            
            if len(valid_values) < 10:
                continue
            
            Q1 = valid_values.quantile(0.25)
            Q3 = valid_values.quantile(0.75)
            IQR = Q3 - Q1
            
            lower_bound = Q1 - 3 * IQR
            upper_bound = Q3 + 3 * IQR
            
            outlier_mask = (
                values.notna() &
                ((values < lower_bound) | (values > upper_bound))
            )
            
            for idx in df[outlier_mask].index:
                record_id = df.loc[idx, 'code'] if 'code' in df.columns else str(idx)
                value = values.loc[idx]
                
                anomalies.append(DataAnomaly(
                    anomaly_id=self._generate_anomaly_id(),
                    anomaly_type=AnomalyType.OUTLIER,
                    severity=AnomalySeverity.LOW,
                    field_name=field,
                    record_id=str(record_id),
                    original_value=value,
                    expected_range=(lower_bound, upper_bound),
                    description=f"字段 '{field}' 值 {value} 为离群点 (IQR范围: [{lower_bound:.2f}, {upper_bound:.2f}])"
                ))
        
        return anomalies
    
    def _detect_logic_errors(self, df: pd.DataFrame) -> List[DataAnomaly]:
        """检测逻辑错误"""
        anomalies = []
        
        # 检查开盘收盘价在高低价范围内
        if all(col in df.columns for col in ['open', 'close', 'high', 'low']):
            logic_error_mask = (
                df['open'].notna() & df['close'].notna() &
                df['high'].notna() & df['low'].notna() &
                ((df['open'] > df['high']) | (df['open'] < df['low']) |
                 (df['close'] > df['high']) | (df['close'] < df['low']))
            )
            
            for idx in df[logic_error_mask].index:
                record_id = df.loc[idx, 'code'] if 'code' in df.columns else str(idx)
                anomalies.append(DataAnomaly(
                    anomaly_id=self._generate_anomaly_id(),
                    anomaly_type=AnomalyType.LOGIC_ERROR,
                    severity=AnomalySeverity.HIGH,
                    field_name='price_range',
                    record_id=str(record_id),
                    original_value={
                        'open': df.loc[idx, 'open'],
                        'close': df.loc[idx, 'close'],
                        'high': df.loc[idx, 'high'],
                        'low': df.loc[idx, 'low']
                    },
                    description="开盘/收盘价超出高低价范围"
                ))
        
        return anomalies



class AnomalyHandler:
    """
    异常处理器
    
    根据配置的策略处理检测到的异常
    """
    
    def __init__(self, config: Optional[AnomalyHandlingConfig] = None):
        """
        初始化异常处理器
        
        Args:
            config: 处理配置
        """
        self.config = config or AnomalyHandlingConfig()
        self._handling_history: List[AnomalyHandlingResult] = []
    
    def handle_anomaly(
        self, 
        anomaly: DataAnomaly, 
        df: pd.DataFrame,
        backup_df: Optional[pd.DataFrame] = None
    ) -> AnomalyHandlingResult:
        """
        处理单个异常
        
        Args:
            anomaly: 异常记录
            df: 数据DataFrame
            backup_df: 备用数据源DataFrame
        
        Returns:
            处理结果
        """
        import time
        start_time = time.time()
        
        # 确定处理策略
        strategy = self._determine_strategy(anomaly)
        anomaly.handling_strategy = strategy
        anomaly.handling_status = HandlingStatus.IN_PROGRESS
        
        try:
            # 根据策略处理
            if strategy == HandlingStrategy.IGNORE:
                result = self._handle_ignore(anomaly)
            elif strategy == HandlingStrategy.AUTO_FIX:
                result = self._handle_auto_fix(anomaly, df)
            elif strategy == HandlingStrategy.FILL_DEFAULT:
                result = self._handle_fill_default(anomaly, df)
            elif strategy == HandlingStrategy.FILL_MEDIAN:
                result = self._handle_fill_median(anomaly, df)
            elif strategy == HandlingStrategy.FILL_MEAN:
                result = self._handle_fill_mean(anomaly, df)
            elif strategy == HandlingStrategy.INTERPOLATE:
                result = self._handle_interpolate(anomaly, df)
            elif strategy == HandlingStrategy.REMOVE_RECORD:
                result = self._handle_remove_record(anomaly, df)
            elif strategy == HandlingStrategy.FLAG_FOR_REVIEW:
                result = self._handle_flag_for_review(anomaly)
            elif strategy == HandlingStrategy.USE_BACKUP_SOURCE:
                result = self._handle_use_backup_source(anomaly, df, backup_df)
            elif strategy == HandlingStrategy.MANUAL_REVIEW:
                result = self._handle_manual_review(anomaly)
            else:
                result = self._handle_flag_for_review(anomaly)
            
            # 更新处理时间
            result.processing_time_ms = (time.time() - start_time) * 1000
            
            # 更新异常状态
            if result.success:
                anomaly.handling_status = HandlingStatus.RESOLVED
                anomaly.corrected_value = result.corrected_value
            else:
                anomaly.handling_status = HandlingStatus.FAILED
            
            anomaly.handled_at = datetime.now()
            
            # 记录历史
            if self.config.log_all_handling:
                self._handling_history.append(result)
            
            return result
            
        except Exception as e:
            logger.error(f"处理异常失败: {e}")
            anomaly.handling_status = HandlingStatus.FAILED
            anomaly.handled_at = datetime.now()
            
            return AnomalyHandlingResult(
                anomaly=anomaly,
                success=False,
                strategy_used=strategy,
                original_value=anomaly.original_value,
                error_message=str(e),
                processing_time_ms=(time.time() - start_time) * 1000
            )
    
    def handle_anomalies(
        self, 
        anomalies: List[DataAnomaly], 
        df: pd.DataFrame,
        backup_df: Optional[pd.DataFrame] = None
    ) -> Tuple[pd.DataFrame, List[AnomalyHandlingResult]]:
        """
        批量处理异常
        
        Args:
            anomalies: 异常列表
            df: 数据DataFrame
            backup_df: 备用数据源DataFrame
        
        Returns:
            Tuple[处理后的DataFrame, 处理结果列表]
        """
        results = []
        processed_df = df.copy()
        
        # 按严重程度排序，优先处理严重的
        sorted_anomalies = sorted(
            anomalies, 
            key=lambda a: list(AnomalySeverity).index(a.severity),
            reverse=True
        )
        
        for anomaly in sorted_anomalies:
            result = self.handle_anomaly(anomaly, processed_df, backup_df)
            results.append(result)
            
            # 如果处理成功且有修正值，更新DataFrame
            if result.success and result.corrected_value is not None:
                processed_df = self._apply_correction(
                    processed_df, 
                    anomaly, 
                    result.corrected_value
                )
        
        # 移除标记为删除的记录
        if '_to_remove' in processed_df.columns:
            processed_df = processed_df[processed_df['_to_remove'] != True]
            processed_df = processed_df.drop(columns=['_to_remove'], errors='ignore')
        
        logger.info(
            f"批量处理完成: {len(results)} 个异常, "
            f"成功 {sum(1 for r in results if r.success)} 个"
        )
        
        return processed_df, results
    
    def _determine_strategy(self, anomaly: DataAnomaly) -> HandlingStrategy:
        """确定处理策略"""
        # 1. 检查字段特定策略
        if anomaly.field_name in self.config.field_strategies:
            return self.config.field_strategies[anomaly.field_name]
        
        # 2. 检查类型特定策略
        if anomaly.anomaly_type in self.config.type_strategies:
            return self.config.type_strategies[anomaly.anomaly_type]
        
        # 3. 根据严重程度决定
        severity_order = list(AnomalySeverity)
        threshold_index = severity_order.index(self.config.auto_fix_threshold)
        anomaly_index = severity_order.index(anomaly.severity)
        
        if anomaly_index <= threshold_index:
            return HandlingStrategy.AUTO_FIX
        else:
            return HandlingStrategy.FLAG_FOR_REVIEW
    
    def _handle_ignore(self, anomaly: DataAnomaly) -> AnomalyHandlingResult:
        """忽略处理"""
        anomaly.handler_notes = "异常已忽略"
        return AnomalyHandlingResult(
            anomaly=anomaly,
            success=True,
            strategy_used=HandlingStrategy.IGNORE,
            original_value=anomaly.original_value
        )
    
    def _handle_auto_fix(
        self, 
        anomaly: DataAnomaly, 
        df: pd.DataFrame
    ) -> AnomalyHandlingResult:
        """自动修复"""
        corrected_value = None
        
        if anomaly.anomaly_type == AnomalyType.INVALID_FORMAT:
            # 尝试修复格式
            if anomaly.field_name == 'code':
                original = str(anomaly.original_value).strip()
                corrected_value = original.zfill(6)
                anomaly.handler_notes = f"代码格式已修复: {original} -> {corrected_value}"
        
        elif anomaly.anomaly_type == AnomalyType.OUT_OF_RANGE:
            # 裁剪到有效范围
            if anomaly.expected_range:
                min_val, max_val = anomaly.expected_range
                original = float(anomaly.original_value)
                corrected_value = max(min_val, min(max_val, original))
                anomaly.handler_notes = f"值已裁剪到有效范围: {original} -> {corrected_value}"
        
        return AnomalyHandlingResult(
            anomaly=anomaly,
            success=corrected_value is not None,
            strategy_used=HandlingStrategy.AUTO_FIX,
            original_value=anomaly.original_value,
            corrected_value=corrected_value,
            error_message=None if corrected_value else "无法自动修复"
        )
    
    def _handle_fill_default(
        self, 
        anomaly: DataAnomaly, 
        df: pd.DataFrame
    ) -> AnomalyHandlingResult:
        """填充默认值"""
        default_value = self.config.default_values.get(anomaly.field_name, 0)
        anomaly.handler_notes = f"已填充默认值: {default_value}"
        
        return AnomalyHandlingResult(
            anomaly=anomaly,
            success=True,
            strategy_used=HandlingStrategy.FILL_DEFAULT,
            original_value=anomaly.original_value,
            corrected_value=default_value
        )
    
    def _handle_fill_median(
        self, 
        anomaly: DataAnomaly, 
        df: pd.DataFrame
    ) -> AnomalyHandlingResult:
        """填充中位数"""
        if anomaly.field_name not in df.columns:
            return AnomalyHandlingResult(
                anomaly=anomaly,
                success=False,
                strategy_used=HandlingStrategy.FILL_MEDIAN,
                original_value=anomaly.original_value,
                error_message=f"字段 {anomaly.field_name} 不存在"
            )
        
        values = pd.to_numeric(df[anomaly.field_name], errors='coerce')
        median_value = values.median()
        
        if pd.isna(median_value):
            median_value = 0
        
        anomaly.handler_notes = f"已填充中位数: {median_value}"
        
        return AnomalyHandlingResult(
            anomaly=anomaly,
            success=True,
            strategy_used=HandlingStrategy.FILL_MEDIAN,
            original_value=anomaly.original_value,
            corrected_value=median_value
        )
    
    def _handle_fill_mean(
        self, 
        anomaly: DataAnomaly, 
        df: pd.DataFrame
    ) -> AnomalyHandlingResult:
        """填充均值"""
        if anomaly.field_name not in df.columns:
            return AnomalyHandlingResult(
                anomaly=anomaly,
                success=False,
                strategy_used=HandlingStrategy.FILL_MEAN,
                original_value=anomaly.original_value,
                error_message=f"字段 {anomaly.field_name} 不存在"
            )
        
        values = pd.to_numeric(df[anomaly.field_name], errors='coerce')
        mean_value = values.mean()
        
        if pd.isna(mean_value):
            mean_value = 0
        
        anomaly.handler_notes = f"已填充均值: {mean_value}"
        
        return AnomalyHandlingResult(
            anomaly=anomaly,
            success=True,
            strategy_used=HandlingStrategy.FILL_MEAN,
            original_value=anomaly.original_value,
            corrected_value=mean_value
        )
    
    def _handle_interpolate(
        self, 
        anomaly: DataAnomaly, 
        df: pd.DataFrame
    ) -> AnomalyHandlingResult:
        """插值处理"""
        if anomaly.field_name not in df.columns:
            return AnomalyHandlingResult(
                anomaly=anomaly,
                success=False,
                strategy_used=HandlingStrategy.INTERPOLATE,
                original_value=anomaly.original_value,
                error_message=f"字段 {anomaly.field_name} 不存在"
            )
        
        # 使用线性插值
        values = pd.to_numeric(df[anomaly.field_name], errors='coerce')
        interpolated = values.interpolate(method='linear')
        
        # 获取对应记录的插值结果
        if anomaly.record_id and 'code' in df.columns:
            mask = df['code'].astype(str) == str(anomaly.record_id)
            if mask.any():
                idx = df[mask].index[0]
                corrected_value = interpolated.loc[idx]
                anomaly.handler_notes = f"已插值: {corrected_value}"
                
                return AnomalyHandlingResult(
                    anomaly=anomaly,
                    success=True,
                    strategy_used=HandlingStrategy.INTERPOLATE,
                    original_value=anomaly.original_value,
                    corrected_value=corrected_value
                )
        
        return AnomalyHandlingResult(
            anomaly=anomaly,
            success=False,
            strategy_used=HandlingStrategy.INTERPOLATE,
            original_value=anomaly.original_value,
            error_message="无法找到对应记录进行插值"
        )
    
    def _handle_remove_record(
        self, 
        anomaly: DataAnomaly, 
        df: pd.DataFrame
    ) -> AnomalyHandlingResult:
        """移除记录"""
        if anomaly.record_id and 'code' in df.columns:
            mask = df['code'].astype(str) == str(anomaly.record_id)
            if mask.any():
                df.loc[mask, '_to_remove'] = True
                anomaly.handler_notes = f"记录已标记为删除: {anomaly.record_id}"
                
                return AnomalyHandlingResult(
                    anomaly=anomaly,
                    success=True,
                    strategy_used=HandlingStrategy.REMOVE_RECORD,
                    original_value=anomaly.original_value
                )
        
        return AnomalyHandlingResult(
            anomaly=anomaly,
            success=False,
            strategy_used=HandlingStrategy.REMOVE_RECORD,
            original_value=anomaly.original_value,
            error_message="无法找到要删除的记录"
        )
    
    def _handle_flag_for_review(self, anomaly: DataAnomaly) -> AnomalyHandlingResult:
        """标记待审核"""
        anomaly.handling_status = HandlingStatus.MANUAL_REQUIRED
        anomaly.handler_notes = "已标记待人工审核"
        
        return AnomalyHandlingResult(
            anomaly=anomaly,
            success=True,
            strategy_used=HandlingStrategy.FLAG_FOR_REVIEW,
            original_value=anomaly.original_value
        )
    
    def _handle_use_backup_source(
        self, 
        anomaly: DataAnomaly, 
        df: pd.DataFrame,
        backup_df: Optional[pd.DataFrame]
    ) -> AnomalyHandlingResult:
        """使用备用数据源"""
        if backup_df is None or backup_df.empty:
            return AnomalyHandlingResult(
                anomaly=anomaly,
                success=False,
                strategy_used=HandlingStrategy.USE_BACKUP_SOURCE,
                original_value=anomaly.original_value,
                error_message="无可用的备用数据源"
            )
        
        if anomaly.record_id and 'code' in backup_df.columns:
            mask = backup_df['code'].astype(str) == str(anomaly.record_id)
            if mask.any() and anomaly.field_name in backup_df.columns:
                backup_value = backup_df.loc[mask, anomaly.field_name].iloc[0]
                
                if pd.notna(backup_value):
                    anomaly.handler_notes = f"已从备用数据源获取值: {backup_value}"
                    
                    return AnomalyHandlingResult(
                        anomaly=anomaly,
                        success=True,
                        strategy_used=HandlingStrategy.USE_BACKUP_SOURCE,
                        original_value=anomaly.original_value,
                        corrected_value=backup_value
                    )
        
        return AnomalyHandlingResult(
            anomaly=anomaly,
            success=False,
            strategy_used=HandlingStrategy.USE_BACKUP_SOURCE,
            original_value=anomaly.original_value,
            error_message="备用数据源中无对应数据"
        )
    
    def _handle_manual_review(self, anomaly: DataAnomaly) -> AnomalyHandlingResult:
        """人工审核"""
        anomaly.handling_status = HandlingStatus.MANUAL_REQUIRED
        anomaly.handler_notes = "需要人工审核处理"
        
        return AnomalyHandlingResult(
            anomaly=anomaly,
            success=True,
            strategy_used=HandlingStrategy.MANUAL_REVIEW,
            original_value=anomaly.original_value
        )
    
    def _apply_correction(
        self, 
        df: pd.DataFrame, 
        anomaly: DataAnomaly, 
        corrected_value: Any
    ) -> pd.DataFrame:
        """应用修正值到DataFrame"""
        if anomaly.record_id and 'code' in df.columns:
            mask = df['code'].astype(str) == str(anomaly.record_id)
            if mask.any() and anomaly.field_name in df.columns:
                df.loc[mask, anomaly.field_name] = corrected_value
        
        return df
    
    def get_handling_history(self, limit: int = 100) -> List[AnomalyHandlingResult]:
        """获取处理历史"""
        return self._handling_history[-limit:]
    
    def get_handling_statistics(self) -> Dict[str, Any]:
        """获取处理统计"""
        total = len(self._handling_history)
        successful = sum(1 for r in self._handling_history if r.success)
        
        strategy_counts = {}
        for result in self._handling_history:
            strategy = result.strategy_used.value
            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
        
        return {
            'total_handled': total,
            'successful': successful,
            'failed': total - successful,
            'success_rate': (successful / total * 100) if total > 0 else 0,
            'by_strategy': strategy_counts,
            'avg_processing_time_ms': (
                sum(r.processing_time_ms for r in self._handling_history) / total
                if total > 0 else 0
            )
        }



class DataAnomalyWorkflow:
    """
    数据异常处理工作流
    
    提供完整的数据异常检测、处理和记录流程
    
    Requirements: 7.2, 7.3, 7.4
    风险缓解措施: 建立数据异常处理流程
    """
    
    def __init__(self, config: Optional[AnomalyHandlingConfig] = None):
        """
        初始化工作流
        
        Args:
            config: 处理配置
        """
        self.config = config or AnomalyHandlingConfig()
        self.detector = AnomalyDetector()
        self.handler = AnomalyHandler(self.config)
        
        # 异常记录
        self._anomalies: List[DataAnomaly] = []
        self._pending_review: List[DataAnomaly] = []
        
        # 持久化路径
        self._history_file = "data/anomaly_handling_history.json"
        self._pending_file = "data/anomaly_pending_review.json"
        
        # 加载历史
        self._load_history()
    
    def process_data(
        self, 
        df: pd.DataFrame,
        backup_df: Optional[pd.DataFrame] = None,
        auto_handle: bool = True
    ) -> Tuple[pd.DataFrame, List[DataAnomaly], List[AnomalyHandlingResult]]:
        """
        处理数据中的异常
        
        Args:
            df: 待处理的数据
            backup_df: 备用数据源
            auto_handle: 是否自动处理
        
        Returns:
            Tuple[处理后的DataFrame, 检测到的异常列表, 处理结果列表]
        """
        if df is None or df.empty:
            return df, [], []
        
        # 1. 检测异常
        anomalies = self.detector.detect_anomalies(df)
        self._anomalies.extend(anomalies)
        
        if not anomalies:
            logger.info("未检测到数据异常")
            return df, [], []
        
        logger.info(f"检测到 {len(anomalies)} 个数据异常")
        
        # 2. 处理异常
        results = []
        processed_df = df.copy()
        
        if auto_handle:
            processed_df, results = self.handler.handle_anomalies(
                anomalies, 
                processed_df, 
                backup_df
            )
            
            # 收集需要人工审核的异常
            for anomaly in anomalies:
                if anomaly.handling_status == HandlingStatus.MANUAL_REQUIRED:
                    self._pending_review.append(anomaly)
        else:
            # 不自动处理，全部标记待审核
            for anomaly in anomalies:
                anomaly.handling_status = HandlingStatus.PENDING
                self._pending_review.append(anomaly)
        
        # 3. 保存历史
        self._save_history()
        
        return processed_df, anomalies, results
    
    def get_pending_review(self) -> List[DataAnomaly]:
        """获取待审核的异常"""
        return [a for a in self._pending_review if a.handling_status == HandlingStatus.MANUAL_REQUIRED]
    
    def review_anomaly(
        self, 
        anomaly_id: str, 
        action: str,
        corrected_value: Any = None,
        notes: str = ""
    ) -> bool:
        """
        人工审核异常
        
        Args:
            anomaly_id: 异常ID
            action: 操作 ('approve', 'reject', 'fix')
            corrected_value: 修正值（当action='fix'时）
            notes: 审核备注
        
        Returns:
            是否成功
        """
        for anomaly in self._pending_review:
            if anomaly.anomaly_id == anomaly_id:
                if action == 'approve':
                    anomaly.handling_status = HandlingStatus.RESOLVED
                    anomaly.handler_notes = f"人工审核通过: {notes}"
                elif action == 'reject':
                    anomaly.handling_status = HandlingStatus.SKIPPED
                    anomaly.handler_notes = f"人工审核拒绝: {notes}"
                elif action == 'fix':
                    anomaly.handling_status = HandlingStatus.RESOLVED
                    anomaly.corrected_value = corrected_value
                    anomaly.handler_notes = f"人工修复: {notes}"
                
                anomaly.handled_at = datetime.now()
                self._save_history()
                return True
        
        return False
    
    def get_anomaly_summary(self) -> Dict[str, Any]:
        """获取异常摘要"""
        total = len(self._anomalies)
        
        by_type = {}
        by_severity = {}
        by_status = {}
        
        for anomaly in self._anomalies:
            # 按类型统计
            type_key = anomaly.anomaly_type.value
            by_type[type_key] = by_type.get(type_key, 0) + 1
            
            # 按严重程度统计
            severity_key = anomaly.severity.value
            by_severity[severity_key] = by_severity.get(severity_key, 0) + 1
            
            # 按状态统计
            status_key = anomaly.handling_status.value
            by_status[status_key] = by_status.get(status_key, 0) + 1
        
        return {
            'total_anomalies': total,
            'pending_review': len(self.get_pending_review()),
            'by_type': by_type,
            'by_severity': by_severity,
            'by_status': by_status,
            'handling_statistics': self.handler.get_handling_statistics()
        }
    
    def generate_report(self) -> str:
        """生成异常处理报告"""
        summary = self.get_anomaly_summary()
        
        lines = [
            "=" * 60,
            "数据异常处理报告",
            "=" * 60,
            f"报告时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "【异常统计】",
            f"  总异常数: {summary['total_anomalies']}",
            f"  待审核数: {summary['pending_review']}",
            "",
            "【按类型分布】",
        ]
        
        for type_name, count in summary['by_type'].items():
            lines.append(f"  - {type_name}: {count}")
        
        lines.extend([
            "",
            "【按严重程度分布】",
        ])
        
        for severity, count in summary['by_severity'].items():
            lines.append(f"  - {severity}: {count}")
        
        lines.extend([
            "",
            "【按处理状态分布】",
        ])
        
        for status, count in summary['by_status'].items():
            lines.append(f"  - {status}: {count}")
        
        handling_stats = summary['handling_statistics']
        lines.extend([
            "",
            "【处理统计】",
            f"  总处理数: {handling_stats['total_handled']}",
            f"  成功数: {handling_stats['successful']}",
            f"  失败数: {handling_stats['failed']}",
            f"  成功率: {handling_stats['success_rate']:.1f}%",
            f"  平均处理时间: {handling_stats['avg_processing_time_ms']:.2f}ms",
        ])
        
        # 显示待审核异常
        pending = self.get_pending_review()
        if pending:
            lines.extend([
                "",
                "【待审核异常】",
            ])
            for anomaly in pending[:10]:
                lines.append(
                    f"  [{anomaly.anomaly_id}] {anomaly.anomaly_type.value} - "
                    f"{anomaly.field_name}: {anomaly.description[:50]}"
                )
            if len(pending) > 10:
                lines.append(f"  ... 还有 {len(pending) - 10} 条待审核")
        
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def _load_history(self):
        """加载历史记录"""
        try:
            if os.path.exists(self._history_file):
                with open(self._history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for item in data[-500:]:  # 只加载最近500条
                        self._anomalies.append(DataAnomaly.from_dict(item))
        except Exception as e:
            logger.debug(f"加载异常历史失败: {e}")
        
        try:
            if os.path.exists(self._pending_file):
                with open(self._pending_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for item in data:
                        self._pending_review.append(DataAnomaly.from_dict(item))
        except Exception as e:
            logger.debug(f"加载待审核列表失败: {e}")
    
    def _save_history(self):
        """保存历史记录"""
        try:
            os.makedirs(os.path.dirname(self._history_file), exist_ok=True)
            
            # 保存异常历史
            with open(self._history_file, 'w', encoding='utf-8') as f:
                json.dump(
                    [a.to_dict() for a in self._anomalies[-500:]],
                    f, ensure_ascii=False, indent=2
                )
            
            # 保存待审核列表
            pending = self.get_pending_review()
            with open(self._pending_file, 'w', encoding='utf-8') as f:
                json.dump(
                    [a.to_dict() for a in pending],
                    f, ensure_ascii=False, indent=2
                )
        except Exception as e:
            logger.warning(f"保存异常历史失败: {e}")
    
    def clear_history(self, days: Optional[int] = None):
        """
        清理历史记录
        
        Args:
            days: 保留最近N天的记录，None表示清除所有
        """
        if days is None:
            self._anomalies = []
            self._pending_review = []
        else:
            cutoff = datetime.now() - timedelta(days=days)
            self._anomalies = [
                a for a in self._anomalies 
                if a.detected_at >= cutoff
            ]
            self._pending_review = [
                a for a in self._pending_review 
                if a.detected_at >= cutoff
            ]
        
        self._save_history()
        logger.info(f"已清理异常历史记录")


# 全局实例
_anomaly_workflow: Optional[DataAnomalyWorkflow] = None


def get_anomaly_workflow(
    config: Optional[AnomalyHandlingConfig] = None
) -> DataAnomalyWorkflow:
    """
    获取异常处理工作流实例
    
    Args:
        config: 处理配置
    
    Returns:
        DataAnomalyWorkflow: 工作流实例
    """
    global _anomaly_workflow
    if _anomaly_workflow is None:
        _anomaly_workflow = DataAnomalyWorkflow(config)
    return _anomaly_workflow


def reset_anomaly_workflow() -> None:
    """重置异常处理工作流"""
    global _anomaly_workflow
    _anomaly_workflow = None


def process_data_anomalies(
    df: pd.DataFrame,
    backup_df: Optional[pd.DataFrame] = None,
    auto_handle: bool = True
) -> Tuple[pd.DataFrame, List[DataAnomaly], List[AnomalyHandlingResult]]:
    """
    便捷函数：处理数据异常
    
    Args:
        df: 待处理的数据
        backup_df: 备用数据源
        auto_handle: 是否自动处理
    
    Returns:
        Tuple[处理后的DataFrame, 检测到的异常列表, 处理结果列表]
    """
    workflow = get_anomaly_workflow()
    return workflow.process_data(df, backup_df, auto_handle)


def get_anomaly_summary() -> Dict[str, Any]:
    """
    便捷函数：获取异常摘要
    
    Returns:
        异常摘要字典
    """
    workflow = get_anomaly_workflow()
    return workflow.get_anomaly_summary()


def generate_anomaly_report() -> str:
    """
    便捷函数：生成异常处理报告
    
    Returns:
        报告文本
    """
    workflow = get_anomaly_workflow()
    return workflow.generate_report()


def review_pending_anomaly(
    anomaly_id: str,
    action: str,
    corrected_value: Any = None,
    notes: str = ""
) -> bool:
    """
    便捷函数：审核待处理异常
    
    Args:
        anomaly_id: 异常ID
        action: 操作 ('approve', 'reject', 'fix')
        corrected_value: 修正值
        notes: 审核备注
    
    Returns:
        是否成功
    """
    workflow = get_anomaly_workflow()
    return workflow.review_anomaly(anomaly_id, action, corrected_value, notes)
