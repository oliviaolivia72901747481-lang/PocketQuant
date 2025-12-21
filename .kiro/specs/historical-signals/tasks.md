# Implementation Plan: 历史信号模块

## Overview

本实现计划将历史信号模块分解为可执行的编码任务。采用增量开发方式，每个任务构建在前一个任务的基础上。

技术栈：Python 3.10+, Pandas, Streamlit, pytest, hypothesis

## Tasks

- [x] 1. Signal Store 模块实现
  - [x] 1.1 创建 `core/signal_store.py` 基础结构
    - 定义 `SignalRecord` 数据类
    - 定义 `SignalStore` 类和 CSV 列常量
    - 实现 `__init__()` 和 `_ensure_file_exists()` 方法
    - _Requirements: 1.4_
  - [x] 1.2 实现信号保存功能（幂等覆盖更新）
    - 实现 `save_signals()` 方法
    - 读取现有数据 → 删除该日期旧数据 → 追加新数据 → 写回文件
    - _Requirements: 1.1, 1.2, 1.3, 1.5_
  - [x] 1.3 实现信号加载和筛选功能
    - 实现 `load_signals()` 方法
    - 支持日期范围、股票代码、信号类型筛选
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_
  - [x] 1.4 实现统计和导出功能
    - 实现 `get_statistics()` 方法
    - 实现 `export_csv()` 方法
    - _Requirements: 4.2, 4.3, 4.4, 5.2_
  - [ ]* 1.5 编写 Signal Store 属性测试
    - **Property 1: 保存-读取 Round-Trip**
    - **Property 2: 幂等覆盖更新**
    - **Property 3: 筛选结果正确性**
    - **Property 4: 统计计算正确性**
    - **Property 5: 导出 Round-Trip**
    - **Validates: Requirements 1.1-1.5, 2.2-2.4, 4.2-4.4, 5.2**

- [x] 2. Checkpoint - Signal Store 验证
  - 确保所有 Signal Store 测试通过，ask the user if questions arise

- [x] 3. 历史信号 UI 实现
  - [x] 3.1 在 `app/pages/3_Daily_Signal.py` 添加信号保存逻辑
    - 在"生成今日信号"按钮点击后，调用 `SignalStore.save_signals()` 保存信号
    - 保持 SignalGenerator 纯净，保存逻辑由 UI 层触发
    - _Requirements: 1.1_
  - [x] 3.2 添加历史信号区域和筛选条件
    - 实现 `render_historical_signals()` 函数
    - 添加筛选条件 UI（日期范围、股票代码、信号类型）
    - _Requirements: 2.1, 2.2, 2.3, 2.4_
  - [x] 3.3 实现统计概览和信号表格
    - 实现统计指标卡片（总信号数、买入/卖出数、涉及股票数）
    - 实现 `render_signal_table()` 函数，使用 `st.dataframe` + `column_config`
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 4.3, 4.4_
  - [x] 3.4 实现导出功能
    - 添加"导出 CSV"下载按钮
    - _Requirements: 5.1, 5.2_

- [x] 4. Final Checkpoint - 集成测试
  - 确保端到端流程：生成信号 → 自动保存 → 历史查询 → 导出
  - ask the user if questions arise

## Notes

- 任务标记 `*` 为可选测试任务，可跳过以加快 MVP 开发
- 每个属性测试引用设计文档中的 Property 编号
- Checkpoint 任务用于阶段性验证
- 属性测试使用 hypothesis 库，每个测试至少运行 100 次迭代
