# Design Document

## Overview

持仓跟踪与卖出信号功能，为 MiniQuant-Lite 添加持仓管理能力。用户可以记录实际买入的股票，系统针对持仓生成卖出信号，解决"只有买入信号，不知道何时卖出"的问题。

核心设计原则：
- **简单实用**：CSV 文件存储，无需数据库
- **人机协同**：系统生成信号，人工确认执行
- **与现有系统集成**：复用现有的信号生成逻辑

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Streamlit UI                            │
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │ 4_Position.py   │  │ 3_Daily_Signal  │                   │
│  │ (持仓管理页面)   │  │ (集成卖出信号)   │                   │
│  └────────┬────────┘  └────────┬────────┘                   │
└───────────┼────────────────────┼────────────────────────────┘
            │                    │
            ▼                    ▼
┌─────────────────────────────────────────────────────────────┐
│                      Core Layer                              │
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │ PositionTracker │  │ SellSignalGen   │                   │
│  │ (持仓管理)       │  │ (卖出信号生成)   │                   │
│  └────────┬────────┘  └────────┬────────┘                   │
│           │                    │                             │
│           ▼                    ▼                             │
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │ positions.csv   │  │ SignalGenerator │                   │
│  │ (持仓数据存储)   │  │ (复用现有逻辑)   │                   │
│  └─────────────────┘  └─────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. PositionTracker (core/position_tracker.py)

持仓管理核心类，负责持仓的 CRUD 操作和盈亏计算。

```python
@dataclass
class Holding:
    """单个持仓记录"""
    code: str              # 股票代码
    name: str              # 股票名称
    buy_price: float       # 买入价格
    buy_date: date         # 买入日期
    quantity: int          # 持仓数量
    strategy: str          # 使用的策略（RSRS/RSI）
    note: str = ""         # 备注

class PositionTracker:
    """持仓跟踪器"""
    
    def __init__(self, data_path: str):
        """初始化，指定数据存储路径"""
    
    def add_position(self, holding: Holding) -> bool:
        """添加持仓"""
    
    def remove_position(self, code: str) -> bool:
        """删除持仓"""
    
    def update_position(self, code: str, **kwargs) -> bool:
        """更新持仓信息"""
    
    def get_all_positions(self) -> List[Holding]:
        """获取所有持仓"""
    
    def get_position(self, code: str) -> Optional[Holding]:
        """获取单个持仓"""
    
    def calculate_pnl(self, holding: Holding, current_price: float) -> Dict:
        """计算单个持仓的盈亏"""
    
    def get_portfolio_summary(self, prices: Dict[str, float]) -> Dict:
        """获取持仓组合汇总"""
    
    def export_csv(self) -> str:
        """导出持仓为 CSV"""
```

### 2. SellSignalChecker (core/sell_signal_checker.py)

卖出信号检查器，针对持仓股票检查卖出条件。

```python
@dataclass
class SellSignal:
    """卖出信号"""
    code: str              # 股票代码
    name: str              # 股票名称
    holding: Holding       # 持仓信息
    current_price: float   # 当前价格
    pnl_pct: float         # 盈亏百分比
    exit_reason: str       # 卖出原因
    urgency: str           # 紧急程度（high/medium/low）
    indicator_value: float # 指标值（RSRS分数或RSI值）

class SellSignalChecker:
    """卖出信号检查器"""
    
    def __init__(self, data_feed: DataFeed):
        """初始化"""
    
    def check_all_positions(
        self, 
        positions: List[Holding]
    ) -> List[SellSignal]:
        """检查所有持仓的卖出信号"""
    
    def check_single_position(
        self, 
        holding: Holding
    ) -> Optional[SellSignal]:
        """检查单个持仓的卖出信号"""
    
    def _check_rsrs_sell(self, df: DataFrame, holding: Holding) -> Optional[SellSignal]:
        """检查 RSRS 卖出条件"""
    
    def _check_rsi_sell(self, df: DataFrame, holding: Holding) -> Optional[SellSignal]:
        """检查 RSI 卖出条件"""
    
    def _check_stop_loss(self, holding: Holding, current_price: float) -> Optional[SellSignal]:
        """检查止损条件"""
```

