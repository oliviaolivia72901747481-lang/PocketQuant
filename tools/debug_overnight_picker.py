#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""调试隔夜选股器"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.overnight_picker.picker import OvernightStockPicker
from config.tech_stock_pool import get_all_tech_stocks

def main():
    # 创建选股器
    picker = OvernightStockPicker(
        total_capital=70000,
        max_recommendations=15,
        min_score=30,
        stock_pool=get_all_tech_stocks(),
    )
    
    # 分析大盘环境
    market_env = picker.analyze_market_environment()
    print('=' * 60)
    print('大盘环境分析:')
    print(f"  环境: {market_env['env']}")
    print(f"  描述: {market_env['description']}")
    print(f"  是否建议空仓: {market_env['should_empty']}")
    
    # 检查是否可交易
    is_tradable, reason = picker.is_market_tradable(market_env)
    print(f"  是否可交易: {is_tradable}")
    print(f"  原因: {reason}")
    
    # 对所有股票评分
    print()
    print('=' * 60)
    print('开始评分...')
    scored = picker._score_all_stocks(hot_topics=[])
    print(f'评分完成: {len(scored)}只股票')
    
    # 按分数排序
    scored.sort(key=lambda x: x['score'], reverse=True)
    
    # 显示前15只
    print()
    print('=' * 60)
    print('评分前15只股票:')
    print(f"{'排名':<4} {'代码':<8} {'名称':<12} {'评分':<6}")
    print('-' * 40)
    for i, s in enumerate(scored[:15], 1):
        print(f"{i:<4} {s['code']:<8} {s['name']:<12} {s['score']:<6.0f}")
    
    # 统计分数分布
    print()
    print('=' * 60)
    print('分数分布:')
    for threshold in [70, 60, 50, 40, 30, 20]:
        count = len([s for s in scored if s['score'] >= threshold])
        print(f"  >= {threshold}分: {count}只")
    
    # 筛选符合条件的股票
    min_score = 30
    qualified = [s for s in scored if s['score'] >= min_score]
    print()
    print(f'符合条件 (>={min_score}分): {len(qualified)}只')

if __name__ == '__main__':
    main()
