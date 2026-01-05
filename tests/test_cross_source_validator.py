"""
多源数据交叉验证测试

验证多数据源的交叉验证功能

Requirements: 7.4 - 多数据源交叉验证
"""

import pytest
import pandas as pd
import numpy as np
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.stock_screener.cross_source_validator import (
    CrossSourceValidator,
    MultiSourceCrossValidator,
    CrossValidationReport,
    CrossValidationConfig,
    FieldValidationResult,
    FieldDiscrepancy,
    ValidationStatus,
    DiscrepancyType,
    get_cross_validator,
    get_multi_source_validator,
    cross_validate_sources,
)


class TestCrossSourceValidator:
    """交叉验证器测试"""
    
    @pytest.fixture
    def validator(self):
        """创建验证器实例"""
        return CrossSourceValidator()
    
    @pytest.fixture
    def matching_data(self):
        """创建匹配的数据"""
        source1 = pd.DataFrame({
            'code': ['000001', '000002', '600000'],
            'name': ['平安银行', '万科A', '浦发银行'],
            'price': [10.0, 20.0, 15.0],
            'total_market_cap': [1000e8, 2000e8, 1500e8],
            'pe_ratio': [8.5, 12.0, 6.5],
        })
        
        source2 = pd.DataFrame({
            'code': ['000001', '000002', '600000'],
            'name': ['平安银行', '万科A', '浦发银行'],
            'price': [10.1, 20.2, 15.1],  # 略有差异但在容差内
            'total_market_cap': [1010e8, 2020e8, 1510e8],
            'pe_ratio': [8.6, 12.1, 6.6],
        })
        
        return source1, source2
    
    @pytest.fixture
    def mismatching_data(self):
        """创建不匹配的数据"""
        source1 = pd.DataFrame({
            'code': ['000001', '000002', '600000'],
            'name': ['平安银行', '万科A', '浦发银行'],
            'price': [10.0, 20.0, 15.0],
            'total_market_cap': [1000e8, 2000e8, 1500e8],
        })
        
        source2 = pd.DataFrame({
            'code': ['000001', '000002', '600000'],
            'name': ['平安银行', '万科A', '浦发银行'],
            'price': [15.0, 30.0, 25.0],  # 差异超过容差
            'total_market_cap': [1500e8, 3000e8, 2500e8],
        })
        
        return source1, source2
    
    def test_validator_initialization(self, validator):
        """测试验证器初始化"""
        assert validator is not None
        assert validator.config is not None
        assert validator.config.numeric_tolerance == 0.05
    
    def test_validate_matching_data(self, validator, matching_data):
        """测试验证匹配数据"""
        source1, source2 = matching_data
        
        report = validator.validate(source1, source2, "akshare", "eastmoney")
        
        assert report is not None
        assert isinstance(report, CrossValidationReport)
        assert report.is_valid is True
        assert report.status in [ValidationStatus.PASSED, ValidationStatus.WARNING]
        assert report.overall_match_rate >= 95.0
        assert report.common_record_count == 3
    
    def test_validate_mismatching_data(self, validator, mismatching_data):
        """测试验证不匹配数据"""
        source1, source2 = mismatching_data
        
        report = validator.validate(source1, source2, "akshare", "eastmoney")
        
        assert report is not None
        # 价格差异超过容差，应该有较低的匹配率
        assert report.overall_match_rate < 100.0
    
    def test_validate_empty_source1(self, validator):
        """测试空数据源1"""
        source1 = pd.DataFrame()
        source2 = pd.DataFrame({
            'code': ['000001'],
            'name': ['测试'],
            'price': [10.0],
        })
        
        report = validator.validate(source1, source2)
        
        assert report is not None
        assert report.status == ValidationStatus.SKIPPED
        assert report.is_valid is False
    
    def test_validate_empty_source2(self, validator):
        """测试空数据源2"""
        source1 = pd.DataFrame({
            'code': ['000001'],
            'name': ['测试'],
            'price': [10.0],
        })
        source2 = pd.DataFrame()
        
        report = validator.validate(source1, source2)
        
        assert report is not None
        assert report.status == ValidationStatus.SKIPPED
    
    def test_validate_none_data(self, validator):
        """测试None数据"""
        report = validator.validate(None, None)
        
        assert report is not None
        assert report.status == ValidationStatus.SKIPPED
    
    def test_validate_missing_key_field(self, validator):
        """测试缺少关联字段"""
        source1 = pd.DataFrame({
            'name': ['测试'],
            'price': [10.0],
        })
        source2 = pd.DataFrame({
            'code': ['000001'],
            'name': ['测试'],
            'price': [10.0],
        })
        
        report = validator.validate(source1, source2)
        
        assert report is not None
        assert report.status == ValidationStatus.SKIPPED
    
    def test_validate_partial_overlap(self, validator):
        """测试部分重叠数据"""
        source1 = pd.DataFrame({
            'code': ['000001', '000002', '000003'],
            'name': ['A', 'B', 'C'],
            'price': [10.0, 20.0, 30.0],
        })
        
        source2 = pd.DataFrame({
            'code': ['000002', '000003', '000004'],
            'name': ['B', 'C', 'D'],
            'price': [20.0, 30.0, 40.0],
        })
        
        report = validator.validate(source1, source2)
        
        assert report is not None
        assert report.common_record_count == 2  # 只有000002和000003重叠
        assert report.summary['only_in_source1'] == 1
        assert report.summary['only_in_source2'] == 1
    
    def test_field_validation_result(self, validator, matching_data):
        """测试字段验证结果"""
        source1, source2 = matching_data
        
        report = validator.validate(source1, source2)
        
        assert len(report.field_results) > 0
        
        for result in report.field_results:
            assert isinstance(result, FieldValidationResult)
            assert result.total_compared > 0
            assert 0 <= result.match_rate <= 100
    
    def test_report_to_dict(self, validator, matching_data):
        """测试报告转换为字典"""
        source1, source2 = matching_data
        
        report = validator.validate(source1, source2)
        report_dict = report.to_dict()
        
        assert 'timestamp' in report_dict
        assert 'source1_name' in report_dict
        assert 'source2_name' in report_dict
        assert 'overall_match_rate' in report_dict
        assert 'status' in report_dict
        assert 'is_valid' in report_dict
    
    def test_generate_report_text(self, validator, matching_data):
        """测试生成报告文本"""
        source1, source2 = matching_data
        
        report = validator.validate(source1, source2, "akshare", "eastmoney")
        report_text = validator.generate_report_text(report)
        
        assert report_text is not None
        assert "多源数据交叉验证报告" in report_text
        assert "akshare" in report_text
        assert "eastmoney" in report_text
        assert "总体匹配率" in report_text


