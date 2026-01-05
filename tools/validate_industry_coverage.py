"""
行业覆盖验证工具

验证科技股池的行业覆盖是否达到8-10个细分领域的要求

Requirements: 2.1 - THE 系统 SHALL 覆盖至少8个科技细分行业
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, List, Tuple
from dataclasses import dataclass
from config.tech_stock_pool import TECH_STOCK_POOL, get_tech_stock_pool


@dataclass
class IndustryCoverageResult:
    """行业覆盖验证结果"""
    passed: bool
    total_industries: int
    industries_with_stocks: int
    min_required: int
    max_target: int
    industry_details: Dict[str, int]
    warnings: List[str]
    suggestions: List[str]


def validate_industry_coverage(
    min_industries: int = 8,
    max_industries: int = 10,
    min_stocks_per_industry: int = 5
) -> IndustryCoverageResult:
    """
    验证行业覆盖是否达到要求
    
    Args:
        min_industries: 最少行业数量要求
        max_industries: 目标行业数量上限
        min_stocks_per_industry: 每个行业最少股票数量
    
    Returns:
        IndustryCoverageResult: 验证结果
    """
    warnings = []
    suggestions = []
    
    # 统计各行业股票数量
    industry_details = {}
    for industry, stocks in TECH_STOCK_POOL.items():
        stock_count = len(stocks)
        industry_details[industry] = stock_count
    
    # 计算有效行业数量（有股票的行业）
    industries_with_stocks = sum(1 for count in industry_details.values() if count > 0)
    total_industries = len(industry_details)
    
    # 验证是否达到最低要求
    passed = industries_with_stocks >= min_industries
    
    # 生成警告和建议
    if industries_with_stocks < min_industries:
        warnings.append(f"行业覆盖数量({industries_with_stocks})低于最低要求({min_industries})")
        suggestions.append("需要扩展更多科技细分行业")
    
    if industries_with_stocks > max_industries:
        warnings.append(f"行业覆盖数量({industries_with_stocks})超过目标上限({max_industries})")
    
    # 检查每个行业的股票数量
    for industry, count in industry_details.items():
        if count > 0 and count < min_stocks_per_industry:
            warnings.append(f"行业'{industry}'股票数量({count})低于建议值({min_stocks_per_industry})")
            suggestions.append(f"建议为'{industry}'行业增加更多股票")
    
    # 检查空行业
    empty_industries = [ind for ind, count in industry_details.items() if count == 0]
    if empty_industries:
        warnings.append(f"以下行业没有股票: {', '.join(empty_industries)}")
    
    return IndustryCoverageResult(
        passed=passed,
        total_industries=total_industries,
        industries_with_stocks=industries_with_stocks,
        min_required=min_industries,
        max_target=max_industries,
        industry_details=industry_details,
        warnings=warnings,
        suggestions=suggestions
    )


def print_validation_report(result: IndustryCoverageResult) -> None:
    """打印验证报告"""
    print("=" * 60)
    print("科技股池行业覆盖验证报告")
    print("=" * 60)
    print()
    
    # 验证结果
    status = "✅ 通过" if result.passed else "❌ 未通过"
    print(f"验证结果: {status}")
    print()
    
    # 行业覆盖统计
    print(f"📊 行业覆盖统计:")
    print(f"   - 总行业数: {result.total_industries}")
    print(f"   - 有效行业数(有股票): {result.industries_with_stocks}")
    print(f"   - 最低要求: {result.min_required}")
    print(f"   - 目标上限: {result.max_target}")
    print()
    
    # 各行业详情
    print(f"🏭 各行业股票数量:")
    sorted_industries = sorted(
        result.industry_details.items(),
        key=lambda x: x[1],
        reverse=True
    )
    
    total_stocks = sum(result.industry_details.values())
    for industry, count in sorted_industries:
        if count > 0:
            pct = count / total_stocks * 100 if total_stocks > 0 else 0
            bar = "█" * min(int(count / 2), 20)
            print(f"   {industry}: {count}只 ({pct:.1f}%) {bar}")
        else:
            print(f"   {industry}: 0只 (空)")
    
    print()
    print(f"   总计: {total_stocks}只股票")
    print()
    
    # 警告
    if result.warnings:
        print("⚠️ 警告:")
        for warning in result.warnings:
            print(f"   - {warning}")
        print()
    
    # 建议
    if result.suggestions:
        print("💡 建议:")
        for suggestion in result.suggestions:
            print(f"   - {suggestion}")
        print()
    
    print("=" * 60)


def get_industry_coverage_summary() -> Dict[str, any]:
    """
    获取行业覆盖摘要
    
    Returns:
        Dict: 包含行业覆盖信息的字典
    """
    result = validate_industry_coverage()
    
    return {
        'passed': result.passed,
        'industries_with_stocks': result.industries_with_stocks,
        'min_required': result.min_required,
        'max_target': result.max_target,
        'industry_details': result.industry_details,
        'total_stocks': sum(result.industry_details.values()),
        'coverage_rate': result.industries_with_stocks / result.min_required * 100
    }


if __name__ == "__main__":
    print("\n🔍 开始验证科技股池行业覆盖...\n")
    
    # 执行验证
    result = validate_industry_coverage(
        min_industries=8,
        max_industries=10,
        min_stocks_per_industry=5
    )
    
    # 打印报告
    print_validation_report(result)
    
    # 返回退出码
    sys.exit(0 if result.passed else 1)
