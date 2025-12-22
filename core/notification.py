"""
MiniQuant-Lite 飞书通知模块

通过飞书群机器人 Webhook 实现交易信号的即时推送。

功能：
- 配置管理和持久化
- 消息格式化（Markdown）
- HTTP 发送（带重试机制）
- 风控警告集成

Requirements: 1.*, 2.*, 3.*, 5.*
"""

import json
import logging
import os
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import List, Tuple, Optional
from pathlib import Path

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# 配置日志
logger = logging.getLogger(__name__)


# ==========================================
# 配置数据类
# ==========================================

@dataclass
class NotificationConfig:
    """
    通知配置数据类
    
    Validates: Requirements 1.1
    """
    webhook_url: str = ""                 # 飞书 Webhook URL
    enabled: bool = False                 # 是否启用通知
    notify_on_buy: bool = True            # 买入信号通知
    notify_on_sell: bool = True           # 卖出信号通知
    timeout: int = 10                     # HTTP 请求超时（秒）
    max_retries: int = 3                  # 最大重试次数
    retry_interval: int = 2               # 重试间隔（秒）


# ==========================================
# 配置持久化
# ==========================================

class NotificationConfigStore:
    """
    通知配置持久化存储
    
    Validates: Requirements 1.3, 1.5, 1.6, 4.7
    """
    CONFIG_FILE = "data/notification_config.json"
    ENV_VAR_NAME = "FEISHU_WEBHOOK_URL"
    
    @classmethod
    def _get_config_path(cls) -> Path:
        """获取配置文件路径"""
        # 获取项目根目录
        base_dir = Path(__file__).parent.parent
        return base_dir / cls.CONFIG_FILE
    
    @classmethod
    def load(cls) -> NotificationConfig:
        """
        从文件加载配置
        
        优先级：
        1. 本地配置文件 (data/notification_config.json)
        2. 环境变量 FEISHU_WEBHOOK_URL
        3. 默认空配置
        
        Validates: Requirements 1.3, 1.6
        """
        config_path = cls._get_config_path()
        
        # 尝试从文件加载
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return NotificationConfig(**data)
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"配置文件损坏，使用默认配置: {e}")
        
        # 尝试从环境变量加载
        env_webhook = os.environ.get(cls.ENV_VAR_NAME, "")
        if env_webhook:
            logger.info("从环境变量加载 Webhook URL")
            return NotificationConfig(webhook_url=env_webhook, enabled=True)
        
        # 返回默认配置
        return NotificationConfig()
    
    @classmethod
    def save(cls, config: NotificationConfig) -> bool:
        """
        保存配置到文件
        
        Validates: Requirements 1.5, 4.2
        """
        config_path = cls._get_config_path()
        
        try:
            # 确保目录存在
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(asdict(config), f, indent=2, ensure_ascii=False)
            
            logger.info(f"通知配置已保存到 {config_path}")
            return True
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False
    
    @classmethod
    def mask_webhook_url(cls, url: str) -> str:
        """
        脱敏显示 webhook URL
        
        示例: https://open.feishu.cn/...xy12
        
        Validates: Requirements 4.7
        """
        if not url or len(url) < 10:
            return "未配置"
        
        # 通用脱敏：显示前 30 字符 + ... + 最后 4 字符
        if len(url) > 40:
            return f"{url[:30]}...{url[-4:]}"
        
        return url[:len(url)-4] + "****"


# ==========================================
# 通知服务
# ==========================================

