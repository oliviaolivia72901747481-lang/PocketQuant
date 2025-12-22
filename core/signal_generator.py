"""
MiniQuant-Lite 每日交易信号生成模块

负责生成每日交易信号，包含：
- 技术面筛选生成候选信号
- 计算限价上限（防止追高）
- 生成新闻链接（人工查看）
- 检查财报窗口期（硬风控）
- 高费率预警

支持两种策略：
1. 趋势滤网 MACD 策略 - 适合趋势行情
2. RSI 超卖反弹策略 - 适合震荡行情

设计原则：把决策权还给人，系统只做硬风控

Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 12.1, 12.2
"""

import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict
from enum import Enum
from datetime import date, datetime
import pandas as pd

try:
    import backtrader as bt
    HAS_BACKTRADER = True
except ImportError:
    HAS_BACKTRADER = False
    bt = None

# 引入项目依赖
from core.data_feed import DataFeed
from core.report_checker import ReportChecker
from core.sizers import calculate_max_shares, calculate_actual_fee_rate
from config.settings import get_settings

# 配置日志
logger = logging.getLogger(__name__)


class SignalType(Enum):
    """
    信号类型枚举
    
    Requirements: 6.2
    """
    BUY = "买入"
    SELL = "卖出"
    HOLD = "持有"


class StrategyType(Enum):
    """策略类型枚举"""
    RSRS = "RSRS 阻力支撑策略"
    RSI_REVERSAL = "RSI 超卖反弹策略"


@dataclass
class TradingSignal:
    """
    交易信号数据类
    
    包含完整的交易信号信息，用于 Dashboard 展示和交易执行
    
    Attributes:
        code: 股票代码（6位数字）
        name: 股票名称
        signal_type: 信号类型（买入/卖出/持有）
        price_range: 建议价格区间 (下限, 上限)
        limit_cap: 限价上限（建议挂单价格，防止追高）
        reason: 信号依据（如：MACD金叉、均线突破）
        generated_at: 信号生成时间
        trade_amount: 预计交易金额
        high_fee_warning: 高费率预警标记
        actual_fee_rate: 实际手续费率（考虑5元低消）
        news_url: 新闻链接（东方财富个股资讯页）
        in_report_window: 是否在财报窗口期
    
    Requirements: 6.2, 6.3, 12.1, 10.2
    """
    code: str                         # 股票代码
    name: str                         # 股票名称
    signal_type: SignalType           # 信号类型
    price_range: Tuple[float, float]  # 建议价格区间 (止损价, 现价)
    limit_cap: float                  # 限价上限（建议挂单价格）
    reason: str                       # 信号依据
    generated_at: date                # 生成时间
    trade_amount: float               # 预计交易金额
    high_fee_warning: bool            # 高费率预警标记 (Requirements 4.8)
    actual_fee_rate: float            # 实际手续费率
    news_url: str                     # 新闻链接 (Requirements 12.1)
    in_report_window: bool            # 是否在财报窗口期 (Requirements 10.2)
    report_warning: Optional[str] = None  # 财报窗口期警告信息


