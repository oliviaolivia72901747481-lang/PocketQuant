"""
MiniQuant-Lite 回测引擎验证测试

验证回测引擎的核心功能：
- BacktestConfig 和 BacktestResult 数据类
- 涨跌停板检测
- 回测引擎基本功能
- 绩效指标计算

Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9
"""

import pytest
import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
import backtrader as bt

from backtest.run_backtest import (
    BacktestConfig,
    BacktestResult,
    BacktestEngine,
    LimitUpDownChecker,
    CommissionScheme,
    run_backtest,
)


class TestBacktestConfig:
    """测试 BacktestConfig 数据类"""
    
    def test_default_values(self):
        """测试默认配置值"""
        config = BacktestConfig()
        
        assert config.initial_cash == 55000.0
        assert config.commission_rate == 0.0003
        assert config.stamp_duty == 0.001
        assert config.benchmark_code == '000300'
        assert config.check_limit_up_down is True
    
    def test_custom_values(self):
        """测试自定义配置值"""
        config = BacktestConfig(
            initial_cash=100000.0,
            commission_rate=0.0005,
            stamp_duty=0.002,
            start_date='2022-01-01',
            end_date='2023-12-31',
            benchmark_code='000001'
        )
        
        assert config.initial_cash == 100000.0
        assert config.commission_rate == 0.0005
        assert config.stamp_duty == 0.002
        assert config.start_date == '2022-01-01'
        assert config.end_date == '2023-12-31'
        assert config.benchmark_code == '000001'


class TestBacktestResult:
    """测试 BacktestResult 数据类"""
    
    def test_result_creation(self):
        """测试结果对象创建"""
        result = BacktestResult(
            initial_value=55000.0,
            final_value=60000.0,
            total_return=0.0909,
            annual_return=0.0909,
            max_drawdown=0.05,
            sharpe_ratio=1.5,
            benchmark_return=0.05,
            alpha=0.0409,
            trade_count=10,
            win_rate=0.6,
            profit_factor=1.5,
            avg_win=1000.0,
            avg_loss=-500.0
        )
        
        assert result.initial_value == 55000.0
        assert result.final_value == 60000.0
        assert result.total_return == 0.0909
        assert result.alpha == 0.0409
        assert result.win_rate == 0.6
    
    def test_result_with_dataframes(self):
        """测试带 DataFrame 的结果对象"""
        equity_curve = pd.DataFrame({
            'date': [date(2023, 1, 1), date(2023, 1, 2)],
            'value': [55000.0, 55500.0]
        })
        
        result = BacktestResult(
            initial_value=55000.0,
            final_value=55500.0,
            total_return=0.0091,
            annual_return=0.0091,
            max_drawdown=0.0,
            sharpe_ratio=0.0,
            benchmark_return=0.0,
            alpha=0.0091,
            trade_count=0,
            win_rate=0.0,
            profit_factor=0.0,
            avg_win=0.0,
            avg_loss=0.0,
            equity_curve=equity_curve
        )
        
        assert len(result.equity_curve) == 2
        assert result.equity_curve.iloc[0]['value'] == 55000.0


class TestLimitUpDownChecker:
    """测试涨跌停板检测器"""
    
    def test_limit_up_detected(self):
        """测试涨停一字板检测"""
        # 一字涨停：开盘=收盘=最高=最低
        result = LimitUpDownChecker.is_limit_up_down(
            open_price=11.0,
            high=11.0,
            low=11.0,
            close=11.0
        )
        assert result is True
    
    def test_limit_down_detected(self):
        """测试跌停一字板检测"""
        # 一字跌停：开盘=收盘=最高=最低
        result = LimitUpDownChecker.is_limit_up_down(
            open_price=9.0,
            high=9.0,
            low=9.0,
            close=9.0
        )
        assert result is True
    
    def test_normal_trading_day(self):
        """测试正常交易日（非一字板）"""
        # 正常交易日：有价格波动
        result = LimitUpDownChecker.is_limit_up_down(
            open_price=10.0,
            high=10.5,
            low=9.8,
            close=10.2
        )
        assert result is False
    
    def test_small_price_difference(self):
        """测试小幅价格差异（应视为一字板）"""
        # 价格差异在容差范围内
        result = LimitUpDownChecker.is_limit_up_down(
            open_price=10.0,
            high=10.0005,
            low=9.9995,
            close=10.0
        )
        assert result is True
    
    def test_significant_price_difference(self):
        """测试显著价格差异（非一字板）"""
        # 价格差异超出容差范围
        result = LimitUpDownChecker.is_limit_up_down(
            open_price=10.0,
            high=10.01,
            low=9.99,
            close=10.0
        )
        assert result is False


