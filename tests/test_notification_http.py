"""
MiniQuant-Lite HTTP 发送单元测试

测试 NotificationService 的 HTTP 发送功能：
- 测试成功发送
- 测试重试机制
- 测试超时处理

Requirements: 3.1, 3.2, 3.3, 3.4, 3.5
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import date
import requests

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.notification import NotificationConfig, NotificationService
from core.signal_generator import SignalType, TradingSignal


class TestHttpSendSuccess:
    """HTTP 成功发送测试 - Requirements 3.1"""
    
    @pytest.fixture
    def notification_service(self):
        """创建通知服务实例"""
        config = NotificationConfig(
            webhook_url="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test-key",
            enabled=True,
            notify_on_buy=True,
            notify_on_sell=True,
            timeout=10,
            max_retries=3,
            retry_interval=0  # 测试时不等待
        )
        return NotificationService(config)
    
    @patch('requests.post')
    def test_successful_send(self, mock_post, notification_service):
        """
        测试成功发送通知
        
        Requirements: 3.1
        """
        # 模拟飞书成功响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": 0, "msg": "success"}
        mock_post.return_value = mock_response
        
        success, error = notification_service._send_with_retry("测试消息")
        
        assert success == True
        assert error == ""
        mock_post.assert_called_once()
    
    @patch('requests.post')
    def test_send_with_correct_payload(self, mock_post, notification_service):
        """
        测试发送正确的 payload 格式（飞书格式）
        
        Requirements: 3.1
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": 0, "msg": "success"}
        mock_post.return_value = mock_response
        
        test_content = "# 测试标题\n\n**测试内容**"
        notification_service._send_with_retry(test_content)
        
        # 验证调用参数（飞书格式）
        call_args = mock_post.call_args
        assert call_args[1]['json']['msg_type'] == 'text'
        assert call_args[1]['json']['content']['text'] == test_content
        assert call_args[1]['timeout'] == 10
    
    @patch('requests.post')
    def test_send_to_correct_url(self, mock_post, notification_service):
        """
        测试发送到正确的 webhook URL
        
        Requirements: 3.1
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": 0, "msg": "success"}
        mock_post.return_value = mock_response
        
        notification_service._send_with_retry("测试消息")
        
        # 验证 URL
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test-key"


class TestHttpRetryMechanism:
    """HTTP 重试机制测试 - Requirements 3.2, 3.3, 3.5"""
    
    @pytest.fixture
    def notification_service(self):
        """创建通知服务实例（短重试间隔）"""
        config = NotificationConfig(
            webhook_url="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test-key",
            enabled=True,
            notify_on_buy=True,
            notify_on_sell=True,
            timeout=10,
            max_retries=3,
            retry_interval=0  # 测试时不等待
        )
        return NotificationService(config)
    
    @patch('requests.post')
    def test_retry_on_http_error(self, mock_post, notification_service):
        """
        测试 HTTP 错误时重试
        
        Requirements: 3.2, 3.5
        """
        # 前两次失败，第三次成功
        mock_response_fail = MagicMock()
        mock_response_fail.status_code = 500
        mock_response_fail.text = "Internal Server Error"
        
        mock_response_success = MagicMock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"code": 0, "msg": "success"}
        
        mock_post.side_effect = [mock_response_fail, mock_response_fail, mock_response_success]
        
        success, error = notification_service._send_with_retry("测试消息")
        
        assert success == True
        assert mock_post.call_count == 3
    
    @patch('requests.post')
    def test_retry_on_wechat_error_response(self, mock_post, notification_service):
        """
        测试飞书返回错误时重试
        
        Requirements: 3.2, 3.5
        """
        # 前两次返回飞书错误，第三次成功
        mock_response_fail = MagicMock()
        mock_response_fail.status_code = 200
        mock_response_fail.json.return_value = {"code": 19001, "msg": "param invalid"}
        
        mock_response_success = MagicMock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"code": 0, "msg": "success"}
        
        mock_post.side_effect = [mock_response_fail, mock_response_fail, mock_response_success]
        
        success, error = notification_service._send_with_retry("测试消息")
        
        assert success == True
        assert mock_post.call_count == 3
    
    @patch('requests.post')
    def test_all_retries_fail(self, mock_post, notification_service):
        """
        测试所有重试都失败
        
        Requirements: 3.2, 3.3
        """
        # 所有请求都失败
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response
        
        success, error = notification_service._send_with_retry("测试消息")
        
        assert success == False
        assert "500" in error
        assert mock_post.call_count == 3  # 重试 3 次
    
    @patch('requests.post')
    def test_max_retries_configurable(self, mock_post):
        """
        测试最大重试次数可配置
        
        Requirements: 3.2
        """
        config = NotificationConfig(
            webhook_url="https://example.com/webhook",
            enabled=True,
            max_retries=5,
            retry_interval=0
        )
        service = NotificationService(config)
        
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Error"
        mock_post.return_value = mock_response
        
        service._send_with_retry("测试消息")
        
        assert mock_post.call_count == 5


class TestHttpTimeout:
    """HTTP 超时处理测试 - Requirements 3.4"""
    
    @pytest.fixture
    def notification_service(self):
        """创建通知服务实例"""
        config = NotificationConfig(
            webhook_url="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test-key",
            enabled=True,
            notify_on_buy=True,
            notify_on_sell=True,
            timeout=10,
            max_retries=3,
            retry_interval=0
        )
        return NotificationService(config)
    
    @patch('requests.post')
    def test_timeout_triggers_retry(self, mock_post, notification_service):
        """
        测试超时触发重试
        
        Requirements: 3.4
        """
        # 前两次超时，第三次成功
        mock_response_success = MagicMock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"code": 0, "msg": "success"}
        
        mock_post.side_effect = [
            requests.Timeout("Connection timed out"),
            requests.Timeout("Connection timed out"),
            mock_response_success
        ]
        
        success, error = notification_service._send_with_retry("测试消息")
        
        assert success == True
        assert mock_post.call_count == 3
    
    @patch('requests.post')
    def test_all_timeouts_fail(self, mock_post, notification_service):
        """
        测试所有请求都超时
        
        Requirements: 3.4
        """
        mock_post.side_effect = requests.Timeout("Connection timed out")
        
        success, error = notification_service._send_with_retry("测试消息")
        
        assert success == False
        assert "超时" in error
        assert mock_post.call_count == 3
    
    @patch('requests.post')
    def test_timeout_value_passed_to_request(self, mock_post, notification_service):
        """
        测试超时值正确传递给请求
        
        Requirements: 3.4
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": 0, "msg": "success"}
        mock_post.return_value = mock_response
        
        notification_service._send_with_retry("测试消息")
        
        # 验证 timeout 参数
        call_args = mock_post.call_args
        assert call_args[1]['timeout'] == 10
    
    @patch('requests.post')
    def test_custom_timeout_value(self, mock_post):
        """
        测试自定义超时值
        
        Requirements: 3.4
        """
        config = NotificationConfig(
            webhook_url="https://example.com/webhook",
            enabled=True,
            timeout=30,  # 自定义超时
            max_retries=1,
            retry_interval=0
        )
        service = NotificationService(config)
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": 0, "msg": "success"}
        mock_post.return_value = mock_response
        
        service._send_with_retry("测试消息")
        
        call_args = mock_post.call_args
        assert call_args[1]['timeout'] == 30


