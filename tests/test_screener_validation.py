"""
MiniQuant-Lite 筛选层验证测试

Checkpoint 5: 筛选层验证
- 验证 Screener 模块基础功能
- 验证流动性过滤正确性
- 验证 MA60 趋势过滤正确性
- 验证大盘滤网正确性
- 验证行业互斥正确性
- 验证两阶段筛选一致性
- 验证预剪枝性能提升

Requirements: 2.1-2.13
"""

import pytest
import pandas as pd
import numpy as np
import tempfile
import os
import sys
import time

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.screener import (
    Screener, 
    ScreenerCondition, 
    LiquidityFilter, 
    MarketFilter,
    IndustryDiversification,
    ScreenerResult
)
from core.data_feed import DataFeed


class TestScreenerCondition:
    """验证筛选条件数据类"""
    
    def test_valid_condition_creation(self):
        """测试有效条件创建"""
        condition = ScreenerCondition(
            indicator='ma60',
            operator='>',
            value=10.0
        )
        assert condition.indicator == 'ma60'
        assert condition.operator == '>'
        assert condition.value == 10.0
    
    def test_between_condition(self):
        """测试 between 条件"""
        condition = ScreenerCondition(
            indicator='price',
            operator='between',
            value=10.0,
            value2=50.0
        )
        assert condition.value2 == 50.0
    
    def test_invalid_operator(self):
        """测试无效运算符"""
        with pytest.raises(ValueError, match="无效的运算符"):
            ScreenerCondition(
                indicator='ma60',
                operator='invalid',
                value=10.0
            )
    
    def test_between_without_value2(self):
        """测试 between 缺少 value2"""
        with pytest.raises(ValueError, match="between 运算符需要提供 value2"):
            ScreenerCondition(
                indicator='price',
                operator='between',
                value=10.0
            )
    
    def test_between_invalid_range(self):
        """测试 between 无效范围"""
        with pytest.raises(ValueError, match="value.*应小于等于.*value2"):
            ScreenerCondition(
                indicator='price',
                operator='between',
                value=50.0,
                value2=10.0
            )


class TestLiquidityFilter:
    """验证流动性过滤配置"""
    
    def test_default_values(self):
        """测试默认值"""
        lf = LiquidityFilter()
        assert lf.min_market_cap == 5e9  # 50亿
        assert lf.max_market_cap == 5e10  # 500亿
        assert lf.min_turnover_rate == 0.02  # 2%
        assert lf.max_turnover_rate == 0.15  # 15%
        assert lf.exclude_st == True
        assert lf.min_listing_days == 60


class TestScreenerBasic:
    """验证 Screener 模块基础功能"""
    
    @pytest.fixture
    def screener(self):
        """创建临时目录的 Screener 实例"""
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_path = os.path.join(tmpdir, 'raw')
            processed_path = os.path.join(tmpdir, 'processed')
            data_feed = DataFeed(raw_path, processed_path)
            yield Screener(data_feed)
    
    def test_screener_initialization(self, screener):
        """测试 Screener 初始化"""
        assert screener is not None
        assert screener.data_feed is not None
        assert screener.liquidity_filter is not None
        assert screener.market_filter is not None
        assert screener.industry_diversification is not None
    
    def test_add_condition_chain(self, screener):
        """测试链式添加条件"""
        result = screener.add_condition(
            ScreenerCondition('ma60', '>', 10.0)
        ).add_condition(
            ScreenerCondition('rsi', '<', 80.0)
        )
        
        assert result is screener  # 返回 self
        assert len(screener._conditions) == 2
    
    def test_clear_conditions(self, screener):
        """测试清空条件"""
        screener.add_condition(ScreenerCondition('ma60', '>', 10.0))
        screener.clear_conditions()
        assert len(screener._conditions) == 0
    
    def test_set_liquidity_filter(self, screener):
        """测试设置流动性过滤"""
        custom_filter = LiquidityFilter(
            min_market_cap=10e9,
            max_market_cap=100e9
        )
        result = screener.set_liquidity_filter(custom_filter)
        
        assert result is screener
        assert screener.liquidity_filter.min_market_cap == 10e9
    
    def test_set_market_filter(self, screener):
        """测试设置大盘滤网"""
        custom_filter = MarketFilter(enabled=False)
        result = screener.set_market_filter(custom_filter)
        
        assert result is screener
        assert screener.market_filter.enabled == False
    
    def test_set_industry_diversification(self, screener):
        """测试设置行业分散"""
        config = IndustryDiversification(max_same_industry=2)
        result = screener.set_industry_diversification(config)
        
        assert result is screener
        assert screener.industry_diversification.max_same_industry == 2


