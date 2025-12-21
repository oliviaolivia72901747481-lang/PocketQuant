# Design Document: 参数敏感性分析模块

## Overview

参数敏感性分析模块为 MiniQuant-Lite 提供策略鲁棒性评估能力。通过在参数空间内进行网格搜索，生成热力图展示策略在不同参数组合下的表现，帮助用户识别"参数高原"（稳健区域）与"过拟合孤岛"（脆弱区域）。

核心设计原则：
1. **复用现有回测引擎** - 不重复造轮子，直接调用 `BacktestEngine`
2. **渐进式计算** - 支持中断和恢复，避免长时间阻塞
3. **直观可视化** - 热力图 + 自动诊断，让小散户一眼看懂

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit UI Layer                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ 参数范围配置 │  │  热力图展示  │  │   鲁棒性诊断面板    │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Parameter Sensitivity Analyzer                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐  │
│  │  ParameterGrid  │  │  GridSearcher   │  │ Diagnostics │  │
│  │  (参数网格生成)  │  │  (网格搜索执行)  │  │ (鲁棒性诊断) │  │
│  └─────────────────┘  └─────────────────┘  └─────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Existing Infrastructure                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐  │
│  │  BacktestEngine │  │    DataFeed     │  │  Strategies │  │
│  └─────────────────┘  └─────────────────┘  └─────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. ParameterGrid（参数网格生成器）

```python
@dataclass
class ParameterRange:
    """单个参数的范围定义"""
    name: str           # 参数名称（如 'ma_period'）
    display_name: str   # 显示名称（如 'MA 周期'）
    min_value: float    # 最小值
    max_value: float    # 最大值
    step: float         # 步长
    default: float      # 默认值（当前使用的值）

@dataclass
class ParameterGrid:
    """参数网格"""
    param_x: ParameterRange  # 横轴参数
    param_y: ParameterRange  # 纵轴参数
    
    def get_x_values(self) -> List[float]:
        """获取横轴所有取值"""
        pass
    
    def get_y_values(self) -> List[float]:
        """获取纵轴所有取值"""
        pass
    
    def get_total_combinations(self) -> int:
        """获取总组合数"""
        pass
    
    def validate(self) -> Tuple[bool, str]:
        """验证参数范围有效性"""
        pass
```

### 2. GridSearchResult（网格搜索结果）

```python
@dataclass
class CellResult:
    """单个参数组合的回测结果"""
    param_x_value: float
    param_y_value: float
    total_return: float
    win_rate: float
    max_drawdown: float
    trade_count: int
    success: bool
    error_message: str = ""

@dataclass
class GridSearchResult:
    """网格搜索完整结果"""
    grid: ParameterGrid
    results: List[List[CellResult]]  # 二维结果矩阵
    elapsed_time: float
    success_count: int
    failure_count: int
    
    def get_return_matrix(self) -> np.ndarray:
        """获取收益率矩阵（用于热力图）"""
        pass
    
    def get_optimal_cell(self) -> CellResult:
        """获取最优参数组合"""
        pass
```

### 3. GridSearcher（网格搜索执行器）

```python
class GridSearcher:
    """网格搜索执行器"""
    
    def __init__(
        self,
        strategy_class: Type[bt.Strategy],
        backtest_config: BacktestConfig,
        stock_codes: List[str],
        data_feed: DataFeed
    ):
        pass
    
    def run(
        self,
        grid: ParameterGrid,
        base_params: Dict[str, Any],
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> GridSearchResult:
        """
        执行网格搜索
        
        Args:
            grid: 参数网格
            base_params: 基础参数（非搜索参数）
            progress_callback: 进度回调函数 (current, total, message)
        
        Returns:
            GridSearchResult 完整结果
        """
        pass
```

### 4. RobustnessDiagnostics（鲁棒性诊断器）

```python
@dataclass
class DiagnosisResult:
    """诊断结果"""
    score: float                    # 鲁棒性评分 (0-100)
    level: str                      # 等级: 'robust', 'sensitive', 'overfitting'
    message: str                    # 诊断信息
    positive_ratio: float           # 正收益区域占比
    return_std: float               # 收益率标准差
    neighbor_consistency: float     # 最优点与邻近点一致性

class RobustnessDiagnostics:
    """鲁棒性诊断器"""
    
    @staticmethod
    def diagnose(result: GridSearchResult) -> DiagnosisResult:
        """
        对网格搜索结果进行鲁棒性诊断
        
        评分算法：
        1. 正收益区域占比 (40分)：正收益格子数 / 总格子数 × 40
        2. 收益率稳定性 (30分)：1 - min(std/mean, 1) × 30
        3. 邻近一致性 (30分)：最优点周围8格的平均收益 / 最优收益 × 30
        
        Returns:
            DiagnosisResult 诊断结果
        """
        pass
```

### 5. HeatmapRenderer（热力图渲染器）

