"""
性能优化模块

提供筛选性能优化功能，包括：
- 数据获取和处理速度优化
- 并行处理和缓存机制
- 筛选过程性能监控
- 结果质量优化

Requirements: 技术约束, 成功标准
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Callable
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import time
import functools
import hashlib
import json
import os

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """性能指标"""
    operation: str
    start_time: datetime
    end_time: datetime
    duration_ms: float
    records_processed: int = 0
    success: bool = True
    error_message: Optional[str] = None
    
    @property
    def records_per_second(self) -> float:
        """每秒处理记录数"""
        if self.duration_ms <= 0:
            return 0
        return self.records_processed / (self.duration_ms / 1000)


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    data: Any
    created_at: datetime
    expires_at: datetime
    hit_count: int = 0
    
    @property
    def is_expired(self) -> bool:
        """是否已过期"""
        return datetime.now() > self.expires_at


class PerformanceMonitor:
    """
    性能监控器
    
    监控筛选过程的性能指标
    """
    
    def __init__(self):
        """初始化性能监控器"""
        self.metrics: List[PerformanceMetrics] = []
        self._current_operation: Optional[str] = None
        self._start_time: Optional[datetime] = None
    
    def start_operation(self, operation: str):
        """开始操作计时"""
        self._current_operation = operation
        self._start_time = datetime.now()
    
    def end_operation(
        self, 
        records_processed: int = 0, 
        success: bool = True,
        error_message: Optional[str] = None
    ) -> PerformanceMetrics:
        """结束操作计时"""
        if self._start_time is None:
            raise ValueError("No operation started")
        
        end_time = datetime.now()
        duration_ms = (end_time - self._start_time).total_seconds() * 1000
        
        metrics = PerformanceMetrics(
            operation=self._current_operation or "unknown",
            start_time=self._start_time,
            end_time=end_time,
            duration_ms=duration_ms,
            records_processed=records_processed,
            success=success,
            error_message=error_message
        )
        
        self.metrics.append(metrics)
        self._current_operation = None
        self._start_time = None
        
        return metrics
    
    def get_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        if not self.metrics:
            return {'total_operations': 0}
        
        total_duration = sum(m.duration_ms for m in self.metrics)
        total_records = sum(m.records_processed for m in self.metrics)
        success_count = sum(1 for m in self.metrics if m.success)
        
        # 按操作类型分组
        by_operation = {}
        for m in self.metrics:
            if m.operation not in by_operation:
                by_operation[m.operation] = {
                    'count': 0,
                    'total_duration_ms': 0,
                    'total_records': 0
                }
            by_operation[m.operation]['count'] += 1
            by_operation[m.operation]['total_duration_ms'] += m.duration_ms
            by_operation[m.operation]['total_records'] += m.records_processed
        
        return {
            'total_operations': len(self.metrics),
            'total_duration_ms': total_duration,
            'total_records': total_records,
            'success_rate': success_count / len(self.metrics) * 100,
            'avg_duration_ms': total_duration / len(self.metrics),
            'by_operation': by_operation
        }
    
    def clear(self):
        """清除所有指标"""
        self.metrics.clear()


class DataCache:
    """
    数据缓存
    
    提供数据缓存功能以提高性能
    """
    
    def __init__(
        self, 
        max_size: int = 100,
        default_ttl_minutes: int = 30
    ):
        """
        初始化数据缓存
        
        Args:
            max_size: 最大缓存条目数
            default_ttl_minutes: 默认过期时间（分钟）
        """
        self.max_size = max_size
        self.default_ttl = timedelta(minutes=default_ttl_minutes)
        self._cache: Dict[str, CacheEntry] = {}
        self._hit_count = 0
        self._miss_count = 0
    
    def _generate_key(self, *args, **kwargs) -> str:
        """生成缓存键"""
        key_data = json.dumps({'args': str(args), 'kwargs': str(kwargs)}, sort_keys=True)
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存数据"""
        if key in self._cache:
            entry = self._cache[key]
            if not entry.is_expired:
                entry.hit_count += 1
                self._hit_count += 1
                return entry.data
            else:
                # 删除过期条目
                del self._cache[key]
        
        self._miss_count += 1
        return None
    
    def set(
        self, 
        key: str, 
        data: Any, 
        ttl: Optional[timedelta] = None
    ):
        """设置缓存数据"""
        # 清理过期条目
        self._cleanup_expired()
        
        # 如果缓存已满，删除最旧的条目
        if len(self._cache) >= self.max_size:
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].created_at)
            del self._cache[oldest_key]
        
        ttl = ttl or self.default_ttl
        entry = CacheEntry(
            key=key,
            data=data,
            created_at=datetime.now(),
            expires_at=datetime.now() + ttl
        )
        self._cache[key] = entry
    
    def _cleanup_expired(self):
        """清理过期条目"""
        expired_keys = [k for k, v in self._cache.items() if v.is_expired]
        for key in expired_keys:
            del self._cache[key]
    
    def clear(self):
        """清除所有缓存"""
        self._cache.clear()
        self._hit_count = 0
        self._miss_count = 0
    
    @property
    def hit_rate(self) -> float:
        """缓存命中率"""
        total = self._hit_count + self._miss_count
        if total == 0:
            return 0.0
        return self._hit_count / total * 100
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        return {
            'size': len(self._cache),
            'max_size': self.max_size,
            'hit_count': self._hit_count,
            'miss_count': self._miss_count,
            'hit_rate': self.hit_rate
        }


