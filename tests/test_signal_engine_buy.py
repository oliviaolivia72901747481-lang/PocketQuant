"""
Signal Engine Buy Signal Tests

测试买入信号生成逻辑，包括条件检查和信号强度计算。
Property 4: Buy Signal Strength Calculation
Validates: Requirements 3.2, 3.3, 3.4
"""

import pytest
from datetime import date, datetime
from hypothesis import given, strategies as st, settings, assume

from core.realtime_monitor.signal_engine import SignalEngine
from core.realtime_monitor.models import StockData, BuySignal
from core.realtime_monitor.config import V114G_STRATEGY_PARAMS


class TestBuyConditionsCheck:
    """买入条件检查测试"""
    
    def setup_method(self):
        """测试前初始化"""
        self.engine = SignalEngine()
    
    def test_all_conditions_met(self):
        """测试所有6个条件满足"""
        stock_data = StockData(
            code='000001',
            name='测试股票',
            current_price=10.0,
            change_pct=0.02,
            volume=1000000,
            turnover=10000000.0,
            ma5=10.5,       # MA5 > MA20 ✓
            ma10=10.2,
            ma20=10.0,
            ma60=9.5,       # Price > MA60 ✓
            rsi=55.0,       # 44 <= RSI <= 70 ✓
            volume_ratio=1.5,  # > 1.1 ✓
            ma20_slope=0.01    # > 0 ✓
            # Price < MA5 * 1.05: 10.0 < 10.5 * 1.05 = 11.025 ✓
        )
        
        conditions = self.engine.check_buy_conditions(stock_data)
        
        assert all(conditions.values())
        assert sum(conditions.values()) == 6
    
    def test_five_conditions_met(self):
        """测试5个条件满足"""
        stock_data = StockData(
            code='000001',
            name='测试股票',
            current_price=10.0,
            change_pct=0.02,
            volume=1000000,
            turnover=10000000.0,
            ma5=10.5,
            ma10=10.2,
            ma20=10.0,
            ma60=9.5,
            rsi=75.0,       # RSI > 70, 不满足 ✗
            volume_ratio=1.5,
            ma20_slope=0.01
        )
        
        conditions = self.engine.check_buy_conditions(stock_data)
        
        assert sum(conditions.values()) == 5
        assert conditions['rsi_in_range'] is False
    
    def test_four_conditions_met(self):
        """测试4个条件满足（不生成信号）"""
        stock_data = StockData(
            code='000001',
            name='测试股票',
            current_price=10.0,
            change_pct=0.02,
            volume=1000000,
            turnover=10000000.0,
            ma5=10.5,
            ma10=10.2,
            ma20=10.0,
            ma60=9.5,
            rsi=75.0,       # RSI > 70 ✗
            volume_ratio=0.9,  # < 1.1 ✗
            ma20_slope=0.01
        )
        
        conditions = self.engine.check_buy_conditions(stock_data)
        
        assert sum(conditions.values()) == 4


class TestSignalStrengthCalculation:
    """信号强度计算测试"""
    
    def setup_method(self):
        """测试前初始化"""
        self.engine = SignalEngine()
    
    def test_strength_100_for_6_conditions(self):
        """测试6个条件满足时强度为100"""
        stock_data = StockData(
            code='000001',
            name='测试股票',
            current_price=10.0,
            change_pct=0.02,
            volume=1000000,
            turnover=10000000.0,
            ma5=10.5,
            ma10=10.2,
            ma20=10.0,
            ma60=9.5,
            rsi=55.0,
            volume_ratio=1.5,
            ma20_slope=0.01
        )
        
        conditions = self.engine.check_buy_conditions(stock_data)
        strength = self.engine.calculate_signal_strength(conditions, stock_data)
        
        assert strength == 100
    
    def test_strength_83_for_5_conditions(self):
        """测试5个条件满足时强度为83"""
        stock_data = StockData(
            code='000001',
            name='测试股票',
            current_price=10.0,
            change_pct=0.02,
            volume=1000000,
            turnover=10000000.0,
            ma5=10.5,
            ma10=10.2,
            ma20=10.0,
            ma60=9.5,
            rsi=75.0,       # 不满足
            volume_ratio=1.5,
            ma20_slope=0.01
        )
        
        conditions = self.engine.check_buy_conditions(stock_data)
        strength = self.engine.calculate_signal_strength(conditions, stock_data)
        
        assert strength == 83
    
    def test_strength_0_for_less_than_5_conditions(self):
        """测试少于5个条件满足时强度为0"""
        stock_data = StockData(
            code='000001',
            name='测试股票',
            current_price=10.0,
            change_pct=0.02,
            volume=1000000,
            turnover=10000000.0,
            ma5=10.5,
            ma10=10.2,
            ma20=10.0,
            ma60=9.5,
            rsi=75.0,       # 不满足
            volume_ratio=0.9,  # 不满足
            ma20_slope=0.01
        )
        
        conditions = self.engine.check_buy_conditions(stock_data)
        strength = self.engine.calculate_signal_strength(conditions, stock_data)
        
        assert strength == 0


