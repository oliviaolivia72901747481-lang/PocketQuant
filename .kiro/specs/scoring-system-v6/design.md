# Design Document: 评分系统 v6.0

## Overview

本设计文档描述隔夜选股系统评分策略的优化方案，将原有8维度100分体系升级为更符合A股短线实战的6维度100分体系。

核心改进点：
1. 强调"题材是第一生产力"，题材风口权重提升至25分
2. 新增"股性活跃度"维度，剔除"死股"
3. 资金强度改为相对值（占比），更准确反映资金意图
4. 量价配合引入换手率和情境判断
5. 趋势与位置结合均线和分位点，识别低位突破和高位风险

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ScorerV6 (主评分器)                        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ TrendPosition│  │ KLinePattern│  │ VolumePrice │         │
│  │   Scorer    │  │   Scorer    │  │   Scorer    │         │
│  │   (20分)    │  │   (15分)    │  │   (15分)    │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │CapitalStrength│ │ ThemeWind  │  │StockActivity│         │
│  │   Scorer    │  │   Scorer    │  │   Scorer    │         │
│  │   (15分)    │  │   (25分)    │  │   (10分)    │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
├─────────────────────────────────────────────────────────────┤
│                    RiskMarker (风险标记器)                    │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. ScorerV6 (主评分器)

```python
class ScorerV6:
    """
    v6.0 评分器 - 6维度100分体系
    """
    
    def __init__(self, weights: Optional[Dict[str, int]] = None):
        """
        初始化评分器
        
        Args:
            weights: 可选的权重配置，默认使用标准权重
        """
        self.weights = weights or {
            'trend_position': 20,      # 趋势与位置
            'kline_pattern': 15,       # K线与形态
            'volume_price': 15,        # 量价配合
            'capital_strength': 15,    # 资金强度
            'theme_wind': 25,          # 题材风口
            'stock_activity': 10,      # 股性活跃度
        }
    
    def score_stock(self, stock_data: Dict, market_data: Dict) -> Tuple[float, Dict]:
        """
        对单只股票进行综合评分
        
        Args:
            stock_data: 股票数据
            market_data: 市场数据（热点、板块等）
        
        Returns:
            (总分, 详情字典包含各维度分数和风险标记)
        """
        pass
    
    def get_score_summary(self, total_score: float, details: Dict) -> str:
        """生成可读的评分摘要"""
        pass
```

### 2. TrendPositionScorer (趋势与位置评分器)

```python
class TrendPositionScorer:
    """
    趋势与位置评分 (20分)
    
    评分逻辑:
    - 低位多头排列: 20分
    - 突破关键均线: 16-18分
    - 均线粘合: 12-14分
    - 高位加速(乖离率>15%): 10分 + 风险标记
    - 空头排列: 0分
    """
    
    def score(self, price: float, ma5: float, ma10: float, 
              ma20: float, ma60: float, 
              price_percentile: float) -> Tuple[float, Dict]:
        """
        计算趋势与位置得分
        
        Args:
            price: 当前价格
            ma5/ma10/ma20/ma60: 各均线值
            price_percentile: 价格在近60日的分位点(0-100)
        
        Returns:
            (得分, 详情)
        """
        pass
    
    def calculate_deviation_rate(self, price: float, ma20: float) -> float:
        """计算乖离率"""
        pass
```

### 3. KLinePatternScorer (K线与形态评分器)

```python
class KLinePatternScorer:
    """
    K线与形态评分 (15分)
    
    评分逻辑:
    - 涨停/反包/突破前高: 15分
    - 下影线阳线: 12分
    - 企稳十字星/多方炮: 10分
    - 普通阳线: 8分
    - 普通阴线: 4分
    - 吊颈线/乌云盖顶: 0分
    """
    
    def score(self, open_p: float, high: float, low: float, 
              close: float, prev_close: float,
              prev_high: float = None) -> Tuple[float, Dict]:
        """
        计算K线形态得分
        
        Args:
            open_p/high/low/close: 今日OHLC
            prev_close: 昨日收盘价
            prev_high: 前期高点（用于判断突破）
        
        Returns:
            (得分, 详情)
        """
        pass
    
    def detect_pattern(self, ...) -> str:
        """识别K线形态"""
        pass
```

### 4. VolumePriceScorer (量价配合评分器)