class TestCommissionScheme:
    """测试佣金方案"""
    
    def test_buy_commission(self):
        """测试买入佣金计算"""
        scheme = CommissionScheme(
            commission=0.0003,
            min_commission=5.0,
            stamp_duty=0.001
        )
        
        # 买入 1000 股，价格 10 元，交易金额 10000 元
        # 标准佣金 = 10000 * 0.0003 = 3 元，低于最低 5 元
        commission = scheme._getcommission(1000, 10.0, False)
        assert commission == 5.0  # 最低佣金
    
    def test_sell_commission_with_stamp_duty(self):
        """测试卖出佣金（含印花税）"""
        scheme = CommissionScheme(
            commission=0.0003,
            min_commission=5.0,
            stamp_duty=0.001
        )
        
        # 卖出 1000 股，价格 10 元，交易金额 10000 元
        # 佣金 = 5 元（最低）+ 印花税 10000 * 0.001 = 10 元
        commission = scheme._getcommission(-1000, 10.0, False)
        assert commission == 15.0  # 5 + 10
    
    def test_large_trade_commission(self):
        """测试大额交易佣金"""
        scheme = CommissionScheme(
            commission=0.0003,
            min_commission=5.0,
            stamp_duty=0.001
        )
        
        # 买入 10000 股，价格 10 元，交易金额 100000 元
        # 标准佣金 = 100000 * 0.0003 = 30 元，高于最低 5 元
        commission = scheme._getcommission(10000, 10.0, False)
        assert abs(commission - 30.0) < 0.01  # 使用近似比较避免浮点精度问题


class TestBacktestEngine:
    """测试回测引擎"""
    
    @pytest.fixture
    def sample_data(self):
        """生成测试用股票数据"""
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        np.random.seed(42)
        
        # 生成模拟价格数据
        base_price = 10.0
        returns = np.random.normal(0.001, 0.02, 100)
        prices = base_price * np.cumprod(1 + returns)
        
        df = pd.DataFrame({
            'date': dates,
            'open': prices * (1 + np.random.uniform(-0.01, 0.01, 100)),
            'high': prices * (1 + np.random.uniform(0, 0.02, 100)),
            'low': prices * (1 - np.random.uniform(0, 0.02, 100)),
            'close': prices,
            'volume': np.random.randint(100000, 1000000, 100)
        })
        
        return df
    
    def test_engine_initialization(self):
        """测试引擎初始化"""
        config = BacktestConfig(initial_cash=55000.0)
        engine = BacktestEngine(config)
        
        assert engine.config.initial_cash == 55000.0
        assert engine.cerebro is not None
    
    def test_add_data(self, sample_data):
        """测试添加股票数据"""
        config = BacktestConfig(
            start_date='2023-01-01',
            end_date='2023-04-10'
        )
        engine = BacktestEngine(config)
        
        engine.add_data('000001', sample_data)
        
        assert '000001' in engine.data_feeds
    
    def test_is_limit_up_down(self, sample_data):
        """测试涨跌停检测方法"""
        config = BacktestConfig()
        engine = BacktestEngine(config)
        
        # 直接测试静态方法
        result = engine._is_limit_up_down_static(10.0, 10.0, 10.0, 10.0)
        assert result is True
        
        result = engine._is_limit_up_down_static(10.0, 10.5, 9.8, 10.2)
        assert result is False
    
    def test_empty_result_creation(self):
        """测试空结果创建"""
        config = BacktestConfig()
        engine = BacktestEngine(config)
        
        result = engine._create_empty_result()
        
        assert result.initial_value == config.initial_cash
        assert result.final_value == config.initial_cash
        assert result.total_return == 0.0
        assert result.trade_count == 0


# 为 BacktestEngine 添加静态方法用于测试
BacktestEngine._is_limit_up_down_static = staticmethod(
    lambda o, h, l, c: LimitUpDownChecker.is_limit_up_down(o, h, l, c)
)


class TestRunBacktestFunction:
    """测试便捷回测函数"""
    
    @pytest.fixture
    def sample_stock_data(self):
        """生成测试用股票数据"""
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        np.random.seed(42)
        
        base_price = 10.0
        returns = np.random.normal(0.001, 0.02, 100)
        prices = base_price * np.cumprod(1 + returns)
        
        df = pd.DataFrame({
            'date': dates,
            'open': prices * (1 + np.random.uniform(-0.01, 0.01, 100)),
            'high': prices * (1 + np.random.uniform(0, 0.02, 100)),
            'low': prices * (1 - np.random.uniform(0, 0.02, 100)),
            'close': prices,
            'volume': np.random.randint(100000, 1000000, 100)
        })
        
        return {'000001': df}
    
    def test_run_backtest_basic(self, sample_stock_data):
        """测试基本回测执行"""
        # 使用简单的买入持有策略
        class SimpleStrategy(bt.Strategy):
            def __init__(self):
                pass
            
            def next(self):
                if not self.position:
                    self.buy(size=100)
        
        config = BacktestConfig(
            initial_cash=55000.0,
            start_date='2023-01-01',
            end_date='2023-04-10'
        )
        
        result = run_backtest(
            stock_data=sample_stock_data,
            strategy_class=SimpleStrategy,
            config=config,
            load_benchmark=False  # 跳过基准加载以加快测试
        )
        
        assert result is not None
        assert result.initial_value == 55000.0
        assert isinstance(result.total_return, float)
        assert isinstance(result.max_drawdown, float)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
