"""
大盘红绿灯过滤器模块

基于创业板指（399006）判断系统性风险，实现大盘红绿灯机制。

绿灯条件（允许买入）：
1. 创业板指收盘价 > MA20
2. MACD 无死叉

红灯条件（禁止买入）：
1. 创业板指收盘价 <= MA20
2. 或 MACD 出现死叉

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional
import pandas as pd
import logging

from config.tech_stock_config import get_tech_config

logger = logging.getLogger(__name__)


@dataclass
class MarketStatus:
    """
    大盘状态数据类
    
    Attributes:
        is_green: 是否绿灯（允许买入）
        gem_close: 创业板指收盘价
        gem_ma20: 创业板指 MA20
        macd_status: MACD 状态 ("golden_cross" / "death_cross" / "neutral")
        check_date: 检查日期
        reason: 状态原因说明
    """
    is_green: bool
    gem_close: float
    gem_ma20: float
    macd_status: str
    check_date: date
    reason: str


class MarketFilter:
    """
    大盘红绿灯过滤器
    
    使用创业板指（399006）作为大盘风控标的，判断系统性风险。
    
    设计原则：
    - 绿灯时允许生成买入信号
    - 红灯时禁止生成任何买入信号
    
    Requirements: 1.1, 1.2, 1.3, 1.4
    """
    
    def __init__(self, data_feed=None):
        """
        初始化大盘过滤器
        
        Args:
            data_feed: 数据获取模块实例，如果为 None 则使用默认配置创建
        """
        self.config = get_tech_config()
        self.gem_index_code = self.config.gem_index_code  # 399006
        self.ma_period = self.config.indicator.ma20_period  # 20
        self.macd_fast = self.config.indicator.macd_fast  # 12
        self.macd_slow = self.config.indicator.macd_slow  # 26
        self.macd_signal = self.config.indicator.macd_signal  # 9
        self._data_feed = data_feed
    
    def check_market_status(self, index_data: Optional[pd.DataFrame] = None) -> MarketStatus:
        """
        检查大盘状态
        
        条件：
        1. 创业板指收盘价 > MA20 → 满足条件1
        2. MACD 无死叉 → 满足条件2
        3. 两个条件同时满足 → 绿灯
        4. 任一条件不满足 → 红灯
        
        Args:
            index_data: 创业板指数据 DataFrame，包含 date, open, high, low, close, volume 列
                       如果为 None，则尝试从 data_feed 获取
        
        Returns:
            MarketStatus 对象，包含大盘状态信息
            
        Requirements: 1.1, 1.2, 1.3
        """
        # 获取指数数据
        if index_data is None:
            index_data = self._get_index_data()
        
        if index_data is None or index_data.empty:
            logger.warning(f"无法获取创业板指数据 ({self.gem_index_code})，默认返回红灯状态")
            return MarketStatus(
                is_green=False,
                gem_close=0.0,
                gem_ma20=0.0,
                macd_status="unknown",
                check_date=date.today(),
                reason="无法获取创业板指数据，默认红灯"
            )
        
        # 确保数据按日期排序
        if 'date' in index_data.columns:
            index_data = index_data.sort_values('date').reset_index(drop=True)
        
        # 计算 MA20
        index_data['ma20'] = index_data['close'].rolling(window=self.ma_period).mean()
        
        # 计算 MACD
        index_data = self._calculate_macd(index_data)
        
        # 获取最新数据
        latest = index_data.iloc[-1]
        gem_close = float(latest['close'])
        gem_ma20 = float(latest['ma20']) if pd.notna(latest['ma20']) else 0.0
        
        # 获取检查日期
        if 'date' in index_data.columns:
            check_date = pd.to_datetime(latest['date']).date()
        else:
            check_date = date.today()
        
        # 判断条件1：收盘价 > MA20
        price_above_ma20 = gem_close > gem_ma20 if gem_ma20 > 0 else False
        
        # 判断条件2：MACD 状态
        macd_status = self._calculate_macd_status(index_data)
        macd_ok = macd_status != "death_cross"
        
        # 综合判断
        is_green = price_above_ma20 and macd_ok
        
        # 生成原因说明
        reasons = []
        if price_above_ma20:
            reasons.append(f"收盘价 {gem_close:.2f} > MA20 {gem_ma20:.2f} ✓")
        else:
            reasons.append(f"收盘价 {gem_close:.2f} <= MA20 {gem_ma20:.2f} ✗")
        
        if macd_ok:
            reasons.append(f"MACD 状态: {macd_status} ✓")
        else:
            reasons.append(f"MACD 死叉 ✗")
        
        reason = "; ".join(reasons)
        
        logger.info(f"大盘状态检查: {'🟢 绿灯' if is_green else '🔴 红灯'} - {reason}")
        
        return MarketStatus(
            is_green=is_green,
            gem_close=gem_close,
            gem_ma20=gem_ma20,
            macd_status=macd_status,
            check_date=check_date,
            reason=reason
        )
    
    def _calculate_macd(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算 MACD 指标
        
        MACD = EMA(fast) - EMA(slow)
        Signal = EMA(MACD, signal_period)
        Histogram = MACD - Signal
        
        Args:
            df: 包含 close 列的 DataFrame
        
        Returns:
            添加了 macd, macd_signal, macd_hist 列的 DataFrame
        """
        df = df.copy()
        
        # 计算 EMA
        ema_fast = df['close'].ewm(span=self.macd_fast, adjust=False).mean()
        ema_slow = df['close'].ewm(span=self.macd_slow, adjust=False).mean()
        
        # 计算 MACD 线（DIF）
        df['macd'] = ema_fast - ema_slow
        
        # 计算信号线（DEA）
        df['macd_signal'] = df['macd'].ewm(span=self.macd_signal, adjust=False).mean()
        
        # 计算柱状图（MACD Histogram）
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        return df
    
    def _calculate_macd_status(self, df: pd.DataFrame) -> str:
        """
        计算 MACD 状态
        
        判断逻辑：
        - 金叉 (golden_cross): MACD 从下向上穿越信号线
        - 死叉 (death_cross): MACD 从上向下穿越信号线
        - 中性 (neutral): 无明显交叉
        
        Args:
            df: 包含 macd 和 macd_signal 列的 DataFrame
        
        Returns:
            MACD 状态字符串: "golden_cross" / "death_cross" / "neutral"
        """
        if 'macd' not in df.columns or 'macd_signal' not in df.columns:
            logger.warning("DataFrame 缺少 MACD 列，无法计算状态")
            return "neutral"
        
        if len(df) < 2:
            return "neutral"
        
        # 获取最近两天的数据
        current = df.iloc[-1]
        previous = df.iloc[-2]
        
        current_macd = current['macd']
        current_signal = current['macd_signal']
        previous_macd = previous['macd']
        previous_signal = previous['macd_signal']
        
        # 检查是否有 NaN
        if pd.isna(current_macd) or pd.isna(current_signal) or \
           pd.isna(previous_macd) or pd.isna(previous_signal):
            return "neutral"
        
        # 判断交叉
        # 金叉：前一天 MACD < Signal，今天 MACD >= Signal
        if previous_macd < previous_signal and current_macd >= current_signal:
            return "golden_cross"
        
        # 死叉：前一天 MACD >= Signal，今天 MACD < Signal
        if previous_macd >= previous_signal and current_macd < current_signal:
            return "death_cross"
        
        # 无交叉，根据当前位置判断趋势
        # 如果 MACD > Signal，说明处于金叉后的上升趋势
        # 如果 MACD < Signal，说明处于死叉后的下降趋势
        if current_macd >= current_signal:
            return "golden_cross"  # 处于金叉状态
        else:
            return "death_cross"  # 处于死叉状态
    
    def _get_index_data(self) -> Optional[pd.DataFrame]:
        """
        获取创业板指数据
        
        尝试从 data_feed 获取，如果失败则尝试直接从 AkShare 获取
        
        Returns:
            创业板指数据 DataFrame，失败时返回 None
        """
        # 如果有 data_feed，尝试从中获取
        if self._data_feed is not None:
            try:
                df = self._data_feed.load_processed_data(self.gem_index_code)
                if df is not None and not df.empty:
                    return df
            except Exception as e:
                logger.warning(f"从 data_feed 获取指数数据失败: {e}")
        
        # 尝试直接从 AkShare 获取
        try:
            import akshare as ak
            from datetime import timedelta
            
            # 获取最近 60 天的数据（确保有足够数据计算 MA20 和 MACD）
            end_date = datetime.now()
            start_date = end_date - timedelta(days=120)
            
            start_str = start_date.strftime('%Y%m%d')
            end_str = end_date.strftime('%Y%m%d')
            
            logger.info(f"从 AkShare 获取创业板指数据: {self.gem_index_code}")
            
            # 使用 stock_zh_index_daily 获取指数日线数据
            df = ak.stock_zh_index_daily(symbol=f"sz{self.gem_index_code}")
            
            if df is None or df.empty:
                logger.warning("AkShare 返回空数据")
                return None
            
            # 标准化列名
            df = df.rename(columns={
                'date': 'date',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume'
            })
            
            # 确保日期列是 datetime 类型
            df['date'] = pd.to_datetime(df['date'])
            
            # 只保留需要的列
            required_cols = ['date', 'open', 'high', 'low', 'close', 'volume']
            available_cols = [col for col in required_cols if col in df.columns]
            df = df[available_cols]
            
            # 按日期排序
            df = df.sort_values('date').reset_index(drop=True)
            
            # 只保留最近 60 天
            df = df.tail(60)
            
            logger.info(f"获取创业板指数据成功: {len(df)} 条记录")
            return df
            
        except Exception as e:
            logger.error(f"从 AkShare 获取创业板指数据失败: {e}")
            return None
    
    def is_trading_allowed(self, index_data: Optional[pd.DataFrame] = None) -> bool:
        """
        判断当前是否允许交易（简化接口）
        
        Args:
            index_data: 创业板指数据，如果为 None 则自动获取
        
        Returns:
            True 表示绿灯（允许交易），False 表示红灯（禁止交易）
            
        Requirements: 1.4
        """
        status = self.check_market_status(index_data)
        return status.is_green