```python
class VolumePriceScorer:
    """
    量价配合评分 (15分)
    
    评分逻辑:
    - 缩量涨停/温和放量(1.5-2倍): 15分
    - 底部/突破口倍量: 15分
    - 正常放量上涨: 12分
    - 缩量上涨: 10分
    - 高位巨量滞涨: 0分
    - 天量阴线: 0分
    
    换手率调整:
    - 3%-15%: 正常
    - <1%: 扣2分
    - >25%: 扣3分
    """
    
    def score(self, volume: float, ma5_vol: float, 
              change_pct: float, turnover_rate: float,
              is_at_bottom: bool = False,
              is_at_breakout: bool = False) -> Tuple[float, Dict]:
        """
        计算量价配合得分
        
        Args:
            volume: 今日成交量
            ma5_vol: 5日均量
            change_pct: 涨跌幅
            turnover_rate: 换手率
            is_at_bottom: 是否处于底部
            is_at_breakout: 是否处于突破位
        
        Returns:
            (得分, 详情)
        """
        pass
```

### 5. CapitalStrengthScorer (资金强度评分器)

```python
class CapitalStrengthScorer:
    """
    资金强度评分 (15分)
    
    评分逻辑 (基于净流入占成交额比例):
    - 占比>10%: 15分
    - 占比5%-10%: 12分
    - 占比0%-5%: 8分
    - 占比-5%-0%: 5分
    - 占比<-10%: 0分
    """
    
    def score(self, main_net_inflow: float, 
              turnover_amount: float) -> Tuple[float, Dict]:
        """
        计算资金强度得分
        
        Args:
            main_net_inflow: 主力净流入(元)
            turnover_amount: 成交额(元)
        
        Returns:
            (得分, 详情)
        """
        pass
    
    def calculate_inflow_ratio(self, inflow: float, amount: float) -> float:
        """计算净流入占比"""
        pass
```

### 6. ThemeWindScorer (题材风口评分器)

```python
class ThemeWindScorer:
    """
    题材风口评分 (25分) - A股短线第一生产力
    
    评分逻辑:
    - 主线题材+板块效应强: 25分
    - 支线题材+有助攻: 15分
    - 独立个股无板块: 8分
    - 无题材关联: 3分
    
    退潮调整:
    - 题材退潮期: 评分减半 + 风险标记
    """
    
    def score(self, concepts: List[str], 
              hot_topics: List[str],
              sector_limit_up_count: int,
              is_sector_leader: bool) -> Tuple[float, Dict]:
        """
        计算题材风口得分
        
        Args:
            concepts: 股票概念列表
            hot_topics: 当前热点题材
            sector_limit_up_count: 板块涨停家数
            is_sector_leader: 是否板块龙头
        
        Returns:
            (得分, 详情)
        """
        pass
```

### 7. StockActivityScorer (股性活跃度评分器)

```python
class StockActivityScorer:
    """
    股性活跃度评分 (10分) - 剔除死股
    
    评分逻辑:
    - 近20日有涨停: 10分
    - 近期有连板: +2分(额外)
    - 历史波动率高(日均振幅>3%): 8分
    - 近60日最大涨幅<10%: 2分
    - 长期横盘(织布机): 0分
    """
    
    def score(self, df: pd.DataFrame) -> Tuple[float, Dict]:
        """
        计算股性活跃度得分
        
        Args:
            df: 近60日K线数据
        
        Returns:
            (得分, 详情)
        """
        pass
    
    def has_limit_up_in_days(self, df: pd.DataFrame, days: int) -> bool:
        """检查近N日是否有涨停"""
        pass
    
    def calculate_volatility(self, df: pd.DataFrame) -> float:
        """计算历史波动率"""
        pass
```

### 8. RiskMarker (风险标记器)

```python
class RiskMarker:
    """
    风险标记器 - 识别并标记高风险情况
    """
    
    RISK_TYPES = {
        'HIGH_CHASE': '追高风险',
        'DISTRIBUTION': '出货风险',
        'THEME_FADE': '题材退潮风险',
        'LOW_ACTIVITY': '股性差',
    }
    
    def mark_risks(self, score_details: Dict) -> List[str]:
        """
        根据评分详情标记风险
        
        Args:
            score_details: 各维度评分详情
        
        Returns:
            风险标记列表
        """
        pass
```

