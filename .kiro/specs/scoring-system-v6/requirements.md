# Requirements Document

## Introduction

优化隔夜选股系统的评分策略，从原有的8维度100分体系升级为更符合A股短线实战的6维度100分体系。新体系强调"题材是第一生产力"，引入股性活跃度维度，并优化趋势、量价、资金等核心维度的评分逻辑。

## Glossary

- **Scorer**: 评分器，负责对股票进行多维度评分的核心模块
- **TrendPositionScorer**: 趋势与位置评分器，评估均线排列和股价相对位置
- **KLinePatternScorer**: K线与形态评分器，识别K线形态和技术形态
- **VolumePriceScorer**: 量价配合评分器，分析成交量与价格的配合关系
- **CapitalStrengthScorer**: 资金强度评分器，评估主力资金流入占比
- **ThemeWindScorer**: 题材风口评分器，评估题材热度和板块效应
- **StockActivityScorer**: 股性活跃度评分器，评估股票的交易活跃程度
- **Deviation_Rate**: 乖离率，股价与均线的偏离程度
- **Turnover_Rate**: 换手率，成交量占流通股本的比例
- **Limit_Up**: 涨停，股价达到当日涨幅上限(10%或20%)

## Requirements

### Requirement 1: 趋势与位置评分 (20分)

**User Story:** As a 短线交易者, I want 系统评估股票的趋势和位置, so that 我能识别低位突破和高位风险。

#### Acceptance Criteria

1. WHEN 股价处于低位且均线多头排列, THE Scorer SHALL 给予满分20分
2. WHEN 股价突破关键均线(MA20/MA60), THE Scorer SHALL 给予16-18分
3. WHEN 股价高位加速且乖离率过大(>15%), THE Scorer SHALL 给予10分并标记风险提示
4. WHEN 均线空头排列, THE Scorer SHALL 给予0分
5. WHEN 均线粘合即将选择方向, THE Scorer SHALL 给予12-14分

### Requirement 2: K线与形态评分 (15分)

**User Story:** As a 短线交易者, I want 系统识别K线形态, so that 我能判断明日走势方向。

#### Acceptance Criteria

1. WHEN 出现涨停/反包/突破前高形态, THE Scorer SHALL 给予满分15分
2. WHEN 出现企稳十字星/多方炮形态, THE Scorer SHALL 给予10分
3. WHEN 出现吊颈线/乌云盖顶等顶部形态, THE Scorer SHALL 给予0分
4. WHEN 出现下影线阳线(有支撑), THE Scorer SHALL 给予12分
5. WHEN 出现普通阳线, THE Scorer SHALL 给予8分

### Requirement 3: 量价配合评分 (15分)

**User Story:** As a 短线交易者, I want 系统分析量价关系, so that 我能识别健康上涨和危险信号。

#### Acceptance Criteria

1. WHEN 缩量涨停或温和放量上涨(1.5-2倍), THE Scorer SHALL 给予满分15分
2. WHEN 底部或突破口出现倍量, THE Scorer SHALL 给予满分15分
3. WHEN 高位出现巨量滞涨, THE Scorer SHALL 给予0分
4. WHEN 出现天量阴线, THE Scorer SHALL 给予0分
5. WHEN 换手率在合理区间(3%-15%), THE Scorer SHALL 给予额外加分
6. WHEN 换手率过低(<1%)或过高(>25%), THE Scorer SHALL 扣分

### Requirement 4: 资金强度评分 (15分)

**User Story:** As a 短线交易者, I want 系统评估资金流入强度, so that 我能跟随主力资金方向。

#### Acceptance Criteria

1. WHEN 主力净流入占比>10%, THE Scorer SHALL 给予满分15分
2. WHEN 主力净流入占比在5%-10%, THE Scorer SHALL 给予12分
3. WHEN 主力净流入占比在0%-5%, THE Scorer SHALL 给予8分
4. WHEN 散户买入为主(主力净流出), THE Scorer SHALL 给予5分
5. WHEN 主力大幅流出(占比<-10%), THE Scorer SHALL 给予0分

### Requirement 5: 题材风口评分 (25分)

**User Story:** As a 短线交易者, I want 系统评估题材热度, so that 我能抓住市场主线机会。

#### Acceptance Criteria

1. WHEN 股票属于主线题材且板块效应强, THE Scorer SHALL 给予满分25分
2. WHEN 股票属于支线题材且有助攻, THE Scorer SHALL 给予15分
3. WHEN 股票为独立个股无板块效应, THE Scorer SHALL 给予8分
4. WHEN 股票无任何题材关联, THE Scorer SHALL 给予3分
5. WHEN 题材处于退潮期, THE Scorer SHALL 降低评分并标记风险

### Requirement 6: 股性活跃度评分 (10分)

**User Story:** As a 短线交易者, I want 系统评估股票活跃度, so that 我能避开"死股"。

#### Acceptance Criteria

1. WHEN 近20日有涨停记录, THE Scorer SHALL 给予满分10分
2. WHEN 历史波动率高(日均振幅>3%), THE Scorer SHALL 给予8分
3. WHEN 近期有连板记录, THE Scorer SHALL 给予额外加分
4. WHEN 股票长期横盘(织布机/心电图走势), THE Scorer SHALL 给予0分
5. WHEN 近60日最大涨幅<10%, THE Scorer SHALL 给予2分

### Requirement 7: 评分系统集成

**User Story:** As a 系统用户, I want 新评分系统无缝替换旧系统, so that 我能立即使用优化后的选股功能。

#### Acceptance Criteria

1. THE Scorer SHALL 保持与现有OvernightStockPicker的接口兼容
2. THE Scorer SHALL 输出总分(0-100)和各维度详情
3. THE Scorer SHALL 支持配置权重调整
4. WHEN 评分完成, THE Scorer SHALL 生成可读的评分摘要
5. THE Scorer SHALL 记录评分日志用于回测分析

### Requirement 8: 风险提示功能

**User Story:** As a 短线交易者, I want 系统标记高风险情况, so that 我能规避潜在风险。

#### Acceptance Criteria

1. WHEN 高位加速(乖离率>15%), THE Scorer SHALL 标记"追高风险"
2. WHEN 天量阴线, THE Scorer SHALL 标记"出货风险"
3. WHEN 题材退潮, THE Scorer SHALL 标记"题材退潮风险"
4. WHEN 股票长期无涨停, THE Scorer SHALL 标记"股性差"
5. THE Scorer SHALL 在评分详情中显示所有风险标记
