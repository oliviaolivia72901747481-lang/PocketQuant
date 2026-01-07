#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V6评分系统 - 科技股池筛选脚本

使用V6评分系统对100只科技股进行评分，输出评分前15的股票
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from config.tech_stock_pool import get_all_tech_stocks, get_stock_name
from core.overnight_picker.scorer_v6 import ScorerV6


def main():
    # 获取科技股池
    tech_stocks = get_all_tech_stocks()
    print(f'科技股池: {len(tech_stocks)}只股票')
    
    # 初始化V6评分器
    scorer = ScorerV6()
    
    # 对每只股票评分
    results = []
    data_path = 'data/processed'
    
    for code in tech_stocks:
        file_path = os.path.join(data_path, f'{code}.csv')
        if not os.path.exists(file_path):
            continue
        
        try:
            df = pd.read_csv(file_path)
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').reset_index(drop=True)
            
            # 获取最新数据
            if len(df) < 20:
                continue
            
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            
            # 计算技术指标
            df['ma5'] = df['close'].rolling(5).mean()
            df['ma10'] = df['close'].rolling(10).mean()
            df['ma20'] = df['close'].rolling(20).mean()
            df['ma60'] = df['close'].rolling(60).mean()
            df['ma5_vol'] = df['volume'].rolling(5).mean()
            
            latest_row = df.iloc[-1]
            
            # 构建股票数据
            stock_data = {
                'code': code,
                'name': get_stock_name(code),
                'open': latest['open'],
                'high': latest['high'],
                'low': latest['low'],
                'close': latest['close'],
                'prev_close': prev['close'],
                'volume': latest['volume'],
                'ma5': latest_row['ma5'],
                'ma10': latest_row['ma10'],
                'ma20': latest_row['ma20'],
                'ma60': latest_row['ma60'] if pd.notna(latest_row['ma60']) else latest_row['ma20'],
                'ma5_vol': latest_row['ma5_vol'],
            }
            
            # 评分
            score, details = scorer.score_stock(stock_data)
            results.append({
                'code': code,
                'name': get_stock_name(code),
                'score': score,
                'close': latest['close'],
                'change_pct': (latest['close'] - prev['close']) / prev['close'] * 100,
                'details': details,
            })
        except Exception as e:
            pass
    
    # 按评分排序
    results.sort(key=lambda x: x['score'], reverse=True)
    
    # 输出前15只
    print()
    print('=' * 80)
    print('📊 V6评分系统 - 科技股池评分前15')
    print('=' * 80)
    print(f"{'排名':<4} {'代码':<8} {'名称':<12} {'评分':<6} {'收盘价':<10} {'涨跌幅':<10}")
    print('-' * 80)
    
    for i, r in enumerate(results[:15], 1):
        print(f"{i:<4} {r['code']:<8} {r['name']:<12} {r['score']:<6.0f} {r['close']:<10.2f} {r['change_pct']:+.2f}%")
    
    print('-' * 80)
    print(f'共筛选 {len(results)} 只股票，显示评分前15')
    
    # 输出详细评分
    print()
    print('=' * 80)
    print('📋 评分详情 (前5只)')
    print('=' * 80)
    
    for i, r in enumerate(results[:5], 1):
        print(f"\n{i}. {r['code']} {r['name']} - 总分: {r['score']:.0f}")
        details = r['details']
        for dim, info in details.items():
            if isinstance(info, dict) and 'score' in info:
                print(f"   - {dim}: {info['score']}/{info.get('max_score', 20)}分")


if __name__ == '__main__':
    main()
