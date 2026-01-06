# Requirements Document

## Introduction

设计"T日选股，T+1执行"的隔夜短线选股系统。每天收盘后(15:00后)运行，基于当日完整日线数据，筛选出明天可以买入的股票，并给出具体的买入价格、仓位和止损止盈建议。

核心设计理念：
- 不依赖实时数据，使用收盘后的完整日线数据
- 解决数据延迟问题：收盘数据是确定的，不存在延迟
- 解决滞后性问题：专注于"明日潜力"而非"今日确认"
- 解决题材匹配问题：智能识别龙头，区分真热点和蹭热点
- 输出可执行的交易计划：明确的买入价、仓位、止损止盈

## Glossary

- **Overnight_Stock_Picker**: 隔夜选股器，收盘后运行的核心选股模块
- **Tomorrow_Potential_Scorer**: 明日潜力评分器，预测明日上涨概率
- **Entry_Price_Calculator**: 买入价计算器，计算理想买入价格区间
- **Position_Advisor**: 仓位顾问，根据评分和风险给出仓位建议
- **Stop_Loss_Calculator**: 止损计算器，计算止损价格
- **Take_Profit_Calculator**: 止盈计算器，计算止盈目标价
- **Smart_Topic_Matcher**: 智能题材匹配器，识别真龙头
- **Trading_Plan_Generator**: 交易计划生成器，输出完整的明日交易计划
- **Call_Auction_Filter**: 竞价过滤器，处理集合竞价阶段的特殊情况
- **Sentiment_Cycle_Predictor**: 情绪周期预判器，预测明日情绪轮动
- **Smart_Stop_Loss**: 智能止损器，技术止损+固定止损结合
- **Trailing_Stop**: 移动止盈器，锁定利润不让盈利变亏损
- **Pre_Market_Adjuster**: 早盘修正器，根据隔夜消息调整计划

## Requirements

### Requirement 1: 隔夜选股核心流程

**User Story:** As a 短线散户, I want 每天收盘后运行选股程序, so that 我可以提前准备明天的交易计划。

#### Acceptance Criteria

1. WHEN 用户在15:00后运行选股程序时, THE Overnight_Stock_Picker SHALL 获取当日完整收盘数据
2. WHEN 选股完成时, THE Overnight_Stock_Picker SHALL 输出明日推荐买入的股票列表(最多5只)
3. THE Overnight_Stock_Picker SHALL 按"明日潜力评分"从高到低排序输出结果
4. WHEN 输出结果时, THE Overnight_Stock_Picker SHALL 包含每只股票的买入价、仓位、止损、止盈建议
5. THE Overnight_Stock_Picker SHALL 在结果中标注当前大盘环境和市场情绪
6. IF 大盘环境极差, THEN THE Overnight_Stock_Picker SHALL 建议空仓观望，不输出买入推荐

### Requirement 2: 明日潜力评分系统

**User Story:** As a 短线散户, I want 系统预测股票明天的上涨潜力, so that 我可以选择最有可能上涨的股票。

#### Acceptance Criteria

1. WHEN 计算明日潜力时, THE Tomorrow_Potential_Scorer SHALL 分析今日收盘形态(阳线/阴线/十字星)
2. WHEN 计算明日潜力时, THE Tomorrow_Potential_Scorer SHALL 分析今日量能变化(放量/缩量/平量)
3. WHEN 计算明日潜力时, THE Tomorrow_Potential_Scorer SHALL 分析均线位置关系(多头/空头/粘合)
4. WHEN 计算明日潜力时, THE Tomorrow_Potential_Scorer SHALL 分析今日资金流向(主力净流入/流出)
5. WHEN 计算明日潜力时, THE Tomorrow_Potential_Scorer SHALL 分析所属热点题材的持续性
6. WHEN 计算明日潜力时, THE Tomorrow_Potential_Scorer SHALL 分析板块内龙头/跟风地位
7. THE Tomorrow_Potential_Scorer SHALL 输出0-100的明日潜力评分

### Requirement 3: 智能题材匹配与龙头识别

**User Story:** As a 短线散户, I want 系统能识别真正的龙头股, so that 我不会买到蹭热点的杂毛股。

#### Acceptance Criteria

