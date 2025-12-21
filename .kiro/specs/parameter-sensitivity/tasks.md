# Implementation Plan: 参数敏感性分析模块

## Overview

将参数敏感性分析功能集成到回测页面，实现参数网格搜索、热力图可视化和鲁棒性自动诊断。采用渐进式实现，先完成核心计算逻辑，再添加 UI 交互。

## Tasks

- [x] 1. 创建核心数据结构和参数网格模块
  - [x] 1.1 创建 `core/parameter_sensitivity.py` 文件，实现 ParameterRange 和 ParameterGrid 数据类
    - 实现 `get_x_values()`, `get_y_values()`, `get_total_combinations()`, `validate()` 方法
    - 添加策略参数配置映射 `STRATEGY_PARAM_CONFIGS`
    - _Requirements: 1.1, 1.2, 1.3, 1.4_
  - [ ]* 1.2 编写 Property 1 和 Property 2 的属性测试
    - **Property 1: 参数网格验证**
    - **Property 2: 组合数计算正确性**
    - **Validates: Requirements 1.3, 1.4**

- [x] 2. 实现网格搜索执行器
  - [x] 2.1 在 `core/parameter_sensitivity.py` 中实现 CellResult 和 GridSearchResult 数据类
    - 实现 `get_return_matrix()`, `get_optimal_cell()` 方法
    - _Requirements: 2.4, 4.6_
  - [x] 2.2 实现 GridSearcher 类
    - 复用现有 BacktestEngine 执行单次回测
    - 支持进度回调函数
    - 处理单个回测失败（记录错误，继续执行）
    - _Requirements: 2.1, 2.2, 2.3, 2.5_
  - [ ]* 2.3 编写 Property 3 和 Property 4 的属性测试
    - **Property 3: 网格搜索完整性**
    - **Property 4: 结果矩阵维度一致性**
    - **Validates: Requirements 2.1, 2.3, 2.4**

- [x] 3. 实现鲁棒性诊断器
  - [x] 3.1 在 `core/parameter_sensitivity.py` 中实现 DiagnosisResult 数据类和 RobustnessDiagnostics 类
    - 实现评分算法：正收益占比(40分) + 稳定性(30分) + 邻近一致性(30分)
    - 实现等级映射：>=70 robust, 40-70 sensitive, <40 overfitting
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_
  - [ ]* 3.2 编写 Property 5 和 Property 6 的属性测试
    - **Property 5: 鲁棒性评分边界**
    - **Property 6: 最优参数查找正确性**
    - **Validates: Requirements 4.1, 4.3, 4.4, 4.5, 4.6**

- [x] 4. 实现热力图渲染器
  - [x] 4.1 在 `core/parameter_sensitivity.py` 中实现 HeatmapRenderer 类
    - 使用 Plotly 生成热力图
    - 实现红绿色阶映射（绿=亏损，红=盈利）
    - 支持高亮当前参数点
    - 支持切换显示指标（收益率/胜率/回撤）
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_
  - [ ]* 4.2 编写 Property 7 的单元测试
    - **Property 7: 热力图颜色映射**
    - **Validates: Requirements 3.2**

- [x] 5. Checkpoint - 核心模块测试
  - 确保所有属性测试通过
  - 确保核心计算逻辑正确
  - 如有问题，询问用户

- [x] 6. 集成到回测页面 UI
  - [x] 6.1 在 `app/pages/2_Backtest.py` 中添加"参数敏感性分析"折叠面板
    - 添加参数范围配置 UI（横轴参数、纵轴参数、范围、步长）
    - 显示总组合数和耗时预估
    - 添加"开始分析"按钮
    - _Requirements: 1.1, 1.2, 1.5_
  - [x] 6.2 实现网格搜索执行和进度显示
    - 显示进度条和当前测试参数
    - 显示完成统计（成功/失败/耗时）
    - _Requirements: 2.2, 2.5_
  - [x] 6.3 实现热力图展示和交互
    - 渲染热力图
    - 添加指标切换下拉框
    - 显示鲁棒性诊断结果（评分 + 等级 + 建议）
    - 显示最优参数组合
    - _Requirements: 3.1, 3.3, 3.5, 4.3, 4.4, 4.5, 4.6_
  - [x] 6.4 实现"应用最优参数"功能
    - 点击按钮后自动填充参数到回测配置
    - _Requirements: 5.2_

- [x] 7. Final Checkpoint - 集成测试
  - 端到端测试：参数配置 → 网格搜索 → 热力图 → 诊断
  - 确保 UI 交互流畅
  - 如有问题，询问用户

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- 核心模块 (`core/parameter_sensitivity.py`) 与 UI 层分离，便于测试
- 复用现有 BacktestEngine，不重复实现回测逻辑
- 热力图使用 Plotly，与现有图表风格一致
- 限制最大组合数为 200，避免长时间阻塞

