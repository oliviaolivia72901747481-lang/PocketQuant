# Implementation Plan: Realtime Monitor

## Overview

实现实时监控模块，基于v11.4g科技股策略提供买卖信号生成、持仓管理和可视化界面。采用增量开发方式，先实现核心功能，再逐步完善。

## Tasks

- [x] 1. 创建核心数据模型和配置
  - [x] 1.1 创建 `core/realtime_monitor/config.py` 配置文件
    - 定义v11.4g策略参数常量
    - 定义监控配置（刷新间隔、最大监控数等）
    - _Requirements: 3.1, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_
  - [x] 1.2 创建 `core/realtime_monitor/models.py` 数据模型
    - 实现 Position 数据类（含盈亏计算属性）
    - 实现 StockData 数据类
    - 实现 BuySignal 和 SellSignal 数据类
    - _Requirements: 2.1, 2.2, 3.1, 4.1_
  - [x] 1.3 编写数据模型单元测试
    - 测试 Position 盈亏计算
    - 测试持仓天数计算
    - **Property 3: PnL Calculation Accuracy**
    - **Validates: Requirements 2.2**

- [x] 2. 实现技术指标计算模块
  - [x] 2.1 创建 `core/realtime_monitor/indicators.py`
    - 实现 MA 计算函数
    - 实现 RSI 计算函数
    - 实现量比计算函数
    - 实现 MA20 斜率计算函数
    - _Requirements: 8.1_
  - [x] 2.2 编写技术指标单元测试
    - 测试各指标计算正确性
    - 测试边界条件

- [x] 3. 实现信号引擎核心逻辑
  - [x] 3.1 创建 `core/realtime_monitor/signal_engine.py`
    - 实现 v11.4g 买入条件检查（6个条件）
    - 实现信号强度计算
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 6.1_
  - [x] 3.2 编写买入信号属性测试
    - **Property 4: Buy Signal Strength Calculation**
    - **Validates: Requirements 3.2, 3.3, 3.4**
  - [x] 3.3 实现卖出信号检查
    - 实现止损信号检查 (-4.6%)
    - 实现止盈信号检查 (+22%)
    - 实现移动止盈信号检查 (+9%触发, 2.8%回撤)
    - 实现RSI超买信号检查 (RSI>80且盈利)
    - 实现趋势反转信号检查 (MA5<MA20且亏损)
    - 实现持仓超时信号检查 (>=15天)
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_
  - [x] 3.4 编写卖出信号属性测试
    - **Property 5: Stop Loss Signal Generation**
    - **Property 6: Take Profit Signal Generation**
    - **Property 7: Trailing Stop Signal Generation**
    - **Property 8: RSI Overbought Signal Generation**
    - **Property 9: Trend Reversal Signal Generation**
    - **Property 10: Timeout Signal Generation**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5, 4.6**

- [x] 4. Checkpoint - 核心信号逻辑验证
  - 确保所有信号生成测试通过
  - 验证v11.4g策略参数正确
  - 如有问题请询问用户

- [x] 5. 实现监控列表和持仓管理
  - [x] 5.1 创建 `core/realtime_monitor/monitor.py` 主类
    - 实现监控列表管理（添加/删除/验证）
    - 实现持仓管理（添加/更新/删除）
    - 实现峰值价格跟踪（用于移动止盈）
    - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.3_
  - [x] 5.2 编写监控列表属性测试
    - **Property 1: Stock Code Validation**
    - **Property 2: Watchlist Size Limit**
    - **Validates: Requirements 1.1, 1.3**

- [x] 6. 实现数据获取和刷新
  - [x] 6.1 创建 `core/realtime_monitor/data_fetcher.py`
    - 实现股票实时数据获取
    - 实现主力资金流向获取
    - 实现市场状态检测
    - _Requirements: 5.1, 5.2, 7.1, 7.2_
  - [x] 6.2 编写市场状态检测测试
    - **Property 11: Market Status Detection**
    - **Validates: Requirements 5.2**

- [x] 7. 实现交易建议生成
  - [x] 7.1 在 signal_engine.py 中添加交易建议
    - 实现买入信号价格计算（入场价、止损价、止盈价）
    - 实现卖出信号建议（紧急程度、操作建议）
    - _Requirements: 9.1, 9.2_
  - [x] 7.2 编写价格计算属性测试
    - **Property 14: Buy Signal Price Calculations**
    - **Validates: Requirements 9.1**

- [x] 8. Checkpoint - 后端功能完整性验证
  - 确保所有后端功能测试通过
  - 验证数据获取正常
  - 如有问题请询问用户

- [x] 9. 实现Streamlit界面
  - [x] 9.1 创建 `app/pages/9_📡_Realtime_Monitor.py`
    - 实现监控列表管理界面
    - 实现持仓输入界面
    - 实现信号展示面板
    - 实现技术指标面板
    - 实现自动刷新功能
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_
  - [x] 9.2 实现颜色映射和样式
    - 实现信号强度颜色映射
    - 实现资金流向颜色映射
    - 实现指标条件高亮
    - _Requirements: 6.2, 7.3, 7.4, 8.2, 8.3_
  - [x] 9.3 编写颜色映射测试
    - **Property 12: Signal Strength Color Mapping**
    - **Property 13: Fund Flow Color Mapping**
    - **Validates: Requirements 6.2, 7.3, 7.4**

- [x] 10. 集成测试和优化
  - [x] 10.1 编写集成测试
    - 测试完整的买入信号生成流程
    - 测试完整的卖出信号生成流程
    - 测试数据刷新机制
  - [x] 10.2 性能优化
    - 优化数据获取效率
    - 实现数据缓存
    - 优化界面刷新

- [x] 11. Final Checkpoint - 功能完整性验证
  - 确保所有测试通过
  - 验证界面功能正常
  - 如有问题请询问用户

## Notes

- All tasks are required for complete implementation
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- 使用 Python 3.8+ 和 hypothesis 库进行属性测试
- 使用 pytest 作为测试框架
