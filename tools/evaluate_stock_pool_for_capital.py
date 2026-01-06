"""
股票池资金适配性评估工具

针对7万元短线交易资金，评估当前科技股票池的适配性
分析维度：
1. 股价区间分布 - 是否能买得起100股
2. 流动性评估 - 换手率是否足够
3. 波动性评估 - 是否适合短线
4. 仓位建议 - 单只股票最大仓位
5. 推荐股票 - 最适合小资金的股票

作者: Kiro AI
日期: 2026-01-06
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import akshare as ak
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from config.tech_stock_pool import get_tech_stock_pool, TechStockPool


@dataclass
class StockEvaluation:
    """股票评估结果"""
    code: str
    name: str
    sector: str
    price: float
    min_buy_amount: float  # 最低买入金额(100股)
    turnover_rate: float   # 换手率
    volatility: float      # 波动率(振幅)
    change_pct: float      # 涨跌幅
    volume: float          # 成交量(万手)
    amount: float          # 成交额(亿元)
    affordability_score: float  # 可负担性评分(0-100)
    liquidity_score: float      # 流动性评分(0-100)
    volatility_score: float     # 波动性评分(0-100)
    total_score: float          # 综合评分


class StockPoolEvaluator:
    """股票池评估器"""
    
    def __init__(self, total_capital: float = 70000):
        """
        初始化评估器
        
        Args:
            total_capital: 总资金(元)，默认7万
        """
        self.total_capital = total_capital
        self.max_single_position = 0.30  # 单只股票最大仓位30%
        self.max_single_amount = total_capital * self.max_single_position
        self.pool = get_tech_stock_pool()
        
    def fetch_realtime_data(self, codes: List[str]) -> pd.DataFrame:
        """获取实时行情数据"""
        try:
            # 获取A股实时行情
            df = ak.stock_zh_a_spot_em()
            
            # 筛选目标股票
            df = df[df['代码'].isin(codes)]
            
            return df
        except Exception as e:
            print(f"获取行情数据失败: {e}")
            return pd.DataFrame()
    
    def evaluate_stock(self, row: pd.Series, sector: str) -> Optional[StockEvaluation]:
        """评估单只股票"""
        try:
            code = row['代码']
            name = row['名称']
            price = float(row['最新价']) if pd.notna(row['最新价']) else 0
            
            if price <= 0:
                return None
            
            # 基础数据
            min_buy = price * 100  # 最低买入金额
            turnover = float(row['换手率']) if pd.notna(row['换手率']) else 0
            amplitude = float(row['振幅']) if pd.notna(row['振幅']) else 0
            change_pct = float(row['涨跌幅']) if pd.notna(row['涨跌幅']) else 0
            volume = float(row['成交量']) / 10000 if pd.notna(row['成交量']) else 0  # 万手
            amount = float(row['成交额']) / 100000000 if pd.notna(row['成交额']) else 0  # 亿元
            
            # 可负担性评分 (价格越低越好，但不能太低)
            if price < 5:
                affordability = 60  # 太便宜可能有问题
            elif price <= 20:
                affordability = 100  # 最佳区间
            elif price <= 35:
                affordability = 90
            elif price <= 50:
                affordability = 75
            elif price <= 70:
                affordability = 50  # 7万只能买1手
            else:
                affordability = max(0, 100 - (price - 70) * 2)  # 超过70元逐渐降低
            
            # 流动性评分 (换手率和成交额)
            liquidity = 0
            if turnover >= 5:
                liquidity += 50
            elif turnover >= 3:
                liquidity += 40
            elif turnover >= 1:
                liquidity += 25
            else:
                liquidity += 10
            
            if amount >= 5:
                liquidity += 50
            elif amount >= 2:
                liquidity += 40
            elif amount >= 0.5:
                liquidity += 25
            else:
                liquidity += 10
            
            # 波动性评分 (短线需要适度波动)
            if 3 <= amplitude <= 8:
                volatility_score = 100  # 最佳波动区间
            elif 2 <= amplitude < 3:
                volatility_score = 80
            elif 8 < amplitude <= 12:
                volatility_score = 70
            elif amplitude < 2:
                volatility_score = 40  # 波动太小
            else:
                volatility_score = 50  # 波动太大风险高
            
            # 综合评分 (可负担40% + 流动性35% + 波动性25%)
            total = affordability * 0.40 + liquidity * 0.35 + volatility_score * 0.25
            
            return StockEvaluation(
                code=code,
                name=name,
                sector=sector,
                price=price,
                min_buy_amount=min_buy,
                turnover_rate=turnover,
                volatility=amplitude,
                change_pct=change_pct,
                volume=volume,
                amount=amount,
                affordability_score=affordability,
                liquidity_score=liquidity,
                volatility_score=volatility_score,
                total_score=total
            )
        except Exception as e:
            print(f"评估股票失败: {e}")
            return None
    
    def evaluate_pool(self) -> Dict:
        """评估整个股票池"""
        print("=" * 60)
        print(f"📊 股票池资金适配性评估")
        print(f"💰 总资金: {self.total_capital:,.0f}元 (7万元)")
        print(f"📈 单只最大仓位: {self.max_single_position*100:.0f}% = {self.max_single_amount:,.0f}元")
        print("=" * 60)
        
        # 获取所有股票
        all_stocks = self.pool.get_all_stocks()
        codes = [s.code for s in all_stocks]
        code_to_sector = {s.code: s.sector for s in all_stocks}
        
        print(f"\n正在获取 {len(codes)} 只股票的实时行情...")
        
        # 获取实时数据
        df = self.fetch_realtime_data(codes)
        
        if df.empty:
            print("❌ 无法获取行情数据，请检查网络连接")
            return {}
        
        print(f"✅ 成功获取 {len(df)} 只股票数据\n")
        
        # 评估每只股票
        evaluations: List[StockEvaluation] = []
        for _, row in df.iterrows():
            code = row['代码']
            sector = code_to_sector.get(code, "未知")
            eval_result = self.evaluate_stock(row, sector)
            if eval_result:
                evaluations.append(eval_result)
        
        # 统计分析
        return self.analyze_results(evaluations)
    
    def analyze_results(self, evaluations: List[StockEvaluation]) -> Dict:
        """分析评估结果"""
        if not evaluations:
            return {}
        
        # 价格区间统计
        price_ranges = {
            "5元以下(风险较高)": 0,
            "5-20元(最佳区间)": 0,
            "20-35元(适中)": 0,
            "35-50元(偏高)": 0,
            "50-70元(较高)": 0,
            "70元以上(不推荐)": 0
        }
        
        affordable_stocks = []  # 可负担的股票
        unaffordable_stocks = []  # 买不起的股票
        
        for e in evaluations:
            if e.price < 5:
                price_ranges["5元以下(风险较高)"] += 1
            elif e.price <= 20:
                price_ranges["5-20元(最佳区间)"] += 1
            elif e.price <= 35:
                price_ranges["20-35元(适中)"] += 1
            elif e.price <= 50:
                price_ranges["35-50元(偏高)"] += 1
            elif e.price <= 70:
                price_ranges["50-70元(较高)"] += 1
            else:
                price_ranges["70元以上(不推荐)"] += 1
            
            # 判断是否买得起(至少能买100股)
            if e.min_buy_amount <= self.max_single_amount:
                affordable_stocks.append(e)
            else:
                unaffordable_stocks.append(e)
        
        # 输出价格分布
        print("=" * 60)
        print("📊 一、股价区间分布分析")
        print("=" * 60)
        total = len(evaluations)
        for range_name, count in price_ranges.items():
            pct = count / total * 100
            bar = "█" * int(pct / 5)
            print(f"  {range_name}: {count}只 ({pct:.1f}%) {bar}")
        
        # 可负担性分析
        print("\n" + "=" * 60)
        print("💰 二、资金可负担性分析")
        print("=" * 60)
        print(f"  ✅ 可买入股票: {len(affordable_stocks)}只 ({len(affordable_stocks)/total*100:.1f}%)")
        print(f"  ❌ 买不起股票: {len(unaffordable_stocks)}只 ({len(unaffordable_stocks)/total*100:.1f}%)")
        
        if unaffordable_stocks:
            print(f"\n  买不起的股票(股价>{self.max_single_amount/100:.0f}元):")
            for e in sorted(unaffordable_stocks, key=lambda x: x.price, reverse=True)[:10]:
                print(f"    - {e.name}({e.code}): {e.price:.2f}元, 最低买入{e.min_buy_amount:,.0f}元")
        
        # 按板块统计
        print("\n" + "=" * 60)
        print("📈 三、板块适配性分析")
        print("=" * 60)
        sector_stats = {}
        for e in evaluations:
            if e.sector not in sector_stats:
                sector_stats[e.sector] = {"total": 0, "affordable": 0, "avg_score": 0, "scores": []}
            sector_stats[e.sector]["total"] += 1
            sector_stats[e.sector]["scores"].append(e.total_score)
            if e.min_buy_amount <= self.max_single_amount:
                sector_stats[e.sector]["affordable"] += 1
        
        for sector, stats in sector_stats.items():
            stats["avg_score"] = sum(stats["scores"]) / len(stats["scores"])
        
        # 按平均分排序
        sorted_sectors = sorted(sector_stats.items(), key=lambda x: x[1]["avg_score"], reverse=True)
        
        print(f"  {'板块':<12} {'总数':>4} {'可买':>4} {'可买率':>8} {'平均分':>8}")
        print("  " + "-" * 50)
        for sector, stats in sorted_sectors:
            affordable_rate = stats["affordable"] / stats["total"] * 100
            print(f"  {sector:<12} {stats['total']:>4} {stats['affordable']:>4} {affordable_rate:>7.1f}% {stats['avg_score']:>7.1f}")
        
        # 推荐股票(综合评分最高)
        print("\n" + "=" * 60)
        print("⭐ 四、7万元短线推荐股票 TOP 15")
        print("=" * 60)
        
        # 只推荐买得起的股票
        top_stocks = sorted(affordable_stocks, key=lambda x: x.total_score, reverse=True)[:15]
        
        print(f"  {'排名':>4} {'代码':<8} {'名称':<10} {'板块':<10} {'股价':>8} {'换手率':>6} {'振幅':>6} {'评分':>6}")
        print("  " + "-" * 75)
        for i, e in enumerate(top_stocks, 1):
            print(f"  {i:>4} {e.code:<8} {e.name:<10} {e.sector:<10} {e.price:>7.2f} {e.turnover_rate:>5.1f}% {e.volatility:>5.1f}% {e.total_score:>5.1f}")
        
        # 仓位建议
        print("\n" + "=" * 60)
        print("💡 五、仓位管理建议")
        print("=" * 60)
        print(f"""
  📌 总资金: {self.total_capital:,.0f}元
  
  🎯 建议仓位配置:
     • 单只股票最大仓位: 30% = {self.max_single_amount:,.0f}元
     • 建议持股数量: 2-3只 (分散风险)
     • 每只股票建议仓位: 20-30%
  
  ⚠️ 风险控制:
     • 单只股票止损线: -5% (亏损{self.max_single_amount*0.05:,.0f}元)
     • 单只股票止盈线: +8-15%
     • 总仓位控制: 不超过80% (保留{self.total_capital*0.2:,.0f}元现金)
  
  📊 推荐操作模式:
     • 优选10-30元股票 (可买200-700股)
     • 关注换手率>3%的活跃股
     • 选择振幅3-8%的股票 (波动适中)
