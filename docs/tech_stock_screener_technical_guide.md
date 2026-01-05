# 科技股筛选引擎技术文档

## 概述

本文档详细介绍科技股池扩充系统的技术架构、API接口、配置说明和维护指南。系统目标是将科技股池从27只扩充至80-100只高质量的主板和中小板科技股。

## 系统架构

### 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        应用层 (Application Layer)                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ 命令行工具  │  │ Streamlit UI│  │ 定时任务调度器          │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        核心层 (Core Layer)                       │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                   股票筛选引擎 (Stock Screener)          │    │
│  │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌─────────┐  │    │
│  │  │行业筛选器 │ │财务筛选器 │ │市场筛选器 │ │综合评分 │  │    │
│  │  └───────────┘ └───────────┘ └───────────┘ └─────────┘  │    │
│  └─────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                   质量控制 (Quality Control)             │    │
│  │  ┌───────────┐ ┌───────────┐ ┌───────────────────────┐  │    │
│  │  │数据验证器 │ │风险评估器 │ │质量监控器             │  │    │
│  │  └───────────┘ └───────────┘ └───────────────────────┘  │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        数据层 (Data Layer)                       │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                   数据源管理器 (DataSourceManager)       │    │
│  │  ┌───────────┐ ┌───────────┐ ┌───────────────────────┐  │    │
│  │  │ AkShare   │ │ 东方财富  │ │ 数据缓存              │  │    │
│  │  └───────────┘ └───────────┘ └───────────────────────┘  │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### 模块依赖关系

```
data_source.py ──────┐
                     │
data_cleaner.py ─────┼──► industry_screener.py ──┐
                     │                            │
config_manager.py ───┘                            │
                                                  │
                     ┌──► financial_screener.py ──┼──► comprehensive_scorer.py
                     │                            │            │
                     └──► market_screener.py ─────┘            │
                                                               ▼
                     ┌──► quality_validator.py ──► pool_updater.py
                     │                                    │
                     └──► risk_controller.py ─────────────┘
                                                          │
                                                          ▼
                                              system_integrator.py
```

## 核心模块详解

### 1. 数据源管理模块 (data_source.py)

#### 类: DataSourceManager

数据源管理器，统一管理多个数据源的数据获取。

**初始化参数:**
- 无需参数，使用默认配置

**主要方法:**

| 方法名 | 参数 | 返回值 | 说明 |
|--------|------|--------|------|
| `get_all_stocks()` | `use_fallback: bool = True` | `DataSourceResult` | 获取全市场股票列表 |
| `get_mainboard_stocks()` | `use_fallback: bool = True` | `DataSourceResult` | 获取主板和中小板股票 |
| `check_health()` | 无 | `Dict[str, Any]` | 检查数据源健康状态 |
| `reset_health_status()` | `source_type: Optional[DataSourceType]` | 无 | 重置健康状态 |
| `get_statistics()` | 无 | `Dict[str, Any]` | 获取使用统计 |

**使用示例:**

```python
from core.stock_screener import get_data_source_manager, DataSourceType

# 获取单例实例
manager = get_data_source_manager()

# 获取主板股票
result = manager.get_mainboard_stocks()
if result.success:
    df = result.data
    print(f"获取到 {len(df)} 只股票")
else:
    print(f"获取失败: {result.error_message}")

# 检查健康状态
health = manager.check_health()
print(f"整体健康: {health['overall_healthy']}")

# 重置特定数据源
manager.reset_health_status(DataSourceType.AKSHARE)
```

#### 数据类: DataSourceResult

| 字段 | 类型 | 说明 |
|------|------|------|
| `success` | `bool` | 是否成功 |
| `data` | `Optional[pd.DataFrame]` | 数据结果 |
| `source` | `Optional[DataSourceType]` | 数据来源 |
| `error_message` | `Optional[str]` | 错误信息 |
| `fetch_time` | `float` | 获取耗时(秒) |
| `retry_count` | `int` | 重试次数 |

### 2. 行业筛选模块 (industry_screener.py)

#### 类: IndustryScreener

基于关键词匹配的科技行业筛选器。

**支持的科技行业 (TechIndustry):**

