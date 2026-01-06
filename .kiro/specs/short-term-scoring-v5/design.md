# 隔夜选股系统 v5.0 设计文档

## Overview

设计"T日选股，T+1执行"的隔夜短线选股系统。

**核心理念**：收盘后运行，使用完整日线数据，输出明日可执行的交易计划。

**使用场景**：
```
每日流程:
15:00 收盘
15:30 运行选股程序
15:35 获得明日交易计划
次日 9:25 根据计划挂单/观察
次日 9:30 执行买入(如果符合条件)
```

**解决的问题**：
| 原问题 | 解决方案 |
|--------|----------|
| 数据延迟 | 使用收盘数据，无延迟问题 |
| 滞后性 | 专注预测明日，而非确认今日 |
| 缺乏分时 | 不需要分时，专注日线形态 |
| 题材僵化 | 智能龙头识别 |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              隔夜选股系统 v5.0 架构                          │
├─────────────────────────────────────────────────────────────┤
│  输入: 收盘后完整日线数据 (15:00后)                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ 大盘环境    │  │ 市场情绪    │  │ 热点题材    │         │
│  │ 分析器      │  │ 分析器      │  │ 管理器      │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         └────────────────┼────────────────┘                 │
│                          ▼                                  │
│  ┌───────────────────────────────────────────────────────┐ │
│  │              明日潜力评分器                             │ │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐      │ │
│  │  │收盘形态 │ │量能分析 │ │均线位置 │ │资金流向 │      │ │
│  │  │评分     │ │评分     │ │评分     │ │评分     │      │ │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘      │ │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐      │ │
│  │  │热点关联 │ │龙头地位 │ │板块强度 │ │技术形态 │      │ │
│  │  │评分     │ │评分     │ │评分     │ │评分     │      │ │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘      │ │
│  └───────────────────────────────────────────────────────┘ │
│                          ▼                                  │
│  ┌───────────────────────────────────────────────────────┐ │
│  │              交易计划生成器                             │ │
│  │  买入价计算 → 仓位计算 → 止损止盈 → 输出计划           │ │
│  └───────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  输出: 明日交易计划 (Markdown格式)                          │
└─────────────────────────────────────────────────────────────┘
```


## Components and Interfaces

### 1. 明日潜力评分器 (TomorrowPotentialScorer)

```python
class TomorrowPotentialScorer:
    """
    明日潜力评分器 - 预测股票明天上涨的概率
    
    8个评分维度，专注于"明日会涨"的预测
    """
    
    def __init__(self, total_capital: float = 70000):
        self.total_capital = total_capital
        self.weights = {
            'closing_pattern': 15,    # 收盘形态
            'volume_analysis': 15,    # 量能分析
            'ma_position': 12,        # 均线位置
            'capital_flow': 15,       # 资金流向
            'hot_topic': 15,          # 热点关联
            'leader_index': 12,       # 龙头地位
            'sector_strength': 8,     # 板块强度
            'technical_pattern': 8,   # 技术形态
        }
    
    def score_closing_pattern(self, open_p, high, low, close, prev_close) -> Tuple[float, Dict]:
        """
        收盘形态评分 (15分)
        
        分析今日K线形态，预测明日走势:
        - 放量阳线收盘: 15分 (明日大概率高开)
        - 缩量阳线收盘: 12分 (明日可能平开)
        - 十字星收盘: 8分 (方向不明)
        - 下影线阳线: 14分 (有支撑，明日看涨)
        - 上影线阴线: 4分 (有压力，明日看跌)
        - 放量阴线收盘: 3分 (明日可能低开)
        """
        pass
    
    def score_volume_analysis(self, volume, ma5_vol, ma10_vol, 
                              change_pct) -> Tuple[float, Dict]:
        """
        量能分析评分 (15分)
        
        分析成交量变化:
        - 温和放量上涨(1.5-3倍): 15分 (健康上涨)
        - 缩量上涨: 10分 (上涨乏力)
        - 放量上涨(>3倍): 8分 (可能见顶)
        - 缩量下跌: 12分 (洗盘，明日可能反弹)
        - 放量下跌: 3分 (出货，明日继续跌)
        """
        pass
    
    def score_ma_position(self, price, ma5, ma10, ma20, ma60) -> Tuple[float, Dict]:
        """
        均线位置评分 (12分)
        
        分析均线排列:
        - 多头排列(价>MA5>MA10>MA20): 12分
        - 均线粘合(三线距离<3%): 10分 (即将突破)
        - 站上MA20: 8分
        - 站上MA60: 6分
        - 空头排列: 2分
        """
        pass
    
    def score_capital_flow(self, main_net_inflow, large_order_ratio,
                           north_flow) -> Tuple[float, Dict]:
        """
        资金流向评分 (15分)
        
        分析今日资金:
        - 主力大幅流入(>5000万): 15分
        - 主力小幅流入(1000-5000万): 12分
        - 资金均衡: 8分
        - 主力小幅流出: 5分
        - 主力大幅流出: 2分
        """
        pass
    
    def score_hot_topic(self, stock_name, sector, concepts) -> Tuple[float, Dict]:
        """
        热点关联评分 (15分)
        
        分析题材热度:
        - 当日最热题材龙头: 15分
        - 当日热点相关股: 12分
        - 持续热点相关: 10分
        - 潜在热点: 6分
        - 无热点关联: 3分
        """
        pass
    
    def score_leader_index(self, stock_code, sector_stocks) -> Tuple[float, Dict]:
        """
        龙头地位评分 (12分)
        
        分析板块内地位:
        - 板块龙头(涨幅第1): 12分
        - 二线龙头(涨幅前3): 10分
        - 板块强势股(涨幅前10): 7分
        - 板块跟风股: 4分
        - 板块最弱: 1分
        """
        pass
    
    def score_sector_strength(self, sector_rank, sector_change) -> Tuple[float, Dict]:
        """
        板块强度评分 (8分)
        
        分析所属板块:
        - 当日涨幅前3板块: 8分
        - 当日涨幅前10板块: 6分
        - 板块涨幅为正: 4分
        - 板块涨幅为负: 2分
        """
        pass
    
    def score_technical_pattern(self, df: pd.DataFrame) -> Tuple[float, Dict]:
        """
        技术形态评分 (8分)
        
        识别经典形态:
        - 突破形态(突破前高): 8分
        - 底部放量: 7分
        - MACD金叉: 6分
        - 均线金叉: 5分
        - 无明显形态: 3分
        - 顶部形态: 1分
        """
        pass
