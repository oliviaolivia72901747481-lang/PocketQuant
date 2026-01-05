"""
CI 冒烟测试

快速验证核心功能的基本可用性
这些测试应该在 CI 环境中快速执行

Requirements: 技术风险 - 实现自动化测试和持续集成
"""

import pytest
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.mark.ci
class TestModuleImports:
    """模块导入测试 - 验证所有核心模块可以正常导入"""
    
    def test_import_stock_screener(self):
        """测试股票筛选模块导入"""
        from core import stock_screener
        assert stock_screener is not None
    
    def test_import_data_source(self):
        """测试数据源模块导入"""
        from core.stock_screener import DataSourceManager
        assert DataSourceManager is not None
    
    def test_import_data_cleaner(self):
        """测试数据清洗模块导入"""
        from core.stock_screener import DataCleaner
        assert DataCleaner is not None
    
    def test_import_industry_screener(self):
        """测试行业筛选模块导入"""
        from core.stock_screener import IndustryScreener
        assert IndustryScreener is not None
    
    def test_import_financial_screener(self):
        """测试财务筛选模块导入"""
        from core.stock_screener import FinancialScreener
        assert FinancialScreener is not None
    
    def test_import_market_screener(self):
        """测试市场筛选模块导入"""
        from core.stock_screener import MarketScreener
        assert MarketScreener is not None
    
    def test_import_comprehensive_scorer(self):
        """测试综合评分模块导入"""
        from core.stock_screener import ComprehensiveScorer
        assert ComprehensiveScorer is not None
    
    def test_import_quality_validator(self):
        """测试质量验证模块导入"""
        from core.stock_screener import DataQualityMonitor
        assert DataQualityMonitor is not None
    
    def test_import_risk_controller(self):
        """测试风险控制模块导入"""
        from core.stock_screener import RiskAssessor
        assert RiskAssessor is not None
    
    def test_import_pool_updater(self):
        """测试股票池更新模块导入"""
        from core.stock_screener import PoolUpdater
        assert PoolUpdater is not None
    
    def test_import_system_integrator(self):
        """测试系统集成模块导入"""
        from core.stock_screener import SystemIntegrator
        assert SystemIntegrator is not None


@pytest.mark.ci
class TestConfigurationLoading:
    """配置加载测试 - 验证配置文件可以正常加载"""
    
    def test_screener_config_loading(self):
        """测试筛选器配置加载"""
        from core.stock_screener import get_screener_config
        config = get_screener_config()
        assert config is not None
        assert config.target_pool_size > 0
    
    def test_industry_keywords_loading(self):
        """测试行业关键词配置加载"""
        from core.stock_screener import get_screener_config
        config = get_screener_config()
        keywords = config.industry_keywords.to_dict()
        assert len(keywords) >= 8
        assert '半导体' in keywords
    
    def test_scoring_weights_validation(self):
        """测试评分权重验证"""
        from core.stock_screener.config_manager import ScoringWeights
        weights = ScoringWeights()
        assert weights.validate()


@pytest.mark.ci
class TestSingletonPatterns:
    """单例模式测试 - 验证单例对象正确工作"""
    
    def test_data_source_manager_singleton(self):
        """测试数据源管理器单例"""
        from core.stock_screener import get_data_source_manager
        manager1 = get_data_source_manager()
        manager2 = get_data_source_manager()
        assert manager1 is manager2
    
    def test_data_cleaner_singleton(self):
        """测试数据清洗器单例"""
        from core.stock_screener import get_data_cleaner
        cleaner1 = get_data_cleaner()
        cleaner2 = get_data_cleaner()
        assert cleaner1 is cleaner2
    
    def test_industry_screener_singleton(self):
        """测试行业筛选器单例"""
        from core.stock_screener import get_industry_screener
        screener1 = get_industry_screener()
        screener2 = get_industry_screener()
        assert screener1 is screener2
    
    def test_comprehensive_scorer_singleton(self):
        """测试综合评分器单例"""
        from core.stock_screener import get_comprehensive_scorer
        scorer1 = get_comprehensive_scorer()
        scorer2 = get_comprehensive_scorer()
        assert scorer1 is scorer2


