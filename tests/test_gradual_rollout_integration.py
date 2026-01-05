"""
渐进式上线策略集成测试

测试渐进式上线与股票池更新器和系统集成器的集成
"""

import pytest
import os
import tempfile
from datetime import datetime
from unittest.mock import patch, MagicMock

from core.stock_screener.pool_updater import PoolUpdater, get_pool_updater
from core.stock_screener.system_integrator import SystemIntegrator, get_system_integrator
from core.stock_screener.gradual_rollout import (
    GradualRolloutManager,
    RolloutConfig,
    RolloutPhase,
    RolloutStatus,
    reset_rollout_manager,
)


@pytest.fixture
def temp_state_file():
    """创建临时状态文件"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write('{}')
        temp_path = f.name
    yield temp_path
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def temp_backup_dir():
    """创建临时备份目录"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    import shutil
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


@pytest.fixture
def isolated_rollout_manager(temp_state_file, temp_backup_dir):
    """创建隔离的渐进式上线管理器"""
    manager = GradualRolloutManager(
        state_file=temp_state_file,
        backup_dir=temp_backup_dir
    )
    return manager


@pytest.fixture
def temp_dirs():
    """创建临时目录"""
    import shutil
    temp_dir = tempfile.mkdtemp()
    history_file = os.path.join(temp_dir, "history.json")
    yield temp_dir, history_file
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


@pytest.fixture
def sample_pools():
    """示例股票池"""
    original = ['000001', '000002', '000003', '000004', '000005']
    new = ['000001', '000002', '000003', '000004', '000005',
           '000006', '000007', '000008', '000009', '000010']
    return original, new


