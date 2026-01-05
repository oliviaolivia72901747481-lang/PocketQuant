#!/usr/bin/env python3
"""
科技股快速筛选工具 - 适合明天投资

基于实时行情数据快速筛选，无需获取历史数据
运行速度快，适合初学者使用

作者: Kiro
日期: 2026-01-05
"""

import sys
sys.path.insert(0, '.')

import akshare as ak
import pandas as pd
from datetime import datetime
from config.tech_stock_pool import get_all_tech_stocks, get_stock_name, get_stock_sector


def quick_screen():
    """快速筛选科技股"""
    print('=' * 60)
    print('🚀 科技股快速筛选 - 适合明天投资')
    print(f'📅 筛选时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print('=' * 60)

    # 获取股票池
    stock_codes = get_all_tech_stocks()
    print(f'\n📊 股票池: {len(stock_codes)} 只科技股')

    # 获取实时行情
    print('\n🔍 获取实时行情数据...')
    try:
        df = ak.stock_zh_a_spot_em()
        df = df[df['代码'].isin(stock_codes)]
        print(f'✅ 获取到 {len(df)} 只股票的实时数据')
    except Exception as e:
        print(f'❌ 获取数据失败: {e}')
        return

    # 筛选条件
    candidates = []
    for _, row in df.iterrows():
        try:
            code = row['代码']
            name = row['名称']
            price = float(row['最新价'])
            change_pct = float(row['涨跌幅'])
            turnover_rate = float(row['换手率'])
            volume_ratio = float(row['量比']) if pd.notna(row['量比']) else 0
            pe = float(row['市盈率-动态']) if pd.notna(row['市盈率-动态']) and row['市盈率-动态'] > 0 else 0
            market_cap = float(row['总市值']) / 100000000  # 亿元
            
            # 排除科创板(688)和创业板(300)
            if code.startswith('688') or code.startswith('300'):
                continue
            
            # 基础筛选条件
            if price > 200 or price < 5:  # 价格5-200元
                continue
            if turnover_rate < 1:  # 换手率>1%
                continue
            
            # 计算综合得分
            score = 0
            reasons = []
            
            # 涨幅适中 (0-3%最佳)
            if 0 <= change_pct <= 3:
                score += 25
                reasons.append('涨幅适中')
            elif -2 <= change_pct < 0:
                score += 15
                reasons.append('小幅回调')
            
            # 量比 (1.2-3最佳)
            if 1.2 <= volume_ratio <= 3:
                score += 25
                reasons.append('量能活跃')
            elif volume_ratio > 3:
                score += 10
                reasons.append('放量明显')
            
            # 换手率 (2-8%最佳)
            if 2 <= turnover_rate <= 8:
                score += 20
                reasons.append('换手健康')
            elif turnover_rate > 8:
                score += 10
                reasons.append('交投活跃')
            
            # 市值 (100-1000亿最佳)
            if 100 <= market_cap <= 1000:
                score += 15
                reasons.append('市值适中')
            elif 50 <= market_cap < 100:
                score += 10
                reasons.append('中小市值')
            
            # PE合理 (20-60最佳)
            if 20 <= pe <= 60:
                score += 15
                reasons.append('估值合理')
            
            if score >= 40:  # 至少40分
                candidates.append({
                    'code': code,
                    'name': get_stock_name(code),
                    'sector': get_stock_sector(code),
                    'price': price,
                    'change_pct': change_pct,
                    'turnover_rate': turnover_rate,
                    'volume_ratio': volume_ratio,
                    'pe': pe,
                    'market_cap': market_cap,
                    'score': score,
                    'reasons': reasons
                })
        except:
            continue

    # 按得分排序
    candidates.sort(key=lambda x: x['score'], reverse=True)

    print('\n' + '=' * 60)
    print('🎯 推荐明天关注的科技股 TOP 5')
    print('=' * 60)

    if not candidates:
        print('\n⚠️ 当前没有符合条件的股票')
        print('可能原因:')
        print('  1. 今天是非交易日，数据可能不是最新的')
        print('  2. 市场整体表现较弱')
        print('  3. 请在交易日运行此工具获取最新结果')
    else:
        top5 = candidates[:5]
        for i, stock in enumerate(top5, 1):
            print(f'\n【{i}】{stock["code"]} {stock["name"]}')
            print(f'    行业: {stock["sector"]}')
            print(f'    现价: {stock["price"]:.2f}元  涨跌: {stock["change_pct"]:+.2f}%')
            print(f'    换手率: {stock["turnover_rate"]:.2f}%  量比: {stock["volume_ratio"]:.2f}')
            print(f'    市值: {stock["market_cap"]:.0f}亿  PE: {stock["pe"]:.1f}')
            print(f'    综合得分: {stock["score"]}/100')
            print(f'    推荐理由: {" | ".join(stock["reasons"])}')

        print('\n' + '-' * 60)
        print('📈 筛选汇总')
        print(f'  符合条件股票: {len(candidates)} 只')
        
        # 按行业统计
        sector_count = {}
        for c in candidates:
            sector = c['sector'] or '未知'
            sector_count[sector] = sector_count.get(sector, 0) + 1
        print(f'  行业分布: {sector_count}')

    print('\n' + '=' * 60)
    print('💡 投资建议 (新手必读)')
    print('=' * 60)
    print('  1. 建议在开盘后观察30分钟再决定是否买入')
    print('  2. 单只股票仓位不超过总资金的10%')
    print('  3. 设置止损位: 买入价 × 0.954 (跌4.6%止损)')
    print('  4. 目标收益: 5-8%可考虑分批止盈')
    print('  5. 关注大盘走势，大盘弱势时谨慎操作')
    print('=' * 60)
    
    return candidates


if __name__ == "__main__":
    quick_screen()
