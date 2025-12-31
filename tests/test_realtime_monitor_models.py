"""
Realtime Monitor Models Tests

测试数据模型，包括Position盈亏计算、持仓天数计算等。
Property 3: PnL Calculation Accuracy
Validates: Requirements 2.2
"""

import pytest
from datetime import date, timedelta
from hypothesis import given, strategies as st, settings

from core.realtime_monitor.models import Position, StockData, BuySignal, SellSignal
from core.realtime_monitor.config import V114G_STRATEGY_PARAMS


class TestPositionPnLCalculation:
    """Position盈亏计算测试"""
    
    def test_pnl_positive_profit(self):
        """测试正盈利计算"""
        position = Position(
            code='000001',
            name='测试股票',
            cost_price=10.0,
            quantity=100,
            buy_date=date.today(),
            current_price=12.0
        )
        
        assert position.pnl == 200.0  # (12-10) * 100
        assert abs(position.pnl_pct - 0.2) < 0.0001  # 20%
    
    def test_pnl_negative_loss(self):
        """测试亏损计算"""
        position = Position(
            code='000001',
            name='测试股票',
            cost_price=10.0,
            quantity=100,
            buy_date=date.today(),
            current_price=9.0
        )
        
        assert position.pnl == -100.0  # (9-10) * 100
        assert abs(position.pnl_pct - (-0.1)) < 0.0001  # -10%
    
    def test_pnl_zero_cost_price(self):
        """测试成本价为0的边界情况"""
        position = Position(
            code='000001',
            name='测试股票',
            cost_price=0.0,
            quantity=100,
            buy_date=date.today(),
            current_price=10.0
        )
        
        assert position.pnl_pct == 0.0  # 避免除零错误
    
    # Property 3: PnL Calculation Accuracy
    # Feature: realtime-monitor, Property 3: PnL Calculation Accuracy
    @given(
        cost_price=st.floats(min_value=0.01, max_value=1000.0, allow_nan=False, allow_infinity=False),
        current_price=st.floats(min_value=0.01, max_value=1000.0, allow_nan=False, allow_infinity=False),
        quantity=st.integers(min_value=1, max_value=100000)
    )
    @settings(max_examples=100)
    def test_pnl_calculation_property(self, cost_price: float, current_price: float, quantity: int):
        """
        Property 3: PnL Calculation Accuracy
        
        For any position with cost price C and current price P,
        the PnL percentage should equal (P - C) / C × 100, with precision to 2 decimal places.
        
        **Validates: Requirements 2.2**
        """
        position = Position(
            code='000001',
            name='测试股票',
            cost_price=cost_price,
            quantity=quantity,
            buy_date=date.today(),
            current_price=current_price
        )
        
        # 验证盈亏百分比计算
        expected_pnl_pct = (current_price - cost_price) / cost_price
        assert abs(position.pnl_pct - expected_pnl_pct) < 1e-10
        
        # 验证盈亏金额计算
        expected_pnl = (current_price - cost_price) * quantity
        assert abs(position.pnl - expected_pnl) < 1e-6
        
        # 验证市值计算
        expected_market_value = current_price * quantity
        assert abs(position.market_value - expected_market_value) < 1e-6
        
        # 验证成本计算
        expected_cost_value = cost_price * quantity
        assert abs(position.cost_value - expected_cost_value) < 1e-6


class TestPositionHoldingDays:
    """Position持仓天数测试"""
    
    def test_holding_days_today(self):
        """测试今天买入的持仓天数"""
        position = Position(
            code='000001',
            name='测试股票',
            cost_price=10.0,
            quantity=100,
            buy_date=date.today(),
            current_price=10.0
        )
        
        assert position.holding_days == 0
    
    def test_holding_days_past(self):
        """测试过去买入的持仓天数"""
        buy_date = date.today() - timedelta(days=10)
        position = Position(
            code='000001',
            name='测试股票',
            cost_price=10.0,
            quantity=100,
            buy_date=buy_date,
            current_price=10.0
        )
        
        assert position.holding_days == 10
    
    @given(days=st.integers(min_value=0, max_value=365))
    @settings(max_examples=100)
    def test_holding_days_property(self, days: int):
        """测试持仓天数计算属性"""
        buy_date = date.today() - timedelta(days=days)
        position = Position(
            code='000001',
            name='测试股票',
            cost_price=10.0,
            quantity=100,
            buy_date=buy_date,
            current_price=10.0
        )
        
        assert position.holding_days == days


class TestPositionPeakPrice:
    """Position峰值价格测试"""
    
    def test_peak_price_initialization(self):
        """测试峰值价格初始化"""
        position = Position(
            code='000001',
            name='测试股票',
            cost_price=10.0,
            quantity=100,
            buy_date=date.today(),
            current_price=10.0
        )
        
        # 未设置峰值价格时，应使用成本价
        assert position.peak_price == 10.0
    
    def test_peak_price_update(self):
        """测试峰值价格更新"""
        position = Position(
            code='000001',
            name='测试股票',
            cost_price=10.0,
            quantity=100,
            buy_date=date.today(),
            current_price=10.0
        )
        
        # 更新到更高价格
        position.update_current_price(12.0)
        assert position.peak_price == 12.0
        assert position.current_price == 12.0
        
        # 价格下跌不应更新峰值
        position.update_current_price(11.0)
        assert position.peak_price == 12.0
        assert position.current_price == 11.0
    
    def test_drawdown_from_peak(self):
        """测试从峰值回撤计算"""
        position = Position(
            code='000001',
            name='测试股票',
            cost_price=10.0,
            quantity=100,
            buy_date=date.today(),
            peak_price=12.0,
            current_price=11.0
        )
        
        # 回撤 = (12 - 11) / 12 ≈ 0.0833
        expected_drawdown = (12.0 - 11.0) / 12.0
        assert abs(position.drawdown_from_peak - expected_drawdown) < 0.0001