class TestIndicatorCalculation:
    """验证技术指标计算功能"""
    
    @pytest.fixture
    def screener(self):
        """创建临时目录的 Screener 实例"""
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_path = os.path.join(tmpdir, 'raw')
            processed_path = os.path.join(tmpdir, 'processed')
            data_feed = DataFeed(raw_path, processed_path)
            yield Screener(data_feed)
    
    @pytest.fixture
    def sample_data(self):
        """创建测试用的 OHLCV 数据"""
        np.random.seed(42)
        dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
        
        # 生成模拟价格数据
        base_price = 50.0
        returns = np.random.randn(100) * 0.02
        prices = base_price * np.cumprod(1 + returns)
        
        df = pd.DataFrame({
            'date': dates,
            'open': prices * (1 + np.random.randn(100) * 0.005),
            'high': prices * (1 + np.abs(np.random.randn(100) * 0.01)),
            'low': prices * (1 - np.abs(np.random.randn(100) * 0.01)),
            'close': prices,
            'volume': np.random.randint(1000000, 10000000, 100)
        })
        return df
    
    def test_calculate_indicators(self, screener, sample_data):
        """测试技术指标计算 (Requirements: 2.2)"""
        result = screener.calculate_indicators(sample_data)
        
        assert not result.empty
        
        # 验证 MA 指标
        assert 'ma5' in result.columns
        assert 'ma10' in result.columns
        assert 'ma20' in result.columns
        assert 'ma60' in result.columns
        
        # 验证 MACD 指标
        assert 'macd' in result.columns
        assert 'macd_signal' in result.columns
        assert 'macd_hist' in result.columns
        
        # 验证 RSI 指标
        assert 'rsi' in result.columns
        
        # 验证成交量均值
        assert 'volume_ma5' in result.columns
        
        # 验证价格别名
        assert 'price' in result.columns
        
        print("技术指标计算测试通过")
    
    def test_calculate_indicators_empty_data(self, screener):
        """测试空数据的指标计算"""
        result = screener.calculate_indicators(pd.DataFrame())
        assert result.empty
    
    def test_calculate_indicators_none_data(self, screener):
        """测试 None 数据的指标计算"""
        result = screener.calculate_indicators(None)
        assert result.empty


class TestSTStockFilter:
    """验证 ST 股票过滤功能"""
    
    @pytest.fixture
    def screener(self):
        """创建临时目录的 Screener 实例"""
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_path = os.path.join(tmpdir, 'raw')
            processed_path = os.path.join(tmpdir, 'processed')
            data_feed = DataFeed(raw_path, processed_path)
            yield Screener(data_feed)
    
    def test_check_st_stock_positive(self, screener):
        """测试 ST 股票识别 (Requirements: 2.8)"""
        assert screener._check_st_stock('ST某某') == True
        assert screener._check_st_stock('*ST某某') == True
        assert screener._check_st_stock('某某ST') == True
    
    def test_check_st_stock_negative(self, screener):
        """测试非 ST 股票"""
        assert screener._check_st_stock('平安银行') == False
        assert screener._check_st_stock('贵州茅台') == False
    
    def test_check_st_stock_none(self, screener):
        """测试 None 名称"""
        assert screener._check_st_stock(None) == False


class TestMA60TrendFilter:
    """验证 MA60 趋势过滤功能"""
    
    @pytest.fixture
    def screener(self):
        """创建临时目录的 Screener 实例"""
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_path = os.path.join(tmpdir, 'raw')
            processed_path = os.path.join(tmpdir, 'processed')
            data_feed = DataFeed(raw_path, processed_path)
            yield Screener(data_feed)
    
    def test_ma60_trend_upward(self, screener):
        """测试 MA60 上升趋势 (Requirements: 2.10)"""
        # 创建上升趋势数据
        dates = pd.date_range(start='2024-01-01', periods=70, freq='D')
        prices = [50 + i * 0.1 for i in range(70)]  # 持续上涨
        
        df = pd.DataFrame({
            'date': dates,
            'close': prices
        })
        
        result = screener._check_ma60_trend(df)
        assert result == True, "上升趋势应返回 True"
    
    def test_ma60_trend_downward(self, screener):
        """测试 MA60 下降趋势"""
        # 创建下降趋势数据
        dates = pd.date_range(start='2024-01-01', periods=70, freq='D')
        prices = [50 - i * 0.1 for i in range(70)]  # 持续下跌
        
        df = pd.DataFrame({
            'date': dates,
            'close': prices
        })
        
        result = screener._check_ma60_trend(df)
        assert result == False, "下降趋势应返回 False"
    
    def test_ma60_trend_insufficient_data(self, screener):
        """测试数据不足的情况"""
        dates = pd.date_range(start='2024-01-01', periods=50, freq='D')
        prices = [50 + i * 0.1 for i in range(50)]
        
        df = pd.DataFrame({
            'date': dates,
            'close': prices
        })
        
        result = screener._check_ma60_trend(df)
        assert result == False, "数据不足应返回 False"
    
    def test_ma60_trend_empty_data(self, screener):
        """测试空数据"""
        result = screener._check_ma60_trend(pd.DataFrame())
        assert result == False


