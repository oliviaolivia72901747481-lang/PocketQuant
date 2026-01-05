"""
今日信号筛选脚本
基于v11.4g策略筛选综合条件最佳的股票
"""
import akshare as ak
import pandas as pd
import numpy as np

print('=== 获取A股实时行情数据 ===')
df = ak.stock_zh_a_spot_em()
print(f'总股票数: {len(df)}')

# 数据类型转换
df['涨跌幅'] = pd.to_numeric(df['涨跌幅'], errors='coerce')
df['换手率'] = pd.to_numeric(df['换手率'], errors='coerce')
df['成交量'] = pd.to_numeric(df['成交量'], errors='coerce')
df['量比'] = pd.to_numeric(df['量比'], errors='coerce')
df['市盈率-动态'] = pd.to_numeric(df['市盈率-动态'], errors='coerce')
df['最新价'] = pd.to_numeric(df['最新价'], errors='coerce')

# v11.4g策略筛选条件
filtered = df[
    (df['涨跌幅'] >= 1) & (df['涨跌幅'] <= 8) &
    (df['换手率'] > 1) &
    (df['成交量'] > 50000) &
    (~df['名称'].str.contains('ST|退', na=False)) &
    (df['最新价'] > 0)
].copy()

print(f'基础筛选后: {len(filtered)}只')

# 综合评分函数
def calc_score(row):
    score = 0
    
    # 涨幅得分 (3-6%最佳, 30分)
    change = row['涨跌幅']
    if 3 <= change <= 6:
        score += 30
    elif 2 <= change < 3 or 6 < change <= 7:
        score += 25
    elif 1 <= change < 2 or 7 < change <= 8:
        score += 20
    
    # 换手率得分 (2-8%最佳, 25分)
    turnover = row['换手率']
    if 2 <= turnover <= 8:
        score += 25
    elif 1 < turnover < 2 or 8 < turnover <= 15:
        score += 20
    elif turnover > 15:
        score += 10
    
    # 量比得分 (1.5-3最佳, 25分)
    vol_ratio = row['量比'] if pd.notna(row['量比']) else 1
    if 1.5 <= vol_ratio <= 3:
        score += 25
    elif 1.1 <= vol_ratio < 1.5 or 3 < vol_ratio <= 5:
        score += 20
    elif vol_ratio > 5:
        score += 10
    
    # PE得分 (0-50最佳, 20分)
    pe = row['市盈率-动态'] if pd.notna(row['市盈率-动态']) else 100
    if 0 < pe <= 30:
        score += 20
    elif 30 < pe <= 50:
        score += 15
    elif 50 < pe <= 100:
        score += 10
    elif pe < 0:
        score += 5
    
    return score

filtered['综合得分'] = filtered.apply(calc_score, axis=1)

# 按综合得分排序，取前10
top10 = filtered.nlargest(10, '综合得分')

print('\n' + '=' * 80)
print('今日综合条件最佳TOP10 (2026-01-05)')
print('=' * 80)

for i, (idx, row) in enumerate(top10.iterrows(), 1):
    pe_str = f"{row['市盈率-动态']:.1f}" if pd.notna(row['市盈率-动态']) else 'N/A'
    vol_ratio = f"{row['量比']:.2f}" if pd.notna(row['量比']) else 'N/A'
    print(f"{i:2d}. {row['代码']} {row['名称'][:8]:8s} | 价格:{row['最新价']:7.2f} | 涨幅:{row['涨跌幅']:5.2f}% | 换手:{row['换手率']:5.2f}% | 量比:{vol_ratio:5s} | PE:{pe_str:6s} | 得分:{row['综合得分']}")

print('\n' + '=' * 80)
print('详细数据')
print('=' * 80)
detail_cols = ['代码', '名称', '最新价', '涨跌幅', '换手率', '量比', '成交量', '成交额', '市盈率-动态', '综合得分']
print(top10[detail_cols].to_string(index=False))