class TestPoolUpdaterGradualRollout:
    """测试股票池更新器的渐进式上线功能"""
    
    def test_start_gradual_update(self, temp_dirs, sample_pools, temp_state_file, temp_backup_dir):
        """测试启动渐进式更新"""
        temp_dir, history_file = temp_dirs
        original, new = sample_pools
        
        # 使用隔离的管理器
        with patch('core.stock_screener.pool_updater.get_rollout_manager') as mock_get_manager:
            manager = GradualRolloutManager(state_file=temp_state_file, backup_dir=temp_backup_dir)
            mock_get_manager.return_value = manager
            
            updater = PoolUpdater(history_file=history_file)
            success, message, details = updater.start_gradual_update(original, new)
            
            assert success is True
            assert 'rollout_id' in details
            assert details['original_count'] == 5
            assert details['target_count'] == 10
            assert details['added_count'] == 5
    
    def test_start_gradual_update_with_config(self, temp_dirs, sample_pools, temp_state_file, temp_backup_dir):
        """测试使用自定义配置启动渐进式更新"""
        temp_dir, history_file = temp_dirs
        original, new = sample_pools
        
        with patch('core.stock_screener.pool_updater.get_rollout_manager') as mock_get_manager:
            manager = GradualRolloutManager(state_file=temp_state_file, backup_dir=temp_backup_dir)
            mock_get_manager.return_value = manager
            
            config = RolloutConfig(canary_percent=20.0)
            updater = PoolUpdater(history_file=history_file)
            success, message, details = updater.start_gradual_update(original, new, config)
            
            assert success is True
    
    def test_advance_gradual_update(self, temp_dirs, sample_pools, temp_state_file, temp_backup_dir):
        """测试推进渐进式更新"""
        temp_dir, history_file = temp_dirs
        original, new = sample_pools
        
        with patch('core.stock_screener.pool_updater.get_rollout_manager') as mock_get_manager:
            manager = GradualRolloutManager(state_file=temp_state_file, backup_dir=temp_backup_dir)
            mock_get_manager.return_value = manager
            
            config = RolloutConfig(
                canary_observation_hours=0,
                early_adopter_observation_hours=0
            )
            
            updater = PoolUpdater(history_file=history_file)
            updater.start_gradual_update(original, new, config)
            
            # 推进到金丝雀阶段
            success, message, details = updater.advance_gradual_update()
            
            assert success is True
            assert details.get('current_phase') == 'canary'
    
    def test_rollback_gradual_update(self, temp_dirs, sample_pools, temp_state_file, temp_backup_dir):
        """测试回滚渐进式更新"""
        temp_dir, history_file = temp_dirs
        original, new = sample_pools
        
        with patch('core.stock_screener.pool_updater.get_rollout_manager') as mock_get_manager:
            manager = GradualRolloutManager(state_file=temp_state_file, backup_dir=temp_backup_dir)
            mock_get_manager.return_value = manager
            
            config = RolloutConfig(canary_observation_hours=0)
            
            updater = PoolUpdater(history_file=history_file)
            updater.start_gradual_update(original, new, config)
            updater.advance_gradual_update()
            
            success, message, details = updater.rollback_gradual_update("测试回滚")
            
            assert success is True
            assert details.get('status') == 'rolled_back'
    
    def test_get_gradual_update_status(self, temp_dirs, sample_pools, temp_state_file, temp_backup_dir):
        """测试获取渐进式更新状态"""
        temp_dir, history_file = temp_dirs
        original, new = sample_pools
        
        with patch('core.stock_screener.pool_updater.get_rollout_manager') as mock_get_manager:
            manager = GradualRolloutManager(state_file=temp_state_file, backup_dir=temp_backup_dir)
            mock_get_manager.return_value = manager
            
            updater = PoolUpdater(history_file=history_file)
            
            # 无上线时
            status = updater.get_gradual_update_status()
            assert status.get('has_active_rollout') is False
            
            # 有上线时
            updater.start_gradual_update(original, new)
            status = updater.get_gradual_update_status()
            assert status.get('has_active_rollout') is True
    
    def test_get_active_pool_from_rollout(self, temp_dirs, sample_pools, temp_state_file, temp_backup_dir):
        """测试从渐进式上线获取活跃股票池"""
        temp_dir, history_file = temp_dirs
        original, new = sample_pools
        
        with patch('core.stock_screener.pool_updater.get_rollout_manager') as mock_get_manager:
            manager = GradualRolloutManager(state_file=temp_state_file, backup_dir=temp_backup_dir)
            mock_get_manager.return_value = manager
            
            config = RolloutConfig(canary_observation_hours=0)
            
            updater = PoolUpdater(history_file=history_file)
            updater.start_gradual_update(original, new, config)
            
            # 初始阶段，活跃池应该是原始池
            pool = updater.get_active_pool_from_rollout()
            assert set(pool) == set(original)
            
            # 推进到金丝雀阶段
            updater.advance_gradual_update()
            pool = updater.get_active_pool_from_rollout()
            
            # 金丝雀阶段应该包含原始股票
            for code in original:
                assert code in pool
    
    def test_record_rollout_success(self, temp_dirs, sample_pools, temp_state_file, temp_backup_dir):
        """测试记录成功操作"""
        temp_dir, history_file = temp_dirs
        original, new = sample_pools
        
        with patch('core.stock_screener.pool_updater.get_rollout_manager') as mock_get_manager:
            manager = GradualRolloutManager(state_file=temp_state_file, backup_dir=temp_backup_dir)
            mock_get_manager.return_value = manager
            
            config = RolloutConfig(canary_observation_hours=0)
            
            updater = PoolUpdater(history_file=history_file)
            updater.start_gradual_update(original, new, config)
            updater.advance_gradual_update()
            
            # 记录成功操作不应抛出异常
            updater.record_rollout_success()
    
    def test_record_rollout_error(self, temp_dirs, sample_pools, temp_state_file, temp_backup_dir):
        """测试记录错误操作"""
        temp_dir, history_file = temp_dirs
        original, new = sample_pools
        
        with patch('core.stock_screener.pool_updater.get_rollout_manager') as mock_get_manager:
            manager = GradualRolloutManager(state_file=temp_state_file, backup_dir=temp_backup_dir)
            mock_get_manager.return_value = manager
            
            config = RolloutConfig(
                auto_rollback_on_error=True,
                rollback_error_threshold=2,
                canary_observation_hours=0
            )
            
            updater = PoolUpdater(history_file=history_file)
            updater.start_gradual_update(original, new, config)
            updater.advance_gradual_update()
            
            # 第一次错误
            triggered, _ = updater.record_rollout_error("错误1")
            assert triggered is False
            
            # 第二次错误应触发回滚
            triggered, _ = updater.record_rollout_error("错误2")
            assert triggered is True