```

### 2. 买入价计算器 (EntryPriceCalculator)

```python
class EntryPriceCalculator:
    """
    买入价计算器 - 计算明日理想买入价格区间
    """
    
    def calculate_entry_prices(self, 
                               today_close: float,
                               today_high: float,
                               today_low: float,
                               score: float,
                               volatility: float) -> Dict:
        """
        计算买入价格区间
        
        Returns:
            {
                'ideal_price': float,      # 理想买入价(低开时买)
                'acceptable_price': float, # 可接受买入价(平开时买)
                'abandon_price': float,    # 放弃买入价(高开超此价不买)
                'reasoning': str           # 计算说明
            }
        
        计算逻辑:
        - 理想买入价 = 收盘价 * (1 - 0.02)  # 低开2%
        - 可接受买入价 = 收盘价 * (1 + 0.01)  # 高开1%以内
        - 放弃买入价 = 收盘价 * (1 + 0.03)  # 高开3%以上不追
        
        根据评分调整:
        - 高分股(>85): 可接受价上调1%
        - 低分股(<75): 可接受价下调1%
        """
        pass
```

### 3. 仓位顾问 (PositionAdvisor)

```python
class PositionAdvisor:
    """
    仓位顾问 - 计算每只股票的买入仓位
    """
    
    def __init__(self, total_capital: float = 70000):
        self.total_capital = total_capital
        self.max_single_position = 0.30  # 单只最大30%
        self.max_total_position = 0.80   # 总仓位最大80%
    
    def calculate_position(self,
                          score: float,
                          stock_price: float,
                          market_env: str,
                          sentiment: str) -> Dict:
        """
        计算建议仓位
        
        Args:
            score: 明日潜力评分 (0-100)
            stock_price: 股票价格
            market_env: 大盘环境 (强势/震荡/弱势)
            sentiment: 市场情绪 (乐观/中性/恐慌)
        
        Returns:
            {
                'position_ratio': float,   # 仓位比例 (0-0.3)
                'position_amount': float,  # 买入金额
                'shares': int,             # 买入股数(100的整数倍)
                'reasoning': str           # 计算说明
            }
        
        计算逻辑:
        基础仓位 = 评分映射
        - 90-100分: 30%
        - 85-90分: 25%
        - 80-85分: 20%
        - 75-80分: 15%
        - 70-75分: 10%
        - <70分: 0% (不建议)
        
        环境调整:
        - 大盘弱势: ×0.6
        - 大盘震荡: ×1.0
        - 大盘强势: ×1.2
        
        情绪调整:
        - 恐慌: ×0.5
        - 中性: ×1.0
        - 乐观: ×1.1
        """
        pass
