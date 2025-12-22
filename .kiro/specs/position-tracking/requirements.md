# Requirements Document

## Introduction

持仓跟踪与卖出信号功能，让用户能够记录实际持仓，并针对持仓股票生成卖出信号。解决当前系统"只有买入信号，不知道何时卖出"的问题。

## Glossary

- **Position_Tracker**: 持仓跟踪器，负责记录和管理用户的实际持仓
- **Holding**: 单个持仓记录，包含股票代码、买入价格、买入日期、数量等信息
- **Sell_Signal_Generator**: 卖出信号生成器，针对持仓股票检查卖出条件
- **Exit_Reason**: 卖出原因，如止损、止盈、策略信号等

## Requirements

### Requirement 1: 持仓记录管理

**User Story:** As a 用户, I want to 记录我的实际持仓, so that 系统能针对我的持仓生成卖出信号。

#### Acceptance Criteria

1. WHEN 用户在持仓管理页面输入股票代码、买入价格、买入数量和买入日期 THEN THE Position_Tracker SHALL 创建一条新的持仓记录
2. WHEN 用户查看持仓列表 THEN THE Position_Tracker SHALL 显示所有持仓的当前盈亏状态
3. WHEN 用户删除一条持仓记录 THEN THE Position_Tracker SHALL 从持仓列表中移除该记录
4. WHEN 用户修改持仓记录 THEN THE Position_Tracker SHALL 更新该记录的信息
5. THE Position_Tracker SHALL 将持仓数据持久化存储到本地 CSV 文件

### Requirement 2: 持仓盈亏计算

**User Story:** As a 用户, I want to 实时查看每只持仓的盈亏情况, so that 我能了解当前投资状态。

#### Acceptance Criteria

1. WHEN 用户查看持仓列表 THEN THE Position_Tracker SHALL 显示每只股票的当前价格
2. WHEN 用户查看持仓列表 THEN THE Position_Tracker SHALL 计算并显示浮动盈亏金额和百分比
3. WHEN 用户查看持仓列表 THEN THE Position_Tracker SHALL 计算并显示持仓天数
4. WHEN 持仓亏损超过止损线 THEN THE Position_Tracker SHALL 用红色高亮显示该持仓

### Requirement 3: 卖出信号生成

**User Story:** As a 用户, I want to 针对我的持仓生成卖出信号, so that 我知道何时应该卖出。

#### Acceptance Criteria

1. WHEN 用户点击"检查卖出信号"按钮 THEN THE Sell_Signal_Generator SHALL 对所有持仓股票检查卖出条件
2. WHEN RSRS 策略下持仓股票的 RSRS 标准分 < -0.7 THEN THE Sell_Signal_Generator SHALL 生成卖出信号
3. WHEN RSI 策略下持仓股票的 RSI > 70 THEN THE Sell_Signal_Generator SHALL 生成卖出信号
4. WHEN 持仓股票亏损达到硬止损线（-6%）THEN THE Sell_Signal_Generator SHALL 生成止损卖出信号
5. WHEN 生成卖出信号 THEN THE Sell_Signal_Generator SHALL 显示卖出原因和建议卖出价格

### Requirement 4: 持仓页面 UI

**User Story:** As a 用户, I want to 在一个专门的页面管理持仓和查看卖出信号, so that 操作更加便捷。

#### Acceptance Criteria

1. THE System SHALL 在侧边栏添加"持仓管理"页面入口
2. WHEN 用户访问持仓管理页面 THEN THE System SHALL 显示持仓列表、添加持仓表单、卖出信号区域
3. WHEN 有卖出信号时 THEN THE System SHALL 在页面顶部显示醒目的卖出提醒
4. THE System SHALL 提供一键导出持仓记录为 CSV 的功能

### Requirement 5: 卖出信号通知

**User Story:** As a 用户, I want to 在每日信号页面也能看到卖出信号, so that 我不会错过卖出时机。

#### Acceptance Criteria

1. WHEN 用户访问每日信号页面且有持仓 THEN THE System SHALL 在买入信号之前显示卖出信号区域
2. WHEN 有紧急卖出信号（如止损）THEN THE System SHALL 用红色警告框显示
3. THE System SHALL 在卖出信号中显示持仓成本、当前价格、盈亏比例和卖出原因
