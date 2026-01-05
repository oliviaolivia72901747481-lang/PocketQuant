#!/usr/bin/env python3
"""
股票精细化评分分析工具

对指定股票进行多维度深度分析，包括：
- 技术面分析 (MA、RSI、MACD、布林带等)
- 资金面分析 (量比、换手率、主力资金等)
- 估值分析 (PE、PB、市值等)
- 趋势分析 (短期、中期、长期趋势)

作者: Kiro
日期: 2026-01-05
"""

import sys
sys.path.insert(0, '.')

import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from config.tech_stock_pool import get_stock_name, get_stock_sector


class DetailedStockAnalyzer:
    """股票精细化分析器"""
    
    def __init__(self):
        self.analysis_date = datetime.now().strftime("%Y-%m-%d")
    
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """计算RSI"""
        if len(prices) < period + 1:
            return 50.0
        delta = prices.diff()
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50.0

    def calculate_macd(self, prices: pd.Series) -> Tuple[float, float, float]:
        """计算MACD"""
        if len(prices) < 26:
            return 0, 0, 0
        ema12 = prices.ewm(span=12, adjust=False).mean()
        ema26 = prices.ewm(span=26, adjust=False).mean()
        dif = ema12 - ema26
        dea = dif.ewm(span=9, adjust=False).mean()
        macd = 2 * (dif - dea)
        return dif.iloc[-1], dea.iloc[-1], macd.iloc[-1]
    
    def calculate_bollinger(self, prices: pd.Series, period: int = 20) -> Tuple[float, float, float]:
        """计算布林带"""
        if len(prices) < period:
            return 0, 0, 0
        ma = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        upper = ma + 2 * std
        lower = ma - 2 * std
        return upper.iloc[-1], ma.iloc[-1], lower.iloc[-1]
    
    def get_stock_data(self, code: str) -> Optional[pd.DataFrame]:
        """获取股票历史数据"""
        try:
            df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq")
            if df is None or len(df) < 60:
                return None
            df = df.rename(columns={
                '日期': 'date', '开盘': 'open', '收盘': 'close',
                '最高': 'high', '最低': 'low', '成交量': 'volume',
                '成交额': 'turnover', '涨跌幅': 'change_pct', '换手率': 'turnover_rate'
            })
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').reset_index(drop=True)
            return df
        except Exception as e:
            print(f"获取{code}数据失败: {e}")
            return None
    
    def get_realtime_data(self, code: str) -> Optional[Dict]:
        """获取实时行情数据"""
        try:
            df = ak.stock_zh_a_spot_em()
            row = df[df['代码'] == code].iloc[0]
            return {
                'price': float(row['最新价']),
                'change_pct': float(row['涨跌幅']),
                'volume_ratio': float(row['量比']) if pd.notna(row['量比']) else 0,
                'turnover_rate': float(row['换手率']),
                'pe': float(row['市盈率-动态']) if pd.notna(row['市盈率-动态']) else 0,
                'pb': float(row['市净率']) if pd.notna(row['市净率']) else 0,
                'market_cap': float(row['总市值']) / 100000000,
                'circulating_cap': float(row['流通市值']) / 100000000,
                'high': float(row['最高']),
                'low': float(row['最低']),
                'open': float(row['今开']),
                'amplitude': float(row['振幅']) if pd.notna(row['振幅']) else 0,
            }
        except Exception as e:
            print(f"获取{code}实时数据失败: {e}")
            return None

    def analyze_technical(self, df: pd.DataFrame, realtime: Dict) -> Dict:
        """技术面分析"""
        # 计算均线
        df['ma5'] = df['close'].rolling(5).mean()
        df['ma10'] = df['close'].rolling(10).mean()
        df['ma20'] = df['close'].rolling(20).mean()
        df['ma60'] = df['close'].rolling(60).mean()
        
        latest = df.iloc[-1]
        price = realtime['price']
        
        # 均线位置
        ma5 = latest['ma5']
        ma10 = latest['ma10']
        ma20 = latest['ma20']
        ma60 = latest['ma60']
        
        # RSI
        rsi = self.calculate_rsi(df['close'], 14)
        rsi6 = self.calculate_rsi(df['close'], 6)
        
        # MACD
        dif, dea, macd = self.calculate_macd(df['close'])
        
        # 布林带
        boll_upper, boll_mid, boll_lower = self.calculate_bollinger(df['close'])
        
        # 计算技术得分
        tech_score = 0
        tech_details = []
        
        # 均线多头排列 (MA5>MA10>MA20>MA60)
        if ma5 > ma10 > ma20:
            tech_score += 15
            tech_details.append("短期均线多头排列 +15")
        if price > ma60:
            tech_score += 10
            tech_details.append("股价站上MA60 +10")
        
        # RSI评分
        if 45 <= rsi <= 65:
            tech_score += 15
            tech_details.append(f"RSI({rsi:.1f})处于健康区间 +15")
        elif 30 <= rsi < 45:
            tech_score += 10
            tech_details.append(f"RSI({rsi:.1f})偏低有反弹空间 +10")
        elif rsi > 70:
            tech_score -= 5
            tech_details.append(f"RSI({rsi:.1f})超买风险 -5")
        
        # MACD评分
        if dif > dea and macd > 0:
            tech_score += 15
            tech_details.append("MACD金叉且红柱 +15")
        elif dif > dea:
            tech_score += 10
            tech_details.append("MACD金叉 +10")
        
        # 布林带位置
        boll_position = (price - boll_lower) / (boll_upper - boll_lower) * 100 if boll_upper != boll_lower else 50
        if 30 <= boll_position <= 70:
            tech_score += 10
            tech_details.append(f"布林带位置({boll_position:.0f}%)适中 +10")
        
        return {
            'score': min(100, max(0, tech_score)),
            'details': tech_details,
            'ma5': ma5, 'ma10': ma10, 'ma20': ma20, 'ma60': ma60,
            'rsi': rsi, 'rsi6': rsi6,
            'dif': dif, 'dea': dea, 'macd': macd,
            'boll_upper': boll_upper, 'boll_mid': boll_mid, 'boll_lower': boll_lower,
            'boll_position': boll_position
        }

    def analyze_capital(self, df: pd.DataFrame, realtime: Dict) -> Dict:
        """资金面分析"""
        # 计算成交量均线
        df['vol_ma5'] = df['volume'].rolling(5).mean()
        df['vol_ma10'] = df['volume'].rolling(10).mean()
        
        latest = df.iloc[-1]
        volume_ratio = realtime['volume_ratio']
        turnover_rate = realtime['turnover_rate']
        
        capital_score = 0
        capital_details = []
        
        # 量比评分
        if 1.2 <= volume_ratio <= 2.5:
            capital_score += 20
            capital_details.append(f"量比({volume_ratio:.2f})温和放量 +20")
        elif 2.5 < volume_ratio <= 4:
            capital_score += 15
            capital_details.append(f"量比({volume_ratio:.2f})明显放量 +15")
        elif volume_ratio > 4:
            capital_score += 5
            capital_details.append(f"量比({volume_ratio:.2f})异常放量需警惕 +5")
        elif 0.8 <= volume_ratio < 1.2:
            capital_score += 10
            capital_details.append(f"量比({volume_ratio:.2f})正常 +10")
        
        # 换手率评分
        if 2 <= turnover_rate <= 6:
            capital_score += 20
            capital_details.append(f"换手率({turnover_rate:.2f}%)健康 +20")
        elif 6 < turnover_rate <= 10:
            capital_score += 15
            capital_details.append(f"换手率({turnover_rate:.2f}%)活跃 +15")
        elif turnover_rate > 10:
            capital_score += 5
            capital_details.append(f"换手率({turnover_rate:.2f}%)过高需警惕 +5")
        elif 1 <= turnover_rate < 2:
            capital_score += 10
            capital_details.append(f"换手率({turnover_rate:.2f}%)偏低 +10")
        
        # 成交量趋势
        vol_ma5 = latest['vol_ma5']
        vol_ma10 = latest['vol_ma10']
        if vol_ma5 > vol_ma10:
            capital_score += 10
            capital_details.append("成交量短期放大 +10")
        
        return {
            'score': min(100, max(0, capital_score)),
            'details': capital_details,
            'volume_ratio': volume_ratio,
            'turnover_rate': turnover_rate,
            'vol_ma5': vol_ma5,
            'vol_ma10': vol_ma10
        }
    
    def analyze_valuation(self, realtime: Dict) -> Dict:
        """估值分析"""
        pe = realtime['pe']
        pb = realtime['pb']
        market_cap = realtime['market_cap']
        
        valuation_score = 0
        valuation_details = []
        
        # PE评分
        if 15 <= pe <= 35:
            valuation_score += 25
            valuation_details.append(f"PE({pe:.1f})估值合理 +25")
        elif 35 < pe <= 60:
            valuation_score += 15
            valuation_details.append(f"PE({pe:.1f})估值偏高但可接受 +15")
        elif 0 < pe < 15:
            valuation_score += 20
            valuation_details.append(f"PE({pe:.1f})估值较低 +20")
        elif pe > 60:
            valuation_score += 5
            valuation_details.append(f"PE({pe:.1f})估值偏高 +5")
        elif pe <= 0:
            valuation_details.append(f"PE({pe:.1f})亏损或异常")
        
        # PB评分
        if 1 <= pb <= 4:
            valuation_score += 15
            valuation_details.append(f"PB({pb:.2f})合理 +15")
        elif pb < 1:
            valuation_score += 10
            valuation_details.append(f"PB({pb:.2f})破净 +10")
        elif pb > 4:
            valuation_score += 5
            valuation_details.append(f"PB({pb:.2f})偏高 +5")
        
        # 市值评分
        if 100 <= market_cap <= 500:
            valuation_score += 15
            valuation_details.append(f"市值({market_cap:.0f}亿)中等偏大 +15")
        elif 500 < market_cap <= 1000:
            valuation_score += 10
            valuation_details.append(f"市值({market_cap:.0f}亿)大盘股 +10")
        elif 50 <= market_cap < 100:
            valuation_score += 10
            valuation_details.append(f"市值({market_cap:.0f}亿)中小盘 +10")
        elif market_cap > 1000:
            valuation_score += 5
            valuation_details.append(f"市值({market_cap:.0f}亿)超大盘 +5")
        
        return {
            'score': min(100, max(0, valuation_score)),
            'details': valuation_details,
            'pe': pe, 'pb': pb, 'market_cap': market_cap
        }

    def analyze_trend(self, df: pd.DataFrame, realtime: Dict) -> Dict:
        """趋势分析"""
        price = realtime['price']
        
        # 计算不同周期涨跌幅
        if len(df) >= 5:
            change_5d = (price - df.iloc[-5]['close']) / df.iloc[-5]['close'] * 100
        else:
            change_5d = 0
        
        if len(df) >= 10:
            change_10d = (price - df.iloc[-10]['close']) / df.iloc[-10]['close'] * 100
        else:
            change_10d = 0
        
        if len(df) >= 20:
            change_20d = (price - df.iloc[-20]['close']) / df.iloc[-20]['close'] * 100
        else:
            change_20d = 0
        
        if len(df) >= 60:
            change_60d = (price - df.iloc[-60]['close']) / df.iloc[-60]['close'] * 100
        else:
            change_60d = 0
        
        trend_score = 0
        trend_details = []
        
        # 短期趋势 (5日)
        if 0 < change_5d <= 10:
            trend_score += 15
            trend_details.append(f"5日涨幅({change_5d:.1f}%)温和上涨 +15")
        elif -5 <= change_5d <= 0:
            trend_score += 10
            trend_details.append(f"5日涨幅({change_5d:.1f}%)小幅调整 +10")
        elif change_5d > 10:
            trend_score += 5
            trend_details.append(f"5日涨幅({change_5d:.1f}%)涨幅较大 +5")
        
        # 中期趋势 (20日)
        if 0 < change_20d <= 15:
            trend_score += 15
            trend_details.append(f"20日涨幅({change_20d:.1f}%)中期向好 +15")
        elif -10 <= change_20d <= 0:
            trend_score += 10
            trend_details.append(f"20日涨幅({change_20d:.1f}%)中期调整 +10")
        elif change_20d > 15:
            trend_score += 5
            trend_details.append(f"20日涨幅({change_20d:.1f}%)中期涨幅大 +5")
        
        # 长期趋势 (60日)
        if change_60d > 0:
            trend_score += 10
            trend_details.append(f"60日涨幅({change_60d:.1f}%)长期向上 +10")
        elif change_60d > -20:
            trend_score += 5
            trend_details.append(f"60日涨幅({change_60d:.1f}%)长期震荡 +5")
        
        return {
            'score': min(100, max(0, trend_score)),
            'details': trend_details,
            'change_5d': change_5d,
            'change_10d': change_10d,
            'change_20d': change_20d,
            'change_60d': change_60d
        }
    
    def calculate_risk_level(self, tech: Dict, capital: Dict, valuation: Dict, trend: Dict) -> Tuple[str, List[str]]:
        """计算风险等级"""
        risks = []
        
        # RSI风险
        if tech['rsi'] > 75:
            risks.append("RSI超买，短期回调风险")
        elif tech['rsi'] < 30:
            risks.append("RSI超卖，可能继续下跌")
        
        # 换手率风险
        if capital['turnover_rate'] > 12:
            risks.append("换手率过高，波动风险大")
        
        # 估值风险
        if valuation['pe'] > 80:
            risks.append("PE过高，估值风险")
        
        # 趋势风险
        if trend['change_5d'] > 15:
            risks.append("短期涨幅过大，追高风险")
        if trend['change_60d'] < -30:
            risks.append("长期下跌趋势，反弹可能有限")
        
        if len(risks) == 0:
            return "低", ["各项指标正常，风险可控"]
        elif len(risks) == 1:
            return "中低", risks
        elif len(risks) == 2:
            return "中", risks
        else:
            return "高", risks

    def analyze_stock(self, code: str) -> Optional[Dict]:
        """分析单只股票"""
        print(f"\n正在分析 {code} {get_stock_name(code)}...")
        
        # 获取数据
        df = self.get_stock_data(code)
        if df is None:
            return None
        
        realtime = self.get_realtime_data(code)
        if realtime is None:
            return None
        
        # 各维度分析
        tech = self.analyze_technical(df, realtime)
        capital = self.analyze_capital(df, realtime)
        valuation = self.analyze_valuation(realtime)
        trend = self.analyze_trend(df, realtime)
        
        # 计算综合得分 (加权平均)
        total_score = (
            tech['score'] * 0.30 +      # 技术面 30%
            capital['score'] * 0.25 +   # 资金面 25%
            valuation['score'] * 0.25 + # 估值 25%
            trend['score'] * 0.20       # 趋势 20%
        )
        
        # 风险评估
        risk_level, risk_details = self.calculate_risk_level(tech, capital, valuation, trend)
        
        return {
            'code': code,
            'name': get_stock_name(code),
            'sector': get_stock_sector(code),
            'price': realtime['price'],
            'change_pct': realtime['change_pct'],
            'total_score': total_score,
            'tech': tech,
            'capital': capital,
            'valuation': valuation,
            'trend': trend,
            'risk_level': risk_level,
            'risk_details': risk_details,
            'realtime': realtime
        }
    
    def print_analysis_report(self, result: Dict):
        """打印分析报告"""
        print("\n" + "=" * 70)
        print(f"📊 {result['code']} {result['name']} 精细化分析报告")
        print(f"   行业: {result['sector']}  |  现价: {result['price']:.2f}元  |  涨跌: {result['change_pct']:+.2f}%")
        print("=" * 70)
        
        # 综合评分
        score = result['total_score']
        if score >= 70:
            grade = "⭐⭐⭐⭐⭐ 强烈推荐"
        elif score >= 60:
            grade = "⭐⭐⭐⭐ 推荐关注"
        elif score >= 50:
            grade = "⭐⭐⭐ 可以关注"
        elif score >= 40:
            grade = "⭐⭐ 谨慎观望"
        else:
            grade = "⭐ 暂不推荐"
        
        print(f"\n🎯 综合评分: {score:.1f}/100  {grade}")
        print(f"   风险等级: {result['risk_level']}")
        
        # 技术面
        tech = result['tech']
        print(f"\n📈 技术面得分: {tech['score']}/100")
        for detail in tech['details']:
            print(f"   • {detail}")
        print(f"   RSI: {tech['rsi']:.1f} | MACD: DIF={tech['dif']:.3f} DEA={tech['dea']:.3f}")
        print(f"   布林带位置: {tech['boll_position']:.0f}%")
        
        # 资金面
        capital = result['capital']
        print(f"\n💰 资金面得分: {capital['score']}/100")
        for detail in capital['details']:
            print(f"   • {detail}")
        
        # 估值
        valuation = result['valuation']
        print(f"\n📉 估值得分: {valuation['score']}/100")
        for detail in valuation['details']:
            print(f"   • {detail}")
        
        # 趋势
        trend = result['trend']
        print(f"\n📊 趋势得分: {trend['score']}/100")
        for detail in trend['details']:
            print(f"   • {detail}")
        print(f"   5日: {trend['change_5d']:+.1f}% | 10日: {trend['change_10d']:+.1f}% | 20日: {trend['change_20d']:+.1f}% | 60日: {trend['change_60d']:+.1f}%")
        
        # 风险提示
        print(f"\n⚠️ 风险提示:")
        for risk in result['risk_details']:
            print(f"   • {risk}")
        
        # 操作建议
        print(f"\n💡 操作建议:")
        if score >= 65 and result['risk_level'] in ['低', '中低']:
            print(f"   ✅ 可考虑买入，建议仓位: 8-10%")
            stop_loss = result['price'] * 0.954
            target1 = result['price'] * 1.05
            target2 = result['price'] * 1.08
            print(f"   止损价: {stop_loss:.2f}元 (-4.6%)")
            print(f"   目标价: {target1:.2f}元 (+5%) / {target2:.2f}元 (+8%)")
        elif score >= 55:
            print(f"   ⏳ 可少量试仓，建议仓位: 5%以内")
            print(f"   等待更好的买点或确认信号")
        else:
            print(f"   ❌ 暂不建议买入，继续观察")