```


### 4. 止损止盈计算器 (StopLossCalculator & TakeProfitCalculator)

```python
class StopLossCalculator:
    """止损计算器"""
    
    def calculate_stop_loss(self, 
                           entry_price: float,
                           position_amount: float,
                           volatility: float = 0.05) -> Dict:
        """
        计算止损价格
        
        Returns:
            {
                'stop_loss_price': float,  # 止损价
                'stop_loss_ratio': float,  # 止损比例
                'max_loss_amount': float,  # 最大亏损金额
                'reasoning': str
            }
        
        计算逻辑:
        - 默认止损: -5%
        - 高波动股: -7%
        - 低波动股: -4%
        """
        pass


class TakeProfitCalculator:
    """止盈计算器"""
    
    def calculate_take_profit(self,
                             entry_price: float,
                             position_amount: float,
                             score: float) -> Dict:
        """
        计算止盈价格
        
        Returns:
            {
                'first_target': float,     # 第一止盈位 (+5%)
                'second_target': float,    # 第二止盈位 (+10%)
                'first_profit': float,     # 第一目标盈利金额
                'second_profit': float,    # 第二目标盈利金额
                'reasoning': str
            }
        
        计算逻辑:
        - 第一止盈: +5% (卖出一半)
        - 第二止盈: +10% (卖出剩余)
        - 高分股可持有到+15%
        """
        pass
```

### 5. 智能题材匹配器 (SmartTopicMatcher)

```python
class SmartTopicMatcher:
    """
    智能题材匹配器 - 解决题材匹配僵化问题
    """
    
    def __init__(self):
        # 公司主营业务数据库
        self.company_business = {}
        # 历史龙头记录
        self.leader_history = {}
    
    def match_topic_relevance(self, 
                              stock_code: str,
                              stock_name: str,
                              topic_name: str) -> float:
        """
        计算股票与题材的真实关联度
        
        不仅看名字，还看:
        - 公司主营业务描述
        - 公司产品/服务
        - 历史上该股与该题材的表现
        
        Returns:
            关联度 (0-1)
            - 1.0: 主营业务高度相关
            - 0.7: 有相关业务
            - 0.3: 名字相关但业务不相关(蹭热点)
            - 0.0: 完全无关
        """
        pass
    
    def calculate_leader_index(self,
                               stock_code: str,
                               limit_up_time: str,
                               seal_amount: float,
                               market_cap: float,
                               continuous_boards: int) -> float:
        """
        计算龙头指数
        
        Args:
            limit_up_time: 涨停时间 (如 "09:35")
            seal_amount: 封单金额 (万元)
            market_cap: 流通市值 (亿元)
            continuous_boards: 连板天数
        
        Returns:
            龙头指数 (0-100)
        
        计算逻辑:
        - 涨停时间 (30%): 9:30-10:00=30分, 10:00-11:00=20分, 午后=10分
        - 封单比例 (25%): 封单/市值 > 5%=25分, 3-5%=20分, 1-3%=15分
        - 连板天数 (25%): 3板以上=25分, 2板=20分, 首板=15分
        - 市场认可 (20%): 跟风股数量
        """
        pass
    
    def identify_leader_type(self, leader_index: float, 
                             relevance: float) -> str:
        """
        识别龙头类型
        
        Returns:
            "真龙头": 龙头指数>70 且 关联度>0.7
            "二线龙头": 龙头指数50-70 且 关联度>0.5
            "跟风股": 龙头指数30-50
            "蹭热点": 关联度<0.3
        """
        pass
```

### 6. 交易计划生成器 (TradingPlanGenerator)

```python
class TradingPlanGenerator:
    """
    交易计划生成器 - 输出完整的明日交易计划
    """
    
    def generate_plan(self,
                     date: str,
                     market_env: Dict,
                     sentiment: Dict,
                     recommendations: List[Dict]) -> str:
        """
        生成交易计划文档
        
        Returns:
            Markdown格式的交易计划
        """
        pass
```

## Data Models

### 股票推荐结果

```python
@dataclass
class StockRecommendation:
    """股票推荐结果"""
    code: str                    # 股票代码
    name: str                    # 股票名称
    sector: str                  # 所属板块
    today_close: float           # 今日收盘价
    today_change: float          # 今日涨跌幅
    
    # 评分
    total_score: float           # 明日潜力总分 (0-100)
    score_details: Dict          # 各维度评分详情
    
    # 买入计划
    ideal_price: float           # 理想买入价
    acceptable_price: float      # 可接受买入价
    abandon_price: float         # 放弃买入价
    
    # 仓位
    position_ratio: float        # 建议仓位比例
    position_amount: float       # 建议买入金额
    shares: int                  # 建议买入股数
    
    # 止损止盈
    stop_loss_price: float       # 止损价
    first_target: float          # 第一止盈价
    second_target: float         # 第二止盈价
    max_loss: float              # 最大亏损金额
    expected_profit: float       # 预期盈利金额
    
    # 其他
    hot_topics: List[str]        # 相关热点
    leader_type: str             # 龙头类型
    risk_level: str              # 风险等级
    reasoning: str               # 推荐理由
