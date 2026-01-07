"""
Tests for ScoreLogger in scorer_v6.py

Validates Requirements 7.5: THE Scorer SHALL 记录评分日志用于回测分析
"""
import os
import json
import tempfile
import pytest
import pandas as pd
from datetime import datetime

from core.overnight_picker.scorer_v6 import ScoreLogger, ScorerV6


class TestScoreLogger:
    """Tests for ScoreLogger functionality"""
    
    def setup_method(self):
        """Setup test fixtures with temporary directory"""
        self.temp_dir = tempfile.mkdtemp()
        self.logger = ScoreLogger(log_dir=self.temp_dir)
    
    def teardown_method(self):
        """Cleanup temporary files"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_log_score_basic(self):
        """Test basic score logging"""
        details = {
            'trend_position': {'score': 16, 'trend_type': '多头排列'},
            'kline_pattern': {'score': 12, 'pattern': '阳线'},
            'volume_price': {'score': 10, 'volume_type': '温和放量'},
            'capital_strength': {'score': 8, 'inflow_ratio': 5.0},
            'theme_wind': {'score': 15, 'topic_type': '主线题材', 'matched_topics': ['AI']},
            'stock_activity': {'score': 8, 'activity_type': '高波动', 'has_limit_up': True, 'volatility': 3.5},
            'risks': ['追高风险'],
        }
        
        self.logger.log_score(
            stock_code='000001',
            stock_name='平安银行',
            total_score=69,
            details=details,
            trade_date='2026-01-06'
        )
        
        records = self.logger.get_records()
        assert len(records) == 1
        assert records[0]['stock_code'] == '000001'
        assert records[0]['stock_name'] == '平安银行'
        assert records[0]['total_score'] == 69
        assert records[0]['trade_date'] == '2026-01-06'
    
    def test_log_batch_scores(self):
        """Test batch score logging"""
        scores = [
            ('000001', '平安银行', 75, {'trend_position': {'score': 16}, 'kline_pattern': {'score': 12}, 
             'volume_price': {'score': 10}, 'capital_strength': {'score': 8}, 
             'theme_wind': {'score': 20, 'matched_topics': []}, 'stock_activity': {'score': 9, 'has_limit_up': True, 'volatility': 3.0}, 'risks': []}),
            ('000002', '万科A', 68, {'trend_position': {'score': 14}, 'kline_pattern': {'score': 10}, 
             'volume_price': {'score': 8}, 'capital_strength': {'score': 6}, 
             'theme_wind': {'score': 18, 'matched_topics': []}, 'stock_activity': {'score': 12, 'has_limit_up': False, 'volatility': 2.5}, 'risks': []}),
        ]
        
        self.logger.log_batch_scores(scores, trade_date='2026-01-06')
        
        records = self.logger.get_records()
        assert len(records) == 2
        assert records[0]['stock_code'] == '000001'
        assert records[1]['stock_code'] == '000002'
    
    def test_save_to_csv(self):
        """Test saving records to CSV"""
        self.logger.log_score('000001', '平安银行', 75, 
                              {'trend_position': {'score': 16}, 'kline_pattern': {'score': 12},
                               'volume_price': {'score': 10}, 'capital_strength': {'score': 8},
                               'theme_wind': {'score': 20, 'matched_topics': []}, 
                               'stock_activity': {'score': 9, 'has_limit_up': True, 'volatility': 3.0}, 'risks': []})
        
        filepath = self.logger.save_to_csv('test_log.csv')
        
        assert os.path.exists(filepath)
        df = pd.read_csv(filepath, encoding='utf-8-sig', dtype={'stock_code': str})
        assert len(df) == 1
        assert str(df.iloc[0]['stock_code']).zfill(6) == '000001'
    
    def test_save_to_json(self):
        """Test saving records to JSON"""
        self.logger.log_score('000001', '平安银行', 75,
                              {'trend_position': {'score': 16}, 'kline_pattern': {'score': 12},
                               'volume_price': {'score': 10}, 'capital_strength': {'score': 8},
                               'theme_wind': {'score': 20, 'matched_topics': []},
                               'stock_activity': {'score': 9, 'has_limit_up': True, 'volatility': 3.0}, 'risks': []})
        
        filepath = self.logger.save_to_json('test_log.json')
        
        assert os.path.exists(filepath)
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        assert len(data) == 1
        assert data[0]['stock_code'] == '000001'
    
    def test_append_to_daily_log(self):
        """Test appending to daily log file"""
        self.logger.log_score('000001', '平安银行', 75,
                              {'trend_position': {'score': 16}, 'kline_pattern': {'score': 12},
                               'volume_price': {'score': 10}, 'capital_strength': {'score': 8},
                               'theme_wind': {'score': 20, 'matched_topics': []},
                               'stock_activity': {'score': 9, 'has_limit_up': True, 'volatility': 3.0}, 'risks': []})
        
        filepath = self.logger.append_to_daily_log('2026-01-06')
        
        assert os.path.exists(filepath)
        assert 'score_log_20260106.csv' in filepath
    
    def test_get_records_df(self):
        """Test getting records as DataFrame"""
        self.logger.log_score('000001', '平安银行', 75,
                              {'trend_position': {'score': 16}, 'kline_pattern': {'score': 12},
                               'volume_price': {'score': 10}, 'capital_strength': {'score': 8},
                               'theme_wind': {'score': 20, 'matched_topics': []},
                               'stock_activity': {'score': 9, 'has_limit_up': True, 'volatility': 3.0}, 'risks': []})
        
        df = self.logger.get_records_df()
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert 'total_score' in df.columns
    
    def test_clear_records(self):
        """Test clearing records"""
        self.logger.log_score('000001', '平安银行', 75,
                              {'trend_position': {'score': 16}, 'kline_pattern': {'score': 12},
                               'volume_price': {'score': 10}, 'capital_strength': {'score': 8},
                               'theme_wind': {'score': 20, 'matched_topics': []},
                               'stock_activity': {'score': 9, 'has_limit_up': True, 'volatility': 3.0}, 'risks': []})
        
        assert len(self.logger.get_records()) == 1
        
        self.logger.clear_records()
        
        assert len(self.logger.get_records()) == 0
    
    def test_analyze_score_distribution(self):
        """Test score distribution analysis"""
        # Add multiple records with different scores
        for i, score in enumerate([85, 78, 72, 65, 55]):
            self.logger.log_score(f'00000{i}', f'Stock{i}', score,
                                  {'trend_position': {'score': 16}, 'kline_pattern': {'score': 12},
                                   'volume_price': {'score': 10}, 'capital_strength': {'score': 8},
                                   'theme_wind': {'score': 20, 'matched_topics': []},
                                   'stock_activity': {'score': 9, 'has_limit_up': True, 'volatility': 3.0}, 
                                   'risks': ['追高风险'] if score > 80 else []})
        
        analysis = self.logger.analyze_score_distribution()
        
        assert analysis['total_records'] == 5
        assert 'score_stats' in analysis
        assert 'score_distribution' in analysis
        assert analysis['score_distribution']['80-100'] == 1
        assert analysis['score_distribution']['70-79'] == 2
    
    def test_get_high_score_stocks(self):
        """Test getting high score stocks"""
        for i, score in enumerate([85, 78, 72, 65, 55]):
            self.logger.log_score(f'00000{i}', f'Stock{i}', score,
                                  {'trend_position': {'score': 16}, 'kline_pattern': {'score': 12},
                                   'volume_price': {'score': 10}, 'capital_strength': {'score': 8},
                                   'theme_wind': {'score': 20, 'matched_topics': []},
                                   'stock_activity': {'score': 9, 'has_limit_up': True, 'volatility': 3.0}, 'risks': []})
        
        high_scores = self.logger.get_high_score_stocks(min_score=75)
        
        assert len(high_scores) == 2
        assert high_scores.iloc[0]['total_score'] == 85
    
    def test_get_risky_stocks(self):
        """Test getting risky stocks"""
        self.logger.log_score('000001', 'Stock1', 75,
                              {'trend_position': {'score': 16}, 'kline_pattern': {'score': 12},
                               'volume_price': {'score': 10}, 'capital_strength': {'score': 8},
                               'theme_wind': {'score': 20, 'matched_topics': []},
                               'stock_activity': {'score': 9, 'has_limit_up': True, 'volatility': 3.0}, 
                               'risks': ['追高风险', '出货风险']})
        self.logger.log_score('000002', 'Stock2', 70,
                              {'trend_position': {'score': 16}, 'kline_pattern': {'score': 12},
                               'volume_price': {'score': 10}, 'capital_strength': {'score': 8},
                               'theme_wind': {'score': 20, 'matched_topics': []},
                               'stock_activity': {'score': 9, 'has_limit_up': True, 'volatility': 3.0}, 'risks': []})
        
        risky = self.logger.get_risky_stocks()
        
        assert len(risky) == 1
        assert risky.iloc[0]['stock_code'] == '000001'
    
    def test_load_log_file_csv(self):
        """Test loading CSV log file"""
        self.logger.log_score('000001', '平安银行', 75,
                              {'trend_position': {'score': 16}, 'kline_pattern': {'score': 12},
                               'volume_price': {'score': 10}, 'capital_strength': {'score': 8},
                               'theme_wind': {'score': 20, 'matched_topics': []},
                               'stock_activity': {'score': 9, 'has_limit_up': True, 'volatility': 3.0}, 'risks': []})
        filepath = self.logger.save_to_csv('test_load.csv')
        
        loaded_df = self.logger.load_log_file(filepath)
        
        assert len(loaded_df) == 1
        # stock_code may be loaded as int, so convert to string and pad with zeros
        assert str(loaded_df.iloc[0]['stock_code']).zfill(6) == '000001'
    
    def test_load_log_file_json(self):
        """Test loading JSON log file"""
        self.logger.log_score('000001', '平安银行', 75,
                              {'trend_position': {'score': 16}, 'kline_pattern': {'score': 12},
                               'volume_price': {'score': 10}, 'capital_strength': {'score': 8},
                               'theme_wind': {'score': 20, 'matched_topics': []},
                               'stock_activity': {'score': 9, 'has_limit_up': True, 'volatility': 3.0}, 'risks': []})
        filepath = self.logger.save_to_json('test_load.json')
        
        loaded_df = self.logger.load_log_file(filepath)
        
        assert len(loaded_df) == 1
        assert loaded_df.iloc[0]['stock_code'] == '000001'
    
    def test_get_log_files(self):
        """Test getting list of log files"""
        self.logger.log_score('000001', '平安银行', 75,
                              {'trend_position': {'score': 16}, 'kline_pattern': {'score': 12},
                               'volume_price': {'score': 10}, 'capital_strength': {'score': 8},
                               'theme_wind': {'score': 20, 'matched_topics': []},
                               'stock_activity': {'score': 9, 'has_limit_up': True, 'volatility': 3.0}, 'risks': []})
        self.logger.save_to_csv('score_log_test1.csv')
        self.logger.save_to_json('score_log_test2.json')
        
        log_files = self.logger.get_log_files()
        
        assert len(log_files) == 2
        assert all('filename' in f for f in log_files)
        assert all('path' in f for f in log_files)


class TestScorerV6LoggingIntegration:
    """Integration tests for ScorerV6 with logging"""
    
    def setup_method(self):
        """Setup test fixtures with temporary directory"""
        self.temp_dir = tempfile.mkdtemp()
        self.scorer = ScorerV6(enable_logging=True, log_dir=self.temp_dir)
    
    def teardown_method(self):
        """Cleanup temporary files"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_scorer_with_logging_enabled(self):
        """Test that scorer logs scores when enabled"""
        stock_data = {
            'code': '000001',
            'name': '平安银行',
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
            'trade_date': '2026-01-06',
        }
        
        total_score, details = self.scorer.score_stock(stock_data, log_score=True)
        
        # Check that score was logged
        records = self.scorer.score_logger.get_records()
        assert len(records) == 1
        assert records[0]['stock_code'] == '000001'
        assert records[0]['total_score'] == total_score
    
    def test_scorer_with_logging_disabled(self):
        """Test that scorer doesn't log when disabled"""
        scorer = ScorerV6(enable_logging=False)
        
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
        
        total_score, details = scorer.score_stock(stock_data)
        
        # Check that no logger exists
        assert scorer.score_logger is None
    
    def test_scorer_log_score_false(self):
        """Test that scorer doesn't log when log_score=False"""
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
        
        total_score, details = self.scorer.score_stock(stock_data, log_score=False)
        
        # Check that no records were logged
        records = self.scorer.score_logger.get_records()
        assert len(records) == 0
    
    def test_save_logs_after_scoring(self):
        """Test saving logs after multiple scorings"""
        stock_data_list = [
            {'code': '000001', 'name': '平安银行', 'close': 15.0, 'open': 14.5, 'high': 15.2, 'low': 14.3,
             'prev_close': 14.0, 'ma5': 14.2, 'ma10': 14.0, 'ma20': 13.8, 'ma60': 13.5,
             'price_percentile': 40, 'volume': 1500000, 'ma5_vol': 1000000, 'change_pct': 7.14, 'turnover_rate': 6.0},
            {'code': '000002', 'name': '万科A', 'close': 10.0, 'open': 9.8, 'high': 10.2, 'low': 9.7,
             'prev_close': 9.5, 'ma5': 9.6, 'ma10': 9.4, 'ma20': 9.2, 'ma60': 9.0,
             'price_percentile': 50, 'volume': 2000000, 'ma5_vol': 1500000, 'change_pct': 5.26, 'turnover_rate': 8.0},
        ]
        
        for stock_data in stock_data_list:
            self.scorer.score_stock(stock_data, log_score=True)
        
        # Save to CSV
        filepath = self.scorer.score_logger.save_to_csv('test_scores.csv')
        
        assert os.path.exists(filepath)
        df = pd.read_csv(filepath, encoding='utf-8-sig')
        assert len(df) == 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
