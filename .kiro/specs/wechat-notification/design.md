# Design Document: WeChat Notification

## Overview

微信通知功能通过企业微信群机器人 Webhook 实现交易信号的即时推送。系统采用轻量级设计，无需复杂的认证流程，用户只需配置 Webhook URL 即可使用。

核心设计原则：
- **简单可靠**：使用标准 HTTP POST，无第三方依赖
- **优雅降级**：网络失败自动重试，最终失败不影响主流程
- **风控优先**：消息包含财报窗口期、高费率等风险警告
- **用户友好**：Markdown 格式消息，清晰易读
- **配置持久化**：配置保存到本地文件，重启不丢失

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                       Daily Signal Page                              │
│  ┌─────────────────┐    ┌───────────────────────────────────────┐   │
│  │ Signal Generator │───▶│ Notification Settings Expander        │   │
│  └────────┬────────┘    │  - Webhook URL input (masked display) │   │
│           │             │  - Enable/Disable toggle              │   │
│           ▼             │  - Buy/Sell notification options      │   │
│  ┌─────────────────┐    │  - Test button                        │   │
│  │ Trading Signals │    └───────────────────────────────────────┘   │
│  └────────┬────────┘                                                │
└───────────┼─────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    NotificationService                               │
│  ┌──────────────────────┐    ┌────────────────────────────────────┐ │
│  │ NotificationConfig   │    │ format_signal()                    │ │
│  │ Store (JSON file)    │    │  - 包含风控警告                     │ │
│  └──────────────────────┘    │  - 区分挂单价/收盘价                │ │
│                              │ format_summary()                    │ │
│  ┌──────────────────────┐    │  - 信号计数                        │ │
│  │ Config Persistence   │    │  - 警告图标                        │ │
│  │ data/notification_   │    └────────────────────────────────────┘ │
│  │ config.json          │                                           │
│  └──────────────────────┘    ┌────────────────────────────────────┐ │
│                              │ _send_with_retry()                 │ │
│                              │  - HTTP POST to webhook            │ │
│                              │  - 10s timeout per request         │ │
│                              │  - 3 retries, 2s interval          │ │
│                              └────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                Enterprise WeChat Bot (External)                      │
│  Webhook URL: https://qyapi.weixin.qq.com/cgi-bin/webhook/          │
│               send?key=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx         │
└─────────────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. NotificationConfig (core/notification.py)

```python
@dataclass
class NotificationConfig:
    """
    通知配置数据类
    
    Validates: Requirements 1.1
    """
    webhook_url: str = ""                 # 企业微信 Webhook URL
    enabled: bool = False                 # 是否启用通知
    notify_on_buy: bool = True            # 买入信号通知
    notify_on_sell: bool = True           # 卖出信号通知
    timeout: int = 10                     # HTTP 请求超时（秒）
    max_retries: int = 3                  # 最大重试次数
    retry_interval: int = 2               # 重试间隔（秒）
```

### 2. NotificationConfigStore (core/notification.py)

```python
class NotificationConfigStore:
    """
    通知配置持久化存储
    
    Validates: Requirements 1.3, 1.5, 1.6, 4.2, 4.3, 4.7
    """
    CONFIG_FILE = "data/notification_config.json"
    
    @classmethod
    def load(cls) -> NotificationConfig:
        """
        从文件加载配置
        
        优先级：
        1. 本地配置文件 (data/notification_config.json)
        2. 环境变量 WECHAT_WEBHOOK_URL
        3. 默认空配置
        
        Validates: Requirements 1.3, 1.6
        """
        
    @classmethod
    def save(cls, config: NotificationConfig) -> bool:
        """
        保存配置到文件
        
        Validates: Requirements 1.5, 4.2
        """
        
    @classmethod
    def mask_webhook_url(cls, url: str) -> str:
        """
        脱敏显示 webhook URL
        
        示例: https://qyapi.weixin.qq.com/...xy12
        
        Validates: Requirements 4.7
        """
```

### 3. NotificationService (core/notification.py)

