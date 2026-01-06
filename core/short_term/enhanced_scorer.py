"""
增强版短线评分系统 - Enhanced Short-Term Scoring System

整合所有优化模块:
1. 热点题材智能识别 (HotTopicManager)
2. 市场情绪分析 (MarketSentimentAnalyzer)
3. 大盘环境分析 (IndexEnvironmentAnalyzer)
4. 8维度综合评分

作者: 卓越股票分析师
版本: 4.0 (增强版)
日期: 2026-01-06
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime

from .hot_topic_manager import HotTopicManager, get_hot_topic_manager
from .market_sentiment import MarketSentimentAnalyzer, MarketSentimentData, SentimentLevel
from .index_analyzer import IndexEnvironmentAnalyzer, IndexData, MarketEnvironment


@dataclass
class EnhancedWeights:
    """增强版评分权重配置 - 8维度"""
    hot_topic: float = 20.0        # 热点题材 (降低，因为增加了新维度)
    capital_flow: float = 18.0     # 资金流向
    trend: float = 15.0            # 趋势强度
    momentum: float = 12.0         # 动量
    volume: float = 8.0            # 成交量
    sector: float = 8.0            # 板块地位
    sentiment: float = 10.0        # 市场情绪 (新增)
    index_env: float = 9.0         # 大盘环境 (新增)
    
    def validate(self) -> bool:
        """验证权重总和是否为100"""
        total = (self.hot_topic + self.capital_flow + self.trend +
                self.momentum + self.volume + self.sector +
                self.sentiment + self.index_env)
        return abs(total - 100.0) < 0.01


class EnhancedShortTermScorer:
    """
    增强版短线评分系统
    
    核心改进:
    1. 8维度评分 - 新增情绪和大盘维度
    2. 智能热点识别 - 自动管理热点题材
    3. 动态调整 - 根据市场环境调整评分
    4. 风险预警 - 极端情况自动预警
    """
    
    def __init__(self,
                 weights: EnhancedWeights = None,
                 hot_topic_manager: HotTopicManager = None,
                 sentiment_analyzer: MarketSentimentAnalyzer = None,
                 index_analyzer: IndexEnvironmentAnalyzer = None):
        """
        初始化增强版评分系统
        
        Args:
            weights: 权重配置
            hot_topic_manager: 热点管理器
            sentiment_analyzer: 情绪分析器
            index_analyzer: 大盘分析器
        """
        self.weights = weights or EnhancedWeights()
        self.hot_topic_manager = hot_topic_manager or get_hot_topic_manager()
        self.sentiment_analyzer = sentiment_analyzer or MarketSentimentAnalyzer()
        self.index_analyzer = index_analyzer or IndexEnvironmentAnalyzer()
        
        if not self.weights.validate():
            raise ValueError("权重总和必须为100%")
    
    # ==================== 1. 热点题材评分 (20%) ====================
    
    def hot_topic_score(self,
                       stock_name: str,
                       sector: str,
                       concepts: List[str] = None) -> Tuple[float, Dict]:
        """热点题材评分 - 使用智能热点管理器"""
        return self.hot_topic_manager.calculate_hot_topic_score(
            stock_name, sector, concepts, max_score=20.0
        )
    
    # ==================== 2. 资金流向评分 (18%) ====================
    
    def capital_flow_score(self,
                          main_net_inflow: float,
                          large_order_ratio: float,
                          north_flow: float = None) -> Tuple[float, Dict]:
        """资金流向评分"""
        max_score = 18.0
        
        # 主力净流入评分 (60%)
        if main_net_inflow > 5000:
            inflow_score = max_score * 0.6
        elif main_net_inflow > 1000:
            inflow_score = max_score * 0.6 * (0.7 + 0.3 * (main_net_inflow - 1000) / 4000)
        elif main_net_inflow > 0:
            inflow_score = max_score * 0.6 * (0.4 + 0.3 * main_net_inflow / 1000)
        elif main_net_inflow > -1000:
            inflow_score = max_score * 0.6 * (0.2 + 0.2 * (1000 + main_net_inflow) / 1000)
        elif main_net_inflow > -5000:
            inflow_score = max_score * 0.6 * 0.15
        else:
            inflow_score = max_score * 0.6 * 0.05
        
        # 大单比例评分 (30%)
        if large_order_ratio >= 55:
            large_score = max_score * 0.3
        elif large_order_ratio >= 50:
            large_score = max_score * 0.3 * 0.7
        elif large_order_ratio >= 45:
            large_score = max_score * 0.3 * 0.4
        else:
            large_score = max_score * 0.3 * 0.1
        
        # 北向资金评分 (10%)
        if north_flow is not None:
            north_score = max_score * 0.1 * min(1, max(0.2, (north_flow + 500) / 1500))
        else:
            north_score = max_score * 0.1 * 0.5
        
        final_score = inflow_score + large_score + north_score
        
        # 分类
        if main_net_inflow > 1000 and large_order_ratio >= 50:
            category = "主力加仓"
        elif main_net_inflow > 0:
            category = "资金流入"
        elif main_net_inflow > -1000:
            category = "资金均衡"
        elif main_net_inflow > -5000:
            category = "资金流出"
        else:
            category = "主力出货"
        
        return round(final_score, 2), {
            'main_net_inflow': main_net_inflow,
            'large_order_ratio': large_order_ratio,
            'north_flow': north_flow,
            'category': category,
            'is_positive': main_net_inflow > 0 and large_order_ratio >= 50
        }
    
    # ==================== 3. 趋势强度评分 (15%) ====================
    
    def trend_score(self,
                   price: float,
                   ma5: float, ma10: float, ma20: float,
                   recent_changes: List[float] = None,
                   rsi: float = 50,
                   macd_status: str = "neutral") -> Tuple[float, Dict]:
        """趋势强度评分"""
        max_score = 15.0
        
        # 均线排列 (40%)
        if price > ma5 > ma10 > ma20:
            ma_score = max_score * 0.4
            ma_status = "多头排列"
        elif price > ma5 > ma10:
            ma_score = max_score * 0.4 * 0.8
            ma_status = "短期多头"
        elif price > ma5:
            ma_score = max_score * 0.4 * 0.5
            ma_status = "弱势反弹"
        elif price > ma20:
            ma_score = max_score * 0.4 * 0.3
            ma_status = "震荡整理"
        else:
            ma_score = max_score * 0.4 * 0.1
            ma_status = "空头排列"
        
        # 近期趋势 (30%)
        if recent_changes:
            total_change = sum(recent_changes)
            positive_days = sum(1 for c in recent_changes if c > 0)
            
            if total_change > 10 and positive_days >= 4:
                trend_score_val = max_score * 0.3
                trend_status = "强势上涨"
            elif total_change > 5 and positive_days >= 3:
                trend_score_val = max_score * 0.3 * 0.8
                trend_status = "稳步上涨"
            elif total_change > 0:
                trend_score_val = max_score * 0.3 * 0.5
                trend_status = "小幅上涨"
            elif total_change > -5:
                trend_score_val = max_score * 0.3 * 0.3
                trend_status = "小幅调整"
            else:
                trend_score_val = max_score * 0.3 * 0.1
                trend_status = "明显下跌"
        else:
            trend_score_val = max_score * 0.3 * 0.5
            trend_status = "数据不足"
        
        # RSI (15%)
        if 50 <= rsi <= 70:
            rsi_score = max_score * 0.15
        elif 40 <= rsi < 50 or 70 < rsi <= 80:
            rsi_score = max_score * 0.15 * 0.6
        else:
            rsi_score = max_score * 0.15 * 0.3
        
        # MACD (15%)
        if macd_status == "golden_cross":
            macd_score = max_score * 0.15
        elif macd_status == "death_cross":
            macd_score = max_score * 0.15 * 0.2
        else:
            macd_score = max_score * 0.15 * 0.5
        
        final_score = ma_score + trend_score_val + rsi_score + macd_score
        
        return round(final_score, 2), {
            'ma_status': ma_status,
            'trend_status': trend_status,
            'rsi': rsi,
            'macd_status': macd_status,
            'is_uptrend': ma_status in ["多头排列", "短期多头"]
        }
    
    # ==================== 4. 动量评分 (12%) ====================
    
    def momentum_score(self,
                      change_pct: float,
                      turnover_rate: float) -> Tuple[float, Dict]:
        """动量评分"""
        max_score = 12.0
        
        # 涨幅评分 (70%)
        if 2 <= change_pct <= 5:
            change_score = max_score * 0.7
            change_status = "理想涨幅"
        elif 5 < change_pct <= 8:
            change_score = max_score * 0.7 * 0.8
            change_status = "强势涨幅"
        elif 0 < change_pct < 2:
            change_score = max_score * 0.7 * 0.6
            change_status = "温和上涨"
        elif change_pct > 8:
            change_score = max_score * 0.7 * 0.4
            change_status = "涨幅过大"
        elif -2 <= change_pct <= 0:
            change_score = max_score * 0.7 * 0.3
            change_status = "小幅调整"
        else:
            change_score = max_score * 0.7 * 0.1
            change_status = "明显下跌"
        
        # 换手率评分 (30%)
        if 3 <= turnover_rate <= 8:
            turnover_score = max_score * 0.3
        elif 1 <= turnover_rate < 3 or 8 < turnover_rate <= 15:
            turnover_score = max_score * 0.3 * 0.6
        else:
            turnover_score = max_score * 0.3 * 0.3
        
        return round(change_score + turnover_score, 2), {
            'change_pct': change_pct,
            'change_status': change_status,
            'turnover_rate': turnover_rate
        }
    
    # ==================== 5. 成交量评分 (8%) ====================
    
    def volume_score(self,
                    volume_ratio: float,
                    change_pct: float) -> Tuple[float, Dict]:
        """成交量评分"""
        max_score = 8.0
        
        if 1.5 <= volume_ratio <= 3:
            base_score = max_score * 0.8
            status = "温和放量"
        elif 1 <= volume_ratio < 1.5:
            base_score = max_score * 0.5
            status = "正常成交"
        elif 3 < volume_ratio <= 5:
            base_score = max_score * 0.6
            status = "明显放量"
        elif volume_ratio < 1:
            base_score = max_score * 0.3
            status = "缩量"
        else:
            base_score = max_score * 0.4
            status = "异常放量"
        
        # 量价配合
        if change_pct > 0 and volume_ratio > 1.2:
            synergy = "量价齐升"
            base_score *= 1.2
        elif change_pct < 0 and volume_ratio < 1:
            synergy = "缩量调整"
            base_score *= 1.1
        elif change_pct < 0 and volume_ratio > 1.5:
            synergy = "放量下跌"
            base_score *= 0.5
        else:
            synergy = "正常"
        
        return round(min(max_score, base_score), 2), {
            'volume_ratio': volume_ratio,
            'status': status,
            'synergy': synergy
        }
    
    # ==================== 6. 板块地位评分 (8%) ====================
    
    def sector_score(self,
                    sector_rank: int,
                    stock_rank_in_sector: int,
                    sector_stock_count: int) -> Tuple[float, Dict]:
        """板块地位评分"""
        max_score = 8.0
        
        # 板块强度 (50%)
        if sector_rank <= 3:
            sector_strength = max_score * 0.5
            sector_status = "热门板块"
        elif sector_rank <= 10:
            sector_strength = max_score * 0.5 * 0.7
            sector_status = "活跃板块"
        elif sector_rank <= 20:
            sector_strength = max_score * 0.5 * 0.4
            sector_status = "一般板块"
        else:
            sector_strength = max_score * 0.5 * 0.2
            sector_status = "冷门板块"
        
        # 板块内地位 (50%)
        position_ratio = stock_rank_in_sector / max(sector_stock_count, 1)
        
        if position_ratio <= 0.1:
            position_score = max_score * 0.5
            position_status = "板块龙头"
        elif position_ratio <= 0.3:
            position_score = max_score * 0.5 * 0.7
            position_status = "板块强势股"
        elif position_ratio <= 0.5:
            position_score = max_score * 0.5 * 0.4
            position_status = "板块中游"
        else:
            position_score = max_score * 0.5 * 0.2
            position_status = "板块跟风股"
        
        return round(sector_strength + position_score, 2), {
            'sector_rank': sector_rank,
            'sector_status': sector_status,
            'position_status': position_status,
            'is_leader': position_ratio <= 0.1 and sector_rank <= 5
        }
    
    # ==================== 7. 市场情绪评分 (10%) - 新增 ====================
    
    def sentiment_score(self) -> Tuple[float, Dict]:
        """市场情绪评分"""
        return self.sentiment_analyzer.calculate_sentiment_score(max_score=10.0)
    
    # ==================== 8. 大盘环境评分 (9%) - 新增 ====================
    
    def index_env_score(self) -> Tuple[float, Dict]:
        """大盘环境评分"""
        return self.index_analyzer.calculate_environment_score(max_score=9.0)
    
    # ==================== 综合评分 ====================
    
    def calculate_comprehensive_score(self,
                                      stock_code: str,
                                      stock_name: str,
                                      sector: str,
                                      price: float,
                                      change_pct: float,
                                      turnover_rate: float,
                                      volume_ratio: float,
                                      ma5: float, ma10: float, ma20: float,
                                      main_net_inflow: float,
                                      large_order_ratio: float,
                                      sector_rank: int,
                                      stock_rank_in_sector: int,
                                      sector_stock_count: int,
                                      recent_changes: List[float] = None,
                                      rsi: float = 50,
                                      macd_status: str = "neutral",
                                      north_flow: float = None,
                                      concepts: List[str] = None) -> Dict:
        """
        计算8维度综合评分
        
        Returns:
            完整的评分结果字典
        """
        # 1. 热点题材 (20%)
        hot_score, hot_details = self.hot_topic_score(stock_name, sector, concepts)
        
        # 2. 资金流向 (18%)
        capital_score, capital_details = self.capital_flow_score(
            main_net_inflow, large_order_ratio, north_flow
        )
        
        # 3. 趋势强度 (15%)
        trend_score_val, trend_details = self.trend_score(
            price, ma5, ma10, ma20, recent_changes, rsi, macd_status
        )
        
        # 4. 动量 (12%)
        momentum_score_val, momentum_details = self.momentum_score(change_pct, turnover_rate)
        
        # 5. 成交量 (8%)
        volume_score_val, volume_details = self.volume_score(volume_ratio, change_pct)
        
        # 6. 板块地位 (8%)
        sector_score_val, sector_details = self.sector_score(
            sector_rank, stock_rank_in_sector, sector_stock_count
        )
        
        # 7. 市场情绪 (10%)
        sentiment_score_val, sentiment_details = self.sentiment_score()
        
        # 8. 大盘环境 (9%)
        index_score_val, index_details = self.index_env_score()
        
        # 计算基础综合得分
        base_score = (
            hot_score * (self.weights.hot_topic / 20) +
            capital_score * (self.weights.capital_flow / 18) +
            trend_score_val * (self.weights.trend / 15) +
            momentum_score_val * (self.weights.momentum / 12) +
            volume_score_val * (self.weights.volume / 8) +
            sector_score_val * (self.weights.sector / 8) +
            sentiment_score_val * (self.weights.sentiment / 10) +
            index_score_val * (self.weights.index_env / 9)
        )
        
        # 应用大盘环境调整系数
        env_multiplier = index_details.get('score_multiplier', 1.0)
        adjusted_score = base_score * env_multiplier
        
        # 质量等级
        quality_grade = self._determine_quality_grade(adjusted_score)
        
        # 生成交易信号
        trading_signal = self._generate_trading_signal(
            adjusted_score, hot_details, capital_details,
            trend_details, sentiment_details, index_details
        )
        
        # 风险预警
        risk_warnings = self._check_risk_warnings(
            sentiment_details, index_details, capital_details
        )
        
        return {
            'stock_code': stock_code,
            'stock_name': stock_name,
            'sector': sector,
            'base_score': round(base_score, 2),
            'adjusted_score': round(adjusted_score, 2),
            'env_multiplier': env_multiplier,
            'quality_grade': quality_grade,
            'scores': {
                'hot_topic': round(hot_score, 2),
                'capital_flow': round(capital_score, 2),
                'trend': round(trend_score_val, 2),
                'momentum': round(momentum_score_val, 2),
                'volume': round(volume_score_val, 2),
                'sector': round(sector_score_val, 2),
                'sentiment': round(sentiment_score_val, 2),
                'index_env': round(index_score_val, 2)
            },
            'details': {
                'hot_topic': hot_details,
                'capital_flow': capital_details,
                'trend': trend_details,
                'momentum': momentum_details,
                'volume': volume_details,
                'sector': sector_details,
                'sentiment': sentiment_details,
                'index_env': index_details
            },
            'trading_signal': trading_signal,
            'risk_warnings': risk_warnings,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def _determine_quality_grade(self, score: float) -> str:
        """确定质量等级"""
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
    
    def _generate_trading_signal(self,
                                score: float,
                                hot_details: Dict,
                                capital_details: Dict,
                                trend_details: Dict,
                                sentiment_details: Dict,
                                index_details: Dict) -> Dict:
        """生成交易信号"""
        buy_conditions = []
        sell_conditions = []
        
        # 综合得分
        if score >= 85:
            buy_conditions.append("综合得分优秀(≥85)")
        elif score < 65:
            sell_conditions.append("综合得分较低(<65)")
        
        # 热点题材
        if hot_details.get('is_hot'):
            buy_conditions.append(f"属于热点({hot_details.get('category')})")
        elif hot_details.get('category') == "冷门题材":
            sell_conditions.append("非热点题材")
        
        # 资金流向
        if capital_details.get('is_positive'):
            buy_conditions.append(f"资金流入({capital_details.get('category')})")
        elif capital_details.get('category') in ["资金流出", "主力出货"]:
            sell_conditions.append(f"资金流出({capital_details.get('category')})")
        
        # 趋势
        if trend_details.get('is_uptrend'):
            buy_conditions.append(f"趋势向上({trend_details.get('ma_status')})")
        elif trend_details.get('ma_status') == "空头排列":
            sell_conditions.append("趋势向下")
        
        # 市场情绪
        if sentiment_details.get('is_favorable'):
            buy_conditions.append("市场情绪良好")
        elif sentiment_details.get('sentiment_level') in ["极度恐慌", "恐慌"]:
            sell_conditions.append(f"市场情绪差({sentiment_details.get('sentiment_level')})")
        
        # 大盘环境
        if index_details.get('is_favorable'):
            buy_conditions.append("大盘环境良好")
        elif index_details.get('environment') in ["熊市", "熊市反弹"]:
            sell_conditions.append(f"大盘环境差({index_details.get('environment')})")
        
        # 综合判断
        buy_score = len(buy_conditions)
        sell_score = len(sell_conditions)
        
        if buy_score >= 5 and sell_score == 0:
            signal = "强烈买入"
            strength = 5
            action = "建议明天开盘买入"
        elif buy_score >= 4 and sell_score <= 1:
            signal = "建议买入"
            strength = 4
            action = "可以考虑买入，注意仓位"
        elif buy_score >= 3 and sell_score <= 1:
            signal = "可以关注"
            strength = 3
            action = "加入自选观察"
        elif sell_score >= 4:
            signal = "建议卖出"
            strength = -2
            action = "如持有建议清仓"
        elif sell_score >= 3:
            signal = "谨慎持有"
            strength = -1
            action = "不建议新买入"
        else:
            signal = "中性观望"
            strength = 0
            action = "暂不操作"
        
        return {
            'signal': signal,
            'strength': strength,
            'action': action,
            'buy_conditions': buy_conditions,
            'sell_conditions': sell_conditions
        }
    
    def _check_risk_warnings(self,
                            sentiment_details: Dict,
                            index_details: Dict,
                            capital_details: Dict) -> List[str]:
        """检查风险预警"""
        warnings = []
        
        # 市场情绪预警
        sentiment_level = sentiment_details.get('sentiment_level', '')
        if sentiment_level == "极度恐慌":
            warnings.append("⚠️ 市场极度恐慌，建议空仓观望")
        elif sentiment_level == "恐慌":
            warnings.append("⚠️ 市场恐慌，控制仓位")
        
        # 大盘环境预警
        env = index_details.get('environment', '')
        if env == "熊市":
            warnings.append("⚠️ 大盘处于熊市，不建议操作")
        elif env == "熊市反弹":
            warnings.append("⚠️ 熊市反弹，快进快出")
        
        # 资金流向预警
        if capital_details.get('category') == "主力出货":
            warnings.append("⚠️ 主力大幅出货，回避")
        
        return warnings


# 便捷函数
def create_enhanced_scorer() -> EnhancedShortTermScorer:
    """创建增强版评分系统"""
    return EnhancedShortTermScorer()