class TestStockDataBuyConditions:
    """StockData买入条件测试"""
    
    def test_all_conditions_met(self):
        """测试所有买入条件满足"""
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
        
        conditions = stock_data.check_buy_conditions()
        
        assert conditions['ma5_above_ma20'] is True      # 10.5 > 10.0
        assert conditions['price_above_ma60'] is True    # 10.0 > 9.5
        assert conditions['rsi_in_range'] is True        # 44 <= 55 <= 70
        assert conditions['volume_ratio_ok'] is True     # 1.5 > 1.1
        assert conditions['ma20_slope_positive'] is True # 0.01 > 0
        assert conditions['price_not_too_high'] is True  # 10.0 < 10.5 * 1.05
        
        assert stock_data.count_conditions_met() == 6
    
    def test_no_conditions_met(self):
        """测试没有买入条件满足"""
        stock_data = StockData(
            code='000001',
            name='测试股票',
            current_price=10.0,
            change_pct=-0.02,
            volume=500000,
            turnover=5000000.0,
            ma5=9.5,       # MA5 < MA20
            ma10=9.8,
            ma20=10.0,
            ma60=10.5,     # Price < MA60
            rsi=30.0,      # RSI < 44
            volume_ratio=0.8,  # 量比 < 1.1
            ma20_slope=-0.01   # 斜率 < 0
        )
        
        conditions = stock_data.check_buy_conditions()
        
        assert conditions['ma5_above_ma20'] is False
        assert conditions['price_above_ma60'] is False
        assert conditions['rsi_in_range'] is False
        assert conditions['volume_ratio_ok'] is False
        assert conditions['ma20_slope_positive'] is False
        
        assert stock_data.count_conditions_met() < 6


class TestBuySignal:
    """BuySignal测试"""
    
    def test_buy_signal_price_calculations(self):
        """测试买入信号价格计算"""
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
        
        signal = BuySignal.from_stock_data(stock_data, signal_strength=100)
        
        params = V114G_STRATEGY_PARAMS
        
        # 验证价格计算
        assert signal.entry_price == 10.0
        assert abs(signal.stop_loss_price - 10.0 * (1 + params.STOP_LOSS_PCT)) < 0.01
        assert abs(signal.take_profit_price - 10.0 * (1 + params.TAKE_PROFIT_PCT)) < 0.01
        assert abs(signal.trailing_trigger_price - 10.0 * (1 + params.TRAILING_TRIGGER_PCT)) < 0.01


class TestSellSignal:
    """SellSignal测试"""
    
    def test_stop_loss_signal(self):
        """测试止损信号创建"""
        position = Position(
            code='000001',
            name='测试股票',
            cost_price=10.0,
            quantity=100,
            buy_date=date.today(),
            current_price=9.5
        )
        
        signal = SellSignal.create_stop_loss_signal(position)
        
        assert signal.signal_type == SellSignal.TYPE_STOP_LOSS
        assert signal.urgency == SellSignal.URGENCY_HIGH
        assert signal.action == SellSignal.ACTION_IMMEDIATE_SELL
    
    def test_take_profit_signal(self):
        """测试止盈信号创建"""
        position = Position(
            code='000001',
            name='测试股票',
            cost_price=10.0,
            quantity=100,
            buy_date=date.today(),
            current_price=12.5
        )
        
        signal = SellSignal.create_take_profit_signal(position)
        
        assert signal.signal_type == SellSignal.TYPE_TAKE_PROFIT
        assert signal.urgency == SellSignal.URGENCY_MEDIUM
        assert signal.action == SellSignal.ACTION_IMMEDIATE_SELL
    
    def test_trailing_stop_signal(self):
        """测试移动止盈信号创建"""
        position = Position(
            code='000001',
            name='测试股票',
            cost_price=10.0,
            quantity=100,
            buy_date=date.today(),
            peak_price=11.0,
            current_price=10.5
        )
        
        signal = SellSignal.create_trailing_stop_signal(position)
        
        assert signal.signal_type == SellSignal.TYPE_TRAILING_STOP
        assert signal.urgency == SellSignal.URGENCY_HIGH
    
    def test_timeout_signal(self):
        """测试持仓超时信号创建"""
        position = Position(
            code='000001',
            name='测试股票',
            cost_price=10.0,
            quantity=100,
            buy_date=date.today() - timedelta(days=20),
            current_price=10.0
        )
        
        signal = SellSignal.create_timeout_signal(position)
        
        assert signal.signal_type == SellSignal.TYPE_TIMEOUT
        assert signal.urgency == SellSignal.URGENCY_LOW
        assert signal.action == SellSignal.ACTION_MONITOR
