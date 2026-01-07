# Implementation Plan: 评分系统 v6.0

## Overview

将隔夜选股系统的评分策略从8维度升级为6维度，实现更符合A股短线实战的评分逻辑。

## Tasks

- [x] 1. 创建评分系统v6核心模块
  - [x] 1.1 创建 `core/overnight_picker/scorer_v6.py` 文件
    - 定义 `ScorerV6` 主类和权重配置
    - 定义 `ScoreResult` 和 `ScoreDimension` 数据类
    - _Requirements: 7.1, 7.2, 7.3_

  - [x] 1.2 实现 `TrendPositionScorer` 趋势与位置评分器
    - 实现均线排列判断逻辑
    - 实现乖离率计算
    - 实现价格分位点判断
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [ ]* 1.3 编写趋势位置评分属性测试
    - **Property 1: 趋势位置评分边界**
    - **Validates: Requirements 1.1, 1.4, 1.3**

- [x] 2. 实现K线与量价评分器
  - [x] 2.1 实现 `KLinePatternScorer` K线形态评分器
    - 实现涨停/反包/突破形态识别
    - 实现十字星/多方炮形态识别
    - 实现顶部形态识别
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [ ]* 2.2 编写K线形态评分属性测试
    - **Property 2: K线形态评分一致性**
    - **Validates: Requirements 2.1, 2.3, 2.5**

  - [x] 2.3 实现 `VolumePriceScorer` 量价配合评分器
    - 实现量比计算和分类
    - 实现换手率调整逻辑
    - 实现底部/突破位判断
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [ ]* 2.4 编写量价配合评分属性测试
    - **Property 3: 量价配合评分逻辑**
    - **Validates: Requirements 3.1, 3.3, 3.4**

- [x] 3. Checkpoint - 确保基础评分器测试通过
  - 运行已完成的属性测试
  - 确保所有测试通过，如有问题请询问用户

- [x] 4. 实现资金与题材评分器
  - [x] 4.1 实现 `CapitalStrengthScorer` 资金强度评分器
    - 实现净流入占比计算
    - 实现分档评分逻辑
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [ ]* 4.2 编写资金强度评分属性测试
    - **Property 4: 资金强度评分单调性**
    - **Validates: Requirements 4.1, 4.5**

  - [x] 4.3 实现 `ThemeWindScorer` 题材风口评分器
    - 实现题材匹配逻辑
    - 实现板块效应判断
    - 实现退潮期识别
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [ ]* 4.4 编写题材风口评分属性测试
    - **Property 5: 题材风口评分层级**
    - **Validates: Requirements 5.1, 5.4, 5.5**

- [x] 5. 实现股性活跃度与风险标记
  - [x] 5.1 实现 `StockActivityScorer` 股性活跃度评分器
    - 实现涨停记录检测
    - 实现波动率计算
    - 实现横盘检测
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [ ]* 5.2 编写股性活跃度评分属性测试
    - **Property 6: 股性活跃度评分**
    - **Validates: Requirements 6.1, 6.4**

  - [x] 5.3 实现 `RiskMarker` 风险标记器
    - 实现追高风险标记
    - 实现出货风险标记
    - 实现题材退潮风险标记
    - 实现股性差风险标记
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

  - [ ]* 5.4 编写风险标记属性测试
    - **Property 8: 风险标记完整性**
    - **Validates: Requirements 8.1, 8.2, 8.4, 8.5**

- [x] 6. Checkpoint - 确保所有评分器测试通过
  - 运行所有属性测试
  - 确保所有测试通过，如有问题请询问用户

- [x] 7. 集成与优化
  - [x] 7.1 实现 `ScorerV6.score_stock()` 综合评分方法
    - 调用所有子评分器
    - 汇总得分和风险标记
    - 生成评分摘要
    - _Requirements: 7.2, 7.4_

  - [ ]* 7.2 编写总分计算属性测试
    - **Property 7: 总分计算正确性**
    - **Validates: Requirements 7.2**

  - [x] 7.3 集成到 `OvernightStockPicker`
    - 修改 `picker.py` 使用新评分器
    - 保持接口兼容
    - 添加评分版本切换选项
    - _Requirements: 7.1_

  - [ ]* 7.4 编写集成测试
    - 测试与 OvernightStockPicker 的集成
    - 验证输出格式正确
    - _Requirements: 7.1, 7.5_

- [x] 8. 文档与收尾
  - [x] 8.1 更新使用指南文档
    - 更新 `docs/隔夜选股系统使用指南.md`
    - 说明新评分维度和权重
    - _Requirements: 7.4_

  - [x] 8.2 添加评分日志功能
    - 记录每次评分的详细信息
    - 支持回测分析
    - _Requirements: 7.5_

- [x] 9. Final Checkpoint - 确保所有测试通过
  - 运行完整测试套件
  - 确保所有测试通过，如有问题请询问用户

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
