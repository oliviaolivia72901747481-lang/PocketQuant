"""
渐进式上线策略测试模块

测试渐进式上线管理器的核心功能
"""

import pytest
import os
import json
import tempfile
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from core.stock_screener.gradual_rollout import (
    GradualRolloutManager,
    RolloutValidator,
    RolloutReporter,
    RolloutConfig,
    RolloutState,
    RolloutPhase,
    RolloutStatus,
    PhaseMetrics,
    get_rollout_manager,
    reset_rollout_manager,
    start_gradual_rollout,
    advance_rollout,
    rollback_rollout,
    get_rollout_status,
    get_active_pool,
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
def sample_original_pool():
    """示例原始股票池"""
    return ['000001', '000002', '000003', '000004', '000005']


@pytest.fixture
def sample_new_pool():
    """示例新股票池"""
    return ['000001', '000002', '000003', '000004', '000005', 
            '000006', '000007', '000008', '000009', '000010']


@pytest.fixture
def rollout_manager(temp_state_file, temp_backup_dir):
    """创建测试用的上线管理器"""
    manager = GradualRolloutManager(
        state_file=temp_state_file,
        backup_dir=temp_backup_dir
    )
    return manager


class TestRolloutConfig:
    """测试上线配置"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = RolloutConfig()
        
        assert config.canary_percent == 10.0
        assert config.early_adopter_percent == 25.0
        assert config.gradual_percent == 50.0
        assert config.majority_percent == 75.0
        assert config.auto_advance is False
        assert config.auto_rollback_on_error is True
    
    def test_config_to_dict(self):
        """测试配置转换为字典"""
        config = RolloutConfig(canary_percent=15.0)
        config_dict = config.to_dict()
        
        assert config_dict['canary_percent'] == 15.0
        assert 'auto_advance' in config_dict
    
    def test_config_from_dict(self):
        """测试从字典创建配置"""
        data = {
            'canary_percent': 20.0,
            'auto_advance': True
        }
        config = RolloutConfig.from_dict(data)
        
        assert config.canary_percent == 20.0
        assert config.auto_advance is True


class TestPhaseMetrics:
    """测试阶段指标"""
    
    def test_success_rate_calculation(self):
        """测试成功率计算"""
        metrics = PhaseMetrics(
            phase=RolloutPhase.CANARY,
            start_time=datetime.now(),
            success_count=90,
            error_count=10
        )
        
        assert metrics.success_rate == 90.0
        assert metrics.error_rate == 10.0
    
    def test_success_rate_zero_operations(self):
        """测试零操作时的成功率"""
        metrics = PhaseMetrics(
            phase=RolloutPhase.CANARY,
            start_time=datetime.now()
        )
        
        assert metrics.success_rate == 100.0
        assert metrics.error_rate == 0.0
    
    def test_duration_hours(self):
        """测试持续时间计算"""
        start = datetime.now() - timedelta(hours=2)
        metrics = PhaseMetrics(
            phase=RolloutPhase.CANARY,
            start_time=start
        )
        
        assert metrics.duration_hours >= 2.0


class TestGradualRolloutManager:
    """测试渐进式上线管理器"""
    
    def test_start_rollout(self, rollout_manager, sample_original_pool, sample_new_pool):
        """测试开始上线"""
        state = rollout_manager.start_rollout(sample_original_pool, sample_new_pool)
        
        assert state is not None
        assert state.status == RolloutStatus.IN_PROGRESS
        assert state.current_phase == RolloutPhase.NOT_STARTED
        assert len(state.original_pool) == 5
        assert len(state.new_pool) == 10
    
    def test_start_rollout_with_custom_config(self, rollout_manager, sample_original_pool, sample_new_pool):
        """测试使用自定义配置开始上线"""
        config = RolloutConfig(canary_percent=20.0)
        state = rollout_manager.start_rollout(sample_original_pool, sample_new_pool, config)
        
        assert state.config.canary_percent == 20.0
    
    def test_advance_to_canary(self, rollout_manager, sample_original_pool, sample_new_pool):
        """测试推进到金丝雀阶段"""
        rollout_manager.start_rollout(sample_original_pool, sample_new_pool)
        success, message = rollout_manager.advance_to_next_phase()
        
        assert success is True
        assert rollout_manager.current_state.current_phase == RolloutPhase.CANARY
    
    def test_advance_multiple_phases(self, rollout_manager, sample_original_pool, sample_new_pool):
        """测试多阶段推进"""
        config = RolloutConfig(
            canary_observation_hours=0,
            early_adopter_observation_hours=0,
            gradual_observation_hours=0,
            majority_observation_hours=0
        )
        rollout_manager.start_rollout(sample_original_pool, sample_new_pool, config)
        
        # 推进到金丝雀
        rollout_manager.advance_to_next_phase()
        assert rollout_manager.current_state.current_phase == RolloutPhase.CANARY
        
        # 模拟成功操作
        rollout_manager.record_success()
        
        # 推进到早期采用
        rollout_manager.advance_to_next_phase()
        assert rollout_manager.current_state.current_phase == RolloutPhase.EARLY_ADOPTER
    
    def test_pause_and_resume(self, rollout_manager, sample_original_pool, sample_new_pool):
        """测试暂停和恢复"""
        rollout_manager.start_rollout(sample_original_pool, sample_new_pool)
        
        # 暂停
        success, _ = rollout_manager.pause_rollout()
        assert success is True
        assert rollout_manager.current_state.status == RolloutStatus.PAUSED
        
        # 恢复
        success, _ = rollout_manager.resume_rollout()
        assert success is True
        assert rollout_manager.current_state.status == RolloutStatus.IN_PROGRESS
    
    def test_rollback(self, rollout_manager, sample_original_pool, sample_new_pool):
        """测试回滚"""
        rollout_manager.start_rollout(sample_original_pool, sample_new_pool)
        rollout_manager.advance_to_next_phase()
        
        success, _ = rollout_manager.rollback("测试回滚")
        
        assert success is True
        assert rollout_manager.current_state.status == RolloutStatus.ROLLED_BACK
        assert rollout_manager.current_state.active_pool == sample_original_pool
    
    def test_auto_rollback_on_errors(self, rollout_manager, sample_original_pool, sample_new_pool):
        """测试错误自动回滚"""
        config = RolloutConfig(
            auto_rollback_on_error=True,
            rollback_error_threshold=3
        )
        rollout_manager.start_rollout(sample_original_pool, sample_new_pool, config)
        rollout_manager.advance_to_next_phase()
        
        # 记录连续错误
        rollout_manager.record_error("错误1")
        rollout_manager.record_error("错误2")
        triggered, _ = rollout_manager.record_error("错误3")
        
        assert triggered is True
        assert rollout_manager.current_state.status == RolloutStatus.ROLLED_BACK
    
    def test_record_success_resets_errors(self, rollout_manager, sample_original_pool, sample_new_pool):
        """测试成功操作重置错误计数"""
        rollout_manager.start_rollout(sample_original_pool, sample_new_pool)
        rollout_manager.advance_to_next_phase()
        
        rollout_manager.record_error("错误1")
        rollout_manager.record_error("错误2")
        assert rollout_manager.current_state.consecutive_errors == 2
        
        rollout_manager.record_success()
        assert rollout_manager.current_state.consecutive_errors == 0
    
    def test_get_current_pool(self, rollout_manager, sample_original_pool, sample_new_pool):
        """测试获取当前股票池"""
        rollout_manager.start_rollout(sample_original_pool, sample_new_pool)
        
        pool = rollout_manager.get_current_pool()
        assert pool == sample_original_pool
    
    def test_get_rollout_progress(self, rollout_manager, sample_original_pool, sample_new_pool):
        """测试获取上线进度"""
        rollout_manager.start_rollout(sample_original_pool, sample_new_pool)
        rollout_manager.advance_to_next_phase()
        
        progress = rollout_manager.get_rollout_progress()
        
        assert progress['has_active_rollout'] is True
        assert progress['current_phase'] == 'canary'
        assert progress['original_pool_size'] == 5
        assert progress['new_pool_size'] == 10
    
    def test_state_persistence(self, temp_state_file, temp_backup_dir, sample_original_pool, sample_new_pool):
        """测试状态持久化"""
        # 创建并启动上线
        manager1 = GradualRolloutManager(temp_state_file, temp_backup_dir)
        manager1.start_rollout(sample_original_pool, sample_new_pool)
        manager1.advance_to_next_phase()
        rollout_id = manager1.current_state.rollout_id
        
        # 创建新实例，应该加载之前的状态
        manager2 = GradualRolloutManager(temp_state_file, temp_backup_dir)
        
        assert manager2.current_state is not None
        assert manager2.current_state.rollout_id == rollout_id
        assert manager2.current_state.current_phase == RolloutPhase.CANARY


class TestRolloutValidator:
    """测试上线验证器"""
    
    def test_validate_phase_integrity(self):
        """测试阶段验证 - 完整性检查"""
        validator = RolloutValidator()
        
        original = ['000001', '000002', '000003']
        active = ['000001', '000002', '000003', '000004']
        
        passed, results = validator.validate_phase(
            RolloutPhase.CANARY,
            active,
            original
        )
        
        # 应该通过，因为原始股票都在活跃池中
        integrity_check = next(c for c in results['checks'] if c['name'] == '股票池完整性')
        assert integrity_check['passed'] is True
    
    def test_validate_phase_missing_stocks(self):
        """测试阶段验证 - 缺失股票"""
        validator = RolloutValidator()
        
        original = ['000001', '000002', '000003']
        active = ['000001', '000002']  # 缺少 000003
        
        passed, results = validator.validate_phase(
            RolloutPhase.CANARY,
            active,
            original
        )
        
        integrity_check = next(c for c in results['checks'] if c['name'] == '股票池完整性')
        assert integrity_check['passed'] is False


class TestRolloutReporter:
    """测试上线报告生成器"""
    
    def test_generate_progress_report_no_rollout(self, rollout_manager):
        """测试无上线时的进度报告"""
        reporter = RolloutReporter(rollout_manager)
        report = reporter.generate_progress_report()
        
        assert "没有正在进行的上线任务" in report
    
    def test_generate_progress_report_with_rollout(self, rollout_manager, sample_original_pool, sample_new_pool):
        """测试有上线时的进度报告"""
        rollout_manager.start_rollout(sample_original_pool, sample_new_pool)
        rollout_manager.advance_to_next_phase()
        
        reporter = RolloutReporter(rollout_manager)
        report = reporter.generate_progress_report()
        
        assert "渐进式上线进度报告" in report
        assert "canary" in report.lower()
    
    def test_generate_phase_report(self):
        """测试阶段报告生成"""
        metrics = PhaseMetrics(
            phase=RolloutPhase.CANARY,
            start_time=datetime.now() - timedelta(hours=1),
            stocks_count=10,
            success_count=95,
            error_count=5
        )
        
        manager = MagicMock()
        reporter = RolloutReporter(manager)
        report = reporter.generate_phase_report(metrics)
        
        assert "canary" in report.lower()
        assert "95" in report


class TestConvenienceFunctions:
    """测试便捷函数"""
    
    def test_reset_rollout_manager(self):
        """测试重置管理器"""
        reset_rollout_manager()
        manager = get_rollout_manager()
        assert manager is not None
    
    def test_get_rollout_status_no_rollout(self):
        """测试无上线时获取状态"""
        reset_rollout_manager()
        status = get_rollout_status()
        assert status['has_active_rollout'] is False


class TestPoolCalculation:
    """测试股票池计算"""
    
    def test_canary_pool_calculation(self, rollout_manager, sample_original_pool, sample_new_pool):
        """测试金丝雀阶段股票池计算"""
        config = RolloutConfig(canary_percent=20.0)  # 20% of new stocks
        rollout_manager.start_rollout(sample_original_pool, sample_new_pool, config)
        rollout_manager.advance_to_next_phase()
        
        active_pool = rollout_manager.get_current_pool()
        
        # 原始5只 + 20%的新增5只 = 5 + 1 = 6只
        assert len(active_pool) >= len(sample_original_pool)
        # 确保原始股票都在
        for code in sample_original_pool:
            assert code in active_pool
    
    def test_full_rollout_pool(self, rollout_manager, sample_original_pool, sample_new_pool):
        """测试全量发布股票池"""
        config = RolloutConfig(
            canary_observation_hours=0,
            early_adopter_observation_hours=0,
            gradual_observation_hours=0,
            majority_observation_hours=0
        )
        rollout_manager.start_rollout(sample_original_pool, sample_new_pool, config)
        
        # 推进到全量
        for _ in range(5):  # NOT_STARTED -> CANARY -> EARLY_ADOPTER -> GRADUAL -> MAJORITY -> FULL
            rollout_manager.record_success()
            rollout_manager.advance_to_next_phase()
        
        assert rollout_manager.current_state.current_phase == RolloutPhase.FULL
        assert rollout_manager.current_state.status == RolloutStatus.COMPLETED
        
        active_pool = rollout_manager.get_current_pool()
        assert len(active_pool) == len(sample_new_pool)
