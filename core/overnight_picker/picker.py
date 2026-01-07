"""
隔夜选股器主类 (OvernightStockPicker)

T日选股，T+1执行的隔夜短线选股系统。
每天收盘后(15:00后)运行，基于当日完整日线数据，
筛选出明天可以买入的股票，并给出具体的买入价格、仓位和止损止盈建议。

整合所有模块:
- TomorrowPotentialScorer: 明日潜力评分器
- EntryPriceCalculator: 买入价计算器
- PositionAdvisor: 仓位顾问
- StopLossCalculator/TakeProfitCalculator: 止损止盈计算器
- SmartTopicMatcher: 智能题材匹配器
- CallAuctionFilter: 竞价过滤器
- SentimentCyclePredictor: 情绪周期预判器
- PreMarketAdjuster: 早盘修正器
- TradingPlanGenerator: 交易计划生成器

Requirements: 1.1-1.6
"""

import os
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
import pandas as pd

from .models import StockRecommendation, TradingPlan
from .scorer import TomorrowPotentialScorer
from .scorer_v6 import ScorerV6
from .calculator import (
    EntryPriceCalculator,
    PositionAdvisor,
    StopLossCalculator,
    TakeProfitCalculator,
    SmartStopLoss,
)
from .topic_matcher import SmartTopicMatcher, get_smart_topic_matcher
from .call_auction_filter import CallAuctionFilter, StrategyType
from .sentiment_predictor import (
    SentimentCyclePredictor,
    SentimentPhase,
    SentimentLevel,
)
from .plan_generator import TradingPlanGenerator

logger = logging.getLogger(__name__)


class MarketEnvironment:
    """大盘环境分析结果"""
    STRONG = "强势"
    NEUTRAL = "震荡"
    WEAK = "弱势"
    EXTREME_WEAK = "极弱"