class TestSystemIntegratorGradualRollout:
    """测试系统集成器的渐进式上线功能"""
    
    def test_get_integration_status_includes_rollout(self, temp_state_file, temp_backup_dir):
        """测试集成状态包含渐进式上线信息"""
        with patch('core.stock_screener.system_integrator.get_rollout_manager') as mock_get_manager:
            manager = GradualRolloutManager(state_file=temp_state_file, backup_dir=temp_backup_dir)
            mock_get_manager.return_value = manager
            
            integrator = SystemIntegrator()
            status = integrator.get_integration_status()
            
            assert 'gradual_rollout' in status
            assert 'modules' in status
            assert 'core.stock_screener.gradual_rollout' in status['modules']
    
    def test_integrate_with_gradual_rollout(self, sample_pools, temp_state_file, temp_backup_dir):
        """测试使用渐进式上线集成筛选结果"""
        original, new = sample_pools
        
        # 创建模拟的筛选结果
        mock_results = []
        for code in new:
            mock_result = MagicMock()
            mock_result.passed = True
            mock_result.code = code
            mock_results.append(mock_result)
        
        with patch('core.stock_screener.system_integrator.get_rollout_manager') as mock_get_manager:
            manager = GradualRolloutManager(state_file=temp_state_file, backup_dir=temp_backup_dir)
            mock_get_manager.return_value = manager
            
            integrator = SystemIntegrator()
            result = integrator.integrate_with_gradual_rollout(mock_results, original)
            
            assert result.success is True
            assert '渐进式上线已启动' in result.message
    
    def test_advance_gradual_rollout(self, sample_pools, temp_state_file, temp_backup_dir):
        """测试推进渐进式上线"""
        original, new = sample_pools
        
        # 创建模拟的筛选结果
        mock_results = []
        for code in new:
            mock_result = MagicMock()
            mock_result.passed = True
            mock_result.code = code
            mock_results.append(mock_result)
        
        config = RolloutConfig(canary_observation_hours=0)
        
        with patch('core.stock_screener.system_integrator.get_rollout_manager') as mock_get_manager:
            manager = GradualRolloutManager(state_file=temp_state_file, backup_dir=temp_backup_dir)
            mock_get_manager.return_value = manager
            
            integrator = SystemIntegrator()
            integrator.integrate_with_gradual_rollout(mock_results, original, config)
            
            result = integrator.advance_gradual_rollout()
            
            assert result.success is True
            assert 'canary' in str(result.warnings).lower()
    
    def test_rollback_gradual_rollout(self, sample_pools, temp_state_file, temp_backup_dir):
        """测试回滚渐进式上线"""
        original, new = sample_pools
        
        # 创建模拟的筛选结果
        mock_results = []
        for code in new:
            mock_result = MagicMock()
            mock_result.passed = True
            mock_result.code = code
            mock_results.append(mock_result)
        
        config = RolloutConfig(canary_observation_hours=0)
        
        with patch('core.stock_screener.system_integrator.get_rollout_manager') as mock_get_manager:
            manager = GradualRolloutManager(state_file=temp_state_file, backup_dir=temp_backup_dir)
            mock_get_manager.return_value = manager
            
            integrator = SystemIntegrator()
            integrator.integrate_with_gradual_rollout(mock_results, original, config)
            integrator.advance_gradual_rollout()
            
            result = integrator.rollback_gradual_rollout("测试回滚")
            
            assert result.success is True
    
    def test_get_gradual_rollout_report(self, sample_pools, temp_state_file, temp_backup_dir):
        """测试获取渐进式上线报告"""
        original, new = sample_pools
        
        # 创建模拟的筛选结果
        mock_results = []
        for code in new:
            mock_result = MagicMock()
            mock_result.passed = True
            mock_result.code = code
            mock_results.append(mock_result)
        
        with patch('core.stock_screener.system_integrator.get_rollout_manager') as mock_get_manager, \
             patch('core.stock_screener.system_integrator.get_rollout_reporter') as mock_get_reporter:
            manager = GradualRolloutManager(state_file=temp_state_file, backup_dir=temp_backup_dir)
            mock_get_manager.return_value = manager
            
            from core.stock_screener.gradual_rollout import RolloutReporter
            reporter = RolloutReporter(manager)
            mock_get_reporter.return_value = reporter
            
            integrator = SystemIntegrator()
            integrator.integrate_with_gradual_rollout(mock_results, original)
            
            report = integrator.get_gradual_rollout_report()
            
            assert '渐进式上线' in report or 'ROLLOUT' in report
    
    def test_no_active_rollout_operations(self, temp_state_file, temp_backup_dir):
        """测试无活跃上线时的操作"""
        with patch('core.stock_screener.system_integrator.get_rollout_manager') as mock_get_manager:
            manager = GradualRolloutManager(state_file=temp_state_file, backup_dir=temp_backup_dir)
            mock_get_manager.return_value = manager
            
            integrator = SystemIntegrator()
            
            # 推进应该失败
            result = integrator.advance_gradual_rollout()
            assert result.success is False
            
            # 回滚应该失败
            result = integrator.rollback_gradual_rollout("测试")
            assert result.success is False


