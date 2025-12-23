"""
硬性筛选器单元测试

测试 HardFilter 类的各项功能：
- 股价筛选 (股价 <= 80元)
- 流通市值筛选 (50亿 <= 市值 <= 500亿)
- 日均成交额筛选 (成交额 >= 1亿)
- 筛选汇总统计

Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6
"""

import pytest
from core.tech_stock import HardFilter, HardFilterResult


class TestHardFilterCheckMethods:
    """测试硬性筛选器的检查方法"""
    
    def setup_method(self):
        """每个测试方法前初始化"""
        self.filter = HardFilter()
    
    # ==================== 股价检查测试 ====================
    
    def test_check_price_valid_low(self):
        """测试低于阈值的股价应该通过"""
        passed, reason = self.filter._check_price(50.0)
        assert passed is True
        assert reason is None
    
    def test_check_price_valid_at_threshold(self):
        """测试等于阈值的股价应该通过"""
        passed, reason = self.filter._check_price(80.0)
        assert passed is True
        assert reason is None
    
    def test_check_price_invalid_high(self):
        """测试高于阈值的股价应该被拒绝"""
        passed, reason = self.filter._check_price(100.0)
        assert passed is False
        assert "股价" in reason
        assert "100.00" in reason
        assert "80" in reason
    
    def test_check_price_invalid_zero(self):
        """测试零股价应该被拒绝"""
        passed, reason = self.filter._check_price(0.0)
        assert passed is False
        assert "无效" in reason
    
    def test_check_price_invalid_negative(self):
        """测试负股价应该被拒绝"""
        passed, reason = self.filter._check_price(-10.0)
        assert passed is False
        assert "无效" in reason
    
    # ==================== 流通市值检查测试 ====================
    
    def test_check_market_cap_valid_middle(self):
        """测试在范围内的市值应该通过"""
        passed, reason = self.filter._check_market_cap(200.0)
        assert passed is True
        assert reason is None
    
    def test_check_market_cap_valid_at_min(self):
        """测试等于最小阈值的市值应该通过"""
        passed, reason = self.filter._check_market_cap(50.0)
        assert passed is True
        assert reason is None
    
    def test_check_market_cap_valid_at_max(self):
        """测试等于最大阈值的市值应该通过"""
        passed, reason = self.filter._check_market_cap(500.0)
        assert passed is True
        assert reason is None
    
    def test_check_market_cap_invalid_too_small(self):
        """测试低于最小阈值的市值应该被拒绝"""
        passed, reason = self.filter._check_market_cap(30.0)
        assert passed is False
        assert "流通市值" in reason
        assert "30.0" in reason
        assert "50" in reason
    
    def test_check_market_cap_invalid_too_large(self):
        """测试高于最大阈值的市值应该被拒绝"""
        passed, reason = self.filter._check_market_cap(600.0)
        assert passed is False
        assert "流通市值" in reason
        assert "600.0" in reason
        assert "500" in reason
    
    def test_check_market_cap_invalid_zero(self):
        """测试零市值应该被拒绝"""
        passed, reason = self.filter._check_market_cap(0.0)
        assert passed is False
        assert "无效" in reason
    
    # ==================== 日均成交额检查测试 ====================
    
    def test_check_turnover_valid_high(self):
        """测试高于阈值的成交额应该通过"""
        passed, reason = self.filter._check_turnover(5.0)
        assert passed is True
        assert reason is None
    
    def test_check_turnover_valid_at_threshold(self):
        """测试等于阈值的成交额应该通过"""
        passed, reason = self.filter._check_turnover(1.0)
        assert passed is True
        assert reason is None
    
    def test_check_turnover_invalid_low(self):
        """测试低于阈值的成交额应该被拒绝"""
        passed, reason = self.filter._check_turnover(0.5)
        assert passed is False
        assert "成交额" in reason
        assert "0.50" in reason
        assert "1" in reason
    
    def test_check_turnover_invalid_zero(self):
        """测试零成交额应该被拒绝"""
        passed, reason = self.filter._check_turnover(0.0)
        assert passed is False
        assert "成交额" in reason


