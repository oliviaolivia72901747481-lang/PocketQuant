"""
激进型股票筛选器 - 适用于强势上涨市场
使用激进型权重配置的高级评分系统
"""

import sys
sys.path.insert(0, '.')

import akshare as ak
import pandas as pd
import numpy as np
from core.advanced_scoring_system import AdvancedScoringSystem, AGGRESSIVE_WEIGHTS
from config.tech_stock_pool import TECH_STOCK_POOL

def aggressive_stock_screening():
    """使用激进型策略筛选最适合投资的股票"""
    
    print("=" * 100)
    print("激进型股票筛选系统 - 强势市场专用")
    print("市场环境: 强势上涨 | 策略类型: 激进型 | 动量权重: 45%")
    print("=" * 100)
    
    # 初始化激进型评分系统
    scorer = AdvancedScoringSystem(AGGRESSIVE_WEIGHTS)
    
    # 获取科技股池
    tech_codes = set()
    tech_stock_info = {}
    for sector, stocks in TECH_STOCK_POOL.items():
        for stock in stocks:
            tech_codes.add(stock['code'])
            tech_stock_info[stock['code']] = {'name': stock['name'], 'sector': sector}
    
    print(f"\n科技股池: {len(tech_codes)} 只股票")
    
    # 获取实时行情数据
    print("正在获取实时行情数据...")
    df = ak.stock_zh_a_spot_em()
    
    # 数据预处理
    numeric_columns = ['涨跌幅', '换手率', '成交量', '量比', '市盈率-动态', '最新价', '总市值', '成交额']
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # 筛选科技股
    tech_df = df[df['代码'].isin(tech_codes)].copy()
    print(f"科技股池中有行情数据: {len(tech_df)} 只")
    
    # 激进型筛选条件 - 更宽松以捕捉更多机会
    filtered = tech_df[
        (tech_df['涨跌幅'] >= 0) & (tech_df['涨跌幅'] <= 10) &
        (tech_df['换手率'] > 0.3) &
        (tech_df['成交量'] > 5000) &
        (~tech_df['名称'].str.contains('ST|退', na=False)) &
        (tech_df['最新价'] > 0)
    ].copy()
    
    print(f"基础筛选后: {len(filtered)} 只")
    
    if len(filtered) == 0:
        print("没有符合条件的科技股")
        return
    
    # 使用激进型评分系统计算得分
    print("正在计算激进型评分...")
    
    results = []
    for idx, row in filtered.iterrows():
        try:
            change_pct = row['涨跌幅']
            turnover_rate = row['换手率']
            volume_ratio = row['量比'] if pd.notna(row['量比']) else 1.0
            pe_ratio = row['市盈率-动态'] if pd.notna(row['市盈率-动态']) else 50.0
            market_cap = row['总市值'] / 1e8 if pd.notna(row['总市值']) else 100
            
            score_result = scorer.calculate_comprehensive_score(
                change_pct=change_pct,
                turnover_rate=turnover_rate,
                volume_ratio=volume_ratio,
                pe_ratio=pe_ratio,
                market_cap=market_cap
            )
            
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
                'amount': row['成交额'] / 1e8 if pd.notna(row['成交额']) else 0,
                **score_result
            }
            
            results.append(result)
            
        except Exception as e:
            continue
    
    if not results:
        print("没有成功计算评分的股票")
        return
    
    # 转换为DataFrame并排序
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('comprehensive_score', ascending=False)
    
    # 筛选S级和A级股票
    top_stocks = results_df[results_df['quality_grade'].isin(['S+', 'S', 'A+', 'A'])].head(10)
    
    print(f"\n{'='*100}")
    print(f"最适合投资的科技股 TOP10 (S/A级)")
    print(f"{'='*100}")
    
    print("\n排名 | 代码   | 名称     | 板块   | 价格   | 涨幅  | 换手率 | 量比  | 成交额(亿) | 得分  | 等级")
    print("-" * 100)
    
    for i, (_, row) in enumerate(top_stocks.iterrows(), 1):
        vol_ratio_str = f"{row['volume_ratio']:.2f}" if pd.notna(row['volume_ratio']) else "N/A"
        
        print(f"{i:2d}   | {row['code']} | {row['name'][:6]:6s} | {row['sector'][:4]:4s} | "
              f"{row['price']:6.2f} | {row['change_pct']:4.1f}% | {row['turnover_rate']:5.2f}% | "
              f"{vol_ratio_str:4s} | {row['amount']:8.2f} | {row['comprehensive_score']:5.2f} | {row['quality_grade']:2s}")
    
    # 详细分析TOP5
    print(f"\n\n{'='*100}")
    print("TOP5 详细投资分析")
    print(f"{'='*100}")
    
    top5 = top_stocks.head(5)
    for i, (_, row) in enumerate(top5.iterrows(), 1):
        print(f"\n{'─'*80}")
        print(f"【{i}】{row['code']} {row['name']} [{row['sector']}]")
        print(f"{'─'*80}")
        
        print(f"综合得分: {row['comprehensive_score']:.2f} (等级: {row['quality_grade']})")
        print(f"\n评分明细:")
        print(f"  ├─ 动量得分: {row['momentum_score']:.2f}/35.0 ({row['details']['momentum']['category']})")
        print(f"  ├─ 流动性得分: {row['liquidity_score']:.2f}/25.0 ({row['details']['liquidity']['category']})")
        print(f"  ├─ 成交量得分: {row['volume_score']:.2f}/25.0 ({row['details']['volume']['category']})")
        print(f"  └─ 估值得分: {row['valuation_score']:.2f}/15.0 ({row['details']['valuation']['category']})")
        
        print(f"\n关键指标:")
        print(f"  当前价格: {row['price']:.2f}元")
        print(f"  今日涨幅: {row['change_pct']:.2f}%")
        print(f"  换手率: {row['turnover_rate']:.2f}%")
        print(f"  量比: {row['volume_ratio']:.2f}")
        print(f"  成交额: {row['amount']:.2f}亿")
        print(f"  市值: {row['market_cap']:.0f}亿")
        
        # 交易策略建议
        stop_loss = row['price'] * 0.95  # -5%止损
        take_profit = row['price'] * 1.25  # +25%止盈
        trailing_trigger = row['price'] * 1.09  # +9%触发移动止盈
        
        print(f"\n交易策略建议:")
        print(f"  止损价: {stop_loss:.2f}元 (-5%)")
        print(f"  止盈价: {take_profit:.2f}元 (+25%)")
        print(f"  移动止盈触发: {trailing_trigger:.2f}元 (+9%)")
        
        # 投资建议
        if row['quality_grade'] in ['S+', 'S']:
            advice = "强烈关注，可考虑建仓"
        elif row['quality_grade'] == 'A+':
            advice = "重点关注，等待回调介入"
        else:
            advice = "一般关注，谨慎操作"
        
        print(f"  投资建议: {advice}")
    
    # 板块分布
    print(f"\n\n{'='*100}")
    print("板块分布统计")
    print(f"{'='*100}")
    
    sector_stats = top_stocks.groupby('sector').agg({
        'comprehensive_score': ['count', 'mean'],
        'change_pct': 'mean'
    }).round(2)
    sector_stats.columns = ['数量', '平均得分', '平均涨幅']
    sector_stats = sector_stats.sort_values('平均得分', ascending=False)
    print(sector_stats.to_string())
    
    return results_df

if __name__ == "__main__":
    results = aggressive_stock_screening()
    
    if results is not None:
        print(f"\n{'='*100}")
        print("筛选完成！")
        print("提示: 当前市场处于强势上涨阶段，建议重点关注S级和A+级股票")
        print("风险提示: 高位追涨需谨慎，严格执行止损纪律")
        print(f"{'='*100}")