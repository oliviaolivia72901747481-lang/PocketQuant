"""
系统稳定性追踪器测试

测试稳定性追踪和验证功能
"""

import pytest
import os
import json
import tempfile
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from core.stock_screener.stability_tracker import (
    StabilityTracker,
    StabilityValidator,
    StabilityMetrics,
    OperationRecord,
    OperationType,
    OperationStatus,
    get_stability_tracker,
    get_stability_validator,
    reset_stability_tracker,
)


class TestOperationRecord:
    """测试操作记录"""
    
    def test_create_operation_record(self):
        """测试创建操作记录"""
        record = OperationRecord(
            operation_id="OP_001",
            operation_type=OperationType.DATA_FETCH,
            status=OperationStatus.SUCCESS,
            timestamp=datetime.now(),
            duration_ms=100.0
        )
        
        assert record.operation_id == "OP_001"
        assert record.operation_type == OperationType.DATA_FETCH
        assert record.status == OperationStatus.SUCCESS
        assert record.duration_ms == 100.0
    
    def test_operation_record_to_dict(self):
        """测试操作记录转换为字典"""
        timestamp = datetime.now()
        record = OperationRecord(
            operation_id="OP_001",
            operation_type=OperationType.SCREENING,
            status=OperationStatus.FAILURE,
            timestamp=timestamp,
            duration_ms=500.0,
            error_message="测试错误"
        )
        
        data = record.to_dict()
        
        assert data['operation_id'] == "OP_001"
        assert data['operation_type'] == "screening"
        assert data['status'] == "failure"
        assert data['error_message'] == "测试错误"
    
    def test_operation_record_from_dict(self):
        """测试从字典创建操作记录"""
        data = {
            'operation_id': "OP_002",
            'operation_type': "scoring",
            'status': "success",
            'timestamp': datetime.now().isoformat(),
            'duration_ms': 200.0,
            'error_message': None,
            'details': {'key': 'value'}
        }
        
        record = OperationRecord.from_dict(data)
        
        assert record.operation_id == "OP_002"
        assert record.operation_type == OperationType.SCORING
        assert record.status == OperationStatus.SUCCESS


class TestStabilityMetrics:
    """测试稳定性指标"""
    
    def test_stability_rate_calculation(self):
        """测试稳定性率计算"""
        metrics = StabilityMetrics(
            total_operations=100,
            successful_operations=99,
            failed_operations=1
        )
        
        assert metrics.stability_rate == 99.0
        assert metrics.failure_rate == 1.0
    
    def test_stability_rate_empty(self):
        """测试空操作时的稳定性率"""
        metrics = StabilityMetrics()
        
        assert metrics.stability_rate == 100.0
        assert metrics.failure_rate == 0.0
    
    def test_meets_target(self):
        """测试是否达到目标"""
        # 达标情况
        metrics_pass = StabilityMetrics(
            total_operations=1000,
            successful_operations=996,
            failed_operations=4
        )
        assert metrics_pass.meets_target(99.5) is True
        
        # 未达标情况
        metrics_fail = StabilityMetrics(
            total_operations=1000,
            successful_operations=990,
            failed_operations=10
        )
        assert metrics_fail.meets_target(99.5) is False
    
    def test_uptime_hours(self):
        """测试运行时间计算"""
        start = datetime.now() - timedelta(hours=24)
        end = datetime.now()
        
        metrics = StabilityMetrics(
            start_time=start,
            end_time=end
        )
        
        assert 23.9 < metrics.uptime_hours < 24.1