class OvernightStockPicker:
    """
    隔夜选股器主类
    
    核心功能:
    1. 获取收盘数据并计算技术指标
    2. 判断大盘环境和市场情绪
    3. 对股票池进行评分和筛选
    4. 计算买入价、仓位、止损止盈
    5. 生成完整的交易计划
    
    使用流程:
    ```python
    picker = OvernightStockPicker(total_capital=70000)
    plan = picker.run()
    print(plan.to_markdown())
    ```
    """
    
    # 默认配置
    DEFAULT_TOTAL_CAPITAL = 70000       # 默认总资金7万
    DEFAULT_MAX_RECOMMENDATIONS = 15    # 最多推荐15只
    DEFAULT_MIN_SCORE = 70              # 最低评分阈值
    DEFAULT_DATA_PATH = "data/processed"  # 数据路径
    
    def __init__(self,
                 total_capital: float = DEFAULT_TOTAL_CAPITAL,
                 max_recommendations: int = DEFAULT_MAX_RECOMMENDATIONS,
                 min_score: float = DEFAULT_MIN_SCORE,
                 data_path: str = DEFAULT_DATA_PATH,
                 stock_pool: List[str] = None,
                 scorer_version: str = "v6"):
        """
        初始化隔夜选股器
        
        Args:
            total_capital: 总资金 (默认7万)
            max_recommendations: 最多推荐股票数 (默认15只)
            min_score: 最低评分阈值 (默认70分)
            data_path: 数据文件路径
            stock_pool: 股票池列表，如果为None则从配置加载
            scorer_version: 评分器版本 ("v5" 或 "v6")，默认使用v6
        """
        self.total_capital = total_capital
        self.max_recommendations = max_recommendations
        self.min_score = min_score
        self.data_path = data_path
        self.scorer_version = scorer_version
        
        # 初始化股票池
        self.stock_pool = stock_pool or self._load_stock_pool()
        
        # 初始化评分器 (支持版本切换)
        if scorer_version == "v6":
            self.scorer = ScorerV6()
            logger.info("使用评分系统 v6.0 (6维度100分体系)")
        else:
            self.scorer = TomorrowPotentialScorer(total_capital=total_capital)
            logger.info("使用评分系统 v5.0 (传统评分体系)")
        
        # 初始化其他模块
        self.entry_calculator = EntryPriceCalculator()
        self.position_advisor = PositionAdvisor(total_capital=total_capital, min_score_threshold=min_score)
        self.stop_loss_calculator = StopLossCalculator()
        self.take_profit_calculator = TakeProfitCalculator()
        self.smart_stop_loss = SmartStopLoss()
        self.topic_matcher = get_smart_topic_matcher()
        self.auction_filter = CallAuctionFilter()
        self.sentiment_predictor = SentimentCyclePredictor()
        self.plan_generator = TradingPlanGenerator(total_capital=total_capital)
        
        # 缓存数据
        self._stock_data_cache: Dict[str, pd.DataFrame] = {}
        self._market_data: Optional[Dict] = None
        
        logger.info(f"隔夜选股器初始化完成: 资金={total_capital}, 股票池={len(self.stock_pool)}只, 评分器={scorer_version}")
    
    def _load_stock_pool(self) -> List[str]:
        """
        加载股票池
        
        优先从配置文件加载，如果不存在则从数据目录获取
        """
        try:
            from config.stock_pool import STOCK_POOL
            logger.info(f"从配置加载股票池: {len(STOCK_POOL)}只")
            return STOCK_POOL
        except ImportError:
            pass
        
        # 从数据目录获取
        if os.path.exists(self.data_path):
            codes = []
            for f in os.listdir(self.data_path):
                if f.endswith('.csv'):
                    code = f.replace('.csv', '')
                    codes.append(code)
            logger.info(f"从数据目录加载股票池: {len(codes)}只")
            return codes
        
        logger.warning("未找到股票池配置")
        return []
    
    def refresh_stock_data(self, codes: List[str] = None, days: int = 365) -> Dict[str, bool]:
        """
        刷新股票数据
        
        使用DataFeed模块下载最新数据
        
        Args:
            codes: 要刷新的股票代码列表，默认刷新整个股票池
            days: 下载天数
        
        Returns:
            {code: success} 刷新结果
        """
        try:
            from core.data_feed import DataFeed
            
            data_feed = DataFeed(
                raw_path="data/raw",
                processed_path=self.data_path
            )
            
            codes = codes or self.stock_pool
            results = {}
            
            logger.info(f"开始刷新数据: {len(codes)}只股票")
            
            for i, code in enumerate(codes):
                if (i + 1) % 10 == 0:
                    logger.info(f"刷新进度: {i+1}/{len(codes)}")
                
                success = data_feed.overwrite_update(code, days=days)
                results[code] = success
                
                # 清除缓存
                if code in self._stock_data_cache:
                    del self._stock_data_cache[code]
            
            success_count = sum(1 for v in results.values() if v)
            logger.info(f"数据刷新完成: 成功{success_count}/{len(codes)}")
            
            return results
        except ImportError:
            logger.error("DataFeed模块不可用，无法刷新数据")
            return {}
        except Exception as e:
            logger.error(f"刷新数据失败: {e}")
            return {}

    def load_stock_data(self, code: str) -> Optional[pd.DataFrame]:
        """
        加载单只股票数据
        
        Args:
            code: 股票代码
        
        Returns:
            DataFrame 或 None
        """
        # 检查缓存
        if code in self._stock_data_cache:
            return self._stock_data_cache[code]
        
        file_path = os.path.join(self.data_path, f"{code}.csv")
        
        if not os.path.exists(file_path):
            logger.warning(f"数据文件不存在: {file_path}")
            return None
        
        try:
            df = pd.read_csv(file_path)
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').reset_index(drop=True)
            
            # 缓存数据
            self._stock_data_cache[code] = df
            return df
        except Exception as e:
            logger.error(f"加载数据失败: {code}, 错误: {e}")
            return None
    
    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算技术指标
        
        计算均线、成交量均线、MACD等指标
        
        Args:
            df: 原始OHLCV数据
        
        Returns:
            添加技术指标后的DataFrame
        """
        if df is None or df.empty:
            return df
        
        df = df.copy()
        
        # 均线
        df['ma5'] = df['close'].rolling(window=5).mean()
        df['ma10'] = df['close'].rolling(window=10).mean()
        df['ma20'] = df['close'].rolling(window=20).mean()
        df['ma60'] = df['close'].rolling(window=60).mean()
        
        # 成交量均线
        df['ma5_vol'] = df['volume'].rolling(window=5).mean()
        df['ma10_vol'] = df['volume'].rolling(window=10).mean()
        
        # 涨跌幅
        df['change_pct'] = df['close'].pct_change()
        
        # 波动率 (5日振幅平均)
        df['amplitude'] = (df['high'] - df['low']) / df['close'].shift(1)
        df['volatility'] = df['amplitude'].rolling(window=5).mean()
        
        # MACD
        df['ema12'] = df['close'].ewm(span=12, adjust=False).mean()
        df['ema26'] = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = df['ema12'] - df['ema26']
        df['signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['signal']
        
        # MACD金叉判断
        df['macd_golden'] = (df['macd'] > df['signal']) & (df['macd'].shift(1) <= df['signal'].shift(1))
        
        # 均线金叉判断 (MA5上穿MA10)
        df['ma_golden'] = (df['ma5'] > df['ma10']) & (df['ma5'].shift(1) <= df['ma10'].shift(1))
        
        # 突破前高判断 (收盘价创20日新高)
        df['high_20'] = df['high'].rolling(window=20).max()
        df['breakout'] = df['close'] > df['high_20'].shift(1)
        
        return df
    
    def get_latest_data(self, df: pd.DataFrame) -> Optional[Dict]:
        """
        获取最新一天的数据
        
        Args:
            df: 带技术指标的DataFrame
        
        Returns:
            最新数据字典
        """
        if df is None or df.empty:
            return None
        
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        
        return {
            'date': latest['date'],
            'open': latest['open'],
            'high': latest['high'],
            'low': latest['low'],
            'close': latest['close'],
            'volume': latest['volume'],
            'prev_close': prev['close'],
            'prev_low': prev['low'],
            'ma5': latest.get('ma5', 0),
            'ma10': latest.get('ma10', 0),
            'ma20': latest.get('ma20', 0),
            'ma60': latest.get('ma60', 0),
            'ma5_vol': latest.get('ma5_vol', 1),
            'ma10_vol': latest.get('ma10_vol', 1),
            'volatility': latest.get('volatility', 0.05),
            'has_macd_golden': bool(latest.get('macd_golden', False)),
            'has_ma_golden': bool(latest.get('ma_golden', False)),
            'has_breakout': bool(latest.get('breakout', False)),
        }
    
    def get_data_status(self) -> Dict[str, Dict]:
        """
        获取数据状态
        
        检查股票池中每只股票的数据状态
        
        Returns:
            {code: {exists, last_date, record_count}}
        """
        status = {}
        
        for code in self.stock_pool:
            file_path = os.path.join(self.data_path, f"{code}.csv")
            
            if os.path.exists(file_path):
                try:
                    df = pd.read_csv(file_path)
                    last_date = df['date'].max() if 'date' in df.columns else 'N/A'
                    status[code] = {
                        'exists': True,
                        'last_date': str(last_date),
                        'record_count': len(df),
                    }
                except Exception:
                    status[code] = {
                        'exists': True,
                        'last_date': 'Error',
                        'record_count': 0,
                    }
            else:
                status[code] = {
                    'exists': False,
                    'last_date': None,
                    'record_count': 0,
                }
        
        return status
    
    def check_data_freshness(self, max_days: int = 3) -> Tuple[List[str], List[str]]:
        """
        检查数据新鲜度
        
        Args:
            max_days: 最大允许的数据延迟天数
        
        Returns:
            (fresh_codes, stale_codes) 新鲜和过期的股票代码列表
        """
        fresh = []
        stale = []
        
        today = date.today()
        cutoff = today - timedelta(days=max_days)
        
        for code in self.stock_pool:
            df = self.load_stock_data(code)
            if df is None or df.empty:
                stale.append(code)
                continue
            
            last_date = pd.to_datetime(df['date'].max()).date()
            if last_date >= cutoff:
                fresh.append(code)
            else:
                stale.append(code)
        
        return fresh, stale
    
    def preload_all_data(self) -> int:
        """
        预加载所有股票数据到缓存
        
        Returns:
            成功加载的股票数量
        """
        success_count = 0
        
        logger.info(f"预加载数据: {len(self.stock_pool)}只股票")
        
        for code in self.stock_pool:
            df = self.load_stock_data(code)
            if df is not None and not df.empty:
                success_count += 1
        
        logger.info(f"预加载完成: {success_count}/{len(self.stock_pool)}")
        return success_count
    
    def analyze_market_environment(self, 
                                   index_data: pd.DataFrame = None) -> Dict:
        """
        分析大盘环境
        
        判断大盘是强势/震荡/弱势/极弱
        
        判断逻辑:
        - 强势: 站上MA20且MA5>MA10>MA20 (多头排列)
        - 震荡: 站上MA20或MA60
        - 弱势: 跌破MA20
        - 极弱: 空头排列 + 当日大跌>2%
        
        Args:
            index_data: 指数数据 (如上证指数)，如果为None则尝试加载
        
        Returns:
            大盘环境分析结果
        """
        # 尝试加载上证指数数据
        if index_data is None:
            index_data = self.load_stock_data('000001')
        
        if index_data is None or index_data.empty:
            logger.warning("无法获取指数数据，使用默认震荡环境")
            return {
                'env': MarketEnvironment.NEUTRAL,
                'description': '无法获取指数数据',
                'index_change': 0,
                'ma_status': '未知',
                'should_empty': False,
            }
        
        # 计算技术指标
        index_data = self.calculate_technical_indicators(index_data)
        latest = index_data.iloc[-1]
        
        # 获取最近数据
        close = latest['close']
        ma5 = latest.get('ma5', close)
        ma10 = latest.get('ma10', close)
        ma20 = latest.get('ma20', close)
        ma60 = latest.get('ma60', close)
        
        # 计算涨跌幅
        prev_close = index_data.iloc[-2]['close'] if len(index_data) > 1 else close
        index_change = (close - prev_close) / prev_close
        
        # 计算近5日涨跌幅
        if len(index_data) >= 5:
            close_5d_ago = index_data.iloc[-5]['close']
            change_5d = (close - close_5d_ago) / close_5d_ago
        else:
            change_5d = 0
        
        # 判断均线状态
        is_above_ma5 = close > ma5
        is_above_ma10 = close > ma10
        is_above_ma20 = close > ma20
        is_above_ma60 = close > ma60
        
        # 判断多头/空头排列
        is_bullish_alignment = ma5 > ma10 > ma20
        is_bearish_alignment = ma5 < ma10 < ma20
        
        # 判断大盘环境
        should_empty = False  # 是否建议空仓
        
        if is_above_ma5 and is_above_ma10 and is_above_ma20:
            if is_bullish_alignment:
                env = MarketEnvironment.STRONG
                ma_status = '多头排列'
            else:
                env = MarketEnvironment.STRONG
                ma_status = '站上MA20'
        elif is_above_ma20:
            env = MarketEnvironment.NEUTRAL
            ma_status = '震荡偏强'
        elif is_above_ma60:
            env = MarketEnvironment.NEUTRAL
            ma_status = '震荡'
        elif is_bearish_alignment:
            if index_change < -0.02 or change_5d < -0.05:
                env = MarketEnvironment.EXTREME_WEAK
                ma_status = '空头排列+大跌'
                should_empty = True
            else:
                env = MarketEnvironment.WEAK
                ma_status = '空头排列'
        else:
            if index_change < -0.03:
                env = MarketEnvironment.EXTREME_WEAK
                ma_status = '大幅下跌'
                should_empty = True
            else:
                env = MarketEnvironment.WEAK
                ma_status = '弱势'
        
        return {
            'env': env,
            'description': f'指数{index_change*100:+.2f}%，{ma_status}',
            'index_change': index_change,
            'change_5d': change_5d,
            'ma_status': ma_status,
            'close': close,
            'ma5': ma5,
            'ma10': ma10,
            'ma20': ma20,
            'ma60': ma60,
            'is_bullish_alignment': is_bullish_alignment,
            'is_bearish_alignment': is_bearish_alignment,
            'should_empty': should_empty,
        }
    
    def is_market_tradable(self, market_env: Dict = None) -> Tuple[bool, str]:
        """
        判断市场是否适合交易
        
        Args:
            market_env: 大盘环境分析结果，如果为None则重新分析
        
        Returns:
            (是否可交易, 原因)
        """
        if market_env is None:
            market_env = self.analyze_market_environment()
        
        env = market_env.get('env', MarketEnvironment.NEUTRAL)
        
        if env == MarketEnvironment.EXTREME_WEAK:
            return False, "大盘环境极差，建议空仓观望"
        
        if market_env.get('should_empty', False):
            return False, "市场风险较高，建议空仓"
        
        if market_env.get('index_change', 0) < -0.03:
            return False, "大盘大幅下跌，建议观望"
        
        return True, "市场环境正常"

    def analyze_market_sentiment(self,
                                 limit_up_count: int = 50,
                                 limit_down_count: int = 10,
                                 broken_board_rate: float = 0.15,
                                 continuous_board_count: int = 5,
                                 market_profit_rate: float = 0.5) -> Dict:
        """
        分析市场情绪
        
        使用情绪周期预判器分析今日情绪并预判明日
        
        Args:
            limit_up_count: 涨停家数
            limit_down_count: 跌停家数
            broken_board_rate: 炸板率
            continuous_board_count: 连板股数量
            market_profit_rate: 市场赚钱效应
        
        Returns:
            市场情绪分析结果
        """
        # 分析今日情绪
        today_sentiment = self.sentiment_predictor.analyze_today_sentiment(
            limit_up_count=limit_up_count,
            limit_down_count=limit_down_count,
            broken_board_rate=broken_board_rate,
            continuous_board_count=continuous_board_count,
            market_profit_rate=market_profit_rate,
        )
        
        # 预判明日情绪
        tomorrow_prediction = self.sentiment_predictor.predict_tomorrow(today_sentiment)
        
        # 转换情绪等级为中文
        sentiment_map = {
            SentimentLevel.EXTREME_GREED: '乐观',
            SentimentLevel.GREED: '乐观',
            SentimentLevel.NEUTRAL: '中性',
            SentimentLevel.FEAR: '恐慌',
            SentimentLevel.EXTREME_FEAR: '恐慌',
        }
        
        return {
            'sentiment': sentiment_map.get(today_sentiment.level, '中性'),
            'phase': today_sentiment.phase.value,
            'score': today_sentiment.score,
            'level': today_sentiment.level.value,
            'prediction': tomorrow_prediction.strategy_advice,
            'position_multiplier': tomorrow_prediction.position_multiplier,
            'focus_stocks': tomorrow_prediction.focus_stocks,
            'today_analysis': today_sentiment,
            'tomorrow_prediction': tomorrow_prediction,
        }
    
    def score_stock(self, 
                    code: str, 
                    name: str = '',
                    sector: str = '',
                    concepts: List[str] = None,
                    hot_topics: List[str] = None) -> Optional[Tuple[float, Dict]]:
        """
        对单只股票进行评分
        
        Args:
            code: 股票代码
            name: 股票名称
            sector: 所属板块
            concepts: 概念列表
            hot_topics: 当前热点列表
        
        Returns:
            (总分, 评分详情) 或 None
        """
        # 加载数据
        df = self.load_stock_data(code)
        if df is None or len(df) < 60:
            logger.warning(f"股票 {code} 数据不足")
            return None
        
        # 计算技术指标
        df = self.calculate_technical_indicators(df)
        
        # 获取最新数据
        latest = self.get_latest_data(df)
        if latest is None:
            return None
        
        # 根据评分器版本使用不同的评分逻辑
        if self.scorer_version == "v6":
            return self._score_stock_v6(code, name, sector, concepts, hot_topics, df, latest)
        else:
            return self._score_stock_v5(code, name, sector, concepts, hot_topics, df, latest)
    
    def _score_stock_v6(self, code: str, name: str, sector: str, 
                        concepts: List[str], hot_topics: List[str],
                        df: pd.DataFrame, latest: Dict) -> Optional[Tuple[float, Dict]]:
        """
        使用v6评分器进行评分
        """
        # 计算价格分位点 (近60日)
        recent_60d = df.tail(60) if len(df) >= 60 else df
        if len(recent_60d) > 1:
            price_percentile = (recent_60d['close'] <= latest['close']).mean() * 100
        else:
            price_percentile = 50
        
        # 计算换手率 (假设流通股本，实际应从外部数据获取)
        # 这里使用简化计算：成交量/平均成交量 * 5% 作为换手率估算
        avg_volume = df['volume'].tail(20).mean()
        turnover_rate = (latest['volume'] / avg_volume) * 5 if avg_volume > 0 else 5
        
        # 计算涨跌幅
        change_pct = (latest['close'] - latest['prev_close']) / latest['prev_close'] * 100
        
        # 构建v6评分器需要的数据格式
        stock_data = {
            'code': code,
            'name': name,
            'concepts': concepts or [],
            'open': latest['open'],
            'high': latest['high'],
            'low': latest['low'],
            'close': latest['close'],
            'prev_close': latest['prev_close'],
            'prev_open': latest.get('prev_open', latest['prev_close']),
            'prev_high': latest.get('prev_high', latest['high']),
            'prev_low': latest['prev_low'],
            'volume': latest['volume'],
            'ma5': latest['ma5'],
            'ma10': latest['ma10'],
            'ma20': latest['ma20'],
            'ma60': latest['ma60'],
            'ma5_vol': latest['ma5_vol'],
            'price_percentile': price_percentile,
            'change_pct': change_pct,
            'turnover_rate': turnover_rate,
            'turnover_amount': latest['volume'] * latest['close'],  # 成交额估算
            'main_net_inflow': 0,  # 需要外部数据，暂时设为0
            'is_breakout': latest.get('has_breakout', False),
            'is_sector_leader': False,  # 需要外部数据
            'kline_df': df,  # 传入完整K线数据用于股性活跃度计算
        }
        
        market_data = {
            'hot_topics': hot_topics or [],
            'sector_limit_up_count': 0,  # 需要外部数据
        }
        
        # 使用v6评分器评分
        total_score, details = self.scorer.score_stock(stock_data, market_data)
        
        return total_score, details
    
    def _score_stock_v5(self, code: str, name: str, sector: str,
                        concepts: List[str], hot_topics: List[str],
                        df: pd.DataFrame, latest: Dict) -> Optional[Tuple[float, Dict]]:
        """
        使用v5评分器进行评分 (保持原有逻辑)
        """
        # 构建v5评分器需要的数据格式
        stock_data = {
            'code': code,
            'name': name,
            'sector': sector,
            'concepts': concepts or [],
            'open': latest['open'],
            'high': latest['high'],
            'low': latest['low'],
            'close': latest['close'],
            'prev_close': latest['prev_close'],
            'volume': latest['volume'],
            'ma5': latest['ma5'],
            'ma10': latest['ma10'],
            'ma20': latest['ma20'],
            'ma60': latest['ma60'],
            'ma5_vol': latest['ma5_vol'],
            'ma10_vol': latest['ma10_vol'],
            'main_net_inflow': 0,  # 需要外部数据
            'sector_rank': 5,  # 默认值
            'sector_size': 20,
            'sector_market_rank': 10,
            'sector_change': 0,
            'has_breakout': latest['has_breakout'],
            'has_macd_golden': latest['has_macd_golden'],
            'has_ma_golden': latest['has_ma_golden'],
            'df': df,
        }
        
        market_data = {
            'hot_topics': hot_topics or [],
        }
        
        # 使用v5评分器评分
        total_score, details = self.scorer.score_stock(stock_data, market_data)
        
        return total_score, details
    
    def create_recommendation(self,
                              code: str,
                              name: str,
                              sector: str,
                              total_score: float,
                              score_details: Dict,
                              market_env: str,
                              sentiment: str,
                              hot_topics: List[str] = None) -> Optional[StockRecommendation]:
        """
        创建股票推荐
        
        计算买入价、仓位、止损止盈等完整信息
        
        Args:
            code: 股票代码
            name: 股票名称
            sector: 所属板块
            total_score: 总评分
            score_details: 评分详情
            market_env: 大盘环境
            sentiment: 市场情绪
            hot_topics: 相关热点
        
        Returns:
            StockRecommendation 或 None
        """
        # 加载数据
        df = self.load_stock_data(code)
        if df is None:
            return None
        
        df = self.calculate_technical_indicators(df)
        latest = self.get_latest_data(df)
        if latest is None:
            return None
        
        today_close = latest['close']
        prev_close = latest['prev_close']
        today_change = (today_close - prev_close) / prev_close * 100
        volatility = latest.get('volatility', 0.05)
        
        # 计算买入价
        entry_prices = self.entry_calculator.calculate_entry_prices(
            today_close=today_close,
            today_high=latest['high'],
            today_low=latest['low'],
            score=total_score,
            volatility=volatility,
        )
        
        # 计算仓位
        position = self.position_advisor.calculate_position(
            score=total_score,
            stock_price=entry_prices['ideal_price'],
            market_env=market_env,
            sentiment=sentiment,
        )
        
        # 如果仓位为0，不推荐
        if position['shares'] == 0:
            return None
        
        # 计算智能止损
        smart_stop = self.smart_stop_loss.calculate_smart_stop(
            entry_price=entry_prices['ideal_price'],
            prev_low=latest['prev_low'],
            ma5=latest['ma5'],
            ma10=latest['ma10'],
            volatility=volatility,
        )
        
        # 计算止盈
        take_profit = self.take_profit_calculator.calculate_take_profit(
            entry_price=entry_prices['ideal_price'],
            position_amount=position['position_amount'],
            score=total_score,
        )
        
        # 确定策略类型 - 根据评分器版本使用不同的数据格式
        if self.scorer_version == "v6":
            # v6格式: 从新的数据结构中提取信息
            trend_details = score_details.get('trend_position', {})
            kline_details = score_details.get('kline_pattern', {})
            
            ma_position = trend_details.get('trend_type', '')
            pattern = kline_details.get('pattern', '')
            # v6没有leader_index，使用题材风口分数作为替代
            theme_score = score_details.get('theme_wind', {}).get('score', 0)
            leader_index = theme_score * 100 / 25  # 转换为百分比
        else:
            # v5格式: 使用原有的数据结构
            ma_position = score_details.get('ma_position', {}).get('ma_type', '')
            pattern = score_details.get('closing_pattern', {}).get('pattern', '')
            leader_index = score_details.get('leader_index', {}).get('score', 0) * 100 / 12
        
        strategy_type = self.auction_filter.determine_strategy_type(
            leader_index=leader_index,
            ma_position=ma_position,
            pattern=pattern,
        )
        
        # 确定龙头类型 - 根据评分器版本使用不同的数据格式
        if self.scorer_version == "v6":
            # v6格式: 从题材风口评分中判断
            theme_details = score_details.get('theme_wind', {})
            if theme_details.get('is_sector_leader', False):
                leader_type = '板块龙头'
            elif theme_details.get('is_main_theme', False):
                leader_type = '主线题材'
            else:
                leader_type = '跟风股'
        else:
            # v5格式: 使用原有逻辑
            leader_type = score_details.get('leader_index', {}).get('leader_type', '')
        
        # 生成推荐理由
        reasoning = self._generate_reasoning(score_details, hot_topics)
        
        # 计算最大亏损和预期盈利
        max_loss = (entry_prices['ideal_price'] - smart_stop['stop_price']) * position['shares']
        expected_profit = (take_profit['first_target'] - entry_prices['ideal_price']) * position['shares']
        
        return StockRecommendation(
            code=code,
            name=name,
            sector=sector,
            today_close=today_close,
            today_change=today_change,
            total_score=total_score,
            score_details=score_details,
            ideal_price=entry_prices['ideal_price'],
            acceptable_price=entry_prices['acceptable_price'],
            abandon_price=entry_prices['abandon_price'],
            position_ratio=position['position_ratio'],
            position_amount=position['position_amount'],
            shares=position['shares'],
            stop_loss_price=smart_stop['stop_price'],
            first_target=take_profit['first_target'],
            second_target=take_profit['second_target'],
            max_loss=max_loss,
            expected_profit=expected_profit,
            hot_topics=hot_topics or [],
            leader_type=leader_type,
            risk_level='MEDIUM',
            reasoning=reasoning,
            strategy_type=strategy_type.value,
        )
    
    def _generate_reasoning(self, score_details: Dict, hot_topics: List[str] = None) -> str:
        """
        生成推荐理由
        
        Args:
            score_details: 评分详情
            hot_topics: 相关热点
        
        Returns:
            推荐理由字符串
        """
        reasons = []
        
        if self.scorer_version == "v6":
            # v6格式: 从新的数据结构中提取推荐理由
            
            # K线形态
            kline = score_details.get('kline_pattern', {})
            if kline.get('score', 0) >= 12:
                reasons.append(kline.get('pattern', ''))
            
            # 量价配合
            volume = score_details.get('volume_price', {})
            if volume.get('score', 0) >= 12:
                reasons.append(volume.get('volume_type', ''))
            
            # 趋势位置
            trend = score_details.get('trend_position', {})
            if trend.get('score', 0) >= 16:
                reasons.append(trend.get('trend_type', ''))
            
            # 题材风口
            theme = score_details.get('theme_wind', {})
            if theme.get('score', 0) >= 15:
                topic_type = theme.get('topic_type', '')
                if topic_type:
                    reasons.append(topic_type)
            
            # 资金强度
            capital = score_details.get('capital_strength', {})
            if capital.get('score', 0) >= 12:
                reasons.append(capital.get('flow_type', ''))
            
            # 股性活跃度
            activity = score_details.get('stock_activity', {})
            if activity.get('score', 0) >= 8:
                reasons.append(activity.get('activity_type', ''))
            
            # 热点关联
            if hot_topics:
                reasons.append(f"关联热点: {', '.join(hot_topics[:2])}")
        
        else:
            # v5格式: 使用原有逻辑
            
            # 收盘形态
            pattern = score_details.get('closing_pattern', {})
            if pattern.get('score', 0) >= 12:
                reasons.append(pattern.get('pattern', ''))
            
            # 量能分析
            volume = score_details.get('volume_analysis', {})
            if volume.get('score', 0) >= 12:
                reasons.append(volume.get('vol_type', ''))
            
            # 均线位置
            ma = score_details.get('ma_position', {})
            if ma.get('score', 0) >= 10:
                reasons.append(ma.get('ma_type', ''))
            
            # 热点关联
            if hot_topics:
                reasons.append(f"关联热点: {', '.join(hot_topics[:2])}")
            
            # 技术形态
            tech = score_details.get('technical_pattern', {})
            if tech.get('score', 0) >= 6:
                reasons.append(tech.get('pattern', ''))
        
        return '，'.join(filter(None, reasons)) or '综合评分较高'

    def run(self,
            plan_date: str = None,
            hot_topics: List[str] = None,
            limit_up_count: int = 50,
            limit_down_count: int = 10,
            broken_board_rate: float = 0.15,
            continuous_board_count: int = 5,
            market_profit_rate: float = 0.5,
            save_plan: bool = True) -> TradingPlan:
        """
        运行完整选股流程
        
        核心流程:
        1. 分析大盘环境
        2. 分析市场情绪
        3. 检查是否应该空仓
        4. 对股票池评分
        5. 筛选高分股票
        6. 计算买入价、仓位、止损止盈
        7. 应用情绪调整
        8. 验证总仓位
        9. 生成交易计划
        
        Args:
            plan_date: 计划日期，默认明天
            hot_topics: 当前热点列表
            limit_up_count: 涨停家数 (用于情绪分析)
            limit_down_count: 跌停家数
            broken_board_rate: 炸板率
            continuous_board_count: 连板股数量
            market_profit_rate: 市场赚钱效应
            save_plan: 是否保存计划
        
        Returns:
            TradingPlan: 完整的交易计划
        """
        logger.info("=" * 50)
        logger.info("开始运行隔夜选股...")
        logger.info("=" * 50)
        
        # 确定计划日期 (默认明天)
        if plan_date is None:
            tomorrow = date.today() + timedelta(days=1)
            plan_date = tomorrow.strftime('%Y-%m-%d')
        
        # 1. 分析大盘环境
        logger.info("步骤1: 分析大盘环境...")
        market_env = self.analyze_market_environment()
        logger.info(f"大盘环境: {market_env['env']} - {market_env['description']}")
        
        # 2. 分析市场情绪
        logger.info("步骤2: 分析市场情绪...")
        sentiment = self.analyze_market_sentiment(
            limit_up_count=limit_up_count,
            limit_down_count=limit_down_count,
            broken_board_rate=broken_board_rate,
            continuous_board_count=continuous_board_count,
            market_profit_rate=market_profit_rate,
        )
        logger.info(f"市场情绪: {sentiment['sentiment']} ({sentiment['phase']})")
        logger.info(f"明日预判: {sentiment['prediction']}")
        
        # 3. 检查是否应该空仓
        is_tradable, reason = self.is_market_tradable(market_env)
        if not is_tradable:
            logger.warning(f"市场不适合交易: {reason}")
            return self._create_empty_plan(
                plan_date=plan_date,
                market_env=market_env,
                sentiment=sentiment,
                hot_topics=hot_topics or [],
                reason=reason,
            )
        
        # 4. 对股票池评分
        logger.info(f"步骤3: 对股票池评分 (共{len(self.stock_pool)}只)...")
        scored_stocks = self._score_all_stocks(hot_topics)
        logger.info(f"评分完成: {len(scored_stocks)}只有效股票")
        
        # 5. 筛选高分股票
        logger.info(f"步骤4: 筛选高分股票 (阈值: {self.min_score}分)...")
        qualified_stocks = [s for s in scored_stocks if s['score'] >= self.min_score]
        qualified_stocks.sort(key=lambda x: x['score'], reverse=True)
        logger.info(f"符合条件: {len(qualified_stocks)}只")
        
        # 如果没有符合条件的股票
        if not qualified_stocks:
            logger.warning("没有符合条件的股票")
            return self._create_empty_plan(
                plan_date=plan_date,
                market_env=market_env,
                sentiment=sentiment,
                hot_topics=hot_topics or [],
                reason="没有符合评分条件的股票",
            )
        
        # 6. 创建推荐列表
        logger.info("步骤5: 创建推荐列表...")
        recommendations = self._create_recommendations(
            qualified_stocks=qualified_stocks,
            market_env=market_env['env'],
            sentiment=sentiment['sentiment'],
            hot_topics=hot_topics,
        )
        logger.info(f"生成推荐: {len(recommendations)}只")
        
        # 7. 应用情绪调整
        if sentiment['position_multiplier'] != 1.0:
            logger.info(f"应用情绪调整: 仓位×{sentiment['position_multiplier']}")
            self._apply_position_adjustment(recommendations, sentiment['position_multiplier'])
        
        # 8. 验证总仓位
        self._validate_total_position(recommendations)
        
        # 9. 生成交易计划
        logger.info("步骤6: 生成交易计划...")
        plan = self.plan_generator.generate_plan(
            date=plan_date,
            market_env=market_env,
            sentiment=sentiment,
            recommendations=recommendations,
            hot_topics=hot_topics or [],
        )
        
        # 10. 保存计划
        if save_plan:
            saved_files = self.plan_generator.save_plan(plan)
            logger.info(f"计划已保存: {saved_files}")
        
        logger.info("=" * 50)
        logger.info(f"选股完成! 推荐{len(recommendations)}只股票")
        logger.info("=" * 50)
        
        return plan
    
    def _score_all_stocks(self, hot_topics: List[str] = None) -> List[Dict]:
        """
        对所有股票评分
        
        Args:
            hot_topics: 当前热点列表
        
        Returns:
            评分结果列表
        """
        scored_stocks = []
        
        for i, code in enumerate(self.stock_pool):
            if (i + 1) % 50 == 0:
                logger.info(f"评分进度: {i+1}/{len(self.stock_pool)}")
            
            try:
                result = self.score_stock(
                    code=code,
                    name=self._get_stock_name(code),
                    hot_topics=hot_topics,
                )
                
                if result is not None:
                    total_score, details = result
                    scored_stocks.append({
                        'code': code,
                        'name': self._get_stock_name(code),
                        'score': total_score,
                        'details': details,
                    })
            except Exception as e:
                logger.warning(f"评分失败 {code}: {e}")
        
        return scored_stocks
    
    def _create_recommendations(self,
                                qualified_stocks: List[Dict],
                                market_env: str,
                                sentiment: str,
                                hot_topics: List[str] = None) -> List[StockRecommendation]:
        """
        创建推荐列表
        
        Args:
            qualified_stocks: 符合条件的股票列表
            market_env: 大盘环境
            sentiment: 市场情绪
            hot_topics: 热点列表
        
        Returns:
            推荐列表
        """
        recommendations = []
        
        for stock in qualified_stocks[:self.max_recommendations * 2]:
            try:
                rec = self.create_recommendation(
                    code=stock['code'],
                    name=stock['name'],
                    sector='',
                    total_score=stock['score'],
                    score_details=stock['details'],
                    market_env=market_env,
                    sentiment=sentiment,
                    hot_topics=hot_topics,
                )
                
                if rec is not None:
                    recommendations.append(rec)
                    if len(recommendations) >= self.max_recommendations:
                        break
            except Exception as e:
                logger.warning(f"创建推荐失败 {stock['code']}: {e}")
        
        return recommendations
    
    def _apply_position_adjustment(self, 
                                   recommendations: List[StockRecommendation],
                                   multiplier: float):
        """
        应用仓位调整
        
        Args:
            recommendations: 推荐列表
            multiplier: 仓位调整系数
        """
        for rec in recommendations:
            rec.position_ratio *= multiplier
            rec.position_amount *= multiplier
            rec.shares = int(rec.position_amount / rec.ideal_price / 100) * 100
            # 重新计算最大亏损和预期盈利
            rec.max_loss = (rec.ideal_price - rec.stop_loss_price) * rec.shares
            rec.expected_profit = (rec.first_target - rec.ideal_price) * rec.shares
    
    def _validate_total_position(self, recommendations: List[StockRecommendation]):
        """
        验证并调整总仓位
        
        确保总仓位不超过80%
        
        Args:
            recommendations: 推荐列表
        """
        total_position = sum(r.position_ratio for r in recommendations)
        
        if total_position > 0.8:
            logger.warning(f"总仓位{total_position*100:.1f}%超过80%，进行调整")
            scale = 0.8 / total_position
            self._apply_position_adjustment(recommendations, scale)
    
    def _create_empty_plan(self,
                           plan_date: str,
                           market_env: Dict,
                           sentiment: Dict,
                           hot_topics: List[str],
                           reason: str) -> TradingPlan:
        """
        创建空仓计划
        
        当大盘环境极差时，建议空仓观望
        """
        return TradingPlan(
            date=plan_date,
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            market_env=market_env['env'],
            market_sentiment=sentiment['sentiment'],
            sentiment_phase=sentiment['phase'],
            hot_topics=hot_topics,
            recommendations=[],
            total_position=0,
            operation_tips=[f"⚠️ {reason}", "建议空仓观望，等待市场企稳"],
            risk_warnings=["当前市场风险较高，不建议操作"],
            tomorrow_prediction=sentiment.get('prediction', ''),
            position_multiplier=0,
        )
    
    def _get_stock_name(self, code: str) -> str:
        """
        获取股票名称
        
        Args:
            code: 股票代码
        
        Returns:
            股票名称，如果获取失败返回代码
        """
        # TODO: 从数据源获取股票名称
        # 暂时返回代码
        return code
    
    def get_recommendations_summary(self, plan: TradingPlan) -> str:
        """
        获取推荐摘要
        
        Args:
            plan: 交易计划
        
        Returns:
            摘要字符串
        """
        if not plan.recommendations:
            return "今日无推荐股票"
        
        lines = []
        lines.append(f"推荐{len(plan.recommendations)}只股票:")
        
        for i, rec in enumerate(plan.recommendations, 1):
            lines.append(
                f"{i}. {rec.name}({rec.code}) "
                f"评分:{rec.total_score:.0f} "
                f"买入:{rec.ideal_price:.2f}-{rec.acceptable_price:.2f} "
                f"仓位:{rec.position_ratio*100:.0f}%"
            )
        
        return "\n".join(lines)


# 便捷函数
def create_overnight_picker(total_capital: float = 70000,
                            stock_pool: List[str] = None,
                            scorer_version: str = "v6") -> OvernightStockPicker:
    """
    创建隔夜选股器
    
    Args:
        total_capital: 总资金
        stock_pool: 股票池
        scorer_version: 评分器版本 ("v5" 或 "v6")
    
    Returns:
        OvernightStockPicker实例
    """
    return OvernightStockPicker(
        total_capital=total_capital,
        stock_pool=stock_pool,
        scorer_version=scorer_version,
    )


def quick_overnight_pick(total_capital: float = 70000,
                         hot_topics: List[str] = None,
                         save_plan: bool = True,
                         scorer_version: str = "v6") -> TradingPlan:
    """
    快速运行隔夜选股
    
    Args:
        total_capital: 总资金
        hot_topics: 当前热点
        save_plan: 是否保存计划
        scorer_version: 评分器版本 ("v5" 或 "v6")
    
    Returns:
        TradingPlan: 交易计划
    """
    picker = create_overnight_picker(
        total_capital=total_capital,
        scorer_version=scorer_version
    )
    return picker.run(hot_topics=hot_topics, save_plan=save_plan)
