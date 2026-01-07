# Checkpoint 6: 计算器测试验证报告

## 验证日期
2026-01-06

## 验证范围
验证隔夜选股系统 v5.0 中所有计算器模块的核心功能。

## 验证的模块

### 1. EntryPriceCalculator (买入价计算器)
- ✅ 计算理想买入价、可接受买入价、放弃买入价
- ✅ 根据评分调整价格区间
- ✅ 根据波动率调整价格区间
- ✅ 确保价格顺序: ideal < acceptable < abandon

### 2. PositionAdvisor (仓位顾问)
- ✅ 基于评分计算基础仓位
- ✅ 根据大盘环境调整仓位
- ✅ 根据市场情绪调整仓位
- ✅ 单只股票仓位限制 ≤ 30%
- ✅ 总仓位限制 ≤ 80%
- ✅ 股数为100的整数倍
- ✅ 评分低于70分不建议买入

### 3. StopLossCalculator (止损计算器)
- ✅ 默认止损比例 5%
- ✅ 高波动止损比例 7%
- ✅ 低波动止损比例 4%
- ✅ 计算最大亏损金额

### 4. TakeProfitCalculator (止盈计算器)
- ✅ 第一止盈位 +5%
- ✅ 第二止盈位 +10%
- ✅ 高分股止盈位 +15%
- ✅ 计算预期盈利金额

### 5. SmartStopLoss (智能止损器)
- ✅ 止损 = MAX(买入价×0.95, 昨日最低价, 5日均线)
- ✅ 技术止损优先，固定比例兜底
- ✅ 根据波动率动态调整

### 6. TrailingStop (移动止盈器)
- ✅ 涨5%: 止盈线上移到成本价
- ✅ 涨10%: 止盈线上移到+5%
- ✅ 涨15%: 止盈线上移到+10%
- ✅ 确保"绝不让盈利变亏损"

## 验证的属性 (Properties)

| Property | 描述 | 状态 |
|----------|------|------|
| Property 2 | 仓位限制有效性 (single ≤ 30%, total ≤ 80%) | ✅ PASS |
| Property 3 | 买入价格合理性 (ideal < acceptable < abandon) | ✅ PASS |
| Property 4 | 止损止盈合理性 (stop_loss < entry < first < second) | ✅ PASS |
| Property 5 | 股数为100整数倍 | ✅ PASS |
| Property 10 | 智能止损MAX逻辑 | ✅ PASS |
| Property 11 | 移动止盈阶梯逻辑 | ✅ PASS |

## 数据模型验证

### StockRecommendation
- ✅ 股数自动取整为100的整数倍
- ✅ 评分自动限制在0-100范围
- ✅ 仓位比例自动限制在0-0.3范围
- ✅ is_valid() 方法正确验证推荐有效性
- ✅ to_dict() 方法正确转换为字典

### TradingPlan
- ✅ 推荐列表自动限制为最多5只
- ✅ 总仓位自动限制在0-0.8范围
- ✅ to_markdown() 方法正确生成Markdown格式

## 评分器验证

### TomorrowPotentialScorer
- ✅ 收盘形态评分 (0-15分)
- ✅ 量能分析评分 (0-15分)
- ✅ 均线位置评分 (0-12分)
- ✅ 资金流向评分 (0-15分)
- ✅ 热点关联评分 (0-15分)
- ✅ 龙头地位评分 (0-12分)
- ✅ 板块强度评分 (0-8分)
- ✅ 技术形态评分 (0-8分)
- ✅ 总分在0-100范围内
- ✅ validate_score() 方法正确验证评分有效性

## 测试结果

```
=== Checkpoint 6: Calculator Verification ===

Property 3: 买入价格合理性 (ideal < acceptable < abandon)
  PASS: All 20 random tests passed

Property 2: 仓位限制有效性 (single <= 30%, total <= 80%)
  PASS: All 20 random tests passed (single position <= 30%)
  PASS: Total position validation correctly identifies > 80%

Property 4: 止损止盈合理性 (stop_loss < entry < first_target < second_target)
  PASS: All 20 random tests passed

Property 5: 股数为100整数倍
  PASS: All 20 random tests passed

Property 10: 智能止损MAX逻辑 (stop = MAX(entry*0.95, prev_low, ma5))
  PASS: All 20 random tests passed

Property 11: 移动止盈阶梯逻辑 (涨幅>=5% -> 止盈线>=成本价)
  PASS: All 20 random tests passed

=== Checkpoint 6 Verification Complete ===

✅ All calculator tests PASSED!
```

## 结论

所有计算器模块测试通过，核心功能正常工作。可以继续进行下一阶段的开发。

## 验证脚本

验证脚本位于: `tests/verify_calculator_checkpoint.py`

运行方式:
```bash
python tests/verify_calculator_checkpoint.py
```
