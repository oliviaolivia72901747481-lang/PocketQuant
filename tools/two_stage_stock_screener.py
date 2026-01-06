#!/usr/bin/env python3
"""
两阶段股票筛选工具

第一阶段: 使用 AdvancedScoringSystem 进行量化评分筛选
第二阶段: 使用 ProfessionalStockScreener 进行四维度精选

为短线散户筛选最适合明天投资的股票

作者: 卓越股票分析师
日期: 2026-01-06
"""

import sys
sys.path.insert(0, '.')

import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple

from core.advanced_scoring_system import AdvancedScoringSystem, ScoringWeights
from config.tech_stock_pool import get_all_tech_stocks, get_stock_name, get_stock_sector


class TwoStageStockScreener:
    """两阶段股票筛选器"""
    
    # 2026年1月政策热点行业（权重加成）
    POLICY_HOT_SECTORS = {
        '半导体': 1.25,
        '人工智能': 1.20,
        '算力': 1.15,
        '新能源科技': 1.10,
        '5G通信': 1.05,
    }
    
    def __init__(self):
        self.analysis_date = datetime.now().strftime('%Y-%m-%d')
        self.advanced_scorer = AdvancedScoringSystem()
        
    def get_realtime_data(self, codes: List[str]) -> pd.DataFrame:
        """获取实时行情数据"""
        print("📊 正在获取实时行情数据...")
        df = ak.stock_zh_a_spot_em()
        df = df[df['代码'].isin(codes)].copy()
        print(f"   成功获取 {len(df)} 只股票数据")
        return df
    
    def get_history_data(self, code: str, days: int = 60) -> pd.DataFrame:
        """获取历史K线数据"""
        try:
            df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq")
            if df is not None and len(df) >= 20:
                df = df.tail(days).reset_index(drop=True)
                df = df.rename(columns={
                    '日期': 'date', '开盘': 'open', '收盘': 'close',
                    '最高': 'high', '最低': 'low', '成交量': 'volume',
                    '成交额': 'turnover', '振幅': 'amplitude', 
                    '涨跌幅': 'change_pct', '涨跌额': 'change_amt', 
                    '换手率': 'turnover_rate'
                })
                return df
        except Exception:
            pass
        return pd.DataFrame()
    
    # ==================== 第一阶段: AdvancedScoringSystem ====================
    
    def stage1_advanced_scoring(self, realtime_df: pd.DataFrame) -> List[Dict]:
        """
        第一阶段: 使用 AdvancedScoringSystem 进行量化评分
        
        评分维度:
        - 动量得分 (35%): 涨跌幅，最优区间3-6%
        - 流动性得分 (25%): 换手率2-8%最佳
        - 成交量得分 (25%): 量比1.5-3倍最优
        - 估值得分 (15%): PE 15-30倍合理
        """
        print("\n" + "=" * 80)
        print("🔬 第一阶段: AdvancedScoringSystem 量化评分")
        print("=" * 80)
        print("   评分维度: 动量(35%) + 流动性(25%) + 成交量(25%) + 估值(15%)")
        
        results = []
        total = len(realtime_df)
        
        for idx, (_, row) in enumerate(realtime_df.iterrows(), 1):
            if idx % 20 == 0:
                print(f"   处理进度: {idx}/{total}")
            
            try:
                code = row['代码']
                name = row['名称']
                
                # 提取评分所需数据
                change_pct = float(row['涨跌幅']) if pd.notna(row['涨跌幅']) else 0
                turnover_rate = float(row['换手率']) if pd.notna(row['换手率']) else 0
                volume_ratio = float(row['量比']) if pd.notna(row['量比']) else 1.0
                pe_ratio = float(row['市盈率-动态']) if pd.notna(row['市盈率-动态']) else 30
                market_cap = float(row['总市值']) / 1e8 if pd.notna(row['总市值']) else 100
                
                # 使用 AdvancedScoringSystem 计算综合评分
                score_result = self.advanced_scorer.calculate_comprehensive_score(
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
                    'price': float(row['最新价']) if pd.notna(row['最新价']) else 0,
                    'change_pct': change_pct,
                    'turnover_rate': turnover_rate,
                    'volume_ratio': volume_ratio,
                    'pe_ratio': pe_ratio,
                    'market_cap': market_cap,
                    'advanced_score': score_result['comprehensive_score'],
                    'quality_grade': score_result['quality_grade'],
                    'momentum_score': score_result['momentum_score'],
                    'liquidity_score': score_result['liquidity_score'],
                    'volume_score': score_result['volume_score'],
                    'valuation_score': score_result['valuation_score'],
                    'details': score_result['details']
                })
            except Exception as e:
                continue
        
        # 按得分排序
        results.sort(key=lambda x: x['advanced_score'], reverse=True)
        
        print(f"\n✅ 第一阶段完成: 共评分 {len(results)} 只股票")
        return results
    
    def filter_high_score_stocks(self, results: List[Dict], min_score: float = 75.0, top_n: int = 30) -> List[Dict]:
        """筛选高分股票进入第二阶段"""
        # 筛选得分>=min_score 或 等级为S+/S/A+的股票
        high_grades = ['S+', 'S', 'A+']
        filtered = [r for r in results if r['advanced_score'] >= min_score or r['quality_grade'] in high_grades]
        
        # 如果筛选结果不足，取前top_n名
        if len(filtered) < top_n:
            filtered = results[:top_n]
        else:
            filtered = filtered[:top_n]
        
        return filtered
    
    # ==================== 第二阶段: ProfessionalStockScreener ====================
    
    def stage2_professional_scoring(self, candidates: List[Dict], realtime_df: pd.DataFrame) -> List[Dict]:
        """
        第二阶段: 四维度专业评分
        
        评分维度:
        - 政策面 (15%): 行业政策热点加成
        - 基本面 (25%): PE、PB、市值分析
        - 情绪面 (25%): 量比、换手率、涨跌幅
        - 技术面 (35%): MA、RSI、MACD
        """
        print("\n" + "=" * 80)
        print("🎯 第二阶段: ProfessionalStockScreener 四维度精选")
        print("=" * 80)
        print("   评分维度: 政策面(15%) + 基本面(25%) + 情绪面(25%) + 技术面(35%)")
        
        results = []
        total = len(candidates)
        
        # 创建代码到实时数据的映射
        realtime_map = {row['代码']: row for _, row in realtime_df.iterrows()}
        
        for idx, candidate in enumerate(candidates, 1):
            code = candidate['code']
            name = candidate['name']
            
            if idx % 10 == 0:
                print(f"   处理进度: {idx}/{total}")
            
            try:
                row = realtime_map.get(code)
                if row is None:
                    continue
                
                # 获取历史数据
                hist_df = self.get_history_data(code)
                
                # 四维度评分
                policy_score, policy_reason = self._score_policy(code)
                fundamental_score, fundamental_reason = self._score_fundamental(row)
                sentiment_score, sentiment_reason = self._score_sentiment(row)
                technical_score, technical_reason = self._score_technical(row, hist_df)
                
                # 计算综合得分
                professional_score = (
                    policy_score * 0.15 +
                    fundamental_score * 0.25 +
                    sentiment_score * 0.25 +
                    technical_score * 0.35
                )
                
                # 综合两阶段得分 (第一阶段40% + 第二阶段60%)
                final_score = candidate['advanced_score'] * 0.4 + professional_score * 0.6
                
                results.append({
                    **candidate,
                    'policy_score': policy_score,
                    'policy_reason': policy_reason,
                    'fundamental_score': fundamental_score,
                    'fundamental_reason': fundamental_reason,
                    'sentiment_score': sentiment_score,
                    'sentiment_reason': sentiment_reason,
                    'technical_score': technical_score,
                    'technical_reason': technical_reason,
                    'professional_score': professional_score,
                    'final_score': final_score
                })
            except Exception as e:
                continue
        
        # 按最终得分排序
        results.sort(key=lambda x: x['final_score'], reverse=True)
        
        print(f"\n✅ 第二阶段完成: 精选出 {len(results)} 只股票")
        return results
    
    def _score_policy(self, code: str) -> Tuple[float, str]:
        """政策面评分"""
        sector = get_stock_sector(code)
        if sector in self.POLICY_HOT_SECTORS:
            multiplier = self.POLICY_HOT_SECTORS[sector]
            score = min(100, 80 + (multiplier - 1) * 100)
            reason = f"政策热点({sector})"
        else:
            score = 50
            reason = f"非热点({sector})"
        return score, reason
    
    def _score_fundamental(self, row: pd.Series) -> Tuple[float, str]:
        """基本面评分"""
        score = 0
        details = []
        
        pe = float(row['市盈率-动态']) if pd.notna(row['市盈率-动态']) else 0
        if 10 <= pe <= 30:
            score += 35
            details.append(f"PE({pe:.0f})优")
        elif 30 < pe <= 50:
            score += 25
            details.append(f"PE({pe:.0f})中")
        else:
            score += 10
            details.append(f"PE({pe:.0f})差")
        
        pb = float(row['市净率']) if pd.notna(row['市净率']) else 0
        if 1 <= pb <= 3:
            score += 25
        elif 3 < pb <= 5:
            score += 18
        else:
            score += 10
        
        market_cap = float(row['总市值']) / 1e8 if pd.notna(row['总市值']) else 0
        if 100 <= market_cap <= 500:
            score += 25
            details.append(f"市值{market_cap:.0f}亿")
        elif 50 <= market_cap < 100 or 500 < market_cap <= 1000:
            score += 18
            details.append(f"市值{market_cap:.0f}亿")
        else:
            score += 10
            details.append(f"市值{market_cap:.0f}亿")
        
        score += 15  # 流通市值基础分
        
        return min(100, score), "；".join(details)
    
    def _score_sentiment(self, row: pd.Series) -> Tuple[float, str]:
        """情绪面评分"""
        score = 0
        details = []
        
        volume_ratio = float(row['量比']) if pd.notna(row['量比']) else 0
        if 1.2 <= volume_ratio <= 2.5:
            score += 30
            details.append(f"量比{volume_ratio:.1f}温和放量")
        elif 0.8 <= volume_ratio < 1.2:
            score += 18
        elif 2.5 < volume_ratio <= 4:
            score += 22
        else:
            score += 10
        
        turnover = float(row['换手率']) if pd.notna(row['换手率']) else 0
        if 2 <= turnover <= 6:
            score += 30
            details.append(f"换手{turnover:.1f}%健康")
        elif 6 < turnover <= 10:
            score += 22
        else:
            score += 12
        
        change_pct = float(row['涨跌幅']) if pd.notna(row['涨跌幅']) else 0
        if 0 < change_pct <= 3:
            score += 25
            details.append(f"涨{change_pct:.1f}%")
        elif 3 < change_pct <= 6:
            score += 20
            details.append(f"涨{change_pct:.1f}%强势")
        elif -2 <= change_pct <= 0:
            score += 18
        else:
            score += 10
        
        score += 15  # 振幅基础分
        
        return min(100, score), "；".join(details)
    
    def _score_technical(self, row: pd.Series, hist_df: pd.DataFrame) -> Tuple[float, str]:
        """技术面评分"""
        score = 0
        details = []
        
        price = float(row['最新价']) if pd.notna(row['最新价']) else 0
        
        if hist_df.empty or len(hist_df) < 20:
            return 50, "数据不足"
        
        closes = hist_df['close'].astype(float)
        
        # 均线分析
        ma5 = closes.tail(5).mean()
        ma10 = closes.tail(10).mean()
        ma20 = closes.tail(20).mean()
        
        if price > ma5 > ma10 > ma20:
            score += 30
            details.append("多头排列")
        elif price > ma5 > ma10:
            score += 25
            details.append("短期多头")
        elif price > ma5:
            score += 18
        else:
            score += 8
        
        # RSI分析
        if len(closes) >= 14:
            delta = closes.diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta).where(delta < 0, 0).rolling(14).mean()
            rs = gain / loss
            rsi = (100 - (100 / (1 + rs))).iloc[-1]
            if pd.isna(rsi):
                rsi = 50
        else:
            rsi = 50
        
        if 45 <= rsi <= 65:
            score += 30
            details.append(f"RSI{rsi:.0f}健康")
        elif 35 <= rsi < 45:
            score += 25
            details.append(f"RSI{rsi:.0f}偏低")
        elif 65 < rsi <= 75:
            score += 20
        else:
            score += 12
        
        # MACD分析
        if len(closes) >= 26:
            ema12 = closes.ewm(span=12, adjust=False).mean()
            ema26 = closes.ewm(span=26, adjust=False).mean()
            dif = ema12 - ema26
            dea = dif.ewm(span=9, adjust=False).mean()
            
            if dif.iloc[-1] > dea.iloc[-1]:
                score += 25
                details.append("MACD金叉")
            else:
                score += 10
        else:
            score += 15
        
        score += 15  # 近期趋势基础分
        
        return min(100, score), "；".join(details)
    
    # ==================== 报告生成 ====================
    
    def print_stage1_report(self, results: List[Dict], top_n: int = 20):
        """打印第一阶段报告"""
        print("\n" + "=" * 80)
        print("📊 第一阶段结果: AdvancedScoringSystem TOP 20")
        print("=" * 80)
        print(f"\n{'排名':<4} {'代码':<8} {'名称':<10} {'行业':<10} {'得分':<8} {'等级':<6} {'涨幅':<8} {'换手':<8} {'量比':<6}")
        print("-" * 80)
        
        for i, s in enumerate(results[:top_n], 1):
            print(f"{i:<4} {s['code']:<8} {s['name']:<10} {s['sector']:<10} "
                  f"{s['advanced_score']:<8.1f} {s['quality_grade']:<6} "
                  f"{s['change_pct']:>+6.2f}% {s['turnover_rate']:>6.2f}% {s['volume_ratio']:>5.2f}")
    
    def print_final_report(self, results: List[Dict], top_n: int = 5):
        """打印最终报告"""
        print("\n" + "=" * 80)
        print("🏆 两阶段筛选最终结果 TOP 5")
        print(f"📅 分析日期: {self.analysis_date}")
        print("=" * 80)
        print("\n📊 评分说明:")
        print("   第一阶段(40%): 动量(35%) + 流动性(25%) + 成交量(25%) + 估值(15%)")
        print("   第二阶段(60%): 政策面(15%) + 基本面(25%) + 情绪面(25%) + 技术面(35%)")
        
        for i, stock in enumerate(results[:top_n], 1):
            print(f"\n{'─' * 80}")
            print(f"🥇 第{i}名: {stock['code']} {stock['name']}")
            print(f"   行业: {stock['sector']} | 现价: {stock['price']:.2f}元 | 涨跌: {stock['change_pct']:+.2f}%")
            
            print(f"\n   🎯 最终得分: {stock['final_score']:.1f}/100")
            print(f"      第一阶段得分: {stock['advanced_score']:.1f} ({stock['quality_grade']}级)")
            print(f"      第二阶段得分: {stock['professional_score']:.1f}")
            
            print(f"\n   📋 第一阶段明细 (AdvancedScoringSystem):")
            print(f"      动量: {stock['momentum_score']:.1f} | 流动性: {stock['liquidity_score']:.1f} | "
                  f"成交量: {stock['volume_score']:.1f} | 估值: {stock['valuation_score']:.1f}")
            
            print(f"\n   📋 第二阶段明细 (ProfessionalStockScreener):")
            print(f"      政策面: {stock['policy_score']:.0f}分 - {stock['policy_reason']}")
            print(f"      基本面: {stock['fundamental_score']:.0f}分 - {stock['fundamental_reason']}")
            print(f"      情绪面: {stock['sentiment_score']:.0f}分 - {stock['sentiment_reason']}")
            print(f"      技术面: {stock['technical_score']:.0f}分 - {stock['technical_reason']}")
            
            print(f"\n   📈 关键指标:")
            print(f"      PE: {stock['pe_ratio']:.1f} | 市值: {stock['market_cap']:.0f}亿 | "
                  f"换手率: {stock['turnover_rate']:.2f}% | 量比: {stock['volume_ratio']:.2f}")
            
            # 操作建议
            score = stock['final_score']
            price = stock['price']
            print(f"\n   💡 操作建议:")
            if score >= 80:
                print(f"      ✅ 强烈推荐，建议仓位: 8-10%")
            elif score >= 70:
                print(f"      ✅ 推荐买入，建议仓位: 5-8%")
            elif score >= 60:
                print(f"      ⏳ 可少量试仓，建议仓位: 3-5%")
            else:
                print(f"      ⏳ 观望为主")
            
            stop_loss = price * 0.954
            target1 = price * 1.05
            target2 = price * 1.08
            print(f"      止损价: {stop_loss:.2f}元(-4.6%) | 目标价: {target1:.2f}元(+5%) / {target2:.2f}元(+8%)")
        
        # 汇总表格
        print(f"\n{'=' * 80}")
        print("📊 TOP 5 汇总排名")
        print("=" * 80)
        print(f"\n{'排名':<4} {'代码':<8} {'名称':<10} {'行业':<10} {'最终分':<8} {'一阶段':<8} {'二阶段':<8} {'等级':<6}")
        print("-" * 80)
        for i, s in enumerate(results[:top_n], 1):
            print(f"{i:<4} {s['code']:<8} {s['name']:<10} {s['sector']:<10} "
                  f"{s['final_score']:<8.1f} {s['advanced_score']:<8.1f} {s['professional_score']:<8.1f} {s['quality_grade']:<6}")
        
        # 投资建议
        print(f"\n{'=' * 80}")
        print("💰 明日投资建议")
        print("=" * 80)
        
        best = results[0]
        print(f"\n🥇 首选推荐: {best['code']} {best['name']} ({best['sector']})")
        print(f"   最终得分: {best['final_score']:.1f}分 (一阶段{best['advanced_score']:.1f} + 二阶段{best['professional_score']:.1f})")
        print(f"   推荐理由: {best['policy_reason']}；{best['technical_reason']}")
        
        if len(results) > 1:
            second = results[1]
            print(f"\n🥈 次选推荐: {second['code']} {second['name']} ({second['sector']})")
            print(f"   最终得分: {second['final_score']:.1f}分")
        
        print("\n⚠️ 风险提示:")
        print("   1. 以上分析基于历史数据和当前市场状态，不构成投资建议")
        print("   2. 请结合大盘走势和个人风险承受能力做出决策")
        print("   3. 严格执行止损纪律，单只股票仓位不超过10%")
        print("   4. 建议开盘后观察30分钟再决定是否买入")
    
    def run(self) -> List[Dict]:
        """运行两阶段筛选"""
        print("=" * 80)
        print("🔬 两阶段股票筛选系统")
        print("   第一阶段: AdvancedScoringSystem 量化评分")
        print("   第二阶段: ProfessionalStockScreener 四维度精选")
        print(f"📅 分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        # 获取科技股池
        all_codes = get_all_tech_stocks()
        print(f"\n📋 科技股池共 {len(all_codes)} 只股票")
        
        # 获取实时数据
        realtime_df = self.get_realtime_data(all_codes)
        
        # 第一阶段: AdvancedScoringSystem 评分
        stage1_results = self.stage1_advanced_scoring(realtime_df)
        self.print_stage1_report(stage1_results)
        
        # 筛选高分股票进入第二阶段
        candidates = self.filter_high_score_stocks(stage1_results, min_score=70.0, top_n=30)
        print(f"\n📌 筛选出 {len(candidates)} 只高分股票进入第二阶段")
        
        # 第二阶段: ProfessionalStockScreener 四维度精选
        final_results = self.stage2_professional_scoring(candidates, realtime_df)
        
        # 打印最终报告
        self.print_final_report(final_results)
        
        return final_results


def main():
    """主函数"""
    screener = TwoStageStockScreener()
    results = screener.run()
    return results


if __name__ == "__main__":
    main()
