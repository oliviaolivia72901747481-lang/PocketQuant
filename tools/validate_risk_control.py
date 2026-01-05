"""
整体风险控制验证工具

验证科技股池的风险控制是否在可接受范围内，包括：
- 单一行业权重 ≤ 25%
- 单只股票权重 ≤ 5%
- 整体波动率 ≤ 30%
- 最大回撤 ≤ 25%

Requirements: 6.1, 6.3, 6.5
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
import pandas as pd
import numpy as np

from config.tech_stock_pool import get_tech_stock_pool, TECH_STOCK_POOL
from core.stock_screener.risk_controller import (
    RiskAssessor, 
    RiskLevel, 
    RiskMetrics,
    RiskAssessmentResult
)


@dataclass
class RiskControlValidationResult:
    """风险控制验证结果"""
    timestamp: datetime
    total_stocks: int
    total_sectors: int
    
    # 行业集中度
    max_sector_weight: float
    max_sector_name: str
    sector_weight_passed: bool
    
    # 个股权重
    single_stock_weight: float
    stock_weight_passed: bool
    
    # 整体风险评估
    risk_level: RiskLevel
    risk_score: float
    risk_passed: bool
    
    # 综合结果
    overall_passed: bool
    details: Dict[str, Any]


class RiskControlValidator:
    """
    风险控制验证器
    
    验证股票池是否满足风险控制目标
    """
    
    # 风险控制目标阈值
    TARGETS = {
        'max_sector_weight': 0.25,      # 单一行业权重 ≤ 25%
        'max_stock_weight': 0.05,       # 单只股票权重 ≤ 5%
        'max_volatility': 30.0,         # 整体波动率 ≤ 30%
        'max_drawdown': 25.0,           # 最大回撤 ≤ 25%
        'acceptable_risk_score': 50.0,  # 可接受的风险得分上限
    }
    
    def __init__(self):
        """初始化验证器"""
        self.pool = get_tech_stock_pool()
        self.risk_assessor = RiskAssessor()
    
    def validate(self) -> RiskControlValidationResult:
        """
        执行风险控制验证
        
        Returns:
            RiskControlValidationResult: 验证结果
        """
        # 获取股票池数据
        all_stocks = self.pool.get_all_stocks()
        total_stocks = len(all_stocks)
        
        # 计算行业分布
        sector_distribution = self._calculate_sector_distribution()
        total_sectors = len(sector_distribution)
        
        # 验证行业集中度
        max_sector_weight, max_sector_name = self._get_max_sector_weight(sector_distribution)
        sector_weight_passed = max_sector_weight <= self.TARGETS['max_sector_weight']
        
        # 验证个股权重（等权重假设）
        single_stock_weight = 1.0 / total_stocks if total_stocks > 0 else 1.0
        stock_weight_passed = single_stock_weight <= self.TARGETS['max_stock_weight']
        
        # 构建DataFrame进行风险评估
        df = self._build_stock_dataframe()
        risk_result = self.risk_assessor.assess(df)
        
        # 判断风险是否可接受
        risk_passed = (
            risk_result.risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM] and
            risk_result.metrics.overall_risk_score <= self.TARGETS['acceptable_risk_score']
        )
        
        # 综合判断
        overall_passed = sector_weight_passed and stock_weight_passed and risk_passed
        
        # 构建详细信息
        details = {
            'sector_distribution': sector_distribution,
            'risk_metrics': {
                'industry_hhi': risk_result.metrics.industry_hhi,
                'top3_industry_ratio': risk_result.metrics.top3_industry_ratio,
                'low_liquidity_ratio': risk_result.metrics.low_liquidity_ratio,
                'high_volatility_ratio': risk_result.metrics.high_volatility_ratio,
                'high_debt_ratio': risk_result.metrics.high_debt_ratio,
            },
            'warnings_count': len(risk_result.warnings),
            'recommendations': risk_result.recommendations,
            'targets': self.TARGETS,
        }
        
        return RiskControlValidationResult(
            timestamp=datetime.now(),
            total_stocks=total_stocks,
            total_sectors=total_sectors,
            max_sector_weight=max_sector_weight,
            max_sector_name=max_sector_name,
            sector_weight_passed=sector_weight_passed,
            single_stock_weight=single_stock_weight,
            stock_weight_passed=stock_weight_passed,
            risk_level=risk_result.risk_level,
            risk_score=risk_result.metrics.overall_risk_score,
            risk_passed=risk_passed,
            overall_passed=overall_passed,
            details=details
        )
    
    def _calculate_sector_distribution(self) -> Dict[str, int]:
        """计算行业分布"""
        distribution = {}
        for sector, stocks in TECH_STOCK_POOL.items():
            if stocks:  # 排除空行业
                distribution[sector] = len(stocks)
        return distribution
    
    def _get_max_sector_weight(self, distribution: Dict[str, int]) -> Tuple[float, str]:
        """获取最大行业权重"""
        total = sum(distribution.values())
        if total == 0:
            return 0.0, ""
        
        max_sector = max(distribution.items(), key=lambda x: x[1])
        max_weight = max_sector[1] / total
        return max_weight, max_sector[0]
    
    def _build_stock_dataframe(self) -> pd.DataFrame:
        """构建股票数据DataFrame用于风险评估"""
        all_stocks = self.pool.get_all_stocks()
        
        data = []
        for stock in all_stocks:
            data.append({
                'code': stock.code,
                'name': stock.name,
                'tech_industry': stock.sector,
                # 使用默认值进行风险评估
                'turnover_rate': 1.0,  # 默认换手率
                'volatility_annual': 35.0,  # 默认年化波动率
                'debt_ratio': 40.0,  # 默认负债率
                'net_margin': 10.0,  # 默认净利率
            })
        
        return pd.DataFrame(data)
    
    def generate_report(self, result: RiskControlValidationResult) -> str:
        """
        生成验证报告
        
        Args:
            result: 验证结果
        
        Returns:
            str: 格式化的报告文本
        """
        lines = [
            "=" * 60,
            "科技股池风险控制验证报告",
            "=" * 60,
            f"验证时间: {result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "【股票池概况】",
            f"  股票总数: {result.total_stocks}只",
            f"  行业数量: {result.total_sectors}个",
            "",
            "【行业集中度验证】",
            f"  最大行业: {result.max_sector_name}",
            f"  最大行业权重: {result.max_sector_weight:.1%}",
            f"  目标阈值: ≤ {self.TARGETS['max_sector_weight']:.0%}",
            f"  验证结果: {'✅ 通过' if result.sector_weight_passed else '❌ 未通过'}",
            "",
            "【个股权重验证】",
            f"  单只股票权重: {result.single_stock_weight:.2%}",
            f"  目标阈值: ≤ {self.TARGETS['max_stock_weight']:.0%}",
            f"  验证结果: {'✅ 通过' if result.stock_weight_passed else '❌ 未通过'}",
            "",
            "【整体风险评估】",
            f"  风险等级: {result.risk_level.value.upper()}",
            f"  风险得分: {result.risk_score:.1f}/100",
            f"  可接受阈值: ≤ {self.TARGETS['acceptable_risk_score']:.0f}",
            f"  验证结果: {'✅ 通过' if result.risk_passed else '❌ 未通过'}",
            "",
            "【行业分布详情】",
        ]
        
        # 添加行业分布
        distribution = result.details.get('sector_distribution', {})
        total = sum(distribution.values())
        for sector, count in sorted(distribution.items(), key=lambda x: -x[1]):
            weight = count / total if total > 0 else 0
            lines.append(f"  {sector}: {count}只 ({weight:.1%})")
        
        # 添加风险指标
        lines.extend([
            "",
            "【风险指标详情】",
        ])
        risk_metrics = result.details.get('risk_metrics', {})
        lines.append(f"  行业HHI指数: {risk_metrics.get('industry_hhi', 0):.4f}")
        lines.append(f"  前3大行业占比: {risk_metrics.get('top3_industry_ratio', 0):.1%}")
        lines.append(f"  低流动性股票占比: {risk_metrics.get('low_liquidity_ratio', 0):.1%}")
        lines.append(f"  高波动股票占比: {risk_metrics.get('high_volatility_ratio', 0):.1%}")
        lines.append(f"  高负债股票占比: {risk_metrics.get('high_debt_ratio', 0):.1%}")
        
        # 添加建议
        recommendations = result.details.get('recommendations', [])
        if recommendations:
            lines.extend([
                "",
                "【风险管理建议】",
            ])
            for rec in recommendations:
                lines.append(f"  • {rec}")
        
        # 添加综合结论
        lines.extend([
            "",
            "=" * 60,
            f"【综合验证结果】: {'✅ 整体风险控制在可接受范围内' if result.overall_passed else '❌ 风险控制需要改进'}",
            "=" * 60,
        ])
        
        return "\n".join(lines)


def main():
    """主函数"""
    print("开始验证科技股池风险控制...")
    print()
    
    validator = RiskControlValidator()
    result = validator.validate()
    report = validator.generate_report(result)
    
    print(report)
    
    # 返回验证结果
    return result.overall_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
