# 股票筛选引擎 API 文档

## 概述

股票筛选引擎是一个用于科技股池扩充的核心模块，提供从数据获取到综合评分的完整筛选流程。

## 模块结构

```
core/stock_screener/
├── __init__.py              # 模块入口，导出所有公共接口
├── data_source.py           # 数据源管理
├── data_cleaner.py          # 数据清洗
├── config_manager.py        # 配置管理
├── industry_screener.py     # 行业筛选
├── financial_screener.py    # 财务筛选
├── market_screener.py       # 市场筛选
├── comprehensive_scorer.py  # 综合评分
├── quality_validator.py     # 质量验证
├── risk_controller.py       # 风险控制
├── pool_updater.py          # 股票池更新
├── system_integrator.py     # 系统集成
└── performance_optimizer.py # 性能优化
```

## 快速开始

### 基本使用

```python
from core.stock_screener import (
    get_data_source_manager,
    get_data_cleaner,
    get_industry_screener,
    get_financial_screener,
    get_market_screener,
    get_comprehensive_scorer,
)

# 1. 获取数据
data_source = get_data_source_manager()
result = data_source.fetch_stock_list()
df = result.data

# 2. 清洗数据
cleaner = get_data_cleaner()
df = cleaner.clean(df)
df = cleaner.filter_mainboard_stocks(df)
df = cleaner.remove_st_stocks(df)

# 3. 行业筛选
industry_screener = get_industry_screener()
df = industry_screener.screen_tech_stocks(df)

# 4. 财务筛选
financial_screener = get_financial_screener()
df, _ = financial_screener.screen_stocks(df)

# 5. 市场筛选
market_screener = get_market_screener()
df, _ = market_screener.screen_stocks(df)

# 6. 综合评分
scorer = get_comprehensive_scorer()
result_df, scores = scorer.score_stocks(df, min_score=60)
```

## 核心模块

### 1. 数据源管理 (DataSourceManager)

管理多数据源的数据获取。

```python
from core.stock_screener import DataSourceManager, DataSourceType

manager = DataSourceManager()

# 获取股票列表
result = manager.fetch_stock_list()
if result.success:
    df = result.data

# 获取财务数据
result = manager.fetch_financial_data(codes=['600000', '600001'])

# 健康检查
health = manager.health_check()
```

### 2. 数据清洗 (DataCleaner)

清洗和验证数据。

```python
from core.stock_screener import DataCleaner

cleaner = DataCleaner()

# 基础清洗
df = cleaner.clean(df)

# 筛选主板股票
df = cleaner.filter_mainboard_stocks(df)

# 移除ST股票
df = cleaner.remove_st_stocks(df)

# 获取质量摘要
summary = cleaner.get_quality_summary(df)
```

### 3. 行业筛选 (IndustryScreener)

筛选科技行业股票。

```python
from core.stock_screener import IndustryScreener, TechIndustry

screener = IndustryScreener()

# 匹配行业
industry, confidence, keywords = screener.match_industry(
    name="中芯国际",
    business_desc="集成电路芯片制造"
)

# 筛选科技股
df = screener.screen_tech_stocks(df)

# 获取行业分布
distribution = screener.get_industry_distribution(df)
```

支持的科技行业：
- SEMICONDUCTOR (半导体)
- AI (人工智能)
- CLOUD_COMPUTING (云计算)
- NEW_ENERGY (新能源)
- COMMUNICATION_5G (5G通信)
- IOT (物联网)
- CYBERSECURITY (网络安全)
- BIG_DATA (大数据)

### 4. 财务筛选 (FinancialScreener)

基于财务指标筛选股票。

```python
from core.stock_screener import FinancialScreener

screener = FinancialScreener()

# 筛选股票
df, results = screener.screen_stocks(df)

# 评估单只股票
result = screener.evaluate_stock(indicators)
```

财务指标：
- ROE (净资产收益率)
- ROA (总资产收益率)
- 毛利率、净利率
- 营收增长率、利润增长率
- 负债率、流动比率
- PE、PB、PEG

### 5. 市场筛选 (MarketScreener)

基于市场表现筛选股票。

```python
from core.stock_screener import MarketScreener

screener = MarketScreener()

# 筛选股票
df, results = screener.screen_stocks(df)

# 评估单只股票
result = screener.evaluate_stock(indicators)
```

市场指标：
- 总市值、流通市值
- 日成交额、换手率
- 年化波动率、最大回撤

### 6. 综合评分 (ComprehensiveScorer)

多维度综合评分。