@pytest.mark.ci
class TestBasicFunctionality:
    """基本功能测试 - 验证核心功能可以正常执行"""
    
    def test_data_cleaner_initialization(self):
        """测试数据清洗器初始化"""
        from core.stock_screener import DataCleaner
        cleaner = DataCleaner()
        assert len(cleaner.REQUIRED_FIELDS) > 0
        assert len(cleaner.NUMERIC_FIELDS) > 0
    
    def test_industry_screener_initialization(self):
        """测试行业筛选器初始化"""
        from core.stock_screener import IndustryScreener
        screener = IndustryScreener()
        assert screener.keyword_config is not None
    
    def test_industry_matching(self):
        """测试行业匹配功能"""
        from core.stock_screener import IndustryScreener, TechIndustry
        screener = IndustryScreener()
        
        # 测试半导体匹配
        industry, confidence, _ = screener.match_industry(
            name="中芯国际",
            business_desc="集成电路芯片制造"
        )
        assert industry == TechIndustry.SEMICONDUCTOR
        assert confidence > 0
    
    def test_comprehensive_scorer_initialization(self):
        """测试综合评分器初始化"""
        from core.stock_screener import ComprehensiveScorer
        scorer = ComprehensiveScorer()
        assert scorer.weights is not None
        assert scorer.financial_screener is not None
        assert scorer.market_screener is not None
    
    def test_risk_assessor_initialization(self):
        """测试风险评估器初始化"""
        from core.stock_screener import RiskAssessor
        assessor = RiskAssessor()
        assert assessor.thresholds is not None


@pytest.mark.ci
class TestDataValidation:
    """数据验证测试 - 验证数据验证功能"""
    
    def test_empty_data_handling(self):
        """测试空数据处理"""
        import pandas as pd
        from core.stock_screener import DataCleaner, DataQualityLevel
        
        cleaner = DataCleaner()
        cleaned_df, report = cleaner.clean_stock_data(pd.DataFrame())
        
        assert cleaned_df.empty
        assert report.quality_level == DataQualityLevel.UNACCEPTABLE
    
    def test_mainboard_stock_filtering(self):
        """测试主板股票过滤"""
        import pandas as pd
        from core.stock_screener import DataCleaner
        
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
    
    def test_st_stock_removal(self):
        """测试ST股票移除"""
        import pandas as pd
        from core.stock_screener import DataCleaner
        
        cleaner = DataCleaner()
        test_data = pd.DataFrame({
            'code': ['000001', '000002', '000003'],
            'name': ['正常股票', 'ST问题股', '*ST退市股'],
            'price': [10, 5, 2],
        })
        
        filtered_df = cleaner.remove_st_stocks(test_data)
        
        assert len(filtered_df) == 1
        assert filtered_df.iloc[0]['name'] == '正常股票'


@pytest.mark.ci
class TestTechStockModule:
    """科技股模块测试"""
    
    def test_import_tech_stock_modules(self):
        """测试科技股模块导入"""
        from core.tech_stock import hard_filter
        from core.tech_stock import market_filter
        from core.tech_stock import signal_generator
        assert hard_filter is not None
        assert market_filter is not None
        assert signal_generator is not None
    
    def test_hard_filter_initialization(self):
        """测试硬过滤器初始化"""
        from core.tech_stock.hard_filter import HardFilter
        filter_instance = HardFilter()
        assert filter_instance is not None


@pytest.mark.ci
class TestConfigFiles:
    """配置文件测试"""
    
    def test_tech_stock_pool_exists(self):
        """测试科技股池配置存在"""
        from config import tech_stock_pool
        assert hasattr(tech_stock_pool, 'TECH_STOCK_POOL')
    
    def test_tech_stock_config_exists(self):
        """测试科技股配置存在"""
        from config import tech_stock_config
        assert tech_stock_config is not None
    
    def test_settings_exists(self):
        """测试设置文件存在"""
        from config import settings
        assert settings is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-m', 'ci'])