```

### 交易计划

```python
@dataclass
class TradingPlan:
    """明日交易计划"""
    date: str                    # 计划日期
    generated_at: str            # 生成时间
    
    # 市场环境
    market_env: str              # 大盘环境
    market_sentiment: str        # 市场情绪
    hot_topics: List[str]        # 当前热点
    
    # 推荐股票
    recommendations: List[StockRecommendation]
    
    # 操作建议
    total_position: float        # 建议总仓位
    operation_tips: List[str]    # 操作要点
    risk_warnings: List[str]     # 风险提示
```


## 输出示例

### 明日交易计划示例

```markdown
# 📈 明日交易计划 (2026-01-07)

生成时间: 2026-01-06 15:35:00

## 📊 市场环境

| 指标 | 状态 | 说明 |
|------|------|------|
| 大盘环境 | 🟢 震荡偏强 | 上证站稳3200点 |
| 市场情绪 | 🟡 中性 | 涨停58家，跌停12家 |
| 当前热点 | AI眼镜、CES概念、半导体 | CES展会期间 |

## ⭐ 推荐买入 (共3只)

### 1. 联创电子 (002036) - 评分: 92分 ⭐⭐⭐

| 项目 | 数值 | 说明 |
|------|------|------|
| 今日收盘 | 11.76元 | 涨幅 +3.2% |
| 所属板块 | 半导体 | 板块涨幅第2 |
| 龙头类型 | 二线龙头 | 龙头指数68 |

**评分详情:**
- 收盘形态: 14/15 (放量阳线)
- 量能分析: 13/15 (温和放量)
- 均线位置: 11/12 (多头排列)
- 资金流向: 12/15 (主力流入2300万)
- 热点关联: 14/15 (CES+半导体双热点)
- 龙头地位: 10/12 (板块涨幅第3)
- 板块强度: 7/8 (板块涨幅前5)
- 技术形态: 6/8 (突破前高)

**买入计划:**
| 价格类型 | 价格 | 操作 |
|----------|------|------|
| 理想买入价 | 11.52元 | 低开2%时买入 |
| 可接受买入价 | 11.88元 | 高开1%以内可买 |
| 放弃买入价 | 12.11元 | 高开3%以上不追 |

**仓位建议:**
- 建议仓位: 25% = 17,500元
- 买入股数: 1400股 (按理想价)
- 止损价: 10.94元 (-5%)
- 第一止盈: 12.35元 (+5%)
- 第二止盈: 12.94元 (+10%)
- 最大亏损: 875元
- 预期盈利: 875-1750元

**推荐理由:** 
CES展会期间消费电子热点持续，公司主营光学镜头与VR/AR高度相关，
今日放量突破前高，主力资金流入，明日大概率继续上涨。

---

### 2. 三维通信 (002115) - 评分: 88分 ⭐⭐⭐

[类似格式...]

---

### 3. 四维图新 (002405) - 评分: 85分 ⭐⭐

[类似格式...]

---

## 💡 明日操作要点

1. **开盘观察**: 9:25集合竞价观察开盘价，低于"可接受买入价"再下单
2. **分批买入**: 建议分2次买入，先买一半，确认走势后再加仓
3. **严格止损**: 跌破止损价立即卖出，不要犹豫
4. **止盈策略**: 涨5%卖一半，涨10%卖剩余

## ⚠️ 风险提示

