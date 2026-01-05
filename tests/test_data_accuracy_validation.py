"""
数据准确率验证测试

验证数据准确率是否达到99%以上的目标

Requirements: 7.2, 7.4, 7.5
成功标准: 数据准确率 ≥ 99%
"""

import pytest
import pandas as pd
import numpy as np
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.stock_screener.data_accuracy_validator import (
    DataAccuracyValidator,
    DataAccuracyReport,
    FieldAccuracyResult,
    AccuracyLevel,
    ValidationMethod,
    get_accuracy_validator,
    validate_data_accuracy,
)


class TestDataAccuracyValidator:
    """数据准确率验证器测试"""
    
    @pytest.fixture
    def validator(self):
        """创建验证器实例"""
        return DataAccuracyValidator(target_accuracy=99.0)
    
    @pytest.fixture
    def valid_stock_data(self):
        """创建有效的股票数据"""
        return pd.DataFrame({
            'code': ['000001', '000002', '600000', '600001', '002001'],
            'name': ['平安银行', '万科A', '浦发银行', '邯郸钢铁', '新和成'],
            'price': [10.5, 15.2, 8.3, 5.6, 25.8],
            'close': [10.5, 15.2, 8.3, 5.6, 25.8],
            'open': [10.3, 15.0, 8.1, 5.5, 25.5],
            'high': [10.8, 15.5, 8.5, 5.8, 26.0],
            'low': [10.2, 14.9, 8.0, 5.4, 25.3],
            'change_pct': [1.5, -0.8, 2.1, 0.5, -1.2],
            'turnover_rate': [2.5, 1.8, 3.2, 1.5, 2.0],
            'pe_ratio': [8.5, 12.3, 6.8, 15.2, 25.6],
            'pb_ratio': [1.2, 1.8, 0.9, 1.5, 3.2],
            'total_market_cap': [2000e8, 3000e8, 1500e8, 500e8, 800e8],
            'float_market_cap': [1800e8, 2500e8, 1200e8, 400e8, 600e8],
            'volume': [1e8, 2e8, 1.5e8, 0.5e8, 0.8e8],
            'turnover': [10e8, 30e8, 12e8, 3e8, 20e8],
        })
    
    def test_validator_initialization(self, validator):
        """测试验证器初始化"""
        assert validator is not None
        assert validator.target_accuracy == 99.0
    
    def test_validate_valid_data(self, validator, valid_stock_data):
        """测试验证有效数据"""
        report = validator.validate_accuracy(valid_stock_data)
        
        assert report is not None
        assert isinstance(report, DataAccuracyReport)
        assert report.total_records == 5
        assert report.overall_accuracy >= 99.0
        assert bool(report.meets_target) is True
        assert report.accuracy_level == AccuracyLevel.EXCELLENT
    
    def test_validate_empty_data(self, validator):
        """测试验证空数据"""
        empty_df = pd.DataFrame()
        report = validator.validate_accuracy(empty_df)
        
        assert report is not None
        assert report.total_records == 0
        assert report.overall_accuracy == 0.0
        assert report.meets_target is False
    
    def test_validate_none_data(self, validator):
        """测试验证None数据"""
        report = validator.validate_accuracy(None)
        
        assert report is not None
        assert report.total_records == 0
        assert report.meets_target is False
    
    def test_code_format_validation(self, validator):
        """测试股票代码格式验证"""
        # 包含无效代码的数据
        data = pd.DataFrame({
            'code': ['000001', '999999', 'INVALID', '600000', ''],
            'name': ['A', 'B', 'C', 'D', 'E'],
            'price': [10, 20, 30, 40, 50],
        })
        
        report = validator.validate_accuracy(data)
        
        # 应该检测到无效代码
        code_result = next(
            (r for r in report.field_results if r.field_name == 'code'), 
            None
        )
        assert code_result is not None
        assert code_result.accuracy_rate < 100  # 有无效代码
    
    def test_numeric_range_validation(self, validator):
        """测试数值范围验证"""
        # 包含超出范围值的数据
        data = pd.DataFrame({
            'code': ['000001', '000002', '000003'],
            'name': ['A', 'B', 'C'],
            'price': [10, -5, 50000],  # -5和50000超出范围
            'turnover_rate': [2, 150, 5],  # 150超出范围
        })
        
        report = validator.validate_accuracy(data)
        
        # 应该检测到范围外的值
        assert report.overall_accuracy < 100
    
    def test_consistency_validation(self, validator):
        """测试数据一致性验证"""
        # 包含不一致数据
        data = pd.DataFrame({
            'code': ['000001', '000002'],
            'name': ['A', 'B'],
            'price': [10, 20],
            'total_market_cap': [100e8, 200e8],
            'float_market_cap': [150e8, 180e8],  # 第一条流通市值>总市值
            'high': [12, 18],
            'low': [8, 22],  # 第二条最低价>最高价
        })
        
        report = validator.validate_accuracy(data)
        
        # 应该检测到一致性问题
        consistency_result = next(
            (r for r in report.field_results if r.field_name == 'consistency'),
            None
        )
        assert consistency_result is not None
        assert consistency_result.accuracy_rate < 100
    
    def test_accuracy_level_determination(self, validator):
        """测试准确率等级判定"""
        # 测试不同准确率对应的等级
        assert validator._determine_accuracy_level(99.5) == AccuracyLevel.EXCELLENT
        assert validator._determine_accuracy_level(97.0) == AccuracyLevel.GOOD
        assert validator._determine_accuracy_level(92.0) == AccuracyLevel.ACCEPTABLE
        assert validator._determine_accuracy_level(85.0) == AccuracyLevel.POOR
        assert validator._determine_accuracy_level(70.0) == AccuracyLevel.UNACCEPTABLE
    
    def test_report_generation(self, validator, valid_stock_data):
        """测试报告生成"""
        report = validator.validate_accuracy(valid_stock_data)
        report_text = validator.generate_accuracy_report(report)
        
        assert report_text is not None
        assert "数据准确率验证报告" in report_text
        assert "总体准确率" in report_text
        assert "字段准确率详情" in report_text
    
    def test_cross_validation(self, validator):
        """测试多源交叉验证"""
        source1 = pd.DataFrame({
            'code': ['000001', '000002', '000003'],
            'price': [10.0, 20.0, 30.0],
            'total_market_cap': [100e8, 200e8, 300e8],
        })
        
        source2 = pd.DataFrame({
            'code': ['000001', '000002', '000003'],
            'price': [10.1, 20.2, 30.3],  # 略有差异但在容差范围内
            'total_market_cap': [101e8, 202e8, 303e8],
        })
        
        match_rate, discrepancies = validator.cross_validate_sources(source1, source2)
        
        assert match_rate >= 90  # 差异在容差范围内
    
    def test_global_validator_instance(self):
        """测试全局验证器实例"""
        validator1 = get_accuracy_validator()
        validator2 = get_accuracy_validator()
        
        assert validator1 is validator2  # 单例模式
    
    def test_convenience_function(self, valid_stock_data):
        """测试便捷函数"""
        report = validate_data_accuracy(valid_stock_data)
        
        assert report is not None
        assert isinstance(report, DataAccuracyReport)


