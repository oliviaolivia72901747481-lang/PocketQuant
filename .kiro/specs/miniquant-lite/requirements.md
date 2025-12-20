# Requirements Document

## Introduction

MiniQuant-Lite 是一套面向 A 股个人投资者的轻量级量化投资辅助系统。系统基于 Python 构建，使用免费开源数据接口（AkShare），提供选股筛选、策略回测和每日交易信号生成功能。目标用户为本金约 5.5 万元人民币的个人投资者。

## Glossary

- **System**: MiniQuant-Lite 量化投资辅助系统
- **Data_Feed**: 数据获取与清洗模块，封装 AkShare 接口
- **Screener**: 选股器，基于 Pandas 筛选符合条件的股票标的
- **Backtest_Engine**: 回测引擎，基于 Backtrader 框架执行策略回测
- **Signal_Generator**: 交易信号生成器，产出每日买卖信号
- **Sizer**: 资金管理模块，控制仓位和资金分配
- **Strategy**: 交易策略，定义买卖规则
- **Stock_Pool**: 股票池，定义可交易的股票范围
- **AI_Agent**: ~~AI 投资助理模块~~（已简化为财报窗口期检测 + 新闻链接，把决策权还给人）

## Requirements

### Requirement 1: 数据获取与管理

**User Story:** 作为个人投资者，我希望能够自动获取和管理 A 股历史行情数据，以便进行后续的选股和回测分析。

#### Acceptance Criteria

1. WHEN 用户请求下载股票数据 THEN THE Data_Feed SHALL 通过 AkShare 接口获取指定股票的历史日线数据并保存为 CSV 格式
2. WHEN 原始数据下载完成 THEN THE Data_Feed SHALL 将数据清洗并转换为 Backtrader 兼容格式（包含 open, high, low, close, volume 字段）
3. THE Data_Feed SHALL 强制使用**前复权（Forward Adjusted）**数据下载，以消除分红送转对技术指标的干扰（AkShare 使用 `adjust="qfq"` 参数）
4. IF 数据获取失败 THEN THE Data_Feed SHALL 记录详细的错误日志，区分网络问题和接口变更问题，并提示用户检查 AkShare 版本
5. WHEN 用户配置股票池 THEN THE System SHALL 支持批量下载股票池内所有股票的历史数据
6. THE Data_Feed SHALL 采用**覆盖更新**策略：每次更新时覆盖重写该股票最近 365 天的数据，以确保复权数据的准确性（避免增量更新导致的复权数据不一致问题）
7. THE System SHALL 在 requirements.txt 中锁定 AkShare 版本号，避免因接口变更导致系统故障
8. THE Data_Feed SHALL 提供 `get_market_snapshot()` 方法，获取全市场实时快照数据（市值、换手率、股票名称等），用于预剪枝优化

### Requirement 2: 选股筛选功能（含流动性过滤、大盘滤网、行业互斥）

**User Story:** 作为个人投资者，我希望能够根据技术指标、基本面条件、流动性指标和大盘环境筛选股票，以便快速找到适合小资金操作的优质标的。

#### Acceptance Criteria

1. WHEN 用户设置筛选条件 THEN THE Screener SHALL 基于 Pandas 对股票池进行条件过滤
2. THE Screener SHALL 支持基于技术指标的筛选条件（如：MA均线、MACD、RSI、成交量）
3. THE Screener SHALL 支持基于价格区间的筛选条件（如：股价在10-50元之间）
4. WHEN 筛选完成 THEN THE Screener SHALL 返回符合条件的股票列表及其关键指标数据
5. IF 没有股票符合筛选条件 THEN THE Screener SHALL 返回空列表并提示用户调整条件
6. THE Screener SHALL 默认启用流动性过滤：流通市值在 50亿-500亿 之间（中盘股，弹性好）
7. THE Screener SHALL 默认启用换手率过滤：换手率 > 2% 且 < 15%（避免僵尸股和出货股）
8. THE Screener SHALL 自动剔除 ST 股票（股票名称包含 ST 或 *ST）
9. THE Screener SHALL 自动剔除上市不满 60 天的新股
10. THE Screener SHALL 支持趋势过滤条件：MA60 > MA60(前一日)（均线向上）
11. THE Screener SHALL 实现大盘滤网：当沪深300指数 < MA20 时，返回空列表并提示"大盘环境不佳，建议空仓观望"
12. THE Screener SHALL 实现行业互斥：同一行业最多选取 1 只股票，避免行业集中风险
13. THE Screener SHALL 采用**两阶段筛选优化**：先用实时快照数据预剪枝（市值/换手率/ST），生成候选池后再下载历史数据进行精筛，以大幅提升筛选速度

### Requirement 3: 策略回测功能

**User Story:** 作为个人投资者，我希望能够对交易策略进行历史回测，以便评估策略的有效性和风险收益特征。

