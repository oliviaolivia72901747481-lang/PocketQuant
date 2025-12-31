# Design Document: Realtime Monitor

## Overview

实时监控模块是一个基于v11.4g科技股策略的股票监控系统，提供实时买卖信号生成、持仓管理、技术指标分析等功能。该模块集成到现有的Streamlit应用中，为用户提供可视化的交易决策支持。

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit UI Layer                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Watchlist   │  │ Positions   │  │ Signals Dashboard   │  │
│  │ Management  │  │ Management  │  │ (Buy/Sell Alerts)   │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  RealtimeMonitor Core                        │
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │ SignalEngine    │  │ PositionTracker │                   │
│  │ - Buy signals   │  │ - PnL calc      │                   │
│  │ - Sell signals  │  │ - Peak tracking │                   │
│  │ - Strength calc │  │ - Holding days  │                   │
│  └─────────────────┘  └─────────────────┘                   │
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │ TechIndicators  │  │ DataRefresher   │                   │
│  │ - MA, RSI       │  │ - Auto refresh  │                   │
│  │ - Volume ratio  │  │ - Market status │                   │
│  │ - Slope calc    │  │ - Error handling│                   │
│  └─────────────────┘  └─────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Data Layer (AkShare)                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Price Data  │  │ Fund Flow   │  │ Technical Data      │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. RealtimeMonitor (主类)

```python
class RealtimeMonitor:
    """实时监控器主类"""
    
    def __init__(self):
        self.watchlist: List[str] = []           # 监控列表
        self.positions: Dict[str, Position] = {} # 持仓字典
        self.signal_engine: SignalEngine         # 信号引擎
        self.data_refresher: DataRefresher       # 数据刷新器
    
    def add_to_watchlist(self, code: str) -> bool:
        """添加股票到监控列表"""
        pass
    
    def remove_from_watchlist(self, code: str) -> bool:
        """从监控列表移除股票"""
        pass
    
    def add_position(self, code: str, cost: float, quantity: int) -> bool:
        """添加持仓"""
        pass
    
    def update_position(self, code: str, cost: float, quantity: int) -> bool:
        """更新持仓"""
        pass
    
    def remove_position(self, code: str) -> bool:
        """移除持仓"""
        pass
    
    def get_all_signals(self) -> Dict[str, List[Signal]]:
        """获取所有信号（买入和卖出）"""
        pass
    
    def refresh_data(self) -> bool:
        """刷新数据"""
        pass
```

### 2. SignalEngine (信号引擎)

```python
class SignalEngine:
    """信号生成引擎"""
    
    # v11.4g 策略参数
    STOP_LOSS_PCT = -0.046        # 止损线 -4.6%
    TAKE_PROFIT_PCT = 0.22        # 止盈线 +22%
    TRAILING_TRIGGER_PCT = 0.09   # 移动止盈触发 +9%
    TRAILING_STOP_PCT = 0.028     # 移动止盈回撤 2.8%
    RSI_MIN = 44                  # RSI下限
    RSI_MAX = 70                  # RSI上限
    RSI_OVERBOUGHT = 80           # RSI超买
    VOLUME_RATIO_MIN = 1.1        # 最小量比
    MAX_HOLDING_DAYS = 15         # 最大持仓天数
    
    def check_buy_conditions(self, stock_data: StockData) -> BuySignal:
        """检查买入条件"""
        pass
    
    def check_sell_conditions(self, position: Position, stock_data: StockData) -> SellSignal:
        """检查卖出条件"""
        pass
    
    def calculate_signal_strength(self, conditions: Dict[str, bool]) -> int:
        """计算信号强度"""
        pass
```

### 3. Position (持仓数据类)

```python
@dataclass
class Position:
    """持仓信息"""
    code: str                    # 股票代码
    name: str                    # 股票名称
    cost_price: float            # 成本价
    quantity: int                # 持仓数量
    buy_date: date               # 买入日期
    peak_price: float            # 历史最高价（用于移动止盈）
    current_price: float = 0.0   # 当前价格
    
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
        """盈亏百分比"""
        return (self.current_price - self.cost_price) / self.cost_price
    
    @property
    def holding_days(self) -> int:
        """持仓天数"""
        return (date.today() - self.buy_date).days
```

### 4. Signal (信号数据类)

```python
@dataclass
class BuySignal:
    """买入信号"""
    code: str
    name: str
    current_price: float
    signal_strength: int          # 0-100
    conditions_met: Dict[str, bool]
    entry_price: float            # 建议入场价
    stop_loss_price: float        # 止损价
    take_profit_price: float      # 止盈价
    trailing_trigger_price: float # 移动止盈触发价
    generated_at: datetime

@dataclass
class SellSignal:
    """卖出信号"""
    code: str
    name: str
    current_price: float
    position: Position
    signal_type: str              # stop_loss, take_profit, trailing_stop, rsi_overbought, trend_reversal, timeout
    urgency: str                  # high, medium, low
    reason: str
    action: str                   # immediate_sell, reduce_position, monitor
    generated_at: datetime
```

### 5. TechIndicators (技术指标计算)