class TestHardFilterFilterStocks:
    """测试硬性筛选器的主筛选方法"""
    
    def setup_method(self):
        """每个测试方法前初始化"""
        self.filter = HardFilter()
    
    def test_filter_stocks_all_pass(self):
        """测试所有股票都通过筛选的情况"""
        mock_data = {
            "000001": {"name": "股票A", "price": 50.0, "market_cap": 200.0, "avg_turnover": 5.0},
            "000002": {"name": "股票B", "price": 30.0, "market_cap": 100.0, "avg_turnover": 2.0},
        }
        
        results = self.filter.filter_stocks(list(mock_data.keys()), mock_data)
        
        assert len(results) == 2
        assert all(r.passed for r in results)
        assert all(len(r.reject_reasons) == 0 for r in results)
    
    def test_filter_stocks_all_reject(self):
        """测试所有股票都被拒绝的情况"""
        mock_data = {
            "000001": {"name": "高价股", "price": 150.0, "market_cap": 200.0, "avg_turnover": 5.0},
            "000002": {"name": "大盘股", "price": 50.0, "market_cap": 1000.0, "avg_turnover": 5.0},
        }
        
        results = self.filter.filter_stocks(list(mock_data.keys()), mock_data)
        
        assert len(results) == 2
        assert all(not r.passed for r in results)
        assert all(len(r.reject_reasons) > 0 for r in results)
    
    def test_filter_stocks_mixed(self):
        """测试部分通过部分拒绝的情况"""
        mock_data = {
            "000001": {"name": "通过股", "price": 50.0, "market_cap": 200.0, "avg_turnover": 5.0},
            "000002": {"name": "高价股", "price": 150.0, "market_cap": 200.0, "avg_turnover": 5.0},
            "000003": {"name": "小盘股", "price": 30.0, "market_cap": 20.0, "avg_turnover": 2.0},
        }
        
        results = self.filter.filter_stocks(list(mock_data.keys()), mock_data)
        
        assert len(results) == 3
        passed = [r for r in results if r.passed]
        rejected = [r for r in results if not r.passed]
        
        assert len(passed) == 1
        assert len(rejected) == 2
        assert passed[0].code == "000001"
    
    def test_filter_stocks_multiple_reject_reasons(self):
        """测试一只股票有多个拒绝原因的情况"""
        mock_data = {
            "000001": {"name": "问题股", "price": 150.0, "market_cap": 1000.0, "avg_turnover": 0.3},
        }
        
        results = self.filter.filter_stocks(list(mock_data.keys()), mock_data)
        
        assert len(results) == 1
        assert not results[0].passed
        assert len(results[0].reject_reasons) == 3  # 股价、市值、成交额都不符合
    
    def test_filter_stocks_missing_data(self):
        """测试股票数据缺失的情况"""
        mock_data = {
            "000001": {"name": "有数据", "price": 50.0, "market_cap": 200.0, "avg_turnover": 5.0},
        }
        
        # 请求两只股票，但只有一只有数据
        results = self.filter.filter_stocks(["000001", "000002"], mock_data)
        
        assert len(results) == 2
        
        # 有数据的应该通过
        result_001 = next(r for r in results if r.code == "000001")
        assert result_001.passed
        
        # 无数据的应该被拒绝
        result_002 = next(r for r in results if r.code == "000002")
        assert not result_002.passed
        assert any("无法获取" in reason for reason in result_002.reject_reasons)