```python
class NotificationService:
    """
    微信通知服务
    
    Validates: Requirements 2.*, 3.*, 5.*
    """
    
    def __init__(self, config: NotificationConfig):
        """初始化通知服务"""
        self.config = config
        
    def send_signal_notification(self, signals: List[TradingSignal]) -> bool:
        """
        发送交易信号通知
        
        流程：
        1. 检查是否启用 (Requirements 1.4)
        2. 检查 webhook_url 是否有效 (Requirements 1.2)
        3. 过滤信号类型 (Requirements 5.2)
        4. 格式化消息 (Requirements 2.*)
        5. 发送通知 (Requirements 3.*)
        
        Returns:
            True 发送成功，False 发送失败或跳过
        """
        
    def send_test_notification(self) -> Tuple[bool, str]:
        """
        发送测试通知
        
        Validates: Requirements 4.4, 4.5, 4.6
        
        Returns:
            (成功, 消息) - 成功时消息为空，失败时包含错误详情
        """
        
    def format_signal(self, signal: TradingSignal) -> str:
        """
        格式化单个信号为 Markdown
        
        包含：
        - 股票代码、名称
        - 买入：建议挂单价 + 参考收盘价 (Requirements 2.1)
        - 卖出：参考价格 (Requirements 2.2)
        - 信号原因
        - 风控警告 (Requirements 2.6, 2.7)
        - 时间戳 (Requirements 2.4)
        - 操作提醒 (Requirements 2.8)
        """
        
    def format_summary(self, signals: List[TradingSignal]) -> str:
        """
        格式化信号摘要为 Markdown
        
        Validates: Requirements 2.3, 2.4, 2.5, 2.8
        """
        
    def _filter_signals(self, signals: List[TradingSignal]) -> List[TradingSignal]:
        """
        根据配置过滤信号类型
        
        Validates: Requirements 5.2
        """
        
    def _send_with_retry(self, content: str) -> Tuple[bool, str]:
        """
        带重试机制的发送
        
        Validates: Requirements 3.2, 3.3, 3.4, 3.5
        
        重试策略：
        - 最多重试 3 次
        - 每次间隔 2 秒
        - 超时 10 秒/次
        """
```

### 4. UI Integration (app/pages/3_Daily_Signal.py)

```python
def render_notification_settings():
    """
    渲染通知配置面板
    
    Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7
    """
    with st.expander("🔔 微信通知设置", expanded=False):
        # 加载已保存配置 (Requirements 4.3)
        config = NotificationConfigStore.load()
        
        # Webhook URL 输入（脱敏显示）(Requirements 4.7)
        webhook_url = st.text_input(
            "Webhook URL",
            value=config.webhook_url,
            type="password",  # 密码框形式
            help="企业微信群机器人 Webhook 地址"
        )
        
        # 启用开关
        enabled = st.checkbox("启用微信通知", value=config.enabled)
        
        # 买入/卖出通知选项
        col1, col2 = st.columns(2)
        with col1:
            notify_on_buy = st.checkbox("买入信号通知", value=config.notify_on_buy)
        with col2:
            notify_on_sell = st.checkbox("卖出信号通知", value=config.notify_on_sell)
        
        # 保存按钮 (Requirements 4.2)
        if st.button("💾 保存配置"):
            new_config = NotificationConfig(
                webhook_url=webhook_url,
                enabled=enabled,
                notify_on_buy=notify_on_buy,
                notify_on_sell=notify_on_sell
            )
            NotificationConfigStore.save(new_config)
            st.success("配置已保存")
        
        # 测试按钮 (Requirements 4.4, 4.5, 4.6)
        if st.button("🔔 发送测试通知"):
            service = NotificationService(config)
            success, message = service.send_test_notification()
            if success:
                st.success("✅ 测试通知发送成功！")
            else:
                st.error(f"❌ 发送失败: {message}")


def auto_send_notification(signals: List[TradingSignal]):
    """
    自动发送通知（信号生成后调用）
    
    Validates: Requirements 5.1, 5.3
    """
    config = NotificationConfigStore.load()
    
    if not config.enabled:
        return
    
    if not signals:  # Requirements 5.3
        return
    
    service = NotificationService(config)
    service.send_signal_notification(signals)
```

## Data Models

### 配置文件格式 (data/notification_config.json)

```json
{
    "webhook_url": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx",
    "enabled": true,
    "notify_on_buy": true,
    "notify_on_sell": true,
    "timeout": 10,
    "max_retries": 3,
    "retry_interval": 2
}
```

### 企业微信 Webhook 请求格式

```json
{
    "msgtype": "markdown",
    "markdown": {
        "content": "# 📊 MiniQuant 交易信号\n\n**买入信号**\n- 股票: 000001 平安银行\n- 挂单价: ¥12.50\n- 原因: RSI超卖反弹"
    }
}
```

### 消息模板

**单个买入信号 (Requirements 2.1, 2.6, 2.7, 2.8)：**
```markdown
# � MMiniQuant 买入信号

**股票**: {code} {name}
**建议挂单价**: ¥{limit_cap}
**参考收盘价**: ¥{close_price}
**信号原因**: {reason}

{warnings}

**生成时间**: {timestamp}

> ⚠️ 请务必在 PC 端确认新闻面及公告后操作
```

**单个卖出信号 (Requirements 2.2, 2.6, 2.7, 2.8)：**
```markdown
# 📉 MiniQuant 卖出信号

**股票**: {code} {name}
**参考价格**: ¥{price}
**信号原因**: {reason}

{warnings}

**生成时间**: {timestamp}

> ⚠️ 请务必在 PC 端确认后操作
```

**风控警告格式 (Requirements 2.6, 2.7)：**
```markdown
⚠️ **财报窗口期**: {report_warning}
⚠️ **高费率预警**: 实际费率 {fee_rate:.2%}，建议增加交易金额
```

