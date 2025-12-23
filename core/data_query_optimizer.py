"""
Data Query Optimizer
数据查询优化器

提供缓存和优化的数据查询功能，减少重复查询和提升性能。

Requirements: Task 3.3 - 优化数据查询
"""

import streamlit as st
import time
import logging
from typing import Dict, Any, List, Optional
from functools import wraps
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

from config.settings import get_settings
from core.data_feed import DataFeed
from core.screener import Screener
from core.position_tracker import PositionTracker, Holding
from core.notification import NotificationConfigStore, NotificationConfig

logger = logging.getLogger(__name__)


class QueryPerformanceMonitor:
    """查询性能监控器"""
    
    def __init__(self):
        self.query_stats = {}
    
    def monitor_query(self, query_name: str):
        """查询性能监控装饰器"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    end_time = time.time()
                    execution_time = end_time - start_time
                    
                    # 记录性能统计
                    if query_name not in self.query_stats:
                        self.query_stats[query_name] = {
                            'total_calls': 0,
                            'total_time': 0.0,
                            'avg_time': 0.0,
                            'min_time': float('inf'),
                            'max_time': 0.0
                        }
                    
                    stats = self.query_stats[query_name]
                    stats['total_calls'] += 1
                    stats['total_time'] += execution_time
                    stats['avg_time'] = stats['total_time'] / stats['total_calls']
                    stats['min_time'] = min(stats['min_time'], execution_time)
                    stats['max_time'] = max(stats['max_time'], execution_time)
                    
                    logger.debug(f"{query_name} 执行时间: {execution_time:.3f}s")
                    
                    return result
                    
                except Exception as e:
                    logger.error(f"{query_name} 执行失败: {str(e)}")
                    raise
                    
            return wrapper
        return decorator
    
    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取性能统计"""
        return self.query_stats.copy()
    
    def reset_stats(self):
        """重置统计数据"""
        self.query_stats.clear()


# 全局性能监控器
performance_monitor = QueryPerformanceMonitor()


@st.cache_resource
def get_cached_data_feed() -> DataFeed:
    """
    获取缓存的 DataFeed 实例
    
    使用 Streamlit 的 cache_resource 缓存 DataFeed 实例，
    避免重复创建和初始化开销。
    
    Returns:
        DataFeed: 缓存的数据源实例
    """
    logger.info("创建新的 DataFeed 实例")
    settings = get_settings()
    return DataFeed(
        raw_path=settings.path.get_raw_path(),
        processed_path=settings.path.get_processed_path()
    )


@st.cache_data(ttl=60)  # 1分钟缓存
@performance_monitor.monitor_query("market_status")
def get_cached_market_status() -> Dict[str, Any]:
    """
    获取缓存的大盘状态
    
    缓存大盘状态查询结果，避免在同一页面中重复计算。
    TTL 设置为 60秒，平衡数据新鲜度和性能。
    
    Returns:
        Dict[str, Any]: 大盘状态信息
    """
    logger.debug("计算大盘状态")
    data_feed = get_cached_data_feed()
    screener = Screener(data_feed)
    return screener.get_market_status()


@st.cache_data(ttl=300)  # 5分钟缓存
@performance_monitor.monitor_query("positions")
def get_cached_positions() -> List[Holding]:
    """
    获取缓存的持仓数据
    
    缓存持仓查询结果，减少数据库访问频率。
    TTL 设置为 5分钟，持仓数据变化相对较慢。
    
    Returns:
        List[Holding]: 持仓列表
    """
    logger.debug("查询持仓数据")
    tracker = PositionTracker()
    return tracker.get_all_positions()


@st.cache_data(ttl=3600)  # 1小时缓存
@performance_monitor.monitor_query("notification_config")
def get_cached_notification_config() -> NotificationConfig:
    """
    获取缓存的通知配置
    
    缓存通知配置，减少文件读取次数。
    TTL 设置为 1小时，配置变化频率较低。
    
    Returns:
        NotificationConfig: 通知配置
    """
    logger.debug("加载通知配置")
    return NotificationConfigStore.load()


