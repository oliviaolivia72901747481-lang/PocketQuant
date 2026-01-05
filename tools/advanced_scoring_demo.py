"""
高级评分系统演示和测试
展示精密量化评分的优势和细节
"""

import sys
sys.path.insert(0, '.')

from core.advanced_scoring_system import (
    AdvancedScoringSystem, 
    CONSERVATIVE_WEIGHTS, 
    AGGRESSIVE_WEIGHTS, 
    BALANCED_WEIGHTS
)
import pandas as pd
import numpy as np

def demo_scoring_precision():
    """演示评分系统的精密性"""
    
    print("=" * 80)
    print("高级股票评分系统 - 精密量化演示")
    print("=" * 80)
    
    # 创建不同风格的评分系统
    balanced_scorer = AdvancedScoringSystem(BALANCED_WEIGHTS)
    conservative_scorer = AdvancedScoringSystem(CONSERVATIVE_WEIGHTS)
    aggressive_scorer = AdvancedScoringSystem(AGGRESSIVE_WEIGHTS)
    
    # 测试案例 - 不同类型的股票
    test_cases = [
        {
            'name': '立讯精密 (实际数据)',
            'change_pct': 3.24,
            'turnover_rate': 2.19,
            'volume_ratio': 1.77,
            'pe_ratio': 27.8,
            'market_cap': 400,  # 400亿市值
        },
        {
            'name': '理想成长股',
            'change_pct': 4.5,
            'turnover_rate': 3.5,
            'volume_ratio': 2.2,
            'pe_ratio': 25.0,
            'market_cap': 500,
        },
        {
            'name': '价值股',
            'change_pct': 2.1,
            'turnover_rate': 1.8,
            'volume_ratio': 1.3,
            'pe_ratio': 12.5,
            'market_cap': 800,
        },
        {
            'name': '投机股',
            'change_pct': 7.8,
            'turnover_rate': 15.2,
            'volume_ratio': 6.5,
            'pe_ratio': 85.0,
            'market_cap': 150,
        },
        {
            'name': '问题股',
            'change_pct': 1.2,
            'turnover_rate': 0.8,
            'volume_ratio': 0.6,
            'pe_ratio': -5.0,  # 亏损
            'market_cap': 80,
        }
    ]
    
    print("\n1. 平衡型评分系统分析")
    print("-" * 60)
    
    for case in test_cases:
        print(f"\n【{case['name']}】")
        result = balanced_scorer.calculate_comprehensive_score(**case)
        
        print(f"综合得分: {result['comprehensive_score']:.2f} (等级: {result['quality_grade']})")
        print(f"  ├─ 动量得分: {result['momentum_score']:.2f}/35 ({result['details']['momentum']['category']})")
        print(f"  ├─ 流动性得分: {result['liquidity_score']:.2f}/25 ({result['details']['liquidity']['category']})")
        print(f"  ├─ 成交量得分: {result['volume_score']:.2f}/25 ({result['details']['volume']['category']})")
        print(f"  └─ 估值得分: {result['valuation_score']:.2f}/15 ({result['details']['valuation']['category']})")
    
    print("\n\n2. 不同风格评分系统对比")
    print("-" * 60)
    
    # 选择立讯精密进行详细对比
    test_stock = test_cases[0]
    print(f"\n以【{test_stock['name']}】为例:")
    
    balanced_result = balanced_scorer.calculate_comprehensive_score(**test_stock)
    conservative_result = conservative_scorer.calculate_comprehensive_score(**test_stock)
    aggressive_result = aggressive_scorer.calculate_comprehensive_score(**test_stock)
    
    comparison_df = pd.DataFrame({
        '评分维度': ['动量得分', '流动性得分', '成交量得分', '估值得分', '综合得分', '质量等级'],
        '平衡型': [
            f"{balanced_result['momentum_score']:.2f}",
            f"{balanced_result['liquidity_score']:.2f}",
            f"{balanced_result['volume_score']:.2f}",
            f"{balanced_result['valuation_score']:.2f}",
            f"{balanced_result['comprehensive_score']:.2f}",
            balanced_result['quality_grade']
        ],
        '保守型': [
            f"{conservative_result['momentum_score']:.2f}",
            f"{conservative_result['liquidity_score']:.2f}",
            f"{conservative_result['volume_score']:.2f}",
            f"{conservative_result['valuation_score']:.2f}",
            f"{conservative_result['comprehensive_score']:.2f}",
            conservative_result['quality_grade']
        ],
        '激进型': [
            f"{aggressive_result['momentum_score']:.2f}",
            f"{aggressive_result['liquidity_score']:.2f}",
            f"{aggressive_result['volume_score']:.2f}",
            f"{aggressive_result['valuation_score']:.2f}",
            f"{aggressive_result['comprehensive_score']:.2f}",
            aggressive_result['quality_grade']
        ]
    })
    
    print(comparison_df.to_string(index=False))
    
    print("\n\n3. 评分系统精密性展示")
    print("-" * 60)
    
    # 展示微小变化对得分的影响
    base_case = test_cases[1].copy()  # 理想成长股
    
    print(f"\n基准股票: {base_case['name']}")
    base_result = balanced_scorer.calculate_comprehensive_score(**base_case)
    print(f"基准得分: {base_result['comprehensive_score']:.2f}")
    
    # 测试涨幅的细微变化
    print(f"\n涨幅敏感性分析:")
    for delta in [-0.5, -0.2, 0, 0.2, 0.5]:
        modified_case = base_case.copy()
        modified_case['change_pct'] += delta
        result = balanced_scorer.calculate_comprehensive_score(**modified_case)
        print(f"  涨幅 {modified_case['change_pct']:.1f}%: 得分 {result['comprehensive_score']:.2f} (变化: {result['comprehensive_score'] - base_result['comprehensive_score']:+.2f})")
    
    # 测试PE的细微变化
    print(f"\nPE敏感性分析:")
    for delta in [-5, -2, 0, 2, 5]:
        modified_case = base_case.copy()
        modified_case['pe_ratio'] += delta
        result = balanced_scorer.calculate_comprehensive_score(**modified_case)
        print(f"  PE {modified_case['pe_ratio']:.1f}: 得分 {result['comprehensive_score']:.2f} (变化: {result['comprehensive_score'] - base_result['comprehensive_score']:+.2f})")

