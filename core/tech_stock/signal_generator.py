"""
科技股买入信号生成器模块

根据技术指标和基本面条件生成科技股买入信号。
实现尾盘判定机制（14:45），符合 T+1 制度最优解。

买入条件：
1. 大盘绿灯（创业板指 > MA20 且 MACD 无死叉）
2. 行业排名 1-2（20日涨幅排名）
3. 通过硬性筛选（股价、市值、成交额）
4. 技术指标满足（趋势、动量、量能）
5. 基本面满足（营收/净利增长、无大额解禁）

尾盘判定机制：
- 14:45 后判定信号为"已确认"
- 14:45 前判定信号为"待确认"
- 交易窗口：14:45-15:00

Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 5.1, 5.2, 5.3, 5.4, 5.5
"""

from typing import List, Dict, Optional, Tuple, Any

from dataclasses import dataclass, field
from datetime import datetime, date, time
from typing import List, Optional, Dict, Tuple
import pandas as pd
import logging

from config.tech_stock_config import (
    get_tech_config,
    get_stock_sector,
    TECH_STOCK_POOL,
)
from core.tech_stock.market_filter import MarketFilter, MarketStatus
from core.tech_stock.sector_ranker import SectorRanker, SectorRank
from core.tech_stock.hard_filter import HardFilter, HardFilterResult
from core.tech_stock.performance_optimizer import (
    optimize_tech_stock_data_loading,
    batch_calculate_indicators,
    performance_timer,
    get_performance_stats
)

logger = logging.getLogger(__name__)


@dataclass
class TechBuySignal:
    """
    科技股买入信号数据类
    
    Attributes:
        code: 股票代码
        name: 股票名称
        sector: 所属行业
        price: 当前价格
        ma5: MA5 值
        ma20: MA20 值
        ma60: MA60 值
        rsi: RSI(14) 值
        volume_ratio: 量比（当日量/5日均量）
        revenue_growth: 营收正增长
        profit_growth: 净利正增长
        has_unlock: 有大额解禁
        signal_strength: 信号强度 (0-100)
        generated_at: 生成时间
        is_confirmed: 是否已确认（14:45后）
        confirmation_time: 确认时间
        conditions_met: 满足的条件列表
    """
    code: str
    name: str
    sector: str
    price: float
    ma5: float
    ma20: float
    ma60: float
    rsi: float
    volume_ratio: float
    revenue_growth: bool
    profit_growth: bool
    has_unlock: bool
    signal_strength: float
    generated_at: datetime
    is_confirmed: bool
    confirmation_time: Optional[datetime]
    conditions_met: List[str] = field(default_factory=list)


