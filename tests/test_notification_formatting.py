"""
MiniQuant-Lite 消息格式化单元测试

测试 NotificationService 的消息格式化功能：
- 买入信号格式化
- 卖出信号格式化
- 风控警告包含
- 摘要格式化

Requirements: 2.1, 2.2, 2.3, 2.6, 2.7
"""

import pytest
from datetime import date
from dataclasses import dataclass
from typing import Tuple, Optional

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.notification import NotificationConfig, NotificationService
from core.signal_generator import SignalType, TradingSignal


class TestFormatBuySignal:
    """买入信号格式化测试 - Requirements 2.1"""
    
    @pytest.fixture
    def notification_service(self):
        """创建通知服务实例"""
        config = NotificationConfig(
            webhook_url="https://example.com/webhook",
            enabled=True,
            notify_on_buy=True,
            notify_on_sell=True
        )
        return NotificationService(config)
    
    @pytest.fixture
    def buy_signal(self):
        """创建买入信号"""
        return TradingSignal(
            code="000001",
            name="平安银行",
            signal_type=SignalType.BUY,
            price_range=(11.50, 12.00),
            limit_cap=12.12,
            reason="RSI超卖反弹",
            generated_at=date.today(),
            trade_amount=10000.0,
            high_fee_warning=False,
            actual_fee_rate=0.0003,
            news_url="https://quote.eastmoney.com/sz000001.html",
            in_report_window=False,
            report_warning=None
        )
    
    def test_buy_signal_contains_stock_code(self, notification_service, buy_signal):
        """测试买入信号包含股票代码"""
        message = notification_service.format_signal(buy_signal)
        assert "000001" in message
    
    def test_buy_signal_contains_stock_name(self, notification_service, buy_signal):
        """测试买入信号包含股票名称"""
        message = notification_service.format_signal(buy_signal)
        assert "平安银行" in message
    
    def test_buy_signal_contains_limit_cap(self, notification_service, buy_signal):
        """测试买入信号包含挂单价"""
        message = notification_service.format_signal(buy_signal)
        assert "挂单价" in message
        assert "12.12" in message
    
    def test_buy_signal_contains_close_price(self, notification_service, buy_signal):
        """测试买入信号包含收盘价"""
        message = notification_service.format_signal(buy_signal)
        assert "收盘价" in message
        assert "12.00" in message
    
    def test_buy_signal_contains_reason(self, notification_service, buy_signal):
        """测试买入信号包含信号原因"""
        message = notification_service.format_signal(buy_signal)
        assert "RSI超卖反弹" in message
    
    def test_buy_signal_contains_buy_indicator(self, notification_service, buy_signal):
        """测试买入信号包含买入标识"""
        message = notification_service.format_signal(buy_signal)
        assert "买入" in message


class TestFormatSellSignal:
    """卖出信号格式化测试 - Requirements 2.2"""
    
    @pytest.fixture
    def notification_service(self):
        """创建通知服务实例"""
        config = NotificationConfig(
            webhook_url="https://example.com/webhook",
            enabled=True,
            notify_on_buy=True,
            notify_on_sell=True
        )
        return NotificationService(config)
    
    @pytest.fixture
    def sell_signal(self):
        """创建卖出信号"""
        return TradingSignal(
            code="600519",
            name="贵州茅台",
            signal_type=SignalType.SELL,
            price_range=(1800.00, 1850.00),
            limit_cap=1868.50,
            reason="MACD死叉",
            generated_at=date.today(),
            trade_amount=185000.0,
            high_fee_warning=False,
            actual_fee_rate=0.0003,
            news_url="https://quote.eastmoney.com/sh600519.html",
            in_report_window=False,
            report_warning=None
        )
    
    def test_sell_signal_contains_stock_code(self, notification_service, sell_signal):
        """测试卖出信号包含股票代码"""
        message = notification_service.format_signal(sell_signal)
        assert "600519" in message
    
    def test_sell_signal_contains_stock_name(self, notification_service, sell_signal):
        """测试卖出信号包含股票名称"""
        message = notification_service.format_signal(sell_signal)
        assert "贵州茅台" in message
    
    def test_sell_signal_contains_price(self, notification_service, sell_signal):
        """测试卖出信号包含参考价格"""
        message = notification_service.format_signal(sell_signal)
        assert "参考价格" in message
        assert "1850.00" in message
    
    def test_sell_signal_contains_reason(self, notification_service, sell_signal):
        """测试卖出信号包含信号原因"""
        message = notification_service.format_signal(sell_signal)
        assert "MACD死叉" in message
    
    def test_sell_signal_contains_sell_indicator(self, notification_service, sell_signal):
        """测试卖出信号包含卖出标识"""
        message = notification_service.format_signal(sell_signal)
        assert "卖出" in message