1. 本计划基于历史数据分析，不构成投资建议
2. 股市有风险，入市需谨慎
3. 建议总仓位不超过80%，保留现金应对突发情况
4. 如果明日大盘大幅低开(>1%)，建议观望不操作
```

## Correctness Properties

### Property 1: 评分范围有效性
*For any* 股票评分结果，总分应在0-100之间，各维度分数不超过其权重上限
**Validates: Requirements 2.7**

### Property 2: 仓位限制有效性
*For any* 仓位建议，单只股票仓位不超过30%，总仓位不超过80%
**Validates: Requirements 5.4, 5.5**

### Property 3: 买入价格合理性
*For any* 买入价格建议，理想价 < 可接受价 < 放弃价
**Validates: Requirements 4.2, 4.3, 4.4**

### Property 4: 止损止盈合理性
*For any* 止损止盈建议，止损价 < 买入价 < 第一止盈 < 第二止盈
**Validates: Requirements 6.1, 6.4, 6.5**

### Property 5: 股数为100整数倍
*For any* 买入股数建议，应为100的整数倍
**Validates: Requirements 5.6**

## Error Handling

### 数据获取失败
- 收盘数据获取失败时，提示用户稍后重试
- 部分数据缺失时，使用默认值并标注

### 无推荐股票
- 如果没有符合条件的股票，输出"今日无推荐，建议观望"
- 说明原因(大盘弱势/无热点/评分都不达标)

### 资金不足
- 如果推荐股票价格过高，自动调整仓位或跳过
- 提示用户资金限制

## Testing Strategy

### 单元测试
- 各评分维度的计算准确性
- 买入价、仓位、止损止盈的计算正确性
- 边界条件测试

### 回测验证
- 使用历史数据验证选股准确率
- 计算策略胜率和收益率
- 优化评分权重参数


## 新增关键模块设计 (解决A股实战盲点)

### 7. 竞价过滤器 (CallAuctionFilter)

```python
class CallAuctionFilter:
    """
    竞价过滤器 - 解决竞价逻辑缺失问题
    
    核心功能:
    1. 核按钮过滤 - 低开>4%取消买入
    2. 抢筹确认 - 龙头高开爆量允许追入
    3. 策略类型区分 - 低吸型vs突破型
    """
    
    def __init__(self):
        self.nuclear_threshold = -0.04  # 核按钮阈值: -4%
        self.chase_threshold = 0.03     # 抢筹阈值: +3%
        self.volume_ratio_threshold = 5  # 竞价量比阈值
    
    def analyze_auction(self, 
                       stock_code: str,
                       prev_close: float,
                       auction_price: float,
                       auction_volume: float,
                       avg_volume: float,
                       leader_index: float,
                       strategy_type: str) -> Dict:
        """
        分析竞价情况，决定是否执行买入
        
        Args:
            stock_code: 股票代码
            prev_close: 昨日收盘价
            auction_price: 竞价价格(09:25确定)
            auction_volume: 竞价成交量
            avg_volume: 平均成交量(用于计算量比)
            leader_index: 龙头指数(0-100)
            strategy_type: 策略类型 "low_buy"(低吸) / "breakout"(突破)
        
        Returns:
            {
                'action': str,           # "BUY" / "CANCEL" / "WAIT"
                'reason': str,           # 原因说明
                'adjusted_price': float, # 调整后的买入价(如果需要)
                'risk_level': str        # 风险等级
            }
        """
        open_change = (auction_price - prev_close) / prev_close
        volume_ratio = auction_volume / (avg_volume / 240 * 5)  # 竞价5分钟量比
        
        # 1. 核按钮检测 - 低开>4%
        if open_change < self.nuclear_threshold:
            return {
                'action': 'CANCEL',
                'reason': f'⚠️ 核按钮警报! 低开{open_change*100:.1f}%，取消买入',
                'adjusted_price': None,
                'risk_level': 'EXTREME'
            }
        
        # 2. 抢筹确认 - 龙头高开爆量
        if (open_change > self.chase_threshold and 
            volume_ratio > self.volume_ratio_threshold and
            leader_index > 70):
            return {
                'action': 'BUY',
                'reason': f'🔥 抢筹确认! 龙头高开{open_change*100:.1f}%，量比{volume_ratio:.1f}，确认买入',
                'adjusted_price': auction_price * 1.01,  # 允许高1%买入
                'risk_level': 'HIGH'
            }
        
        # 3. 策略类型判断
        if strategy_type == 'low_buy':
            # 低吸型: 严格遵守放弃价
            if open_change > 0.03:
                return {
                    'action': 'CANCEL',
                    'reason': f'低吸策略: 高开{open_change*100:.1f}%超过3%，放弃买入',
                    'adjusted_price': None,
                    'risk_level': 'MEDIUM'
                }
        elif strategy_type == 'breakout':
            # 突破型: 允许放宽，但要求量比
            if open_change > 0.03 and volume_ratio < 3:
                return {
                    'action': 'CANCEL',
                    'reason': f'突破策略: 高开{open_change*100:.1f}%但量比{volume_ratio:.1f}不足，放弃',
                    'adjusted_price': None,
                    'risk_level': 'MEDIUM'
                }
        
        # 4. 正常情况
        return {
            'action': 'BUY',
            'reason': f'竞价正常，开盘价{auction_price:.2f}，可执行买入',
            'adjusted_price': auction_price,
            'risk_level': 'LOW'
        }
    
    def determine_strategy_type(self, 
                                leader_index: float,
                                ma_position: str,
                                pattern: str) -> str:
        """
        确定策略类型
        
        Returns:
            "low_buy": 低吸型 - 适合回调买入
            "breakout": 突破型 - 适合追涨买入
        """
        # 龙头股 + 多头排列 + 突破形态 → 突破型
        if leader_index > 60 and ma_position == '多头排列' and pattern in ['突破前高', '放量阳线']:
            return 'breakout'
        
        # 其他情况 → 低吸型
        return 'low_buy'
