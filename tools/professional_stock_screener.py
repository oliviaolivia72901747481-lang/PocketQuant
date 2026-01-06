#!/usr/bin/env python3
"""
专业股票分析师筛选工具

结合政策面、基本面、情绪面、技术面四维度综合评分
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
from config.tech_stock_pool import get_all_tech_stocks, get_stock_name, get_stock_sector


class ProfessionalStockScreener:
    """专业股票筛选器 - 四维度综合评分"""
    
    # 2026年1月政策热点行业（权重加成）
    POLICY_HOT_SECTORS = {
        '半导体': 1.25,      # 国产替代政策持续
        '人工智能': 1.20,    # AI大模型政策支持
        '算力': 1.15,        # 数字经济基建
        '新能源科技': 1.10,  # 双碳政策
        '5G通信': 1.05,      # 新基建
    }
    
    def __init__(self):
        self.analysis_date = datetime.now().strftime('%Y-%m-%d')
    
    def get_realtime_data(self, codes: List[str]) -> pd.DataFrame:
        """获取实时行情数据"""
        df = ak.stock_zh_a_spot_em()
        df = df[df['代码'].isin(codes)].copy()
        return df
    
    def get_history_data(self, code: str, days: int = 60) -> pd.DataFrame:
        """获取历史K线数据"""
        try:
            df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq")
            if df is not None and len(df) >= 20:
                df = df.tail(days).reset_index(drop=True)
                # 重命名列
                df = df.rename(columns={
                    '日期': 'date', '开盘': 'open', '收盘': 'close',
                    '最高': 'high', '最低': 'low', '成交量': 'volume',
                    '成交额': 'turnover', '振幅': 'amplitude', 
                    '涨跌幅': 'change_pct', '涨跌额': 'change_amt', 
                    '换手率': 'turnover_rate'
                })
                return df
        except Exception as e:
            pass
        return pd.DataFrame()
    
    def score_policy(self, code: str) -> Tuple[float, str]:
        """
        政策面评分 (0-100分)
        根据行业是否属于政策热点给予加分
        """
        sector = get_stock_sector(code)
        if sector in self.POLICY_HOT_SECTORS:
            multiplier = self.POLICY_HOT_SECTORS[sector]
            base_score = 80
            bonus = (multiplier - 1) * 100
            score = min(100, base_score + bonus)
            reason = f"政策热点行业({sector})，加成{multiplier:.0%}"
        else:
            score = 50
            reason = f"非政策热点行业({sector})"
        return score, reason
    
    def score_fundamental(self, row: pd.Series) -> Tuple[float, str, Dict]:
        """
        基本面评分 (0-100分)
        考虑PE、PB、市值等因素
        """
        score = 0
        details = []
        
        # PE评分 (0-35分)
        pe = float(row['市盈率-动态']) if pd.notna(row['市盈率-动态']) else 0
        if 10 <= pe <= 30:
            pe_score = 35
            details.append(f"PE({pe:.1f})优秀")
        elif 30 < pe <= 50:
            pe_score = 25
            details.append(f"PE({pe:.1f})合理")
        elif 50 < pe <= 80:
            pe_score = 15
            details.append(f"PE({pe:.1f})偏高")
        elif pe > 80 or pe <= 0:
            pe_score = 5
            details.append(f"PE({pe:.1f})异常")
        else:
            pe_score = 20
            details.append(f"PE({pe:.1f})偏低")
        score += pe_score
        
        # PB评分 (0-25分)
        pb = float(row['市净率']) if pd.notna(row['市净率']) else 0
        if 1 <= pb <= 3:
            pb_score = 25
            details.append(f"PB({pb:.2f})优秀")
        elif 3 < pb <= 5:
            pb_score = 18
            details.append(f"PB({pb:.2f})合理")
        elif pb > 5:
            pb_score = 10
            details.append(f"PB({pb:.2f})偏高")
        else:
            pb_score = 15
            details.append(f"PB({pb:.2f})偏低")
        score += pb_score
        
        # 市值评分 (0-25分) - 中等市值最佳
        market_cap = float(row['总市值']) / 1e8 if pd.notna(row['总市值']) else 0
        if 100 <= market_cap <= 500:
            cap_score = 25
            details.append(f"市值({market_cap:.0f}亿)中等偏大")
        elif 500 < market_cap <= 1000:
            cap_score = 20
            details.append(f"市值({market_cap:.0f}亿)大盘")
        elif 50 <= market_cap < 100:
            cap_score = 18
            details.append(f"市值({market_cap:.0f}亿)中小盘")
        elif market_cap > 1000:
            cap_score = 15
            details.append(f"市值({market_cap:.0f}亿)超大盘")
        else:
            cap_score = 10
            details.append(f"市值({market_cap:.0f}亿)小盘")
        score += cap_score
        
        # 流通市值评分 (0-15分)
        circ_cap = float(row['流通市值']) / 1e8 if pd.notna(row['流通市值']) else 0
        if 50 <= circ_cap <= 300:
            circ_score = 15
            details.append(f"流通({circ_cap:.0f}亿)适中")
        elif 300 < circ_cap <= 600:
            circ_score = 12
            details.append(f"流通({circ_cap:.0f}亿)较大")
        else:
            circ_score = 8
        score += circ_score
        
        reason = "；".join(details)
        metrics = {'pe': pe, 'pb': pb, 'market_cap': market_cap, 'circ_cap': circ_cap}
        return min(100, score), reason, metrics
    
    def score_sentiment(self, row: pd.Series) -> Tuple[float, str, Dict]:
        """
        情绪面评分 (0-100分)
        考虑量比、换手率、涨跌幅、振幅等
        """
        score = 0
        details = []
        
        # 量比评分 (0-30分) - 温和放量最佳
        volume_ratio = float(row['量比']) if pd.notna(row['量比']) else 0
        if 1.2 <= volume_ratio <= 2.5:
            vr_score = 30
            details.append(f"量比({volume_ratio:.2f})温和放量")
        elif 2.5 < volume_ratio <= 4:
            vr_score = 22
            details.append(f"量比({volume_ratio:.2f})明显放量")
        elif 0.8 <= volume_ratio < 1.2:
            vr_score = 18
            details.append(f"量比({volume_ratio:.2f})正常")
        elif volume_ratio > 4:
            vr_score = 10
            details.append(f"量比({volume_ratio:.2f})异常放量")
        else:
            vr_score = 8
            details.append(f"量比({volume_ratio:.2f})缩量")
        score += vr_score
        
        # 换手率评分 (0-30分)
        turnover = float(row['换手率']) if pd.notna(row['换手率']) else 0
        if 2 <= turnover <= 6:
            tr_score = 30
            details.append(f"换手({turnover:.2f}%)健康")
        elif 6 < turnover <= 10:
            tr_score = 22
            details.append(f"换手({turnover:.2f}%)活跃")
        elif 1 <= turnover < 2:
            tr_score = 15
            details.append(f"换手({turnover:.2f}%)偏低")
        elif turnover > 10:
            tr_score = 10
            details.append(f"换手({turnover:.2f}%)过高")
        else:
            tr_score = 8
            details.append(f"换手({turnover:.2f}%)低迷")
        score += tr_score
        
        # 当日涨跌幅评分 (0-25分)
        change_pct = float(row['涨跌幅']) if pd.notna(row['涨跌幅']) else 0
        if 0 < change_pct <= 3:
            chg_score = 25
            details.append(f"涨幅({change_pct:.2f}%)温和上涨")
        elif 3 < change_pct <= 6:
            chg_score = 20
            details.append(f"涨幅({change_pct:.2f}%)强势")
        elif -2 <= change_pct <= 0:
            chg_score = 18
            details.append(f"涨幅({change_pct:.2f}%)小幅调整")
        elif change_pct > 6:
            chg_score = 12
            details.append(f"涨幅({change_pct:.2f}%)涨幅过大")
        else:
            chg_score = 10
            details.append(f"涨幅({change_pct:.2f}%)下跌")
        score += chg_score
        
        # 振幅评分 (0-15分)
        amplitude = float(row['振幅']) if pd.notna(row['振幅']) else 0
        if 2 <= amplitude <= 5:
            amp_score = 15
            details.append(f"振幅({amplitude:.2f}%)适中")
        elif 5 < amplitude <= 8:
            amp_score = 10
            details.append(f"振幅({amplitude:.2f}%)较大")
        else:
            amp_score = 8
        score += amp_score
        
        reason = "；".join(details)
        metrics = {'volume_ratio': volume_ratio, 'turnover': turnover, 'change_pct': change_pct, 'amplitude': amplitude}
        return min(100, score), reason, metrics
    
    def score_technical(self, row: pd.Series, hist_df: pd.DataFrame) -> Tuple[float, str, Dict]:
        """
        技术面评分 (0-100分)
        考虑均线、RSI、MACD等
        """
        score = 0
        details = []
        metrics = {}
        
        price = float(row['最新价']) if pd.notna(row['最新价']) else 0
        
        if hist_df.empty or len(hist_df) < 20:
            return 50, "历史数据不足", {'price': price}
        
        closes = hist_df['close'].astype(float)
        
        # 计算均线
        ma5 = closes.tail(5).mean()
        ma10 = closes.tail(10).mean()
        ma20 = closes.tail(20).mean()
        
        # 均线多头排列评分 (0-30分)
        if price > ma5 > ma10 > ma20:
            ma_score = 30
            details.append("均线完美多头排列")
        elif price > ma5 > ma10:
            ma_score = 25
            details.append("短期均线多头")
        elif price > ma5:
            ma_score = 18
            details.append("站上MA5")
        elif price > ma20:
            ma_score = 12
            details.append("站上MA20")
        else:
            ma_score = 5
            details.append("均线空头")
        score += ma_score
        
        # RSI评分 (0-30分)
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
            rsi_score = 30
            details.append(f"RSI({rsi:.0f})健康区间")
        elif 35 <= rsi < 45:
            rsi_score = 25
            details.append(f"RSI({rsi:.0f})偏低有反弹空间")
        elif 65 < rsi <= 75:
            rsi_score = 20
            details.append(f"RSI({rsi:.0f})偏强")
        elif rsi > 75:
            rsi_score = 10
            details.append(f"RSI({rsi:.0f})超买风险")
        else:
            rsi_score = 15
            details.append(f"RSI({rsi:.0f})超卖")
        score += rsi_score
        
        # MACD评分 (0-25分)
        if len(closes) >= 26:
            ema12 = closes.ewm(span=12, adjust=False).mean()
            ema26 = closes.ewm(span=26, adjust=False).mean()
            dif = ema12 - ema26
            dea = dif.ewm(span=9, adjust=False).mean()
            macd = 2 * (dif - dea)
            dif_val = dif.iloc[-1]
            dea_val = dea.iloc[-1]
            macd_val = macd.iloc[-1]
        else:
            dif_val, dea_val, macd_val = 0, 0, 0
        
        if dif_val > dea_val and macd_val > 0:
            macd_score = 25
            details.append("MACD金叉+红柱")
        elif dif_val > dea_val:
            macd_score = 20
            details.append("MACD金叉")
        elif dif_val > 0:
            macd_score = 15
            details.append("DIF在零轴上")
        else:
            macd_score = 8
            details.append("MACD偏弱")
        score += macd_score
        
        # 近期涨幅评分 (0-15分)
        if len(closes) >= 5:
            change_5d = (price - closes.iloc[-5]) / closes.iloc[-5] * 100
        else:
            change_5d = 0
        
        if 0 < change_5d <= 8:
            trend_score = 15
            details.append(f"5日涨({change_5d:.1f}%)温和")
        elif -5 <= change_5d <= 0:
            trend_score = 12
            details.append(f"5日跌({change_5d:.1f}%)小幅调整")
        elif change_5d > 8:
            trend_score = 8
            details.append(f"5日涨({change_5d:.1f}%)涨幅较大")
        else:
            trend_score = 5
            details.append(f"5日跌({change_5d:.1f}%)下跌")
        score += trend_score
        
        reason = "；".join(details)
        metrics = {
            'price': price, 'ma5': ma5, 'ma10': ma10, 'ma20': ma20,
            'rsi': rsi, 'dif': dif_val, 'dea': dea_val, 'macd': macd_val,
            'change_5d': change_5d
        }
        return min(100, score), reason, metrics
    
    def calculate_comprehensive_score(self, policy_score: float, fundamental_score: float, 
                                       sentiment_score: float, technical_score: float) -> float:
        """
        计算综合得分
        权重: 政策面15% + 基本面25% + 情绪面25% + 技术面35%
        """
        return (
            policy_score * 0.15 +
            fundamental_score * 0.25 +
            sentiment_score * 0.25 +
            technical_score * 0.35
        )
    
    def screen_stocks(self, codes: List[str]) -> List[Dict]:
        """筛选股票并评分"""
        print(f"\n📊 正在获取 {len(codes)} 只股票的实时数据...")
        
        # 获取实时数据
        realtime_df = self.get_realtime_data(codes)
        print(f"   成功获取 {len(realtime_df)} 只股票数据")
        
        results = []
        total = len(realtime_df)
        
        for idx, (_, row) in enumerate(realtime_df.iterrows(), 1):
            code = row['代码']
            name = row['名称']
            
            if idx % 20 == 0:
                print(f"   处理进度: {idx}/{total}")
            
            try:
                # 获取历史数据
                hist_df = self.get_history_data(code)
                
                # 四维度评分
                policy_score, policy_reason = self.score_policy(code)
                fundamental_score, fundamental_reason, fundamental_metrics = self.score_fundamental(row)
                sentiment_score, sentiment_reason, sentiment_metrics = self.score_sentiment(row)
                technical_score, technical_reason, technical_metrics = self.score_technical(row, hist_df)
                
                # 综合得分
                total_score = self.calculate_comprehensive_score(
                    policy_score, fundamental_score, sentiment_score, technical_score
                )
                
                results.append({
                    'code': code,
                    'name': name,
                    'sector': get_stock_sector(code),
                    'price': float(row['最新价']) if pd.notna(row['最新价']) else 0,
                    'change_pct': float(row['涨跌幅']) if pd.notna(row['涨跌幅']) else 0,
                    'total_score': total_score,
                    'policy_score': policy_score,
                    'policy_reason': policy_reason,
                    'fundamental_score': fundamental_score,
                    'fundamental_reason': fundamental_reason,
                    'fundamental_metrics': fundamental_metrics,
                    'sentiment_score': sentiment_score,
                    'sentiment_reason': sentiment_reason,
                    'sentiment_metrics': sentiment_metrics,
                    'technical_score': technical_score,
                    'technical_reason': technical_reason,
                    'technical_metrics': technical_metrics,
                })
            except Exception as e:
                print(f"   ⚠️ {code} {name} 分析失败: {e}")
                continue
        
        # 按综合得分排序
        results.sort(key=lambda x: x['total_score'], reverse=True)
        return results
    
    def get_top5(self, results: List[Dict]) -> List[Dict]:
        """获取TOP5股票"""
        return results[:5]
    
    def print_top5_report(self, top5: List[Dict]):
        """打印TOP5详细报告"""
        print("\n" + "=" * 80)
        print("🏆 四维度综合评分 TOP 5 股票推荐")
        print(f"📅 分析日期: {self.analysis_date}")
        print("=" * 80)
        
        print("\n📊 评分权重说明:")
        print("   政策面(15%) + 基本面(25%) + 情绪面(25%) + 技术面(35%)")
        
        for i, stock in enumerate(top5, 1):
            print(f"\n{'─' * 80}")
            print(f"🥇 第{i}名: {stock['code']} {stock['name']}")
            print(f"   行业: {stock['sector']} | 现价: {stock['price']:.2f}元 | 涨跌: {stock['change_pct']:+.2f}%")
            print(f"\n   🎯 综合得分: {stock['total_score']:.1f}/100")
            print(f"\n   📋 四维度得分明细:")
            print(f"      政策面: {stock['policy_score']:.0f}分 - {stock['policy_reason']}")
            print(f"      基本面: {stock['fundamental_score']:.0f}分 - {stock['fundamental_reason']}")
            print(f"      情绪面: {stock['sentiment_score']:.0f}分 - {stock['sentiment_reason']}")
            print(f"      技术面: {stock['technical_score']:.0f}分 - {stock['technical_reason']}")
            
            # 关键指标
            fm = stock['fundamental_metrics']
            sm = stock['sentiment_metrics']
            tm = stock['technical_metrics']
            
            print(f"\n   📈 关键指标:")
            print(f"      PE: {fm['pe']:.1f} | PB: {fm['pb']:.2f} | 市值: {fm['market_cap']:.0f}亿")
            print(f"      量比: {sm['volume_ratio']:.2f} | 换手率: {sm['turnover']:.2f}%")
            if 'rsi' in tm:
                print(f"      RSI: {tm['rsi']:.0f} | 5日涨幅: {tm.get('change_5d', 0):.1f}%")
            
            # 操作建议
            score = stock['total_score']
            price = stock['price']
            print(f"\n   💡 操作建议:")
            if score >= 70:
                print(f"      ✅ 强烈推荐买入，建议仓位: 8-10%")
            elif score >= 60:
                print(f"      ✅ 推荐买入，建议仓位: 5-8%")
            elif score >= 55:
                print(f"      ⏳ 可少量试仓，建议仓位: 3-5%")
            else:
                print(f"      ⏳ 观望为主，等待更好时机")
            
            stop_loss = price * 0.954
            target1 = price * 1.05
            target2 = price * 1.08
            print(f"      止损价: {stop_loss:.2f}元(-4.6%) | 目标价: {target1:.2f}元(+5%) / {target2:.2f}元(+8%)")
        
        # 汇总表格
        print(f"\n{'=' * 80}")
        print("📊 TOP 5 汇总排名")
        print("=" * 80)
        print(f"\n{'排名':<4} {'代码':<8} {'名称':<10} {'行业':<10} {'综合分':<8} {'政策':<6} {'基本':<6} {'情绪':<6} {'技术':<6}")
        print("-" * 80)
        for i, s in enumerate(top5, 1):
            print(f"{i:<4} {s['code']:<8} {s['name']:<10} {s['sector']:<10} "
                  f"{s['total_score']:<8.1f} {s['policy_score']:<6.0f} {s['fundamental_score']:<6.0f} "
                  f"{s['sentiment_score']:<6.0f} {s['technical_score']:<6.0f}")
        
        # 投资建议
        print(f"\n{'=' * 80}")
        print("💰 明日投资建议")
        print("=" * 80)
        
        best = top5[0]
        print(f"\n🥇 首选推荐: {best['code']} {best['name']} ({best['sector']})")
        print(f"   综合得分: {best['total_score']:.1f}分")
        print(f"   推荐理由: {best['policy_reason']}；{best['technical_reason']}")
        
        if len(top5) > 1:
            second = top5[1]
            print(f"\n🥈 次选推荐: {second['code']} {second['name']} ({second['sector']})")
            print(f"   综合得分: {second['total_score']:.1f}分")
        
        print("\n⚠️ 风险提示:")
        print("   1. 以上分析基于历史数据和当前市场状态，不构成投资建议")
        print("   2. 请结合大盘走势和个人风险承受能力做出决策")
        print("   3. 严格执行止损纪律，单只股票仓位不超过10%")
        print("   4. 建议开盘后观察30分钟再决定是否买入")


def main():
    """主函数"""
    print("=" * 80)
    print("🔬 专业四维度股票筛选系统")
    print("   政策面 + 基本面 + 情绪面 + 技术面 综合评分")
    print(f"📅 分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # 获取科技股池
    all_codes = get_all_tech_stocks()
    print(f"\n📋 科技股池共 {len(all_codes)} 只股票")
    
    # 创建筛选器
    screener = ProfessionalStockScreener()
    
    # 筛选评分
    results = screener.screen_stocks(all_codes)
    print(f"\n✅ 成功分析 {len(results)} 只股票")
    
    # 获取TOP5
    top5 = screener.get_top5(results)
    
    # 打印报告
    screener.print_top5_report(top5)
    
    return top5


if __name__ == "__main__":
    main()
