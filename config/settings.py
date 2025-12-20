"""
MiniQuant-Lite 全局配置模块

提供系统运行所需的所有配置参数，包括：
- 资金配置（初始资金、手续费率、印花税率）
- 回测配置（起止日期）
- 仓位配置（最大持仓数、最小交易金额）
- 数据路径配置
- 日志配置

Requirements: 1.7, 8.1, 8.5
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional
import os


@dataclass
class FundConfig:
    """资金配置"""
    initial_capital: float = 55000.0      # 初始资金（元）
    commission_rate: float = 0.0003       # 手续费率（万三）
    min_commission: float = 5.0           # 最低手续费（5元低消）
    stamp_tax_rate: float = 0.001         # 印花税率（千一，仅卖出收取）


@dataclass
class PositionConfig:
    """仓位配置"""
    max_positions_count: int = 2          # 最大同时持仓只数
    position_tolerance: float = 0.05      # 仓位容差（允许超限5%）
    min_trade_amount: float = 15000.0     # 最小交易金额门槛
    cash_buffer: float = 0.05             # 现金缓冲比例（5%）


@dataclass
class BacktestConfig:
    """回测配置"""
    start_date: Optional[str] = None      # 回测开始日期 'YYYY-MM-DD'
    end_date: Optional[str] = None        # 回测结束日期 'YYYY-MM-DD'
    benchmark_code: str = '000300'        # 基准指数代码（沪深300）
    
    def __post_init__(self):
        """设置默认日期（最近一年）"""
        if self.end_date is None:
            self.end_date = date.today().strftime('%Y-%m-%d')
        if self.start_date is None:
            start = date.today() - timedelta(days=365)
            self.start_date = start.strftime('%Y-%m-%d')


@dataclass
class StrategyConfig:
    """策略配置"""
    # MACD 参数
    macd_fast_period: int = 12
    macd_slow_period: int = 26
    macd_signal_period: int = 9
    
    # 均线参数
    ma_period: int = 60                   # MA60 趋势均线
    ma_market_period: int = 20            # 大盘滤网均线周期
    
    # RSI 参数
    rsi_period: int = 14
    rsi_upper: int = 80                   # RSI 上限
    rsi_extreme: int = 90                 # RSI 极端值
    
    # 止损止盈参数
    hard_stop_loss: float = -0.08         # 硬止损（-8%）
    trailing_start: float = 0.15          # 移动止盈启动阈值（+15%）
    trailing_stop: float = 0.05           # 移动止盈回撤比例（5%）


@dataclass
class LiquidityConfig:
    """流动性过滤配置"""
    min_market_cap: float = 5e9           # 最小流通市值（50亿）
    max_market_cap: float = 5e10          # 最大流通市值（500亿）
    min_turnover_rate: float = 0.02       # 最小换手率（2%）
    max_turnover_rate: float = 0.15       # 最大换手率（15%）
    exclude_st: bool = True               # 剔除 ST 股
    min_listing_days: int = 60            # 最小上市天数


@dataclass
class PathConfig:
    """路径配置"""
    base_dir: str = field(default_factory=lambda: os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data_dir: str = field(default='data')
    raw_data_dir: str = field(default='data/raw')
    processed_data_dir: str = field(default='data/processed')
    log_dir: str = field(default='logs')
    
    def __post_init__(self):
        """确保目录存在"""
        for dir_name in [self.data_dir, self.raw_data_dir, self.processed_data_dir, self.log_dir]:
            dir_path = os.path.join(self.base_dir, dir_name)
            os.makedirs(dir_path, exist_ok=True)
    
    def get_raw_path(self) -> str:
        """获取原始数据目录绝对路径"""
        return os.path.join(self.base_dir, self.raw_data_dir)
    
    def get_processed_path(self) -> str:
        """获取处理后数据目录绝对路径"""
        return os.path.join(self.base_dir, self.processed_data_dir)
    
    def get_log_path(self) -> str:
        """获取日志目录绝对路径"""
        return os.path.join(self.base_dir, self.log_dir)


@dataclass
class LogConfig:
    """日志配置"""
    level: str = 'INFO'                   # 日志级别
    format: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format: str = '%Y-%m-%d %H:%M:%S'
    file_prefix: str = 'miniquant'        # 日志文件前缀


@dataclass
class Settings:
    """
    全局配置类
    
    集中管理所有系统配置，支持通过配置文件或代码修改
    """
    fund: FundConfig = field(default_factory=FundConfig)
    position: PositionConfig = field(default_factory=PositionConfig)
    backtest: BacktestConfig = field(default_factory=BacktestConfig)
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    liquidity: LiquidityConfig = field(default_factory=LiquidityConfig)
    path: PathConfig = field(default_factory=PathConfig)
    log: LogConfig = field(default_factory=LogConfig)
    
    # AkShare 推荐版本
    RECOMMENDED_AKSHARE_VERSION: str = '1.12.0'


# 全局配置实例（单例模式）
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    获取全局配置实例
    
    Returns:
        Settings 单例实例
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """重置全局配置（主要用于测试）"""
    global _settings
    _settings = None
