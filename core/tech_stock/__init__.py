# MiniQuant-Lite Tech Stock Module
# 科技股专属板块：宏观风控、信号生成、卖出管理、回测验证
#
# 核心设计原则：
# - 小资金生存优先：股价≤80元、市值/成交额过滤
# - T+1 制度最优解：14:45 尾盘判定信号
# - 风险控制优先：信号优先级 紧急避险 > 止损 > 止盈 > 趋势
# - 震荡市验证：强制验证 2022-2023 表现
#
# Requirements: 12.1, 12.2

from core.tech_stock.market_filter import MarketFilter, MarketStatus
from core.tech_stock.sector_ranker import SectorRanker, SectorRank
from core.tech_stock.hard_filter import HardFilter, HardFilterResult
# from core.tech_stock.signal_generator import TechSignalGenerator, TechBuySignal  # Temporarily disabled
from core.tech_stock.exit_manager import TechExitManager, TechExitSignal, SignalPriority
from core.tech_stock.backtester import TechBacktester, TechBacktestResult, PeriodPerformance

__all__ = [
    # 大盘红绿灯过滤器
    'MarketFilter',
    'MarketStatus',
    # 行业强弱排位器
    'SectorRanker',
    'SectorRank',
    # 硬性筛选器
    'HardFilter',
    'HardFilterResult',
    # 科技股买入信号生成器
    'TechSignalGenerator',
    'TechBuySignal',
    # 卖出信号管理器
    'TechExitManager',
    'TechExitSignal',
    'SignalPriority',
    # 回测引擎
    'TechBacktester',
    'TechBacktestResult',
    'PeriodPerformance',
]
