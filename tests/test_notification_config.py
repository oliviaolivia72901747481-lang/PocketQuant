"""
MiniQuant-Lite 通知配置持久化单元测试

测试 NotificationConfig 和 NotificationConfigStore 的功能：
- 配置保存和加载往返
- 环境变量回退
- URL 脱敏显示

Requirements: 1.3, 1.5, 1.6, 4.7
"""

import pytest
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.notification import NotificationConfig, NotificationConfigStore


class TestNotificationConfig:
    """NotificationConfig 数据类测试"""
    
    def test_default_values(self):
        """测试默认值"""
        config = NotificationConfig()
        
        assert config.webhook_url == ""
        assert config.enabled == False
        assert config.notify_on_buy == True
        assert config.notify_on_sell == True
        assert config.timeout == 10
        assert config.max_retries == 3
        assert config.retry_interval == 2
    
    def test_custom_values(self):
        """测试自定义值"""
        config = NotificationConfig(
            webhook_url="https://example.com/webhook",
            enabled=True,
            notify_on_buy=False,
            notify_on_sell=True,
            timeout=15,
            max_retries=5,
            retry_interval=3
        )
        
        assert config.webhook_url == "https://example.com/webhook"
        assert config.enabled == True
        assert config.notify_on_buy == False
        assert config.notify_on_sell == True
        assert config.timeout == 15
        assert config.max_retries == 5
        assert config.retry_interval == 3


class TestNotificationConfigStore:
    """NotificationConfigStore 持久化测试"""
    
    @pytest.fixture
    def temp_config_dir(self):
        """创建临时配置目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def test_save_and_load_roundtrip(self, temp_config_dir):
        """
        测试保存和加载往返
        
        Requirements: 1.3, 1.5, 1.6
        """
        # 创建临时配置文件路径
        config_file = Path(temp_config_dir) / "notification_config.json"
        
        # 创建测试配置
        original_config = NotificationConfig(
            webhook_url="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test-key-1234",
            enabled=True,
            notify_on_buy=True,
            notify_on_sell=False,
            timeout=15,
            max_retries=5,
            retry_interval=3
        )
        
        # 使用 patch 替换配置文件路径
        with patch.object(NotificationConfigStore, '_get_config_path', return_value=config_file):
            # 保存配置
            save_result = NotificationConfigStore.save(original_config)
            assert save_result == True, "保存配置失败"
            
            # 验证文件已创建
            assert config_file.exists(), "配置文件未创建"
            
            # 加载配置
            loaded_config = NotificationConfigStore.load()
            
            # 验证所有字段一致
            assert loaded_config.webhook_url == original_config.webhook_url
            assert loaded_config.enabled == original_config.enabled
            assert loaded_config.notify_on_buy == original_config.notify_on_buy
            assert loaded_config.notify_on_sell == original_config.notify_on_sell
            assert loaded_config.timeout == original_config.timeout
            assert loaded_config.max_retries == original_config.max_retries
            assert loaded_config.retry_interval == original_config.retry_interval
    
    def test_environment_variable_fallback(self, temp_config_dir):
        """
        测试环境变量回退
        
        Requirements: 1.3
        """
        # 创建不存在的配置文件路径
        config_file = Path(temp_config_dir) / "nonexistent_config.json"
        
        test_webhook_url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=env-test-key"
        
        with patch.object(NotificationConfigStore, '_get_config_path', return_value=config_file):
            # 设置环境变量
            with patch.dict(os.environ, {NotificationConfigStore.ENV_VAR_NAME: test_webhook_url}):
                # 加载配置（应从环境变量读取）
                config = NotificationConfigStore.load()
                
                assert config.webhook_url == test_webhook_url
                assert config.enabled == True  # 从环境变量加载时默认启用
    
    def test_default_config_when_no_file_no_env(self, temp_config_dir):
        """
        测试无文件无环境变量时返回默认配置
        
        Requirements: 1.6
        """
        # 创建不存在的配置文件路径
        config_file = Path(temp_config_dir) / "nonexistent_config.json"
        
        with patch.object(NotificationConfigStore, '_get_config_path', return_value=config_file):
            # 确保环境变量不存在
            with patch.dict(os.environ, {}, clear=True):
                # 移除可能存在的环境变量
                env_backup = os.environ.pop(NotificationConfigStore.ENV_VAR_NAME, None)
                try:
                    config = NotificationConfigStore.load()
                    
                    # 应返回默认配置
                    assert config.webhook_url == ""
                    assert config.enabled == False
                finally:
                    # 恢复环境变量
                    if env_backup:
                        os.environ[NotificationConfigStore.ENV_VAR_NAME] = env_backup
    
    def test_corrupted_config_file_fallback(self, temp_config_dir):
        """
        测试损坏的配置文件回退到默认配置
        
        Requirements: 1.6
        """
        config_file = Path(temp_config_dir) / "notification_config.json"
        
        # 写入损坏的 JSON
        config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config_file, 'w') as f:
            f.write("{ invalid json content")
        
        with patch.object(NotificationConfigStore, '_get_config_path', return_value=config_file):
            # 确保环境变量不存在
            env_backup = os.environ.pop(NotificationConfigStore.ENV_VAR_NAME, None)
            try:
                config = NotificationConfigStore.load()
                
                # 应返回默认配置
                assert config.webhook_url == ""
                assert config.enabled == False
            finally:
                if env_backup:
                    os.environ[NotificationConfigStore.ENV_VAR_NAME] = env_backup


class TestWebhookUrlMasking:
    """Webhook URL 脱敏测试"""
    
    def test_mask_standard_webhook_url(self):
        """
        测试标准企业微信 Webhook URL 脱敏
        
        Requirements: 4.7
        """
        url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=abcd1234-5678-90ab-cdef-ghijklmnopqr"
        masked = NotificationConfigStore.mask_webhook_url(url)
        
        # 应只显示最后 4 个字符
        assert masked.endswith("opqr")
        assert "abcd1234" not in masked
        assert "key=" in masked
    
    def test_mask_short_url(self):
        """测试短 URL 脱敏"""
        url = "http://short"
        masked = NotificationConfigStore.mask_webhook_url(url)
        
        # 短 URL 应部分脱敏
        assert len(masked) > 0
    
    def test_mask_empty_url(self):
        """测试空 URL 脱敏"""
        masked = NotificationConfigStore.mask_webhook_url("")
        assert masked == "未配置"
    
    def test_mask_none_url(self):
        """测试 None URL 脱敏"""
        masked = NotificationConfigStore.mask_webhook_url(None)
        assert masked == "未配置"
    
    def test_mask_very_short_url(self):
        """测试非常短的 URL 脱敏"""
        url = "abc"
        masked = NotificationConfigStore.mask_webhook_url(url)
        assert masked == "未配置"
    
    def test_mask_url_without_key_parameter(self):
        """测试不含 key 参数的 URL 脱敏"""
        url = "https://example.com/webhook/some-long-path-that-needs-masking"
        masked = NotificationConfigStore.mask_webhook_url(url)
        
        # 应使用通用脱敏逻辑
        assert masked.endswith("king") or "..." in masked


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
