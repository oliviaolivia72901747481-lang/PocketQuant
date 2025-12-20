"""
MiniQuant-Lite 数据层验证测试

Checkpoint 3: 数据层验证
- 验证 AkShare 接口可用性
- 验证 DataFeed 模块基础功能
- 验证数据清洗格式正确性

Requirements: 1.1, 1.2, 1.3, 1.4, 1.6, 1.8
"""

import pytest
import pandas as pd
import tempfile
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.data_feed import DataFeed, LiquidityFilter


class TestAkShareAvailability:
    """验证 AkShare 接口可用性"""
    
    def test_akshare_import(self):
        """测试 AkShare 是否可以正常导入"""
        import akshare as ak
        assert ak is not None
        assert hasattr(ak, '__version__')
        print(f"AkShare 版本: {ak.__version__}")
    
    def test_akshare_stock_hist_api(self):
        """测试 AkShare 股票历史数据接口是否可用"""
        import akshare as ak
        
        # 使用平安银行(000001)作为测试股票
        try:
            df = ak.stock_zh_a_hist(
                symbol='000001',
                period='daily',
                start_date='20240101',
                end_date='20240110',
                adjust='qfq'
            )
            
            assert df is not None, "API 返回 None"
            assert not df.empty, "API 返回空数据"
            
            # 验证必需列存在
            required_columns = ['日期', '开盘', '收盘', '最高', '最低', '成交量']
            for col in required_columns:
                assert col in df.columns, f"缺少必需列: {col}"
            
            print(f"股票历史数据接口测试通过，返回 {len(df)} 条记录")
            
        except Exception as e:
            pytest.fail(f"AkShare 股票历史数据接口不可用: {e}")
    
    def test_akshare_market_snapshot_api(self):
        """测试 AkShare 全市场快照接口是否可用"""
        import akshare as ak
        import requests
        
        try:
            df = ak.stock_zh_a_spot_em()
            
            assert df is not None, "API 返回 None"
            assert not df.empty, "API 返回空数据"
            
            # 验证必需列存在
            required_columns = ['代码', '名称', '最新价', '流通市值', '换手率']
            for col in required_columns:
                assert col in df.columns, f"缺少必需列: {col}"
            
            print(f"全市场快照接口测试通过，返回 {len(df)} 只股票")
            
        except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as e:
            pytest.skip(f"网络超时，跳过测试: {e}")
        except Exception as e:
            pytest.fail(f"AkShare 全市场快照接口不可用: {e}")


class TestDataFeedBasic:
    """验证 DataFeed 模块基础功能"""
    
    @pytest.fixture
    def data_feed(self):
        """创建临时目录的 DataFeed 实例"""
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_path = os.path.join(tmpdir, 'raw')
            processed_path = os.path.join(tmpdir, 'processed')
            yield DataFeed(raw_path, processed_path)
    
    def test_data_feed_initialization(self, data_feed):
        """测试 DataFeed 初始化"""
        assert data_feed is not None
        assert os.path.exists(data_feed.raw_path)
        assert os.path.exists(data_feed.processed_path)
    
    def test_download_single_stock(self, data_feed):
        """测试单只股票数据下载（前复权）"""
        # 下载平安银行最近10天数据
        df = data_feed.download_stock_data(
            code='000001',
            start_date='2024-01-01',
            end_date='2024-01-10',
            adjust='qfq'
        )
        
        assert df is not None, "下载返回 None"
        assert not df.empty, "下载返回空数据"
        print(f"单只股票下载测试通过，返回 {len(df)} 条记录")
    
    def test_download_invalid_stock(self, data_feed):
        """测试无效股票代码处理"""
        # 使用不存在的股票代码
        df = data_feed.download_stock_data(
            code='999999',
            start_date='2024-01-01',
            end_date='2024-01-10'
        )
        
        # 应该返回 None 或空 DataFrame，不应抛出异常
        assert df is None or df.empty, "无效股票代码应返回 None 或空数据"
        print("无效股票代码处理测试通过")


class TestDataCleaning:
    """验证数据清洗功能"""
    
    @pytest.fixture
    def data_feed(self):
        """创建临时目录的 DataFeed 实例"""
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_path = os.path.join(tmpdir, 'raw')
            processed_path = os.path.join(tmpdir, 'processed')
            yield DataFeed(raw_path, processed_path)
    
    def test_clean_data_format(self, data_feed):
        """测试数据清洗后的格式正确性 (Requirements: 1.2)"""
        # 先下载原始数据
        raw_df = data_feed.download_stock_data(
            code='000001',
            start_date='2024-01-01',
            end_date='2024-01-31'
        )
        
        assert raw_df is not None and not raw_df.empty, "无法获取测试数据"
        
        # 清洗数据
        cleaned_df = data_feed.clean_data(raw_df)
        
        # 验证清洗后的格式
        assert not cleaned_df.empty, "清洗后数据为空"
        
        # 验证 Backtrader 兼容格式的列
        required_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
        for col in required_columns:
            assert col in cleaned_df.columns, f"清洗后数据缺少列: {col}"
        
        # 验证数据类型
        assert pd.api.types.is_datetime64_any_dtype(cleaned_df['date']), "date 列应为 datetime 类型"
        assert pd.api.types.is_numeric_dtype(cleaned_df['open']), "open 列应为数值类型"
        assert pd.api.types.is_numeric_dtype(cleaned_df['close']), "close 列应为数值类型"
        assert pd.api.types.is_numeric_dtype(cleaned_df['volume']), "volume 列应为数值类型"
        
        # 验证数据排序（按日期升序）
        dates = cleaned_df['date'].tolist()
        assert dates == sorted(dates), "数据应按日期升序排列"
        
        # 验证无 NaN 值
        assert not cleaned_df.isnull().any().any(), "清洗后数据不应包含 NaN"
        
        print(f"数据清洗格式测试通过，清洗后 {len(cleaned_df)} 条记录")
    
    def test_clean_empty_data(self, data_feed):
        """测试空数据清洗"""
        empty_df = pd.DataFrame()
        cleaned = data_feed.clean_data(empty_df)
        assert cleaned.empty, "空数据清洗后应为空"
    
    def test_clean_none_data(self, data_feed):
        """测试 None 数据清洗"""
        cleaned = data_feed.clean_data(None)
        assert cleaned.empty, "None 数据清洗后应为空"


