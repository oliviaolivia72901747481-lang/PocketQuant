# Design Document

## Overview

科技股专属板块是一个完整的科技股交易系统，包含宏观风控、信号生成、卖出管理和回测验证四大核心模块。系统采用分层架构，将风控逻辑、信号逻辑和界面展示分离，便于维护和扩展。

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    科技股专属板块 (Tech Module)                       │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │
│  │ 宏观风控层   │  │ 硬性筛选层   │  │ 信号生成层   │  │ 回测验证层  │  │
│  │             │  │             │  │             │  │            │  │
│  │ ┌─────────┐ │  │ ┌─────────┐ │  │ ┌─────────┐ │  │ ┌────────┐ │  │
│  │ │大盘红绿灯│ │  │ │价格过滤  │ │  │ │买入信号  │ │  │ │回测引擎│ │  │
│  │ └─────────┘ │  │ └─────────┘ │  │ └─────────┘ │  │ └────────┘ │  │
│  │ ┌─────────┐ │  │ ┌─────────┐ │  │ ┌─────────┐ │  │ ┌────────┐ │  │
│  │ │行业排位  │ │  │ │市值过滤  │ │  │ │卖出信号  │ │  │ │绩效分析│ │  │
│  │ └─────────┘ │  │ └─────────┘ │  │ └─────────┘ │  │ └────────┘ │  │
│  │             │  │ ┌─────────┐ │  │ ┌─────────┐ │  │ ┌────────┐ │  │
│  │             │  │ │成交额过滤│ │  │ │信号优先级│ │  │ │震荡市  │ │  │
│  │             │  │ └─────────┘ │  │ └─────────┘ │  │ │验证    │ │  │
│  │             │  │             │  │ ┌─────────┐ │  │ └────────┘ │  │
│  │             │  │             │  │ │尾盘判定  │ │  │            │  │
│  │             │  │             │  │ └─────────┘ │  │            │  │
│  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘  │
├─────────────────────────────────────────────────────────────────────┤
│                      数据层 (Data Layer)                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │
│  │ 指数数据    │  │ 个股数据    │  │ 基本面数据   │  │ 持仓数据    │  │
│  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. MarketFilter (大盘红绿灯)

```python
@dataclass
class MarketStatus:
    """大盘状态"""
    is_green: bool              # 是否绿灯
    gem_close: float            # 创业板指收盘价
    gem_ma20: float             # 创业板指 MA20
    macd_status: str            # MACD 状态 ("golden_cross" / "death_cross" / "neutral")
    check_date: date            # 检查日期
    reason: str                 # 状态原因说明

class MarketFilter:
    """大盘红绿灯过滤器"""
    
    GEM_INDEX_CODE = "399006"   # 创业板指代码
    
    def check_market_status(self) -> MarketStatus:
        """
        检查大盘状态
        
        条件：
        1. 创业板指收盘价 > MA20
        2. MACD 无死叉
        
        Returns:
            MarketStatus 对象
        """
        pass
    
    def _calculate_macd_status(self, df: pd.DataFrame) -> str:
        """计算 MACD 状态"""
        pass
```

### 2. SectorRanker (行业强弱排位)

