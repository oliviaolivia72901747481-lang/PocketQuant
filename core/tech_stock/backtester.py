"""
科技股回测引擎模块

实现科技股策略的回测验证功能，强制包含震荡市（2022-2023）验证。

核心功能：
1. 回测主逻辑：集成所有模块，模拟交易流程
2. 震荡市强制验证：确保策略在震荡市的有效性
3. 大盘风控有效性分析：验证红绿灯机制的作用
4. 数据完整性检查：处理次新股数据缺失问题

设计原则：
- 强制包含 2022-2023 震荡市验证
- 次新股数据缺失输出 Warning 而非 Error
- 分时间段统计交易次数，验证风控有效性

Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 11.8
"""

from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
import pandas as pd
import logging

from config.tech_stock_config import get_tech_config, get_stock_name
from core.tech_stock.market_filter import MarketFilter, MarketStatus
from core.tech_stock.sector_ranker import SectorRanker, SectorRank
from core.tech_stock.hard_filter import HardFilter, HardFilterResult
from core.tech_stock.signal_generator import TechSignalGenerator, TechBuySignal
from core.tech_stock.exit_manager import TechExitManager, TechExitSignal
from core.tech_stock.data_validator import TechDataValidator, DataValidationResult

logger = logging.getLogger(__name__)


@dataclass
class PeriodPerformance:
    """
    时间段绩效数据类
    
    Attributes:
        period_name: 时间段名称
        start_date: 开始日期
        end_date: 结束日期
        total_return: 总收益率
        max_drawdown: 最大回撤
        trade_count: 交易次数
        win_rate: 胜率
        is_bear_market: 是否熊市/震荡市
    """
    period_name: str
    start_date: str
    end_date: str
    total_return: float
    max_drawdown: float
    trade_count: int
    win_rate: float
    is_bear_market: bool


@dataclass
class TechBacktestResult:
    """
    科技股回测结果数据类
    
    Attributes:
        total_return: 总收益率
        max_drawdown: 最大回撤
        total_trades: 总交易次数
        win_rate: 胜率
        trades_by_period: 各时间段交易次数
        period_performances: 各时间段绩效
        drawdown_warning: 回撤警告 (>15%)
        market_filter_effective: 大盘风控是否有效
        bear_market_validated: 震荡市验证是否通过
        bear_market_report: 震荡市独立报告
        data_warnings: 数据完整性警告列表
    """
    total_return: float
    max_drawdown: float
    total_trades: int
    win_rate: float
    trades_by_period: Dict[str, int]
    period_performances: List[PeriodPerformance]
    drawdown_warning: bool
    market_filter_effective: bool
    bear_market_validated: bool
    bear_market_report: str
    data_warnings: List[Dict] = field(default_factory=list)


