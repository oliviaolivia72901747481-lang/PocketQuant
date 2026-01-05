"""
市场表现筛选模块

提供股票市场表现的评估和筛选功能，包括：
- 流动性评估（市值、成交额、换手率）
- 价格稳定性分析（波动率、最大回撤）
- 市场表现评分

Requirements: 3.3, 6.2, 6.3
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class LiquidityLevel(Enum):
    """流动性等级"""
    EXCELLENT = "excellent"    # 优秀
    GOOD = "good"              # 良好
    ACCEPTABLE = "acceptable"  # 可接受
    POOR = "poor"              # 较差
    ILLIQUID = "illiquid"      # 流动性不足


class VolatilityLevel(Enum):
    """波动性等级"""
    LOW = "low"                # 低波动
    MODERATE = "moderate"      # 中等波动
    HIGH = "high"              # 高波动
    EXTREME = "extreme"        # 极端波动


@dataclass
class MarketIndicators:
    """市场表现指标"""
    code: str
    name: str
    
    # 市值指标
    total_market_cap: Optional[float] = None      # 总市值（亿元）
    float_market_cap: Optional[float] = None      # 流通市值（亿元）
    
    # 流动性指标
    daily_turnover: Optional[float] = None        # 日均成交额（亿元）
    turnover_rate: Optional[float] = None         # 换手率 (%)
    volume_ratio: Optional[float] = None          # 量比
    trading_days_ratio: Optional[float] = None    # 年交易天数比例 (%)
    
    # 价格稳定性指标
    volatility_annual: Optional[float] = None     # 年化波动率 (%)
    max_drawdown: Optional[float] = None          # 最大回撤 (%)
    limit_up_down_freq: Optional[float] = None    # 涨跌停频率 (%)
    price_amplitude: Optional[float] = None       # 平均振幅 (%)
    
    # 价格表现
    change_1m: Optional[float] = None             # 1个月涨跌幅 (%)
    change_3m: Optional[float] = None             # 3个月涨跌幅 (%)
    change_6m: Optional[float] = None             # 6个月涨跌幅 (%)
    change_1y: Optional[float] = None             # 1年涨跌幅 (%)


@dataclass
class MarketScreeningResult:
    """市场表现筛选结果"""
    code: str
    name: str
    indicators: MarketIndicators
    
    # 各维度得分
    liquidity_score: float = 0.0          # 流动性得分
    stability_score: float = 0.0          # 价格稳定性得分
    market_cap_score: float = 0.0         # 市值得分
    
    # 综合得分
    total_score: float = 0.0
    liquidity_level: LiquidityLevel = LiquidityLevel.POOR
    volatility_level: VolatilityLevel = VolatilityLevel.HIGH
    
    # 筛选状态
    passed: bool = False
    failed_criteria: List[str] = field(default_factory=list)
    risk_warnings: List[str] = field(default_factory=list)


@dataclass
class MarketCriteriaConfig:
    """市场表现筛选标准配置"""
    # 市值标准
    min_total_market_cap: float = 50.0    # 最小总市值（亿元）
    max_total_market_cap: float = 5000.0  # 最大总市值（亿元）
    min_float_market_cap: float = 30.0    # 最小流通市值（亿元）
    
    # 流动性标准
    min_daily_turnover: float = 0.5       # 最小日均成交额（亿元）
    min_turnover_rate: float = 0.5        # 最小换手率 (%)
    max_turnover_rate: float = 15.0       # 最大换手率 (%)
    min_trading_days_ratio: float = 80.0  # 最小年交易天数比例 (%)
    
    # 价格稳定性标准
    max_volatility_annual: float = 60.0   # 最大年化波动率 (%)
    max_max_drawdown: float = 50.0        # 最大回撤限制 (%)
    max_limit_up_down_freq: float = 10.0  # 最大涨跌停频率 (%)


class LiquidityEvaluator:
    """
    流动性评估模块
    
    评估股票的流动性状况
    
    Requirements: 3.3, 6.2
    """
    
    def __init__(self, config: Optional[MarketCriteriaConfig] = None):
        """初始化流动性评估器"""
        self.config = config or MarketCriteriaConfig()
    
    def evaluate(self, indicators: MarketIndicators) -> Tuple[float, LiquidityLevel, List[str]]:
        """
        评估流动性
        
        Args:
            indicators: 市场指标
        
        Returns:
            Tuple[流动性得分, 流动性等级, 风险警告列表]
        """
        scores = []
        weights = []
        warnings = []
        
        # 市值评分 (30%)
        if indicators.total_market_cap is not None:
            if indicators.total_market_cap >= 500:
                cap_score = 100
            elif indicators.total_market_cap >= 200:
                cap_score = 85
            elif indicators.total_market_cap >= 100:
                cap_score = 70
            elif indicators.total_market_cap >= self.config.min_total_market_cap:
                cap_score = 55
            elif indicators.total_market_cap >= 30:
                cap_score = 40
            else:
                cap_score = 20
                warnings.append(f"市值偏小({indicators.total_market_cap:.1f}亿)")
            scores.append(cap_score)
            weights.append(0.30)
        
        # 日均成交额评分 (35%)
        if indicators.daily_turnover is not None:
            if indicators.daily_turnover >= 5:
                turnover_score = 100
            elif indicators.daily_turnover >= 2:
                turnover_score = 85
            elif indicators.daily_turnover >= 1:
                turnover_score = 70
            elif indicators.daily_turnover >= self.config.min_daily_turnover:
                turnover_score = 55
            elif indicators.daily_turnover >= 0.2:
                turnover_score = 35
            else:
                turnover_score = 15
                warnings.append(f"成交额偏低({indicators.daily_turnover:.2f}亿)")
            scores.append(turnover_score)
            weights.append(0.35)
        
        # 换手率评分 (20%)
        if indicators.turnover_rate is not None:
            # 换手率过高或过低都不好
            if 1.0 <= indicators.turnover_rate <= 5.0:
                rate_score = 100
            elif 0.5 <= indicators.turnover_rate <= 8.0:
                rate_score = 80
            elif indicators.turnover_rate >= self.config.min_turnover_rate:
                rate_score = 60
            elif indicators.turnover_rate > self.config.max_turnover_rate:
                rate_score = 40
                warnings.append(f"换手率过高({indicators.turnover_rate:.1f}%)")
            else:
                rate_score = 30
                warnings.append(f"换手率过低({indicators.turnover_rate:.1f}%)")
            scores.append(rate_score)
            weights.append(0.20)
        
        # 交易天数比例评分 (15%)
        if indicators.trading_days_ratio is not None:
            if indicators.trading_days_ratio >= 95:
                days_score = 100
            elif indicators.trading_days_ratio >= 90:
                days_score = 85
            elif indicators.trading_days_ratio >= self.config.min_trading_days_ratio:
                days_score = 70
            elif indicators.trading_days_ratio >= 60:
                days_score = 40
            else:
                days_score = 20
                warnings.append(f"停牌天数过多")
            scores.append(days_score)
            weights.append(0.15)
        
        if not scores:
            return 0.0, LiquidityLevel.ILLIQUID, ["无流动性数据"]
        
        # 计算加权得分
        total_weight = sum(weights)
        normalized_weights = [w / total_weight for w in weights]
        total_score = sum(s * w for s, w in zip(scores, normalized_weights))
        
        # 确定流动性等级
        if total_score >= 85:
            level = LiquidityLevel.EXCELLENT
        elif total_score >= 70:
            level = LiquidityLevel.GOOD
        elif total_score >= 55:
            level = LiquidityLevel.ACCEPTABLE
        elif total_score >= 40:
            level = LiquidityLevel.POOR
        else:
            level = LiquidityLevel.ILLIQUID
        
        return total_score, level, warnings


class StabilityEvaluator:
    """
    价格稳定性评估模块
    
    评估股票的价格稳定性
    
    Requirements: 6.3
    """
    
    def __init__(self, config: Optional[MarketCriteriaConfig] = None):
        """初始化稳定性评估器"""
        self.config = config or MarketCriteriaConfig()
    
    def evaluate(self, indicators: MarketIndicators) -> Tuple[float, VolatilityLevel, List[str]]:
        """
        评估价格稳定性
        
        Args:
            indicators: 市场指标
        
        Returns:
            Tuple[稳定性得分, 波动性等级, 风险警告列表]
        """
        scores = []
        weights = []
        warnings = []
        
        # 年化波动率评分 (40%) - 越低越好
        if indicators.volatility_annual is not None:
            if indicators.volatility_annual <= 25:
                vol_score = 100
            elif indicators.volatility_annual <= 35:
                vol_score = 85
            elif indicators.volatility_annual <= 45:
                vol_score = 70
            elif indicators.volatility_annual <= self.config.max_volatility_annual:
                vol_score = 55
            elif indicators.volatility_annual <= 80:
                vol_score = 35
            else:
                vol_score = 15
                warnings.append(f"波动率过高({indicators.volatility_annual:.1f}%)")
            scores.append(vol_score)
            weights.append(0.40)
        
        # 最大回撤评分 (35%) - 越小越好
        if indicators.max_drawdown is not None:
            if indicators.max_drawdown <= 15:
                dd_score = 100
            elif indicators.max_drawdown <= 25:
                dd_score = 85
            elif indicators.max_drawdown <= 35:
                dd_score = 70
            elif indicators.max_drawdown <= self.config.max_max_drawdown:
                dd_score = 55
            elif indicators.max_drawdown <= 70:
                dd_score = 35
            else:
                dd_score = 15
                warnings.append(f"最大回撤过大({indicators.max_drawdown:.1f}%)")
            scores.append(dd_score)
            weights.append(0.35)
        
        # 涨跌停频率评分 (25%) - 越低越好
        if indicators.limit_up_down_freq is not None:
            if indicators.limit_up_down_freq <= 2:
                limit_score = 100
            elif indicators.limit_up_down_freq <= 5:
                limit_score = 85
            elif indicators.limit_up_down_freq <= self.config.max_limit_up_down_freq:
                limit_score = 70
            elif indicators.limit_up_down_freq <= 20:
                limit_score = 45
            else:
                limit_score = 20
                warnings.append(f"涨跌停频繁({indicators.limit_up_down_freq:.1f}%)")
            scores.append(limit_score)
            weights.append(0.25)
        
        if not scores:
            return 50.0, VolatilityLevel.MODERATE, ["无稳定性数据"]
        
        # 计算加权得分
        total_weight = sum(weights)
        normalized_weights = [w / total_weight for w in weights]
        total_score = sum(s * w for s, w in zip(scores, normalized_weights))
        
        # 确定波动性等级
        if total_score >= 80:
            level = VolatilityLevel.LOW
        elif total_score >= 60:
            level = VolatilityLevel.MODERATE
        elif total_score >= 40:
            level = VolatilityLevel.HIGH
        else:
            level = VolatilityLevel.EXTREME
        
        return total_score, level, warnings


class MarketScreener:
    """
    市场表现筛选器
    
    综合评估股票的市场表现
    
    Requirements: 3.3, 6.2, 6.3
    """
    
    def __init__(
        self, 
        config: Optional[MarketCriteriaConfig] = None,
        weights: Optional[Dict[str, float]] = None
    ):
        """
        初始化市场筛选器
        
        Args:
            config: 市场筛选标准配置
            weights: 各维度权重配置
        """
        self.config = config or MarketCriteriaConfig()
        self.liquidity_evaluator = LiquidityEvaluator(self.config)
        self.stability_evaluator = StabilityEvaluator(self.config)
        
        # 默认权重
        self.weights = weights or {
            'liquidity': 0.50,     # 流动性
            'stability': 0.30,    # 价格稳定性
            'market_cap': 0.20    # 市值
        }
    
    def evaluate_stock(
        self, 
        indicators: MarketIndicators
    ) -> MarketScreeningResult:
        """
        评估单只股票的市场表现
        
        Args:
            indicators: 市场指标
        
        Returns:
            MarketScreeningResult: 筛选结果
        """
        # 评估流动性
        liquidity_score, liquidity_level, liquidity_warnings = \
            self.liquidity_evaluator.evaluate(indicators)
        
        # 评估价格稳定性
        stability_score, volatility_level, stability_warnings = \
            self.stability_evaluator.evaluate(indicators)
        
        # 计算市值得分
        market_cap_score = self._score_market_cap(indicators)
        
        # 计算综合得分
        total_score = (
            liquidity_score * self.weights['liquidity'] +
            stability_score * self.weights['stability'] +
            market_cap_score * self.weights['market_cap']
        )
        
        # 检查是否通过筛选
        passed, failed_criteria = self._check_criteria(indicators)
        
        # 合并风险警告
        risk_warnings = liquidity_warnings + stability_warnings
        
        return MarketScreeningResult(
            code=indicators.code,
            name=indicators.name,
            indicators=indicators,
            liquidity_score=liquidity_score,
            stability_score=stability_score,
            market_cap_score=market_cap_score,
            total_score=total_score,
            liquidity_level=liquidity_level,
            volatility_level=volatility_level,
            passed=passed,
            failed_criteria=failed_criteria,
            risk_warnings=risk_warnings
        )
    
    def _score_market_cap(self, indicators: MarketIndicators) -> float:
        """计算市值得分"""
        if indicators.total_market_cap is None:
            return 50.0
        
        cap = indicators.total_market_cap
        
        # 市值在100-1000亿之间得分最高
        if 100 <= cap <= 1000:
            return 100
        elif 50 <= cap < 100 or 1000 < cap <= 2000:
            return 85
        elif cap >= self.config.min_total_market_cap:
            return 70
        elif cap >= 30:
            return 50
        else:
            return 30
    
    def _check_criteria(
        self, 
        indicators: MarketIndicators
    ) -> Tuple[bool, List[str]]:
        """检查是否满足筛选标准"""
        failed_criteria = []
        
        # 检查市值
        if indicators.total_market_cap is not None:
            if indicators.total_market_cap < self.config.min_total_market_cap:
                failed_criteria.append(
                    f"总市值({indicators.total_market_cap:.1f}亿) < {self.config.min_total_market_cap}亿"
                )
        
        # 检查流动性
        if indicators.daily_turnover is not None:
            if indicators.daily_turnover < self.config.min_daily_turnover:
                failed_criteria.append(
                    f"日均成交额({indicators.daily_turnover:.2f}亿) < {self.config.min_daily_turnover}亿"
                )
        
        if indicators.turnover_rate is not None:
            if indicators.turnover_rate < self.config.min_turnover_rate:
                failed_criteria.append(
                    f"换手率({indicators.turnover_rate:.1f}%) < {self.config.min_turnover_rate}%"
                )
        
        # 检查价格稳定性
        if indicators.volatility_annual is not None:
            if indicators.volatility_annual > self.config.max_volatility_annual:
                failed_criteria.append(
                    f"年化波动率({indicators.volatility_annual:.1f}%) > {self.config.max_volatility_annual}%"
                )
        
        if indicators.max_drawdown is not None:
            if indicators.max_drawdown > self.config.max_max_drawdown:
                failed_criteria.append(
                    f"最大回撤({indicators.max_drawdown:.1f}%) > {self.config.max_max_drawdown}%"
                )
        
        passed = len(failed_criteria) == 0
        return passed, failed_criteria
    
    def screen_stocks(
        self, 
        df: pd.DataFrame,
        min_score: float = 55.0,
        strict_mode: bool = False
    ) -> Tuple[pd.DataFrame, List[MarketScreeningResult]]:
        """
        批量筛选股票
        
        Args:
            df: 股票数据DataFrame
            min_score: 最低综合得分
            strict_mode: 严格模式（必须通过所有标准）
        
        Returns:
            Tuple[筛选后的DataFrame, 筛选结果列表]
        """
        if df is None or df.empty:
            return pd.DataFrame(), []
        
        results: List[MarketScreeningResult] = []
        passed_indices = []
        
        for idx, row in df.iterrows():
            # 构建市场指标
            indicators = self._extract_indicators(row)
            
            # 评估股票
            result = self.evaluate_stock(indicators)
            results.append(result)
            
            # 判断是否通过筛选
            if result.total_score >= min_score:
                if strict_mode and not result.passed:
                    continue
                passed_indices.append(idx)
        
        # 筛选通过的股票
        passed_df = df.loc[passed_indices].copy()
        
        # 添加评分列
        if len(passed_df) > 0:
            score_map = {r.code: r.total_score for r in results if r.code in passed_df['code'].values}
            liquidity_map = {r.code: r.liquidity_level.value for r in results if r.code in passed_df['code'].values}
            
            passed_df['market_score'] = passed_df['code'].map(score_map)
            passed_df['liquidity_level'] = passed_df['code'].map(liquidity_map)
        
        logger.info(f"市场表现筛选: 从 {len(df)} 只股票中筛选出 {len(passed_df)} 只")
        
        return passed_df, results
    
    def _extract_indicators(self, row: pd.Series) -> MarketIndicators:
        """从DataFrame行提取市场指标"""
        return MarketIndicators(
            code=str(row.get('code', '')),
            name=str(row.get('name', '')),
            total_market_cap=self._safe_float(row.get('total_market_cap')),
            float_market_cap=self._safe_float(row.get('float_market_cap')),
            daily_turnover=self._safe_float(row.get('daily_turnover', row.get('turnover'))),
            turnover_rate=self._safe_float(row.get('turnover_rate')),
            volume_ratio=self._safe_float(row.get('volume_ratio')),
            trading_days_ratio=self._safe_float(row.get('trading_days_ratio')),
            volatility_annual=self._safe_float(row.get('volatility_annual', row.get('volatility'))),
            max_drawdown=self._safe_float(row.get('max_drawdown')),
            limit_up_down_freq=self._safe_float(row.get('limit_up_down_freq')),
            price_amplitude=self._safe_float(row.get('price_amplitude', row.get('amplitude'))),
            change_1m=self._safe_float(row.get('change_1m')),
            change_3m=self._safe_float(row.get('change_3m')),
            change_6m=self._safe_float(row.get('change_6m')),
            change_1y=self._safe_float(row.get('change_1y', row.get('change_ytd'))),
        )
    
    def _safe_float(self, value: Any) -> Optional[float]:
        """安全转换为浮点数"""
        if value is None or pd.isna(value):
            return None
        try:
            result = float(value)
            # 处理市值单位转换（如果是元，转换为亿元）
            if result > 1e10:  # 大于100亿，可能是元为单位
                result = result / 1e8
            return result
        except (ValueError, TypeError):
            return None
    
    def get_screening_summary(
        self, 
        results: List[MarketScreeningResult]
    ) -> Dict[str, Any]:
        """
        获取筛选结果摘要
        
        Args:
            results: 筛选结果列表
        
        Returns:
            摘要字典
        """
        if not results:
            return {'total': 0}
        
        passed_count = sum(1 for r in results if r.passed)
        scores = [r.total_score for r in results]
        
        # 按流动性等级统计
        liquidity_counts = {}
        for level in LiquidityLevel:
            liquidity_counts[level.value] = sum(1 for r in results if r.liquidity_level == level)
        
        # 按波动性等级统计
        volatility_counts = {}
        for level in VolatilityLevel:
            volatility_counts[level.value] = sum(1 for r in results if r.volatility_level == level)
        
        return {
            'total': len(results),
            'passed': passed_count,
            'failed': len(results) - passed_count,
            'pass_rate': passed_count / len(results) * 100,
            'avg_score': np.mean(scores),
            'max_score': max(scores),
            'min_score': min(scores),
            'liquidity_distribution': liquidity_counts,
            'volatility_distribution': volatility_counts
        }


# 全局市场筛选器实例
_market_screener: Optional[MarketScreener] = None


def get_market_screener() -> MarketScreener:
    """
    获取市场筛选器实例（单例模式）
    
    Returns:
        MarketScreener: 市场筛选器实例
    """
    global _market_screener
    if _market_screener is None:
        _market_screener = MarketScreener()
    return _market_screener