def main():
    """主函数"""
    print("=" * 70)
    print("🔬 股票精细化评分分析系统")
    print(f"📅 分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # 待分析的5只股票
    stocks_to_analyze = [
        "002185",  # 华天科技
        "000661",  # 长春高新
        "002273",  # 水晶光电
        "603169",  # 兰石重装
        "002241",  # 歌尔股份
    ]
    
    analyzer = DetailedStockAnalyzer()
    results = []
    
    for code in stocks_to_analyze:
        result = analyzer.analyze_stock(code)
        if result:
            results.append(result)
            analyzer.print_analysis_report(result)
    
    # 汇总排名
    if results:
        print("\n" + "=" * 70)
        print("🏆 综合排名汇总")
        print("=" * 70)
        
        results.sort(key=lambda x: x['total_score'], reverse=True)
        
        print(f"\n{'排名':<4} {'代码':<8} {'名称':<12} {'综合得分':<10} {'技术面':<8} {'资金面':<8} {'估值':<8} {'趋势':<8} {'风险':<6}")
        print("-" * 80)
        
        for i, r in enumerate(results, 1):
            print(f"{i:<4} {r['code']:<8} {r['name']:<12} {r['total_score']:<10.1f} "
                  f"{r['tech']['score']:<8} {r['capital']['score']:<8} "
                  f"{r['valuation']['score']:<8} {r['trend']['score']:<8} {r['risk_level']:<6}")
        
        print("\n" + "=" * 70)
        print("📋 投资建议总结")
        print("=" * 70)
        
        best = results[0]
        print(f"\n🥇 首选推荐: {best['code']} {best['name']}")
        print(f"   综合得分: {best['total_score']:.1f}分 | 风险等级: {best['risk_level']}")
        print(f"   现价: {best['price']:.2f}元 | 止损: {best['price']*0.954:.2f}元 | 目标: {best['price']*1.06:.2f}元")
        
        if len(results) > 1:
            second = results[1]
            print(f"\n🥈 次选推荐: {second['code']} {second['name']}")
            print(f"   综合得分: {second['total_score']:.1f}分 | 风险等级: {second['risk_level']}")
        
        print("\n⚠️ 重要提示:")
        print("   1. 以上分析仅供参考，不构成投资建议")
        print("   2. 请结合大盘走势和自身风险承受能力决策")
        print("   3. 严格执行止损纪律，控制单只股票仓位")
        print("   4. 建议在开盘30分钟后观察走势再决定")


if __name__ == "__main__":
    main()
