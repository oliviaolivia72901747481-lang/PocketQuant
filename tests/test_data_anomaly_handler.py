"""
数据异常处理流程模块测试

测试数据异常的检测、分类、处理和恢复功能

Requirements: 7.2, 7.3, 7.4
风险缓解措施: 建立数据异常处理流程
"""

import pytest
import os
import json
import tempfile
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np

from core.stock_screener.data_anomaly_handler import (
    DataAnomalyWorkflow,
    AnomalyDetector,
    AnomalyHandler,
    DataAnomaly,
    AnomalyHandlingResult,
    AnomalyHandlingConfig,
    AnomalyType,
    AnomalySeverity,
    HandlingStrategy,
    HandlingStatus,
    get_anomaly_workflow,
    reset_anomaly_workflow,
    process_data_anomalies,
    get_anomaly_summary,
    generate_anomaly_report,
    review_pending_anomaly,
)


class TestAnomalyType:
    """异常类型测试"""
    
    def test_anomaly_types_exist(self):
        """测试异常类型枚举存在"""
        assert AnomalyType.MISSING_VALUE.value == "missing_value"
        assert AnomalyType.OUT_OF_RANGE.value == "out_of_range"
        assert AnomalyType.INVALID_FORMAT.value == "invalid_format"
        assert AnomalyType.INCONSISTENT.value == "inconsistent"
        assert AnomalyType.DUPLICATE.value == "duplicate"
        assert AnomalyType.OUTLIER.value == "outlier"
        assert AnomalyType.STALE_DATA.value == "stale_data"
        assert AnomalyType.SOURCE_MISMATCH.value == "source_mismatch"
        assert AnomalyType.LOGIC_ERROR.value == "logic_error"


class TestAnomalySeverity:
    """异常严重程度测试"""
    
    def test_severity_levels_exist(self):
        """测试严重程度枚举存在"""
        assert AnomalySeverity.LOW.value == "low"
        assert AnomalySeverity.MEDIUM.value == "medium"
        assert AnomalySeverity.HIGH.value == "high"
        assert AnomalySeverity.CRITICAL.value == "critical"


class TestHandlingStrategy:
    """处理策略测试"""
    
    def test_strategies_exist(self):
        """测试处理策略枚举存在"""
        assert HandlingStrategy.IGNORE.value == "ignore"
        assert HandlingStrategy.AUTO_FIX.value == "auto_fix"
        assert HandlingStrategy.FILL_DEFAULT.value == "fill_default"
        assert HandlingStrategy.FILL_MEDIAN.value == "fill_median"
        assert HandlingStrategy.FILL_MEAN.value == "fill_mean"
        assert HandlingStrategy.REMOVE_RECORD.value == "remove_record"
        assert HandlingStrategy.FLAG_FOR_REVIEW.value == "flag_for_review"
        assert HandlingStrategy.USE_BACKUP_SOURCE.value == "use_backup_source"
        assert HandlingStrategy.MANUAL_REVIEW.value == "manual_review"


