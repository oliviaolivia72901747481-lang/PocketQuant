"""
评分系统 v6.0 - 6维度100分体系

核心改进:
1. 强调"题材是第一生产力"，题材风口权重提升至25分
2. 新增"股性活跃度"维度，剔除"死股"
3. 资金强度改为相对值（占比），更准确反映资金意图
4. 量价配合引入换手率和情境判断
5. 趋势与位置结合均线和分位点，识别低位突破和高位风险
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np

from core.logging_config import get_logger

# 获取模块日志记录器
logger = get_logger(__name__)


@dataclass
class ScoreDimension:
    """单维度评分"""
    score: float        # 得分
    max_score: float    # 满分
    description: str    # 描述
    details: Dict = field(default_factory=dict)  # 详细信息


@dataclass
class ScoreResult:
    """评分结果"""
    total_score: float              # 总分 (0-100)
    trend_position: ScoreDimension  # 趋势与位置
    kline_pattern: ScoreDimension   # K线与形态
    volume_price: ScoreDimension    # 量价配合
    capital_strength: ScoreDimension # 资金强度
    theme_wind: ScoreDimension      # 题材风口
    stock_activity: ScoreDimension  # 股性活跃度
    risks: List[str] = field(default_factory=list)  # 风险标记列表
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            'total_score': self.total_score,
            'trend_position': {
                'score': self.trend_position.score,
                'max_score': self.trend_position.max_score,
                'description': self.trend_position.description,
                'details': self.trend_position.details,
            },
            'kline_pattern': {
                'score': self.kline_pattern.score,
                'max_score': self.kline_pattern.max_score,
                'description': self.kline_pattern.description,
                'details': self.kline_pattern.details,
            },
            'volume_price': {
                'score': self.volume_price.score,
                'max_score': self.volume_price.max_score,
                'description': self.volume_price.description,
                'details': self.volume_price.details,
            },
            'capital_strength': {
                'score': self.capital_strength.score,
                'max_score': self.capital_strength.max_score,
                'description': self.capital_strength.description,
                'details': self.capital_strength.details,
            },
            'theme_wind': {
                'score': self.theme_wind.score,
                'max_score': self.theme_wind.max_score,
                'description': self.theme_wind.description,
                'details': self.theme_wind.details,
            },
            'stock_activity': {
                'score': self.stock_activity.score,
                'max_score': self.stock_activity.max_score,
                'description': self.stock_activity.description,
                'details': self.stock_activity.details,
            },
            'risks': self.risks,
        }


class TrendPositionScorer:
    """
    趋势与位置评分 (20分)
    
    评分逻辑:
    - 低位多头排列: 20分
    - 突破关键均线: 16-18分
    - 均线粘合: 12-14分
    - 高位加速(乖离率>15%): 10分 + 风险标记
    - 空头排列: 0分
    """
    
    MAX_SCORE = 20
    
    def calculate_deviation_rate(self, price: float, ma20: float) -> float:
        """
        计算乖离率
        
        Args:
            price: 当前价格
            ma20: 20日均线
        
        Returns:
            乖离率 (百分比)
        """
        if ma20 <= 0:
            return 0.0
        return ((price - ma20) / ma20) * 100
    
    def _is_bullish_alignment(self, price: float, ma5: float, ma10: float, 
                               ma20: float, ma60: float) -> bool:
        """判断是否多头排列"""
        return price > ma5 > ma10 > ma20 > ma60
    
    def _is_bearish_alignment(self, price: float, ma5: float, ma10: float, 
                               ma20: float, ma60: float) -> bool:
        """判断是否空头排列"""
        return price < ma5 < ma10 < ma20 < ma60
    
    def _is_ma_converging(self, ma5: float, ma10: float, ma20: float) -> bool:
        """判断均线是否粘合 (三线距离<3%)"""
        if ma5 <= 0 or ma10 <= 0 or ma20 <= 0:
            return False
        ma_range = max(ma5, ma10, ma20) - min(ma5, ma10, ma20)
        avg_ma = (ma5 + ma10 + ma20) / 3
        return (ma_range / avg_ma) < 0.03 if avg_ma > 0 else False
    
    def _is_breaking_ma(self, price: float, ma20: float, ma60: float, 
                        prev_close: float = None) -> Tuple[bool, str]:
        """判断是否突破关键均线"""
        if prev_close is None:
            prev_close = price * 0.98  # 假设昨日收盘价略低
        
        # 突破MA60
        if price > ma60 and prev_close <= ma60:
            return True, "突破MA60"
        # 突破MA20
        if price > ma20 and prev_close <= ma20:
            return True, "突破MA20"
        return False, ""
    
    def score(self, price: float, ma5: float, ma10: float, 
              ma20: float, ma60: float, 
              price_percentile: float,
              prev_close: float = None) -> Tuple[float, Dict, List[str]]:
        """
        计算趋势与位置得分
        
        Args:
            price: 当前价格
            ma5/ma10/ma20/ma60: 各均线值
            price_percentile: 价格在近60日的分位点(0-100)
            prev_close: 昨日收盘价 (可选)
        
        Returns:
            (得分, 详情, 风险标记列表)
        """
        risks = []
        
        # 处理无效数据
        if price <= 0 or ma5 <= 0 or ma10 <= 0 or ma20 <= 0 or ma60 <= 0:
            return 0, {
                'score': 0,
                'max_score': self.MAX_SCORE,
                'trend_type': '数据无效',
                'deviation_rate': 0,
                'price_percentile': price_percentile,
            }, risks
        
        # 计算乖离率
        deviation_rate = self.calculate_deviation_rate(price, ma20)
        
        score = 0
        trend_type = ""
        
        # 1. 检查空头排列 -> 0分
        if self._is_bearish_alignment(price, ma5, ma10, ma20, ma60):
            score = 0
            trend_type = "空头排列"
        
        # 2. 检查高位加速 (乖离率>15%) -> 10分 + 风险标记
        elif deviation_rate > 15:
            score = 10
            trend_type = "高位加速"
            risks.append("追高风险")
        
        # 3. 检查低位多头排列 -> 20分
        elif self._is_bullish_alignment(price, ma5, ma10, ma20, ma60):
            if price_percentile <= 50:  # 低位
                score = 20
                trend_type = "低位多头排列"
            else:
                score = 16
                trend_type = "多头排列"
        
        # 4. 检查突破关键均线 -> 16-18分
        elif prev_close is not None:
            is_breaking, break_type = self._is_breaking_ma(price, ma20, ma60, prev_close)
            if is_breaking:
                if break_type == "突破MA60":
                    score = 18
                else:
                    score = 16
                trend_type = break_type
            elif self._is_ma_converging(ma5, ma10, ma20):
                score = 13
                trend_type = "均线粘合"
            elif price > ma20:
                score = 12
                trend_type = "站上MA20"
            elif price > ma60:
                score = 8
                trend_type = "站上MA60"
            else:
                score = 4
                trend_type = "均线下方"
        
        # 5. 检查均线粘合 -> 12-14分
        elif self._is_ma_converging(ma5, ma10, ma20):
            score = 13
            trend_type = "均线粘合"
        
        # 6. 其他情况
        else:
            if price > ma20:
                score = 12
                trend_type = "站上MA20"
            elif price > ma60:
                score = 8
                trend_type = "站上MA60"
            else:
                score = 4
                trend_type = "均线下方"
        
        details = {
            'score': score,
            'max_score': self.MAX_SCORE,
            'trend_type': trend_type,
            'deviation_rate': round(deviation_rate, 2),
            'price_percentile': price_percentile,
            'is_bullish': self._is_bullish_alignment(price, ma5, ma10, ma20, ma60),
            'is_bearish': self._is_bearish_alignment(price, ma5, ma10, ma20, ma60),
            'is_converging': self._is_ma_converging(ma5, ma10, ma20),
        }
        
        return score, details, risks


class KLinePatternScorer:
    """
    K线与形态评分 (15分)
    
    评分逻辑:
    - 涨停/反包/突破前高: 15分
    - 下影线阳线: 12分
    - 企稳十字星/多方炮: 10分
    - 普通阳线: 8分
    - 普通阴线: 4分
    - 吊颈线/乌云盖顶: 0分
    """
    
    MAX_SCORE = 15
    
    # 涨停阈值 (主板10%, 创业板/科创板20%)
    LIMIT_UP_THRESHOLD = 0.095  # 9.5%以上视为涨停
    LIMIT_UP_THRESHOLD_20 = 0.195  # 19.5%以上视为20%涨停
    
    def _calculate_change_pct(self, close: float, prev_close: float) -> float:
        """计算涨跌幅"""
        if prev_close <= 0:
            return 0.0
        return (close - prev_close) / prev_close
    
    def _is_limit_up(self, close: float, prev_close: float, is_cyb_kcb: bool = False) -> bool:
        """
        判断是否涨停
        
        Args:
            close: 收盘价
            prev_close: 昨日收盘价
            is_cyb_kcb: 是否创业板/科创板 (20%涨停)
        """
        change_pct = self._calculate_change_pct(close, prev_close)
        threshold = self.LIMIT_UP_THRESHOLD_20 if is_cyb_kcb else self.LIMIT_UP_THRESHOLD
        return change_pct >= threshold
    
    def _is_reversal_pattern(self, open_p: float, high: float, low: float, 
                              close: float, prev_close: float, prev_low: float) -> bool:
        """
        判断是否反包形态
        反包: 今日阳线完全覆盖昨日阴线
        """
        # 今日是阳线
        if close <= open_p:
            return False
        # 昨日是阴线 (prev_close < 前一日开盘价，简化判断为今日开盘低于昨收)
        if open_p >= prev_close:
            return False
        # 今日收盘高于昨日收盘
        if close <= prev_close:
            return False
        # 今日最低低于昨日最低
        if low > prev_low:
            return False
        return True
    
    def _is_breakout(self, close: float, prev_high: float) -> bool:
        """判断是否突破前高"""
        if prev_high is None or prev_high <= 0:
            return False
        return close > prev_high
    
    def _is_doji(self, open_p: float, high: float, low: float, close: float) -> bool:
        """
        判断是否十字星
        实体很小，上下影线较长
        """
        body = abs(close - open_p)
        total_range = high - low
        if total_range <= 0:
            return False
        body_ratio = body / total_range
        return body_ratio < 0.1  # 实体占比<10%
    
    def _is_bullish_engulfing(self, open_p: float, close: float, 
                               prev_open: float, prev_close: float) -> bool:
        """
        判断是否多方炮/吞没形态
        今日阳线实体完全覆盖昨日阴线实体
        """
        # 今日是阳线
        if close <= open_p:
            return False
        # 昨日是阴线
        if prev_close >= prev_open:
            return False
        # 今日开盘低于昨日收盘，今日收盘高于昨日开盘
        return open_p <= prev_close and close >= prev_open
    
    def _is_hammer(self, open_p: float, high: float, low: float, close: float) -> bool:
        """
        判断是否下影线阳线 (锤子线)
        下影线长度至少是实体的2倍
        """
        body = abs(close - open_p)
        lower_shadow = min(open_p, close) - low
        upper_shadow = high - max(open_p, close)
        
        if body <= 0:
            return False
        
        # 下影线至少是实体的2倍，上影线较短
        return lower_shadow >= body * 2 and upper_shadow < body
    
    def _is_hanging_man(self, open_p: float, high: float, low: float, 
                         close: float, is_at_high: bool = False) -> bool:
        """
        判断是否吊颈线 (高位锤子线)
        形态与锤子线相同，但出现在高位
        """
        if not is_at_high:
            return False
        return self._is_hammer(open_p, high, low, close)
    
    def _is_dark_cloud_cover(self, open_p: float, close: float, 
                              prev_open: float, prev_close: float, prev_high: float) -> bool:
        """
        判断是否乌云盖顶
        昨日大阳线，今日高开低走，收盘价深入昨日阳线实体50%以上
        """
        # 昨日是阳线
        if prev_close <= prev_open:
            return False
        # 今日是阴线
        if close >= open_p:
            return False
        # 今日开盘高于昨日最高
        if open_p <= prev_high:
            return False
        # 今日收盘深入昨日实体50%以上
        prev_body_mid = (prev_open + prev_close) / 2
        return close < prev_body_mid
    
    def _is_positive_candle(self, open_p: float, close: float) -> bool:
        """判断是否阳线"""
        return close > open_p
    
    def _is_negative_candle(self, open_p: float, close: float) -> bool:
        """判断是否阴线"""
        return close < open_p
    
    def detect_pattern(self, open_p: float, high: float, low: float, 
                       close: float, prev_close: float,
                       prev_open: float = None, prev_high: float = None, 
                       prev_low: float = None, is_at_high: bool = False,
                       is_cyb_kcb: bool = False) -> Tuple[str, int]:
        """
        识别K线形态
        
        Args:
            open_p/high/low/close: 今日OHLC
            prev_close: 昨日收盘价
            prev_open: 昨日开盘价 (可选)
            prev_high: 前期高点 (可选)
            prev_low: 昨日最低价 (可选)
            is_at_high: 是否处于高位
            is_cyb_kcb: 是否创业板/科创板
        
        Returns:
            (形态名称, 优先级) - 优先级越高越重要
        """
        patterns = []
        
        # 1. 涨停 - 最高优先级
        if self._is_limit_up(close, prev_close, is_cyb_kcb):
            patterns.append(("涨停", 100))
        
        # 2. 反包形态
        if prev_low is not None and self._is_reversal_pattern(open_p, high, low, close, prev_close, prev_low):
            patterns.append(("反包", 90))
        
        # 3. 突破前高
        if prev_high is not None and self._is_breakout(close, prev_high):
            patterns.append(("突破前高", 85))
        
        # 4. 顶部形态 - 负面 (高优先级检测)
        if is_at_high and self._is_hammer(open_p, high, low, close):
            # 高位锤子线 = 吊颈线
            patterns.append(("吊颈线", 95))  # 高优先级，仅次于涨停
        
        if prev_open is not None and self._is_dark_cloud_cover(open_p, close, prev_open, prev_close, prev_high or high):
            patterns.append(("乌云盖顶", 94))
        
        # 5. 下影线阳线 (非高位)
        if not is_at_high and self._is_hammer(open_p, high, low, close) and self._is_positive_candle(open_p, close):
            patterns.append(("下影线阳线", 70))
        
        # 6. 十字星
        if self._is_doji(open_p, high, low, close):
            patterns.append(("十字星", 60))
        
        # 7. 多方炮
        if prev_open is not None and self._is_bullish_engulfing(open_p, close, prev_open, prev_close):
            patterns.append(("多方炮", 65))
        
        # 8. 普通阳线/阴线
        if self._is_positive_candle(open_p, close):
            patterns.append(("阳线", 50))
        elif self._is_negative_candle(open_p, close):
            patterns.append(("阴线", 20))
        else:
            patterns.append(("平盘", 30))
        
        # 返回优先级最高的形态
        if patterns:
            patterns.sort(key=lambda x: x[1], reverse=True)
            return patterns[0]
        
        return ("未知", 0)
    
    def score(self, open_p: float, high: float, low: float, 
              close: float, prev_close: float,
              prev_open: float = None, prev_high: float = None,
              prev_low: float = None, is_at_high: bool = False,
              is_cyb_kcb: bool = False) -> Tuple[float, Dict, List[str]]:
        """
        计算K线形态得分
        
        Args:
            open_p/high/low/close: 今日OHLC
            prev_close: 昨日收盘价
            prev_open: 昨日开盘价 (可选)
            prev_high: 前期高点 (可选)
            prev_low: 昨日最低价 (可选)
            is_at_high: 是否处于高位
            is_cyb_kcb: 是否创业板/科创板
        
        Returns:
            (得分, 详情, 风险标记列表)
        """
        risks = []
        
        # 处理无效数据
        if close <= 0 or prev_close <= 0 or open_p <= 0 or high <= 0 or low <= 0:
            return 0, {
                'score': 0,
                'max_score': self.MAX_SCORE,
                'pattern': '数据无效',
                'change_pct': 0,
            }, risks
        
        # 识别形态
        pattern, priority = self.detect_pattern(
            open_p, high, low, close, prev_close,
            prev_open, prev_high, prev_low, is_at_high, is_cyb_kcb
        )
        
        # 计算涨跌幅
        change_pct = self._calculate_change_pct(close, prev_close) * 100
        
        # 根据形态评分
        score = 0
        if pattern == "涨停":
            score = 15
        elif pattern == "反包":
            score = 15
        elif pattern == "突破前高":
            score = 15
        elif pattern == "下影线阳线":
            score = 12
        elif pattern == "多方炮":
            score = 10
        elif pattern == "十字星":
            score = 10
        elif pattern == "阳线":
            score = 8
        elif pattern == "平盘":
            score = 4
        elif pattern == "阴线":
            score = 4
        elif pattern == "吊颈线":
            score = 0
            risks.append("顶部形态风险")
        elif pattern == "乌云盖顶":
            score = 0
            risks.append("顶部形态风险")
        else:
            score = 4
        
        details = {
            'score': score,
            'max_score': self.MAX_SCORE,
            'pattern': pattern,
            'change_pct': round(change_pct, 2),
            'is_positive': self._is_positive_candle(open_p, close),
            'is_limit_up': self._is_limit_up(close, prev_close, is_cyb_kcb),
            'is_at_high': is_at_high,
        }
        
        return score, details, risks


class VolumePriceScorer:
    """
    量价配合评分 (15分)
    
    评分逻辑:
    - 缩量涨停/温和放量(1.5-2倍): 15分
    - 底部/突破口倍量: 15分
    - 正常放量上涨: 12分
    - 缩量上涨: 10分
    - 高位巨量滞涨: 0分
    - 天量阴线: 0分
    
    换手率调整:
    - 3%-15%: 正常
    - <1%: 扣2分
    - >25%: 扣3分
    """
    
    MAX_SCORE = 15
    
    def calculate_volume_ratio(self, volume: float, ma5_vol: float) -> float:
        """
        计算量比
        
        Args:
            volume: 今日成交量
            ma5_vol: 5日均量
        
        Returns:
            量比
        """
        if ma5_vol <= 0:
            return 1.0
        return volume / ma5_vol
    
    def _classify_volume(self, volume_ratio: float) -> str:
        """
        分类成交量
        
        Returns:
            缩量/温和放量/放量/巨量
        """
        if volume_ratio < 0.8:
            return "缩量"
        elif volume_ratio < 1.5:
            return "正常"
        elif volume_ratio <= 2.0:
            return "温和放量"
        elif volume_ratio <= 3.0:
            return "放量"
        else:
            return "巨量"
    
    def _get_turnover_adjustment(self, turnover_rate: float) -> Tuple[int, str]:
        """
        根据换手率计算调整分数
        
        Args:
            turnover_rate: 换手率 (百分比, 如5.0表示5%)
        
        Returns:
            (调整分数, 描述)
        """
        if turnover_rate < 1:
            return -2, "换手率过低"
        elif turnover_rate > 25:
            return -3, "换手率过高"
        elif 3 <= turnover_rate <= 15:
            return 0, "换手率正常"
        else:
            return 0, "换手率偏离"
    
    def _is_limit_up(self, change_pct: float) -> bool:
        """判断是否涨停 (涨幅>=9.5%)"""
        return change_pct >= 9.5
    
    def _is_negative(self, change_pct: float) -> bool:
        """判断是否阴线"""
        return change_pct < 0
    
    def score(self, volume: float, ma5_vol: float, 
              change_pct: float, turnover_rate: float,
              is_at_bottom: bool = False,
              is_at_breakout: bool = False,
              is_at_high: bool = False) -> Tuple[float, Dict, List[str]]:
        """
        计算量价配合得分
        
        Args:
            volume: 今日成交量
            ma5_vol: 5日均量
            change_pct: 涨跌幅 (百分比, 如5.0表示5%)
            turnover_rate: 换手率 (百分比, 如5.0表示5%)
            is_at_bottom: 是否处于底部
            is_at_breakout: 是否处于突破位
            is_at_high: 是否处于高位
        
        Returns:
            (得分, 详情, 风险标记列表)
        """
        risks = []
        
        # 处理无效数据
        if volume <= 0:
            return 0, {
                'score': 0,
                'max_score': self.MAX_SCORE,
                'volume_type': '无成交',
                'volume_ratio': 0,
                'turnover_rate': turnover_rate,
            }, risks
        
        # 计算量比
        volume_ratio = self.calculate_volume_ratio(volume, ma5_vol)
        volume_type = self._classify_volume(volume_ratio)
        
        # 基础评分逻辑
        score = 0
        vol_price_type = ""
        
        # 1. 高位巨量滞涨 -> 0分
        if is_at_high and volume_type == "巨量" and abs(change_pct) < 3:
            score = 0
            vol_price_type = "高位巨量滞涨"
            risks.append("出货风险")
        
        # 2. 天量阴线 -> 0分
        elif volume_type == "巨量" and self._is_negative(change_pct):
            score = 0
            vol_price_type = "天量阴线"
            risks.append("出货风险")
        
        # 3. 缩量涨停 -> 15分
        elif volume_type == "缩量" and self._is_limit_up(change_pct):
            score = 15
            vol_price_type = "缩量涨停"
        
        # 4. 温和放量上涨 -> 15分
        elif volume_type == "温和放量" and change_pct > 0:
            score = 15
            vol_price_type = "温和放量上涨"
        
        # 5. 底部/突破位倍量 -> 15分
        elif (is_at_bottom or is_at_breakout) and volume_ratio >= 2.0 and change_pct > 0:
            score = 15
            vol_price_type = "底部/突破倍量"
        
        # 6. 正常放量上涨 -> 12分
        elif volume_type in ["放量", "正常"] and change_pct > 3:
            score = 12
            vol_price_type = "放量上涨"
        
        # 7. 缩量上涨 -> 10分
        elif volume_type == "缩量" and change_pct > 0:
            score = 10
            vol_price_type = "缩量上涨"
        
        # 8. 正常量能小涨 -> 8分
        elif volume_type == "正常" and change_pct > 0:
            score = 8
            vol_price_type = "正常上涨"
        
        # 9. 缩量下跌 -> 6分 (抛压减轻)
        elif volume_type == "缩量" and change_pct < 0:
            score = 6
            vol_price_type = "缩量下跌"
        
        # 10. 放量下跌 -> 3分
        elif volume_type in ["放量", "巨量"] and change_pct < 0:
            score = 3
            vol_price_type = "放量下跌"
        
        # 11. 其他情况 -> 5分
        else:
            score = 5
            vol_price_type = "量价一般"
        
        # 换手率调整
        turnover_adj, turnover_desc = self._get_turnover_adjustment(turnover_rate)
        score = max(0, min(self.MAX_SCORE, score + turnover_adj))
        
        details = {
            'score': score,
            'max_score': self.MAX_SCORE,
            'volume_type': vol_price_type,
            'volume_ratio': round(volume_ratio, 2),
            'volume_class': volume_type,
            'turnover_rate': round(turnover_rate, 2),
            'turnover_adjustment': turnover_adj,
            'turnover_desc': turnover_desc,
            'change_pct': round(change_pct, 2),
            'is_at_bottom': is_at_bottom,
            'is_at_breakout': is_at_breakout,
            'is_at_high': is_at_high,
        }
        
        return score, details, risks


class CapitalStrengthScorer:
    """
    资金强度评分 (15分)
    
    评分逻辑 (基于净流入占成交额比例):
    - 占比>10%: 15分
    - 占比5%-10%: 12分
    - 占比0%-5%: 8分
    - 占比-5%-0%: 5分
    - 占比<-10%: 0分
    """
    
    MAX_SCORE = 15
    
    def calculate_inflow_ratio(self, inflow: float, amount: float) -> float:
        """
        计算净流入占比
        
        Args:
            inflow: 主力净流入(元)
            amount: 成交额(元)
        
        Returns:
            净流入占比 (百分比)
        """
        if amount <= 0:
            return 0.0
        return (inflow / amount) * 100
    
    def _classify_capital_flow(self, inflow_ratio: float) -> str:
        """
        分类资金流向
        
        Args:
            inflow_ratio: 净流入占比 (百分比)
        
        Returns:
            资金流向类型
        """
        if inflow_ratio > 10:
            return "主力大幅流入"
        elif inflow_ratio > 5:
            return "主力明显流入"
        elif inflow_ratio > 0:
            return "主力小幅流入"
        elif inflow_ratio > -5:
            return "主力小幅流出"
        elif inflow_ratio > -10:
            return "主力明显流出"
        else:
            return "主力大幅流出"
    
    def score(self, main_net_inflow: float, 
              turnover_amount: float) -> Tuple[float, Dict, List[str]]:
        """
        计算资金强度得分
        
        Args:
            main_net_inflow: 主力净流入(元)
            turnover_amount: 成交额(元)
        
        Returns:
            (得分, 详情, 风险标记列表)
        """
        risks = []
        
        # 处理无效数据
        if turnover_amount <= 0:
            return 0, {
                'score': 0,
                'max_score': self.MAX_SCORE,
                'flow_type': '成交额无效',
                'inflow_ratio': 0,
                'main_net_inflow': main_net_inflow,
                'turnover_amount': turnover_amount,
            }, risks
        
        # 计算净流入占比
        inflow_ratio = self.calculate_inflow_ratio(main_net_inflow, turnover_amount)
        flow_type = self._classify_capital_flow(inflow_ratio)
        
        # 评分逻辑
        score = 0
        if inflow_ratio > 10:
            score = 15
        elif inflow_ratio > 5:
            score = 12
        elif inflow_ratio > 0:
            score = 8
        elif inflow_ratio > -5:
            score = 5
        elif inflow_ratio > -10:
            score = 2
        else:
            score = 0
            # 主力大幅流出时标记风险
            if inflow_ratio < -10:
                risks.append("资金大幅流出")
        
        details = {
            'score': score,
            'max_score': self.MAX_SCORE,
            'flow_type': flow_type,
            'inflow_ratio': round(inflow_ratio, 2),
            'main_net_inflow': main_net_inflow,
            'turnover_amount': turnover_amount,
        }
        
        return score, details, risks


class ThemeWindScorer:
    """
    题材风口评分 (25分) - A股短线第一生产力
    
    评分逻辑:
    - 主线题材+板块效应强: 25分
    - 支线题材+有助攻: 15分
    - 独立个股无板块: 8分
    - 无题材关联: 3分
    
    退潮调整:
    - 题材退潮期: 评分减半 + 风险标记
    """
    
    MAX_SCORE = 25
    
    def _match_hot_topics(self, concepts: List[str], hot_topics: List[str]) -> Tuple[List[str], bool]:
        """
        匹配热点题材
        
        Args:
            concepts: 股票概念列表
            hot_topics: 当前热点题材列表
        
        Returns:
            (匹配的热点题材, 是否主线题材)
        """
        if not concepts or not hot_topics:
            return [], False
        
        matched_topics = []
        for concept in concepts:
            for hot_topic in hot_topics:
                # 简单的字符串匹配，实际应用中可能需要更复杂的匹配逻辑
                if concept in hot_topic or hot_topic in concept:
                    matched_topics.append(hot_topic)
        
        # 去重
        matched_topics = list(set(matched_topics))
        
        # 判断是否主线题材 (假设热点题材列表前3个为主线)
        is_main_theme = False
        if matched_topics and len(hot_topics) > 0:
            main_themes = hot_topics[:3] if len(hot_topics) >= 3 else hot_topics
            is_main_theme = any(topic in main_themes for topic in matched_topics)
        
        return matched_topics, is_main_theme
    
    def _assess_sector_effect(self, sector_limit_up_count: int, is_sector_leader: bool) -> Tuple[str, int]:
        """
        评估板块效应
        
        Args:
            sector_limit_up_count: 板块涨停家数
            is_sector_leader: 是否板块龙头
        
        Returns:
            (板块效应描述, 效应强度分数)
        """
        if sector_limit_up_count >= 5:
            effect_desc = "板块效应强"
            effect_score = 10 if is_sector_leader else 8
        elif sector_limit_up_count >= 3:
            effect_desc = "板块效应中等"
            effect_score = 6 if is_sector_leader else 4
        elif sector_limit_up_count >= 1:
            effect_desc = "板块效应弱"
            effect_score = 3 if is_sector_leader else 2
        else:
            effect_desc = "无板块效应"
            effect_score = 0
        
        return effect_desc, effect_score
    
    def _detect_theme_fading(self, matched_topics: List[str], sector_limit_up_count: int) -> bool:
        """
        检测题材是否退潮
        
        Args:
            matched_topics: 匹配的热点题材
            sector_limit_up_count: 板块涨停家数
        
        Returns:
            是否退潮
        """
        # 简化的退潮判断逻辑：
        # 1. 有题材但板块涨停家数为0
        # 2. 实际应用中可能需要考虑更多因素，如题材持续时间、市场情绪等
        if matched_topics and sector_limit_up_count == 0:
            return True
        return False
    
    def score(self, concepts: List[str], 
              hot_topics: List[str],
              sector_limit_up_count: int,
              is_sector_leader: bool) -> Tuple[float, Dict, List[str]]:
        """
        计算题材风口得分
        
        Args:
            concepts: 股票概念列表
            hot_topics: 当前热点题材
            sector_limit_up_count: 板块涨停家数
            is_sector_leader: 是否板块龙头
        
        Returns:
            (得分, 详情, 风险标记列表)
        """
        risks = []
        
        # 匹配热点题材
        matched_topics, is_main_theme = self._match_hot_topics(concepts, hot_topics)
        
        # 评估板块效应
        sector_effect_desc, sector_effect_score = self._assess_sector_effect(
            sector_limit_up_count, is_sector_leader
        )
        
        # 检测题材退潮
        is_fading = self._detect_theme_fading(matched_topics, sector_limit_up_count)
        
        # 基础评分逻辑
        base_score = 0
        topic_type = ""
        
        if not matched_topics:
            # 无题材关联
            if concepts:
                base_score = 3
                topic_type = "无热点题材"
            else:
                base_score = 1
                topic_type = "无概念"
        elif is_main_theme:
            # 主线题材
            base_score = 15
            topic_type = "主线题材"
        else:
            # 支线题材
            base_score = 8
            topic_type = "支线题材"
        
        # 加上板块效应分数
        score = base_score + sector_effect_score
        
        # 题材退潮调整
        if is_fading:
            score = score // 2  # 评分减半
            risks.append("题材退潮风险")
            topic_type += "(退潮)"
        
        # 确保分数在有效范围内
        score = max(0, min(self.MAX_SCORE, score))
        
        details = {
            'score': score,
            'max_score': self.MAX_SCORE,
            'topic_type': topic_type,
            'matched_topics': matched_topics,
            'is_main_theme': is_main_theme,
            'sector_effect': sector_effect_desc,
            'sector_limit_up_count': sector_limit_up_count,
            'is_sector_leader': is_sector_leader,
            'is_fading': is_fading,
            'base_score': base_score,
            'sector_effect_score': sector_effect_score,
        }
        
        return score, details, risks


class StockActivityScorer:
    """
    股性活跃度评分 (10分) - 剔除死股
    
    评分逻辑:
    - 近20日有涨停: 10分
    - 近期有连板: +2分(额外)
    - 历史波动率高(日均振幅>3%): 8分
    - 近60日最大涨幅<10%: 2分
    - 长期横盘(织布机): 0分
    """
    
    MAX_SCORE = 10
    
    def has_limit_up_in_days(self, df: pd.DataFrame, days: int = 20) -> bool:
        """
        检查近N日是否有涨停
        
        Args:
            df: K线数据 (需包含 'change_pct' 或 'close'/'prev_close' 列)
            days: 检查天数
        
        Returns:
            是否有涨停
        """
        if df is None or len(df) == 0:
            return False
        
        # 取最近N日数据
        recent_df = df.tail(days) if len(df) >= days else df
        
        # 计算涨跌幅
        if 'change_pct' in recent_df.columns:
            change_pcts = recent_df['change_pct']
        elif 'close' in recent_df.columns:
            change_pcts = recent_df['close'].pct_change() * 100
        else:
            return False
        
        # 检查是否有涨停 (>=9.5% 或 >=19.5%)
        return (change_pcts >= 9.5).any() or (change_pcts >= 19.5).any()
    
    def count_consecutive_limit_ups(self, df: pd.DataFrame, days: int = 20) -> int:
        """
        统计近N日内的最大连板数
        
        Args:
            df: K线数据
            days: 检查天数
        
        Returns:
            最大连板数
        """
        if df is None or len(df) == 0:
            return 0
        
        # 取最近N日数据
        recent_df = df.tail(days) if len(df) >= days else df
        
        # 计算涨跌幅
        if 'change_pct' in recent_df.columns:
            change_pcts = recent_df['change_pct'].values
        elif 'close' in recent_df.columns:
            change_pcts = recent_df['close'].pct_change().values * 100
        else:
            return 0
        
        # 统计连板
        max_consecutive = 0
        current_consecutive = 0
        
        for pct in change_pcts:
            if pd.isna(pct):
                continue
            # 涨停判断 (9.5% 或 19.5%)
            if pct >= 9.5:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0
        
        return max_consecutive
    
    def calculate_volatility(self, df: pd.DataFrame, days: int = 20) -> float:
        """
        计算历史波动率 (日均振幅)
        
        Args:
            df: K线数据 (需包含 'high', 'low', 'close' 列)
            days: 计算天数
        
        Returns:
            日均振幅 (百分比)
        """
        if df is None or len(df) == 0:
            return 0.0
        
        # 取最近N日数据
        recent_df = df.tail(days) if len(df) >= days else df
        
        if 'high' not in recent_df.columns or 'low' not in recent_df.columns:
            return 0.0
        
        # 计算振幅 = (最高 - 最低) / 收盘价
        if 'close' in recent_df.columns:
            amplitudes = (recent_df['high'] - recent_df['low']) / recent_df['close'] * 100
        else:
            amplitudes = (recent_df['high'] - recent_df['low']) / recent_df['low'] * 100
        
        # 返回平均振幅
        return amplitudes.mean() if len(amplitudes) > 0 else 0.0
    
    def calculate_max_gain(self, df: pd.DataFrame, days: int = 60) -> float:
        """
        计算近N日最大涨幅
        
        Args:
            df: K线数据
            days: 计算天数
        
        Returns:
            最大涨幅 (百分比)
        """
        if df is None or len(df) == 0:
            return 0.0
        
        # 取最近N日数据
        recent_df = df.tail(days) if len(df) >= days else df
        
        if 'close' not in recent_df.columns or len(recent_df) < 2:
            return 0.0
        
        # 计算从最低点到最高点的涨幅
        min_close = recent_df['close'].min()
        max_close = recent_df['close'].max()
        
        if min_close <= 0:
            return 0.0
        
        return (max_close - min_close) / min_close * 100
    
    def is_sideways(self, df: pd.DataFrame, days: int = 60, threshold: float = 10.0) -> bool:
        """
        判断是否长期横盘 (织布机/心电图走势)
        
        Args:
            df: K线数据
            days: 检查天数
            threshold: 振幅阈值 (百分比)
        
        Returns:
            是否横盘
        """
        if df is None or len(df) == 0:
            return False
        
        # 取最近N日数据
        recent_df = df.tail(days) if len(df) >= days else df
        
        if 'close' not in recent_df.columns or len(recent_df) < 10:
            return False
        
        # 计算价格区间
        min_close = recent_df['close'].min()
        max_close = recent_df['close'].max()
        
        if min_close <= 0:
            return False
        
        # 价格波动范围
        price_range = (max_close - min_close) / min_close * 100
        
        # 如果价格波动范围小于阈值，认为是横盘
        return price_range < threshold
    
    def score(self, df: pd.DataFrame) -> Tuple[float, Dict, List[str]]:
        """
        计算股性活跃度得分
        
        Args:
            df: 近60日K线数据
        
        Returns:
            (得分, 详情, 风险标记列表)
        """
        risks = []
        
        # 处理无效数据
        if df is None or len(df) == 0:
            return 0, {
                'score': 0,
                'max_score': self.MAX_SCORE,
                'activity_type': '数据无效',
                'has_limit_up': False,
                'consecutive_limit_ups': 0,
                'volatility': 0,
                'max_gain_60d': 0,
                'is_sideways': False,
            }, risks
        
        # 计算各项指标
        has_limit_up_20d = self.has_limit_up_in_days(df, 20)
        consecutive_limit_ups = self.count_consecutive_limit_ups(df, 20)
        volatility = self.calculate_volatility(df, 20)
        max_gain_60d = self.calculate_max_gain(df, 60)
        is_sideways = self.is_sideways(df, 60)
        
        # 评分逻辑
        score = 0
        activity_type = ""
        
        # 1. 长期横盘 -> 0分
        if is_sideways:
            score = 0
            activity_type = "长期横盘"
            risks.append("股性差")
        
        # 2. 近60日最大涨幅<10% -> 2分
        elif max_gain_60d < 10:
            score = 2
            activity_type = "涨幅有限"
            risks.append("股性差")
        
        # 3. 近20日有涨停 -> 10分
        elif has_limit_up_20d:
            score = 10
            activity_type = "近期涨停"
            
            # 连板加分 (额外+2分，但不超过满分)
            if consecutive_limit_ups >= 2:
                score = min(self.MAX_SCORE, score + 2)
                activity_type = f"连板{consecutive_limit_ups}次"
        
        # 4. 历史波动率高 (日均振幅>3%) -> 8分
        elif volatility > 3:
            score = 8
            activity_type = "高波动"
        
        # 5. 中等波动率 (日均振幅2%-3%) -> 6分
        elif volatility > 2:
            score = 6
            activity_type = "中等波动"
        
        # 6. 低波动率 -> 4分
        else:
            score = 4
            activity_type = "低波动"
        
        details = {
            'score': score,
            'max_score': self.MAX_SCORE,
            'activity_type': activity_type,
            'has_limit_up': has_limit_up_20d,
            'consecutive_limit_ups': consecutive_limit_ups,
            'volatility': round(volatility, 2),
            'max_gain_60d': round(max_gain_60d, 2),
            'is_sideways': is_sideways,
        }
        
        return score, details, risks


class RiskMarker:
    """
    风险标记器 - 识别并标记高风险情况
    
    风险类型:
    - HIGH_CHASE: 追高风险 (乖离率>15%)
    - DISTRIBUTION: 出货风险 (天量阴线)
    - THEME_FADE: 题材退潮风险
    - LOW_ACTIVITY: 股性差 (长期无涨停)
    """
    
    RISK_TYPES = {
        'HIGH_CHASE': '追高风险',
        'DISTRIBUTION': '出货风险',
        'THEME_FADE': '题材退潮风险',
        'LOW_ACTIVITY': '股性差',
    }
    
    def mark_high_chase_risk(self, deviation_rate: float, threshold: float = 15.0) -> Optional[str]:
        """
        标记追高风险
        
        Args:
            deviation_rate: 乖离率 (百分比)
            threshold: 阈值
        
        Returns:
            风险标记或None
        """
        if deviation_rate > threshold:
            return self.RISK_TYPES['HIGH_CHASE']
        return None
    
    def mark_distribution_risk(self, volume_ratio: float, change_pct: float,
                                is_at_high: bool = False) -> Optional[str]:
        """
        标记出货风险
        
        Args:
            volume_ratio: 量比
            change_pct: 涨跌幅 (百分比)
            is_at_high: 是否处于高位
        
        Returns:
            风险标记或None
        """
        # 天量阴线 (量比>3 且 下跌)
        if volume_ratio > 3 and change_pct < 0:
            return self.RISK_TYPES['DISTRIBUTION']
        
        # 高位巨量滞涨
        if is_at_high and volume_ratio > 3 and abs(change_pct) < 3:
            return self.RISK_TYPES['DISTRIBUTION']
        
        return None
    
    def mark_theme_fade_risk(self, is_theme_fading: bool) -> Optional[str]:
        """
        标记题材退潮风险
        
        Args:
            is_theme_fading: 题材是否退潮
        
        Returns:
            风险标记或None
        """
        if is_theme_fading:
            return self.RISK_TYPES['THEME_FADE']
        return None
    
    def mark_low_activity_risk(self, has_limit_up_20d: bool, 
                                is_sideways: bool,
                                max_gain_60d: float) -> Optional[str]:
        """
        标记股性差风险
        
        Args:
            has_limit_up_20d: 近20日是否有涨停
            is_sideways: 是否长期横盘
            max_gain_60d: 近60日最大涨幅
        
        Returns:
            风险标记或None
        """
        # 长期横盘
        if is_sideways:
            return self.RISK_TYPES['LOW_ACTIVITY']
        
        # 近60日最大涨幅<10% 且 近20日无涨停
        if max_gain_60d < 10 and not has_limit_up_20d:
            return self.RISK_TYPES['LOW_ACTIVITY']
        
        return None
    
    def mark_risks(self, score_details: Dict) -> List[str]:
        """
        根据评分详情标记风险
        
        Args:
            score_details: 各维度评分详情
        
        Returns:
            风险标记列表
        """
        risks = []
        
        # 1. 追高风险 - 从趋势位置评分中获取乖离率
        trend_details = score_details.get('trend_position', {})
        deviation_rate = trend_details.get('deviation_rate', 0)
        high_chase_risk = self.mark_high_chase_risk(deviation_rate)
        if high_chase_risk:
            risks.append(high_chase_risk)
        
        # 2. 出货风险 - 从量价评分中获取
        volume_details = score_details.get('volume_price', {})
        volume_ratio = volume_details.get('volume_ratio', 1)
        change_pct = volume_details.get('change_pct', 0)
        is_at_high = volume_details.get('is_at_high', False)
        distribution_risk = self.mark_distribution_risk(volume_ratio, change_pct, is_at_high)
        if distribution_risk:
            risks.append(distribution_risk)
        
        # 3. 题材退潮风险 - 从题材评分中获取
        theme_details = score_details.get('theme_wind', {})
        is_theme_fading = theme_details.get('is_fading', False)
        theme_fade_risk = self.mark_theme_fade_risk(is_theme_fading)
        if theme_fade_risk:
            risks.append(theme_fade_risk)
        
        # 4. 股性差风险 - 从股性活跃度评分中获取
        activity_details = score_details.get('stock_activity', {})
        has_limit_up = activity_details.get('has_limit_up', False)
        is_sideways = activity_details.get('is_sideways', False)
        max_gain_60d = activity_details.get('max_gain_60d', 100)
        low_activity_risk = self.mark_low_activity_risk(has_limit_up, is_sideways, max_gain_60d)
        if low_activity_risk:
            risks.append(low_activity_risk)
        
        # 去重
        return list(set(risks))


class ScorerV6:
    """
    v6.0 评分器 - 6维度100分体系
    
    维度权重:
    - 趋势与位置: 20分
    - K线与形态: 15分
    - 量价配合: 15分
    - 资金强度: 15分
    - 题材风口: 25分
    - 股性活跃度: 10分
    """
    
    DEFAULT_WEIGHTS = {
        'trend_position': 20,      # 趋势与位置
        'kline_pattern': 15,       # K线与形态
        'volume_price': 15,        # 量价配合
        'capital_strength': 15,    # 资金强度
        'theme_wind': 25,          # 题材风口
        'stock_activity': 10,      # 股性活跃度
    }
    
    def __init__(self, weights: Optional[Dict[str, int]] = None, 
                 enable_logging: bool = True,
                 log_dir: str = "data/score_logs"):
        """
        初始化评分器
        
        Args:
            weights: 可选的权重配置，默认使用标准权重
            enable_logging: 是否启用评分日志记录
            log_dir: 日志存储目录
        """
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
        self.enable_logging = enable_logging
        
        # 初始化子评分器
        self.trend_position_scorer = TrendPositionScorer()
        self.kline_pattern_scorer = KLinePatternScorer()
        self.volume_price_scorer = VolumePriceScorer()
        self.capital_strength_scorer = CapitalStrengthScorer()
        self.theme_wind_scorer = ThemeWindScorer()
        self.stock_activity_scorer = StockActivityScorer()
        self.risk_marker = RiskMarker()
        
        # 初始化评分日志记录器
        self._score_logger = ScoreLogger(log_dir) if enable_logging else None
    
    @property
    def score_logger(self) -> Optional['ScoreLogger']:
        """获取评分日志记录器"""
        return self._score_logger
    
    def score_stock(self, stock_data: Dict, market_data: Dict = None,
                    log_score: bool = True) -> Tuple[float, Dict]:
        """
        对单只股票进行综合评分
        
        Args:
            stock_data: 股票数据
            market_data: 市场数据（热点、板块等）
            log_score: 是否记录评分日志
        
        Returns:
            (总分, 详情字典包含各维度分数和风险标记)
        """
        if market_data is None:
            market_data = {}
        
        all_risks = []
        
        # 1. 趋势与位置评分
        trend_score, trend_details, trend_risks = self.trend_position_scorer.score(
            price=stock_data.get('close', 0),
            ma5=stock_data.get('ma5', 0),
            ma10=stock_data.get('ma10', 0),
            ma20=stock_data.get('ma20', 0),
            ma60=stock_data.get('ma60', 0),
            price_percentile=stock_data.get('price_percentile', 50),
            prev_close=stock_data.get('prev_close'),
        )
        all_risks.extend(trend_risks)
        
        # 2. K线与形态评分
        # 判断是否创业板/科创板
        stock_code = stock_data.get('code', '')
        is_cyb_kcb = stock_code.startswith('300') or stock_code.startswith('688')
        
        # 判断是否高位 (使用价格分位点)
        price_percentile = stock_data.get('price_percentile', 50)
        is_at_high = price_percentile >= 80
        
        kline_score, kline_details, kline_risks = self.kline_pattern_scorer.score(
            open_p=stock_data.get('open', 0),
            high=stock_data.get('high', 0),
            low=stock_data.get('low', 0),
            close=stock_data.get('close', 0),
            prev_close=stock_data.get('prev_close', 0),
            prev_open=stock_data.get('prev_open'),
            prev_high=stock_data.get('prev_high'),
            prev_low=stock_data.get('prev_low'),
            is_at_high=is_at_high,
            is_cyb_kcb=is_cyb_kcb,
        )
        all_risks.extend(kline_risks)
        
        # 3. 量价配合评分
        # 判断是否底部/突破位
        is_at_bottom = price_percentile <= 20
        is_at_breakout = stock_data.get('is_breakout', False)
        
        volume_score, volume_details, volume_risks = self.volume_price_scorer.score(
            volume=stock_data.get('volume', 0),
            ma5_vol=stock_data.get('ma5_vol', 0),
            change_pct=stock_data.get('change_pct', 0),
            turnover_rate=stock_data.get('turnover_rate', 5),
            is_at_bottom=is_at_bottom,
            is_at_breakout=is_at_breakout,
            is_at_high=is_at_high,
        )
        all_risks.extend(volume_risks)
        
        # 4. 资金强度评分
        capital_score, capital_details, capital_risks = self.capital_strength_scorer.score(
            main_net_inflow=stock_data.get('main_net_inflow', 0),
            turnover_amount=stock_data.get('turnover_amount', 1),
        )
        all_risks.extend(capital_risks)
        
        # 5. 题材风口评分
        theme_score, theme_details, theme_risks = self.theme_wind_scorer.score(
            concepts=stock_data.get('concepts', []),
            hot_topics=market_data.get('hot_topics', []),
            sector_limit_up_count=market_data.get('sector_limit_up_count', 0),
            is_sector_leader=stock_data.get('is_sector_leader', False),
        )
        all_risks.extend(theme_risks)
        
        # 6. 股性活跃度评分
        kline_df = stock_data.get('kline_df')
        activity_score, activity_details, activity_risks = self.stock_activity_scorer.score(kline_df)
        all_risks.extend(activity_risks)
        
        # 计算总分
        total_score = trend_score + kline_score + volume_score + capital_score + theme_score + activity_score
        total_score = max(0, min(100, total_score))
        
        # 构建详情字典
        details = {
            'total_score': total_score,
            'trend_position': trend_details,
            'kline_pattern': kline_details,
            'volume_price': volume_details,
            'capital_strength': capital_details,
            'theme_wind': theme_details,
            'stock_activity': activity_details,
            'risks': all_risks,
        }
        
        # 使用 RiskMarker 进行综合风险标记
        additional_risks = self.risk_marker.mark_risks(details)
        # 合并风险标记并去重
        all_risks_set = set(all_risks) | set(additional_risks)
        details['risks'] = list(all_risks_set)
        
        # 记录评分日志
        if log_score and self._score_logger is not None:
            stock_code = stock_data.get('code', '')
            stock_name = stock_data.get('name', '')
            trade_date = stock_data.get('trade_date')
            self._score_logger.log_score(
                stock_code=stock_code,
                stock_name=stock_name,
                total_score=total_score,
                details=details,
                market_data=market_data,
                trade_date=trade_date
            )
        
        return total_score, details
    
    def get_score_summary(self, total_score: float, details: Dict) -> str:
        """
        生成可读的评分摘要
        
        Args:
            total_score: 总分
            details: 评分详情
        
        Returns:
            评分摘要字符串
        """
        lines = []
        lines.append(f"📊 评分系统v6.0 总分: {total_score:.0f}/100")
        lines.append("")
        
        dimension_names = {
            'trend_position': '趋势与位置',
            'kline_pattern': 'K线与形态',
            'volume_price': '量价配合',
            'capital_strength': '资金强度',
            'theme_wind': '题材风口',
            'stock_activity': '股性活跃度',
        }
        
        for dim_key, dim_name in dimension_names.items():
            dim_data = details.get(dim_key, {})
            score = dim_data.get('score', 0)
            max_score = dim_data.get('max_score', 0)
            
            # 获取描述
            desc = ""
            if 'trend_type' in dim_data:
                desc = dim_data['trend_type']
            elif 'pattern' in dim_data:
                desc = dim_data['pattern']
            elif 'volume_type' in dim_data:
                desc = dim_data['volume_type']
            elif 'flow_type' in dim_data:
                desc = dim_data['flow_type']
            elif 'topic_type' in dim_data:
                desc = dim_data['topic_type']
            elif 'activity_type' in dim_data:
                desc = dim_data['activity_type']
            
            lines.append(f"- {dim_name}: {score}/{max_score} ({desc})")
        
        # 风险标记
        risks = details.get('risks', [])
        if risks:
            lines.append("")
            lines.append("⚠️ 风险提示:")
            for risk in risks:
                lines.append(f"  - {risk}")
        
        return "\n".join(lines)


class ScoreLogger:
    """
    评分日志记录器 - 记录每次评分的详细信息，支持回测分析
    
    功能:
    - 记录每次评分的详细信息
    - 支持按日期存储日志
    - 支持导出为CSV/JSON格式
    - 支持回测分析查询
    
    Requirements: 7.5
    """
    
    def __init__(self, log_dir: str = "data/score_logs"):
        """
        初始化评分日志记录器
        
        Args:
            log_dir: 日志存储目录
        """
        self.log_dir = log_dir
        self._ensure_log_dir()
        self._score_records: List[Dict] = []
    
    def _ensure_log_dir(self) -> None:
        """确保日志目录存在"""
        os.makedirs(self.log_dir, exist_ok=True)
    
    def log_score(self, stock_code: str, stock_name: str, 
                  total_score: float, details: Dict,
                  market_data: Dict = None,
                  trade_date: str = None) -> None:
        """
        记录单只股票的评分信息
        
        Args:
            stock_code: 股票代码
            stock_name: 股票名称
            total_score: 总分
            details: 评分详情
            market_data: 市场数据
            trade_date: 交易日期 (YYYY-MM-DD格式)
        """
        if trade_date is None:
            trade_date = datetime.now().strftime('%Y-%m-%d')
        
        record = {
            'timestamp': datetime.now().isoformat(),
            'trade_date': trade_date,
            'stock_code': stock_code,
            'stock_name': stock_name,
            'total_score': total_score,
            # 各维度得分
            'trend_position_score': details.get('trend_position', {}).get('score', 0),
            'kline_pattern_score': details.get('kline_pattern', {}).get('score', 0),
            'volume_price_score': details.get('volume_price', {}).get('score', 0),
            'capital_strength_score': details.get('capital_strength', {}).get('score', 0),
            'theme_wind_score': details.get('theme_wind', {}).get('score', 0),
            'stock_activity_score': details.get('stock_activity', {}).get('score', 0),
            # 关键指标
            'trend_type': details.get('trend_position', {}).get('trend_type', ''),
            'deviation_rate': details.get('trend_position', {}).get('deviation_rate', 0),
            'kline_pattern': details.get('kline_pattern', {}).get('pattern', ''),
            'change_pct': details.get('kline_pattern', {}).get('change_pct', 0),
            'volume_type': details.get('volume_price', {}).get('volume_type', ''),
            'volume_ratio': details.get('volume_price', {}).get('volume_ratio', 0),
            'turnover_rate': details.get('volume_price', {}).get('turnover_rate', 0),
            'inflow_ratio': details.get('capital_strength', {}).get('inflow_ratio', 0),
            'topic_type': details.get('theme_wind', {}).get('topic_type', ''),
            'matched_topics': ','.join(details.get('theme_wind', {}).get('matched_topics', [])),
            'activity_type': details.get('stock_activity', {}).get('activity_type', ''),
            'has_limit_up': details.get('stock_activity', {}).get('has_limit_up', False),
            'volatility': details.get('stock_activity', {}).get('volatility', 0),
            # 风险标记
            'risks': ','.join(details.get('risks', [])),
            'risk_count': len(details.get('risks', [])),
            # 市场数据
            'hot_topics': ','.join(market_data.get('hot_topics', [])) if market_data else '',
        }
        
        self._score_records.append(record)
        
        # 记录到日志
        logger.info(f"评分记录: {stock_code} {stock_name} 总分={total_score:.0f} "
                   f"趋势={record['trend_position_score']} K线={record['kline_pattern_score']} "
                   f"量价={record['volume_price_score']} 资金={record['capital_strength_score']} "
                   f"题材={record['theme_wind_score']} 股性={record['stock_activity_score']} "
                   f"风险={record['risks']}")
    
    def log_batch_scores(self, scores: List[Tuple[str, str, float, Dict]], 
                         market_data: Dict = None,
                         trade_date: str = None) -> None:
        """
        批量记录评分信息
        
        Args:
            scores: 评分列表 [(stock_code, stock_name, total_score, details), ...]
            market_data: 市场数据
            trade_date: 交易日期
        """
        for stock_code, stock_name, total_score, details in scores:
            self.log_score(stock_code, stock_name, total_score, details, 
                          market_data, trade_date)
    
    def save_to_csv(self, filename: str = None) -> str:
        """
        保存评分记录到CSV文件
        
        Args:
            filename: 文件名，默认使用日期命名
        
        Returns:
            保存的文件路径
        """
        if not self._score_records:
            logger.warning("没有评分记录可保存")
            return ""
        
        if filename is None:
            filename = f"score_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        filepath = os.path.join(self.log_dir, filename)
        
        df = pd.DataFrame(self._score_records)
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        
        logger.info(f"评分日志已保存到: {filepath}")
        return filepath
    
    def save_to_json(self, filename: str = None) -> str:
        """
        保存评分记录到JSON文件
        
        Args:
            filename: 文件名，默认使用日期命名
        
        Returns:
            保存的文件路径
        """
        if not self._score_records:
            logger.warning("没有评分记录可保存")
            return ""
        
        if filename is None:
            filename = f"score_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        filepath = os.path.join(self.log_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self._score_records, f, ensure_ascii=False, indent=2)
        
        logger.info(f"评分日志已保存到: {filepath}")
        return filepath
    
    def append_to_daily_log(self, trade_date: str = None) -> str:
        """
        追加到每日日志文件
        
        Args:
            trade_date: 交易日期
        
        Returns:
            日志文件路径
        """
        if not self._score_records:
            return ""
        
        if trade_date is None:
            trade_date = datetime.now().strftime('%Y-%m-%d')
        
        filename = f"score_log_{trade_date.replace('-', '')}.csv"
        filepath = os.path.join(self.log_dir, filename)
        
        df = pd.DataFrame(self._score_records)
        
        # 如果文件存在，追加；否则创建新文件
        if os.path.exists(filepath):
            df.to_csv(filepath, mode='a', header=False, index=False, encoding='utf-8-sig')
        else:
            df.to_csv(filepath, index=False, encoding='utf-8-sig')
        
        logger.info(f"评分日志已追加到: {filepath}")
        return filepath
    
    def get_records(self) -> List[Dict]:
        """获取所有评分记录"""
        return self._score_records.copy()
    
    def get_records_df(self) -> pd.DataFrame:
        """获取评分记录DataFrame"""
        return pd.DataFrame(self._score_records)
    
    def clear_records(self) -> None:
        """清空内存中的评分记录"""
        self._score_records.clear()
    
    def load_log_file(self, filepath: str) -> pd.DataFrame:
        """
        加载日志文件
        
        Args:
            filepath: 日志文件路径
        
        Returns:
            评分记录DataFrame
        """
        if filepath.endswith('.csv'):
            return pd.read_csv(filepath, encoding='utf-8-sig')
        elif filepath.endswith('.json'):
            with open(filepath, 'r', encoding='utf-8') as f:
                records = json.load(f)
            return pd.DataFrame(records)
        else:
            raise ValueError(f"不支持的文件格式: {filepath}")
    
    def get_log_files(self) -> List[Dict]:
        """
        获取所有日志文件列表
        
        Returns:
            日志文件信息列表
        """
        if not os.path.exists(self.log_dir):
            return []
        
        log_files = []
        for filename in os.listdir(self.log_dir):
            if filename.startswith('score_log_') and (filename.endswith('.csv') or filename.endswith('.json')):
                filepath = os.path.join(self.log_dir, filename)
                stat = os.stat(filepath)
                log_files.append({
                    'filename': filename,
                    'path': filepath,
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                })
        
        # 按修改时间降序排序
        log_files.sort(key=lambda x: x['modified'], reverse=True)
        return log_files
    
    def analyze_score_distribution(self, df: pd.DataFrame = None) -> Dict:
        """
        分析评分分布
        
        Args:
            df: 评分记录DataFrame，默认使用内存中的记录
        
        Returns:
            分析结果字典
        """
        if df is None:
            df = self.get_records_df()
        
        if df.empty:
            return {}
        
        analysis = {
            'total_records': len(df),
            'score_stats': {
                'mean': df['total_score'].mean(),
                'std': df['total_score'].std(),
                'min': df['total_score'].min(),
                'max': df['total_score'].max(),
                'median': df['total_score'].median(),
            },
            'score_distribution': {
                '80-100': len(df[df['total_score'] >= 80]),
                '70-79': len(df[(df['total_score'] >= 70) & (df['total_score'] < 80)]),
                '60-69': len(df[(df['total_score'] >= 60) & (df['total_score'] < 70)]),
                '<60': len(df[df['total_score'] < 60]),
            },
            'dimension_means': {
                'trend_position': df['trend_position_score'].mean(),
                'kline_pattern': df['kline_pattern_score'].mean(),
                'volume_price': df['volume_price_score'].mean(),
                'capital_strength': df['capital_strength_score'].mean(),
                'theme_wind': df['theme_wind_score'].mean(),
                'stock_activity': df['stock_activity_score'].mean(),
            },
            'risk_stats': {
                'total_with_risks': len(df[df['risk_count'] > 0]),
                'risk_rate': len(df[df['risk_count'] > 0]) / len(df) * 100 if len(df) > 0 else 0,
            },
        }
        
        return analysis
    
    def get_high_score_stocks(self, df: pd.DataFrame = None, 
                               min_score: float = 80) -> pd.DataFrame:
        """
        获取高分股票
        
        Args:
            df: 评分记录DataFrame
            min_score: 最低分数阈值
        
        Returns:
            高分股票DataFrame
        """
        if df is None:
            df = self.get_records_df()
        
        if df.empty:
            return pd.DataFrame()
        
        return df[df['total_score'] >= min_score].sort_values('total_score', ascending=False)
    
    def get_risky_stocks(self, df: pd.DataFrame = None) -> pd.DataFrame:
        """
        获取有风险标记的股票
        
        Args:
            df: 评分记录DataFrame
        
        Returns:
            有风险股票DataFrame
        """
        if df is None:
            df = self.get_records_df()
        
        if df.empty:
            return pd.DataFrame()
        
        return df[df['risk_count'] > 0].sort_values('risk_count', ascending=False)
