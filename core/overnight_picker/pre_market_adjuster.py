"""
早盘修正器 (PreMarketAdjuster) - 解决隔夜消息真空问题

运行时间: 09:00-09:15
数据来源: 美股、A50期指、个股公告

核心功能:
1. 获取隔夜数据 (美股、A50期指、个股公告)
2. 根据隔夜数据调整交易计划
3. 生成早盘修正报告

调整规则:
- A50跌>1%: 下调所有计划股买入限价2%
- A50跌>2%: 取消非核心龙头的买入计划
- 个股有重大利空公告: 取消该股买入计划
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import copy


class AdjustmentType(Enum):
    """调整类型"""
    PRICE_ADJUST = "price_adjust"       # 价格调整
    CANCEL_STOCK = "cancel_stock"       # 取消个股
    POSITION_REDUCE = "position_reduce" # 仓位降低
    NO_CHANGE = "no_change"             # 无需调整


class MarketSeverity(Enum):
    """市场严重程度"""
    NORMAL = "normal"           # 正常
    MILD = "mild"               # 轻度
    SEVERE = "severe"           # 严重
    EXTREME = "extreme"         # 极端


@dataclass
class USMarketData:
    """美股市场数据"""
    sp500_change: float = 0.0       # 标普500涨跌幅
    nasdaq_change: float = 0.0      # 纳斯达克涨跌幅
    dow_change: float = 0.0         # 道琼斯涨跌幅
    
    def get_worst_change(self) -> float:
        """获取最差涨跌幅"""
        return min(self.sp500_change, self.nasdaq_change, self.dow_change)
    
    def get_average_change(self) -> float:
        """获取平均涨跌幅"""
        return (self.sp500_change + self.nasdaq_change + self.dow_change) / 3


@dataclass
class StockAnnouncement:
    """个股公告"""
    code: str                       # 股票代码
    name: str                       # 股票名称
    title: str                      # 公告标题
    announcement_type: str          # 公告类型: positive/negative/neutral
    severity: str = "low"           # 严重程度: low/medium/high
    summary: str = ""               # 公告摘要
    publish_time: str = ""          # 发布时间


@dataclass
class OvernightData:
    """隔夜数据"""
    us_market: USMarketData = field(default_factory=USMarketData)
    a50_change: float = 0.0         # A50期指涨跌幅
    announcements: List[StockAnnouncement] = field(default_factory=list)
    fetch_time: str = ""            # 数据获取时间
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'us_market': {
                'sp500_change': self.us_market.sp500_change,
                'nasdaq_change': self.us_market.nasdaq_change,
                'dow_change': self.us_market.dow_change,
            },
            'a50_change': self.a50_change,
            'announcements': [
                {
                    'code': ann.code,
                    'name': ann.name,
                    'title': ann.title,
                    'type': ann.announcement_type,
                    'severity': ann.severity,
                }
                for ann in self.announcements
            ],
            'fetch_time': self.fetch_time,
        }


@dataclass
class Adjustment:
    """单个调整记录"""
    adjustment_type: AdjustmentType
    target: str                     # 调整目标 (股票代码或"all")
    description: str                # 调整描述
    original_value: Any = None      # 原始值
    adjusted_value: Any = None      # 调整后的值
    reason: str = ""                # 调整原因


@dataclass
class AdjustmentReport:
    """早盘修正报告"""
    report_time: str                # 报告时间
    overnight_data: OvernightData   # 隔夜数据
    adjustments: List[Adjustment] = field(default_factory=list)
    market_severity: MarketSeverity = MarketSeverity.NORMAL
    original_stock_count: int = 0   # 原始推荐股票数
    adjusted_stock_count: int = 0   # 调整后股票数
    summary: str = ""               # 总结
    
    def to_markdown(self) -> str:
        """生成Markdown格式报告"""
        lines = []
        lines.append(f"# 📋 早盘修正报告 ({self.report_time})")
        lines.append("")
        
        # 隔夜市场情况
        lines.append("## 🌍 隔夜市场情况")
        lines.append("")
        lines.append("| 指数 | 涨跌幅 | 状态 |")
        lines.append("|------|--------|------|")
        
        us = self.overnight_data.us_market
        sp_icon = "🟢" if us.sp500_change >= 0 else "🔴"
        nasdaq_icon = "🟢" if us.nasdaq_change >= 0 else "🔴"
        dow_icon = "🟢" if us.dow_change >= 0 else "🔴"
        a50_icon = "🟢" if self.overnight_data.a50_change >= 0 else "🔴"
        
        lines.append(f"| 标普500 | {us.sp500_change*100:+.2f}% | {sp_icon} |")
        lines.append(f"| 纳斯达克 | {us.nasdaq_change*100:+.2f}% | {nasdaq_icon} |")
        lines.append(f"| 道琼斯 | {us.dow_change*100:+.2f}% | {dow_icon} |")
        lines.append(f"| A50期指 | {self.overnight_data.a50_change*100:+.2f}% | {a50_icon} |")
        lines.append("")
        
        # 市场严重程度
        severity_map = {
            MarketSeverity.NORMAL: "🟢 正常",
            MarketSeverity.MILD: "🟡 轻度风险",
            MarketSeverity.SEVERE: "🟠 严重风险",
            MarketSeverity.EXTREME: "🔴 极端风险",
        }
        lines.append(f"**市场风险等级:** {severity_map.get(self.market_severity, '未知')}")
        lines.append("")
        
        # 个股公告
        if self.overnight_data.announcements:
            lines.append("## 📢 重要公告")
            lines.append("")
            for ann in self.overnight_data.announcements:
                type_icon = "🔴" if ann.announcement_type == "negative" else ("🟢" if ann.announcement_type == "positive" else "🟡")
                lines.append(f"- {type_icon} **{ann.name}({ann.code})**: {ann.title}")
            lines.append("")
        
        # 调整内容
        lines.append("## 🔧 调整内容")
        lines.append("")
        
        if self.adjustments:
            for adj in self.adjustments:
                if adj.adjustment_type == AdjustmentType.PRICE_ADJUST:
                    lines.append(f"- 📉 **价格调整**: {adj.description}")
                elif adj.adjustment_type == AdjustmentType.CANCEL_STOCK:
                    lines.append(f"- ❌ **取消买入**: {adj.description}")
                elif adj.adjustment_type == AdjustmentType.POSITION_REDUCE:
                    lines.append(f"- 📊 **仓位调整**: {adj.description}")
                else:
                    lines.append(f"- ℹ️ {adj.description}")
        else:
            lines.append("- ✅ 无需调整，按原计划执行")
        lines.append("")
        
        # 总结
        lines.append("## 📝 总结")
        lines.append("")
        lines.append(f"- 原始推荐: {self.original_stock_count}只")
        lines.append(f"- 调整后: {self.adjusted_stock_count}只")
        if self.summary:
            lines.append(f"- {self.summary}")
        lines.append("")
        
        return "\n".join(lines)


class PreMarketAdjuster:
    """
    早盘修正器 - 解决隔夜消息真空问题
    
    运行时间: 09:00-09:15
    数据来源: 美股、A50期指、个股公告
    
    调整规则:
    - A50跌>1%: 下调所有计划股买入限价2%
    - A50跌>2%: 取消非核心龙头的买入计划
    - 个股有重大利空公告: 取消该股买入计划
    - 美股大跌(纳指跌>2%): 降低总仓位30%
    """
    
    def __init__(self):
        # A50期指阈值
        self.a50_threshold_mild = -0.01     # A50跌1%: 轻度调整
        self.a50_threshold_severe = -0.02   # A50跌2%: 严重调整
        
        # 美股阈值
        self.us_threshold_mild = -0.01      # 美股跌1%: 轻度
        self.us_threshold_severe = -0.02    # 美股跌2%: 严重
        
        # 价格调整比例
        self.price_adjust_ratio = 0.02      # 下调买入价2%
        
        # 仓位调整比例
        self.position_reduce_ratio = 0.70   # 降低到70%
    
    def fetch_overnight_data(self) -> OvernightData:
        """
        获取隔夜数据
        
        实际使用时需要调用外部数据接口获取:
        - 美股三大指数涨跌幅
        - A50期指涨跌幅
        - 个股公告
        
        Returns:
            OvernightData: 隔夜数据对象
        """
        # 这里返回模拟数据，实际使用时需要调用数据接口
        # 可以通过以下方式获取数据:
        # 1. 调用财经API (如东方财富、同花顺等)
        # 2. 爬取财经网站数据
        # 3. 使用第三方数据服务
        
        fetch_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        return OvernightData(
            us_market=USMarketData(
                sp500_change=0.0,
                nasdaq_change=0.0,
                dow_change=0.0,
            ),
            a50_change=0.0,
            announcements=[],
            fetch_time=fetch_time,
        )
    
    def fetch_overnight_data_with_values(self,
                                         sp500_change: float = 0.0,
                                         nasdaq_change: float = 0.0,
                                         dow_change: float = 0.0,
                                         a50_change: float = 0.0,
                                         announcements: List[Dict] = None) -> OvernightData:
        """
        使用指定值创建隔夜数据 (用于测试或手动输入)
        
        Args:
            sp500_change: 标普500涨跌幅 (如 -0.01 表示跌1%)
            nasdaq_change: 纳斯达克涨跌幅
            dow_change: 道琼斯涨跌幅
            a50_change: A50期指涨跌幅
            announcements: 公告列表
        
        Returns:
            OvernightData: 隔夜数据对象
        """
        fetch_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        ann_list = []
        if announcements:
            for ann in announcements:
                ann_list.append(StockAnnouncement(
                    code=ann.get('code', ''),
                    name=ann.get('name', ''),
                    title=ann.get('title', ''),
                    announcement_type=ann.get('type', 'neutral'),
                    severity=ann.get('severity', 'low'),
                    summary=ann.get('summary', ''),
                    publish_time=ann.get('publish_time', ''),
                ))
        
        return OvernightData(
            us_market=USMarketData(
                sp500_change=sp500_change,
                nasdaq_change=nasdaq_change,
                dow_change=dow_change,
            ),
            a50_change=a50_change,
            announcements=ann_list,
            fetch_time=fetch_time,
        )
    
    def _assess_market_severity(self, overnight_data: OvernightData) -> MarketSeverity:
        """
        评估市场严重程度
        
        Args:
            overnight_data: 隔夜数据
        
        Returns:
            MarketSeverity: 市场严重程度
        """
        a50 = overnight_data.a50_change
        us_worst = overnight_data.us_market.get_worst_change()
        
        # 极端情况: A50跌>3% 或 美股跌>3%
        if a50 < -0.03 or us_worst < -0.03:
            return MarketSeverity.EXTREME
        
        # 严重情况: A50跌>2% 或 美股跌>2%
        if a50 < self.a50_threshold_severe or us_worst < self.us_threshold_severe:
            return MarketSeverity.SEVERE
        
        # 轻度情况: A50跌>1% 或 美股跌>1%
        if a50 < self.a50_threshold_mild or us_worst < self.us_threshold_mild:
            return MarketSeverity.MILD
        
        return MarketSeverity.NORMAL

    def adjust_trading_plan(self,
                           original_plan: Dict,
                           overnight_data: OvernightData) -> Dict:
        """
        根据隔夜数据调整交易计划
        
        调整规则:
        1. A50跌>1%: 下调所有计划股买入限价2%
        2. A50跌>2%: 取消非核心龙头的买入计划，并下调买入价2%
        3. 个股有重大利空公告: 取消该股买入计划
        4. 美股大跌(纳指跌>2%): 降低总仓位30%
        
        Args:
            original_plan: 原始交易计划 (Dict格式)
            overnight_data: 隔夜数据
        
        Returns:
            调整后的交易计划 (Dict格式)
        """
        # 深拷贝原始计划
        adjusted_plan = copy.deepcopy(original_plan)
        adjustments = []
        
        a50_change = overnight_data.a50_change
        nasdaq_change = overnight_data.us_market.nasdaq_change
        
        # 获取推荐列表
        recommendations = adjusted_plan.get('recommendations', [])
        original_count = len(recommendations)
        
        # 1. A50期指调整
        if a50_change < self.a50_threshold_severe:
            # A50跌超2%: 取消非核心龙头 + 下调买入价
            adjustments.append(Adjustment(
                adjustment_type=AdjustmentType.CANCEL_STOCK,
                target="non_core_leaders",
                description=f"A50跌{a50_change*100:.1f}%，取消非核心龙头买入",
                reason=f"A50期指跌幅{a50_change*100:.1f}%超过-2%阈值",
            ))
            
            # 过滤只保留真龙头
            recommendations = [
                r for r in recommendations
                if r.get('leader_type') == '真龙头'
            ]
            
            # 下调所有买入价2%
            for r in recommendations:
                original_ideal = r.get('ideal_price', 0)
                original_acceptable = r.get('acceptable_price', 0)
                r['ideal_price'] = round(original_ideal * (1 - self.price_adjust_ratio), 2)
                r['acceptable_price'] = round(original_acceptable * (1 - self.price_adjust_ratio), 2)
            
            adjustments.append(Adjustment(
                adjustment_type=AdjustmentType.PRICE_ADJUST,
                target="all",
                description=f"下调所有买入价{self.price_adjust_ratio*100:.0f}%",
                reason=f"A50期指跌幅{a50_change*100:.1f}%超过-2%阈值",
            ))
            
        elif a50_change < self.a50_threshold_mild:
            # A50跌1-2%: 仅下调买入价2%
            adjustments.append(Adjustment(
                adjustment_type=AdjustmentType.PRICE_ADJUST,
                target="all",
                description=f"A50跌{a50_change*100:.1f}%，下调所有买入价{self.price_adjust_ratio*100:.0f}%",
                reason=f"A50期指跌幅{a50_change*100:.1f}%超过-1%阈值",
            ))
            
            for r in recommendations:
                original_ideal = r.get('ideal_price', 0)
                original_acceptable = r.get('acceptable_price', 0)
                r['ideal_price'] = round(original_ideal * (1 - self.price_adjust_ratio), 2)
                r['acceptable_price'] = round(original_acceptable * (1 - self.price_adjust_ratio), 2)
        
        # 2. 个股公告检查
        for ann in overnight_data.announcements:
            if ann.announcement_type == 'negative' and ann.severity in ['medium', 'high']:
                stock_code = ann.code
                # 检查是否在推荐列表中
                before_count = len(recommendations)
                recommendations = [
                    r for r in recommendations
                    if r.get('code') != stock_code
                ]
                after_count = len(recommendations)
                
                if before_count > after_count:
                    adjustments.append(Adjustment(
                        adjustment_type=AdjustmentType.CANCEL_STOCK,
                        target=stock_code,
                        description=f"{ann.name}({stock_code})有利空公告，取消买入",
                        reason=f"公告: {ann.title}",
                    ))
        
        # 3. 美股大跌预警
        if nasdaq_change < self.us_threshold_severe:
            adjustments.append(Adjustment(
                adjustment_type=AdjustmentType.POSITION_REDUCE,
                target="total_position",
                description=f"纳指跌{nasdaq_change*100:.1f}%，建议降低总仓位至{self.position_reduce_ratio*100:.0f}%",
                original_value=adjusted_plan.get('total_position', 0.8),
                adjusted_value=adjusted_plan.get('total_position', 0.8) * self.position_reduce_ratio,
                reason=f"纳斯达克跌幅{nasdaq_change*100:.1f}%超过-2%阈值",
            ))
            
            original_position = adjusted_plan.get('total_position', 0.8)
            adjusted_plan['total_position'] = round(original_position * self.position_reduce_ratio, 4)
        
        # 更新推荐列表
        adjusted_plan['recommendations'] = recommendations
        
        # 添加调整信息
        adjusted_plan['adjustments'] = [
            {
                'type': adj.adjustment_type.value,
                'target': adj.target,
                'description': adj.description,
                'reason': adj.reason,
            }
            for adj in adjustments
        ]
        adjusted_plan['adjustment_time'] = datetime.now().strftime("%H:%M")
        adjusted_plan['overnight_data'] = overnight_data.to_dict()
        adjusted_plan['market_severity'] = self._assess_market_severity(overnight_data).value
        
        return adjusted_plan, adjustments
    
    def generate_adjustment_report(self,
                                   original_plan: Dict,
                                   adjusted_plan: Dict,
                                   overnight_data: OvernightData,
                                   adjustments: List[Adjustment]) -> AdjustmentReport:
        """
        生成早盘修正报告
        
        Args:
            original_plan: 原始交易计划
            adjusted_plan: 调整后的交易计划
            overnight_data: 隔夜数据
            adjustments: 调整列表
        
        Returns:
            AdjustmentReport: 早盘修正报告
        """
        report_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        original_count = len(original_plan.get('recommendations', []))
        adjusted_count = len(adjusted_plan.get('recommendations', []))
        
        market_severity = self._assess_market_severity(overnight_data)
        
        # 生成总结
        if not adjustments:
            summary = "隔夜市场平稳，无需调整，按原计划执行"
        elif market_severity == MarketSeverity.EXTREME:
            summary = "⚠️ 隔夜市场剧烈波动，建议谨慎操作或观望"
        elif market_severity == MarketSeverity.SEVERE:
            summary = "⚠️ 隔夜市场大幅下跌，已调整买入计划，请严格执行"
        elif market_severity == MarketSeverity.MILD:
            summary = "隔夜市场小幅波动，已适当调整买入价格"
        else:
            summary = "按调整后的计划执行"
        
        return AdjustmentReport(
            report_time=report_time,
            overnight_data=overnight_data,
            adjustments=adjustments,
            market_severity=market_severity,
            original_stock_count=original_count,
            adjusted_stock_count=adjusted_count,
            summary=summary,
        )
    
    def run_pre_market_adjustment(self,
                                  original_plan: Dict,
                                  overnight_data: OvernightData = None) -> tuple:
        """
        运行早盘修正流程
        
        完整流程:
        1. 获取隔夜数据 (如果未提供)
        2. 调整交易计划
        3. 生成修正报告
        
        Args:
            original_plan: 原始交易计划
            overnight_data: 隔夜数据 (可选，如果不提供则自动获取)
        
        Returns:
            tuple: (adjusted_plan, report)
                - adjusted_plan: 调整后的交易计划
                - report: AdjustmentReport 早盘修正报告
        """
        # 1. 获取隔夜数据
        if overnight_data is None:
            overnight_data = self.fetch_overnight_data()
        
        # 2. 调整交易计划
        adjusted_plan, adjustments = self.adjust_trading_plan(original_plan, overnight_data)
        
        # 3. 生成修正报告
        report = self.generate_adjustment_report(
            original_plan, adjusted_plan, overnight_data, adjustments
        )
        
        return adjusted_plan, report


# 便捷函数
def create_pre_market_adjuster() -> PreMarketAdjuster:
    """创建早盘修正器实例"""
    return PreMarketAdjuster()


def quick_pre_market_check(original_plan: Dict,
                           a50_change: float = 0.0,
                           nasdaq_change: float = 0.0) -> tuple:
    """
    快速早盘检查
    
    Args:
        original_plan: 原始交易计划
        a50_change: A50期指涨跌幅
        nasdaq_change: 纳斯达克涨跌幅
    
    Returns:
        tuple: (adjusted_plan, report_markdown)
    """
    adjuster = PreMarketAdjuster()
    overnight_data = adjuster.fetch_overnight_data_with_values(
        a50_change=a50_change,
        nasdaq_change=nasdaq_change,
    )
    
    adjusted_plan, report = adjuster.run_pre_market_adjustment(original_plan, overnight_data)
    
    return adjusted_plan, report.to_markdown()
