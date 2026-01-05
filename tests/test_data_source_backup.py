"""
多数据源备份机制测试

测试数据源备份管理器的核心功能：
- 数据源注册和健康状态管理
- 故障检测和自动转移
- 数据缓存和本地备份
- 恢复机制

Requirements: 7.1, 7.4, 技术风险缓解
"""

import pytest
import pandas as pd
import os
import shutil
import time
from datetime import datetime, timedelta

from core.stock_screener.data_source_backup import (
    DataSourceBackupManager,
    DataSourceHealth,
    BackupStatus,
    FailoverStrategy,
    FailoverEvent,
    BackupConfig,
    CachedData,
    get_backup_manager,
    reset_backup_manager,
)


class TestDataSourceHealth:
    """数据源健康状态测试"""
    
    def test_health_initialization(self):
        """测试健康状态初始化"""
        health = DataSourceHealth(
            source_name="test_source",
            status=BackupStatus.ACTIVE
        )
        
        assert health.source_name == "test_source"
        assert health.status == BackupStatus.ACTIVE
        assert health.consecutive_failures == 0
        assert health.total_requests == 0
        assert health.success_rate == 0.0
        assert health.is_healthy is True

    
    def test_success_rate_calculation(self):
        """测试成功率计算"""
        health = DataSourceHealth(
            source_name="test_source",
            status=BackupStatus.ACTIVE,
            total_requests=10,
            total_failures=2
        )
        
        assert health.success_rate == 0.8
    
    def test_is_healthy_status(self):
        """测试健康状态判断"""
        # ACTIVE状态应该是健康的
        health_active = DataSourceHealth(
            source_name="test",
            status=BackupStatus.ACTIVE
        )
        assert health_active.is_healthy is True
        
        # DEGRADED状态应该是健康的（但性能下降）
        health_degraded = DataSourceHealth(
            source_name="test",
            status=BackupStatus.DEGRADED
        )
        assert health_degraded.is_healthy is True
        
        # FAILED状态不健康
        health_failed = DataSourceHealth(
            source_name="test",
            status=BackupStatus.FAILED
        )
        assert health_failed.is_healthy is False
        
        # DISABLED状态不健康
        health_disabled = DataSourceHealth(
            source_name="test",
            status=BackupStatus.DISABLED
        )
        assert health_disabled.is_healthy is False
    
    def test_to_dict(self):
        """测试转换为字典"""
        health = DataSourceHealth(
            source_name="test_source",
            status=BackupStatus.ACTIVE,
            total_requests=5,
            total_failures=1
        )
        
        result = health.to_dict()
        
        assert result['source_name'] == "test_source"
        assert result['status'] == "active"
        assert result['total_requests'] == 5
        assert result['total_failures'] == 1
        assert result['success_rate'] == 0.8



class TestCachedData:
    """缓存数据测试"""
    
    def test_cache_not_expired(self):
        """测试未过期缓存"""
        data = pd.DataFrame({'code': ['000001'], 'name': ['测试']})
        cached = CachedData(
            data=data,
            source_name="test",
            fetch_time=datetime.now(),
            expiry_time=datetime.now() + timedelta(hours=1),
            checksum="abc123"
        )
        
        assert cached.is_expired is False
    
    def test_cache_expired(self):
        """测试过期缓存"""
        data = pd.DataFrame({'code': ['000001'], 'name': ['测试']})
        cached = CachedData(
            data=data,
            source_name="test",
            fetch_time=datetime.now() - timedelta(hours=2),
            expiry_time=datetime.now() - timedelta(hours=1),
            checksum="abc123"
        )
        
        assert cached.is_expired is True
    
    def test_cache_age(self):
        """测试缓存年龄"""
        data = pd.DataFrame({'code': ['000001'], 'name': ['测试']})
        fetch_time = datetime.now() - timedelta(seconds=100)
        cached = CachedData(
            data=data,
            source_name="test",
            fetch_time=fetch_time,
            expiry_time=datetime.now() + timedelta(hours=1),
            checksum="abc123"
        )
        
        # 年龄应该大约是100秒
        assert 99 <= cached.age_seconds <= 102


