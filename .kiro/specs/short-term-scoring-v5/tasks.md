# Implementation Plan: 隔夜选股系统 v5.0

## Overview

实现"T日选股，T+1执行"的隔夜短线选股系统。基于Python实现，使用现有的数据基础设施，输出Markdown格式的交易计划。

## Tasks

- [-] 1. 项目结构和核心接口设置
  - [-] 1.1 创建 `core/overnight_picker/` 目录结构
    - 创建 `__init__.py`, `models.py`, `scorer.py`, `calculator.py` 等文件
    - _Requirements: 1.1_
  - [ ] 1.2 定义核心数据模型 (StockRecommendation, TradingPlan)
    - 在 `models.py` 中实现 dataclass 定义
    - _Requirements: 1.4, 7.2, 7.3_
  - [ ]* 1.3 编写数据模型属性测试
    - **Property 5: 股数为100整数倍**
    - **Validates: Requirements 5.6**

- [ ] 2. 明日潜力评分器实现
  - [ ] 2.1 实现 TomorrowPotentialScorer 基础框架
    - 8个评分维度的权重配置
    - _Requirements: 2.1-2.7_
  - [ ] 2.2 实现收盘形态评分 (score_closing_pattern)
    - 分析K线形态：阳线/阴线/十字星/上下影线
    - _Requirements: 2.1_
  - [ ] 2.3 实现量能分析评分 (score_volume_analysis)
    - 分析成交量变化：放量/缩量/温和放量
    - _Requirements: 2.2_
  - [ ] 2.4 实现均线位置评分 (score_ma_position)
    - 分析均线排列：多头/空头/粘合
    - _Requirements: 2.3_
  - [ ] 2.5 实现资金流向评分 (score_capital_flow)
    - 分析主力资金流入流出
    - _Requirements: 2.4_
  - [ ] 2.6 实现热点关联评分 (score_hot_topic)
    - 分析题材热度和关联性
    - _Requirements: 2.5_
  - [ ] 2.7 实现龙头地位评分 (score_leader_index)
    - 分析板块内龙头/跟风地位
    - _Requirements: 2.6_
  - [ ] 2.8 实现板块强度和技术形态评分
    - score_sector_strength 和 score_technical_pattern
    - _Requirements: 2.7_
  - [ ]* 2.9 编写评分器属性测试
    - **Property 1: 评分范围有效性**
    - *For any* 股票评分结果，总分应在0-100之间，各维度分数不超过其权重上限
    - **Validates: Requirements 2.7**

- [ ] 3. Checkpoint - 评分器测试验证
  - 确保所有评分测试通过，如有问题请询问用户

- [ ] 4. 买入价和仓位计算器实现
  - [ ] 4.1 实现 EntryPriceCalculator
    - 计算理想买入价、可接受买入价、放弃买入价
    - _Requirements: 4.1-4.6_
  - [ ]* 4.2 编写买入价属性测试
    - **Property 3: 买入价格合理性**
    - *For any* 买入价格建议，理想价 < 可接受价 < 放弃价
    - **Validates: Requirements 4.2, 4.3, 4.4**
  - [ ] 4.3 实现 PositionAdvisor
    - 基于7万元资金计算仓位，单只≤30%，总仓≤80%
    - _Requirements: 5.1-5.7_
  - [ ]* 4.4 编写仓位属性测试
    - **Property 2: 仓位限制有效性**
    - *For any* 仓位建议，单只股票仓位不超过30%，总仓位不超过80%
    - **Validates: Requirements 5.4, 5.5**

