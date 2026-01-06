"""
短线散户专用评分系统 - Short-Term Retail Investor Scoring System

专为短线散户设计的量化选股系统，解决传统评分系统的以下问题：
1. 增加热点题材维度
2. 增加资金流向分析
3. 增加趋势强度判断
4. 增加板块联动分析
5. 动态调整参数
6. 提供买卖时机建议

作者: 卓越股票分析师
版本: 3.0 (短线专用版)
日期: 2026-01-06
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import math


# ==================== 配置类 ====================

@dataclass
class ShortTermWeights:
    """短线评分权重配置 - 专为短线优化"""
    hot_topic_score: float = 25.0      # 热点题材得分 (新增，最重要)
    capital_flow_score: float = 20.0   # 资金流向得分 (新增)
    trend_score: float = 20.0          # 趋势强度得分 (新增)
    momentum_score: float = 15.0       # 动量得分 (降低权重)
    volume_score: float = 10.0         # 成交量得分 (降低权重)
    sector_score: float = 10.0         # 板块地位得分 (新增)
    # 注意：移除了PE估值，短线不看估值
    
    def validate(self) -> bool:
        """验证权重总和是否为100"""
        total = (self.hot_topic_score + self.capital_flow_score + 
                self.trend_score + self.momentum_score + 
                self.volume_score + self.sector_score)
        return abs(total - 100.0) < 0.01


@dataclass
class HotTopic:
    """热点题材配置"""
    name: str                          # 题材名称
    keywords: List[str]                # 关键词
    weight: float                      # 权重加成 (1.0-1.5)
    start_date: str                    # 开始日期
    end_date: Optional[str] = None     # 结束日期 (None表示持续)
    description: str = ""              # 描述


@dataclass 
class MarketEnvironment:
    """市场环境配置"""
    market_trend: str = "neutral"      # bullish/bearish/neutral
    volatility_level: str = "normal"   # low/normal/high
    sector_rotation: List[str] = field(default_factory=list)  # 当前轮动板块


# ==================== 2026年1月热点题材配置 ====================

CURRENT_HOT_TOPICS = [
    HotTopic(
        name="CES科技展",
        keywords=["CES", "消费电子", "AI眼镜", "VR", "AR", "智能穿戴"],
        weight=1.5,
        start_date="2026-01-01",
        end_date="2026-01-15",
        description="CES 2026消费电子展，AI眼镜、VR/AR设备是焦点"
    ),
    HotTopic(
        name="AI人工智能",
        keywords=["AI", "人工智能", "大模型", "ChatGPT", "算力", "GPU"],
        weight=1.4,
        start_date="2025-01-01",
        end_date=None,
        description="AI长期主线，持续受资金关注"
    ),
    HotTopic(
        name="半导体国产替代",
        keywords=["半导体", "芯片", "封测", "光刻", "国产替代"],
        weight=1.35,
        start_date="2025-01-01",
        end_date=None,
        description="半导体国产替代，政策持续支持"
    ),
    HotTopic(
        name="机器人",
        keywords=["机器人", "人形机器人", "特斯拉", "Optimus"],
        weight=1.3,
        start_date="2025-10-01",
        end_date=None,
        description="人形机器人概念，特斯拉Optimus带动"
    ),
    HotTopic(
        name="新能源汽车",
        keywords=["新能源", "电动车", "锂电池", "充电桩"],
        weight=1.1,
        start_date="2024-01-01",
        end_date=None,
        description="新能源汽车，长期赛道但短期热度一般"
    ),
]

# 板块热度排名 (每日更新)
SECTOR_HEAT_RANKING = {
    "消费电子": 95,    # CES热点
    "半导体": 90,
    "人工智能": 88,
    "算力": 85,
    "5G通信": 75,
    "新能源科技": 65,
    "软件服务": 60,
    "生物医药科技": 55,
    "智能制造": 50,
}


# ==================== 核心评分系统 ====================

class ShortTermScoringSystem:
    """
    短线散户专用评分系统
    
    核心理念:
    1. 热点优先 - 短线炒的是题材和情绪
    2. 资金为王 - 主力资金流向决定涨跌
    3. 趋势跟随 - 顺势而为，不抄底
    4. 板块联动 - 龙头优于跟风
    5. 动态调整 - 根据市场环境调整参数
    """
    
    def __init__(self, 
                 weights: Optional[ShortTermWeights] = None,
                 hot_topics: Optional[List[HotTopic]] = None,
                 market_env: Optional[MarketEnvironment] = None):
        """
        初始化评分系统
        
        Args:
            weights: 自定义权重配置
            hot_topics: 热点题材列表
            market_env: 市场环境配置
        """
        self.weights = weights or ShortTermWeights()
        self.hot_topics = hot_topics or CURRENT_HOT_TOPICS
        self.market_env = market_env or MarketEnvironment()
        
        if not self.weights.validate():
            raise ValueError("权重总和必须为100%")
    
    # ==================== 1. 热点题材评分 (25%) ====================
    
    def hot_topic_score(self, 
                       stock_name: str, 
                       sector: str,
                       concepts: List[str] = None) -> Tuple[float, Dict]:
        """
        热点题材评分 - 短线最重要的维度
        
        评分逻辑:
        1. 检查股票是否属于当前热点题材
        2. 检查所属板块的热度排名
        3. 多重热点叠加加分
        
        Args:
            stock_name: 股票名称
            sector: 所属板块
            concepts: 概念标签列表
        
        Returns:
            (得分, 详细信息)
        """
        max_score = 25.0
        base_score = 0.0
        matched_topics = []
        
        # 1. 检查热点题材匹配
        search_text = f"{stock_name} {sector} {' '.join(concepts or [])}"
        
        for topic in self.hot_topics:
            # 检查是否在有效期内
            if topic.end_date:
                end = datetime.strptime(topic.end_date, "%Y-%m-%d")
                if datetime.now() > end:
                    continue
            
            # 检查关键词匹配
            for keyword in topic.keywords:
                if keyword in search_text:
                    matched_topics.append({
                        'name': topic.name,
                        'weight': topic.weight,
                        'keyword': keyword
                    })
                    break
        
        # 2. 计算热点得分
        if matched_topics:
            # 取最高权重的热点
            max_weight = max(t['weight'] for t in matched_topics)
            base_score = max_score * (0.6 + 0.4 * (max_weight - 1) / 0.5)
            
            # 多重热点叠加加分 (每多一个热点+5%)
            if len(matched_topics) > 1:
                bonus = min(0.2, (len(matched_topics) - 1) * 0.05)
                base_score *= (1 + bonus)
        else:
            # 非热点股票，基础分较低
            base_score = max_score * 0.3
        
        # 3. 板块热度调整
        sector_heat = SECTOR_HEAT_RANKING.get(sector, 50)
        sector_multiplier = 0.8 + 0.4 * (sector_heat / 100)
        
        final_score = min(max_score, base_score * sector_multiplier)
        
        details = {
            'matched_topics': matched_topics,
            'topic_count': len(matched_topics),
            'sector_heat': sector_heat,
            'is_hot': len(matched_topics) > 0,
            'category': self._categorize_hot_topic(len(matched_topics), sector_heat)
        }
        
        return round(final_score, 2), details
    
    # ==================== 2. 资金流向评分 (20%) ====================
    
    def capital_flow_score(self,
                          main_net_inflow: float,
                          large_order_ratio: float,
                          north_flow: Optional[float] = None) -> Tuple[float, Dict]:
        """
        资金流向评分 - 主力资金决定涨跌
        
        评分逻辑:
        1. 主力净流入/流出金额
        2. 大单买卖比例
        3. 北向资金动向 (可选)
        
        Args:
            main_net_inflow: 主力净流入金额 (万元，正为流入，负为流出)
            large_order_ratio: 大单买入占比 (0-100%)
            north_flow: 北向资金净流入 (万元，可选)
        
        Returns:
            (得分, 详细信息)
        """
        max_score = 20.0
        
        # 1. 主力净流入评分 (占60%)
        if main_net_inflow > 5000:  # 大幅流入 (>5000万)
            inflow_score = max_score * 0.6
        elif main_net_inflow > 1000:  # 明显流入 (1000-5000万)
            inflow_score = max_score * 0.6 * (0.7 + 0.3 * (main_net_inflow - 1000) / 4000)
        elif main_net_inflow > 0:  # 小幅流入 (0-1000万)
            inflow_score = max_score * 0.6 * (0.4 + 0.3 * main_net_inflow / 1000)
        elif main_net_inflow > -1000:  # 小幅流出 (0 ~ -1000万)
            inflow_score = max_score * 0.6 * (0.2 + 0.2 * (1000 + main_net_inflow) / 1000)
        elif main_net_inflow > -5000:  # 明显流出 (-1000 ~ -5000万)
            inflow_score = max_score * 0.6 * 0.15
        else:  # 大幅流出 (< -5000万)
            inflow_score = max_score * 0.6 * 0.05
        
        # 2. 大单买入比例评分 (占30%)
        if large_order_ratio >= 55:  # 大单买入占优
            large_score = max_score * 0.3
        elif large_order_ratio >= 50:  # 买卖均衡
            large_score = max_score * 0.3 * 0.7
        elif large_order_ratio >= 45:  # 略有卖压
            large_score = max_score * 0.3 * 0.4
        else:  # 大单卖出占优
            large_score = max_score * 0.3 * 0.1
        
        # 3. 北向资金评分 (占10%)
        if north_flow is not None:
            if north_flow > 0:
                north_score = max_score * 0.1 * min(1, north_flow / 1000)
            else:
                north_score = max_score * 0.1 * 0.2
        else:
            north_score = max_score * 0.1 * 0.5  # 无数据给中等分
        
        final_score = inflow_score + large_score + north_score
        
        # 资金流向分类
        if main_net_inflow > 1000 and large_order_ratio >= 50:
            flow_category = "主力加仓"
        elif main_net_inflow > 0:
            flow_category = "资金流入"
        elif main_net_inflow > -1000:
            flow_category = "资金均衡"
        elif main_net_inflow > -5000:
            flow_category = "资金流出"
        else:
            flow_category = "主力出货"
        
        details = {
            'main_net_inflow': main_net_inflow,
            'large_order_ratio': large_order_ratio,
            'north_flow': north_flow,
            'inflow_score': round(inflow_score, 2),
            'large_score': round(large_score, 2),
            'north_score': round(north_score, 2),
            'category': flow_category,
            'is_positive': main_net_inflow > 0 and large_order_ratio >= 50
        }
        
        return round(final_score, 2), details
    
    # ==================== 3. 趋势强度评分 (20%) ====================
    
    def trend_score(self,
                   price: float,
                   ma5: float,
                   ma10: float,
                   ma20: float,
                   recent_changes: List[float],
                   rsi: float = 50,
                   macd_status: str = "neutral") -> Tuple[float, Dict]:
        """
        趋势强度评分 - 顺势而为
        
        评分逻辑:
        1. 均线排列 (多头/空头)
        2. 近期涨跌趋势
        3. RSI位置
        4. MACD状态
        
        Args:
            price: 当前价格
            ma5: 5日均线
            ma10: 10日均线
            ma20: 20日均线
            recent_changes: 近5日涨跌幅列表
            rsi: RSI值 (0-100)
            macd_status: MACD状态 ("golden_cross"/"death_cross"/"neutral")
        
        Returns:
            (得分, 详细信息)
        """
        max_score = 20.0
        
        # 1. 均线排列评分 (占40%)
        if price > ma5 > ma10 > ma20:
            ma_score = max_score * 0.4  # 完美多头排列
            ma_status = "多头排列"
        elif price > ma5 > ma10:
            ma_score = max_score * 0.4 * 0.8  # 短期多头
            ma_status = "短期多头"
        elif price > ma5:
            ma_score = max_score * 0.4 * 0.5  # 站上5日线
            ma_status = "弱势反弹"
        elif price > ma20:
            ma_score = max_score * 0.4 * 0.3  # 站上20日线
            ma_status = "震荡整理"
        else:
            ma_score = max_score * 0.4 * 0.1  # 空头排列
            ma_status = "空头排列"
        
        # 2. 近期趋势评分 (占30%)
        if recent_changes:
            # 计算近期涨跌
            total_change = sum(recent_changes)
            positive_days = sum(1 for c in recent_changes if c > 0)
            
            if total_change > 10 and positive_days >= 4:
                trend_score = max_score * 0.3  # 强势上涨
                trend_status = "强势上涨"
            elif total_change > 5 and positive_days >= 3:
                trend_score = max_score * 0.3 * 0.8  # 稳步上涨
                trend_status = "稳步上涨"
            elif total_change > 0:
                trend_score = max_score * 0.3 * 0.5  # 小幅上涨
                trend_status = "小幅上涨"
            elif total_change > -5:
                trend_score = max_score * 0.3 * 0.3  # 小幅调整
                trend_status = "小幅调整"
            else:
                trend_score = max_score * 0.3 * 0.1  # 明显下跌
                trend_status = "明显下跌"
        else:
            trend_score = max_score * 0.3 * 0.5
            trend_status = "数据不足"
        
        # 3. RSI评分 (占15%)
        if 50 <= rsi <= 70:
            rsi_score = max_score * 0.15  # 健康区间
            rsi_status = "健康"
        elif 40 <= rsi < 50:
            rsi_score = max_score * 0.15 * 0.7  # 偏弱
            rsi_status = "偏弱"
        elif 70 < rsi <= 80:
            rsi_score = max_score * 0.15 * 0.6  # 偏强，注意回调
            rsi_status = "偏强"
        elif 30 <= rsi < 40:
            rsi_score = max_score * 0.15 * 0.5  # 超卖区
            rsi_status = "超卖"
        else:
            rsi_score = max_score * 0.15 * 0.3  # 极端区域
            rsi_status = "极端"
        
        # 4. MACD评分 (占15%)
        if macd_status == "golden_cross":
            macd_score = max_score * 0.15  # 金叉
        elif macd_status == "death_cross":
            macd_score = max_score * 0.15 * 0.2  # 死叉
        else:
            macd_score = max_score * 0.15 * 0.5  # 中性
        
        final_score = ma_score + trend_score + rsi_score + macd_score
        
        details = {
            'ma_status': ma_status,
            'trend_status': trend_status,
            'rsi': rsi,
            'rsi_status': rsi_status,
            'macd_status': macd_status,
            'recent_total_change': sum(recent_changes) if recent_changes else 0,
            'positive_days': sum(1 for c in recent_changes if c > 0) if recent_changes else 0,
            'is_uptrend': ma_status in ["多头排列", "短期多头"] and trend_status in ["强势上涨", "稳步上涨"]
        }
        
        return round(final_score, 2), details
    
    # ==================== 4. 动量评分 (15%) ====================
    
    def momentum_score(self, 
                      change_pct: float,
                      turnover_rate: float) -> Tuple[float, Dict]:
        """
        动量评分 - 简化版，降低权重
        
        Args:
            change_pct: 涨跌幅
            turnover_rate: 换手率
        
        Returns:
            (得分, 详细信息)
        """
        max_score = 15.0
        
        # 涨幅评分 (占70%)
        if 2 <= change_pct <= 5:
            change_score = max_score * 0.7  # 理想涨幅
            change_status = "理想涨幅"
        elif 5 < change_pct <= 8:
            change_score = max_score * 0.7 * 0.8  # 强势涨幅
            change_status = "强势涨幅"
        elif 0 < change_pct < 2:
            change_score = max_score * 0.7 * 0.6  # 温和上涨
            change_status = "温和上涨"
        elif change_pct > 8:
            change_score = max_score * 0.7 * 0.4  # 涨幅过大
            change_status = "涨幅过大"
        elif -2 <= change_pct <= 0:
            change_score = max_score * 0.7 * 0.3  # 小幅调整
            change_status = "小幅调整"
        else:
            change_score = max_score * 0.7 * 0.1  # 明显下跌
            change_status = "明显下跌"
        
        # 换手率评分 (占30%)
        if 3 <= turnover_rate <= 8:
            turnover_score = max_score * 0.3  # 活跃
            turnover_status = "活跃"
        elif 1 <= turnover_rate < 3:
            turnover_score = max_score * 0.3 * 0.6  # 正常
            turnover_status = "正常"
        elif 8 < turnover_rate <= 15:
            turnover_score = max_score * 0.3 * 0.7  # 高换手
            turnover_status = "高换手"
        else:
            turnover_score = max_score * 0.3 * 0.3  # 异常
            turnover_status = "异常"
        
        final_score = change_score + turnover_score
        
        details = {
            'change_pct': change_pct,
            'change_status': change_status,
            'turnover_rate': turnover_rate,
            'turnover_status': turnover_status
        }
        
        return round(final_score, 2), details
    
    # ==================== 5. 成交量评分 (10%) ====================
    
    def volume_score(self,
                    volume_ratio: float,
                    change_pct: float) -> Tuple[float, Dict]:
        """
        成交量评分 - 量价配合
        
        Args:
            volume_ratio: 量比
            change_pct: 涨跌幅
        
        Returns:
            (得分, 详细信息)
        """
        max_score = 10.0
        
        # 基础量比评分
        if 1.5 <= volume_ratio <= 3:
            base_score = max_score * 0.8
            volume_status = "温和放量"
        elif 1 <= volume_ratio < 1.5:
            base_score = max_score * 0.5
            volume_status = "正常成交"
        elif 3 < volume_ratio <= 5:
            base_score = max_score * 0.6
            volume_status = "明显放量"
        elif volume_ratio < 1:
            base_score = max_score * 0.3
            volume_status = "缩量"
        else:
            base_score = max_score * 0.4
            volume_status = "异常放量"
        
        # 量价配合调整
        if change_pct > 0 and volume_ratio > 1.2:
            synergy = "量价齐升"
            base_score *= 1.2
        elif change_pct < 0 and volume_ratio < 1:
            synergy = "缩量调整"
            base_score *= 1.1
        elif change_pct > 0 and volume_ratio < 1:
            synergy = "缩量上涨"
            base_score *= 0.8
        elif change_pct < 0 and volume_ratio > 1.5:
            synergy = "放量下跌"
            base_score *= 0.5
        else:
            synergy = "正常"
        
        final_score = min(max_score, base_score)
        
        details = {
            'volume_ratio': volume_ratio,
            'volume_status': volume_status,
            'synergy': synergy
        }
        
        return round(final_score, 2), details
    
    # ==================== 6. 板块地位评分 (10%) ====================
    
    def sector_score(self,
                    sector: str,
                    sector_rank: int,
                    sector_change: float,
                    stock_rank_in_sector: int,
                    sector_stock_count: int) -> Tuple[float, Dict]:
        """
        板块地位评分 - 龙头优于跟风
        
        Args:
            sector: 板块名称
            sector_rank: 板块涨幅排名 (1-N)
            sector_change: 板块涨跌幅
            stock_rank_in_sector: 股票在板块内排名
            sector_stock_count: 板块股票总数
        
        Returns:
            (得分, 详细信息)
        """
        max_score = 10.0
        
        # 1. 板块强度评分 (占50%)
        if sector_rank <= 3:
            sector_strength_score = max_score * 0.5  # 热门板块
            sector_status = "热门板块"
        elif sector_rank <= 10:
            sector_strength_score = max_score * 0.5 * 0.7  # 活跃板块
            sector_status = "活跃板块"
        elif sector_rank <= 20:
            sector_strength_score = max_score * 0.5 * 0.4  # 一般板块
            sector_status = "一般板块"
        else:
            sector_strength_score = max_score * 0.5 * 0.2  # 冷门板块
            sector_status = "冷门板块"
        
        # 2. 板块内地位评分 (占50%)
        position_ratio = stock_rank_in_sector / max(sector_stock_count, 1)
        
        if position_ratio <= 0.1:  # 前10%
            position_score = max_score * 0.5
            position_status = "板块龙头"
        elif position_ratio <= 0.3:  # 前30%
            position_score = max_score * 0.5 * 0.7
            position_status = "板块强势股"
        elif position_ratio <= 0.5:  # 前50%
            position_score = max_score * 0.5 * 0.4
            position_status = "板块中游"
        else:
            position_score = max_score * 0.5 * 0.2
            position_status = "板块跟风股"
        
        final_score = sector_strength_score + position_score
        
        details = {
            'sector': sector,
            'sector_rank': sector_rank,
            'sector_change': sector_change,
            'sector_status': sector_status,
            'stock_rank_in_sector': stock_rank_in_sector,
            'position_status': position_status,
            'is_leader': position_ratio <= 0.1 and sector_rank <= 5
        }
        
        return round(final_score, 2), details
    
    # ==================== 辅助方法 ====================
    
    def _categorize_hot_topic(self, topic_count: int, sector_heat: int) -> str:
        """热点题材分类"""
        if topic_count >= 2 and sector_heat >= 80:
            return "超级热点"
        elif topic_count >= 1 and sector_heat >= 70:
            return "当前热点"
        elif topic_count >= 1 or sector_heat >= 60:
            return "潜在热点"
        elif sector_heat >= 50:
            return "一般题材"
        else:
            return "冷门题材"
    
    # ==================== 7. 综合评分计算 ====================
    
    def calculate_comprehensive_score(self,
                                      stock_code: str,
                                      stock_name: str,
                                      sector: str,
                                      price: float,
                                      change_pct: float,
                                      turnover_rate: float,
                                      volume_ratio: float,
                                      ma5: float,
                                      ma10: float,
                                      ma20: float,
                                      main_net_inflow: float,
                                      large_order_ratio: float,
                                      sector_rank: int,
                                      stock_rank_in_sector: int,
                                      sector_stock_count: int,
                                      sector_change: float = 0,
                                      recent_changes: List[float] = None,
                                      rsi: float = 50,
                                      macd_status: str = "neutral",
                                      north_flow: float = None,
                                      concepts: List[str] = None) -> Dict:
        """
        计算综合评分 - 短线散户专用
        
        Returns:
            包含各项得分、综合得分、交易建议的完整字典
        """
        # 1. 热点题材得分 (25%)
        hot_score, hot_details = self.hot_topic_score(
            stock_name, sector, concepts
        )
        
        # 2. 资金流向得分 (20%)
        capital_score, capital_details = self.capital_flow_score(
            main_net_inflow, large_order_ratio, north_flow
        )
        
        # 3. 趋势强度得分 (20%)
        trend_score_val, trend_details = self.trend_score(
            price, ma5, ma10, ma20, 
            recent_changes or [], rsi, macd_status
        )
        
        # 4. 动量得分 (15%)
        momentum_score_val, momentum_details = self.momentum_score(
            change_pct, turnover_rate
        )
        
        # 5. 成交量得分 (10%)
        volume_score_val, volume_details = self.volume_score(
            volume_ratio, change_pct
        )
        
        # 6. 板块地位得分 (10%)
        sector_score_val, sector_details = self.sector_score(
            sector, sector_rank, sector_change,
            stock_rank_in_sector, sector_stock_count
        )
        
        # 计算加权综合得分
        comprehensive_score = (
            hot_score * (self.weights.hot_topic_score / 25) +
            capital_score * (self.weights.capital_flow_score / 20) +
            trend_score_val * (self.weights.trend_score / 20) +
            momentum_score_val * (self.weights.momentum_score / 15) +
            volume_score_val * (self.weights.volume_score / 10) +
            sector_score_val * (self.weights.sector_score / 10)
        )
        
        # 质量等级评定
        quality_grade = self._determine_quality_grade(comprehensive_score)
        
        # 生成交易信号
        trading_signal = self.generate_trading_signal(
            comprehensive_score, hot_details, capital_details, 
            trend_details, momentum_details
        )
        
        return {
            'stock_code': stock_code,
            'stock_name': stock_name,
            'sector': sector,
            'comprehensive_score': round(comprehensive_score, 2),
            'quality_grade': quality_grade,
            'scores': {
                'hot_topic': round(hot_score, 2),
                'capital_flow': round(capital_score, 2),
                'trend': round(trend_score_val, 2),
                'momentum': round(momentum_score_val, 2),
                'volume': round(volume_score_val, 2),
                'sector': round(sector_score_val, 2)
            },
            'details': {
                'hot_topic': hot_details,
                'capital_flow': capital_details,
                'trend': trend_details,
                'momentum': momentum_details,
                'volume': volume_details,
                'sector': sector_details
            },
            'trading_signal': trading_signal,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def _determine_quality_grade(self, score: float) -> str:
        """确定质量等级 - 短线标准"""
        if score >= 90:
            return "S+ (强烈推荐)"
        elif score >= 85:
            return "S (推荐买入)"
        elif score >= 80:
            return "A+ (可以买入)"
        elif score >= 75:
            return "A (观望为主)"
        elif score >= 70:
            return "B+ (谨慎参与)"
        elif score >= 65:
            return "B (不建议)"
        elif score >= 60:
            return "C (回避)"
        else:
            return "D (坚决回避)"
    
    # ==================== 8. 交易信号生成 ====================
    
    def generate_trading_signal(self,
                               comprehensive_score: float,
                               hot_details: Dict,
                               capital_details: Dict,
                               trend_details: Dict,
                               momentum_details: Dict) -> Dict:
        """
        生成交易信号 - 买卖时机建议
        
        综合多个维度判断是否适合买入/卖出
        """
        # 买入条件检查
        buy_conditions = []
        sell_conditions = []
        
        # 1. 综合得分条件
        if comprehensive_score >= 85:
            buy_conditions.append("综合得分优秀(≥85)")
        elif comprehensive_score < 65:
            sell_conditions.append("综合得分较低(<65)")
        
        # 2. 热点题材条件
        if hot_details.get('is_hot'):
            buy_conditions.append(f"属于当前热点({hot_details.get('category')})")
        elif hot_details.get('category') == "冷门题材":
            sell_conditions.append("非热点题材")
        
        # 3. 资金流向条件
        if capital_details.get('is_positive'):
            buy_conditions.append(f"资金流入({capital_details.get('category')})")
        elif capital_details.get('category') in ["资金流出", "主力出货"]:
            sell_conditions.append(f"资金流出({capital_details.get('category')})")
        
        # 4. 趋势条件
        if trend_details.get('is_uptrend'):
            buy_conditions.append(f"趋势向上({trend_details.get('ma_status')})")
        elif trend_details.get('ma_status') == "空头排列":
            sell_conditions.append("趋势向下(空头排列)")
        
        # 5. 动量条件
        if momentum_details.get('change_status') in ["理想涨幅", "温和上涨"]:
            buy_conditions.append(f"涨幅适中({momentum_details.get('change_pct'):.1f}%)")
        elif momentum_details.get('change_status') == "涨幅过大":
            sell_conditions.append("涨幅过大，追高风险")
        
        # 综合判断
        buy_score = len(buy_conditions)
        sell_score = len(sell_conditions)
        
        if buy_score >= 4 and sell_score == 0:
            signal = "强烈买入"
            signal_strength = 5
            action = "建议明天开盘买入"
        elif buy_score >= 3 and sell_score <= 1:
            signal = "建议买入"
            signal_strength = 4
            action = "可以考虑买入，注意仓位控制"
        elif buy_score >= 2 and sell_score <= 1:
            signal = "可以关注"
            signal_strength = 3
            action = "加入自选观察，等待更好时机"
        elif sell_score >= 3:
            signal = "建议卖出"
            signal_strength = -2
            action = "如持有建议减仓或清仓"
        elif sell_score >= 2:
            signal = "谨慎持有"
            signal_strength = -1
            action = "不建议新买入，持有者观望"
        else:
            signal = "中性观望"
            signal_strength = 0
            action = "暂不操作，继续观察"
        
        return {
            'signal': signal,
            'signal_strength': signal_strength,
            'action': action,
            'buy_conditions': buy_conditions,
            'sell_conditions': sell_conditions,
            'buy_score': buy_score,
            'sell_score': sell_score,
            'confidence': f"{min(100, buy_score * 20 + 20)}%" if buy_score > sell_score else f"{min(100, sell_score * 20 + 20)}%"
        }



# ==================== 买卖时机顾问 ====================

class TimingAdvisor:
    """
    买卖时机顾问 - 提供具体的入场/出场建议
    
    核心功能:
    1. 最佳买入时机判断
    2. 止损止盈位计算
    3. 仓位建议
    4. 风险提示
    """
    
    def __init__(self, risk_tolerance: str = "moderate"):
        """
        初始化时机顾问
        
        Args:
            risk_tolerance: 风险承受能力 ("conservative"/"moderate"/"aggressive")
        """
        self.risk_tolerance = risk_tolerance
        
        # 根据风险承受能力设置参数
        self.params = {
            "conservative": {
                "stop_loss_pct": 3.0,      # 止损比例
                "take_profit_pct": 5.0,    # 止盈比例
                "max_position_pct": 20.0,  # 最大仓位
                "min_score": 85            # 最低买入分数
            },
            "moderate": {
                "stop_loss_pct": 5.0,
                "take_profit_pct": 8.0,
                "max_position_pct": 30.0,
                "min_score": 80
            },
            "aggressive": {
                "stop_loss_pct": 8.0,
                "take_profit_pct": 15.0,
                "max_position_pct": 50.0,
                "min_score": 75
            }
        }[risk_tolerance]
    
    def get_entry_advice(self, 
                        current_price: float,
                        score_result: Dict,
                        support_level: float = None,
                        resistance_level: float = None) -> Dict:
        """
        获取入场建议
        
        Args:
            current_price: 当前价格
            score_result: 评分系统返回的结果
            support_level: 支撑位 (可选)
            resistance_level: 阻力位 (可选)
        
        Returns:
            入场建议字典
        """
        comprehensive_score = score_result.get('comprehensive_score', 0)
        trading_signal = score_result.get('trading_signal', {})
        
        # 判断是否适合买入
        can_buy = (
            comprehensive_score >= self.params['min_score'] and
            trading_signal.get('signal_strength', 0) >= 3
        )
        
        if not can_buy:
            return {
                'recommendation': "不建议买入",
                'reason': f"综合得分{comprehensive_score}分，未达到{self.params['min_score']}分的买入标准",
                'action': "继续观察或寻找其他机会"
            }
        
        # 计算止损止盈位
        stop_loss_price = current_price * (1 - self.params['stop_loss_pct'] / 100)
        take_profit_price = current_price * (1 + self.params['take_profit_pct'] / 100)
        
        # 如果有支撑位，调整止损
        if support_level and support_level < current_price:
            stop_loss_price = max(stop_loss_price, support_level * 0.98)
        
        # 如果有阻力位，调整止盈
        if resistance_level and resistance_level > current_price:
            take_profit_price = min(take_profit_price, resistance_level * 0.98)
        
        # 计算风险收益比
        risk = current_price - stop_loss_price
        reward = take_profit_price - current_price
        risk_reward_ratio = reward / risk if risk > 0 else 0
        
        # 仓位建议
        if comprehensive_score >= 90:
            position_pct = self.params['max_position_pct']
            position_advice = "可以重仓"
        elif comprehensive_score >= 85:
            position_pct = self.params['max_position_pct'] * 0.7
            position_advice = "中等仓位"
        else:
            position_pct = self.params['max_position_pct'] * 0.5
            position_advice = "轻仓试探"
        
        # 最佳买入时机
        if trading_signal.get('signal') == "强烈买入":
            entry_timing = "明天开盘可直接买入"
        else:
            entry_timing = "建议等待回调至支撑位附近再买入"
        
        return {
            'recommendation': "建议买入",
            'entry_timing': entry_timing,
            'current_price': current_price,
            'stop_loss_price': round(stop_loss_price, 2),
            'stop_loss_pct': f"-{self.params['stop_loss_pct']}%",
            'take_profit_price': round(take_profit_price, 2),
            'take_profit_pct': f"+{self.params['take_profit_pct']}%",
            'risk_reward_ratio': round(risk_reward_ratio, 2),
            'position_pct': round(position_pct, 1),
            'position_advice': position_advice,
            'risk_level': self.risk_tolerance,
            'key_points': [
                f"止损位: {stop_loss_price:.2f}元 (跌破必须止损)",
                f"止盈位: {take_profit_price:.2f}元 (可分批止盈)",
                f"建议仓位: {position_pct:.0f}% (不要满仓)",
                f"风险收益比: 1:{risk_reward_ratio:.1f}"
            ]
        }
    
    def get_exit_advice(self,
                       entry_price: float,
                       current_price: float,
                       holding_days: int,
                       score_result: Dict) -> Dict:
        """
        获取出场建议
        
        Args:
            entry_price: 买入价格
            current_price: 当前价格
            holding_days: 持有天数
            score_result: 最新评分结果
        
        Returns:
            出场建议字典
        """
        profit_pct = (current_price - entry_price) / entry_price * 100
        comprehensive_score = score_result.get('comprehensive_score', 0)
        trading_signal = score_result.get('trading_signal', {})
        
        # 止损检查
        if profit_pct <= -self.params['stop_loss_pct']:
            return {
                'recommendation': "立即止损",
                'reason': f"亏损已达{profit_pct:.1f}%，超过止损线{self.params['stop_loss_pct']}%",
                'action': "明天开盘卖出，不要犹豫",
                'urgency': "紧急"
            }
        
        # 止盈检查
        if profit_pct >= self.params['take_profit_pct']:
            return {
                'recommendation': "建议止盈",
                'reason': f"盈利已达{profit_pct:.1f}%，达到止盈目标{self.params['take_profit_pct']}%",
                'action': "可以分批卖出，先卖一半锁定利润",
                'urgency': "建议"
            }
        
        # 信号恶化检查
        if trading_signal.get('signal_strength', 0) <= -1:
            return {
                'recommendation': "建议减仓",
                'reason': f"技术信号转弱: {trading_signal.get('signal')}",
                'action': "减仓50%，保留底仓观察",
                'urgency': "注意"
            }
        
        # 持有时间过长
        if holding_days > 5 and profit_pct < 3:
            return {
                'recommendation': "考虑换股",
                'reason': f"持有{holding_days}天，盈利仅{profit_pct:.1f}%，效率较低",
                'action': "可以考虑换入更强势的股票",
                'urgency': "提示"
            }
        
        # 继续持有
        return {
            'recommendation': "继续持有",
            'reason': f"当前盈利{profit_pct:.1f}%，评分{comprehensive_score}分，趋势正常",
            'action': "保持持有，关注止损止盈位",
            'urgency': "正常"
        }


# ==================== 市场环境自适应 ====================

class MarketAdaptiveWeights:
    """
    市场环境自适应权重调整
    
    根据市场环境动态调整各维度权重
    """
    
    @staticmethod
    def get_adaptive_weights(market_env: MarketEnvironment) -> ShortTermWeights:
        """
        根据市场环境获取自适应权重
        
        Args:
            market_env: 市场环境配置
        
        Returns:
            调整后的权重配置
        """
        # 基础权重
        weights = ShortTermWeights()
        
        # 根据市场趋势调整
        if market_env.market_trend == "bullish":
            # 牛市：更重视动量和热点
            weights.hot_topic_score = 28.0
            weights.momentum_score = 18.0
            weights.capital_flow_score = 18.0
            weights.trend_score = 18.0
            weights.volume_score = 8.0
            weights.sector_score = 10.0
        elif market_env.market_trend == "bearish":
            # 熊市：更重视资金流向和趋势
            weights.hot_topic_score = 20.0
            weights.momentum_score = 12.0
            weights.capital_flow_score = 25.0
            weights.trend_score = 25.0
            weights.volume_score = 10.0
            weights.sector_score = 8.0
        
        # 根据波动率调整
        if market_env.volatility_level == "high":
            # 高波动：更重视资金流向
            weights.capital_flow_score += 3.0
            weights.momentum_score -= 3.0
        elif market_env.volatility_level == "low":
            # 低波动：更重视热点题材
            weights.hot_topic_score += 3.0
            weights.trend_score -= 3.0
        
        return weights


# ==================== 预设配置 ====================

# 激进型短线配置 (适合经验丰富的短线客)
AGGRESSIVE_SHORT_TERM_WEIGHTS = ShortTermWeights(
    hot_topic_score=30.0,    # 更重视热点
    capital_flow_score=20.0,
    trend_score=15.0,
    momentum_score=20.0,     # 更重视动量
    volume_score=10.0,
    sector_score=5.0
)

# 稳健型短线配置 (适合新手)
CONSERVATIVE_SHORT_TERM_WEIGHTS = ShortTermWeights(
    hot_topic_score=20.0,    # 降低热点权重
    capital_flow_score=25.0, # 更重视资金
    trend_score=25.0,        # 更重视趋势
    momentum_score=12.0,
    volume_score=10.0,
    sector_score=8.0
)

# 默认平衡配置
BALANCED_SHORT_TERM_WEIGHTS = ShortTermWeights()


# ==================== 便捷函数 ====================

def create_short_term_scorer(style: str = "balanced") -> ShortTermScoringSystem:
    """
    创建短线评分系统的便捷函数
    
    Args:
        style: 风格 ("aggressive"/"conservative"/"balanced")
    
    Returns:
        配置好的评分系统实例
    """
    weights_map = {
        "aggressive": AGGRESSIVE_SHORT_TERM_WEIGHTS,
        "conservative": CONSERVATIVE_SHORT_TERM_WEIGHTS,
        "balanced": BALANCED_SHORT_TERM_WEIGHTS
    }
    
    return ShortTermScoringSystem(weights=weights_map.get(style, BALANCED_SHORT_TERM_WEIGHTS))


def quick_score(stock_data: Dict) -> Dict:
    """
    快速评分函数 - 一键评分
    
    Args:
        stock_data: 包含所有必要字段的股票数据字典
    
    Returns:
        评分结果
    """
    scorer = create_short_term_scorer("balanced")
    
    return scorer.calculate_comprehensive_score(
        stock_code=stock_data.get('code', ''),
        stock_name=stock_data.get('name', ''),
        sector=stock_data.get('sector', ''),
        price=stock_data.get('price', 0),
        change_pct=stock_data.get('change_pct', 0),
        turnover_rate=stock_data.get('turnover_rate', 0),
        volume_ratio=stock_data.get('volume_ratio', 1),
        ma5=stock_data.get('ma5', 0),
        ma10=stock_data.get('ma10', 0),
        ma20=stock_data.get('ma20', 0),
        main_net_inflow=stock_data.get('main_net_inflow', 0),
        large_order_ratio=stock_data.get('large_order_ratio', 50),
        sector_rank=stock_data.get('sector_rank', 10),
        stock_rank_in_sector=stock_data.get('stock_rank_in_sector', 5),
        sector_stock_count=stock_data.get('sector_stock_count', 20),
        sector_change=stock_data.get('sector_change', 0),
        recent_changes=stock_data.get('recent_changes', []),
        rsi=stock_data.get('rsi', 50),
        macd_status=stock_data.get('macd_status', 'neutral'),
        north_flow=stock_data.get('north_flow'),
        concepts=stock_data.get('concepts', [])
    )
