# auto_update_pool.py
import sys
import os
import datetime

# 1. 环境设置
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from core.data_feed import DataFeed
from core.screener import Screener, LiquidityFilter, MarketFilter, IndustryDiversification, ScreenerCondition

def main():
    print("🚀 开始全市场扫描，自动配置股票池...")

    # 2. 初始化模块
    data_feed = DataFeed(raw_path='data/raw', processed_path='data/processed')
    screener = Screener(data_feed)

    # 3. 配置“硬门槛” (根据你的偏好修改)
    # 自动过滤掉垃圾股，只保留流动性好的票
    screener.set_liquidity_filter(LiquidityFilter(
        min_market_cap=5e9,         # 最小市值 50亿
        max_market_cap=8e10,        # 最大市值 800亿 (小资金不做大象股)
        min_turnover_rate=0.03,     # 最小换手 3% (活跃股)
        exclude_st=True             # 剔除 ST
    ))

    # 4. 配置技术筛选条件
    # 提示：MA60趋势向上和财报窗口期避雷在 screen() 中默认开启
    # 这里添加额外的过滤，例如 RSI 指标健康
    screener.add_condition(ScreenerCondition(
        indicator='rsi',
        operator='<',
        value=70.0  # 选股时要求RSI<70，留出上涨空间
    ))
    
    # 行业分散：同一行业只选最强的一只
    screener.set_industry_diversification(IndustryDiversification(
        enabled=True,
        max_same_industry=1
    ))

    # 5. 执行全市场筛选
    print("🔍 正在执行两阶段筛选 (预剪枝 + 精筛)...")
    # 不传参数 = 扫描全市场
    results = screener.screen()
    
    if not results:
        print("⚠️ 未找到符合条件的股票 (可能大盘环境不佳或条件过严)")
        return

    # 6. 提取股票代码并格式化
    new_pool = [result.code for result in results]
    print(f"✅ 筛选出 {len(new_pool)} 只优质股票")
    
    # 7. (可选) 自动更新到配置文件
    update_config_file(new_pool)

def update_config_file(stock_codes):
    """将筛选结果写入 config/stock_pool.py"""
    file_path = 'config/stock_pool.py'
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    content = f"""# 股票池配置
# 自动更新于: {timestamp}
# 由 auto_update_pool.py 生成

# 自选股列表
WATCHLIST = [
"""
    
    for code in stock_codes:
        content += f"    '{code}',\n"
        
    content += "]\n"
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"💾 已自动更新股票池配置文件: {file_path}")
        print("   现在你可以直接运行每日信号或回测了！")
    except Exception as e:
        print(f"❌ 写入文件失败: {e}")
        # 失败时打印出来供手动复制
        print("请手动复制以下列表到 config/stock_pool.py:")
        print(stock_codes)

if __name__ == "__main__":
    main()