```python
@dataclass
class SectorRank:
    """行业排名"""
    sector_name: str            # 行业名称
    index_code: str             # 行业指数代码
    return_20d: float           # 20日涨幅
    rank: int                   # 排名 (1-4)
    is_tradable: bool           # 是否可交易 (排名1-2)
    data_source: str            # 数据来源 ("index" / "proxy_stocks")

class SectorRanker:
    """行业强弱排位器"""
    
    # 科技行业指数映射
    SECTOR_INDICES = {
        "半导体": "399678",      # 深证半导体指数
        "AI应用": "930713",      # 人工智能指数
        "算力": "931071",        # 算力指数
        "消费电子": "931139",    # 消费电子指数
    }
    
    # 备选方案：行业龙头股（当指数数据不可用时使用）
    SECTOR_PROXY_STOCKS = {
        "半导体": ["002371", "688981", "002049"],  # 北方华创、中芯国际、紫光国微
        "AI应用": ["300308", "002415", "300496"],  # 中际旭创、海康威视、中科创达
        "算力": ["000977", "603019", "688256"],    # 浪潮信息、中科曙光、寒武纪
        "消费电子": ["002475", "002600", "601138"], # 立讯精密、长盈精密、工业富联
    }
    
    def get_sector_rankings(self, use_proxy_stocks: bool = False) -> List[SectorRank]:
        """
        获取行业排名
        
        计算各行业指数的20日涨幅，按涨幅排序
        
        Args:
            use_proxy_stocks: 是否使用龙头股替代指数（当指数数据不可用时）
        
        Returns:
            排序后的行业排名列表
        """
        pass
    
    def _get_index_return(self, index_code: str) -> Optional[float]:
        """
        获取指数20日涨幅
        
        Returns:
            涨幅百分比，如果获取失败返回 None
        """
        pass
    
    def _get_proxy_return(self, sector_name: str) -> float:
        """
        使用龙头股平均涨幅替代行业涨幅（备选方案）
        
        计算该行业前3大权重股的20日平均涨幅
        
        Returns:
            龙头股平均涨幅
        """
        stocks = self.SECTOR_PROXY_STOCKS.get(sector_name, [])
        returns = []
        for code in stocks:
            ret = self._get_stock_return(code)
            if ret is not None:
                returns.append(ret)
        return sum(returns) / len(returns) if returns else 0.0
    
    def is_sector_tradable(self, sector_name: str) -> bool:
        """判断行业是否可交易（排名1-2）"""
        pass
```

### 3. HardFilter (硬性筛选器 - 小资金生存基础)

```python
@dataclass
class HardFilterResult:
    """硬性筛选结果"""
    code: str                   # 股票代码
    name: str                   # 股票名称
    passed: bool                # 是否通过筛选
    price: float                # 当前价格
    market_cap: float           # 流通市值（亿元）
    avg_turnover: float         # 日均成交额（亿元）
    reject_reasons: List[str]   # 被拒绝的原因列表

class HardFilter:
    """硬性筛选器 - 小资金生存基础"""
    
    # 筛选阈值
    MAX_PRICE = 80.0            # 最高股价 80元
    MIN_MARKET_CAP = 50.0       # 最小流通市值 50亿
    MAX_MARKET_CAP = 500.0      # 最大流通市值 500亿
    MIN_AVG_TURNOVER = 1.0      # 最小日均成交额 1亿
    
    def filter_stocks(self, stock_codes: List[str]) -> List[HardFilterResult]:
        """
        对股票列表进行硬性筛选
        
        筛选条件：
        1. 股价 <= 80元
        2. 50亿 <= 流通市值 <= 500亿
        3. 日均成交额 >= 1亿
        
        Returns:
            筛选结果列表（包含通过和未通过的股票）
        """
        pass
    
    def _check_price(self, price: float) -> Tuple[bool, Optional[str]]:
        """检查股价是否符合要求"""
        if price > self.MAX_PRICE:
            return False, f"股价 {price:.2f}元 > {self.MAX_PRICE}元"
        return True, None
    
    def _check_market_cap(self, market_cap: float) -> Tuple[bool, Optional[str]]:
        """检查流通市值是否符合要求"""
        if market_cap < self.MIN_MARKET_CAP:
            return False, f"流通市值 {market_cap:.1f}亿 < {self.MIN_MARKET_CAP}亿"
        if market_cap > self.MAX_MARKET_CAP:
            return False, f"流通市值 {market_cap:.1f}亿 > {self.MAX_MARKET_CAP}亿"
        return True, None
    
    def _check_turnover(self, avg_turnover: float) -> Tuple[bool, Optional[str]]:
        """检查日均成交额是否符合要求"""
        if avg_turnover < self.MIN_AVG_TURNOVER:
            return False, f"日均成交额 {avg_turnover:.2f}亿 < {self.MIN_AVG_TURNOVER}亿"
        return True, None
    
    def get_filter_summary(self, results: List[HardFilterResult]) -> Dict:
        """获取筛选汇总统计"""
        passed = [r for r in results if r.passed]
        rejected = [r for r in results if not r.passed]
        return {
            "total": len(results),
            "passed": len(passed),
            "rejected": len(rejected),
            "reject_by_price": len([r for r in rejected if any("股价" in reason for reason in r.reject_reasons)]),
            "reject_by_market_cap": len([r for r in rejected if any("流通市值" in reason for reason in r.reject_reasons)]),
            "reject_by_turnover": len([r for r in rejected if any("成交额" in reason for reason in r.reject_reasons)]),
        }
```

