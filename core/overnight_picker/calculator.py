"""
买入价、仓位、止损止盈计算器

包含:
- EntryPriceCalculator: 买入价计算器
- PositionAdvisor: 仓位顾问
- StopLossCalculator: 止损计算器
- TakeProfitCalculator: 止盈计算器
"""

from typing import Dict
import math


class EntryPriceCalculator:
    """
    买入价计算器 - 计算明日理想买入价格区间
    """
    
    def __init__(self):
        self.ideal_discount = 0.02      # 理想买入价折扣 2%
        self.acceptable_premium = 0.01  # 可接受买入价溢价 1%
        self.abandon_premium = 0.03     # 放弃买入价溢价 3%
    
    def calculate_entry_prices(self,
                               today_close: float,
                               today_high: float,
                               today_low: float,
                               score: float,
                               volatility: float = 0.05) -> Dict:
        """
        计算买入价格区间
        
        Args:
            today_close: 今日收盘价
            today_high: 今日最高价
            today_low: 今日最低价
            score: 明日潜力评分 (0-100)
            volatility: 波动率
        
        Returns:
            {
                'ideal_price': float,      # 理想买入价(低开时买)
                'acceptable_price': float, # 可接受买入价(平开时买)
                'abandon_price': float,    # 放弃买入价(高开超此价不买)
                'reasoning': str           # 计算说明
            }
        """
        # 基础计算
        ideal_price = today_close * (1 - self.ideal_discount)
        acceptable_price = today_close * (1 + self.acceptable_premium)
        abandon_price = today_close * (1 + self.abandon_premium)
        
        # 根据评分调整
        if score >= 85:
            # 高分股: 可接受价上调1%
            acceptable_price = today_close * (1 + self.acceptable_premium + 0.01)
            abandon_price = today_close * (1 + self.abandon_premium + 0.01)
        elif score < 75:
            # 低分股: 可接受价下调1%
            acceptable_price = today_close * (1 + self.acceptable_premium - 0.01)
            abandon_price = today_close * (1 + self.abandon_premium - 0.01)
        
        # 根据波动率调整
        if volatility > 0.08:
            # 高波动: 扩大区间
            ideal_price = today_close * (1 - self.ideal_discount - 0.01)
            abandon_price = today_close * (1 + self.abandon_premium + 0.01)
        
        # 确保价格顺序正确: ideal < acceptable < abandon
        ideal_price = round(ideal_price, 2)
        acceptable_price = round(max(acceptable_price, ideal_price + 0.01), 2)
        abandon_price = round(max(abandon_price, acceptable_price + 0.01), 2)
        
        reasoning = f"收盘价{today_close:.2f}，评分{score:.0f}分"
        if score >= 85:
            reasoning += "，高分股上调可接受价"
        elif score < 75:
            reasoning += "，低分股下调可接受价"
        
        return {
            'ideal_price': ideal_price,
            'acceptable_price': acceptable_price,
            'abandon_price': abandon_price,
            'reasoning': reasoning,
        }