#### Acceptance Criteria

1. WHEN 用户选择策略和回测参数 THEN THE Backtest_Engine SHALL 使用 Backtrader 框架执行回测
2. THE Backtest_Engine SHALL 支持配置初始资金（默认5.5万元）、手续费率、印花税率
3. WHEN 回测完成 THEN THE Backtest_Engine SHALL 计算并返回关键绩效指标（总收益率、年化收益率、最大回撤、夏普比率、**超额收益 Alpha**、**胜率 Winning Rate**）
4. THE Backtest_Engine SHALL 引入**沪深300指数作为基准（Benchmark）**，计算同期基准收益率
5. THE Backtest_Engine SHALL 生成回测期间的资金曲线数据
6. THE Backtest_Engine SHALL 记录所有交易明细（买入/卖出时间、价格、数量、盈亏、**止损/止盈触发原因**）
7. THE Backtest_Engine SHALL 支持**涨跌停板检测**：在策略执行时判断是否为一字板（open == close == high == low），若是则禁止交易，避免回测结果虚高
8. IF 回测过程中发生错误 THEN THE Backtest_Engine SHALL 记录错误并返回错误信息
9. THE Backtest_Engine SHALL 在回测报告中重点展示**胜率（Winning Rate）**和**最大回撤（Max Drawdown）**，对于小散户低回撤比高收益更重要

### Requirement 4: 资金管理与仓位控制

**User Story:** 作为小资金投资者，我希望系统能够智能管理仓位，以便在有限本金下控制风险并最大化资金利用率。

#### Acceptance Criteria

1. THE Sizer SHALL 根据配置的初始资金（5.5万元）计算每笔交易的最大可买入数量
2. THE Sizer SHALL 确保每笔买入数量为100股的整数倍（A股最小交易单位）
3. WHEN 计算买入数量时 THE Sizer SHALL 预留足够资金支付手续费
4. THE Sizer SHALL 采用**最大持仓只数（Max N Positions）**模式控制风险，默认同时最多持仓 2-3 只股票，避免因百分比限制导致无法买入高价优质股
5. THE Sizer SHALL 支持**仓位容差逻辑**：如果买入 1 手导致仓位略超预设比例（如达到 35%），只要现金足够，应允许买入
6. THE Sizer SHALL 设置**最小交易金额门槛**（默认 15000 元）：如果计算出的交易金额低于此门槛，则禁止开仓，以避免"5元低消"手续费导致的高费率磨损
7. IF 可用资金不足以买入最小单位 THEN THE Sizer SHALL 跳过该交易并记录日志
8. THE Signal_Generator SHALL 对低于最小交易金额门槛的信号标记"高费率预警"
9. WHEN 交易被拒绝时 THE Sizer SHALL 返回明确的拒绝原因（如"股价过高，只能买一手，放弃交易"），让用户死心

### Requirement 5: 交易策略实现（趋势滤网 + 止损止盈）

**User Story:** 作为个人投资者，我希望系统提供经过优化的策略框架，包含趋势过滤和风险控制机制，以便在小资金条件下实现稳健收益。

#### Acceptance Criteria

1. THE Strategy SHALL 继承统一的策略基类，包含标准的日志记录和订单管理功能
2. THE System SHALL 提供 Trend Filtered MACD 策略作为默认策略（替代纯 MACD 策略）
3. WHEN 策略产生买入信号 THEN THE Strategy SHALL 调用 Sizer 计算买入数量并下单
4. WHEN 策略产生卖出信号 THEN THE Strategy SHALL 卖出持有的全部或指定数量的股票
5. THE Strategy SHALL 在每个交易日结束时记录当前持仓和资金状态
6. THE Strategy SHALL 实现趋势滤网：只有当股价 > MA60 时，MACD 金叉才视为有效买入信号（右侧交易）
7. THE Strategy SHALL 实现 RSI 过滤：买入时要求 RSI < 80，若 RSI > 90 则即使 MACD 金叉也不追高
8. THE Strategy SHALL 实现硬止损：买入后亏损达到 -8% 时，无条件市价止损（给高波动股留活路）
9. THE Strategy SHALL 实现移动止盈：当盈利超过 15% 后，从最高点回撤 5% 时止盈（让利润多奔跑）
10. THE Strategy SHALL 记录每笔交易的止损/止盈触发原因

### Requirement 6: 每日交易信号生成

**User Story:** 作为个人投资者，我希望系统能够每天生成交易信号，以便我在开盘前了解当日的操作建议。

#### Acceptance Criteria