class TestHardFilterSummary:
    """测试硬性筛选器的汇总统计方法"""
    
    def setup_method(self):
        """每个测试方法前初始化"""
        self.filter = HardFilter()
    
    def test_get_filter_summary_all_pass(self):
        """测试所有通过时的汇总"""
        results = [
            HardFilterResult("000001", "股票A", True, 50.0, 200.0, 5.0, []),
            HardFilterResult("000002", "股票B", True, 30.0, 100.0, 2.0, []),
        ]
        
        summary = self.filter.get_filter_summary(results)
        
        assert summary["total"] == 2
        assert summary["passed"] == 2
        assert summary["rejected"] == 0
        assert summary["pass_rate"] == 100.0
    
    def test_get_filter_summary_all_reject(self):
        """测试所有拒绝时的汇总"""
        results = [
            HardFilterResult("000001", "高价股", False, 150.0, 200.0, 5.0, ["股价 150.00元 > 80.0元"]),
            HardFilterResult("000002", "大盘股", False, 50.0, 1000.0, 5.0, ["流通市值 1000.0亿 > 500.0亿"]),
        ]
        
        summary = self.filter.get_filter_summary(results)
        
        assert summary["total"] == 2
        assert summary["passed"] == 0
        assert summary["rejected"] == 2
        assert summary["reject_by_price"] == 1
        assert summary["reject_by_market_cap"] == 1
        assert summary["pass_rate"] == 0.0
    
    def test_get_filter_summary_mixed(self):
        """测试混合情况的汇总"""
        results = [
            HardFilterResult("000001", "通过股", True, 50.0, 200.0, 5.0, []),
            HardFilterResult("000002", "高价股", False, 150.0, 200.0, 5.0, ["股价 150.00元 > 80.0元"]),
            HardFilterResult("000003", "小盘股", False, 30.0, 20.0, 2.0, ["流通市值 20.0亿 < 50.0亿"]),
            HardFilterResult("000004", "低成交", False, 30.0, 100.0, 0.3, ["日均成交额 0.30亿 < 1.0亿"]),
        ]
        
        summary = self.filter.get_filter_summary(results)
        
        assert summary["total"] == 4
        assert summary["passed"] == 1
        assert summary["rejected"] == 3
        assert summary["reject_by_price"] == 1
        assert summary["reject_by_market_cap"] == 1
        assert summary["reject_by_turnover"] == 1
        assert summary["pass_rate"] == 25.0
    
    def test_get_filter_summary_empty(self):
        """测试空列表的汇总"""
        summary = self.filter.get_filter_summary([])
        
        assert summary["total"] == 0
        assert summary["passed"] == 0
        assert summary["rejected"] == 0
        assert summary["pass_rate"] == 0.0


class TestHardFilterHelperMethods:
    """测试硬性筛选器的辅助方法"""
    
    def setup_method(self):
        """每个测试方法前初始化"""
        self.filter = HardFilter()
    
    def test_get_passed_stocks(self):
        """测试获取通过筛选的股票列表"""
        results = [
            HardFilterResult("000001", "通过1", True, 50.0, 200.0, 5.0, []),
            HardFilterResult("000002", "拒绝1", False, 150.0, 200.0, 5.0, ["股价过高"]),
            HardFilterResult("000003", "通过2", True, 30.0, 100.0, 2.0, []),
        ]
        
        passed = self.filter.get_passed_stocks(results)
        
        assert len(passed) == 2
        assert "000001" in passed
        assert "000003" in passed
        assert "000002" not in passed
    
    def test_get_rejected_stocks(self):
        """测试获取未通过筛选的股票列表"""
        results = [
            HardFilterResult("000001", "通过1", True, 50.0, 200.0, 5.0, []),
            HardFilterResult("000002", "拒绝1", False, 150.0, 200.0, 5.0, ["股价过高"]),
            HardFilterResult("000003", "拒绝2", False, 30.0, 20.0, 2.0, ["市值过小"]),
        ]
        
        rejected = self.filter.get_rejected_stocks(results)
        
        assert len(rejected) == 2
        assert all(not r.passed for r in rejected)
        codes = [r.code for r in rejected]
        assert "000002" in codes
        assert "000003" in codes
    
    def test_format_results_for_display(self):
        """测试格式化结果为 DataFrame"""
        results = [
            HardFilterResult("000001", "通过股", True, 50.0, 200.0, 5.0, []),
            HardFilterResult("000002", "拒绝股", False, 150.0, 200.0, 5.0, ["股价过高"]),
        ]
        
        df = self.filter.format_results_for_display(results)
        
        assert len(df) == 2
        assert "代码" in df.columns
        assert "名称" in df.columns
        assert "通过" in df.columns
        assert "股价(元)" in df.columns
        assert "流通市值(亿)" in df.columns
        assert "日均成交额(亿)" in df.columns
        assert "拒绝原因" in df.columns