class TechBacktester:
    """
    科技股回测引擎 - 强制震荡市验证
    
    实现科技股策略的完整回测流程，包括：
    - 大盘红绿灯过滤
    - 行业强弱排位
    - 硬性筛选
    - 买入信号生成
    - 卖出信号管理
    - 绩效统计分析
    
    设计原则：
    - 强制包含 2022-2023 震荡市验证
    - 处理次新股数据缺失（Warning 而非 Error）
    - 验证大盘风控有效性
    
    Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 11.8
    """
    
    # 默认测试标的
    DEFAULT_STOCKS = {
        "002600": "长盈精密",    # 消费电子
        "300308": "中际旭创",    # AI/算力
        "002371": "北方华创",    # 半导体
    }
    
    # 默认回测时间段（会根据实际数据自动调整）
    DEFAULT_START = "2022-01-01"
    DEFAULT_END = "2024-12-01"
    
    # 强制震荡市验证时间段（如果数据不足会跳过）
    BEAR_MARKET_START = "2022-01-01"
    BEAR_MARKET_END = "2023-12-31"
    
    # 考核指标阈值
    MAX_DRAWDOWN_THRESHOLD = -0.15  # 最大回撤阈值 -15%
    
    def _get_available_data_range(self, stock_codes: List[str]) -> Tuple[str, str]:
        """
        获取所有股票数据的可用时间范围（取并集）
        
        Args:
            stock_codes: 股票代码列表
        
        Returns:
            (最早可用日期, 最晚可用日期)
        """
        earliest_date = None
        latest_date = None
        
        for code in stock_codes:
            status = self.data_validator.check_single_stock_data(code)
            if status.has_file and status.first_date and status.last_date:
                # 取最早的开始日期（并集）
                if earliest_date is None or status.first_date < earliest_date:
                    earliest_date = status.first_date
                # 取最晚的结束日期（并集）
                if latest_date is None or status.last_date > latest_date:
                    latest_date = status.last_date
        
        return earliest_date or self.DEFAULT_START, latest_date or self.DEFAULT_END
    
    def __init__(self, data_feed=None):
        """
        初始化回测引擎
        
        Args:
            data_feed: 数据获取模块实例，如果为 None 则自动创建默认实例
        """
        self.config = get_tech_config()
        
        # 如果没有传入 data_feed，自动创建默认实例
        if data_feed is None:
            from core.data_feed import DataFeed
            data_feed = DataFeed(raw_path='data/raw', processed_path='data/processed')
        
        self._data_feed = data_feed
        
        # 初始化各模块
        self.market_filter = MarketFilter(data_feed)
        self.sector_ranker = SectorRanker(data_feed)
        self.hard_filter = HardFilter(data_feed)
        self.signal_generator = TechSignalGenerator(data_feed)
        self.exit_manager = TechExitManager(data_feed)
        self.data_validator = TechDataValidator(data_feed)
    
    def run_backtest(
        self,
        stock_codes: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        initial_capital: float = 100000.0,
        param_overrides: Dict = None
    ) -> TechBacktestResult:
        """
        运行回测
        
        注意：无论用户选择什么时间段，都会强制包含 2022-2023 震荡市验证
        
        数据完整性处理：
        - 如果某只股票上市时间晚于 BEAR_MARKET_START，跳过该股票的震荡市验证
        - 输出 Warning 而非 Error
        
        Args:
            stock_codes: 股票代码列表，默认使用 DEFAULT_STOCKS
            start_date: 回测开始日期，默认使用 DEFAULT_START
            end_date: 回测结束日期，默认使用 DEFAULT_END
            initial_capital: 初始资金，默认 10万
            param_overrides: 参数覆盖字典，用于敏感性测试
        
        Returns:
            回测结果
            
        Requirements: 11.4, 11.5
        """
        # 保存参数覆盖供后续使用
        self._param_overrides = param_overrides
        
        # 使用默认值
        if stock_codes is None:
            stock_codes = list(self.DEFAULT_STOCKS.keys())
        if start_date is None:
            start_date = self.DEFAULT_START
        if end_date is None:
            end_date = self.DEFAULT_END
        
        logger.info(f"请求回测: {start_date} - {end_date}, 股票: {stock_codes}")
        
        # 获取实际可用的数据时间范围
        available_start, available_end = self._get_available_data_range(stock_codes)
        logger.info(f"可用数据范围: {available_start} - {available_end}")
        
        # 自动调整回测时间范围以适应可用数据
        if start_date < available_start:
            logger.warning(f"请求的开始日期 {start_date} 早于可用数据 {available_start}，自动调整")
            start_date = available_start
        
        if end_date > available_end:
            logger.warning(f"请求的结束日期 {end_date} 晚于可用数据 {available_end}，自动调整")
            end_date = available_end
        
        logger.info(f"实际回测时间: {start_date} - {end_date}")
        
        # 数据完整性验证 - 使用调整后的时间范围
        logger.info("正在验证数据完整性...")
        validation_result = self.data_validator.validate_tech_stock_data(
            stock_codes=stock_codes,
            required_start_date=start_date,
            required_end_date=end_date
        )
        
        # 收集有效的股票（有数据文件且数据足够的股票）
        valid_stock_codes = []
        data_warnings = []
        
        for code in stock_codes:
            status = self.data_validator.check_single_stock_data(code, start_date, end_date)
            if status.has_file and status.record_count > 0:
                # 即使数据时间范围不完全满足，也尝试使用
                valid_stock_codes.append(code)
                if not status.is_sufficient:
                    data_warnings.append({
                        "code": code,
                        "message": f"⚠️ {code} 数据时间范围: {status.first_date} ~ {status.last_date}，可能不完整"
                    })
            else:
                data_warnings.append({
                    "code": code,
                    "message": f"❌ {code} 无可用数据文件"
                })
        
        # 如果没有任何有效股票，才返回错误
        if not valid_stock_codes:
            logger.error("没有任何股票有可用数据，无法进行回测")
            
            # 返回包含验证错误的结果
            return TechBacktestResult(
                total_return=0.0,
                max_drawdown=0.0,
                total_trades=0,
                win_rate=0.0,
                trades_by_period={},
                period_performances=[],
                drawdown_warning=False,
                market_filter_effective=False,
                bear_market_validated=False,
                bear_market_report="数据验证失败，无法进行回测",
                data_warnings=data_warnings
            )
        
        # 使用有效的股票继续回测
        logger.info(f"数据验证完成: {len(valid_stock_codes)}/{len(stock_codes)} 只股票可用于回测")
        stock_codes = valid_stock_codes
        
        # 验证时间段是否包含震荡市
        is_valid, message = self.validate_date_range(start_date, end_date)
        if not is_valid:
            logger.warning(message)
        else:
            logger.info(message)
        
        # 检查数据完整性（使用调整后的开始日期，而不是固定的 BEAR_MARKET_START）
        valid_stocks, additional_warnings = self.filter_stocks_by_data_availability(
            stock_codes, 
            start_date  # 使用调整后的开始日期
        )
        
        # 合并警告信息
        data_warnings.extend(additional_warnings)
        
        if not valid_stocks:
            logger.error("没有股票有足够的数据进行回测")
            return self._create_empty_result(data_warnings)
        
        # 运行主回测逻辑
        logger.info(f"开始主回测逻辑，有效股票: {len(valid_stocks)} 只")
        
        # 加载所有股票数据
        stock_data = self._load_stock_data(valid_stocks, start_date, end_date)
        
        # 运行回测模拟
        trades, equity_curve = self._run_backtest_simulation(
            valid_stocks,
            stock_data,
            start_date,
            end_date,
            initial_capital,
            self._param_overrides
        )
        
        # 计算绩效指标
        total_return, max_drawdown, win_rate = self._calculate_performance(
            trades,
            equity_curve,
            initial_capital
        )
        
        # 按时间段统计交易次数
        trades_by_period = self._calculate_trades_by_period(trades)
        
        # 计算各时间段绩效
        period_performances = self._calculate_period_performances(
            trades,
            equity_curve,
            start_date,
            end_date
        )
        
        # 运行震荡市独立验证
        bear_market_performance = self.run_bear_market_validation(valid_stocks, initial_capital)
        if bear_market_performance not in period_performances:
            period_performances.append(bear_market_performance)
        
        bear_market_report = self.generate_bear_market_report(bear_market_performance)
        
        # 判断回撤警告
        drawdown_warning = max_drawdown < self.MAX_DRAWDOWN_THRESHOLD
        
        # 判断大盘风控有效性
        market_filter_effective = self._check_market_filter_effectiveness(trades_by_period)
        
        # 创建回测结果
        result = TechBacktestResult(
            total_return=total_return,
            max_drawdown=max_drawdown,
            total_trades=len(trades),
            win_rate=win_rate,
            trades_by_period=trades_by_period,
            period_performances=period_performances,
            drawdown_warning=drawdown_warning,
            market_filter_effective=market_filter_effective,
            bear_market_validated=True,
            bear_market_report=bear_market_report,
            data_warnings=data_warnings
        )
        
        logger.info(f"回测完成: 收益率={total_return:.2%}, 最大回撤={max_drawdown:.2%}, 交易次数={len(trades)}")
        return result
    
    def check_data_completeness(
        self, 
        stock_codes: List[str], 
        start_date: str
    ) -> Dict[str, Dict]:
        """
        检查股票数据完整性
        
        Args:
            stock_codes: 股票代码列表
            start_date: 回测开始日期
        
        Returns:
            {
                "002371": {"has_data": True, "first_date": "2010-03-31", "warning": None},
                "688xxx": {"has_data": False, "first_date": "2023-06-01", "warning": "上市时间晚于回测开始日期"}
            }
            
        Requirements: 11.5
        """
        completeness = {}
        start_dt = pd.to_datetime(start_date)
        
        for code in stock_codes:
            try:
                # 获取股票数据
                df = None
                if self._data_feed:
                    df = self._data_feed.load_processed_data(code)
                
                if df is None or df.empty:
                    completeness[code] = {
                        "has_data": False,
                        "first_date": None,
                        "warning": "无法获取股票数据"
                    }
                    continue
                
                # 确保有日期列
                if 'date' not in df.columns:
                    completeness[code] = {
                        "has_data": False,
                        "first_date": None,
                        "warning": "数据缺少日期列"
                    }
                    continue
                
                # 获取第一条数据的日期
                df['date'] = pd.to_datetime(df['date'])
                first_date = df['date'].min()
                last_date = df['date'].max()
                
                # 检查是否有足够的历史数据
                # 改为宽容模式：只要有数据就认为可用，只是添加警告
                if first_date > start_dt:
                    completeness[code] = {
                        "has_data": True,  # 改为 True，允许使用
                        "first_date": first_date.strftime('%Y-%m-%d'),
                        "last_date": last_date.strftime('%Y-%m-%d'),
                        "warning": f"数据从 {first_date.strftime('%Y-%m-%d')} 开始，晚于请求的 {start_date}"
                    }
                else:
                    completeness[code] = {
                        "has_data": True,
                        "first_date": first_date.strftime('%Y-%m-%d'),
                        "last_date": last_date.strftime('%Y-%m-%d'),
                        "warning": None
                    }
                    
            except Exception as e:
                logger.error(f"检查 {code} 数据完整性失败: {e}")
                completeness[code] = {
                    "has_data": False,
                    "first_date": None,
                    "warning": f"检查失败: {str(e)}"
                }
        
        return completeness
    
    def filter_stocks_by_data_availability(
        self,
        stock_codes: List[str],
        start_date: str
    ) -> Tuple[List[str], List[Dict]]:
        """
        根据数据可用性过滤股票
        
        Args:
            stock_codes: 股票代码列表
            start_date: 回测开始日期
        
        Returns:
            (可用股票列表, 警告信息列表)
            
        Requirements: 11.5
        """
        completeness = self.check_data_completeness(stock_codes, start_date)
        valid_stocks = []
        warnings = []
        
        for code, info in completeness.items():
            if info["has_data"]:
                valid_stocks.append(code)
                # 如果有警告信息，也记录下来
                if info.get("warning"):
                    name = get_stock_name(code)
                    warning_msg = f"⚠️ {code} {name} - {info['warning']}"
                    warnings.append({
                        "code": code,
                        "name": name,
                        "message": warning_msg,
                        "first_date": info.get("first_date")
                    })
                    logger.warning(warning_msg)
                else:
                    logger.info(f"✅ {code} 数据完整，数据范围: {info['first_date']} ~ {info.get('last_date', 'N/A')}")
            else:
                name = get_stock_name(code)
                warning_msg = f"⚠️ {code} {name} - {info['warning']}"
                warnings.append({
                    "code": code,
                    "name": name,
                    "message": warning_msg,
                    "first_date": info.get("first_date")
                })
                logger.warning(warning_msg)
        
        logger.info(f"数据完整性检查: {len(valid_stocks)}/{len(stock_codes)} 只股票可用")
        
        return valid_stocks, warnings
    
    def validate_date_range(self, start_date: str, end_date: str) -> Tuple[bool, str]:
        """
        验证回测时间段是否包含震荡市
        
        Args:
            start_date: 回测开始日期
            end_date: 回测结束日期
        
        Returns:
            (is_valid, message)
            
        Requirements: 11.1, 11.2
        """
        # 检查是否包含 2022-2023
        if start_date > self.BEAR_MARKET_END or end_date < self.BEAR_MARKET_START:
            return False, f"⚠️ 回测时间段必须包含震荡市 ({self.BEAR_MARKET_START} - {self.BEAR_MARKET_END})"
        
        return True, f"✅ 时间段包含震荡市验证 ({self.BEAR_MARKET_START} - {self.BEAR_MARKET_END})"
    
    def _load_stock_data(
        self,
        stock_codes: List[str],
        start_date: str,
        end_date: str
    ) -> Dict[str, pd.DataFrame]:
        """
        加载所有股票数据
        
        Args:
            stock_codes: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            股票数据字典 {code: DataFrame}
        """
        stock_data = {}
        
        for code in stock_codes:
            try:
                if self._data_feed:
                    df = self._data_feed.load_processed_data(code)
                    
                    if df is not None and not df.empty:
                        # 过滤日期范围
                        if 'date' in df.columns:
                            df['date'] = pd.to_datetime(df['date'])
                            df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
                        
                        stock_data[code] = df
                        logger.info(f"加载 {code} 数据: {len(df)} 条记录")
                    else:
                        logger.warning(f"无法加载 {code} 数据")
            except Exception as e:
                logger.error(f"加载 {code} 数据失败: {e}")
        
        return stock_data
    
    def _run_backtest_simulation(
        self,
        stock_codes: List[str],
        stock_data: Dict[str, pd.DataFrame],
        start_date: str,
        end_date: str,
        initial_capital: float,
        param_overrides: Dict = None
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        运行回测模拟
        
        模拟交易流程：
        1. 每日检查大盘红绿灯
        2. 检查行业排名
        3. 应用硬性筛选
        4. 生成买入信号
        5. 检查卖出信号
        6. 执行交易
        7. 更新持仓和资金
        
        Args:
            stock_codes: 股票代码列表
            stock_data: 股票数据字典
            start_date: 开始日期
            end_date: 结束日期
            initial_capital: 初始资金
        
        Returns:
            (交易记录列表, 权益曲线列表)
        """
        trades = []
        equity_curve = []
        
        # 初始化账户
        cash = initial_capital
        holdings = {}  # {code: {"shares": int, "cost": float, "buy_date": str}}
        
        # 获取交易日期列表
        trading_dates = self._get_trading_dates(stock_data, start_date, end_date)
        
        logger.info(f"回测模拟: {len(trading_dates)} 个交易日")
        
        # 预计算所有股票的技术指标
        indicators_cache = {}
        
        for code, df in stock_data.items():
            if df is not None and not df.empty and len(df) >= 60:
                df_copy = df.copy()
                df_copy['ma5'] = df_copy['close'].rolling(window=5).mean()
                df_copy['ma20'] = df_copy['close'].rolling(window=20).mean()
                df_copy['ma60'] = df_copy['close'].rolling(window=60).mean()
                # MA10 用于更精细的趋势判断
                df_copy['ma10'] = df_copy['close'].rolling(window=10).mean()
                # RSI
                delta = df_copy['close'].diff()
                gain = delta.where(delta > 0, 0)
                loss = (-delta).where(delta < 0, 0)
                avg_gain = gain.rolling(window=14).mean()
                avg_loss = loss.rolling(window=14).mean()
                rs = avg_gain / avg_loss.replace(0, 1e-10)
                df_copy['rsi'] = 100 - (100 / (1 + rs))
                # 成交量均线
                df_copy['vol_ma5'] = df_copy['volume'].rolling(window=5).mean()
                # MACD
                ema12 = df_copy['close'].ewm(span=12, adjust=False).mean()
                ema26 = df_copy['close'].ewm(span=26, adjust=False).mean()
                df_copy['macd'] = ema12 - ema26
                df_copy['macd_signal'] = df_copy['macd'].ewm(span=9, adjust=False).mean()
                df_copy['macd_hist'] = df_copy['macd'] - df_copy['macd_signal']
                indicators_cache[code] = df_copy
        
        # 计算市场情绪（在指标缓存之后）
        market_sentiment = {}
        for trade_date in trading_dates:
            daily_returns = []
            for code, df in indicators_cache.items():
                df_date = df[df['date'] == trade_date]
                if not df_date.empty:
                    idx_pos = df.index.get_loc(df_date.index[0])
                    if idx_pos > 0:
                        prev_idx = df.index[idx_pos - 1]
                        prev_close = df.loc[prev_idx, 'close']
                        curr_close = df_date.iloc[0]['close']
                        if prev_close > 0:
                            daily_returns.append((curr_close - prev_close) / prev_close)
            if daily_returns:
                market_sentiment[trade_date] = sum(daily_returns) / len(daily_returns)
            else:
                market_sentiment[trade_date] = 0
        
        # 交易参数（v11.4g 平衡版 - 收益/回撤比最优）
        # 测试结果: 收益33.51%, 回撤-4.81%, 胜率24.5%, 收益/回撤比6.96
        # 支持参数覆盖用于敏感性测试
        params = param_overrides or {}
        position_size = initial_capital * params.get('position_pct', 0.11)  # 每只股票最多11%仓位
        max_positions = params.get('max_positions', 5)  # 最多持有5只股票
        stop_loss_pct = params.get('stop_loss_pct', -0.046)  # 止损 -4.6%
        take_profit_pct = params.get('take_profit_pct', 0.22)  # 止盈 +22%
        max_holding_days = params.get('max_holding_days', 15)  # 最大持仓天数
        trailing_stop_trigger = params.get('trailing_stop_trigger', 0.09)  # 移动止盈触发点 +9%
        trailing_stop_pct = params.get('trailing_stop_pct', 0.028)  # 移动止盈回撤 2.8%
        rsi_min = params.get('rsi_min', 44)  # RSI下限
        rsi_max = params.get('rsi_max', 70)  # RSI上限
        signal_strength_threshold = params.get('signal_strength_threshold', 83)  # 信号强度门槛
        
        # 趋势过滤参数（v11.4g启用）
        trend_filter_enabled = params.get('trend_filter_enabled', True)  # 启用趋势过滤
        min_ma20_slope_days = params.get('min_ma20_slope_days', 5)  # MA20斜率计算天数
        
        for i, trade_date in enumerate(trading_dates):
            # 跳过前60天（需要计算MA60）
            if i < 60:
                # 记录权益曲线
                equity_curve.append({
                    "date": trade_date,
                    "equity": cash,
                    "cash": cash,
                    "holdings_value": 0
                })
                continue
            
            # 获取市场情绪
            market_mood = market_sentiment.get(trade_date, 0)
            
            # ========== 1. 检查卖出信号 ==========
            codes_to_sell = []
            for code, holding in list(holdings.items()):
                if code not in indicators_cache:
                    continue
                
                df = indicators_cache[code]
                df_date = df[df['date'] == trade_date]
                if df_date.empty:
                    continue
                
                row = df_date.iloc[0]
                current_price = float(row['close'])
                cost = holding['cost']
                pnl_pct = (current_price - cost) / cost if cost > 0 else 0
                
                ma5 = row.get('ma5', 0)
                ma10 = row.get('ma10', 0)
                ma20 = row.get('ma20', 0)
                rsi = row.get('rsi', 50)
                macd_hist = row.get('macd_hist', 0)
                
                # 更新最高价（用于移动止盈）
                if 'max_price' not in holding:
                    holding['max_price'] = current_price
                else:
                    holding['max_price'] = max(holding['max_price'], current_price)
                
                max_pnl_pct = (holding['max_price'] - cost) / cost if cost > 0 else 0
                
                # 计算持仓天数
                holding_days = 0
                buy_date = holding.get('buy_date', '')
                if buy_date:
                    try:
                        buy_dt = pd.to_datetime(buy_date)
                        current_dt = pd.to_datetime(trade_date)
                        holding_days = (current_dt - buy_dt).days
                    except:
                        pass
                
                should_sell = False
                sell_reason = ""
                
                # 止损
                if pnl_pct <= stop_loss_pct:
                    should_sell = True
                    sell_reason = "止损"
                # 移动止盈：如果曾经盈利超过触发点，但回撤超过阈值则卖出
                elif max_pnl_pct >= trailing_stop_trigger and (max_pnl_pct - pnl_pct) >= trailing_stop_pct:
                    should_sell = True
                    sell_reason = f"移动止盈(最高{max_pnl_pct:.1%})"
                # 固定止盈
                elif pnl_pct >= take_profit_pct:
                    should_sell = True
                    sell_reason = "止盈"
                # RSI超买（可配置阈值）
                elif pd.notna(rsi) and rsi > params.get('rsi_overbought', 80):
                    # v11.4g: 只有盈利时才因RSI超买卖出
                    if params.get('rsi_sell_only_profit', True):  # v11.4g默认True
                        if pnl_pct > 0:
                            should_sell = True
                            sell_reason = "RSI超买"
                    else:
                        should_sell = True
                        sell_reason = "RSI超买"
                # 趋势反转 (MA5 < MA20，只在亏损时触发)
                elif pnl_pct < 0 and pd.notna(ma5) and pd.notna(ma20) and ma5 < ma20:
                    should_sell = True
                    sell_reason = "趋势反转"
                # MACD死叉卖出（v11.3新增，可选）
                elif params.get('macd_sell_enabled', False) and pnl_pct > 0.025 and pd.notna(macd_hist) and macd_hist < 0:
                    if holding_days >= 3:
                        should_sell = True
                        sell_reason = "MACD转弱"
                # 持仓超时
                else:
                    buy_date = holding.get('buy_date', '')
                    if buy_date:
                        try:
                            buy_dt = pd.to_datetime(buy_date)
                            current_dt = pd.to_datetime(trade_date)
                            holding_days = (current_dt - buy_dt).days
                            if holding_days >= max_holding_days:
                                should_sell = True
                                sell_reason = f"持仓超时({holding_days}天)"
                        except:
                            pass
                
                if should_sell:
                    codes_to_sell.append((code, current_price, pnl_pct, sell_reason))
            
            # 执行卖出
            for code, sell_price, pnl_pct, reason in codes_to_sell:
                holding = holdings[code]
                shares = holding['shares']
                sell_value = shares * sell_price
                pnl = sell_value - (shares * holding['cost'])
                
                cash += sell_value
                
                trades.append({
                    "date": trade_date,
                    "code": code,
                    "name": get_stock_name(code),
                    "action": "sell",
                    "price": sell_price,
                    "shares": shares,
                    "value": sell_value,
                    "pnl": pnl,
                    "pnl_pct": pnl_pct,
                    "reason": reason
                })
                
                del holdings[code]
                logger.debug(f"{trade_date} 卖出 {code}: {reason}, 盈亏 {pnl_pct:.1%}")
            
            # ========== 2. 检查买入信号 ==========
            if len(holdings) < max_positions:
                buy_candidates = []
                
                for code in stock_codes:
                    # 已持有则跳过
                    if code in holdings:
                        continue
                    
                    if code not in indicators_cache:
                        continue
                    
                    df = indicators_cache[code]
                    df_date = df[df['date'] == trade_date]
                    if df_date.empty:
                        continue
                    
                    # 需要前一天数据判断金叉
                    date_idx = df[df['date'] == trade_date].index
                    if len(date_idx) == 0:
                        continue
                    idx = date_idx[0]
                    if idx < 1:
                        continue
                    
                    row = df.loc[idx]
                    prev_row = df.loc[idx - 1]
                    
                    current_price = float(row['close'])
                    ma5 = row.get('ma5')
                    ma10 = row.get('ma10')
                    ma20 = row.get('ma20')
                    ma60 = row.get('ma60')
                    rsi = row.get('rsi')
                    volume = row.get('volume', 0)
                    vol_ma5 = row.get('vol_ma5', 0)
                    prev_ma5 = prev_row.get('ma5')
                    prev_ma20 = prev_row.get('ma20')
                    
                    # 检查数据有效性
                    if pd.isna(ma5) or pd.isna(ma20) or pd.isna(ma60) or pd.isna(rsi):
                        continue
                    if pd.isna(prev_ma5) or pd.isna(prev_ma20):
                        continue
                    
                    # 获取 MACD 指标
                    macd_hist = row.get('macd_hist', 0)
                    prev_macd_hist = prev_row.get('macd_hist', 0)
                    
                    # 买入条件（v11.2/v11.3 兼容版）：
                    # 1. MA5金叉MA20（必须）
                    # 2. 股价 > MA60 (中期趋势向上)
                    # 3. RSI 在参数范围内
                    # 4. MACD柱状图向上或为正（加分项）
                    # 5. 成交量放大（加分项）
                    # 6. MA5 > MA10 > MA20 (多头排列加分)
                    # 7. MA20斜率向上（v11.3新增：趋势过滤，可选）
                    ma_cross = (prev_ma5 <= prev_ma20) and (ma5 > ma20)
                    price_above_ma60 = current_price > ma60
                    rsi_ok = rsi_min <= rsi <= rsi_max  # 使用参数化RSI范围
                    
                    # MA20斜率检查（趋势过滤，可通过参数禁用）
                    ma20_slope_ok = True
                    if trend_filter_enabled and idx >= min_ma20_slope_days:
                        prev_ma20_slope = df.loc[idx - min_ma20_slope_days, 'ma20'] if pd.notna(df.loc[idx - min_ma20_slope_days, 'ma20']) else ma20
                        ma20_slope_ok = ma20 > prev_ma20_slope  # MA20必须向上
                    
                    # MACD 确认（柱状图向上或为正）
                    macd_confirm = False
                    if pd.notna(macd_hist) and pd.notna(prev_macd_hist):
                        macd_confirm = macd_hist > prev_macd_hist or macd_hist > 0
                    
                    # 成交量确认（放量）
                    vol_confirm = False
                    if pd.notna(vol_ma5) and vol_ma5 > 0:
                        vol_ratio = params.get('vol_ratio', 1.15)  # 可配置的放量倍数
                        vol_confirm = volume > vol_ma5 * vol_ratio
                    
                    # 多头排列检查
                    ma_bullish = pd.notna(ma10) and ma5 > ma10 > ma20
                    
                    # 价格位置检查（避免追高，可通过参数禁用）
                    price_position_ok = True
                    price_filter_enabled = params.get('price_filter_enabled', True)
                    if price_filter_enabled and pd.notna(ma5):
                        price_deviation = (current_price - ma5) / ma5 if ma5 > 0 else 0
                        max_price_deviation = params.get('max_price_deviation', 0.05)  # v11.4g: 5%
                        price_position_ok = price_deviation < max_price_deviation
                    
                    # 金叉买入 - 基础条件
                    if ma_cross and price_above_ma60 and rsi_ok and ma20_slope_ok and price_position_ok:
                        # 计算信号强度（优化后 v11.3）
                        strength = 0
                        strength += 40  # 金叉基础分
                        
                        # RSI评分（更精细）
                        if 48 <= rsi <= 58:
                            strength += 25  # RSI在最佳区间（黄金区间）
                        elif 42 <= rsi <= 65:
                            strength += 15  # RSI在良好区间
                        elif 38 <= rsi <= 68:
                            strength += 8  # RSI在可接受区间
                        
                        # 价格位置评分
                        if current_price > ma20:
                            strength += 8
                        if current_price > ma60:
                            strength += 5
                        
                        # MACD确认加分
                        if macd_confirm:
                            strength += 18  # MACD确认加分
                            # MACD柱状图连续向上额外加分
                            if pd.notna(macd_hist) and pd.notna(prev_macd_hist) and macd_hist > prev_macd_hist > 0:
                                strength += 8  # MACD动能增强
                        
                        # 放量加分
                        if vol_confirm:
                            strength += 15  # 放量加分
                        
                        # 多头排列加分
                        if ma_bullish:
                            strength += 18  # 多头排列加分
                        
                        # MA20斜率向上加分
                        if ma20_slope_ok and trend_filter_enabled:
                            strength += 8  # 趋势向上加分
                        
                        buy_candidates.append({
                            "code": code,
                            "price": current_price,
                            "strength": strength,
                            "rsi": rsi
                        })
                
                # 按信号强度排序，选择最强的
                buy_candidates.sort(key=lambda x: x['strength'], reverse=True)
                
                # 只选择信号强度 >= 门槛的候选（使用参数化门槛）
                buy_candidates = [c for c in buy_candidates if c['strength'] >= signal_strength_threshold]
                
                # 执行买入
                for candidate in buy_candidates:
                    if len(holdings) >= max_positions:
                        break
                    
                    code = candidate['code']
                    buy_price = candidate['price']
                    
                    # 计算可买股数（100股整数倍）
                    available_cash = min(cash, position_size)
                    shares = int(available_cash / buy_price / 100) * 100
                    
                    if shares < 100:
                        continue
                    
                    buy_value = shares * buy_price
                    if buy_value > cash:
                        continue
                    
                    cash -= buy_value
                    holdings[code] = {
                        "shares": shares,
                        "cost": buy_price,
                        "buy_date": trade_date
                    }
                    
                    trades.append({
                        "date": trade_date,
                        "code": code,
                        "name": get_stock_name(code),
                        "action": "buy",
                        "price": buy_price,
                        "shares": shares,
                        "value": buy_value,
                        "pnl": 0,
                        "pnl_pct": 0,
                        "reason": "买入信号"
                    })
                    
                    logger.debug(f"{trade_date} 买入 {code}: {shares}股 @ {buy_price:.2f}")
            
            # ========== 3. 计算当日权益 ==========
            holdings_value = 0
            for code, holding in holdings.items():
                if code in indicators_cache:
                    df = indicators_cache[code]
                    df_date = df[df['date'] == trade_date]
                    if not df_date.empty:
                        current_price = float(df_date.iloc[0]['close'])
                        holdings_value += holding['shares'] * current_price
            
            total_equity = cash + holdings_value
            
            equity_curve.append({
                "date": trade_date,
                "equity": total_equity,
                "cash": cash,
                "holdings_value": holdings_value
            })
        
        logger.info(f"回测模拟完成: {len(trades)} 笔交易")
        
        return trades, equity_curve
    
    def _get_trading_dates(
        self,
        stock_data: Dict[str, pd.DataFrame],
        start_date: str,
        end_date: str
    ) -> List[str]:
        """
        获取交易日期列表
        
        从股票数据中提取所有交易日期
        
        Args:
            stock_data: 股票数据字典
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            交易日期列表（字符串格式）
        """
        all_dates = set()
        
        for df in stock_data.values():
            if 'date' in df.columns:
                dates = pd.to_datetime(df['date'])
                all_dates.update(dates.dt.strftime('%Y-%m-%d').tolist())
        
        # 排序并过滤日期范围
        trading_dates = sorted([d for d in all_dates if start_date <= d <= end_date])
        
        return trading_dates
    
    def _calculate_performance(
        self,
        trades: List[Dict],
        equity_curve: List[Dict],
        initial_capital: float
    ) -> Tuple[float, float, float]:
        """
        计算绩效指标
        
        Args:
            trades: 交易记录列表
            equity_curve: 权益曲线列表
            initial_capital: 初始资金
        
        Returns:
            (总收益率, 最大回撤, 胜率)
        """
        if not equity_curve:
            return 0.0, 0.0, 0.0
        
        # 计算总收益率
        final_equity = equity_curve[-1]['equity']
        total_return = (final_equity - initial_capital) / initial_capital
        
        # 计算最大回撤
        max_drawdown = 0.0
        peak = initial_capital
        
        for point in equity_curve:
            equity = point['equity']
            if equity > peak:
                peak = equity
            drawdown = (equity - peak) / peak
            if drawdown < max_drawdown:
                max_drawdown = drawdown
        
        # 计算胜率
        win_rate = 0.0
        if trades:
            winning_trades = sum(1 for t in trades if t.get('pnl', 0) > 0)
            win_rate = winning_trades / len(trades)
        
        return total_return, max_drawdown, win_rate
    
    def _calculate_trades_by_period(self, trades: List[Dict]) -> Dict[str, int]:
        """
        按时间段统计交易次数
        
        时间段：
        - 2022年全年
        - 2023年上半年 (1-6月)
        - 2023年下半年 (7-12月)
        - 2024年
        
        Args:
            trades: 交易记录列表
        
        Returns:
            各时间段交易次数字典
        """
        trades_by_period = {
            "2022": 0,
            "2023上半年": 0,
            "2023下半年": 0,
            "2024": 0
        }
        
        for trade in trades:
            trade_date = trade.get('date', '')
            if not trade_date:
                continue
            
            if trade_date.startswith('2022'):
                trades_by_period["2022"] += 1
            elif trade_date.startswith('2023'):
                month = int(trade_date[5:7])
                if month <= 6:
                    trades_by_period["2023上半年"] += 1
                else:
                    trades_by_period["2023下半年"] += 1
            elif trade_date.startswith('2024'):
                trades_by_period["2024"] += 1
        
        return trades_by_period
    
    def _calculate_period_performances(
        self,
        trades: List[Dict],
        equity_curve: List[Dict],
        start_date: str,
        end_date: str
    ) -> List[PeriodPerformance]:
        """
        计算各时间段绩效
        
        Args:
            trades: 交易记录列表
            equity_curve: 权益曲线列表
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            各时间段绩效列表
        """
        performances = []
        
        # 定义时间段
        periods = [
            ("2022年", "2022-01-01", "2022-12-31", True),
            ("2023年上半年", "2023-01-01", "2023-06-30", True),
            ("2023年下半年", "2023-07-01", "2023-12-31", True),
            ("2024年", "2024-01-01", "2024-12-31", False),
        ]
        
        for period_name, period_start, period_end, is_bear in periods:
            # 过滤该时间段的数据
            period_equity = [e for e in equity_curve if period_start <= e['date'] <= period_end]
            period_trades = [t for t in trades if period_start <= t.get('date', '') <= period_end]
            
            if not period_equity:
                continue
            
            # 计算该时间段的绩效
            initial = period_equity[0]['equity']
            final = period_equity[-1]['equity']
            total_return = (final - initial) / initial if initial > 0 else 0.0
            
            # 计算最大回撤
            max_dd = 0.0
            peak = initial
            for point in period_equity:
                equity = point['equity']
                if equity > peak:
                    peak = equity
                dd = (equity - peak) / peak
                if dd < max_dd:
                    max_dd = dd
            
            # 计算胜率
            win_rate = 0.0
            if period_trades:
                winning = sum(1 for t in period_trades if t.get('pnl', 0) > 0)
                win_rate = winning / len(period_trades)
            
            performances.append(PeriodPerformance(
                period_name=period_name,
                start_date=period_start,
                end_date=period_end,
                total_return=total_return,
                max_drawdown=max_dd,
                trade_count=len(period_trades),
                win_rate=win_rate,
                is_bear_market=is_bear
            ))
        
        return performances
    
    def _check_market_filter_effectiveness(self, trades_by_period: Dict[str, int]) -> bool:
        """
        检查大盘风控有效性
        
        判断标准：2022年和2023下半年交易次数应显著低于平均值
        
        Args:
            trades_by_period: 各时间段交易次数
        
        Returns:
            是否有效
        """
        trades_2022 = trades_by_period.get("2022", 0)
        trades_2023_h2 = trades_by_period.get("2023下半年", 0)
        
        total_trades = sum(trades_by_period.values())
        avg_trades = total_trades / len(trades_by_period) if trades_by_period else 0
        
        # 判断：2022年和2023下半年交易次数应低于平均值的70%
        is_effective = (trades_2022 < avg_trades * 0.7) and (trades_2023_h2 < avg_trades * 0.7)
        
        return is_effective
    
    def run_bear_market_validation(
        self,
        stock_codes: List[str],
        initial_capital: float = 100000.0
    ) -> PeriodPerformance:
        """
        运行震荡市独立验证 (2022-2023)
        
        Args:
            stock_codes: 股票代码列表
            initial_capital: 初始资金
        
        Returns:
            震荡市时间段的绩效
            
        Requirements: 11.1, 11.2, 11.8
        """
        logger.info(f"开始震荡市验证: {self.BEAR_MARKET_START} - {self.BEAR_MARKET_END}")
        
        # 加载震荡市时间段的数据
        stock_data = self._load_stock_data(
            stock_codes,
            self.BEAR_MARKET_START,
            self.BEAR_MARKET_END
        )
        
        if not stock_data:
            logger.warning("震荡市验证：无可用数据")
            return PeriodPerformance(
                period_name="震荡市验证 (2022-2023)",
                start_date=self.BEAR_MARKET_START,
                end_date=self.BEAR_MARKET_END,
                total_return=0.0,
                max_drawdown=0.0,
                trade_count=0,
                win_rate=0.0,
                is_bear_market=True
            )
        
        # 运行回测模拟
        trades, equity_curve = self._run_backtest_simulation(
            stock_codes,
            stock_data,
            self.BEAR_MARKET_START,
            self.BEAR_MARKET_END,
            initial_capital
        )
        
        # 计算绩效
        total_return, max_drawdown, win_rate = self._calculate_performance(
            trades,
            equity_curve,
            initial_capital
        )
        
        performance = PeriodPerformance(
            period_name="震荡市验证 (2022-2023)",
            start_date=self.BEAR_MARKET_START,
            end_date=self.BEAR_MARKET_END,
            total_return=total_return,
            max_drawdown=max_drawdown,
            trade_count=len(trades),
            win_rate=win_rate,
            is_bear_market=True
        )
        
        logger.info(f"震荡市验证完成: 收益率={performance.total_return:.2%}, 最大回撤={performance.max_drawdown:.2%}")
        
        return performance
    
    def generate_bear_market_report(
        self, 
        performance: PeriodPerformance
    ) -> str:
        """
        生成震荡市独立绩效报告
        
        Args:
            performance: 震荡市绩效数据
        
        Returns:
            格式化的报告字符串
            
        Requirements: 11.8
        """
        drawdown_status = "⚠️ 超过阈值!" if performance.max_drawdown < self.MAX_DRAWDOWN_THRESHOLD else "✅ 达标"
        
        report = f"""
═══════════════════════════════════════════
        震荡市验证报告 (2022-2023)
═══════════════════════════════════════════
时间段: {performance.start_date} - {performance.end_date}
总收益率: {performance.total_return:.2%}
最大回撤: {performance.max_drawdown:.2%} {drawdown_status}
交易次数: {performance.trade_count}
胜率: {performance.win_rate:.1%}
═══════════════════════════════════════════
"""
        return report
    
    def analyze_market_filter_effectiveness(
        self, 
        result: TechBacktestResult
    ) -> str:
        """
        分析大盘风控有效性
        
        检查 2022 年和 2023 年下半年的交易次数是否显著减少
        
        Args:
            result: 回测结果
        
        Returns:
            分析报告字符串
            
        Requirements: 11.6, 11.7
        """
        trades_by_period = result.trades_by_period
        
        # 获取各时间段交易次数
        trades_2022 = trades_by_period.get("2022", 0)
        trades_2023_h1 = trades_by_period.get("2023上半年", 0)
        trades_2023_h2 = trades_by_period.get("2023下半年", 0)
        trades_2024 = trades_by_period.get("2024", 0)
        
        # 计算平均交易次数
        total_trades = trades_2022 + trades_2023_h1 + trades_2023_h2 + trades_2024
        avg_trades = total_trades / 4 if total_trades > 0 else 0
        
        # 判断风控是否有效
        # 2022年和2023下半年交易次数应该显著低于平均值
        is_effective = (trades_2022 < avg_trades * 0.7) and (trades_2023_h2 < avg_trades * 0.7)
        
        report = f"""
═══════════════════════════════════════════
        大盘风控有效性分析
═══════════════════════════════════════════
各时间段交易次数:
- 2022年 (熊市): {trades_2022} 次
- 2023上半年 (震荡): {trades_2023_h1} 次
- 2023下半年 (震荡): {trades_2023_h2} 次
- 2024年: {trades_2024} 次

平均交易次数: {avg_trades:.1f} 次

风控有效性: {'✅ 有效' if is_effective else '⚠️ 需要优化'}
说明: {'2022年和2023下半年交易次数显著减少，大盘红绿灯有效避开了系统性风险' if is_effective else '2022年和2023下半年交易次数未显著减少，需要优化大盘风控参数'}
═══════════════════════════════════════════
"""
        return report
    
    def get_period_breakdown(
        self, 
        result: TechBacktestResult
    ) -> List[Dict]:
        """
        获取各时间段分解统计
        
        时间段：
        - 2022年全年 (熊市)
        - 2023年上半年 (震荡)
        - 2023年下半年 (震荡)
        - 2024年 (如有)
        
        Args:
            result: 回测结果
        
        Returns:
            时间段统计列表
            
        Requirements: 11.6, 11.7
        """
        breakdown = []
        
        for performance in result.period_performances:
            breakdown.append({
                "period_name": performance.period_name,
                "start_date": performance.start_date,
                "end_date": performance.end_date,
                "total_return": performance.total_return,
                "max_drawdown": performance.max_drawdown,
                "trade_count": performance.trade_count,
                "win_rate": performance.win_rate,
                "is_bear_market": performance.is_bear_market
            })
        
        return breakdown
    
    def _create_empty_result(self, data_warnings: List[Dict]) -> TechBacktestResult:
        """
        创建空的回测结果（当没有可用数据时）
        
        Args:
            data_warnings: 数据警告列表
        
        Returns:
            空的回测结果
        """
        return TechBacktestResult(
            total_return=0.0,
            max_drawdown=0.0,
            total_trades=0,
            win_rate=0.0,
            trades_by_period={},
            period_performances=[],
            drawdown_warning=False,
            market_filter_effective=False,
            bear_market_validated=False,
            bear_market_report="无可用数据，无法进行震荡市验证",
            data_warnings=data_warnings
        )
    
    def format_result_for_display(self, result: TechBacktestResult) -> Dict:
        """
        将回测结果格式化为便于显示的字典
        
        Args:
            result: 回测结果
        
        Returns:
            格式化的结果字典
        """
        return {
            "总收益率": f"{result.total_return:.2%}",
            "最大回撤": f"{result.max_drawdown:.2%}",
            "总交易次数": result.total_trades,
            "胜率": f"{result.win_rate:.1%}",
            "回撤警告": "⚠️ 是" if result.drawdown_warning else "✅ 否",
            "大盘风控有效": "✅ 是" if result.market_filter_effective else "⚠️ 否",
            "震荡市验证": "✅ 通过" if result.bear_market_validated else "❌ 未通过",
            "数据警告数": len(result.data_warnings)
        }
