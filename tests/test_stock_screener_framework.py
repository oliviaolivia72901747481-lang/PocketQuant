"""
股票筛选引擎框架测试

验证里程碑1的完成情况：
- 数据获取和基础筛选功能正常
- 系统架构的可扩展性

Requirements: 1.1, 1.3, 2.1, 2.3, 7.1, 7.2, 7.3, 7.4
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.stock_screener import (
    DataSourceManager,
    DataSourceConfig,
    DataSourceResult,
    DataSourceType,
    DataCleaner,
    DataQualityReport,
    DataQualityLevel,
    ScreenerConfigManager,
    ScreenerConfig,
    IndustryScreener,
    TechIndustry,
    IndustryKeywordConfig,
    get_data_source_manager,
    get_data_cleaner,
    get_screener_config,
    get_industry_screener,
)


class TestDataSourceManager:
    """数据源管理器测试"""
    
    def test_initialization(self):
        """测试初始化"""
        manager = DataSourceManager()
        assert manager is not None
        
        # 验证默认数据源配置
        enabled_sources = manager.get_enabled_sources()
        assert len(enabled_sources) >= 1
        assert DataSourceType.AKSHARE in enabled_sources
    
    def test_configure_source(self):
        """测试数据源配置"""
        manager = DataSourceManager()
        
        config = DataSourceConfig(
            source_type=DataSourceType.AKSHARE,
            enabled=True,
            priority=1,
            max_retries=5,
            retry_delay=2.0
        )
        
        manager.configure_source(DataSourceType.AKSHARE, config)
        
        # 验证配置已更新
        assert manager._source_configs[DataSourceType.AKSHARE].max_retries == 5
        assert manager._source_configs[DataSourceType.AKSHARE].retry_delay == 2.0
    
    def test_health_check(self):
        """测试健康检查"""
        manager = DataSourceManager()
        
        health_report = manager.check_health()
        
        assert 'overall_healthy' in health_report
        assert 'sources' in health_report
        assert 'akshare' in health_report['sources']
    
    def test_statistics(self):
        """测试统计功能"""
        manager = DataSourceManager()
        
        stats = manager.get_statistics()
        
        assert 'total_requests' in stats
        assert 'successful_requests' in stats
        assert 'failed_requests' in stats
        assert 'source_usage' in stats
    
    def test_singleton_pattern(self):
        """测试单例模式"""
        manager1 = get_data_source_manager()
        manager2 = get_data_source_manager()
        
        assert manager1 is manager2


class TestDataCleaner:
    """数据清洗器测试"""
    
    def test_initialization(self):
        """测试初始化"""
        cleaner = DataCleaner()
        assert cleaner is not None
        assert len(cleaner.REQUIRED_FIELDS) > 0
        assert len(cleaner.NUMERIC_FIELDS) > 0
    
    def test_clean_empty_data(self):
        """测试清洗空数据"""
        cleaner = DataCleaner()
        
        cleaned_df, report = cleaner.clean_stock_data(pd.DataFrame())
        
        assert cleaned_df.empty
        assert report.total_records == 0
        assert report.quality_level == DataQualityLevel.UNACCEPTABLE
    
    def test_clean_valid_data(self):
        """测试清洗有效数据"""
        cleaner = DataCleaner()
        
        # 创建测试数据
        test_data = pd.DataFrame({
            'code': ['000001', '600000', '002001'],
            'name': ['平安银行', '浦发银行', '新和成'],
            'price': [10.5, 8.2, 25.3],
            'total_market_cap': [1e11, 8e10, 5e10],
            'float_market_cap': [8e10, 6e10, 4e10],
            'turnover_rate': [1.5, 2.0, 3.5],
            'pe_ratio': [8.5, 6.2, 25.0],
            'pb_ratio': [0.8, 0.6, 3.5],
        })
        
        cleaned_df, report = cleaner.clean_stock_data(test_data)
        
        assert len(cleaned_df) == 3
        assert report.valid_records == 3
        assert report.quality_score > 0
    
    def test_filter_mainboard_stocks(self):
        """测试过滤主板股票"""
        cleaner = DataCleaner()
        
        test_data = pd.DataFrame({
            'code': ['000001', '300001', '688001', '002001', '600001'],
            'name': ['股票A', '股票B', '股票C', '股票D', '股票E'],
            'price': [10, 20, 30, 40, 50],
        })
        
        filtered_df = cleaner.filter_mainboard_stocks(test_data, include_sme=True)
        
        # 应该包含000001, 002001, 600001
        assert len(filtered_df) == 3
        assert '300001' not in filtered_df['code'].values
        assert '688001' not in filtered_df['code'].values
    
    def test_remove_st_stocks(self):
        """测试移除ST股票"""
        cleaner = DataCleaner()
        
        test_data = pd.DataFrame({
            'code': ['000001', '000002', '000003'],
            'name': ['正常股票', 'ST问题股', '*ST退市股'],
            'price': [10, 5, 2],
        })
        
        filtered_df = cleaner.remove_st_stocks(test_data)
        
        assert len(filtered_df) == 1
        assert filtered_df.iloc[0]['name'] == '正常股票'
    
    def test_quality_summary(self):
        """测试质量摘要生成"""
        cleaner = DataCleaner()
        
        test_data = pd.DataFrame({
            'code': ['000001'],
            'name': ['测试股票'],
            'price': [10.0],
        })
        
        _, report = cleaner.clean_stock_data(test_data)
        summary = cleaner.get_quality_summary(report)
        
        assert '数据质量报告摘要' in summary
        assert '总记录数' in summary
    
    def test_singleton_pattern(self):
        """测试单例模式"""
        cleaner1 = get_data_cleaner()
        cleaner2 = get_data_cleaner()
        
        assert cleaner1 is cleaner2


class TestScreenerConfig:
    """筛选器配置测试"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = ScreenerConfig()
        
        assert config.target_pool_size == 80
        assert config.min_pool_size == 60
        assert config.max_pool_size == 100
        assert config.exclude_st == True
    
    def test_config_validation(self):
        """测试配置验证"""
        manager = ScreenerConfigManager()
        
        # 有效配置
        errors = manager.validate_config()
        assert len(errors) == 0
        
        # 无效配置
        config = manager.get_config()
        config.min_pool_size = 200
        config.max_pool_size = 100
        
        errors = manager.validate_config(config)
        assert len(errors) > 0
    
    def test_scoring_weights_validation(self):
        """测试评分权重验证"""
        from core.stock_screener.config_manager import ScoringWeights
        
        # 有效权重
        weights = ScoringWeights(
            financial_health=0.35,
            growth_potential=0.25,
            market_performance=0.20,
            competitive_advantage=0.20
        )
        assert weights.validate() == True
        
        # 无效权重
        invalid_weights = ScoringWeights(
            financial_health=0.5,
            growth_potential=0.5,
            market_performance=0.5,
            competitive_advantage=0.5
        )
        assert invalid_weights.validate() == False
    
    def test_industry_keywords(self):
        """测试行业关键词配置"""
        config = get_screener_config()
        keywords = config.industry_keywords.to_dict()
        
        assert '半导体' in keywords
        assert '人工智能' in keywords
        assert len(keywords) >= 8