class TestStabilityTracker:
    """测试稳定性追踪器"""
    
    @pytest.fixture
    def tracker(self):
        """创建测试用追踪器"""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            temp_file = f.name
        
        tracker = StabilityTracker(history_file=temp_file)
        yield tracker
        
        # 清理
        if os.path.exists(temp_file):
            os.remove(temp_file)
    
    def test_record_success(self, tracker):
        """测试记录成功操作"""
        record = tracker.record_success(
            OperationType.DATA_FETCH,
            duration_ms=100.0
        )
        
        assert record.status == OperationStatus.SUCCESS
        assert record.operation_type == OperationType.DATA_FETCH
        assert len(tracker.records) == 1
    
    def test_record_failure(self, tracker):
        """测试记录失败操作"""
        record = tracker.record_failure(
            OperationType.SCREENING,
            error_message="测试错误",
            duration_ms=500.0
        )
        
        assert record.status == OperationStatus.FAILURE
        assert record.error_message == "测试错误"
    
    def test_record_timeout(self, tracker):
        """测试记录超时操作"""
        record = tracker.record_timeout(
            OperationType.SCORING,
            duration_ms=30000.0
        )
        
        assert record.status == OperationStatus.TIMEOUT
    
    def test_get_metrics(self, tracker):
        """测试获取稳定性指标"""
        # 记录一些操作
        for _ in range(99):
            tracker.record_success(OperationType.DATA_FETCH)
        tracker.record_failure(OperationType.DATA_FETCH, "错误")
        
        metrics = tracker.get_metrics()
        
        assert metrics.total_operations == 100
        assert metrics.successful_operations == 99
        assert metrics.failed_operations == 1
        assert metrics.stability_rate == 99.0
    
    def test_get_metrics_by_type(self, tracker):
        """测试按类型获取指标"""
        tracker.record_success(OperationType.DATA_FETCH)
        tracker.record_success(OperationType.SCREENING)
        tracker.record_failure(OperationType.SCREENING, "错误")
        
        metrics = tracker.get_metrics(operation_type=OperationType.SCREENING)
        
        assert metrics.total_operations == 2
        assert metrics.successful_operations == 1
        assert metrics.failed_operations == 1
    
    def test_check_stability_target(self, tracker):
        """测试检查稳定性目标"""
        # 记录高稳定性操作
        for _ in range(998):
            tracker.record_success(OperationType.DATA_FETCH)
        for _ in range(2):
            tracker.record_failure(OperationType.DATA_FETCH, "错误")
        
        meets_target, rate, message = tracker.check_stability_target()
        
        assert meets_target is True
        assert rate == 99.8
        assert "达标" in message
    
    def test_check_stability_target_fail(self, tracker):
        """测试稳定性目标未达标"""
        # 记录低稳定性操作
        for _ in range(98):
            tracker.record_success(OperationType.DATA_FETCH)
        for _ in range(2):
            tracker.record_failure(OperationType.DATA_FETCH, "错误")
        
        meets_target, rate, message = tracker.check_stability_target()
        
        assert meets_target is False
        assert rate == 98.0
        assert "未达标" in message
    
    def test_get_recent_failures(self, tracker):
        """测试获取最近失败记录"""
        tracker.record_success(OperationType.DATA_FETCH)
        tracker.record_failure(OperationType.SCREENING, "错误1")
        tracker.record_failure(OperationType.SCORING, "错误2")
        
        failures = tracker.get_recent_failures(count=5)
        
        assert len(failures) == 2
        assert failures[0].error_message == "错误1"
        assert failures[1].error_message == "错误2"
    
    def test_save_and_load_history(self, tracker):
        """测试保存和加载历史"""
        tracker.record_success(OperationType.DATA_FETCH)
        tracker.record_failure(OperationType.SCREENING, "错误")
        
        # 保存
        assert tracker.save_history() is True
        
        # 创建新追踪器加载历史
        new_tracker = StabilityTracker(history_file=tracker.history_file)
        
        assert len(new_tracker.records) == 2
    
    def test_generate_report(self, tracker):
        """测试生成报告"""
        for _ in range(99):
            tracker.record_success(OperationType.DATA_FETCH)
        tracker.record_failure(OperationType.DATA_FETCH, "测试错误")
        
        report = tracker.generate_report(time_range_hours=24)
        
        assert "系统稳定性报告" in report
        assert "99.00%" in report
        assert "达标" in report


