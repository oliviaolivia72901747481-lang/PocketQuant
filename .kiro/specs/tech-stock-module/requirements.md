# Requirements Document

## Introduction

科技股专属板块是 MiniQuant-Lite 的一个专门针对科技股的筛选和回测模块。该模块实现了一套完整的科技股交易策略，包括宏观风控（大盘红绿灯、行业强弱排位）、硬性筛选、买入信号、卖出信号和回测验证功能。

**当前策略版本**: v11.4g (平衡版)
- 收益率: 33.51%，最大回撤: -4.81%，收益/回撤比: 6.96
- 通过参数敏感性测试和滚动回测验证

**核心设计原则**：
- 小资金生存优先：股价≤80元、市值/成交额过滤
- T+1 制度最优解：14:45 尾盘判定信号
- 风险控制优先：信号优先级 紧急避险 > 止损 > 止盈 > 趋势
- 震荡市验证：强制验证 2022-2023 表现
- 趋势过滤：MA20斜率向上才买入（v11.4g新增）
- 价格位置过滤：避免追高，价格不超过MA5的5%（v11.4g新增）

## Glossary

- **Tech_Module**: 科技股专属板块模块
- **Market_Filter**: 大盘红绿灯过滤器，基于创业板指判断系统性风险
- **Sector_Ranker**: 行业强弱排位器，计算各科技行业的相对强度
- **Hard_Filter**: 硬性筛选器，过滤股价、市值、成交额
- **Signal_Generator**: 科技股买入信号生成器
- **Exit_Manager**: 卖出信号管理器，包含止损、止盈和趋势断裂逻辑
- **Backtest_Engine**: 回测引擎，用于验证策略有效性
- **GEM_Index**: 创业板指（399006）
- **MA5**: 5日移动平均线
- **MA20**: 20日移动平均线
- **MA60**: 60日移动平均线
- **MA20_Slope**: MA20斜率，用于判断趋势方向（v11.4g新增）
- **MACD**: 移动平均收敛散度指标
- **RSI**: 相对强弱指标（14日周期）
- **EOD_Signal**: 尾盘信号，14:45 判定的交易信号
- **Trailing_Stop**: 移动止盈，盈利达到触发点后启动（v11.4g新增）
- **Signal_Strength**: 信号强度，综合评分0-100（v11.4g新增）

## Requirements

### Requirement 1: 大盘红绿灯风控

**User Story:** As a 科技股投资者, I want 系统在选股前检查大盘环境, so that 我可以避免在系统性风险期间交易。

#### Acceptance Criteria

1. THE Market_Filter SHALL 使用创业板指（399006）作为大盘风控标的
2. WHEN 创业板指收盘价 > MA20 且 MACD 无死叉 THEN THE Market_Filter SHALL 返回绿灯状态
3. WHEN 创业板指收盘价 <= MA20 或 MACD 出现死叉 THEN THE Market_Filter SHALL 返回红灯状态
4. WHEN Market_Filter 返回红灯状态 THEN THE Tech_Module SHALL 禁止生成任何买入信号
5. THE Tech_Module SHALL 在界面上清晰显示当前大盘红绿灯状态

### Requirement 2: 行业强弱排位

**User Story:** As a 科技股投资者, I want 系统自动计算各科技行业的相对强度, so that 我可以只在最强的行业中选股。

#### Acceptance Criteria

1. THE Sector_Ranker SHALL 跟踪以下四个科技行业指数：半导体、AI应用、算力、消费电子
2. THE Sector_Ranker SHALL 计算各行业指数的20日涨幅
3. THE Sector_Ranker SHALL 按20日涨幅对行业进行排名
4. WHEN 生成买入信号时 THE Tech_Module SHALL 只在排名第1和第2的行业中选股
5. WHEN 股票所属行业排名第3或第4 THEN THE Tech_Module SHALL 不生成该股票的买入信号
6. THE Tech_Module SHALL 在界面上显示当前行业排名和各行业的20日涨幅

### Requirement 3: 硬性筛选指标（小资金生存基础）

**User Story:** As a 小资金投资者, I want 系统过滤掉高价股和流动性差的股票, so that 我可以在资金范围内安全交易。

#### Acceptance Criteria

1. THE Hard_Filter SHALL 过滤掉股价 > 80元的股票
2. THE Hard_Filter SHALL 过滤掉市值过大（流通市值 > 500亿）的股票
3. THE Hard_Filter SHALL 过滤掉市值过小（流通市值 < 50亿）的股票
4. THE Hard_Filter SHALL 过滤掉成交额过低（日均成交额 < 1亿）的股票
5. THE Hard_Filter SHALL 在买入信号生成前执行硬性筛选
6. THE Tech_Module SHALL 在界面上显示被过滤的股票及过滤原因

### Requirement 4: 尾盘交易机制（T+1 最优解）

**User Story:** As a A股投资者, I want 系统在尾盘（14:45）判定信号, so that 我可以在 T+1 制度下做出最优决策。

#### Acceptance Criteria