class ParallelProcessor:
    """
    并行处理器
    
    提供并行数据处理功能
    """
    
    def __init__(self, max_workers: int = 4):
        """
        初始化并行处理器
        
        Args:
            max_workers: 最大工作线程数
        """
        self.max_workers = max_workers
    
    def process_in_parallel(
        self,
        items: List[Any],
        processor: Callable[[Any], Any],
        chunk_size: int = 100
    ) -> List[Any]:
        """
        并行处理数据
        
        Args:
            items: 待处理项目列表
            processor: 处理函数
            chunk_size: 每个任务的数据块大小
        
        Returns:
            处理结果列表
        """
        if not items:
            return []
        
        # 分块
        chunks = [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]
        
        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self._process_chunk, chunk, processor): i 
                for i, chunk in enumerate(chunks)
            }
            
            for future in as_completed(futures):
                try:
                    chunk_results = future.result()
                    results.extend(chunk_results)
                except Exception as e:
                    logger.error(f"并行处理失败: {e}")
        
        return results
    
    def _process_chunk(
        self, 
        chunk: List[Any], 
        processor: Callable[[Any], Any]
    ) -> List[Any]:
        """处理数据块"""
        return [processor(item) for item in chunk]
    
    def process_dataframe_in_parallel(
        self,
        df: pd.DataFrame,
        processor: Callable[[pd.Series], Any],
        n_partitions: int = 4
    ) -> List[Any]:
        """
        并行处理DataFrame
        
        Args:
            df: 待处理DataFrame
            processor: 行处理函数
            n_partitions: 分区数
        
        Returns:
            处理结果列表
        """
        if df.empty:
            return []
        
        # 分区
        partitions = np.array_split(df, min(n_partitions, len(df)))
        
        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            for partition in partitions:
                future = executor.submit(
                    lambda p: [processor(row) for _, row in p.iterrows()],
                    partition
                )
                futures.append(future)
            
            for future in as_completed(futures):
                try:
                    partition_results = future.result()
                    results.extend(partition_results)
                except Exception as e:
                    logger.error(f"DataFrame并行处理失败: {e}")
        
        return results