```python
class HeatmapRenderer:
    """热力图渲染器"""
    
    @staticmethod
    def render(
        result: GridSearchResult,
        metric: str = 'total_return',  # 'total_return', 'win_rate', 'max_drawdown'
        highlight_current: bool = True,
        current_x: Optional[float] = None,
        current_y: Optional[float] = None
    ) -> go.Figure:
        """
        渲染热力图
        
        Args:
            result: 网格搜索结果
            metric: 显示指标
            highlight_current: 是否高亮当前参数
            current_x: 当前横轴参数值
            current_y: 当前纵轴参数值
        
        Returns:
            Plotly Figure 对象
        """
        pass
```

## Data Models

### 策略参数配置映射

```python
STRATEGY_PARAM_CONFIGS = {
    "趋势滤网 MACD 策略": {
        "primary_params": [
            ParameterRange("ma_period", "MA 周期", 40, 80, 5, 60),
            ParameterRange("rsi_upper", "RSI 上限", 70, 90, 5, 80),
        ],
        "secondary_params": [
            ParameterRange("hard_stop_loss", "硬止损", -0.15, -0.05, 0.02, -0.08),
            ParameterRange("trailing_start", "移动止盈启动", 0.10, 0.25, 0.05, 0.15),
        ],
    },
    "RSI 超卖反弹策略": {
        "primary_params": [
            ParameterRange("buy_threshold", "买入阈值", 20, 40, 5, 30),
            ParameterRange("sell_threshold", "卖出阈值", 60, 80, 5, 70),
        ],
        "secondary_params": [
            ParameterRange("stop_loss", "止损比例", 0.03, 0.10, 0.01, 0.05),
            ParameterRange("take_profit", "止盈比例", 0.10, 0.30, 0.05, 0.15),
        ],
    },
}
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: 参数网格验证

*For any* ParameterRange with min_value, max_value, and step, the validation function SHALL return True if and only if min_value < max_value AND step > 0 AND (max_value - min_value) is divisible by step.

**Validates: Requirements 1.3**

### Property 2: 组合数计算正确性

*For any* valid ParameterGrid with param_x and param_y, the total_combinations SHALL equal `len(get_x_values()) * len(get_y_values())`, where `len(get_x_values()) = floor((max - min) / step) + 1`.

**Validates: Requirements 1.4**

### Property 3: 网格搜索完整性

*For any* GridSearchResult, the number of CellResult entries (success + failure) SHALL equal the total_combinations of the input ParameterGrid. No parameter combination shall be skipped.

**Validates: Requirements 2.1, 2.3, 2.4**

### Property 4: 结果矩阵维度一致性

*For any* GridSearchResult, the dimensions of the results matrix SHALL be `[len(y_values), len(x_values)]`, matching the parameter grid dimensions exactly.

**Validates: Requirements 2.4, 3.1**

### Property 5: 鲁棒性评分边界

*For any* DiagnosisResult, the score SHALL be in the range [0, 100], and the level SHALL be 'robust' if score >= 70, 'sensitive' if 40 <= score < 70, and 'overfitting' if score < 40.

**Validates: Requirements 4.1, 4.3, 4.4, 4.5**

### Property 6: 最优参数查找正确性

*For any* GridSearchResult with at least one successful cell, get_optimal_cell() SHALL return the CellResult with the highest total_return among all successful cells.

**Validates: Requirements 4.6**

### Property 7: 热力图颜色映射

*For any* return value in the result matrix, the color mapping SHALL assign green tones to negative returns and red tones to positive returns, with intensity proportional to absolute value.

**Validates: Requirements 3.2**

## Error Handling

| 错误场景 | 处理方式 |
|---------|---------|
| 参数范围无效（min >= max） | 显示错误提示，禁用"开始分析"按钮 |
| 步长为0或负数 | 显示错误提示，禁用"开始分析"按钮 |
| 单个回测失败 | 记录错误，该格子标记为灰色，继续执行 |
| 所有回测都失败 | 显示错误信息，不生成热力图 |
| 数据不足 | 跳过该股票，使用其他股票数据 |
| 内存不足（组合数过多） | 限制最大组合数为200，超出时提示用户减少范围 |

## Testing Strategy

### Unit Tests

1. **ParameterRange 验证测试**
   - 测试有效范围（min < max, step > 0）
   - 测试无效范围的错误处理
   - 测试边界情况（step 刚好整除）

2. **组合数计算测试**
   - 测试各种范围和步长组合
   - 测试边界情况（单点、两点）

3. **鲁棒性评分测试**
   - 测试全正收益矩阵（应得高分）
   - 测试全负收益矩阵（应得低分）
   - 测试孤立高点矩阵（应得低分）
   - 测试均匀分布矩阵（应得中等分）

### Property-Based Tests

使用 Hypothesis 库进行属性测试：

1. **Property 1 测试**: 生成随机 ParameterRange，验证 validate() 结果与手动计算一致
2. **Property 2 测试**: 生成随机 ParameterGrid，验证 total_combinations 计算正确
3. **Property 5 测试**: 生成随机结果矩阵，验证评分在 [0, 100] 范围内且等级映射正确
4. **Property 6 测试**: 生成随机结果矩阵，验证 get_optimal_cell() 返回最大值

### Integration Tests

1. 端到端测试：参数配置 → 网格搜索 → 热力图生成 → 诊断输出
2. 与现有回测引擎的集成测试
3. UI 交互测试（使用 Streamlit 测试框架）