class PositionAdvisor:
    """
    仓位顾问 - 计算每只股票的买入仓位
    """
    
    def __init__(self, total_capital: float = 70000, min_score_threshold: float = 70):
        self.total_capital = total_capital
        self.max_single_position = 0.30  # 单只最大30%
        self.max_total_position = 0.80   # 总仓位最大80%
        self.min_score_threshold = min_score_threshold  # 最低评分阈值
    
    def calculate_position(self,
                          score: float,
                          stock_price: float,
                          market_env: str = "震荡",
                          sentiment: str = "中性") -> Dict:
        """
        计算建议仓位
        
        Args:
            score: 明日潜力评分 (0-100)
            stock_price: 股票价格
            market_env: 大盘环境 (强势/震荡/弱势)
            sentiment: 市场情绪 (乐观/中性/恐慌)
        
        Returns:
            {
                'position_ratio': float,   # 仓位比例 (0-0.3)
                'position_amount': float,  # 买入金额
                'shares': int,             # 买入股数(100的整数倍)
                'reasoning': str           # 计算说明
            }
        """
        # 评分低于阈值不建议买入
        if score < self.min_score_threshold:
            return {
                'position_ratio': 0,
                'position_amount': 0,
                'shares': 0,
                'reasoning': f"评分{score:.0f}分低于{self.min_score_threshold}分阈值，不建议买入",
            }
        
        # 基础仓位映射
        if score >= 90:
            base_ratio = 0.30
        elif score >= 85:
            base_ratio = 0.25
        elif score >= 80:
            base_ratio = 0.20
        elif score >= 75:
            base_ratio = 0.15
        else:  # 70-75
            base_ratio = 0.10
        
        # 环境调整系数
        env_multiplier = {
            "强势": 1.2,
            "震荡": 1.0,
            "弱势": 0.6,
        }.get(market_env, 1.0)
        
        # 情绪调整系数
        sentiment_multiplier = {
            "乐观": 1.1,
            "中性": 1.0,
            "恐慌": 0.5,
        }.get(sentiment, 1.0)
        
        # 计算最终仓位比例
        position_ratio = base_ratio * env_multiplier * sentiment_multiplier
        
        # 限制单只最大仓位
        position_ratio = min(position_ratio, self.max_single_position)
        
        # 计算买入金额
        position_amount = self.total_capital * position_ratio
        
        # 计算买入股数 (100的整数倍)
        shares = int(position_amount / stock_price / 100) * 100
        
        # 重新计算实际买入金额
        actual_amount = shares * stock_price
        actual_ratio = actual_amount / self.total_capital
        
        reasoning = f"评分{score:.0f}分，基础仓位{base_ratio*100:.0f}%"
        if env_multiplier != 1.0:
            reasoning += f"，{market_env}环境×{env_multiplier}"
        if sentiment_multiplier != 1.0:
            reasoning += f"，{sentiment}情绪×{sentiment_multiplier}"
        
        return {
            'position_ratio': round(actual_ratio, 4),
            'position_amount': round(actual_amount, 2),
            'shares': shares,
            'reasoning': reasoning,
        }
    
    def validate_total_position(self, positions: list) -> Dict:
        """
        验证总仓位是否超限
        
        Args:
            positions: 各股票仓位列表 [{'ratio': 0.2, 'amount': 14000}, ...]
        
        Returns:
            {
                'is_valid': bool,
                'total_ratio': float,
                'total_amount': float,
                'adjustment_needed': bool,
                'message': str,
            }
        """
        total_ratio = sum(p.get('ratio', 0) for p in positions)
        total_amount = sum(p.get('amount', 0) for p in positions)
        
        is_valid = total_ratio <= self.max_total_position
        
        return {
            'is_valid': is_valid,
            'total_ratio': round(total_ratio, 4),
            'total_amount': round(total_amount, 2),
            'adjustment_needed': not is_valid,
            'message': f"总仓位{total_ratio*100:.1f}%，{'符合' if is_valid else '超过'}80%限制",
        }


class StopLossCalculator:
    """
    止损计算器
    """
    
    def __init__(self):
        self.default_stop_ratio = 0.05   # 默认止损5%
        self.high_vol_stop_ratio = 0.07  # 高波动止损7%
        self.low_vol_stop_ratio = 0.04   # 低波动止损4%
    
    def calculate_stop_loss(self,
                           entry_price: float,
                           position_amount: float,
                           volatility: float = 0.05) -> Dict:
        """
        计算止损价格
        
        Args:
            entry_price: 买入价
            position_amount: 买入金额
            volatility: 波动率
        
        Returns:
            {
                'stop_loss_price': float,  # 止损价
                'stop_loss_ratio': float,  # 止损比例
                'max_loss_amount': float,  # 最大亏损金额
                'reasoning': str
            }
        """
        # 根据波动率确定止损比例
        if volatility > 0.08:
            stop_ratio = self.high_vol_stop_ratio
            vol_type = "高波动"
        elif volatility < 0.04:
            stop_ratio = self.low_vol_stop_ratio
            vol_type = "低波动"
        else:
            stop_ratio = self.default_stop_ratio
            vol_type = "正常波动"
        
        # 计算止损价
        stop_loss_price = entry_price * (1 - stop_ratio)
        
        # 计算最大亏损金额
        max_loss_amount = position_amount * stop_ratio
        
        return {
            'stop_loss_price': round(stop_loss_price, 2),
            'stop_loss_ratio': stop_ratio,
            'max_loss_amount': round(max_loss_amount, 2),
            'reasoning': f"{vol_type}，止损比例{stop_ratio*100:.0f}%",
        }