class TechSignalGenerator:
    """
    科技股买入信号生成器 - 含尾盘判定机制
    
    生成科技股买入信号，实现 T+1 制度下的尾盘判定机制。
    
    设计原则：
    - 14:45 尾盘判定，避免日内波动干扰
    - 多条件联合验证，确保信号质量
    - 量比使用预估全天成交量，避免"未来函数"风险
    
    Requirements: 4.1, 4.2, 5.1, 5.2, 5.3, 5.4, 5.5
    """
    
    # 尾盘判定时间常量 (T+1 最优解)
    EOD_CONFIRMATION_TIME = time(14, 45)  # 14:45
    MARKET_CLOSE_TIME = time(15, 0)       # 15:00
    
    def __init__(self, data_feed=None):
        """
        初始化信号生成器
        
        Args:
            data_feed: 数据获取模块实例
        """
        self.config = get_tech_config()
        self._data_feed = data_feed
        
        # 从配置获取参数
        self.RSI_MIN = self.config.indicator.rsi_min  # 55
        self.RSI_MAX = self.config.indicator.rsi_max  # 80
        self.VOLUME_RATIO_MIN = self.config.indicator.volume_ratio_min  # 1.5
        
        # 均线周期
        self.MA5_PERIOD = self.config.indicator.ma5_period  # 5
        self.MA20_PERIOD = self.config.indicator.ma20_period  # 20
        self.MA60_PERIOD = self.config.indicator.ma60_period  # 60
        
        # RSI 周期
        self.RSI_PERIOD = self.config.indicator.rsi_period  # 14
    
    @performance_timer
    def generate_signals(
        self,
        stock_pool: List[str],
        market_status: MarketStatus,
        sector_rankings: List[SectorRank],
        hard_filter_results: List[HardFilterResult],
        stock_data: Optional[Dict[str, pd.DataFrame]] = None,
        current_time: Optional[datetime] = None
    ) -> List[TechBuySignal]:
        """
        生成买入信号（性能优化版）
        
        流程：
        1. 检查大盘红绿灯（红灯直接返回空）
        2. 应用硬性筛选结果（只保留通过的股票）
        3. 过滤行业排名（只保留排名1-2的行业）
        4. 批量加载和计算技术指标（性能优化）
        5. 检查技术指标（趋势、动量、量能）
        6. 检查基本面（营收/净利增长、解禁）
        7. 标记信号确认状态（14:45后为已确认）
        
        Args:
            stock_pool: 股票代码列表
            market_status: 大盘状态
            sector_rankings: 行业排名列表
            hard_filter_results: 硬性筛选结果列表
            stock_data: 股票数据字典 {code: DataFrame}
            current_time: 当前时间（用于测试，默认使用系统时间）
        
        Returns:
            符合条件的买入信号列表
            
        Requirements: 4.1, 4.2, 5.1, 5.2, 5.3, 5.4, 5.5
        """
        signals = []
        
        if current_time is None:
            current_time = datetime.now()
        
        # 1. 检查大盘红绿灯
        if not market_status.is_green:
            logger.info(f"🔴 大盘红灯，禁止生成买入信号: {market_status.reason}")
            return signals
        
        logger.info(f"🟢 大盘绿灯，开始生成买入信号")
        
        # 2. 获取通过硬性筛选的股票
        passed_codes = {r.code for r in hard_filter_results if r.passed}
        hard_filter_map = {r.code: r for r in hard_filter_results}
        
        if not passed_codes:
            logger.info("没有股票通过硬性筛选")
            return signals
        
        logger.info(f"通过硬性筛选: {len(passed_codes)} 只股票")
        
        # 3. 获取可交易行业
        tradable_sectors = {r.sector_name for r in sector_rankings if r.is_tradable}
        logger.info(f"可交易行业: {tradable_sectors}")
        
        # 4. 过滤出可交易行业的股票
        eligible_codes = []
        for code in stock_pool:
            if code not in passed_codes:
                continue
            
            sector = get_stock_sector(code)
            if sector is None or sector not in tradable_sectors:
                continue
                
            eligible_codes.append(code)
        
        if not eligible_codes:
            logger.info("没有股票在可交易行业中")
            return signals
        
        logger.info(f"符合条件的股票: {len(eligible_codes)} 只")
        
        # 5. 性能优化：批量加载数据和计算指标
        if stock_data is None:
            logger.info("批量加载股票数据...")
            stock_data = optimize_tech_stock_data_loading(self._data_feed, eligible_codes)
        
        # 过滤出有效数据的股票
        valid_data = {code: df for code, df in stock_data.items() 
                     if df is not None and not df.empty and len(df) >= self.MA60_PERIOD + 1}
        
        if not valid_data:
            logger.info("没有股票有足够的数据")
            return signals
        
        logger.info(f"批量计算技术指标: {len(valid_data)} 只股票")
        indicators = batch_calculate_indicators(valid_data)
        
        # 6. 判断信号确认状态
        is_confirmed = self.is_signal_confirmed(current_time.time())
        confirmation_time = current_time if is_confirmed else None
        
        # 7. 遍历股票生成信号
        for code in eligible_codes:
            if code not in valid_data or code not in indicators:
                logger.debug(f"{code} 数据不足，跳过")
                continue
            
            df = valid_data[code]
            stock_indicators = indicators[code]
            
            # 获取最新数据
            latest = df.iloc[-1]
            
            # 检查技术条件
            conditions_met = []
            
            # 趋势条件：使用批量计算的指标
            trend_ok = self._check_trend_condition_optimized(stock_indicators, latest)
            if trend_ok:
                conditions_met.append("趋势: MA5金叉MA20, 股价>MA60")
            
            # 动量条件：使用批量计算的RSI
            momentum_ok = self._check_momentum_condition_optimized(stock_indicators)
            if momentum_ok:
                rsi_value = stock_indicators['rsi'].iloc[-1] if stock_indicators['rsi'] is not None else 0
                conditions_met.append(f"动量: RSI={rsi_value:.1f} (55-80)")
            
            # 量能条件
            volume_ok = self._check_volume_condition(df, current_time.time())
            if volume_ok:
                volume_ratio = self._calculate_volume_ratio(df, current_time.time())
                conditions_met.append(f"量能: 量比={volume_ratio:.2f} (>1.5)")
            
            # 基本面条件
            revenue_growth, profit_growth, has_unlock = self._check_fundamental_condition(code)
            fundamental_ok = (revenue_growth or profit_growth) and not has_unlock
            if fundamental_ok:
                growth_info = []
                if revenue_growth:
                    growth_info.append("营收增长")
                if profit_growth:
                    growth_info.append("净利增长")
                conditions_met.append(f"基本面: {'/'.join(growth_info)}, 无大额解禁")
            
            # 检查是否所有条件都满足
            all_conditions_met = trend_ok and momentum_ok and volume_ok and fundamental_ok
            
            if not all_conditions_met:
                logger.debug(f"{code} 技术条件不满足，跳过")
                continue
            
            # 获取股票名称
            hard_filter_result = hard_filter_map.get(code)
            stock_name = hard_filter_result.name if hard_filter_result else code
            
            # 计算信号强度
            rsi_value = stock_indicators['rsi'].iloc[-1] if stock_indicators['rsi'] is not None else 0
            volume_ratio = self._calculate_volume_ratio(df, current_time.time())
            signal_strength = self._calculate_signal_strength(
                rsi=rsi_value,
                volume_ratio=volume_ratio,
                revenue_growth=revenue_growth,
                profit_growth=profit_growth
            )
            
            # 获取技术指标值
            ma5_value = stock_indicators['ma5'].iloc[-1] if stock_indicators['ma5'] is not None else 0
            ma20_value = stock_indicators['ma20'].iloc[-1] if stock_indicators['ma20'] is not None else 0
            ma60_value = stock_indicators['ma60'].iloc[-1] if stock_indicators['ma60'] is not None else 0
            
            # 创建买入信号
            signal = TechBuySignal(
                code=code,
                name=stock_name,
                sector=get_stock_sector(code),
                price=float(latest['close']),
                ma5=ma5_value,
                ma20=ma20_value,
                ma60=ma60_value,
                rsi=rsi_value,
                volume_ratio=volume_ratio,
                revenue_growth=revenue_growth,
                profit_growth=profit_growth,
                has_unlock=has_unlock,
                signal_strength=signal_strength,
                generated_at=current_time,
                is_confirmed=is_confirmed,
                confirmation_time=confirmation_time,
                conditions_met=conditions_met
            )
            
            signals.append(signal)
            logger.info(f"✅ 生成买入信号: {code} {stock_name}, 强度: {signal_strength:.0f}")
        
        logger.info(f"🎯 共生成 {len(signals)} 个买入信号")
        return signals
    
    def is_signal_confirmed(self, current_time: Optional[time] = None) -> bool:
        """
        检查当前时间是否已过尾盘确认时间
        
        Args:
            current_time: 当前时间，默认使用系统时间
        
        Returns:
            True if 当前时间 >= 14:45
            
        Requirements: 4.1
        """
        if current_time is None:
            current_time = datetime.now().time()
        
        return current_time >= self.EOD_CONFIRMATION_TIME
    
    def get_signal_status(self, current_time: Optional[time] = None) -> str:
        """
        获取信号状态描述
        
        Args:
            current_time: 当前时间，默认使用系统时间
        
        Returns:
            "信号已确认" if 14:45后
            "信号待确认 (14:45后生效)" if 14:45前
            
        Requirements: 4.5
        """
        if self.is_signal_confirmed(current_time):
            return "信号已确认"
        return "信号待确认 (14:45后生效)"
    
    def get_trading_window_status(self, current_time: Optional[time] = None) -> Dict:
        """
        获取交易窗口状态
        
        Args:
            current_time: 当前时间，默认使用系统时间
        
        Returns:
            {
                "is_trading_window": bool,  # 是否在交易窗口 (14:45-15:00)
                "minutes_remaining": int,   # 剩余分钟数
                "status_message": str       # 状态消息
            }
            
        Requirements: 4.3, 4.4
        """
        if current_time is None:
            current_time = datetime.now().time()
        
        if current_time < self.EOD_CONFIRMATION_TIME:
            return {
                "is_trading_window": False,
                "minutes_remaining": -1,
                "status_message": "等待尾盘确认 (14:45)"
            }
        elif current_time <= self.MARKET_CLOSE_TIME:
            # 计算剩余分钟
            now_minutes = current_time.hour * 60 + current_time.minute
            close_minutes = self.MARKET_CLOSE_TIME.hour * 60 + self.MARKET_CLOSE_TIME.minute
            remaining = close_minutes - now_minutes
            return {
                "is_trading_window": True,
                "minutes_remaining": remaining,
                "status_message": f"⚡ 交易窗口开启，剩余 {remaining} 分钟"
            }
        else:
            return {
                "is_trading_window": False,
                "minutes_remaining": 0,
                "status_message": "今日交易已结束"
            }

    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算技术指标
        
        计算 MA5, MA20, MA60, RSI, 量比等指标
        
        Args:
            df: 股票数据 DataFrame
        
        Returns:
            添加了技术指标列的 DataFrame
        """
        df = df.copy()
        
        # 计算均线
        df['ma5'] = df['close'].rolling(window=self.MA5_PERIOD).mean()
        df['ma20'] = df['close'].rolling(window=self.MA20_PERIOD).mean()
        df['ma60'] = df['close'].rolling(window=self.MA60_PERIOD).mean()
        
        # 计算 RSI
        df['rsi'] = self._calculate_rsi(df['close'], self.RSI_PERIOD)
        
        # 计算量比（当日量/5日均量）
        df['avg_volume_5d'] = df['volume'].rolling(window=5).mean()
        df['volume_ratio'] = df['volume'] / df['avg_volume_5d']
        
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
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _check_trend_condition(self, df: pd.DataFrame) -> bool:
        """
        检查趋势条件
        
        条件：MA5 金叉 MA20，股价 > MA60
        
        Args:
            df: 包含技术指标的 DataFrame
        
        Returns:
            是否满足趋势条件
            
        Requirements: 5.1
        """
        if len(df) < 2:
            return False
        
        latest = df.iloc[-1]
        previous = df.iloc[-2]
        
        # 检查数据有效性
        if pd.isna(latest.get('ma5')) or pd.isna(latest.get('ma20')) or pd.isna(latest.get('ma60')):
            return False
        
        ma5 = latest['ma5']
        ma20 = latest['ma20']
        ma60 = latest['ma60']
        close = latest['close']
        
        prev_ma5 = previous.get('ma5', 0)
        prev_ma20 = previous.get('ma20', 0)
        
        # 条件1: MA5 金叉 MA20（MA5 从下向上穿越 MA20，或 MA5 > MA20）
        # 简化判断：当前 MA5 > MA20
        ma5_above_ma20 = ma5 > ma20
        
        # 条件2: 股价 > MA60
        price_above_ma60 = close > ma60
        
        return ma5_above_ma20 and price_above_ma60
    
    def _check_momentum_condition(self, df: pd.DataFrame) -> bool:
        """
        检查动量条件
        
        条件：RSI(14) 在 55-80 之间
        
        Args:
            df: 包含技术指标的 DataFrame
        
        Returns:
            是否满足动量条件
            
        Requirements: 5.2
        """
        if df.empty:
            return False
        
        latest = df.iloc[-1]
        rsi = latest.get('rsi')
        
        if pd.isna(rsi):
            return False
        
        return self.RSI_MIN <= rsi <= self.RSI_MAX
    
    def _check_volume_condition(
        self, 
        df: pd.DataFrame, 
        current_time: Optional[time] = None
    ) -> bool:
        """
        检查量能条件
        
        条件：当日量 > 5日均量 × 1.5
        
        注意：14:45 运行时，当日成交量约为全天的 92%-95%
        需要使用"预估全天成交量"进行比较，避免漏掉信号
        
        Args:
            df: 股票数据
            current_time: 当前时间（用于计算预估全天成交量）
        
        Returns:
            是否满足量能条件
            
        Requirements: 5.3
        """
        if df.empty:
            return False
        
        latest = df.iloc[-1]
        current_volume = latest.get('volume', 0)
        avg_volume_5d = latest.get('avg_volume_5d', 0)
        
        if pd.isna(current_volume) or pd.isna(avg_volume_5d) or avg_volume_5d <= 0:
            return False
        
        # 如果提供了当前时间，使用预估全天成交量
        if current_time is not None:
            predicted_volume = self._predict_daily_volume(current_volume, current_time)
        else:
            predicted_volume = current_volume
        
        volume_ratio = predicted_volume / avg_volume_5d
        
        return volume_ratio >= self.VOLUME_RATIO_MIN
    
    def _predict_daily_volume(self, current_volume: float, current_time: time) -> float:
        """
        预估全天成交量（避免"未来函数"风险）
        
        Args:
            current_volume: 当前累计成交量
            current_time: 当前时间
        
        Returns:
            预估全天成交量
        
        计算逻辑：
        - 交易时间：9:30-11:30 (120分钟) + 13:00-15:00 (120分钟) = 240分钟
        - 当前已交易分钟数 = (current_time - 9:30) 或 (current_time - 13:00 + 120)
        - 预估全天量 = 当前量 / (已交易分钟 / 240)
        
        Requirements: 5.3
        """
        hour, minute = current_time.hour, current_time.minute
        
        # 计算已交易分钟数
        if hour < 9 or (hour == 9 and minute < 30):
            # 开盘前
            return current_volume
        elif hour < 11 or (hour == 11 and minute <= 30):
            # 上午交易时段 9:30-11:30
            elapsed_minutes = (hour - 9) * 60 + minute - 30
        elif hour < 13:
            # 午休时段，使用上午结束时间
            elapsed_minutes = 120
        elif hour < 15:
            # 下午交易时段 13:00-15:00
            elapsed_minutes = 120 + (hour - 13) * 60 + minute
        else:
            # 收盘后，返回实际成交量
            return current_volume
        
        # 避免除零
        if elapsed_minutes <= 0:
            return current_volume
        
        # 预估全天成交量
        total_trading_minutes = 240
        predicted_volume = current_volume / (elapsed_minutes / total_trading_minutes)
        
        return predicted_volume
    
    def _check_fundamental_condition(self, code: str) -> Tuple[bool, bool, bool]:
        """
        检查基本面条件
        
        条件：营收或净利至少一个正增长，且无大额解禁
        
        Args:
            code: 股票代码
        
        Returns:
            (营收正增长, 净利正增长, 有大额解禁)
            
        Requirements: 5.4
        """
        revenue_growth = False
        profit_growth = False
        has_unlock = False
        
        try:
            import akshare as ak
            
            # 获取财务数据
            try:
                # 使用 AkShare 获取财务指标
                df_finance = ak.stock_financial_analysis_indicator(symbol=code)
                
                if df_finance is not None and not df_finance.empty:
                    # 获取最新一期数据
                    latest = df_finance.iloc[0]
                    
                    # 检查营收增长率
                    revenue_growth_rate = latest.get('营业收入同比增长率(%)', None)
                    if revenue_growth_rate is not None and not pd.isna(revenue_growth_rate):
                        revenue_growth = float(revenue_growth_rate) > 0
                    
                    # 检查净利润增长率
                    profit_growth_rate = latest.get('净利润同比增长率(%)', None)
                    if profit_growth_rate is not None and not pd.isna(profit_growth_rate):
                        profit_growth = float(profit_growth_rate) > 0
                        
            except Exception as e:
                logger.debug(f"获取 {code} 财务数据失败: {e}")
                # 财务数据获取失败时，默认为满足条件（避免误杀）
                revenue_growth = True
                profit_growth = True
            
            # 检查解禁数据
            try:
                # 获取限售解禁数据
                df_unlock = ak.stock_restricted_release_queue_sina(symbol=code)
                
                if df_unlock is not None and not df_unlock.empty:
                    # 检查近期是否有大额解禁（30天内）
                    from datetime import timedelta
                    today = date.today()
                    future_30d = today + timedelta(days=30)
                    
                    for _, row in df_unlock.iterrows():
                        unlock_date_str = row.get('解禁日期', '')
                        if unlock_date_str:
                            try:
                                unlock_date = pd.to_datetime(unlock_date_str).date()
                                if today <= unlock_date <= future_30d:
                                    # 检查解禁市值（假设大额解禁为 > 10亿）
                                    unlock_value = row.get('解禁市值(万元)', 0)
                                    if unlock_value and float(unlock_value) > 100000:  # 10亿 = 100000万
                                        has_unlock = True
                                        break
                            except:
                                pass
                                
            except Exception as e:
                logger.debug(f"获取 {code} 解禁数据失败: {e}")
                # 解禁数据获取失败时，默认为无解禁
                has_unlock = False
                
        except ImportError:
            logger.warning("AkShare 未安装，无法获取基本面数据")
            # 默认满足条件
            revenue_growth = True
            profit_growth = True
            has_unlock = False
        
        return revenue_growth, profit_growth, has_unlock
    
    def _calculate_signal_strength(
        self,
        rsi: float,
        volume_ratio: float,
        revenue_growth: bool,
        profit_growth: bool
    ) -> float:
        """
        计算信号强度
        
        综合 RSI、量比、基本面等因素计算信号强度
        
        Args:
            rsi: RSI 值
            volume_ratio: 量比
            revenue_growth: 营收正增长
            profit_growth: 净利正增长
        
        Returns:
            信号强度 (0-100)
        """
        strength = 0.0
        
        # RSI 贡献 (30分)
        # RSI 在 60-75 之间最佳
        if 60 <= rsi <= 75:
            strength += 30
        elif 55 <= rsi < 60 or 75 < rsi <= 80:
            strength += 20
        else:
            strength += 10
        
        # 量比贡献 (30分)
        # 量比越高越好，但不超过 3
        if volume_ratio >= 2.5:
            strength += 30
        elif volume_ratio >= 2.0:
            strength += 25
        elif volume_ratio >= 1.5:
            strength += 20
        else:
            strength += 10
        
        # 基本面贡献 (40分)
        if revenue_growth and profit_growth:
            strength += 40
        elif revenue_growth or profit_growth:
            strength += 25
        else:
            strength += 10
        
        return min(strength, 100)
    
    def get_signals_summary(self, signals: List[TechBuySignal]) -> Dict:
        """
        获取信号汇总统计
        
        Args:
            signals: 买入信号列表
        
        Returns:
            汇总统计字典
        """
        if not signals:
            return {
                "total": 0,
                "confirmed": 0,
                "pending": 0,
                "by_sector": {},
                "avg_strength": 0.0
            }
        
        confirmed = [s for s in signals if s.is_confirmed]
        pending = [s for s in signals if not s.is_confirmed]
        
        # 按行业统计
        by_sector = {}
        for s in signals:
            if s.sector not in by_sector:
                by_sector[s.sector] = 0
            by_sector[s.sector] += 1
        
        # 平均信号强度
        avg_strength = sum(s.signal_strength for s in signals) / len(signals)
        
        return {
            "total": len(signals),
            "confirmed": len(confirmed),
            "pending": len(pending),
            "by_sector": by_sector,
            "avg_strength": avg_strength
        }
    
    def format_signals_for_display(self, signals: List[TechBuySignal]) -> pd.DataFrame:
        """
        将信号格式化为 DataFrame，便于界面显示
        
        Args:
            signals: 买入信号列表
        
        Returns:
            格式化的 DataFrame
        """
        data = []
        for s in signals:
            data.append({
                "代码": s.code,
                "名称": s.name,
                "行业": s.sector,
                "价格": f"{s.price:.2f}",
                "RSI": f"{s.rsi:.1f}",
                "量比": f"{s.volume_ratio:.2f}",
                "信号强度": f"{s.signal_strength:.0f}",
                "状态": "✅ 已确认" if s.is_confirmed else "⏳ 待确认",
                "生成时间": s.generated_at.strftime("%H:%M:%S")
            })
        
        return pd.DataFrame(data)
    
    # ==========================================
    # 性能优化方法
    # ==========================================
    
    def _check_trend_condition_optimized(self, indicators: Dict[str, Any], latest_data: pd.Series) -> bool:
        """
        检查趋势条件（性能优化版）
        
        使用预计算的指标数据，避免重复计算
        
        Args:
            indicators: 预计算的指标字典
            latest_data: 最新数据行
            
        Returns:
            是否满足趋势条件
        """
        try:
            ma5_series = indicators.get('ma5')
            ma20_series = indicators.get('ma20')
            ma60_series = indicators.get('ma60')
            
            if ma5_series is None or ma20_series is None or ma60_series is None:
                return False
            
            # 获取最新值
            ma5_current = ma5_series.iloc[-1]
            ma20_current = ma20_series.iloc[-1]
            ma60_current = ma60_series.iloc[-1]
            current_price = latest_data['close']
            
            # 检查 MA5 > MA20（金叉）
            if len(ma5_series) >= 2 and len(ma20_series) >= 2:
                ma5_prev = ma5_series.iloc[-2]
                ma20_prev = ma20_series.iloc[-2]
                
                # 金叉条件：前一日 MA5 <= MA20，当日 MA5 > MA20
                golden_cross = (ma5_prev <= ma20_prev) and (ma5_current > ma20_current)
                # 或者已经处于金叉状态
                already_above = ma5_current > ma20_current
                
                ma_condition = golden_cross or already_above
            else:
                ma_condition = ma5_current > ma20_current
            
            # 检查股价 > MA60
            price_condition = current_price > ma60_current
            
            return ma_condition and price_condition
            
        except Exception as e:
            logger.debug(f"趋势条件检查失败: {e}")
            return False
    
    def _check_momentum_condition_optimized(self, indicators: Dict[str, Any]) -> bool:
        """
        检查动量条件（性能优化版）
        
        使用预计算的RSI数据
        
        Args:
            indicators: 预计算的指标字典
            
        Returns:
            是否满足动量条件
        """
        try:
            rsi_series = indicators.get('rsi')
            if rsi_series is None or rsi_series.empty:
                return False
            
            current_rsi = rsi_series.iloc[-1]
            
            # RSI 在 55-80 之间
            return self.RSI_MIN <= current_rsi <= self.RSI_MAX
            
        except Exception as e:
            logger.debug(f"动量条件检查失败: {e}")
            return False
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        获取信号生成器性能统计
        
        Returns:
            性能统计字典
        """
        return get_performance_stats()
    
    def clear_performance_cache(self) -> None:
        """清空性能缓存"""
        from core.tech_stock.performance_optimizer import clear_all_caches
        clear_all_caches()
        logger.info("信号生成器性能缓存已清空")