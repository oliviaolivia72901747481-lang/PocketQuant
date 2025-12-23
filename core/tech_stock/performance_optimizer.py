"""
科技股模块性能优化器

提供以下优化功能：
1. 智能数据预加载
2. 批量指标计算优化
3. 内存使用优化
4. 计算结果缓存

Requirements: 12.2 性能优化
- 优化数据加载速度
- 添加缓存机制
- 优化指标计算效率
"""

import logging
import time
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from functools import lru_cache, wraps
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import numpy as np
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """性能指标"""
    operation: str
    duration: float
    cache_hit: bool
    data_size: int
    timestamp: datetime


class PerformanceCache:
    """
    高性能缓存管理器
    
    提供多层缓存策略：
    1. 内存缓存：快速访问常用数据
    2. 计算结果缓存：避免重复计算技术指标
    3. 批量数据缓存：优化多股票数据加载
    """
    
    def __init__(self, max_memory_mb: int = 500):
        """
        初始化缓存
        
        Args:
            max_memory_mb: 最大内存使用量（MB）
        """
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self._stock_data_cache: Dict[str, Tuple[pd.DataFrame, float]] = {}
        self._indicator_cache: Dict[str, Tuple[Any, float]] = {}
        self._batch_cache: Dict[str, Tuple[Dict, float]] = {}
        self._performance_metrics: List[PerformanceMetrics] = []
        
        # 缓存TTL（秒）
        self.STOCK_DATA_TTL = 300  # 5分钟
        self.INDICATOR_TTL = 180   # 3分钟
        self.BATCH_TTL = 240       # 4分钟
    
    def get_stock_data(self, code: str) -> Optional[pd.DataFrame]:
        """获取股票数据缓存"""
        if code in self._stock_data_cache:
            data, timestamp = self._stock_data_cache[code]
            if time.time() - timestamp < self.STOCK_DATA_TTL:
                self._record_metric("stock_data_get", 0.001, True, len(data))
                return data.copy()
            else:
                # 过期数据清理
                del self._stock_data_cache[code]
        return None
    
    def set_stock_data(self, code: str, data: pd.DataFrame) -> None:
        """设置股票数据缓存"""
        # 检查内存使用
        if self._check_memory_usage():
            self._evict_old_data()
        
        self._stock_data_cache[code] = (data.copy(), time.time())
        self._record_metric("stock_data_set", 0.002, False, len(data))
    
    def get_indicator(self, key: str) -> Optional[Any]:
        """获取指标计算结果缓存"""
        if key in self._indicator_cache:
            result, timestamp = self._indicator_cache[key]
            if time.time() - timestamp < self.INDICATOR_TTL:
                self._record_metric("indicator_get", 0.0005, True, 1)
                return result
            else:
                del self._indicator_cache[key]
        return None
    
    def set_indicator(self, key: str, result: Any) -> None:
        """设置指标计算结果缓存"""
        self._indicator_cache[key] = (result, time.time())
        self._record_metric("indicator_set", 0.001, False, 1)
    
    def get_batch_data(self, batch_key: str) -> Optional[Dict]:
        """获取批量数据缓存"""
        if batch_key in self._batch_cache:
            data, timestamp = self._batch_cache[batch_key]
            if time.time() - timestamp < self.BATCH_TTL:
                self._record_metric("batch_get", 0.005, True, len(data))
                return data.copy()
            else:
                del self._batch_cache[batch_key]
        return None
    
    def set_batch_data(self, batch_key: str, data: Dict) -> None:
        """设置批量数据缓存"""
        self._batch_cache[batch_key] = (data.copy(), time.time())
        self._record_metric("batch_set", 0.01, False, len(data))
    
    def _check_memory_usage(self) -> bool:
        """检查内存使用是否超限"""
        # 简化的内存估算
        total_items = (len(self._stock_data_cache) + 
                      len(self._indicator_cache) + 
                      len(self._batch_cache))
        estimated_bytes = total_items * 1024 * 100  # 每项约100KB
        return estimated_bytes > self.max_memory_bytes
    
    def _evict_old_data(self) -> None:
        """清理过期数据"""
        current_time = time.time()
        
        # 清理过期股票数据
        expired_stocks = [
            code for code, (_, timestamp) in self._stock_data_cache.items()
            if current_time - timestamp > self.STOCK_DATA_TTL
        ]
        for code in expired_stocks:
            del self._stock_data_cache[code]
        
        # 清理过期指标数据
        expired_indicators = [
            key for key, (_, timestamp) in self._indicator_cache.items()
            if current_time - timestamp > self.INDICATOR_TTL
        ]
        for key in expired_indicators:
            del self._indicator_cache[key]
        
        logger.debug(f"清理过期数据: {len(expired_stocks)} 股票, {len(expired_indicators)} 指标")
    
    def _record_metric(self, operation: str, duration: float, cache_hit: bool, data_size: int) -> None:
        """记录性能指标"""
        metric = PerformanceMetrics(
            operation=operation,
            duration=duration,
            cache_hit=cache_hit,
            data_size=data_size,
            timestamp=datetime.now()
        )
        self._performance_metrics.append(metric)
        
        # 保持最近1000条记录
        if len(self._performance_metrics) > 1000:
            self._performance_metrics = self._performance_metrics[-1000:]
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        if not self._performance_metrics:
            return {}
        
        recent_metrics = [m for m in self._performance_metrics 
                         if (datetime.now() - m.timestamp).seconds < 300]  # 最近5分钟
        
        if not recent_metrics:
            return {}
        
        cache_hits = sum(1 for m in recent_metrics if m.cache_hit)
        total_ops = len(recent_metrics)
        avg_duration = sum(m.duration for m in recent_metrics) / total_ops
        
        return {
            "cache_hit_rate": cache_hits / total_ops if total_ops > 0 else 0,
            "avg_operation_time": avg_duration,
            "total_operations": total_ops,
            "cache_sizes": {
                "stock_data": len(self._stock_data_cache),
                "indicators": len(self._indicator_cache),
                "batch_data": len(self._batch_cache)
            }
        }
    
    def clear_all(self) -> None:
        """清空所有缓存"""
        self._stock_data_cache.clear()
        self._indicator_cache.clear()
        self._batch_cache.clear()
        logger.info("所有缓存已清空")


