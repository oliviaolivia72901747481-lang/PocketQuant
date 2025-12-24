# 股票池配置
# 自动更新于: 2025-12-23 22:27:40
# 由 auto_update_pool.py 生成

# 自选股列表
WATCHLIST = [
    '300179',
    '002175',
    '688411',
    '603906',
    '603232',
    '002317',
    '300123',
    '000678',
    '600078',
    '300903',
    '300071',
    '600172',
    '002067',
    '301171',
    '600829',
    '600376',
    '300938',
    '300115',
    '002632',
    '300082',
    '002307',
    '000833',
    '605580',
    '002356',
    '600593',
    '002173',
    '000536',
    '688525',
    '300638',
    '600255',
    '600815',
    '002301',
    '300821',
    '003041',
    '002611',
    '002249',
    '300850',
    '000034',
    '600635',
    '601059',
    '300204',
    '000560',
    '605178',
    '002150',
    '002741',
    '300856',
    '001313',
    '002210',
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
