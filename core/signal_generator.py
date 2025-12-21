"""
MiniQuant-Lite 每日交易信号生成模块

负责生成每日交易信号，包含：
- 技术面筛选生成候选信号
- 计算限价上限（防止追高）
- 生成新闻链接（人工查看）
- 检查财报窗口期（硬风控）
- 高费率预警

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
    
    设计原则：
    - 把决策权还给人，系统只做硬风控
    - 新闻链接比 AI 分析更可靠（人眼看标题只需 10 秒）
    - 财报窗口期一律剔除，宁可错过不可做错
    
    Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6
    """
    
    # 允许的高开滑点系数 (1%)
    # 限价上限 = 收盘价 × 1.01，防止次日高开时盲目追高
    LIMIT_CAP_FACTOR = 1.01
    
    # 东方财富个股资讯 URL 模板
    # 格式：https://quote.eastmoney.com/{market}{code}.html
    # market: sh（上海）, sz（深圳）, bj（北京）
    EASTMONEY_NEWS_URL = "https://quote.eastmoney.com/{market}{code}.html"

    def __init__(
        self, 
        data_feed: DataFeed, 
        strategy_class: Optional[type] = None
    ):
        """
        初始化信号生成器
        
        Args:
            data_feed: 数据获取模块实例
            strategy_class: 策略类（可选，用于获取策略参数）
        """
        self.data_feed = data_feed
        self.strategy_class = strategy_class
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
        
        # 确保数据足够（至少需要 60 天计算 MA60）
        if len(df) < 60:
            logger.warning(f"数据不足（{len(df)} 条），跳过: {code}")
            return None
        
        # 2. 获取最新数据
        latest_row = df.iloc[-1]
        close_price = float(latest_row['close'])
        
        # 获取股票名称
        stock_name = self._stock_names_cache.get(code, code)
        
        # 3. 检查财报窗口期（硬风控）
        is_in_window, report_warning = self.report_checker.check_report_window(code)
        
        # 4. 计算技术指标，判断信号
        signal_type, reason = self._check_signal_conditions(df)
        
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
        检查技术指标条件，判断信号类型 (针对小资金优化的 RSI 反转策略)
        
        策略逻辑 (RSI Mean Reversion):
        - 买入: RSI(14) < 30 (超卖区反弹)
        - 卖出: RSI(14) > 70 (超买区止盈)
        
        为什么改这个？
        MACD 适合大趋势，但在震荡市中太慢。对于5.5万资金，
        我们需要更灵敏的信号，快进快出，积累小胜为大胜。
        
        Args:
            df: 股票历史数据 DataFrame
        
        Returns:
            (信号类型, 信号依据) 或 (None, "") 无信号时
        """
        if len(df) < 20:  # RSI至少需要15天数据
            return None, ""
        
        # 1. 计算 RSI (相对强弱指标)
        close = df['close']
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        
        # 避免除以零
        loss = loss.replace(0, 0.000001)
        rs = gain / loss
        rsi_series = 100 - (100 / (1 + rs))
        
        current_rsi = rsi_series.iloc[-1]
        prev_rsi = rsi_series.iloc[-2]
        
        # 2. 计算 MA60 (作为生命线风控)
        # 虽然我们做超跌反弹，但如果股价在 MA60 之下太远（比如下跌趋势中），
        # 可能是主跌浪，最好还是小心点。
        # 这里我们放宽限制：只要不是"暴跌"（例如偏离均线20%以上）就可以尝试抄底
        if len(df) >= 60:
            ma60 = df['close'].rolling(window=60).mean().iloc[-1]
            current_close = close.iloc[-1]
            # 简单的趋势判断：如果股价跌破 MA60 太多(>20%)，可能是垃圾股，不抄底
            if current_close < ma60 * 0.8:
                return None, ""
        
        # ==========================================
        # 🎯 买入信号：超卖反弹
        # 条件：RSI 跌破 30 (恐慌盘杀出)
        # ==========================================
        if current_rsi < 30:
            reason = f"RSI超卖反弹 (RSI={current_rsi:.1f} < 30)"
            return SignalType.BUY, reason
            
        # 备选买入：RSI 从下方穿过 30 (右侧买点)
        if prev_rsi < 30 and current_rsi >= 30:
            reason = f"RSI低位金叉 (上穿30, RSI={current_rsi:.1f})"
            return SignalType.BUY, reason

        # ==========================================
        # 🛑 卖出信号：超买止盈
        # 条件：RSI 冲过 70 (贪婪盘涌入)
        # ==========================================
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
