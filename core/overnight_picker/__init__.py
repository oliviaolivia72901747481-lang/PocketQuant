"""
隔夜选股系统 v5.0 - Overnight Stock Picker

T日选股，T+1执行的隔夜短线选股系统。
每天收盘后(15:00后)运行，基于当日完整日线数据，
筛选出明天可以买入的股票，并给出具体的买入价格、仓位和止损止盈建议。
"""

from .models import StockRecommendation, TradingPlan
from .scorer import TomorrowPotentialScorer
from .calculator import (
    EntryPriceCalculator,
    PositionAdvisor,
    StopLossCalculator,
    TakeProfitCalculator,
    SmartStopLoss,
    TrailingStop,
)
from .topic_matcher import (
    SmartTopicMatcher,
    CompanyBusiness,
    LeaderRecord,
    get_smart_topic_matcher,
)
from .call_auction_filter import (
    CallAuctionFilter,
    AuctionAction,
    AuctionResult,
    RiskLevel,
    StrategyType,
)
from .sentiment_predictor import (
    SentimentCyclePredictor,
    SentimentPhase,
    SentimentLevel,
    SentimentAnalysisResult,
    TomorrowPrediction,
    create_sentiment_predictor,
    quick_sentiment_prediction,
)
from .pre_market_adjuster import (
    PreMarketAdjuster,
    OvernightData,
    USMarketData,
    StockAnnouncement,
    AdjustmentReport,
    Adjustment,
    AdjustmentType,
    MarketSeverity,
    create_pre_market_adjuster,
    quick_pre_market_check,
)
from .plan_generator import (
    TradingPlanGenerator,
    create_trading_plan_generator,
    quick_generate_plan,
)
from .picker import (
    OvernightStockPicker,
    MarketEnvironment,
    create_overnight_picker,
    quick_overnight_pick,
)
from .backtester import (
    OvernightBacktestEngine,
    BacktestConfig,
    BacktestResult,
    DailyPickResult,
    run_overnight_backtest,
    quick_backtest,
)

__all__ = [
    'StockRecommendation',
    'TradingPlan',
    'TomorrowPotentialScorer',
    'EntryPriceCalculator',
    'PositionAdvisor',
    'StopLossCalculator',
    'TakeProfitCalculator',
    'SmartStopLoss',
    'TrailingStop',
    'SmartTopicMatcher',
    'CompanyBusiness',
    'LeaderRecord',
    'get_smart_topic_matcher',
    'CallAuctionFilter',
    'AuctionAction',
    'AuctionResult',
    'RiskLevel',
    'StrategyType',
    # Sentiment Cycle Predictor
    'SentimentCyclePredictor',
    'SentimentPhase',
    'SentimentLevel',
    'SentimentAnalysisResult',
    'TomorrowPrediction',
    'create_sentiment_predictor',
    'quick_sentiment_prediction',
    # Pre-Market Adjuster
    'PreMarketAdjuster',
    'OvernightData',
    'USMarketData',
    'StockAnnouncement',
    'AdjustmentReport',
    'Adjustment',
    'AdjustmentType',
    'MarketSeverity',
    'create_pre_market_adjuster',
    'quick_pre_market_check',
    # Trading Plan Generator
    'TradingPlanGenerator',
    'create_trading_plan_generator',
    'quick_generate_plan',
    # Overnight Stock Picker (Main Class)
    'OvernightStockPicker',
    'MarketEnvironment',
    'create_overnight_picker',
    'quick_overnight_pick',
    # Backtest Engine
    'OvernightBacktestEngine',
    'BacktestConfig',
    'BacktestResult',
    'DailyPickResult',
    'run_overnight_backtest',
    'quick_backtest',
]
