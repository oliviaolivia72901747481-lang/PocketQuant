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


class TestHistoricalSignalsIntegration:
    """
    历史信号模块集成测试
    
    Final Checkpoint 4: 验证端到端流程
    - 生成信号 → 自动保存 → 历史查询 → 导出
    
    Requirements: 1.1-1.5, 2.1-2.5, 4.2-4.4, 5.1-5.2
    """
    
    @pytest.fixture
    def temp_signal_store(self):
        """创建临时目录的 SignalStore 实例"""
        from core.signal_store import SignalStore
        from pathlib import Path
        
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "signal_history.csv"
            yield SignalStore(file_path=file_path)
    
    @pytest.fixture
    def mock_trading_signals(self):
        """创建模拟的交易信号列表"""
        from core.signal_generator import TradingSignal, SignalType
        
        signals = [
            TradingSignal(
                code='000001',
                name='平安银行',
                signal_type=SignalType.BUY,
                price_range=(10.50, 10.80),
                limit_cap=10.91,
                reason='MACD金叉+MA60趋势向上',
                generated_at=date.today(),
                trade_amount=50000.0,
                high_fee_warning=False,
                actual_fee_rate=0.0003,
                news_url='https://quote.eastmoney.com/sz000001.html',
                in_report_window=False,
                report_warning=None
            ),
            TradingSignal(
                code='600036',
                name='招商银行',
                signal_type=SignalType.BUY,
                price_range=(35.20, 36.00),
                limit_cap=36.36,
                reason='MACD金叉+RSI=65',
                generated_at=date.today(),
                trade_amount=60000.0,
                high_fee_warning=False,
                actual_fee_rate=0.0003,
                news_url='https://quote.eastmoney.com/sh600036.html',
                in_report_window=True,
                report_warning='财报窗口期'
            ),
            TradingSignal(
                code='000002',
                name='万科A',
                signal_type=SignalType.SELL,
                price_range=(8.50, 8.80),
                limit_cap=8.89,
                reason='MACD死叉',
                generated_at=date.today(),
                trade_amount=30000.0,
                high_fee_warning=True,
                actual_fee_rate=0.0005,
                news_url='https://quote.eastmoney.com/sz000002.html',
                in_report_window=False,
                report_warning=None
            )
        ]
        return signals
    
    def test_signal_store_initialization(self, temp_signal_store):
        """测试 SignalStore 初始化和文件创建"""
        store = temp_signal_store
        
        # 验证文件已创建
        assert store.file_path.exists(), "信号历史文件未创建"
        
        # 验证列定义
        assert len(store.COLUMNS) == 11, "列定义数量不正确"
        
        print("SignalStore 初始化测试通过")
    
    def test_save_signals_flow(self, temp_signal_store, mock_trading_signals):
        """测试信号保存流程 (Requirements: 1.1, 1.2)"""
        store = temp_signal_store
        signals = mock_trading_signals
        
        # 保存信号
        saved_count = store.save_signals(
            signals=signals,
            generated_date=date.today(),
            market_status="健康"
        )
        
        # 验证保存数量
        assert saved_count == len(signals), f"保存数量不匹配: {saved_count} != {len(signals)}"
        
        print(f"信号保存流程测试通过: 保存 {saved_count} 条信号")
    
    def test_load_signals_flow(self, temp_signal_store, mock_trading_signals):
        """测试信号加载流程 (Requirements: 2.1, 2.2, 2.3, 2.4)"""
        store = temp_signal_store
        signals = mock_trading_signals
        
        # 先保存信号
        store.save_signals(signals, date.today(), "健康")
        
        # 加载全部信号
        df = store.load_signals()
        assert len(df) == len(signals), "加载信号数量不匹配"
        
        # 按日期范围筛选
        df_date = store.load_signals(
            start_date=date.today(),
            end_date=date.today()
        )
        assert len(df_date) == len(signals), "日期筛选结果不正确"
        
        # 按股票代码筛选
        df_code = store.load_signals(code='000001')
        assert len(df_code) == 1, "股票代码筛选结果不正确"
        
        # 按信号类型筛选
        df_buy = store.load_signals(signal_type='买入')
        assert len(df_buy) == 2, "信号类型筛选结果不正确"
        
        df_sell = store.load_signals(signal_type='卖出')
        assert len(df_sell) == 1, "信号类型筛选结果不正确"
        
        print("信号加载流程测试通过")
    
    def test_idempotent_save_flow(self, temp_signal_store, mock_trading_signals):
        """测试幂等覆盖更新流程 (Requirements: 1.3, 1.5)"""
        store = temp_signal_store
        signals = mock_trading_signals
        
        # 第一次保存
        store.save_signals(signals, date.today(), "健康")
        
        # 第二次保存（同一天，应覆盖）
        new_signals = signals[:1]  # 只保存第一条
        store.save_signals(new_signals, date.today(), "不佳")
        
        # 验证只保留最后一次的数据
        df = store.load_signals(start_date=date.today(), end_date=date.today())
        assert len(df) == 1, f"幂等覆盖更新失败: 期望 1 条，实际 {len(df)} 条"
        
        # 验证大盘状态已更新
        assert df.iloc[0]['market_status'] == '不佳', "大盘状态未更新"
        
        print("幂等覆盖更新流程测试通过")
    
    def test_statistics_flow(self, temp_signal_store, mock_trading_signals):
        """测试统计计算流程 (Requirements: 4.2, 4.3, 4.4)"""
        store = temp_signal_store
        signals = mock_trading_signals
        
        # 保存信号
        store.save_signals(signals, date.today(), "健康")
        
        # 加载并计算统计
        df = store.load_signals()
        stats = store.get_statistics(df)
        
        # 验证统计结果
        assert stats['total_count'] == 3, "总信号数不正确"
        assert stats['buy_count'] == 2, "买入信号数不正确"
        assert stats['sell_count'] == 1, "卖出信号数不正确"
        assert stats['stock_count'] == 3, "涉及股票数不正确"
        
        print(f"统计计算流程测试通过: {stats}")
    
    def test_export_csv_flow(self, temp_signal_store, mock_trading_signals):
        """测试 CSV 导出流程 (Requirements: 5.1, 5.2)"""
        store = temp_signal_store
        signals = mock_trading_signals
        
        # 保存信号
        store.save_signals(signals, date.today(), "健康")
        
        # 加载并导出
        df = store.load_signals()
        csv_bytes = store.export_csv(df)
        
        # 验证导出内容
        assert csv_bytes is not None, "导出内容为空"
        assert len(csv_bytes) > 0, "导出内容长度为 0"
        
        # 验证可以解析回 DataFrame
        import io
        exported_df = pd.read_csv(io.BytesIO(csv_bytes))
        assert len(exported_df) == len(df), "导出数据行数不匹配"
        
        print(f"CSV 导出流程测试通过: 导出 {len(csv_bytes)} 字节")
    
    def test_end_to_end_signal_flow(self, temp_signal_store, mock_trading_signals):
        """
        测试完整的端到端流程
        
        流程: 生成信号 → 自动保存 → 历史查询 → 导出
        """
        store = temp_signal_store
        signals = mock_trading_signals
        
        # 1. 生成信号（模拟）
        print("Step 1: 生成信号")
        assert len(signals) == 3, "信号生成失败"
        
        # 2. 自动保存
        print("Step 2: 自动保存")
        saved_count = store.save_signals(signals, date.today(), "健康")
        assert saved_count == 3, "信号保存失败"
        
        # 3. 历史查询
        print("Step 3: 历史查询")
        df = store.load_signals(
            start_date=date.today() - timedelta(days=30),
            end_date=date.today()
        )
        assert len(df) == 3, "历史查询失败"
        
        # 4. 统计计算
        print("Step 4: 统计计算")
        stats = store.get_statistics(df)
        assert stats['total_count'] == 3, "统计计算失败"
        
        # 5. 导出
        print("Step 5: 导出 CSV")
        csv_bytes = store.export_csv(df)
        assert len(csv_bytes) > 0, "CSV 导出失败"
        
        print(f"""
端到端流程测试通过:
  - 生成信号: {len(signals)} 条
  - 保存信号: {saved_count} 条
  - 历史查询: {len(df)} 条
  - 统计: 总数={stats['total_count']}, 买入={stats['buy_count']}, 卖出={stats['sell_count']}
  - 导出: {len(csv_bytes)} 字节
        """)
    
    def test_empty_signals_handling(self, temp_signal_store):
        """测试空信号列表处理"""
        store = temp_signal_store
        
        # 保存空列表
        saved_count = store.save_signals([], date.today(), "健康")
        assert saved_count == 0, "空列表保存应返回 0"
        
        # 加载空数据
        df = store.load_signals()
        assert df.empty, "空数据加载应返回空 DataFrame"
        
        # 空数据统计
        stats = store.get_statistics(df)
        assert stats['total_count'] == 0, "空数据统计应返回 0"
        
        print("空信号列表处理测试通过")
    
    def test_no_matching_signals(self, temp_signal_store, mock_trading_signals):
        """测试无匹配信号的情况 (Requirements: 2.5)"""
        store = temp_signal_store
        signals = mock_trading_signals
        
        # 保存信号
        store.save_signals(signals, date.today(), "健康")
        
        # 查询不存在的股票代码
        df = store.load_signals(code='999999')
        assert df.empty, "不存在的股票代码应返回空结果"
        
        # 查询未来日期
        future_date = date.today() + timedelta(days=30)
        df = store.load_signals(start_date=future_date, end_date=future_date)
        assert df.empty, "未来日期应返回空结果"
        
        print("无匹配信号处理测试通过")
    
    def test_signal_store_module_import(self):
        """测试 SignalStore 模块可导入"""
        from core.signal_store import SignalStore, SignalRecord
        
        # 验证类存在
        assert SignalStore is not None
        assert SignalRecord is not None
        
        # 验证 SignalRecord 字段
        record = SignalRecord(
            generated_date=date.today(),
            code='000001',
            name='测试股票',
            signal_type='买入',
            price_low=10.0,
            price_high=10.5,
            limit_cap=10.61,
            reason='测试原因',
            in_report_window=False,
            high_fee_warning=False,
            market_status='健康'
        )
        
        assert record.code == '000001'
        assert record.signal_type == '买入'
        
        print("SignalStore 模块导入测试通过")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
