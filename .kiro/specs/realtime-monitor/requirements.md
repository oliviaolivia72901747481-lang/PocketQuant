# Requirements Document

## Introduction

实时监控模块用于监控用户输入的个股，根据v11.4g科技股策略实时生成买入和卖出信号。该模块支持持仓管理、止损止盈监控、信号强度计算，并提供可视化界面展示。

## Glossary

- **Realtime_Monitor**: 实时监控器，负责监控股票并生成交易信号
- **Buy_Signal**: 买入信号，当股票满足v11.4g策略买入条件时生成
- **Sell_Signal**: 卖出信号，当持仓股票触发止损、止盈或趋势反转条件时生成
- **Position**: 持仓记录，包含股票代码、成本价、数量等信息
- **Signal_Strength**: 信号强度，0-100分，综合评估信号质量
- **V11.4g_Strategy**: 科技股交易策略，包含买入条件、止损止盈规则

## Requirements

### Requirement 1: 股票监控列表管理

**User Story:** As a trader, I want to add and remove stocks from my watchlist, so that I can monitor specific stocks for trading signals.

#### Acceptance Criteria

1. WHEN a user inputs a stock code, THE Realtime_Monitor SHALL validate the code format and add it to the watchlist
2. WHEN a user removes a stock from the watchlist, THE Realtime_Monitor SHALL stop monitoring that stock immediately
3. THE Realtime_Monitor SHALL support monitoring up to 20 stocks simultaneously
4. WHEN displaying the watchlist, THE Realtime_Monitor SHALL show stock code, name, current price, and change percentage

### Requirement 2: 持仓信息管理

**User Story:** As a trader, I want to input my position details, so that the system can calculate profit/loss and generate sell signals.

#### Acceptance Criteria

1. WHEN a user inputs position details (code, cost price, quantity), THE Realtime_Monitor SHALL store and track the position
2. THE Realtime_Monitor SHALL calculate real-time profit/loss percentage for each position
3. WHEN position data changes, THE Realtime_Monitor SHALL update profit/loss calculations immediately
4. THE Realtime_Monitor SHALL display position summary including total market value and total profit/loss

### Requirement 3: v11.4g买入信号生成

**User Story:** As a trader, I want to receive buy signals based on v11.4g strategy, so that I can identify potential entry points.

#### Acceptance Criteria

1. WHEN monitoring a stock, THE Realtime_Monitor SHALL check all v11.4g buy conditions:
   - MA5 > MA20 (金叉)
   - Price > MA60 (中期趋势向上)
   - RSI between 44-70 (动量适中)
   - Volume ratio > 1.1 (放量确认)
   - MA20 slope > 0 (趋势向上)
   - Price < MA5 × 1.05 (避免追高)
2. WHEN all 6 conditions are met, THE Realtime_Monitor SHALL generate a buy signal with strength 100
3. WHEN 5 conditions are met, THE Realtime_Monitor SHALL generate a buy signal with strength 83
4. WHEN fewer than 5 conditions are met, THE Realtime_Monitor SHALL NOT generate a buy signal
5. THE Realtime_Monitor SHALL display which conditions are met and which are not

### Requirement 4: v11.4g卖出信号生成

**User Story:** As a trader, I want to receive sell signals for my positions, so that I can protect profits and limit losses.

#### Acceptance Criteria

1. WHEN a position loss reaches -4.6%, THE Realtime_Monitor SHALL generate a stop-loss signal with urgency "high"
2. WHEN a position profit reaches +22%, THE Realtime_Monitor SHALL generate a take-profit signal
3. WHEN a position profit reaches +9% and then retraces 2.8% from peak, THE Realtime_Monitor SHALL generate a trailing-stop signal
4. WHEN RSI > 80 and position is profitable, THE Realtime_Monitor SHALL generate an RSI-overbought signal
5. WHEN MA5 < MA20 and position is at loss, THE Realtime_Monitor SHALL generate a trend-reversal signal
6. WHEN position holding days >= 15, THE Realtime_Monitor SHALL generate a timeout signal

### Requirement 5: 实时数据刷新

**User Story:** As a trader, I want real-time price updates, so that I can make timely trading decisions.

#### Acceptance Criteria

1. THE Realtime_Monitor SHALL refresh stock data every 30 seconds during trading hours (9:30-11:30, 13:00-15:00)
2. WHEN market is closed, THE Realtime_Monitor SHALL display the last available data with a "market closed" indicator
3. THE Realtime_Monitor SHALL display the last update timestamp
4. IF data refresh fails, THEN THE Realtime_Monitor SHALL show an error message and retry after 60 seconds

### Requirement 6: 信号强度计算

**User Story:** As a trader, I want to see signal strength scores, so that I can prioritize which signals to act on.

#### Acceptance Criteria

1. THE Realtime_Monitor SHALL calculate signal strength (0-100) based on:
   - Number of conditions met (max 60 points)
   - RSI position within range (max 20 points)
   - Volume ratio strength (max 20 points)
2. THE Realtime_Monitor SHALL display signal strength with color coding:
   - Green: 80-100 (strong signal)
   - Yellow: 60-79 (moderate signal)
   - Red: below 60 (weak signal)

### Requirement 7: 主力资金流向显示

**User Story:** As a trader, I want to see fund flow data, so that I can understand market sentiment.

#### Acceptance Criteria

1. THE Realtime_Monitor SHALL display today's main fund net inflow/outflow for each stock
2. THE Realtime_Monitor SHALL display 5-day cumulative fund flow trend
3. WHEN main fund net inflow > 0, THE Realtime_Monitor SHALL display in green
4. WHEN main fund net outflow > 0, THE Realtime_Monitor SHALL display in red

### Requirement 8: 技术指标面板

**User Story:** As a trader, I want to see key technical indicators, so that I can analyze stock trends.

#### Acceptance Criteria

1. THE Realtime_Monitor SHALL display for each stock:
   - Current price and change percentage
   - MA5, MA10, MA20, MA60 values
   - RSI(14) value
   - Volume ratio
   - MA20 slope (5-day)
2. THE Realtime_Monitor SHALL highlight indicators that meet v11.4g conditions in green
3. THE Realtime_Monitor SHALL highlight indicators that fail v11.4g conditions in red

### Requirement 9: 交易建议生成

**User Story:** As a trader, I want actionable trading recommendations, so that I can execute trades efficiently.

#### Acceptance Criteria

1. WHEN a buy signal is generated, THE Realtime_Monitor SHALL display:
   - Recommended entry price range
   - Stop-loss price (-4.6% from entry)
   - Take-profit target (+22% from entry)
   - Trailing stop trigger (+9% from entry)
2. WHEN a sell signal is generated, THE Realtime_Monitor SHALL display:
   - Signal urgency (high/medium/low)
   - Recommended action (immediate sell / reduce position / monitor)
   - Exit reason explanation

### Requirement 10: Streamlit界面集成

**User Story:** As a user, I want a user-friendly interface, so that I can easily monitor stocks and view signals.

#### Acceptance Criteria

1. THE Realtime_Monitor SHALL provide a Streamlit page accessible from the main navigation
2. THE Realtime_Monitor SHALL display watchlist and positions in separate tabs
3. THE Realtime_Monitor SHALL provide input fields for adding stocks and positions
4. THE Realtime_Monitor SHALL display signals in a prominent alert section
5. THE Realtime_Monitor SHALL support manual refresh button in addition to auto-refresh