- [ ] 5. 止损止盈计算器实现
  - [ ] 5.1 实现 SmartStopLoss 智能止损器
    - 止损 = MAX(买入价×0.95, 昨日最低价, 5日均线)
    - _Requirements: 10.1-10.3_
  - [ ] 5.2 实现 TrailingStop 移动止盈器
    - 涨5%→成本价，涨10%→+5%，涨15%→+10%
    - _Requirements: 10.4-10.6_
  - [ ] 5.3 实现基础 StopLossCalculator 和 TakeProfitCalculator
    - 默认止损-5%，止盈+5%/+10%
    - _Requirements: 6.1-6.6_
  - [ ]* 5.4 编写止损止盈属性测试
    - **Property 4: 止损止盈合理性**
    - *For any* 止损止盈建议，止损价 < 买入价 < 第一止盈 < 第二止盈
    - **Validates: Requirements 6.1, 6.4, 6.5**
  - [ ]* 5.5 编写智能止损属性测试
    - **Property 10: 智能止损MAX逻辑**
    - *For any* 智能止损计算，结果应等于MAX(买入价×0.95, 昨日最低, 5日均线)
    - **Validates: Requirements 10.1**
  - [ ]* 5.6 编写移动止盈属性测试
    - **Property 11: 移动止盈阶梯逻辑**
    - *For any* 涨幅≥5%的持仓，移动止盈线应≥成本价
    - **Validates: Requirements 10.4, 10.5**

- [ ] 6. Checkpoint - 计算器测试验证
  - 确保所有计算器测试通过，如有问题请询问用户

- [ ] 7. 智能题材匹配器实现
  - [ ] 7.1 实现 SmartTopicMatcher 基础框架
    - 公司主营业务数据库、历史龙头记录
    - _Requirements: 3.1, 3.4_
  - [ ] 7.2 实现题材关联度计算 (match_topic_relevance)
    - 分析主营业务与题材的真实关联度
    - _Requirements: 3.1_
  - [ ] 7.3 实现龙头指数计算 (calculate_leader_index)
    - 涨停时间、封单量、连板天数、市场认可度
    - _Requirements: 3.2_
  - [ ] 7.4 实现龙头类型识别 (identify_leader_type)
    - 区分真龙头、二线龙头、跟风股、蹭热点
    - _Requirements: 3.3_

- [ ] 8. 竞价过滤器实现 (解决竞价逻辑缺失)
  - [ ] 8.1 实现 CallAuctionFilter 基础框架
    - 核按钮阈值-4%，抢筹阈值+3%，量比阈值5
    - _Requirements: 8.1, 8.2_
  - [ ] 8.2 实现竞价分析逻辑 (analyze_auction)
    - 核按钮检测、抢筹确认、策略类型判断
    - _Requirements: 8.1-8.5_
  - [ ] 8.3 实现策略类型确定 (determine_strategy_type)
    - 低吸型 vs 突破型
    - _Requirements: 8.3-8.5_
  - [ ]* 8.4 编写竞价过滤器属性测试
    - **Property 8: 核按钮过滤正确性**
    - *For any* 低开>4%的情况，竞价过滤器应返回CANCEL
    - **Validates: Requirements 8.1**

- [ ] 9. 情绪周期预判器实现 (解决情绪轮动问题)
  - [ ] 9.1 实现 SentimentCyclePredictor 基础框架
    - 6阶段周期定义：冰点→修复→升温→高潮→分歧→退潮
    - _Requirements: 9.5_
  - [ ] 9.2 实现今日情绪分析 (analyze_today_sentiment)
    - 涨停家数、跌停家数、炸板率、连板股、赚钱效应
    - _Requirements: 9.1, 9.3_
  - [ ] 9.3 实现明日情绪预判 (predict_tomorrow)
    - 高潮→分歧(×0.5)，冰点→修复(×1.2)
    - _Requirements: 9.1-9.4_
  - [ ]* 9.4 编写情绪周期属性测试
    - **Property 9: 情绪周期预判一致性**
    - *For any* EXTREME_GREED情绪，预判应为"分歧日"
    - **Validates: Requirements 9.1, 9.3**

