"""
Test signal generation functionality - Basic tests

Requirements: Compact layout task - Test signal generation functionality
"""

import unittest
from unittest.mock import Mock, patch
import sys
import os
from datetime import date

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.signal_generator import SignalGenerator, TradingSignal, SignalType, StrategyType
from core.data_feed import DataFeed


class TestSignalGeneration(unittest.TestCase):
    """Test signal generation functionality"""
    
    def setUp(self):
        """Setup test fixtures"""
        self.mock_data_feed = Mock(spec=DataFeed)
        
    def test_signal_generator_creation(self):
        """Test that SignalGenerator can be created"""
        generator = SignalGenerator(
            data_feed=self.mock_data_feed,
            strategy_type=StrategyType.RSI_REVERSAL
        )
        self.assertIsInstance(generator, SignalGenerator)
        
    def test_signal_generator_with_empty_pool(self):
        """Test signal generation with empty stock pool"""
        generator = SignalGenerator(
            data_feed=self.mock_data_feed,
            strategy_type=StrategyType.RSI_REVERSAL
        )
        
        with patch('core.signal_generator.get_settings') as mock_settings:
            mock_settings.return_value.fund.initial_capital = 100000.0
            
            # Test with empty stock pool
            signals = generator.generate_signals(
                stock_pool=[],
                current_cash=100000.0,
                current_positions=0
            )
            
            self.assertIsInstance(signals, list)
            self.assertEqual(len(signals), 0)
    
    def test_trading_signal_creation(self):
        """Test that TradingSignal objects can be created"""
        signal = TradingSignal(
            code="000001",
            name="Test Stock",
            signal_type=SignalType.BUY,
            price_range=(10.0, 11.0),
            limit_cap=11.11,
            reason="Test signal",
            generated_at=date.today(),
            trade_amount=10000.0,
            high_fee_warning=False,
            actual_fee_rate=0.0003,
            news_url="https://example.com",
            in_report_window=False,
            signal_strength=75.0
        )
        
        self.assertEqual(signal.code, "000001")
        self.assertEqual(signal.signal_type, SignalType.BUY)
        self.assertEqual(signal.trade_amount, 10000.0)
    
    def test_daily_signal_module_import(self):
        """Test that Daily Signal module can be imported"""
        import importlib.util
        
        spec = importlib.util.spec_from_file_location(
            "daily_signal", 
            "app/pages/3_Daily_Signal.py"
        )
        
        self.assertIsNotNone(spec)
        
        daily_signal_module = importlib.util.module_from_spec(spec)
        self.assertIsNotNone(daily_signal_module)
        
        # Mock dependencies before loading
        with patch.dict('sys.modules', {
            'streamlit': Mock(),
            'core.data_feed': Mock(),
            'core.signal_generator': Mock(),
            'core.screener': Mock(),
            'core.signal_store': Mock(),
            'core.position_tracker': Mock(),
            'core.sell_signal_checker': Mock(),
            'core.logging_config': Mock(),
            'core.notification': Mock(),
            'config.settings': Mock(),
            'config.stock_pool': Mock()
        }):
            spec.loader.exec_module(daily_signal_module)
            
            # Verify the generate_signals function exists
            self.assertTrue(hasattr(daily_signal_module, 'generate_signals'))
            self.assertTrue(callable(getattr(daily_signal_module, 'generate_signals')))


if __name__ == '__main__':
    unittest.main()