class TestOverwriteUpdate:
    """验证覆盖更新功能"""
    
    @pytest.fixture
    def data_feed(self):
        """创建临时目录的 DataFeed 实例"""
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_path = os.path.join(tmpdir, 'raw')
            processed_path = os.path.join(tmpdir, 'processed')
            yield DataFeed(raw_path, processed_path)
    
    def test_overwrite_update(self, data_feed):
        """测试覆盖更新功能 (Requirements: 1.6)"""
        # 执行覆盖更新
        success = data_feed.overwrite_update(code='000001', days=30)
        
        assert success, "覆盖更新应成功"
        
        # 验证文件已创建
        file_path = os.path.join(data_feed.processed_path, '000001.csv')
        assert os.path.exists(file_path), "覆盖更新后应创建数据文件"
        
        # 验证可以加载数据
        loaded_df = data_feed.load_processed_data('000001')
        assert loaded_df is not None and not loaded_df.empty, "应能加载更新后的数据"
        
        print(f"覆盖更新测试通过，保存 {len(loaded_df)} 条记录")


class TestMarketSnapshot:
    """验证全市场快照功能"""
    
    @pytest.fixture
    def data_feed(self):
        """创建临时目录的 DataFeed 实例"""
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_path = os.path.join(tmpdir, 'raw')
            processed_path = os.path.join(tmpdir, 'processed')
            yield DataFeed(raw_path, processed_path)
    
    def test_market_snapshot_basic(self, data_feed):
        """测试全市场快照基础功能 (Requirements: 1.8)"""
        import requests
        
        try:
            snapshot = data_feed.get_market_snapshot()
            
            assert snapshot is not None, "快照不应为 None"
            
            # 如果快照为空，可能是网络问题，跳过测试
            if snapshot.empty:
                pytest.skip("快照为空，可能是网络超时")
            
            # 验证输出列
            required_columns = ['code', 'name', 'price', 'market_cap', 'turnover_rate']
            for col in required_columns:
                assert col in snapshot.columns, f"快照缺少列: {col}"
            
            print(f"全市场快照测试通过，返回 {len(snapshot)} 只候选股票")
            
        except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as e:
            pytest.skip(f"网络超时，跳过测试: {e}")
    
    def test_market_snapshot_with_filter(self, data_feed):
        """测试带流动性过滤的全市场快照"""
        # 使用更严格的过滤条件
        strict_filter = LiquidityFilter(
            min_market_cap=10e9,   # 100亿
            max_market_cap=30e10,  # 3000亿
            min_turnover_rate=0.03,  # 3%
            max_turnover_rate=0.10,  # 10%
            exclude_st=True
        )
        
        snapshot = data_feed.get_market_snapshot(liquidity_filter=strict_filter)
        
        assert snapshot is not None, "快照不应为 None"
        
        if not snapshot.empty:
            # 验证过滤条件生效
            assert (snapshot['market_cap'] >= strict_filter.min_market_cap).all(), "市值下限过滤失效"
            assert (snapshot['market_cap'] <= strict_filter.max_market_cap).all(), "市值上限过滤失效"
            assert (snapshot['turnover_rate'] >= strict_filter.min_turnover_rate).all(), "换手率下限过滤失效"
            assert (snapshot['turnover_rate'] <= strict_filter.max_turnover_rate).all(), "换手率上限过滤失效"
            
            # 验证无 ST 股票
            assert not snapshot['name'].str.contains('ST', na=False).any(), "应剔除 ST 股票"
        
        print(f"带过滤的全市场快照测试通过，返回 {len(snapshot)} 只候选股票")


class TestBatchDownload:
    """验证批量下载功能"""
    
    @pytest.fixture
    def data_feed(self):
        """创建临时目录的 DataFeed 实例"""
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_path = os.path.join(tmpdir, 'raw')
            processed_path = os.path.join(tmpdir, 'processed')
            yield DataFeed(raw_path, processed_path)
    
    def test_batch_download(self, data_feed):
        """测试批量下载功能 (Requirements: 1.5)"""
        # 使用少量股票测试
        test_codes = ['000001', '000002']
        
        results = data_feed.download_batch(
            codes=test_codes,
            start_date='2024-01-01',
            end_date='2024-01-10'
        )
        
        assert results is not None, "批量下载结果不应为 None"
        assert len(results) > 0, "批量下载应返回至少一只股票的数据"
        
        # 验证返回的数据格式
        for code, df in results.items():
            assert code in test_codes, f"返回了未请求的股票: {code}"
            assert not df.empty, f"股票 {code} 数据为空"
        
        print(f"批量下载测试通过，成功下载 {len(results)}/{len(test_codes)} 只股票")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
