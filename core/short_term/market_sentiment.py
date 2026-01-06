"""
市场情绪分析器 - Market Sentiment Analyzer

功能:
1. 计算涨跌停家数
2. 计算炸板率
3. 计算连板股数量
4. 计算市场赚钱效应指数
5. 输出市场情绪等级

作者: 卓越股票分析师
版本: 1.0
日期: 2026-01-06
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class SentimentLevel(Enum):
    """市场情绪等级"""
    EXTREME_FEAR = "极度恐慌"      # 0-20
    FEAR = "恐慌"                  # 20-40
    NEUTRAL = "中性"              # 40-60
    OPTIMISTIC = "乐观"           # 60-80
    EXTREME_GREED = "极度乐观"    # 80-100


@dataclass
class MarketSentimentData:
    """市场情绪数据"""
    # 涨跌停统计
    limit_up_count: int = 0        # 涨停家数
    limit_down_count: int = 0      # 跌停家数
    failed_limit_up: int = 0       # 炸板家数
    
    # 连板统计
    continuous_limit_up: Dict[int, int] = None  # {连板数: 家数}
    highest_board: int = 0         # 最高连板数
    
    # 市场宽度
    up_count: int = 0              # 上涨家数
    down_count: int = 0            # 下跌家数
    flat_count: int = 0            # 平盘家数
    
    # 成交统计
    total_volume: float = 0        # 总成交额(亿)
    avg_turnover: float = 0        # 平均换手率
    
    def __post_init__(self):
        if self.continuous_limit_up is None:
            self.continuous_limit_up = {}


class MarketSentimentAnalyzer:
    """
    市场情绪分析器
    
    核心指标:
    1. 涨跌停比 - 涨停/跌停比例
    2. 炸板率 - 炸板数/涨停数
    3. 连板高度 - 最高连板数
    4. 赚钱效应 - 上涨家数占比
    5. 情绪指数 - 综合情绪得分
    """
    
    def __init__(self):
        """初始化分析器"""
        self.sentiment_data: Optional[MarketSentimentData] = None
        self.last_update: Optional[datetime] = None
    
    def update_data(self, data: MarketSentimentData):
        """
        更新市场数据
        
        Args:
            data: 市场情绪数据
        """
        self.sentiment_data = data
        self.last_update = datetime.now()
    
    def calculate_limit_ratio(self) -> Tuple[float, str]:
        """
        计算涨跌停比
        
        Returns:
            (比值, 描述)
        """
        if not self.sentiment_data:
            return 1.0, "数据不足"
        
        up = self.sentiment_data.limit_up_count
        down = self.sentiment_data.limit_down_count
        
        if down == 0:
            if up > 0:
                return 10.0, "极度强势(无跌停)"
            return 1.0, "平静"
        
        ratio = up / down
        
        if ratio >= 5:
            desc = "极度强势"
        elif ratio >= 3:
            desc = "强势"
        elif ratio >= 1.5:
            desc = "偏强"
        elif ratio >= 0.7:
            desc = "均衡"
        elif ratio >= 0.3:
            desc = "偏弱"
        else:
            desc = "极度弱势"
        
        return round(ratio, 2), desc
    
    def calculate_failed_rate(self) -> Tuple[float, str]:
        """
        计算炸板率
        
        Returns:
            (炸板率%, 描述)
        """
        if not self.sentiment_data:
            return 0, "数据不足"
        
        up = self.sentiment_data.limit_up_count
        failed = self.sentiment_data.failed_limit_up
        
        if up == 0:
            return 0, "无涨停"
        
        rate = (failed / (up + failed)) * 100
        
        if rate <= 10:
            desc = "封板坚决"
        elif rate <= 20:
            desc = "封板较好"
        elif rate <= 30:
            desc = "封板一般"
        elif rate <= 50:
            desc = "炸板较多"
        else:
            desc = "炸板严重"
        
        return round(rate, 1), desc
    
    def calculate_continuous_board_score(self) -> Tuple[float, str]:
        """
        计算连板高度得分
        
        Returns:
            (得分, 描述)
        """
        if not self.sentiment_data:
            return 50, "数据不足"
        
        highest = self.sentiment_data.highest_board
        boards = self.sentiment_data.continuous_limit_up
        
        # 计算连板股总数
        total_continuous = sum(boards.values()) if boards else 0
        
        # 基础分 = 最高板数 * 10
        base_score = min(100, highest * 10)
        
        # 连板数量加成
        if total_continuous >= 10:
            base_score += 10
        elif total_continuous >= 5:
            base_score += 5
        
        if highest >= 7:
            desc = f"妖股活跃({highest}板)"
        elif highest >= 5:
            desc = f"连板活跃({highest}板)"
        elif highest >= 3:
            desc = f"连板正常({highest}板)"
        elif highest >= 2:
            desc = f"连板较少({highest}板)"
        else:
            desc = "无连板"
        
        return min(100, base_score), desc
    
    def calculate_profit_effect(self) -> Tuple[float, str]:
        """
        计算赚钱效应
        
        Returns:
            (赚钱效应%, 描述)
        """
        if not self.sentiment_data:
            return 50, "数据不足"
        
        up = self.sentiment_data.up_count
        down = self.sentiment_data.down_count
        flat = self.sentiment_data.flat_count
        total = up + down + flat
        
        if total == 0:
            return 50, "数据不足"
        
        profit_rate = (up / total) * 100
        
        if profit_rate >= 70:
            desc = "赚钱效应极好"
        elif profit_rate >= 55:
            desc = "赚钱效应较好"
        elif profit_rate >= 45:
            desc = "赚钱效应一般"
        elif profit_rate >= 30:
            desc = "亏钱效应"
        else:
            desc = "亏钱效应严重"
        
        return round(profit_rate, 1), desc
    
    def calculate_sentiment_index(self) -> Tuple[float, SentimentLevel, Dict]:
        """
        计算综合情绪指数
        
        Returns:
            (情绪指数0-100, 情绪等级, 详细信息)
        """
        if not self.sentiment_data:
            return 50, SentimentLevel.NEUTRAL, {'error': '数据不足'}
        
        # 1. 涨跌停比得分 (权重30%)
        limit_ratio, limit_desc = self.calculate_limit_ratio()
        limit_score = min(100, limit_ratio * 20)  # ratio=5 -> 100分
        
        # 2. 炸板率得分 (权重20%)
        failed_rate, failed_desc = self.calculate_failed_rate()
        failed_score = max(0, 100 - failed_rate * 2)  # 炸板率50% -> 0分
        
        # 3. 连板高度得分 (权重20%)
        board_score, board_desc = self.calculate_continuous_board_score()
        
        # 4. 赚钱效应得分 (权重30%)
        profit_rate, profit_desc = self.calculate_profit_effect()
        profit_score = profit_rate  # 直接使用百分比
        
        # 综合得分
        sentiment_index = (
            limit_score * 0.30 +
            failed_score * 0.20 +
            board_score * 0.20 +
            profit_score * 0.30
        )
        
        # 确定情绪等级
        if sentiment_index >= 80:
            level = SentimentLevel.EXTREME_GREED
        elif sentiment_index >= 60:
            level = SentimentLevel.OPTIMISTIC
        elif sentiment_index >= 40:
            level = SentimentLevel.NEUTRAL
        elif sentiment_index >= 20:
            level = SentimentLevel.FEAR
        else:
            level = SentimentLevel.EXTREME_FEAR
        
        details = {
            'limit_ratio': {'value': limit_ratio, 'desc': limit_desc, 'score': limit_score},
            'failed_rate': {'value': failed_rate, 'desc': failed_desc, 'score': failed_score},
            'board_height': {'value': self.sentiment_data.highest_board, 'desc': board_desc, 'score': board_score},
            'profit_effect': {'value': profit_rate, 'desc': profit_desc, 'score': profit_score},
            'limit_up_count': self.sentiment_data.limit_up_count,
            'limit_down_count': self.sentiment_data.limit_down_count,
            'up_count': self.sentiment_data.up_count,
            'down_count': self.sentiment_data.down_count
        }
        
        return round(sentiment_index, 1), level, details
    
    def get_trading_suggestion(self) -> Dict:
        """
        根据市场情绪给出交易建议
        
        Returns:
            交易建议字典
        """
        index, level, details = self.calculate_sentiment_index()
        
        suggestions = {
            SentimentLevel.EXTREME_GREED: {
                'position': "可满仓",
                'strategy': "积极进攻，追涨龙头",
                'risk': "注意高位风险，设好止盈",
                'score_adjustment': 1.1  # 评分上调10%
            },
            SentimentLevel.OPTIMISTIC: {
                'position': "7-8成仓",
                'strategy': "顺势操作，关注热点",
                'risk': "控制追高，分批建仓",
                'score_adjustment': 1.05
            },
            SentimentLevel.NEUTRAL: {
                'position': "5成仓",
                'strategy': "精选个股，控制仓位",
                'risk': "观望为主，等待方向",
                'score_adjustment': 1.0
            },
            SentimentLevel.FEAR: {
                'position': "3成仓以下",
                'strategy': "防守为主，轻仓试探",
                'risk': "严格止损，不抄底",
                'score_adjustment': 0.9
            },
            SentimentLevel.EXTREME_FEAR: {
                'position': "空仓观望",
                'strategy': "休息等待，保存实力",
                'risk': "坚决不操作，等待企稳",
                'score_adjustment': 0.8
            }
        }
        
        suggestion = suggestions[level]
        
        return {
            'sentiment_index': index,
            'sentiment_level': level.value,
            'position_suggestion': suggestion['position'],
            'strategy': suggestion['strategy'],
            'risk_warning': suggestion['risk'],
            'score_adjustment': suggestion['score_adjustment'],
            'details': details
        }
    
    def calculate_sentiment_score(self, max_score: float = 10.0) -> Tuple[float, Dict]:
        """
        计算情绪维度得分 (用于综合评分)
        
        Args:
            max_score: 最高分
        
        Returns:
            (得分, 详细信息)
        """
        index, level, details = self.calculate_sentiment_index()
        
        # 情绪指数直接映射到得分
        score = max_score * (index / 100)
        
        return round(score, 2), {
            'sentiment_index': index,
            'sentiment_level': level.value,
            'is_favorable': index >= 50,
            'details': details
        }
    
    def print_status(self):
        """打印市场情绪状态"""
        if not self.sentiment_data:
            print("⚠️ 暂无市场数据")
            return
        
        index, level, details = self.calculate_sentiment_index()
        suggestion = self.get_trading_suggestion()
        
        print("\n" + "=" * 50)
        print("📊 市场情绪分析报告")
        print("=" * 50)
        
        # 情绪指数
        emoji = "🔥" if index >= 70 else "😊" if index >= 50 else "😐" if index >= 30 else "😰"
        print(f"\n{emoji} 情绪指数: {index} ({level.value})")
        
        # 详细指标
        print(f"\n📈 涨跌停比: {details['limit_ratio']['value']} ({details['limit_ratio']['desc']})")
        print(f"   涨停: {details['limit_up_count']}家 | 跌停: {details['limit_down_count']}家")
        
        print(f"\n💥 炸板率: {details['failed_rate']['value']}% ({details['failed_rate']['desc']})")
        
        print(f"\n🎯 连板高度: {details['board_height']['desc']}")
        
        print(f"\n💰 赚钱效应: {details['profit_effect']['value']}% ({details['profit_effect']['desc']})")
        print(f"   上涨: {details['up_count']}家 | 下跌: {details['down_count']}家")
        
        # 交易建议
        print(f"\n💡 交易建议:")
        print(f"   仓位: {suggestion['position_suggestion']}")
        print(f"   策略: {suggestion['strategy']}")
        print(f"   风险: {suggestion['risk_warning']}")
        
        print("=" * 50)


# 便捷函数
def create_sentiment_analyzer() -> MarketSentimentAnalyzer:
    """创建情绪分析器"""
    return MarketSentimentAnalyzer()


def quick_sentiment_check(limit_up: int, limit_down: int, 
                         up_count: int, down_count: int,
                         failed_limit_up: int = 0,
                         highest_board: int = 0) -> Dict:
    """
    快速情绪检查
    
    Args:
        limit_up: 涨停家数
        limit_down: 跌停家数
        up_count: 上涨家数
        down_count: 下跌家数
        failed_limit_up: 炸板家数
        highest_board: 最高连板数
    
    Returns:
        情绪分析结果
    """
    analyzer = MarketSentimentAnalyzer()
    
    data = MarketSentimentData(
        limit_up_count=limit_up,
        limit_down_count=limit_down,
        failed_limit_up=failed_limit_up,
        up_count=up_count,
        down_count=down_count,
        highest_board=highest_board
    )
    
    analyzer.update_data(data)
    return analyzer.get_trading_suggestion()