@st.cache_data(ttl=1800)  # 30分钟缓存
@performance_monitor.monitor_query("strategy_params")
def get_cached_strategy_params() -> Dict[str, Any]:
    """
    获取缓存的策略参数
    
    缓存策略参数，减少文件读取次数。
    TTL 设置为 30分钟，策略参数变化频率中等。
    
    Returns:
        Dict[str, Any]: 策略参数
    """
    logger.debug("加载策略参数")
    from config.settings import load_strategy_params
    return load_strategy_params()


class BatchDataLoader:
    """批量数据加载器"""
    
    @staticmethod
    @performance_monitor.monitor_query("batch_preload")
    def preload_page_data() -> Dict[str, Any]:
        """
        预加载页面所需的所有数据
        
        使用并行加载提升数据获取效率，减少用户等待时间。
        
        Returns:
            Dict[str, Any]: 预加载的数据字典
        """
        logger.info("开始批量预加载页面数据")
        
        def load_data_feed():
            return get_cached_data_feed()
        
        def load_market_status():
            return get_cached_market_status()
        
        def load_positions():
            return get_cached_positions()
        
        def load_notification_config():
            return get_cached_notification_config()
        
        def load_strategy_params():
            return get_cached_strategy_params()
        
        # 并行加载多个数据源
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                'data_feed': executor.submit(load_data_feed),
                'market_status': executor.submit(load_market_status),
                'positions': executor.submit(load_positions),
                'notification_config': executor.submit(load_notification_config),
                'strategy_params': executor.submit(load_strategy_params),
            }
            
            # 等待所有数据加载完成
            results = {}
            for key, future in futures.items():
                try:
                    results[key] = future.result(timeout=10)  # 10秒超时
                    logger.debug(f"成功加载 {key}")
                except Exception as e:
                    logger.error(f"加载 {key} 失败: {str(e)}")
                    results[key] = None
        
        logger.info(f"批量预加载完成，成功加载 {len([v for v in results.values() if v is not None])}/{len(results)} 项数据")
        return results


class CacheManager:
    """缓存管理器"""
    
    @staticmethod
    def clear_all_caches():
        """清空所有缓存"""
        logger.info("清空所有数据查询缓存")
        
        # 清空 Streamlit 缓存
        st.cache_data.clear()
        st.cache_resource.clear()
        
        # 清空 DataFeed 内部缓存
        try:
            data_feed = get_cached_data_feed()
            if hasattr(data_feed, 'cache') and hasattr(data_feed.cache, 'clear'):
                data_feed.cache.clear()
        except Exception as e:
            logger.warning(f"清空 DataFeed 缓存失败: {str(e)}")
    
    @staticmethod
    def clear_market_status_cache():
        """清空大盘状态缓存"""
        logger.info("清空大盘状态缓存")
        # 清空特定函数的缓存
        get_cached_market_status.clear()
    
    @staticmethod
    def clear_positions_cache():
        """清空持仓数据缓存"""
        logger.info("清空持仓数据缓存")
        get_cached_positions.clear()
    
    @staticmethod
    def get_cache_stats() -> Dict[str, Any]:
        """获取缓存统计信息"""
        stats = {
            'performance_stats': performance_monitor.get_stats(),
            'cache_info': {
                'market_status': getattr(get_cached_market_status, 'cache_info', lambda: {})(),
                'positions': getattr(get_cached_positions, 'cache_info', lambda: {})(),
                'notification_config': getattr(get_cached_notification_config, 'cache_info', lambda: {})(),
                'strategy_params': getattr(get_cached_strategy_params, 'cache_info', lambda: {})(),
            }
        }
        return stats