**多信号摘要 (Requirements 2.3, 2.4, 2.5, 2.8)：**
```markdown
# 📊 MiniQuant 信号汇总

**买入信号**: {buy_count} 个
**卖出信号**: {sell_count} 个

## 买入
- {code1} {name1} 挂单价 ¥{price1} {warning_icon}
- {code2} {name2} 挂单价 ¥{price2}

## 卖出
- {code3} {name3}

**生成时间**: {timestamp}

> ⚠️ 请务必在 PC 端确认新闻面及公告后操作
```

**测试通知消息：**
```markdown
# 🔔 MiniQuant 测试通知

恭喜！微信通知配置成功 ✅

您将在以下情况收到通知：
- 买入信号: {notify_on_buy}
- 卖出信号: {notify_on_sell}

**测试时间**: {timestamp}
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Empty webhook skips notification

*For any* notification attempt with empty or None webhook_url, the send_signal_notification method SHALL return False without raising any exception.

**Validates: Requirements 1.2**

### Property 2: Disabled service skips notification

*For any* notification attempt when enabled is False, the send_signal_notification method SHALL return False without making any HTTP request.

**Validates: Requirements 1.4**

### Property 3: Config persistence round-trip

*For any* valid NotificationConfig, saving then loading SHALL produce an equivalent configuration object.

**Validates: Requirements 1.5, 1.6**

### Property 4: Signal formatting contains required fields

*For any* TradingSignal with signal_type BUY, the formatted message SHALL contain the stock code, stock name, limit_cap (挂单价), close_price (收盘价), and reason. *For any* TradingSignal with signal_type SELL, the formatted message SHALL contain the stock code, stock name, price, and reason.

**Validates: Requirements 2.1, 2.2**

### Property 5: Risk warnings included when applicable

*For any* TradingSignal with in_report_window=True, the formatted message SHALL contain "财报窗口期" warning. *For any* TradingSignal with high_fee_warning=True, the formatted message SHALL contain "高费率预警" warning.

**Validates: Requirements 2.6, 2.7**

### Property 6: Summary contains signal count

*For any* non-empty list of signals, the formatted summary SHALL contain the correct count of buy and sell signals matching the actual counts in the list.

**Validates: Requirements 2.3**

### Property 7: Message format requirements

*For any* formatted notification message, it SHALL contain a timestamp, use markdown syntax (headers with #, bold with **), and include the operation reminder "请务必在 PC 端确认".

**Validates: Requirements 2.4, 2.5, 2.8**

### Property 8: Signal type filtering

*For any* list of signals, when notify_on_buy is False, the filtered list SHALL contain no BUY signals; when notify_on_sell is False, the filtered list SHALL contain no SELL signals.

**Validates: Requirements 5.2**

### Property 9: Webhook URL masking

*For any* webhook URL with length > 4, the masked URL SHALL show only the last 4 characters of the key portion, with the rest replaced by asterisks or ellipsis.

**Validates: Requirements 4.7**

## Error Handling

| 场景 | 处理方式 |
|------|----------|
| Webhook URL 为空 | 静默跳过，返回 False |
| 通知已禁用 | 静默跳过，返回 False |
| HTTP 请求超时 | 重试最多 3 次，间隔 2 秒 |
| HTTP 非 200 响应 | 重试最多 3 次，记录响应内容 |
| 网络连接失败 | 重试最多 3 次，记录异常 |
| 所有重试失败 | 记录错误日志，返回 False |
| 信号列表为空 | 不发送通知，返回 True |
| 配置文件不存在 | 使用默认配置，尝试从环境变量读取 |
| 配置文件损坏 | 使用默认配置，记录警告 |

关键原则：**通知失败不应影响主流程**，所有错误都应被捕获并记录。

## Testing Strategy

### Unit Tests

1. **NotificationConfig 测试**
   - 验证默认值
   - 验证字段类型

2. **NotificationConfigStore 测试**
   - 保存配置到文件
   - 从文件加载配置
   - 环境变量回退
   - 文件不存在时的处理
   - URL 脱敏显示

3. **消息格式化测试**
   - 买入信号格式化（包含挂单价、收盘价）
   - 卖出信号格式化
   - 风控警告格式化
   - 多信号摘要格式化
   - 空信号列表处理

4. **信号过滤测试**
   - notify_on_buy=False 时过滤买入信号
   - notify_on_sell=False 时过滤卖出信号

5. **错误处理测试**
   - 空 webhook URL
   - 禁用状态
   - HTTP 错误响应（使用 mock）
   - 重试机制验证

### Property-Based Tests

使用 Hypothesis 库进行属性测试：

1. **Property 1**: 空 webhook 测试
2. **Property 3**: 配置持久化往返测试
3. **Property 4**: 信号格式化包含必要字段
4. **Property 5**: 风控警告包含测试
5. **Property 6**: 摘要包含正确计数
6. **Property 7**: 消息格式要求
7. **Property 8**: 信号类型过滤
8. **Property 9**: URL 脱敏测试

测试配置：
- 最少 100 次迭代
- 使用 `@given` 装饰器生成随机信号数据
- 使用 `@example` 装饰器覆盖边界情况
