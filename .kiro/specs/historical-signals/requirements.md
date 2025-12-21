# Requirements Document

## Introduction

历史信号模块是 MiniQuant-Lite 系统的扩展功能，用于记录、存储和展示系统生成的历史交易信号。该模块帮助用户回顾过去的交易建议，为投资决策提供历史参考。

设计原则：**极简主义**
- 单文件存储，不搞分表
- 幂等写入，每日覆盖更新
- 原生 Streamlit 渲染，不搞复杂 HTML

## Glossary

- **Signal_Store**: 信号存储模块，负责将交易信号持久化到单一 CSV 文件
- **Historical_Signal_Viewer**: 历史信号查看器，在 Streamlit 界面中展示历史信号

## Requirements

### Requirement 1: 信号持久化存储

**User Story:** 作为个人投资者，我希望系统能够自动保存每次生成的交易信号，以便我日后回顾和分析。

#### Acceptance Criteria

1. WHEN 用户生成每日信号 THEN THE Signal_Store SHALL 将信号数据保存到 `data/signal_history.csv` 单一文件
2. THE Signal_Store SHALL 为每条信号记录保存以下字段：生成日期、股票代码、股票名称、信号类型、建议价格区间、限价上限、信号依据、是否财报窗口期、是否高费率预警、大盘状态
3. WHEN 同一天多次生成信号 THEN THE Signal_Store SHALL 先删除该日期的旧数据再写入新数据（幂等覆盖更新）
4. IF 信号文件不存在 THEN THE Signal_Store SHALL 自动创建文件并写入表头
5. THE Signal_Store SHALL 确保每个日期只保留最后一次生成的信号版本

### Requirement 2: 历史信号查询

**User Story:** 作为个人投资者，我希望能够按日期范围和股票代码查询历史信号，以便快速找到我关心的信号记录。

#### Acceptance Criteria

1. WHEN 用户访问历史信号页面 THEN THE Historical_Signal_Viewer SHALL 默认显示最近 30 天的信号记录
2. THE Historical_Signal_Viewer SHALL 支持按日期范围筛选信号
3. THE Historical_Signal_Viewer SHALL 支持按股票代码筛选信号
4. THE Historical_Signal_Viewer SHALL 支持按信号类型（买入/卖出）筛选信号
5. IF 没有符合条件的历史信号 THEN THE Historical_Signal_Viewer SHALL 显示"暂无历史信号记录"

### Requirement 3: 历史信号展示

**User Story:** 作为个人投资者，我希望能够清晰地查看历史信号的详细信息，以便分析过去的交易建议。

#### Acceptance Criteria

1. THE Historical_Signal_Viewer SHALL 使用 Streamlit 原生 `st.dataframe` 配合 `column_config` 展示历史信号表格
2. THE Historical_Signal_Viewer SHALL 在表格中显示：日期、股票代码、股票名称、信号类型、限价上限、信号依据
3. THE Historical_Signal_Viewer SHALL 对买入信号使用绿色标识，卖出信号使用红色标识
4. THE Historical_Signal_Viewer SHALL 对财报窗口期信号添加警告标识
5. THE Historical_Signal_Viewer SHALL 对高费率预警信号添加警告标识

### Requirement 4: 信号统计概览

**User Story:** 作为个人投资者，我希望能够看到历史信号的统计概览，以便了解系统的信号生成情况。

#### Acceptance Criteria

1. THE Historical_Signal_Viewer SHALL 在页面顶部显示统计指标卡片
2. THE Historical_Signal_Viewer SHALL 显示当前筛选结果的总信号数量
3. THE Historical_Signal_Viewer SHALL 分别显示买入信号和卖出信号的数量
4. THE Historical_Signal_Viewer SHALL 显示涉及的股票数量

### Requirement 5: 信号导出功能

**User Story:** 作为个人投资者，我希望能够导出历史信号数据，以便在其他工具中进行分析。

#### Acceptance Criteria

1. THE Historical_Signal_Viewer SHALL 提供"导出 CSV"按钮
2. WHEN 用户点击导出按钮 THEN THE System SHALL 生成包含当前筛选结果的 CSV 文件供下载

