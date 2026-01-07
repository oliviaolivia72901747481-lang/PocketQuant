"""
Tests for KLinePatternScorer and VolumePriceScorer in scorer_v6.py
"""
import pytest
from core.overnight_picker.scorer_v6 import KLinePatternScorer, VolumePriceScorer, ScorerV6


class TestKLinePatternScorer:
    """Tests for KLinePatternScorer"""
    
    def setup_method(self):
        self.scorer = KLinePatternScorer()
    
    def test_limit_up_pattern(self):
        """Test limit up detection gives max score"""
        # 10% limit up
        score, details, risks = self.scorer.score(
            open_p=10.0, high=11.0, low=9.9, close=11.0, prev_close=10.0
        )
        assert score == 15
        assert details['pattern'] == '涨停'
        assert details['is_limit_up'] == True
    
    def test_normal_positive_candle(self):
        """Test normal positive candle"""
        score, details, risks = self.scorer.score(
            open_p=10.0, high=10.5, low=9.8, close=10.3, prev_close=10.0
        )
        assert score == 8
        assert details['pattern'] == '阳线'
        assert details['is_positive'] == True
    
    def test_normal_negative_candle(self):
        """Test normal negative candle"""
        score, details, risks = self.scorer.score(
            open_p=10.0, high=10.2, low=9.5, close=9.7, prev_close=10.0
        )
        assert score == 4
        assert details['pattern'] == '阴线'
        assert details['is_positive'] == False
    
    def test_doji_pattern(self):
        """Test doji (cross star) pattern"""
        score, details, risks = self.scorer.score(
            open_p=10.0, high=10.5, low=9.5, close=10.01, prev_close=10.0
        )
        assert score == 10
        assert details['pattern'] == '十字星'
    
    def test_hammer_pattern(self):
        """Test hammer (lower shadow positive) pattern"""
        score, details, risks = self.scorer.score(
            open_p=10.0, high=10.1, low=9.0, close=10.05, prev_close=10.0
        )
        assert score == 12
        assert details['pattern'] == '下影线阳线'
    
    def test_hanging_man_at_high(self):
        """Test hanging man at high position gives 0 score"""
        score, details, risks = self.scorer.score(
            open_p=10.0, high=10.1, low=9.0, close=10.05, prev_close=10.0,
            is_at_high=True
        )
        assert score == 0
        assert details['pattern'] == '吊颈线'
        assert '顶部形态风险' in risks
    
    def test_score_bounds(self):
        """Test score is always within 0-15"""
        # Various test cases
        test_cases = [
            {'open_p': 10.0, 'high': 11.0, 'low': 9.9, 'close': 11.0, 'prev_close': 10.0},
            {'open_p': 10.0, 'high': 10.5, 'low': 9.5, 'close': 9.7, 'prev_close': 10.0},
            {'open_p': 10.0, 'high': 10.1, 'low': 9.9, 'close': 10.0, 'prev_close': 10.0},
        ]
        for tc in test_cases:
            score, details, risks = self.scorer.score(**tc)
            assert 0 <= score <= 15, f"Score {score} out of bounds for {tc}"
    
    def test_invalid_data(self):
        """Test handling of invalid data"""
        score, details, risks = self.scorer.score(
            open_p=0, high=0, low=0, close=0, prev_close=0
        )
        assert score == 0
        assert details['pattern'] == '数据无效'
    
    def test_cyb_kcb_limit_up(self):
        """Test 20% limit up for ChiNext/STAR Market"""
        # 20% limit up
        score, details, risks = self.scorer.score(
            open_p=10.0, high=12.0, low=10.0, close=12.0, prev_close=10.0,
            is_cyb_kcb=True
        )
        assert score == 15
        assert details['pattern'] == '涨停'


