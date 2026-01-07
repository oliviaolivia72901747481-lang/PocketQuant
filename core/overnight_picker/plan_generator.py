"""
交易计划生成器 (TradingPlanGenerator)

生成完整的明日交易计划，包含:
- 市场环境分析
- 推荐股票列表
- 买入价、仓位、止损止盈建议
- 操作要点和风险提示
- Markdown格式输出
- 历史计划记录
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

import numpy as np

from .models import StockRecommendation, TradingPlan


class NumpyJSONEncoder(json.JSONEncoder):
    """自定义JSON编码器，处理numpy类型"""
    
    def default(self, obj):
        # 处理numpy布尔类型
        if isinstance(obj, np.bool_):
            return bool(obj)
        # 处理numpy整数类型
        if isinstance(obj, np.integer):
            return int(obj)
        # 处理numpy浮点类型
        if isinstance(obj, np.floating):
            return float(obj)
        # 处理numpy数组
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


class TradingPlanGenerator:
    """
    交易计划生成器 - 输出完整的明日交易计划
    
    功能:
    1. 生成交易计划文档
    2. 输出Markdown格式
    3. 记录历史计划
    """
    
    # 默认操作要点
    DEFAULT_OPERATION_TIPS = [
        "**开盘观察**: 9:25集合竞价观察开盘价，低于\"可接受买入价\"再下单",
        "**分批买入**: 建议分2次买入，先买一半，确认走势后再加仓",
        "**严格止损**: 跌破止损价立即卖出，不要犹豫",
        "**止盈策略**: 涨5%卖一半，涨10%卖剩余",
    ]
    
    # 默认风险提示
    DEFAULT_RISK_WARNINGS = [
        "本计划基于历史数据分析，不构成投资建议",
        "股市有风险，入市需谨慎",
        "建议总仓位不超过80%，保留现金应对突发情况",
        "如果明日大盘大幅低开(>1%)，建议观望不操作",
    ]
    
    def __init__(self, 
                 history_dir: str = "data/trading_plans",
                 total_capital: float = 70000):
        """
        初始化交易计划生成器
        
        Args:
            history_dir: 历史计划保存目录
            total_capital: 总资金
        """
        self.history_dir = history_dir
        self.total_capital = total_capital
        self._ensure_history_dir()
    
    def _ensure_history_dir(self):
        """确保历史计划目录存在"""
        Path(self.history_dir).mkdir(parents=True, exist_ok=True)

    def generate_plan(self,
                     date: str,
                     market_env: Dict,
                     sentiment: Dict,
                     recommendations: List[StockRecommendation],
                     hot_topics: List[str] = None) -> TradingPlan:
        """
        生成交易计划
        
        Args:
            date: 计划日期 (YYYY-MM-DD)
            market_env: 市场环境信息
                - env: 大盘环境 (强势/震荡/弱势)
                - description: 环境描述
            sentiment: 市场情绪信息
                - sentiment: 情绪等级 (乐观/中性/恐慌)
                - phase: 情绪周期阶段
                - prediction: 明日预判
                - position_multiplier: 仓位调整系数
            recommendations: 推荐股票列表
            hot_topics: 当前热点列表
        
        Returns:
            TradingPlan: 完整的交易计划
        """
        if hot_topics is None:
            hot_topics = []
        
        # 生成时间
        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 限制推荐列表最多5只
        if len(recommendations) > 5:
            recommendations = recommendations[:5]
        
        # 按评分排序
        recommendations = sorted(recommendations, 
                                key=lambda x: x.total_score, 
                                reverse=True)
        
        # 计算总仓位
        total_position = sum(r.position_ratio for r in recommendations)
        total_position = min(total_position, 0.8)  # 限制最大80%
        
        # 生成操作要点
        operation_tips = self._generate_operation_tips(
            market_env=market_env,
            sentiment=sentiment,
            recommendations=recommendations
        )
        
        # 生成风险提示
        risk_warnings = self._generate_risk_warnings(
            market_env=market_env,
            sentiment=sentiment,
            recommendations=recommendations
        )
        
        # 创建交易计划
        plan = TradingPlan(
            date=date,
            generated_at=generated_at,
            market_env=market_env.get('env', '震荡'),
            market_sentiment=sentiment.get('sentiment', '中性'),
            sentiment_phase=sentiment.get('phase', ''),
            hot_topics=hot_topics,
            recommendations=recommendations,
            total_position=total_position,
            operation_tips=operation_tips,
            risk_warnings=risk_warnings,
            tomorrow_prediction=sentiment.get('prediction', ''),
            position_multiplier=sentiment.get('position_multiplier', 1.0),
        )
        
        return plan
    
    def _generate_operation_tips(self,
                                market_env: Dict,
                                sentiment: Dict,
                                recommendations: List[StockRecommendation]) -> List[str]:
        """
        生成操作要点
        
        根据市场环境和情绪生成针对性的操作建议
        """
        tips = list(self.DEFAULT_OPERATION_TIPS)
        
        env = market_env.get('env', '震荡')
        phase = sentiment.get('phase', '')
        
        # 根据市场环境添加特殊提示
        if env == '弱势':
            tips.insert(0, "⚠️ **弱势市场**: 降低仓位，优先观望，只做最强龙头")
        elif env == '强势':
            tips.insert(0, "💪 **强势市场**: 可适当提高仓位，跟随热点操作")
        
        # 根据情绪周期添加提示
        if phase == '高潮':
            tips.insert(1, "🔥 **高潮日后**: 明日大概率分歧，减半仓位，只做核心龙头")
        elif phase == '冰点':
            tips.insert(1, "❄️ **冰点修复**: 可适当试错，关注反包形态")
        elif phase == '分歧':
            tips.insert(1, "⚡ **分歧日**: 观望为主，等待方向明确")
        
        # 根据推荐股票数量添加提示
        if len(recommendations) == 0:
            tips = ["今日无推荐股票，建议空仓观望"]
        elif len(recommendations) == 1:
            tips.append("**集中持仓**: 只有1只推荐，可适当提高该股仓位")
        
        return tips
    
    def _generate_risk_warnings(self,
                               market_env: Dict,
                               sentiment: Dict,
                               recommendations: List[StockRecommendation]) -> List[str]:
        """
        生成风险提示
        
        根据市场环境和推荐股票生成针对性的风险提示
        """
        warnings = list(self.DEFAULT_RISK_WARNINGS)
        
        env = market_env.get('env', '震荡')
        phase = sentiment.get('phase', '')
        
        # 根据市场环境添加风险提示
        if env == '弱势':
            warnings.insert(0, "⚠️ 当前大盘弱势，系统性风险较高，请谨慎操作")
        
        # 根据情绪周期添加风险提示
        if phase == '高潮':
            warnings.insert(0, "🔥 市场情绪高潮，明日分歧概率大，注意控制仓位")
        elif phase == '退潮':
            warnings.insert(0, "📉 市场情绪退潮，赚钱效应减弱，建议轻仓")
        
        # 检查推荐股票的风险
        high_risk_count = sum(1 for r in recommendations if r.risk_level == 'HIGH')
        if high_risk_count > 0:
            warnings.append(f"有{high_risk_count}只高风险股票，请特别注意止损")
        
        # 检查总仓位
        total_position = sum(r.position_ratio for r in recommendations)
        if total_position > 0.6:
            warnings.append(f"建议总仓位{total_position*100:.0f}%较高，请根据实际情况调整")
        
        return warnings

    def to_markdown(self, plan: TradingPlan) -> str:
        """
        生成Markdown格式的交易计划
        
        Args:
            plan: 交易计划对象
        
        Returns:
            Markdown格式的字符串
        """
        lines = []
        
        # 标题
        lines.append(f"# 📈 明日交易计划 ({plan.date})")
        lines.append("")
        lines.append(f"生成时间: {plan.generated_at}")
        lines.append("")
        
        # 市场环境
        lines.append("## 📊 市场环境")
        lines.append("")
        lines.append("| 指标 | 状态 | 说明 |")
        lines.append("|------|------|------|")
        
        # 大盘环境图标
        env_icon = self._get_env_icon(plan.market_env)
        lines.append(f"| 大盘环境 | {env_icon} {plan.market_env} | - |")
        
        # 市场情绪图标
        sentiment_icon = self._get_sentiment_icon(plan.market_sentiment)
        phase_desc = f"({plan.sentiment_phase})" if plan.sentiment_phase else ""
        lines.append(f"| 市场情绪 | {sentiment_icon} {plan.market_sentiment} | {plan.sentiment_phase} |")
        
        # 当前热点
        if plan.hot_topics:
            topics_str = ', '.join(plan.hot_topics[:5])
            lines.append(f"| 当前热点 | {topics_str} | - |")
        
        lines.append("")
        
        # 明日预判
        if plan.tomorrow_prediction:
            lines.append("### 📅 明日预判")
            lines.append("")
            lines.append(f"> {plan.tomorrow_prediction}")
            lines.append("")
        
        # 推荐股票
        if plan.recommendations:
            lines.append(f"## ⭐ 推荐买入 (共{len(plan.recommendations)}只)")
            lines.append("")
            
            for i, rec in enumerate(plan.recommendations, 1):
                lines.extend(self._format_recommendation(i, rec))
        else:
            lines.append("## ⚠️ 今日无推荐")
            lines.append("")
            lines.append("当前市场环境不适合操作，建议观望。")
            lines.append("")
        
        # 投资汇总
        if plan.recommendations:
            lines.extend(self._format_investment_summary(plan))
        
        # 操作要点
        if plan.operation_tips:
            lines.append("## 💡 明日操作要点")
            lines.append("")
            for i, tip in enumerate(plan.operation_tips, 1):
                lines.append(f"{i}. {tip}")
            lines.append("")
        
        # 风险提示
        if plan.risk_warnings:
            lines.append("## ⚠️ 风险提示")
            lines.append("")
            for i, warning in enumerate(plan.risk_warnings, 1):
                lines.append(f"{i}. {warning}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _get_env_icon(self, env: str) -> str:
        """获取大盘环境图标"""
        icons = {
            "强势": "🟢",
            "震荡": "🟡",
            "弱势": "🔴",
        }
        return icons.get(env, "🟡")
    
    def _get_sentiment_icon(self, sentiment: str) -> str:
        """获取市场情绪图标"""
        icons = {
            "乐观": "🟢",
            "中性": "🟡",
            "恐慌": "🔴",
        }
        return icons.get(sentiment, "🟡")
    
    def _format_recommendation(self, index: int, rec: StockRecommendation) -> List[str]:
        """格式化单只股票推荐"""
        lines = []
        
        # 评分星级
        stars = "⭐" * min(3, int(rec.total_score / 30) + 1)
        
        lines.append(f"### {index}. {rec.name} ({rec.code}) - 评分: {rec.total_score:.0f}分 {stars}")
        lines.append("")
        
        # 基本信息表格
        lines.append("| 项目 | 数值 | 说明 |")
        lines.append("|------|------|------|")
        lines.append(f"| 今日收盘 | {rec.today_close:.2f}元 | 涨幅 {rec.today_change:+.1f}% |")
        lines.append(f"| 所属板块 | {rec.sector} | - |")
        lines.append(f"| 龙头类型 | {rec.leader_type or '-'} | - |")
        lines.append(f"| 策略类型 | {self._get_strategy_type_name(rec.strategy_type)} | - |")
        lines.append("")
        
        # 评分详情
        if rec.score_details:
            lines.append("**评分详情:**")
            for dim, detail in rec.score_details.items():
                dim_name = self._get_dimension_name(dim)
                # 处理不同格式的评分详情
                if isinstance(detail, dict):
                    score = detail.get('score', 0)
                    max_score = detail.get('max_score', 0)
                    desc = self._get_detail_desc(detail)
                    lines.append(f"- {dim_name}: {score}/{max_score} ({desc})")
                elif isinstance(detail, (int, float)):
                    # 如果是数值，直接显示
                    lines.append(f"- {dim_name}: {detail}")
                elif isinstance(detail, list):
                    # 如果是列表（如risks），显示为逗号分隔
                    if detail:
                        lines.append(f"- {dim_name}: {', '.join(str(x) for x in detail)}")
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
        
        # 推荐理由
        if rec.reasoning:
            lines.append(f"**推荐理由:** {rec.reasoning}")
            lines.append("")
        
        # 相关热点
        if rec.hot_topics:
            lines.append(f"**相关热点:** {', '.join(rec.hot_topics)}")
            lines.append("")
        
        lines.append("---")
        lines.append("")
        
        return lines
    
    def _get_strategy_type_name(self, strategy_type: str) -> str:
        """获取策略类型中文名"""
        names = {
            "low_buy": "低吸型",
            "breakout": "突破型",
        }
        return names.get(strategy_type, strategy_type)
    
    def _get_dimension_name(self, dimension: str) -> str:
        """获取评分维度中文名"""
        names = {
            'closing_pattern': '收盘形态',
            'volume_analysis': '量能分析',
            'ma_position': '均线位置',
            'capital_flow': '资金流向',
            'hot_topic': '热点关联',
            'leader_index': '龙头地位',
            'sector_strength': '板块强度',
            'technical_pattern': '技术形态',
        }
        return names.get(dimension, dimension)
    
    def _get_detail_desc(self, detail: Dict) -> str:
        """获取评分详情描述"""
        for key in ['pattern', 'vol_type', 'ma_type', 'flow_type', 
                    'topic_type', 'leader_type', 'strength_type']:
            if key in detail:
                return detail[key]
        return '-'
    
    def _format_investment_summary(self, plan: TradingPlan) -> List[str]:
        """格式化投资汇总"""
        lines = []
        
        total_investment = plan.get_total_investment()
        max_loss = plan.get_max_total_loss()
        expected_profit = plan.get_expected_total_profit()
        
        lines.append("## 📊 投资汇总")
        lines.append("")
        lines.append("| 项目 | 金额 | 说明 |")
        lines.append("|------|------|------|")
        lines.append(f"| 总投资金额 | {total_investment:.0f}元 | 占总资金{plan.total_position*100:.0f}% |")
        lines.append(f"| 最大亏损 | {max_loss:.0f}元 | 全部止损时 |")
        lines.append(f"| 预期盈利 | {expected_profit:.0f}元 | 全部止盈时 |")
        lines.append(f"| 盈亏比 | {expected_profit/max_loss:.1f}:1 | - |" if max_loss > 0 else "| 盈亏比 | - | - |")
        lines.append("")
        
        return lines

    def save_plan(self, plan: TradingPlan, 
                  save_markdown: bool = True,
                  save_json: bool = True) -> Dict[str, str]:
        """
        保存交易计划到历史记录
        
        Args:
            plan: 交易计划对象
            save_markdown: 是否保存Markdown格式
            save_json: 是否保存JSON格式
        
        Returns:
            保存的文件路径字典
        """
        saved_files = {}
        
        # 生成文件名
        date_str = plan.date.replace('-', '')
        base_filename = f"trading_plan_{date_str}"
        
        # 保存Markdown格式
        if save_markdown:
            md_path = os.path.join(self.history_dir, f"{base_filename}.md")
            md_content = self.to_markdown(plan)
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(md_content)
            saved_files['markdown'] = md_path
        
        # 保存JSON格式
        if save_json:
            json_path = os.path.join(self.history_dir, f"{base_filename}.json")
            json_content = plan.to_dict()
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(json_content, f, ensure_ascii=False, indent=2, cls=NumpyJSONEncoder)
            saved_files['json'] = json_path
        
        return saved_files
    
    def load_plan(self, date: str) -> Optional[TradingPlan]:
        """
        加载历史交易计划
        
        Args:
            date: 计划日期 (YYYY-MM-DD)
        
        Returns:
            TradingPlan对象，如果不存在返回None
        """
        date_str = date.replace('-', '')
        json_path = os.path.join(self.history_dir, f"trading_plan_{date_str}.json")
        
        if not os.path.exists(json_path):
            return None
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 重建推荐列表
            recommendations = []
            for rec_data in data.get('recommendations', []):
                rec = StockRecommendation(
                    code=rec_data['code'],
                    name=rec_data['name'],
                    sector=rec_data['sector'],
                    today_close=rec_data['today_close'],
                    today_change=rec_data['today_change'],
                    total_score=rec_data['total_score'],
                    score_details=rec_data.get('score_details', {}),
                    ideal_price=rec_data.get('ideal_price', 0),
                    acceptable_price=rec_data.get('acceptable_price', 0),
                    abandon_price=rec_data.get('abandon_price', 0),
                    position_ratio=rec_data.get('position_ratio', 0),
                    position_amount=rec_data.get('position_amount', 0),
                    shares=rec_data.get('shares', 0),
                    stop_loss_price=rec_data.get('stop_loss_price', 0),
                    first_target=rec_data.get('first_target', 0),
                    second_target=rec_data.get('second_target', 0),
                    max_loss=rec_data.get('max_loss', 0),
                    expected_profit=rec_data.get('expected_profit', 0),
                    hot_topics=rec_data.get('hot_topics', []),
                    leader_type=rec_data.get('leader_type', ''),
                    risk_level=rec_data.get('risk_level', 'MEDIUM'),
                    reasoning=rec_data.get('reasoning', ''),
                    strategy_type=rec_data.get('strategy_type', 'low_buy'),
                )
                recommendations.append(rec)
            
            # 创建交易计划
            plan = TradingPlan(
                date=data['date'],
                generated_at=data['generated_at'],
                market_env=data.get('market_env', '震荡'),
                market_sentiment=data.get('market_sentiment', '中性'),
                sentiment_phase=data.get('sentiment_phase', ''),
                hot_topics=data.get('hot_topics', []),
                recommendations=recommendations,
                total_position=data.get('total_position', 0),
                operation_tips=data.get('operation_tips', []),
                risk_warnings=data.get('risk_warnings', []),
                tomorrow_prediction=data.get('tomorrow_prediction', ''),
                position_multiplier=data.get('position_multiplier', 1.0),
            )
            
            return plan
        except Exception as e:
            print(f"加载交易计划失败: {e}")
            return None
    
    def list_history_plans(self, limit: int = 30) -> List[Dict]:
        """
        列出历史交易计划
        
        Args:
            limit: 最大返回数量
        
        Returns:
            历史计划列表，每项包含日期和文件路径
        """
        plans = []
        
        if not os.path.exists(self.history_dir):
            return plans
        
        # 查找所有JSON文件
        for filename in os.listdir(self.history_dir):
            if filename.startswith('trading_plan_') and filename.endswith('.json'):
                date_str = filename.replace('trading_plan_', '').replace('.json', '')
                # 转换日期格式
                if len(date_str) == 8:
                    date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
                    plans.append({
                        'date': date,
                        'json_path': os.path.join(self.history_dir, filename),
                        'md_path': os.path.join(self.history_dir, filename.replace('.json', '.md')),
                    })
        
        # 按日期降序排序
        plans.sort(key=lambda x: x['date'], reverse=True)
        
        return plans[:limit]
    
    def delete_plan(self, date: str) -> bool:
        """
        删除历史交易计划
        
        Args:
            date: 计划日期 (YYYY-MM-DD)
        
        Returns:
            是否删除成功
        """
        date_str = date.replace('-', '')
        json_path = os.path.join(self.history_dir, f"trading_plan_{date_str}.json")
        md_path = os.path.join(self.history_dir, f"trading_plan_{date_str}.md")
        
        deleted = False
        
        if os.path.exists(json_path):
            os.remove(json_path)
            deleted = True
        
        if os.path.exists(md_path):
            os.remove(md_path)
            deleted = True
        
        return deleted


def create_trading_plan_generator(history_dir: str = "data/trading_plans",
                                  total_capital: float = 70000) -> TradingPlanGenerator:
    """
    创建交易计划生成器的工厂函数
    
    Args:
        history_dir: 历史计划保存目录
        total_capital: 总资金
    
    Returns:
        TradingPlanGenerator实例
    """
    return TradingPlanGenerator(history_dir=history_dir, total_capital=total_capital)


def quick_generate_plan(date: str,
                       market_env: str,
                       market_sentiment: str,
                       recommendations: List[StockRecommendation],
                       hot_topics: List[str] = None,
                       save: bool = True) -> TradingPlan:
    """
    快速生成交易计划的便捷函数
    
    Args:
        date: 计划日期
        market_env: 大盘环境
        market_sentiment: 市场情绪
        recommendations: 推荐股票列表
        hot_topics: 热点列表
        save: 是否保存到历史
    
    Returns:
        TradingPlan对象
    """
    generator = create_trading_plan_generator()
    
    plan = generator.generate_plan(
        date=date,
        market_env={'env': market_env},
        sentiment={'sentiment': market_sentiment},
        recommendations=recommendations,
        hot_topics=hot_topics or []
    )
    
    if save:
        generator.save_plan(plan)
    
    return plan
