# Requirements Document

## Introduction

交易记录功能（Trade Journal）是 MiniQuant-Lite 系统的核心增强功能，用于记录用户的实盘交易操作，追踪交易表现，并与回测结果进行对比验证。该功能帮助用户建立对系统的信任，同时提供数据支持以持续优化交易策略。

## Glossary

- **Trade_Journal**: 交易日志管理器，负责交易记录的增删改查和统计分析
- **Trade_Record**: 单条交易记录，包含买入或卖出的完整信息
- **Trade_Action**: 交易动作枚举，包括买入(BUY)和卖出(SELL)
- **Slippage**: 滑点，实际成交价格与信号建议价格的偏差百分比
- **Trade_Performance**: 交易表现统计，包括收益率、胜率、平均持仓天数等
- **Signal_Execution**: 信号执行记录，关联信号与实际交易

## Requirements

### Requirement 1: 交易记录数据模型

**User Story:** As a user, I want to record my trades with complete information, so that I can track my trading history accurately.

#### Acceptance Criteria

1. THE Trade_Record SHALL contain the following required fields: code (股票代码), name (股票名称), action (买入/卖出), price (成交价格), quantity (成交数量), trade_date (成交日期)
2. THE Trade_Record SHALL contain the following optional fields: signal_date (信号日期), signal_price (信号价格), strategy (策略名称), reason (交易原因), commission (手续费), note (备注)
3. WHEN a Trade_Record is created, THE Trade_Journal SHALL automatically calculate slippage if signal_price is provided
4. WHEN a Trade_Record is created, THE Trade_Journal SHALL automatically calculate total_amount as price × quantity
5. THE Trade_Record SHALL support both manual entry and signal-linked entry modes

### Requirement 2: 交易记录持久化存储

**User Story:** As a user, I want my trade records to be saved persistently, so that I don't lose my trading history.

#### Acceptance Criteria

1. THE Trade_Journal SHALL store all trade records in a CSV file at data/trade_journal.csv
2. WHEN a new trade is added, THE Trade_Journal SHALL append it to the CSV file immediately
3. WHEN the CSV file does not exist, THE Trade_Journal SHALL create it with proper headers
4. THE Trade_Journal SHALL support loading existing records from the CSV file on initialization
5. THE Trade_Journal SHALL validate data integrity when loading records and skip invalid rows with warning

### Requirement 3: 交易记录查询功能

**User Story:** As a user, I want to query my trade history with filters, so that I can analyze specific periods or stocks.

#### Acceptance Criteria

1. WHEN querying trades, THE Trade_Journal SHALL support filtering by date range (start_date, end_date)
2. WHEN querying trades, THE Trade_Journal SHALL support filtering by stock code
3. WHEN querying trades, THE Trade_Journal SHALL support filtering by trade action (买入/卖出/全部)
4. WHEN querying trades, THE Trade_Journal SHALL support filtering by strategy name
5. THE Trade_Journal SHALL return results sorted by trade_date in descending order (newest first)

### Requirement 4: 交易表现统计

**User Story:** As a user, I want to see my trading performance statistics, so that I can evaluate my trading effectiveness.

#### Acceptance Criteria

1. THE Trade_Journal SHALL calculate total_trades (总交易次数) for a given period
2. THE Trade_Journal SHALL calculate total_profit (总盈亏金额) by matching buy and sell records
3. THE Trade_Journal SHALL calculate win_rate (胜率) as profitable_trades / total_closed_trades
4. THE Trade_Journal SHALL calculate average_holding_days (平均持仓天数) for closed positions
5. THE Trade_Journal SHALL calculate total_commission (总手续费) for a given period
6. THE Trade_Journal SHALL calculate net_profit (净利润) as total_profit - total_commission
7. IF no closed trades exist, THEN THE Trade_Journal SHALL return zero for profit-related metrics

### Requirement 5: 信号执行追踪

**User Story:** As a user, I want to link my trades to system signals, so that I can track signal execution quality.

#### Acceptance Criteria

1. WHEN adding a trade, THE Trade_Journal SHALL allow linking to a signal by signal_id
2. THE Trade_Journal SHALL calculate signal_execution_rate as executed_signals / total_signals for a period
3. THE Trade_Journal SHALL calculate average_slippage for executed signals
4. WHEN a signal is executed, THE Trade_Journal SHALL record the execution_delay (days between signal and trade)
5. THE Trade_Journal SHALL provide a method to get unexecuted signals for follow-up

### Requirement 6: 交易记录UI界面

**User Story:** As a user, I want a user-friendly interface to manage my trades, so that I can easily add, view, and analyze my trading history.

#### Acceptance Criteria

1. THE UI SHALL display a trade history table with sortable columns
2. THE UI SHALL provide a form to add new trade records with validation
3. THE UI SHALL highlight profitable trades in green and losing trades in red
4. THE UI SHALL display summary statistics at the top of the page
5. THE UI SHALL provide export functionality to download trades as CSV
6. WHEN adding a trade from signal page, THE UI SHALL pre-fill signal-related fields automatically

### Requirement 7: 回测对比功能

**User Story:** As a user, I want to compare my actual trading performance with backtest results, so that I can validate the system's effectiveness.

#### Acceptance Criteria

1. THE Trade_Journal SHALL calculate actual_return for a given period from real trades
2. THE Trade_Journal SHALL retrieve backtest_return for the same period and strategy
3. THE UI SHALL display a comparison chart showing actual vs backtest performance
4. THE UI SHALL calculate and display performance_gap as (actual_return - backtest_return)
5. IF performance_gap is significantly negative (> 5%), THEN THE UI SHALL display a warning with possible reasons

### Requirement 8: 数据完整性与错误处理

**User Story:** As a user, I want the system to handle errors gracefully, so that my data remains safe and I understand what went wrong.

#### Acceptance Criteria

1. IF a required field is missing when adding a trade, THEN THE Trade_Journal SHALL return an error message specifying the missing field
2. IF the trade price or quantity is invalid (≤ 0), THEN THE Trade_Journal SHALL reject the record with an error
3. IF the trade date is in the future, THEN THE Trade_Journal SHALL reject the record with an error
4. WHEN loading corrupted CSV data, THE Trade_Journal SHALL skip invalid rows and log warnings
5. THE Trade_Journal SHALL create a backup before any bulk operations