```

### 8. 情绪周期预判器 (SentimentCyclePredictor)

```python
class SentimentCyclePredictor:
    """
    情绪周期预判器 - 解决情绪轮动问题
    
    A股情绪周期: 冰点 → 修复 → 升温 → 高潮 → 分歧 → 退潮 → 冰点
    
    核心逻辑:
    - 今日高潮 → 明日大概率分歧
    - 今日冰点 → 明日大概率修复
    """
    
    # 情绪周期定义
    CYCLE_PHASES = ['冰点', '修复', '升温', '高潮', '分歧', '退潮']
    
    def __init__(self):
        self.history = []  # 历史情绪记录
    
    def analyze_today_sentiment(self,
                                limit_up_count: int,
                                limit_down_count: int,
                                broken_board_rate: float,
                                continuous_board_count: int,
                                market_profit_rate: float) -> Dict:
        """
        分析今日情绪
        
        Args:
            limit_up_count: 涨停家数
            limit_down_count: 跌停家数
            broken_board_rate: 炸板率
            continuous_board_count: 连板股数量
            market_profit_rate: 市场赚钱效应(上涨股票比例)
        
        Returns:
            {
                'phase': str,           # 当前周期阶段
                'level': str,           # 情绪等级
                'score': float,         # 情绪分数(0-100)
                'description': str      # 描述
            }
        """
        # 计算情绪分数
        score = 0
        
        # 涨停家数 (0-30分)
        if limit_up_count >= 100:
            score += 30
        elif limit_up_count >= 60:
            score += 20
        elif limit_up_count >= 30:
            score += 10
        
        # 跌停家数 (扣分)
        if limit_down_count >= 50:
            score -= 20
        elif limit_down_count >= 20:
            score -= 10
        
        # 炸板率 (0-20分)
        if broken_board_rate < 0.1:
            score += 20
        elif broken_board_rate < 0.2:
            score += 10
        elif broken_board_rate > 0.4:
            score -= 10
        
        # 连板股 (0-25分)
        if continuous_board_count >= 10:
            score += 25
        elif continuous_board_count >= 5:
            score += 15
        elif continuous_board_count >= 2:
            score += 5
        
        # 赚钱效应 (0-25分)
        if market_profit_rate >= 0.7:
            score += 25
        elif market_profit_rate >= 0.5:
            score += 15
        elif market_profit_rate < 0.3:
            score -= 10
        
        score = max(0, min(100, score))
        
        # 判断周期阶段
        if score >= 85:
            phase = '高潮'
            level = 'EXTREME_GREED'
        elif score >= 70:
            phase = '升温'
            level = 'GREED'
        elif score >= 50:
            phase = '修复'
            level = 'NEUTRAL'
        elif score >= 30:
            phase = '退潮'
            level = 'FEAR'
        else:
            phase = '冰点'
            level = 'EXTREME_FEAR'
        
        return {
            'phase': phase,
            'level': level,
            'score': score,
            'description': self._get_description(phase)
        }
    
    def predict_tomorrow(self, today_sentiment: Dict) -> Dict:
        """
        预判明日情绪
        
        Returns:
            {
                'predicted_phase': str,      # 预判明日阶段
                'position_multiplier': float, # 仓位调整系数
                'strategy_advice': str,       # 策略建议
                'focus_stocks': str           # 重点关注类型
            }
        """
        phase = today_sentiment['phase']
        
        if phase == '高潮':
            return {
                'predicted_phase': '分歧',
                'position_multiplier': 0.5,
                'strategy_advice': '⚠️ 明日大概率分歧，减半仓位，只做核心龙头',
                'focus_stocks': '核心龙头(去弱留强)'
            }
        elif phase == '冰点':
            return {
                'predicted_phase': '修复',
                'position_multiplier': 1.2,
                'strategy_advice': '💡 明日可能修复，可适当加仓试错',
                'focus_stocks': '反包形态、抗跌股'
            }
        elif phase == '升温':
            return {
                'predicted_phase': '高潮或继续升温',
                'position_multiplier': 1.0,
                'strategy_advice': '正常操作，跟随热点',
                'focus_stocks': '热点龙头、补涨股'
            }
        elif phase == '分歧':
            return {
                'predicted_phase': '退潮或修复',
                'position_multiplier': 0.7,
                'strategy_advice': '观望为主，等待方向明确',
                'focus_stocks': '穿越分歧的强势股'
            }
        else:  # 退潮/修复
            return {
                'predicted_phase': '继续调整或企稳',
                'position_multiplier': 0.8,
                'strategy_advice': '轻仓试错，控制风险',
                'focus_stocks': '超跌反弹股'
            }
    
    def _get_description(self, phase: str) -> str:
        descriptions = {
            '冰点': '市场极度恐慌，涨停稀少，跌停遍地',
            '修复': '市场开始企稳，情绪逐步修复',
            '升温': '市场活跃度提升，热点开始发酵',
            '高潮': '市场极度亢奋，涨停潮，连板股众多',
            '分歧': '市场出现分歧，龙头分化，炸板增多',
            '退潮': '市场热度下降，赚钱效应减弱'
        }
        return descriptions.get(phase, '')