class TestGradualRolloutEndToEnd:
    """端到端测试渐进式上线流程"""
    
    def test_full_rollout_cycle(self, temp_dirs, sample_pools, temp_state_file, temp_backup_dir):
        """测试完整的渐进式上线周期"""
        temp_dir, history_file = temp_dirs
        original, new = sample_pools
        
        config = RolloutConfig(
            canary_observation_hours=0,
            early_adopter_observation_hours=0,
            gradual_observation_hours=0,
            majority_observation_hours=0
        )
        
        with patch('core.stock_screener.pool_updater.get_rollout_manager') as mock_get_manager:
            manager = GradualRolloutManager(state_file=temp_state_file, backup_dir=temp_backup_dir)
            mock_get_manager.return_value = manager
            
            updater = PoolUpdater(history_file=history_file)
            
            # 启动
            success, _, _ = updater.start_gradual_update(original, new, config)
            assert success is True
            
            # 推进到金丝雀
            updater.record_rollout_success()
            success, _, details = updater.advance_gradual_update()
            assert success is True
            assert details.get('current_phase') == 'canary'
            
            # 推进到早期采用
            updater.record_rollout_success()
            success, _, details = updater.advance_gradual_update()
            assert success is True
            assert details.get('current_phase') == 'early_adopter'
            
            # 推进到渐进扩展
            updater.record_rollout_success()
            success, _, details = updater.advance_gradual_update()
            assert success is True
            assert details.get('current_phase') == 'gradual'
            
            # 推进到大多数
            updater.record_rollout_success()
            success, _, details = updater.advance_gradual_update()
            assert success is True
            assert details.get('current_phase') == 'majority'
            
            # 推进到全量
            updater.record_rollout_success()
            success, _, details = updater.advance_gradual_update()
            assert success is True
            assert details.get('current_phase') == 'full'
            assert details.get('status') == 'completed'
            
            # 验证最终股票池
            pool = updater.get_active_pool_from_rollout()
            assert len(pool) == len(new)
