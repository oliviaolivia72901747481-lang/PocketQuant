"""
Realtime Monitor Data Models

数据模型定义，包括持仓、股票数据、买卖信号等。
Requirements: 2.1, 2.2, 3.1, 4.1
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, Optional

from .config import V114G_STRATEGY_PARAMS


@dataclass
class Position:
    """
    持仓信息
    
    Requirements: 2.1, 2.2
    """
    code: str                           # 股票代码
    name: str                           # 股票名称
    cost_price: float                   # 成本价
    quantity: int                       # 持仓数量
    buy_date: date                      # 买入日期
    peak_price: float = 0.0             # 历史最高价（用于移动止盈）
    current_price: float = 0.0          # 当前价格
    
    def __post_init__(self):
        """初始化后处理"""
        # 如果未设置峰值价格，使用成本价初始化
        if self.peak_price <= 0:
            self.peak_price = self.cost_price
    
    @property
    def market_value(self) -> float:
        """市值"""
        return self.current_price * self.quantity
    
    @property
    def cost_value(self) -> float:
        """成本"""
        return self.cost_price * self.quantity
    
    @property
    def pnl(self) -> float:
        """盈亏金额"""
        return self.market_value - self.cost_value
    
    @property
    def pnl_pct(self) -> float:
        """
        盈亏百分比
        
        Property 3: PnL Calculation Accuracy
        For any position with cost price C and current price P,
        the PnL percentage should equal (P - C) / C
        """
        if self.cost_price <= 0:
            return 0.0
        return (self.current_price - self.cost_price) / self.cost_price
    
    @property
    def holding_days(self) -> int:
        """持仓天数"""
        return (date.today() - self.buy_date).days
    
    @property
    def peak_pnl_pct(self) -> float:
        """峰值盈亏百分比（用于移动止盈计算）"""
        if self.cost_price <= 0:
            return 0.0
        return (self.peak_price - self.cost_price) / self.cost_price
    
    @property
    def drawdown_from_peak(self) -> float:
        """从峰值回撤百分比"""
        if self.peak_price <= 0:
            return 0.0
        return (self.peak_price - self.current_price) / self.peak_price
    
    def update_peak_price(self, new_price: float) -> None:
        """更新峰值价格"""
        if new_price > self.peak_price:
            self.peak_price = new_price
    
    def update_current_price(self, new_price: float) -> None:
        """更新当前价格并同步更新峰值"""
        self.current_price = new_price
        self.update_peak_price(new_price)


@dataclass
class StockData:
    """
    股票数据
    
    Requirement: 3.1
    """
    code: str                           # 股票代码
    name: str                           # 股票名称
    current_price: float                # 当前价格
    change_pct: float                   # 涨跌幅
    volume: int                         # 成交量
    turnover: float                     # 成交额
    ma5: float                          # 5日均线
    ma10: float                         # 10日均线
    ma20: float                         # 20日均线
    ma60: float                         # 60日均线
    rsi: float                          # RSI(14)
    volume_ratio: float                 # 量比
    ma20_slope: float                   # MA20斜率
    main_fund_flow: float = 0.0         # 今日主力净流入
    fund_flow_5d: float = 0.0           # 5日累计主力净流入
    updated_at: datetime = field(default_factory=datetime.now)
    
    def check_buy_conditions(self) -> Dict[str, bool]:
        """
        检查v11.4g买入条件
        
        Returns:
            Dict[str, bool]: 各条件是否满足
        """
        params = V114G_STRATEGY_PARAMS
        
        return {
            'ma5_above_ma20': self.ma5 > self.ma20,                    # MA5 > MA20 (金叉)
            'price_above_ma60': self.current_price > self.ma60,       # Price > MA60 (中期趋势向上)
            'rsi_in_range': params.RSI_MIN <= self.rsi <= params.RSI_MAX,  # RSI在44-70之间
            'volume_ratio_ok': self.volume_ratio > params.VOLUME_RATIO_MIN,  # 量比 > 1.1
            'ma20_slope_positive': self.ma20_slope > 0,               # MA20斜率 > 0
            'price_not_too_high': self.current_price < self.ma5 * (1 + params.MAX_PRICE_ABOVE_MA5_PCT),  # 避免追高
        }
    
    def count_conditions_met(self) -> int:
        """统计满足的买入条件数"""
        conditions = self.check_buy_conditions()
        return sum(conditions.values())


@dataclass
class BuySignal:
    """
    买入信号
    
    Requirements: 3.1, 3.2, 3.3, 3.4
    """
    code: str                           # 股票代码
    name: str                           # 股票名称
    current_price: float                # 当前价格
    signal_strength: int                # 信号强度 0-100
    conditions_met: Dict[str, bool]     # 各条件满足情况
    entry_price: float                  # 建议入场价
    stop_loss_price: float              # 止损价
    take_profit_price: float            # 止盈价
    trailing_trigger_price: float       # 移动止盈触发价
    generated_at: datetime = field(default_factory=datetime.now)
    
    @classmethod
    def from_stock_data(cls, stock_data: StockData, signal_strength: int) -> 'BuySignal':
        """从股票数据创建买入信号"""
        params = V114G_STRATEGY_PARAMS
        entry_price = stock_data.current_price
        
        return cls(
            code=stock_data.code,
            name=stock_data.name,
            current_price=stock_data.current_price,
            signal_strength=signal_strength,
            conditions_met=stock_data.check_buy_conditions(),
            entry_price=entry_price,
            stop_loss_price=round(entry_price * (1 + params.STOP_LOSS_PCT), 2),
            take_profit_price=round(entry_price * (1 + params.TAKE_PROFIT_PCT), 2),
            trailing_trigger_price=round(entry_price * (1 + params.TRAILING_TRIGGER_PCT), 2),
        )


@dataclass
class SellSignal:
    """
    卖出信号
    
    Requirement: 4.1
    """
    code: str                           # 股票代码
    name: str                           # 股票名称
    current_price: float                # 当前价格
    cost_price: float                   # 成本价
    pnl_pct: float                      # 盈亏百分比
    signal_type: str                    # 信号类型
    urgency: str                        # 紧急程度: high, medium, low
    reason: str                         # 卖出原因
    action: str                         # 建议操作: immediate_sell, reduce_position, monitor
    generated_at: datetime = field(default_factory=datetime.now)
    
    # 信号类型常量
    TYPE_STOP_LOSS = 'stop_loss'           # 止损
    TYPE_TAKE_PROFIT = 'take_profit'       # 止盈
    TYPE_TRAILING_STOP = 'trailing_stop'   # 移动止盈
    TYPE_RSI_OVERBOUGHT = 'rsi_overbought' # RSI超买
    TYPE_TREND_REVERSAL = 'trend_reversal' # 趋势反转
    TYPE_TIMEOUT = 'timeout'               # 持仓超时
    
    # 紧急程度常量
    URGENCY_HIGH = 'high'
    URGENCY_MEDIUM = 'medium'
    URGENCY_LOW = 'low'
    
    # 建议操作常量
    ACTION_IMMEDIATE_SELL = 'immediate_sell'
    ACTION_REDUCE_POSITION = 'reduce_position'
    ACTION_MONITOR = 'monitor'
    
    @classmethod
    def create_stop_loss_signal(cls, position: Position) -> 'SellSignal':
        """创建止损信号"""
        return cls(
            code=position.code,
            name=position.name,
            current_price=position.current_price,
            cost_price=position.cost_price,
            pnl_pct=position.pnl_pct,
            signal_type=cls.TYPE_STOP_LOSS,
            urgency=cls.URGENCY_HIGH,
            reason=f'触发止损线 {V114G_STRATEGY_PARAMS.STOP_LOSS_PCT*100:.1f}%',
            action=cls.ACTION_IMMEDIATE_SELL,
        )
    
    @classmethod
    def create_take_profit_signal(cls, position: Position) -> 'SellSignal':
        """创建止盈信号"""
        return cls(
            code=position.code,
            name=position.name,
            current_price=position.current_price,
            cost_price=position.cost_price,
            pnl_pct=position.pnl_pct,
            signal_type=cls.TYPE_TAKE_PROFIT,
            urgency=cls.URGENCY_MEDIUM,
            reason=f'达到止盈目标 +{V114G_STRATEGY_PARAMS.TAKE_PROFIT_PCT*100:.0f}%',
            action=cls.ACTION_IMMEDIATE_SELL,
        )
    
    @classmethod
    def create_trailing_stop_signal(cls, position: Position) -> 'SellSignal':
        """创建移动止盈信号"""
        return cls(
            code=position.code,
            name=position.name,
            current_price=position.current_price,
            cost_price=position.cost_price,
            pnl_pct=position.pnl_pct,
            signal_type=cls.TYPE_TRAILING_STOP,
            urgency=cls.URGENCY_HIGH,
            reason=f'移动止盈触发，从峰值回撤 {position.drawdown_from_peak*100:.1f}%',
            action=cls.ACTION_IMMEDIATE_SELL,
        )
    
    @classmethod
    def create_rsi_overbought_signal(cls, position: Position, rsi: float) -> 'SellSignal':
        """创建RSI超买信号"""
        return cls(
            code=position.code,
            name=position.name,
            current_price=position.current_price,
            cost_price=position.cost_price,
            pnl_pct=position.pnl_pct,
            signal_type=cls.TYPE_RSI_OVERBOUGHT,
            urgency=cls.URGENCY_MEDIUM,
            reason=f'RSI超买 ({rsi:.1f} > {V114G_STRATEGY_PARAMS.RSI_OVERBOUGHT})',
            action=cls.ACTION_REDUCE_POSITION,
        )
    
    @classmethod
    def create_trend_reversal_signal(cls, position: Position) -> 'SellSignal':
        """创建趋势反转信号"""
        return cls(
            code=position.code,
            name=position.name,
            current_price=position.current_price,
            cost_price=position.cost_price,
            pnl_pct=position.pnl_pct,
            signal_type=cls.TYPE_TREND_REVERSAL,
            urgency=cls.URGENCY_MEDIUM,
            reason='MA5下穿MA20且处于亏损状态',
            action=cls.ACTION_IMMEDIATE_SELL,
        )
    
    @classmethod
    def create_timeout_signal(cls, position: Position) -> 'SellSignal':
        """创建持仓超时信号"""
        return cls(
            code=position.code,
            name=position.name,
            current_price=position.current_price,
            cost_price=position.cost_price,
            pnl_pct=position.pnl_pct,
            signal_type=cls.TYPE_TIMEOUT,
            urgency=cls.URGENCY_LOW,
            reason=f'持仓超过 {V114G_STRATEGY_PARAMS.MAX_HOLDING_DAYS} 天',
            action=cls.ACTION_MONITOR,
        )