class TestBuySignalGeneration:
    """买入信号生成测试"""
    
    def setup_method(self):
        """测试前初始化"""
        self.engine = SignalEngine()
    
    def test_generate_buy_signal_6_conditions(self):
        """测试6个条件满足时生成买入信号"""
        stock_data = StockData(
            code='000001',
            name='测试股票',
            current_price=10.0,
            change_pct=0.02,
            volume=1000000,
            turnover=10000000.0,
            ma5=10.5,
            ma10=10.2,
            ma20=10.0,
            ma60=9.5,
            rsi=55.0,
            volume_ratio=1.5,
            ma20_slope=0.01
        )
        
        signal = self.engine.generate_buy_signal(stock_data)
        
        assert signal is not None
        assert signal.signal_strength == 100
        assert signal.code == '000001'
    
    def test_generate_buy_signal_5_conditions(self):
        """测试5个条件满足时生成买入信号"""
        stock_data = StockData(
            code='000001',
            name='测试股票',
            current_price=10.0,
            change_pct=0.02,
            volume=1000000,
            turnover=10000000.0,
            ma5=10.5,
            ma10=10.2,
            ma20=10.0,
            ma60=9.5,
            rsi=75.0,       # 不满足
            volume_ratio=1.5,
            ma20_slope=0.01
        )
        
        signal = self.engine.generate_buy_signal(stock_data)
        
        assert signal is not None
        assert signal.signal_strength == 83
    
    def test_no_buy_signal_less_than_5_conditions(self):
        """测试少于5个条件满足时不生成买入信号"""
        stock_data = StockData(
            code='000001',
            name='测试股票',
            current_price=10.0,
            change_pct=0.02,
            volume=1000000,
            turnover=10000000.0,
            ma5=10.5,
            ma10=10.2,
            ma20=10.0,
            ma60=9.5,
            rsi=75.0,       # 不满足
            volume_ratio=0.9,  # 不满足
            ma20_slope=0.01
        )
        
        signal = self.engine.generate_buy_signal(stock_data)
        
        assert signal is None


