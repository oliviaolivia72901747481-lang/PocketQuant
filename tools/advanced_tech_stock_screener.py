"""
基于高级评分系统的科技股筛选器
使用精密量化评分模型筛选最优科技股
"""

import sys
sys.path.insert(0, '.')

import akshare as ak
import pandas as pd
import numpy as np
from core.advanced_scoring_system import AdvancedScoringSystem, BALANCED_WEIGHTS
from config.tech_stock_pool import TECH_STOCK_POOL

def advanced_tech_stock_screening():
    """使用高级评分系统筛选科技股"""
    
    print("=" * 90)
    print("高级科技股筛选系统 - 基于精密量化评分")
    print("=" * 90)
    
    # 初始化高级评分系统
    scorer = AdvancedScoringSystem(BALANCED_WEIGHTS)
    
    # 获取科技股池
    tech_codes = set()
    tech_stock_info = {}
    for sector, stocks in TECH_STOCK_POOL.items():
        for stock in stocks:
            tech_codes.add(stock['code'])
            tech_stock_info[stock['code']] = {'name': stock['name'], 'sector': sector}
    
    print(f"科技股池: {len(tech_codes)} 只股票")
    
    # 获取实时行情数据
    print("\n正在获取实时行情数据...")
    df = ak.stock_zh_a_spot_em()
    
    # 数据预处理
    numeric_columns = ['涨跌幅', '换手率', '成交量', '量比', '市盈率-动态', '最新价', '总市值']
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # 筛选科技股
    tech_df = df[df['代码'].isin(tech_codes)].copy()
    print(f"科技股池中有行情数据: {len(tech_df)} 只")
    
    # 基础筛选条件
    filtered = tech_df[
        (tech_df['涨跌幅'] >= 0.5) & (tech_df['涨跌幅'] <= 10) &  # 放宽涨幅范围
        (tech_df['换手率'] > 0.5) &  # 放宽换手率要求
        (tech_df['成交量'] > 10000) &  # 降低成交量要求
        (~tech_df['名称'].str.contains('ST|退', na=False)) &
        (tech_df['最新价'] > 0)
    ].copy()
    
    print(f"基础筛选后: {len(filtered)} 只")
    
    if len(filtered) == 0:
        print("没有符合基础条件的科技股")
        return
    
    # 使用高级评分系统计算得分
    print("\n正在计算高级评分...")
    
    results = []
    for idx, row in filtered.iterrows():
        try:
            # 准备评分参数
            change_pct = row['涨跌幅']
            turnover_rate = row['换手率']
            volume_ratio = row['量比'] if pd.notna(row['量比']) else 1.0
            pe_ratio = row['市盈率-动态'] if pd.notna(row['市盈率-动态']) else 50.0
            market_cap = row['总市值'] / 1e8 if pd.notna(row['总市值']) else 100  # 转换为亿元
            
            # 计算高级评分
            score_result = scorer.calculate_comprehensive_score(
                change_pct=change_pct,
                turnover_rate=turnover_rate,
                volume_ratio=volume_ratio,
                pe_ratio=pe_ratio,
                market_cap=market_cap
            )
            
            # 添加股票信息
            stock_info = tech_stock_info.get(row['代码'], {})
            
            result = {
                'code': row['代码'],
                'name': row['名称'],
                'sector': stock_info.get('sector', '未知'),
                'price': row['最新价'],
                'change_pct': change_pct,
                'turnover_rate': turnover_rate,
                'volume_ratio': volume_ratio,
                'pe_ratio': pe_ratio,
                'market_cap': market_cap,
                'volume': row['成交量'],
                'amount': row['成交额'],
                **score_result
            }
            
            results.append(result)
            
        except Exception as e:
            print(f"计算 {row['代码']} {row['名称']} 评分时出错: {e}")
            continue
    
    if not results:
        print("没有成功计算评分的股票")
        return
    
    # 转换为DataFrame并排序
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('comprehensive_score', ascending=False)
    
    # 显示结果
    print(f"\n高级评分结果 (共 {len(results_df)} 只)")
    print("=" * 120)
    
    # 显示TOP20
    top_stocks = results_df.head(20)
    
    print("排名 | 代码   | 名称     | 板块   | 价格   | 涨幅  | 换手率 | 量比  | PE   | 综合得分 | 等级")
    print("-" * 120)
    
    for i, (_, row) in enumerate(top_stocks.iterrows(), 1):
        pe_str = f"{row['pe_ratio']:.1f}" if row['pe_ratio'] > 0 else "亏损"
        vol_ratio_str = f"{row['volume_ratio']:.2f}" if pd.notna(row['volume_ratio']) else "N/A"
        
        print(f"{i:2d}   | {row['code']} | {row['name'][:6]:6s} | {row['sector'][:4]:4s} | "
              f"{row['price']:6.2f} | {row['change_pct']:4.1f}% | {row['turnover_rate']:5.2f}% | "
              f"{vol_ratio_str:4s} | {pe_str:4s} | {row['comprehensive_score']:7.2f} | {row['quality_grade']:2s}")
    
    # 详细分析TOP5
    print(f"\n\nTOP5 详细评分分析")
    print("=" * 120)
    
    top5 = results_df.head(5)
    for i, (_, row) in enumerate(top5.iterrows(), 1):
        print(f"\n{i}. {row['code']} {row['name']} [{row['sector']}]")
        print(f"   综合得分: {row['comprehensive_score']:.2f} (等级: {row['quality_grade']})")
        print(f"   ├─ 动量得分: {row['momentum_score']:.2f}/35.0 ({row['details']['momentum']['category']})")
        print(f"   ├─ 流动性得分: {row['liquidity_score']:.2f}/25.0 ({row['details']['liquidity']['category']})")
        print(f"   ├─ 成交量得分: {row['volume_score']:.2f}/25.0 ({row['details']['volume']['category']})")
        print(f"   └─ 估值得分: {row['valuation_score']:.2f}/15.0 ({row['details']['valuation']['category']})")
        
        # 显示关键指标
        print(f"   关键指标: 价格{row['price']:.2f}元, 涨幅{row['change_pct']:.2f}%, "
              f"换手{row['turnover_rate']:.2f}%, 量比{row['volume_ratio']:.2f}, PE{row['pe_ratio']:.1f}")
    
    # 等级分布统计
    print(f"\n\n质量等级分布")
    print("-" * 40)
    grade_counts = results_df['quality_grade'].value_counts().sort_index(ascending=False)
    for grade, count in grade_counts.items():
        percentage = count / len(results_df) * 100
        print(f"{grade:2s} 级: {count:2d} 只 ({percentage:4.1f}%)")
    
    # 板块分布统计
    print(f"\n板块表现统计")
    print("-" * 50)
    sector_stats = results_df.groupby('sector').agg({
        'comprehensive_score': ['count', 'mean', 'max'],
        'quality_grade': lambda x: (x.isin(['S+', 'S', 'A+'])).sum()
    }).round(2)
    
    sector_stats.columns = ['数量', '平均得分', '最高得分', '优质股数量']
    sector_stats = sector_stats.sort_values('平均得分', ascending=False)
    print(sector_stats.to_string())
    
    return results_df

if __name__ == "__main__":
    results = advanced_tech_stock_screening()
    
    if results is not None:
        print(f"\n" + "=" * 90)
        print("筛选完成！高级评分系统已识别出最具投资价值的科技股")
        print("建议重点关注S+和S级股票，它们在多个维度都表现优异")
        print("=" * 90)