class ScreeningOptimizer:
    """
    筛选优化器
    
    优化筛选过程的性能和结果质量
    """
    
    def __init__(self):
        """初始化筛选优化器"""
        self.monitor = PerformanceMonitor()
        self.cache = DataCache()
        self.parallel_processor = ParallelProcessor()
    
    def optimize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        优化DataFrame内存使用
        
        Args:
            df: 待优化的DataFrame
        
        Returns:
            优化后的DataFrame
        """
        if df.empty:
            return df
        
        self.monitor.start_operation("optimize_dataframe")
        
        try:
            # 优化数值列
            for col in df.select_dtypes(include=['float64']).columns:
                df[col] = pd.to_numeric(df[col], downcast='float')
            
            for col in df.select_dtypes(include=['int64']).columns:
                df[col] = pd.to_numeric(df[col], downcast='integer')
            
            # 优化字符串列
            for col in df.select_dtypes(include=['object']).columns:
                if df[col].nunique() / len(df) < 0.5:  # 低基数列
                    df[col] = df[col].astype('category')
            
            self.monitor.end_operation(records_processed=len(df))
            return df
            
        except Exception as e:
            self.monitor.end_operation(success=False, error_message=str(e))
            return df
    
    def cached_operation(
        self,
        operation_name: str,
        operation: Callable[[], Any],
        cache_key: str,
        ttl_minutes: int = 30
    ) -> Any:
        """
        执行带缓存的操作
        
        Args:
            operation_name: 操作名称
            operation: 操作函数
            cache_key: 缓存键
            ttl_minutes: 缓存过期时间
        
        Returns:
            操作结果
        """
        # 尝试从缓存获取
        cached = self.cache.get(cache_key)
        if cached is not None:
            logger.debug(f"缓存命中: {operation_name}")
            return cached
        
        # 执行操作
        self.monitor.start_operation(operation_name)
        try:
            result = operation()
            self.cache.set(cache_key, result, timedelta(minutes=ttl_minutes))
            self.monitor.end_operation()
            return result
        except Exception as e:
            self.monitor.end_operation(success=False, error_message=str(e))
            raise
    
    def batch_score_stocks(
        self,
        df: pd.DataFrame,
        scorer: Callable[[pd.Series], Any],
        batch_size: int = 100
    ) -> List[Any]:
        """
        批量评分股票
        
        Args:
            df: 股票数据
            scorer: 评分函数
            batch_size: 批次大小
        
        Returns:
            评分结果列表
        """
        self.monitor.start_operation("batch_score_stocks")
        
        try:
            results = self.parallel_processor.process_dataframe_in_parallel(
                df, scorer, n_partitions=4
            )
            self.monitor.end_operation(records_processed=len(df))
            return results
        except Exception as e:
            self.monitor.end_operation(success=False, error_message=str(e))
            return []
    
    def get_performance_report(self) -> str:
        """获取性能报告"""
        summary = self.monitor.get_summary()
        cache_stats = self.cache.get_stats()
        
        lines = [
            "=" * 60,
            "筛选性能报告",
            "=" * 60,
            "",
            "操作统计:",
            f"  总操作数: {summary.get('total_operations', 0)}",
            f"  总耗时: {summary.get('total_duration_ms', 0):.2f}ms",
            f"  总记录数: {summary.get('total_records', 0)}",
            f"  成功率: {summary.get('success_rate', 0):.1f}%",
            "",
            "缓存统计:",
            f"  缓存大小: {cache_stats.get('size', 0)}/{cache_stats.get('max_size', 0)}",
            f"  命中次数: {cache_stats.get('hit_count', 0)}",
            f"  未命中次数: {cache_stats.get('miss_count', 0)}",
            f"  命中率: {cache_stats.get('hit_rate', 0):.1f}%",
            "",
        ]
        
        # 按操作类型统计
        by_operation = summary.get('by_operation', {})
        if by_operation:
            lines.append("按操作类型:")
            for op, stats in by_operation.items():
                lines.append(f"  {op}:")
                lines.append(f"    次数: {stats['count']}")
                lines.append(f"    总耗时: {stats['total_duration_ms']:.2f}ms")
                lines.append(f"    记录数: {stats['total_records']}")
        
        lines.append("=" * 60)
        
        return "\n".join(lines)


# 全局实例
_performance_monitor: Optional[PerformanceMonitor] = None
_data_cache: Optional[DataCache] = None
_screening_optimizer: Optional[ScreeningOptimizer] = None


def get_performance_monitor() -> PerformanceMonitor:
    """获取性能监控器实例"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


def get_data_cache() -> DataCache:
    """获取数据缓存实例"""
    global _data_cache
    if _data_cache is None:
        _data_cache = DataCache()
    return _data_cache


def get_screening_optimizer() -> ScreeningOptimizer:
    """获取筛选优化器实例"""
    global _screening_optimizer
    if _screening_optimizer is None:
        _screening_optimizer = ScreeningOptimizer()
    return _screening_optimizer


def timed_operation(operation_name: str):
    """
    计时装饰器
    
    用于自动记录函数执行时间
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            monitor = get_performance_monitor()
            monitor.start_operation(operation_name)
            try:
                result = func(*args, **kwargs)
                # 尝试获取记录数
                records = 0
                if isinstance(result, pd.DataFrame):
                    records = len(result)
                elif isinstance(result, (list, tuple)):
                    records = len(result)
                monitor.end_operation(records_processed=records)
                return result
            except Exception as e:
                monitor.end_operation(success=False, error_message=str(e))
                raise
        return wrapper
    return decorator