class TestIndustryScreener:
    """行业筛选器测试"""
    
    def test_initialization(self):
        """测试初始化"""
        screener = IndustryScreener()
        assert screener is not None
        assert screener.keyword_config is not None
    
    def test_match_semiconductor(self):
        """测试半导体行业匹配"""
        screener = IndustryScreener()
        
        industry, confidence, keywords = screener.match_industry(
            name="中芯国际",
            business_desc="集成电路芯片制造"
        )
        
        assert industry == TechIndustry.SEMICONDUCTOR
        assert confidence > 0
        assert len(keywords) > 0
    
    def test_match_ai(self):
        """测试人工智能行业匹配"""
        screener = IndustryScreener()
        
        industry, confidence, keywords = screener.match_industry(
            name="科大讯飞",
            business_desc="人工智能语音识别"
        )
        
        assert industry == TechIndustry.AI
        assert confidence > 0
    
    def test_match_unknown(self):
        """测试未知行业匹配"""
        screener = IndustryScreener()
        
        industry, confidence, keywords = screener.match_industry(
            name="贵州茅台",
            business_desc="白酒生产销售"
        )
        
        assert industry == TechIndustry.UNKNOWN
        assert confidence == 0
    
    def test_screen_tech_stocks(self):
        """测试科技股筛选"""
        screener = IndustryScreener()
        
        test_data = pd.DataFrame({
            'code': ['000001', '000002', '000003'],
            'name': ['芯片科技', '白酒集团', '人工智能'],
            'price': [50, 200, 80],
        })
        
        tech_df, results = screener.screen_tech_stocks(test_data)
        
        assert len(tech_df) == 2  # 芯片科技和人工智能
        assert len(results) == 2
    
    def test_industry_distribution(self):
        """测试行业分布统计"""
        screener = IndustryScreener()
        
        test_data = pd.DataFrame({
            'code': ['000001', '000002', '000003', '000004'],
            'name': ['芯片A', '芯片B', 'AI公司', '软件公司'],
            'price': [50, 60, 70, 80],
        })
        
        _, results = screener.screen_tech_stocks(test_data)
        distribution = screener.get_industry_distribution(results)
        
        assert isinstance(distribution, dict)
        assert sum(distribution.values()) == len(results)
    
    def test_is_tech_stock(self):
        """测试科技股判断"""
        screener = IndustryScreener()
        
        assert screener.is_tech_stock("中芯国际", "芯片制造") == True
        assert screener.is_tech_stock("贵州茅台", "白酒生产") == False
    
    def test_add_keyword(self):
        """测试添加关键词"""
        screener = IndustryScreener()
        
        # 添加新关键词
        result = screener.add_keyword(TechIndustry.SEMICONDUCTOR, "新型芯片")
        assert result == True
        
        # 验证关键词已添加
        keywords = screener.get_keywords(TechIndustry.SEMICONDUCTOR)
        assert "新型芯片" in keywords
    
    def test_singleton_pattern(self):
        """测试单例模式"""
        screener1 = get_industry_screener()
        screener2 = get_industry_screener()
        
        assert screener1 is screener2


class TestSystemArchitecture:
    """系统架构测试"""
    
    def test_module_imports(self):
        """测试模块导入"""
        from core.stock_screener import (
            DataSourceManager,
            DataCleaner,
            ScreenerConfigManager,
            IndustryScreener,
        )
        
        assert DataSourceManager is not None
        assert DataCleaner is not None
        assert ScreenerConfigManager is not None
        assert IndustryScreener is not None
    
    def test_extensibility(self):
        """测试可扩展性"""
        # 验证可以创建自定义配置
        custom_config = IndustryKeywordConfig()
        custom_config.semiconductor.append("自定义关键词")
        
        screener = IndustryScreener(keyword_config=custom_config)
        keywords = screener.get_keywords(TechIndustry.SEMICONDUCTOR)
        
        assert "自定义关键词" in keywords
    
    def test_integration(self):
        """测试组件集成"""
        # 获取各组件实例
        data_manager = get_data_source_manager()
        cleaner = get_data_cleaner()
        config = get_screener_config()
        screener = get_industry_screener()
        
        # 验证组件可以协同工作
        assert data_manager is not None
        assert cleaner is not None
        assert config is not None
        assert screener is not None
        
        # 验证配置可以影响筛选器行为
        assert config.exclude_st == True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