1. THE Signal_Generator SHALL 在 14:45 后判定买入信号
2. THE Signal_Generator SHALL 使用 14:45 时点的价格和指标数据
3. THE Tech_Module SHALL 在界面上显示信号判定时间
4. THE Tech_Module SHALL 提醒用户在 14:45-15:00 之间确认并执行交易
5. WHEN 在 14:45 前查看信号 THEN THE Tech_Module SHALL 显示"信号待确认"状态

### Requirement 5: 买入信号生成（v11.4g 优化版）

**User Story:** As a 科技股投资者, I want 系统根据技术指标和基本面生成买入信号, so that 我可以在合适的时机买入。

#### Acceptance Criteria

1. WHEN MA5 金叉 MA20 且 股价 > MA60 THEN THE Signal_Generator SHALL 满足趋势条件
2. WHEN RSI(14) 在 44-70 之间 THEN THE Signal_Generator SHALL 满足动量条件（v11.4g更新：原55-80）
3. WHEN 当日成交量 > 5日均量 × 1.1 THEN THE Signal_Generator SHALL 满足量能条件（v11.4g更新：原1.5）
4. WHEN 营收或净利至少一个正增长 且 无大额解禁 THEN THE Signal_Generator SHALL 满足基本面条件
5. WHEN MA20斜率向上 THEN THE Signal_Generator SHALL 满足趋势过滤条件（v11.4g新增）
6. WHEN 当前价格 < MA5 × 1.05 THEN THE Signal_Generator SHALL 满足价格位置条件（v11.4g新增：避免追高）
7. WHEN 信号强度 >= 83 THEN THE Signal_Generator SHALL 满足信号质量条件（v11.4g新增）
8. WHEN 趋势、动量、量能、基本面、趋势过滤、价格位置、信号质量七个条件同时满足 THEN THE Signal_Generator SHALL 生成买入信号
9. IF 任一条件不满足 THEN THE Signal_Generator SHALL 不生成买入信号

### Requirement 6: 止损管理（v11.4g 优化版）

**User Story:** As a 科技股投资者, I want 系统自动计算止损位, so that 我可以控制风险。

#### Acceptance Criteria

1. WHEN 持仓亏损达到 -4.6% THEN THE Exit_Manager SHALL 生成清仓卖出信号（v11.4g更新：原-10%）
2. WHEN 持仓盈利 > 9% THEN THE Exit_Manager SHALL 启动移动止盈机制（v11.4g新增）
3. WHEN 移动止盈启动后 从最高点回撤 2.8% THEN THE Exit_Manager SHALL 生成卖出信号（v11.4g新增）
4. WHEN 持仓盈利达到 22% THEN THE Exit_Manager SHALL 生成止盈卖出信号（v11.4g新增）
5. WHEN 持仓天数 >= 15天 THEN THE Exit_Manager SHALL 生成超时卖出信号（v11.4g新增）
6. THE Exit_Manager SHALL 确保单笔亏损控制在可接受范围内

### Requirement 7: RSI分仓止盈（v11.4g 优化版）

**User Story:** As a 科技股投资者, I want 系统根据RSI和持仓量提供分仓止盈建议, so that 我可以锁定部分利润。

#### Acceptance Criteria

1. WHEN 持仓 >= 200股 且 RSI > 80 且 持仓盈利 THEN THE Exit_Manager SHALL 建议卖出一半仓位（v11.4g更新：RSI阈值从85降至80，新增盈利条件）
2. WHEN 持仓 = 100股 且 RSI > 80 且 持仓盈利 THEN THE Exit_Manager SHALL 建议止损紧贴 MA5（v11.4g更新：RSI阈值从85降至80，新增盈利条件）
3. WHEN RSI > 80 且 持仓亏损 THEN THE Exit_Manager SHALL 不触发RSI止盈（v11.4g新增：仅盈利时触发）
4. THE Exit_Manager SHALL 在界面上显示当前RSI值和止盈建议

### Requirement 8: 趋势断裂卖出

**User Story:** As a 科技股投资者, I want 系统检测趋势断裂, so that 我可以及时退出下跌趋势。

#### Acceptance Criteria

1. WHEN 收盘价连续2日跌破 MA20 THEN THE Exit_Manager SHALL 生成趋势断裂卖出信号
2. THE Exit_Manager SHALL 在界面上显示MA20跌破天数

### Requirement 9: 信号优先级管理

**User Story:** As a 科技股投资者, I want 系统按优先级显示卖出信号, so that 我可以优先处理最紧急的风险。

#### Acceptance Criteria

1. THE Exit_Manager SHALL 按以下优先级排序卖出信号：紧急避险 > 止损 > 止盈 > 趋势断裂
2. WHEN 大盘红灯 且 持仓亏损 THEN THE Exit_Manager SHALL 生成"紧急避险"信号（最高优先级）
3. WHEN 触发 -4.6% 止损 THEN THE Exit_Manager SHALL 生成"止损"信号（第二优先级，v11.4g更新：原-10%）
4. WHEN RSI > 80 且 盈利 触发止盈 THEN THE Exit_Manager SHALL 生成"止盈"信号（第三优先级，v11.4g更新：原RSI>85）
5. WHEN 趋势断裂 THEN THE Exit_Manager SHALL 生成"趋势断裂"信号（第四优先级）
6. THE Tech_Module SHALL 在界面上用不同颜色区分信号优先级

