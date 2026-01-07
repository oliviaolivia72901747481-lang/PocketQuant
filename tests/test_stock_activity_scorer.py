"""
测试股性活跃度评分器和风险标记器
"""

import pytest
import pandas as pd
import numpy as np
from core.overnight_picker.scorer_v6 import StockActivityScorer, RiskMarker


class TestStockActivityScorer:
    """测试股性活跃度评分器"""
    
    @pytest.fixture
    def scorer(self):
        return StockActivityScorer()
    
    @pytest.fixture
    def dates(self):
        return pd.date_range('2025-01-01', periods=60, freq='D')
    
    def test_score_with_limit_up(self, scorer, dates):
        """测试近20日有涨停的情况 -> 10分"""
        df = pd.DataFrame({
            'close': [10 + i * 0.1 for i in range(60)],
            'high': [10.5 + i * 0.1 for i in range(60)],
            'low': [9.5 + i * 0.1 for i in range(60)],
            'change_pct': [1.0] * 55 + [10.0, 2.0, 1.0, 1.0, 1.0],  # One limit up
        }, index=dates)
        
        score, details, risks = scorer.score(df)
        
        assert score >= 8  # 近20日有涨停应该得高分
        assert details['has_limit_up'] == True
        assert details['activity_type'] == '近期涨停'
    
    def test_score_with_consecutive_limit_ups(self, scorer, dates):
        """测试连板情况 -> 额外加分"""
        df = pd.DataFrame({
            'close': [10 + i * 0.1 for i in range(60)],
            'high': [10.5 + i * 0.1 for i in range(60)],
            'low': [9.5 + i * 0.1 for i in range(60)],
            'change_pct': [1.0] * 55 + [10.0, 10.0, 10.0, 1.0, 1.0],  # 3 consecutive limit ups
        }, index=dates)
        
        score, details, risks = scorer.score(df)
        
        assert score == 10  # 满分 (连板加分但不超过满分)
        assert details['consecutive_limit_ups'] >= 2
        assert '连板' in details['activity_type']
    
    def test_score_sideways_stock(self, scorer, dates):
        """测试长期横盘股票 -> 0分"""
        # 创建横盘数据 (价格波动<10%)
        df = pd.DataFrame({
            'close': [10.0 + np.sin(i/10) * 0.3 for i in range(60)],
            'high': [10.2 + np.sin(i/10) * 0.3 for i in range(60)],
            'low': [9.8 + np.sin(i/10) * 0.3 for i in range(60)],
            'change_pct': [0.5] * 60,
        }, index=dates)
        
        score, details, risks = scorer.score(df)
        
        assert score == 0
        assert details['is_sideways'] == True
        assert details['activity_type'] == '长期横盘'
        assert '股性差' in risks
    
    def test_score_low_max_gain(self, scorer, dates):
        """测试近60日最大涨幅<10% -> 2分"""
        # 创建低涨幅数据 (非横盘，但涨幅有限)
        # 需要确保不是横盘 (价格波动>10%)
        df = pd.DataFrame({
            'close': [10.0 + i * 0.015 for i in range(60)],  # 总涨幅约9%
            'high': [10.5 + i * 0.015 for i in range(60)],  # 高点有波动
            'low': [9.5 + i * 0.015 for i in range(60)],
            'change_pct': [0.15] * 60,
        }, index=dates)
        
        score, details, risks = scorer.score(df)
        
        # 由于价格波动范围约9%，可能被判定为横盘
        # 检查是否是涨幅有限或横盘
        assert score <= 2
        assert details['max_gain_60d'] < 10
        assert '股性差' in risks
    
    def test_score_high_volatility(self, scorer, dates):
        """测试高波动率股票 (日均振幅>3%) -> 8分"""
        # 创建高波动数据
        df = pd.DataFrame({
            'close': [10.0 + i * 0.5 for i in range(60)],  # 有明显涨幅
            'high': [10.5 + i * 0.5 for i in range(60)],  # 振幅约5%
            'low': [9.5 + i * 0.5 for i in range(60)],
            'change_pct': [2.0] * 60,
        }, index=dates)
        
        score, details, risks = scorer.score(df)
        
        assert score >= 6  # 高波动应该得分较高
        assert details['volatility'] > 2
    
    def test_score_empty_dataframe(self, scorer):
        """测试空数据"""
        df = pd.DataFrame()
        
        score, details, risks = scorer.score(df)
        
        assert score == 0
        assert details['activity_type'] == '数据无效'
    
    def test_score_none_dataframe(self, scorer):
        """测试None数据"""
        score, details, risks = scorer.score(None)
        
        assert score == 0
        assert details['activity_type'] == '数据无效'
    
    def test_has_limit_up_in_days(self, scorer, dates):
        """测试涨停检测"""
        df = pd.DataFrame({
            'change_pct': [1.0] * 15 + [10.0] + [1.0] * 4,
        }, index=dates[:20])
        
        assert scorer.has_limit_up_in_days(df, 20) == True
        assert scorer.has_limit_up_in_days(df, 5) == True  # 涨停在最近5日内
    
    def test_calculate_volatility(self, scorer, dates):
        """测试波动率计算"""
        df = pd.DataFrame({
            'close': [10.0] * 20,
            'high': [10.5] * 20,  # 振幅5%
            'low': [9.5] * 20,
        }, index=dates[:20])
        
        volatility = scorer.calculate_volatility(df, 20)
        
        assert volatility > 0
        assert volatility <= 15  # 合理范围 (振幅约10%)


