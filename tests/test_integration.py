"""
MiniQuant-Lite 集成测试

Final Checkpoint 15: 集成测试
- 验证端到端流程：数据下载 → 筛选 → 回测 → 信号生成 → UI 展示
- 确保所有模块协同工作

Requirements: 全部
"""

import pytest
import pandas as pd
import numpy as np
import tempfile
import os
import sys
from datetime import date, timedelta

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.data_feed import DataFeed, LiquidityFilter
from core.screener import Screener, ScreenerCondition, MarketFilter, IndustryDiversification
from core.sizers import calculate_max_shares, calculate_actual_fee_rate
from core.signal_generator import SignalGenerator, SignalType
from core.report_checker import ReportChecker
from backtest.run_backtest import BacktestConfig, BacktestEngine, LimitUpDownChecker
from strategies.trend_filtered_macd_strategy import TrendFilteredMACDStrategy, ExitReason
from strategies.base_strategy import BaseStrategy
from config.settings import get_settings


class TestEndToEndDataFlow:
    """端到端数据流测试"""
    
    @pytest.fixture
    def temp_data_feed(self):
        """创建临时目录的 DataFeed 实例"""
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_path = os.path.join(tmpdir, 'raw')
            processed_path = os.path.join(tmpdir, 'processed')
            yield DataFeed(raw_path, processed_path)
    
    def test_data_download_to_clean_flow(self, temp_data_feed):
        """测试数据下载到清洗的完整流程"""
        # 1. 下载数据
        df = temp_data_feed.download_stock_data(
            code='000001',
            start_date='2024-01-01',
            end_date='2024-01-31',
            adjust='qfq'
        )
        
        assert df is not None, "数据下载失败"
        assert not df.empty, "下载数据为空"
        
        # 2. 清洗数据
        cleaned = temp_data_feed.clean_data(df)
        
        assert not cleaned.empty, "清洗后数据为空"
        
        # 3. 验证 Backtrader 格式
        required_cols = ['date', 'open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            assert col in cleaned.columns, f"缺少列: {col}"
        
        print(f"数据流测试通过: 下载 {len(df)} 条 → 清洗后 {len(cleaned)} 条")
    
    def test_overwrite_update_and_load(self, temp_data_feed):
        """测试覆盖更新和加载流程"""
        # 1. 覆盖更新
        success = temp_data_feed.overwrite_update(code='000001', days=30)
        assert success, "覆盖更新失败"
        
        # 2. 加载数据
        loaded = temp_data_feed.load_processed_data('000001')
        assert loaded is not None, "加载数据失败"
        assert not loaded.empty, "加载数据为空"
        
        print(f"覆盖更新流程测试通过: 保存并加载 {len(loaded)} 条记录")


class TestScreenerIntegration:
    """筛选器集成测试"""
    
    @pytest.fixture
    def screener_with_data(self):
        """创建带数据的 Screener 实例"""
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_path = os.path.join(tmpdir, 'raw')
            processed_path = os.path.join(tmpdir, 'processed')
            data_feed = DataFeed(raw_path, processed_path)
            
            # 下载测试数据
            data_feed.overwrite_update('000001', days=90)
            
            yield Screener(data_feed)
    
    def test_screener_with_conditions(self, screener_with_data):
        """测试带条件的筛选流程"""
        screener = screener_with_data
        
        # 添加筛选条件
        screener.add_condition(ScreenerCondition('price', '>', 5.0))
        screener.add_condition(ScreenerCondition('price', '<', 100.0))
        
        # 验证条件已添加
        assert len(screener._conditions) == 2
        
        # 清空条件
        screener.clear_conditions()
        assert len(screener._conditions) == 0
        
        print("筛选器条件管理测试通过")
    
    def test_market_filter_integration(self, screener_with_data):
        """测试大盘滤网集成"""
        screener = screener_with_data
        
        # 获取大盘状态
        status = screener.get_market_status()
        
        assert 'status' in status
        assert status['status'] in ['healthy', 'unhealthy', 'unknown', 'error']
        
        print(f"大盘滤网测试通过: 状态 = {status['status']}")
    
    def test_indicator_calculation_integration(self, screener_with_data):
        """测试技术指标计算集成"""
        screener = screener_with_data
        
        # 加载数据
        df = screener.data_feed.load_processed_data('000001')
        
        if df is not None and len(df) >= 60:
            # 计算指标
            result = screener.calculate_indicators(df)
            
            assert not result.empty
            assert 'ma60' in result.columns
            assert 'macd' in result.columns
            assert 'rsi' in result.columns
            
            print("技术指标计算集成测试通过")
        else:
            pytest.skip("数据不足，跳过指标计算测试")


class TestSizerIntegration:
    """仓位管理集成测试"""
    
    def test_sizer_with_settings(self):
        """测试仓位管理与配置集成"""
        settings = get_settings()
        
        # 使用配置的参数计算仓位
        shares, warning, reason = calculate_max_shares(
            cash=settings.fund.initial_capital,
            price=25.0,
            commission_rate=settings.fund.commission_rate,
            min_commission=settings.fund.min_commission,
            max_positions_count=settings.position.max_positions_count,
            current_positions=0,
            total_value=settings.fund.initial_capital,
            position_tolerance=settings.position.position_tolerance,
            min_trade_amount=settings.position.min_trade_amount,
            cash_buffer=settings.position.cash_buffer
        )
        
        assert shares >= 0
        assert shares % 100 == 0  # 100股整数倍
        
        print(f"仓位管理集成测试通过: 可买 {shares} 股")
    
    def test_fee_rate_calculation(self):
        """测试费率计算"""
        settings = get_settings()
        
        # 大金额交易
        rate_large = calculate_actual_fee_rate(
            50000, 
            settings.fund.commission_rate, 
            settings.fund.min_commission
        )
        
        # 小金额交易
        rate_small = calculate_actual_fee_rate(
            10000, 
            settings.fund.commission_rate, 
            settings.fund.min_commission
        )
        
        # 小金额交易费率应更高（5元低消影响）
        assert rate_small >= rate_large
        
        print(f"费率计算测试通过: 大额 {rate_large:.4%}, 小额 {rate_small:.4%}")


class TestBacktestIntegration:
    """回测引擎集成测试"""
    
    @pytest.fixture
    def sample_stock_data(self):
        """生成测试用股票数据"""
        np.random.seed(42)
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        
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
    
    def test_backtest_engine_initialization(self):
        """测试回测引擎初始化"""
        settings = get_settings()
        
        config = BacktestConfig(
            initial_cash=settings.fund.initial_capital,
            commission_rate=settings.fund.commission_rate,
            stamp_duty=settings.fund.stamp_tax_rate
        )
        
        engine = BacktestEngine(config)
        
        assert engine.config.initial_cash == settings.fund.initial_capital
        assert engine.cerebro is not None
        
        print("回测引擎初始化测试通过")
    
    def test_limit_up_down_detection(self):
        """测试涨跌停检测"""
        # 一字板
        assert LimitUpDownChecker.is_limit_up_down(10.0, 10.0, 10.0, 10.0) == True
        
        # 正常交易
        assert LimitUpDownChecker.is_limit_up_down(10.0, 10.5, 9.8, 10.2) == False
        
        print("涨跌停检测测试通过")


class TestSignalGeneratorIntegration:
    """信号生成器集成测试"""
    
    @pytest.fixture
    def signal_generator_with_data(self):
        """创建带数据的信号生成器"""
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_path = os.path.join(tmpdir, 'raw')
            processed_path = os.path.join(tmpdir, 'processed')
            data_feed = DataFeed(raw_path, processed_path)
            
            # 下载测试数据
            data_feed.overwrite_update('000001', days=90)
            
            yield SignalGenerator(data_feed=data_feed)
    
    def test_signal_generator_initialization(self, signal_generator_with_data):
        """测试信号生成器初始化"""
        sg = signal_generator_with_data
        
        assert sg.data_feed is not None
        assert sg.report_checker is not None
        
        print("信号生成器初始化测试通过")
    
    def test_limit_cap_calculation(self, signal_generator_with_data):
        """测试限价上限计算"""
        sg = signal_generator_with_data
        
        close_price = 10.0
        limit_cap = sg._calculate_limit_cap(close_price)
        
        # 限价上限 = 收盘价 × 1.01
        expected = round(close_price * 1.01, 2)
        assert limit_cap == expected
        
        print(f"限价上限计算测试通过: {close_price} → {limit_cap}")
    
    def test_news_url_generation(self, signal_generator_with_data):
        """测试新闻链接生成"""
        sg = signal_generator_with_data
        
        # 上海股票
        url_sh = sg._generate_news_url('600036')
        assert 'sh600036' in url_sh
        
        # 深圳股票
        url_sz = sg._generate_news_url('000001')
        assert 'sz000001' in url_sz
        
        # 创业板股票
        url_cy = sg._generate_news_url('300750')
        assert 'sz300750' in url_cy
        
        print("新闻链接生成测试通过")


class TestReportCheckerIntegration:
    """财报检测器集成测试"""
    
    def test_report_checker_initialization(self):
        """测试财报检测器初始化"""
        checker = ReportChecker(window_days=3)
        
        assert checker.window_days == 3
        
        print("财报检测器初始化测试通过")
    
    def test_report_window_check(self):
        """测试财报窗口期检查"""
        checker = ReportChecker(window_days=3)
        
        # 检查财报窗口期（可能返回 True 或 False，取决于当前日期）
        is_in_window, warning = checker.check_report_window('000001')
        
        assert isinstance(is_in_window, bool)
        
        if is_in_window:
            assert warning is not None
            print(f"财报窗口期检查测试通过: 在窗口期内 - {warning}")
        else:
            print("财报窗口期检查测试通过: 不在窗口期内")


class TestStrategyIntegration:
    """策略集成测试"""
    
    def test_strategy_inheritance(self):
        """测试策略继承关系"""
        assert issubclass(TrendFilteredMACDStrategy, BaseStrategy)
        
        print("策略继承关系测试通过")
    
    def test_strategy_parameters(self):
        """测试策略参数"""
        params = dict(TrendFilteredMACDStrategy.params._getitems())
        
        # 验证关键参数存在
        assert 'ma_period' in params
        assert 'hard_stop_loss' in params
        assert 'trailing_start' in params
        assert 'trailing_stop' in params
        assert 'rsi_upper' in params
        
        # 验证默认值
        assert params['ma_period'] == 60
        assert params['hard_stop_loss'] == -0.08
        assert params['trailing_start'] == 0.15
        
        print("策略参数测试通过")
    
    def test_exit_reasons(self):
        """测试退出原因枚举"""
        assert ExitReason.HARD_STOP_LOSS.value == "硬止损(-8%)"
        assert ExitReason.TRAILING_STOP.value == "移动止盈"
        assert ExitReason.MACD_DEATH_CROSS.value == "MACD死叉"
        
        print("退出原因枚举测试通过")


class TestConfigIntegration:
    """配置集成测试"""
    
    def test_settings_loading(self):
        """测试配置加载"""
        settings = get_settings()
        
        # 验证资金配置
        assert settings.fund.initial_capital > 0
        assert settings.fund.commission_rate > 0
        
        # 验证仓位配置
        assert settings.position.max_positions_count > 0
        assert settings.position.min_trade_amount > 0
        
        # 验证策略配置
        assert settings.strategy.ma_period > 0
        assert settings.strategy.hard_stop_loss < 0
        
        print("配置加载测试通过")
    
    def test_path_configuration(self):
        """测试路径配置"""
        settings = get_settings()
        
        raw_path = settings.path.get_raw_path()
        processed_path = settings.path.get_processed_path()
        
        assert raw_path is not None
        assert processed_path is not None
        
        print(f"路径配置测试通过: raw={raw_path}, processed={processed_path}")


class TestFullPipelineIntegration:
    """完整流水线集成测试"""
    
    def test_data_to_signal_pipeline(self):
        """测试数据到信号的完整流水线"""
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_path = os.path.join(tmpdir, 'raw')
            processed_path = os.path.join(tmpdir, 'processed')
            
            # 1. 数据层
            data_feed = DataFeed(raw_path, processed_path)
            
            # 2. 下载数据
            success = data_feed.overwrite_update('000001', days=90)
            if not success:
                pytest.skip("无法下载数据，跳过流水线测试")
            
            # 3. 加载数据
            df = data_feed.load_processed_data('000001')
            assert df is not None and not df.empty
            
            # 4. 筛选层
            screener = Screener(data_feed)
            indicators = screener.calculate_indicators(df)
            assert not indicators.empty
            
            # 5. 信号层
            signal_generator = SignalGenerator(data_feed=data_feed)
            limit_cap = signal_generator._calculate_limit_cap(df['close'].iloc[-1])
            assert limit_cap > 0
            
            # 6. 仓位层
            settings = get_settings()
            shares, warning, reason = calculate_max_shares(
                cash=settings.fund.initial_capital,
                price=df['close'].iloc[-1],
                commission_rate=settings.fund.commission_rate,
                min_commission=settings.fund.min_commission,
                max_positions_count=settings.position.max_positions_count,
                current_positions=0,
                total_value=settings.fund.initial_capital
            )
            
            print(f"""
完整流水线测试通过:
  - 数据记录数: {len(df)}
  - 指标计算: {len(indicators.columns)} 列
  - 限价上限: ¥{limit_cap:.2f}
  - 可买股数: {shares} 股
            """)


class TestModuleImports:
    """模块导入测试"""
    
    def test_all_core_modules_import(self):
        """测试所有核心模块可导入"""
        # 数据层
        from core.data_feed import DataFeed, LiquidityFilter, StockData
        
        # 筛选层
        from core.screener import Screener, ScreenerCondition, ScreenerResult
        
        # 仓位层
        from core.sizers import SmallCapitalSizer, calculate_max_shares
        
        # 信号层
        from core.signal_generator import SignalGenerator, TradingSignal, SignalType
        
        # 财报检测
        from core.report_checker import ReportChecker
        
        # 策略层
        from strategies.base_strategy import BaseStrategy
        from strategies.trend_filtered_macd_strategy import TrendFilteredMACDStrategy
        
        # 回测层
        from backtest.run_backtest import BacktestConfig, BacktestResult, BacktestEngine
        
        # 配置层
        from config.settings import get_settings
        from config.stock_pool import get_watchlist
        
        print("所有核心模块导入测试通过")
    
    def test_app_modules_import(self):
        """测试应用模块可导入（不运行 Streamlit）"""
        # 这些模块依赖 Streamlit，只测试语法正确性
        import importlib.util
        
        app_files = [
            'app/Home.py',
            'app/pages/1_📊_Data_Manager.py',
            'app/pages/2_Backtest.py',
            'app/pages/3_Daily_Signal.py',
        ]
        
        for app_file in app_files:
            if os.path.exists(app_file):
                # 检查文件语法
                with open(app_file, 'r', encoding='utf-8') as f:
                    code = f.read()
                    compile(code, app_file, 'exec')
        
        print("应用模块语法检查通过")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
