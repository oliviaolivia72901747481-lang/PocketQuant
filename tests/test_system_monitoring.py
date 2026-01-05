"""
系统监控模块测试

测试系统监控和告警机制的核心功能

Requirements: 5.2, 5.5, 13.2
"""

import pytest
import os
import json
import tempfile
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from core.stock_screener.monitoring import (
    HealthChecker,
    HealthStatus,
    HealthCheckResult,
    ComponentType,
    AlertManager,
    AlertSeverity,
    SystemAlert,
    MaintenanceScheduler,
    MaintenanceTask,
    SystemMonitor,
    EnhancedSystemMonitor,
    AlertNotifier,
    AlertNotificationConfig,
    AlertThresholds,
    MetricsCollector,
    get_health_checker,
    get_system_alert_manager,
    get_maintenance_scheduler,
    get_system_monitor,
    get_enhanced_system_monitor,
    get_alert_notifier,
    get_metrics_collector,
    reset_enhanced_monitor,
)


class TestHealthChecker:
    """健康检查器测试"""
    
    def test_health_checker_initialization(self):
        """测试健康检查器初始化"""
        checker = HealthChecker()
        assert checker.check_interval == 60
        assert isinstance(checker.check_results, dict)
    
    def test_check_all_returns_results(self):
        """测试执行所有健康检查"""
        checker = HealthChecker()
        results = checker.check_all()
        
        assert isinstance(results, list)
        assert len(results) > 0
        
        for result in results:
            assert isinstance(result, HealthCheckResult)
            assert result.component is not None
            assert result.status in HealthStatus
    
    def test_get_overall_status_healthy(self):
        """测试整体健康状态判断"""
        checker = HealthChecker()
        
        # 模拟所有组件健康
        checker.check_results = {
            'comp1': HealthCheckResult(
                component='comp1',
                component_type=ComponentType.SYSTEM,
                status=HealthStatus.HEALTHY,
                message='OK'
            ),
            'comp2': HealthCheckResult(
                component='comp2',
                component_type=ComponentType.DATA_SOURCE,
                status=HealthStatus.HEALTHY,
                message='OK'
            )
        }
        
        assert checker.get_overall_status() == HealthStatus.HEALTHY
    
    def test_get_overall_status_degraded(self):
        """测试降级状态判断"""
        checker = HealthChecker()
        
        checker.check_results = {
            'comp1': HealthCheckResult(
                component='comp1',
                component_type=ComponentType.SYSTEM,
                status=HealthStatus.HEALTHY,
                message='OK'
            ),
            'comp2': HealthCheckResult(
                component='comp2',
                component_type=ComponentType.DATA_SOURCE,
                status=HealthStatus.DEGRADED,
                message='Slow'
            )
        }
        
        assert checker.get_overall_status() == HealthStatus.DEGRADED
    
    def test_get_overall_status_unhealthy(self):
        """测试不健康状态判断"""
        checker = HealthChecker()
        
        checker.check_results = {
            'comp1': HealthCheckResult(
                component='comp1',
                component_type=ComponentType.SYSTEM,
                status=HealthStatus.UNHEALTHY,
                message='Failed'
            )
        }
        
        assert checker.get_overall_status() == HealthStatus.UNHEALTHY


class TestAlertManager:
    """告警管理器测试"""
    
    def test_alert_manager_initialization(self):
        """测试告警管理器初始化"""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            manager = AlertManager(alert_file=temp_file)
            assert isinstance(manager.alerts, list)
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)
    
    def test_create_alert(self):
        """测试创建告警"""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            manager = AlertManager(alert_file=temp_file)
            
            alert = manager.create_alert(
                severity=AlertSeverity.WARNING,
                component='TestComponent',
                title='Test Alert',
                message='This is a test alert'
            )
            
            assert alert.alert_id.startswith('ALERT_')
            assert alert.severity == AlertSeverity.WARNING
            assert alert.component == 'TestComponent'
            assert alert.title == 'Test Alert'
            assert alert.message == 'This is a test alert'
            assert not alert.acknowledged
            assert not alert.resolved
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)
    
    def test_acknowledge_alert(self):
        """测试确认告警"""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            manager = AlertManager(alert_file=temp_file)
            alert = manager.create_alert(
                severity=AlertSeverity.ERROR,
                component='Test',
                title='Test',
                message='Test'
            )
            
            result = manager.acknowledge_alert(alert.alert_id)
            assert result is True
            assert alert.acknowledged is True
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)
    
    def test_resolve_alert(self):
        """测试解决告警"""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            manager = AlertManager(alert_file=temp_file)
            alert = manager.create_alert(
                severity=AlertSeverity.ERROR,
                component='Test',
                title='Test',
                message='Test'
            )
            
            result = manager.resolve_alert(alert.alert_id)
            assert result is True
            assert alert.resolved is True
            assert alert.resolved_at is not None
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)
    
    def test_get_active_alerts(self):
        """测试获取活跃告警"""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            manager = AlertManager(alert_file=temp_file)
            
            # 创建两个告警
            alert1 = manager.create_alert(
                severity=AlertSeverity.WARNING,
                component='Test1',
                title='Test1',
                message='Test1'
            )
            alert2 = manager.create_alert(
                severity=AlertSeverity.ERROR,
                component='Test2',
                title='Test2',
                message='Test2'
            )
            
            # 解决一个
            manager.resolve_alert(alert1.alert_id)
            
            active = manager.get_active_alerts()
            assert len(active) == 1
            assert active[0].alert_id == alert2.alert_id
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)
    
    def test_get_alert_summary(self):
        """测试获取告警摘要"""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            manager = AlertManager(alert_file=temp_file)
            
            manager.create_alert(AlertSeverity.WARNING, 'Test', 'Test', 'Test')
            manager.create_alert(AlertSeverity.ERROR, 'Test', 'Test', 'Test')
            manager.create_alert(AlertSeverity.CRITICAL, 'Test', 'Test', 'Test')
            
            summary = manager.get_alert_summary()
            
            assert summary['total'] == 3
            assert summary['active'] == 3
            assert summary['by_severity']['warning'] == 1
            assert summary['by_severity']['error'] == 1
            assert summary['by_severity']['critical'] == 1
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)