| 枚举值 | 中文名称 | 关键词示例 |
|--------|----------|------------|
| `SEMICONDUCTOR` | 半导体 | 芯片、集成电路、晶圆、封测 |
| `AI` | 人工智能 | AI、机器学习、深度学习、算法 |
| `COMMUNICATION` | 5G通信 | 5G、基站、光通信、射频 |
| `NEW_ENERGY` | 新能源科技 | 锂电池、储能、光伏、风电 |
| `CONSUMER_ELECTRONICS` | 消费电子 | 智能手机、可穿戴、传感器 |
| `SOFTWARE` | 软件服务 | 软件、云计算、SaaS、数据库 |
| `BIOTECH` | 生物医药科技 | 医疗器械、体外诊断、基因 |
| `SMART_MANUFACTURING` | 智能制造 | 工业自动化、机器人、3D打印 |

**主要方法:**

```python
from core.stock_screener import get_industry_screener, TechIndustry

screener = get_industry_screener()

# 匹配单只股票的行业
industry, confidence, keywords = screener.match_industry(
    name="中芯国际",
    business_desc="集成电路芯片制造",
    industry_name="半导体"
)
print(f"行业: {industry.value}, 置信度: {confidence:.2f}")

# 批量筛选科技股
tech_df, match_results = screener.screen_tech_stocks(
    df=stock_df,
    min_confidence=0.3,
    name_col='name'
)

# 获取行业分布
distribution = screener.get_industry_distribution(match_results)
```

### 3. 财务筛选模块 (financial_screener.py)

#### 类: FinancialScreener

基于财务指标的股票筛选器。

**财务指标 (FinancialIndicators):**

| 指标类别 | 指标名称 | 字段名 | 默认阈值 |
|----------|----------|--------|----------|
| 盈利能力 | 净资产收益率 | `roe` | ≥ 8% |
| 盈利能力 | 总资产收益率 | `roa` | ≥ 4% |
| 盈利能力 | 毛利率 | `gross_margin` | ≥ 20% |
| 盈利能力 | 净利率 | `net_margin` | ≥ 5% |
| 成长性 | 1年营收增长率 | `revenue_growth_1y` | ≥ 5% |
| 成长性 | 3年营收复合增长率 | `revenue_growth_3y` | ≥ 10% |
| 成长性 | 研发投入占比 | `rd_ratio` | ≥ 3% |
| 稳健性 | 资产负债率 | `debt_ratio` | ≤ 60% |
| 稳健性 | 流动比率 | `current_ratio` | ≥ 1.2 |
| 估值 | 市盈率 | `pe_ratio` | ≤ 50 |
| 估值 | 市净率 | `pb_ratio` | ≤ 8 |

**使用示例:**

```python
from core.stock_screener import (
    get_financial_screener,
    FinancialCriteriaConfig,
    FinancialIndicators
)

# 使用自定义配置
config = FinancialCriteriaConfig(
    min_roe=10.0,
    min_gross_margin=25.0,
    max_debt_ratio=50.0
)
screener = FinancialScreener(config=config)

# 批量筛选
passed_df, results = screener.screen_stocks(
    df=stock_df,
    min_score=60.0,
    strict_mode=False
)

# 获取筛选摘要
summary = screener.get_screening_summary(results)
print(f"通过率: {summary['pass_rate']:.1f}%")
```

### 4. 市场筛选模块 (market_screener.py)

#### 类: MarketScreener

基于市场表现的股票筛选器。

**市场指标 (MarketIndicators):**

| 指标类别 | 指标名称 | 字段名 | 默认阈值 |
|----------|----------|--------|----------|
| 市值 | 总市值 | `total_market_cap` | ≥ 50亿 |
| 市值 | 流通市值 | `float_market_cap` | ≥ 30亿 |
| 流动性 | 日均成交额 | `daily_turnover` | ≥ 0.5亿 |
| 流动性 | 换手率 | `turnover_rate` | 0.5% - 15% |
| 稳定性 | 年化波动率 | `volatility_annual` | ≤ 60% |
| 稳定性 | 最大回撤 | `max_drawdown` | ≤ 50% |

**流动性等级 (LiquidityLevel):**

