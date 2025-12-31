"""
Realtime Monitor Integration Tests

集成测试，测试完整的买入信号生成流程、卖出信号生成流程和数据刷新机制。
Task 10.1: 编写集成测试
"""

import pytest
from datetime import date, datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from core.realtime_monitor.monitor import RealtimeMonitor
from core.realtime_monitor.signal_engine import SignalEngine
from core.realtime_monitor.data_fetcher import DataFetcher, MarketStatus
from core.realtime_monitor.models import Position, StockData, BuySignal, SellSignal
from core.realtime_monitor.config import V114G_STRATEGY_PARAMS, MONITOR_CONFIG


class TestBuySignalGenerationFlow:
    """
    测试完整的买入信号生成流程
    
    流程: 添加股票到监控列表 -> 获取股票数据 -> 检查买入条件 -> 生成买入信号
    """
    
    def setup_method(self):
        """测试前初始化"""
        self.monitor = RealtimeMonitor()
        self.engine = SignalEngine()
    
    def test_complete_buy_signal_flow_6_conditions(self):
        """测试完整买入信号流程 - 6个条件满足"""
        # Step 1: 添加股票到监控列表
        code = '000001'
        result = self.monitor.add_to_watchlist(code)
        assert result is True
        assert code in self.monitor.watchlist
        
        # Step 2: 创建满足所有买入条件的股票数据
        stock_data = StockData(
            code=code,
            name='平安银行',
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
        
        # Step 3: 检查买入条件
        conditions = self.engine.check_buy_conditions(stock_data)
        assert all(conditions.values()), "All 6 conditions should be met"
        
        # Step 4: 生成买入信号
        signal = self.engine.generate_buy_signal(stock_data)
        
        # 验证信号
        assert signal is not None
        assert signal.code == code
        assert signal.signal_strength == 100
        assert signal.entry_price == 10.0
        assert signal.stop_loss_price == round(10.0 * 0.954, 2)
        assert signal.take_profit_price == round(10.0 * 1.22, 2)
        assert signal.trailing_trigger_price == round(10.0 * 1.09, 2)
    
    def test_complete_buy_signal_flow_5_conditions(self):
        """测试完整买入信号流程 - 5个条件满足"""
        code = '300001'
        self.monitor.add_to_watchlist(code)
        
        # 创建满足5个条件的股票数据（RSI超出范围）
        stock_data = StockData(
            code=code,
            name='特锐德',
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
        
        signal = self.engine.generate_buy_signal(stock_data)
        
        assert signal is not None
        assert signal.signal_strength == 83
    
    def test_no_buy_signal_when_conditions_insufficient(self):
        """测试条件不足时不生成买入信号"""
        code = '600001'
        self.monitor.add_to_watchlist(code)
        
        # 创建只满足4个条件的股票数据
        stock_data = StockData(
            code=code,
            name='邯郸钢铁',
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
        assert sum(conditions.values()) == 4
        
        signal = self.engine.generate_buy_signal(stock_data)
        assert signal is None


class TestSellSignalGenerationFlow:
    """
    测试完整的卖出信号生成流程
    
    流程: 添加持仓 -> 更新价格 -> 检查卖出条件 -> 生成卖出信号
    """
    
    def setup_method(self):
        """测试前初始化"""
        self.monitor = RealtimeMonitor()
        self.engine = SignalEngine()
    
    def test_stop_loss_signal_flow(self):
        """测试止损信号生成流程"""
        # Step 1: 添加持仓
        code = '000001'
        self.monitor.add_position(
            code=code,
            name='平安银行',
            cost_price=10.0,
            quantity=100
        )
        
        # Step 2: 更新价格（触发止损）
        stop_loss_price = 10.0 * (1 + V114G_STRATEGY_PARAMS.STOP_LOSS_PCT)  # 9.54
        self.monitor.update_position_price(code, stop_loss_price)
        
        position = self.monitor.get_position(code)
        assert position.pnl_pct <= V114G_STRATEGY_PARAMS.STOP_LOSS_PCT
        
        # Step 3: 创建股票数据
        stock_data = StockData(
            code=code,
            name='平安银行',
            current_price=stop_loss_price,
            change_pct=-0.046,
            volume=1000000,
            turnover=10000000.0,
            ma5=10.0,
            ma10=10.0,
            ma20=10.0,
            ma60=9.5,
            rsi=50.0,
            volume_ratio=1.5,
            ma20_slope=0.01
        )
        
        # Step 4: 生成卖出信号
        signals = self.engine.generate_sell_signals(position, stock_data)
        
        # 验证止损信号
        stop_loss_signals = [s for s in signals if s.signal_type == SellSignal.TYPE_STOP_LOSS]
        assert len(stop_loss_signals) == 1
        assert stop_loss_signals[0].urgency == SellSignal.URGENCY_HIGH
        assert stop_loss_signals[0].action == SellSignal.ACTION_IMMEDIATE_SELL
    
    def test_take_profit_signal_flow(self):
        """测试止盈信号生成流程"""
        code = '300001'
        self.monitor.add_position(
            code=code,
            name='特锐德',
            cost_price=10.0,
            quantity=100
        )
        
        # 更新价格（触发止盈，使用略高于阈值的价格避免浮点精度问题）
        take_profit_price = 12.3  # +23% > +22%
        self.monitor.update_position_price(code, take_profit_price)
        
        position = self.monitor.get_position(code)
        
        stock_data = StockData(
            code=code,
            name='特锐德',
            current_price=take_profit_price,
            change_pct=0.22,
            volume=1000000,
            turnover=10000000.0,
            ma5=12.0,
            ma10=11.5,
            ma20=11.0,
            ma60=10.0,
            rsi=70.0,
            volume_ratio=1.5,
            ma20_slope=0.01
        )
        
        signals = self.engine.generate_sell_signals(position, stock_data)
        
        take_profit_signals = [s for s in signals if s.signal_type == SellSignal.TYPE_TAKE_PROFIT]
        assert len(take_profit_signals) == 1
        assert take_profit_signals[0].urgency == SellSignal.URGENCY_MEDIUM

    
    def test_trailing_stop_signal_flow(self):
        """测试移动止盈信号生成流程"""
        code = '600001'
        self.monitor.add_position(
            code=code,
            name='邯郸钢铁',
            cost_price=10.0,
            quantity=100
        )
        
        # Step 1: 价格上涨到触发移动止盈阈值 (+9%)
        peak_price = 10.0 * 1.10  # 11.0 (+10%)
        self.monitor.update_position_price(code, peak_price)
        
        position = self.monitor.get_position(code)
        assert position.peak_price == peak_price
        
        # Step 2: 价格回撤超过2.8%
        drawdown_price = peak_price * (1 - 0.03)  # 从峰值回撤3%
        self.monitor.update_position_price(code, drawdown_price)
        
        position = self.monitor.get_position(code)
        assert position.peak_price == peak_price  # 峰值不变
        assert position.current_price == drawdown_price
        
        stock_data = StockData(
            code=code,
            name='邯郸钢铁',
            current_price=drawdown_price,
            change_pct=0.067,
            volume=1000000,
            turnover=10000000.0,
            ma5=10.8,
            ma10=10.5,
            ma20=10.2,
            ma60=9.5,
            rsi=60.0,
            volume_ratio=1.5,
            ma20_slope=0.01
        )
        
        signals = self.engine.generate_sell_signals(position, stock_data)
        
        trailing_signals = [s for s in signals if s.signal_type == SellSignal.TYPE_TRAILING_STOP]
        assert len(trailing_signals) == 1
        assert trailing_signals[0].urgency == SellSignal.URGENCY_HIGH
    
    def test_rsi_overbought_signal_flow(self):
        """测试RSI超买信号生成流程"""
        code = '000002'
        self.monitor.add_position(
            code=code,
            name='万科A',
            cost_price=10.0,
            quantity=100
        )
        
        # 更新价格（盈利状态）
        self.monitor.update_position_price(code, 11.0)
        
        position = self.monitor.get_position(code)
        
        stock_data = StockData(
            code=code,
            name='万科A',
            current_price=11.0,
            change_pct=0.10,
            volume=1000000,
            turnover=10000000.0,
            ma5=10.8,
            ma10=10.5,
            ma20=10.2,
            ma60=9.5,
            rsi=85.0,  # RSI > 80
            volume_ratio=1.5,
            ma20_slope=0.01
        )
        
        signals = self.engine.generate_sell_signals(position, stock_data)
        
        rsi_signals = [s for s in signals if s.signal_type == SellSignal.TYPE_RSI_OVERBOUGHT]
        assert len(rsi_signals) == 1
        assert rsi_signals[0].action == SellSignal.ACTION_REDUCE_POSITION
    
    def test_trend_reversal_signal_flow(self):
        """测试趋势反转信号生成流程"""
        code = '300002'
        self.monitor.add_position(
            code=code,
            name='神州泰岳',
            cost_price=10.0,
            quantity=100
        )
        
        # 更新价格（亏损状态）
        self.monitor.update_position_price(code, 9.8)
        
        position = self.monitor.get_position(code)
        
        stock_data = StockData(
            code=code,
            name='神州泰岳',
            current_price=9.8,
            change_pct=-0.02,
            volume=1000000,
            turnover=10000000.0,
            ma5=9.7,   # MA5 < MA20
            ma10=9.9,
            ma20=10.0,
            ma60=9.5,
            rsi=45.0,
            volume_ratio=1.5,
            ma20_slope=-0.01
        )
        
        signals = self.engine.generate_sell_signals(position, stock_data)
        
        reversal_signals = [s for s in signals if s.signal_type == SellSignal.TYPE_TREND_REVERSAL]
        assert len(reversal_signals) == 1

    
    def test_timeout_signal_flow(self):
        """测试持仓超时信号生成流程"""
        code = '600002'
        
        # 添加持仓（买入日期为15天前）
        buy_date = date.today() - timedelta(days=15)
        self.monitor.add_position(
            code=code,
            name='齐鲁石化',
            cost_price=10.0,
            quantity=100,
            buy_date=buy_date
        )
        
        self.monitor.update_position_price(code, 10.5)
        
        position = self.monitor.get_position(code)
        assert position.holding_days >= 15
        
        stock_data = StockData(
            code=code,
            name='齐鲁石化',
            current_price=10.5,
            change_pct=0.05,
            volume=1000000,
            turnover=10000000.0,
            ma5=10.4,
            ma10=10.3,
            ma20=10.2,
            ma60=9.5,
            rsi=55.0,
            volume_ratio=1.5,
            ma20_slope=0.01
        )
        
        signals = self.engine.generate_sell_signals(position, stock_data)
        
        timeout_signals = [s for s in signals if s.signal_type == SellSignal.TYPE_TIMEOUT]
        assert len(timeout_signals) == 1
        assert timeout_signals[0].urgency == SellSignal.URGENCY_LOW
    
    def test_multiple_sell_signals_priority(self):
        """测试多个卖出信号的优先级"""
        code = '000003'
        
        # 添加持仓（超时 + 止损）
        buy_date = date.today() - timedelta(days=20)
        self.monitor.add_position(
            code=code,
            name='PT金田A',
            cost_price=10.0,
            quantity=100,
            buy_date=buy_date
        )
        
        # 触发止损
        self.monitor.update_position_price(code, 9.5)
        
        position = self.monitor.get_position(code)
        
        stock_data = StockData(
            code=code,
            name='PT金田A',
            current_price=9.5,
            change_pct=-0.05,
            volume=1000000,
            turnover=10000000.0,
            ma5=9.6,
            ma10=9.8,
            ma20=10.0,
            ma60=9.5,
            rsi=40.0,
            volume_ratio=1.5,
            ma20_slope=-0.01
        )
        
        signals = self.engine.generate_sell_signals(position, stock_data)
        
        # 应该有多个信号
        assert len(signals) >= 2
        
        # 获取最高优先级信号
        highest_signal = self.engine.get_highest_priority_sell_signal(position, stock_data)
        
        # 止损优先级最高
        assert highest_signal.signal_type == SellSignal.TYPE_STOP_LOSS


class TestDataRefreshMechanism:
    """
    测试数据刷新机制
    """
    
    def setup_method(self):
        """测试前初始化"""
        self.fetcher = DataFetcher()
    
    def test_market_status_during_trading_hours(self):
        """测试交易时间内的市场状态"""
        # 模拟上午交易时间
        morning_time = datetime(2025, 12, 31, 10, 0, 0)  # 周三 10:00
        status = self.fetcher.get_market_status(morning_time)
        
        assert status.is_open is True
        assert status.status == MarketStatus.STATUS_OPEN
        
        # 模拟下午交易时间
        afternoon_time = datetime(2025, 12, 31, 14, 0, 0)  # 周三 14:00
        status = self.fetcher.get_market_status(afternoon_time)
        
        assert status.is_open is True
        assert status.status == MarketStatus.STATUS_OPEN
    
    def test_market_status_outside_trading_hours(self):
        """测试非交易时间的市场状态"""
        # 盘前
        pre_market = datetime(2025, 12, 31, 9, 0, 0)
        status = self.fetcher.get_market_status(pre_market)
        assert status.is_open is False
        assert status.status == MarketStatus.STATUS_PRE_MARKET
        
        # 午休
        lunch_break = datetime(2025, 12, 31, 12, 0, 0)
        status = self.fetcher.get_market_status(lunch_break)
        assert status.is_open is False
        assert status.status == MarketStatus.STATUS_LUNCH_BREAK
        
        # 盘后
        after_hours = datetime(2025, 12, 31, 16, 0, 0)
        status = self.fetcher.get_market_status(after_hours)
        assert status.is_open is False
        assert status.status == MarketStatus.STATUS_AFTER_HOURS

    
    def test_market_status_weekend(self):
        """测试周末的市场状态"""
        # 周六
        saturday = datetime(2025, 12, 27, 10, 0, 0)
        status = self.fetcher.get_market_status(saturday)
        assert status.is_open is False
        assert status.status == MarketStatus.STATUS_CLOSED
        
        # 周日
        sunday = datetime(2025, 12, 28, 10, 0, 0)
        status = self.fetcher.get_market_status(sunday)
        assert status.is_open is False
        assert status.status == MarketStatus.STATUS_CLOSED
    
    def test_should_refresh_initial(self):
        """测试初始状态需要刷新"""
        fetcher = DataFetcher()
        assert fetcher.should_refresh() is True
    
    def test_cache_management(self):
        """测试缓存管理"""
        fetcher = DataFetcher()
        
        # 初始缓存为空
        assert fetcher.get_cached_data('000001') is None
        
        # 清空缓存
        fetcher.clear_cache()
        assert fetcher._last_update is None


class TestEndToEndSignalFlow:
    """
    端到端信号流程测试
    """
    
    def setup_method(self):
        """测试前初始化"""
        self.monitor = RealtimeMonitor()
        self.engine = SignalEngine()
    
    def test_watchlist_to_buy_signal_flow(self):
        """测试从监控列表到买入信号的完整流程"""
        # 1. 添加多只股票到监控列表
        codes = ['000001', '300001', '600001']
        for code in codes:
            self.monitor.add_to_watchlist(code)
        
        assert self.monitor.watchlist_size == 3
        
        # 2. 模拟获取股票数据并生成信号
        stock_data_list = [
            StockData(
                code='000001',
                name='平安银行',
                current_price=10.0,
                change_pct=0.02,
                volume=1000000,
                turnover=10000000.0,
                ma5=10.5, ma10=10.2, ma20=10.0, ma60=9.5,
                rsi=55.0, volume_ratio=1.5, ma20_slope=0.01
            ),
            StockData(
                code='300001',
                name='特锐德',
                current_price=20.0,
                change_pct=0.01,
                volume=500000,
                turnover=10000000.0,
                ma5=20.5, ma10=20.2, ma20=20.0, ma60=19.0,
                rsi=75.0,  # RSI超出范围
                volume_ratio=1.5, ma20_slope=0.01
            ),
            StockData(
                code='600001',
                name='邯郸钢铁',
                current_price=5.0,
                change_pct=-0.01,
                volume=200000,
                turnover=1000000.0,
                ma5=5.2, ma10=5.3, ma20=5.4, ma60=5.5,
                rsi=40.0,  # RSI太低
                volume_ratio=0.8,  # 量比不足
                ma20_slope=-0.01  # 斜率为负
            ),
        ]
        
        # 3. 生成买入信号
        buy_signals = []
        for stock_data in stock_data_list:
            signal = self.engine.generate_buy_signal(stock_data)
            if signal:
                buy_signals.append(signal)
        
        # 验证结果
        assert len(buy_signals) == 2  # 只有前两只股票满足条件
        assert buy_signals[0].signal_strength == 100  # 6个条件
        assert buy_signals[1].signal_strength == 83   # 5个条件

    
    def test_position_to_sell_signal_flow(self):
        """测试从持仓到卖出信号的完整流程"""
        # 1. 添加多个持仓
        positions_data = [
            ('000001', '平安银行', 10.0, 100, date.today()),
            ('300001', '特锐德', 20.0, 200, date.today() - timedelta(days=10)),
            ('600001', '邯郸钢铁', 5.0, 500, date.today() - timedelta(days=20)),
        ]
        
        for code, name, cost, qty, buy_date in positions_data:
            self.monitor.add_position(code, name, cost, qty, buy_date)
        
        assert self.monitor.position_count == 3
        
        # 2. 更新价格
        price_updates = {
            '000001': 9.5,   # 止损
            '300001': 24.5,  # 止盈
            '600001': 5.2,   # 超时
        }
        self.monitor.update_all_position_prices(price_updates)
        
        # 3. 生成卖出信号
        all_sell_signals = []
        
        stock_data_map = {
            '000001': StockData(
                code='000001', name='平安银行', current_price=9.5,
                change_pct=-0.05, volume=1000000, turnover=10000000.0,
                ma5=9.6, ma10=9.8, ma20=10.0, ma60=9.5,
                rsi=40.0, volume_ratio=1.5, ma20_slope=-0.01
            ),
            '300001': StockData(
                code='300001', name='特锐德', current_price=24.5,
                change_pct=0.225, volume=500000, turnover=10000000.0,
                ma5=24.0, ma10=23.0, ma20=22.0, ma60=20.0,
                rsi=75.0, volume_ratio=1.5, ma20_slope=0.02
            ),
            '600001': StockData(
                code='600001', name='邯郸钢铁', current_price=5.2,
                change_pct=0.04, volume=200000, turnover=1000000.0,
                ma5=5.1, ma10=5.0, ma20=4.9, ma60=4.8,
                rsi=55.0, volume_ratio=1.2, ma20_slope=0.01
            ),
        }
        
        for code in self.monitor.positions:
            position = self.monitor.get_position(code)
            stock_data = stock_data_map[code]
            signals = self.engine.generate_sell_signals(position, stock_data)
            all_sell_signals.extend(signals)
        
        # 验证结果
        assert len(all_sell_signals) >= 3  # 至少3个信号
        
        # 验证各类型信号
        signal_types = [s.signal_type for s in all_sell_signals]
        assert SellSignal.TYPE_STOP_LOSS in signal_types
        assert SellSignal.TYPE_TAKE_PROFIT in signal_types
        assert SellSignal.TYPE_TIMEOUT in signal_types
    
    def test_position_summary_calculation(self):
        """测试持仓汇总计算"""
        # 添加持仓
        self.monitor.add_position('000001', '平安银行', 10.0, 100)
        self.monitor.add_position('300001', '特锐德', 20.0, 200)
        
        # 更新价格
        self.monitor.update_position_price('000001', 12.0)  # +20%
        self.monitor.update_position_price('300001', 22.0)  # +10%
        
        # 获取汇总
        summary = self.monitor.get_position_summary()
        
        # 验证计算
        expected_market_value = 12.0 * 100 + 22.0 * 200  # 1200 + 4400 = 5600
        expected_cost_value = 10.0 * 100 + 20.0 * 200    # 1000 + 4000 = 5000
        expected_pnl = expected_market_value - expected_cost_value  # 600
        expected_pnl_pct = expected_pnl / expected_cost_value  # 0.12
        
        assert abs(summary['total_market_value'] - expected_market_value) < 0.01
        assert abs(summary['total_cost_value'] - expected_cost_value) < 0.01
        assert abs(summary['total_pnl'] - expected_pnl) < 0.01
        assert abs(summary['total_pnl_pct'] - expected_pnl_pct) < 0.0001


class TestSignalRecommendations:
    """
    测试交易建议生成
    """
    
    def setup_method(self):
        """测试前初始化"""
        self.engine = SignalEngine()
    
    def test_buy_signal_price_recommendations(self):
        """测试买入信号价格建议"""
        entry_price = 10.0
        prices = self.engine.calculate_buy_signal_prices(entry_price)
        
        # 验证价格关系
        assert prices['stop_loss_price'] < prices['entry_price']
        assert prices['entry_price'] < prices['trailing_trigger_price']
        assert prices['trailing_trigger_price'] < prices['take_profit_price']
        
        # 验证具体值
        assert prices['stop_loss_price'] == 9.54
        assert prices['take_profit_price'] == 12.2
        assert prices['trailing_trigger_price'] == 10.9
    
    def test_sell_signal_recommendations(self):
        """测试卖出信号建议"""
        # 创建各类型卖出信号并获取建议
        signal_types = [
            (SellSignal.TYPE_STOP_LOSS, SellSignal.URGENCY_HIGH, SellSignal.ACTION_IMMEDIATE_SELL),
            (SellSignal.TYPE_TAKE_PROFIT, SellSignal.URGENCY_MEDIUM, SellSignal.ACTION_IMMEDIATE_SELL),
            (SellSignal.TYPE_RSI_OVERBOUGHT, SellSignal.URGENCY_MEDIUM, SellSignal.ACTION_REDUCE_POSITION),
            (SellSignal.TYPE_TIMEOUT, SellSignal.URGENCY_LOW, SellSignal.ACTION_MONITOR),
        ]
        
        for signal_type, urgency, action in signal_types:
            sell_signal = SellSignal(
                code='000001',
                name='测试股票',
                current_price=10.0,
                cost_price=10.0,
                pnl_pct=0.0,
                signal_type=signal_type,
                urgency=urgency,
                reason='测试原因',
                action=action,
            )
            
            recommendation = self.engine.get_sell_recommendation(sell_signal)
            
            assert 'urgency_description' in recommendation
            assert 'action_description' in recommendation
            assert 'reason_explanation' in recommendation



class TestDataCachePerformance:
    """
    测试数据缓存性能优化
    
    Task 10.2: 性能优化
    """
    
    def test_cache_basic_operations(self):
        """测试缓存基本操作"""
        from core.realtime_monitor.data_fetcher import DataCache
        
        cache = DataCache()
        
        # 测试设置和获取
        cache.set("key1", "value1", ttl=60)
        assert cache.get("key1") == "value1"
        
        # 测试不存在的键
        assert cache.get("nonexistent") is None
        
        # 测试删除
        assert cache.delete("key1") is True
        assert cache.get("key1") is None
        assert cache.delete("key1") is False
    
    def test_cache_expiration(self):
        """测试缓存过期"""
        from core.realtime_monitor.data_fetcher import DataCache, CacheEntry
        from datetime import datetime, timedelta
        
        # 创建一个已过期的缓存条目
        entry = CacheEntry(
            data="test_data",
            timestamp=datetime.now() - timedelta(seconds=100),
            ttl=60
        )
        
        assert entry.is_expired() is True
        
        # 创建一个未过期的缓存条目
        entry2 = CacheEntry(
            data="test_data",
            timestamp=datetime.now(),
            ttl=60
        )
        
        assert entry2.is_expired() is False
    
    def test_cache_stats(self):
        """测试缓存统计"""
        from core.realtime_monitor.data_fetcher import DataCache
        
        cache = DataCache()
        
        # 初始状态
        stats = cache.stats
        assert stats['size'] == 0
        assert stats['hit_count'] == 0
        assert stats['miss_count'] == 0
        
        # 添加数据
        cache.set("key1", "value1")
        
        # 命中
        cache.get("key1")
        stats = cache.stats
        assert stats['hit_count'] == 1
        
        # 未命中
        cache.get("nonexistent")
        stats = cache.stats
        assert stats['miss_count'] == 1
    
    def test_cache_clear(self):
        """测试缓存清空"""
        from core.realtime_monitor.data_fetcher import DataCache
        
        cache = DataCache()
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        assert cache.stats['size'] == 2
        
        cache.clear()
        
        assert cache.stats['size'] == 0
        assert cache.get("key1") is None
        assert cache.get("key2") is None
    
    def test_data_fetcher_cache_stats(self):
        """测试DataFetcher缓存统计"""
        from core.realtime_monitor.data_fetcher import DataFetcher
        
        fetcher = DataFetcher()
        
        stats = fetcher.cache_stats
        
        assert 'realtime' in stats
        assert 'historical' in stats
        assert 'fund_flow' in stats
        
        # 验证每个缓存的统计结构
        for cache_name, cache_stats in stats.items():
            assert 'size' in cache_stats
            assert 'hit_count' in cache_stats
            assert 'miss_count' in cache_stats
            assert 'hit_rate' in cache_stats
    
    def test_data_fetcher_clear_all_caches(self):
        """测试DataFetcher清空所有缓存"""
        from core.realtime_monitor.data_fetcher import DataFetcher
        
        fetcher = DataFetcher()
        
        # 手动添加一些缓存数据
        fetcher._realtime_cache.set("test_key", "test_value")
        fetcher._historical_cache.set("test_key", "test_value")
        
        # 清空所有缓存
        fetcher.clear_cache()
        
        # 验证所有缓存都被清空
        assert fetcher._realtime_cache.get("test_key") is None
        assert fetcher._historical_cache.get("test_key") is None
        assert fetcher._batch_quote_cache is None
        assert fetcher._last_update is None