```python
from core.stock_screener import ComprehensiveScorer, ScoringWeightsConfig

# 自定义权重
weights = ScoringWeightsConfig(
    financial_health=0.35,
    growth_potential=0.25,
    market_performance=0.20,
    competitive_advantage=0.20
)

scorer = ComprehensiveScorer(weights=weights)

# 批量评分
df, scores = scorer.score_stocks(df, min_score=60, top_n=100)

# 获取评分摘要
summary = scorer.get_scoring_summary(scores)
```

评级标准：
- AAA: 90-100分
- AA: 80-89分
- A: 70-79分
- BBB: 60-69分
- BB: 50-59分
- B: 40-49分
- C: <40分

### 7. 质量验证 (DataQualityMonitor)

验证数据质量。

```python
from core.stock_screener import DataQualityMonitor

monitor = DataQualityMonitor(min_quality_score=70)

# 验证数据
result = monitor.validate(df)

# 生成报告
report = monitor.generate_quality_report(result)
```

质量指标：
- 完整性 (Completeness)
- 准确性 (Accuracy)
- 一致性 (Consistency)
- 时效性 (Timeliness)
- 有效性 (Validity)

### 8. 风险控制 (RiskAssessor)

评估股票池风险。

```python
from core.stock_screener import RiskAssessor, RiskAlertManager

assessor = RiskAssessor()

# 评估风险
result = assessor.assess(df)

# 处理预警
alert_manager = RiskAlertManager()
alerts = alert_manager.process_assessment(result)
```

风险类型：
- 集中度风险 (Concentration)
- 流动性风险 (Liquidity)
- 波动性风险 (Volatility)
- 财务风险 (Financial)
- 市场风险 (Market)

### 9. 股票池更新 (PoolUpdater)

管理股票池更新。

```python
from core.stock_screener import PoolUpdater, CandidateScreener

# 候选股票筛选
screener = CandidateScreener(
    min_score=60,
    target_count=100,
    max_single_industry=0.25
)
df, scores, summary = screener.screen_candidates()

# 更新股票池
updater = PoolUpdater()
result = updater.update_pool(current_pool=['600000', '600001'])

# 获取增量变更
adds, removes = updater.get_incremental_changes(
    current_pool, scores, max_changes=10
)
```

### 10. 系统集成 (SystemIntegrator)

集成到现有系统。

```python
from core.stock_screener import SystemIntegrator

integrator = SystemIntegrator()

# 集成筛选结果
result = integrator.integrate_screening_results(scores)

# 验证集成
passed, issues = integrator.validate_integration()

# 获取集成状态
status = integrator.get_integration_status()
```

### 11. 性能优化 (ScreeningOptimizer)

优化筛选性能。

```python
from core.stock_screener import ScreeningOptimizer, timed_operation

optimizer = ScreeningOptimizer()

# 优化DataFrame
df = optimizer.optimize_dataframe(df)

# 带缓存的操作
result = optimizer.cached_operation(
    "fetch_data",
    lambda: fetch_data(),
    cache_key="stock_list",
    ttl_minutes=30
)

# 获取性能报告
report = optimizer.get_performance_report()

# 使用计时装饰器
@timed_operation("my_operation")
def my_function():
    pass
```

## 配置管理

### 筛选配置

```python
from core.stock_screener import ScreenerConfigManager, ScreenerConfig

config_manager = ScreenerConfigManager()

# 获取默认配置
config = config_manager.get_config()

# 更新配置
config_manager.update_config(
    financial_criteria={'min_roe': 10},
    market_criteria={'min_market_cap': 100}
)
```

### 评分权重

```python
from core.stock_screener import ScoringWeightsConfig

weights = ScoringWeightsConfig(
    financial_health=0.35,      # 财务健康度
    growth_potential=0.25,      # 成长潜力
    market_performance=0.20,    # 市场表现
    competitive_advantage=0.20  # 竞争优势
)

# 验证权重
assert weights.validate()  # 权重总和必须为1
```

## 错误处理

所有模块都返回结构化的结果对象，包含成功状态和错误信息：

```python
result = data_source.fetch_stock_list()
if not result.success:
    print(f"错误: {result.error_message}")
```

## 日志

模块使用Python标准logging：

```python
import logging
logging.basicConfig(level=logging.INFO)
```

## 性能建议

1. 使用单例模式获取实例（`get_xxx()`函数）
2. 启用缓存减少重复计算
3. 使用并行处理加速批量操作
4. 定期清理过期缓存

## 版本历史

- v1.0.0: 初始版本，完整筛选流程