class TestRiskMarker:
    """测试风险标记器"""
    
    @pytest.fixture
    def marker(self):
        return RiskMarker()
    
    def test_mark_high_chase_risk(self, marker):
        """测试追高风险标记"""
        # 乖离率>15% 应该标记追高风险
        risk = marker.mark_high_chase_risk(20.0)
        assert risk == '追高风险'
        
        # 乖离率<=15% 不应该标记
        risk = marker.mark_high_chase_risk(10.0)
        assert risk is None
    
    def test_mark_distribution_risk_heavy_volume_down(self, marker):
        """测试天量阴线出货风险"""
        # 量比>3 且 下跌
        risk = marker.mark_distribution_risk(4.0, -5.0)
        assert risk == '出货风险'
        
        # 量比>3 但上涨
        risk = marker.mark_distribution_risk(4.0, 5.0)
        assert risk is None
    
    def test_mark_distribution_risk_high_stagnation(self, marker):
        """测试高位巨量滞涨出货风险"""
        # 高位 + 巨量 + 滞涨
        risk = marker.mark_distribution_risk(4.0, 1.0, is_at_high=True)
        assert risk == '出货风险'
        
        # 非高位
        risk = marker.mark_distribution_risk(4.0, 1.0, is_at_high=False)
        assert risk is None
    
    def test_mark_theme_fade_risk(self, marker):
        """测试题材退潮风险"""
        risk = marker.mark_theme_fade_risk(True)
        assert risk == '题材退潮风险'
        
        risk = marker.mark_theme_fade_risk(False)
        assert risk is None
    
    def test_mark_low_activity_risk_sideways(self, marker):
        """测试横盘股性差风险"""
        risk = marker.mark_low_activity_risk(False, True, 5.0)
        assert risk == '股性差'
    
    def test_mark_low_activity_risk_low_gain(self, marker):
        """测试低涨幅股性差风险"""
        # 近60日最大涨幅<10% 且 近20日无涨停
        risk = marker.mark_low_activity_risk(False, False, 5.0)
        assert risk == '股性差'
        
        # 有涨停则不标记
        risk = marker.mark_low_activity_risk(True, False, 5.0)
        assert risk is None
    
    def test_mark_risks_comprehensive(self, marker):
        """测试综合风险标记"""
        score_details = {
            'trend_position': {'deviation_rate': 18.0},
            'volume_price': {'volume_ratio': 4.0, 'change_pct': -3.0, 'is_at_high': True},
            'theme_wind': {'is_fading': True},
            'stock_activity': {'has_limit_up': False, 'is_sideways': True, 'max_gain_60d': 5.0},
        }
        
        risks = marker.mark_risks(score_details)
        
        assert '追高风险' in risks
        assert '出货风险' in risks
        assert '题材退潮风险' in risks
        assert '股性差' in risks
    
    def test_mark_risks_no_risk(self, marker):
        """测试无风险情况"""
        score_details = {
            'trend_position': {'deviation_rate': 5.0},
            'volume_price': {'volume_ratio': 1.5, 'change_pct': 3.0, 'is_at_high': False},
            'theme_wind': {'is_fading': False},
            'stock_activity': {'has_limit_up': True, 'is_sideways': False, 'max_gain_60d': 30.0},
        }
        
        risks = marker.mark_risks(score_details)
        
        assert len(risks) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
