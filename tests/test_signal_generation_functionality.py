import unittest
from unittest.mock import Mock, patch
import sys
import os
from datetime import date
import importlib.util

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.signal_generator import SignalGenerator, TradingSignal, SignalType, StrategyType
from core.data_feed import DataFeed


class TestSignalGenerationFunctionality(unittest.TestCase):
    """Test signal generation functionality"""
    
    def setUp(self):
        """Setup test fixtures"""
        self.test_stock_pool = ["000001", "000002", "600036"]
        self.mock_data_feed = Mock(spec=DataFeed)
        
        # Mock settings
        self.mock_settings = Mock()
        self.mock_settings.fund.initial_capital = 100000.0
        self.mock_settings.fund.commission_rate = 0.0003
        self.mock_settings.fund.min_commission = 5.0
        
    def _load_daily_signal_module(self):
        """Load Daily Signal module"""
        spec = importlib.util.spec_from_file_location(
            "daily_signal", 
            "app/pages/3_Daily_Signal.py"
        )
        daily_signal_module = importlib.util.module_from_spec(spec)
        
        # Mock all dependencies
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
            
        return daily_signal_module
        
    def test_generate_signals_function_exists(self):
        """Test that generate_signals function exists"""
        daily_signal_module = self._load_daily_signal_module()
        
        # Verify function exists
        self.assertTrue(hasattr(daily_signal_module, 'generate_signals'))
        self.assertTrue(callable(getattr(daily_signal_module, 'generate_signals')))
        
    def test_generate_signals_with_valid_stock_pool(self):
        """Test signal generation with valid stock pool"""
        daily_signal_module = self._load_daily_signal_module()
        
        # Mock dependency functions
        daily_signal_module.get_data_feed = Mock(return_value=self.mock_data_feed)
        daily_signal_module.get_settings = Mock(return_value=self.mock_settings)
        
        # Mock SignalGenerator
        mock_signal_generator = Mock(spec=SignalGenerator)
        mock_signals = [
            TradingSignal(
                code="000001",
                name="Test Stock",
                signal_type=SignalType.BUY,
                price_range=(10.0, 11.0),
                limit_cap=11.11,
                reason="RSI < 30 oversold bounce",
                generated_at=date.today(),
                trade_amount=10000.0,
                high_fee_warning=False,
                actual_fee_rate=0.0003,
                news_url="https://quote.eastmoney.com/sz000001.html",
                in_report_window=False,
                signal_strength=75.0
            )
        ]
        mock_signal_generator.generate_signals.return_value = mock_signals
        
        # Replace SignalGenerator constructor
        with patch.object(daily_signal_module, 'SignalGenerator', return_value=mock_signal_generator):
            # Call generate_signals function
            result = daily_signal_module.generate_signals(
                stock_pool=self.test_stock_pool,
                strategy_type=StrategyType.RSI_REVERSAL
            )
            
            # Verify results
            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0].code, "000001")
            self.assertEqual(result[0].signal_type, SignalType.BUY)
    
    def test_generate_signals_with_empty_stock_pool(self):
        """Test signal generation with empty stock pool"""
        daily_signal_module = self._load_daily_signal_module()
        
        # Mock dependency functions
        daily_signal_module.get_data_feed = Mock(return_value=self.mock_data_feed)
        daily_signal_module.get_settings = Mock(return_value=self.mock_settings)
        
        # Mock SignalGenerator
        mock_signal_generator = Mock(spec=SignalGenerator)
        mock_signal_generator.generate_signals.return_value = []
        
        # Replace SignalGenerator constructor
        with patch.object(daily_signal_module, 'SignalGenerator', return_value=mock_signal_generator):
            # Call generate_signals function
            result = daily_signal_module.generate_signals(
                stock_pool=[],  # Empty stock pool
                strategy_type=StrategyType.RSI_REVERSAL
            )
            
            # Verify results
            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 0)


if __name__ == '__main__':
    unittest.main()