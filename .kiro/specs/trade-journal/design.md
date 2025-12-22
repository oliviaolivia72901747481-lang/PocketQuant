# Design Document: Trade Journal

## Overview

交易记录功能（Trade Journal）为 MiniQuant-Lite 系统提供实盘交易记录、追踪和分析能力。该功能采用分层架构设计，包括数据层（TradeRecord 数据模型）、业务层（TradeJournal 管理器）和展示层（Streamlit UI）。

核心设计原则：
1. **数据完整性** - 所有交易记录必须包含完整的必填字段
2. **可追溯性** - 支持将交易与系统信号关联，追踪信号执行质量
3. **持久化** - 使用 CSV 文件存储，便于备份和导出
4. **性能** - 支持缓存机制，避免频繁文件读写

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                        │
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │ 6_Trade_Journal │  │ 3_Daily_Signal  │                   │
│  │     (新增)      │  │   (集成入口)    │                   │
│  └────────┬────────┘  └────────┬────────┘                   │
└───────────┼────────────────────┼────────────────────────────┘
            │                    │
┌───────────┼────────────────────┼────────────────────────────┐
│           ▼                    ▼     Business Layer          │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              TradeJournal (core/trade_journal.py)    │    │
│  │  - add_trade()           - get_trades()              │    │
│  │  - calculate_performance() - compare_with_backtest() │    │
│  │  - get_signal_execution_stats()                      │    │
│  └─────────────────────────────────────────────────────┘    │
│                              │                               │
│  ┌───────────────────────────┼───────────────────────────┐  │
│  │                           ▼                           │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │  │
│  │  │ SignalStore │  │PositionTracker│ │BacktestEngine│  │  │
│  │  │  (关联信号) │  │  (关联持仓)  │  │  (对比回测) │   │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘   │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
            │
┌───────────┼─────────────────────────────────────────────────┐
│           ▼              Data Layer                          │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              data/trade_journal.csv                  │    │
│  │  - 持久化存储所有交易记录                            │    │
│  │  - 支持增量追加和全量加载                            │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. TradeAction 枚举

```python
from enum import Enum

class TradeAction(Enum):
    """交易动作"""
    BUY = "买入"
    SELL = "卖出"
```

### 2. TradeRecord 数据类

```python
from dataclasses import dataclass, field
from datetime import date
from typing import Optional
import uuid

@dataclass
class TradeRecord:
    """交易记录"""
    # 必填字段
    code: str                           # 股票代码
    name: str                           # 股票名称
    action: TradeAction                 # 买入/卖出
    price: float                        # 成交价格
    quantity: int                       # 成交数量
    trade_date: date                    # 成交日期
    
    # 可选字段
    signal_id: Optional[str] = None     # 关联的信号ID
    signal_date: Optional[date] = None  # 信号生成日期
    signal_price: Optional[float] = None # 信号建议价格
    strategy: str = ""                  # 使用策略
    reason: str = ""                    # 交易原因
    commission: float = 0.0             # 实际手续费
    note: str = ""                      # 备注
    
    # 自动生成字段
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    
    @property
    def total_amount(self) -> float:
        """成交金额"""
        return self.price * self.quantity
    
    @property
    def slippage(self) -> Optional[float]:
        """滑点（实际价格与信号价格的偏差）"""
        if self.signal_price and self.signal_price > 0:
            return (self.price - self.signal_price) / self.signal_price
        return None
    
    @property
    def execution_delay(self) -> Optional[int]:
        """执行延迟（天数）"""
        if self.signal_date:
            return (self.trade_date - self.signal_date).days
        return None
```

### 3. TradePerformance 数据类

```python
@dataclass
class TradePerformance:
    """交易表现统计"""
    total_trades: int = 0               # 总交易次数
    buy_trades: int = 0                 # 买入次数
    sell_trades: int = 0                # 卖出次数
    closed_trades: int = 0              # 已平仓交易数
    profitable_trades: int = 0          # 盈利交易数
    total_profit: float = 0.0           # 总盈亏金额
    total_commission: float = 0.0       # 总手续费
    net_profit: float = 0.0             # 净利润
    win_rate: float = 0.0               # 胜率
    average_holding_days: float = 0.0   # 平均持仓天数
    average_slippage: float = 0.0       # 平均滑点
    signal_execution_rate: float = 0.0  # 信号执行率
```

### 4. TradeJournal 管理器接口

```python
class TradeJournal:
    """交易日志管理器"""
    
    def __init__(self, file_path: str = "data/trade_journal.csv"):
        """初始化，加载现有记录"""
        pass
    
    # ===== 基础操作 =====
    def add_trade(self, record: TradeRecord) -> Tuple[bool, str]:
        """添加交易记录，返回 (成功, 消息)"""
        pass
    
    def get_trades(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        code: Optional[str] = None,
        action: Optional[TradeAction] = None,
        strategy: Optional[str] = None
    ) -> List[TradeRecord]:
        """查询交易记录"""
        pass
    
    def delete_trade(self, trade_id: str) -> Tuple[bool, str]:
        """删除交易记录"""
        pass
    
    # ===== 统计分析 =====
    def calculate_performance(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> TradePerformance:
        """计算交易表现"""
        pass
    
    def get_signal_execution_stats(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """获取信号执行统计"""
        pass
    
    # ===== 回测对比 =====
    def compare_with_backtest(
        self,
        strategy: str,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """与回测结果对比"""
        pass
    
    # ===== 导出功能 =====
    def export_csv(self, trades: Optional[List[TradeRecord]] = None) -> str:
        """导出为 CSV 字符串"""
        pass
```