### 4. TechSignalGenerator (科技股信号生成器 - 含尾盘判定)

```python
from datetime import datetime, time

@dataclass
class TechBuySignal:
    """科技股买入信号"""
    code: str                   # 股票代码
    name: str                   # 股票名称
    sector: str                 # 所属行业
    price: float                # 当前价格
    ma5: float                  # MA5
    ma20: float                 # MA20
    ma60: float                 # MA60
    rsi: float                  # RSI(14)
    volume_ratio: float         # 量比 (当日量/5日均量)
    revenue_growth: bool        # 营收正增长
    profit_growth: bool         # 净利正增长
    has_unlock: bool            # 有大额解禁
    signal_strength: float      # 信号强度 (0-100)
    generated_at: datetime      # 生成时间
    is_confirmed: bool          # 是否已确认（14:45后）
    confirmation_time: Optional[datetime]  # 确认时间

class TechSignalGenerator:
    """科技股买入信号生成器 - 含尾盘判定机制"""
    
    # 信号参数
    RSI_MIN = 55
    RSI_MAX = 80
    VOLUME_RATIO_MIN = 1.5
    
    # 尾盘判定时间 (T+1 最优解)
    EOD_CONFIRMATION_TIME = time(14, 45)  # 14:45
    MARKET_CLOSE_TIME = time(15, 0)       # 15:00
    
    def generate_signals(
        self, 
        stock_pool: List[str],
        market_status: MarketStatus,
        sector_rankings: List[SectorRank],
        hard_filter_results: List[HardFilterResult]
    ) -> List[TechBuySignal]:
        """
        生成买入信号
        
        流程：
        1. 检查大盘红绿灯（红灯直接返回空）
        2. 应用硬性筛选结果（只保留通过的股票）
        3. 过滤行业排名（只保留排名1-2的行业）
        4. 检查技术指标（趋势、动量、量能）
        5. 检查基本面（营收/净利增长、解禁）
        6. 标记信号确认状态（14:45后为已确认）
        
        Returns:
            符合条件的买入信号列表
        """
        pass
    
    def is_signal_confirmed(self) -> bool:
        """
        检查当前时间是否已过尾盘确认时间
        
        Returns:
            True if 当前时间 >= 14:45
        """
        now = datetime.now().time()
        return now >= self.EOD_CONFIRMATION_TIME
    
    def get_signal_status(self) -> str:
        """
        获取信号状态描述
        
        Returns:
            "信号已确认" if 14:45后
            "信号待确认 (14:45后生效)" if 14:45前
        """
        if self.is_signal_confirmed():
            return "信号已确认"
        return "信号待确认 (14:45后生效)"
    
    def get_trading_window_status(self) -> Dict:
        """
        获取交易窗口状态
        
        Returns:
            {
                "is_trading_window": bool,  # 是否在交易窗口 (14:45-15:00)
                "minutes_remaining": int,   # 剩余分钟数
                "status_message": str       # 状态消息
            }
        """
        now = datetime.now().time()
        if now < self.EOD_CONFIRMATION_TIME:
            return {
                "is_trading_window": False,
                "minutes_remaining": -1,
                "status_message": f"等待尾盘确认 (14:45)"
            }
        elif now <= self.MARKET_CLOSE_TIME:
            # 计算剩余分钟
            now_minutes = now.hour * 60 + now.minute
            close_minutes = self.MARKET_CLOSE_TIME.hour * 60 + self.MARKET_CLOSE_TIME.minute
            remaining = close_minutes - now_minutes
            return {
                "is_trading_window": True,
                "minutes_remaining": remaining,
                "status_message": f"⚡ 交易窗口开启，剩余 {remaining} 分钟"
            }
        else:
            return {
                "is_trading_window": False,
                "minutes_remaining": 0,
                "status_message": "今日交易已结束"
            }
    
    def _check_trend_condition(self, df: pd.DataFrame) -> bool:
        """检查趋势条件：MA5 金叉 MA20，股价 > MA60"""
        pass
    
    def _check_momentum_condition(self, df: pd.DataFrame) -> bool:
        """检查动量条件：RSI(14) 在 55-80 之间"""
        pass
    
    def _check_volume_condition(self, df: pd.DataFrame, current_time: Optional[time] = None) -> bool:
        """
        检查量能条件：当日量 > 5日均量 × 1.5
        
        注意：14:45 运行时，当日成交量约为全天的 92%-95%
        需要使用"预估全天成交量"进行比较，避免漏掉信号
        
        Args:
            df: 股票数据
            current_time: 当前时间（用于计算预估全天成交量）
        
        公式：predicted_volume = current_volume / (current_minutes / 240)
        """
        pass
    
    def _predict_daily_volume(self, current_volume: float, current_time: time) -> float:
        """
        预估全天成交量（避免"未来函数"风险）
        
        Args:
            current_volume: 当前累计成交量
            current_time: 当前时间
        
        Returns:
            预估全天成交量
        
        计算逻辑：
        - 交易时间：9:30-11:30 (120分钟) + 13:00-15:00 (120分钟) = 240分钟
        - 当前已交易分钟数 = (current_time - 9:30) 或 (current_time - 13:00 + 120)
        - 预估全天量 = 当前量 / (已交易分钟 / 240)
        """
        # 计算已交易分钟数
        hour, minute = current_time.hour, current_time.minute
        
        if hour < 11 or (hour == 11 and minute <= 30):
            # 上午交易时段 9:30-11:30
            elapsed_minutes = (hour - 9) * 60 + minute - 30
        elif hour < 13:
            # 午休时段，使用上午结束时间
            elapsed_minutes = 120
        else:
            # 下午交易时段 13:00-15:00
            elapsed_minutes = 120 + (hour - 13) * 60 + minute
        
        # 避免除零
        if elapsed_minutes <= 0:
            return current_volume
        
        # 预估全天成交量
        total_trading_minutes = 240
        predicted_volume = current_volume / (elapsed_minutes / total_trading_minutes)
        
        return predicted_volume
    
    def _check_fundamental_condition(self, code: str) -> Tuple[bool, bool, bool]:
        """检查基本面条件：营收/净利增长、无大额解禁"""
        pass
```