# 全局缓存实例
_performance_cache = PerformanceCache()


def performance_timer(func):
    """性能计时装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start_time
        
        if duration > 0.1:  # 只记录耗时操作
            logger.debug(f"{func.__name__} 耗时: {duration:.3f}秒")
        
        return result
    return wrapper


class BatchDataLoader:
    """
    批量数据加载器
    
    优化多股票数据加载性能：
    1. 并发加载
    2. 智能预加载
    3. 数据去重
    """
    
    def __init__(self, data_feed, max_workers: int = 4):
        """
        初始化批量加载器
        
        Args:
            data_feed: 数据获取模块
            max_workers: 最大并发线程数
        """
        self.data_feed = data_feed
        self.max_workers = max_workers
        self.cache = _performance_cache
    
    @performance_timer
    def load_batch_stocks(self, codes: List[str], days: int = 60) -> Dict[str, pd.DataFrame]:
        """
        批量加载股票数据
        
        Args:
            codes: 股票代码列表
            days: 加载天数
            
        Returns:
            {code: DataFrame} 字典
        """
        batch_key = f"batch_{hash(tuple(sorted(codes)))}_{days}"
        
        # 检查批量缓存
        cached_data = self.cache.get_batch_data(batch_key)
        if cached_data:
            logger.debug(f"批量数据缓存命中: {len(codes)} 只股票")
            return cached_data
        
        # 检查单个股票缓存
        results = {}
        uncached_codes = []
        
        for code in codes:
            cached_stock = self.cache.get_stock_data(code)
            if cached_stock is not None and len(cached_stock) >= days:
                results[code] = cached_stock.tail(days)
            else:
                uncached_codes.append(code)
        
        # 并发加载未缓存的股票
        if uncached_codes:
            logger.debug(f"并发加载 {len(uncached_codes)} 只股票数据")
            
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_code = {
                    executor.submit(self._load_single_stock, code, days): code
                    for code in uncached_codes
                }
                
                for future in as_completed(future_to_code):
                    code = future_to_code[future]
                    try:
                        data = future.result()
                        if data is not None:
                            results[code] = data
                            self.cache.set_stock_data(code, data)
                    except Exception as e:
                        logger.error(f"加载股票 {code} 失败: {e}")
        
        # 缓存批量结果
        if results:
            self.cache.set_batch_data(batch_key, results)
        
        logger.info(f"批量加载完成: {len(results)}/{len(codes)} 只股票")
        return results
    
    def _load_single_stock(self, code: str, days: int) -> Optional[pd.DataFrame]:
        """加载单只股票数据"""
        try:
            # 计算日期范围（多加载一些数据以备后用）
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days + 30)
            
            data = self.data_feed.get_stock_data(
                code=code,
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d')
            )
            
            return data
        except Exception as e:
            logger.error(f"加载股票 {code} 数据失败: {e}")
            return None


class IndicatorOptimizer:
    """
    技术指标计算优化器
    
    优化策略：
    1. 向量化计算
    2. 结果缓存
    3. 增量计算
    """
    
    def __init__(self):
        self.cache = _performance_cache
    
    @performance_timer
    def calculate_ma_batch(self, data_dict: Dict[str, pd.DataFrame], periods: List[int]) -> Dict[str, Dict[int, pd.Series]]:
        """
        批量计算移动平均线
        
        Args:
            data_dict: {code: DataFrame} 股票数据字典
            periods: MA周期列表，如 [5, 20, 60]
            
        Returns:
            {code: {period: Series}} 嵌套字典
        """
        results = {}
        
        for code, df in data_dict.items():
            if df is None or df.empty:
                continue
                
            results[code] = {}
            
            for period in periods:
                cache_key = f"ma_{code}_{period}_{len(df)}"
                
                # 检查缓存
                cached_ma = self.cache.get_indicator(cache_key)
                if cached_ma is not None:
                    results[code][period] = cached_ma
                    continue
                
                # 向量化计算
                ma_series = df['close'].rolling(window=period, min_periods=period).mean()
                results[code][period] = ma_series
                
                # 缓存结果
                self.cache.set_indicator(cache_key, ma_series)
        
        return results
    
    @performance_timer
    def calculate_rsi_batch(self, data_dict: Dict[str, pd.DataFrame], period: int = 14) -> Dict[str, pd.Series]:
        """
        批量计算RSI指标
        
        Args:
            data_dict: {code: DataFrame} 股票数据字典
            period: RSI周期，默认14
            
        Returns:
            {code: Series} RSI序列字典
        """
        results = {}
        
        for code, df in data_dict.items():
            if df is None or df.empty or len(df) < period + 1:
                continue
            
            cache_key = f"rsi_{code}_{period}_{len(df)}"
            
            # 检查缓存
            cached_rsi = self.cache.get_indicator(cache_key)
            if cached_rsi is not None:
                results[code] = cached_rsi
                continue
            
            # 向量化计算RSI
            close_prices = df['close']
            delta = close_prices.diff()
            
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            
            avg_gain = gain.rolling(window=period, min_periods=period).mean()
            avg_loss = loss.rolling(window=period, min_periods=period).mean()
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            results[code] = rsi
            
            # 缓存结果
            self.cache.set_indicator(cache_key, rsi)
        
        return results
    
    @performance_timer
    def calculate_macd_batch(self, data_dict: Dict[str, pd.DataFrame], 
                           fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, Dict[str, pd.Series]]:
        """
        批量计算MACD指标
        
        Args:
            data_dict: {code: DataFrame} 股票数据字典
            fast: 快线周期
            slow: 慢线周期
            signal: 信号线周期
            
        Returns:
            {code: {'dif': Series, 'dea': Series, 'macd': Series}}
        """
        results = {}
        
        for code, df in data_dict.items():
            if df is None or df.empty or len(df) < slow + signal:
                continue
            
            cache_key = f"macd_{code}_{fast}_{slow}_{signal}_{len(df)}"
            
            # 检查缓存
            cached_macd = self.cache.get_indicator(cache_key)
            if cached_macd is not None:
                results[code] = cached_macd
                continue
            
            # 向量化计算MACD
            close_prices = df['close']
            
            ema_fast = close_prices.ewm(span=fast).mean()
            ema_slow = close_prices.ewm(span=slow).mean()
            
            dif = ema_fast - ema_slow
            dea = dif.ewm(span=signal).mean()
            macd = (dif - dea) * 2
            
            macd_dict = {
                'dif': dif,
                'dea': dea,
                'macd': macd
            }
            
            results[code] = macd_dict
            
            # 缓存结果
            self.cache.set_indicator(cache_key, macd_dict)
        
        return results


class MemoryOptimizer:
    """
    内存使用优化器
    
    优化策略：
    1. 数据类型优化
    2. 内存回收
    3. 数据压缩
    """
    
    @staticmethod
    def optimize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """
        优化DataFrame内存使用
        
        Args:
            df: 原始DataFrame
            
        Returns:
            优化后的DataFrame
        """
        if df is None or df.empty:
            return df
        
        optimized_df = df.copy()
        
        # 优化数值列的数据类型
        for col in optimized_df.select_dtypes(include=['float64']).columns:
            optimized_df[col] = pd.to_numeric(optimized_df[col], downcast='float')
        
        for col in optimized_df.select_dtypes(include=['int64']).columns:
            optimized_df[col] = pd.to_numeric(optimized_df[col], downcast='integer')
        
        # 优化日期列
        if 'date' in optimized_df.columns:
            optimized_df['date'] = pd.to_datetime(optimized_df['date'])
        
        return optimized_df
    
    @staticmethod
    def get_memory_usage(df: pd.DataFrame) -> Dict[str, float]:
        """
        获取DataFrame内存使用情况
        
        Args:
            df: DataFrame
            
        Returns:
            内存使用统计
        """
        if df is None or df.empty:
            return {"total_mb": 0, "per_column": {}}
        
        memory_usage = df.memory_usage(deep=True)
        total_bytes = memory_usage.sum()
        
        return {
            "total_mb": total_bytes / (1024 * 1024),
            "per_column": {
                col: memory_usage[col] / (1024 * 1024)
                for col in memory_usage.index
            }
        }


# 全局优化器实例
batch_loader = None
indicator_optimizer = IndicatorOptimizer()
memory_optimizer = MemoryOptimizer()


def get_batch_loader(data_feed):
    """获取批量加载器实例"""
    global batch_loader
    if batch_loader is None:
        batch_loader = BatchDataLoader(data_feed)
    return batch_loader


def get_performance_stats() -> Dict[str, Any]:
    """获取性能统计信息"""
    return _performance_cache.get_performance_stats()


def clear_all_caches() -> None:
    """清空所有缓存"""
    _performance_cache.clear_all()


def optimize_tech_stock_data_loading(data_feed, stock_codes: List[str]) -> Dict[str, pd.DataFrame]:
    """
    优化科技股数据加载
    
    Args:
        data_feed: 数据获取模块
        stock_codes: 股票代码列表
        
    Returns:
        优化后的股票数据字典
    """
    loader = get_batch_loader(data_feed)
    
    # 批量加载数据
    raw_data = loader.load_batch_stocks(stock_codes, days=120)  # 加载4个月数据
    
    # 内存优化
    optimized_data = {}
    for code, df in raw_data.items():
        optimized_data[code] = memory_optimizer.optimize_dataframe(df)
    
    return optimized_data


def batch_calculate_indicators(data_dict: Dict[str, pd.DataFrame]) -> Dict[str, Dict[str, Any]]:
    """
    批量计算技术指标
    
    Args:
        data_dict: 股票数据字典
        
    Returns:
        指标计算结果
    """
    results = {}
    
    # 批量计算MA
    ma_results = indicator_optimizer.calculate_ma_batch(data_dict, [5, 20, 60])
    
    # 批量计算RSI
    rsi_results = indicator_optimizer.calculate_rsi_batch(data_dict, 14)
    
    # 批量计算MACD
    macd_results = indicator_optimizer.calculate_macd_batch(data_dict)
    
    # 整合结果
    for code in data_dict.keys():
        if code in ma_results and code in rsi_results and code in macd_results:
            results[code] = {
                'ma5': ma_results[code].get(5),
                'ma20': ma_results[code].get(20),
                'ma60': ma_results[code].get(60),
                'rsi': rsi_results[code],
                'macd': macd_results[code]
            }
    
    return results