""")
        
        # 总体评估
        print("=" * 60)
        print("📋 六、股票池总体评估")
        print("=" * 60)
        
        affordable_rate = len(affordable_stocks) / total * 100
        avg_score = sum(e.total_score for e in evaluations) / len(evaluations)
        
        if affordable_rate >= 80 and avg_score >= 70:
            verdict = "✅ 非常适合"
            verdict_detail = "股票池与7万元资金高度匹配，大部分股票都可以买入"
        elif affordable_rate >= 60 and avg_score >= 60:
            verdict = "✅ 比较适合"
            verdict_detail = "股票池基本适合7万元资金，有足够的选择空间"
        elif affordable_rate >= 40:
            verdict = "⚠️ 部分适合"
            verdict_detail = "约一半股票可以买入，建议关注低价优质股"
        else:
            verdict = "❌ 不太适合"
            verdict_detail = "大部分股票价格偏高，建议增加低价股或增加资金"
        
        print(f"""
  📊 评估结果: {verdict}
  
  📈 关键指标:
     • 可买入股票比例: {affordable_rate:.1f}%
     • 股票池平均评分: {avg_score:.1f}分
     • 最佳价格区间(5-35元)股票: {price_ranges['5-20元(最佳区间)'] + price_ranges['20-35元(适中)']}只
  
  💬 评估说明: {verdict_detail}