class TestMaintenanceScheduler:
    """维护调度器测试"""
    
    def test_scheduler_initialization(self):
        """测试调度器初始化"""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            scheduler = MaintenanceScheduler(schedule_file=temp_file)
            tasks = scheduler.get_all_tasks()
            
            assert len(tasks) > 0
            assert all(isinstance(t, MaintenanceTask) for t in tasks)
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)
    
    def test_enable_disable_task(self):
        """测试启用/禁用任务"""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            scheduler = MaintenanceScheduler(schedule_file=temp_file)
            tasks = scheduler.get_all_tasks()
            
            if tasks:
                task_id = tasks[0].task_id
                
                # 禁用
                scheduler.disable_task(task_id)
                task = scheduler.get_task(task_id)
                assert task.enabled is False
                
                # 启用
                scheduler.enable_task(task_id)
                task = scheduler.get_task(task_id)
                assert task.enabled is True
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)
    
    def test_record_task_run(self):
        """测试记录任务执行"""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            scheduler = MaintenanceScheduler(schedule_file=temp_file)
            tasks = scheduler.get_all_tasks()
            
            if tasks:
                task_id = tasks[0].task_id
                
                scheduler.record_task_run(task_id)
                task = scheduler.get_task(task_id)
                
                assert task.last_run is not None
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)


class TestAlertNotifier:
    """告警通知器测试"""
    
    def test_notifier_initialization(self):
        """测试通知器初始化"""
        config = AlertNotificationConfig(
            enabled=True,
            min_severity=AlertSeverity.WARNING
        )
        notifier = AlertNotifier(config)
        
        assert notifier.config.enabled is True
        assert notifier.config.min_severity == AlertSeverity.WARNING
    
    def test_should_notify_disabled(self):
        """测试禁用时不通知"""
        config = AlertNotificationConfig(enabled=False)
        notifier = AlertNotifier(config)
        
        alert = SystemAlert(
            alert_id='TEST_001',
            severity=AlertSeverity.CRITICAL,
            component='Test',
            title='Test',
            message='Test'
        )
        
        assert notifier.should_notify(alert) is False
    
    def test_should_notify_severity_filter(self):
        """测试严重程度过滤"""
        config = AlertNotificationConfig(
            enabled=True,
            min_severity=AlertSeverity.ERROR
        )
        notifier = AlertNotifier(config)
        
        # INFO级别不应通知
        info_alert = SystemAlert(
            alert_id='TEST_001',
            severity=AlertSeverity.INFO,
            component='Test',
            title='Test',
            message='Test'
        )
        assert notifier.should_notify(info_alert) is False
        
        # WARNING级别不应通知
        warning_alert = SystemAlert(
            alert_id='TEST_002',
            severity=AlertSeverity.WARNING,
            component='Test',
            title='Test',
            message='Test'
        )
        assert notifier.should_notify(warning_alert) is False
        
        # ERROR级别应该通知
        error_alert = SystemAlert(
            alert_id='TEST_003',
            severity=AlertSeverity.ERROR,
            component='Test',
            title='Test',
            message='Test'
        )
        assert notifier.should_notify(error_alert) is True
    
    def test_cooldown_period(self):
        """测试冷却时间"""
        config = AlertNotificationConfig(
            enabled=True,
            min_severity=AlertSeverity.WARNING,
            cooldown_minutes=5
        )
        notifier = AlertNotifier(config)
        
        alert = SystemAlert(
            alert_id='TEST_001',
            severity=AlertSeverity.ERROR,
            component='TestComp',
            title='TestTitle',
            message='Test'
        )
        
        # 第一次应该通知
        assert notifier.should_notify(alert) is True
        
        # 模拟已发送
        notifier._last_alert_times['TestComp:TestTitle'] = datetime.now()
        
        # 冷却期内不应通知
        assert notifier.should_notify(alert) is False