### Requirement 10: 特殊持仓标记

**User Story:** As a 科技股投资者, I want 系统高亮显示100股持仓, so that 我可以对最小仓位执行严格止盈。

#### Acceptance Criteria

1. THE Tech_Module SHALL 高亮显示持仓数量为100股的持仓
2. THE Tech_Module SHALL 在100股持仓旁显示"严格止盈"提醒
3. WHEN 100股持仓 且 RSI > 85 THEN THE Tech_Module SHALL 显示"止损紧贴MA5"警告
4. THE Tech_Module SHALL 使用特殊颜色或图标标记100股持仓

### Requirement 11: 回测验证（强制震荡市验证）

**User Story:** As a 科技股投资者, I want 在实盘前进行回测验证, so that 我可以确认策略在震荡市的有效性。

#### Acceptance Criteria

1. THE Backtest_Engine SHALL 强制包含 2022.01.01 - 2023.12.31 的震荡市时间段
2. THE Backtest_Engine SHALL 支持自定义回测时间段（但必须包含震荡市）
3. THE Backtest_Engine SHALL 默认提供长盈精密、中际旭创、北方华创作为测试标的
4. THE Backtest_Engine SHALL 计算并显示最大回撤指标
5. WHEN 最大回撤 > -15% THEN THE Backtest_Engine SHALL 显示警告
6. THE Backtest_Engine SHALL 分别统计 2022年、2023年上半年、2023年下半年的交易次数
7. THE Backtest_Engine SHALL 验证大盘红灯期间交易次数是否显著减少
8. THE Backtest_Engine SHALL 显示震荡市（2022-2023）的独立绩效报告

### Requirement 12: 科技股池管理

**User Story:** As a 科技股投资者, I want 管理科技股候选池, so that 我可以专注于特定的科技股。

#### Acceptance Criteria

1. THE Tech_Module SHALL 提供预设的科技股池（按行业分类）
2. THE Tech_Module SHALL 支持用户自定义添加/删除股票
3. THE Tech_Module SHALL 显示每只股票所属的行业分类
4. THE Tech_Module SHALL 支持按行业筛选股票

### Requirement 13: 界面展示

**User Story:** As a 科技股投资者, I want 在专属页面查看所有科技股相关信息, so that 我可以高效地进行决策。

#### Acceptance Criteria

1. THE Tech_Module SHALL 提供独立的科技股页面入口
2. THE Tech_Module SHALL 在页面顶部显示大盘红绿灯状态
3. THE Tech_Module SHALL 显示行业强弱排名表
4. THE Tech_Module SHALL 显示符合条件的买入信号列表
5. THE Tech_Module SHALL 显示持仓的卖出信号和止损位
6. THE Tech_Module SHALL 提供回测功能入口
7. THE Tech_Module SHALL 用不同颜色区分信号优先级（紧急避险红色、止损橙色、止盈黄色、趋势蓝色）
8. THE Tech_Module SHALL 在回测验证页面显示当前策略参数配置（v11.4g新增）

### Requirement 14: 策略参数配置（v11.4g）

**User Story:** As a 科技股投资者, I want 查看和理解当前策略的参数配置, so that 我可以了解策略的运作方式。

#### Acceptance Criteria

1. THE Tech_Module SHALL 使用以下仓位管理参数：
   - 单只股票仓位: 11%
   - 最大持仓数量: 5只

2. THE Tech_Module SHALL 使用以下止盈止损参数：
   - 止损线: -4.6%
   - 止盈线: +22%
   - 移动止盈触发: +9%
   - 移动止盈回撤: 2.8%
   - 最大持仓天数: 15天

3. THE Tech_Module SHALL 使用以下买入条件参数：
   - RSI范围: 44 ~ 70
   - 成交量确认: 当日量 > 5日均量×1.1
   - 信号强度门槛: ≥ 83
   - 趋势过滤: MA20斜率向上
   - 价格位置: 价格 < MA5×1.05

4. THE Tech_Module SHALL 使用以下卖出条件参数：
   - RSI超买: RSI > 80 且盈利时触发
   - 趋势反转: MA5 < MA20 且亏损时触发

5. THE Tech_Module SHALL 在界面上显示策略参数配置和说明

### Requirement 15: 策略验证（v11.4g）

**User Story:** As a 科技股投资者, I want 了解策略的验证结果, so that 我可以对策略有信心。

#### Acceptance Criteria

1. THE Backtest_Engine SHALL 完成参数敏感性测试，验证策略鲁棒性
2. THE Backtest_Engine SHALL 完成滚动回测验证（Walk-Forward Analysis）
3. WHEN 参数敏感性测试显示所有参数组合的最大回撤 < -5% THEN THE Backtest_Engine SHALL 标记策略为"鲁棒"
4. WHEN 滚动回测显示 > 70% 的窗口盈利 THEN THE Backtest_Engine SHALL 标记策略为"实盘可行"
5. THE Tech_Module SHALL 在界面上显示策略验证结果摘要