class TestMultiSourceCrossValidator:
    """多源验证管理器测试"""
    
    @pytest.fixture
    def multi_validator(self):
        """创建多源验证管理器"""
        return MultiSourceCrossValidator()
    
    @pytest.fixture
    def three_sources(self):
        """创建三个数据源"""
        source1 = pd.DataFrame({
            'code': ['000001', '000002'],
            'name': ['A', 'B'],
            'price': [10.0, 20.0],
        })
        
        source2 = pd.DataFrame({
            'code': ['000001', '000002'],
            'name': ['A', 'B'],
            'price': [10.1, 20.1],
        })
        
        source3 = pd.DataFrame({
            'code': ['000001', '000002'],
            'name': ['A', 'B'],
            'price': [10.2, 20.2],
        })
        
        return {
            'source1': source1,
            'source2': source2,
            'source3': source3,
        }
    
    def test_validate_all_sources(self, multi_validator, three_sources):
        """测试验证所有数据源对"""
        reports = multi_validator.validate_all_sources(three_sources)
        
        # 3个数据源应该产生3对比较
        assert len(reports) == 3
        assert 'source1_vs_source2' in reports
        assert 'source1_vs_source3' in reports
        assert 'source2_vs_source3' in reports
    
    def test_get_consensus_data_primary(self, multi_validator, three_sources):
        """测试获取共识数据（主数据源策略）"""
        consensus = multi_validator.get_consensus_data(three_sources, strategy="primary")
        
        assert consensus is not None
        assert len(consensus) == 2
        # 应该返回第一个数据源的数据
        assert consensus['price'].iloc[0] == 10.0
    
    def test_generate_summary_report(self, multi_validator, three_sources):
        """测试生成汇总报告"""
        reports = multi_validator.validate_all_sources(three_sources)
        summary = multi_validator.generate_summary_report(reports)
        
        assert summary is not None
        assert "多源数据交叉验证汇总报告" in summary
        assert "验证对数: 3" in summary


