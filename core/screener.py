"""
MiniQuant-Lite 选股器模块

基于 Pandas 实现选股筛选逻辑，包含：
- 技术指标筛选（MA, MACD, RSI）
- 流动性过滤（市值、换手率、ST、上市天数）
- 大盘滤网（沪深300 MA20）
- 行业互斥（同行业最多 N 只）
- 两阶段筛选优化（预剪枝 + 精筛）

Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10, 2.11, 2.12, 2.13
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
import pandas as pd
import logging

logger = logging.getLogger(__name__)


@dataclass
class ScreenerCondition:
    """
    筛选条件
    
    用于定义技术指标筛选规则
    """
    indicator: str      # 指标名称（如 'ma5', 'ma60', 'macd', 'rsi', 'price', 'volume'）
    operator: str       # 比较运算符（'>', '<', '>=', '<=', '==', 'between'）
    value: float        # 比较值
    value2: Optional[float] = None  # between 时的第二个值（上限）
    
    def __post_init__(self):
        """验证条件参数"""
        valid_operators = ('>', '<', '>=', '<=', '==', 'between')
        if self.operator not in valid_operators:
            raise ValueError(f"无效的运算符: {self.operator}，支持: {valid_operators}")
        
        if self.operator == 'between' and self.value2 is None:
            raise ValueError("between 运算符需要提供 value2 参数")
        
        if self.operator == 'between' and self.value > self.value2:
            raise ValueError(f"between 条件中 value({self.value}) 应小于等于 value2({self.value2})")


@dataclass
class LiquidityFilter:
    """
    流动性过滤配置
    
    用于过滤流动性不佳的股票，避免买入后无法卖出
    """
    min_market_cap: float = 5e9       # 最小流通市值（50亿）
    max_market_cap: float = 5e10      # 最大流通市值（500亿）
    min_turnover_rate: float = 0.02   # 最小换手率（2%）
    max_turnover_rate: float = 0.15   # 最大换手率（15%）
    exclude_st: bool = True           # 剔除 ST 股
    min_listing_days: int = 60        # 最小上市天数


@dataclass
class MarketFilter:
    """
    大盘滤网配置
    
    当大盘环境不佳时，强制空仓观望，这是小资金的保命符
    """
    enabled: bool = True              # 是否启用大盘滤网
    benchmark_code: str = '000300'    # 基准指数代码（沪深300）
    ma_period: int = 20               # 均线周期
    require_above_ma: bool = True     # 要求指数在均线之上


@dataclass
class IndustryDiversification:
    """
    行业分散配置
    
    避免同一行业持仓过多，分散行业风险
    """
    enabled: bool = True              # 是否启用行业互斥
    max_same_industry: int = 1        # 同一行业最多选几只


@dataclass
class ScreenerResult:
    """
    筛选结果
    
    包含筛选出的股票及其关键指标
    """
    code: str                         # 股票代码
    name: str                         # 股票名称
    price: float                      # 当前价格
    market_cap: float                 # 流通市值
    turnover_rate: float              # 换手率
    ma60_trend: str                   # MA60 趋势（上升/下降）
    industry: str                     # 所属行业
    indicators: Dict[str, float] = field(default_factory=dict)  # 关键指标值
    in_report_window: bool = False    # 是否在财报窗口期
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'code': self.code,
            'name': self.name,
            'price': self.price,
            'market_cap': self.market_cap,
            'turnover_rate': self.turnover_rate,
            'ma60_trend': self.ma60_trend,
            'industry': self.industry,
            'indicators': self.indicators,
            'in_report_window': self.in_report_window
        }


class Screener:
    """
    选股器（含流动性过滤、大盘滤网、行业互斥）
    
    设计原则：
    - 两阶段筛选优化：先用实时快照预剪枝，再下载历史数据精筛
    - 大盘滤网：沪深300 < MA20 时强制空仓
    - 行业互斥：同行业最多 1 只，分散风险
    
    Requirements: 2.1-2.13
    """
    
    def __init__(self, data_feed: 'DataFeed'):
        """
        初始化选股器
        
        Args:
            data_feed: 数据获取模块实例
        """
        self.data_feed = data_feed
        self._conditions: List[ScreenerCondition] = []
        self.liquidity_filter = LiquidityFilter()
        self.market_filter = MarketFilter()
        self.industry_diversification = IndustryDiversification()
        
        # 行业缓存（避免重复查询）
        self._industry_cache: Dict[str, str] = {}
    
    def add_condition(self, condition: ScreenerCondition) -> 'Screener':
        """
        添加筛选条件，支持链式调用
        
        Args:
            condition: 筛选条件
        
        Returns:
            self，支持链式调用
        """
        self._conditions.append(condition)
        logger.debug(f"添加筛选条件: {condition.indicator} {condition.operator} {condition.value}")
        return self
    
    def set_liquidity_filter(self, filter_config: LiquidityFilter) -> 'Screener':
        """
        设置流动性过滤配置
        
        Args:
            filter_config: 流动性过滤配置
        
        Returns:
            self，支持链式调用
        """
        self.liquidity_filter = filter_config
        logger.debug(f"设置流动性过滤: 市值 {filter_config.min_market_cap/1e8:.0f}亿-{filter_config.max_market_cap/1e8:.0f}亿")
        return self
    
    def set_market_filter(self, filter_config: MarketFilter) -> 'Screener':
        """
        设置大盘滤网配置
        
        Args:
            filter_config: 大盘滤网配置
        
        Returns:
            self，支持链式调用
        """
        self.market_filter = filter_config
        logger.debug(f"设置大盘滤网: {'启用' if filter_config.enabled else '禁用'}")
        return self
    
    def set_industry_diversification(self, config: IndustryDiversification) -> 'Screener':
        """
        设置行业分散配置
        
        Args:
            config: 行业分散配置
        
        Returns:
            self，支持链式调用
        """
        self.industry_diversification = config
        logger.debug(f"设置行业分散: {'启用' if config.enabled else '禁用'}, 同行业最多 {config.max_same_industry} 只")
        return self
    
    def clear_conditions(self) -> None:
        """清空所有筛选条件"""
        self._conditions.clear()
        logger.debug("已清空所有筛选条件")
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算技术指标
        
        支持指标:
        - MA5, MA10, MA20, MA60: 移动平均线
        - MACD: MACD 指标（macd, signal, hist）
        - RSI: 相对强弱指标
        - volume_ma5: 5日成交量均值
        
        Args:
            df: 包含 OHLCV 数据的 DataFrame
        
        Returns:
            添加了技术指标列的 DataFrame
            
        Requirements: 2.2
        """
        if df is None or df.empty:
            return pd.DataFrame()
        
        result = df.copy()
        
        # 确保有 close 列
        if 'close' not in result.columns:
            logger.error("数据缺少 close 列，无法计算技术指标")
            return result
        
        close = result['close']
        
        # 计算移动平均线
        for period in [5, 10, 20, 60]:
            col_name = f'ma{period}'
            result[col_name] = close.rolling(window=period).mean()
        
        # 计算 MACD
        # MACD = EMA12 - EMA26
        # Signal = EMA9(MACD)
        # Histogram = MACD - Signal
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        result['macd'] = ema12 - ema26
        result['macd_signal'] = result['macd'].ewm(span=9, adjust=False).mean()
        result['macd_hist'] = result['macd'] - result['macd_signal']
        
        # 计算 RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / avg_loss.replace(0, float('inf'))
        result['rsi'] = 100 - (100 / (1 + rs))
        
        # 计算成交量均值
        if 'volume' in result.columns:
            result['volume_ma5'] = result['volume'].rolling(window=5).mean()
        
        # 添加价格列别名（方便条件筛选）
        result['price'] = close
        
        logger.debug(f"技术指标计算完成，共 {len(result)} 条记录")
        return result

    
    def _check_market_condition(self) -> bool:
        """
        检查大盘环境（沪深300均线滤网）
        
        规则：沪深300指数 > MA20 时，大盘环境健康，允许开仓
        这是小资金的保命符，大盘不好时强制空仓
        
        Returns:
            True 表示大盘环境健康，允许交易
            
        Requirements: 2.11
        """
        if not self.market_filter.enabled:
            logger.debug("大盘滤网已禁用")
            return True
        
        try:
            import akshare as ak
            
            # 获取沪深300指数数据
            end_date = date.today()
            start_date = end_date - timedelta(days=60)  # 获取足够的数据计算 MA20
            
            df = ak.index_zh_a_hist(
                symbol=self.market_filter.benchmark_code,
                period='daily',
                start_date=start_date.strftime('%Y%m%d'),
                end_date=end_date.strftime('%Y%m%d')
            )
            
            if df is None or df.empty:
                logger.warning("无法获取沪深300指数数据，默认允许交易")
                return True
            
            # 计算 MA20
            close_col = '收盘' if '收盘' in df.columns else 'close'
            if close_col not in df.columns:
                logger.warning(f"沪深300数据缺少收盘价列，可用列: {df.columns.tolist()}")
                return True
            
            close_prices = df[close_col].astype(float)
            ma_period = self.market_filter.ma_period
            
            if len(close_prices) < ma_period:
                logger.warning(f"沪深300数据不足 {ma_period} 天，默认允许交易")
                return True
            
            ma20 = close_prices.rolling(window=ma_period).mean().iloc[-1]
            current_price = close_prices.iloc[-1]
            
            is_healthy = current_price > ma20
            
            if is_healthy:
                logger.info(f"大盘环境健康: 沪深300 {current_price:.2f} > MA{ma_period} {ma20:.2f}")
            else:
                logger.warning(f"大盘环境不佳: 沪深300 {current_price:.2f} < MA{ma_period} {ma20:.2f}，建议空仓观望")
            
            return is_healthy
            
        except Exception as e:
            logger.error(f"检查大盘环境失败: {e}，默认允许交易")
            return True
    
    def _check_st_stock(self, name: str) -> bool:
        """
        检查是否为 ST 股票
        
        Args:
            name: 股票名称
        
        Returns:
            True 表示是 ST 股票，应剔除
            
        Requirements: 2.8
        """
        if name is None:
            return False
        return 'ST' in str(name).upper() or '*ST' in str(name).upper()
    
    def _check_listing_days(self, code: str, min_days: int = 60) -> bool:
        """
        检查上市天数是否满足要求
        
        Args:
            code: 股票代码
            min_days: 最小上市天数
        
        Returns:
            True 表示满足要求（上市天数 >= min_days）
            
        Requirements: 2.9
        """
        try:
            import akshare as ak
            
            # 获取股票基本信息
            df = ak.stock_individual_info_em(symbol=code)
            
            if df is None or df.empty:
                logger.warning(f"无法获取股票 {code} 的基本信息，默认通过")
                return True
            
            # 查找上市日期
            listing_date_row = df[df['item'] == '上市时间']
            if listing_date_row.empty:
                logger.warning(f"股票 {code} 无上市时间信息，默认通过")
                return True
            
            listing_date_str = listing_date_row['value'].iloc[0]
            listing_date = datetime.strptime(str(listing_date_str), '%Y%m%d').date()
            
            days_since_listing = (date.today() - listing_date).days
            
            if days_since_listing < min_days:
                logger.debug(f"股票 {code} 上市仅 {days_since_listing} 天，不满足 {min_days} 天要求")
                return False
            
            return True
            
        except Exception as e:
            logger.warning(f"检查股票 {code} 上市天数失败: {e}，默认通过")
            return True
    
    def _check_ma60_trend(self, df: pd.DataFrame) -> bool:
        """
        检查 MA60 趋势是否向上
        
        规则: MA60(今日) > MA60(昨日)
        均线向上表示趋势健康，先天胜率高
        
        Args:
            df: 包含 OHLCV 数据的 DataFrame
        
        Returns:
            True 表示均线向上
            
        Requirements: 2.10
        """
        if df is None or df.empty:
            return False
        
        if 'close' not in df.columns:
            logger.warning("数据缺少 close 列，无法检查 MA60 趋势")
            return False
        
        if len(df) < 61:
            logger.debug(f"数据不足 61 天（当前 {len(df)} 天），无法计算 MA60 趋势")
            return False
        
        close = df['close'].astype(float)
        
        # 计算今日和昨日的 MA60
        ma60_today = close.tail(60).mean()
        ma60_yesterday = close.iloc[-61:-1].mean()
        
        is_uptrend = ma60_today > ma60_yesterday
        
        if is_uptrend:
            logger.debug(f"MA60 趋势向上: {ma60_today:.2f} > {ma60_yesterday:.2f}")
        else:
            logger.debug(f"MA60 趋势向下: {ma60_today:.2f} <= {ma60_yesterday:.2f}")
        
        return is_uptrend
    
    def _get_stock_industry(self, code: str) -> str:
        """
        获取股票所属行业
        
        使用 AkShare 获取行业分类，结果会缓存
        
        Args:
            code: 股票代码
        
        Returns:
            行业名称，获取失败时返回 "未知"
        """
        # 检查缓存
        if code in self._industry_cache:
            return self._industry_cache[code]
        
        try:
            import akshare as ak
            
            # 获取股票基本信息
            df = ak.stock_individual_info_em(symbol=code)
            
            if df is None or df.empty:
                self._industry_cache[code] = "未知"
                return "未知"
            
            # 查找行业信息
            industry_row = df[df['item'] == '行业']
            if industry_row.empty:
                self._industry_cache[code] = "未知"
                return "未知"
            
            industry = str(industry_row['value'].iloc[0])
            self._industry_cache[code] = industry
            logger.debug(f"股票 {code} 所属行业: {industry}")
            return industry
            
        except Exception as e:
            logger.warning(f"获取股票 {code} 行业信息失败: {e}")
            self._industry_cache[code] = "未知"
            return "未知"
    
    def _apply_industry_diversification(
        self, 
        results: List[ScreenerResult]
    ) -> List[ScreenerResult]:
        """
        应用行业互斥逻辑
        
        同一行业最多保留 N 只股票，避免行业集中风险
        
        Args:
            results: 初步筛选结果
        
        Returns:
            行业分散后的结果
            
        Requirements: 2.12
        """
        if not self.industry_diversification.enabled:
            logger.debug("行业互斥已禁用")
            return results
        
        if not results:
            return results
        
        industry_count: Dict[str, int] = {}
        diversified_results: List[ScreenerResult] = []
        max_per_industry = self.industry_diversification.max_same_industry
        
        for result in results:
            industry = result.industry
            current_count = industry_count.get(industry, 0)
            
            if current_count < max_per_industry:
                diversified_results.append(result)
                industry_count[industry] = current_count + 1
                logger.debug(f"保留股票 {result.code} ({industry}): {current_count + 1}/{max_per_industry}")
            else:
                logger.debug(f"剔除股票 {result.code} ({industry}): 已达行业上限 {max_per_industry}")
        
        removed_count = len(results) - len(diversified_results)
        if removed_count > 0:
            logger.info(f"行业互斥: 剔除 {removed_count} 只股票，保留 {len(diversified_results)} 只")
        
        return diversified_results

    
    def _get_lookback_date(self, days: int) -> str:
        """
        获取回溯日期
        
        Args:
            days: 回溯天数
        
        Returns:
            日期字符串 'YYYY-MM-DD'
        """
        lookback_date = date.today() - timedelta(days=days)
        return lookback_date.strftime('%Y-%m-%d')
    
    def _get_today(self) -> str:
        """
        获取今日日期
        
        Returns:
            日期字符串 'YYYY-MM-DD'
        """
        return date.today().strftime('%Y-%m-%d')
    
    def _check_report_window(self, code: str, window_days: int = 3) -> bool:
        """
        检查是否处于财报披露窗口期
        
        Args:
            code: 股票代码
            window_days: 窗口期天数（前后各 N 天）
        
        Returns:
            True 表示在财报窗口期，应剔除
            
        Requirements: 10.1, 10.2
        """
        try:
            from core.report_checker import ReportChecker
            
            checker = ReportChecker(window_days=window_days)
            in_window, warning = checker.check_report_window(code)
            
            if in_window and warning:
                logger.info(f"股票 {code} {warning}")
            
            return in_window
            
        except Exception as e:
            logger.debug(f"检查财报窗口期失败: {code}, {e}")
            return False
    
    def _check_technical_conditions(self, df: pd.DataFrame) -> bool:
        """
        检查技术指标条件
        
        Args:
            df: 包含技术指标的 DataFrame
        
        Returns:
            True 表示满足所有技术条件
        """
        if not self._conditions:
            return True
        
        if df is None or df.empty:
            return False
        
        # 计算技术指标
        df_with_indicators = self.calculate_indicators(df)
        
        if df_with_indicators.empty:
            return False
        
        # 获取最新一行数据
        latest = df_with_indicators.iloc[-1]
        
        for condition in self._conditions:
            indicator = condition.indicator.lower()
            
            # 检查指标是否存在
            if indicator not in latest.index:
                logger.warning(f"指标 {indicator} 不存在，跳过该条件")
                continue
            
            value = latest[indicator]
            
            # 处理 NaN 值
            if pd.isna(value):
                logger.debug(f"指标 {indicator} 值为 NaN，条件不满足")
                return False
            
            # 应用条件
            if not self._apply_condition(value, condition):
                logger.debug(f"条件不满足: {indicator}={value:.2f} {condition.operator} {condition.value}")
                return False
        
        return True
    
    def _apply_condition(self, value: float, condition: ScreenerCondition) -> bool:
        """
        应用单个筛选条件
        
        Args:
            value: 指标值
            condition: 筛选条件
        
        Returns:
            True 表示满足条件
        """
        op = condition.operator
        target = condition.value
        target2 = condition.value2
        
        if op == '>':
            return value > target
        elif op == '<':
            return value < target
        elif op == '>=':
            return value >= target
        elif op == '<=':
            return value <= target
        elif op == '==':
            return abs(value - target) < 1e-6
        elif op == 'between':
            return target <= value <= target2
        else:
            logger.warning(f"未知运算符: {op}")
            return False
    
    def _build_screener_result(
        self, 
        code: str, 
        df: pd.DataFrame,
        snapshot_row: Optional[pd.Series] = None
    ) -> Optional[ScreenerResult]:
        """
        构建筛选结果对象
        
        Args:
            code: 股票代码
            df: 历史数据 DataFrame
            snapshot_row: 快照数据行（可选）
        
        Returns:
            ScreenerResult 或 None
        """
        if df is None or df.empty:
            return None
        
        # 计算技术指标
        df_with_indicators = self.calculate_indicators(df)
        if df_with_indicators.empty:
            return None
        
        latest = df_with_indicators.iloc[-1]
        
        # 获取基本信息
        price = float(latest.get('close', 0))
        
        # 从快照获取市值和换手率，或使用默认值
        if snapshot_row is not None:
            market_cap = float(snapshot_row.get('market_cap', 0))
            turnover_rate = float(snapshot_row.get('turnover_rate', 0))
            name = str(snapshot_row.get('name', code))
        else:
            market_cap = 0
            turnover_rate = 0
            name = code
        
        # 判断 MA60 趋势
        ma60_trend = "上升" if self._check_ma60_trend(df) else "下降"
        
        # 获取行业
        industry = self._get_stock_industry(code)
        
        # 收集关键指标
        indicators = {}
        for col in ['ma5', 'ma10', 'ma20', 'ma60', 'macd', 'rsi']:
            if col in latest.index and not pd.isna(latest[col]):
                indicators[col] = float(latest[col])
        
        # 检查财报窗口期
        in_report_window = self._check_report_window(code)
        
        return ScreenerResult(
            code=code,
            name=name,
            price=price,
            market_cap=market_cap,
            turnover_rate=turnover_rate,
            ma60_trend=ma60_trend,
            industry=industry,
            indicators=indicators,
            in_report_window=in_report_window
        )
    
    def screen(self, stock_pool: Optional[List[str]] = None) -> List[ScreenerResult]:
        """
        执行筛选（两阶段优化：预剪枝 + 精筛）
        
        性能优化关键：
        - 第一阶段：用实时快照数据预剪枝（1-2秒，5000只→100-300只）
        - 第二阶段：对候选池下载历史数据并精筛（几十秒）
        - 总耗时从"几十分钟"降到"1分钟内"
        
        筛选流程：
        ┌─────────────────────────────────────────────────────────┐
        │ 第一阶段：预剪枝（基于实时快照，无需下载历史数据）        │
        │ 0. 大盘滤网检查（沪深300 > MA20）                        │
        │ 1. 流通市值过滤（50亿-500亿）                            │
        │ 2. 换手率过滤（2%-15%）                                  │
        │ 3. 剔除 ST 股票                                          │
        │ → 生成 candidate_pool（约 100-300 只）                   │
        └─────────────────────────────────────────────────────────┘
                                    ↓
        ┌─────────────────────────────────────────────────────────┐
        │ 第二阶段：精筛（对 candidate_pool 下载历史数据）         │
        │ 4. 下载候选池历史数据                                    │
        │ 5. 上市天数过滤                                          │
        │ 6. 财报窗口期过滤                                        │
        │ 7. MA60 趋势过滤（均线向上）                             │
        │ 8. 技术指标条件过滤（MACD、RSI 等）                      │
        │ 9. 行业互斥（同行业最多 1 只）                           │
        └─────────────────────────────────────────────────────────┘
        
        Args:
            stock_pool: 股票代码列表（可选，None 时使用全市场预剪枝）
        
        Returns:
            符合条件的股票列表
            
        Requirements: 2.4, 2.5, 2.13
        """
        logger.info("开始执行选股筛选...")
        
        # ========== 第零阶段：大盘滤网检查 ==========
        if not self._check_market_condition():
            logger.warning("大盘环境不佳（沪深300 < MA20），建议空仓观望，返回空列表")
            return []
        
        # ========== 第一阶段：预剪枝 ==========
        snapshot_data: Optional[pd.DataFrame] = None
        
        if stock_pool is None:
            # 使用全市场快照进行预剪枝
            logger.info("第一阶段：获取全市场快照进行预剪枝...")
            
            # 将 LiquidityFilter 转换为 data_feed 使用的格式
            from core.data_feed import LiquidityFilter as DFLiquidityFilter
            df_filter = DFLiquidityFilter(
                min_market_cap=self.liquidity_filter.min_market_cap,
                max_market_cap=self.liquidity_filter.max_market_cap,
                min_turnover_rate=self.liquidity_filter.min_turnover_rate,
                max_turnover_rate=self.liquidity_filter.max_turnover_rate,
                exclude_st=self.liquidity_filter.exclude_st,
                min_listing_days=self.liquidity_filter.min_listing_days
            )
            
            snapshot_data = self.data_feed.get_market_snapshot(liquidity_filter=df_filter)
            
            if snapshot_data is None or snapshot_data.empty:
                logger.warning("预剪枝后无候选股票")
                return []
            
            candidate_pool = snapshot_data['code'].tolist()
            logger.info(f"预剪枝完成: {len(candidate_pool)} 只候选股票")
        else:
            # 使用指定股票池
            candidate_pool = stock_pool
            logger.info(f"使用指定股票池: {len(candidate_pool)} 只股票")
        
        if not candidate_pool:
            logger.warning("候选池为空")
            return []
        
        # ========== 第二阶段：精筛 ==========
        logger.info(f"第二阶段：对 {len(candidate_pool)} 只候选股票进行精筛...")
        
        # 下载候选池历史数据（需要 90 天数据来计算 MA60 + 缓冲）
        start_date = self._get_lookback_date(90)
        end_date = self._get_today()
        
        historical_data = self.data_feed.download_batch(
            codes=candidate_pool,
            start_date=start_date,
            end_date=end_date
        )
        
        if not historical_data:
            logger.warning("无法获取历史数据")
            return []
        
        results: List[ScreenerResult] = []
        
        for code, raw_df in historical_data.items():
            # 清洗数据
            df = self.data_feed.clean_data(raw_df)
            
            if df is None or df.empty:
                logger.debug(f"股票 {code} 数据清洗后为空，跳过")
                continue
            
            # 获取快照数据行（如果有）
            snapshot_row = None
            if snapshot_data is not None and not snapshot_data.empty:
                matching = snapshot_data[snapshot_data['code'] == code]
                if not matching.empty:
                    snapshot_row = matching.iloc[0]
            
            # 5. 上市天数过滤（如果使用指定股票池，需要额外检查）
            if stock_pool is not None:
                if not self._check_listing_days(code, self.liquidity_filter.min_listing_days):
                    logger.debug(f"股票 {code} 上市天数不足，跳过")
                    continue
                
                # 检查 ST
                if snapshot_row is not None:
                    name = snapshot_row.get('name', '')
                    if self._check_st_stock(name):
                        logger.debug(f"股票 {code} 是 ST 股票，跳过")
                        continue
            
            # 6. 财报窗口期过滤
            if self._check_report_window(code):
                logger.debug(f"股票 {code} 处于财报窗口期，跳过")
                continue
            
            # 7. MA60 趋势过滤
            if not self._check_ma60_trend(df):
                logger.debug(f"股票 {code} MA60 趋势向下，跳过")
                continue
            
            # 8. 技术指标条件过滤
            if not self._check_technical_conditions(df):
                logger.debug(f"股票 {code} 不满足技术指标条件，跳过")
                continue
            
            # 构建结果
            result = self._build_screener_result(code, df, snapshot_row)
            if result:
                results.append(result)
                logger.debug(f"股票 {code} 通过所有筛选条件")
        
        logger.info(f"精筛完成: {len(results)} 只股票通过技术指标筛选")
        
        # 9. 行业互斥
        final_results = self._apply_industry_diversification(results)
        
        logger.info(f"筛选完成: 最终 {len(final_results)} 只股票")
        
        return final_results
    
    def get_market_status(self) -> Dict[str, Any]:
        """
        获取当前大盘状态
        
        Returns:
            包含大盘状态信息的字典
        """
        try:
            import akshare as ak
            
            end_date = date.today()
            start_date = end_date - timedelta(days=60)
            
            df = ak.index_zh_a_hist(
                symbol=self.market_filter.benchmark_code,
                period='daily',
                start_date=start_date.strftime('%Y%m%d'),
                end_date=end_date.strftime('%Y%m%d')
            )
            
            if df is None or df.empty:
                return {'status': 'unknown', 'message': '无法获取大盘数据'}
            
            close_col = '收盘' if '收盘' in df.columns else 'close'
            close_prices = df[close_col].astype(float)
            
            ma_period = self.market_filter.ma_period
            ma20 = close_prices.rolling(window=ma_period).mean().iloc[-1]
            current_price = close_prices.iloc[-1]
            
            is_healthy = current_price > ma20
            
            return {
                'status': 'healthy' if is_healthy else 'unhealthy',
                'benchmark_code': self.market_filter.benchmark_code,
                'current_price': current_price,
                f'ma{ma_period}': ma20,
                'is_above_ma': is_healthy,
                'message': '大盘环境健康，允许交易' if is_healthy else '大盘环境不佳，建议空仓观望'
            }
            
        except Exception as e:
            return {'status': 'error', 'message': f'获取大盘状态失败: {e}'}