### 5. TechExitManager (卖出信号管理器 - 含优先级)

```python
from enum import IntEnum

class SignalPriority(IntEnum):
    """信号优先级枚举 (数值越小优先级越高)"""
    EMERGENCY = 1       # 紧急避险 (大盘红灯+亏损)
    STOP_LOSS = 2       # 止损 (-10%)
    TAKE_PROFIT = 3     # 止盈 (RSI>85)
    TREND_BREAK = 4     # 趋势断裂 (连续2日跌破MA20)

@dataclass
class TechExitSignal:
    """科技股卖出信号"""
    code: str                   # 股票代码
    name: str                   # 股票名称
    exit_type: str              # 卖出类型 ("emergency" / "stop_loss" / "take_profit" / "trend_break" / "rsi_partial")
    priority: SignalPriority    # 信号优先级
    current_price: float        # 当前价格
    stop_loss_price: float      # 止损价
    pnl_pct: float              # 盈亏百分比
    rsi: float                  # 当前 RSI
    ma5: float                  # MA5
    ma20: float                 # MA20
    ma20_break_days: int        # MA20 跌破天数
    shares: int                 # 持仓股数
    is_min_position: bool       # 是否最小仓位 (100股)
    suggested_action: str       # 建议操作
    urgency_color: str          # 紧急程度颜色 ("red" / "orange" / "yellow" / "blue")

class TechExitManager:
    """科技股卖出信号管理器 - 含优先级排序"""
    
    # 止损参数
    HARD_STOP_LOSS = -0.10      # 硬止损 -10%
    PROFIT_THRESHOLD_1 = 0.05   # 盈利阈值1：5%
    PROFIT_THRESHOLD_2 = 0.15   # 盈利阈值2：15%
    RSI_OVERBOUGHT = 85         # RSI 超买阈值
    MA20_BREAK_DAYS = 2         # MA20 跌破天数阈值
    MIN_POSITION_SHARES = 100   # 最小仓位股数
    
    # 优先级颜色映射
    PRIORITY_COLORS = {
        SignalPriority.EMERGENCY: "red",      # 紧急避险 - 红色
        SignalPriority.STOP_LOSS: "orange",   # 止损 - 橙色
        SignalPriority.TAKE_PROFIT: "yellow", # 止盈 - 黄色
        SignalPriority.TREND_BREAK: "blue",   # 趋势断裂 - 蓝色
    }
    
    def check_exit_signals(
        self, 
        holdings: List[Holding],
        market_status: MarketStatus
    ) -> List[TechExitSignal]:
        """
        检查所有持仓的卖出信号
        
        检查顺序（按优先级）：
        1. 紧急避险 (大盘红灯 + 持仓亏损)
        2. 硬止损 (-10%)
        3. RSI 分仓止盈 (RSI>85)
        4. 趋势断裂 (连续2日跌破MA20)
        
        Returns:
            按优先级排序的卖出信号列表
        """
        pass
    
    def _check_emergency_exit(
        self, 
        holding: Holding, 
        market_status: MarketStatus,
        pnl_pct: float
    ) -> Optional[TechExitSignal]:
        """
        检查紧急避险信号
        
        条件：大盘红灯 且 持仓亏损
        优先级：最高 (EMERGENCY)
        """
        if not market_status.is_green and pnl_pct < 0:
            return TechExitSignal(
                exit_type="emergency",
                priority=SignalPriority.EMERGENCY,
                suggested_action="⚠️ 紧急避险：大盘红灯+亏损，建议立即清仓",
                urgency_color="red",
                # ... other fields
            )
        return None
    
    def sort_signals_by_priority(
        self, 
        signals: List[TechExitSignal]
    ) -> List[TechExitSignal]:
        """按优先级排序信号（优先级高的在前）"""
        return sorted(signals, key=lambda s: s.priority)
    
    def calculate_stop_loss_price(
        self, 
        holding: Holding, 
        current_price: float,
        ma5: float
    ) -> float:
        """
        计算当前止损价
        
        规则：
        - 亏损状态：成本价 × (1 + HARD_STOP_LOSS)
        - 盈利 5-15%：成本价
        - 盈利 >15%：MA5
        """
        pass
    
    def _check_rsi_partial_sell(
        self, 
        holding: Holding, 
        rsi: float,
        ma5: float
    ) -> Optional[TechExitSignal]:
        """
        检查 RSI 分仓止盈
        
        规则：
        - 持仓 >= 200股 且 RSI > 85：卖一半
        - 持仓 = 100股 且 RSI > 85：止损紧贴 MA5
        """
        if rsi <= self.RSI_OVERBOUGHT:
            return None
            
        shares = holding.shares
        is_min_position = shares == self.MIN_POSITION_SHARES
        
        if is_min_position:
            return TechExitSignal(
                exit_type="rsi_partial",
                priority=SignalPriority.TAKE_PROFIT,
                is_min_position=True,
                suggested_action=f"⚡ 100股持仓 RSI>{self.RSI_OVERBOUGHT}：止损紧贴 MA5 ({ma5:.2f})",
                urgency_color="yellow",
                # ... other fields
            )
        elif shares >= 200:
            return TechExitSignal(
                exit_type="rsi_partial",
                priority=SignalPriority.TAKE_PROFIT,
                is_min_position=False,
                suggested_action=f"💰 RSI>{self.RSI_OVERBOUGHT}：建议卖出一半 ({shares // 2}股)",
                urgency_color="yellow",
                # ... other fields
            )
        return None
    
    def mark_special_positions(
        self, 
        holdings: List[Holding]
    ) -> List[Dict]:
        """
        标记特殊持仓（100股最小仓位）
        
        Returns:
            带有特殊标记的持仓列表
        """
        result = []
        for h in holdings:
            is_min = h.shares == self.MIN_POSITION_SHARES
            result.append({
                "holding": h,
                "is_min_position": is_min,
                "special_marker": "🔸 严格止盈" if is_min else None,
                "highlight_color": "amber" if is_min else None,
            })
        return result
```

