"""
Signal Engine Module

信号引擎模块，实现v11.4g策略的买入和卖出信号生成逻辑。
Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 6.1
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime

from .config import V114G_STRATEGY_PARAMS, MONITOR_CONFIG
from .models import Position, StockData, BuySignal, SellSignal


class SignalEngine:
    """
    信号生成引擎
    
    实现v11.4g科技股策略的买入和卖出信号生成。
    
    买入条件 (Requirements: 3.1):
    1. MA5 > MA20 (金叉)
    2. Price > MA60 (中期趋势向上)
    3. RSI between 44-70 (动量适中)
    4. Volume ratio > 1.1 (放量确认)
    5. MA20 slope > 0 (趋势向上)
    6. Price < MA5 × 1.05 (避免追高)
    
    卖出条件 (Requirements: 4.1-4.6):
    - 止损: -4.6%
    - 止盈: +22%
    - 移动止盈: +9%触发, 2.8%回撤
    - RSI超买: RSI>80且盈利
    - 趋势反转: MA5<MA20且亏损
    - 持仓超时: >=15天
    """
    
    def __init__(self, params=None):
        """
        初始化信号引擎
        
        Args:
            params: 策略参数，默认使用V114G_STRATEGY_PARAMS
        """
        self.params = params or V114G_STRATEGY_PARAMS
    
    def check_buy_conditions(self, stock_data: StockData) -> Dict[str, bool]:
        """
        检查v11.4g买入条件
        
        Requirements: 3.1, 3.5
        
        Args:
            stock_data: 股票数据
            
        Returns:
            Dict[str, bool]: 各条件是否满足
        """
        return {
            'ma5_above_ma20': stock_data.ma5 > stock_data.ma20,
            'price_above_ma60': stock_data.current_price > stock_data.ma60,
            'rsi_in_range': self.params.RSI_MIN <= stock_data.rsi <= self.params.RSI_MAX,
            'volume_ratio_ok': stock_data.volume_ratio > self.params.VOLUME_RATIO_MIN,
            'ma20_slope_positive': stock_data.ma20_slope > 0,
            'price_not_too_high': stock_data.current_price < stock_data.ma5 * (1 + self.params.MAX_PRICE_ABOVE_MA5_PCT),
        }
    
    def calculate_signal_strength(self, conditions: Dict[str, bool], stock_data: StockData) -> int:
        """
        计算信号强度
        
        Requirements: 3.2, 3.3, 3.4, 6.1
        
        信号强度计算规则:
        - 6个条件全满足: 100分
        - 5个条件满足: 83分
        - 少于5个条件: 0分（不生成信号）
        
        额外加分项（在基础分上调整）:
        - RSI位置加分: 最多20分
        - 量比强度加分: 最多20分
        
        Property 4: Buy Signal Strength Calculation
        For any stock data, if N conditions (out of 6) are met:
        - N = 6: signal strength = 100
        - N = 5: signal strength = 83
        - N < 5: no buy signal generated (strength = 0)
        
        Args:
            conditions: 买入条件满足情况
            stock_data: 股票数据
            
        Returns:
            int: 信号强度 0-100
        """
        conditions_met = sum(conditions.values())
        
        # 少于5个条件不生成信号
        if conditions_met < self.params.MIN_CONDITIONS_FOR_SIGNAL:
            return 0
        
        # 基础分数
        if conditions_met == 6:
            base_score = 100
        else:  # conditions_met == 5
            base_score = 83
        
        return base_score

    
    def generate_buy_signal(self, stock_data: StockData) -> Optional[BuySignal]:
        """
        生成买入信号
        
        Requirements: 3.1, 3.2, 3.3, 3.4
        
        Args:
            stock_data: 股票数据
            
        Returns:
            BuySignal: 买入信号，不满足条件时返回None
        """
        conditions = self.check_buy_conditions(stock_data)
        signal_strength = self.calculate_signal_strength(conditions, stock_data)
        
        # 信号强度为0表示不满足最低条件
        if signal_strength == 0:
            return None
        
        return BuySignal.from_stock_data(stock_data, signal_strength)
    
    def check_stop_loss(self, position: Position) -> bool:
        """
        检查止损条件
        
        Property 5: Stop Loss Signal Generation
        For any position where (current_price - cost_price) / cost_price <= -0.046,
        a stop-loss sell signal with urgency "high" must be generated.
        
        Requirements: 4.1
        
        Args:
            position: 持仓信息
            
        Returns:
            bool: 是否触发止损
        """
        return position.pnl_pct <= self.params.STOP_LOSS_PCT
    
    def check_take_profit(self, position: Position) -> bool:
        """
        检查止盈条件
        
        Property 6: Take Profit Signal Generation
        For any position where (current_price - cost_price) / cost_price >= 0.22,
        a take-profit sell signal must be generated.
        
        Requirements: 4.2
        
        Args:
            position: 持仓信息
            
        Returns:
            bool: 是否触发止盈
        """
        return position.pnl_pct >= self.params.TAKE_PROFIT_PCT
    
    def check_trailing_stop(self, position: Position) -> bool:
        """
        检查移动止盈条件
        
        Property 7: Trailing Stop Signal Generation
        For any position where:
        1. Peak profit reached >= 9% (peak_price >= cost_price × 1.09)
        2. Current price retraced >= 2.8% from peak (current_price <= peak_price × 0.972)
        A trailing-stop sell signal must be generated.
        
        Requirements: 4.3
        
        Args:
            position: 持仓信息
            
        Returns:
            bool: 是否触发移动止盈
        """
        # 条件1: 峰值盈利达到触发阈值
        peak_profit_triggered = position.peak_pnl_pct >= self.params.TRAILING_TRIGGER_PCT
        
        # 条件2: 从峰值回撤超过阈值
        drawdown_triggered = position.drawdown_from_peak >= self.params.TRAILING_STOP_PCT
        
        return peak_profit_triggered and drawdown_triggered
    
    def check_rsi_overbought(self, position: Position, rsi: float) -> bool:
        """
        检查RSI超买条件
        
        Property 8: RSI Overbought Signal Generation
        For any position where RSI > 80 AND position is profitable (pnl_pct > 0),
        an RSI-overbought sell signal must be generated.
        
        Requirements: 4.4
        
        Args:
            position: 持仓信息
            rsi: 当前RSI值
            
        Returns:
            bool: 是否触发RSI超买
        """
        return rsi > self.params.RSI_OVERBOUGHT and position.pnl_pct > 0
    
    def check_trend_reversal(self, position: Position, ma5: float, ma20: float) -> bool:
        """
        检查趋势反转条件
        
        Property 9: Trend Reversal Signal Generation
        For any position where MA5 < MA20 AND position is at loss (pnl_pct < 0),
        a trend-reversal sell signal must be generated.
        
        Requirements: 4.5
        
        Args:
            position: 持仓信息
            ma5: MA5值
            ma20: MA20值
            
        Returns:
            bool: 是否触发趋势反转
        """
        return ma5 < ma20 and position.pnl_pct < 0
    
    def check_timeout(self, position: Position) -> bool:
        """
        检查持仓超时条件
        
        Property 10: Timeout Signal Generation
        For any position where holding_days >= 15,
        a timeout sell signal must be generated.
        
        Requirements: 4.6
        
        Args:
            position: 持仓信息
            
        Returns:
            bool: 是否触发持仓超时
        """
        return position.holding_days >= self.params.MAX_HOLDING_DAYS

    
    def check_sell_conditions(
        self, 
        position: Position, 
        stock_data: StockData
    ) -> List[Tuple[str, bool]]:
        """
        检查所有卖出条件
        
        Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6
        
        Args:
            position: 持仓信息
            stock_data: 股票数据
            
        Returns:
            List[Tuple[str, bool]]: 各卖出条件及其触发状态
        """
        # 更新持仓的当前价格
        position.update_current_price(stock_data.current_price)
        
        return [
            ('stop_loss', self.check_stop_loss(position)),
            ('take_profit', self.check_take_profit(position)),
            ('trailing_stop', self.check_trailing_stop(position)),
            ('rsi_overbought', self.check_rsi_overbought(position, stock_data.rsi)),
            ('trend_reversal', self.check_trend_reversal(position, stock_data.ma5, stock_data.ma20)),
            ('timeout', self.check_timeout(position)),
        ]
    
    def generate_sell_signals(
        self, 
        position: Position, 
        stock_data: StockData
    ) -> List[SellSignal]:
        """
        生成卖出信号
        
        Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6
        
        按优先级检查卖出条件并生成信号:
        1. 止损 (最高优先级)
        2. 止盈
        3. 移动止盈
        4. RSI超买
        5. 趋势反转
        6. 持仓超时 (最低优先级)
        
        Args:
            position: 持仓信息
            stock_data: 股票数据
            
        Returns:
            List[SellSignal]: 触发的卖出信号列表
        """
        signals = []
        
        # 更新持仓的当前价格
        position.update_current_price(stock_data.current_price)
        
        # 按优先级检查各卖出条件
        if self.check_stop_loss(position):
            signals.append(SellSignal.create_stop_loss_signal(position))
        
        if self.check_take_profit(position):
            signals.append(SellSignal.create_take_profit_signal(position))
        
        if self.check_trailing_stop(position):
            signals.append(SellSignal.create_trailing_stop_signal(position))
        
        if self.check_rsi_overbought(position, stock_data.rsi):
            signals.append(SellSignal.create_rsi_overbought_signal(position, stock_data.rsi))
        
        if self.check_trend_reversal(position, stock_data.ma5, stock_data.ma20):
            signals.append(SellSignal.create_trend_reversal_signal(position))
        
        if self.check_timeout(position):
            signals.append(SellSignal.create_timeout_signal(position))
        
        return signals
    
    def get_highest_priority_sell_signal(
        self, 
        position: Position, 
        stock_data: StockData
    ) -> Optional[SellSignal]:
        """
        获取最高优先级的卖出信号
        
        Args:
            position: 持仓信息
            stock_data: 股票数据
            
        Returns:
            SellSignal: 最高优先级的卖出信号，无信号时返回None
        """
        signals = self.generate_sell_signals(position, stock_data)
        return signals[0] if signals else None
    
    def calculate_buy_signal_prices(self, entry_price: float) -> Dict[str, float]:
        """
        计算买入信号的价格建议
        
        Property 14: Buy Signal Price Calculations
        For any buy signal with entry price E:
        - stop_loss_price = E × (1 - 0.046) = E × 0.954
        - take_profit_price = E × (1 + 0.22) = E × 1.22
        - trailing_trigger_price = E × (1 + 0.09) = E × 1.09
        
        Requirements: 9.1
        
        Args:
            entry_price: 入场价格
            
        Returns:
            Dict[str, float]: 包含止损价、止盈价、移动止盈触发价的字典
        """
        return {
            'entry_price': round(entry_price, 2),
            'stop_loss_price': round(entry_price * (1 + self.params.STOP_LOSS_PCT), 2),
            'take_profit_price': round(entry_price * (1 + self.params.TAKE_PROFIT_PCT), 2),
            'trailing_trigger_price': round(entry_price * (1 + self.params.TRAILING_TRIGGER_PCT), 2),
        }
    
    def get_sell_recommendation(self, sell_signal: SellSignal) -> Dict[str, str]:
        """
        获取卖出信号的交易建议
        
        Requirements: 9.2
        
        根据卖出信号类型生成详细的交易建议，包括:
        - 紧急程度说明
        - 建议操作说明
        - 退出原因解释
        
        Args:
            sell_signal: 卖出信号
            
        Returns:
            Dict[str, str]: 包含紧急程度、建议操作、原因解释的字典
        """
        urgency_descriptions = {
            SellSignal.URGENCY_HIGH: '高 - 建议立即执行',
            SellSignal.URGENCY_MEDIUM: '中 - 建议尽快处理',
            SellSignal.URGENCY_LOW: '低 - 可继续观察',
        }
        
        action_descriptions = {
            SellSignal.ACTION_IMMEDIATE_SELL: '立即卖出 - 全部清仓',
            SellSignal.ACTION_REDUCE_POSITION: '减仓 - 卖出部分持仓',
            SellSignal.ACTION_MONITOR: '观察 - 密切关注后续走势',
        }
        
        signal_type_explanations = {
            SellSignal.TYPE_STOP_LOSS: f'股价已跌破止损线({self.params.STOP_LOSS_PCT*100:.1f}%)，为控制风险建议立即止损。',
            SellSignal.TYPE_TAKE_PROFIT: f'股价已达到止盈目标(+{self.params.TAKE_PROFIT_PCT*100:.0f}%)，建议锁定利润。',
            SellSignal.TYPE_TRAILING_STOP: f'股价从高点回撤超过{self.params.TRAILING_STOP_PCT*100:.1f}%，移动止盈触发，建议卖出保护利润。',
            SellSignal.TYPE_RSI_OVERBOUGHT: f'RSI超过{self.params.RSI_OVERBOUGHT}进入超买区域，且持仓盈利，建议减仓锁定部分利润。',
            SellSignal.TYPE_TREND_REVERSAL: 'MA5下穿MA20形成死叉，且持仓处于亏损状态，趋势可能反转，建议止损。',
            SellSignal.TYPE_TIMEOUT: f'持仓已超过{self.params.MAX_HOLDING_DAYS}天，资金效率降低，建议评估是否继续持有。',
        }
        
        return {
            'urgency_description': urgency_descriptions.get(sell_signal.urgency, '未知'),
            'action_description': action_descriptions.get(sell_signal.action, '未知'),
            'reason_explanation': signal_type_explanations.get(sell_signal.signal_type, sell_signal.reason),
        }
