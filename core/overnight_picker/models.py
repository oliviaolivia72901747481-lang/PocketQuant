"""
隔夜选股系统数据模型

定义核心数据结构：StockRecommendation 和 TradingPlan
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime


@dataclass
class StockRecommendation:
    """
    股票推荐结果
    
    包含股票的评分、买入计划、仓位建议、止损止盈等完整信息
    """
    # 基本信息
    code: str                           # 股票代码
    name: str                           # 股票名称
    sector: str                         # 所属板块
    today_close: float                  # 今日收盘价
    today_change: float                 # 今日涨跌幅 (百分比，如 3.2 表示 +3.2%)
    
    # 评分
    total_score: float                  # 明日潜力总分 (0-100)
    score_details: Dict[str, float] = field(default_factory=dict)  # 各维度评分详情
    
    # 买入计划
    ideal_price: float = 0.0            # 理想买入价 (低开时买入)
    acceptable_price: float = 0.0       # 可接受买入价 (平开时买入)
    abandon_price: float = 0.0          # 放弃买入价 (高开超此价不买)
    
    # 仓位
    position_ratio: float = 0.0         # 建议仓位比例 (0-0.3)
    position_amount: float = 0.0        # 建议买入金额
    shares: int = 0                     # 建议买入股数 (100的整数倍)
    
    # 止损止盈
    stop_loss_price: float = 0.0        # 止损价
    first_target: float = 0.0           # 第一止盈价 (+5%)
    second_target: float = 0.0          # 第二止盈价 (+10%)
    max_loss: float = 0.0               # 最大亏损金额
    expected_profit: float = 0.0        # 预期盈利金额
    
    # 其他
    hot_topics: List[str] = field(default_factory=list)  # 相关热点
    leader_type: str = ""               # 龙头类型 (真龙头/二线龙头/跟风股/蹭热点)
    risk_level: str = "MEDIUM"          # 风险等级 (LOW/MEDIUM/HIGH/EXTREME)
    reasoning: str = ""                 # 推荐理由
    strategy_type: str = "low_buy"      # 策略类型 (low_buy/breakout)


    def __post_init__(self):
        """验证数据有效性"""
        # 确保股数为100的整数倍
        if self.shares > 0 and self.shares % 100 != 0:
            self.shares = (self.shares // 100) * 100
        
        # 确保评分在有效范围内
        self.total_score = max(0, min(100, self.total_score))
        
        # 确保仓位比例在有效范围内
        self.position_ratio = max(0, min(0.3, self.position_ratio))
    
    def is_valid(self) -> bool:
        """检查推荐是否有效"""
        return (
            self.total_score >= 70 and
            self.shares > 0 and
            self.shares % 100 == 0 and
            self.ideal_price < self.acceptable_price < self.abandon_price and
            self.stop_loss_price < self.ideal_price < self.first_target < self.second_target
        )
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            'code': self.code,
            'name': self.name,
            'sector': self.sector,
            'today_close': self.today_close,
            'today_change': self.today_change,
            'total_score': self.total_score,
            'score_details': self.score_details,
            'ideal_price': self.ideal_price,
            'acceptable_price': self.acceptable_price,
            'abandon_price': self.abandon_price,
            'position_ratio': self.position_ratio,
            'position_amount': self.position_amount,
            'shares': self.shares,
            'stop_loss_price': self.stop_loss_price,
            'first_target': self.first_target,
            'second_target': self.second_target,
            'max_loss': self.max_loss,
            'expected_profit': self.expected_profit,
            'hot_topics': self.hot_topics,
            'leader_type': self.leader_type,
            'risk_level': self.risk_level,
            'reasoning': self.reasoning,
            'strategy_type': self.strategy_type,
        }


@dataclass
class TradingPlan:
    """
    明日交易计划
    
    包含市场环境、推荐股票列表、操作建议等完整交易计划
    """
    date: str                           # 计划日期 (YYYY-MM-DD)
    generated_at: str                   # 生成时间 (YYYY-MM-DD HH:MM:SS)
    
    # 市场环境
    market_env: str = "震荡"            # 大盘环境 (强势/震荡/弱势)
    market_sentiment: str = "中性"      # 市场情绪 (乐观/中性/恐慌)
    sentiment_phase: str = ""           # 情绪周期阶段 (冰点/修复/升温/高潮/分歧/退潮)
    hot_topics: List[str] = field(default_factory=list)  # 当前热点
    
    # 推荐股票
    recommendations: List[StockRecommendation] = field(default_factory=list)
    
    # 操作建议
    total_position: float = 0.0         # 建议总仓位比例
    operation_tips: List[str] = field(default_factory=list)  # 操作要点
    risk_warnings: List[str] = field(default_factory=list)   # 风险提示
    
    # 预判信息
    tomorrow_prediction: str = ""       # 明日预判
    position_multiplier: float = 1.0    # 仓位调整系数
    
    def __post_init__(self):
        """验证数据有效性"""
        # 确保推荐列表不超过5只
        if len(self.recommendations) > 5:
            self.recommendations = self.recommendations[:5]
        
        # 确保总仓位不超过80%
        self.total_position = max(0, min(0.8, self.total_position))
    
    def get_total_investment(self) -> float:
        """获取总投资金额"""
        return sum(r.position_amount for r in self.recommendations)
    
    def get_max_total_loss(self) -> float:
        """获取最大总亏损"""
        return sum(r.max_loss for r in self.recommendations)
    
    def get_expected_total_profit(self) -> float:
        """获取预期总盈利"""
        return sum(r.expected_profit for r in self.recommendations)
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            'date': self.date,
            'generated_at': self.generated_at,
            'market_env': self.market_env,
            'market_sentiment': self.market_sentiment,
            'sentiment_phase': self.sentiment_phase,
            'hot_topics': self.hot_topics,
            'recommendations': [r.to_dict() for r in self.recommendations],
            'total_position': self.total_position,
            'operation_tips': self.operation_tips,
            'risk_warnings': self.risk_warnings,
            'tomorrow_prediction': self.tomorrow_prediction,
            'position_multiplier': self.position_multiplier,
        }
    
    def to_markdown(self) -> str:
        """生成Markdown格式的交易计划"""
        lines = []
        lines.append(f"# 📈 明日交易计划 ({self.date})")
        lines.append("")
        lines.append(f"生成时间: {self.generated_at}")
        lines.append("")
        
        # 市场环境
        lines.append("## 📊 市场环境")
        lines.append("")
        lines.append("| 指标 | 状态 | 说明 |")
        lines.append("|------|------|------|")
        
        env_icon = "🟢" if self.market_env == "强势" else ("🟡" if self.market_env == "震荡" else "🔴")
        lines.append(f"| 大盘环境 | {env_icon} {self.market_env} | - |")
        
        sentiment_icon = "🟢" if self.market_sentiment == "乐观" else ("🟡" if self.market_sentiment == "中性" else "🔴")
        lines.append(f"| 市场情绪 | {sentiment_icon} {self.market_sentiment} | {self.sentiment_phase} |")
        
        if self.hot_topics:
            lines.append(f"| 当前热点 | {', '.join(self.hot_topics[:3])} | - |")
        lines.append("")
        
        # 推荐股票
        if self.recommendations:
            lines.append(f"## ⭐ 推荐买入 (共{len(self.recommendations)}只)")
            lines.append("")
            
            for i, rec in enumerate(self.recommendations, 1):
                stars = "⭐" * min(3, int(rec.total_score / 30) + 1)
                lines.append(f"### {i}. {rec.name} ({rec.code}) - 评分: {rec.total_score:.0f}分 {stars}")
                lines.append("")
                lines.append("| 项目 | 数值 | 说明 |")
                lines.append("|------|------|------|")
                lines.append(f"| 今日收盘 | {rec.today_close:.2f}元 | 涨幅 {rec.today_change:+.1f}% |")
                lines.append(f"| 所属板块 | {rec.sector} | - |")
                lines.append(f"| 龙头类型 | {rec.leader_type or '-'} | - |")
                lines.append("")
                
                # 买入计划
                lines.append("**买入计划:**")
                lines.append("| 价格类型 | 价格 | 操作 |")
                lines.append("|----------|------|------|")
                lines.append(f"| 理想买入价 | {rec.ideal_price:.2f}元 | 低开时买入 |")
                lines.append(f"| 可接受买入价 | {rec.acceptable_price:.2f}元 | 平开时可买 |")
                lines.append(f"| 放弃买入价 | {rec.abandon_price:.2f}元 | 高开超此价不追 |")
                lines.append("")
                
                # 仓位建议
                lines.append("**仓位建议:**")
                lines.append(f"- 建议仓位: {rec.position_ratio*100:.0f}% = {rec.position_amount:.0f}元")
                lines.append(f"- 买入股数: {rec.shares}股")
                lines.append(f"- 止损价: {rec.stop_loss_price:.2f}元")
                lines.append(f"- 第一止盈: {rec.first_target:.2f}元 (+5%)")
                lines.append(f"- 第二止盈: {rec.second_target:.2f}元 (+10%)")
                lines.append(f"- 最大亏损: {rec.max_loss:.0f}元")
                lines.append(f"- 预期盈利: {rec.expected_profit:.0f}元")
                lines.append("")
                
                if rec.reasoning:
                    lines.append(f"**推荐理由:** {rec.reasoning}")
                    lines.append("")
                
                lines.append("---")
                lines.append("")
        else:
            lines.append("## ⚠️ 今日无推荐")
            lines.append("")
            lines.append("当前市场环境不适合操作，建议观望。")
            lines.append("")
        
        # 操作要点
        if self.operation_tips:
            lines.append("## 💡 明日操作要点")
            lines.append("")
            for i, tip in enumerate(self.operation_tips, 1):
                lines.append(f"{i}. {tip}")
            lines.append("")
        
        # 风险提示
        if self.risk_warnings:
            lines.append("## ⚠️ 风险提示")
            lines.append("")
            for i, warning in enumerate(self.risk_warnings, 1):
                lines.append(f"{i}. {warning}")
            lines.append("")
        
        return "\n".join(lines)
