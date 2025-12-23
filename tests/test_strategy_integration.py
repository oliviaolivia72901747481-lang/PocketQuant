"""
策略选择和参数显示集成测试

验证策略选择和参数显示功能在实际使用场景中的表现

Requirements: Task 3.1 - 测试策略选择和参数显示
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
import importlib.util

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import StrategyParamsConfig, save_strategy_params, load_strategy_params


class TestStrategyIntegration(unittest.TestCase):
    """策略选择和参数显示集成测试"""
    
    def setUp(self):
        """测试前准备"""
        # 保存原始参数配置
        self.original_params = load_strategy_params()
    
    def tearDown(self):
        """测试后清理"""
        # 恢复原始参数配置
        save_strategy_params(self.original_params)
    
    def test_strategy_params_persistence(self):
        """测试策略参数持久化功能"""
        # 创建测试参数
        test_params = StrategyParamsConfig(
            rsi_period=21,
            rsi_buy_threshold=25,
            rsi_sell_threshold=75,
            rsrs_n_period=20,
            rsrs_buy_threshold=0.8,
            rsrs_sell_threshold=-0.8
        )
        
        # 保存参数
        success = save_strategy_params(test_params)
        self.assertTrue(success, "参数保存应该成功")
        
        # 加载参数
        loaded_params = load_strategy_params()
        
        # 验证参数正确性
        self.assertEqual(loaded_params.rsi_period, 21)
        self.assertEqual(loaded_params.rsi_buy_threshold, 25)
        self.assertEqual(loaded_params.rsi_sell_threshold, 75)
        self.assertEqual(loaded_params.rsrs_n_period, 20)
        self.assertEqual(loaded_params.rsrs_buy_threshold, 0.8)
        self.assertEqual(loaded_params.rsrs_sell_threshold, -0.8)
    
    def test_default_strategy_params(self):
        """测试默认策略参数"""
        # 删除参数文件（如果存在）
        import os
        from config.settings import _get_strategy_params_path
        
        params_file = _get_strategy_params_path()
        if os.path.exists(params_file):
            os.remove(params_file)
        
        # 加载默认参数
        default_params = load_strategy_params()
        
        # 验证默认值
        self.assertEqual(default_params.rsi_period, 14)
        self.assertEqual(default_params.rsi_buy_threshold, 30)
        self.assertEqual(default_params.rsi_sell_threshold, 70)
        self.assertEqual(default_params.rsrs_n_period, 18)
        self.assertEqual(default_params.rsrs_buy_threshold, 0.7)
        self.assertEqual(default_params.rsrs_sell_threshold, -0.7)
    
    def test_strategy_params_validation(self):
        """测试策略参数验证"""
        # 测试 RSI 参数范围
        params = StrategyParamsConfig()
        
        # RSI 周期应该在合理范围内
        self.assertGreater(params.rsi_period, 0)
        self.assertLess(params.rsi_period, 100)
        
        # RSI 阈值应该在 0-100 范围内
        self.assertGreaterEqual(params.rsi_buy_threshold, 0)
        self.assertLessEqual(params.rsi_buy_threshold, 100)
        self.assertGreaterEqual(params.rsi_sell_threshold, 0)
        self.assertLessEqual(params.rsi_sell_threshold, 100)
        
        # 买入阈值应该小于卖出阈值
        self.assertLess(params.rsi_buy_threshold, params.rsi_sell_threshold)
        
        # RSRS 参数验证
        self.assertGreater(params.rsrs_n_period, 0)
        self.assertGreater(params.rsrs_m_period, params.rsrs_n_period)
        
        # RSRS 阈值应该对称
        self.assertGreater(params.rsrs_buy_threshold, 0)
        self.assertLess(params.rsrs_sell_threshold, 0)
    
    def test_strategy_configuration_completeness(self):
        """测试策略配置的完整性"""
        # 验证策略参数配置类的完整性
        params = StrategyParamsConfig()
        
        # 验证 RSI 策略参数
        self.assertIsNotNone(params.rsi_period)
        self.assertIsNotNone(params.rsi_buy_threshold)
        self.assertIsNotNone(params.rsi_sell_threshold)
        self.assertIsNotNone(params.rsi_stop_loss)
        self.assertIsNotNone(params.rsi_take_profit)
        
        # 验证 RSRS 策略参数
        self.assertIsNotNone(params.rsrs_n_period)
        self.assertIsNotNone(params.rsrs_m_period)
        self.assertIsNotNone(params.rsrs_buy_threshold)
        self.assertIsNotNone(params.rsrs_sell_threshold)
        self.assertIsNotNone(params.rsrs_hard_stop_loss)
    
    def test_strategy_parameter_format(self):
        """测试策略参数格式化显示"""
        params = StrategyParamsConfig(
            rsrs_buy_threshold=0.7,
            rsrs_sell_threshold=-0.7
        )
        
        # 测试 RSRS 阈值格式化
        buy_threshold_str = f"{params.rsrs_buy_threshold:.1f}"
        sell_threshold_str = f"{params.rsrs_sell_threshold:.1f}"
        
        self.assertEqual(buy_threshold_str, "0.7")
        self.assertEqual(sell_threshold_str, "-0.7")
        
        # 测试整数参数不需要格式化
        self.assertEqual(params.rsi_period, 14)
        self.assertEqual(params.rsi_buy_threshold, 30)
        self.assertEqual(params.rsi_sell_threshold, 70)


if __name__ == '__main__':
    unittest.main()