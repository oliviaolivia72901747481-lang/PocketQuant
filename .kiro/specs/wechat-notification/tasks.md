# Implementation Plan: WeChat Notification

## Overview

实现企业微信通知功能，包括配置管理、消息格式化、HTTP 发送（带重试）、UI 集成和自动触发。

## Tasks

- [x] 1. 创建通知配置和持久化模块
  - [x] 1.1 创建 NotificationConfig 数据类
    - 定义 webhook_url, enabled, notify_on_buy, notify_on_sell, timeout, max_retries, retry_interval 字段
    - _Requirements: 1.1_
  - [x] 1.2 实现 NotificationConfigStore 类
    - 实现 load() 方法：从 JSON 文件加载，支持环境变量回退
    - 实现 save() 方法：保存到 data/notification_config.json
    - 实现 mask_webhook_url() 方法：脱敏显示 URL
    - _Requirements: 1.3, 1.5, 1.6, 4.7_
  - [x] 1.3 编写配置持久化单元测试

    - 测试保存和加载往返
    - 测试环境变量回退
    - 测试 URL 脱敏
    - _Requirements: 1.3, 1.5, 1.6, 4.7_

- [x] 2. 实现消息格式化功能
  - [x] 2.1 实现 format_signal() 方法
    - 买入信号：包含挂单价、收盘价、原因
    - 卖出信号：包含参考价格、原因
    - 包含风控警告（财报窗口期、高费率）
    - 包含时间戳和操作提醒
    - _Requirements: 2.1, 2.2, 2.4, 2.5, 2.6, 2.7, 2.8_
  - [x] 2.2 实现 format_summary() 方法
    - 统计买入/卖出信号数量
    - 列出所有信号简要信息
    - 包含警告图标
    - _Requirements: 2.3, 2.4, 2.5, 2.8_
  - [x] 2.3 编写消息格式化单元测试

    - 测试买入信号格式化
    - 测试卖出信号格式化
    - 测试风控警告包含
    - 测试摘要格式化
    - _Requirements: 2.1, 2.2, 2.3, 2.6, 2.7_

- [x] 3. 实现 HTTP 发送功能（带重试）
  - [x] 3.1 实现 _send_with_retry() 方法
    - HTTP POST 请求到 webhook_url
    - 10 秒超时
    - 失败重试 3 次，间隔 2 秒
    - 记录错误日志
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_
  - [x] 3.2 实现 send_signal_notification() 方法
    - 检查 enabled 和 webhook_url
    - 过滤信号类型
    - 格式化并发送消息
    - _Requirements: 1.2, 1.4, 5.1, 5.2, 5.3_
  - [x] 3.3 实现 send_test_notification() 方法
    - 发送测试消息
    - 返回成功/失败状态和详情
    - _Requirements: 4.4, 4.5, 4.6_
  - [x] 3.4 编写 HTTP 发送单元测试（使用 mock）

    - 测试成功发送
    - 测试重试机制
    - 测试超时处理
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 4. Checkpoint - 核心功能测试
  - 运行所有单元测试确保通过
  - 如有问题请询问用户

- [x] 5. UI 集成
  - [x] 5.1 实现 render_notification_settings() 函数
    - 添加通知设置 expander
    - Webhook URL 输入（密码框形式）
    - 启用开关和买入/卖出选项
    - 保存配置按钮
    - 测试通知按钮
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7_
  - [x] 5.2 集成自动通知触发
    - 在信号生成后调用 auto_send_notification()
    - 检查 enabled 状态
    - 空信号时不发送
    - _Requirements: 5.1, 5.2, 5.3_

- [x] 6. Final Checkpoint - 完整功能测试
  - 运行所有测试确保通过
  - 手动测试 UI 功能
  - 验证配置持久化
  - 如有问题请询问用户

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- HTTP 发送测试使用 mock 避免实际网络请求
