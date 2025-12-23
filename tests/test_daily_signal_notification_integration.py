"""
MiniQuant-Lite 每日信号页面飞书通知集成测试

测试每日信号页面中飞书通知配置的集成功能：
- 紧凑版通知配置显示
- 配置保存和加载
- 通知发送集成

Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7
"""

import pytest
from unittest.mock import patch, MagicMock
import tempfile
from pathlib import Path
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.notification import NotificationConfig, NotificationConfigStore, NotificationService


class TestDailySignalNotificationIntegration:
    """每日信号页面通知集成测试"""
    
    @pytest.fixture
    def temp_config_dir(self):
        """创建临时配置目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def test_notification_config_loading_in_daily_signal(self, temp_config_dir):
        """
        测试每日信号页面加载通知配置
        
        Requirements: 4.1, 4.3
        """
        config_file = Path(temp_config_dir) / "notification_config.json"
        
        # 创建测试配置
        test_config = NotificationConfig(
            webhook_url="https://open.feishu.cn/open-apis/bot/v2/hook/daily-signal-test",
            enabled=True,
            notify_on_buy=True,
            notify_on_sell=True
        )
        
        with patch.object(NotificationConfigStore, '_get_config_path', return_value=config_file):
            # 保存配置
            NotificationConfigStore.save(test_config)
            
            # 模拟每日信号页面加载配置
            loaded_config = NotificationConfigStore.load()
            
            # 验证配置正确加载
            assert loaded_config.webhook_url == test_config.webhook_url
            assert loaded_config.enabled == test_config.enabled
            assert loaded_config.notify_on_buy == test_config.notify_on_buy
            assert loaded_config.notify_on_sell == test_config.notify_on_sell
    
    def test_compact_notification_status_display(self, temp_config_dir):
        """
        测试紧凑版通知状态显示
        
        Requirements: 4.1
        """
        config_file = Path(temp_config_dir) / "notification_config.json"
        
        with patch.object(NotificationConfigStore, '_get_config_path', return_value=config_file):
            # 测试已启用状态
            enabled_config = NotificationConfig(
                webhook_url="https://open.feishu.cn/open-apis/bot/v2/hook/enabled-test",
                enabled=True
            )
            NotificationConfigStore.save(enabled_config)
            
            config = NotificationConfigStore.load()
            assert config.enabled == True
            assert config.webhook_url != ""
            
            # 验证脱敏显示
            masked_url = NotificationConfigStore.mask_webhook_url(config.webhook_url)
            assert "test" in masked_url
            assert "enabled" not in masked_url
            
            # 测试未启用状态
            disabled_config = NotificationConfig(
                webhook_url="",
                enabled=False
            )
            NotificationConfigStore.save(disabled_config)
            
            config = NotificationConfigStore.load()
            assert config.enabled == False
            assert config.webhook_url == ""
    
    @patch('requests.post')
    def test_notification_save_and_test_workflow(self, mock_post, temp_config_dir):
        """
        测试保存和测试通知工作流
        
        Requirements: 4.2, 4.4, 4.5
        """
        config_file = Path(temp_config_dir) / "notification_config.json"
        
        # 模拟飞书成功响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": 0, "msg": "success"}
        mock_post.return_value = mock_response
        
        with patch.object(NotificationConfigStore, '_get_config_path', return_value=config_file):
            # 1. 用户输入新配置
            new_config = NotificationConfig(
                webhook_url="https://open.feishu.cn/open-apis/bot/v2/hook/workflow-test",
                enabled=True,
                notify_on_buy=True,
                notify_on_sell=True
            )
            
            # 2. 测试通知（在保存前）
            service = NotificationService(new_config)
            test_success, test_message = service.send_test_notification()
            assert test_success == True
            assert test_message == ""
            
            # 3. 保存配置
            save_success = NotificationConfigStore.save(new_config)
            assert save_success == True
            
            # 4. 验证配置已保存
            saved_config = NotificationConfigStore.load()
            assert saved_config.webhook_url == new_config.webhook_url
            assert saved_config.enabled == new_config.enabled
            
            # 5. 验证可以再次测试
            service_after_save = NotificationService(saved_config)
            test_success_2, test_message_2 = service_after_save.send_test_notification()
            assert test_success_2 == True
    
    @patch('requests.post')
    def test_notification_error_handling(self, mock_post, temp_config_dir):
        """
        测试通知错误处理
        
        Requirements: 4.6
        """
        config_file = Path(temp_config_dir) / "notification_config.json"
        
        # 模拟飞书错误响应
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request - Invalid webhook"
        mock_post.return_value = mock_response
        
        with patch.object(NotificationConfigStore, '_get_config_path', return_value=config_file):
            # 创建无效配置
            invalid_config = NotificationConfig(
                webhook_url="https://open.feishu.cn/open-apis/bot/v2/hook/invalid-key",
                enabled=True,
                notify_on_buy=True,
                notify_on_sell=True
            )
            
            # 测试通知失败
            service = NotificationService(invalid_config)
            test_success, test_message = service.send_test_notification()
            
            assert test_success == False
            assert "400" in test_message
            
            # 即使测试失败，配置仍可保存
            save_success = NotificationConfigStore.save(invalid_config)
            assert save_success == True
    
    def test_notification_config_update_scenario(self, temp_config_dir):
        """
        测试通知配置更新场景
        
        Requirements: 4.2, 4.3
        """
        config_file = Path(temp_config_dir) / "notification_config.json"
        
        with patch.object(NotificationConfigStore, '_get_config_path', return_value=config_file):
            # 初始配置
            initial_config = NotificationConfig(
                webhook_url="https://open.feishu.cn/open-apis/bot/v2/hook/initial-key",
                enabled=False,
                notify_on_buy=True,
                notify_on_sell=False
            )
            NotificationConfigStore.save(initial_config)
            
            # 验证初始配置
            config = NotificationConfigStore.load()
            assert config.enabled == False
            assert "initial" in config.webhook_url
            
            # 更新配置
            updated_config = NotificationConfig(
                webhook_url="https://open.feishu.cn/open-apis/bot/v2/hook/updated-key",
                enabled=True,
                notify_on_buy=False,
                notify_on_sell=True
            )
            NotificationConfigStore.save(updated_config)
            
            # 验证更新后的配置
            config = NotificationConfigStore.load()
            assert config.enabled == True
            assert "updated" in config.webhook_url
            assert config.notify_on_buy == False
            assert config.notify_on_sell == True
    
    def test_empty_webhook_validation_in_ui(self):
        """
        测试 UI 中空 Webhook 验证
        
        Requirements: 4.4
        """
        # 测试空 webhook URL
        empty_config = NotificationConfig(
            webhook_url="",
            enabled=True,
            notify_on_buy=True,
            notify_on_sell=True
        )
        
        service = NotificationService(empty_config)
        success, message = service.send_test_notification()
        
        assert success == False
        assert "未配置" in message
        
        # 测试 None webhook URL
        none_config = NotificationConfig(
            webhook_url=None,
            enabled=True,
            notify_on_buy=True,
            notify_on_sell=True
        )
        
        service_none = NotificationService(none_config)
        success_none, message_none = service_none.send_test_notification()
        
        assert success_none == False
        assert "未配置" in message_none
    
    def test_url_masking_for_ui_display(self):
        """
        测试 UI 显示的 URL 脱敏
        
        Requirements: 4.7
        """
        # 测试各种长度的 URL
        test_urls = [
            "https://open.feishu.cn/open-apis/bot/v2/hook/short",
            "https://open.feishu.cn/open-apis/bot/v2/hook/medium-length-key-1234",
            "https://open.feishu.cn/open-apis/bot/v2/hook/very-long-webhook-key-abcd1234-5678-90ab-cdef-ghijklmnopqr"
        ]
        
        for url in test_urls:
            masked = NotificationConfigStore.mask_webhook_url(url)
            
            # 验证脱敏效果
            assert len(masked) > 0
            assert masked != url  # 应该被脱敏
            
            # 长 URL 应该有省略号
            if len(url) > 40:
                assert "..." in masked
            
            # 应该显示最后几个字符
            assert masked.endswith(url[-4:])
    
    @patch('requests.post')
    def test_notification_integration_with_signal_generation(self, mock_post, temp_config_dir):
        """
        测试通知与信号生成的集成
        
        Requirements: 4.1, 4.2, 4.5
        """
        config_file = Path(temp_config_dir) / "notification_config.json"
        
        # 模拟飞书成功响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": 0, "msg": "success"}
        mock_post.return_value = mock_response
        
        with patch.object(NotificationConfigStore, '_get_config_path', return_value=config_file):
            # 配置通知
            notification_config = NotificationConfig(
                webhook_url="https://open.feishu.cn/open-apis/bot/v2/hook/signal-integration",
                enabled=True,
                notify_on_buy=True,
                notify_on_sell=True
            )
            NotificationConfigStore.save(notification_config)
            
            # 验证配置可用于信号通知
            loaded_config = NotificationConfigStore.load()
            service = NotificationService(loaded_config)
            
            # 模拟发送信号通知
            test_success, test_message = service.send_test_notification()
            assert test_success == True
            
            # 验证请求内容
            mock_post.assert_called()
            call_args = mock_post.call_args
            assert call_args[1]['json']['msg_type'] == 'text'
            content = call_args[1]['json']['content']['text']
            assert "测试通知" in content


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])