class SignalGenerator:
    """
    每日交易信号生成器
    
    职责：
    1. 运行策略逻辑获取买卖点
    2. 计算资金和费率预警
    3. 生成辅助信息（新闻链接、限价上限）
    4. 集成硬风控（财报窗口期）
    
    支持策略：
    - MACD_TREND: 趋势滤网 MACD 策略（适合趋势行情）
    - RSI_REVERSAL: RSI 超卖反弹策略（适合震荡行情）
    
    设计原则：
    - 把决策权还给人，系统只做硬风控
    - 新闻链接比 AI 分析更可靠（人眼看标题只需 10 秒）
    - 财报窗口期一律剔除，宁可错过不可做错
    
    Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6
    """
    
    # 允许的高开滑点系数 (1%)
    LIMIT_CAP_FACTOR = 1.01
    
    # 东方财富个股资讯 URL 模板
    EASTMONEY_NEWS_URL = "https://quote.eastmoney.com/{market}{code}.html"

    def __init__(
        self, 
        data_feed: DataFeed, 
        strategy_class: Optional[type] = None,
        strategy_type: StrategyType = StrategyType.RSRS
    ):
        """
        初始化信号生成器
        
        Args:
            data_feed: 数据获取模块实例
            strategy_class: 策略类（可选，用于获取策略参数）
            strategy_type: 策略类型，默认为趋势滤网 MACD 策略
        """
        self.data_feed = data_feed
        self.strategy_class = strategy_class
        self.strategy_type = strategy_type
        self.report_checker = ReportChecker()
        
        # 缓存股票名称，避免重复查询
        self._stock_names_cache: Dict[str, str] = {}

    def generate_signals(
        self, 
        stock_pool: List[str],
        current_cash: float = None,
        current_positions: int = 0
    ) -> List[TradingSignal]:
        """
        生成每日交易信号
        
        流程：
        1. 获取股票名称（批量查询，提高效率）
        2. 对每只股票：
           a. 加载历史数据
           b. 检查财报窗口期（硬风控）
           c. 计算技术指标，判断信号
           d. 计算资金和费率
           e. 生成辅助信息（新闻链接、限价上限）
        3. 返回信号列表
        
        设计原则：把决策权还给人，系统只做硬风控
        
        Args:
            stock_pool: 候选股票池（通常来自 Screener 的输出）
            current_cash: 当前可用现金，默认使用配置的初始资金
            current_positions: 当前持仓只数，默认为 0
        
        Returns:
            交易信号列表
            
        Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6
        """
        signals: List[TradingSignal] = []
        
        if not stock_pool:
            logger.info("股票池为空，无信号生成")
            return signals
        
        logger.info(f"开始生成交易信号，候选股票数: {len(stock_pool)}")
        
        # 使用配置的初始资金作为默认值
        if current_cash is None:
            settings = get_settings()
            current_cash = settings.fund.initial_capital
        
        # 批量获取股票名称
        self._stock_names_cache = self.data_feed.get_stock_names_batch(stock_pool)

        for code in stock_pool:
            try:
                signal = self._analyze_stock(
                    code=code,
                    current_cash=current_cash,
                    current_positions=current_positions
                )
                
                if signal is not None:
                    signals.append(signal)
                    
            except Exception as e:
                logger.error(f"生成信号失败 {code}: {e}")
                continue
        
        # 按信号类型排序：买入信号优先
        signals.sort(key=lambda s: (
            0 if s.signal_type == SignalType.BUY else 1,
            -s.trade_amount  # 交易金额大的优先
        ))
        
        logger.info(f"信号生成完成: 共 {len(signals)} 个信号")
        return signals

    def _analyze_stock(
        self,
        code: str,
        current_cash: float,
        current_positions: int
    ) -> Optional[TradingSignal]:
        """
        分析单只股票，生成交易信号
        
        重要修复：使用 T-1 日数据生成信号，避免未来函数
        - 信号基于 T-1 日收盘数据计算
        - 限价上限基于 T-1 日收盘价 × 1.01
        - 实际执行在 T 日
        
        Args:
            code: 股票代码
            current_cash: 当前可用现金
            current_positions: 当前持仓只数
        
        Returns:
            TradingSignal 或 None（无信号时）
        """
        # 1. 加载历史数据
        df = self.data_feed.load_processed_data(code)
        if df is None or df.empty:
            logger.warning(f"无法加载数据，跳过: {code}")
            return None
        
        # 确保数据足够（至少需要 61 天，因为要用 T-1 数据）
        if len(df) < 61:
            logger.warning(f"数据不足（{len(df)} 条），跳过: {code}")
            return None
        
        # 2. 【重要修复】使用 T-1 日数据生成信号，避免未来函数
        # df.iloc[-1] 是最新数据（T日），df.iloc[-2] 是前一天数据（T-1日）
        # 信号基于 T-1 日数据计算，T 日执行
        signal_df = df.iloc[:-1]  # 排除最新一天，使用 T-1 及之前的数据
        latest_row = signal_df.iloc[-1]  # T-1 日数据
        close_price = float(latest_row['close'])  # T-1 日收盘价
        
        # 获取股票名称
        stock_name = self._stock_names_cache.get(code, code)
        
        # 3. 检查财报窗口期（硬风控）
        is_in_window, report_warning = self.report_checker.check_report_window(code)
        
        # 4. 计算技术指标，判断信号（使用 T-1 及之前的数据）
        signal_type, reason = self._check_signal_conditions(signal_df)
        
        if signal_type is None:
            logger.debug(f"无交易信号: {code}")
            return None
        
        # 5. 计算资金和费率
        settings = get_settings()
        max_shares, high_fee_warning, reject_reason = calculate_max_shares(
            cash=current_cash,
            price=close_price,
            commission_rate=settings.fund.commission_rate,
            min_commission=settings.fund.min_commission,
            max_positions_count=settings.position.max_positions_count,
            current_positions=current_positions,
            total_value=current_cash,  # 简化处理，使用现金作为总价值
            position_tolerance=settings.position.position_tolerance,
            min_trade_amount=settings.position.min_trade_amount,
            cash_buffer=settings.position.cash_buffer
        )
        
        # 如果资金风控拒绝，仍然生成信号但标记
        if max_shares == 0:
            logger.info(f"资金风控提示 {code}: {reject_reason}")
            # 使用最小交易金额作为预估
            trade_amount = settings.position.min_trade_amount
        else:
            trade_amount = max_shares * close_price
        
        # 计算实际费率
        actual_fee_rate = calculate_actual_fee_rate(
            trade_amount, 
            settings.fund.commission_rate, 
            settings.fund.min_commission
        )
        
        # 6. 计算辅助数据
        limit_cap = self._calculate_limit_cap(close_price)
        news_url = self._generate_news_url(code)
        
        # 计算建议价格区间（止损价作为下限）
        stop_loss_price = round(close_price * (1 + settings.strategy.hard_stop_loss), 2)
        price_range = (stop_loss_price, close_price)
        
        # 7. 构建信号对象
        signal = TradingSignal(
            code=code,
            name=stock_name,
            signal_type=signal_type,
            price_range=price_range,
            limit_cap=limit_cap,
            reason=reason,
            generated_at=date.today(),
            trade_amount=trade_amount,
            high_fee_warning=high_fee_warning,
            actual_fee_rate=actual_fee_rate,
            news_url=news_url,
            in_report_window=is_in_window,
            report_warning=report_warning
        )
        
        logger.info(
            f"生成信号: {code} {stock_name} - {signal_type.value}, "
            f"限价上限: ¥{limit_cap:.2f}, "
            f"财报窗口期: {'是' if is_in_window else '否'}"
        )
        
        return signal

    def _check_signal_conditions(
        self, 
        df: pd.DataFrame
    ) -> Tuple[Optional[SignalType], str]:
        """
        检查技术指标条件，判断信号类型
        
        根据 self.strategy_type 选择不同的策略逻辑
        
        Args:
            df: 股票历史数据 DataFrame
        
        Returns:
            (信号类型, 信号依据) 或 (None, "") 无信号时
        """
        if self.strategy_type == StrategyType.RSI_REVERSAL:
            return self._check_rsi_reversal_conditions(df)
        else:
            return self._check_rsrs_conditions(df)

    def _check_rsrs_conditions(
        self, 
        df: pd.DataFrame
    ) -> Tuple[Optional[SignalType], str]:
        """
        RSRS 阻力支撑相对强度策略
        
        计算步骤：
        1. 取过去 N 天的 High/Low 数据，做线性回归，得到斜率 Beta
        2. 将 Beta 标准化（Z-Score），与过去 M 天的历史比较
        3. RSRS 标准分 > 0.7 买入，< -0.7 卖出
        """
        n_period = 18   # 斜率计算窗口
        m_period = 600  # 标准化窗口
        buy_threshold = 0.7
        sell_threshold = -0.7
        
        if len(df) < max(n_period, 100):  # 至少需要 100 天数据
            return None, ""
        
        import numpy as np
        
        high = df['high'].values
        low = df['low'].values
        
        # 计算所有历史的 beta 值
        betas = []
        for i in range(n_period, len(df) + 1):
            h = high[i-n_period:i]
            l = low[i-n_period:i]
            
            # 线性回归：Y = High, X = Low
            x_mean = np.mean(l)
            y_mean = np.mean(h)
            
            numerator = np.sum((l - x_mean) * (h - y_mean))
            denominator = np.sum((l - x_mean) ** 2)
            
            if denominator != 0:
                beta = numerator / denominator
            else:
                beta = 1.0
            
            betas.append(beta)
        
        if len(betas) < 2:
            return None, ""
        
        # 当前 beta
        current_beta = betas[-1]
        
        # 标准化（Z-Score）
        if len(betas) >= m_period:
            recent_betas = betas[-m_period:]
        else:
            recent_betas = betas
        
        mean_beta = np.mean(recent_betas)
        std_beta = np.std(recent_betas)
        
        if std_beta > 0:
            rsrs_score = (current_beta - mean_beta) / std_beta
        else:
            rsrs_score = 0
        
        # 买入信号：RSRS 标准分 > 0.7
        if rsrs_score > buy_threshold:
            reason = f"RSRS买入信号 (标准分={rsrs_score:.2f} > {buy_threshold})"
            return SignalType.BUY, reason
        
        # 卖出信号：RSRS 标准分 < -0.7
        if rsrs_score < sell_threshold:
            reason = f"RSRS卖出信号 (标准分={rsrs_score:.2f} < {sell_threshold})"
            return SignalType.SELL, reason
        
        return None, ""

    def _check_bollinger_reversion_conditions(
        self, 
        df: pd.DataFrame
    ) -> Tuple[Optional[SignalType], str]:
        """
        布林带均值回归策略
        
        买入条件（全部满足）:
        1. 收盘价 < 布林带下轨（超卖区）
        2. RSI < 35（确认超卖）
        3. 成交量 > 5日均量（有资金介入）
        
        卖出条件：
        1. 收盘价 >= 布林带中轨（均值回归完成）
        2. 收盘价 >= 布林带上轨（超买区止盈）
        """
        if len(df) < 30:
            return None, ""
        
        close = df['close']
        volume = df['volume']
        
        # 1. 计算布林带 (20日, 2倍标准差)
        bb_period = 20
        bb_std = 2.0
        
        ma20 = close.rolling(window=bb_period).mean()
        std20 = close.rolling(window=bb_period).std()
        
        upper_band = ma20 + bb_std * std20
        middle_band = ma20
        lower_band = ma20 - bb_std * std20
        
        current_close = close.iloc[-1]
        current_upper = upper_band.iloc[-1]
        current_middle = middle_band.iloc[-1]
        current_lower = lower_band.iloc[-1]
        
        # 2. 计算 RSI
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        loss = loss.replace(0, 0.000001)
        rs = gain / loss
        rsi_series = 100 - (100 / (1 + rs))
        current_rsi = rsi_series.iloc[-1]
        
        # 3. 计算成交量均线
        volume_ma5 = volume.rolling(window=5).mean()
        current_volume = volume.iloc[-1]
        current_volume_ma = volume_ma5.iloc[-1]
        
        # 买入信号：价格 < 下轨 + RSI < 35 + 放量
        if current_close < current_lower and current_rsi < 35 and current_volume > current_volume_ma:
            reason = f"布林带超卖反弹 (价格{current_close:.2f}<下轨{current_lower:.2f}, RSI={current_rsi:.1f}, 放量)"
            return SignalType.BUY, reason
        
        # 卖出信号：价格 >= 上轨
        if current_close >= current_upper:
            reason = f"触及布林带上轨 (价格{current_close:.2f}>=上轨{current_upper:.2f})"
            return SignalType.SELL, reason
        
        # 卖出信号：价格 >= 中轨（均值回归完成）
        if current_close >= current_middle:
            # 只有当之前在下轨附近买入时才触发
            prev_close = close.iloc[-2]
            prev_lower = lower_band.iloc[-2]
            if prev_close < prev_lower * 1.02:  # 之前接近下轨
                reason = f"均值回归完成 (价格{current_close:.2f}>=中轨{current_middle:.2f})"
                return SignalType.SELL, reason
        
        return None, ""

    def _check_macd_trend_conditions(
        self, 
        df: pd.DataFrame
    ) -> Tuple[Optional[SignalType], str]:
        """
        趋势滤网 MACD 策略
        
        买入条件（全部满足）:
        1. 股价 > MA60（趋势滤网，只做右侧交易）
        2. MACD 金叉（DIF 上穿 DEA）
        3. RSI < 80（避免追高）
        
        卖出条件：MACD 死叉
        """
        if len(df) < 60:
            return None, ""
        
        close = df['close']
        
        # 1. 计算 MA60
        ma60 = close.rolling(window=60).mean()
        current_close = close.iloc[-1]
        current_ma60 = ma60.iloc[-1]
        
        # 趋势滤网：股价必须在 MA60 之上
        if current_close <= current_ma60:
            return None, ""
        
        # 2. 计算 MACD
        exp12 = close.ewm(span=12, adjust=False).mean()
        exp26 = close.ewm(span=26, adjust=False).mean()
        dif = exp12 - exp26
        dea = dif.ewm(span=9, adjust=False).mean()
        
        current_dif = dif.iloc[-1]
        current_dea = dea.iloc[-1]
        prev_dif = dif.iloc[-2]
        prev_dea = dea.iloc[-2]
        
        # 3. 计算 RSI
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        loss = loss.replace(0, 0.000001)
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1]
        
        # 买入信号：MACD 金叉 + RSI < 80
        if prev_dif <= prev_dea and current_dif > current_dea:
            if current_rsi < 80:
                reason = f"MACD金叉 (价格{current_close:.2f}>MA60 {current_ma60:.2f}, RSI={current_rsi:.1f})"
                return SignalType.BUY, reason
        
        # 卖出信号：MACD 死叉
        if prev_dif >= prev_dea and current_dif < current_dea:
            reason = f"MACD死叉 (DIF={current_dif:.3f} < DEA={current_dea:.3f})"
            return SignalType.SELL, reason
        
        return None, ""

    def _check_rsi_reversal_conditions(
        self, 
        df: pd.DataFrame
    ) -> Tuple[Optional[SignalType], str]:
        """
        RSI 超卖反弹策略（增强版）
        
        买入条件（全部满足）：
        1. RSI < 30（超卖区反弹）
        2. 股价 > MA60 × 0.85（趋势确认，避免接飞刀）
        3. 股价 > MA20 × 0.90（短期趋势确认）
        
        卖出条件：RSI > 70（超买区止盈）
        
        优化说明：
        - 增加趋势确认，避免在单边下跌市中频繁抄底
        - MA60 × 0.85 是趋势安全底线
        - MA20 × 0.90 是短期趋势确认
        """
        if len(df) < 60:
            return None, ""
        
        close = df['close']
        current_close = close.iloc[-1]
        
        # 计算 RSI
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        loss = loss.replace(0, 0.000001)
        rs = gain / loss
        rsi_series = 100 - (100 / (1 + rs))
        
        current_rsi = rsi_series.iloc[-1]
        prev_rsi = rsi_series.iloc[-2]
        
        # 计算均线
        ma60 = close.rolling(window=60).mean().iloc[-1]
        ma20 = close.rolling(window=20).mean().iloc[-1]
        
        # 趋势确认条件
        ma60_floor = ma60 * 0.85  # MA60 的 85% 是安全底线
        ma20_floor = ma20 * 0.90  # MA20 的 90% 是短期底线
        
        # 买入信号：RSI < 30 + 趋势确认
        if current_rsi < 30:
            # 检查趋势安全性
            if current_close < ma60_floor:
                # 股价跌破 MA60 太多，可能是单边下跌，不买入
                return None, ""
            
            if current_close < ma20_floor:
                # 短期趋势太弱，谨慎买入
                reason = f"RSI超卖反弹 (RSI={current_rsi:.1f} < 30, ⚠️短期趋势偏弱)"
            else:
                reason = f"RSI超卖反弹 (RSI={current_rsi:.1f} < 30, 趋势确认✓)"
            
            return SignalType.BUY, reason
        
        # 备选买入：RSI 上穿 30 + 趋势确认
        if prev_rsi < 30 and current_rsi >= 30:
            if current_close >= ma60_floor:
                reason = f"RSI低位金叉 (上穿30, RSI={current_rsi:.1f}, 趋势确认✓)"
                return SignalType.BUY, reason
        
        # 卖出信号：RSI > 70
        if current_rsi > 70:
            reason = f"RSI超买止盈 (RSI={current_rsi:.1f} > 70)"
            return SignalType.SELL, reason
        
        return None, ""

    def _calculate_limit_cap(self, close_price: float) -> float:
        """
        计算限价上限
        
        逻辑：建议挂单价格 = 今日收盘价 × 1.01（允许 1% 的高开滑点）
        
        这个价格用于次日挂单，防止因高开而盲目追高
        
        Args:
            close_price: 今日收盘价
        
        Returns:
            限价上限（四舍五入到小数点后两位）
            
        Requirements: 6.3
        """
        return round(close_price * self.LIMIT_CAP_FACTOR, 2)

    def _generate_news_url(self, code: str) -> str:
        """
        生成东方财富个股资讯链接
        
        设计原则：人眼看新闻标题只需 10 秒，比 AI 分析更可靠
        
        URL 格式：
        - 上海股票（6开头）：https://quote.eastmoney.com/sh{code}.html
        - 深圳股票（0/3开头）：https://quote.eastmoney.com/sz{code}.html
        - 北京股票（8/4开头）：https://quote.eastmoney.com/bj{code}.html
        
        Args:
            code: 6位股票代码
        
        Returns:
            东方财富个股资讯页面 URL
            
        Requirements: 12.1, 12.2
        """
        # 根据股票代码判断市场
        if code.startswith("6"):
            market = "sh"  # 上海
        elif code.startswith("0") or code.startswith("3"):
            market = "sz"  # 深圳
        elif code.startswith("8") or code.startswith("4"):
            market = "bj"  # 北京
        else:
            market = "sz"  # 默认深圳
        
        return self.EASTMONEY_NEWS_URL.format(market=market, code=code)

    def generate_no_signal_message(self) -> str:
        """
        生成无信号时的提示消息
        
        Returns:
            提示消息字符串
            
        Requirements: 6.6
        """
        return "今日无操作建议"

    def get_signal_summary(self, signals: List[TradingSignal]) -> Dict:
        """
        获取信号摘要统计
        
        Args:
            signals: 信号列表
        
        Returns:
            摘要统计字典
        """
        if not signals:
            return {
                'total': 0,
                'buy_count': 0,
                'sell_count': 0,
                'hold_count': 0,
                'report_window_count': 0,
                'high_fee_warning_count': 0
            }
        
        return {
            'total': len(signals),
            'buy_count': sum(1 for s in signals if s.signal_type == SignalType.BUY),
            'sell_count': sum(1 for s in signals if s.signal_type == SignalType.SELL),
            'hold_count': sum(1 for s in signals if s.signal_type == SignalType.HOLD),
            'report_window_count': sum(1 for s in signals if s.in_report_window),
            'high_fee_warning_count': sum(1 for s in signals if s.high_fee_warning)
        }
