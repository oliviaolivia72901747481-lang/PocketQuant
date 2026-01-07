"""
竞价过滤器 (CallAuctionFilter)

解决竞价逻辑缺失问题:
1. 核按钮过滤 - 低开>4%取消买入
2. 抢筹确认 - 龙头高开爆量允许追入
3. 策略类型区分 - 低吸型vs突破型

Requirements: 8.1-8.5
"""

from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum


class AuctionAction(Enum):
    """竞价分析结果动作"""
    BUY = "BUY"           # 执行买入
    CANCEL = "CANCEL"     # 取消买入
    WAIT = "WAIT"         # 等待观察


class RiskLevel(Enum):
    """风险等级"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    EXTREME = "EXTREME"


class StrategyType(Enum):
    """策略类型"""
    LOW_BUY = "low_buy"       # 低吸型 - 适合回调买入
    BREAKOUT = "breakout"     # 突破型 - 适合追涨买入


@dataclass
class AuctionResult:
    """竞价分析结果"""
    action: AuctionAction
    reason: str
    adjusted_price: Optional[float]
    risk_level: RiskLevel
    open_change: float = 0.0
    volume_ratio: float = 0.0
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            'action': self.action.value,
            'reason': self.reason,
            'adjusted_price': self.adjusted_price,
            'risk_level': self.risk_level.value,
            'open_change': self.open_change,
            'volume_ratio': self.volume_ratio,
        }


class CallAuctionFilter:
    """
    竞价过滤器 - 解决竞价逻辑缺失问题
    
    核心功能:
    1. 核按钮过滤 - 低开>4%取消买入 (Requirements 8.1)
    2. 抢筹确认 - 龙头高开爆量允许追入 (Requirements 8.2)
    3. 策略类型区分 - 低吸型vs突破型 (Requirements 8.3-8.5)
    
    使用场景:
    - 09:25 竞价结束后运行
    - 根据竞价情况决定是否执行买入计划
    """
    
    def __init__(self,
                 nuclear_threshold: float = -0.04,
                 chase_threshold: float = 0.03,
                 volume_ratio_threshold: float = 5.0):
        """
        初始化竞价过滤器
        
        Args:
            nuclear_threshold: 核按钮阈值，低开超过此比例取消买入 (默认-4%)
            chase_threshold: 抢筹阈值，高开超过此比例需要确认 (默认+3%)
            volume_ratio_threshold: 竞价量比阈值，用于确认抢筹 (默认5)
        """
        self.nuclear_threshold = nuclear_threshold      # 核按钮阈值: -4%
        self.chase_threshold = chase_threshold          # 抢筹阈值: +3%
        self.volume_ratio_threshold = volume_ratio_threshold  # 竞价量比阈值: 5
        
        # 低吸型策略的放弃阈值
        self.low_buy_abandon_threshold = 0.03  # 低吸型高开3%以上放弃
        
        # 突破型策略的最低量比要求
        self.breakout_min_volume_ratio = 3.0   # 突破型最低量比要求
    
    def analyze_auction(self,
                       stock_code: str,
                       prev_close: float,
                       auction_price: float,
                       auction_volume: float,
                       avg_volume: float,
                       leader_index: float = 0,
                       strategy_type: str = "low_buy") -> AuctionResult:
        """
        分析竞价情况，决定是否执行买入
        
        核心逻辑:
        1. 核按钮检测: 低开>4% → CANCEL
        2. 抢筹确认: 龙头高开>3% + 量比>5 → BUY (允许追入)
        3. 策略类型判断: 低吸型严格遵守放弃价，突破型允许放宽但要求量比
        
        Args:
            stock_code: 股票代码
            prev_close: 昨日收盘价
            auction_price: 竞价价格(09:25确定)
            auction_volume: 竞价成交量
            avg_volume: 平均成交量(用于计算量比)
            leader_index: 龙头指数(0-100)
            strategy_type: 策略类型 "low_buy"(低吸) / "breakout"(突破)
        
        Returns:
            AuctionResult: 竞价分析结果
        """
        # 计算开盘涨跌幅
        if prev_close <= 0:
            return AuctionResult(
                action=AuctionAction.CANCEL,
                reason="昨日收盘价无效",
                adjusted_price=None,
                risk_level=RiskLevel.EXTREME
            )
        
        open_change = (auction_price - prev_close) / prev_close
        
        # 计算竞价量比 (竞价5分钟量比)
        # 假设竞价时间约5分钟，日均成交量按240分钟计算
        if avg_volume > 0:
            volume_ratio = auction_volume / (avg_volume / 240 * 5)
        else:
            volume_ratio = 1.0
        
        # 1. 核按钮检测 - 低开>4% (Requirements 8.1)
        if open_change < self.nuclear_threshold:
            return AuctionResult(
                action=AuctionAction.CANCEL,
                reason=f'⚠️ 核按钮警报! 低开{open_change*100:.1f}%，取消买入',
                adjusted_price=None,
                risk_level=RiskLevel.EXTREME,
                open_change=open_change,
                volume_ratio=volume_ratio
            )
        
        # 2. 抢筹确认 - 龙头高开爆量 (Requirements 8.2)
        if (open_change > self.chase_threshold and 
            volume_ratio > self.volume_ratio_threshold and
            leader_index > 70):
            return AuctionResult(
                action=AuctionAction.BUY,
                reason=f'🔥 抢筹确认! 龙头高开{open_change*100:.1f}%，量比{volume_ratio:.1f}，确认买入',
                adjusted_price=round(auction_price * 1.01, 2),  # 允许高1%买入
                risk_level=RiskLevel.HIGH,
                open_change=open_change,
                volume_ratio=volume_ratio
            )
        
        # 3. 策略类型判断 (Requirements 8.3-8.5)
        if strategy_type == StrategyType.LOW_BUY.value or strategy_type == "low_buy":
            # 低吸型: 严格遵守放弃价 (Requirements 8.4)
            if open_change > self.low_buy_abandon_threshold:
                return AuctionResult(
                    action=AuctionAction.CANCEL,
                    reason=f'低吸策略: 高开{open_change*100:.1f}%超过3%，放弃买入',
                    adjusted_price=None,
                    risk_level=RiskLevel.MEDIUM,
                    open_change=open_change,
                    volume_ratio=volume_ratio
                )
        elif strategy_type == StrategyType.BREAKOUT.value or strategy_type == "breakout":
            # 突破型: 允许放宽，但要求量比 (Requirements 8.5)
            if open_change > self.low_buy_abandon_threshold and volume_ratio < self.breakout_min_volume_ratio:
                return AuctionResult(
                    action=AuctionAction.CANCEL,
                    reason=f'突破策略: 高开{open_change*100:.1f}%但量比{volume_ratio:.1f}不足，放弃',
                    adjusted_price=None,
                    risk_level=RiskLevel.MEDIUM,
                    open_change=open_change,
                    volume_ratio=volume_ratio
                )
        
        # 4. 正常情况 - 可以执行买入
        return AuctionResult(
            action=AuctionAction.BUY,
            reason=f'竞价正常，开盘价{auction_price:.2f}，可执行买入',
            adjusted_price=round(auction_price, 2),
            risk_level=RiskLevel.LOW,
            open_change=open_change,
            volume_ratio=volume_ratio
        )
    
    def determine_strategy_type(self,
                                leader_index: float,
                                ma_position: str,
                                pattern: str) -> StrategyType:
        """
        确定策略类型
        
        根据龙头指数、均线位置和技术形态判断应该使用低吸型还是突破型策略
        
        Args:
            leader_index: 龙头指数 (0-100)
            ma_position: 均线位置 ('多头排列'/'空头排列'/'均线粘合'等)
            pattern: 技术形态 ('突破前高'/'放量阳线'/'底部放量'等)
        
        Returns:
            StrategyType: 策略类型
            - BREAKOUT: 龙头股 + 多头排列 + 突破形态 → 突破型
            - LOW_BUY: 其他情况 → 低吸型
        """
        # 突破型条件: 龙头指数>60 + 多头排列 + 突破形态
        breakout_patterns = ['突破前高', '放量阳线', '大阳线', '突破形态']
        bullish_ma_positions = ['多头排列', '均线粘合']
        
        is_leader = leader_index > 60
        is_bullish_ma = ma_position in bullish_ma_positions
        is_breakout_pattern = pattern in breakout_patterns
        
        if is_leader and is_bullish_ma and is_breakout_pattern:
            return StrategyType.BREAKOUT
        
        # 其他情况 → 低吸型
        return StrategyType.LOW_BUY
    
    def generate_auction_report(self,
                               results: list) -> str:
        """
        生成竞价修正报告
        
        在09:25竞价结束后输出"竞价修正建议" (Requirements 8.6)
        
        Args:
            results: 竞价分析结果列表 [(stock_code, AuctionResult), ...]
        
        Returns:
            str: Markdown格式的竞价修正报告
        """
        lines = []
        lines.append("# 📊 竞价修正报告")
        lines.append("")
        lines.append("生成时间: 09:25 竞价结束")
        lines.append("")
        
        # 统计
        buy_count = sum(1 for _, r in results if r.action == AuctionAction.BUY)
        cancel_count = sum(1 for _, r in results if r.action == AuctionAction.CANCEL)
        wait_count = sum(1 for _, r in results if r.action == AuctionAction.WAIT)
        
        lines.append("## 📈 汇总")
        lines.append("")
        lines.append(f"- ✅ 可执行买入: {buy_count}只")
        lines.append(f"- ❌ 取消买入: {cancel_count}只")
        lines.append(f"- ⏳ 等待观察: {wait_count}只")
        lines.append("")
        
        # 详细结果
        if results:
            lines.append("## 📋 详细分析")
            lines.append("")
            lines.append("| 股票代码 | 动作 | 开盘涨跌 | 量比 | 风险 | 说明 |")
            lines.append("|----------|------|----------|------|------|------|")
            
            for stock_code, result in results:
                action_icon = {
                    AuctionAction.BUY: "✅",
                    AuctionAction.CANCEL: "❌",
                    AuctionAction.WAIT: "⏳"
                }.get(result.action, "")
                
                risk_icon = {
                    RiskLevel.LOW: "🟢",
                    RiskLevel.MEDIUM: "🟡",
                    RiskLevel.HIGH: "🟠",
                    RiskLevel.EXTREME: "🔴"
                }.get(result.risk_level, "")
                
                lines.append(
                    f"| {stock_code} | {action_icon} {result.action.value} | "
                    f"{result.open_change*100:+.1f}% | {result.volume_ratio:.1f} | "
                    f"{risk_icon} | {result.reason[:30]}... |"
                )
            
            lines.append("")
        
        # 核按钮警告
        nuclear_stocks = [(code, r) for code, r in results 
                         if r.action == AuctionAction.CANCEL and r.risk_level == RiskLevel.EXTREME]
        if nuclear_stocks:
            lines.append("## ⚠️ 核按钮警报")
            lines.append("")
            for code, result in nuclear_stocks:
                lines.append(f"- **{code}**: {result.reason}")
            lines.append("")
        
        # 抢筹确认
        chase_stocks = [(code, r) for code, r in results 
                       if r.action == AuctionAction.BUY and r.risk_level == RiskLevel.HIGH]
        if chase_stocks:
            lines.append("## 🔥 抢筹确认")
            lines.append("")
            for code, result in chase_stocks:
                lines.append(f"- **{code}**: {result.reason}")
                if result.adjusted_price:
                    lines.append(f"  - 调整后买入价: {result.adjusted_price:.2f}")
            lines.append("")
        
        return "\n".join(lines)
    
    def batch_analyze(self,
                     stocks: list) -> list:
        """
        批量分析多只股票的竞价情况
        
        Args:
            stocks: 股票列表，每个元素为字典:
                {
                    'code': str,
                    'prev_close': float,
                    'auction_price': float,
                    'auction_volume': float,
                    'avg_volume': float,
                    'leader_index': float,
                    'strategy_type': str
                }
        
        Returns:
            list: [(stock_code, AuctionResult), ...]
        """
        results = []
        
        for stock in stocks:
            result = self.analyze_auction(
                stock_code=stock.get('code', ''),
                prev_close=stock.get('prev_close', 0),
                auction_price=stock.get('auction_price', 0),
                auction_volume=stock.get('auction_volume', 0),
                avg_volume=stock.get('avg_volume', 0),
                leader_index=stock.get('leader_index', 0),
                strategy_type=stock.get('strategy_type', 'low_buy')
            )
            results.append((stock.get('code', ''), result))
        
        return results
    
    def is_nuclear_button(self, open_change: float) -> bool:
        """
        判断是否触发核按钮
        
        Args:
            open_change: 开盘涨跌幅
        
        Returns:
            bool: 是否触发核按钮 (低开>4%)
        """
        return open_change < self.nuclear_threshold
    
    def is_chase_confirmed(self,
                          open_change: float,
                          volume_ratio: float,
                          leader_index: float) -> bool:
        """
        判断是否确认抢筹
        
        Args:
            open_change: 开盘涨跌幅
            volume_ratio: 竞价量比
            leader_index: 龙头指数
        
        Returns:
            bool: 是否确认抢筹 (龙头高开>3% + 量比>5)
        """
        return (open_change > self.chase_threshold and 
                volume_ratio > self.volume_ratio_threshold and
                leader_index > 70)
