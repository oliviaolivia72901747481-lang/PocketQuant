# Implementation Plan: Position Tracking

## Overview

实现持仓跟踪与卖出信号功能，包括持仓管理核心模块、卖出信号检查器、持仓管理页面，以及与每日信号页面的集成。

## Tasks

- [x] 1. 实现 PositionTracker 核心模块
  - [x] 1.1 创建 Holding 数据类和 PositionTracker 类
    - 创建 `core/position_tracker.py`
    - 实现 Holding dataclass（code, name, buy_price, buy_date, quantity, strategy, note）
    - 实现 PositionTracker 的 __init__、add_position、remove_position、get_all_positions
    - _Requirements: 1.1, 1.3, 1.5_

  - [x] 1.2 实现持仓盈亏计算
    - 实现 calculate_pnl 方法（计算浮动盈亏金额和百分比）
    - 实现 get_holding_days 方法（计算持仓天数）
    - 实现 get_portfolio_summary 方法（汇总所有持仓）
    - _Requirements: 2.2, 2.3_

  - [x] 1.3 实现 CSV 持久化
    - 实现 _load_from_csv 和 _save_to_csv 方法
    - 实现 export_csv 方法（导出为字符串）
    - 处理文件不存在、格式错误等异常
    - _Requirements: 1.5, 4.4_

  - [ ]* 1.4 编写 PositionTracker 单元测试
    - 测试 CRUD 操作
    - 测试盈亏计算边界情况
    - 测试 CSV 持久化
    - _Requirements: 1.1, 1.3, 2.2, 2.3_

- [x] 2. 实现 SellSignalChecker 模块
  - [x] 2.1 创建 SellSignal 数据类和 SellSignalChecker 类
    - 创建 `core/sell_signal_checker.py`
    - 实现 SellSignal dataclass
    - 实现 SellSignalChecker 的 __init__ 和 check_all_positions
    - _Requirements: 3.1_

  - [x] 2.2 实现止损信号检查
    - 实现 _check_stop_loss 方法
    - 当亏损 >= 6% 时生成 urgency="high" 的卖出信号
    - _Requirements: 3.4_

  - [x] 2.3 实现 RSRS 卖出信号检查
    - 实现 _check_rsrs_sell 方法
    - 复用 signal_generator 中的 RSRS 计算逻辑
    - 当 RSRS 标准分 < -0.7 时生成卖出信号
    - _Requirements: 3.2_

  - [x] 2.4 实现 RSI 卖出信号检查
    - 实现 _check_rsi_sell 方法
    - 当 RSI > 70 时生成卖出信号
    - _Requirements: 3.3_

  - [ ]* 2.5 编写 SellSignalChecker 单元测试
    - 测试止损信号生成
    - 测试 RSRS/RSI 卖出信号生成
    - _Requirements: 3.2, 3.3, 3.4_

- [ ] 3. Checkpoint - 核心模块完成
  - 确保所有测试通过，ask the user if questions arise.

- [x] 4. 创建持仓管理页面
  - [x] 4.1 创建页面基础结构
    - 创建 `app/pages/4_Position.py`
    - 实现页面布局（持仓列表、添加表单、卖出信号区域）
    - _Requirements: 4.1, 4.2_

  - [x] 4.2 实现持仓列表展示
    - 显示所有持仓及其盈亏状态
    - 亏损超过止损线的持仓用红色高亮
    - 支持删除持仓操作
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x] 4.3 实现添加持仓表单
    - 输入股票代码、买入价格、数量、日期、策略
    - 验证输入有效性
    - 添加成功后刷新列表
    - _Requirements: 1.1, 1.2_

  - [x] 4.4 实现卖出信号展示
    - 显示所有卖出信号
    - 紧急信号（止损）用红色警告框
    - 显示卖出原因和指标值
    - _Requirements: 3.5, 4.3_

  - [x] 4.5 实现导出功能
    - 添加"导出 CSV"按钮
    - 下载持仓记录
    - _Requirements: 4.4_

- [x] 5. 集成到每日信号页面
  - [x] 5.1 在每日信号页面添加卖出信号区域
    - 修改 `app/pages/3_Daily_Signal.py`
    - 在买入信号之前显示卖出信号
    - 只有当有持仓时才显示
    - _Requirements: 5.1, 5.2, 5.3_

- [x] 6. Final Checkpoint
  - 所有功能已实现完成

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
