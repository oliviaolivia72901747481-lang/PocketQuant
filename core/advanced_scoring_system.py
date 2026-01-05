"""
高级股票评分系统 - Advanced Stock Scoring System

基于量化金融理论和技术分析的精密评分模型
采用多维度、非线性评分函数，结合市场微观结构理论

作者: 卓越股票分析师
版本: 2.0 (精密量化版)
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
from dataclasses import dataclass
import math


@dataclass
class ScoringWeights:
    """评分权重配置"""
    momentum_score: float = 35.0      # 动量得分权重 (涨幅)
    liquidity_score: float = 25.0     # 流动性得分权重 (换手率)
    volume_score: float = 25.0        # 成交量得分权重 (量比)
    valuation_score: float = 15.0     # 估值得分权重 (PE)
    
    def validate(self) -> bool:
        """验证权重总和是否为100"""
        total = self.momentum_score + self.liquidity_score + self.volume_score + self.valuation_score
        return abs(total - 100.0) < 0.01


class AdvancedScoringSystem:
    """
    高级股票评分系统
    
    核心理念:
    1. 非线性评分函数 - 使用高斯分布、对数函数等数学模型
    2. 动态权重调整 - 根据市场环境调整各指标权重
    3. 风险调整收益 - 考虑波动率对收益的影响
    4. 市场微观结构 - 结合订单流、价格发现等理论
    """
    
    def __init__(self, weights: Optional[ScoringWeights] = None):
        """
        初始化评分系统
        
        Args:
            weights: 自定义权重配置，默认使用标准配置
        """
        self.weights = weights or ScoringWeights()
        if not self.weights.validate():
            raise ValueError("权重总和必须为100%")
    
    def momentum_score(self, change_pct: float, volatility: Optional[float] = None) -> Tuple[float, Dict]:
        """
        动量评分 - 基于风险调整收益理论
        
        核心思想:
        1. 最优涨幅区间: 3-6% (黄金区间)
        2. 风险调整: 考虑波动率对收益质量的影响
        3. 非线性衰减: 偏离最优区间时得分非线性下降
        
        Args:
            change_pct: 涨跌幅百分比
            volatility: 波动率 (可选)
        
        Returns:
            (得分, 详细信息)
        """
        # 定义最优区间参数
        optimal_center = 4.5  # 最优中心点
        optimal_width = 1.5   # 最优宽度
        max_score = 35.0
        
        # 使用高斯函数计算基础得分
        distance_from_optimal = abs(change_pct - optimal_center)
        
        if distance_from_optimal <= optimal_width:
            # 在最优区间内，使用平顶高斯
            base_score = max_score
        else:
            # 超出最优区间，使用高斯衰减
            excess_distance = distance_from_optimal - optimal_width
            decay_factor = math.exp(-(excess_distance ** 2) / (2 * (optimal_width ** 2)))
            base_score = max_score * decay_factor
        
        # 风险调整 (如果提供波动率)
        risk_adjustment = 1.0
        if volatility is not None:
            # 波动率过高时降低得分
            if volatility > 0.05:  # 5%以上波动率
                risk_adjustment = max(0.7, 1 - (volatility - 0.05) * 2)
        
        final_score = base_score * risk_adjustment
        
        # 边界处理
        if change_pct < 0:
            final_score *= 0.1  # 下跌股票大幅降分
        elif change_pct > 10:
            final_score *= 0.3  # 涨幅过大风险增加
        
        details = {
            'optimal_center': optimal_center,
            'distance_from_optimal': distance_from_optimal,
            'base_score': base_score,
            'risk_adjustment': risk_adjustment,
            'category': self._categorize_momentum(change_pct)
        }
        
        return min(max_score, max(0, final_score)), details
    
    def liquidity_score(self, turnover_rate: float, market_cap: Optional[float] = None) -> Tuple[float, Dict]:
        """
        流动性评分 - 基于市场微观结构理论
        
        核心思想:
        1. 适度换手率最优: 2-8% (既有活跃度又不过度投机)
        2. 市值调整: 大盘股和小盘股的换手率标准不同
        3. 流动性溢价: 高流动性降低交易成本
        
        Args:
            turnover_rate: 换手率百分比
            market_cap: 市值 (可选，用于调整标准)
        
        Returns:
            (得分, 详细信息)
        """
        max_score = 25.0
        
        # 根据市值调整最优区间
        if market_cap is not None:
            if market_cap > 1000:  # 大盘股 (>1000亿)
                optimal_min, optimal_max = 1.5, 6.0
            elif market_cap > 300:  # 中盘股 (300-1000亿)
                optimal_min, optimal_max = 2.0, 8.0
            else:  # 小盘股 (<300亿)
                optimal_min, optimal_max = 3.0, 12.0
        else:
            optimal_min, optimal_max = 2.0, 8.0  # 默认标准
        
        # 计算得分
        if optimal_min <= turnover_rate <= optimal_max:
            # 在最优区间内，使用二次函数达到峰值
            center = (optimal_min + optimal_max) / 2
            normalized_pos = 1 - abs(turnover_rate - center) / (optimal_max - optimal_min) * 2
            base_score = max_score * (0.8 + 0.2 * normalized_pos)
        else:
            # 超出最优区间，使用对数衰减
            if turnover_rate < optimal_min:
                # 换手率过低 - 流动性不足
                ratio = turnover_rate / optimal_min
                base_score = max_score * (0.3 + 0.5 * ratio)
            else:
                # 换手率过高 - 过度投机
                excess_ratio = turnover_rate / optimal_max
                if excess_ratio <= 2:
                    base_score = max_score * (1 - 0.3 * (excess_ratio - 1))
                else:
                    base_score = max_score * 0.4 * math.exp(-(excess_ratio - 2) * 0.5)
        
        # 极端情况处理
        if turnover_rate > 50:  # 超高换手率，风险极大
            base_score *= 0.1
        elif turnover_rate < 0.5:  # 极低换手率，流动性风险
            base_score *= 0.2
        
        details = {
            'optimal_range': (optimal_min, optimal_max),
            'category': self._categorize_liquidity(turnover_rate),
            'liquidity_premium': base_score / max_score
        }
        
        return min(max_score, max(0, base_score)), details
    
    def volume_score(self, volume_ratio: float, price_change: float) -> Tuple[float, Dict]:
        """
        成交量评分 - 基于量价关系理论
        
        核心思想:
        1. 量价配合: 上涨配合放量最优
        2. 适度放量: 1.5-3倍量比最佳
        3. 异常放量: 超过5倍需要警惕
        
        Args:
            volume_ratio: 量比
            price_change: 价格变化百分比
        
        Returns:
            (得分, 详细信息)
        """
        max_score = 25.0
        
        # 基础量比评分
        if 1.5 <= volume_ratio <= 3.0:
            # 最优量比区间
            center = 2.25
            distance = abs(volume_ratio - center)
            base_score = max_score * (1 - distance / 1.5 * 0.2)
        elif 1.0 <= volume_ratio < 1.5:
            # 温和放量
            base_score = max_score * (0.6 + 0.3 * (volume_ratio - 1) / 0.5)
        elif 3.0 < volume_ratio <= 5.0:
            # 较大放量
            base_score = max_score * (0.8 - 0.3 * (volume_ratio - 3) / 2)
        else:
            # 极端情况
            if volume_ratio < 1.0:
                base_score = max_score * 0.3 * volume_ratio
            else:  # volume_ratio > 5.0
                base_score = max_score * 0.3 * math.exp(-(volume_ratio - 5) * 0.2)
        
        # 量价配合度调整
        volume_price_synergy = self._calculate_volume_price_synergy(volume_ratio, price_change)
        synergy_multiplier = 0.8 + 0.4 * volume_price_synergy  # 0.8-1.2倍调整
        
        final_score = base_score * synergy_multiplier
        
        details = {
            'base_volume_score': base_score,
            'volume_price_synergy': volume_price_synergy,
            'synergy_multiplier': synergy_multiplier,
            'category': self._categorize_volume(volume_ratio)
        }
        
        return min(max_score, max(0, final_score)), details
    
    def valuation_score(self, pe_ratio: float, sector_avg_pe: Optional[float] = None) -> Tuple[float, Dict]:
        """
        估值评分 - 基于相对估值理论
        
        核心思想:
        1. 合理估值区间: PE 15-30倍
        2. 行业相对估值: 与行业平均PE比较
        3. 成长性溢价: 高成长股可容忍更高PE
        
        Args:
            pe_ratio: 市盈率
            sector_avg_pe: 行业平均PE (可选)
        
        Returns:
            (得分, 详细信息)
        """
        max_score = 15.0
        
        # 处理异常PE值
        if pe_ratio <= 0:
            return 2.0, {'category': '亏损股', 'risk_level': 'high'}
        
        if pe_ratio > 200:
            return 1.0, {'category': '极高估值', 'risk_level': 'extreme'}
        
        # 基础估值评分
        if 15 <= pe_ratio <= 30:
            # 合理估值区间
            center = 22.5
            distance = abs(pe_ratio - center)
            base_score = max_score * (1 - distance / 15 * 0.2)
        elif 10 <= pe_ratio < 15:
            # 低估值
            base_score = max_score * (0.7 + 0.25 * (pe_ratio - 10) / 5)
        elif 30 < pe_ratio <= 50:
            # 高估值但可接受
            base_score = max_score * (0.8 - 0.4 * (pe_ratio - 30) / 20)
        elif 5 <= pe_ratio < 10:
            # 超低估值，可能有问题
            base_score = max_score * (0.4 + 0.3 * (pe_ratio - 5) / 5)
        else:
            # 极端估值
            if pe_ratio < 5:
                base_score = max_score * 0.2
            else:  # pe_ratio > 50
                base_score = max_score * 0.3 * math.exp(-(pe_ratio - 50) / 30)
        
        # 行业相对估值调整
        relative_multiplier = 1.0
        if sector_avg_pe is not None and sector_avg_pe > 0:
            relative_pe = pe_ratio / sector_avg_pe
            if 0.7 <= relative_pe <= 1.3:
                # 与行业估值接近
                relative_multiplier = 1.0 + 0.1 * (1 - abs(relative_pe - 1) / 0.3)
            elif relative_pe < 0.7:
                # 相对低估
                relative_multiplier = 1.1
            else:
                # 相对高估
                relative_multiplier = 0.9
        
        final_score = base_score * relative_multiplier
        
        details = {
            'base_valuation_score': base_score,
            'relative_pe': pe_ratio / sector_avg_pe if sector_avg_pe else None,
            'relative_multiplier': relative_multiplier,
            'category': self._categorize_valuation(pe_ratio)
        }
        
        return min(max_score, max(0, final_score)), details
    
    def calculate_comprehensive_score(self, 
                                    change_pct: float,
                                    turnover_rate: float, 
                                    volume_ratio: float,
                                    pe_ratio: float,
                                    **kwargs) -> Dict:
        """
        计算综合评分
        
        Args:
            change_pct: 涨跌幅
            turnover_rate: 换手率
            volume_ratio: 量比
            pe_ratio: 市盈率
            **kwargs: 其他可选参数
        
        Returns:
            包含各项得分和综合得分的字典
        """
        # 计算各项得分
        momentum_score, momentum_details = self.momentum_score(
            change_pct, kwargs.get('volatility')
        )
        
        liquidity_score, liquidity_details = self.liquidity_score(
            turnover_rate, kwargs.get('market_cap')
        )
        
        volume_score, volume_details = self.volume_score(
            volume_ratio, change_pct
        )
        
        valuation_score, valuation_details = self.valuation_score(
            pe_ratio, kwargs.get('sector_avg_pe')
        )
        
        # 计算综合得分
        comprehensive_score = (
            momentum_score * self.weights.momentum_score / 35.0 +
            liquidity_score * self.weights.liquidity_score / 25.0 +
            volume_score * self.weights.volume_score / 25.0 +
            valuation_score * self.weights.valuation_score / 15.0
        )
        
        # 质量等级评定
        quality_grade = self._determine_quality_grade(comprehensive_score)
        
        return {
            'comprehensive_score': round(comprehensive_score, 2),
            'quality_grade': quality_grade,
            'momentum_score': round(momentum_score, 2),
            'liquidity_score': round(liquidity_score, 2),
            'volume_score': round(volume_score, 2),
            'valuation_score': round(valuation_score, 2),
            'details': {
                'momentum': momentum_details,
                'liquidity': liquidity_details,
                'volume': volume_details,
                'valuation': valuation_details
            }
        }
    
    def _calculate_volume_price_synergy(self, volume_ratio: float, price_change: float) -> float:
        """计算量价配合度 (0-1)"""
        if price_change > 0:
            # 上涨时，放量为正面
            if volume_ratio > 1.2:
                return min(1.0, (volume_ratio - 1) / 3)
            else:
                return 0.3  # 上涨缩量，配合度一般
        else:
            # 下跌时，缩量为正面
            if volume_ratio < 1.0:
                return 0.8
            else:
                return max(0.2, 1 - (volume_ratio - 1) / 2)
    
    def _categorize_momentum(self, change_pct: float) -> str:
        """动量分类"""
        if change_pct < 0:
            return "下跌"
        elif change_pct < 2:
            return "温和上涨"
        elif change_pct <= 6:
            return "理想上涨"
        elif change_pct <= 9:
            return "强势上涨"
        else:
            return "过度上涨"
    
    def _categorize_liquidity(self, turnover_rate: float) -> str:
        """流动性分类"""
        if turnover_rate < 1:
            return "低流动性"
        elif turnover_rate <= 3:
            return "适度活跃"
        elif turnover_rate <= 8:
            return "高度活跃"
        elif turnover_rate <= 15:
            return "过度活跃"
        else:
            return "极度投机"
    
    def _categorize_volume(self, volume_ratio: float) -> str:
        """成交量分类"""
        if volume_ratio < 0.8:
            return "明显缩量"
        elif volume_ratio < 1.2:
            return "正常成交"
        elif volume_ratio <= 3:
            return "适度放量"
        elif volume_ratio <= 5:
            return "大幅放量"
        else:
            return "异常放量"
    
    def _categorize_valuation(self, pe_ratio: float) -> str:
        """估值分类"""
        if pe_ratio <= 0:
            return "亏损"
        elif pe_ratio < 10:
            return "超低估值"
        elif pe_ratio <= 20:
            return "合理估值"
        elif pe_ratio <= 35:
            return "适中估值"
        elif pe_ratio <= 60:
            return "高估值"
        else:
            return "极高估值"
    
    def _determine_quality_grade(self, score: float) -> str:
        """确定质量等级"""
        if score >= 95:
            return "S+"
        elif score >= 90:
            return "S"
        elif score >= 85:
            return "A+"
        elif score >= 80:
            return "A"
        elif score >= 75:
            return "B+"
        elif score >= 70:
            return "B"
        elif score >= 60:
            return "C"
        else:
            return "D"


# 预设配置
CONSERVATIVE_WEIGHTS = ScoringWeights(
    momentum_score=25.0,    # 保守型更注重估值
    liquidity_score=25.0,
    volume_score=20.0,
    valuation_score=30.0
)

AGGRESSIVE_WEIGHTS = ScoringWeights(
    momentum_score=45.0,    # 激进型更注重动量
    liquidity_score=25.0,
    volume_score=20.0,
    valuation_score=10.0
)

BALANCED_WEIGHTS = ScoringWeights()  # 默认平衡配置