class TestHttpNetworkErrors:
    """HTTP 网络错误处理测试 - Requirements 3.3"""
    
    @pytest.fixture
    def notification_service(self):
        """创建通知服务实例"""
        config = NotificationConfig(
            webhook_url="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test-key",
            enabled=True,
            timeout=10,
            max_retries=3,
            retry_interval=0
        )
        return NotificationService(config)
    
    @patch('requests.post')
    def test_connection_error_triggers_retry(self, mock_post, notification_service):
        """
        测试连接错误触发重试
        
        Requirements: 3.3
        """
        mock_response_success = MagicMock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"code": 0, "msg": "success"}
        
        mock_post.side_effect = [
            requests.ConnectionError("Connection refused"),
            mock_response_success
        ]
        
        success, error = notification_service._send_with_retry("测试消息")
        
        assert success == True
        assert mock_post.call_count == 2
    
    @patch('requests.post')
    def test_all_network_errors_fail(self, mock_post, notification_service):
        """
        测试所有网络错误都失败
        
        Requirements: 3.3
        """
        mock_post.side_effect = requests.ConnectionError("Connection refused")
        
        success, error = notification_service._send_with_retry("测试消息")
        
        assert success == False
        assert "网络错误" in error
        assert mock_post.call_count == 3
    
    @patch('requests.post')
    def test_request_exception_handled(self, mock_post, notification_service):
        """
        测试通用请求异常处理
        
        Requirements: 3.3
        """
        mock_post.side_effect = requests.RequestException("Unknown error")
        
        success, error = notification_service._send_with_retry("测试消息")
        
        assert success == False
        assert mock_post.call_count == 3


