# Requirements Document

## Introduction

参数敏感性分析模块，用于评估量化策略的鲁棒性。通过在参数空间内进行网格搜索，生成热力图展示策略在不同参数组合下的表现，帮助用户识别"参数高原"（稳健区域）与"过拟合孤岛"（脆弱区域）。

核心价值：将回测从"单次点估计"升级为"参数空间面估计"，让小散户能直观判断策略是"真有效"还是"蒙的"。

## Glossary

- **Parameter_Sensitivity_Analyzer**: 参数敏感性分析器，负责执行网格搜索和生成热力图
- **Heatmap_Renderer**: 热力图渲染器，负责将分析结果可视化
- **Parameter_Grid**: 参数网格，定义待测试的参数组合空间
- **Robustness_Score**: 鲁棒性评分，衡量策略在参数空间内的稳定性
- **Parameter_Plateau**: 参数高原，指策略表现稳定的参数区域（红色区域）
- **Overfitting_Island**: 过拟合孤岛，指策略表现孤立的参数点（孤零零的红点）

## Requirements

### Requirement 1: 参数网格定义

**User Story:** As a 小散户, I want to 定义要测试的参数范围和步长, so that 我可以探索策略在不同参数下的表现。

#### Acceptance Criteria

1. WHEN 用户选择"趋势滤网 MACD 策略" THEN THE Parameter_Grid SHALL 提供 MA 周期（40-80，步长5）和 RSI 上限（70-90，步长5）的默认范围
2. WHEN 用户选择"RSI 超卖反弹策略" THEN THE Parameter_Grid SHALL 提供买入阈值（20-40，步长5）和卖出阈值（60-80，步长5）的默认范围
3. WHEN 用户修改参数范围 THEN THE Parameter_Grid SHALL 验证范围有效性（最小值<最大值，步长>0）
4. THE Parameter_Grid SHALL 计算并显示总测试组合数（横轴点数 × 纵轴点数）
5. IF 总测试组合数超过100 THEN THE Parameter_Sensitivity_Analyzer SHALL 显示警告"测试组合较多，预计耗时较长"

### Requirement 2: 网格搜索执行

**User Story:** As a 小散户, I want to 对选定的参数空间进行批量回测, so that 我可以获得每个参数组合的收益率数据。

#### Acceptance Criteria

1. WHEN 用户点击"开始分析"按钮 THEN THE Parameter_Sensitivity_Analyzer SHALL 遍历所有参数组合执行回测
2. WHILE 网格搜索执行中 THEN THE Parameter_Sensitivity_Analyzer SHALL 显示进度条和当前测试的参数组合
3. WHEN 单个回测失败 THEN THE Parameter_Sensitivity_Analyzer SHALL 记录失败原因并继续执行下一个组合
4. THE Parameter_Sensitivity_Analyzer SHALL 将每个参数组合的回测结果（总收益率、胜率、最大回撤）存储到结果矩阵
5. WHEN 网格搜索完成 THEN THE Parameter_Sensitivity_Analyzer SHALL 显示总耗时和成功/失败统计

### Requirement 3: 热力图可视化

**User Story:** As a 小散户, I want to 通过热力图直观看到参数敏感性, so that 我可以判断策略是否稳健。

#### Acceptance Criteria

1. WHEN 网格搜索完成 THEN THE Heatmap_Renderer SHALL 生成以横轴为第一参数、纵轴为第二参数、颜色深浅为收益率的热力图
2. THE Heatmap_Renderer SHALL 使用红绿色阶（绿色=亏损，红色=盈利，颜色越深收益越高）
3. THE Heatmap_Renderer SHALL 在热力图上标注当前使用的参数点位置（用星号或边框高亮）
4. WHEN 用户悬停在热力图单元格上 THEN THE Heatmap_Renderer SHALL 显示该参数组合的详细指标（收益率、胜率、回撤）
5. THE Heatmap_Renderer SHALL 支持切换显示指标（收益率/胜率/最大回撤）

### Requirement 4: 鲁棒性诊断

**User Story:** As a 小散户, I want to 获得策略鲁棒性的自动诊断, so that 我不需要自己解读热力图。

#### Acceptance Criteria

1. WHEN 热力图生成完成 THEN THE Parameter_Sensitivity_Analyzer SHALL 计算鲁棒性评分（0-100分）
2. THE Robustness_Score SHALL 基于以下因素计算：正收益区域占比、收益率标准差、最优点与邻近点的差异
3. IF 鲁棒性评分 >= 70 THEN THE Parameter_Sensitivity_Analyzer SHALL 显示"🟢 参数高原：策略稳健，参数微调不影响表现"
4. IF 鲁棒性评分 >= 40 AND < 70 THEN THE Parameter_Sensitivity_Analyzer SHALL 显示"🟡 参数敏感：策略对参数有一定依赖，建议谨慎使用"
5. IF 鲁棒性评分 < 40 THEN THE Parameter_Sensitivity_Analyzer SHALL 显示"🔴 过拟合风险：策略表现高度依赖特定参数，可能是蒙的"
6. THE Parameter_Sensitivity_Analyzer SHALL 显示最优参数组合及其收益率

### Requirement 5: 用户交互与导出

**User Story:** As a 小散户, I want to 保存分析结果并应用最优参数, so that 我可以优化我的策略配置。

#### Acceptance Criteria

1. WHEN 用户点击热力图中的某个单元格 THEN THE Parameter_Sensitivity_Analyzer SHALL 显示该参数组合的完整回测报告
2. THE Parameter_Sensitivity_Analyzer SHALL 提供"应用最优参数"按钮，点击后自动填充到回测页面的参数配置
3. THE Parameter_Sensitivity_Analyzer SHALL 提供"导出分析报告"功能，生成包含热力图和诊断结论的 PNG 图片
4. WHEN 用户切换策略类型 THEN THE Parameter_Sensitivity_Analyzer SHALL 清空之前的分析结果并重置参数范围