```

### 9. 智能止损器 (SmartStopLoss)

```python
class SmartStopLoss:
    """
    智能止损器 - 解决固定止损问题
    
    核心逻辑:
    - 技术止损优先(跌破关键位)
    - 固定比例兜底(防灾难)
    - 根据波动率动态调整
    """
    
    def __init__(self):
        self.default_stop_ratio = 0.05   # 默认止损5%
        self.high_vol_stop_ratio = 0.07  # 高波动止损7%
        self.low_vol_stop_ratio = 0.04   # 低波动止损4%
    
    def calculate_smart_stop(self,
                            entry_price: float,
                            prev_low: float,
                            ma5: float,
                            ma10: float,
                            volatility: float) -> Dict:
        """
        计算智能止损价
        
        Args:
            entry_price: 买入价
            prev_low: 昨日最低价
            ma5: 5日均线
            ma10: 10日均线
            volatility: 波动率(近5日振幅平均)
        
        Returns:
            {
                'stop_price': float,        # 最终止损价
                'stop_type': str,           # 止损类型
                'stop_ratio': float,        # 止损比例
                'technical_stop': float,    # 技术止损价
                'fixed_stop': float,        # 固定止损价
                'reasoning': str            # 说明
            }
        """
        # 1. 计算固定止损价
        if volatility > 0.08:
            fixed_ratio = self.high_vol_stop_ratio
        elif volatility < 0.04:
            fixed_ratio = self.low_vol_stop_ratio
        else:
            fixed_ratio = self.default_stop_ratio
        
        fixed_stop = entry_price * (1 - fixed_ratio)
        
        # 2. 计算技术止损价
        # 取 昨日最低价、5日均线、10日均线 中的最高值作为支撑
        support_levels = [prev_low, ma5, ma10]
        technical_stop = max([s for s in support_levels if s < entry_price], default=fixed_stop)
        
        # 3. 最终止损价 = MAX(技术止损, 固定止损)
        # 确保不会因为技术位太低而承受过大亏损
        final_stop = max(technical_stop, fixed_stop)
        
        # 4. 确定止损类型
        if final_stop == technical_stop and technical_stop > fixed_stop:
            stop_type = '技术止损(跌破支撑)'
        else:
            stop_type = '固定止损(兜底)'
        
        stop_ratio = (entry_price - final_stop) / entry_price
        
        return {
            'stop_price': round(final_stop, 2),
            'stop_type': stop_type,
            'stop_ratio': round(stop_ratio, 4),
            'technical_stop': round(technical_stop, 2),
            'fixed_stop': round(fixed_stop, 2),
            'reasoning': f'波动率{volatility*100:.1f}%，技术支撑{technical_stop:.2f}，固定止损{fixed_stop:.2f}'
        }


class TrailingStop:
    """
    移动止盈器 - 锁定利润
    
    核心逻辑:
    - 涨5%: 止盈线上移到成本价(保本)
    - 涨10%: 止盈线上移到+5%(锁定5%利润)
    - 涨15%: 止盈线上移到+10%(锁定10%利润)
    """
    
    def calculate_trailing_stop(self,
                               entry_price: float,
                               current_price: float,
                               highest_price: float) -> Dict:
        """
        计算移动止盈价
        
        Args:
            entry_price: 买入价
            current_price: 当前价
            highest_price: 持仓期间最高价
        
        Returns:
            {
                'trailing_stop': float,  # 移动止盈价
                'locked_profit': float,  # 锁定利润比例
                'action': str,           # 建议操作
                'reasoning': str
            }
        """
        profit_ratio = (highest_price - entry_price) / entry_price
        
        if profit_ratio >= 0.15:
            # 涨15%以上，止盈线在+10%
            trailing_stop = entry_price * 1.10
            locked_profit = 0.10
            action = '持有，止盈线+10%'
        elif profit_ratio >= 0.10:
            # 涨10%以上，止盈线在+5%
            trailing_stop = entry_price * 1.05
            locked_profit = 0.05
            action = '持有，止盈线+5%'
        elif profit_ratio >= 0.05:
            # 涨5%以上，止盈线在成本价
            trailing_stop = entry_price
            locked_profit = 0
            action = '持有，保本止盈'
        else:
            # 未达5%，使用原止损
            trailing_stop = None
            locked_profit = None
            action = '未触发移动止盈'
        
        return {
            'trailing_stop': round(trailing_stop, 2) if trailing_stop else None,
            'locked_profit': locked_profit,
            'action': action,
            'reasoning': f'最高涨幅{profit_ratio*100:.1f}%，锁定利润{locked_profit*100 if locked_profit else 0:.0f}%'
        }
