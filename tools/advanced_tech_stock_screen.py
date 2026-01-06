#!/usr/bin/env python3
"""
使用高级评分系统筛选科技股

基于 AdvancedScoringSystem 对100只科技股进行综合评分
采用量化金融理论和技术分析的精密评分模型

作者: Kiro
日期: 2026-01-06
"""

import sys
sys.path.insert(0, '.')

import akshare as ak
import pandas as pd
from datetime import datetime
from typing import Dict, List
from config.tech_stock_pool import get_all_tech_stocks, get_stock_name, get_stock_sector
from core.advanced_scoring_system import AdvancedScoringSystem, BALANCED_WEIGHTS


def get_realtime_data(codes: List[str]) -> pd.DataFrame:
    """获取实时行情数据"""
    df = ak.stock_zh_a_spot_em()
    df = df[df['代码'].isin(codes)].copy()
    return df


def screen_with_advanced_scoring(codes: List[str]) -> List[Dict]:
    """使用高级评分系统筛选股票"""
    print(f"\n📊 正在获取 {len(codes)} 只股票的实时数据...")
    
    # 获取实时数据
    realtime_df = get_realtime_data(codes)
    print(f"   成功获取 {len(realtime_df)} 只股票数据")
    
    # 创建评分系统
    scorer = AdvancedScoringSystem(BALANCED_WEIGHTS)
    
    results = []
    total = len(realtime_df)
    
    for idx, (_, row) in enumerate(realtime_df.iterrows(), 1):
        code = row['代码']
        name = row['名称']
        
        if idx % 20 == 0:
            print(f"   处理进度: {idx}/{total}")
        
        try:
            # 提取指标
            change_pct = float(row['涨跌幅']) if pd.notna(row['涨跌幅']) else 0
            turnover_rate = float(row['换手率']) if pd.notna(row['换手率']) else 0
            volume_ratio = float(row['量比']) if pd.notna(row['量比']) else 0
            pe_ratio = float(row['市盈率-动态']) if pd.notna(row['市盈率-动态']) else 0
            market_cap = float(row['总市值']) / 1e8 if pd.notna(row['总市值']) else 0
            price = float(row['最新价']) if pd.notna(row['最新价']) else 0
            pb = float(row['市净率']) if pd.notna(row['市净率']) else 0
            
            # 计算综合评分
            score_result = scorer.calculate_comprehensive_score(
                change_pct=change_pct,
                turnover_rate=turnover_rate,
                volume_ratio=volume_ratio,
                pe_ratio=pe_ratio,
                market_cap=market_cap
            )
            
            results.append({
                'code': code,
                'name': name,
                'sector': get_stock_sector(code),
                'price': price,
                'change_pct': change_pct,
                'turnover_rate': turnover_rate,
                'volume_ratio': volume_ratio,
                'pe': pe_ratio,
                'pb': pb,
                'market_cap': market_cap,
                'comprehensive_score': score_result['comprehensive_score'],
                'quality_grade': score_result['quality_grade'],
                'momentum_score': score_result['momentum_score'],
                'liquidity_score': score_result['liquidity_score'],
                'volume_score': score_result['volume_score'],
                'valuation_score': score_result['valuation_score'],
                'details': score_result['details']
            })
        except Exception as e:
            print(f"   ⚠️ {code} {name} 分析失败: {e}")
            continue
    
    # 按综合得分排序
    results.sort(key=lambda x: x['comprehensive_score'], reverse=True)
    return results