class TestMetricsCollector:
    """指标收集器测试"""
    
    def test_collector_initialization(self):
        """测试收集器初始化"""
        collector = MetricsCollector()
        assert collector._max_history == 1000
        assert isinstance(collector._metrics_history, list)
    
    def test_collect_metrics(self):
        """测试收集指标"""
        collector = MetricsCollector()
        metrics = collector.collect_metrics()
        
        assert 'timestamp' in metrics
        assert 'disk' in metrics
        assert 'data' in metrics
        assert 'screening' in metrics
        assert 'errors' in metrics
    
    def test_get_metrics_history(self):
        """测试获取指标历史"""
        collector = MetricsCollector()
        
        # 收集几次指标
        collector.collect_metrics()
        collector.collect_metrics()
        collector.collect_metrics()
        
        history = collector.get_metrics_history(limit=2)
        assert len(history) == 2


class TestEnhancedSystemMonitor:
    """增强版系统监控器测试"""
    
    def test_enhanced_monitor_initialization(self):
        """测试增强版监控器初始化"""
        reset_enhanced_monitor()
        
        config = AlertNotificationConfig(enabled=True)
        thresholds = AlertThresholds()
        
        monitor = EnhancedSystemMonitor(config, thresholds)
        
        assert monitor.notifier is not None
        assert monitor.thresholds is not None
        assert monitor.metrics_collector is not None
    
    def test_get_enhanced_status(self):
        """测试获取增强版状态"""
        reset_enhanced_monitor()
        
        monitor = EnhancedSystemMonitor()
        status = monitor.get_enhanced_status()
        
        assert 'timestamp' in status
        assert 'overall_health' in status
        assert 'health_checks' in status
        assert 'alerts' in status
        assert 'metrics' in status
        assert 'notification' in status
        assert 'thresholds' in status
    
    def test_generate_enhanced_report(self):
        """测试生成增强版报告"""
        reset_enhanced_monitor()
        
        monitor = EnhancedSystemMonitor()
        report = monitor.generate_enhanced_report()
        
        assert isinstance(report, str)
        assert '系统监控状态报告' in report
        assert '组件健康状态' in report
        assert '告警摘要' in report
        assert '系统指标' in report


class TestGlobalFunctions:
    """全局函数测试"""
    
    def test_get_health_checker(self):
        """测试获取健康检查器"""
        checker = get_health_checker()
        assert isinstance(checker, HealthChecker)
    
    def test_get_system_monitor(self):
        """测试获取系统监控器"""
        monitor = get_system_monitor()
        assert isinstance(monitor, SystemMonitor)
    
    def test_get_enhanced_system_monitor(self):
        """测试获取增强版系统监控器"""
        reset_enhanced_monitor()
        monitor = get_enhanced_system_monitor()
        assert isinstance(monitor, EnhancedSystemMonitor)
    
    def test_get_alert_notifier(self):
        """测试获取告警通知器"""
        reset_enhanced_monitor()
        notifier = get_alert_notifier()
        assert isinstance(notifier, AlertNotifier)
    
    def test_get_metrics_collector(self):
        """测试获取指标收集器"""
        reset_enhanced_monitor()
        collector = get_metrics_collector()
        assert isinstance(collector, MetricsCollector)


class TestSystemMonitorIntegration:
    """系统监控集成测试"""
    
    def test_full_monitoring_cycle(self):
        """测试完整监控周期"""
        reset_enhanced_monitor()
        
        # 创建监控器
        config = AlertNotificationConfig(
            enabled=True,
            min_severity=AlertSeverity.WARNING,
            notification_channels=["log"]
        )
        monitor = EnhancedSystemMonitor(config)
        
        # 执行健康检查
        results = monitor.health_checker.check_all()
        assert len(results) > 0
        
        # 检查阈值
        alerts = monitor.check_thresholds()
        assert isinstance(alerts, list)
        
        # 获取状态
        status = monitor.get_enhanced_status()
        assert status['overall_health'] in ['healthy', 'degraded', 'unhealthy', 'unknown']
        
        # 生成报告
        report = monitor.generate_enhanced_report()
        assert len(report) > 0