class TestVolumePriceScorer:
    """Tests for VolumePriceScorer"""
    
    def setup_method(self):
        self.scorer = VolumePriceScorer()
    
    def test_moderate_volume_increase(self):
        """Test moderate volume increase with positive change"""
        score, details, risks = self.scorer.score(
            volume=1500000, ma5_vol=1000000, change_pct=5.0, turnover_rate=8.0
        )
        assert score == 15
        assert details['volume_type'] == '温和放量上涨'
        assert details['volume_class'] == '温和放量'
    
    def test_shrink_volume_limit_up(self):
        """Test shrink volume with limit up"""
        score, details, risks = self.scorer.score(
            volume=700000, ma5_vol=1000000, change_pct=10.0, turnover_rate=5.0
        )
        assert score == 15
        assert details['volume_type'] == '缩量涨停'
    
    def test_high_volume_stagnation(self):
        """Test high volume stagnation at high position"""
        score, details, risks = self.scorer.score(
            volume=4000000, ma5_vol=1000000, change_pct=1.0, turnover_rate=10.0,
            is_at_high=True
        )
        assert score == 0
        assert details['volume_type'] == '高位巨量滞涨'
        assert '出货风险' in risks
    
    def test_huge_volume_negative(self):
        """Test huge volume with negative change (distribution)"""
        score, details, risks = self.scorer.score(
            volume=4000000, ma5_vol=1000000, change_pct=-5.0, turnover_rate=15.0
        )
        assert score == 0
        assert details['volume_type'] == '天量阴线'
        assert '出货风险' in risks
    
    def test_bottom_double_volume(self):
        """Test double volume at bottom"""
        score, details, risks = self.scorer.score(
            volume=2500000, ma5_vol=1000000, change_pct=5.0, turnover_rate=8.0,
            is_at_bottom=True
        )
        assert score == 15
        assert details['volume_type'] == '底部/突破倍量'
    
    def test_turnover_rate_adjustment_low(self):
        """Test turnover rate adjustment for low turnover"""
        score, details, risks = self.scorer.score(
            volume=1500000, ma5_vol=1000000, change_pct=5.0, turnover_rate=0.5
        )
        # Base score 15 - 2 (low turnover) = 13
        assert score == 13
        assert details['turnover_adjustment'] == -2
    
    def test_turnover_rate_adjustment_high(self):
        """Test turnover rate adjustment for high turnover"""
        score, details, risks = self.scorer.score(
            volume=1500000, ma5_vol=1000000, change_pct=5.0, turnover_rate=30.0
        )
        # Base score 15 - 3 (high turnover) = 12
        assert score == 12
        assert details['turnover_adjustment'] == -3
    
    def test_score_bounds(self):
        """Test score is always within 0-15"""
        test_cases = [
            {'volume': 1500000, 'ma5_vol': 1000000, 'change_pct': 5.0, 'turnover_rate': 8.0},
            {'volume': 500000, 'ma5_vol': 1000000, 'change_pct': -3.0, 'turnover_rate': 5.0},
            {'volume': 4000000, 'ma5_vol': 1000000, 'change_pct': -5.0, 'turnover_rate': 20.0},
        ]
        for tc in test_cases:
            score, details, risks = self.scorer.score(**tc)
            assert 0 <= score <= 15, f"Score {score} out of bounds for {tc}"
    
    def test_zero_volume(self):
        """Test handling of zero volume"""
        score, details, risks = self.scorer.score(
            volume=0, ma5_vol=1000000, change_pct=5.0, turnover_rate=5.0
        )
        assert score == 0
        assert details['volume_type'] == '无成交'


class TestScorerV6Integration:
    """Integration tests for ScorerV6 with KLine and Volume scorers"""
    
    def setup_method(self):
        self.scorer = ScorerV6()
    
    def test_basic_scoring(self):
        """Test basic stock scoring"""
        stock_data = {
            'code': '000001',
            'close': 15.0,
            'open': 14.5,
            'high': 15.2,
            'low': 14.3,
            'prev_close': 14.0,
            'ma5': 14.2,
            'ma10': 14.0,
            'ma20': 13.8,
            'ma60': 13.5,
            'price_percentile': 40,
            'volume': 1500000,
            'ma5_vol': 1000000,
            'change_pct': 7.14,
            'turnover_rate': 6.0,
        }
        total_score, details = self.scorer.score_stock(stock_data)
        
        # Check total score is sum of dimensions
        expected_sum = (
            details['trend_position']['score'] +
            details['kline_pattern']['score'] +
            details['volume_price']['score'] +
            details['capital_strength']['score'] +
            details['theme_wind']['score'] +
            details['stock_activity']['score']
        )
        assert total_score == expected_sum
        
        # Check individual scores are within bounds
        assert 0 <= details['trend_position']['score'] <= 20
        assert 0 <= details['kline_pattern']['score'] <= 15
        assert 0 <= details['volume_price']['score'] <= 15
    
    def test_cyb_stock_detection(self):
        """Test ChiNext stock detection"""
        stock_data = {
            'code': '300001',  # ChiNext stock
            'close': 22.0,
            'open': 20.0,
            'high': 22.0,
            'low': 20.0,
            'prev_close': 20.0,
            'ma5': 19.0,
            'ma10': 18.5,
            'ma20': 18.0,
            'ma60': 17.0,
            'price_percentile': 50,
            'volume': 1000000,
            'ma5_vol': 1000000,
            'change_pct': 10.0,
            'turnover_rate': 5.0,
        }
        total_score, details = self.scorer.score_stock(stock_data)
        
        # 10% change is not limit up for ChiNext (needs 20%)
        assert details['kline_pattern']['pattern'] != '涨停'
    
    def test_high_position_risk_marking(self):
        """Test risk marking at high position"""
        stock_data = {
            'code': '000001',
            'close': 15.0,
            'open': 15.0,
            'high': 15.1,
            'low': 14.0,
            'prev_close': 15.0,
            'ma5': 14.0,
            'ma10': 13.5,
            'ma20': 13.0,
            'ma60': 12.0,
            'price_percentile': 85,  # High position
            'volume': 4000000,
            'ma5_vol': 1000000,
            'change_pct': 0.5,
            'turnover_rate': 10.0,
        }
        total_score, details = self.scorer.score_stock(stock_data)
        
        # Should have distribution risk
        assert '出货风险' in details['risks']
    
    def test_score_summary_generation(self):
        """Test score summary generation"""
        stock_data = {
            'code': '000001',
            'close': 15.0,
            'open': 14.5,
            'high': 15.2,
            'low': 14.3,
            'prev_close': 14.0,
            'ma5': 14.2,
            'ma10': 14.0,
            'ma20': 13.8,
            'ma60': 13.5,
            'price_percentile': 40,
            'volume': 1500000,
            'ma5_vol': 1000000,
            'change_pct': 7.14,
            'turnover_rate': 6.0,
        }
        total_score, details = self.scorer.score_stock(stock_data)
        summary = self.scorer.get_score_summary(total_score, details)
        
        assert '评分系统v6.0' in summary
        assert '趋势与位置' in summary
        assert 'K线与形态' in summary
        assert '量价配合' in summary


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
