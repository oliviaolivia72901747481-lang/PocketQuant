# 股票池配置
# 自动更新于: 2025-12-22 15:47:33
# 由 auto_update_pool.py 生成

# 自选股列表
WATCHLIST = [
    '002759',
    '002213',
    '002549',
    '002067',
    '300903',
    '002196',
    '300115',
    '603686',
    '688726',
    '300846',
    '300058',
    '000753',
    '300390',
    '600592',
    '002173',
    '300123',
    '688411',
    '600868',
    '301013',
    '002488',
    '300006',
    '603322',
    '603232',
    '002307',
    '600815',
    '600376',
    '301191',
    '300192',
    '600635',
    '605178',
    '002356',
    '601059',
    '600593',
    '003041',
    '605196',
    '300850',
    '002317',
    '000833',
    '300204',
    '601020',
    '301228',
    '002108',
    '600839',
    '000560',
    '603399',
    '600375',
    '600829',
    '301071',
    '002734',
]


# === 功能函数区域 ===

def get_watchlist():
    """获取股票列表"""
    return WATCHLIST

def validate_stock_codes(codes):
    """验证股票代码格式"""
    if not codes:
        return []
    # 过滤掉非6位数字的代码
    return [c for c in codes if str(c).isdigit() and len(str(c)) == 6]

class StockPool:
    """股票池管理类（兼容 Data Manager）"""
    
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