class TestSendSignalNotification:
    """send_signal_notification 集成测试"""
    
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
    
    @patch('requests.post')
    def test_send_signal_notification_success(self, mock_post, buy_signal):
        """测试发送信号通知成功"""
        config = NotificationConfig(
            webhook_url="https://example.com/webhook",
            enabled=True,
            notify_on_buy=True,
            retry_interval=0
        )
        service = NotificationService(config)
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": 0, "msg": "success"}
        mock_post.return_value = mock_response
        
        result = service.send_signal_notification([buy_signal])
        
        assert result == True
        mock_post.assert_called_once()
    
    @patch('requests.post')
    def test_send_signal_notification_disabled(self, mock_post, buy_signal):
        """测试禁用时不发送"""
        config = NotificationConfig(
            webhook_url="https://example.com/webhook",
            enabled=False,  # 禁用
            notify_on_buy=True
        )
        service = NotificationService(config)
        
        result = service.send_signal_notification([buy_signal])
        
        assert result == False
        mock_post.assert_not_called()
    
    @patch('requests.post')
    def test_send_signal_notification_empty_webhook(self, mock_post, buy_signal):
        """测试空 webhook 不发送"""
        config = NotificationConfig(
            webhook_url="",  # 空 URL
            enabled=True,
            notify_on_buy=True
        )
        service = NotificationService(config)
        
        result = service.send_signal_notification([buy_signal])
        
        assert result == False
        mock_post.assert_not_called()


class TestSendTestNotification:
    """send_test_notification 测试"""
    
    @patch('requests.post')
    def test_send_test_notification_success(self, mock_post):
        """测试发送测试通知成功"""
        config = NotificationConfig(
            webhook_url="https://example.com/webhook",
            enabled=True,
            notify_on_buy=True,
            notify_on_sell=False,
            retry_interval=0
        )
        service = NotificationService(config)
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": 0, "msg": "success"}
        mock_post.return_value = mock_response
        
        success, error = service.send_test_notification()
        
        assert success == True
        assert error == ""
        
        # 验证消息内容包含配置状态
        call_args = mock_post.call_args
        content = call_args[1]['json']['content']['text']
        assert "测试通知" in content
        assert "买入信号" in content
        assert "卖出信号" in content
    
    def test_send_test_notification_no_webhook(self):
        """测试无 webhook 时返回错误"""
        config = NotificationConfig(
            webhook_url="",
            enabled=True
        )
        service = NotificationService(config)
        
        success, error = service.send_test_notification()
        
        assert success == False
        assert "未配置" in error


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
