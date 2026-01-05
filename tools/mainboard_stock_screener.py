#!/usr/bin/env python3
"""
主板科技股筛选器 - 仅筛选主板和中小板股票

基于高级评分系统，筛选出最适合投资的主板科技股
排除创业板(300xxx)和科创板(688xxx)股票

作者: 卓越股票分析师
日期: 2026-01-05
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import akshare as ak
import pandas as pd
from datetime import datetime
from typing import List, Dict, Tuple
import time

from core.advanced_scoring_system import AdvancedScoringSystem, AGGRESSIVE_WEIGHTS
from config.tech_stock_pool import get_tech_stock_pool


class MainboardStockScreener:
    """主板科技股筛选器"""
    
    def __init__(self):
        """初始化筛选器"""
        self.scoring_system = AdvancedScoringSystem(AGGRESSIVE_WEIGHTS)
        self.tech_pool = get_tech_stock_pool()
        self.results = []
        
    def get_stock_data(self, code: str) -> Dict:
        """获取股票实时数据"""
        try:
            # 获取实时行情
            stock_info = ak.stock_zh_a_spot_em()
            stock_data = stock_info[stock_info['代码'] == code]
            
            if stock_data.empty:
                return None
                
            data = stock_data.iloc[0]
            
            # 获取PE数据
            try:
                pe_data = ak.stock_zh_a_valuation_em(symbol=code)
                if not pe_data.empty:
                    pe_ratio = pe_data.iloc[-1]['市盈率-动态']
                else:
                    pe_ratio = 25.0  # 默认PE
            except:
                pe_ratio = 25.0
            
            return {
                'code': code,
                'name': data['名称'],
                'price': float(data['最新价']),
                'change_pct': float(data['涨跌幅']),
                'turnover_rate': float(data['换手率']),
                'volume_ratio': float(data['量比']),
                'pe_ratio': float(pe_ratio) if pe_ratio > 0 else 25.0,
                'market_cap': float(data['总市值']) / 100000000,  # 转换为亿元
                'sector': self.tech_pool.get_stock_sector(code)
            }
            
        except Exception as e:
            print(f"获取 {code} 数据失败: {e}")
            return None
    
    def screen_stocks(self) -> List[Dict]:
        """筛选股票"""
        print("🔍 开始筛选主板科技股...")
        print(f"📊 使用激进型权重配置 (动量45%, 流动性25%, 成交量20%, 估值10%)")
        print(f"🚫 已排除创业板(300xxx)和科创板(688xxx)股票")
        print("-" * 60)
        
        all_stocks = self.tech_pool.get_all_stocks()
        total_stocks = len(all_stocks)
        
        print(f"📈 股票池总数: {total_stocks} 只")
        
        # 按行业统计
        sector_counts = {}
        for stock in all_stocks:
            sector_counts[stock.sector] = sector_counts.get(stock.sector, 0) + 1
        
        print("📊 行业分布:")
        for sector, count in sector_counts.items():
            print(f"   {sector}: {count} 只")
        print("-" * 60)
        
        results = []
        processed = 0
        
        for stock in all_stocks:
            processed += 1
            print(f"处理进度: {processed}/{total_stocks} - {stock.code} {stock.name}")
            
            # 获取股票数据
            stock_data = self.get_stock_data(stock.code)
            if stock_data is None:
                continue
            
            # 计算评分
            score_result = self.scoring_system.calculate_comprehensive_score(
                change_pct=stock_data['change_pct'],
                turnover_rate=stock_data['turnover_rate'],
                volume_ratio=stock_data['volume_ratio'],
                pe_ratio=stock_data['pe_ratio'],
                market_cap=stock_data['market_cap']
            )
            
            # 合并结果
            result = {**stock_data, **score_result}
            results.append(result)
            
            # 避免请求过于频繁
            time.sleep(0.1)
        
        # 按综合得分排序
        results.sort(key=lambda x: x['comprehensive_score'], reverse=True)
        self.results = results
        
        return results
    
    def display_results(self, top_n: int = 20):
        """显示筛选结果"""
        if not self.results:
            print("❌ 没有筛选结果")
            return
        
        print(f"\n🏆 主板科技股筛选结果 (前{top_n}名)")
        print("=" * 100)
        
        # 表头
        print(f"{'排名':<4} {'代码':<8} {'名称':<10} {'行业':<8} {'涨幅%':<6} {'换手%':<6} {'量比':<6} {'PE':<6} {'综合得分':<8} {'等级':<4}")
        print("-" * 100)
        
        for i, stock in enumerate(self.results[:top_n], 1):
            print(f"{i:<4} {stock['code']:<8} {stock['name']:<10} {stock['sector']:<8} "
                  f"{stock['change_pct']:<6.2f} {stock['turnover_rate']:<6.2f} "
                  f"{stock['volume_ratio']:<6.2f} {stock['pe_ratio']:<6.1f} "
                  f"{stock['comprehensive_score']:<8.2f} {stock['quality_grade']:<4}")
        
        # 统计信息
        print("\n📊 筛选统计:")
        print(f"   总筛选股票数: {len(self.results)}")
        
        # 按等级统计
        grade_counts = {}
        for stock in self.results:
            grade = stock['quality_grade']
            grade_counts[grade] = grade_counts.get(grade, 0) + 1
        
        print("   等级分布:")
        for grade in ['S+', 'S', 'A+', 'A', 'B+', 'B', 'C', 'D']:
            if grade in grade_counts:
                print(f"     {grade}级: {grade_counts[grade]} 只")
        
        # 按行业统计前10名
        print(f"\n🏭 前{min(10, len(self.results))}名行业分布:")
        sector_scores = {}
        for stock in self.results[:10]:
            sector = stock['sector']
            if sector not in sector_scores:
                sector_scores[sector] = []
            sector_scores[sector].append(stock['comprehensive_score'])
        
        for sector, scores in sector_scores.items():
            avg_score = sum(scores) / len(scores)
            print(f"   {sector}: {len(scores)}只, 平均得分 {avg_score:.2f}")
    
    def get_top_recommendations(self, min_score: float = 85.0) -> List[Dict]:
        """获取高分推荐股票"""
        if not self.results:
            return []
        
        recommendations = [
            stock for stock in self.results 
            if stock['comprehensive_score'] >= min_score
        ]
        
        return recommendations
    
    def display_trading_suggestions(self, top_n: int = 5):
        """显示交易建议"""
        if not self.results:
            return
        
        print(f"\n💡 交易建议 (前{top_n}名)")
        print("=" * 80)
        
        for i, stock in enumerate(self.results[:top_n], 1):
            print(f"\n{i}. {stock['name']} ({stock['code']}) - {stock['sector']}")
            print(f"   综合得分: {stock['comprehensive_score']:.2f} ({stock['quality_grade']}级)")
            print(f"   当前价格: ¥{stock['price']:.2f}")
            print(f"   今日涨幅: {stock['change_pct']:+.2f}%")
            
            # 基于得分给出建议
            score = stock['comprehensive_score']
            if score >= 90:
                suggestion = "🟢 强烈推荐 - 综合条件优秀，建议重点关注"
                position = "建议仓位: 15-20%"
                stop_loss = f"止损位: {stock['price'] * 0.95:.2f} (-5%)"
                take_profit = f"止盈位: {stock['price'] * 1.25:.2f} (+25%)"
            elif score >= 85:
                suggestion = "🟡 推荐 - 条件良好，可适量配置"
                position = "建议仓位: 10-15%"
                stop_loss = f"止损位: {stock['price'] * 0.93:.2f} (-7%)"
                take_profit = f"止盈位: {stock['price'] * 1.20:.2f} (+20%)"
            else:
                suggestion = "🟠 观察 - 条件一般，谨慎操作"
                position = "建议仓位: 5-10%"
                stop_loss = f"止损位: {stock['price'] * 0.90:.2f} (-10%)"
                take_profit = f"止盈位: {stock['price'] * 1.15:.2f} (+15%)"
            
            print(f"   {suggestion}")
            print(f"   {position}")
            print(f"   {stop_loss}")
            print(f"   {take_profit}")


def main():
    """主函数"""
    print("🚀 主板科技股智能筛选系统")
    print(f"📅 筛选时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🎯 目标: 筛选最适合投资的主板科技股")
    print("⚠️  注意: 已排除创业板和科创板股票")
    print("=" * 60)
    
    # 创建筛选器
    screener = MainboardStockScreener()
    
    # 执行筛选
    results = screener.screen_stocks()
    
    if results:
        # 显示结果
        screener.display_results(top_n=15)
        
        # 显示交易建议
        screener.display_trading_suggestions(top_n=5)
        
        # 显示高分股票
        high_score_stocks = screener.get_top_recommendations(min_score=85.0)
        if high_score_stocks:
            print(f"\n⭐ 高分推荐股票 (得分≥85分): {len(high_score_stocks)} 只")
            for stock in high_score_stocks:
                print(f"   {stock['name']} ({stock['code']}): {stock['comprehensive_score']:.2f}分")
    else:
        print("❌ 未找到符合条件的股票")
    
    print(f"\n✅ 筛选完成! 共处理 {len(results)} 只股票")


if __name__ == "__main__":
    main()