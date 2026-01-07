"""
情绪周期预判器 - Sentiment Cycle Predictor

解决情绪轮动问题，预判明日情绪周期。

A股情绪周期: 冰点 → 修复 → 升温 → 高潮 → 分歧 → 退潮 → 冰点

核心逻辑:
- 今日高潮 → 明日大概率分歧
- 今日冰点 → 明日大概率修复

Requirements: 9.1-9.5
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
from datetime import datetime


class SentimentPhase(Enum):
    """情绪周期阶段"""
    FREEZING = "冰点"      # 极度恐慌，涨停稀少，跌停遍地
    RECOVERY = "修复"      # 市场开始企稳，情绪逐步修复
    WARMING = "升温"       # 市场活跃度提升，热点开始发酵
    CLIMAX = "高潮"        # 市场极度亢奋，涨停潮，连板股众多
    DIVERGENCE = "分歧"    # 市场出现分歧，龙头分化，炸板增多
    RETREAT = "退潮"       # 市场热度下降，赚钱效应减弱


class SentimentLevel(Enum):
    """情绪等级"""
    EXTREME_FEAR = "极度恐慌"
    FEAR = "恐慌"
    NEUTRAL = "中性"
    GREED = "乐观"
    EXTREME_GREED = "极度乐观"


@dataclass
class SentimentAnalysisResult:
    """今日情绪分析结果"""
    phase: SentimentPhase           # 当前周期阶段
    level: SentimentLevel           # 情绪等级
    score: float                    # 情绪分数 (0-100)
    description: str                # 描述
    
    # 详细指标
    limit_up_count: int = 0         # 涨停家数
    limit_down_count: int = 0       # 跌停家数
    broken_board_rate: float = 0.0  # 炸板率
    continuous_board_count: int = 0 # 连板股数量
    market_profit_rate: float = 0.0 # 市场赚钱效应
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'phase': self.phase.value,
            'level': self.level.value,
            'score': self.score,
            'description': self.description,
            'limit_up_count': self.limit_up_count,
            'limit_down_count': self.limit_down_count,
            'broken_board_rate': self.broken_board_rate,
            'continuous_board_count': self.continuous_board_count,
            'market_profit_rate': self.market_profit_rate,
        }


@dataclass
class TomorrowPrediction:
    """明日情绪预判结果"""
    predicted_phase: str            # 预判明日阶段
    position_multiplier: float      # 仓位调整系数
    strategy_advice: str            # 策略建议
    focus_stocks: str               # 重点关注类型
    confidence: float = 0.7         # 预判置信度 (0-1)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'predicted_phase': self.predicted_phase,
            'position_multiplier': self.position_multiplier,
            'strategy_advice': self.strategy_advice,
            'focus_stocks': self.focus_stocks,
            'confidence': self.confidence,
        }


class SentimentCyclePredictor:
    """
    情绪周期预判器 - 解决情绪轮动问题
    
    A股情绪周期: 冰点 → 修复 → 升温 → 高潮 → 分歧 → 退潮
    
    核心逻辑:
    - 今日高潮 → 明日大概率分歧
    - 今日冰点 → 明日大概率修复
    """
    
    # 情绪周期定义 (按顺序)
    CYCLE_PHASES = [
        SentimentPhase.FREEZING,    # 冰点
        SentimentPhase.RECOVERY,    # 修复
        SentimentPhase.WARMING,     # 升温
        SentimentPhase.CLIMAX,      # 高潮
        SentimentPhase.DIVERGENCE,  # 分歧
        SentimentPhase.RETREAT,     # 退潮
    ]
    
    # 阶段描述
    PHASE_DESCRIPTIONS = {
        SentimentPhase.FREEZING: "市场极度恐慌，涨停稀少，跌停遍地",
        SentimentPhase.RECOVERY: "市场开始企稳，情绪逐步修复",
        SentimentPhase.WARMING: "市场活跃度提升，热点开始发酵",
        SentimentPhase.CLIMAX: "市场极度亢奋，涨停潮，连板股众多",
        SentimentPhase.DIVERGENCE: "市场出现分歧，龙头分化，炸板增多",
        SentimentPhase.RETREAT: "市场热度下降，赚钱效应减弱",
    }
    
    def __init__(self):
        """初始化情绪周期预判器"""
        self.history: List[SentimentAnalysisResult] = []  # 历史情绪记录
        self.last_analysis: Optional[SentimentAnalysisResult] = None
        self.last_prediction: Optional[TomorrowPrediction] = None
    
    def analyze_today_sentiment(
        self,
        limit_up_count: int,
        limit_down_count: int,
        broken_board_rate: float,
        continuous_board_count: int,
        market_profit_rate: float
    ) -> SentimentAnalysisResult:
        """
        分析今日情绪
        
        Args:
            limit_up_count: 涨停家数
            limit_down_count: 跌停家数
            broken_board_rate: 炸板率 (0-1, 如0.2表示20%)
            continuous_board_count: 连板股数量
            market_profit_rate: 市场赚钱效应 (0-1, 上涨股票比例)
        
        Returns:
            SentimentAnalysisResult: 今日情绪分析结果
        """
        # 计算情绪分数
        score = self._calculate_sentiment_score(
            limit_up_count,
            limit_down_count,
            broken_board_rate,
            continuous_board_count,
            market_profit_rate
        )
        
        # 判断周期阶段
        phase = self._determine_phase(score, broken_board_rate, continuous_board_count)
        
        # 判断情绪等级
        level = self._determine_level(score)
        
        # 获取描述
        description = self.PHASE_DESCRIPTIONS.get(phase, "")
        
        result = SentimentAnalysisResult(
            phase=phase,
            level=level,
            score=score,
            description=description,
            limit_up_count=limit_up_count,
            limit_down_count=limit_down_count,
            broken_board_rate=broken_board_rate,
            continuous_board_count=continuous_board_count,
            market_profit_rate=market_profit_rate,
        )
        
        # 保存分析结果
        self.last_analysis = result
        self.history.append(result)
        
        return result
    
    def _calculate_sentiment_score(
        self,
        limit_up_count: int,
        limit_down_count: int,
        broken_board_rate: float,
        continuous_board_count: int,
        market_profit_rate: float
    ) -> float:
        """
        计算情绪分数 (0-100)
        
        评分逻辑 (基础分40分，上下浮动):
        - 涨停家数 (0-20分)
        - 跌停家数 (扣分 0-15分)
        - 炸板率 (0-15分)
        - 连板股 (0-15分)
        - 赚钱效应 (0-15分)
        """
        # 基础分
        score = 40.0
        
        # 1. 涨停家数 (+0-20分)
        if limit_up_count >= 100:
            score += 20
        elif limit_up_count >= 80:
            score += 16
        elif limit_up_count >= 60:
            score += 12
        elif limit_up_count >= 40:
            score += 8
        elif limit_up_count >= 20:
            score += 4
        elif limit_up_count < 10:
            score -= 10  # 涨停太少扣分
        
        # 2. 跌停家数 (扣分 0-15分)
        if limit_down_count >= 50:
            score -= 15
        elif limit_down_count >= 30:
            score -= 10
        elif limit_down_count >= 15:
            score -= 5
        elif limit_down_count <= 5:
            score += 5  # 跌停很少加分
        
        # 3. 炸板率 (+0-15分，炸板率越低越好)
        if broken_board_rate <= 0.1:
            score += 15
        elif broken_board_rate <= 0.15:
            score += 10
        elif broken_board_rate <= 0.2:
            score += 5
        elif broken_board_rate <= 0.3:
            score += 0
        elif broken_board_rate <= 0.4:
            score -= 5
        else:
            score -= 10  # 炸板率>40%扣分
        
        # 4. 连板股 (+0-15分)
        if continuous_board_count >= 10:
            score += 15
        elif continuous_board_count >= 7:
            score += 12
        elif continuous_board_count >= 5:
            score += 8
        elif continuous_board_count >= 3:
            score += 4
        elif continuous_board_count == 0:
            score -= 5  # 无连板扣分
        
        # 5. 赚钱效应 (+0-15分)
        if market_profit_rate >= 0.7:
            score += 15
        elif market_profit_rate >= 0.6:
            score += 10
        elif market_profit_rate >= 0.5:
            score += 5
        elif market_profit_rate >= 0.4:
            score += 0
        elif market_profit_rate < 0.3:
            score -= 10  # 赚钱效应差扣分
        
        # 确保分数在0-100范围内
        return max(0, min(100, score))
    
    def _determine_phase(
        self,
        score: float,
        broken_board_rate: float,
        continuous_board_count: int
    ) -> SentimentPhase:
        """
        判断周期阶段
        
        综合考虑情绪分数、炸板率、连板股数量
        """
        # 高潮: 高分 + 低炸板率 + 多连板
        if score >= 85 and broken_board_rate < 0.2 and continuous_board_count >= 5:
            return SentimentPhase.CLIMAX
        
        # 分歧: 中高分 + 高炸板率 (关键特征是炸板多)
        if score >= 55 and broken_board_rate >= 0.3:
            return SentimentPhase.DIVERGENCE
        
        # 升温: 高分
        if score >= 75:
            return SentimentPhase.WARMING
        
        # 修复: 中等分数
        if score >= 55:
            return SentimentPhase.RECOVERY
        
        # 退潮: 中低分
        if score >= 35:
            return SentimentPhase.RETREAT
        
        # 冰点: 低分
        return SentimentPhase.FREEZING
    
    def _determine_level(self, score: float) -> SentimentLevel:
        """判断情绪等级"""
        if score >= 85:
            return SentimentLevel.EXTREME_GREED
        elif score >= 70:
            return SentimentLevel.GREED
        elif score >= 50:
            return SentimentLevel.NEUTRAL
        elif score >= 30:
            return SentimentLevel.FEAR
        else:
            return SentimentLevel.EXTREME_FEAR

    
    def predict_tomorrow(
        self,
        today_sentiment: Optional[SentimentAnalysisResult] = None
    ) -> TomorrowPrediction:
        """
        预判明日情绪
        
        核心逻辑:
        - 高潮 → 分歧 (仓位×0.5)
        - 冰点 → 修复 (仓位×1.2)
        - 升温 → 高潮或继续升温
        - 分歧 → 退潮或修复
        - 退潮/修复 → 继续调整或企稳
        
        Args:
            today_sentiment: 今日情绪分析结果，如果为None则使用last_analysis
        
        Returns:
            TomorrowPrediction: 明日情绪预判结果
        """
        if today_sentiment is None:
            today_sentiment = self.last_analysis
        
        if today_sentiment is None:
            # 没有今日数据，返回中性预判
            return TomorrowPrediction(
                predicted_phase="未知",
                position_multiplier=1.0,
                strategy_advice="⚠️ 缺少今日情绪数据，建议观望",
                focus_stocks="等待数据更新",
                confidence=0.3,
            )
        
        phase = today_sentiment.phase
        level = today_sentiment.level
        
        # 根据今日阶段预判明日
        if phase == SentimentPhase.CLIMAX:
            # 高潮 → 分歧
            prediction = TomorrowPrediction(
                predicted_phase="分歧",
                position_multiplier=0.5,
                strategy_advice="⚠️ 明日大概率分歧，减半仓位，只做核心龙头",
                focus_stocks="核心龙头(去弱留强)",
                confidence=0.8,
            )
        
        elif phase == SentimentPhase.FREEZING:
            # 冰点 → 修复
            prediction = TomorrowPrediction(
                predicted_phase="修复",
                position_multiplier=1.2,
                strategy_advice="💡 明日可能修复，可适当加仓试错",
                focus_stocks="反包形态、抗跌股",
                confidence=0.75,
            )
        
        elif phase == SentimentPhase.WARMING:
            # 升温 → 高潮或继续升温
            prediction = TomorrowPrediction(
                predicted_phase="高潮或继续升温",
                position_multiplier=1.0,
                strategy_advice="正常操作，跟随热点",
                focus_stocks="热点龙头、补涨股",
                confidence=0.7,
            )
        
        elif phase == SentimentPhase.DIVERGENCE:
            # 分歧 → 退潮或修复
            prediction = TomorrowPrediction(
                predicted_phase="退潮或修复",
                position_multiplier=0.7,
                strategy_advice="观望为主，等待方向明确",
                focus_stocks="穿越分歧的强势股",
                confidence=0.65,
            )
        
        elif phase == SentimentPhase.RETREAT:
            # 退潮 → 继续调整或企稳
            prediction = TomorrowPrediction(
                predicted_phase="继续调整或企稳",
                position_multiplier=0.8,
                strategy_advice="轻仓试错，控制风险",
                focus_stocks="超跌反弹股",
                confidence=0.6,
            )
        
        else:  # RECOVERY
            # 修复 → 升温或继续修复
            prediction = TomorrowPrediction(
                predicted_phase="升温或继续修复",
                position_multiplier=0.9,
                strategy_advice="逐步加仓，关注热点启动",
                focus_stocks="率先企稳的板块龙头",
                confidence=0.65,
            )
        
        # 根据情绪等级微调
        if level == SentimentLevel.EXTREME_GREED:
            # 极度乐观时，预判分歧的置信度更高
            if prediction.predicted_phase != "分歧":
                prediction = TomorrowPrediction(
                    predicted_phase="分歧",
                    position_multiplier=0.5,
                    strategy_advice="⚠️ 极度乐观后大概率分歧，减半仓位",
                    focus_stocks="核心龙头(去弱留强)",
                    confidence=0.85,
                )
        
        elif level == SentimentLevel.EXTREME_FEAR:
            # 极度恐慌时，预判修复的置信度更高
            if prediction.predicted_phase != "修复":
                prediction = TomorrowPrediction(
                    predicted_phase="修复",
                    position_multiplier=1.2,
                    strategy_advice="💡 极度恐慌后可能修复，可适当试错",
                    focus_stocks="反包形态、抗跌股",
                    confidence=0.8,
                )
        
        # 保存预判结果
        self.last_prediction = prediction
        
        return prediction
    
    def get_position_adjustment(
        self,
        base_position: float,
        today_sentiment: Optional[SentimentAnalysisResult] = None
    ) -> Tuple[float, str]:
        """
        获取仓位调整建议
        
        Args:
            base_position: 基础仓位比例 (0-1)
            today_sentiment: 今日情绪分析结果
        
        Returns:
            (调整后仓位, 调整说明)
        """
        prediction = self.predict_tomorrow(today_sentiment)
        
        adjusted_position = base_position * prediction.position_multiplier
        
        # 确保仓位在合理范围内
        adjusted_position = max(0, min(0.8, adjusted_position))
        
        if prediction.position_multiplier < 1.0:
            reason = f"明日预判{prediction.predicted_phase}，仓位下调至{prediction.position_multiplier:.0%}"
        elif prediction.position_multiplier > 1.0:
            reason = f"明日预判{prediction.predicted_phase}，仓位上调至{prediction.position_multiplier:.0%}"
        else:
            reason = f"明日预判{prediction.predicted_phase}，仓位保持不变"
        
        return adjusted_position, reason
    
    def get_cycle_position(self, phase: SentimentPhase) -> int:
        """
        获取阶段在周期中的位置
        
        Returns:
            位置索引 (0-5)
        """
        try:
            return self.CYCLE_PHASES.index(phase)
        except ValueError:
            return -1
    
    def get_next_phase(self, current_phase: SentimentPhase) -> SentimentPhase:
        """
        获取下一个周期阶段
        
        Returns:
            下一个阶段
        """
        current_idx = self.get_cycle_position(current_phase)
        if current_idx == -1:
            return SentimentPhase.NEUTRAL if hasattr(SentimentPhase, 'NEUTRAL') else SentimentPhase.RECOVERY
        
        next_idx = (current_idx + 1) % len(self.CYCLE_PHASES)
        return self.CYCLE_PHASES[next_idx]
    
    def generate_sentiment_report(
        self,
        today_sentiment: Optional[SentimentAnalysisResult] = None
    ) -> str:
        """
        生成情绪分析报告
        
        Args:
            today_sentiment: 今日情绪分析结果
        
        Returns:
            Markdown格式的报告
        """
        if today_sentiment is None:
            today_sentiment = self.last_analysis
        
        if today_sentiment is None:
            return "⚠️ 暂无情绪数据"
        
        prediction = self.predict_tomorrow(today_sentiment)
        
        # 情绪图标
        phase_icons = {
            SentimentPhase.FREEZING: "🥶",
            SentimentPhase.RECOVERY: "🌱",
            SentimentPhase.WARMING: "☀️",
            SentimentPhase.CLIMAX: "🔥",
            SentimentPhase.DIVERGENCE: "⚡",
            SentimentPhase.RETREAT: "🌧️",
        }
        
        icon = phase_icons.get(today_sentiment.phase, "📊")
        
        report = f"""