| 等级 | 说明 | 得分范围 |
|------|------|----------|
| EXCELLENT | 优秀 | ≥ 85 |
| GOOD | 良好 | 70-84 |
| ACCEPTABLE | 可接受 | 55-69 |
| POOR | 较差 | 40-54 |
| ILLIQUID | 流动性不足 | < 40 |

### 5. 综合评分模块 (comprehensive_scorer.py)

#### 类: ComprehensiveScorer

多维度综合评分系统。

**评分权重配置 (ScoringWeightsConfig):**

| 维度 | 默认权重 | 说明 |
|------|----------|------|
| `financial_health` | 35% | 财务健康度 |
| `growth_potential` | 25% | 成长潜力 |
| `market_performance` | 20% | 市场表现 |
| `competitive_advantage` | 20% | 竞争优势 |

**综合评级 (OverallRating):**

| 评级 | 分数范围 | 投资建议 |
|------|----------|----------|
| AAA | 90-100 | 顶级，强烈推荐 |
| AA | 80-89 | 优秀，重点关注 |
| A | 70-79 | 良好，可纳入观察池 |
| BBB | 60-69 | 中等偏上，谨慎关注 |
| BB | 50-59 | 中等，需要更多研究 |
| B | 40-49 | 中等偏下，不推荐 |
| C | < 40 | 较差，建议回避 |

**使用示例:**

```python
from core.stock_screener import (
    get_comprehensive_scorer,
    ScoringWeightsConfig
)

# 自定义权重
weights = ScoringWeightsConfig(
    financial_health=0.40,
    growth_potential=0.30,
    market_performance=0.15,
    competitive_advantage=0.15
)

scorer = ComprehensiveScorer(weights=weights)

# 批量评分
result_df, scores = scorer.score_stocks(
    df=stock_df,
    min_score=60.0,
    top_n=100
)

# 获取评分摘要
summary = scorer.get_scoring_summary(scores)
print(f"平均得分: {summary['avg_score']:.1f}")
print(f"评级分布: {summary['rating_distribution']}")
```

### 6. 质量验证模块 (quality_validator.py)

#### 类: DataQualityMonitor

数据质量监控器。

**质量指标:**

| 指标 | 说明 | 权重 |
|------|------|------|
| 完整性 | 必需字段的填充率 | 30% |
| 准确性 | 数据值的合理性 | 25% |
| 一致性 | 数据间的逻辑一致性 | 20% |
| 时效性 | 数据的新鲜程度 | 15% |
| 有效性 | 数据格式的正确性 | 10% |

### 7. 风险控制模块 (risk_controller.py)

#### 类: RiskAssessor

风险评估器。

**风险类型 (RiskType):**

| 类型 | 说明 | 阈值 |
|------|------|------|
| CONCENTRATION | 集中度风险 | 单一行业 ≤ 25% |
| LIQUIDITY | 流动性风险 | 日成交额 ≥ 0.5亿 |
| VOLATILITY | 波动性风险 | 年化波动率 ≤ 60% |
| FINANCIAL | 财务风险 | 负债率 ≤ 60% |

### 8. 股票池更新模块 (pool_updater.py)

#### 类: PoolUpdater

股票池动态更新管理器。

**更新流程:**

```
1. 数据获取 (DATA_FETCH)
       ↓
2. 数据清洗 (DATA_CLEAN)
       ↓
3. 行业筛选 (INDUSTRY_SCREEN)
       ↓
4. 财务筛选 (FINANCIAL_SCREEN)
       ↓
5. 市场筛选 (MARKET_SCREEN)
       ↓
6. 综合评分 (COMPREHENSIVE_SCORE)
       ↓
7. 质量验证 (QUALITY_VALIDATE)
       ↓
8. 风险评估 (RISK_ASSESS)
```

**使用示例:**

```python
from core.stock_screener import get_pool_updater

updater = get_pool_updater()

# 定义进度回调
def on_progress(progress):
    print(f"[{progress.stage.value}] {progress.progress:.0f}% - {progress.message}")

# 执行更新
current_pool = ['600000', '600001', '600002']
result = updater.update_pool(
    current_pool=current_pool,
    progress_callback=on_progress
)

if result.success:
    print(f"新增: {result.added_stocks}")
    print(f"移除: {result.removed_stocks}")
else:
    print(f"更新失败: {result.error}")
```