1. WHEN 用户请求生成每日信号 THEN THE Signal_Generator SHALL 基于最新数据和选定策略计算买卖信号
2. THE Signal_Generator SHALL 输出信号类型（买入/卖出/持有）、股票代码、建议价格区间
3. THE Signal_Generator SHALL 输出限价上限（limit_cap = 收盘价 × 1.01），防止次日高开时盲目追高
4. THE Signal_Generator SHALL 显示信号生成的依据（如：MACD金叉、均线突破）
5. WHEN 信号生成完成 THEN THE Dashboard SHALL 以清晰的表格形式展示所有信号
6. IF 当日无交易信号 THEN THE Signal_Generator SHALL 显示"今日无操作建议"

### Requirement 7: 可视化界面

**User Story:** 作为个人投资者，我希望通过简洁的 Web 界面操作系统，以便无需编写代码即可使用各项功能。

#### Acceptance Criteria

1. THE Dashboard SHALL 使用 Streamlit 框架构建，提供数据管理、回测、信号三个主要页面
2. WHEN 用户访问数据管理页面 THEN THE Dashboard SHALL 显示数据更新状态和下载功能
3. THE Dashboard SHALL 在数据管理页面提供**"一键清空缓存"**按钮，以便在数据出错时快速重置
4. WHEN 用户访问回测页面 THEN THE Dashboard SHALL 提供策略选择、参数配置和回测结果展示
5. THE Dashboard SHALL 在回测结果页面将**策略净值曲线与沪深300基准曲线**绑定在同一张图上展示
6. WHEN 用户访问信号页面 THEN THE Dashboard SHALL 显示当日交易信号和历史信号记录
7. THE Dashboard SHALL 对低于最小交易金额门槛的信号使用**红色高亮显示"高费率预警"**
8. THE Dashboard SHALL 使用图表展示资金曲线和关键指标
9. THE Dashboard SHALL 在首页显示**"避险战绩看板"**，展示大盘滤网生效期间规避的下跌风险，安抚用户空仓期焦虑
10. THE Dashboard SHALL 在信号页面显著位置展示**"早安确认清单"**，提醒用户在 9:25 集合竞价前确认隔夜风险（美股、低开等）

### Requirement 8: 配置管理

**User Story:** 作为个人投资者，我希望能够灵活配置系统参数，以便根据我的实际情况调整系统行为。

#### Acceptance Criteria

1. THE System SHALL 支持通过配置文件设置初始资金、手续费率、印花税率
2. THE System SHALL 支持配置回测的起止日期
3. THE System SHALL 支持配置股票池（沪深300成分股或自选股列表）
4. WHEN 配置参数变更 THEN THE System SHALL 在下次运行时使用新配置
5. THE System SHALL 提供合理的默认配置值

### Requirement 9: 日志与错误处理

**User Story:** 作为个人投资者，我希望系统能够记录运行日志，以便在出现问题时能够追溯和排查。

#### Acceptance Criteria

1. THE System SHALL 记录所有关键操作的日志（数据下载、回测执行、信号生成）
2. THE System SHALL 将日志按日期分文件存储
3. IF 发生异常 THEN THE System SHALL 记录详细的错误堆栈信息
4. THE System SHALL 支持配置日志级别（DEBUG、INFO、WARNING、ERROR）
5. WHEN 用户查看日志 THEN THE Dashboard SHALL 提供日志查看功能


### Requirement 10: 财报窗口期风险检测

**User Story:** 作为个人投资者，我希望系统能够自动检测财报披露日期，以便我避开财报窗口期的不确定性风险。

#### Acceptance Criteria

1. THE Screener SHALL 在筛选阶段检查股票的财报披露日期
2. WHEN 股票距离财报披露日前后 3 天内 THEN THE Screener SHALL 自动剔除该股票并在信号中标记"财报窗口期"
3. THE System SHALL 把最终决策权交给用户，系统只做硬风控（财报窗口期检测）

### Requirement 11: 回测与实盘差异说明

**User Story:** 作为个人投资者，我希望系统能够清晰说明回测结果与实盘操作的差异，以便我对系统有正确的预期。

#### Acceptance Criteria

1. THE Dashboard SHALL 在回测结果页面显著位置展示"回测局限性免责声明"
2. THE Dashboard SHALL 说明回测结果仅基于技术指标，不包含新闻面人工过滤
3. THE Dashboard SHALL 提示用户实盘操作时应结合新闻链接进行人工判断
4. THE Dashboard SHALL 说明回测无法模拟真实的滑点、流动性不足等市场摩擦

- **Dashboard**: Streamlit 可视化界面


### Requirement 12: 便捷的新闻查看入口

**User Story:** 作为个人投资者，我希望能够快速查看候选股票的新闻资讯，以便人工判断是否存在风险。

#### Acceptance Criteria

1. THE Dashboard SHALL 在信号页面为每只股票提供新闻快捷链接
2. WHEN 用户点击新闻链接 THEN THE System SHALL 跳转到东方财富/同花顺的个股资讯页面
3. THE System SHALL 保留财报窗口期自动检测功能，在信号中标记"财报窗口期"风险
