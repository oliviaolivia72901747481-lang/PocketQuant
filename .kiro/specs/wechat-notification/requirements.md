# Requirements Document

## Introduction

微信通知功能允许用户在交易信号生成时通过企业微信机器人接收即时通知，确保不错过重要的买卖时机。该功能使用企业微信 Webhook 方式推送消息，配置简单，无需复杂的认证流程。

## Glossary

- **Webhook**: 一种 HTTP 回调机制，允许应用程序通过 HTTP POST 请求向指定 URL 发送数据
- **Enterprise_WeChat_Bot**: 企业微信群机器人，可通过 Webhook URL 接收并转发消息到群聊
- **Notification_Service**: 负责格式化和发送通知消息的服务模块
- **Signal**: 交易信号，包含股票代码、买卖方向、价格等信息

## Requirements

### Requirement 1: 配置管理

**User Story:** As a user, I want to configure WeChat notification settings, so that I can receive trading signals on my phone.

#### Acceptance Criteria

1. THE Settings SHALL include a NotificationConfig dataclass with webhook_url, enabled, and notify_on_buy/notify_on_sell fields
2. WHEN webhook_url is empty or None, THE Notification_Service SHALL skip sending notifications without raising errors
3. THE System SHALL support reading webhook_url from environment variable WECHAT_WEBHOOK_URL as fallback
4. WHEN enabled is False, THE Notification_Service SHALL skip all notifications
5. THE System SHALL persist notification config to local file (data/notification_config.json)
6. WHEN the application starts, THE System SHALL load saved config from local file

### Requirement 2: 消息格式化

**User Story:** As a user, I want notifications to be clear and actionable, so that I can quickly understand the trading signal.

#### Acceptance Criteria

1. THE Notification_Service SHALL format buy signals with stock code, name, limit cap (挂单价), close price (参考收盘价), and reason
2. THE Notification_Service SHALL format sell signals with stock code, name, current price, and reason
3. WHEN multiple signals exist, THE Notification_Service SHALL send a summary message with signal count and key details
4. THE Notification_Service SHALL include timestamp in all notification messages
5. THE Notification_Service SHALL use markdown format for better readability in WeChat
6. WHEN a signal has report_window warning, THE Notification_Service SHALL include ⚠️ 财报窗口期 warning prominently
7. WHEN a signal has high_fee_warning, THE Notification_Service SHALL include ⚠️ 高费率预警 warning
8. THE Notification_Service SHALL append "请务必在 PC 端确认新闻面及公告后操作" reminder at message end

### Requirement 3: 消息发送

**User Story:** As a user, I want notifications to be sent reliably, so that I don't miss important signals.

#### Acceptance Criteria

1. WHEN a trading signal is generated, THE Notification_Service SHALL send HTTP POST request to webhook_url
2. IF the HTTP request fails, THEN THE Notification_Service SHALL retry up to 3 times with 2 second intervals
3. IF all retries fail, THEN THE Notification_Service SHALL log the error and return False without crashing
4. THE Notification_Service SHALL set a timeout of 10 seconds for each HTTP request
5. WHEN the webhook returns non-200 status, THE Notification_Service SHALL log the response and retry

### Requirement 4: UI 集成

**User Story:** As a user, I want to configure notifications through the UI, so that I don't need to edit config files.

#### Acceptance Criteria

1. THE Daily_Signal page SHALL include a notification settings expander
2. WHEN user enters webhook_url in UI, THE System SHALL save it to local config file for persistence
3. WHEN the page loads, THE System SHALL read saved config and pre-fill the webhook_url field
4. THE UI SHALL provide a "Test Notification" button to verify webhook configuration
5. WHEN test notification succeeds, THE UI SHALL display success message
6. IF test notification fails, THEN THE UI SHALL display error details
7. THE UI SHALL mask webhook_url display (show only last 4 characters) for privacy protection

### Requirement 5: 自动通知触发

**User Story:** As a user, I want notifications to be sent automatically when signals are generated, so that I receive timely alerts.

#### Acceptance Criteria

1. WHEN signals are generated on Daily_Signal page, THE System SHALL automatically send notification if enabled
2. THE System SHALL only notify for signal types that user has enabled (buy/sell)
3. WHEN no signals are generated, THE System SHALL NOT send any notification