class TakeProfitCalculator:
    """
    止盈计算器
    """
    
    def __init__(self):
        self.first_target_ratio = 0.05   # 第一止盈 +5%
        self.second_target_ratio = 0.10  # 第二止盈 +10%
        self.high_score_target_ratio = 0.15  # 高分股止盈 +15%
    
    def calculate_take_profit(self,
                             entry_price: float,
                             position_amount: float,
                             score: float = 80) -> Dict:
        """
        计算止盈价格
        
        Args:
            entry_price: 买入价
            position_amount: 买入金额
            score: 评分
        
        Returns:
            {
                'first_target': float,     # 第一止盈位 (+5%)
                'second_target': float,    # 第二止盈位 (+10%)
                'first_profit': float,     # 第一目标盈利金额
                'second_profit': float,    # 第二目标盈利金额
                'reasoning': str
            }
        """
        # 计算止盈价
        first_target = entry_price * (1 + self.first_target_ratio)
        
        # 高分股可以持有到更高
        if score >= 90:
            second_target = entry_price * (1 + self.high_score_target_ratio)
            target_desc = "+15%"
        else:
            second_target = entry_price * (1 + self.second_target_ratio)
            target_desc = "+10%"
        
        # 计算盈利金额
        first_profit = position_amount * self.first_target_ratio
        second_profit = position_amount * (self.second_target_ratio if score < 90 else self.high_score_target_ratio)
        
        return {
            'first_target': round(first_target, 2),
            'second_target': round(second_target, 2),
            'first_profit': round(first_profit, 2),
            'second_profit': round(second_profit, 2),
            'reasoning': f"第一止盈+5%，第二止盈{target_desc}",
        }


class SmartStopLoss:
    """
    智能止损器 - 解决固定止损问题
    
    核心逻辑:
    - 技术止损优先(跌破关键位)
    - 固定比例兜底(防灾难)
    - 根据波动率动态调整
    
    止损 = MAX(买入价×0.95, 昨日最低价, 5日均线)
    """
    
    def __init__(self):
        self.default_stop_ratio = 0.05   # 默认止损5%
        self.high_vol_stop_ratio = 0.07  # 高波动止损7%
        self.low_vol_stop_ratio = 0.04   # 低波动止损4%
    
    def calculate_smart_stop(self,
                            entry_price: float,
                            prev_low: float,
                            ma5: float,
                            ma10: float = None,
                            volatility: float = 0.05) -> Dict:
        """
        计算智能止损价
        
        核心公式: 止损 = MAX(买入价×0.95, 昨日最低价, 5日均线)
        
        Args:
            entry_price: 买入价
            prev_low: 昨日最低价
            ma5: 5日均线
            ma10: 10日均线 (可选，用于额外参考)
            volatility: 波动率(近5日振幅平均)
        
        Returns:
            {
                'stop_price': float,        # 最终止损价
                'stop_type': str,           # 止损类型
                'stop_ratio': float,        # 止损比例
                'technical_stop': float,    # 技术止损价
                'fixed_stop': float,        # 固定止损价
                'reasoning': str            # 说明
            }
        """
        # 1. 计算固定止损价 (根据波动率调整)
        if volatility > 0.08:
            fixed_ratio = self.high_vol_stop_ratio
        elif volatility < 0.04:
            fixed_ratio = self.low_vol_stop_ratio
        else:
            fixed_ratio = self.default_stop_ratio
        
        fixed_stop = entry_price * (1 - fixed_ratio)
        
        # 2. 计算技术止损价
        # 取 昨日最低价、5日均线 中低于买入价的最高值作为支撑
        support_levels = [prev_low, ma5]
        if ma10 is not None:
            support_levels.append(ma10)
        
        # 过滤出低于买入价的支撑位
        valid_supports = [s for s in support_levels if s < entry_price]
        
        if valid_supports:
            technical_stop = max(valid_supports)
        else:
            # 如果所有支撑位都高于买入价，使用固定止损
            technical_stop = fixed_stop
        
        # 3. 最终止损价 = MAX(技术止损, 固定止损)
        # 确保不会因为技术位太低而承受过大亏损
        final_stop = max(technical_stop, fixed_stop)
        
        # 4. 确定止损类型
        if final_stop == technical_stop and technical_stop > fixed_stop:
            stop_type = '技术止损(跌破支撑)'
        else:
            stop_type = '固定止损(兜底)'
        
        # 计算实际止损比例
        stop_ratio = (entry_price - final_stop) / entry_price
        
        return {
            'stop_price': round(final_stop, 2),
            'stop_type': stop_type,
            'stop_ratio': round(stop_ratio, 4),
            'technical_stop': round(technical_stop, 2),
            'fixed_stop': round(fixed_stop, 2),
            'reasoning': f'波动率{volatility*100:.1f}%，技术支撑{technical_stop:.2f}，固定止损{fixed_stop:.2f}'
        }
    
    def calculate_max_loss(self, 
                          entry_price: float,
                          stop_price: float,
                          shares: int) -> Dict:
        """
        计算最大亏损金额
        
        Args:
            entry_price: 买入价
            stop_price: 止损价
            shares: 持仓股数
        
        Returns:
            {
                'max_loss_amount': float,   # 最大亏损金额
                'max_loss_ratio': float,    # 最大亏损比例
                'position_value': float     # 持仓市值
            }
        """
        position_value = entry_price * shares
        max_loss_amount = (entry_price - stop_price) * shares
        max_loss_ratio = (entry_price - stop_price) / entry_price
        
        return {
            'max_loss_amount': round(max_loss_amount, 2),
            'max_loss_ratio': round(max_loss_ratio, 4),
            'position_value': round(position_value, 2)
        }