## Data Models

```python
@dataclass
class ScoreResult:
    """评分结果"""
    total_score: float              # 总分 (0-100)
    trend_position: ScoreDimension  # 趋势与位置
    kline_pattern: ScoreDimension   # K线与形态
    volume_price: ScoreDimension    # 量价配合
    capital_strength: ScoreDimension # 资金强度
    theme_wind: ScoreDimension      # 题材风口
    stock_activity: ScoreDimension  # 股性活跃度
    risks: List[str]                # 风险标记列表
    
@dataclass
class ScoreDimension:
    """单维度评分"""
    score: float        # 得分
    max_score: float    # 满分
    description: str    # 描述
    details: Dict       # 详细信息
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: 趋势位置评分边界

*For any* 股票数据，趋势与位置评分必须在0-20分范围内，且：
- 多头排列+低位 → 得分≥16
- 空头排列 → 得分=0
- 高乖离率(>15%) → 得分≤10且有风险标记

**Validates: Requirements 1.1, 1.4, 1.3**

### Property 2: K线形态评分一致性

*For any* K线数据，形态评分必须在0-15分范围内，且：
- 涨停形态 → 得分=15
- 顶部形态(吊颈线/乌云盖顶) → 得分=0
- 阳线得分 > 阴线得分

**Validates: Requirements 2.1, 2.3, 2.5**

### Property 3: 量价配合评分逻辑

*For any* 量价数据，评分必须在0-15分范围内，且：
- 温和放量上涨(1.5-2倍) → 得分≥12
- 高位巨量滞涨 → 得分=0
- 天量阴线 → 得分=0

**Validates: Requirements 3.1, 3.3, 3.4**

### Property 4: 资金强度评分单调性

*For any* 资金流入占比，评分必须随占比单调递增：
- 占比越高 → 得分越高
- 占比>10% → 得分=15
- 占比<-10% → 得分=0

**Validates: Requirements 4.1, 4.5**

### Property 5: 题材风口评分层级

*For any* 题材数据，评分必须在0-25分范围内，且：
- 主线题材+板块效应 → 得分≥20
- 无题材关联 → 得分≤5
- 题材退潮 → 有风险标记

**Validates: Requirements 5.1, 5.4, 5.5**

### Property 6: 股性活跃度评分

*For any* 历史K线数据，评分必须在0-10分范围内，且：
- 近20日有涨停 → 得分≥8
- 长期横盘 → 得分=0

**Validates: Requirements 6.1, 6.4**

### Property 7: 总分计算正确性

*For any* 股票评分，总分必须等于各维度得分之和，且在0-100范围内。

**Validates: Requirements 7.2**

### Property 8: 风险标记完整性

*For any* 评分结果，当满足风险条件时必须有对应的风险标记：
- 乖离率>15% → 包含"追高风险"
- 天量阴线 → 包含"出货风险"
- 长期无涨停 → 包含"股性差"

**Validates: Requirements 8.1, 8.2, 8.4, 8.5**

## Error Handling

1. **数据缺失处理**
   - 缺少均线数据：使用可用数据计算，缺失维度给予中性分数
   - 缺少资金流向：该维度给予5分（中性）
   - 缺少概念数据：题材风口给予3分（最低）

2. **异常值处理**
   - 价格为0或负数：跳过该股票
   - 成交量为0：量价配合给予0分
   - 换手率异常(>100%)：标记数据异常

3. **计算错误处理**
   - 除零错误：使用默认值或跳过
   - 溢出错误：限制在有效范围内

## Testing Strategy

### 单元测试
- 每个评分器独立测试
- 边界条件测试（满分、零分、中间值）
- 异常输入测试

### 属性测试 (Property-Based Testing)
- 使用 Hypothesis 库
- 每个属性测试运行100次以上
- 测试评分边界、单调性、一致性

### 集成测试
- 与 OvernightStockPicker 集成测试
- 回测验证评分有效性
- 对比新旧评分系统结果

### 测试框架
```python
# 使用 pytest + hypothesis
import pytest
from hypothesis import given, strategies as st

@given(st.floats(min_value=0, max_value=100))
def test_trend_position_score_bounds(price_percentile):
    """Property 1: 趋势位置评分边界测试"""
    # 测试实现
    pass
```
