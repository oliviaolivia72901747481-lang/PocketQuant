# auto_update_pool.py (增强调试版)
import sys
import os
import datetime
import logging

# 1. 环境设置
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 导入日志配置
from core.logging_config import setup_logging

# 2. 开启控制台日志 (关键步骤)
setup_logging(level='INFO', console_output=True)
logger = logging.getLogger(__name__)

try:
    from core.data_feed import DataFeed
    from core.screener import Screener, LiquidityFilter, IndustryDiversification, ScreenerCondition, MarketFilter
except ImportError as e:
    print(f"❌ 导入模块失败: {e}")
    print(f"请确认脚本是否放在项目根目录: {current_dir}")
    input("按回车键退出...")
    sys.exit(1)

def main():
    print("\n" + "="*50)
    print("🚀 启动全市场扫描 (Debug模式)")
    print("="*50 + "\n")

    try:
        # 初始化
        print("1. 正在初始化数据接口...")
        data_feed = DataFeed(raw_path='data/raw', processed_path='data/processed')
        screener = Screener(data_feed)

        # 开启大盘风控 (实盘建议开启)
        print("   ! 已开启大盘风控，若沪深300 < MA20 将自动空仓")
        screener.set_market_filter(MarketFilter(
            enabled=True,  # <--- 改为 True
            benchmark_code='000300',
            ma_period=60  # <--- 将 20 改为 60
            ))

        # 配置参数
        print("2. 正在配置筛选条件...")
        screener.set_liquidity_filter(LiquidityFilter(
            min_market_cap=5e9,         # 50亿
            max_market_cap=8e10,        # 800亿
            min_turnover_rate=0.03,     # 3%
            exclude_st=True,
            min_listing_days=180
        ))
        
        screener.set_industry_diversification(IndustryDiversification(
            enabled=True,
            max_same_industry=1
        ))

        # 添加技术指标
        screener.add_condition(ScreenerCondition(
            indicator='rsi',
            operator='<',
            value=70.0
        ))

        # 执行筛选
        print("3. 开始执行筛选 (这一步可能需要 1-2 分钟，请耐心等待)...")
        print("   >>> 如果卡在这里，说明正在连接 AkShare 获取数据，请检查网络 <<<")
        
        # 调用核心筛选逻辑
        results = screener.screen() 

        print(f"\n4. 筛选结束，找到 {len(results)} 个结果")

        if not results:
            print("\n⚠️ 结果为空！可能原因：")
            print("   - 大盘风控生效 (沪深300 < MA20)")
            print("   - AkShare 数据接口连接超时")
            print("   - 没有股票满足筛选条件")
        else:
            # 提取代码
            new_pool = [result.code for result in results]
            
            # 更新文件
            update_config_file(new_pool)

    except Exception as e:
        print(f"\n❌ 运行过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()

def update_config_file(stock_codes):
    """写入配置文件 (完整版：包含所有必要的类和函数)"""
    file_path = os.path.join(current_dir, 'config', 'stock_pool.py')
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 1. 写入列表数据
    content = f"""# 股票池配置
# 自动更新于: {timestamp}
# 由 auto_update_pool.py 生成

# 自选股列表
WATCHLIST = [
"""
    for code in stock_codes:
        content += f"    '{code}',\n"
    
    content += "]\n\n"

    # 2. 写入缺失的功能代码 (补全 get_watchlist, StockPool, validate_stock_codes)
    content += """
# === 功能函数区域 ===

def get_watchlist():
    \"\"\"获取股票列表\"\"\"
    return WATCHLIST

def validate_stock_codes(codes):
    \"\"\"验证股票代码格式\"\"\"
    if not codes:
        return []
    # 过滤掉非6位数字的代码
    return [c for c in codes if str(c).isdigit() and len(str(c)) == 6]

class StockPool:
    \"\"\"股票池管理类（兼容 Data Manager）\"\"\"
    
    @staticmethod
    def get_codes():
        return WATCHLIST
        
    @staticmethod
    def add_code(code):
        if code not in WATCHLIST:
            WATCHLIST.append(code)
            
    @staticmethod
    def remove_code(code):
        if code in WATCHLIST:
            WATCHLIST.remove(code)
"""
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"\n✅ 成功！已将 {len(stock_codes)} 只股票更新到: {file_path}")
        print("   (已自动修复 StockPool 和 validate_stock_codes 缺失问题)")
    except Exception as e:
        print(f"❌ 写入文件失败: {e}")

if __name__ == "__main__":
    main()
    # 防止双击运行后窗口直接关闭
    input("\n程序运行结束，按回车键关闭窗口...")