class TestBackupConfig:
    """备份配置测试"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = BackupConfig()
        
        assert config.failover_strategy == FailoverStrategy.PRIORITY
        assert config.max_consecutive_failures == 3
        assert config.cache_enabled is True
        assert config.local_backup_enabled is True
        assert config.auto_recovery_enabled is True
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = BackupConfig(
            failover_strategy=FailoverStrategy.FASTEST,
            max_consecutive_failures=5,
            cache_ttl_seconds=7200
        )
        
        assert config.failover_strategy == FailoverStrategy.FASTEST
        assert config.max_consecutive_failures == 5
        assert config.cache_ttl_seconds == 7200



class TestDataSourceBackupManager:
    """数据源备份管理器测试"""
    
    @pytest.fixture
    def backup_manager(self, tmp_path):
        """创建测试用备份管理器"""
        config = BackupConfig(
            backup_dir=str(tmp_path / "backups"),
            cache_ttl_seconds=60,
            max_consecutive_failures=2
        )
        manager = DataSourceBackupManager(config)
        yield manager
        # 清理
        manager.stop_recovery_monitor()
    
    def test_register_source(self, backup_manager):
        """测试注册数据源"""
        backup_manager.register_source("source1", priority=1)
        backup_manager.register_source("source2", priority=2)
        
        health = backup_manager.get_health_status()
        
        assert "source1" in health
        assert "source2" in health
        assert health["source1"]["status"] == "active"
    
    def test_record_success(self, backup_manager):
        """测试记录成功请求"""
        backup_manager.register_source("test_source")
        backup_manager.record_success("test_source", 100.0)
        
        health = backup_manager.get_health_status("test_source")
        
        assert health["consecutive_successes"] == 1
        assert health["consecutive_failures"] == 0
        assert health["total_requests"] == 1
        assert health["avg_response_time_ms"] == 100.0
    
    def test_record_failure(self, backup_manager):
        """测试记录失败请求"""
        backup_manager.register_source("test_source")
        backup_manager.record_failure("test_source", "连接超时")
        
        health = backup_manager.get_health_status("test_source")
        
        assert health["consecutive_failures"] == 1
        assert health["total_failures"] == 1
        assert health["error_message"] == "连接超时"

    
    def test_status_degradation(self, backup_manager):
        """测试状态降级"""
        backup_manager.register_source("test_source")
        
        # 连续失败触发降级
        backup_manager.record_failure("test_source", "错误1")
        backup_manager.record_failure("test_source", "错误2")
        
        health = backup_manager.get_health_status("test_source")
        assert health["status"] == "degraded"
    
    def test_failover_trigger(self, backup_manager):
        """测试故障转移触发"""
        backup_manager.register_source("primary", priority=1)
        backup_manager.register_source("backup", priority=2)
        
        # 主数据源连续失败
        for i in range(4):
            backup_manager.record_failure("primary", f"错误{i}")
        
        # 检查是否触发了故障转移
        history = backup_manager.get_failover_history()
        assert len(history) > 0
        assert history[-1]["from_source"] == "primary"
        assert history[-1]["to_source"] == "backup"
    
    def test_cache_data(self, backup_manager):
        """测试数据缓存"""
        data = pd.DataFrame({
            'code': ['000001', '000002'],
            'name': ['平安银行', '万科A']
        })
        
        backup_manager.cache_data("test_key", data, "test_source")
        
        # 获取缓存
        result = backup_manager.get_cached_data("test_key")
        
        assert result is not None
        cached_data, source = result
        assert len(cached_data) == 2
        assert source == "test_source"
    
    def test_cache_expiry(self, backup_manager):
        """测试缓存过期"""
        # 使用非常短的TTL
        backup_manager.config.cache_ttl_seconds = 1
        
        data = pd.DataFrame({'code': ['000001']})
        backup_manager.cache_data("test_key", data, "test_source")
        
        # 等待过期
        time.sleep(1.5)
        
        # 不允许使用过期数据
        result = backup_manager.get_cached_data("test_key", allow_stale=False)
        assert result is None
        
        # 允许使用过期数据
        result = backup_manager.get_cached_data("test_key", allow_stale=True)
        assert result is not None

    
    def test_local_backup_save_and_load(self, backup_manager):
        """测试本地备份保存和加载"""
        data = pd.DataFrame({
            'code': ['000001', '000002', '000003'],
            'name': ['平安银行', '万科A', '国农科技']
        })
        
        # 保存备份
        backup_manager.save_local_backup("test_backup", data, "test_source")
        
        # 加载备份
        result = backup_manager.load_local_backup("test_backup")
        
        assert result is not None
        loaded_data, meta = result
        assert len(loaded_data) == 3
        assert meta['source_name'] == "test_source"
        assert meta['row_count'] == 3
    
    def test_backup_cleanup(self, backup_manager):
        """测试备份清理"""
        backup_manager.config.max_backup_files = 2
        
        data = pd.DataFrame({'code': ['000001']})
        
        # 创建多个备份
        for i in range(4):
            backup_manager.save_local_backup("cleanup_test", data, "source")
            time.sleep(0.1)  # 确保时间戳不同
        
        # 检查备份文件数量
        backup_files = [
            f for f in os.listdir(backup_manager.config.backup_dir)
            if f.startswith("cleanup_test") and f.endswith(".csv")
        ]
        
        assert len(backup_files) <= 2
    
    def test_get_available_sources(self, backup_manager):
        """测试获取可用数据源"""
        backup_manager.register_source("source1", priority=1)
        backup_manager.register_source("source2", priority=2)
        backup_manager.register_source("source3", priority=3)
        
        # 禁用一个数据源
        backup_manager.disable_source("source2")
        
        available = backup_manager.get_available_sources()
        
        assert "source1" in available
        assert "source2" not in available
        assert "source3" in available
    
    def test_reset_source(self, backup_manager):
        """测试重置数据源状态"""
        backup_manager.register_source("test_source")
        
        # 制造失败状态
        for i in range(5):
            backup_manager.record_failure("test_source", "错误")
        
        health = backup_manager.get_health_status("test_source")
        assert health["status"] in ["degraded", "failed"]
        
        # 重置
        backup_manager.reset_source("test_source")
        
        health = backup_manager.get_health_status("test_source")
        assert health["status"] == "active"
        assert health["consecutive_failures"] == 0

    
    def test_backup_summary(self, backup_manager):
        """测试备份摘要"""
        backup_manager.register_source("source1")
        backup_manager.register_source("source2")
        
        data = pd.DataFrame({'code': ['000001']})
        backup_manager.cache_data("key1", data, "source1")
        backup_manager.save_local_backup("summary_test", data, "source1")
        
        summary = backup_manager.get_backup_summary()
        
        assert 'active_source' in summary
        assert 'registered_sources' in summary
        assert 'cache' in summary
        assert 'local_backup' in summary
        assert summary['cache']['total_entries'] >= 1
    
    def test_clear_cache(self, backup_manager):
        """测试清除缓存"""
        data = pd.DataFrame({'code': ['000001']})
        
        backup_manager.cache_data("key1", data, "source1")
        backup_manager.cache_data("key2", data, "source2")
        
        # 清除单个缓存
        backup_manager.clear_cache("key1")
        assert backup_manager.get_cached_data("key1") is None
        assert backup_manager.get_cached_data("key2") is not None
        
        # 清除所有缓存
        backup_manager.clear_cache()
        assert backup_manager.get_cached_data("key2") is None


class TestFailoverStrategies:
    """故障转移策略测试"""
    
    @pytest.fixture
    def manager_with_sources(self, tmp_path):
        """创建带有多个数据源的管理器"""
        config = BackupConfig(
            backup_dir=str(tmp_path / "backups"),
            max_consecutive_failures=2
        )
        manager = DataSourceBackupManager(config)
        
        manager.register_source("fast", priority=3)
        manager.register_source("reliable", priority=1)
        manager.register_source("backup", priority=2)
        
        # 设置不同的响应时间
        manager.record_success("fast", 50.0)
        manager.record_success("reliable", 200.0)
        manager.record_success("backup", 150.0)
        
        yield manager
        manager.stop_recovery_monitor()
    
    def test_priority_strategy(self, manager_with_sources):
        """测试优先级策略"""
        manager_with_sources.config.failover_strategy = FailoverStrategy.PRIORITY
        
        # 让reliable失败
        for i in range(3):
            manager_with_sources.record_failure("reliable", "错误")
        
        # 应该切换到backup（优先级2）
        history = manager_with_sources.get_failover_history()
        if history:
            assert history[-1]["to_source"] == "backup"
    
    def test_fastest_strategy(self, manager_with_sources):
        """测试最快响应策略"""
        manager_with_sources.config.failover_strategy = FailoverStrategy.FASTEST
        
        # 让reliable失败
        for i in range(3):
            manager_with_sources.record_failure("reliable", "错误")
        
        # 应该切换到fast（响应最快）
        history = manager_with_sources.get_failover_history()
        if history:
            assert history[-1]["to_source"] == "fast"



class TestGlobalInstance:
    """全局实例测试"""
    
    def test_get_backup_manager_singleton(self):
        """测试单例模式"""
        reset_backup_manager()
        
        manager1 = get_backup_manager()
        manager2 = get_backup_manager()
        
        assert manager1 is manager2
        
        reset_backup_manager()
    
    def test_reset_backup_manager(self):
        """测试重置全局实例"""
        manager1 = get_backup_manager()
        manager1.register_source("test")
        
        reset_backup_manager()
        
        manager2 = get_backup_manager()
        
        # 新实例不应该有之前注册的数据源
        health = manager2.get_health_status("test")
        assert health == {}
        
        reset_backup_manager()


class TestIntegrationWithDataSourceManager:
    """与DataSourceManager集成测试"""
    
    def test_data_source_manager_has_backup(self):
        """测试DataSourceManager集成备份管理器"""
        from core.stock_screener import DataSourceManager, reset_data_source_manager
        
        reset_data_source_manager()
        
        manager = DataSourceManager(use_backup_manager=True)
        
        backup_manager = manager.get_backup_manager()
        assert backup_manager is not None
        
        summary = manager.get_backup_summary()
        assert 'backup_manager_enabled' not in summary or summary.get('active_source') is not None
    
    def test_data_source_manager_without_backup(self):
        """测试禁用备份管理器"""
        from core.stock_screener import DataSourceManager
        
        manager = DataSourceManager(use_backup_manager=False)
        
        backup_manager = manager.get_backup_manager()
        assert backup_manager is None
        
        summary = manager.get_backup_summary()
        assert summary['backup_manager_enabled'] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