1. WHEN 匹配题材时, THE Smart_Topic_Matcher SHALL 分析公司主营业务与题材的关联度
2. WHEN 识别龙头时, THE Smart_Topic_Matcher SHALL 计算"龙头指数"(涨停时间、封单量、连板天数)
3. WHEN 识别龙头时, THE Smart_Topic_Matcher SHALL 区分"真龙头"、"二线龙头"和"蹭热点股"
4. THE Smart_Topic_Matcher SHALL 记录每个题材的历史龙头，用于预测明日龙头
5. WHEN 今日有新热点出现时, THE Smart_Topic_Matcher SHALL 识别并加入热点列表
6. THE Smart_Topic_Matcher SHALL 输出每只股票的"龙头指数"(0-100)

### Requirement 4: 买入价格计算

**User Story:** As a 短线散户, I want 系统告诉我明天应该在什么价格买入, so that 我不会追高买入。

#### Acceptance Criteria

1. WHEN 计算买入价时, THE Entry_Price_Calculator SHALL 基于今日收盘价计算理想买入区间
2. THE Entry_Price_Calculator SHALL 输出"理想买入价"(低开时买入)
3. THE Entry_Price_Calculator SHALL 输出"可接受买入价"(平开时买入)
4. THE Entry_Price_Calculator SHALL 输出"放弃买入价"(高开超过此价不买)
5. WHEN 股票处于强势时, THE Entry_Price_Calculator SHALL 适当提高可接受买入价
6. WHEN 股票处于弱势时, THE Entry_Price_Calculator SHALL 降低可接受买入价

### Requirement 5: 仓位与风险管理

**User Story:** As a 短线散户(7万元资金), I want 系统告诉我每只股票买多少, so that 我可以控制风险。

#### Acceptance Criteria

1. WHEN 计算仓位时, THE Position_Advisor SHALL 基于总资金7万元计算
2. WHEN 计算仓位时, THE Position_Advisor SHALL 考虑股票评分(高分多买，低分少买)
3. WHEN 计算仓位时, THE Position_Advisor SHALL 考虑大盘环境(弱势降仓)
4. THE Position_Advisor SHALL 限制单只股票最大仓位为30%(2.1万元)
5. THE Position_Advisor SHALL 限制总仓位最大为80%(5.6万元)
6. THE Position_Advisor SHALL 输出具体的买入金额和股数(100股的整数倍)
7. IF 评分低于70分, THEN THE Position_Advisor SHALL 不建议买入

### Requirement 6: 止损止盈计算

**User Story:** As a 短线散户, I want 系统告诉我止损和止盈价格, so that 我可以提前设置好卖出计划。

#### Acceptance Criteria

1. WHEN 计算止损价时, THE Stop_Loss_Calculator SHALL 基于买入价计算(默认-5%)
2. WHEN 计算止损价时, THE Stop_Loss_Calculator SHALL 考虑股票波动性(高波动可放宽到-7%)
3. THE Stop_Loss_Calculator SHALL 输出止损价格和最大亏损金额
4. WHEN 计算止盈价时, THE Take_Profit_Calculator SHALL 基于买入价计算(默认+8%)
5. THE Take_Profit_Calculator SHALL 输出第一止盈位(+5%)和第二止盈位(+10%)
6. THE Take_Profit_Calculator SHALL 输出预期盈利金额

### Requirement 7: 交易计划生成

**User Story:** As a 短线散户, I want 系统生成完整的明日交易计划, so that 我明天可以直接执行。

#### Acceptance Criteria

1. WHEN 选股完成时, THE Trading_Plan_Generator SHALL 生成完整的交易计划文档
2. THE Trading_Plan_Generator SHALL 包含：日期、大盘环境、市场情绪、推荐股票列表
3. THE Trading_Plan_Generator SHALL 为每只股票包含：代码、名称、评分、买入价区间、仓位、止损、止盈
4. THE Trading_Plan_Generator SHALL 包含"明日操作要点"提示
5. THE Trading_Plan_Generator SHALL 支持导出为Markdown格式
6. THE Trading_Plan_Generator SHALL 记录历史交易计划，用于后续复盘

### Requirement 8: 竞价过滤器 (解决竞价逻辑缺失)

**User Story:** As a 短线散户, I want 系统在竞价阶段帮我判断是否执行买入计划, so that 我不会在核按钮时买入或错过强势抢筹。

#### Acceptance Criteria