```

### 10. 早盘修正器 (PreMarketAdjuster)

```python
class PreMarketAdjuster:
    """
    早盘修正器 - 解决隔夜消息真空问题
    
    运行时间: 09:00-09:15
    数据来源: 美股、A50期指、个股公告
    """
    
    def __init__(self):
        self.a50_threshold_mild = -0.01    # A50跌1%: 轻度调整
        self.a50_threshold_severe = -0.02  # A50跌2%: 严重调整
    
    def fetch_overnight_data(self) -> Dict:
        """
        获取隔夜数据
        
        Returns:
            {
                'us_market': {
                    'sp500_change': float,
                    'nasdaq_change': float,
                    'dow_change': float
                },
                'a50_change': float,
                'announcements': List[Dict]  # 个股公告
            }
        """
        # 实际实现需要调用数据接口
        pass
    
    def adjust_trading_plan(self,
                           original_plan: Dict,
                           overnight_data: Dict) -> Dict:
        """
        根据隔夜数据调整交易计划
        
        Args:
            original_plan: 原始交易计划
            overnight_data: 隔夜数据
        
        Returns:
            调整后的交易计划
        """
        adjustments = []
        adjusted_plan = original_plan.copy()
        
        a50_change = overnight_data.get('a50_change', 0)
        
        # 1. A50期指调整
        if a50_change < self.a50_threshold_severe:
            # A50跌超2%: 取消非核心龙头
            adjustments.append(f'⚠️ A50跌{a50_change*100:.1f}%，取消非核心龙头买入')
            adjusted_plan['recommendations'] = [
                r for r in adjusted_plan['recommendations']
                if r.get('leader_type') == '真龙头'
            ]
            # 下调所有买入价2%
            for r in adjusted_plan['recommendations']:
                r['ideal_price'] *= 0.98
                r['acceptable_price'] *= 0.98
                
        elif a50_change < self.a50_threshold_mild:
            # A50跌1-2%: 下调买入价2%
            adjustments.append(f'⚠️ A50跌{a50_change*100:.1f}%，下调所有买入价2%')
            for r in adjusted_plan['recommendations']:
                r['ideal_price'] *= 0.98
                r['acceptable_price'] *= 0.98
        
        # 2. 个股公告检查
        announcements = overnight_data.get('announcements', [])
        for ann in announcements:
            if ann.get('type') == 'negative':
                stock_code = ann.get('code')
                adjustments.append(f'⚠️ {stock_code}有利空公告，取消买入')
                adjusted_plan['recommendations'] = [
                    r for r in adjusted_plan['recommendations']
                    if r.get('code') != stock_code
                ]
        
        # 3. 美股大跌预警
        us_change = overnight_data.get('us_market', {}).get('nasdaq_change', 0)
        if us_change < -0.02:
            adjustments.append(f'⚠️ 纳指跌{us_change*100:.1f}%，建议降低总仓位')
            adjusted_plan['total_position'] *= 0.7
        
        adjusted_plan['adjustments'] = adjustments
        adjusted_plan['adjustment_time'] = '09:15'
        
        return adjusted_plan
    
    def generate_adjustment_report(self, 
                                   original_plan: Dict,
                                   adjusted_plan: Dict) -> str:
        """
        生成早盘修正报告
        """
        report = f"""
# 📋 早盘修正报告 ({adjusted_plan.get('adjustment_time', '09:15')})

## 隔夜市场情况
- 纳斯达克: {adjusted_plan.get('nasdaq_change', 0)*100:.1f}%
- A50期指: {adjusted_plan.get('a50_change', 0)*100:.1f}%

## 调整内容
"""
        for adj in adjusted_plan.get('adjustments', []):
            report += f"- {adj}\n"
        
        if not adjusted_plan.get('adjustments'):
            report += "- 无需调整，按原计划执行\n"
        
        return report
```
