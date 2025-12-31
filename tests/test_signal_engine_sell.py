"""
Signal Engine Sell Signal Tests

测试卖出信号生成逻辑，包括止损、止盈、移动止盈、RSI超买、趋势反转、持仓超时。
Properties 5-10: Sell Signal Generation
Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5, 4.6
"""

import pytest
from datetime import date, timedelta
from hypothesis import given, strategies as st, settings, assume

from core.realtime_monitor.signal_engine import SignalEngine
from core.realtime_monitor.models import Position, StockData, SellSignal
from core.realtime_monitor.config import V114G_STRATEGY_PARAMS


def create_stock_data(
    current_price: float = 10.0,
    ma5: float = 10.0,
    ma20: float = 10.0,
    rsi: float = 50.0
) -> StockData:
    """创建测试用股票数据"""
    return StockData(
        code='000001',
        name='测试股票',
        current_price=current_price,
        change_pct=0.0,
        volume=1000000,
        turnover=10000000.0,
        ma5=ma5,
        ma10=10.0,
        ma20=ma20,
        ma60=9.5,
        rsi=rsi,
        volume_ratio=1.5,
        ma20_slope=0.01
    )


class TestStopLossSignal:
    """
    Property 5: Stop Loss Signal Generation
    
    止损信号测试
    
    **Validates: Requirements 4.1**
    """
    
    def setup_method(self):
        """测试前初始化"""
        self.engine = SignalEngine()
        self.params = V114G_STRATEGY_PARAMS
    
    def test_stop_loss_triggered(self):
        """测试止损触发"""
        position = Position(
            code='000001',
            name='测试股票',
            cost_price=10.0,
            quantity=100,
            buy_date=date.today(),
            current_price=9.5  # -5% < -4.6%
        )
        
        assert self.engine.check_stop_loss(position) is True
    
    def test_stop_loss_not_triggered(self):
        """测试止损未触发"""
        position = Position(
            code='000001',
            name='测试股票',
            cost_price=10.0,
            quantity=100,
            buy_date=date.today(),
            current_price=9.6  # -4% > -4.6%
        )
        
        assert self.engine.check_stop_loss(position) is False
    
    def test_stop_loss_boundary(self):
        """测试止损边界值"""
        # 精确到-4.6%
        cost_price = 10.0
        stop_loss_price = cost_price * (1 + self.params.STOP_LOSS_PCT)  # 9.54
        
        position = Position(
            code='000001',
            name='测试股票',
            cost_price=cost_price,
            quantity=100,
            buy_date=date.today(),
            current_price=stop_loss_price
        )
        
        assert self.engine.check_stop_loss(position) is True
    
    # Feature: realtime-monitor, Property 5: Stop Loss Signal Generation
    @given(
        cost_price=st.floats(min_value=1.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        # Use integers for loss percentage to avoid floating point precision issues at boundaries
        loss_pct_int=st.integers(min_value=-20, max_value=0)
    )
    @settings(max_examples=100)
    def test_stop_loss_property(self, cost_price: float, loss_pct_int: int):
        """
        Property 5: Stop Loss Signal Generation
        
        For any position where (current_price - cost_price) / cost_price <= -0.046,
        a stop-loss sell signal with urgency "high" must be generated.
        
        **Validates: Requirements 4.1**
        """
        # Convert integer percentage to float (e.g., -5 -> -0.05)
        # Avoid exact boundary value -4.6% by using integer percentages
        loss_pct = loss_pct_int / 100.0
        current_price = cost_price * (1 + loss_pct)
        
        position = Position(
            code='000001',
            name='测试股票',
            cost_price=cost_price,
            quantity=100,
            buy_date=date.today(),
            current_price=current_price
        )
        
        # Use the actual pnl_pct from position to avoid floating point issues
        should_trigger = position.pnl_pct <= self.params.STOP_LOSS_PCT
        
        assert self.engine.check_stop_loss(position) == should_trigger
        
        if should_trigger:
            stock_data = create_stock_data(current_price=current_price)
            signals = self.engine.generate_sell_signals(position, stock_data)
            stop_loss_signals = [s for s in signals if s.signal_type == SellSignal.TYPE_STOP_LOSS]
            
            assert len(stop_loss_signals) == 1
            assert stop_loss_signals[0].urgency == SellSignal.URGENCY_HIGH


class TestTakeProfitSignal:
    """
    Property 6: Take Profit Signal Generation
    
    止盈信号测试
    
    **Validates: Requirements 4.2**
    """
    
    def setup_method(self):
        """测试前初始化"""
        self.engine = SignalEngine()
        self.params = V114G_STRATEGY_PARAMS
    
    def test_take_profit_triggered(self):
        """测试止盈触发"""
        position = Position(
            code='000001',
            name='测试股票',
            cost_price=10.0,
            quantity=100,
            buy_date=date.today(),
            current_price=12.5  # +25% >= +22%
        )
        
        assert self.engine.check_take_profit(position) is True
    
    def test_take_profit_not_triggered(self):
        """测试止盈未触发"""
        position = Position(
            code='000001',
            name='测试股票',
            cost_price=10.0,
            quantity=100,
            buy_date=date.today(),
            current_price=12.0  # +20% < +22%
        )
        
        assert self.engine.check_take_profit(position) is False
    
    # Feature: realtime-monitor, Property 6: Take Profit Signal Generation
    @given(
        cost_price=st.floats(min_value=1.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        # Use integers for profit percentage to avoid floating point precision issues
        profit_pct_int=st.integers(min_value=0, max_value=50)
    )
    @settings(max_examples=100)
    def test_take_profit_property(self, cost_price: float, profit_pct_int: int):
        """
        Property 6: Take Profit Signal Generation
        
        For any position where (current_price - cost_price) / cost_price >= 0.22,
        a take-profit sell signal must be generated.
        
        **Validates: Requirements 4.2**
        """
        # Convert integer percentage to float (e.g., 22 -> 0.22)
        profit_pct = profit_pct_int / 100.0
        current_price = cost_price * (1 + profit_pct)
        
        position = Position(
            code='000001',
            name='测试股票',
            cost_price=cost_price,
            quantity=100,
            buy_date=date.today(),
            current_price=current_price
        )
        
        # Use the actual pnl_pct from position to avoid floating point issues
        should_trigger = position.pnl_pct >= self.params.TAKE_PROFIT_PCT
        
        assert self.engine.check_take_profit(position) == should_trigger
        
        if should_trigger:
            stock_data = create_stock_data(current_price=current_price)
            signals = self.engine.generate_sell_signals(position, stock_data)
            take_profit_signals = [s for s in signals if s.signal_type == SellSignal.TYPE_TAKE_PROFIT]
            
            assert len(take_profit_signals) == 1


class TestTrailingStopSignal:
    """
    Property 7: Trailing Stop Signal Generation
    
    移动止盈信号测试
    
    **Validates: Requirements 4.3**
    """
    
    def setup_method(self):
        """测试前初始化"""
        self.engine = SignalEngine()
        self.params = V114G_STRATEGY_PARAMS
    
    def test_trailing_stop_triggered(self):
        """测试移动止盈触发"""
        # 成本10，峰值11（+10%），当前10.6（从峰值回撤3.6%）
        position = Position(
            code='000001',
            name='测试股票',
            cost_price=10.0,
            quantity=100,
            buy_date=date.today(),
            peak_price=11.0,  # +10% >= +9%
            current_price=10.6  # 从峰值回撤 (11-10.6)/11 = 3.6% >= 2.8%
        )
        
        assert self.engine.check_trailing_stop(position) is True
    
    def test_trailing_stop_not_triggered_no_peak(self):
        """测试移动止盈未触发（峰值未达到）"""
        position = Position(
            code='000001',
            name='测试股票',
            cost_price=10.0,
            quantity=100,
            buy_date=date.today(),
            peak_price=10.5,  # +5% < +9%
            current_price=10.2
        )
        
        assert self.engine.check_trailing_stop(position) is False
    
    def test_trailing_stop_not_triggered_no_drawdown(self):
        """测试移动止盈未触发（回撤不足）"""
        position = Position(
            code='000001',
            name='测试股票',
            cost_price=10.0,
            quantity=100,
            buy_date=date.today(),
            peak_price=11.0,  # +10% >= +9%
            current_price=10.8  # 从峰值回撤 (11-10.8)/11 = 1.8% < 2.8%
        )
        
        assert self.engine.check_trailing_stop(position) is False
    
    # Feature: realtime-monitor, Property 7: Trailing Stop Signal Generation
    @given(
        cost_price=st.floats(min_value=1.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        # Use integers for percentages to avoid floating point precision issues at boundaries
        peak_pct_int=st.integers(min_value=0, max_value=30),
        drawdown_pct_int=st.integers(min_value=0, max_value=10)
    )
    @settings(max_examples=100)
    def test_trailing_stop_property(self, cost_price: float, peak_pct_int: int, drawdown_pct_int: int):
        """
        Property 7: Trailing Stop Signal Generation
        
        For any position where:
        1. Peak profit reached >= 9% (peak_price >= cost_price × 1.09)
        2. Current price retraced >= 2.8% from peak (current_price <= peak_price × 0.972)
        A trailing-stop sell signal must be generated.
        
        **Validates: Requirements 4.3**
        """
        # Convert integer percentages to float (e.g., 9 -> 0.09, 3 -> 0.03)
        peak_pct = peak_pct_int / 100.0
        drawdown_pct = drawdown_pct_int / 100.0
        
        peak_price = cost_price * (1 + peak_pct)
        current_price = peak_price * (1 - drawdown_pct)
        
        position = Position(
            code='000001',
            name='测试股票',
            cost_price=cost_price,
            quantity=100,
            buy_date=date.today(),
            peak_price=peak_price,
            current_price=current_price
        )
        
        # Use the actual values from position to avoid floating point issues
        # 条件1: 峰值盈利 >= 9%
        peak_triggered = position.peak_pnl_pct >= self.params.TRAILING_TRIGGER_PCT
        # 条件2: 从峰值回撤 >= 2.8%
        drawdown_triggered = position.drawdown_from_peak >= self.params.TRAILING_STOP_PCT
        
        should_trigger = peak_triggered and drawdown_triggered
        
        assert self.engine.check_trailing_stop(position) == should_trigger


class TestRSIOverboughtSignal:
    """
    Property 8: RSI Overbought Signal Generation
    
    RSI超买信号测试
    
    **Validates: Requirements 4.4**
    """
    
    def setup_method(self):
        """测试前初始化"""
        self.engine = SignalEngine()
        self.params = V114G_STRATEGY_PARAMS
    
    def test_rsi_overbought_triggered(self):
        """测试RSI超买触发"""
        position = Position(
            code='000001',
            name='测试股票',
            cost_price=10.0,
            quantity=100,
            buy_date=date.today(),
            current_price=11.0  # 盈利
        )
        
        assert self.engine.check_rsi_overbought(position, rsi=85.0) is True
    
    def test_rsi_overbought_not_triggered_low_rsi(self):
        """测试RSI超买未触发（RSI不够高）"""
        position = Position(
            code='000001',
            name='测试股票',
            cost_price=10.0,
            quantity=100,
            buy_date=date.today(),
            current_price=11.0  # 盈利
        )
        
        assert self.engine.check_rsi_overbought(position, rsi=75.0) is False
    
    def test_rsi_overbought_not_triggered_loss(self):
        """测试RSI超买未触发（亏损状态）"""
        position = Position(
            code='000001',
            name='测试股票',
            cost_price=10.0,
            quantity=100,
            buy_date=date.today(),
            current_price=9.5  # 亏损
        )
        
        assert self.engine.check_rsi_overbought(position, rsi=85.0) is False
    
    # Feature: realtime-monitor, Property 8: RSI Overbought Signal Generation
    @given(
        cost_price=st.floats(min_value=1.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        # Use integers for pnl percentage to avoid floating point precision issues
        pnl_pct_int=st.integers(min_value=-10, max_value=20),
        rsi=st.floats(min_value=50.0, max_value=100.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_rsi_overbought_property(self, cost_price: float, pnl_pct_int: int, rsi: float):
        """
        Property 8: RSI Overbought Signal Generation
        
        For any position where RSI > 80 AND position is profitable (pnl_pct > 0),
        an RSI-overbought sell signal must be generated.
        
        **Validates: Requirements 4.4**
        """
        # Convert integer percentage to float (e.g., 5 -> 0.05)
        pnl_pct = pnl_pct_int / 100.0
        current_price = cost_price * (1 + pnl_pct)
        
        position = Position(
            code='000001',
            name='测试股票',
            cost_price=cost_price,
            quantity=100,
            buy_date=date.today(),
            current_price=current_price
        )
        
        # Use the actual pnl_pct from position to avoid floating point issues
        should_trigger = rsi > self.params.RSI_OVERBOUGHT and position.pnl_pct > 0
        
        assert self.engine.check_rsi_overbought(position, rsi) == should_trigger


class TestTrendReversalSignal:
    """
    Property 9: Trend Reversal Signal Generation
    
    趋势反转信号测试
    
    **Validates: Requirements 4.5**
    """
    
    def setup_method(self):
        """测试前初始化"""
        self.engine = SignalEngine()
    
    def test_trend_reversal_triggered(self):
        """测试趋势反转触发"""
        position = Position(
            code='000001',
            name='测试股票',
            cost_price=10.0,
            quantity=100,
            buy_date=date.today(),
            current_price=9.5  # 亏损
        )
        
        # MA5 < MA20 且亏损
        assert self.engine.check_trend_reversal(position, ma5=9.8, ma20=10.0) is True
    
    def test_trend_reversal_not_triggered_ma5_above(self):
        """测试趋势反转未触发（MA5 > MA20）"""
        position = Position(
            code='000001',
            name='测试股票',
            cost_price=10.0,
            quantity=100,
            buy_date=date.today(),
            current_price=9.5  # 亏损
        )
        
        assert self.engine.check_trend_reversal(position, ma5=10.2, ma20=10.0) is False
    
    def test_trend_reversal_not_triggered_profit(self):
        """测试趋势反转未触发（盈利状态）"""
        position = Position(
            code='000001',
            name='测试股票',
            cost_price=10.0,
            quantity=100,
            buy_date=date.today(),
            current_price=10.5  # 盈利
        )
        
        assert self.engine.check_trend_reversal(position, ma5=9.8, ma20=10.0) is False
    
    # Feature: realtime-monitor, Property 9: Trend Reversal Signal Generation
    @given(
        cost_price=st.floats(min_value=1.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        # Use integers for pnl percentage to avoid floating point precision issues
        pnl_pct_int=st.integers(min_value=-10, max_value=10),
        ma5=st.floats(min_value=5.0, max_value=15.0, allow_nan=False, allow_infinity=False),
        ma20=st.floats(min_value=5.0, max_value=15.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=100)
    def test_trend_reversal_property(self, cost_price: float, pnl_pct_int: int, ma5: float, ma20: float):
        """
        Property 9: Trend Reversal Signal Generation
        
        For any position where MA5 < MA20 AND position is at loss (pnl_pct < 0),
        a trend-reversal sell signal must be generated.
        
        **Validates: Requirements 4.5**
        """
        # Convert integer percentage to float (e.g., -5 -> -0.05)
        pnl_pct = pnl_pct_int / 100.0
        current_price = cost_price * (1 + pnl_pct)
        
        position = Position(
            code='000001',
            name='测试股票',
            cost_price=cost_price,
            quantity=100,
            buy_date=date.today(),
            current_price=current_price
        )
        
        # Use the actual pnl_pct from position to avoid floating point issues
        should_trigger = ma5 < ma20 and position.pnl_pct < 0
        
        assert self.engine.check_trend_reversal(position, ma5, ma20) == should_trigger


class TestTimeoutSignal:
    """
    Property 10: Timeout Signal Generation
    
    持仓超时信号测试
    
    **Validates: Requirements 4.6**
    """
    
    def setup_method(self):
        """测试前初始化"""
        self.engine = SignalEngine()
        self.params = V114G_STRATEGY_PARAMS
    
    def test_timeout_triggered(self):
        """测试持仓超时触发"""
        position = Position(
            code='000001',
            name='测试股票',
            cost_price=10.0,
            quantity=100,
            buy_date=date.today() - timedelta(days=15),
            current_price=10.0
        )
        
        assert self.engine.check_timeout(position) is True
    
    def test_timeout_not_triggered(self):
        """测试持仓超时未触发"""
        position = Position(
            code='000001',
            name='测试股票',
            cost_price=10.0,
            quantity=100,
            buy_date=date.today() - timedelta(days=10),
            current_price=10.0
        )
        
        assert self.engine.check_timeout(position) is False
    
    def test_timeout_boundary(self):
        """测试持仓超时边界值"""
        # 正好14天，不触发
        position_14 = Position(
            code='000001',
            name='测试股票',
            cost_price=10.0,
            quantity=100,
            buy_date=date.today() - timedelta(days=14),
            current_price=10.0
        )
        assert self.engine.check_timeout(position_14) is False
        
        # 正好15天，触发
        position_15 = Position(
            code='000001',
            name='测试股票',
            cost_price=10.0,
            quantity=100,
            buy_date=date.today() - timedelta(days=15),
            current_price=10.0
        )
        assert self.engine.check_timeout(position_15) is True
    
    # Feature: realtime-monitor, Property 10: Timeout Signal Generation
    @given(
        holding_days=st.integers(min_value=0, max_value=30)
    )
    @settings(max_examples=100)
    def test_timeout_property(self, holding_days: int):
        """
        Property 10: Timeout Signal Generation
        
        For any position where holding_days >= 15,
        a timeout sell signal must be generated.
        
        **Validates: Requirements 4.6**
        """
        position = Position(
            code='000001',
            name='测试股票',
            cost_price=10.0,
            quantity=100,
            buy_date=date.today() - timedelta(days=holding_days),
            current_price=10.0
        )
        
        should_trigger = holding_days >= self.params.MAX_HOLDING_DAYS
        
        assert self.engine.check_timeout(position) == should_trigger
        
        if should_trigger:
            stock_data = create_stock_data()
            signals = self.engine.generate_sell_signals(position, stock_data)
            timeout_signals = [s for s in signals if s.signal_type == SellSignal.TYPE_TIMEOUT]
            
            assert len(timeout_signals) == 1
            assert timeout_signals[0].urgency == SellSignal.URGENCY_LOW


class TestSellSignalGeneration:
    """卖出信号生成综合测试"""
    
    def setup_method(self):
        """测试前初始化"""
        self.engine = SignalEngine()
    
    def test_multiple_signals_generated(self):
        """测试多个卖出信号同时生成"""
        # 创建一个同时触发止损和趋势反转的持仓
        position = Position(
            code='000001',
            name='测试股票',
            cost_price=10.0,
            quantity=100,
            buy_date=date.today(),
            current_price=9.5  # -5%
        )
        
        stock_data = create_stock_data(
            current_price=9.5,
            ma5=9.3,   # MA5 < MA20
            ma20=9.8
        )
        
        signals = self.engine.generate_sell_signals(position, stock_data)
        
        # 应该同时有止损和趋势反转信号
        signal_types = [s.signal_type for s in signals]
        assert SellSignal.TYPE_STOP_LOSS in signal_types
        assert SellSignal.TYPE_TREND_REVERSAL in signal_types
    
    def test_highest_priority_signal(self):
        """测试获取最高优先级信号"""
        position = Position(
            code='000001',
            name='测试股票',
            cost_price=10.0,
            quantity=100,
            buy_date=date.today() - timedelta(days=20),  # 超时
            current_price=9.5  # 止损
        )
        
        stock_data = create_stock_data(current_price=9.5)
        
        signal = self.engine.get_highest_priority_sell_signal(position, stock_data)
        
        # 止损优先级最高
        assert signal is not None
        assert signal.signal_type == SellSignal.TYPE_STOP_LOSS
    
    def test_no_sell_signal(self):
        """测试无卖出信号"""
        position = Position(
            code='000001',
            name='测试股票',
            cost_price=10.0,
            quantity=100,
            buy_date=date.today(),
            current_price=10.5  # 小幅盈利
        )
        
        stock_data = create_stock_data(
            current_price=10.5,
            ma5=10.6,
            ma20=10.4,
            rsi=55.0
        )
        
        signals = self.engine.generate_sell_signals(position, stock_data)
        
        assert len(signals) == 0
