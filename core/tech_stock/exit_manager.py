"""
科技股卖出信号管理器模块

实现卖出信号的生成、优先级排序和特殊持仓标记。

信号优先级（从高到低）：
1. 紧急避险 (EMERGENCY): 大盘红灯 + 持仓亏损
2. 止损 (STOP_LOSS): 亏损达 -10%
3. 止盈 (TAKE_PROFIT): RSI > 85
4. 趋势断裂 (TREND_BREAK): 连续2日跌破MA20

止损规则：
- 亏损状态：硬止损 -10%
- 盈利 5-15%：止损移至成本价
- 盈利 >15%：止损移至 MA5

RSI 分仓止盈：
- 持仓 >= 200股 且 RSI > 85：卖一半
- 持仓 = 100股 且 RSI > 85：止损紧贴 MA5

Requirements: 6.1, 6.2, 6.3, 6.4, 7.1, 7.2, 8.1, 9.1, 9.2, 9.3, 9.4, 9.5, 10.1, 10.2, 10.3, 10.4
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from enum import IntEnum
from typing import List, Optional, Dict, Tuple, Any
import pandas as pd
import logging

from config.tech_stock_config import get_tech_config
from core.tech_stock.market_filter import MarketStatus
from core.position_tracker import Holding

logger = logging.getLogger(__name__)


class SignalPriority(IntEnum):
    """
    信号优先级枚举（数值越小优先级越高）
    
    优先级顺序：紧急避险 > 止损 > 止盈 > 趋势断裂
    
    Requirements: 9.1
    """
    EMERGENCY = 1       # 紧急避险 (大盘红灯+亏损)
    STOP_LOSS = 2       # 止损 (-10%)
    TAKE_PROFIT = 3     # 止盈 (RSI>85)
    TREND_BREAK = 4     # 趋势断裂 (连续2日跌破MA20)


@dataclass
class TechExitSignal:
    """
    科技股卖出信号数据类
    
    Attributes:
        code: 股票代码
        name: 股票名称
        exit_type: 卖出类型 ("emergency" / "stop_loss" / "take_profit" / "trend_break" / "rsi_partial")
        priority: 信号优先级
        current_price: 当前价格
        stop_loss_price: 止损价
        cost_price: 成本价
        pnl_pct: 盈亏百分比
        rsi: 当前 RSI
        ma5: MA5
        ma20: MA20
        ma20_break_days: MA20 跌破天数
        shares: 持仓股数
        is_min_position: 是否最小仓位 (100股)
        suggested_action: 建议操作
        urgency_color: 紧急程度颜色 ("red" / "orange" / "yellow" / "blue")
        generated_at: 生成时间
    
    Requirements: 6.1, 9.6
    """
    code: str
    name: str
    exit_type: str
    priority: SignalPriority
    current_price: float
    stop_loss_price: float
    cost_price: float
    pnl_pct: float
    rsi: float
    ma5: float
    ma20: float
    ma20_break_days: int
    shares: int
    is_min_position: bool
    suggested_action: str
    urgency_color: str
    generated_at: datetime = field(default_factory=datetime.now)


class TechExitManager:
    """
    科技股卖出信号管理器 - 含优先级排序
    
    负责生成卖出信号、计算止损价、处理 RSI 分仓止盈、
    检测趋势断裂、按优先级排序信号、标记特殊持仓。
    
    设计原则：
    - 风险控制优先：信号优先级 紧急避险 > 止损 > 止盈 > 趋势
    - 小资金保护：100股持仓严格止盈
    - 移动止损：盈利后逐步上移止损位
    
    Requirements: 6.1, 6.2, 6.3, 6.4, 7.1, 7.2, 8.1, 9.1, 9.2, 9.3, 9.4, 9.5
    """
    
    # 止损参数
    HARD_STOP_LOSS = -0.10      # 硬止损 -10%
    PROFIT_THRESHOLD_1 = 0.05   # 盈利阈值1：5%
    PROFIT_THRESHOLD_2 = 0.15   # 盈利阈值2：15%
    RSI_OVERBOUGHT = 85         # RSI 超买阈值
    MA20_BREAK_DAYS = 2         # MA20 跌破天数阈值
    MIN_POSITION_SHARES = 100   # 最小仓位股数
    
    # 优先级颜色映射
    PRIORITY_COLORS = {
        SignalPriority.EMERGENCY: "red",      # 紧急避险 - 红色
        SignalPriority.STOP_LOSS: "orange",   # 止损 - 橙色
        SignalPriority.TAKE_PROFIT: "yellow", # 止盈 - 黄色
        SignalPriority.TREND_BREAK: "blue",   # 趋势断裂 - 蓝色
    }
    
    def __init__(self, data_feed=None):
        """
        初始化卖出信号管理器
        
        Args:
            data_feed: 数据获取模块实例
        """
        self.config = get_tech_config()
        self._data_feed = data_feed
        
        # RSI 周期
        self.RSI_PERIOD = self.config.indicator.rsi_period  # 14
        # 均线周期
        self.MA5_PERIOD = self.config.indicator.ma5_period  # 5
        self.MA20_PERIOD = self.config.indicator.ma20_period  # 20

    def check_exit_signals(
        self,
        holdings: List[Holding],
        market_status: MarketStatus,
        stock_data: Optional[Dict[str, pd.DataFrame]] = None,
        current_prices: Optional[Dict[str, float]] = None
    ) -> List[TechExitSignal]:
        """
        检查所有持仓的卖出信号
        
        检查顺序（按优先级）：
        1. 紧急避险 (大盘红灯 + 持仓亏损)
        2. 硬止损 (-10%)
        3. RSI 分仓止盈 (RSI>85)
        4. 趋势断裂 (连续2日跌破MA20)
        
        Args:
            holdings: 持仓列表
            market_status: 大盘状态
            stock_data: 股票数据字典 {code: DataFrame}
            current_prices: 当前价格字典 {code: price}
        
        Returns:
            按优先级排序的卖出信号列表
            
        Requirements: 6.1, 9.1, 9.2, 9.3, 9.4, 9.5
        """
        signals = []
        
        for holding in holdings:
            code = holding.code
            
            # 获取股票数据
            df = None
            if stock_data and code in stock_data:
                df = stock_data[code]
            elif self._data_feed:
                try:
                    df = self._data_feed.load_processed_data(code)
                except Exception as e:
                    logger.warning(f"获取 {code} 数据失败: {e}")
            
            if df is None or df.empty:
                logger.warning(f"{code} 无法获取数据，跳过卖出信号检查")
                continue
            
            # 确保数据按日期排序
            if 'date' in df.columns:
                df = df.sort_values('date').reset_index(drop=True)
            
            # 计算技术指标
            df = self._calculate_indicators(df)
            
            # 获取最新数据
            latest = df.iloc[-1]
            
            # 获取当前价格
            if current_prices and code in current_prices:
                current_price = current_prices[code]
            else:
                current_price = float(latest['close'])
            
            # 计算盈亏百分比
            pnl_pct = (current_price - holding.buy_price) / holding.buy_price if holding.buy_price > 0 else 0
            
            # 获取技术指标
            rsi = float(latest.get('rsi', 0)) if pd.notna(latest.get('rsi')) else 0
            ma5 = float(latest.get('ma5', 0)) if pd.notna(latest.get('ma5')) else 0
            ma20 = float(latest.get('ma20', 0)) if pd.notna(latest.get('ma20')) else 0
            
            # 计算 MA20 跌破天数
            ma20_break_days = self._calculate_ma20_break_days(df)
            
            # 计算止损价
            stop_loss_price = self.calculate_stop_loss_price(holding, current_price, ma5)
            
            # 检查各类卖出信号
            
            # 1. 紧急避险信号
            emergency_signal = self._check_emergency_exit(
                holding, market_status, current_price, pnl_pct,
                rsi, ma5, ma20, ma20_break_days, stop_loss_price
            )
            if emergency_signal:
                signals.append(emergency_signal)
                continue  # 紧急避险优先级最高，不再检查其他信号
            
            # 2. 硬止损信号
            stop_loss_signal = self._check_stop_loss(
                holding, current_price, pnl_pct,
                rsi, ma5, ma20, ma20_break_days, stop_loss_price
            )
            if stop_loss_signal:
                signals.append(stop_loss_signal)
                continue  # 止损优先级次高
            
            # 3. RSI 分仓止盈信号
            rsi_signal = self._check_rsi_partial_sell(
                holding, current_price, pnl_pct,
                rsi, ma5, ma20, ma20_break_days, stop_loss_price
            )
            if rsi_signal:
                signals.append(rsi_signal)
                # RSI 止盈不阻止趋势断裂检查
            
            # 4. 趋势断裂信号
            trend_signal = self._check_trend_break(
                holding, current_price, pnl_pct,
                rsi, ma5, ma20, ma20_break_days, stop_loss_price
            )
            if trend_signal and not rsi_signal:  # 避免重复信号
                signals.append(trend_signal)
        
        # 按优先级排序
        return self.sort_signals_by_priority(signals)

    def _check_emergency_exit(
        self,
        holding: Holding,
        market_status: MarketStatus,
        current_price: float,
        pnl_pct: float,
        rsi: float,
        ma5: float,
        ma20: float,
        ma20_break_days: int,
        stop_loss_price: float
    ) -> Optional[TechExitSignal]:
        """
        检查紧急避险信号
        
        条件：大盘红灯 且 持仓亏损
        优先级：最高 (EMERGENCY)
        
        Args:
            holding: 持仓记录
            market_status: 大盘状态
            current_price: 当前价格
            pnl_pct: 盈亏百分比
            rsi: RSI 值
            ma5: MA5 值
            ma20: MA20 值
            ma20_break_days: MA20 跌破天数
            stop_loss_price: 止损价
        
        Returns:
            紧急避险信号，如果不满足条件返回 None
            
        Requirements: 9.2
        """
        # 条件：大盘红灯 且 持仓亏损
        if not market_status.is_green and pnl_pct < 0:
            is_min_position = holding.quantity == self.MIN_POSITION_SHARES
            
            return TechExitSignal(
                code=holding.code,
                name=holding.name,
                exit_type="emergency",
                priority=SignalPriority.EMERGENCY,
                current_price=current_price,
                stop_loss_price=stop_loss_price,
                cost_price=holding.buy_price,
                pnl_pct=pnl_pct,
                rsi=rsi,
                ma5=ma5,
                ma20=ma20,
                ma20_break_days=ma20_break_days,
                shares=holding.quantity,
                is_min_position=is_min_position,
                suggested_action=f"⚠️ 紧急避险：大盘红灯+亏损({pnl_pct:.1%})，建议立即清仓",
                urgency_color=self.PRIORITY_COLORS[SignalPriority.EMERGENCY]
            )
        
        return None
    
    def _check_stop_loss(
        self,
        holding: Holding,
        current_price: float,
        pnl_pct: float,
        rsi: float,
        ma5: float,
        ma20: float,
        ma20_break_days: int,
        stop_loss_price: float
    ) -> Optional[TechExitSignal]:
        """
        检查硬止损信号
        
        条件：亏损达到 -10%
        优先级：第二 (STOP_LOSS)
        
        Args:
            holding: 持仓记录
            current_price: 当前价格
            pnl_pct: 盈亏百分比
            rsi: RSI 值
            ma5: MA5 值
            ma20: MA20 值
            ma20_break_days: MA20 跌破天数
            stop_loss_price: 止损价
        
        Returns:
            止损信号，如果不满足条件返回 None
            
        Requirements: 6.1
        """
        # 条件：亏损达到硬止损线
        if pnl_pct <= self.HARD_STOP_LOSS:
            is_min_position = holding.quantity == self.MIN_POSITION_SHARES
            
            return TechExitSignal(
                code=holding.code,
                name=holding.name,
                exit_type="stop_loss",
                priority=SignalPriority.STOP_LOSS,
                current_price=current_price,
                stop_loss_price=stop_loss_price,
                cost_price=holding.buy_price,
                pnl_pct=pnl_pct,
                rsi=rsi,
                ma5=ma5,
                ma20=ma20,
                ma20_break_days=ma20_break_days,
                shares=holding.quantity,
                is_min_position=is_min_position,
                suggested_action=f"🛑 硬止损触发：亏损{pnl_pct:.1%}达到-10%，建议清仓",
                urgency_color=self.PRIORITY_COLORS[SignalPriority.STOP_LOSS]
            )
        
        return None

    def calculate_stop_loss_price(
        self,
        holding: Holding,
        current_price: float,
        ma5: float
    ) -> float:
        """
        计算当前止损价
        
        规则：
        - 亏损状态：成本价 × (1 + HARD_STOP_LOSS) = 成本价 × 0.90
        - 盈利 5-15%：成本价（保本止损）
        - 盈利 >15%：MA5（移动止损）
        
        Args:
            holding: 持仓记录
            current_price: 当前价格
            ma5: MA5 值
        
        Returns:
            止损价
            
        Requirements: 6.2, 6.3, 6.4
        """
        cost_price = holding.buy_price
        
        if cost_price <= 0:
            return 0.0
        
        # 计算盈亏百分比
        pnl_pct = (current_price - cost_price) / cost_price
        
        if pnl_pct < 0:
            # 亏损状态：硬止损 -10%
            stop_loss_price = cost_price * (1 + self.HARD_STOP_LOSS)
        elif pnl_pct < self.PROFIT_THRESHOLD_1:
            # 盈利 0-5%：仍使用硬止损
            stop_loss_price = cost_price * (1 + self.HARD_STOP_LOSS)
        elif pnl_pct < self.PROFIT_THRESHOLD_2:
            # 盈利 5-15%：止损移至成本价
            stop_loss_price = cost_price
        else:
            # 盈利 >15%：止损移至 MA5
            stop_loss_price = ma5 if ma5 > 0 else cost_price
        
        return stop_loss_price
    
    def _check_rsi_partial_sell(
        self,
        holding: Holding,
        current_price: float,
        pnl_pct: float,
        rsi: float,
        ma5: float,
        ma20: float,
        ma20_break_days: int,
        stop_loss_price: float
    ) -> Optional[TechExitSignal]:
        """
        检查 RSI 分仓止盈
        
        规则：
        - 持仓 >= 200股 且 RSI > 85：卖一半
        - 持仓 = 100股 且 RSI > 85：止损紧贴 MA5
        
        Args:
            holding: 持仓记录
            current_price: 当前价格
            pnl_pct: 盈亏百分比
            rsi: RSI 值
            ma5: MA5 值
            ma20: MA20 值
            ma20_break_days: MA20 跌破天数
            stop_loss_price: 止损价
        
        Returns:
            RSI 止盈信号，如果不满足条件返回 None
            
        Requirements: 7.1, 7.2
        """
        # 条件：RSI > 85
        if rsi <= self.RSI_OVERBOUGHT:
            return None
        
        shares = holding.quantity
        is_min_position = shares == self.MIN_POSITION_SHARES
        
        if is_min_position:
            # 100股持仓：止损紧贴 MA5
            return TechExitSignal(
                code=holding.code,
                name=holding.name,
                exit_type="rsi_partial",
                priority=SignalPriority.TAKE_PROFIT,
                current_price=current_price,
                stop_loss_price=ma5 if ma5 > 0 else stop_loss_price,  # 止损紧贴 MA5
                cost_price=holding.buy_price,
                pnl_pct=pnl_pct,
                rsi=rsi,
                ma5=ma5,
                ma20=ma20,
                ma20_break_days=ma20_break_days,
                shares=shares,
                is_min_position=True,
                suggested_action=f"⚡ 100股持仓 RSI>{self.RSI_OVERBOUGHT}({rsi:.1f})：止损紧贴 MA5 ({ma5:.2f})",
                urgency_color=self.PRIORITY_COLORS[SignalPriority.TAKE_PROFIT]
            )
        elif shares >= 200:
            # 持仓 >= 200股：卖一半
            sell_shares = shares // 2
            # 确保卖出后剩余股数是100的整数倍
            sell_shares = (sell_shares // 100) * 100
            if sell_shares < 100:
                sell_shares = 100
            
            return TechExitSignal(
                code=holding.code,
                name=holding.name,
                exit_type="rsi_partial",
                priority=SignalPriority.TAKE_PROFIT,
                current_price=current_price,
                stop_loss_price=stop_loss_price,
                cost_price=holding.buy_price,
                pnl_pct=pnl_pct,
                rsi=rsi,
                ma5=ma5,
                ma20=ma20,
                ma20_break_days=ma20_break_days,
                shares=shares,
                is_min_position=False,
                suggested_action=f"💰 RSI>{self.RSI_OVERBOUGHT}({rsi:.1f})：建议卖出一半 ({sell_shares}股)",
                urgency_color=self.PRIORITY_COLORS[SignalPriority.TAKE_PROFIT]
            )
        
        return None

    def _check_trend_break(
        self,
        holding: Holding,
        current_price: float,
        pnl_pct: float,
        rsi: float,
        ma5: float,
        ma20: float,
        ma20_break_days: int,
        stop_loss_price: float
    ) -> Optional[TechExitSignal]:
        """
        检查趋势断裂信号
        
        条件：连续2日收盘价跌破 MA20
        优先级：第四 (TREND_BREAK)
        
        Args:
            holding: 持仓记录
            current_price: 当前价格
            pnl_pct: 盈亏百分比
            rsi: RSI 值
            ma5: MA5 值
            ma20: MA20 值
            ma20_break_days: MA20 跌破天数
            stop_loss_price: 止损价
        
        Returns:
            趋势断裂信号，如果不满足条件返回 None
            
        Requirements: 8.1
        """
        # 条件：连续2日跌破 MA20
        if ma20_break_days >= self.MA20_BREAK_DAYS:
            is_min_position = holding.quantity == self.MIN_POSITION_SHARES
            
            return TechExitSignal(
                code=holding.code,
                name=holding.name,
                exit_type="trend_break",
                priority=SignalPriority.TREND_BREAK,
                current_price=current_price,
                stop_loss_price=stop_loss_price,
                cost_price=holding.buy_price,
                pnl_pct=pnl_pct,
                rsi=rsi,
                ma5=ma5,
                ma20=ma20,
                ma20_break_days=ma20_break_days,
                shares=holding.quantity,
                is_min_position=is_min_position,
                suggested_action=f"📉 趋势断裂：连续{ma20_break_days}日跌破MA20，建议减仓或清仓",
                urgency_color=self.PRIORITY_COLORS[SignalPriority.TREND_BREAK]
            )
        
        return None
    
    def _calculate_ma20_break_days(self, df: pd.DataFrame) -> int:
        """
        计算连续跌破 MA20 的天数
        
        Args:
            df: 包含 close 和 ma20 列的 DataFrame
        
        Returns:
            连续跌破天数
            
        Requirements: 8.1
        """
        if df.empty or 'close' not in df.columns or 'ma20' not in df.columns:
            return 0
        
        # 从最新数据往前数
        break_days = 0
        for i in range(len(df) - 1, -1, -1):
            row = df.iloc[i]
            close = row.get('close')
            ma20 = row.get('ma20')
            
            if pd.isna(close) or pd.isna(ma20):
                break
            
            if close < ma20:
                break_days += 1
            else:
                break
        
        return break_days
    
    def sort_signals_by_priority(
        self,
        signals: List[TechExitSignal]
    ) -> List[TechExitSignal]:
        """
        按优先级排序信号（优先级高的在前）
        
        优先级顺序：紧急避险 > 止损 > 止盈 > 趋势断裂
        
        Args:
            signals: 卖出信号列表
        
        Returns:
            按优先级排序的信号列表
            
        Requirements: 9.1
        """
        return sorted(signals, key=lambda s: s.priority)

    def mark_special_positions(
        self,
        holdings: List[Holding]
    ) -> List[Dict[str, Any]]:
        """
        标记特殊持仓（100股最小仓位）
        
        Args:
            holdings: 持仓列表
        
        Returns:
            带有特殊标记的持仓列表
            
        Requirements: 10.1, 10.2, 10.3, 10.4
        """
        result = []
        for h in holdings:
            is_min = h.quantity == self.MIN_POSITION_SHARES
            result.append({
                "holding": h,
                "is_min_position": is_min,
                "special_marker": "🔸 严格止盈" if is_min else None,
                "highlight_color": "amber" if is_min else None,
            })
        return result
    
    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算技术指标
        
        计算 MA5, MA20, RSI 等指标
        
        Args:
            df: 股票数据 DataFrame
        
        Returns:
            添加了技术指标列的 DataFrame
        """
        df = df.copy()
        
        # 计算均线
        df['ma5'] = df['close'].rolling(window=self.MA5_PERIOD).mean()
        df['ma20'] = df['close'].rolling(window=self.MA20_PERIOD).mean()
        
        # 计算 RSI
        df['rsi'] = self._calculate_rsi(df['close'], self.RSI_PERIOD)
        
        return df
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """
        计算 RSI 指标
        
        RSI = 100 - 100 / (1 + RS)
        RS = 平均涨幅 / 平均跌幅
        
        Args:
            prices: 价格序列
            period: RSI 周期
        
        Returns:
            RSI 序列
        """
        delta = prices.diff()
        
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        # 避免除零
        rs = avg_gain / avg_loss.replace(0, float('inf'))
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def get_signals_summary(self, signals: List[TechExitSignal]) -> Dict[str, Any]:
        """
        获取卖出信号汇总统计
        
        Args:
            signals: 卖出信号列表
        
        Returns:
            汇总统计字典
        """
        if not signals:
            return {
                "total": 0,
                "by_type": {},
                "by_priority": {},
                "min_position_count": 0
            }
        
        # 按类型统计
        by_type = {}
        for s in signals:
            if s.exit_type not in by_type:
                by_type[s.exit_type] = 0
            by_type[s.exit_type] += 1
        
        # 按优先级统计
        by_priority = {}
        for s in signals:
            priority_name = s.priority.name
            if priority_name not in by_priority:
                by_priority[priority_name] = 0
            by_priority[priority_name] += 1
        
        # 最小仓位数量
        min_position_count = sum(1 for s in signals if s.is_min_position)
        
        return {
            "total": len(signals),
            "by_type": by_type,
            "by_priority": by_priority,
            "min_position_count": min_position_count
        }
    
    def format_signals_for_display(self, signals: List[TechExitSignal]) -> pd.DataFrame:
        """
        将信号格式化为 DataFrame，便于界面显示
        
        Args:
            signals: 卖出信号列表
        
        Returns:
            格式化的 DataFrame
        """
        data = []
        for s in signals:
            # 优先级图标
            priority_icons = {
                SignalPriority.EMERGENCY: "🔴",
                SignalPriority.STOP_LOSS: "🟠",
                SignalPriority.TAKE_PROFIT: "🟡",
                SignalPriority.TREND_BREAK: "🔵",
            }
            
            data.append({
                "优先级": priority_icons.get(s.priority, ""),
                "代码": s.code,
                "名称": s.name,
                "类型": self._get_exit_type_name(s.exit_type),
                "当前价": f"{s.current_price:.2f}",
                "止损价": f"{s.stop_loss_price:.2f}",
                "盈亏": f"{s.pnl_pct:.1%}",
                "RSI": f"{s.rsi:.1f}",
                "MA20跌破": f"{s.ma20_break_days}天",
                "持仓": f"{s.shares}股",
                "建议": s.suggested_action,
            })
        
        return pd.DataFrame(data)
    
    def _get_exit_type_name(self, exit_type: str) -> str:
        """获取卖出类型的中文名称"""
        type_names = {
            "emergency": "紧急避险",
            "stop_loss": "止损",
            "take_profit": "止盈",
            "trend_break": "趋势断裂",
            "rsi_partial": "RSI止盈",
        }
        return type_names.get(exit_type, exit_type)
    
    def get_priority_color(self, priority: SignalPriority) -> str:
        """
        获取优先级对应的颜色
        
        Args:
            priority: 信号优先级
        
        Returns:
            颜色名称
        """
        return self.PRIORITY_COLORS.get(priority, "gray")