## Data Models

### positions.csv 文件格式

```csv
code,name,buy_price,buy_date,quantity,strategy,note
600036,招商银行,35.50,2024-01-15,1000,RSRS,看好银行股
000001,平安银行,12.30,2024-02-01,2000,RSI,超卖反弹
```

### Holding 数据结构

| 字段 | 类型 | 说明 |
|------|------|------|
| code | str | 股票代码（6位） |
| name | str | 股票名称 |
| buy_price | float | 买入价格 |
| buy_date | date | 买入日期 |
| quantity | int | 持仓数量（股） |
| strategy | str | 策略类型（RSRS/RSI） |
| note | str | 备注（可选） |

### SellSignal 数据结构

| 字段 | 类型 | 说明 |
|------|------|------|
| code | str | 股票代码 |
| name | str | 股票名称 |
| holding | Holding | 持仓信息 |
| current_price | float | 当前价格 |
| pnl_pct | float | 盈亏百分比 |
| exit_reason | str | 卖出原因 |
| urgency | str | 紧急程度 |
| indicator_value | float | 指标值 |



## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Position CRUD Operations

*For any* valid Holding data, adding it to the PositionTracker should increase the position count by 1, and the added position should be retrievable by its code. Deleting a position should decrease the count by 1 and make it no longer retrievable.

**Validates: Requirements 1.1, 1.3, 1.4**

### Property 2: Position Persistence Round-Trip

*For any* list of valid Holdings, saving to CSV then loading from CSV should produce an equivalent list of Holdings (same codes, prices, dates, quantities).

**Validates: Requirements 1.5**

### Property 3: PnL Calculation Correctness

*For any* Holding with buy_price > 0 and any current_price > 0, the calculated PnL percentage should equal (current_price - buy_price) / buy_price, and PnL amount should equal (current_price - buy_price) * quantity.

**Validates: Requirements 2.2**

### Property 4: Holding Days Calculation

*For any* Holding with a valid buy_date, the holding days should equal (today - buy_date).days, and should always be >= 0.

**Validates: Requirements 2.3**

### Property 5: Stop Loss Signal Generation

*For any* Holding where (current_price - buy_price) / buy_price <= -0.06, the SellSignalChecker should generate a stop loss signal with urgency="high".

**Validates: Requirements 3.4**

### Property 6: RSRS Sell Signal Generation

*For any* Holding with strategy="RSRS" and stock data where RSRS score < -0.7, the SellSignalChecker should generate a sell signal with exit_reason containing "RSRS".

**Validates: Requirements 3.2**

### Property 7: RSI Sell Signal Generation

*For any* Holding with strategy="RSI" and stock data where RSI > 70, the SellSignalChecker should generate a sell signal with exit_reason containing "RSI".

**Validates: Requirements 3.3**

## Error Handling

| 场景 | 处理方式 |
|------|----------|
| CSV 文件不存在 | 创建空文件，返回空列表 |
| CSV 文件格式错误 | 记录日志，返回空列表，不覆盖原文件 |
| 股票代码无效 | 返回错误提示，不添加持仓 |
| 买入价格 <= 0 | 返回错误提示，不添加持仓 |
| 数量 <= 0 | 返回错误提示，不添加持仓 |
| 重复添加同一股票 | 提示已存在，询问是否更新 |
| 获取当前价格失败 | 显示"--"，不计算盈亏 |
| 股票数据不足 | 跳过该股票的信号检查，记录日志 |

## Testing Strategy

### Unit Tests

- 测试 Holding 数据类的创建和验证
- 测试 PositionTracker 的 CRUD 操作
- 测试 PnL 计算的边界情况（价格为0、负数等）
- 测试 CSV 导入导出的格式正确性

### Property-Based Tests

使用 Hypothesis 库进行属性测试：

- **Property 1-2**: 生成随机 Holding 数据，测试 CRUD 和持久化
- **Property 3-4**: 生成随机价格和日期，测试计算正确性
- **Property 5-7**: 生成满足/不满足条件的数据，测试信号生成

测试配置：
- 每个属性测试运行 100 次迭代
- 使用 pytest + hypothesis