class TestStabilityValidator:
    """测试稳定性验证器"""
    
    @pytest.fixture
    def validator(self):
        """创建测试用验证器"""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            temp_file = f.name
        
        tracker = StabilityTracker(history_file=temp_file)
        validator = StabilityValidator(tracker=tracker)
        yield validator
        
        # 清理
        if os.path.exists(temp_file):
            os.remove(temp_file)
    
    def test_validate_stability_insufficient_data(self, validator):
        """测试数据不足时的验证"""
        # 只记录少量操作
        for _ in range(5):
            validator.tracker.record_success(OperationType.DATA_FETCH)
        
        meets_target, details = validator.validate_stability(min_operations=10)
        
        assert meets_target is True
        assert details['status'] == 'insufficient_data'
    
    def test_validate_stability_pass(self, validator):
        """测试稳定性验证通过"""
        # 记录高稳定性操作
        for _ in range(998):
            validator.tracker.record_success(OperationType.DATA_FETCH)
        for _ in range(2):
            validator.tracker.record_failure(OperationType.DATA_FETCH, "错误")
        
        meets_target, details = validator.validate_stability(min_operations=10)
        
        assert meets_target is True
        assert details['status'] == 'validated'
        assert details['stability_rate'] == 99.8
    
    def test_validate_stability_fail(self, validator):
        """测试稳定性验证失败"""
        # 记录低稳定性操作
        for _ in range(90):
            validator.tracker.record_success(OperationType.DATA_FETCH)
        for _ in range(10):
            validator.tracker.record_failure(OperationType.DATA_FETCH, "错误")
        
        meets_target, details = validator.validate_stability(min_operations=10)
        
        assert meets_target is False
        assert details['stability_rate'] == 90.0


class TestGlobalInstances:
    """测试全局实例"""
    
    def setup_method(self):
        """每个测试前重置"""
        reset_stability_tracker()
    
    def test_get_stability_tracker(self):
        """测试获取稳定性追踪器"""
        tracker1 = get_stability_tracker()
        tracker2 = get_stability_tracker()
        
        assert tracker1 is tracker2
    
    def test_get_stability_validator(self):
        """测试获取稳定性验证器"""
        validator1 = get_stability_validator()
        validator2 = get_stability_validator()
        
        assert validator1 is validator2
    
    def test_reset_stability_tracker(self):
        """测试重置稳定性追踪器"""
        tracker1 = get_stability_tracker()
        reset_stability_tracker()
        tracker2 = get_stability_tracker()
        
        assert tracker1 is not tracker2


class TestStabilityTargetValidation:
    """测试99.5%稳定性目标验证"""
    
    @pytest.fixture
    def tracker(self):
        """创建测试用追踪器"""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            temp_file = f.name
        
        tracker = StabilityTracker(history_file=temp_file)
        yield tracker
        
        if os.path.exists(temp_file):
            os.remove(temp_file)
    
    def test_exactly_99_5_percent(self, tracker):
        """测试恰好99.5%稳定性"""
        # 1000次操作，995次成功，5次失败
        for _ in range(995):
            tracker.record_success(OperationType.DATA_FETCH)
        for _ in range(5):
            tracker.record_failure(OperationType.DATA_FETCH, "错误")
        
        meets_target, rate, _ = tracker.check_stability_target()
        
        assert rate == 99.5
        assert meets_target is True
    
    def test_above_99_5_percent(self, tracker):
        """测试高于99.5%稳定性"""
        # 1000次操作，998次成功，2次失败
        for _ in range(998):
            tracker.record_success(OperationType.DATA_FETCH)
        for _ in range(2):
            tracker.record_failure(OperationType.DATA_FETCH, "错误")
        
        meets_target, rate, _ = tracker.check_stability_target()
        
        assert rate == 99.8
        assert meets_target is True
    
    def test_below_99_5_percent(self, tracker):
        """测试低于99.5%稳定性"""
        # 1000次操作，994次成功，6次失败
        for _ in range(994):
            tracker.record_success(OperationType.DATA_FETCH)
        for _ in range(6):
            tracker.record_failure(OperationType.DATA_FETCH, "错误")
        
        meets_target, rate, _ = tracker.check_stability_target()
        
        assert rate == 99.4
        assert meets_target is False
    
    def test_target_constant(self, tracker):
        """测试目标常量"""
        assert StabilityTracker.TARGET_STABILITY_RATE == 99.5
