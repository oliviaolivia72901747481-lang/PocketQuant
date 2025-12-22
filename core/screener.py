"""
MiniQuant-Lite 选股器模块 (多线程加速版)

基于 Pandas 实现选股筛选逻辑，包含：
- 技术指标筛选（MA, MACD, RSI）
- 流动性过滤（市值、换手率、ST、上市天数）
- 大盘滤网（沪深300 MA20）
- 行业互斥（同行业最多 N 只）
- 两阶段筛选优化（预剪枝 + 多线程精筛）

Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10, 2.11, 2.12, 2.13
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
import pandas as pd
import logging
import concurrent.futures  # 引入并发库
from tqdm import tqdm  # <--- 新增这行进度条插件

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
    max_market_cap: float = float('inf')  # 最大流通市值（不限制，保留大盘股）
    min_turnover_rate: float = 0.02   # 最小换手率（2%）
    max_turnover_rate: float = 0.20   # 最大换手率（20%，放宽以适应放量反弹）
    extreme_turnover_threshold: float = 0.25  # 极端换手率阈值（25%），超过标记警告
    exclude_st: bool = True           # 剔除 ST 股
    min_listing_days: int = 60        # 最小上市天数
    require_ma60_uptrend: bool = False  # 是否要求 MA60 趋势向上（RSI策略不需要）


@dataclass
class VolatilityFilter:
    """
    波动率过滤配置
    
    使用 NATR (Normalized ATR) 过滤波动率异常的股票
    NATR = ATR(14) / Close * 100%
    """
    enabled: bool = True              # 是否启用波动率过滤
    min_natr: float = 2.0             # 最小 NATR（%），低于此值为"织布机"
    max_natr: float = 8.0             # 最大 NATR（%），高于此值为"妖股"
    atr_period: int = 14              # ATR 计算周期


@dataclass
class RiskFilter:
    """
    风险过滤配置
    
    基于近期涨跌幅的风险控制
    """
    enabled: bool = True              # 是否启用风险过滤
    max_5d_gain: float = 0.20         # 5日最大涨幅（20%），超过标记为"追高风险"
    max_5d_loss: float = -0.15        # 5日最大跌幅（-15%），超过标记为"超跌"
    volume_alert_ratio: float = 3.0   # 成交量异常倍数（相对5日均量）


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
class TrendSafetyFilter:
    """
    趋势安全过滤配置
    
    防止在极端下跌趋势中抄底，避免"接飞刀"
    从 SignalGenerator 中提取的隐藏风控，显式化配置
    """
    enabled: bool = True              # 是否启用趋势安全过滤
    ma60_floor_ratio: float = 0.80    # 股价不能跌破 MA60 的 80%
    ma20_floor_ratio: float = 0.85    # 股价不能跌破 MA20 的 85%（更严格的短期保护）


@dataclass
class StrategyPrefilter:
    """
    策略预筛配置
    
    根据不同策略类型进行预筛，提高信号生成效率
    """
    enabled: bool = True              # 是否启用策略预筛
    strategy_type: str = "RSI_REVERSAL"  # 策略类型: RSI_REVERSAL, RSRS, BOLLINGER
    
    # RSI 超卖反弹策略预筛
    rsi_prefilter_enabled: bool = True
    rsi_max_threshold: float = 45.0   # RSI < 45 才有反弹空间
    rsi_min_threshold: float = 10.0   # RSI > 10 避免极端超跌
    
    # RSRS 策略预筛
    min_history_days: int = 100       # 最小历史数据天数（RSRS 需要足够数据）
    
    # 布林带策略预筛
    bollinger_prefilter_enabled: bool = False
    price_below_ma20_ratio: float = 0.98  # 价格低于 MA20 的 98%


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
    # 风险标记
    natr: float = 0.0                 # NATR 波动率（%）
    gain_5d: float = 0.0              # 5日涨跌幅
    volume_ratio: float = 0.0         # 成交量比（相对5日均量）
    risk_warnings: List[str] = field(default_factory=list)  # 风险警告列表
    # 策略预筛指标
    rsi: float = 50.0                 # RSI 值（用于策略预筛）
    history_days: int = 0             # 历史数据天数
    ma60_distance: float = 0.0        # 与 MA60 的距离百分比
    
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
            'in_report_window': self.in_report_window,
            'natr': self.natr,
            'gain_5d': self.gain_5d,
            'volume_ratio': self.volume_ratio,
            'risk_warnings': self.risk_warnings,
            'rsi': self.rsi,
            'history_days': self.history_days,
            'ma60_distance': self.ma60_distance
        }


class Screener:
    """
    选股器（含流动性过滤、大盘滤网、行业互斥、策略预筛）
    
    设计原则：
    - 两阶段筛选优化：先用实时快照预剪枝，再下载历史数据精筛
    - 多线程加速：并行处理历史数据分析
    - 大盘滤网：沪深300 < MA20 时强制空仓
    - 行业互斥：同行业最多 1 只，分散风险
    - 策略预筛：根据策略类型进行针对性预筛
    - 趋势安全：防止在极端下跌趋势中抄底
    
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
        self.volatility_filter = VolatilityFilter()
        self.risk_filter = RiskFilter()
        self.trend_safety_filter = TrendSafetyFilter()    # 新增趋势安全过滤
        self.strategy_prefilter = StrategyPrefilter()     # 新增策略预筛
        
        # 行业缓存（避免重复查询）
        self._industry_cache: Dict[str, str] = {}
    
    def add_condition(self, condition: ScreenerCondition) -> 'Screener':
        """添加筛选条件，支持链式调用"""
        self._conditions.append(condition)
        logger.debug(f"添加筛选条件: {condition.indicator} {condition.operator} {condition.value}")
        return self
    
    def set_liquidity_filter(self, filter_config: LiquidityFilter) -> 'Screener':
        """设置流动性过滤配置"""
        self.liquidity_filter = filter_config
        logger.debug(f"设置流动性过滤: 市值 {filter_config.min_market_cap/1e8:.0f}亿-{filter_config.max_market_cap/1e8:.0f}亿")
        return self
    
    def set_market_filter(self, filter_config: MarketFilter) -> 'Screener':
        """设置大盘滤网配置"""
        self.market_filter = filter_config
        logger.debug(f"设置大盘滤网: {'启用' if filter_config.enabled else '禁用'}")
        return self
    
    def set_industry_diversification(self, config: IndustryDiversification) -> 'Screener':
        """设置行业分散配置"""
        self.industry_diversification = config
        logger.debug(f"设置行业分散: {'启用' if config.enabled else '禁用'}, 同行业最多 {config.max_same_industry} 只")
        return self
    
    def set_trend_safety_filter(self, filter_config: TrendSafetyFilter) -> 'Screener':
        """设置趋势安全过滤配置"""
        self.trend_safety_filter = filter_config
        logger.debug(f"设置趋势安全过滤: {'启用' if filter_config.enabled else '禁用'}")
        return self
    
    def set_strategy_prefilter(self, config: StrategyPrefilter) -> 'Screener':
        """设置策略预筛配置"""
        self.strategy_prefilter = config
        logger.debug(f"设置策略预筛: {'启用' if config.enabled else '禁用'}, 策略类型: {config.strategy_type}")
        return self
    
    def set_volatility_filter(self, filter_config: VolatilityFilter) -> 'Screener':
        """设置波动率过滤配置"""
        self.volatility_filter = filter_config
        logger.debug(f"设置波动率过滤: {'启用' if filter_config.enabled else '禁用'}, NATR {filter_config.min_natr}%-{filter_config.max_natr}%")
        return self
    
    def set_risk_filter(self, filter_config: RiskFilter) -> 'Screener':
        """设置风险过滤配置"""
        self.risk_filter = filter_config
        logger.debug(f"设置风险过滤: {'启用' if filter_config.enabled else '禁用'}")
        return self
    
    def clear_conditions(self) -> None:
        """清空所有筛选条件"""
        self._conditions.clear()
        logger.debug("已清空所有筛选条件")
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算技术指标 (MA, MACD, RSI, Volume)
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
        
        # 添加价格列别名
        result['price'] = close
        
        logger.debug(f"技术指标计算完成，共 {len(result)} 条记录")
        return result

    def _check_market_condition(self) -> bool:
        """检查大盘环境（沪深300均线滤网）"""
        if not self.market_filter.enabled:
            logger.debug("大盘滤网已禁用")
            return True
        
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
                logger.warning("无法获取沪深300指数数据，默认允许交易")
                return True
            
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
        """检查是否为 ST 股票"""
        if name is None:
            return False
        return 'ST' in str(name).upper() or '*ST' in str(name).upper()
    
    def _check_listing_days(self, code: str, min_days: int = 60) -> bool:
        """检查上市天数是否满足要求"""
        try:
            import akshare as ak
            df = ak.stock_individual_info_em(symbol=code)
            
            if df is None or df.empty:
                return True
            
            listing_date_row = df[df['item'] == '上市时间']
            if listing_date_row.empty:
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
        """检查 MA60 趋势是否向上"""
        if df is None or df.empty:
            return False
        
        if 'close' not in df.columns:
            return False
        
        if len(df) < 61:
            return False
        
        close = df['close'].astype(float)
        
        ma60_today = close.tail(60).mean()
        ma60_yesterday = close.iloc[-61:-1].mean()
        
        return ma60_today > ma60_yesterday
    
    def _get_stock_industry(self, code: str) -> str:
        """获取股票所属行业（带缓存）"""
        if code in self._industry_cache:
            return self._industry_cache[code]
        
        try:
            import akshare as ak
            df = ak.stock_individual_info_em(symbol=code)
            
            if df is None or df.empty:
                self._industry_cache[code] = "未知"
                return "未知"
            
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
    
    def _apply_industry_diversification(self, results: List[ScreenerResult]) -> List[ScreenerResult]:
        """
        应用行业互斥逻辑 (优化版：按换手率优胜劣汰)
        
        逻辑：
        1. 先将所有入选股票按【换手率从高到低】排序。
        2. 遍历排序后的列表，每个行业只取前 N 名。
        3. 这样确保留下的那一只，一定是该行业当前最活跃的龙头。
        """
        # 1. 如果没开启互斥，或者结果为空，直接返回
        if not self.industry_diversification.enabled:
            return results
        
        if not results:
            return results
        
        # =======================================================
        # 核心修改：排序
        # key=lambda x: x.turnover_rate  --> 指定按换手率排
        # reverse=True                   --> 降序（大的在前）
        # =======================================================
        results.sort(key=lambda x: x.turnover_rate, reverse=True)
        
        industry_count: Dict[str, int] = {}
        diversified_results: List[ScreenerResult] = []
        max_per_industry = self.industry_diversification.max_same_industry
        
        for result in results:
            industry = result.industry
            
            # 某些数据源可能返回 '未知' 行业，建议不限制或单独处理
            # 这里选择不限制'未知'行业，或者你可以视作同一个行业处理
            if industry == '未知': 
                diversified_results.append(result)
                continue

            current_count = industry_count.get(industry, 0)
            
            if current_count < max_per_industry:
                diversified_results.append(result)
                industry_count[industry] = current_count + 1
            else:
                # 因为已经排过序了，所以被剔除的一定是换手率较低的
                logger.debug(f"剔除股票 {result.code} ({industry}): 换手率 {result.turnover_rate:.2f}% 排名靠后，已达行业上限")
        
        # 统计剔除数量
        removed_count = len(results) - len(diversified_results)
        if removed_count > 0:
            logger.info(f"行业互斥: 按换手率优胜劣汰，剔除 {removed_count} 只较弱股票，保留 {len(diversified_results)} 只活跃龙头")
        
        return diversified_results

    def _get_lookback_date(self, days: int) -> str:
        lookback_date = date.today() - timedelta(days=days)
        return lookback_date.strftime('%Y-%m-%d')
    
    def _get_today(self) -> str:
        return date.today().strftime('%Y-%m-%d')
    
    def _check_report_window(self, code: str, window_days: int = 3) -> bool:
        """
        检查是否处于财报披露窗口期（优化版：复用实例）
        """
        try:
            # 性能优化：缓存 ReportChecker 实例，避免重复初始化
            if not hasattr(self, '_cached_report_checker'):
                from core.report_checker import ReportChecker
                self._cached_report_checker = ReportChecker(window_days=window_days)
            
            in_window, warning = self._cached_report_checker.check_report_window(code)
            
            if in_window and warning:
                logger.info(f"股票 {code} {warning}")
            
            return in_window
            
        except Exception as e:
            logger.debug(f"检查财报窗口期失败: {code}, {e}")
            return False
    
    def _check_technical_conditions(self, df: pd.DataFrame) -> bool:
        """检查技术指标条件"""
        if not self._conditions:
            return True
        
        if df is None or df.empty:
            return False
        
        df_with_indicators = self.calculate_indicators(df)
        
        if df_with_indicators.empty:
            return False
        
        latest = df_with_indicators.iloc[-1]
        
        for condition in self._conditions:
            indicator = condition.indicator.lower()
            
            if indicator not in latest.index:
                logger.warning(f"指标 {indicator} 不存在，跳过该条件")
                continue
            
            value = latest[indicator]
            
            if pd.isna(value):
                return False
            
            if not self._apply_condition(value, condition):
                logger.debug(f"条件不满足: {indicator}={value:.2f} {condition.operator} {condition.value}")
                return False
        
        return True
    
    def _apply_condition(self, value: float, condition: ScreenerCondition) -> bool:
        op = condition.operator
        target = condition.value
        target2 = condition.value2
        
        if op == '>': return value > target
        elif op == '<': return value < target
        elif op == '>=': return value >= target
        elif op == '<=': return value <= target
        elif op == '==': return abs(value - target) < 1e-6
        elif op == 'between': return target <= value <= target2
        else: return False
    
    def _calculate_natr(self, df: pd.DataFrame) -> float:
        """
        计算 NATR (Normalized Average True Range)
        
        NATR = ATR(14) / Close * 100%
        用于衡量股票波动率，过滤"织布机"和"妖股"
        
        Returns:
            NATR 百分比值，计算失败返回 0.0
        """
        if df is None or df.empty or len(df) < self.volatility_filter.atr_period + 1:
            return 0.0
        
        try:
            high = df['high'].astype(float)
            low = df['low'].astype(float)
            close = df['close'].astype(float)
            
            # 计算 True Range
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            
            # 计算 ATR
            atr = tr.rolling(window=self.volatility_filter.atr_period).mean()
            
            # 计算 NATR (百分比)
            natr = (atr / close) * 100
            
            latest_natr = natr.iloc[-1]
            return float(latest_natr) if not pd.isna(latest_natr) else 0.0
            
        except Exception as e:
            logger.debug(f"计算 NATR 失败: {e}")
            return 0.0
    
    def _calculate_risk_metrics(self, df: pd.DataFrame) -> tuple:
        """
        计算风险指标
        
        Returns:
            (gain_5d, volume_ratio, risk_warnings)
            - gain_5d: 5日涨跌幅（百分比）
            - volume_ratio: 成交量比（相对5日均量）
            - risk_warnings: 风险警告列表
        """
        risk_warnings = []
        gain_5d = 0.0
        volume_ratio = 0.0
        
        if df is None or df.empty or len(df) < 6:
            return gain_5d, volume_ratio, risk_warnings
        
        try:
            close = df['close'].astype(float)
            
            # 计算5日涨跌幅
            if len(close) >= 6:
                price_5d_ago = close.iloc[-6]
                price_today = close.iloc[-1]
                if price_5d_ago > 0:
                    gain_5d = (price_today - price_5d_ago) / price_5d_ago * 100
            
            # 计算成交量比
            if 'volume' in df.columns and len(df) >= 6:
                volume = df['volume'].astype(float)
                vol_ma5 = volume.iloc[-6:-1].mean()  # 前5日均量
                vol_today = volume.iloc[-1]
                if vol_ma5 > 0:
                    volume_ratio = vol_today / vol_ma5
            
            # 生成风险警告
            if self.risk_filter.enabled:
                if gain_5d > self.risk_filter.max_5d_gain * 100:
                    risk_warnings.append(f"追高风险: 5日涨幅 {gain_5d:.1f}%")
                
                if gain_5d < self.risk_filter.max_5d_loss * 100:
                    risk_warnings.append(f"超跌警告: 5日跌幅 {gain_5d:.1f}%")
                
                if volume_ratio > self.risk_filter.volume_alert_ratio:
                    risk_warnings.append(f"放量异常: 成交量是5日均量的 {volume_ratio:.1f} 倍")
            
            # 检查极端换手率
            if hasattr(self.liquidity_filter, 'extreme_turnover_threshold'):
                # 这里 volume_ratio 是成交量比，换手率需要从 snapshot 获取
                pass
            
            return gain_5d, volume_ratio, risk_warnings
            
        except Exception as e:
            logger.debug(f"计算风险指标失败: {e}")
            return gain_5d, volume_ratio, risk_warnings
    
    def _calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> float:
        """
        计算 RSI 指标
        
        用于策略预筛，筛选出 RSI 接近超卖区的股票
        
        Args:
            df: 股票历史数据
            period: RSI 计算周期，默认 14
        
        Returns:
            RSI 值，计算失败返回 50.0（中性值）
        """
        if df is None or df.empty or len(df) < period + 1:
            return 50.0
        
        try:
            close = df['close'].astype(float)
            delta = close.diff()
            
            gain = delta.where(delta > 0, 0)
            loss = (-delta).where(delta < 0, 0)
            
            avg_gain = gain.rolling(window=period).mean()
            avg_loss = loss.rolling(window=period).mean()
            
            # 避免除零
            avg_loss = avg_loss.replace(0, 1e-10)
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            latest_rsi = rsi.iloc[-1]
            return float(latest_rsi) if not pd.isna(latest_rsi) else 50.0
            
        except Exception as e:
            logger.debug(f"计算 RSI 失败: {e}")
            return 50.0
    
    def _calculate_ma60_distance(self, df: pd.DataFrame) -> float:
        """
        计算当前价格与 MA60 的距离百分比
        
        用于趋势安全过滤，防止在极端下跌趋势中抄底
        
        Returns:
            距离百分比，正值表示在 MA60 之上，负值表示在 MA60 之下
        """
        if df is None or df.empty or len(df) < 60:
            return 0.0
        
        try:
            close = df['close'].astype(float)
            ma60 = close.rolling(window=60).mean().iloc[-1]
            current_price = close.iloc[-1]
            
            if ma60 > 0:
                distance = (current_price - ma60) / ma60 * 100
                return float(distance)
            return 0.0
            
        except Exception as e:
            logger.debug(f"计算 MA60 距离失败: {e}")
            return 0.0
    
    def _check_trend_safety(self, df: pd.DataFrame) -> tuple:
        """
        检查趋势安全性
        
        防止在极端下跌趋势中抄底，避免"接飞刀"
        
        Returns:
            (is_safe, warning_message)
            - is_safe: 是否安全
            - warning_message: 警告信息（如果不安全）
        """
        if not self.trend_safety_filter.enabled:
            return True, None
        
        if df is None or df.empty or len(df) < 60:
            return True, None
        
        try:
            close = df['close'].astype(float)
            current_price = close.iloc[-1]
            
            # 检查 MA60 底线
            ma60 = close.rolling(window=60).mean().iloc[-1]
            ma60_floor = ma60 * self.trend_safety_filter.ma60_floor_ratio
            
            if current_price < ma60_floor:
                warning = f"趋势风险: 股价 {current_price:.2f} 跌破 MA60 的 {self.trend_safety_filter.ma60_floor_ratio*100:.0f}% ({ma60_floor:.2f})"
                return False, warning
            
            # 检查 MA20 底线（更严格的短期保护）
            if len(df) >= 20:
                ma20 = close.rolling(window=20).mean().iloc[-1]
                ma20_floor = ma20 * self.trend_safety_filter.ma20_floor_ratio
                
                if current_price < ma20_floor:
                    warning = f"短期趋势风险: 股价 {current_price:.2f} 跌破 MA20 的 {self.trend_safety_filter.ma20_floor_ratio*100:.0f}% ({ma20_floor:.2f})"
                    # 这里只标记警告，不强制剔除
                    logger.debug(warning)
            
            return True, None
            
        except Exception as e:
            logger.debug(f"检查趋势安全性失败: {e}")
            return True, None
    
    def _check_strategy_prefilter(self, df: pd.DataFrame) -> tuple:
        """
        检查策略预筛条件
        
        根据策略类型进行针对性预筛，提高信号生成效率
        
        Returns:
            (pass_filter, rsi_value, history_days)
            - pass_filter: 是否通过预筛
            - rsi_value: RSI 值
            - history_days: 历史数据天数
        """
        if not self.strategy_prefilter.enabled:
            return True, 50.0, len(df) if df is not None else 0
        
        if df is None or df.empty:
            return False, 50.0, 0
        
        history_days = len(df)
        rsi_value = self._calculate_rsi(df)
        
        strategy_type = self.strategy_prefilter.strategy_type
        
        # RSRS 策略：检查历史数据充足性
        if strategy_type == "RSRS":
            if history_days < self.strategy_prefilter.min_history_days:
                logger.debug(f"RSRS 预筛: 历史数据不足 ({history_days} < {self.strategy_prefilter.min_history_days})")
                return False, rsi_value, history_days
        
        # RSI 超卖反弹策略：检查 RSI 是否在合适区间
        if strategy_type == "RSI_REVERSAL" and self.strategy_prefilter.rsi_prefilter_enabled:
            if rsi_value > self.strategy_prefilter.rsi_max_threshold:
                logger.debug(f"RSI 预筛: RSI={rsi_value:.1f} > {self.strategy_prefilter.rsi_max_threshold}，无反弹空间")
                return False, rsi_value, history_days
            
            if rsi_value < self.strategy_prefilter.rsi_min_threshold:
                logger.debug(f"RSI 预筛: RSI={rsi_value:.1f} < {self.strategy_prefilter.rsi_min_threshold}，极端超跌")
                # 极端超跌不剔除，但标记警告
                pass
        
        # 布林带策略：检查价格是否接近下轨
        if strategy_type == "BOLLINGER" and self.strategy_prefilter.bollinger_prefilter_enabled:
            if len(df) >= 20:
                close = df['close'].astype(float)
                ma20 = close.rolling(window=20).mean().iloc[-1]
                current_price = close.iloc[-1]
                
                if current_price > ma20 * self.strategy_prefilter.price_below_ma20_ratio:
                    logger.debug(f"布林带预筛: 价格 {current_price:.2f} 高于 MA20 的 {self.strategy_prefilter.price_below_ma20_ratio*100:.0f}%")
                    return False, rsi_value, history_days
        
        return True, rsi_value, history_days
    
    def _build_screener_result(
        self, 
        code: str, 
        df: pd.DataFrame,
        snapshot_row: Optional[pd.Series] = None
    ) -> Optional[ScreenerResult]:
        """构建筛选结果对象"""
        if df is None or df.empty:
            return None
        
        df_with_indicators = self.calculate_indicators(df)
        if df_with_indicators.empty:
            return None
        
        latest = df_with_indicators.iloc[-1]
        price = float(latest.get('close', 0))
        
        if snapshot_row is not None:
            market_cap = float(snapshot_row.get('market_cap', 0))
            turnover_rate = float(snapshot_row.get('turnover_rate', 0))
            name = str(snapshot_row.get('name', code))
        else:
            market_cap = 0
            turnover_rate = 0
            name = code
        
        ma60_trend = "上升" if self._check_ma60_trend(df) else "下降"
        industry = self._get_stock_industry(code)
        
        indicators = {}
        for col in ['ma5', 'ma10', 'ma20', 'ma60', 'macd', 'rsi']:
            if col in latest.index and not pd.isna(latest[col]):
                indicators[col] = float(latest[col])
        
        in_report_window = self._check_report_window(code)
        
        # 计算波动率和风险指标
        natr = self._calculate_natr(df)
        gain_5d, volume_ratio, risk_warnings = self._calculate_risk_metrics(df)
        
        # 计算策略预筛指标
        rsi = self._calculate_rsi(df)
        history_days = len(df)
        ma60_distance = self._calculate_ma60_distance(df)
        
        # 检查极端换手率并添加警告
        if hasattr(self.liquidity_filter, 'extreme_turnover_threshold'):
            if turnover_rate > self.liquidity_filter.extreme_turnover_threshold * 100:
                risk_warnings.append(f"极端换手: 换手率 {turnover_rate:.1f}% 超过 {self.liquidity_filter.extreme_turnover_threshold*100:.0f}%")
        
        return ScreenerResult(
            code=code,
            name=name,
            price=price,
            market_cap=market_cap,
            turnover_rate=turnover_rate,
            ma60_trend=ma60_trend,
            industry=industry,
            indicators=indicators,
            in_report_window=in_report_window,
            natr=natr,
            gain_5d=gain_5d,
            volume_ratio=volume_ratio,
            risk_warnings=risk_warnings,
            rsi=rsi,
            history_days=history_days,
            ma60_distance=ma60_distance
        )
    
    def screen(self, stock_pool: Optional[List[str]] = None) -> List[ScreenerResult]:
        """
        执行筛选（两阶段优化 + 多线程并发加速）
        
        优化说明：
        1. 保持了原有的两阶段筛选逻辑（预剪枝+精筛）。
        2. 在第二阶段引入 ThreadPoolExecutor，开启 8 个线程并行处理“体检”逻辑。
        3. 大幅减少了网络请求（查财报、查行业）带来的等待时间。
        """
        logger.info("开始执行选股筛选 (多线程加速版)...")
        
        # ========== 第零阶段：大盘滤网检查 ==========
        if not self._check_market_condition():
            logger.warning("大盘环境不佳（沪深300 < MA20），建议空仓观望，返回空列表")
            return []
        
        # ========== 第一阶段：预剪枝 ==========
        snapshot_data: Optional[pd.DataFrame] = None
        
        if stock_pool is None:
            logger.info("第一阶段：获取全市场快照进行预剪枝...")
            
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
            candidate_pool = stock_pool
            logger.info(f"使用指定股票池: {len(candidate_pool)} 只股票")
        
        if not candidate_pool:
            return []
        
        # ========== 第二阶段：精筛 (准备数据) ==========
        logger.info(f"第二阶段：对 {len(candidate_pool)} 只候选股票进行精筛...")
        
        start_date = self._get_lookback_date(1095)
        end_date = self._get_today()
        
        # 注意：这里假设 data_feed.download_batch 已经实现了多线程下载，如果没有，这里仍是串行的
        # 但 screener 自身的逻辑在下面会进行并行加速
        historical_data = self.data_feed.download_batch(
            codes=candidate_pool,
            start_date=start_date,
            end_date=end_date
        )
        
        if not historical_data:
            logger.warning("无法获取历史数据")
            return []
        
        # ========== 第三阶段：多线程并行筛选 (带进度条) ==========
        logger.info(f"启动多线程分析，正在处理 {len(historical_data)} 只股票...")
        results: List[ScreenerResult] = []
        
        # 定义单只股票的处理逻辑（闭包函数）
        def process_single_stock(item):
            code, raw_df = item
            try:
                # 清洗数据
                df = self.data_feed.clean_data(raw_df)
                if df is None or df.empty: return None
                
                # 获取快照行
                snapshot_row = None
                if snapshot_data is not None and not snapshot_data.empty:
                    match = snapshot_data[snapshot_data['code'] == code]
                    if not match.empty: snapshot_row = match.iloc[0]
                
                # 上市天数过滤 (自选池模式补查)
                if stock_pool is not None:
                    if not self._check_listing_days(code, self.liquidity_filter.min_listing_days): return None
                    if snapshot_row is not None and self._check_st_stock(snapshot_row.get('name', '')): return None
                
                # 财报窗口期检查（不再强制剔除，只标记）
                # 注：财报窗口期的股票会在结果中标记 in_report_window=True
                # 由信号生成器决定是否过滤
                
                # 波动率过滤（NATR）- 硬性剔除"织布机"和"妖股"
                if self.volatility_filter.enabled:
                    natr = self._calculate_natr(df)
                    if natr > 0:  # 只有计算成功才过滤
                        if natr < self.volatility_filter.min_natr:
                            logger.debug(f"股票 {code} NATR={natr:.2f}% < {self.volatility_filter.min_natr}%，波动率过低（织布机），剔除")
                            return None
                        if natr > self.volatility_filter.max_natr:
                            logger.debug(f"股票 {code} NATR={natr:.2f}% > {self.volatility_filter.max_natr}%，波动率过高（妖股），剔除")
                            return None
                
                # 趋势安全过滤 - 防止在极端下跌趋势中抄底
                is_trend_safe, trend_warning = self._check_trend_safety(df)
                if not is_trend_safe:
                    logger.debug(f"股票 {code} {trend_warning}，剔除")
                    return None
                
                # 策略预筛 - 根据策略类型进行针对性预筛
                pass_prefilter, rsi_value, history_days = self._check_strategy_prefilter(df)
                if not pass_prefilter:
                    logger.debug(f"股票 {code} 未通过策略预筛，剔除")
                    return None
                
                # MA60 趋势过滤（可选，RSI策略不需要）
                if self.liquidity_filter.require_ma60_uptrend:
                    if not self._check_ma60_trend(df): return None
                
                # 技术指标条件过滤
                if not self._check_technical_conditions(df): return None
                
                # 构建结果
                result = self._build_screener_result(code, df, snapshot_row)
                if result:
                    logger.debug(f"股票 {code} 通过筛选 (RSI={rsi_value:.1f}, 历史天数={history_days})")
                return result
                
            except Exception as e:
                logger.error(f"处理股票 {code} 时出错: {e}")
                return None

        # 使用线程池 + tqdm 进度条
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            # 提交任务
            futures = [executor.submit(process_single_stock, item) for item in historical_data.items()]
            
            # 使用 tqdm 包裹 as_completed，显示进度条
            # ncols=100 控制宽度，desc 是前缀文字
            for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="正在精筛", ncols=100):
                try:
                    res = future.result()
                    if res:
                        results.append(res)
                except Exception:
                    pass

        logger.info(f"精筛完成: {len(results)} 只股票通过")
        
        # ========== 第四阶段：行业互斥 ==========
        final_results = self._apply_industry_diversification(results)
        
        logger.info(f"筛选完成: 最终 {len(final_results)} 只股票")
        
        return final_results
    
    def get_market_status(self) -> Dict[str, Any]:
        """获取当前大盘状态"""
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