class TestDataAccuracyWithRealData:
    """使用真实数据测试数据准确率"""
    
    @pytest.fixture
    def validator(self):
        """创建验证器实例"""
        return DataAccuracyValidator(target_accuracy=99.0)
    
    def test_real_market_data_accuracy(self, validator):
        """测试真实市场数据准确率"""
        import requests
        
        try:
            from core.stock_screener import get_data_source_manager
            
            manager = get_data_source_manager()
            result = manager.get_mainboard_stocks()
            
            if not result.success or result.data is None or result.data.empty:
                pytest.skip("无法获取市场数据")
            
            # 验证数据准确率
            report = validator.validate_accuracy(result.data)
            
            print(f"\n真实数据准确率验证结果:")
            print(f"  总记录数: {report.total_records}")
            print(f"  总体准确率: {report.overall_accuracy:.2f}%")
            print(f"  准确率等级: {report.accuracy_level.value}")
            print(f"  是否达标: {report.meets_target}")
            
            # 打印各字段准确率
            print(f"\n字段准确率:")
            for field_result in report.field_results:
                print(f"  {field_result.field_name}: {field_result.accuracy_rate:.2f}%")
            
            # 验证准确率达到99%目标
            assert report.overall_accuracy >= 99.0, (
                f"数据准确率({report.overall_accuracy:.2f}%)未达到99%目标"
            )
            assert bool(report.meets_target) is True
            
        except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as e:
            pytest.skip(f"网络超时，跳过测试: {e}")
        except ImportError as e:
            pytest.skip(f"模块导入失败: {e}")
    
    def test_tech_stock_pool_data_accuracy(self, validator):
        """测试科技股池数据准确率"""
        try:
            from config.tech_stock_pool import get_tech_stock_pool
            
            pool = get_tech_stock_pool()
            all_stocks = pool.get_all_stocks()
            
            if not all_stocks:
                pytest.skip("科技股池为空")
            
            # 构建股票池数据
            pool_data = pd.DataFrame([
                {
                    'code': stock.code,
                    'name': stock.name,
                    'industry': stock.sector,
                }
                for stock in all_stocks
            ])
            
            # 验证基本字段准确率
            report = validator.validate_accuracy(pool_data)
            
            print(f"\n科技股池数据准确率:")
            print(f"  股票数量: {report.total_records}")
            print(f"  代码格式准确率: ", end="")
            
            code_result = next(
                (r for r in report.field_results if r.field_name == 'code'),
                None
            )
            if code_result:
                print(f"{code_result.accuracy_rate:.2f}%")
            
            # 股票代码格式应该100%正确
            assert code_result is not None
            assert code_result.accuracy_rate == 100.0, (
                f"股票代码格式准确率({code_result.accuracy_rate:.2f}%)应为100%"
            )
            
        except ImportError as e:
            pytest.skip(f"模块导入失败: {e}")


class TestFieldAccuracyResult:
    """字段准确率结果测试"""
    
    def test_is_accurate_property(self):
        """测试is_accurate属性"""
        # 准确率>=99%
        result1 = FieldAccuracyResult(
            field_name='test',
            total_records=100,
            accurate_records=99,
            accuracy_rate=99.0,
            validation_method=ValidationMethod.RANGE_CHECK
        )
        assert result1.is_accurate is True
        
        # 准确率<99%
        result2 = FieldAccuracyResult(
            field_name='test',
            total_records=100,
            accurate_records=98,
            accuracy_rate=98.0,
            validation_method=ValidationMethod.RANGE_CHECK
        )
        assert result2.is_accurate is False


class TestDataAccuracyReport:
    """数据准确率报告测试"""
    
    def test_meets_target_property(self):
        """测试meets_target属性"""
        # 达标
        report1 = DataAccuracyReport(
            timestamp=pd.Timestamp.now(),
            total_records=100,
            total_fields_checked=5,
            overall_accuracy=99.5,
            accuracy_level=AccuracyLevel.EXCELLENT
        )
        assert report1.meets_target is True
        
        # 未达标
        report2 = DataAccuracyReport(
            timestamp=pd.Timestamp.now(),
            total_records=100,
            total_fields_checked=5,
            overall_accuracy=98.0,
            accuracy_level=AccuracyLevel.GOOD
        )
        assert report2.meets_target is False


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
