# 科技股筛选引擎故障排除指南

## 概述

本文档提供科技股筛选引擎常见问题的诊断和解决方案。

## 快速诊断

### 系统健康检查

运行以下命令进行系统健康检查:

```python
from core.stock_screener import (
    get_data_source_manager,
    get_quality_monitor,
    get_performance_monitor
)

# 1. 检查数据源健康状态
data_source = get_data_source_manager()
health = data_source.check_health()
print(f"数据源健康状态: {health}")

# 2. 检查性能状态
perf_monitor = get_performance_monitor()
report = perf_monitor.get_report()
print(f"性能报告: {report}")

# 3. 获取统计信息
stats = data_source.get_statistics()
print(f"数据源统计: {stats}")
```

## 常见问题及解决方案

### 1. 数据获取问题

#### 问题: 无法获取股票数据

**症状:**
- `DataSourceResult.success` 返回 `False`
- 错误信息: "所有数据源均获取失败"

**可能原因:**
1. 网络连接问题
2. 数据源服务不可用
3. API限流

**解决方案:**

```python
from core.stock_screener import get_data_source_manager, DataSourceType

manager = get_data_source_manager()

# 方案1: 检查并重置数据源健康状态
health = manager.check_health()
if not health['overall_healthy']:
    manager.reset_health_status()
    print("已重置所有数据源健康状态")

# 方案2: 重置特定数据源
manager.reset_health_status(DataSourceType.AKSHARE)

# 方案3: 检查网络连接
import requests
try:
    response = requests.get("https://www.baidu.com", timeout=5)
    print("网络连接正常")
except:
    print("网络连接异常，请检查网络")
```

#### 问题: 数据获取超时

**症状:**
- 长时间无响应
- 错误信息包含 "timeout"

**解决方案:**

```python
from core.stock_screener import DataSourceConfig, DataSourceType

# 增加超时时间
config = DataSourceConfig(
    source_type=DataSourceType.AKSHARE,
    timeout=60.0,  # 增加到60秒
    max_retries=5,
    retry_delay=2.0
)

manager = get_data_source_manager()
manager.configure_source(DataSourceType.AKSHARE, config)
```

#### 问题: 数据不完整

**症状:**
- 返回的DataFrame缺少某些列
- 数据行数明显偏少

**解决方案:**

```python
from core.stock_screener import get_data_cleaner

cleaner = get_data_cleaner()

# 检查数据质量
quality_report = cleaner.get_quality_summary(df)
print(f"数据完整性: {quality_report}")

# 如果数据不完整，尝试使用备用数据源
result = manager.get_stock_data_with_validation('get_all_stocks')
if result.confidence < 0.8:
    print("数据置信度较低，建议稍后重试")
```

### 2. 筛选问题

#### 问题: 筛选结果为空

**症状:**
- 筛选后DataFrame为空
- 所有股票都被过滤掉

**可能原因:**
1. 筛选标准过于严格
2. 数据缺失导致无法评估
3. 行业关键词匹配失败

**解决方案:**

```python
from core.stock_screener import (
    get_industry_screener,
    get_financial_screener,
    FinancialCriteriaConfig
)

# 方案1: 降低筛选标准
config = FinancialCriteriaConfig(
    min_roe=5.0,        # 降低ROE要求
    min_gross_margin=15.0,  # 降低毛利率要求
    max_debt_ratio=70.0     # 放宽负债率限制
)
screener = get_financial_screener()
screener.config = config

# 方案2: 分步骤调试
# 先检查行业筛选
industry_screener = get_industry_screener()
tech_df, results = industry_screener.screen_tech_stocks(df, min_confidence=0.2)
print(f"行业筛选后: {len(tech_df)} 只")

# 再检查财务筛选
financial_df, _ = screener.screen_stocks(tech_df, min_score=40, strict_mode=False)
print(f"财务筛选后: {len(financial_df)} 只")
```

#### 问题: 行业分类不准确

**症状:**
- 股票被分到错误的行业
- 置信度普遍偏低

**解决方案:**

```python
from core.stock_screener import IndustryScreener, IndustryKeywordConfig, TechIndustry

# 方案1: 添加自定义关键词
screener = get_industry_screener()
screener.add_keyword(TechIndustry.SEMICONDUCTOR, "芯片制造")
screener.add_keyword(TechIndustry.AI, "大模型")

# 方案2: 使用自定义关键词配置
custom_config = IndustryKeywordConfig()
custom_config.semiconductor.extend(["先进封装", "Chiplet"])
custom_config.ai.extend(["生成式AI", "AIGC"])

screener = IndustryScreener(keyword_config=custom_config)
```

#### 问题: 评分异常

**症状:**
- 评分结果不符合预期
- 高质量股票得分偏低

**解决方案:**

```python
from core.stock_screener import ComprehensiveScorer, ScoringWeightsConfig

# 检查评分明细
scorer = get_comprehensive_scorer()
score = scorer.score_stock(row)

print(f"财务得分: {score.financial_score}")
print(f"市场得分: {score.market_score}")
print(f"行业得分: {score.industry_score}")
print(f"定性得分: {score.qualitative_score}")
print(f"评分明细: {score.score_breakdown}")

# 调整权重
weights = ScoringWeightsConfig(
    financial_health=0.30,
    growth_potential=0.30,
    market_performance=0.25,
    competitive_advantage=0.15
)
scorer = ComprehensiveScorer(weights=weights)
```

### 3. 性能问题

#### 问题: 筛选速度慢

**症状:**
- 筛选过程耗时过长
- 超过30分钟未完成

**解决方案:**

