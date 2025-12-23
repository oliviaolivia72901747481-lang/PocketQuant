"""
科技股专属板块配置模块

提供科技股模块所需的所有配置参数，包括：
- 硬性筛选阈值（股价、市值、成交额）
- 技术指标参数（RSI、MA、MACD）
- 止损止盈参数
- 行业指数映射
- 科技股池配置

Requirements: 12.1, 12.2
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ==========================================
# 硬性筛选配置（小资金生存基础）
# ==========================================

@dataclass
class HardFilterConfig:
    """硬性筛选配置 - 小资金生存基础"""
    max_price: float = 80.0              # 最高股价 80元
    min_market_cap: float = 50.0         # 最小流通市值 50亿
    max_market_cap: float = 500.0        # 最大流通市值 500亿
    min_avg_turnover: float = 1.0        # 最小日均成交额 1亿


# ==========================================
# 技术指标配置
# ==========================================

@dataclass
class TechIndicatorConfig:
    """技术指标配置"""
    # RSI 参数
    rsi_period: int = 14                 # RSI 周期
    rsi_min: int = 55                    # RSI 买入下限
    rsi_max: int = 80                    # RSI 买入上限
    rsi_overbought: int = 85             # RSI 超买阈值（止盈）
    
    # 均线参数
    ma5_period: int = 5                  # MA5 周期
    ma20_period: int = 20                # MA20 周期
    ma60_period: int = 60                # MA60 周期
    
    # MACD 参数
    macd_fast: int = 12                  # MACD 快线周期
    macd_slow: int = 26                  # MACD 慢线周期
    macd_signal: int = 9                 # MACD 信号线周期
    
    # 量能参数
    volume_ratio_min: float = 1.5        # 最小量比


# ==========================================
# 止损止盈配置
# ==========================================

@dataclass
class ExitConfig:
    """止损止盈配置"""
    hard_stop_loss: float = -0.10        # 硬止损 -10%
    profit_threshold_1: float = 0.05     # 盈利阈值1：5%（止损移至成本）
    profit_threshold_2: float = 0.15     # 盈利阈值2：15%（止损移至MA5）
    ma20_break_days: int = 2             # MA20 跌破天数阈值
    min_position_shares: int = 100       # 最小仓位股数


# ==========================================
# 尾盘交易配置（T+1 最优解）
# ==========================================

@dataclass
class TradingWindowConfig:
    """尾盘交易窗口配置"""
    confirmation_hour: int = 14          # 确认时间 - 小时
    confirmation_minute: int = 45        # 确认时间 - 分钟
    market_close_hour: int = 15          # 收盘时间 - 小时
    market_close_minute: int = 0         # 收盘时间 - 分钟


# ==========================================
# 行业指数映射
# ==========================================

SECTOR_INDEX_MAPPING: Dict[str, Dict[str, str]] = {
    "半导体": {
        "code": "399678",
        "name": "深证半导体指数",
        "source": "深交所"
    },
    "AI应用": {
        "code": "930713",
        "name": "人工智能指数",
        "source": "中证指数"
    },
    "算力": {
        "code": "931071",
        "name": "算力指数",
        "source": "中证指数"
    },
    "消费电子": {
        "code": "931139",
        "name": "消费电子指数",
        "source": "中证指数"
    },
}


# ==========================================
# 行业龙头股映射（备选方案）
# ==========================================

SECTOR_PROXY_STOCKS: Dict[str, List[str]] = {
    "半导体": ["002371", "688981", "002049"],    # 北方华创、中芯国际、紫光国微
    "AI应用": ["300308", "002415", "300496"],    # 中际旭创、海康威视、中科创达
    "算力": ["000977", "603019", "688256"],      # 浪潮信息、中科曙光、寒武纪
    "消费电子": ["002475", "002600", "601138"],  # 立讯精密、长盈精密、工业富联
}


# ==========================================
# 科技股池配置
# ==========================================

TECH_STOCK_POOL: Dict[str, List[Dict[str, str]]] = {
    "半导体": [
        {"code": "002371", "name": "北方华创"},
        {"code": "688981", "name": "中芯国际"},
        {"code": "002049", "name": "紫光国微"},
    ],
    "AI应用": [
        {"code": "300308", "name": "中际旭创"},
        {"code": "002415", "name": "海康威视"},
        {"code": "300496", "name": "中科创达"},
    ],
    "算力": [
        {"code": "000977", "name": "浪潮信息"},
        {"code": "603019", "name": "中科曙光"},
        {"code": "688256", "name": "寒武纪"},
    ],
    "消费电子": [
        {"code": "002600", "name": "长盈精密"},
        {"code": "002475", "name": "立讯精密"},
        {"code": "601138", "name": "工业富联"},
    ],
}


# ==========================================
# 默认测试标的
# ==========================================

DEFAULT_TEST_STOCKS: Dict[str, str] = {
    "002600": "长盈精密",    # 消费电子
    "300308": "中际旭创",    # AI/算力
    "002371": "北方华创",    # 半导体
}


# ==========================================
# 回测配置
# ==========================================

@dataclass
class BacktestConfig:
    """回测配置"""
    default_start: str = "2022-01-01"
    default_end: str = "2024-12-01"
    bear_market_start: str = "2022-01-01"    # 震荡市开始
    bear_market_end: str = "2023-12-31"      # 震荡市结束
    max_drawdown_threshold: float = -0.15    # 最大回撤阈值 -15%


# ==========================================
# 信号优先级颜色映射
# ==========================================

PRIORITY_COLORS: Dict[str, str] = {
    "emergency": "red",      # 紧急避险 - 红色
    "stop_loss": "orange",   # 止损 - 橙色
    "take_profit": "yellow", # 止盈 - 黄色
    "trend_break": "blue",   # 趋势断裂 - 蓝色
}


# ==========================================
# 科技股模块总配置
# ==========================================

@dataclass
class TechStockConfig:
    """
    科技股模块总配置
    
    集中管理科技股模块所有配置
    """
    hard_filter: HardFilterConfig = field(default_factory=HardFilterConfig)
    indicator: TechIndicatorConfig = field(default_factory=TechIndicatorConfig)
    exit: ExitConfig = field(default_factory=ExitConfig)
    trading_window: TradingWindowConfig = field(default_factory=TradingWindowConfig)
    backtest: BacktestConfig = field(default_factory=BacktestConfig)
    
    # 大盘风控标的
    gem_index_code: str = "399006"       # 创业板指代码


# 全局配置实例
_tech_config: Optional[TechStockConfig] = None


def get_tech_config() -> TechStockConfig:
    """
    获取科技股模块配置实例
    
    Returns:
        TechStockConfig 单例实例
    """
    global _tech_config
    if _tech_config is None:
        _tech_config = TechStockConfig()
    return _tech_config


def reset_tech_config() -> None:
    """重置科技股模块配置（主要用于测试）"""
    global _tech_config
    _tech_config = None


# ==========================================
# 辅助函数
# ==========================================

def get_all_tech_stocks() -> List[str]:
    """
    获取所有科技股代码
    
    Returns:
        所有科技股代码列表
    """
    codes = []
    for sector_stocks in TECH_STOCK_POOL.values():
        for stock in sector_stocks:
            codes.append(stock["code"])
    return codes


def get_stock_sector(code: str) -> Optional[str]:
    """
    获取股票所属行业
    
    Args:
        code: 股票代码
        
    Returns:
        行业名称，如果不在科技股池中返回 None
    """
    for sector, stocks in TECH_STOCK_POOL.items():
        for stock in stocks:
            if stock["code"] == code:
                return sector
    return None


def get_sector_stocks(sector: str) -> List[Dict[str, str]]:
    """
    获取指定行业的股票列表
    
    Args:
        sector: 行业名称
        
    Returns:
        该行业的股票列表
    """
    return TECH_STOCK_POOL.get(sector, [])


def get_stock_name(code: str) -> str:
    """
    获取股票名称
    
    Args:
        code: 股票代码
        
    Returns:
        股票名称，如果不在科技股池中返回代码本身
    """
    for sector_stocks in TECH_STOCK_POOL.values():
        for stock in sector_stocks:
            if stock["code"] == code:
                return stock["name"]
    
    # 检查默认测试标的
    if code in DEFAULT_TEST_STOCKS:
        return DEFAULT_TEST_STOCKS[code]
    
    # 如果找不到，返回代码本身
    return code