## {icon} 情绪周期分析

### 今日情绪
- **周期阶段**: {today_sentiment.phase.value}
- **情绪等级**: {today_sentiment.level.value}
- **情绪分数**: {today_sentiment.score:.0f}/100
- **描述**: {today_sentiment.description}

### 市场数据
| 指标 | 数值 |
|------|------|
| 涨停家数 | {today_sentiment.limit_up_count} |
| 跌停家数 | {today_sentiment.limit_down_count} |
| 炸板率 | {today_sentiment.broken_board_rate*100:.1f}% |
| 连板股数 | {today_sentiment.continuous_board_count} |
| 赚钱效应 | {today_sentiment.market_profit_rate*100:.1f}% |

### 明日预判
- **预判阶段**: {prediction.predicted_phase}
- **仓位系数**: {prediction.position_multiplier:.1f}x
- **置信度**: {prediction.confidence*100:.0f}%
- **策略建议**: {prediction.strategy_advice}
- **关注方向**: {prediction.focus_stocks}
"""
        return report
    
    def clear_history(self):
        """清空历史记录"""
        self.history.clear()
        self.last_analysis = None
        self.last_prediction = None


# 便捷函数
def create_sentiment_predictor() -> SentimentCyclePredictor:
    """创建情绪周期预判器"""
    return SentimentCyclePredictor()


def quick_sentiment_prediction(
    limit_up_count: int,
    limit_down_count: int,
    broken_board_rate: float,
    continuous_board_count: int,
    market_profit_rate: float
) -> Dict:
    """
    快速情绪预判
    
    Args:
        limit_up_count: 涨停家数
        limit_down_count: 跌停家数
        broken_board_rate: 炸板率 (0-1)
        continuous_board_count: 连板股数量
        market_profit_rate: 市场赚钱效应 (0-1)
    
    Returns:
        包含今日分析和明日预判的字典
    """
    predictor = SentimentCyclePredictor()
    
    today = predictor.analyze_today_sentiment(
        limit_up_count=limit_up_count,
        limit_down_count=limit_down_count,
        broken_board_rate=broken_board_rate,
        continuous_board_count=continuous_board_count,
        market_profit_rate=market_profit_rate,
    )
    
    tomorrow = predictor.predict_tomorrow(today)
    
    return {
        'today': today.to_dict(),
        'tomorrow': tomorrow.to_dict(),
        'report': predictor.generate_sentiment_report(today),
    }