## Data Models

### CSV 文件格式

```csv
id,code,name,action,price,quantity,trade_date,signal_id,signal_date,signal_price,strategy,reason,commission,note
a1b2c3d4,600036,招商银行,买入,35.50,1000,2024-12-20,sig_001,2024-12-19,35.20,RSI,RSI超卖反弹,5.00,首次建仓
e5f6g7h8,600036,招商银行,卖出,38.00,1000,2024-12-25,sig_002,2024-12-24,37.80,RSI,RSI超买止盈,5.00,止盈出局
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | 是 | 唯一标识符（自动生成） |
| code | string | 是 | 股票代码 |
| name | string | 是 | 股票名称 |
| action | string | 是 | 买入/卖出 |
| price | float | 是 | 成交价格 |
| quantity | int | 是 | 成交数量 |
| trade_date | date | 是 | 成交日期 |
| signal_id | string | 否 | 关联信号ID |
| signal_date | date | 否 | 信号日期 |
| signal_price | float | 否 | 信号价格 |
| strategy | string | 否 | 策略名称 |
| reason | string | 否 | 交易原因 |
| commission | float | 否 | 手续费 |
| note | string | 否 | 备注 |

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Computed Fields Correctness

*For any* TradeRecord with valid price and quantity, total_amount SHALL equal price × quantity, and if signal_price is provided, slippage SHALL equal (price - signal_price) / signal_price.

**Validates: Requirements 1.3, 1.4**

### Property 2: Round-Trip Persistence

*For any* valid TradeRecord added to TradeJournal, saving to CSV and then loading from CSV SHALL produce an equivalent TradeRecord with all fields preserved.

**Validates: Requirements 2.2, 2.4**

### Property 3: Filter Correctness

*For any* set of TradeRecords and filter criteria (date range, code, action, strategy), all returned records SHALL satisfy all specified filter conditions.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4**

### Property 4: Sort Order Correctness

*For any* query result from TradeJournal, the records SHALL be sorted by trade_date in descending order (newest first).

**Validates: Requirements 3.5**

### Property 5: Performance Calculation Correctness

*For any* set of closed trades (matching buy and sell pairs), win_rate SHALL equal profitable_trades / total_closed_trades, and net_profit SHALL equal total_profit - total_commission.

**Validates: Requirements 4.3, 4.6**

### Property 6: Signal Execution Tracking

*For any* TradeRecord with signal_id, execution_delay SHALL equal (trade_date - signal_date).days, and signal_execution_rate SHALL equal executed_signals / total_signals.

**Validates: Requirements 5.2, 5.4**

### Property 7: Input Validation

*For any* TradeRecord with missing required fields, invalid price (≤ 0), invalid quantity (≤ 0), or future trade_date, add_trade SHALL return (False, error_message) and NOT persist the record.

**Validates: Requirements 8.1, 8.2, 8.3**

### Property 8: Performance Gap Calculation

*For any* comparison between actual trades and backtest results, performance_gap SHALL equal (actual_return - backtest_return).

**Validates: Requirements 7.4**

## Error Handling

### 输入验证错误

| 错误类型 | 触发条件 | 错误消息 |
|---------|---------|---------|
| MissingFieldError | 必填字段为空 | "缺少必填字段: {field_name}" |
| InvalidPriceError | price ≤ 0 | "成交价格必须大于0" |
| InvalidQuantityError | quantity ≤ 0 | "成交数量必须大于0" |
| FutureDateError | trade_date > today | "成交日期不能是未来日期" |
| DuplicateTradeError | 相同ID已存在 | "交易记录已存在: {trade_id}" |

### 文件操作错误

| 错误类型 | 触发条件 | 处理方式 |
|---------|---------|---------|
| FileNotFoundError | CSV文件不存在 | 创建新文件并写入表头 |
| PermissionError | 无写入权限 | 返回错误消息，不中断程序 |
| CSVParseError | CSV格式错误 | 跳过错误行，记录警告日志 |

## Testing Strategy

### 单元测试

1. **TradeRecord 测试**
   - 测试必填字段验证
   - 测试计算属性（total_amount, slippage, execution_delay）
   - 测试边界值（price=0, quantity=0）

2. **TradeJournal 测试**
   - 测试添加/删除/查询操作
   - 测试筛选条件组合
   - 测试统计计算准确性

### 属性测试

使用 Hypothesis 库进行属性测试，每个属性测试至少运行 100 次迭代。

```python
# 测试框架配置
import hypothesis
from hypothesis import given, strategies as st

# 生成器：有效的 TradeRecord
@st.composite
def valid_trade_record(draw):
    return TradeRecord(
        code=draw(st.from_regex(r'[036]\d{5}', fullmatch=True)),
        name=draw(st.text(min_size=2, max_size=10)),
        action=draw(st.sampled_from(TradeAction)),
        price=draw(st.floats(min_value=0.01, max_value=1000.0)),
        quantity=draw(st.integers(min_value=100, max_value=100000).filter(lambda x: x % 100 == 0)),
        trade_date=draw(st.dates(min_value=date(2020, 1, 1), max_value=date.today())),
    )
```

### 集成测试

1. **与 SignalStore 集成**
   - 测试信号关联功能
   - 测试信号执行率计算

2. **与 BacktestEngine 集成**
   - 测试回测对比功能
   - 测试性能差距计算