## 配置说明

### 筛选标准配置

配置文件位置: `config/settings.py`

```python
# 财务筛选标准
FINANCIAL_CRITERIA = {
    'min_roe': 8.0,           # 最小ROE (%)
    'min_roa': 4.0,           # 最小ROA (%)
    'min_gross_margin': 20.0, # 最小毛利率 (%)
    'max_debt_ratio': 60.0,   # 最大负债率 (%)
    'max_pe': 50.0,           # 最大PE
    'max_pb': 8.0,            # 最大PB
}

# 市场筛选标准
MARKET_CRITERIA = {
    'min_market_cap': 50.0,      # 最小市值 (亿)
    'min_daily_turnover': 0.5,   # 最小日成交额 (亿)
    'max_volatility': 60.0,      # 最大波动率 (%)
}

# 评分权重
SCORING_WEIGHTS = {
    'financial_health': 0.35,
    'growth_potential': 0.25,
    'market_performance': 0.20,
    'competitive_advantage': 0.20,
}
```

### 数据源配置

```python
# 数据源优先级
DATA_SOURCE_PRIORITY = ['akshare', 'eastmoney']

# 重试配置
DATA_SOURCE_RETRY = {
    'max_retries': 3,
    'retry_delay': 1.0,
    'timeout': 30.0,
}
```

## 性能优化

### 缓存机制

系统内置多级缓存:

1. **内存缓存**: 热点数据缓存，默认TTL 30分钟
2. **文件缓存**: 历史数据缓存，存储在 `data/cache/`

```python
from core.stock_screener import get_data_cache

cache = get_data_cache()

# 设置缓存
cache.set('stock_list', df, ttl_minutes=30)

# 获取缓存
df = cache.get('stock_list')

# 清除缓存
cache.clear()
```

### 并行处理

批量操作支持并行处理:

```python
from core.stock_screener import ParallelProcessor

processor = ParallelProcessor(max_workers=4)

# 并行处理股票列表
results = processor.process_batch(
    items=stock_codes,
    process_func=process_single_stock
)
```

### 性能监控

```python
from core.stock_screener import get_performance_monitor, timed_operation

monitor = get_performance_monitor()

# 使用装饰器监控
@timed_operation("my_operation")
def my_function():
    pass

# 获取性能报告
report = monitor.get_report()
print(f"平均耗时: {report['avg_duration']:.2f}s")
```

## 错误处理

### 错误类型

| 错误类型 | 说明 | 处理建议 |
|----------|------|----------|
| `DataFetchError` | 数据获取失败 | 检查网络连接，重试 |
| `DataValidationError` | 数据验证失败 | 检查数据格式 |
| `ScreeningError` | 筛选过程错误 | 检查筛选配置 |
| `ConfigurationError` | 配置错误 | 检查配置文件 |

### 错误处理示例

```python
from core.stock_screener import get_data_source_manager

manager = get_data_source_manager()

try:
    result = manager.get_all_stocks()
    if not result.success:
        # 处理获取失败
        logger.error(f"数据获取失败: {result.error_message}")
        # 尝试重置数据源
        manager.reset_health_status()
except Exception as e:
    logger.exception(f"未预期的错误: {e}")
```

## 日志配置

### 日志级别

| 级别 | 说明 |
|------|------|
| DEBUG | 详细调试信息 |
| INFO | 一般运行信息 |
| WARNING | 警告信息 |
| ERROR | 错误信息 |
| CRITICAL | 严重错误 |

### 配置示例

```python
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/screener.log'),
        logging.StreamHandler()
    ]
)

# 设置模块日志级别
logging.getLogger('core.stock_screener').setLevel(logging.DEBUG)
```

## 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 1.0.0 | 2026-01-05 | 初始版本，完整筛选流程 |

## 相关文档

- [API参考文档](stock_screener_api.md)
- [用户操作指南](stock_screener_user_guide.md)
- [故障排除指南](tech_stock_screener_troubleshooting.md)