def demonstrate_advanced_features():
    """演示高级功能"""
    
    print("\n\n4. 高级功能演示")
    print("-" * 60)
    
    scorer = AdvancedScoringSystem()
    
    # 演示量价配合分析
    print("\n量价配合度分析:")
    volume_price_cases = [
        (2.5, 4.0, "上涨放量"),
        (0.8, 3.5, "上涨缩量"),
        (3.2, -2.0, "下跌放量"),
        (0.6, -1.5, "下跌缩量"),
    ]
    
    for vol_ratio, price_change, desc in volume_price_cases:
        synergy = scorer._calculate_volume_price_synergy(vol_ratio, price_change)
        print(f"  {desc}: 量比{vol_ratio}, 涨幅{price_change:+.1f}% → 配合度{synergy:.2f}")
    
    # 演示行业相对估值
    print(f"\n行业相对估值分析:")
    pe_cases = [20, 25, 30, 35]
    sector_avg_pe = 28
    
    for pe in pe_cases:
        score, details = scorer.valuation_score(pe, sector_avg_pe)
        relative_pe = details.get('relative_pe', 0)
        print(f"  PE {pe} (行业均值{sector_avg_pe}): 相对PE{relative_pe:.2f}, 得分{score:.2f}")

if __name__ == "__main__":
    demo_scoring_precision()
    demonstrate_advanced_features()
    
    print("\n" + "=" * 80)
    print("评分系统优势总结:")
    print("1. 非线性评分函数 - 更符合市场实际")
    print("2. 多维度风险调整 - 考虑波动率、流动性等")
    print("3. 动态权重配置 - 适应不同投资风格")
    print("4. 精密量化分析 - 微小差异也能体现")
    print("5. 理论基础扎实 - 基于现代金融理论")
    print("=" * 80)