class QueryOptimizer:
    """查询优化器主类"""
    
    def __init__(self):
        self.batch_loader = BatchDataLoader()
        self.cache_manager = CacheManager()
        self.performance_monitor = performance_monitor
    
    def optimize_page_queries(self) -> Dict[str, Any]:
        """
        优化页面查询
        
        执行页面级别的查询优化，包括预加载和缓存管理。
        
        Returns:
            Dict[str, Any]: 优化后的数据
        """
        logger.info("开始页面查询优化")
        
        # 预加载数据
        preloaded_data = self.batch_loader.preload_page_data()
        
        # 返回优化后的数据访问接口
        return {
            'get_data_feed': lambda: preloaded_data.get('data_feed') or get_cached_data_feed(),
            'get_market_status': lambda: preloaded_data.get('market_status') or get_cached_market_status(),
            'get_positions': lambda: preloaded_data.get('positions') or get_cached_positions(),
            'get_notification_config': lambda: preloaded_data.get('notification_config') or get_cached_notification_config(),
            'get_strategy_params': lambda: preloaded_data.get('strategy_params') or get_cached_strategy_params(),
            'preloaded_data': preloaded_data
        }
    
    def get_performance_report(self) -> Dict[str, Any]:
        """
        获取性能报告
        
        Returns:
            Dict[str, Any]: 性能统计报告
        """
        stats = self.performance_monitor.get_stats()
        cache_stats = self.cache_manager.get_cache_stats()
        
        report = {
            'query_performance': stats,
            'cache_statistics': cache_stats,
            'optimization_summary': {
                'total_queries': sum(stat['total_calls'] for stat in stats.values()),
                'total_time': sum(stat['total_time'] for stat in stats.values()),
                'avg_query_time': sum(stat['avg_time'] for stat in stats.values()) / len(stats) if stats else 0,
                'fastest_query': min((stat['min_time'] for stat in stats.values()), default=0),
                'slowest_query': max((stat['max_time'] for stat in stats.values()), default=0),
            }
        }
        
        return report


# 全局查询优化器实例
query_optimizer = QueryOptimizer()


# 便捷函数，用于替换原有的查询函数
def get_optimized_data_feed() -> DataFeed:
    """获取优化的数据源实例"""
    return get_cached_data_feed()


def get_optimized_market_status() -> Dict[str, Any]:
    """获取优化的大盘状态"""
    return get_cached_market_status()


def get_optimized_positions() -> List[Holding]:
    """获取优化的持仓数据"""
    return get_cached_positions()


def get_optimized_notification_config() -> NotificationConfig:
    """获取优化的通知配置"""
    return get_cached_notification_config()


def get_optimized_strategy_params() -> Dict[str, Any]:
    """获取优化的策略参数"""
    return get_cached_strategy_params()


# 性能测试函数
def benchmark_query_performance(iterations: int = 100) -> Dict[str, float]:
    """
    基准测试查询性能
    
    Args:
        iterations: 测试迭代次数
        
    Returns:
        Dict[str, float]: 性能测试结果
    """
    logger.info(f"开始查询性能基准测试，迭代次数: {iterations}")
    
    results = {}
    
    # 测试 DataFeed 创建
    start_time = time.time()
    for _ in range(iterations):
        get_cached_data_feed()
    results['data_feed_creation'] = (time.time() - start_time) / iterations
    
    # 测试大盘状态查询
    start_time = time.time()
    for _ in range(iterations):
        get_cached_market_status()
    results['market_status_query'] = (time.time() - start_time) / iterations
    
    # 测试持仓数据查询
    start_time = time.time()
    for _ in range(iterations):
        get_cached_positions()
    results['positions_query'] = (time.time() - start_time) / iterations
    
    logger.info(f"基准测试完成: {results}")
    return results


if __name__ == "__main__":
    # 性能测试示例
    print("数据查询优化器性能测试")
    print("=" * 50)
    
    # 运行基准测试
    benchmark_results = benchmark_query_performance(10)
    
    print("基准测试结果:")
    for query_type, avg_time in benchmark_results.items():
        print(f"  {query_type}: {avg_time:.4f}s")
    
    # 获取性能报告
    report = query_optimizer.get_performance_report()
    print(f"\n性能报告:")
    print(f"  总查询次数: {report['optimization_summary']['total_queries']}")
    print(f"  总查询时间: {report['optimization_summary']['total_time']:.3f}s")
    print(f"  平均查询时间: {report['optimization_summary']['avg_query_time']:.4f}s")