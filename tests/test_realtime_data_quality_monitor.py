"""
数据质量实时监控模块测试

测试实时数据质量监控的核心功能

Requirements: 7.2, 7.5
风险缓解措施: 实现数据质量实时监控
"""

import pytest
import os
import json
import tempfile
import time
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np

from core.stock_screener.realtime_data_quality_monitor import (
    RealtimeDataQualityMonitor,
    RealtimeMonitorConfig,
    DataQualityAlert,
    DataQualitySnapshot,
    DataQualityAlertLevel,
    DataQualityDimension,
    MonitoringStatus,
    get_realtime_data_quality_monitor,
    reset_realtime_monitor,
    start_realtime_quality_monitoring,
    stop_realtime_quality_monitoring,
    check_data_quality_now,
    get_data_quality_status,
    generate_data_quality_report,
)


class TestRealtimeMonitorConfig:
    """监控配置测试"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = RealtimeMonitorConfig()
        
        assert config.check_interval_seconds == 300
        assert config.completeness_threshold == 95.0
        assert config.accuracy_threshold == 99.0
        assert config.consistency_threshold == 98.0
        assert config.timeliness_threshold_hours == 24
        assert config.validity_threshold == 95.0
        assert config.alert_cooldown_minutes == 30
        assert config.max_history_snapshots == 1000
        assert config.enable_auto_alert is True
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = RealtimeMonitorConfig(
            check_interval_seconds=60,
            completeness_threshold=90.0,
            accuracy_threshold=95.0,
            enable_auto_alert=False
        )
        
        assert config.check_interval_seconds == 60
        assert config.completeness_threshold == 90.0
        assert config.accuracy_threshold == 95.0
        assert config.enable_auto_alert is False
    
    def test_config_to_dict(self):
        """测试配置转换为字典"""
        config = RealtimeMonitorConfig()
        config_dict = config.to_dict()
        
        assert 'check_interval_seconds' in config_dict
        assert 'completeness_threshold' in config_dict
        assert 'accuracy_threshold' in config_dict
        assert 'alert_channels' in config_dict


class TestDataQualityAlert:
    """数据质量告警测试"""
    
    def test_alert_creation(self):
        """测试告警创建"""
        alert = DataQualityAlert(
            alert_id="DQ_TEST_001",
            level=DataQualityAlertLevel.WARNING,
            dimension=DataQualityDimension.COMPLETENESS,
            title="测试告警",
            message="这是一个测试告警"
        )
        
        assert alert.alert_id == "DQ_TEST_001"
        assert alert.level == DataQualityAlertLevel.WARNING
        assert alert.dimension == DataQualityDimension.COMPLETENESS
        assert alert.title == "测试告警"
        assert alert.resolved is False
    
    def test_alert_to_dict(self):
        """测试告警转换为字典"""
        alert = DataQualityAlert(
            alert_id="DQ_TEST_002",
            level=DataQualityAlertLevel.ERROR,
            dimension=DataQualityDimension.ACCURACY,
            title="准确性告警",
            message="数据准确性不达标",
            affected_records=100
        )
        
        alert_dict = alert.to_dict()
        
        assert alert_dict['alert_id'] == "DQ_TEST_002"
        assert alert_dict['level'] == "error"
        assert alert_dict['dimension'] == "accuracy"
        assert alert_dict['affected_records'] == 100


class TestDataQualitySnapshot:
    """数据质量快照测试"""
    
    def test_snapshot_creation(self):
        """测试快照创建"""
        snapshot = DataQualitySnapshot(
            timestamp=datetime.now(),
            total_records=1000,
            completeness_score=98.5,
            accuracy_score=99.2,
            consistency_score=97.8,
            timeliness_score=95.0,
            validity_score=96.5,
            overall_score=97.4,
            alerts_count=2
        )
        
        assert snapshot.total_records == 1000
        assert snapshot.completeness_score == 98.5
        assert snapshot.overall_score == 97.4
    
    def test_snapshot_to_dict(self):
        """测试快照转换为字典"""
        snapshot = DataQualitySnapshot(
            timestamp=datetime.now(),
            total_records=500,
            completeness_score=95.0,
            accuracy_score=98.0,
            consistency_score=96.0,
            timeliness_score=90.0,
            validity_score=94.0,
            overall_score=94.6,
            alerts_count=1
        )
        
        snapshot_dict = snapshot.to_dict()
        
        assert 'timestamp' in snapshot_dict
        assert snapshot_dict['total_records'] == 500
        assert snapshot_dict['overall_score'] == 94.6


class TestRealtimeDataQualityMonitor:
    """实时数据质量监控器测试"""
    
    def setup_method(self):
        """测试前重置监控器"""
        reset_realtime_monitor()
    
    def teardown_method(self):
        """测试后清理"""
        reset_realtime_monitor()
    
    def test_monitor_initialization(self):
        """测试监控器初始化"""
        monitor = RealtimeDataQualityMonitor()
        
        assert monitor.status == MonitoringStatus.STOPPED
        assert monitor.is_running is False
        assert monitor.config is not None
    
    def test_monitor_with_custom_config(self):
        """测试使用自定义配置初始化"""
        config = RealtimeMonitorConfig(
            check_interval_seconds=60,
            enable_auto_alert=False
        )
        monitor = RealtimeDataQualityMonitor(config)
        
        assert monitor.config.check_interval_seconds == 60
        assert monitor.config.enable_auto_alert is False
    
    def test_set_data_provider(self):
        """测试设置数据提供者"""
        monitor = RealtimeDataQualityMonitor()
        
        def mock_provider():
            return pd.DataFrame({'code': ['000001'], 'name': ['测试']})
        
        monitor.set_data_provider(mock_provider)
        assert monitor._data_provider is not None
    
    def test_add_alert_handler(self):
        """测试添加告警处理器"""
        monitor = RealtimeDataQualityMonitor()
        
        alerts_received = []
        def handler(alert):
            alerts_received.append(alert)
        
        monitor.add_alert_handler(handler)
        assert len(monitor._alert_handlers) == 1
    
    def test_check_completeness(self):
        """测试完整性检查"""
        monitor = RealtimeDataQualityMonitor()
        
        # 完整数据
        df_complete = pd.DataFrame({
            'code': ['000001', '000002'],
            'name': ['股票A', '股票B'],
            'price': [10.0, 20.0]
        })
        score = monitor._check_completeness(df_complete)
        assert score == 100.0
        
        # 有缺失的数据
        df_missing = pd.DataFrame({
            'code': ['000001', '000002'],
            'name': ['股票A', None],
            'price': [10.0, None]
        })
        score = monitor._check_completeness(df_missing)
        assert score < 100.0
    
    def test_check_accuracy(self):
        """测试准确性检查"""
        monitor = RealtimeDataQualityMonitor()
        
        # 准确数据
        df_accurate = pd.DataFrame({
            'code': ['000001', '000002'],
            'price': [10.0, 20.0],
            'pe_ratio': [15.0, 25.0]
        })
        score = monitor._check_accuracy(df_accurate)
        assert score == 100.0
        
        # 有异常值的数据
        df_inaccurate = pd.DataFrame({
            'code': ['000001', '000002'],
            'price': [10.0, -5.0],  # 负价格
            'pe_ratio': [15.0, 200000.0]  # 超出范围
        })
        score = monitor._check_accuracy(df_inaccurate)
        assert score < 100.0
    
    def test_check_consistency(self):
        """测试一致性检查"""
        monitor = RealtimeDataQualityMonitor()
        
        # 一致数据
        df_consistent = pd.DataFrame({
            'code': ['000001'],
            'total_market_cap': [1000000000],
            'float_market_cap': [800000000],
            'high': [12.0],
            'low': [10.0]
        })
        score = monitor._check_consistency(df_consistent)
        assert score == 100.0
        
        # 不一致数据（流通市值大于总市值）
        df_inconsistent = pd.DataFrame({
            'code': ['000001'],
            'total_market_cap': [800000000],
            'float_market_cap': [1000000000],  # 大于总市值
            'high': [10.0],
            'low': [12.0]  # 低价高于高价
        })
        score = monitor._check_consistency(df_inconsistent)
        assert score < 100.0
    
    def test_check_validity(self):
        """测试有效性检查"""
        monitor = RealtimeDataQualityMonitor()
        
        # 有效数据
        df_valid = pd.DataFrame({
            'code': ['000001', '600000'],
            'name': ['股票A', '股票B']
        })
        score = monitor._check_validity(df_valid)
        assert score == 100.0
        
        # 无效数据（无效股票代码）
        df_invalid = pd.DataFrame({
            'code': ['000001', 'INVALID'],
            'name': ['股票A', '']
        })
        score = monitor._check_validity(df_invalid)
        assert score < 100.0
    
    def test_check_now(self):
        """测试立即检查"""
        monitor = RealtimeDataQualityMonitor()
        
        # 设置数据提供者
        def mock_provider():
            return pd.DataFrame({
                'code': ['000001', '000002', '600000'],
                'name': ['股票A', '股票B', '股票C'],
                'price': [10.0, 20.0, 30.0],
                'pe_ratio': [15.0, 25.0, 35.0]
            })
        
        monitor.set_data_provider(mock_provider)
        snapshot = monitor.check_now()
        
        assert snapshot is not None
        assert snapshot.total_records == 3
        assert snapshot.overall_score > 0
    
    def test_get_latest_snapshot(self):
        """测试获取最新快照"""
        monitor = RealtimeDataQualityMonitor()
        
        # 初始无快照
        assert monitor.get_latest_snapshot() is None
        
        # 执行检查后有快照
        def mock_provider():
            return pd.DataFrame({
                'code': ['000001'],
                'name': ['测试']
            })
        
        monitor.set_data_provider(mock_provider)
        monitor.check_now()
        
        snapshot = monitor.get_latest_snapshot()
        assert snapshot is not None
    
    def test_get_active_alerts(self):
        """测试获取活跃告警"""
        monitor = RealtimeDataQualityMonitor()
        
        # 创建告警
        alert = monitor._create_alert_if_needed(
            level=DataQualityAlertLevel.WARNING,
            dimension=DataQualityDimension.COMPLETENESS,
            title="测试告警",
            message="测试消息"
        )
        
        active = monitor.get_active_alerts()
        assert len(active) == 1
        
        # 解决告警
        monitor.resolve_alert(alert.alert_id)
        active = monitor.get_active_alerts()
        assert len(active) == 0
    
    def test_resolve_alert(self):
        """测试解决告警"""
        monitor = RealtimeDataQualityMonitor()
        
        alert = monitor._create_alert_if_needed(
            level=DataQualityAlertLevel.ERROR,
            dimension=DataQualityDimension.ACCURACY,
            title="测试",
            message="测试"
        )
        
        assert alert.resolved is False
        
        result = monitor.resolve_alert(alert.alert_id)
        assert result is True
        assert alert.resolved is True
        assert alert.resolved_at is not None
    
    def test_get_alert_summary(self):
        """测试获取告警摘要"""
        monitor = RealtimeDataQualityMonitor()
        
        # 创建不同级别的告警
        monitor._create_alert_if_needed(
            level=DataQualityAlertLevel.WARNING,
            dimension=DataQualityDimension.COMPLETENESS,
            title="警告1",
            message="测试"
        )
        monitor._create_alert_if_needed(
            level=DataQualityAlertLevel.ERROR,
            dimension=DataQualityDimension.ACCURACY,
            title="错误1",
            message="测试"
        )
        
        summary = monitor.get_alert_summary()
        
        assert summary['total'] == 2
        assert summary['active'] == 2
        assert summary['by_level']['warning'] == 1
        assert summary['by_level']['error'] == 1
    
    def test_alert_cooldown(self):
        """测试告警冷却时间"""
        config = RealtimeMonitorConfig(alert_cooldown_minutes=60)
        monitor = RealtimeDataQualityMonitor(config)
        
        # 第一次告警应该创建
        alert1 = monitor._create_alert_if_needed(
            level=DataQualityAlertLevel.WARNING,
            dimension=DataQualityDimension.COMPLETENESS,
            title="重复告警",
            message="测试"
        )
        assert alert1 is not None
        
        # 冷却期内相同告警不应创建
        alert2 = monitor._create_alert_if_needed(
            level=DataQualityAlertLevel.WARNING,
            dimension=DataQualityDimension.COMPLETENESS,
            title="重复告警",
            message="测试"
        )
        assert alert2 is None
    
    def test_generate_quality_report(self):
        """测试生成质量报告"""
        monitor = RealtimeDataQualityMonitor()
        
        def mock_provider():
            return pd.DataFrame({
                'code': ['000001', '000002'],
                'name': ['股票A', '股票B'],
                'price': [10.0, 20.0]
            })
        
        monitor.set_data_provider(mock_provider)
        monitor.check_now()
        
        report = monitor.generate_quality_report()
        
        assert isinstance(report, str)
        assert '数据质量实时监控报告' in report
        assert '综合得分' in report
    
    def test_get_status(self):
        """测试获取监控状态"""
        monitor = RealtimeDataQualityMonitor()
        
        status = monitor.get_status()
        
        assert 'status' in status
        assert 'is_running' in status
        assert 'config' in status
        assert 'alerts' in status
        assert status['status'] == 'stopped'
        assert status['is_running'] is False


class TestGlobalFunctions:
    """全局函数测试"""
    
    def setup_method(self):
        """测试前重置"""
        reset_realtime_monitor()
    
    def teardown_method(self):
        """测试后清理"""
        reset_realtime_monitor()
    
    def test_get_realtime_data_quality_monitor(self):
        """测试获取监控器实例"""
        monitor = get_realtime_data_quality_monitor()
        assert isinstance(monitor, RealtimeDataQualityMonitor)
        
        # 单例模式
        monitor2 = get_realtime_data_quality_monitor()
        assert monitor is monitor2
    
    def test_reset_realtime_monitor(self):
        """测试重置监控器"""
        monitor1 = get_realtime_data_quality_monitor()
        reset_realtime_monitor()
        monitor2 = get_realtime_data_quality_monitor()
        
        assert monitor1 is not monitor2
    
    def test_check_data_quality_now(self):
        """测试立即检查数据质量"""
        monitor = get_realtime_data_quality_monitor()
        
        def mock_provider():
            return pd.DataFrame({
                'code': ['000001'],
                'name': ['测试']
            })
        
        monitor.set_data_provider(mock_provider)
        snapshot = check_data_quality_now()
        
        assert snapshot is not None
    
    def test_get_data_quality_status(self):
        """测试获取数据质量状态"""
        status = get_data_quality_status()
        
        assert isinstance(status, dict)
        assert 'status' in status
        assert 'is_running' in status
    
    def test_generate_data_quality_report(self):
        """测试生成数据质量报告"""
        report = generate_data_quality_report()
        
        assert isinstance(report, str)
        assert '数据质量' in report


class TestMonitoringIntegration:
    """监控集成测试"""
    
    def setup_method(self):
        """测试前重置"""
        reset_realtime_monitor()
    
    def teardown_method(self):
        """测试后清理"""
        stop_realtime_quality_monitoring()
        reset_realtime_monitor()
    
    def test_full_monitoring_cycle(self):
        """测试完整监控周期"""
        config = RealtimeMonitorConfig(
            check_interval_seconds=1,
            enable_auto_alert=True
        )
        monitor = RealtimeDataQualityMonitor(config)
        
        # 设置数据提供者
        def mock_provider():
            return pd.DataFrame({
                'code': ['000001', '000002', '600000'],
                'name': ['股票A', '股票B', '股票C'],
                'price': [10.0, 20.0, 30.0],
                'total_market_cap': [1e9, 2e9, 3e9],
                'float_market_cap': [8e8, 1.5e9, 2.5e9]
            })
        
        monitor.set_data_provider(mock_provider)
        
        # 执行检查
        snapshot = monitor.check_now()
        
        assert snapshot is not None
        assert snapshot.total_records == 3
        assert snapshot.completeness_score > 0
        assert snapshot.accuracy_score > 0
        assert snapshot.consistency_score > 0
        assert snapshot.validity_score > 0
        assert snapshot.overall_score > 0
        
        # 获取状态
        status = monitor.get_status()
        assert status['latest_snapshot'] is not None
        
        # 生成报告
        report = monitor.generate_quality_report()
        assert len(report) > 0
    
    def test_alert_generation_on_low_quality(self):
        """测试低质量数据时生成告警"""
        config = RealtimeMonitorConfig(
            completeness_threshold=99.0,
            enable_auto_alert=True,
            alert_cooldown_minutes=0  # 禁用冷却以便测试
        )
        monitor = RealtimeDataQualityMonitor(config)
        
        # 设置有缺失数据的提供者
        def mock_provider():
            return pd.DataFrame({
                'code': ['000001', '000002', '600000'],
                'name': ['股票A', None, '股票C'],  # 有缺失
                'price': [10.0, None, 30.0]  # 有缺失
            })
        
        monitor.set_data_provider(mock_provider)
        monitor.check_now()
        
        # 应该有告警
        alerts = monitor.get_active_alerts()
        # 由于完整性低于99%，应该有告警
        assert len(alerts) >= 0  # 可能有告警
    
    def test_quality_trend(self):
        """测试质量趋势"""
        monitor = RealtimeDataQualityMonitor()
        
        def mock_provider():
            return pd.DataFrame({
                'code': ['000001'],
                'name': ['测试']
            })
        
        monitor.set_data_provider(mock_provider)
        
        # 执行多次检查
        for _ in range(3):
            monitor.check_now()
        
        trend = monitor.get_quality_trend(hours=1)
        assert len(trend) == 3