class TrailingStop:
    """
    移动止盈器 - 锁定利润，绝不让盈利变亏损
    
    核心逻辑:
    - 涨5%: 止盈线上移到成本价(保本)
    - 涨10%: 止盈线上移到+5%(锁定5%利润)
    - 涨15%: 止盈线上移到+10%(锁定10%利润)
    """
    
    def __init__(self):
        # 触发阈值
        self.threshold_level1 = 0.05   # 涨5%触发
        self.threshold_level2 = 0.10   # 涨10%触发
        self.threshold_level3 = 0.15   # 涨15%触发
        
        # 对应的止盈线位置
        self.stop_level1 = 0.00        # 成本价
        self.stop_level2 = 0.05        # +5%
        self.stop_level3 = 0.10        # +10%
    
    def calculate_trailing_stop(self,
                               entry_price: float,
                               current_price: float,
                               highest_price: float) -> Dict:
        """
        计算移动止盈价
        
        Args:
            entry_price: 买入价
            current_price: 当前价
            highest_price: 持仓期间最高价
        
        Returns:
            {
                'trailing_stop': float,  # 移动止盈价
                'locked_profit': float,  # 锁定利润比例
                'action': str,           # 建议操作
                'reasoning': str
            }
        """
        # 计算最高涨幅
        profit_ratio = (highest_price - entry_price) / entry_price
        
        if profit_ratio >= self.threshold_level3:
            # 涨15%以上，止盈线在+10%
            trailing_stop = entry_price * (1 + self.stop_level3)
            locked_profit = self.stop_level3
            action = '持有，止盈线+10%'
        elif profit_ratio >= self.threshold_level2:
            # 涨10%以上，止盈线在+5%
            trailing_stop = entry_price * (1 + self.stop_level2)
            locked_profit = self.stop_level2
            action = '持有，止盈线+5%'
        elif profit_ratio >= self.threshold_level1:
            # 涨5%以上，止盈线在成本价
            trailing_stop = entry_price * (1 + self.stop_level1)
            locked_profit = self.stop_level1
            action = '持有，保本止盈'
        else:
            # 未达5%，使用原止损
            trailing_stop = None
            locked_profit = None
            action = '未触发移动止盈'
        
        return {
            'trailing_stop': round(trailing_stop, 2) if trailing_stop else None,
            'locked_profit': locked_profit,
            'action': action,
            'reasoning': f'最高涨幅{profit_ratio*100:.1f}%，锁定利润{locked_profit*100 if locked_profit is not None else 0:.0f}%'
        }
    
    def should_sell(self,
                   entry_price: float,
                   current_price: float,
                   highest_price: float) -> Dict:
        """
        判断是否应该卖出
        
        Args:
            entry_price: 买入价
            current_price: 当前价
            highest_price: 持仓期间最高价
        
        Returns:
            {
                'should_sell': bool,     # 是否应该卖出
                'reason': str,           # 原因
                'trailing_stop': float   # 移动止盈价
            }
        """
        result = self.calculate_trailing_stop(entry_price, current_price, highest_price)
        
        if result['trailing_stop'] is None:
            return {
                'should_sell': False,
                'reason': '未触发移动止盈',
                'trailing_stop': None
            }
        
        # 当前价跌破移动止盈线
        if current_price < result['trailing_stop']:
            return {
                'should_sell': True,
                'reason': f'当前价{current_price:.2f}跌破移动止盈线{result["trailing_stop"]:.2f}',
                'trailing_stop': result['trailing_stop']
            }
        
        return {
            'should_sell': False,
            'reason': f'当前价{current_price:.2f}高于移动止盈线{result["trailing_stop"]:.2f}',
            'trailing_stop': result['trailing_stop']
        }