class TestIndustryDiversification:
    """验证行业互斥功能"""
    
    @pytest.fixture
    def screener(self):
        """创建临时目录的 Screener 实例"""
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_path = os.path.join(tmpdir, 'raw')
            processed_path = os.path.join(tmpdir, 'processed')
            data_feed = DataFeed(raw_path, processed_path)
            yield Screener(data_feed)
    
    def test_industry_diversification_enabled(self, screener):
        """测试行业互斥启用 (Requirements: 2.12)"""
        # 创建测试结果，同一行业多只股票
        results = [
            ScreenerResult(code='000001', name='股票A', price=10.0, 
                          market_cap=10e9, turnover_rate=0.05, 
                          ma60_trend='上升', industry='银行'),
            ScreenerResult(code='000002', name='股票B', price=20.0,
                          market_cap=20e9, turnover_rate=0.06,
                          ma60_trend='上升', industry='银行'),
            ScreenerResult(code='000003', name='股票C', price=30.0,
                          market_cap=30e9, turnover_rate=0.07,
                          ma60_trend='上升', industry='科技'),
        ]
        
        screener.industry_diversification = IndustryDiversification(
            enabled=True, max_same_industry=1
        )
        
        diversified = screener._apply_industry_diversification(results)
        
        # 银行行业应只保留 1 只
        bank_stocks = [r for r in diversified if r.industry == '银行']
        assert len(bank_stocks) == 1, "银行行业应只保留 1 只"
        
        # 科技行业应保留
        tech_stocks = [r for r in diversified if r.industry == '科技']
        assert len(tech_stocks) == 1, "科技行业应保留"
        
        print("行业互斥测试通过")
    
    def test_industry_diversification_disabled(self, screener):
        """测试行业互斥禁用"""
        results = [
            ScreenerResult(code='000001', name='股票A', price=10.0,
                          market_cap=10e9, turnover_rate=0.05,
                          ma60_trend='上升', industry='银行'),
            ScreenerResult(code='000002', name='股票B', price=20.0,
                          market_cap=20e9, turnover_rate=0.06,
                          ma60_trend='上升', industry='银行'),
        ]
        
        screener.industry_diversification = IndustryDiversification(enabled=False)
        
        diversified = screener._apply_industry_diversification(results)
        
        assert len(diversified) == 2, "禁用时应保留所有股票"
    
    def test_industry_diversification_empty_results(self, screener):
        """测试空结果"""
        diversified = screener._apply_industry_diversification([])
        assert len(diversified) == 0


class TestConditionApplication:
    """验证条件应用功能"""
    
    @pytest.fixture
    def screener(self):
        """创建临时目录的 Screener 实例"""
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_path = os.path.join(tmpdir, 'raw')
            processed_path = os.path.join(tmpdir, 'processed')
            data_feed = DataFeed(raw_path, processed_path)
            yield Screener(data_feed)
    
    def test_apply_condition_greater(self, screener):
        """测试大于条件"""
        condition = ScreenerCondition('price', '>', 10.0)
        assert screener._apply_condition(15.0, condition) == True
        assert screener._apply_condition(5.0, condition) == False
    
    def test_apply_condition_less(self, screener):
        """测试小于条件"""
        condition = ScreenerCondition('rsi', '<', 80.0)
        assert screener._apply_condition(70.0, condition) == True
        assert screener._apply_condition(85.0, condition) == False
    
    def test_apply_condition_between(self, screener):
        """测试区间条件"""
        condition = ScreenerCondition('price', 'between', 10.0, 50.0)
        assert screener._apply_condition(30.0, condition) == True
        assert screener._apply_condition(5.0, condition) == False
        assert screener._apply_condition(60.0, condition) == False
    
    def test_apply_condition_equal(self, screener):
        """测试等于条件"""
        condition = ScreenerCondition('price', '==', 10.0)
        assert screener._apply_condition(10.0, condition) == True
        assert screener._apply_condition(10.000001, condition) == True  # 浮点容差
        assert screener._apply_condition(11.0, condition) == False


