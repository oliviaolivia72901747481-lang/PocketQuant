# Requirements Document

## Introduction

优化短线散户专用评分系统，解决当前系统的7大不足：热点识别不智能、缺少实时数据、没有历史回测、缺少盘中监控、板块联动分析不足、没有考虑大盘环境、缺少情绪面分析。

## Glossary

- **Short_Term_Scorer**: 短线评分系统核心模块
- **Hot_Topic_Manager**: 热点题材管理器，负责热点的自动识别和更新
- **Market_Data_Fetcher**: 市场数据获取器，负责实时获取资金流向等数据
- **Market_Sentiment_Analyzer**: 市场情绪分析器，分析涨跌停、炸板率等
- **Index_Environment_Analyzer**: 大盘环境分析器，判断大盘强弱
- **Sector_Linkage_Analyzer**: 板块联动分析器，分析龙头与跟风股关系
- **Backtest_Engine**: 回测引擎，验证评分系统有效性

## Requirements

### Requirement 1: 热点题材智能识别

**User Story:** As a 短线散户, I want 系统自动识别当前市场热点, so that 我不需要手动更新热点配置。

#### Acceptance Criteria

1. WHEN 系统启动时, THE Hot_Topic_Manager SHALL 从配置文件加载热点题材列表
2. WHEN 用户调用更新热点功能时, THE Hot_Topic_Manager SHALL 基于涨停板数据自动识别当日热点板块
3. WHEN 热点题材过期时, THE Hot_Topic_Manager SHALL 自动将其标记为失效
4. WHEN 新热点被识别时, THE Hot_Topic_Manager SHALL 自动添加到热点列表并设置权重
5. THE Hot_Topic_Manager SHALL 支持手动添加和删除热点题材

### Requirement 2: 实时市场数据获取

**User Story:** As a 短线散户, I want 系统自动获取资金流向数据, so that 我不需要手动输入这些数据。

#### Acceptance Criteria

1. WHEN 用户请求股票评分时, THE Market_Data_Fetcher SHALL 自动获取主力净流入数据
2. WHEN 用户请求股票评分时, THE Market_Data_Fetcher SHALL 自动获取大单买卖比例
3. WHEN 用户请求股票评分时, THE Market_Data_Fetcher SHALL 自动获取北向资金流向
4. WHEN 数据获取失败时, THE Market_Data_Fetcher SHALL 返回默认值并记录警告
5. THE Market_Data_Fetcher SHALL 支持数据缓存以减少API调用

### Requirement 3: 市场情绪分析

**User Story:** As a 短线散户, I want 了解当前市场情绪, so that 我可以判断是否适合操作。

#### Acceptance Criteria

1. WHEN 用户请求市场情绪时, THE Market_Sentiment_Analyzer SHALL 计算涨停家数和跌停家数
2. WHEN 用户请求市场情绪时, THE Market_Sentiment_Analyzer SHALL 计算炸板率
3. WHEN 用户请求市场情绪时, THE Market_Sentiment_Analyzer SHALL 计算连板股数量
4. WHEN 用户请求市场情绪时, THE Market_Sentiment_Analyzer SHALL 计算市场赚钱效应指数
5. THE Market_Sentiment_Analyzer SHALL 根据情绪指标给出市场情绪等级(极度恐慌/恐慌/中性/乐观/极度乐观)

### Requirement 4: 大盘环境分析

**User Story:** As a 短线散户, I want 了解大盘环境强弱, so that 我可以调整仓位和策略。

#### Acceptance Criteria

1. WHEN 用户请求大盘分析时, THE Index_Environment_Analyzer SHALL 分析上证指数趋势
2. WHEN 用户请求大盘分析时, THE Index_Environment_Analyzer SHALL 分析创业板指数趋势
3. WHEN 大盘处于弱势时, THE Index_Environment_Analyzer SHALL 建议降低仓位
4. WHEN 大盘处于强势时, THE Index_Environment_Analyzer SHALL 建议可以加仓
5. THE Index_Environment_Analyzer SHALL 输出大盘环境等级(强势/震荡/弱势)

### Requirement 5: 板块联动分析

**User Story:** As a 短线散户, I want 了解板块内龙头和跟风股的关系, so that 我可以选择更好的买入时机。

#### Acceptance Criteria

1. WHEN 用户请求板块分析时, THE Sector_Linkage_Analyzer SHALL 识别板块龙头股
2. WHEN 用户请求板块分析时, THE Sector_Linkage_Analyzer SHALL 计算板块内个股相关性
3. WHEN 龙头股涨停时, THE Sector_Linkage_Analyzer SHALL 预测可能补涨的跟风股
4. THE Sector_Linkage_Analyzer SHALL 输出板块强度评分
5. THE Sector_Linkage_Analyzer SHALL 标记每只股票在板块内的地位(龙头/二线/跟风)

### Requirement 6: 综合评分系统升级

**User Story:** As a 短线散户, I want 评分系统综合考虑所有因素, so that 我可以得到更准确的投资建议。

#### Acceptance Criteria

1. WHEN 计算综合评分时, THE Short_Term_Scorer SHALL 加入市场情绪维度
2. WHEN 计算综合评分时, THE Short_Term_Scorer SHALL 加入大盘环境调整系数
3. WHEN 大盘弱势时, THE Short_Term_Scorer SHALL 自动提高买入门槛
4. WHEN 市场情绪极度恐慌时, THE Short_Term_Scorer SHALL 发出风险警告
5. THE Short_Term_Scorer SHALL 支持8个评分维度(热点+资金+趋势+动量+成交量+板块+情绪+大盘)

### Requirement 7: 历史回测验证

**User Story:** As a 开发者, I want 用历史数据验证评分系统, so that 我可以优化参数配置。

#### Acceptance Criteria

1. WHEN 用户运行回测时, THE Backtest_Engine SHALL 使用历史数据模拟评分
2. WHEN 回测完成时, THE Backtest_Engine SHALL 计算评分系统的胜率
3. WHEN 回测完成时, THE Backtest_Engine SHALL 计算评分系统的收益率
4. THE Backtest_Engine SHALL 支持不同时间段的回测
5. THE Backtest_Engine SHALL 输出回测报告包含关键指标