class TestBuySignalStrengthProperty:
    """
    Property 4: Buy Signal Strength Calculation
    
    买入信号强度属性测试
    
    **Validates: Requirements 3.2, 3.3, 3.4**
    """
    
    def setup_method(self):
        """测试前初始化"""
        self.engine = SignalEngine()
        self.params = V114G_STRATEGY_PARAMS
    
    # Feature: realtime-monitor, Property 4: Buy Signal Strength Calculation
    @given(
        ma5=st.floats(min_value=5.0, max_value=20.0, allow_nan=False, allow_infinity=False),
        ma20=st.floats(min_value=5.0, max_value=20.0, allow_nan=False, allow_infinity=False),
        ma60=st.floats(min_value=5.0, max_value=20.0, allow_nan=False, allow_infinity=False),
        rsi=st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        volume_ratio=st.floats(min_value=0.1, max_value=5.0, allow_nan=False, allow_infinity=False),
        ma20_slope=st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        price_factor=st.floats(min_value=0.9, max_value=1.1, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=100)
    def test_buy_signal_strength_property(
        self, 
        ma5: float, 
        ma20: float, 
        ma60: float, 
        rsi: float, 
        volume_ratio: float, 
        ma20_slope: float,
        price_factor: float
    ):
        """
        Property 4: Buy Signal Strength Calculation
        
        For any stock data, if N conditions (out of 6) are met:
        - N = 6: signal strength = 100
        - N = 5: signal strength = 83
        - N < 5: no buy signal generated (strength = 0)
        
        **Validates: Requirements 3.2, 3.3, 3.4**
        """
        # 使用price_factor来生成相对于ma5的价格
        current_price = ma5 * price_factor
        
        stock_data = StockData(
            code='000001',
            name='测试股票',
            current_price=current_price,
            change_pct=0.0,
            volume=1000000,
            turnover=10000000.0,
            ma5=ma5,
            ma10=(ma5 + ma20) / 2,
            ma20=ma20,
            ma60=ma60,
            rsi=rsi,
            volume_ratio=volume_ratio,
            ma20_slope=ma20_slope
        )
        
        conditions = self.engine.check_buy_conditions(stock_data)
        conditions_met = sum(conditions.values())
        strength = self.engine.calculate_signal_strength(conditions, stock_data)
        
        # 验证Property 4
        if conditions_met == 6:
            assert strength == 100, f"Expected 100 for 6 conditions, got {strength}"
        elif conditions_met == 5:
            assert strength == 83, f"Expected 83 for 5 conditions, got {strength}"
        else:
            assert strength == 0, f"Expected 0 for {conditions_met} conditions, got {strength}"
        
        # 验证信号生成
        signal = self.engine.generate_buy_signal(stock_data)
        
        if conditions_met >= 5:
            assert signal is not None, f"Expected signal for {conditions_met} conditions"
            assert signal.signal_strength == strength
        else:
            assert signal is None, f"Expected no signal for {conditions_met} conditions"


class TestBuySignalPriceCalculations:
    """
    Property 14: Buy Signal Price Calculations
    
    买入信号价格计算属性测试
    
    **Validates: Requirements 9.1**
    """
    
    def setup_method(self):
        """测试前初始化"""
        self.engine = SignalEngine()
        self.params = V114G_STRATEGY_PARAMS
    
    def test_price_calculations_basic(self):
        """测试基本价格计算"""
        entry_price = 10.0
        prices = self.engine.calculate_buy_signal_prices(entry_price)
        
        # 验证止损价: E × (1 - 0.046) = E × 0.954
        expected_stop_loss = round(entry_price * (1 + self.params.STOP_LOSS_PCT), 2)
        assert prices['stop_loss_price'] == expected_stop_loss
        
        # 验证止盈价: E × (1 + 0.22) = E × 1.22
        expected_take_profit = round(entry_price * (1 + self.params.TAKE_PROFIT_PCT), 2)
        assert prices['take_profit_price'] == expected_take_profit
        
        # 验证移动止盈触发价: E × (1 + 0.09) = E × 1.09
        expected_trailing_trigger = round(entry_price * (1 + self.params.TRAILING_TRIGGER_PCT), 2)
        assert prices['trailing_trigger_price'] == expected_trailing_trigger
    
    # Feature: realtime-monitor, Property 14: Buy Signal Price Calculations
    @given(
        entry_price=st.floats(min_value=1.0, max_value=1000.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_buy_signal_price_calculations_property(self, entry_price: float):
        """
        Property 14: Buy Signal Price Calculations
        
        For any buy signal with entry price E:
        - stop_loss_price = E × (1 - 0.046) = E × 0.954
        - take_profit_price = E × (1 + 0.22) = E × 1.22
        - trailing_trigger_price = E × (1 + 0.09) = E × 1.09
        
        **Validates: Requirements 9.1**
        """
        prices = self.engine.calculate_buy_signal_prices(entry_price)
        
        # 验证入场价
        assert prices['entry_price'] == round(entry_price, 2)
        
        # 验证止损价: E × (1 + STOP_LOSS_PCT) = E × 0.954
        expected_stop_loss = round(entry_price * (1 + self.params.STOP_LOSS_PCT), 2)
        assert prices['stop_loss_price'] == expected_stop_loss, \
            f"Stop loss: expected {expected_stop_loss}, got {prices['stop_loss_price']}"
        
        # 验证止盈价: E × (1 + TAKE_PROFIT_PCT) = E × 1.22
        expected_take_profit = round(entry_price * (1 + self.params.TAKE_PROFIT_PCT), 2)
        assert prices['take_profit_price'] == expected_take_profit, \
            f"Take profit: expected {expected_take_profit}, got {prices['take_profit_price']}"
        
        # 验证移动止盈触发价: E × (1 + TRAILING_TRIGGER_PCT) = E × 1.09
        expected_trailing_trigger = round(entry_price * (1 + self.params.TRAILING_TRIGGER_PCT), 2)
        assert prices['trailing_trigger_price'] == expected_trailing_trigger, \
            f"Trailing trigger: expected {expected_trailing_trigger}, got {prices['trailing_trigger_price']}"
        
        # 验证价格关系: stop_loss < entry < trailing_trigger < take_profit
        assert prices['stop_loss_price'] < prices['entry_price'], \
            "Stop loss should be less than entry price"
        assert prices['entry_price'] < prices['trailing_trigger_price'], \
            "Entry price should be less than trailing trigger"
        assert prices['trailing_trigger_price'] < prices['take_profit_price'], \
            "Trailing trigger should be less than take profit"


class TestSellRecommendation:
    """卖出建议测试"""
    
    def setup_method(self):
        """测试前初始化"""
        self.engine = SignalEngine()
    
    def test_stop_loss_recommendation(self):
        """测试止损信号建议"""
        from core.realtime_monitor.models import SellSignal
        
        sell_signal = SellSignal(
            code='000001',
            name='测试股票',
            current_price=9.54,
            cost_price=10.0,
            pnl_pct=-0.046,
            signal_type=SellSignal.TYPE_STOP_LOSS,
            urgency=SellSignal.URGENCY_HIGH,
            reason='触发止损线',
            action=SellSignal.ACTION_IMMEDIATE_SELL,
        )
        
        recommendation = self.engine.get_sell_recommendation(sell_signal)
        
        assert 'urgency_description' in recommendation
        assert 'action_description' in recommendation
        assert 'reason_explanation' in recommendation
        assert '高' in recommendation['urgency_description']
        assert '立即卖出' in recommendation['action_description']
    
    def test_take_profit_recommendation(self):
        """测试止盈信号建议"""
        from core.realtime_monitor.models import SellSignal
        
        sell_signal = SellSignal(
            code='000001',
            name='测试股票',
            current_price=12.2,
            cost_price=10.0,
            pnl_pct=0.22,
            signal_type=SellSignal.TYPE_TAKE_PROFIT,
            urgency=SellSignal.URGENCY_MEDIUM,
            reason='达到止盈目标',
            action=SellSignal.ACTION_IMMEDIATE_SELL,
        )
        
        recommendation = self.engine.get_sell_recommendation(sell_signal)
        
        assert '中' in recommendation['urgency_description']
        assert '止盈' in recommendation['reason_explanation']
    
    def test_rsi_overbought_recommendation(self):
        """测试RSI超买信号建议"""
        from core.realtime_monitor.models import SellSignal
        
        sell_signal = SellSignal(
            code='000001',
            name='测试股票',
            current_price=11.0,
            cost_price=10.0,
            pnl_pct=0.10,
            signal_type=SellSignal.TYPE_RSI_OVERBOUGHT,
            urgency=SellSignal.URGENCY_MEDIUM,
            reason='RSI超买',
            action=SellSignal.ACTION_REDUCE_POSITION,
        )
        
        recommendation = self.engine.get_sell_recommendation(sell_signal)
        
        assert '减仓' in recommendation['action_description']
        assert 'RSI' in recommendation['reason_explanation']
    
    def test_timeout_recommendation(self):
        """测试持仓超时信号建议"""
        from core.realtime_monitor.models import SellSignal
        
        sell_signal = SellSignal(
            code='000001',
            name='测试股票',
            current_price=10.5,
            cost_price=10.0,
            pnl_pct=0.05,
            signal_type=SellSignal.TYPE_TIMEOUT,
            urgency=SellSignal.URGENCY_LOW,
            reason='持仓超时',
            action=SellSignal.ACTION_MONITOR,
        )
        
        recommendation = self.engine.get_sell_recommendation(sell_signal)
        
        assert '低' in recommendation['urgency_description']
        assert '观察' in recommendation['action_description']