class TestConvenienceFunctions:
    """便捷函数测试"""
    
    def test_get_cross_validator(self):
        """测试获取验证器实例"""
        validator1 = get_cross_validator()
        validator2 = get_cross_validator()
        
        assert validator1 is validator2  # 单例模式
    
    def test_get_multi_source_validator(self):
        """测试获取多源验证管理器实例"""
        validator1 = get_multi_source_validator()
        validator2 = get_multi_source_validator()
        
        assert validator1 is validator2  # 单例模式
    
    def test_cross_validate_sources_function(self):
        """测试便捷验证函数"""
        source1 = pd.DataFrame({
            'code': ['000001', '000002'],
            'name': ['A', 'B'],
            'price': [10.0, 20.0],
        })
        
        source2 = pd.DataFrame({
            'code': ['000001', '000002'],
            'name': ['A', 'B'],
            'price': [10.1, 20.1],
        })
        
        report = cross_validate_sources(source1, source2, "src1", "src2")
        
        assert report is not None
        assert isinstance(report, CrossValidationReport)


class TestCrossValidationConfig:
    """配置测试"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = CrossValidationConfig()
        
        assert config.numeric_tolerance == 0.05
        assert config.price_tolerance == 0.02
        assert config.min_match_rate == 95.0
        assert config.key_field == 'code'
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = CrossValidationConfig(
            numeric_tolerance=0.1,
            min_match_rate=90.0,
            key_field='stock_code'
        )
        
        validator = CrossSourceValidator(config)
        
        assert validator.config.numeric_tolerance == 0.1
        assert validator.config.min_match_rate == 90.0
        assert validator.config.key_field == 'stock_code'


class TestFieldDiscrepancy:
    """字段差异测试"""
    
    def test_discrepancy_to_dict(self):
        """测试差异转换为字典"""
        discrepancy = FieldDiscrepancy(
            field_name='price',
            discrepancy_type=DiscrepancyType.VALUE_MISMATCH,
            source1_value=10.0,
            source2_value=15.0,
            record_key='000001',
            relative_diff=0.4
        )
        
        d = discrepancy.to_dict()
        
        assert d['field_name'] == 'price'
        assert d['discrepancy_type'] == 'value_mismatch'
        assert d['record_key'] == '000001'
        assert d['relative_diff'] == 0.4


class TestValidationStatus:
    """验证状态测试"""
    
    def test_status_values(self):
        """测试状态值"""
        assert ValidationStatus.PASSED.value == "passed"
        assert ValidationStatus.WARNING.value == "warning"
        assert ValidationStatus.FAILED.value == "failed"
        assert ValidationStatus.SKIPPED.value == "skipped"


class TestDiscrepancyType:
    """差异类型测试"""
    
    def test_discrepancy_type_values(self):
        """测试差异类型值"""
        assert DiscrepancyType.MISSING_RECORD.value == "missing_record"
        assert DiscrepancyType.VALUE_MISMATCH.value == "value_mismatch"
        assert DiscrepancyType.TYPE_MISMATCH.value == "type_mismatch"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