class TestRiskWarnings:
    """风控警告测试 - Requirements 2.6, 2.7"""
    
    @pytest.fixture
    def notification_service(self):
        """创建通知服务实例"""
        config = NotificationConfig(
            webhook_url="https://example.com/webhook",
            enabled=True,
            notify_on_buy=True,
            notify_on_sell=True
        )
        return NotificationService(config)
    
    def test_report_window_warning_included(self, notification_service):
        """测试财报窗口期警告包含 - Requirements 2.6"""
        signal = TradingSignal(
            code="000001",
            name="平安银行",
            signal_type=SignalType.BUY,
            price_range=(11.50, 12.00),
            limit_cap=12.12,
            reason="RSI超卖反弹",
            generated_at=date.today(),
            trade_amount=10000.0,
            high_fee_warning=False,
            actual_fee_rate=0.0003,
            news_url="https://quote.eastmoney.com/sz000001.html",
            in_report_window=True,
            report_warning="年报将于4月发布"
        )
        
        message = notification_service.format_signal(signal)
        assert "财报窗口期" in message
        assert "年报将于4月发布" in message
    
    def test_high_fee_warning_included(self, notification_service):
        """测试高费率预警包含 - Requirements 2.7"""
        signal = TradingSignal(
            code="000001",
            name="平安银行",
            signal_type=SignalType.BUY,
            price_range=(11.50, 12.00),
            limit_cap=12.12,
            reason="RSI超卖反弹",
            generated_at=date.today(),
            trade_amount=1000.0,
            high_fee_warning=True,
            actual_fee_rate=0.005,
            news_url="https://quote.eastmoney.com/sz000001.html",
            in_report_window=False,
            report_warning=None
        )
        
        message = notification_service.format_signal(signal)
        assert "高费率预警" in message
    
    def test_both_warnings_included(self, notification_service):
        """测试同时包含两种警告"""
        signal = TradingSignal(
            code="000001",
            name="平安银行",
            signal_type=SignalType.BUY,
            price_range=(11.50, 12.00),
            limit_cap=12.12,
            reason="RSI超卖反弹",
            generated_at=date.today(),
            trade_amount=1000.0,
            high_fee_warning=True,
            actual_fee_rate=0.005,
            news_url="https://quote.eastmoney.com/sz000001.html",
            in_report_window=True,
            report_warning="季报窗口期"
        )
        
        message = notification_service.format_signal(signal)
        assert "财报窗口期" in message
        assert "高费率预警" in message
    
    def test_no_warnings_when_not_applicable(self, notification_service):
        """测试无警告时不显示警告内容"""
        signal = TradingSignal(
            code="000001",
            name="平安银行",
            signal_type=SignalType.BUY,
            price_range=(11.50, 12.00),
            limit_cap=12.12,
            reason="RSI超卖反弹",
            generated_at=date.today(),
            trade_amount=10000.0,
            high_fee_warning=False,
            actual_fee_rate=0.0003,
            news_url="https://quote.eastmoney.com/sz000001.html",
            in_report_window=False,
            report_warning=None
        )
        
        message = notification_service.format_signal(signal)
        # 不应包含警告关键词（除了操作提醒中的⚠️）
        assert "财报窗口期" not in message
        assert "高费率预警" not in message


