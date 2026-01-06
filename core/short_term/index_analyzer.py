"""
大盘环境分析器 - Index Environment Analyzer

功能:
1. 分析上证指数趋势
2. 分析创业板指数趋势
3. 判断大盘强弱
4. 给出仓位建议
5. 计算大盘环境调整系数

作者: 卓越股票分析师
版本: 1.0
日期: 2026-01-06
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class IndexTrend(Enum):
    """指数趋势"""
    STRONG_UP = "强势上涨"
    UP = "上涨"
    CONSOLIDATION = "震荡整理"
    DOWN = "下跌"
    STRONG_DOWN = "强势下跌"


class MarketEnvironment(Enum):
    """市场环境"""
    BULL = "牛市"
    BULL_CONSOLIDATION = "牛市震荡"
    NEUTRAL = "震荡市"
    BEAR_CONSOLIDATION = "熊市反弹"
    BEAR = "熊市"


@dataclass
class IndexData:
    """指数数据"""
    code: str                      # 指数代码
    name: str                      # 指数名称
    price: float                   # 当前点位
    change_pct: float              # 涨跌幅%
    ma5: float                     # 5日均线
    ma10: float                    # 10日均线
    ma20: float                    # 20日均线
    ma60: float                    # 60日均线
    volume_ratio: float = 1.0      # 量比
    recent_changes: List[float] = None  # 近5日涨跌幅
    
    def __post_init__(self):
        if self.recent_changes is None:
            self.recent_changes = []


class IndexEnvironmentAnalyzer:
    """
    大盘环境分析器
    
    核心功能:
    1. 均线趋势分析 - 判断多头/空头排列
    2. 动量分析 - 近期涨跌趋势
    3. 量能分析 - 成交量配合
    4. 综合环境判断 - 给出市场环境等级
    5. 仓位建议 - 根据环境调整仓位
    """
    
    def __init__(self):
        """初始化分析器"""
        self.shanghai_index: Optional[IndexData] = None  # 上证指数
        self.chinext_index: Optional[IndexData] = None   # 创业板指
        self.last_update: Optional[datetime] = None
    
    def update_index_data(self, 
                         shanghai: IndexData = None,
                         chinext: IndexData = None):
        """
        更新指数数据
        
        Args:
            shanghai: 上证指数数据
            chinext: 创业板指数据
        """
        if shanghai:
            self.shanghai_index = shanghai
        if chinext:
            self.chinext_index = chinext
        self.last_update = datetime.now()
    
    def analyze_single_index(self, index: IndexData) -> Tuple[IndexTrend, float, Dict]:
        """
        分析单个指数
        
        Args:
            index: 指数数据
        
        Returns:
            (趋势, 强度得分0-100, 详细信息)
        """
        if not index:
            return IndexTrend.CONSOLIDATION, 50, {'error': '数据不足'}
        
        score = 50  # 基础分
        details = {}
        
        # 1. 均线排列分析 (40分)
        price = index.price
        ma5, ma10, ma20, ma60 = index.ma5, index.ma10, index.ma20, index.ma60
        
        if price > ma5 > ma10 > ma20 > ma60:
            ma_score = 40
            ma_status = "完美多头排列"
        elif price > ma5 > ma10 > ma20:
            ma_score = 35
            ma_status = "多头排列"
        elif price > ma5 > ma10:
            ma_score = 28
            ma_status = "短期多头"
        elif price > ma5:
            ma_score = 20
            ma_status = "站上5日线"
        elif price > ma20:
            ma_score = 15
            ma_status = "站上20日线"
        elif price > ma60:
            ma_score = 10
            ma_status = "站上60日线"
        elif price < ma5 < ma10 < ma20 < ma60:
            ma_score = 0
            ma_status = "完美空头排列"
        elif price < ma5 < ma10 < ma20:
            ma_score = 5
            ma_status = "空头排列"
        else:
            ma_score = 12
            ma_status = "均线缠绕"
        
        details['ma_status'] = ma_status
        details['ma_score'] = ma_score
        
        # 2. 当日涨跌分析 (30分)
        change = index.change_pct
        
        if change >= 2:
            change_score = 30
            change_status = "大涨"
        elif change >= 1:
            change_score = 25
            change_status = "上涨"
        elif change >= 0.3:
            change_score = 20
            change_status = "小涨"
        elif change >= -0.3:
            change_score = 15
            change_status = "平盘"
        elif change >= -1:
            change_score = 10
            change_status = "小跌"
        elif change >= -2:
            change_score = 5
            change_status = "下跌"
        else:
            change_score = 0
            change_status = "大跌"
        
        details['change_status'] = change_status
        details['change_score'] = change_score
        details['change_pct'] = change
        
        # 3. 近期趋势分析 (20分)
        if index.recent_changes:
            total_change = sum(index.recent_changes)
            positive_days = sum(1 for c in index.recent_changes if c > 0)
            
            if total_change > 5 and positive_days >= 4:
                trend_score = 20
                trend_status = "强势上涨"
            elif total_change > 2 and positive_days >= 3:
                trend_score = 16
                trend_status = "稳步上涨"
            elif total_change > 0:
                trend_score = 12
                trend_status = "小幅上涨"
            elif total_change > -2:
                trend_score = 8
                trend_status = "小幅调整"
            elif total_change > -5:
                trend_score = 4
                trend_status = "明显下跌"
            else:
                trend_score = 0
                trend_status = "大幅下跌"
        else:
            trend_score = 10
            trend_status = "数据不足"
        
        details['trend_status'] = trend_status
        details['trend_score'] = trend_score
        
        # 4. 量能分析 (10分)
        vr = index.volume_ratio
        
        if 1.2 <= vr <= 2.0 and change > 0:
            volume_score = 10
            volume_status = "放量上涨"
        elif vr < 1.0 and change < 0:
            volume_score = 8
            volume_status = "缩量调整"
        elif 0.8 <= vr <= 1.2:
            volume_score = 6
            volume_status = "量能正常"
        elif vr > 2.0 and change < 0:
            volume_score = 2
            volume_status = "放量下跌"
        else:
            volume_score = 4
            volume_status = "量能异常"
        
        details['volume_status'] = volume_status
        details['volume_score'] = volume_score
        
        # 综合得分
        total_score = ma_score + change_score + trend_score + volume_score
        
        # 确定趋势
        if total_score >= 80:
            trend = IndexTrend.STRONG_UP
        elif total_score >= 60:
            trend = IndexTrend.UP
        elif total_score >= 40:
            trend = IndexTrend.CONSOLIDATION
        elif total_score >= 20:
            trend = IndexTrend.DOWN
        else:
            trend = IndexTrend.STRONG_DOWN
        
        details['total_score'] = total_score
        
        return trend, total_score, details
    
    def analyze_market_environment(self) -> Tuple[MarketEnvironment, float, Dict]:
        """
        分析综合市场环境
        
        Returns:
            (市场环境, 环境得分0-100, 详细信息)
        """
        # 分析上证指数
        sh_trend, sh_score, sh_details = self.analyze_single_index(self.shanghai_index)
        
        # 分析创业板指
        cy_trend, cy_score, cy_details = self.analyze_single_index(self.chinext_index)
        
        # 综合得分 (上证60% + 创业板40%)
        if self.shanghai_index and self.chinext_index:
            total_score = sh_score * 0.6 + cy_score * 0.4
        elif self.shanghai_index:
            total_score = sh_score
        elif self.chinext_index:
            total_score = cy_score
        else:
            total_score = 50
        
        # 确定市场环境
        if total_score >= 75:
            env = MarketEnvironment.BULL
        elif total_score >= 60:
            env = MarketEnvironment.BULL_CONSOLIDATION
        elif total_score >= 40:
            env = MarketEnvironment.NEUTRAL
        elif total_score >= 25:
            env = MarketEnvironment.BEAR_CONSOLIDATION
        else:
            env = MarketEnvironment.BEAR
        
        details = {
            'shanghai': {
                'trend': sh_trend.value if sh_trend else None,
                'score': sh_score,
                'details': sh_details
            },
            'chinext': {
                'trend': cy_trend.value if cy_trend else None,
                'score': cy_score,
                'details': cy_details
            },
            'total_score': round(total_score, 1)
        }
        
        return env, total_score, details
    
    def get_position_suggestion(self) -> Dict:
        """
        获取仓位建议
        
        Returns:
            仓位建议字典
        """
        env, score, details = self.analyze_market_environment()
        
        suggestions = {
            MarketEnvironment.BULL: {
                'max_position': 100,
                'suggested_position': 80,
                'strategy': "积极进攻，重仓热点龙头",
                'risk_level': "低",
                'score_multiplier': 1.15  # 评分上调15%
            },
            MarketEnvironment.BULL_CONSOLIDATION: {
                'max_position': 80,
                'suggested_position': 60,
                'strategy': "顺势操作，关注回调机会",
                'risk_level': "中低",
                'score_multiplier': 1.08
            },
            MarketEnvironment.NEUTRAL: {
                'max_position': 60,
                'suggested_position': 40,
                'strategy': "精选个股，控制仓位",
                'risk_level': "中",
                'score_multiplier': 1.0
            },
            MarketEnvironment.BEAR_CONSOLIDATION: {
                'max_position': 40,
                'suggested_position': 20,
                'strategy': "轻仓试探，快进快出",
                'risk_level': "中高",
                'score_multiplier': 0.9
            },
            MarketEnvironment.BEAR: {
                'max_position': 20,
                'suggested_position': 0,
                'strategy': "空仓观望，保存实力",
                'risk_level': "高",
                'score_multiplier': 0.75
            }
        }
        
        suggestion = suggestions[env]
        
        return {
            'environment': env.value,
            'environment_score': round(score, 1),
            'max_position': suggestion['max_position'],
            'suggested_position': suggestion['suggested_position'],
            'strategy': suggestion['strategy'],
            'risk_level': suggestion['risk_level'],
            'score_multiplier': suggestion['score_multiplier'],
            'details': details
        }
    
    def calculate_environment_score(self, max_score: float = 10.0) -> Tuple[float, Dict]:
        """
        计算大盘环境维度得分 (用于综合评分)
        
        Args:
            max_score: 最高分
        
        Returns:
            (得分, 详细信息)
        """
        env, score, details = self.analyze_market_environment()
        
        # 环境得分映射到维度得分
        dimension_score = max_score * (score / 100)
        
        return round(dimension_score, 2), {
            'environment': env.value,
            'environment_score': score,
            'is_favorable': score >= 50,
            'score_multiplier': self.get_position_suggestion()['score_multiplier']
        }
    
    def print_status(self):
        """打印大盘环境状态"""
        env, score, details = self.analyze_market_environment()
        suggestion = self.get_position_suggestion()
        
        print("\n" + "=" * 50)
        print("📈 大盘环境分析报告")
        print("=" * 50)
        
        # 环境等级
        emoji = "🚀" if score >= 70 else "📈" if score >= 50 else "📊" if score >= 30 else "📉"
        print(f"\n{emoji} 市场环境: {env.value} (得分: {score:.1f})")
        
        # 上证指数
        if self.shanghai_index:
            sh = details['shanghai']
            print(f"\n🔵 上证指数: {self.shanghai_index.price:.2f} ({self.shanghai_index.change_pct:+.2f}%)")
            print(f"   趋势: {sh['trend']} | 得分: {sh['score']}")
            print(f"   均线: {sh['details'].get('ma_status', 'N/A')}")
        
        # 创业板指
        if self.chinext_index:
            cy = details['chinext']
            print(f"\n🟢 创业板指: {self.chinext_index.price:.2f} ({self.chinext_index.change_pct:+.2f}%)")
            print(f"   趋势: {cy['trend']} | 得分: {cy['score']}")
            print(f"   均线: {cy['details'].get('ma_status', 'N/A')}")
        
        # 仓位建议
        print(f"\n💡 仓位建议:")
        print(f"   建议仓位: {suggestion['suggested_position']}%")
        print(f"   最大仓位: {suggestion['max_position']}%")
        print(f"   策略: {suggestion['strategy']}")
        print(f"   风险等级: {suggestion['risk_level']}")
        
        print("=" * 50)


# 便捷函数
def create_index_analyzer() -> IndexEnvironmentAnalyzer:
    """创建大盘分析器"""
    return IndexEnvironmentAnalyzer()


def quick_index_check(sh_price: float, sh_change: float,
                     sh_ma5: float, sh_ma10: float, sh_ma20: float, sh_ma60: float,
                     cy_price: float = None, cy_change: float = None,
                     cy_ma5: float = None, cy_ma10: float = None,
                     cy_ma20: float = None, cy_ma60: float = None) -> Dict:
    """
    快速大盘检查
    
    Args:
        sh_*: 上证指数数据
        cy_*: 创业板指数据 (可选)
    
    Returns:
        大盘分析结果
    """
    analyzer = IndexEnvironmentAnalyzer()
    
    # 上证指数
    shanghai = IndexData(
        code="000001",
        name="上证指数",
        price=sh_price,
        change_pct=sh_change,
        ma5=sh_ma5,
        ma10=sh_ma10,
        ma20=sh_ma20,
        ma60=sh_ma60
    )
    
    # 创业板指
    chinext = None
    if cy_price is not None:
        chinext = IndexData(
            code="399006",
            name="创业板指",
            price=cy_price,
            change_pct=cy_change or 0,
            ma5=cy_ma5 or cy_price,
            ma10=cy_ma10 or cy_price,
            ma20=cy_ma20 or cy_price,
            ma60=cy_ma60 or cy_price
        )
    
    analyzer.update_index_data(shanghai, chinext)
    return analyzer.get_position_suggestion()
