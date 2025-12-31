"""
科技股实时筛选工具

根据v11.4g策略筛选午后最值得关注的科技股
"""
import sys
sys.path.insert(0, '.')

import pandas as pd
import numpy as np
from datetime import datetime, date
import warnings
warnings.filterwarnings('ignore')

# 导入配置
from config.tech_stock_pool import get_all_tech_stocks, get_stock_name, get_stock_sector

def calculate_rsi(prices: pd.Series, period: int = 14) -> float:
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


def screen_tech_stocks():
    """筛选科技股"""
    print("=" * 60)
    print("科技股实时筛选 - v11.4g策略")
    print(f"筛选时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    try:
        import akshare as ak
    except ImportError:
        print("❌ 请先安装 akshare: pip install akshare")
        return
    
    # 获取股票池
    stock_codes = get_all_tech_stocks()
    print(f"\n📊 股票池: {len(stock_codes)} 只科技股")
    
    # 筛选结果
    candidates = []
    
    print("\n🔍 正在筛选...")
    
    for i, code in enumerate(stock_codes):
        try:
            # 获取日线数据
            df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq")
            
            if df is None or len(df) < 60:
                continue
            
            # 重命名列 (akshare返回中文列名)
            df = df.rename(columns={
                '日期': 'date',
                '股票代码': 'code_col',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume',
                '成交额': 'turnover',
                '振幅': 'amplitude',
                '涨跌幅': 'change_pct',
                '涨跌额': 'change',
                '换手率': 'turnover_rate'
            })
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').reset_index(drop=True)
            
            # 计算技术指标
            df['ma5'] = df['close'].rolling(5).mean()
            df['ma20'] = df['close'].rolling(20).mean()
            df['ma60'] = df['close'].rolling(60).mean()
            df['avg_vol_5d'] = df['volume'].rolling(5).mean()
            
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            
            price = latest['close']
            ma5 = latest['ma5']
            ma20 = latest['ma20']
            ma60 = latest['ma60']
            volume = latest['volume']
            avg_vol = latest['avg_vol_5d']
            change_pct = latest['change_pct']
            
            # 计算RSI
            rsi = calculate_rsi(df['close'], 14)
            
            # 计算量比
            volume_ratio = volume / avg_vol if avg_vol > 0 else 0
            
            # 计算MA20斜率
            ma20_5d_ago = df['ma20'].iloc[-5] if len(df) >= 5 else ma20
            ma20_slope = (ma20 - ma20_5d_ago) / ma20_5d_ago * 100 if ma20_5d_ago > 0 else 0
            
            # 计算价格偏离MA5
            price_deviation = (price - ma5) / ma5 * 100 if ma5 > 0 else 0
            
            # v11.4g筛选条件
            conditions = {
                'ma_golden_cross': ma5 > ma20,  # MA5 > MA20
                'above_ma60': price > ma60,  # 股价 > MA60
                'rsi_range': 44 <= rsi <= 70,  # RSI 44-70
                'volume_ok': volume_ratio >= 1.1,  # 量比 > 1.1
                'trend_up': ma20_slope > 0,  # MA20斜率向上
                'not_chasing': price_deviation < 5,  # 价格 < MA5*1.05
            }
            
            # 计算满足条件数
            conditions_met = sum(conditions.values())
            
            # 计算信号强度
            signal_strength = 0
            if conditions['ma_golden_cross']:
                signal_strength += 20
            if conditions['above_ma60']:
                signal_strength += 15
            if conditions['rsi_range']:
                signal_strength += 20
            if conditions['volume_ok']:
                signal_strength += 15
            if conditions['trend_up']:
                signal_strength += 15
            if conditions['not_chasing']:
                signal_strength += 15
            
            # 只保留满足至少3个条件、股价≤200元、仅主板（排除科创板688和创业板300）
            is_kcb = code.startswith('688')  # 科创板以688开头
            is_cyb = code.startswith('300')  # 创业板以300开头
            if conditions_met >= 3 and price <= 200 and not is_kcb and not is_cyb:
                candidates.append({
                    'code': code,
                    'name': get_stock_name(code),
                    'sector': get_stock_sector(code),
                    'price': price,
                    'change_pct': change_pct,
                    'rsi': rsi,
                    'volume_ratio': volume_ratio,
                    'ma20_slope': ma20_slope,
                    'price_deviation': price_deviation,
                    'signal_strength': signal_strength,
                    'conditions_met': conditions_met,
                    'conditions': conditions
                })
            
            # 进度显示
            if (i + 1) % 10 == 0:
                print(f"  已筛选 {i+1}/{len(stock_codes)} 只股票...")
                
        except Exception as e:
            continue
    
    # 按信号强度排序
    candidates.sort(key=lambda x: x['signal_strength'], reverse=True)
    
    # 输出结果
    print("\n" + "=" * 60)
    print("🎯 午后最值得关注的5支科技股")
    print("=" * 60)
    
    if not candidates:
        print("\n⚠️ 当前没有符合v11.4g策略条件的股票")
        print("可能原因：")
        print("  1. 大盘环境不佳")
        print("  2. 科技股整体处于调整期")
        print("  3. 今日非交易日")
        return
    
    top5 = candidates[:5]
    
    for i, stock in enumerate(top5, 1):
        print(f"\n【{i}】{stock['code']} {stock['name']}")
        print(f"    行业: {stock['sector']}")
        print(f"    现价: {stock['price']:.2f} 元  涨跌: {stock['change_pct']:+.2f}%")
        print(f"    RSI: {stock['rsi']:.1f}  量比: {stock['volume_ratio']:.2f}")
        print(f"    MA20斜率: {stock['ma20_slope']:+.2f}%  偏离MA5: {stock['price_deviation']:+.2f}%")
        print(f"    信号强度: {stock['signal_strength']}/100  满足条件: {stock['conditions_met']}/6")
        
        # 显示条件状态
        cond = stock['conditions']
        status = []
        if cond['ma_golden_cross']:
            status.append("✅MA金叉")
        else:
            status.append("❌MA金叉")
        if cond['above_ma60']:
            status.append("✅>MA60")
        else:
            status.append("❌>MA60")
        if cond['rsi_range']:
            status.append("✅RSI")
        else:
            status.append("❌RSI")
        if cond['volume_ok']:
            status.append("✅量比")
        else:
            status.append("❌量比")
        if cond['trend_up']:
            status.append("✅趋势")
        else:
            status.append("❌趋势")
        if cond['not_chasing']:
            status.append("✅位置")
        else:
            status.append("❌位置")
        
        print(f"    条件: {' '.join(status)}")
    
    # 汇总统计
    print("\n" + "-" * 60)
    print("📈 筛选汇总")
    print(f"  符合条件股票: {len(candidates)} 只")
    
    # 按行业统计
    sector_count = {}
    for c in candidates:
        sector = c['sector'] or '未知'
        sector_count[sector] = sector_count.get(sector, 0) + 1
    
    print(f"  行业分布: {sector_count}")
    
    # 风险提示
    print("\n" + "=" * 60)
    print("⚠️ 风险提示")
    print("  1. 以上仅为技术面筛选结果，不构成投资建议")
    print("  2. 请结合大盘环境和个股基本面综合判断")
    print("  3. 严格执行止损(-4.6%)，控制仓位(单只≤11%)")
    print("  4. 建议在14:45后确认信号再操作")
    print("=" * 60)
    
    return candidates


if __name__ == "__main__":
    screen_tech_stocks()
