"""
MiniQuant-Lite 测试配置和共享 Fixtures

科技股池扩充项目的测试基础设施
提供共享的测试数据、模拟对象和辅助函数
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, patch
import sys
import os

# 确保项目根目录在 Python 路径中
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ============== 测试数据生成器 ==============

@pytest.fixture
def sample_stock_codes() -> List[str]:
    """示例股票代码列表"""
    return [
        '000001', '000002', '000063', '000333', '000651',
        '600000', '600036', '600519', '600900', '601318',
        '002001', '002008', '002049', '002230', '002415',
    ]


@pytest.fixture
def sample_tech_stock_codes() -> List[str]:
    """示例科技股代码列表"""
    return [
        '000063',  # 中兴通讯
        '000333',  # 美的集团
        '002230',  # 科大讯飞
        '002415',  # 海康威视
        '600584',  # 长电科技
        '688981',  # 中芯国际
    ]


@pytest.fixture
def sample_stock_data() -> pd.DataFrame:
    """生成示例股票数据"""
    np.random.seed(42)
    n = 20
    
    codes = [f"{600000 + i:06d}" for i in range(n)]
    names = [f"测试股票{i}" for i in range(n)]
    industries = ['半导体', '人工智能', '云计算', '新能源', '5G通信'] * 4
    
    return pd.DataFrame({
        'code': codes,
        'name': names,
        'tech_industry': industries[:n],
        'roe': np.random.uniform(5, 25, n),
        'roa': np.random.uniform(3, 15, n),
        'gross_margin': np.random.uniform(20, 60, n),
        'net_margin': np.random.uniform(5, 30, n),
        'revenue_growth_1y': np.random.uniform(-10, 50, n),
        'profit_growth_1y': np.random.uniform(-20, 60, n),
        'debt_ratio': np.random.uniform(20, 70, n),
        'current_ratio': np.random.uniform(1, 3, n),
        'pe_ratio': np.random.uniform(10, 100, n),
        'pb_ratio': np.random.uniform(1, 10, n),
        'total_market_cap': np.random.uniform(50, 500, n),
        'float_market_cap': np.random.uniform(30, 400, n),
        'daily_turnover': np.random.uniform(1, 20, n),
        'turnover_rate': np.random.uniform(0.5, 5, n),
        'volatility_annual': np.random.uniform(20, 60, n),
        'close': np.random.uniform(10, 100, n),
    })


@pytest.fixture
def sample_financial_data() -> pd.DataFrame:
    """生成示例财务数据"""
    np.random.seed(42)
    n = 10
    
    return pd.DataFrame({
        'code': [f"{600000 + i:06d}" for i in range(n)],
        'name': [f"财务测试{i}" for i in range(n)],
        'roe': np.random.uniform(8, 20, n),
        'roa': np.random.uniform(4, 12, n),
        'gross_margin': np.random.uniform(25, 50, n),
        'net_margin': np.random.uniform(8, 25, n),
        'debt_ratio': np.random.uniform(25, 55, n),
        'current_ratio': np.random.uniform(1.2, 2.5, n),
        'quick_ratio': np.random.uniform(0.8, 2.0, n),
        'cash_flow_ratio': np.random.uniform(0.1, 0.5, n),
    })


@pytest.fixture
def sample_market_data() -> pd.DataFrame:
    """生成示例市场数据"""
    np.random.seed(42)
    n = 10
    
    return pd.DataFrame({
        'code': [f"{600000 + i:06d}" for i in range(n)],
        'name': [f"市场测试{i}" for i in range(n)],
        'total_market_cap': np.random.uniform(100, 1000, n),
        'float_market_cap': np.random.uniform(80, 800, n),
        'daily_turnover': np.random.uniform(5, 50, n),
        'turnover_rate': np.random.uniform(1, 5, n),
        'pe_ratio': np.random.uniform(15, 60, n),
        'pb_ratio': np.random.uniform(1.5, 6, n),
        'volatility_annual': np.random.uniform(25, 50, n),
        'max_drawdown': np.random.uniform(10, 40, n),
    })


@pytest.fixture
def empty_dataframe() -> pd.DataFrame:
    """空数据框"""
    return pd.DataFrame()


@pytest.fixture
def minimal_stock_data() -> pd.DataFrame:
    """最小化股票数据（仅必需字段）"""
    return pd.DataFrame({
        'code': ['000001', '600000'],
        'name': ['平安银行', '浦发银行'],
        'price': [10.5, 8.2],
    })


# ============== 模拟对象 ==============

@pytest.fixture
def mock_data_source():
    """模拟数据源"""
    mock = Mock()
    mock.fetch_stock_list.return_value = pd.DataFrame({
        'code': ['000001', '600000'],
        'name': ['测试A', '测试B'],
    })
    mock.is_available.return_value = True
    return mock


@pytest.fixture
def mock_screener_config():
    """模拟筛选器配置"""
    from core.stock_screener.config_manager import ScreenerConfig
    
    config = ScreenerConfig()
    config.target_pool_size = 80
    config.min_pool_size = 60
    config.max_pool_size = 100
    return config


# ============== 辅助函数 ==============

def create_test_stock_data(n: int = 10, seed: int = 42) -> pd.DataFrame:
    """创建测试股票数据的辅助函数"""
    np.random.seed(seed)
    
    codes = [f"{600000 + i:06d}" for i in range(n)]
    names = [f"测试股票{i}" for i in range(n)]
    industries = ['半导体', '人工智能', '云计算', '新能源', '5G通信'] * (n // 5 + 1)
    
    return pd.DataFrame({
        'code': codes,
        'name': names,
        'tech_industry': industries[:n],
        'roe': np.random.uniform(5, 25, n),
        'roa': np.random.uniform(3, 15, n),
        'gross_margin': np.random.uniform(20, 60, n),
        'net_margin': np.random.uniform(5, 30, n),
        'revenue_growth_1y': np.random.uniform(-10, 50, n),
        'profit_growth_1y': np.random.uniform(-20, 60, n),
        'debt_ratio': np.random.uniform(20, 70, n),
        'current_ratio': np.random.uniform(1, 3, n),
        'pe_ratio': np.random.uniform(10, 100, n),
        'pb_ratio': np.random.uniform(1, 10, n),
        'total_market_cap': np.random.uniform(50, 500, n),
        'float_market_cap': np.random.uniform(30, 400, n),
        'daily_turnover': np.random.uniform(1, 20, n),
        'turnover_rate': np.random.uniform(0.5, 5, n),
        'volatility_annual': np.random.uniform(20, 60, n),
        'close': np.random.uniform(10, 100, n),
    })


# ============== 测试标记 ==============

def pytest_configure(config):
    """配置 pytest 标记"""
    config.addinivalue_line("markers", "unit: 单元测试")
    config.addinivalue_line("markers", "integration: 集成测试")
    config.addinivalue_line("markers", "slow: 慢速测试")
    config.addinivalue_line("markers", "screener: 股票筛选测试")
    config.addinivalue_line("markers", "scoring: 评分系统测试")
    config.addinivalue_line("markers", "risk: 风险控制测试")
    config.addinivalue_line("markers", "data: 数据处理测试")
    config.addinivalue_line("markers", "ci: CI 测试")


# ============== 测试会话钩子 ==============

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """设置测试环境"""
    # 设置环境变量
    os.environ['TESTING'] = 'true'
    
    yield
    
    # 清理环境变量
    if 'TESTING' in os.environ:
        del os.environ['TESTING']


@pytest.fixture(autouse=True)
def reset_singletons():
    """重置单例对象（每个测试后）"""
    yield
    
    # 重置可能的单例缓存
    try:
        from core.stock_screener import (
            get_data_source_manager,
            get_data_cleaner,
            get_screener_config,
            get_industry_screener,
        )
        # 单例通常在模块级别缓存，这里不做强制重置
    except ImportError:
        pass


# ============== 性能测试辅助 ==============

@pytest.fixture
def performance_timer():
    """性能计时器"""
    import time
    
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
            
        def start(self):
            self.start_time = time.time()
            
        def stop(self):
            self.end_time = time.time()
            
        @property
        def elapsed(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None
            
        def __enter__(self):
            self.start()
            return self
            
        def __exit__(self, *args):
            self.stop()
    
    return Timer()


# ============== 数据验证辅助 ==============

@pytest.fixture
def data_validator():
    """数据验证辅助类"""
    
    class DataValidator:
        @staticmethod
        def is_valid_stock_code(code: str) -> bool:
            """验证股票代码格式"""
            if not isinstance(code, str):
                return False
            if len(code) != 6:
                return False
            if not code.isdigit():
                return False
            # 主板和中小板代码前缀
            valid_prefixes = ('000', '001', '002', '600', '601', '603', '605')
            return code.startswith(valid_prefixes)
        
        @staticmethod
        def is_valid_score(score: float) -> bool:
            """验证评分范围"""
            return 0 <= score <= 100
        
        @staticmethod
        def has_required_columns(df: pd.DataFrame, columns: List[str]) -> bool:
            """验证数据框包含必需列"""
            return all(col in df.columns for col in columns)
    
    return DataValidator()