1. IF 开盘价低于昨收-4%, THEN THE Call_Auction_Filter SHALL 触发"核按钮警报"，取消该股买入计划
2. IF 龙头股高开>3% 且 竞价量比>5, THEN THE Call_Auction_Filter SHALL 触发"抢筹确认"，允许突破买入
3. WHEN 生成交易计划时, THE Entry_Price_Calculator SHALL 为每只股票标注策略类型(低吸型/突破型)
4. IF 策略类型为"低吸型", THEN THE Call_Auction_Filter SHALL 严格遵守放弃价
5. IF 策略类型为"突破型", THEN THE Call_Auction_Filter SHALL 允许放宽放弃价但要求竞价爆量
6. THE Call_Auction_Filter SHALL 在09:25竞价结束后输出"竞价修正建议"

### Requirement 9: 情绪周期预判 (解决情绪轮动问题)

**User Story:** As a 短线散户, I want 系统预判明日情绪周期, so that 我不会在高潮日买入被套。

#### Acceptance Criteria

1. WHEN 今日情绪为EXTREME_GREED(极度乐观), THE Sentiment_Cycle_Predictor SHALL 预判明日为"分歧日"
2. IF 预判明日为"分歧日", THEN THE Position_Advisor SHALL 将仓位建议×0.5，且只做核心龙头
3. WHEN 今日情绪为EXTREME_FEAR(极度恐慌), THE Sentiment_Cycle_Predictor SHALL 预判明日为"修复日"
4. IF 预判明日为"修复日", THEN THE Position_Advisor SHALL 将仓位建议×1.2，重点关注反包形态
5. THE Sentiment_Cycle_Predictor SHALL 输出情绪周期位置(冰点→修复→升温→高潮→分歧→退潮)
6. THE Trading_Plan_Generator SHALL 在计划中标注当前情绪周期和明日预判

### Requirement 10: 智能止损止盈 (解决固定止损问题)

**User Story:** As a 短线散户, I want 止损止盈更智能, so that 我不会被正常波动洗出去。

#### Acceptance Criteria

1. WHEN 计算止损价时, THE Smart_Stop_Loss SHALL 取MAX(买入价×0.95, 昨日最低价, 5日均线)
2. THE Smart_Stop_Loss SHALL 优先使用技术止损(跌破5日线)，固定比例作为兜底
3. IF 股票波动率>8%, THEN THE Smart_Stop_Loss SHALL 放宽止损到-7%
4. WHEN 股价上涨>5%时, THE Trailing_Stop SHALL 启动移动止盈，止盈线上移到成本价
5. WHEN 股价上涨>10%时, THE Trailing_Stop SHALL 将止盈线上移到+5%位置
6. THE Trailing_Stop SHALL 确保"绝不让盈利变亏损"

### Requirement 11: 早盘修正模块 (解决隔夜消息真空)

**User Story:** As a 短线散户, I want 系统在早盘根据隔夜消息修正计划, so that 我不会因为美股大跌而盲目买入。

#### Acceptance Criteria

1. THE Pre_Market_Adjuster SHALL 在09:00-09:15运行，获取隔夜信息
2. WHEN 获取隔夜信息时, THE Pre_Market_Adjuster SHALL 检查美股涨跌幅、A50期指、个股公告
3. IF A50期指跌幅>1%, THEN THE Pre_Market_Adjuster SHALL 下调所有计划股买入限价2%
4. IF A50期指跌幅>2%, THEN THE Pre_Market_Adjuster SHALL 取消非核心龙头的买入计划
5. IF 个股有重大利空公告, THEN THE Pre_Market_Adjuster SHALL 取消该股买入计划
6. THE Pre_Market_Adjuster SHALL 输出"早盘修正报告"，说明调整原因

### Requirement 12: 历史回测验证

**User Story:** As a 开发者, I want 用历史数据验证选股策略, so that 我可以优化参数配置。

#### Acceptance Criteria

1. WHEN 用户运行回测时, THE Backtest_Engine SHALL 模拟历史每日选股
2. WHEN 回测完成时, THE Backtest_Engine SHALL 计算策略胜率(次日上涨比例)
3. WHEN 回测完成时, THE Backtest_Engine SHALL 计算平均收益率
4. THE Backtest_Engine SHALL 支持不同时间段的回测(1周/1月/3月)
5. THE Backtest_Engine SHALL 输出回测报告，包含关键指标和改进建议