""")
        
        # 优化建议
        print("=" * 60)
        print("🔧 七、股票池优化建议")
        print("=" * 60)
        
        suggestions = []
        if price_ranges["70元以上(不推荐)"] > 5:
            suggestions.append("• 考虑移除部分高价股(>70元)，增加中低价优质股")
        if price_ranges["5元以下(风险较高)"] > 10:
            suggestions.append("• 低价股(<5元)较多，注意筛选基本面良好的股票")
        if affordable_rate < 70:
            suggestions.append("• 可买入股票比例偏低，建议增加10-30元区间的优质股")
        
        # 板块建议
        hot_sectors = ["半导体", "人工智能", "算力", "消费电子"]
        for sector in hot_sectors:
            if sector in sector_stats:
                if sector_stats[sector]["affordable"] < 5:
                    suggestions.append(f"• {sector}板块可买股票较少，建议补充该板块中低价股")
        
        if not suggestions:
            suggestions.append("• 当前股票池配置合理，无需大幅调整")
            suggestions.append("• 建议定期更新，关注政策热点板块")
        
        for s in suggestions:
            print(f"  {s}")
        
        print("\n" + "=" * 60)
        
        return {
            "total_stocks": total,
            "affordable_stocks": len(affordable_stocks),
            "affordable_rate": affordable_rate,
            "avg_score": avg_score,
            "price_ranges": price_ranges,
            "sector_stats": sector_stats,
            "top_recommendations": top_stocks,
            "verdict": verdict
        }


def main():
    """主函数"""
    print("\n" + "🚀" * 30)
    print("     7万元短线交易 - 股票池适配性评估工具")
    print("🚀" * 30 + "\n")
    
    evaluator = StockPoolEvaluator(total_capital=70000)
    results = evaluator.evaluate_pool()
    
    if results:
        print("\n✅ 评估完成！")
        print(f"📊 可操作股票: {results['affordable_stocks']}只")
        print(f"⭐ 推荐关注TOP3:")
        for i, stock in enumerate(results['top_recommendations'][:3], 1):
            print(f"   {i}. {stock.name}({stock.code}) - {stock.sector} - {stock.price:.2f}元 - 评分{stock.total_score:.1f}")


if __name__ == "__main__":
    main()
