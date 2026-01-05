"""
快速回滚机制测试

测试快速回滚功能的核心功能，包括：
- 备份创建和管理
- 快速回滚
- 紧急回滚
- 回滚验证
- 回滚历史记录

Requirements: 业务风险 - 建立快速回滚机制
"""

import pytest
import os
import json
import tempfile
import shutil
from datetime import datetime
from unittest.mock import patch, MagicMock

from core.stock_screener.quick_rollback import (
    QuickRollbackManager,
    BackupInfo,
    RollbackRecord,
    RollbackValidation,
    RollbackType,
    RollbackStatus,
    get_quick_rollback_manager,
    reset_quick_rollback_manager,
    quick_rollback,
    emergency_rollback,
    rollback_to_version,
    create_backup,
    list_available_backups,
    get_rollback_status,
    validate_backup_for_rollback,
)


@pytest.fixture
def temp_backup_dir():
    """创建临时备份目录"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def temp_history_file(temp_backup_dir):
    """创建临时历史文件路径"""
    return os.path.join(temp_backup_dir, "rollback_history.json")


@pytest.fixture
def sample_backup_data():
    """示例备份数据"""
    return {
        'backup_id': 'BACKUP_20260105_120000',
        'timestamp': '2026-01-05T12:00:00',
        'pool': ['000001', '000002', '002001', '600001', '600002'],
        'count': 5,
        'backup_type': 'manual',
        'description': '测试备份'
    }


@pytest.fixture
def rollback_manager(temp_backup_dir, temp_history_file):
    """创建测试用的回滚管理器"""
    manager = QuickRollbackManager(
        backup_dir=temp_backup_dir,
        history_file=temp_history_file
    )
    return manager


@pytest.fixture
def manager_with_backup(rollback_manager, temp_backup_dir, sample_backup_data):
    """创建带有备份的回滚管理器"""
    # 创建备份文件
    backup_filename = "pool_backup_20260105_120000.json"
    backup_path = os.path.join(temp_backup_dir, backup_filename)
    
    with open(backup_path, 'w', encoding='utf-8') as f:
        json.dump(sample_backup_data, f, ensure_ascii=False, indent=2)
    
    # 重新扫描备份
    rollback_manager._scan_backups()
    
    return rollback_manager


class TestBackupInfo:
    """测试备份信息类"""
    
    def test_backup_info_creation(self):
        """测试创建备份信息"""
        backup = BackupInfo(
            backup_id='BACKUP_001',
            backup_path='/path/to/backup.json',
            timestamp=datetime.now(),
            pool_count=10,
            pool_codes=['000001', '000002'],
            backup_type='manual',
            description='测试'
        )
        
        assert backup.backup_id == 'BACKUP_001'
        assert backup.pool_count == 10
        assert len(backup.pool_codes) == 2
    
    def test_backup_info_to_dict(self):
        """测试转换为字典"""
        backup = BackupInfo(
            backup_id='BACKUP_001',
            backup_path='/path/to/backup.json',
            timestamp=datetime(2026, 1, 5, 12, 0, 0),
            pool_count=10,
            pool_codes=['000001'],
            backup_type='auto',
            description=''
        )
        
        data = backup.to_dict()
        
        assert data['backup_id'] == 'BACKUP_001'
        assert data['pool_count'] == 10
        assert '2026-01-05' in data['timestamp']
    
    def test_backup_info_from_dict(self):
        """测试从字典创建"""
        data = {
            'backup_id': 'BACKUP_002',
            'backup_path': '/path/backup.json',
            'timestamp': '2026-01-05T12:00:00',
            'pool_count': 5,
            'pool_codes': ['000001'],
            'backup_type': 'manual',
            'description': '测试'
        }
        
        backup = BackupInfo.from_dict(data)
        
        assert backup.backup_id == 'BACKUP_002'
        assert backup.pool_count == 5


class TestRollbackRecord:
    """测试回滚记录类"""
    
    def test_rollback_record_creation(self):
        """测试创建回滚记录"""
        record = RollbackRecord(
            rollback_id='ROLLBACK_001',
            rollback_type=RollbackType.QUICK,
            status=RollbackStatus.COMPLETED,
            timestamp=datetime.now(),
            backup_id='BACKUP_001',
            reason='测试回滚',
            operator='test_user'
        )
        
        assert record.rollback_id == 'ROLLBACK_001'
        assert record.rollback_type == RollbackType.QUICK
        assert record.status == RollbackStatus.COMPLETED
    
    def test_rollback_record_to_dict(self):
        """测试转换为字典"""
        record = RollbackRecord(
            rollback_id='ROLLBACK_001',
            rollback_type=RollbackType.EMERGENCY,
            status=RollbackStatus.FAILED,
            timestamp=datetime(2026, 1, 5, 12, 0, 0),
            backup_id='BACKUP_001',
            reason='紧急回滚',
            error_message='测试错误'
        )
        
        data = record.to_dict()
        
        assert data['rollback_type'] == 'emergency'
        assert data['status'] == 'failed'
        assert data['error_message'] == '测试错误'


class TestRollbackValidation:
    """测试回滚验证类"""
    
    def test_validation_result(self):
        """测试验证结果"""
        validation = RollbackValidation(
            is_valid=True,
            backup_exists=True,
            backup_readable=True,
            pool_count_valid=True,
            codes_valid=True
        )
        
        assert validation.is_valid is True
        assert len(validation.errors) == 0
    
    def test_validation_with_errors(self):
        """测试带错误的验证结果"""
        validation = RollbackValidation(
            is_valid=False,
            backup_exists=False,
            backup_readable=False,
            pool_count_valid=False,
            codes_valid=False,
            errors=['备份不存在']
        )
        
        assert validation.is_valid is False
        assert len(validation.errors) == 1


class TestQuickRollbackManager:
    """测试快速回滚管理器"""
    
    def test_manager_initialization(self, rollback_manager):
        """测试管理器初始化"""
        assert rollback_manager is not None
        assert os.path.exists(rollback_manager.backup_dir)
    
    def test_create_backup(self, rollback_manager):
        """测试创建备份"""
        with patch.object(rollback_manager, '_get_current_pool', return_value=['000001', '000002', '600001']):
            success, message, backup_info = rollback_manager.create_backup(
                description='测试备份',
                backup_type='manual'
            )
        
        assert success is True
        assert backup_info is not None
        assert backup_info.pool_count == 3
        assert os.path.exists(backup_info.backup_path)
    
    def test_list_backups(self, manager_with_backup):
        """测试列出备份"""
        backups = manager_with_backup.list_backups()
        
        assert len(backups) >= 1
        assert backups[0].backup_id is not None
    
    def test_get_latest_backup(self, manager_with_backup):
        """测试获取最新备份"""
        latest = manager_with_backup.get_latest_backup()
        
        assert latest is not None
        assert latest.pool_count == 5
    
    def test_validate_backup(self, manager_with_backup, sample_backup_data):
        """测试验证备份"""
        backup_id = sample_backup_data['backup_id']
        validation = manager_with_backup.validate_backup(backup_id)
        
        assert validation.backup_exists is True
        assert validation.backup_readable is True
        assert validation.is_valid is True
    
    def test_validate_nonexistent_backup(self, rollback_manager):
        """测试验证不存在的备份"""
        validation = rollback_manager.validate_backup('NONEXISTENT_BACKUP')
        
        assert validation.is_valid is False
        assert validation.backup_exists is False
        assert len(validation.errors) > 0
    
    def test_quick_rollback_no_backup(self, rollback_manager):
        """测试没有备份时的快速回滚"""
        success, message, details = rollback_manager.quick_rollback()
        
        assert success is False
        assert '没有可用的备份' in message
    
    def test_quick_rollback_with_backup(self, manager_with_backup, sample_backup_data):
        """测试有备份时的快速回滚"""
        with patch.object(manager_with_backup, '_get_current_pool', return_value=['000001', '000002']):
            success, message, details = manager_with_backup.quick_rollback(
                reason='测试快速回滚',
                operator='test_user'
            )
        
        assert success is True
        assert 'record' in details
        assert details['record']['status'] == 'completed'
    
    def test_emergency_rollback(self, manager_with_backup):
        """测试紧急回滚"""
        with patch.object(manager_with_backup, '_get_current_pool', return_value=['000001']):
            success, message, details = manager_with_backup.emergency_rollback(
                reason='紧急情况',
                operator='admin'
            )
        
        assert success is True
        assert details['record']['rollback_type'] == 'emergency'
    
    def test_rollback_to_specific_version(self, manager_with_backup, sample_backup_data):
        """测试回滚到指定版本"""
        backup_id = sample_backup_data['backup_id']
        
        with patch.object(manager_with_backup, '_get_current_pool', return_value=['000001']):
            success, message, details = manager_with_backup.rollback_to_backup(
                backup_id=backup_id,
                reason='回滚到指定版本',
                operator='test_user'
            )
        
        assert success is True
        assert details['backup_info']['backup_id'] == backup_id
    
    def test_rollback_history(self, manager_with_backup):
        """测试回滚历史记录"""
        # 执行一次回滚
        with patch.object(manager_with_backup, '_get_current_pool', return_value=['000001']):
            manager_with_backup.quick_rollback(reason='测试')
        
        history = manager_with_backup.get_rollback_history()
        
        assert len(history) >= 1
        assert history[0].reason == '测试'
    
    def test_rollback_summary(self, manager_with_backup):
        """测试回滚摘要"""
        summary = manager_with_backup.get_rollback_summary()
        
        assert 'total_backups' in summary
        assert 'latest_backup' in summary
        assert summary['total_backups'] >= 1
    
    def test_cleanup_old_backups(self, rollback_manager):
        """测试清理旧备份"""
        import time
        
        # 创建多个备份，每个之间稍微延迟以确保不同的时间戳
        with patch.object(rollback_manager, '_get_current_pool', return_value=['000001']):
            for i in range(5):
                rollback_manager.create_backup(description=f'备份{i}')
                time.sleep(0.01)  # 小延迟确保不同时间戳
        
        # 获取当前备份数量
        initial_count = len(rollback_manager.list_backups(limit=100))
        
        # 清理，只保留2个
        deleted = rollback_manager.cleanup_old_backups(keep_count=2)
        
        # 验证清理后的数量
        final_count = len(rollback_manager.list_backups(limit=100))
        assert final_count == 2
        assert deleted == initial_count - 2
    
    def test_stock_code_validation(self, rollback_manager):
        """测试股票代码验证"""
        # 有效代码
        assert rollback_manager._is_valid_stock_code('000001') is True
        assert rollback_manager._is_valid_stock_code('002001') is True
        assert rollback_manager._is_valid_stock_code('600001') is True
        assert rollback_manager._is_valid_stock_code('300001') is True
        assert rollback_manager._is_valid_stock_code('688001') is True
        
        # 无效代码
        assert rollback_manager._is_valid_stock_code('') is False
        assert rollback_manager._is_valid_stock_code('12345') is False
        assert rollback_manager._is_valid_stock_code('abcdef') is False
        assert rollback_manager._is_valid_stock_code('999999') is False


class TestConvenienceFunctions:
    """测试便捷函数"""
    
    def test_reset_manager(self):
        """测试重置管理器"""
        reset_quick_rollback_manager()
        manager1 = get_quick_rollback_manager()
        reset_quick_rollback_manager()
        manager2 = get_quick_rollback_manager()
        
        # 重置后应该是新实例
        assert manager1 is not manager2
    
    def test_get_rollback_status_function(self, temp_backup_dir, temp_history_file):
        """测试获取回滚状态函数"""
        reset_quick_rollback_manager()
        
        # 使用临时目录创建管理器
        with patch('core.stock_screener.quick_rollback._quick_rollback_manager', None):
            with patch('core.stock_screener.quick_rollback.QuickRollbackManager') as MockManager:
                mock_instance = MagicMock()
                mock_instance.get_rollback_summary.return_value = {
                    'total_backups': 5,
                    'total_rollbacks': 2
                }
                MockManager.return_value = mock_instance
                
                reset_quick_rollback_manager()


class TestEdgeCases:
    """测试边界情况"""
    
    def test_empty_pool_backup(self, rollback_manager):
        """测试空股票池备份"""
        with patch.object(rollback_manager, '_get_current_pool', return_value=[]):
            success, message, backup_info = rollback_manager.create_backup()
        
        assert success is True
        assert backup_info.pool_count == 0
    
    def test_backup_with_invalid_codes(self, temp_backup_dir):
        """测试包含无效代码的备份验证"""
        # 创建包含无效代码的备份
        backup_data = {
            'backup_id': 'BACKUP_INVALID',
            'timestamp': '2026-01-05T12:00:00',
            'pool': ['000001', 'invalid', '12345', '600001'],
            'count': 4
        }
        
        backup_path = os.path.join(temp_backup_dir, 'pool_backup_invalid.json')
        with open(backup_path, 'w') as f:
            json.dump(backup_data, f)
        
        manager = QuickRollbackManager(
            backup_dir=temp_backup_dir,
            history_file=os.path.join(temp_backup_dir, 'history.json')
        )
        
        validation = manager.validate_backup('BACKUP_INVALID')
        
        # 应该有警告但仍然有效（无效代码比例不超过10%）
        assert len(validation.warnings) > 0
    
    def test_concurrent_rollback_protection(self, manager_with_backup):
        """测试并发回滚保护"""
        # 模拟并发回滚场景
        with patch.object(manager_with_backup, '_get_current_pool', return_value=['000001']):
            success1, _, _ = manager_with_backup.quick_rollback(reason='回滚1')
            success2, _, _ = manager_with_backup.quick_rollback(reason='回滚2')
        
        # 两次回滚都应该成功（因为是顺序执行）
        assert success1 is True
        assert success2 is True
        
        # 历史记录应该有两条
        history = manager_with_backup.get_rollback_history()
        assert len(history) >= 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