### 6. TechBacktester (科技股回测引擎 - 强制震荡市验证)

```python
@dataclass
class PeriodPerformance:
    """时间段绩效"""
    period_name: str            # 时间段名称
    start_date: str             # 开始日期
    end_date: str               # 结束日期
    total_return: float         # 总收益率
    max_drawdown: float         # 最大回撤
    trade_count: int            # 交易次数
    win_rate: float             # 胜率
    is_bear_market: bool        # 是否熊市/震荡市

@dataclass
class TechBacktestResult:
    """科技股回测结果"""
    total_return: float         # 总收益率
    max_drawdown: float         # 最大回撤
    total_trades: int           # 总交易次数
    win_rate: float             # 胜率
    trades_by_period: Dict[str, int]  # 各时间段交易次数
    period_performances: List[PeriodPerformance]  # 各时间段绩效
    drawdown_warning: bool      # 回撤警告 (>15%)
    market_filter_effective: bool  # 大盘风控是否有效
    bear_market_validated: bool # 震荡市验证是否通过
    bear_market_report: str     # 震荡市独立报告

class TechBacktester:
    """科技股回测引擎 - 强制震荡市验证"""
    
    # 默认测试标的
    DEFAULT_STOCKS = {
        "002600": "长盈精密",    # 消费电子
        "300308": "中际旭创",    # AI/算力
        "002371": "北方华创",    # 半导体
    }
    
    # 默认回测时间段
    DEFAULT_START = "2022-01-01"
    DEFAULT_END = "2024-12-01"
    
    # 强制震荡市验证时间段
    BEAR_MARKET_START = "2022-01-01"
    BEAR_MARKET_END = "2023-12-31"
    
    # 考核指标阈值
    MAX_DRAWDOWN_THRESHOLD = -0.15  # 最大回撤阈值 -15%
    
    def run_backtest(
        self,
        stock_codes: List[str],
        start_date: str,
        end_date: str
    ) -> TechBacktestResult:
        """
        运行回测
        
        注意：无论用户选择什么时间段，都会强制包含 2022-2023 震荡市验证
        
        数据完整性处理：
        - 如果某只股票上市时间晚于 BEAR_MARKET_START，跳过该股票的震荡市验证
        - 输出 Warning 而非 Error
        
        Returns:
            回测结果
        """
        pass
    
    def check_data_completeness(
        self, 
        stock_codes: List[str], 
        start_date: str
    ) -> Dict[str, Dict]:
        """
        检查股票数据完整性
        
        Args:
            stock_codes: 股票代码列表
            start_date: 回测开始日期
        
        Returns:
            {
                "002371": {"has_data": True, "first_date": "2010-03-31", "warning": None},
                "688xxx": {"has_data": False, "first_date": "2023-06-01", "warning": "上市时间晚于回测开始日期"}
            }
        """
        pass
    
    def filter_stocks_by_data_availability(
        self,
        stock_codes: List[str],
        start_date: str
    ) -> Tuple[List[str], List[Dict]]:
        """
        根据数据可用性过滤股票
        
        Returns:
            (可用股票列表, 警告信息列表)
        """
        completeness = self.check_data_completeness(stock_codes, start_date)
        valid_stocks = []
        warnings = []
        
        for code, info in completeness.items():
            if info["has_data"]:
                valid_stocks.append(code)
            else:
                warnings.append({
                    "code": code,
                    "message": f"⚠️ {code} 上市时间 ({info['first_date']}) 晚于回测开始日期 ({start_date})，已跳过震荡市验证"
                })
        
        return valid_stocks, warnings
    
    def validate_date_range(self, start_date: str, end_date: str) -> Tuple[bool, str]:
        """
        验证回测时间段是否包含震荡市
        
        Returns:
            (is_valid, message)
        """
        # 检查是否包含 2022-2023
        if start_date > self.BEAR_MARKET_END or end_date < self.BEAR_MARKET_START:
            return False, f"⚠️ 回测时间段必须包含震荡市 ({self.BEAR_MARKET_START} - {self.BEAR_MARKET_END})"
        return True, "✅ 时间段包含震荡市验证"
    
    def run_bear_market_validation(
        self,
        stock_codes: List[str]
    ) -> PeriodPerformance:
        """
        运行震荡市独立验证 (2022-2023)
        
        Returns:
            震荡市时间段的绩效
        """
        pass
    
    def generate_bear_market_report(
        self, 
        performance: PeriodPerformance
    ) -> str:
        """
        生成震荡市独立绩效报告
        
        Returns:
            格式化的报告字符串
        """
        report = f"""
═══════════════════════════════════════════
        震荡市验证报告 (2022-2023)
═══════════════════════════════════════════
时间段: {performance.start_date} - {performance.end_date}
总收益率: {performance.total_return:.2%}
最大回撤: {performance.max_drawdown:.2%} {'⚠️ 超过阈值!' if performance.max_drawdown < self.MAX_DRAWDOWN_THRESHOLD else '✅ 达标'}
交易次数: {performance.trade_count}
胜率: {performance.win_rate:.1%}
═══════════════════════════════════════════
"""
        return report
    
    def analyze_market_filter_effectiveness(
        self, 
        result: TechBacktestResult
    ) -> str:
        """
        分析大盘风控有效性
        
        检查 2022 年和 2023 年下半年的交易次数是否显著减少
        """
        pass
    
    def get_period_breakdown(
        self, 
        result: TechBacktestResult
    ) -> List[Dict]:
        """
        获取各时间段分解统计
        
        时间段：
        - 2022年全年 (熊市)
        - 2023年上半年 (震荡)
        - 2023年下半年 (震荡)
        - 2024年 (如有)
        """
        pass
```

