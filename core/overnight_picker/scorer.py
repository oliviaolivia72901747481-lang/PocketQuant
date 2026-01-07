"""
明日潜力评分器 (TomorrowPotentialScorer)

预测股票明天上涨的概率，8个评分维度
"""

from typing import Dict, Tuple, List, Optional
import pandas as pd


class TomorrowPotentialScorer:
    """
    明日潜力评分器 - 预测股票明天上涨的概率
    
    8个评分维度，专注于"明日会涨"的预测:
    - 收盘形态 (15分)
    - 量能分析 (15分)
    - 均线位置 (12分)
    - 资金流向 (15分)
    - 热点关联 (15分)
    - 龙头地位 (12分)
    - 板块强度 (8分)
    - 技术形态 (8分)
    """
    
    def __init__(self, total_capital: float = 70000):
        self.total_capital = total_capital
        self.weights = {
            'closing_pattern': 15,    # 收盘形态
            'volume_analysis': 15,    # 量能分析
            'ma_position': 12,        # 均线位置
            'capital_flow': 15,       # 资金流向
            'hot_topic': 15,          # 热点关联
            'leader_index': 12,       # 龙头地位
            'sector_strength': 8,     # 板块强度
            'technical_pattern': 8,   # 技术形态
        }
    
    def score_closing_pattern(self, open_p: float, high: float, low: float, 
                              close: float, prev_close: float) -> Tuple[float, Dict]:
        """
        收盘形态评分 (15分)
        
        分析今日K线形态，预测明日走势:
        - 放量阳线收盘: 15分 (明日大概率高开)
        - 缩量阳线收盘: 12分 (明日可能平开)
        - 十字星收盘: 8分 (方向不明)
        - 下影线阳线: 14分 (有支撑，明日看涨)
        - 上影线阴线: 4分 (有压力，明日看跌)
        - 放量阴线收盘: 3分 (明日可能低开)
        """
        max_score = self.weights['closing_pattern']
        
        # 计算K线特征
        body = close - open_p
        upper_shadow = high - max(open_p, close)
        lower_shadow = min(open_p, close) - low
        body_ratio = abs(body) / (high - low) if high != low else 0
        change_pct = (close - prev_close) / prev_close if prev_close > 0 else 0
        
        score = 0
        pattern = ""
        
        # 判断K线类型
        is_bullish = close > open_p
        is_doji = body_ratio < 0.1  # 十字星
        has_long_lower_shadow = lower_shadow > abs(body) * 2
        has_long_upper_shadow = upper_shadow > abs(body) * 2
        
        if is_doji:
            score = 8
            pattern = "十字星"
        elif is_bullish:
            if has_long_lower_shadow:
                score = 14
                pattern = "下影线阳线"
            elif has_long_upper_shadow:
                score = 10
                pattern = "上影线阳线"
            elif change_pct > 0.05:
                score = 15
                pattern = "大阳线"
            else:
                score = 12
                pattern = "阳线"
        else:  # 阴线
            if has_long_upper_shadow:
                score = 4
                pattern = "上影线阴线"
            elif has_long_lower_shadow:
                score = 7
                pattern = "下影线阴线"
            elif change_pct < -0.05:
                score = 3
                pattern = "大阴线"
            else:
                score = 6
                pattern = "阴线"
        
        details = {
            'score': score,
            'max_score': max_score,
            'pattern': pattern,
            'change_pct': round(change_pct * 100, 2),
            'body_ratio': round(body_ratio, 2),
        }
        
        return score, details
    
    def score_volume_analysis(self, volume: float, ma5_vol: float, 
                              ma10_vol: float, change_pct: float) -> Tuple[float, Dict]:
        """
        量能分析评分 (15分)
        
        分析成交量变化:
        - 温和放量上涨(1.5-3倍): 15分 (健康上涨)
        - 缩量上涨: 10分 (上涨乏力)
        - 放量上涨(>3倍): 8分 (可能见顶)
        - 缩量下跌: 12分 (洗盘，明日可能反弹)
        - 放量下跌: 3分 (出货，明日继续跌)
        """
        max_score = self.weights['volume_analysis']
        
        # 计算量比
        vol_ratio = volume / ma5_vol if ma5_vol > 0 else 1
        
        score = 0
        vol_type = ""
        
        is_up = change_pct > 0
        
        if is_up:
            if 1.5 <= vol_ratio <= 3:
                score = 15
                vol_type = "温和放量上涨"
            elif vol_ratio > 3:
                score = 8
                vol_type = "巨量上涨(警惕)"
            elif vol_ratio < 0.8:
                score = 10
                vol_type = "缩量上涨"
            else:
                score = 12
                vol_type = "平量上涨"
        else:
            if vol_ratio < 0.8:
                score = 12
                vol_type = "缩量下跌(洗盘)"
            elif vol_ratio > 2:
                score = 3
                vol_type = "放量下跌(出货)"
            else:
                score = 6
                vol_type = "平量下跌"
        
        details = {
            'score': score,
            'max_score': max_score,
            'vol_ratio': round(vol_ratio, 2),
            'vol_type': vol_type,
        }
        
        return score, details
    
    def score_ma_position(self, price: float, ma5: float, ma10: float, 
                          ma20: float, ma60: float) -> Tuple[float, Dict]:
        """
        均线位置评分 (12分)
        
        分析均线排列:
        - 多头排列(价>MA5>MA10>MA20): 12分
        - 均线粘合(三线距离<3%): 10分 (即将突破)
        - 站上MA20: 8分
        - 站上MA60: 6分
        - 空头排列: 2分
        """
        max_score = self.weights['ma_position']
        
        score = 0
        ma_type = ""
        
        # 检查多头排列
        is_bullish_alignment = price > ma5 > ma10 > ma20
        is_bearish_alignment = price < ma5 < ma10 < ma20
        
        # 检查均线粘合
        ma_range = max(ma5, ma10, ma20) - min(ma5, ma10, ma20)
        avg_ma = (ma5 + ma10 + ma20) / 3
        is_converging = (ma_range / avg_ma) < 0.03 if avg_ma > 0 else False
        
        if is_bullish_alignment:
            score = 12
            ma_type = "多头排列"
        elif is_converging:
            score = 10
            ma_type = "均线粘合"
        elif price > ma20:
            if price > ma60:
                score = 8
                ma_type = "站上MA20和MA60"
            else:
                score = 7
                ma_type = "站上MA20"
        elif price > ma60:
            score = 6
            ma_type = "站上MA60"
        elif is_bearish_alignment:
            score = 2
            ma_type = "空头排列"
        else:
            score = 4
            ma_type = "均线交织"
        
        details = {
            'score': score,
            'max_score': max_score,
            'ma_type': ma_type,
            'above_ma5': price > ma5,
            'above_ma10': price > ma10,
            'above_ma20': price > ma20,
            'above_ma60': price > ma60,
        }
        
        return score, details
    
    def score_capital_flow(self, main_net_inflow: float, 
                           large_order_ratio: float = 0,
                           north_flow: float = 0) -> Tuple[float, Dict]:
        """
        资金流向评分 (15分)
        
        分析今日资金:
        - 主力大幅流入(>5000万): 15分
        - 主力小幅流入(1000-5000万): 12分
        - 资金均衡: 8分
        - 主力小幅流出: 5分
        - 主力大幅流出: 2分
        """
        max_score = self.weights['capital_flow']
        
        score = 0
        flow_type = ""
        
        # 主力净流入 (单位: 万元)
        if main_net_inflow > 5000:
            score = 15
            flow_type = "主力大幅流入"
        elif main_net_inflow > 1000:
            score = 12
            flow_type = "主力小幅流入"
        elif main_net_inflow > -1000:
            score = 8
            flow_type = "资金均衡"
        elif main_net_inflow > -5000:
            score = 5
            flow_type = "主力小幅流出"
        else:
            score = 2
            flow_type = "主力大幅流出"
        
        details = {
            'score': score,
            'max_score': max_score,
            'main_net_inflow': main_net_inflow,
            'flow_type': flow_type,
            'large_order_ratio': large_order_ratio,
            'north_flow': north_flow,
        }
        
        return score, details
    
    def score_hot_topic(self, stock_name: str, sector: str, 
                        concepts: List[str], hot_topics: List[str] = None) -> Tuple[float, Dict]:
        """
        热点关联评分 (15分)
        
        分析题材热度:
        - 当日最热题材龙头: 15分
        - 当日热点相关股: 12分
        - 持续热点相关: 10分
        - 潜在热点: 6分
        - 无热点关联: 3分
        """
        max_score = self.weights['hot_topic']
        
        if hot_topics is None:
            hot_topics = []
        
        score = 3  # 默认无热点
        topic_type = "无热点关联"
        matched_topics = []
        
        # 检查概念与热点的匹配
        for concept in concepts:
            for hot in hot_topics:
                if hot in concept or concept in hot:
                    matched_topics.append(concept)
        
        if matched_topics:
            if len(matched_topics) >= 2:
                score = 15
                topic_type = "多热点叠加"
            else:
                score = 12
                topic_type = "热点相关"
        elif concepts:
            score = 6
            topic_type = "有概念但非热点"
        
        details = {
            'score': score,
            'max_score': max_score,
            'topic_type': topic_type,
            'matched_topics': matched_topics,
            'concepts': concepts,
        }
        
        return score, details
    
    def score_leader_index(self, stock_code: str, sector_rank: int = 0,
                           sector_size: int = 10) -> Tuple[float, Dict]:
        """
        龙头地位评分 (12分)
        
        分析板块内地位:
        - 板块龙头(涨幅第1): 12分
        - 二线龙头(涨幅前3): 10分
        - 板块强势股(涨幅前10): 7分
        - 板块跟风股: 4分
        - 板块最弱: 1分
        """
        max_score = self.weights['leader_index']
        
        score = 0
        leader_type = ""
        
        if sector_rank == 1:
            score = 12
            leader_type = "板块龙头"
        elif sector_rank <= 3:
            score = 10
            leader_type = "二线龙头"
        elif sector_rank <= 10:
            score = 7
            leader_type = "板块强势股"
        elif sector_rank <= sector_size * 0.5:
            score = 4
            leader_type = "板块跟风股"
        else:
            score = 1
            leader_type = "板块弱势股"
        
        details = {
            'score': score,
            'max_score': max_score,
            'leader_type': leader_type,
            'sector_rank': sector_rank,
            'sector_size': sector_size,
        }
        
        return score, details
    
    def score_sector_strength(self, sector_rank: int, 
                              sector_change: float) -> Tuple[float, Dict]:
        """
        板块强度评分 (8分)
        
        分析所属板块:
        - 当日涨幅前3板块: 8分
        - 当日涨幅前10板块: 6分
        - 板块涨幅为正: 4分
        - 板块涨幅为负: 2分
        """
        max_score = self.weights['sector_strength']
        
        score = 0
        strength_type = ""
        
        if sector_rank <= 3:
            score = 8
            strength_type = "最强板块"
        elif sector_rank <= 10:
            score = 6
            strength_type = "强势板块"
        elif sector_change > 0:
            score = 4
            strength_type = "上涨板块"
        else:
            score = 2
            strength_type = "下跌板块"
        
        details = {
            'score': score,
            'max_score': max_score,
            'strength_type': strength_type,
            'sector_rank': sector_rank,
            'sector_change': sector_change,
        }
        
        return score, details
    
    def score_technical_pattern(self, df: pd.DataFrame = None,
                                has_breakout: bool = False,
                                has_macd_golden: bool = False,
                                has_ma_golden: bool = False) -> Tuple[float, Dict]:
        """
        技术形态评分 (8分)
        
        识别经典形态:
        - 突破形态(突破前高): 8分
        - 底部放量: 7分
        - MACD金叉: 6分
        - 均线金叉: 5分
        - 无明显形态: 3分
        - 顶部形态: 1分
        """
        max_score = self.weights['technical_pattern']
        
        score = 3  # 默认无明显形态
        pattern = "无明显形态"
        
        if has_breakout:
            score = 8
            pattern = "突破形态"
        elif has_macd_golden:
            score = 6
            pattern = "MACD金叉"
        elif has_ma_golden:
            score = 5
            pattern = "均线金叉"
        
        details = {
            'score': score,
            'max_score': max_score,
            'pattern': pattern,
            'has_breakout': has_breakout,
            'has_macd_golden': has_macd_golden,
            'has_ma_golden': has_ma_golden,
        }
        
        return score, details
    
    def calculate_total_score(self, scores: Dict[str, Tuple[float, Dict]]) -> Tuple[float, Dict]:
        """
        计算总分
        
        Args:
            scores: 各维度评分结果
        
        Returns:
            (总分, 详情字典)
        """
        total = 0
        details = {}
        
        for dimension, (score, detail) in scores.items():
            total += score
            details[dimension] = detail
        
        # 确保总分在0-100之间
        total = max(0, min(100, total))
        
        return total, details
    
    def score_stock(self, 
                    stock_data: Dict,
                    market_data: Optional[Dict] = None) -> Tuple[float, Dict]:
        """
        综合评分方法 - 对单只股票进行全面评分
        
        Args:
            stock_data: 股票数据字典，包含:
                - open: 开盘价
                - high: 最高价
                - low: 最低价
                - close: 收盘价
                - prev_close: 昨日收盘价
                - volume: 成交量
                - ma5_vol: 5日均量
                - ma10_vol: 10日均量
                - ma5: 5日均线
                - ma10: 10日均线
                - ma20: 20日均线
                - ma60: 60日均线
                - main_net_inflow: 主力净流入(万元)
                - concepts: 概念列表
                - sector: 所属板块
                - sector_rank: 板块内排名
                - sector_size: 板块股票数量
                - sector_change: 板块涨跌幅
                - sector_market_rank: 板块市场排名
            market_data: 市场数据字典，包含:
                - hot_topics: 当前热点列表
        
        Returns:
            (总分, 详情字典)
        """
        if market_data is None:
            market_data = {}
        
        scores = {}
        
        # 1. 收盘形态评分
        scores['closing_pattern'] = self.score_closing_pattern(
            open_p=stock_data.get('open', 0),
            high=stock_data.get('high', 0),
            low=stock_data.get('low', 0),
            close=stock_data.get('close', 0),
            prev_close=stock_data.get('prev_close', 0)
        )
        
        # 2. 量能分析评分
        change_pct = 0
        if stock_data.get('prev_close', 0) > 0:
            change_pct = (stock_data.get('close', 0) - stock_data.get('prev_close', 0)) / stock_data.get('prev_close', 0)
        
        scores['volume_analysis'] = self.score_volume_analysis(
            volume=stock_data.get('volume', 0),
            ma5_vol=stock_data.get('ma5_vol', 1),
            ma10_vol=stock_data.get('ma10_vol', 1),
            change_pct=change_pct
        )
        
        # 3. 均线位置评分
        scores['ma_position'] = self.score_ma_position(
            price=stock_data.get('close', 0),
            ma5=stock_data.get('ma5', 0),
            ma10=stock_data.get('ma10', 0),
            ma20=stock_data.get('ma20', 0),
            ma60=stock_data.get('ma60', 0)
        )
        
        # 4. 资金流向评分
        scores['capital_flow'] = self.score_capital_flow(
            main_net_inflow=stock_data.get('main_net_inflow', 0),
            large_order_ratio=stock_data.get('large_order_ratio', 0),
            north_flow=stock_data.get('north_flow', 0)
        )
        
        # 5. 热点关联评分
        scores['hot_topic'] = self.score_hot_topic(
            stock_name=stock_data.get('name', ''),
            sector=stock_data.get('sector', ''),
            concepts=stock_data.get('concepts', []),
            hot_topics=market_data.get('hot_topics', [])
        )
        
        # 6. 龙头地位评分
        scores['leader_index'] = self.score_leader_index(
            stock_code=stock_data.get('code', ''),
            sector_rank=stock_data.get('sector_rank', 50),
            sector_size=stock_data.get('sector_size', 100)
        )
        
        # 7. 板块强度评分
        scores['sector_strength'] = self.score_sector_strength(
            sector_rank=stock_data.get('sector_market_rank', 50),
            sector_change=stock_data.get('sector_change', 0)
        )
        
        # 8. 技术形态评分
        scores['technical_pattern'] = self.score_technical_pattern(
            df=stock_data.get('df'),
            has_breakout=stock_data.get('has_breakout', False),
            has_macd_golden=stock_data.get('has_macd_golden', False),
            has_ma_golden=stock_data.get('has_ma_golden', False)
        )
        
        # 计算总分
        return self.calculate_total_score(scores)
    
    def get_score_summary(self, total_score: float, details: Dict) -> str:
        """
        生成评分摘要
        
        Args:
            total_score: 总分
            details: 评分详情
        
        Returns:
            评分摘要字符串
        """
        lines = []
        lines.append(f"明日潜力评分: {total_score:.0f}/100")
        lines.append("")
        
        for dimension, detail in details.items():
            score = detail.get('score', 0)
            max_score = detail.get('max_score', 0)
            
            # 获取维度中文名
            dimension_names = {
                'closing_pattern': '收盘形态',
                'volume_analysis': '量能分析',
                'ma_position': '均线位置',
                'capital_flow': '资金流向',
                'hot_topic': '热点关联',
                'leader_index': '龙头地位',
                'sector_strength': '板块强度',
                'technical_pattern': '技术形态',
            }
            name = dimension_names.get(dimension, dimension)
            
            # 获取描述
            desc = ""
            if 'pattern' in detail:
                desc = detail['pattern']
            elif 'vol_type' in detail:
                desc = detail['vol_type']
            elif 'ma_type' in detail:
                desc = detail['ma_type']
            elif 'flow_type' in detail:
                desc = detail['flow_type']
            elif 'topic_type' in detail:
                desc = detail['topic_type']
            elif 'leader_type' in detail:
                desc = detail['leader_type']
            elif 'strength_type' in detail:
                desc = detail['strength_type']
            
            lines.append(f"- {name}: {score}/{max_score} ({desc})")
        
        return "\n".join(lines)
    
    def validate_score(self, total_score: float, details: Dict) -> bool:
        """
        验证评分结果的有效性
        
        Args:
            total_score: 总分
            details: 评分详情
        
        Returns:
            是否有效
        """
        # 检查总分范围
        if not (0 <= total_score <= 100):
            return False
        
        # 检查各维度分数不超过权重上限
        for dimension, detail in details.items():
            score = detail.get('score', 0)
            max_score = self.weights.get(dimension, 0)
            if score > max_score:
                return False
            if score < 0:
                return False
        
        return True