class NotificationService:
    """
    飞书通知服务
    
    Validates: Requirements 2.*, 3.*, 5.*
    """
    
    # 操作提醒文本
    OPERATION_REMINDER = "⚠️ 请务必在 PC 端确认新闻面及公告后操作"
    
    def __init__(self, config: NotificationConfig):
        """初始化通知服务"""
        self.config = config
    
    def format_signal(self, signal) -> str:
        """
        格式化单个信号为 Markdown
        
        包含：
        - 股票代码、名称
        - 买入：建议挂单价 + 参考收盘价
        - 卖出：参考价格
        - 信号原因
        - 风控警告
        - 时间戳和操作提醒
        
        Validates: Requirements 2.1, 2.2, 2.4, 2.5, 2.6, 2.7, 2.8
        """
        from core.signal_generator import SignalType
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # 构建风控警告
        warnings = self._format_warnings(signal)
        
        if signal.signal_type == SignalType.BUY:
            # 买入信号
            content = f"""📈 **MiniQuant 买入信号**

**股票**: {signal.code} {signal.name}
**建议挂单价**: ¥{signal.limit_cap:.2f}
**参考收盘价**: ¥{signal.price_range[1]:.2f}
**信号原因**: {signal.reason}
{warnings}
**生成时间**: {timestamp}

{self.OPERATION_REMINDER}"""
        else:
            # 卖出信号
            content = f"""📉 **MiniQuant 卖出信号**

**股票**: {signal.code} {signal.name}
**参考价格**: ¥{signal.price_range[1]:.2f}
**信号原因**: {signal.reason}
{warnings}
**生成时间**: {timestamp}

{self.OPERATION_REMINDER}"""
        
        return content.strip()
    
    def _format_warnings(self, signal) -> str:
        """
        格式化风控警告
        
        Validates: Requirements 2.6, 2.7
        """
        warnings = []
        
        # 财报窗口期警告
        if signal.in_report_window:
            warning_text = signal.report_warning or "请注意财报发布时间"
            warnings.append(f"⚠️ **财报窗口期**: {warning_text}")
        
        # 高费率预警
        if signal.high_fee_warning:
            warnings.append(f"⚠️ **高费率预警**: 实际费率 {signal.actual_fee_rate:.2%}，建议增加交易金额")
        
        if warnings:
            return "\n" + "\n".join(warnings) + "\n"
        return ""
    
    def format_summary(self, signals: list) -> str:
        """
        格式化信号摘要为 Markdown
        
        Validates: Requirements 2.3, 2.4, 2.5, 2.8
        """
        from core.signal_generator import SignalType
        
        if not signals:
            return ""
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # 统计信号数量
        buy_signals = [s for s in signals if s.signal_type == SignalType.BUY]
        sell_signals = [s for s in signals if s.signal_type == SignalType.SELL]
        
        content = f"""📊 **MiniQuant 信号汇总**

**买入信号**: {len(buy_signals)} 个
**卖出信号**: {len(sell_signals)} 个
"""
        
        # 买入信号列表
        if buy_signals:
            content += "\n**买入**\n"
            for s in buy_signals:
                warning_icon = "⚠️" if s.in_report_window or s.high_fee_warning else ""
                content += f"- {s.code} {s.name} 挂单价 ¥{s.limit_cap:.2f} {warning_icon}\n"
        
        # 卖出信号列表
        if sell_signals:
            content += "\n**卖出**\n"
            for s in sell_signals:
                content += f"- {s.code} {s.name}\n"
        
        content += f"""
**生成时间**: {timestamp}

{self.OPERATION_REMINDER}"""
        
        return content.strip()
    
    def _filter_signals(self, signals: list) -> list:
        """
        根据配置过滤信号类型
        
        Validates: Requirements 5.2
        """
        from core.signal_generator import SignalType
        
        filtered = []
        for signal in signals:
            if signal.signal_type == SignalType.BUY and not self.config.notify_on_buy:
                continue
            if signal.signal_type == SignalType.SELL and not self.config.notify_on_sell:
                continue
            filtered.append(signal)
        
        return filtered

    
    def _send_with_retry(self, content: str) -> Tuple[bool, str]:
        """
        带重试机制的发送（飞书格式）
        
        Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5
        
        重试策略：
        - 最多重试 max_retries 次
        - 每次间隔 retry_interval 秒
        - 超时 timeout 秒/次
        """
        if not HAS_REQUESTS:
            return False, "requests 库未安装"
        
        # 飞书 Webhook 请求格式
        payload = {
            "msg_type": "text",
            "content": {
                "text": content
            }
        }
        
        last_error = ""
        
        for attempt in range(self.config.max_retries):
            try:
                response = requests.post(
                    self.config.webhook_url,
                    json=payload,
                    timeout=self.config.timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    # 飞书成功响应: {"code": 0, "msg": "success"}
                    if result.get("code") == 0 or result.get("StatusCode") == 0:
                        logger.info("飞书通知发送成功")
                        return True, ""
                    else:
                        last_error = f"飞书返回错误: {result.get('msg', result.get('StatusMessage', '未知错误'))}"
                        logger.warning(f"第 {attempt + 1} 次发送失败: {last_error}")
                else:
                    last_error = f"HTTP {response.status_code}: {response.text[:100]}"
                    logger.warning(f"第 {attempt + 1} 次发送失败: {last_error}")
                    
            except requests.Timeout:
                last_error = f"请求超时 ({self.config.timeout}秒)"
                logger.warning(f"第 {attempt + 1} 次发送超时")
            except requests.RequestException as e:
                last_error = f"网络错误: {str(e)}"
                logger.warning(f"第 {attempt + 1} 次发送网络错误: {e}")
            except Exception as e:
                last_error = f"未知错误: {str(e)}"
                logger.error(f"第 {attempt + 1} 次发送异常: {e}")
            
            # 如果不是最后一次尝试，等待后重试
            if attempt < self.config.max_retries - 1:
                time.sleep(self.config.retry_interval)
        
        logger.error(f"飞书通知发送失败，已重试 {self.config.max_retries} 次: {last_error}")
        return False, last_error
    
    def send_signal_notification(self, signals: list) -> bool:
        """
        发送交易信号通知
        
        流程：
        1. 检查是否启用
        2. 检查 webhook_url 是否有效
        3. 过滤信号类型
        4. 格式化并发送消息
        
        Validates: Requirements 1.2, 1.4, 5.1, 5.2, 5.3
        
        Returns:
            True 发送成功，False 发送失败或跳过
        """
        # 检查是否启用 (Requirements 1.4)
        if not self.config.enabled:
            logger.debug("飞书通知未启用，跳过发送")
            return False
        
        # 检查 webhook_url (Requirements 1.2)
        if not self.config.webhook_url:
            logger.debug("Webhook URL 未配置，跳过发送")
            return False
        
        # 空信号不发送 (Requirements 5.3)
        if not signals:
            logger.debug("无信号，跳过发送")
            return True
        
        # 过滤信号类型 (Requirements 5.2)
        filtered_signals = self._filter_signals(signals)
        
        if not filtered_signals:
            logger.debug("过滤后无信号，跳过发送")
            return True
        
        # 格式化消息
        if len(filtered_signals) == 1:
            content = self.format_signal(filtered_signals[0])
        else:
            content = self.format_summary(filtered_signals)
        
        # 发送通知
        success, error = self._send_with_retry(content)
        return success
    
    def send_test_notification(self) -> Tuple[bool, str]:
        """
        发送测试通知
        
        Validates: Requirements 4.4, 4.5, 4.6
        
        Returns:
            (成功, 消息) - 成功时消息为空，失败时包含错误详情
        """
        # 检查 webhook_url
        if not self.config.webhook_url:
            return False, "Webhook URL 未配置"
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        buy_status = "✅ 开启" if self.config.notify_on_buy else "❌ 关闭"
        sell_status = "✅ 开启" if self.config.notify_on_sell else "❌ 关闭"
        
        content = f"""🔔 **MiniQuant 测试通知**

恭喜！飞书通知配置成功 ✅

您将在以下情况收到通知：
- 买入信号: {buy_status}
- 卖出信号: {sell_status}

**测试时间**: {timestamp}"""
        
        return self._send_with_retry(content)


# ==========================================
# 便捷函数
# ==========================================

def auto_send_notification(signals: list) -> bool:
    """
    自动发送通知（信号生成后调用）
    
    Validates: Requirements 5.1, 5.3
    
    Args:
        signals: 交易信号列表
        
    Returns:
        True 发送成功或无需发送，False 发送失败
    """
    config = NotificationConfigStore.load()
    
    if not config.enabled:
        return True
    
    if not signals:
        return True
    
    service = NotificationService(config)
    return service.send_signal_notification(signals)