class TestFormatSummary:
    """摘要格式化测试 - Requirements 2.3"""
    
    @pytest.fixture
    def notification_service(self):
        """创建通知服务实例"""
        config = NotificationConfig(
            webhook_url="https://example.com/webhook",
            enabled=True,
            notify_on_buy=True,
            notify_on_sell=True
        )
        return NotificationService(config)
    
    @pytest.fixture
    def mixed_signals(self):
        """创建混合信号列表"""
        return [
            TradingSignal(
                code="000001",
                name="平安银行",
                signal_type=SignalType.BUY,
                price_range=(11.50, 12.00),
                limit_cap=12.12,
                reason="RSI超卖反弹",
                generated_at=date.today(),
                trade_amount=10000.0,
                high_fee_warning=False,
                actual_fee_rate=0.0003,
                news_url="https://quote.eastmoney.com/sz000001.html",
                in_report_window=False,
                report_warning=None
            ),
            TradingSignal(
                code="600036",
                name="招商银行",
                signal_type=SignalType.BUY,
                price_range=(35.00, 36.00),
                limit_cap=36.36,
                reason="MACD金叉",
                generated_at=date.today(),
                trade_amount=20000.0,
                high_fee_warning=False,
                actual_fee_rate=0.0003,
                news_url="https://quote.eastmoney.com/sh600036.html",
                in_report_window=True,
                report_warning="季报窗口期"
            ),
            TradingSignal(
                code="600519",
                name="贵州茅台",
                signal_type=SignalType.SELL,
                price_range=(1800.00, 1850.00),
                limit_cap=1868.50,
                reason="MACD死叉",
                generated_at=date.today(),
                trade_amount=185000.0,
                high_fee_warning=False,
                actual_fee_rate=0.0003,
                news_url="https://quote.eastmoney.com/sh600519.html",
                in_report_window=False,
                report_warning=None
            )
        ]
    
    def test_summary_contains_buy_count(self, notification_service, mixed_signals):
        """测试摘要包含买入信号数量"""
        message = notification_service.format_summary(mixed_signals)
        assert "买入信号" in message
        assert "2" in message  # 2个买入信号
    
    def test_summary_contains_sell_count(self, notification_service, mixed_signals):
        """测试摘要包含卖出信号数量"""
        message = notification_service.format_summary(mixed_signals)
        assert "卖出信号" in message
        assert "1" in message  # 1个卖出信号
    
    def test_summary_contains_stock_codes(self, notification_service, mixed_signals):
        """测试摘要包含所有股票代码"""
        message = notification_service.format_summary(mixed_signals)
        assert "000001" in message
        assert "600036" in message
        assert "600519" in message
    
    def test_summary_contains_warning_icon(self, notification_service, mixed_signals):
        """测试摘要包含警告图标"""
        message = notification_service.format_summary(mixed_signals)
        # 招商银行有财报窗口期警告，应显示警告图标
        assert "⚠️" in message
    
    def test_summary_empty_signals(self, notification_service):
        """测试空信号列表返回空字符串"""
        message = notification_service.format_summary([])
        assert message == ""
    
    def test_summary_contains_operation_reminder(self, notification_service, mixed_signals):
        """测试摘要包含操作提醒"""
        message = notification_service.format_summary(mixed_signals)
        assert "请务必在 PC 端确认" in message


class TestMessageFormatRequirements:
    """消息格式要求测试 - Requirements 2.4, 2.5, 2.8"""
    
    @pytest.fixture
    def notification_service(self):
        """创建通知服务实例"""
        config = NotificationConfig(
            webhook_url="https://example.com/webhook",
            enabled=True,
            notify_on_buy=True,
            notify_on_sell=True
        )
        return NotificationService(config)
    
    @pytest.fixture
    def buy_signal(self):
        """创建买入信号"""
        return TradingSignal(
            code="000001",
            name="平安银行",
            signal_type=SignalType.BUY,
            price_range=(11.50, 12.00),
            limit_cap=12.12,
            reason="RSI超卖反弹",
            generated_at=date.today(),
            trade_amount=10000.0,
            high_fee_warning=False,
            actual_fee_rate=0.0003,
            news_url="https://quote.eastmoney.com/sz000001.html",
            in_report_window=False,
            report_warning=None
        )
    
    def test_message_contains_timestamp(self, notification_service, buy_signal):
        """测试消息包含时间戳 - Requirements 2.4"""
        message = notification_service.format_signal(buy_signal)
        assert "生成时间" in message
    
    def test_message_uses_markdown_headers(self, notification_service, buy_signal):
        """测试消息使用 Markdown 标题 - Requirements 2.5"""
        message = notification_service.format_signal(buy_signal)
        assert message.startswith("#")
    
    def test_message_uses_markdown_bold(self, notification_service, buy_signal):
        """测试消息使用 Markdown 粗体 - Requirements 2.5"""
        message = notification_service.format_signal(buy_signal)
        assert "**" in message
    
    def test_message_contains_operation_reminder(self, notification_service, buy_signal):
        """测试消息包含操作提醒 - Requirements 2.8"""
        message = notification_service.format_signal(buy_signal)
        assert "请务必在 PC 端确认" in message


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