## Data Models

### 科技股池配置

```python
TECH_STOCK_POOL = {
    "半导体": [
        {"code": "002371", "name": "北方华创"},
        {"code": "688981", "name": "中芯国际"},
        {"code": "002049", "name": "紫光国微"},
        # ...
    ],
    "AI应用": [
        {"code": "300308", "name": "中际旭创"},
        {"code": "002415", "name": "海康威视"},
        # ...
    ],
    "算力": [
        {"code": "000977", "name": "浪潮信息"},
        {"code": "603019", "name": "中科曙光"},
        # ...
    ],
    "消费电子": [
        {"code": "002600", "name": "长盈精密"},
        {"code": "002475", "name": "立讯精密"},
        # ...
    ],
}
```

### 行业指数映射

```python
SECTOR_INDEX_MAPPING = {
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
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system.*

### Property 1: 大盘红灯时无买入信号

*For any* 大盘红灯状态（创业板指 < MA20 或 MACD 死叉），系统不应生成任何买入信号

**Validates: Requirements 1.4**

### Property 2: 行业排名过滤

*For any* 排名第3或第4的行业中的股票，即使技术指标满足条件，系统也不应生成买入信号

**Validates: Requirements 2.5**

### Property 3: 硬性筛选过滤

*For any* 股价 > 80元 或 流通市值不在 50-500亿 或 日均成交额 < 1亿的股票，系统不应生成买入信号

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

### Property 4: 买入信号完整性

*For any* 买入信号，必须同时满足趋势、动量、量能、基本面四个条件

**Validates: Requirements 5.5**

### Property 5: 尾盘信号确认

*For any* 在 14:45 前生成的信号，系统应标记为"待确认"状态；14:45 后生成的信号应标记为"已确认"

**Validates: Requirements 4.1, 4.5**

### Property 6: 止损价计算正确性

*For any* 持仓，止损价应根据盈亏状态正确计算：
- 亏损状态：成本价 × 0.90
- 盈利 5-15%：成本价
- 盈利 >15%：MA5

**Validates: Requirements 6.2, 6.3**

### Property 7: RSI 分仓止盈逻辑

*For any* RSI > 85 的持仓：
- 持仓 >= 200股：建议卖出一半
- 持仓 = 100股：止损紧贴 MA5

**Validates: Requirements 7.1, 7.2**

### Property 8: 趋势断裂检测

*For any* 连续2日收盘价跌破 MA20 的持仓，系统应生成趋势断裂卖出信号

**Validates: Requirements 8.1**

### Property 9: 信号优先级排序

*For any* 卖出信号列表，信号应按优先级排序：紧急避险 > 止损 > 止盈 > 趋势断裂

**Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5**

### Property 10: 特殊持仓标记

*For any* 持仓数量为 100 股的持仓，系统应高亮显示并标记"严格止盈"

**Validates: Requirements 10.1, 10.2**

### Property 11: 震荡市强制验证

*For any* 回测请求，系统必须包含 2022-2023 震荡市时间段的验证

**Validates: Requirements 11.1, 11.8**

## Error Handling

1. **数据获取失败**
   - 指数数据获取失败：显示警告，使用缓存数据或禁止交易
   - 个股数据获取失败：跳过该股票，记录日志

2. **基本面数据缺失**
   - 营收/净利数据缺失：视为不满足基本面条件
   - 解禁数据缺失：显示警告，建议人工确认

3. **计算异常**
   - 数据不足导致指标无法计算：跳过该股票
   - 除零错误：使用默认值或跳过

## Testing Strategy

### 单元测试

1. **MarketFilter 测试**
   - 测试绿灯条件判断
   - 测试红灯条件判断
   - 测试 MACD 状态计算

2. **SectorRanker 测试**
   - 测试行业排名计算
   - 测试可交易行业判断

3. **HardFilter 测试**
   - 测试股价过滤 (>80元)
   - 测试市值过滤 (50-500亿)
   - 测试成交额过滤 (<1亿)
   - 测试组合过滤逻辑

4. **TechSignalGenerator 测试**
   - 测试各条件独立判断
   - 测试组合条件判断
   - 测试信号过滤逻辑
   - 测试尾盘确认逻辑 (14:45)
   - 测试交易窗口状态

5. **TechExitManager 测试**
   - 测试止损价计算
   - 测试 RSI 分仓逻辑
   - 测试趋势断裂检测
   - 测试信号优先级排序
   - 测试紧急避险信号
   - 测试特殊持仓标记 (100股)

6. **TechBacktester 测试**
   - 测试回测结果计算
   - 测试震荡市强制验证
   - 测试时间段验证
   - 测试风控有效性分析

### 属性测试

使用 Hypothesis 库进行属性测试：

1. **Property 1**: 大盘红灯时无买入信号
2. **Property 2**: 行业排名过滤正确性
3. **Property 3**: 硬性筛选过滤正确性
4. **Property 4**: 买入信号完整性
5. **Property 5**: 尾盘信号确认逻辑
6. **Property 6**: 止损价计算正确性
7. **Property 9**: 信号优先级排序正确性
8. **Property 10**: 特殊持仓标记正确性

### 回测验证

1. **时间段**: 2022.01.01 - 2024.12.01 (强制包含震荡市)
2. **标的**: 长盈精密、中际旭创、北方华创
3. **考核指标**:
   - 最大回撤 <= -15%
   - 2022年和2023年下半年交易次数显著减少
4. **震荡市独立报告**: 2022-2023 独立绩效分析