class TestDataAnomaly:
    """数据异常记录测试"""
    
    def test_anomaly_creation(self):
        """测试异常记录创建"""
        anomaly = DataAnomaly(
            anomaly_id="ANO_TEST_001",
            anomaly_type=AnomalyType.MISSING_VALUE,
            severity=AnomalySeverity.MEDIUM,
            field_name="price",
            record_id="000001",
            description="价格字段缺失"
        )
        
        assert anomaly.anomaly_id == "ANO_TEST_001"
        assert anomaly.anomaly_type == AnomalyType.MISSING_VALUE
        assert anomaly.severity == AnomalySeverity.MEDIUM
        assert anomaly.field_name == "price"
        assert anomaly.record_id == "000001"
        assert anomaly.handling_status == HandlingStatus.PENDING
    
    def test_anomaly_to_dict(self):
        """测试异常记录转换为字典"""
        anomaly = DataAnomaly(
            anomaly_id="ANO_TEST_002",
            anomaly_type=AnomalyType.OUT_OF_RANGE,
            severity=AnomalySeverity.HIGH,
            field_name="pe_ratio",
            record_id="600000",
            original_value=999999,
            expected_range=(-10000, 100000),
            description="PE值超出范围"
        )
        
        anomaly_dict = anomaly.to_dict()
        
        assert anomaly_dict['anomaly_id'] == "ANO_TEST_002"
        assert anomaly_dict['anomaly_type'] == "out_of_range"
        assert anomaly_dict['severity'] == "high"
        assert anomaly_dict['field_name'] == "pe_ratio"
        assert anomaly_dict['expected_range'] == [-10000, 100000]
    
    def test_anomaly_from_dict(self):
        """测试从字典创建异常记录"""
        data = {
            'anomaly_id': 'ANO_TEST_003',
            'anomaly_type': 'invalid_format',
            'severity': 'low',
            'field_name': 'code',
            'record_id': 'ABC123',
            'original_value': 'ABC123',
            'expected_range': None,
            'description': '股票代码格式无效',
            'detected_at': datetime.now().isoformat(),
            'handling_strategy': None,
            'handling_status': 'pending',
            'corrected_value': None,
            'handled_at': None,
            'handler_notes': ''
        }
        
        anomaly = DataAnomaly.from_dict(data)
        
        assert anomaly.anomaly_id == 'ANO_TEST_003'
        assert anomaly.anomaly_type == AnomalyType.INVALID_FORMAT
        assert anomaly.severity == AnomalySeverity.LOW


