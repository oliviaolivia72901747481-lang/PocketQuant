"""
筛选综合得分100分的科技股
基于科技股池和v11.4g策略
"""
import akshare as ak
import pandas as pd
import sys
sys.path.insert(0, '.')

from config.tech_stock_pool import TECH_STOCK_POOL

# 获取科技股池所有代码
tech_codes = set()
tech_stock_info = {}
for sector, stocks in TECH_STOCK_POOL.items():
    for stock in stocks:
        tech_codes.add(stock['code'])
        tech_stock_info[stock['code']] = {'name': stock['name'], 'sector': sector}

print(f'科技股池共 {len(tech_codes)} 只股票')
print('板块分布:', {k: len(v) for k, v in TECH_STOCK_POOL.items()})

print('\n=== 获取A股实时行情数据 ===')
df = ak.stock_zh_a_spot_em()

# 数据类型转换
df['涨跌幅'] = pd.to_numeric(df['涨跌幅'], errors='coerce')
df['换手率'] = pd.to_numeric(df['换手率'], errors='coerce')
df['成交量'] = pd.to_numeric(df['成交量'], errors='coerce')
df['量比'] = pd.to_numeric(df['量比'], errors='coerce')
df['市盈率-动态'] = pd.to_numeric(df['市盈率-动态'], errors='coerce')
df['最新价'] = pd.to_numeric(df['最新价'], errors='coerce')

# 筛选科技股
tech_df = df[df['代码'].isin(tech_codes)].copy()
print(f'科技股池中有行情数据: {len(tech_df)} 只')

# v11.4g策略筛选条件
filtered = tech_df[
    (tech_df['涨跌幅'] >= 1) & (tech_df['涨跌幅'] <= 8) &
    (tech_df['换手率'] > 1) &
    (tech_df['成交量'] > 50000) &
    (~tech_df['名称'].str.contains('ST|退', na=False)) &
    (tech_df['最新价'] > 0)
].copy()

print(f'基础筛选后: {len(filtered)} 只')

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

# 添加板块信息
filtered['板块'] = filtered['代码'].apply(lambda x: tech_stock_info.get(x, {}).get('sector', '未知'))

# 筛选100分的股票
score_100 = filtered[filtered['综合得分'] == 100].copy()
score_100 = score_100.sort_values('涨跌幅', ascending=False)

print('\n' + '=' * 90)
print(f'综合得分100分的科技股 (共 {len(score_100)} 只)')
print('=' * 90)

if len(score_100) > 0:
    for i, (idx, row) in enumerate(score_100.iterrows(), 1):
        pe_str = f"{row['市盈率-动态']:.1f}" if pd.notna(row['市盈率-动态']) else 'N/A'
        vol_ratio = f"{row['量比']:.2f}" if pd.notna(row['量比']) else 'N/A'
        print(f"{i:2d}. {row['代码']} {row['名称'][:8]:8s} [{row['板块']:6s}] | 价格:{row['最新价']:7.2f} | 涨幅:{row['涨跌幅']:5.2f}% | 换手:{row['换手率']:5.2f}% | 量比:{vol_ratio:5s} | PE:{pe_str:6s}")
    
    print('\n' + '=' * 90)
    print('详细数据')
    print('=' * 90)
    detail_cols = ['代码', '名称', '板块', '最新价', '涨跌幅', '换手率', '量比', '成交量', '市盈率-动态', '综合得分']
    print(score_100[detail_cols].to_string(index=False))
else:
    print('今日没有综合得分100分的科技股')
    
    # 显示得分最高的科技股
    if len(filtered) > 0:
        top_scores = filtered.nlargest(10, '综合得分')
        print('\n得分最高的科技股 TOP10:')
        for i, (idx, row) in enumerate(top_scores.iterrows(), 1):
            pe_str = f"{row['市盈率-动态']:.1f}" if pd.notna(row['市盈率-动态']) else 'N/A'
            vol_ratio = f"{row['量比']:.2f}" if pd.notna(row['量比']) else 'N/A'
            print(f"{i:2d}. {row['代码']} {row['名称'][:8]:8s} [{row['板块']:6s}] | 涨幅:{row['涨跌幅']:5.2f}% | 换手:{row['换手率']:5.2f}% | 量比:{vol_ratio:5s} | PE:{pe_str:6s} | 得分:{row['综合得分']}")
