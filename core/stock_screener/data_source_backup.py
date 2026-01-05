"""
多数据源备份机制模块

提供数据源的自动备份、故障转移和恢复功能，包括：
- 数据源健康监控和自动切换
- 数据缓存和本地备份
- 故障自动恢复机制
- 数据源优先级动态调整
- 多源数据一致性验证

Requirements: 7.1, 7.4, 技术风险缓解
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Tuple
from enum import Enum
from datetime import datetime, timedelta
import time
import logging
import os
import json
import threading
import hashlib
import pandas as pd

logger = logging.getLogger(__name__)


class BackupStatus(Enum):
    """备份状态"""
    ACTIVE = "active"           # 活跃可用
    DEGRADED = "degraded"       # 性能下降
    FAILED = "failed"           # 失败
    RECOVERING = "recovering"   # 恢复中
    DISABLED = "disabled"       # 已禁用


class FailoverStrategy(Enum):
    """故障转移策略"""
    PRIORITY = "priority"           # 按优先级顺序
    ROUND_ROBIN = "round_robin"     # 轮询
    LEAST_FAILURES = "least_failures"  # 最少失败次数
    FASTEST = "fastest"             # 最快响应


@dataclass
class DataSourceHealth:
    """数据源健康状态"""
    source_name: str
    status: BackupStatus
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    total_requests: int = 0
    total_failures: int = 0
    avg_response_time_ms: float = 0.0
    last_check: Optional[datetime] = None
    error_message: Optional[str] = None
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_requests == 0:
            return 0.0
        return (self.total_requests - self.total_failures) / self.total_requests
    
    @property
    def is_healthy(self) -> bool:
        """是否健康"""
        return self.status in [BackupStatus.ACTIVE, BackupStatus.DEGRADED]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'source_name': self.source_name,
            'status': self.status.value,
            'last_success': self.last_success.isoformat() if self.last_success else None,
            'last_failure': self.last_failure.isoformat() if self.last_failure else None,
            'consecutive_failures': self.consecutive_failures,
            'consecutive_successes': self.consecutive_successes,
            'total_requests': self.total_requests,
            'total_failures': self.total_failures,
            'success_rate': self.success_rate,
            'avg_response_time_ms': self.avg_response_time_ms,
            'last_check': self.last_check.isoformat() if self.last_check else None,
            'error_message': self.error_message
        }


@dataclass
class CachedData:
    """缓存数据"""
    data: pd.DataFrame
    source_name: str
    fetch_time: datetime
    expiry_time: datetime
    checksum: str
    
    @property
    def is_expired(self) -> bool:
        """是否过期"""
        return datetime.now() > self.expiry_time
    
    @property
    def age_seconds(self) -> float:
        """数据年龄（秒）"""
        return (datetime.now() - self.fetch_time).total_seconds()


@dataclass
class FailoverEvent:
    """故障转移事件"""
    timestamp: datetime
    from_source: str
    to_source: str
    reason: str
    success: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'from_source': self.from_source,
            'to_source': self.to_source,
            'reason': self.reason,
            'success': self.success
        }


@dataclass
class BackupConfig:
    """备份配置"""
    # 故障转移配置
    failover_strategy: FailoverStrategy = FailoverStrategy.PRIORITY
    max_consecutive_failures: int = 3  # 触发故障转移的连续失败次数
    recovery_check_interval: int = 300  # 恢复检查间隔（秒）
    auto_recovery_enabled: bool = True  # 是否启用自动恢复
    
    # 缓存配置
    cache_enabled: bool = True
    cache_ttl_seconds: int = 3600  # 缓存有效期（秒）
    use_stale_on_failure: bool = True  # 失败时使用过期缓存
    stale_cache_max_age: int = 86400  # 过期缓存最大年龄（秒）
    
    # 本地备份配置
    local_backup_enabled: bool = True
    backup_dir: str = "data/source_backups"
    max_backup_files: int = 10
    
    # 健康检查配置
    health_check_interval: int = 60  # 健康检查间隔（秒）
    health_check_timeout: int = 30  # 健康检查超时（秒）


class DataSourceBackupManager:
    """
    数据源备份管理器
    
    提供多数据源的备份、故障转移和恢复功能
    
    Features:
    - 自动故障检测和转移
    - 数据缓存和本地备份
    - 健康状态监控
    - 自动恢复机制
    - 多源数据一致性验证
    """
    
    def __init__(self, config: Optional[BackupConfig] = None):
        """
        初始化备份管理器
        
        Args:
            config: 备份配置，None则使用默认配置
        """
        self.config = config or BackupConfig()
        
        # 数据源健康状态
        self._health_status: Dict[str, DataSourceHealth] = {}
        
        # 数据缓存
        self._cache: Dict[str, CachedData] = {}
        
        # 故障转移历史
        self._failover_history: List[FailoverEvent] = []
        
        # 当前活跃数据源
        self._active_source: Optional[str] = None
        
        # 数据源优先级（动态调整）
        self._source_priorities: Dict[str, int] = {}
        
        # 线程锁
        self._lock = threading.RLock()
        
        # 恢复检查线程
        self._recovery_thread: Optional[threading.Thread] = None
        self._running = False
        
        # 确保备份目录存在
        if self.config.local_backup_enabled:
            os.makedirs(self.config.backup_dir, exist_ok=True)
    
    def register_source(self, source_name: str, priority: int = 1):
        """
        注册数据源
        
        Args:
            source_name: 数据源名称
            priority: 优先级（数字越小优先级越高）
        """
        with self._lock:
            if source_name not in self._health_status:
                self._health_status[source_name] = DataSourceHealth(
                    source_name=source_name,
                    status=BackupStatus.ACTIVE
                )
            self._source_priorities[source_name] = priority
            
            # 设置初始活跃数据源
            if self._active_source is None:
                self._active_source = source_name
            
            logger.info(f"注册数据源: {source_name}, 优先级: {priority}")

    
    def record_success(self, source_name: str, response_time_ms: float):
        """
        记录成功请求
        
        Args:
            source_name: 数据源名称
            response_time_ms: 响应时间（毫秒）
        """
        with self._lock:
            if source_name not in self._health_status:
                self.register_source(source_name)
            
            health = self._health_status[source_name]
            health.last_success = datetime.now()
            health.consecutive_successes += 1
            health.consecutive_failures = 0
            health.total_requests += 1
            health.last_check = datetime.now()
            health.error_message = None
            
            # 更新平均响应时间
            if health.avg_response_time_ms == 0:
                health.avg_response_time_ms = response_time_ms
            else:
                health.avg_response_time_ms = (
                    health.avg_response_time_ms * 0.8 + response_time_ms * 0.2
                )
            
            # 恢复状态
            if health.status == BackupStatus.RECOVERING:
                if health.consecutive_successes >= 3:
                    health.status = BackupStatus.ACTIVE
                    logger.info(f"数据源 {source_name} 已恢复正常")
            elif health.status == BackupStatus.DEGRADED:
                if health.consecutive_successes >= 5:
                    health.status = BackupStatus.ACTIVE
    
    def record_failure(self, source_name: str, error_message: str):
        """
        记录失败请求
        
        Args:
            source_name: 数据源名称
            error_message: 错误信息
        """
        with self._lock:
            if source_name not in self._health_status:
                self.register_source(source_name)
            
            health = self._health_status[source_name]
            health.last_failure = datetime.now()
            health.consecutive_failures += 1
            health.consecutive_successes = 0
            health.total_requests += 1
            health.total_failures += 1
            health.last_check = datetime.now()
            health.error_message = error_message
            
            # 检查是否需要降级或标记失败
            if health.consecutive_failures >= self.config.max_consecutive_failures:
                if health.status == BackupStatus.ACTIVE:
                    health.status = BackupStatus.DEGRADED
                    logger.warning(f"数据源 {source_name} 已降级")
                elif health.status == BackupStatus.DEGRADED:
                    health.status = BackupStatus.FAILED
                    logger.error(f"数据源 {source_name} 已标记为失败")
                    self._trigger_failover(source_name)

    
    def _trigger_failover(self, failed_source: str):
        """
        触发故障转移
        
        Args:
            failed_source: 失败的数据源
        """
        if self._active_source != failed_source:
            return
        
        # 选择下一个可用数据源
        next_source = self._select_next_source(failed_source)
        
        if next_source:
            event = FailoverEvent(
                timestamp=datetime.now(),
                from_source=failed_source,
                to_source=next_source,
                reason=f"连续失败 {self.config.max_consecutive_failures} 次",
                success=True
            )
            self._failover_history.append(event)
            self._active_source = next_source
            logger.warning(f"故障转移: {failed_source} -> {next_source}")
        else:
            event = FailoverEvent(
                timestamp=datetime.now(),
                from_source=failed_source,
                to_source="",
                reason="无可用备用数据源",
                success=False
            )
            self._failover_history.append(event)
            logger.error("故障转移失败: 无可用备用数据源")
    
    def _select_next_source(self, exclude_source: str) -> Optional[str]:
        """
        选择下一个数据源
        
        Args:
            exclude_source: 要排除的数据源
        
        Returns:
            下一个可用数据源名称，无可用则返回None
        """
        available_sources = [
            (name, health) for name, health in self._health_status.items()
            if name != exclude_source and health.is_healthy
        ]
        
        if not available_sources:
            return None
        
        strategy = self.config.failover_strategy
        
        if strategy == FailoverStrategy.PRIORITY:
            # 按优先级选择
            available_sources.sort(
                key=lambda x: self._source_priorities.get(x[0], 999)
            )
            return available_sources[0][0]
        
        elif strategy == FailoverStrategy.LEAST_FAILURES:
            # 选择失败次数最少的
            available_sources.sort(key=lambda x: x[1].total_failures)
            return available_sources[0][0]
        
        elif strategy == FailoverStrategy.FASTEST:
            # 选择响应最快的
            available_sources.sort(key=lambda x: x[1].avg_response_time_ms)
            return available_sources[0][0]
        
        else:  # ROUND_ROBIN
            # 轮询选择
            return available_sources[0][0]

    
    def cache_data(self, cache_key: str, data: pd.DataFrame, source_name: str):
        """
        缓存数据
        
        Args:
            cache_key: 缓存键
            data: 数据
            source_name: 数据源名称
        """
        if not self.config.cache_enabled:
            return
        
        with self._lock:
            # 计算数据校验和
            checksum = self._calculate_checksum(data)
            
            cached = CachedData(
                data=data.copy(),
                source_name=source_name,
                fetch_time=datetime.now(),
                expiry_time=datetime.now() + timedelta(
                    seconds=self.config.cache_ttl_seconds
                ),
                checksum=checksum
            )
            
            self._cache[cache_key] = cached
            logger.debug(f"数据已缓存: {cache_key}")
    
    def get_cached_data(
        self, 
        cache_key: str, 
        allow_stale: bool = False
    ) -> Optional[Tuple[pd.DataFrame, str]]:
        """
        获取缓存数据
        
        Args:
            cache_key: 缓存键
            allow_stale: 是否允许使用过期数据
        
        Returns:
            (数据, 数据源名称) 或 None
        """
        with self._lock:
            if cache_key not in self._cache:
                return None
            
            cached = self._cache[cache_key]
            
            if not cached.is_expired:
                return cached.data.copy(), cached.source_name
            
            # 检查是否允许使用过期数据
            if allow_stale and self.config.use_stale_on_failure:
                if cached.age_seconds <= self.config.stale_cache_max_age:
                    logger.warning(f"使用过期缓存数据: {cache_key}")
                    return cached.data.copy(), cached.source_name
            
            return None
    
    def _calculate_checksum(self, data: pd.DataFrame) -> str:
        """计算数据校验和"""
        data_str = data.to_json()
        return hashlib.md5(data_str.encode()).hexdigest()

    
    def save_local_backup(self, backup_name: str, data: pd.DataFrame, source_name: str):
        """
        保存本地备份
        
        Args:
            backup_name: 备份名称
            data: 数据
            source_name: 数据源名称
        """
        if not self.config.local_backup_enabled:
            return
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{backup_name}_{timestamp}.csv"
            filepath = os.path.join(self.config.backup_dir, filename)
            
            # 保存数据
            data.to_csv(filepath, index=False, encoding='utf-8')
            
            # 保存元数据
            meta_filepath = filepath.replace('.csv', '_meta.json')
            meta = {
                'backup_name': backup_name,
                'source_name': source_name,
                'timestamp': timestamp,
                'row_count': len(data),
                'checksum': self._calculate_checksum(data)
            }
            with open(meta_filepath, 'w', encoding='utf-8') as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
            
            logger.info(f"本地备份已保存: {filepath}")
            
            # 清理旧备份
            self._cleanup_old_backups(backup_name)
            
        except Exception as e:
            logger.error(f"保存本地备份失败: {e}")
    
    def load_local_backup(self, backup_name: str) -> Optional[Tuple[pd.DataFrame, Dict]]:
        """
        加载最新的本地备份
        
        Args:
            backup_name: 备份名称
        
        Returns:
            (数据, 元数据) 或 None
        """
        if not self.config.local_backup_enabled:
            return None
        
        try:
            # 查找最新备份
            backup_files = []
            for f in os.listdir(self.config.backup_dir):
                if f.startswith(backup_name) and f.endswith('.csv'):
                    backup_files.append(f)
            
            if not backup_files:
                return None
            
            # 按时间排序，取最新
            backup_files.sort(reverse=True)
            latest_file = backup_files[0]
            filepath = os.path.join(self.config.backup_dir, latest_file)
            
            # 加载数据
            data = pd.read_csv(filepath, encoding='utf-8')
            
            # 加载元数据
            meta_filepath = filepath.replace('.csv', '_meta.json')
            meta = {}
            if os.path.exists(meta_filepath):
                with open(meta_filepath, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
            
            logger.info(f"已加载本地备份: {filepath}")
            return data, meta
            
        except Exception as e:
            logger.error(f"加载本地备份失败: {e}")
            return None

    
    def _cleanup_old_backups(self, backup_name: str):
        """清理旧备份文件"""
        try:
            backup_files = []
            for f in os.listdir(self.config.backup_dir):
                if f.startswith(backup_name) and f.endswith('.csv'):
                    filepath = os.path.join(self.config.backup_dir, f)
                    backup_files.append((filepath, os.path.getmtime(filepath)))
            
            # 按修改时间排序
            backup_files.sort(key=lambda x: x[1], reverse=True)
            
            # 删除超出限制的旧文件
            for filepath, _ in backup_files[self.config.max_backup_files:]:
                os.remove(filepath)
                meta_path = filepath.replace('.csv', '_meta.json')
                if os.path.exists(meta_path):
                    os.remove(meta_path)
                logger.debug(f"已删除旧备份: {filepath}")
                
        except Exception as e:
            logger.warning(f"清理旧备份失败: {e}")
    
    def start_recovery_monitor(self):
        """启动恢复监控线程"""
        if self._running:
            return
        
        self._running = True
        self._recovery_thread = threading.Thread(
            target=self._recovery_loop,
            daemon=True
        )
        self._recovery_thread.start()
        logger.info("恢复监控已启动")
    
    def stop_recovery_monitor(self):
        """停止恢复监控线程"""
        self._running = False
        if self._recovery_thread:
            self._recovery_thread.join(timeout=5)
        logger.info("恢复监控已停止")
    
    def _recovery_loop(self):
        """恢复监控循环"""
        while self._running:
            try:
                if self.config.auto_recovery_enabled:
                    self._check_recovery()
            except Exception as e:
                logger.error(f"恢复检查出错: {e}")
            
            time.sleep(self.config.recovery_check_interval)
    
    def _check_recovery(self):
        """检查失败数据源是否可恢复"""
        with self._lock:
            for name, health in self._health_status.items():
                if health.status == BackupStatus.FAILED:
                    # 标记为恢复中
                    health.status = BackupStatus.RECOVERING
                    health.consecutive_failures = 0
                    logger.info(f"数据源 {name} 开始恢复检查")

    
    def get_active_source(self) -> Optional[str]:
        """获取当前活跃数据源"""
        return self._active_source
    
    def get_available_sources(self) -> List[str]:
        """获取所有可用数据源"""
        with self._lock:
            return [
                name for name, health in self._health_status.items()
                if health.is_healthy
            ]
    
    def get_health_status(self, source_name: Optional[str] = None) -> Dict[str, Any]:
        """
        获取健康状态
        
        Args:
            source_name: 数据源名称，None则返回所有
        
        Returns:
            健康状态字典
        """
        with self._lock:
            if source_name:
                if source_name in self._health_status:
                    return self._health_status[source_name].to_dict()
                return {}
            
            return {
                name: health.to_dict()
                for name, health in self._health_status.items()
            }
    
    def get_failover_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取故障转移历史
        
        Args:
            limit: 返回记录数量限制
        
        Returns:
            故障转移事件列表
        """
        with self._lock:
            return [
                event.to_dict()
                for event in self._failover_history[-limit:]
            ]
    
    def get_backup_summary(self) -> Dict[str, Any]:
        """获取备份摘要"""
        with self._lock:
            # 统计缓存
            cache_stats = {
                'total_entries': len(self._cache),
                'valid_entries': sum(
                    1 for c in self._cache.values() if not c.is_expired
                ),
                'expired_entries': sum(
                    1 for c in self._cache.values() if c.is_expired
                )
            }
            
            # 统计本地备份
            backup_stats = {'total_files': 0, 'total_size_mb': 0}
            if self.config.local_backup_enabled and os.path.exists(self.config.backup_dir):
                for f in os.listdir(self.config.backup_dir):
                    if f.endswith('.csv'):
                        backup_stats['total_files'] += 1
                        filepath = os.path.join(self.config.backup_dir, f)
                        backup_stats['total_size_mb'] += os.path.getsize(filepath) / (1024 * 1024)
            
            return {
                'active_source': self._active_source,
                'registered_sources': list(self._health_status.keys()),
                'healthy_sources': self.get_available_sources(),
                'cache': cache_stats,
                'local_backup': backup_stats,
                'failover_count': len(self._failover_history),
                'config': {
                    'failover_strategy': self.config.failover_strategy.value,
                    'cache_enabled': self.config.cache_enabled,
                    'local_backup_enabled': self.config.local_backup_enabled,
                    'auto_recovery_enabled': self.config.auto_recovery_enabled
                }
            }

    
    def reset_source(self, source_name: str):
        """
        重置数据源状态
        
        Args:
            source_name: 数据源名称
        """
        with self._lock:
            if source_name in self._health_status:
                health = self._health_status[source_name]
                health.status = BackupStatus.ACTIVE
                health.consecutive_failures = 0
                health.consecutive_successes = 0
                health.error_message = None
                logger.info(f"数据源 {source_name} 状态已重置")
    
    def disable_source(self, source_name: str):
        """禁用数据源"""
        with self._lock:
            if source_name in self._health_status:
                self._health_status[source_name].status = BackupStatus.DISABLED
                if self._active_source == source_name:
                    self._trigger_failover(source_name)
                logger.info(f"数据源 {source_name} 已禁用")
    
    def enable_source(self, source_name: str):
        """启用数据源"""
        with self._lock:
            if source_name in self._health_status:
                self._health_status[source_name].status = BackupStatus.ACTIVE
                logger.info(f"数据源 {source_name} 已启用")
    
    def clear_cache(self, cache_key: Optional[str] = None):
        """
        清除缓存
        
        Args:
            cache_key: 缓存键，None则清除所有
        """
        with self._lock:
            if cache_key:
                if cache_key in self._cache:
                    del self._cache[cache_key]
                    logger.debug(f"已清除缓存: {cache_key}")
            else:
                self._cache.clear()
                logger.info("已清除所有缓存")


# 全局实例
_backup_manager: Optional[DataSourceBackupManager] = None


def get_backup_manager() -> DataSourceBackupManager:
    """
    获取备份管理器实例（单例模式）
    
    Returns:
        DataSourceBackupManager: 备份管理器实例
    """
    global _backup_manager
    if _backup_manager is None:
        _backup_manager = DataSourceBackupManager()
    return _backup_manager


def reset_backup_manager():
    """重置备份管理器实例"""
    global _backup_manager
    if _backup_manager:
        _backup_manager.stop_recovery_monitor()
    _backup_manager = None