```python
class TechIndicators:
    """技术指标计算器"""
    
    @staticmethod
    def calculate_ma(prices: pd.Series, period: int) -> pd.Series:
        """计算移动平均线"""
        return prices.rolling(window=period).mean()
    
    @staticmethod
    def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        """计算RSI"""
        pass
    
    @staticmethod
    def calculate_volume_ratio(volumes: pd.Series, period: int = 5) -> float:
        """计算量比"""
        pass
    
    @staticmethod
    def calculate_ma_slope(ma_series: pd.Series, days: int = 5) -> float:
        """计算MA斜率"""
        pass
```

## Data Models

### StockData

```python
@dataclass
class StockData:
    """股票数据"""
    code: str
    name: str
    current_price: float
    change_pct: float
    volume: int
    turnover: float
    ma5: float
    ma10: float
    ma20: float
    ma60: float
    rsi: float
    volume_ratio: float
    ma20_slope: float
    main_fund_flow: float         # 今日主力净流入
    fund_flow_5d: float           # 5日累计主力净流入
    updated_at: datetime
```

### MonitorConfig

```python
@dataclass
class MonitorConfig:
    """监控配置"""
    max_watchlist_size: int = 20
    refresh_interval: int = 30    # 秒
    retry_interval: int = 60      # 秒
    trading_hours: List[Tuple[time, time]] = field(default_factory=lambda: [
        (time(9, 30), time(11, 30)),
        (time(13, 0), time(15, 0))
    ])
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Stock Code Validation

*For any* input string, the watchlist add function should accept only valid A-share stock codes (6 digits starting with 0, 3, or 6) and reject all others.

**Validates: Requirements 1.1**

### Property 2: Watchlist Size Limit

*For any* watchlist with 20 stocks, attempting to add another stock should fail and the watchlist size should remain 20.

**Validates: Requirements 1.3**

### Property 3: PnL Calculation Accuracy

*For any* position with cost price C and current price P, the PnL percentage should equal (P - C) / C × 100, with precision to 2 decimal places.

**Validates: Requirements 2.2**

### Property 4: Buy Signal Strength Calculation

*For any* stock data, if N conditions (out of 6) are met:
- N = 6: signal strength = 100
- N = 5: signal strength = 83
- N < 5: no buy signal generated

**Validates: Requirements 3.2, 3.3, 3.4**

### Property 5: Stop Loss Signal Generation

*For any* position where (current_price - cost_price) / cost_price <= -0.046, a stop-loss sell signal with urgency "high" must be generated.

**Validates: Requirements 4.1**

### Property 6: Take Profit Signal Generation

*For any* position where (current_price - cost_price) / cost_price >= 0.22, a take-profit sell signal must be generated.

**Validates: Requirements 4.2**

### Property 7: Trailing Stop Signal Generation

*For any* position where:
1. Peak profit reached >= 9% (peak_price >= cost_price × 1.09)
2. Current price retraced >= 2.8% from peak (current_price <= peak_price × 0.972)

A trailing-stop sell signal must be generated.

**Validates: Requirements 4.3**

### Property 8: RSI Overbought Signal Generation

*For any* position where RSI > 80 AND position is profitable (pnl_pct > 0), an RSI-overbought sell signal must be generated.

**Validates: Requirements 4.4**

### Property 9: Trend Reversal Signal Generation

*For any* position where MA5 < MA20 AND position is at loss (pnl_pct < 0), a trend-reversal sell signal must be generated.

**Validates: Requirements 4.5**

### Property 10: Timeout Signal Generation

*For any* position where holding_days >= 15, a timeout sell signal must be generated.

**Validates: Requirements 4.6**

### Property 11: Market Status Detection

*For any* time T:
- If T is within trading hours (9:30-11:30 or 13:00-15:00), market status should be "open"
- Otherwise, market status should be "closed"

**Validates: Requirements 5.2**

### Property 12: Signal Strength Color Mapping

*For any* signal strength S:
- S >= 80: color = "green"
- 60 <= S < 80: color = "yellow"
- S < 60: color = "red"

**Validates: Requirements 6.2**

### Property 13: Fund Flow Color Mapping

*For any* fund flow value F:
- F > 0: color = "green" (inflow)
- F < 0: color = "red" (outflow)
- F = 0: color = "gray" (neutral)

**Validates: Requirements 7.3, 7.4**

### Property 14: Buy Signal Price Calculations

*For any* buy signal with entry price E:
- stop_loss_price = E × (1 - 0.046) = E × 0.954
- take_profit_price = E × (1 + 0.22) = E × 1.22
- trailing_trigger_price = E × (1 + 0.09) = E × 1.09

**Validates: Requirements 9.1**

## Error Handling

1. **数据获取失败**: 显示错误提示，使用缓存数据，60秒后重试
2. **无效股票代码**: 显示格式错误提示，不添加到监控列表
3. **网络超时**: 显示网络错误，自动重试
4. **计算异常**: 记录日志，显示"数据异常"，跳过该股票

## Testing Strategy

### Unit Tests
- 股票代码验证函数
- PnL计算函数
- 信号强度计算函数
- 各类卖出条件检查函数
- 技术指标计算函数

### Property-Based Tests
使用 `hypothesis` 库进行属性测试：
- Property 1-14 的自动化验证
- 边界条件测试（如止损线精确到-4.6%）
- 随机输入测试

### Integration Tests
- 完整的买入信号生成流程
- 完整的卖出信号生成流程
- 数据刷新和缓存机制
- Streamlit界面交互