def print_top5_report(results: List[Dict]):
    """打印TOP5详细报告"""
    top5 = results[:5]
    
    print("\n" + "=" * 85)
    print("🏆 高级评分系统 TOP 5 股票推荐")
    print(f"📅 分析日期: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 85)
    
    print("\n📊 评分权重说明:")
    print("   动量得分(35%) + 流动性得分(25%) + 成交量得分(25%) + 估值得分(15%)")
    
    for i, stock in enumerate(top5, 1):
        print(f"\n{'─' * 85}")
        print(f"🥇 第{i}名: {stock['code']} {stock['name']} [{stock['quality_grade']}级]")
        print(f"   行业: {stock['sector']} | 现价: {stock['price']:.2f}元 | 涨跌: {stock['change_pct']:+.2f}%")
        print(f"\n   🎯 综合得分: {stock['comprehensive_score']:.1f}/100")
        
        print(f"\n   📋 四维度得分明细:")
        print(f"      动量得分: {stock['momentum_score']:.1f}/35 - {stock['details']['momentum']['category']}")
        print(f"      流动性得分: {stock['liquidity_score']:.1f}/25 - {stock['details']['liquidity']['category']}")
        print(f"      成交量得分: {stock['volume_score']:.1f}/25 - {stock['details']['volume']['category']}")
        print(f"      估值得分: {stock['valuation_score']:.1f}/15 - {stock['details']['valuation']['category']}")
        
        print(f"\n   📈 关键指标:")
        print(f"      PE: {stock['pe']:.1f} | PB: {stock['pb']:.2f} | 市值: {stock['market_cap']:.0f}亿")
        print(f"      量比: {stock['volume_ratio']:.2f} | 换手率: {stock['turnover_rate']:.2f}%")
        
        # 操作建议
        score = stock['comprehensive_score']
        price = stock['price']
        grade = stock['quality_grade']
        
        print(f"\n   💡 操作建议:")
        if grade in ['S+', 'S']:
            print(f"      ✅ 强烈推荐买入，建议仓位: 8-10%")
        elif grade in ['A+', 'A']:
            print(f"      ✅ 推荐买入，建议仓位: 5-8%")
        elif grade in ['B+', 'B']:
            print(f"      ⏳ 可少量试仓，建议仓位: 3-5%")
        else:
            print(f"      ⏳ 观望为主，等待更好时机")
        
        stop_loss = price * 0.954
        target1 = price * 1.05
        target2 = price * 1.08
        print(f"      止损价: {stop_loss:.2f}元(-4.6%) | 目标价: {target1:.2f}元(+5%) / {target2:.2f}元(+8%)")
    
    # 汇总表格
    print(f"\n{'=' * 85}")
    print("📊 TOP 5 汇总排名")
    print("=" * 85)
    print(f"\n{'排名':<4} {'代码':<8} {'名称':<10} {'行业':<10} {'等级':<4} {'综合分':<8} {'动量':<6} {'流动':<6} {'成交':<6} {'估值':<6}")
    print("-" * 85)
    for i, s in enumerate(top5, 1):
        print(f"{i:<4} {s['code']:<8} {s['name']:<10} {s['sector']:<10} {s['quality_grade']:<4} "
              f"{s['comprehensive_score']:<8.1f} {s['momentum_score']:<6.1f} {s['liquidity_score']:<6.1f} "
              f"{s['volume_score']:<6.1f} {s['valuation_score']:<6.1f}")
    
    # 投资建议
    print(f"\n{'=' * 85}")
    print("💰 明日投资建议")
    print("=" * 85)
    
    best = top5[0]
    print(f"\n🥇 首选推荐: {best['code']} {best['name']} ({best['sector']})")
    print(f"   综合得分: {best['comprehensive_score']:.1f}分 | 质量等级: {best['quality_grade']}")
    print(f"   推荐理由: {best['details']['momentum']['category']}；{best['details']['volume']['category']}；{best['details']['valuation']['category']}")
    
    if len(top5) > 1:
        second = top5[1]
        print(f"\n🥈 次选推荐: {second['code']} {second['name']} ({second['sector']})")
        print(f"   综合得分: {second['comprehensive_score']:.1f}分 | 质量等级: {second['quality_grade']}")
    
    print("\n⚠️ 风险提示:")
    print("   1. 以上分析基于量化模型和当前市场状态，不构成投资建议")
    print("   2. 请结合大盘走势和个人风险承受能力做出决策")
    print("   3. 严格执行止损纪律，单只股票仓位不超过10%")
    print("   4. 建议开盘后观察30分钟再决定是否买入")
    
    return top5


def main():
    """主函数"""
    print("=" * 85)
    print("🔬 高级量化评分系统 - 科技股筛选")
    print("   动量 + 流动性 + 成交量 + 估值 综合评分")
    print(f"📅 分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 85)
    
    # 获取科技股池
    all_codes = get_all_tech_stocks()
    print(f"\n📋 科技股池共 {len(all_codes)} 只股票")
    
    # 筛选评分
    results = screen_with_advanced_scoring(all_codes)
    print(f"\n✅ 成功分析 {len(results)} 只股票")
    
    # 打印报告
    top5 = print_top5_report(results)
    
    return results, top5


if __name__ == "__main__":
    main()
