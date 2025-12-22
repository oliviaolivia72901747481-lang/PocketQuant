# Implementation Plan: Trade Journal

## Overview

本实现计划将交易记录功能分解为可执行的编码任务，按照数据层 → 业务层 → 展示层的顺序逐步实现。每个任务都包含明确的验收标准和测试要求。

## Tasks

- [x] 1. 创建数据模型和枚举类型
  - [x] 1.1 创建 core/trade_journal.py 文件，定义 TradeAction 枚举
    - 定义 BUY 和 SELL 两个枚举值
    - _Requirements: 1.1_
  - [x] 1.2 实现 TradeRecord 数据类
    - 定义所有必填字段（code, name, action, price, quantity, trade_date）
    - 定义所有可选字段（signal_id, signal_date, signal_price, strategy, reason, commission, note）
    - 实现 id 字段自动生成（UUID 前8位）
    - _Requirements: 1.1, 1.2_
  - [x] 1.3 实现 TradeRecord 计算属性
    - 实现 total_amount 属性（price × quantity）
    - 实现 slippage 属性（(price - signal_price) / signal_price）
    - 实现 execution_delay 属性（trade_date - signal_date）
    - _Requirements: 1.3, 1.4_
  - [ ]* 1.4 编写 TradeRecord 属性测试
    - **Property 1: Computed Fields Correctness**
    - **Validates: Requirements 1.3, 1.4**
  - [x] 1.5 实现 TradePerformance 数据类
    - 定义所有统计字段
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

- [x] 2. 实现 TradeJournal 核心功能
  - [x] 2.1 实现 TradeJournal 初始化和文件加载
    - 初始化时加载现有 CSV 文件
    - 如果文件不存在则创建空列表
    - 实现数据验证和错误行跳过
    - _Requirements: 2.3, 2.4, 2.5_
  - [x] 2.2 实现 add_trade 方法
    - 验证必填字段
    - 验证 price > 0 和 quantity > 0
    - 验证 trade_date 不是未来日期
    - 追加到 CSV 文件
    - _Requirements: 2.2, 8.1, 8.2, 8.3_
  - [ ]* 2.3 编写 add_trade 输入验证属性测试
    - **Property 7: Input Validation**
    - **Validates: Requirements 8.1, 8.2, 8.3**
  - [x] 2.4 实现 CSV 持久化功能
    - 实现 _save_to_csv 私有方法
    - 实现 _load_from_csv 私有方法
    - 确保数据完整性
    - _Requirements: 2.1, 2.2, 2.4_
  - [ ]* 2.5 编写 CSV 持久化属性测试
    - **Property 2: Round-Trip Persistence**
    - **Validates: Requirements 2.2, 2.4**

- [x] 3. Checkpoint - 确保核心功能测试通过
  - 运行所有已编写的测试
  - 确保 TradeRecord 和基础 TradeJournal 功能正常
  - 如有问题请询问用户

- [x] 4. 实现查询和筛选功能
  - [x] 4.1 实现 get_trades 方法
    - 支持 start_date 和 end_date 筛选
    - 支持 code 筛选
    - 支持 action 筛选
    - 支持 strategy 筛选
    - 返回结果按 trade_date 降序排序
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_
  - [ ]* 4.2 编写筛选功能属性测试
    - **Property 3: Filter Correctness**
    - **Property 4: Sort Order Correctness**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**
  - [x] 4.3 实现 delete_trade 方法
    - 根据 trade_id 删除记录
    - 更新 CSV 文件
    - _Requirements: 2.2_

- [x] 5. 实现统计分析功能
  - [x] 5.1 实现 calculate_performance 方法
    - 计算 total_trades（总交易次数）
    - 计算 buy_trades 和 sell_trades
    - 匹配买卖对计算 closed_trades
    - 计算 total_profit 和 profitable_trades
    - 计算 win_rate（胜率）
    - 计算 total_commission 和 net_profit
    - 计算 average_holding_days
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7_
  - [ ]* 5.2 编写统计计算属性测试
    - **Property 5: Performance Calculation Correctness**
    - **Validates: Requirements 4.3, 4.6**
  - [x] 5.3 实现 get_signal_execution_stats 方法
    - 计算 signal_execution_rate
    - 计算 average_slippage
    - 获取未执行信号列表
    - _Requirements: 5.2, 5.3, 5.5_
  - [ ]* 5.4 编写信号执行追踪属性测试
    - **Property 6: Signal Execution Tracking**
    - **Validates: Requirements 5.2, 5.4**

- [x] 6. Checkpoint - 确保统计功能测试通过
  - 运行所有统计相关测试
  - 验证计算结果准确性
  - 如有问题请询问用户

- [x] 7. 实现回测对比功能
  - [x] 7.1 实现 compare_with_backtest 方法
    - 计算实盘收益率 actual_return
    - 获取回测收益率 backtest_return
    - 计算 performance_gap
    - _Requirements: 7.1, 7.2, 7.4_
  - [ ]* 7.2 编写回测对比属性测试
    - **Property 8: Performance Gap Calculation**
    - **Validates: Requirements 7.4**
  - [x] 7.3 实现 export_csv 方法
    - 导出指定交易记录为 CSV 字符串
    - _Requirements: 6.5_

- [x] 8. 创建交易记录 UI 页面
  - [x] 8.1 创建 app/pages/6_📝_Trade_Journal.py 文件
    - 设置页面配置和标题
    - 导入必要模块
    - _Requirements: 6.1_
  - [x] 8.2 实现交易记录表格展示
    - 显示交易历史表格
    - 盈利交易绿色高亮，亏损交易红色高亮
    - 支持按列排序
    - _Requirements: 6.1, 6.3_
  - [x] 8.3 实现添加交易表单
    - 创建表单输入字段
    - 实现表单验证
    - 提交后刷新页面
    - _Requirements: 6.2_
  - [x] 8.4 实现统计概览区域
    - 显示总交易次数、胜率、净利润等指标
    - 使用 st.metric 组件
    - _Requirements: 6.4_
  - [x] 8.5 实现导出功能
    - 添加导出 CSV 按钮
    - 使用 st.download_button
    - _Requirements: 6.5_

- [x] 9. 集成到每日信号页面
  - [x] 9.1 在信号卡片中添加"记录交易"按钮
    - 点击后跳转到交易记录页面
    - 自动填充信号相关字段
    - _Requirements: 6.6_
  - [x] 9.2 实现信号预填充逻辑
    - 通过 session_state 传递信号数据
    - 在交易记录页面读取并填充表单
    - _Requirements: 6.6_

- [x] 10. 实现回测对比 UI
  - [x] 10.1 添加回测对比区域
    - 选择策略和日期范围
    - 显示实盘 vs 回测收益对比
    - _Requirements: 7.3_
  - [x] 10.2 实现性能差距警告
    - 如果 performance_gap < -5%，显示警告
    - 提供可能原因分析
    - _Requirements: 7.5_

- [x] 11. Final Checkpoint - 完整功能测试
  - 运行所有测试确保通过
  - 手动测试 UI 功能
  - 验证与现有模块的集成
  - 如有问题请询问用户

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