- [ ] 10. 早盘修正器实现 (解决隔夜消息真空)
  - [ ] 10.1 实现 PreMarketAdjuster 基础框架
    - A50阈值：-1%轻度，-2%严重
    - _Requirements: 11.1, 11.2_
  - [ ] 10.2 实现隔夜数据获取 (fetch_overnight_data)
    - 美股、A50期指、个股公告
    - _Requirements: 11.2_
  - [ ] 10.3 实现交易计划调整 (adjust_trading_plan)
    - A50跌>1%下调买入价2%，跌>2%取消非核心龙头
    - _Requirements: 11.3-11.5_
  - [ ] 10.4 实现早盘修正报告生成 (generate_adjustment_report)
    - _Requirements: 11.6_

- [ ] 11. Checkpoint - 核心模块测试验证
  - 确保竞价过滤器、情绪周期、早盘修正模块测试通过

- [ ] 12. 交易计划生成器实现
  - [ ] 12.1 实现 TradingPlanGenerator 基础框架
    - _Requirements: 7.1_
  - [ ] 12.2 实现交易计划生成 (generate_plan)
    - 日期、大盘环境、市场情绪、推荐股票列表
    - _Requirements: 7.2, 7.3_
  - [ ] 12.3 实现Markdown格式输出
    - 包含操作要点和风险提示
    - _Requirements: 7.4, 7.5_
  - [ ] 12.4 实现历史计划记录
    - 保存历史交易计划用于复盘
    - _Requirements: 7.6_
  - [ ]* 12.5 编写推荐列表属性测试
    - **Property 6: 推荐列表长度限制**
    - *For any* 选股结果，推荐列表长度应≤5
    - **Validates: Requirements 1.2**
  - [ ]* 12.6 编写排序属性测试
    - **Property 7: 推荐列表排序正确性**
    - *For any* 推荐列表，评分应按降序排列
    - **Validates: Requirements 1.3**

- [ ] 13. 隔夜选股器主流程实现
  - [ ] 13.1 实现 OvernightStockPicker 主类
    - 整合所有模块，实现完整选股流程
    - _Requirements: 1.1-1.6_
  - [ ] 13.2 实现数据获取和预处理
    - 获取收盘数据、计算技术指标
    - _Requirements: 1.1_
  - [ ] 13.3 实现大盘环境判断
    - 强势/震荡/弱势判断，极差时空仓
    - _Requirements: 1.5, 1.6_
  - [ ] 13.4 实现完整选股流程
    - 评分→筛选→排序→生成计划
    - _Requirements: 1.2, 1.3, 1.4_

- [ ] 14. 命令行工具实现
  - [ ] 14.1 创建 `tools/overnight_stock_picker.py`
    - 命令行入口，支持参数配置
    - _Requirements: 1.1_
  - [ ] 14.2 实现交易计划输出
    - 输出到控制台和Markdown文件
    - _Requirements: 7.5_

- [ ] 15. Checkpoint - 集成测试验证
  - 确保完整流程测试通过，如有问题请询问用户

- [ ] 16. 历史回测模块实现
  - [ ] 16.1 实现 BacktestEngine 基础框架
    - _Requirements: 12.1_
  - [ ] 16.2 实现历史选股模拟
    - 模拟历史每日选股
    - _Requirements: 12.1_
  - [ ] 16.3 实现策略指标计算
    - 胜率、平均收益率
    - _Requirements: 12.2, 12.3_
  - [ ] 16.4 实现回测报告生成
    - 支持不同时间段回测
    - _Requirements: 12.4, 12.5_

- [ ] 17. Final Checkpoint - 完整系统验证
  - 确保所有测试通过，系统可正常运行
  - 如有问题请询问用户

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- 使用 Python 实现，基于现有的 `core/short_term/` 模块扩展
- 使用 hypothesis 库进行属性测试
- 每个 Checkpoint 确保阶段性功能完整可用
- 优先实现核心选股流程，回测模块可后续完善