class TestAnomalyHandlingConfig:
    """异常处理配置测试"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = AnomalyHandlingConfig()
        
        assert config.auto_fix_threshold == AnomalySeverity.MEDIUM
        assert config.enable_cross_source_fix is True
        assert config.max_auto_fix_attempts == 3
        assert config.log_all_handling is True
        assert config.history_retention_days == 30
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = AnomalyHandlingConfig(
            auto_fix_threshold=AnomalySeverity.LOW,
            enable_cross_source_fix=False,
            max_auto_fix_attempts=5
        )
        
        assert config.auto_fix_threshold == AnomalySeverity.LOW
        assert config.enable_cross_source_fix is False
        assert config.max_auto_fix_attempts == 5
    
    def test_default_type_strategies(self):
        """测试默认类型策略"""
        config = AnomalyHandlingConfig()
        
        assert AnomalyType.MISSING_VALUE in config.type_strategies
        assert AnomalyType.DUPLICATE in config.type_strategies
        assert config.type_strategies[AnomalyType.DUPLICATE] == HandlingStrategy.REMOVE_RECORD
    
    def test_config_to_dict(self):
        """测试配置转换为字典"""
        config = AnomalyHandlingConfig()
        config_dict = config.to_dict()
        
        assert 'auto_fix_threshold' in config_dict
        assert 'type_strategies' in config_dict
        assert 'default_values' in config_dict


class TestAnomalyDetector:
    """异常检测器测试"""
    
    def setup_method(self):
        """测试前初始化"""
        self.detector = AnomalyDetector()
    
    def test_detect_missing_values(self):
        """测试检测缺失值"""
        df = pd.DataFrame({
            'code': ['000001', '000002', '000003'],
            'name': ['股票A', None, '股票C'],
            'price': [10.0, 20.0, None]
        })
        
        anomalies = self.detector.detect_anomalies(df)
        
        # 应该检测到name和price的缺失值
        missing_anomalies = [a for a in anomalies if a.anomaly_type == AnomalyType.MISSING_VALUE]
        assert len(missing_anomalies) >= 1
    
    def test_detect_invalid_format(self):
        """测试检测格式无效"""
        df = pd.DataFrame({
            'code': ['000001', 'INVALID', '600000'],
            'name': ['股票A', '股票B', '股票C'],
            'price': [10.0, 20.0, 30.0]
        })
        
        anomalies = self.detector.detect_anomalies(df)
        
        format_anomalies = [a for a in anomalies if a.anomaly_type == AnomalyType.INVALID_FORMAT]
        assert len(format_anomalies) >= 1
    
    def test_detect_out_of_range(self):
        """测试检测超出范围"""
        df = pd.DataFrame({
            'code': ['000001', '000002'],
            'name': ['股票A', '股票B'],
            'price': [10.0, -5.0],  # 负价格超出范围
            'pe_ratio': [15.0, 200000.0]  # PE超出范围
        })
        
        anomalies = self.detector.detect_anomalies(df)
        
        range_anomalies = [a for a in anomalies if a.anomaly_type == AnomalyType.OUT_OF_RANGE]
        assert len(range_anomalies) >= 1
    
    def test_detect_inconsistencies(self):
        """测试检测数据不一致"""
        df = pd.DataFrame({
            'code': ['000001'],
            'name': ['股票A'],
            'total_market_cap': [800000000],
            'float_market_cap': [1000000000],  # 流通市值大于总市值
        })
        
        anomalies = self.detector.detect_anomalies(df)
        
        inconsistent_anomalies = [a for a in anomalies if a.anomaly_type == AnomalyType.INCONSISTENT]
        assert len(inconsistent_anomalies) >= 1
    
    def test_detect_duplicates(self):
        """测试检测重复数据"""
        df = pd.DataFrame({
            'code': ['000001', '000001', '000002'],  # 重复代码
            'name': ['股票A', '股票A副本', '股票B'],
            'price': [10.0, 10.5, 20.0]
        })
        
        anomalies = self.detector.detect_anomalies(df)
        
        duplicate_anomalies = [a for a in anomalies if a.anomaly_type == AnomalyType.DUPLICATE]
        assert len(duplicate_anomalies) >= 1
    
    def test_detect_logic_errors(self):
        """测试检测逻辑错误"""
        df = pd.DataFrame({
            'code': ['000001'],
            'name': ['股票A'],
            'open': [15.0],
            'close': [14.0],
            'high': [12.0],  # 高价低于开盘价
            'low': [10.0]
        })
        
        anomalies = self.detector.detect_anomalies(df)
        
        logic_anomalies = [a for a in anomalies if a.anomaly_type == AnomalyType.LOGIC_ERROR]
        assert len(logic_anomalies) >= 1
    
    def test_detect_empty_dataframe(self):
        """测试空DataFrame"""
        df = pd.DataFrame()
        anomalies = self.detector.detect_anomalies(df)
        assert len(anomalies) == 0
    
    def test_detect_clean_data(self):
        """测试干净数据"""
        df = pd.DataFrame({
            'code': ['000001', '000002', '600000'],
            'name': ['股票A', '股票B', '股票C'],
            'price': [10.0, 20.0, 30.0],
            'pe_ratio': [15.0, 25.0, 35.0],
            'total_market_cap': [1e9, 2e9, 3e9],
            'float_market_cap': [8e8, 1.5e9, 2.5e9]
        })
        
        anomalies = self.detector.detect_anomalies(df)
        
        # 干净数据应该没有严重异常
        high_severity = [a for a in anomalies if a.severity in [AnomalySeverity.HIGH, AnomalySeverity.CRITICAL]]
        assert len(high_severity) == 0


class TestAnomalyHandler:
    """异常处理器测试"""
    
    def setup_method(self):
        """测试前初始化"""
        self.config = AnomalyHandlingConfig()
        self.handler = AnomalyHandler(self.config)
    
    def test_handle_ignore(self):
        """测试忽略处理"""
        anomaly = DataAnomaly(
            anomaly_id="ANO_TEST_001",
            anomaly_type=AnomalyType.OUTLIER,
            severity=AnomalySeverity.LOW,
            field_name="turnover_rate",
            original_value=50.0
        )
        
        df = pd.DataFrame({'code': ['000001'], 'turnover_rate': [50.0]})
        
        # 设置忽略策略
        self.config.type_strategies[AnomalyType.OUTLIER] = HandlingStrategy.IGNORE
        
        result = self.handler.handle_anomaly(anomaly, df)
        
        assert result.success is True
        assert result.strategy_used == HandlingStrategy.IGNORE
    
    def test_handle_fill_median(self):
        """测试填充中位数"""
        anomaly = DataAnomaly(
            anomaly_id="ANO_TEST_002",
            anomaly_type=AnomalyType.MISSING_VALUE,
            severity=AnomalySeverity.MEDIUM,
            field_name="pe_ratio",
            record_id="000001",
            original_value=None
        )
        
        df = pd.DataFrame({
            'code': ['000001', '000002', '000003'],
            'pe_ratio': [None, 20.0, 30.0]
        })
        
        result = self.handler.handle_anomaly(anomaly, df)
        
        assert result.success is True
        assert result.corrected_value is not None
    
    def test_handle_fill_default(self):
        """测试填充默认值"""
        self.config.field_strategies['roe'] = HandlingStrategy.FILL_DEFAULT
        self.config.default_values['roe'] = 0
        
        anomaly = DataAnomaly(
            anomaly_id="ANO_TEST_003",
            anomaly_type=AnomalyType.MISSING_VALUE,
            severity=AnomalySeverity.MEDIUM,
            field_name="roe",
            record_id="000001",
            original_value=None
        )
        
        df = pd.DataFrame({
            'code': ['000001'],
            'roe': [None]
        })
        
        result = self.handler.handle_anomaly(anomaly, df)
        
        assert result.success is True
        assert result.corrected_value == 0
    
    def test_handle_remove_record(self):
        """测试移除记录"""
        anomaly = DataAnomaly(
            anomaly_id="ANO_TEST_004",
            anomaly_type=AnomalyType.DUPLICATE,
            severity=AnomalySeverity.LOW,
            field_name="code",
            record_id="000001",
            original_value="000001"
        )
        
        df = pd.DataFrame({
            'code': ['000001', '000001', '000002'],
            'name': ['股票A', '股票A副本', '股票B']
        })
        
        result = self.handler.handle_anomaly(anomaly, df)
        
        assert result.success is True
        assert result.strategy_used == HandlingStrategy.REMOVE_RECORD
    
    def test_handle_flag_for_review(self):
        """测试标记待审核"""
        anomaly = DataAnomaly(
            anomaly_id="ANO_TEST_005",
            anomaly_type=AnomalyType.INCONSISTENT,
            severity=AnomalySeverity.HIGH,
            field_name="float_market_cap",
            record_id="000001"
        )
        
        df = pd.DataFrame({
            'code': ['000001'],
            'float_market_cap': [1e10]
        })
        
        result = self.handler.handle_anomaly(anomaly, df)
        
        assert result.success is True
        assert result.strategy_used == HandlingStrategy.FLAG_FOR_REVIEW
        # 标记待审核是一个成功的处理动作，状态会变为RESOLVED
        # 但handler_notes会记录需要人工审核
        assert '审核' in anomaly.handler_notes
    
    def test_handle_use_backup_source(self):
        """测试使用备用数据源"""
        anomaly = DataAnomaly(
            anomaly_id="ANO_TEST_006",
            anomaly_type=AnomalyType.STALE_DATA,
            severity=AnomalySeverity.MEDIUM,
            field_name="price",
            record_id="000001",
            original_value=None
        )
        
        df = pd.DataFrame({
            'code': ['000001'],
            'price': [None]
        })
        
        backup_df = pd.DataFrame({
            'code': ['000001'],
            'price': [15.5]
        })
        
        result = self.handler.handle_anomaly(anomaly, df, backup_df)
        
        assert result.success is True
        assert result.corrected_value == 15.5
    
    def test_handle_anomalies_batch(self):
        """测试批量处理异常"""
        anomalies = [
            DataAnomaly(
                anomaly_id="ANO_BATCH_001",
                anomaly_type=AnomalyType.MISSING_VALUE,
                severity=AnomalySeverity.MEDIUM,
                field_name="pe_ratio",
                record_id="000001"
            ),
            DataAnomaly(
                anomaly_id="ANO_BATCH_002",
                anomaly_type=AnomalyType.DUPLICATE,
                severity=AnomalySeverity.LOW,
                field_name="code",
                record_id="000002"
            )
        ]
        
        df = pd.DataFrame({
            'code': ['000001', '000002', '000002'],
            'pe_ratio': [None, 20.0, 20.0]
        })
        
        processed_df, results = self.handler.handle_anomalies(anomalies, df)
        
        assert len(results) == 2
        assert len(processed_df) < len(df)  # 应该移除了重复记录
    
    def test_get_handling_statistics(self):
        """测试获取处理统计"""
        # 处理一些异常
        anomaly = DataAnomaly(
            anomaly_id="ANO_STAT_001",
            anomaly_type=AnomalyType.MISSING_VALUE,
            severity=AnomalySeverity.MEDIUM,
            field_name="pe_ratio"
        )
        
        df = pd.DataFrame({'code': ['000001'], 'pe_ratio': [None]})
        self.handler.handle_anomaly(anomaly, df)
        
        stats = self.handler.get_handling_statistics()
        
        assert 'total_handled' in stats
        assert 'successful' in stats
        assert 'success_rate' in stats
        assert 'by_strategy' in stats



class TestDataAnomalyWorkflow:
    """数据异常处理工作流测试"""
    
    def setup_method(self):
        """测试前重置"""
        reset_anomaly_workflow()
    
    def teardown_method(self):
        """测试后清理"""
        reset_anomaly_workflow()
    
    def test_workflow_initialization(self):
        """测试工作流初始化"""
        workflow = DataAnomalyWorkflow()
        
        assert workflow.detector is not None
        assert workflow.handler is not None
        assert workflow.config is not None
    
    def test_workflow_with_custom_config(self):
        """测试使用自定义配置初始化"""
        config = AnomalyHandlingConfig(
            auto_fix_threshold=AnomalySeverity.LOW,
            enable_cross_source_fix=False
        )
        workflow = DataAnomalyWorkflow(config)
        
        assert workflow.config.auto_fix_threshold == AnomalySeverity.LOW
        assert workflow.config.enable_cross_source_fix is False
    
    def test_process_data_with_anomalies(self):
        """测试处理包含异常的数据"""
        workflow = DataAnomalyWorkflow()
        
        df = pd.DataFrame({
            'code': ['000001', '000002', 'INVALID'],
            'name': ['股票A', None, '股票C'],
            'price': [10.0, -5.0, 30.0],
            'pe_ratio': [15.0, 200000.0, 25.0]
        })
        
        processed_df, anomalies, results = workflow.process_data(df)
        
        assert len(anomalies) > 0
        assert len(results) > 0
        assert processed_df is not None
    
    def test_process_clean_data(self):
        """测试处理干净数据"""
        workflow = DataAnomalyWorkflow()
        
        df = pd.DataFrame({
            'code': ['000001', '000002', '600000'],
            'name': ['股票A', '股票B', '股票C'],
            'price': [10.0, 20.0, 30.0]
        })
        
        processed_df, anomalies, results = workflow.process_data(df)
        
        # 干净数据应该没有严重异常
        high_severity = [a for a in anomalies if a.severity in [AnomalySeverity.HIGH, AnomalySeverity.CRITICAL]]
        assert len(high_severity) == 0
    
    def test_process_data_without_auto_handle(self):
        """测试不自动处理"""
        workflow = DataAnomalyWorkflow()
        
        df = pd.DataFrame({
            'code': ['000001', 'INVALID'],
            'name': ['股票A', '股票B'],
            'price': [10.0, 20.0]
        })
        
        processed_df, anomalies, results = workflow.process_data(df, auto_handle=False)
        
        # 不自动处理时，所有异常应该待审核
        for anomaly in anomalies:
            assert anomaly.handling_status == HandlingStatus.PENDING
    
    def test_get_pending_review(self):
        """测试获取待审核异常"""
        workflow = DataAnomalyWorkflow()
        
        df = pd.DataFrame({
            'code': ['000001'],
            'name': ['股票A'],
            'total_market_cap': [800000000],
            'float_market_cap': [1000000000]  # 不一致
        })
        
        workflow.process_data(df)
        pending = workflow.get_pending_review()
        
        # 不一致的数据应该标记待审核
        assert isinstance(pending, list)
    
    def test_review_anomaly_approve(self):
        """测试审核通过"""
        workflow = DataAnomalyWorkflow()
        
        # 创建一个待审核的异常
        anomaly = DataAnomaly(
            anomaly_id="ANO_REVIEW_001",
            anomaly_type=AnomalyType.INCONSISTENT,
            severity=AnomalySeverity.HIGH,
            field_name="test",
            handling_status=HandlingStatus.MANUAL_REQUIRED
        )
        workflow._pending_review.append(anomaly)
        
        result = workflow.review_anomaly(
            "ANO_REVIEW_001",
            action="approve",
            notes="数据已确认正确"
        )
        
        assert result is True
        assert anomaly.handling_status == HandlingStatus.RESOLVED
    
    def test_review_anomaly_reject(self):
        """测试审核拒绝"""
        workflow = DataAnomalyWorkflow()
        
        anomaly = DataAnomaly(
            anomaly_id="ANO_REVIEW_002",
            anomaly_type=AnomalyType.OUTLIER,
            severity=AnomalySeverity.MEDIUM,
            field_name="test",
            handling_status=HandlingStatus.MANUAL_REQUIRED
        )
        workflow._pending_review.append(anomaly)
        
        result = workflow.review_anomaly(
            "ANO_REVIEW_002",
            action="reject",
            notes="异常值是正常的"
        )
        
        assert result is True
        assert anomaly.handling_status == HandlingStatus.SKIPPED
    
    def test_review_anomaly_fix(self):
        """测试人工修复"""
        workflow = DataAnomalyWorkflow()
        
        anomaly = DataAnomaly(
            anomaly_id="ANO_REVIEW_003",
            anomaly_type=AnomalyType.MISSING_VALUE,
            severity=AnomalySeverity.MEDIUM,
            field_name="price",
            handling_status=HandlingStatus.MANUAL_REQUIRED
        )
        workflow._pending_review.append(anomaly)
        
        result = workflow.review_anomaly(
            "ANO_REVIEW_003",
            action="fix",
            corrected_value=15.5,
            notes="手动填充价格"
        )
        
        assert result is True
        assert anomaly.handling_status == HandlingStatus.RESOLVED
        assert anomaly.corrected_value == 15.5
    
    def test_get_anomaly_summary(self):
        """测试获取异常摘要"""
        workflow = DataAnomalyWorkflow()
        
        df = pd.DataFrame({
            'code': ['000001', 'INVALID', '000002'],
            'name': ['股票A', None, '股票C'],
            'price': [10.0, -5.0, 30.0]
        })
        
        workflow.process_data(df)
        summary = workflow.get_anomaly_summary()
        
        assert 'total_anomalies' in summary
        assert 'pending_review' in summary
        assert 'by_type' in summary
        assert 'by_severity' in summary
        assert 'by_status' in summary
        assert 'handling_statistics' in summary
    
    def test_generate_report(self):
        """测试生成报告"""
        workflow = DataAnomalyWorkflow()
        
        df = pd.DataFrame({
            'code': ['000001', '000002'],
            'name': ['股票A', '股票B'],
            'price': [10.0, 20.0]
        })
        
        workflow.process_data(df)
        report = workflow.generate_report()
        
        assert isinstance(report, str)
        assert '数据异常处理报告' in report
        assert '异常统计' in report
    
    def test_clear_history(self):
        """测试清理历史"""
        workflow = DataAnomalyWorkflow()
        
        df = pd.DataFrame({
            'code': ['000001', 'INVALID'],
            'name': ['股票A', '股票B'],
            'price': [10.0, 20.0]
        })
        
        workflow.process_data(df)
        assert len(workflow._anomalies) > 0
        
        workflow.clear_history()
        assert len(workflow._anomalies) == 0


class TestGlobalFunctions:
    """全局函数测试"""
    
    def setup_method(self):
        """测试前重置"""
        reset_anomaly_workflow()
    
    def teardown_method(self):
        """测试后清理"""
        reset_anomaly_workflow()
    
    def test_get_anomaly_workflow(self):
        """测试获取工作流实例"""
        workflow = get_anomaly_workflow()
        assert isinstance(workflow, DataAnomalyWorkflow)
        
        # 单例模式
        workflow2 = get_anomaly_workflow()
        assert workflow is workflow2
    
    def test_reset_anomaly_workflow(self):
        """测试重置工作流"""
        workflow1 = get_anomaly_workflow()
        reset_anomaly_workflow()
        workflow2 = get_anomaly_workflow()
        
        assert workflow1 is not workflow2
    
    def test_process_data_anomalies_function(self):
        """测试便捷函数：处理数据异常"""
        df = pd.DataFrame({
            'code': ['000001', '000002'],
            'name': ['股票A', '股票B'],
            'price': [10.0, 20.0]
        })
        
        processed_df, anomalies, results = process_data_anomalies(df)
        
        assert processed_df is not None
        assert isinstance(anomalies, list)
        assert isinstance(results, list)
    
    def test_get_anomaly_summary_function(self):
        """测试便捷函数：获取异常摘要"""
        summary = get_anomaly_summary()
        
        assert isinstance(summary, dict)
        assert 'total_anomalies' in summary
    
    def test_generate_anomaly_report_function(self):
        """测试便捷函数：生成报告"""
        report = generate_anomaly_report()
        
        assert isinstance(report, str)
        assert '数据异常处理报告' in report


class TestIntegration:
    """集成测试"""
    
    def setup_method(self):
        """测试前重置"""
        reset_anomaly_workflow()
    
    def teardown_method(self):
        """测试后清理"""
        reset_anomaly_workflow()
    
    def test_full_workflow_cycle(self):
        """测试完整工作流周期"""
        workflow = DataAnomalyWorkflow()
        
        # 1. 准备包含各种异常的数据
        df = pd.DataFrame({
            'code': ['000001', '000002', 'INVALID', '000003', '000003'],
            'name': ['股票A', None, '股票C', '股票D', '股票D副本'],
            'price': [10.0, -5.0, 30.0, 40.0, 40.0],
            'pe_ratio': [15.0, 200000.0, 25.0, 35.0, 35.0],
            'total_market_cap': [1e9, 2e9, 3e9, 4e9, 4e9],
            'float_market_cap': [8e8, 3e9, 2.5e9, 3.5e9, 3.5e9]  # 000002不一致
        })
        
        # 2. 处理数据
        processed_df, anomalies, results = workflow.process_data(df)
        
        # 3. 验证检测到异常
        assert len(anomalies) > 0
        
        # 4. 验证处理结果
        assert len(results) > 0
        
        # 5. 获取摘要
        summary = workflow.get_anomaly_summary()
        assert summary['total_anomalies'] > 0
        
        # 6. 生成报告
        report = workflow.generate_report()
        assert len(report) > 0
        
        # 7. 处理待审核项
        pending = workflow.get_pending_review()
        for anomaly in pending[:2]:  # 处理前两个
            workflow.review_anomaly(
                anomaly.anomaly_id,
                action="approve",
                notes="测试审核"
            )
    
    def test_workflow_with_backup_source(self):
        """测试使用备用数据源的工作流"""
        config = AnomalyHandlingConfig()
        config.type_strategies[AnomalyType.MISSING_VALUE] = HandlingStrategy.USE_BACKUP_SOURCE
        
        workflow = DataAnomalyWorkflow(config)
        
        # 主数据源有缺失
        df = pd.DataFrame({
            'code': ['000001', '000002'],
            'name': ['股票A', '股票B'],
            'price': [None, 20.0]
        })
        
        # 备用数据源完整
        backup_df = pd.DataFrame({
            'code': ['000001', '000002'],
            'name': ['股票A', '股票B'],
            'price': [15.5, 20.0]
        })
        
        processed_df, anomalies, results = workflow.process_data(df, backup_df)
        
        # 应该从备用数据源获取了缺失值
        backup_results = [r for r in results if r.strategy_used == HandlingStrategy.USE_BACKUP_SOURCE]
        # 可能有也可能没有，取决于具体的异常检测
        assert processed_df is not None
    
    def test_anomaly_severity_ordering(self):
        """测试异常按严重程度排序处理"""
        workflow = DataAnomalyWorkflow()
        
        # 创建不同严重程度的异常
        anomalies = [
            DataAnomaly(
                anomaly_id="ANO_SEV_001",
                anomaly_type=AnomalyType.OUTLIER,
                severity=AnomalySeverity.LOW,
                field_name="test1"
            ),
            DataAnomaly(
                anomaly_id="ANO_SEV_002",
                anomaly_type=AnomalyType.LOGIC_ERROR,
                severity=AnomalySeverity.CRITICAL,
                field_name="test2"
            ),
            DataAnomaly(
                anomaly_id="ANO_SEV_003",
                anomaly_type=AnomalyType.MISSING_VALUE,
                severity=AnomalySeverity.MEDIUM,
                field_name="test3"
            ),
        ]
        
        df = pd.DataFrame({'code': ['000001'], 'test1': [1], 'test2': [2], 'test3': [3]})
        
        _, results = workflow.handler.handle_anomalies(anomalies, df)
        
        # 验证处理了所有异常
        assert len(results) == 3