class TestMarketCondition:
    """验证大盘滤网功能"""
    
    @pytest.fixture
    def screener(self):
        """创建临时目录的 Screener 实例"""
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_path = os.path.join(tmpdir, 'raw')
            processed_path = os.path.join(tmpdir, 'processed')
            data_feed = DataFeed(raw_path, processed_path)
            yield Screener(data_feed)
    
    def test_market_filter_disabled(self, screener):
        """测试大盘滤网禁用 (Requirements: 2.11)"""
        screener.market_filter = MarketFilter(enabled=False)
        result = screener._check_market_condition()
        assert result == True, "禁用时应返回 True"
    
    def test_get_market_status(self, screener):
        """测试获取大盘状态"""
        status = screener.get_market_status()
        
        assert 'status' in status
        assert status['status'] in ['healthy', 'unhealthy', 'unknown', 'error']
        
        if status['status'] in ['healthy', 'unhealthy']:
            assert 'current_price' in status
            assert 'ma20' in status
            assert 'is_above_ma' in status
        
        print(f"大盘状态: {status}")


class TestPrePruningPerformance:
    """验证预剪枝性能提升"""
    
    @pytest.fixture
    def data_feed(self):
        """创建临时目录的 DataFeed 实例"""
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_path = os.path.join(tmpdir, 'raw')
            processed_path = os.path.join(tmpdir, 'processed')
            yield DataFeed(raw_path, processed_path)
    
    def test_snapshot_returns_filtered_candidates(self, data_feed):
        """测试快照返回过滤后的候选池 (Requirements: 2.13)"""
        # 获取全市场快照
        snapshot = data_feed.get_market_snapshot()
        
        assert snapshot is not None
        
        if not snapshot.empty:
            # 验证预剪枝效果：候选池应远小于全市场股票数
            # A股全市场约 5000+ 只，预剪枝后应在 100-500 只左右
            candidate_count = len(snapshot)
            
            print(f"预剪枝后候选池: {candidate_count} 只股票")
            
            # 验证过滤条件生效
            default_filter = LiquidityFilter()
            
            # 市值过滤
            assert (snapshot['market_cap'] >= default_filter.min_market_cap).all()
            assert (snapshot['market_cap'] <= default_filter.max_market_cap).all()
            
            # 换手率过滤
            assert (snapshot['turnover_rate'] >= default_filter.min_turnover_rate).all()
            assert (snapshot['turnover_rate'] <= default_filter.max_turnover_rate).all()
            
            # ST 过滤
            assert not snapshot['name'].str.contains('ST', na=False).any()
    
    def test_snapshot_performance(self, data_feed):
        """测试快照获取性能"""
        start_time = time.time()
        snapshot = data_feed.get_market_snapshot()
        elapsed = time.time() - start_time
        
        print(f"快照获取耗时: {elapsed:.2f} 秒")
        
        # 快照获取应在合理时间内完成（通常 1-5 秒）
        assert elapsed < 30, f"快照获取耗时过长: {elapsed:.2f} 秒"


class TestScreenerResult:
    """验证筛选结果数据类"""
    
    def test_screener_result_creation(self):
        """测试筛选结果创建"""
        result = ScreenerResult(
            code='000001',
            name='平安银行',
            price=10.5,
            market_cap=10e9,
            turnover_rate=0.05,
            ma60_trend='上升',
            industry='银行',
            indicators={'ma60': 10.2, 'rsi': 55.0}
        )
        
        assert result.code == '000001'
        assert result.name == '平安银行'
        assert result.price == 10.5
        assert result.industry == '银行'
        assert result.in_report_window == False
    
    def test_screener_result_to_dict(self):
        """测试筛选结果转字典"""
        result = ScreenerResult(
            code='000001',
            name='平安银行',
            price=10.5,
            market_cap=10e9,
            turnover_rate=0.05,
            ma60_trend='上升',
            industry='银行'
        )
        
        d = result.to_dict()
        
        assert d['code'] == '000001'
        assert d['name'] == '平安银行'
        assert 'indicators' in d


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