```python
from core.stock_screener import (
    get_screening_optimizer,
    get_data_cache,
    ParallelProcessor
)

# 方案1: 启用缓存
cache = get_data_cache()
cache.enable()

# 方案2: 使用并行处理
optimizer = get_screening_optimizer()
optimizer.enable_parallel(max_workers=4)

# 方案3: 优化DataFrame
df = optimizer.optimize_dataframe(df)

# 方案4: 分批处理
batch_size = 500
for i in range(0, len(df), batch_size):
    batch_df = df.iloc[i:i+batch_size]
    # 处理批次
```

#### 问题: 内存占用过高

**症状:**
- 程序运行时内存持续增长
- 出现内存不足错误

**解决方案:**

```python
import gc
from core.stock_screener import get_data_cache

# 方案1: 清理缓存
cache = get_data_cache()
cache.clear()

# 方案2: 强制垃圾回收
gc.collect()

# 方案3: 分批处理并及时释放
def process_in_batches(df, batch_size=500):
    results = []
    for i in range(0, len(df), batch_size):
        batch = df.iloc[i:i+batch_size].copy()
        result = process_batch(batch)
        results.append(result)
        del batch
        gc.collect()
    return pd.concat(results)
```

### 4. 质量验证问题

#### 问题: 数据质量检查失败

**症状:**
- `QualityValidationResult.passed` 返回 `False`
- 质量得分低于阈值

**解决方案:**

```python
from core.stock_screener import get_quality_monitor

monitor = get_quality_monitor()

# 获取详细的质量报告
result = monitor.validate(df)
print(f"质量得分: {result.quality_score}")
print(f"问题列表: {result.issues}")

# 针对性修复
for issue in result.issues:
    if issue.type == 'missing_data':
        # 处理缺失数据
        df[issue.column].fillna(df[issue.column].median(), inplace=True)
    elif issue.type == 'outlier':
        # 处理异常值
        df = df[df[issue.column] < issue.threshold]
```

### 5. 风险评估问题

#### 问题: 风险预警过多

**症状:**
- 大量股票触发风险预警
- 风险评估结果过于保守

**解决方案:**

```python
from core.stock_screener import RiskAssessor

# 调整风险阈值
assessor = RiskAssessor(
    max_concentration=0.30,  # 放宽集中度限制
    max_volatility=70.0,     # 放宽波动率限制
    min_liquidity=0.3        # 降低流动性要求
)

result = assessor.assess(df)
print(f"风险等级: {result.risk_level}")
print(f"预警数量: {len(result.warnings)}")
```

### 6. 系统集成问题

#### 问题: 股票池更新失败

**症状:**
- `PoolUpdateResult.success` 返回 `False`
- 更新历史记录显示失败状态

**解决方案:**

```python
from core.stock_screener import get_pool_updater

updater = get_pool_updater()

# 检查更新历史
history = updater.get_update_history(limit=5)
for record in history:
    print(f"{record.timestamp}: {record.status.value}")
    if record.error_message:
        print(f"  错误: {record.error_message}")

# 使用增量更新减少风险
adds, removes = updater.get_incremental_changes(
    current_pool=current_pool,
    new_candidates=scores,
    max_changes=5  # 限制每次最多变更5只
)
```

## 日志分析

### 日志位置

- 主日志: `logs/miniquant.log`
- 筛选日志: `logs/screener.log`

### 常见日志模式

```
# 数据源切换
WARNING - AkShare获取股票列表失败 (尝试 1/3): Connection timeout
INFO - 成功从 eastmoney 获取 5000 只股票

# 筛选进度
INFO - 从 5000 只股票中筛选出 800 只科技股
INFO - 财务筛选: 从 800 只股票中筛选出 350 只
INFO - 市场表现筛选: 从 350 只股票中筛选出 200 只
INFO - 综合评分: 从 200 只股票中筛选出 100 只

# 质量警告
WARNING - 数据完整性低于阈值: 85% < 90%
WARNING - 发现异常值: PE > 1000
```

### 日志级别调整

```python
import logging

# 开启详细日志
logging.getLogger('core.stock_screener').setLevel(logging.DEBUG)

# 只显示错误
logging.getLogger('core.stock_screener').setLevel(logging.ERROR)
```

## 维护建议

### 日常维护

1. **每日检查**
   - 检查数据源健康状态
   - 查看最近的更新历史
   - 监控性能指标

2. **每周维护**
   - 清理过期缓存
   - 检查日志文件大小
   - 验证筛选结果质量

3. **每月维护**
   - 更新行业关键词库
   - 调整筛选参数
   - 备份配置文件

### 维护脚本

```python
#!/usr/bin/env python
"""日常维护脚本"""

from core.stock_screener import (
    get_data_source_manager,
    get_data_cache,
    get_performance_monitor
)

def daily_maintenance():
    # 1. 检查数据源
    manager = get_data_source_manager()
    health = manager.check_health()
    if not health['overall_healthy']:
        print("警告: 数据源健康状态异常")
        manager.reset_health_status()
    
    # 2. 清理过期缓存
    cache = get_data_cache()
    cache.cleanup_expired()
    
    # 3. 重置性能统计
    monitor = get_performance_monitor()
    monitor.reset()
    
    print("日常维护完成")

if __name__ == '__main__':
    daily_maintenance()
```

## 联系支持

如果以上方案无法解决问题，请:

1. 收集相关日志文件
2. 记录错误信息和复现步骤
3. 查看技术文档: `docs/tech_stock_screener_technical_guide.md`
4. 查看API文档: `docs/stock_screener_api.md`

## 版本信息

- 文档版本: 1.0.0
- 更新日期: 2026-01-05
- 适用系统版本: 1.0.0+
