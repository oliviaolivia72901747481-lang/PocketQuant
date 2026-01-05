"""
科技股池配置模块

提供科技股池的完整配置和管理功能，包括：
- 九个科技行业的股票池（半导体、人工智能、算力、消费电子、新能源科技、软件服务、生物医药科技、5G通信、智能制造）
- 股票池管理功能（添加、删除、筛选）
- 行业分类查询

更新时间: 2026-01-05 21:30:00
股票总数: 100只 (目标: 80-100只) ✅

Requirements: 12.1, 12.2, 12.3, 12.4
"""

from typing import Dict, List, Optional, Set
from dataclasses import dataclass


# ==========================================
# 科技股池配置
# ==========================================

@dataclass
class StockInfo:
    """股票信息"""
    code: str
    name: str
    sector: str
    
    def to_dict(self) -> Dict[str, str]:
        """转换为字典"""
        return {
            "code": self.code,
            "name": self.name,
            "sector": self.sector
        }


# 半导体行业股票池 (13只)
SEMICONDUCTOR_STOCKS = [
    {"code": "002371", "name": "北方华创"},
    {"code": "002049", "name": "紫光国微"},
    {"code": "603501", "name": "韦尔股份"},
    {"code": "002185", "name": "华天科技"},
    {"code": "600584", "name": "长电科技"},
    {"code": "002156", "name": "通富微电"},
    {"code": "603986", "name": "兆易创新"},
    {"code": "600460", "name": "士兰微"},
    {"code": "600703", "name": "三安光电"},
    {"code": "002036", "name": "联创电子"},
    {"code": "600353", "name": "旭光电子"},
    {"code": "002077", "name": "大港股份"},
    {"code": "002129", "name": "中环股份"},
]

# 人工智能行业股票池 (11只)
AI_APPLICATION_STOCKS = [
    {"code": "002415", "name": "海康威视"},
    {"code": "002230", "name": "科大讯飞"},
    {"code": "002410", "name": "广联达"},
    {"code": "603011", "name": "合锻智能"},
    {"code": "001339", "name": "智微智能"},
    {"code": "002421", "name": "达实智能"},
    {"code": "002849", "name": "威星智能"},
    {"code": "002313", "name": "日海智能"},
    {"code": "002362", "name": "汉王科技"},
    {"code": "002405", "name": "四维图新"},
    {"code": "002232", "name": "启明信息"},
]

# 算力行业股票池 (10只)
COMPUTING_POWER_STOCKS = [
    {"code": "000977", "name": "浪潮信息"},
    {"code": "603019", "name": "中科曙光"},
    {"code": "002439", "name": "启明星辰"},
    {"code": "002916", "name": "深南电路"},
    {"code": "603703", "name": "盛洋科技"},
    {"code": "000066", "name": "中国长城"},
    {"code": "600756", "name": "浪潮软件"},
    {"code": "002368", "name": "太极股份"},
    {"code": "600845", "name": "宝信软件"},
    {"code": "002065", "name": "东华软件"},
]

# 消费电子行业股票池 (15只)
CONSUMER_ELECTRONICS_STOCKS = [
    {"code": "002600", "name": "领益智造"},
    {"code": "002475", "name": "立讯精密"},
    {"code": "601138", "name": "工业富联"},
    {"code": "002241", "name": "歌尔股份"},
    {"code": "002456", "name": "欧菲光"},
    {"code": "002008", "name": "大族激光"},
    {"code": "002273", "name": "水晶光电"},
    {"code": "002044", "name": "美年健康"},
    {"code": "002228", "name": "合兴包装"},
    {"code": "002236", "name": "大华股份"},
    {"code": "002351", "name": "漫步者"},
    {"code": "002055", "name": "得润电子"},
    {"code": "002384", "name": "东山精密"},
    {"code": "002106", "name": "莱宝高科"},
    {"code": "002045", "name": "国光电器"},
]

# 新能源科技行业股票池 (14只)
NEW_ENERGY_TECH_STOCKS = [
    {"code": "000063", "name": "中兴通讯"},
    {"code": "603169", "name": "兰石重装"},
    {"code": "603528", "name": "多伦科技"},
    {"code": "600617", "name": "国新能源"},
    {"code": "001258", "name": "立新能源"},
    {"code": "000690", "name": "宝新能源"},
    {"code": "002202", "name": "金风科技"},
    {"code": "601012", "name": "隆基绿能"},
    {"code": "002459", "name": "晶澳科技"},
    {"code": "600438", "name": "通威股份"},
    {"code": "002074", "name": "国轩高科"},
    {"code": "002594", "name": "比亚迪"},
    {"code": "600089", "name": "特变电工"},
]

# 软件服务行业股票池 (11只)
SOFTWARE_SERVICE_STOCKS = [
    {"code": "600588", "name": "用友网络"},
    {"code": "002279", "name": "久其软件"},
    {"code": "002474", "name": "榕基软件"},
    {"code": "603189", "name": "网达软件"},
    {"code": "600570", "name": "恒生电子"},
    {"code": "002268", "name": "卫士通"},
    {"code": "002212", "name": "天融信"},
    {"code": "002197", "name": "证通电子"},
    {"code": "600446", "name": "金证股份"},
    {"code": "002401", "name": "中远海科"},
    {"code": "002777", "name": "久远银海"},
]

# 生物医药科技行业股票池 (9只)
BIOMEDICAL_TECH_STOCKS = [
    {"code": "002030", "name": "达安基因"},
    {"code": "603658", "name": "安图生物"},
    {"code": "002223", "name": "鱼跃医疗"},
    {"code": "000661", "name": "长春高新"},
    {"code": "002007", "name": "华兰生物"},
    {"code": "000963", "name": "华东医药"},
    {"code": "002252", "name": "上海莱士"},
    {"code": "002432", "name": "九安医疗"},
    {"code": "002551", "name": "尚荣医疗"},
]

# 5G通信行业股票池 (8只)
COMMUNICATION_5G_STOCKS = [
    {"code": "600498", "name": "烽火通信"},
    {"code": "002396", "name": "星网锐捷"},
    {"code": "002093", "name": "国脉科技"},
    {"code": "002115", "name": "三维通信"},
    {"code": "002446", "name": "盛路通信"},
    {"code": "002194", "name": "武汉凡谷"},
    {"code": "002281", "name": "光迅科技"},
    {"code": "600522", "name": "中天科技"},
]

# 智能制造行业股票池 (10只)
SMART_MANUFACTURING_STOCKS = [
    {"code": "002184", "name": "海得控制"},
    {"code": "002527", "name": "新时达"},
    {"code": "002747", "name": "埃斯顿"},
    {"code": "002472", "name": "双环传动"},
    {"code": "002270", "name": "华明装备"},
    {"code": "002097", "name": "山河智能"},
    {"code": "002248", "name": "华东数控"},
    {"code": "002611", "name": "东方精工"},
    {"code": "002031", "name": "巨轮智能"},
    {"code": "002698", "name": "博实股份"},
]

# 科技ETF股票池 (保留为空，用户无权限)
TECH_ETF_STOCKS = []

# 科技股池总配置
TECH_STOCK_POOL: Dict[str, List[Dict[str, str]]] = {
    "半导体": SEMICONDUCTOR_STOCKS,
    "人工智能": AI_APPLICATION_STOCKS,
    "算力": COMPUTING_POWER_STOCKS,
    "消费电子": CONSUMER_ELECTRONICS_STOCKS,
    "新能源科技": NEW_ENERGY_TECH_STOCKS,
    "软件服务": SOFTWARE_SERVICE_STOCKS,
    "生物医药科技": BIOMEDICAL_TECH_STOCKS,
    "5G通信": COMMUNICATION_5G_STOCKS,
    "智能制造": SMART_MANUFACTURING_STOCKS,
    "科技ETF": TECH_ETF_STOCKS,
}


# ==========================================
# 股票池管理类
# ==========================================

class TechStockPool:
    """
    科技股池管理类
    
    提供股票池的查询、添加、删除、筛选等功能
    支持用户自定义管理股票池
    
    Requirements: 12.2, 12.4
    """
    
    def __init__(self):
        """初始化股票池"""
        # 深拷贝股票池，避免修改原始配置
        self._pool: Dict[str, List[Dict[str, str]]] = {
            sector: [stock.copy() for stock in stocks]
            for sector, stocks in TECH_STOCK_POOL.items()
        }
        
        # 用户自定义股票（不属于预设行业）
        self._custom_stocks: List[Dict[str, str]] = []
    
    def get_all_stocks(self) -> List[StockInfo]:
        """
        获取所有科技股
        
        Returns:
            所有科技股信息列表
        """
        stocks = []
        for sector, sector_stocks in self._pool.items():
            for stock in sector_stocks:
                stocks.append(StockInfo(
                    code=stock["code"],
                    name=stock["name"],
                    sector=sector
                ))
        
        # 添加自定义股票
        for stock in self._custom_stocks:
            stocks.append(StockInfo(
                code=stock["code"],
                name=stock["name"],
                sector=stock.get("sector", "自定义")
            ))
        
        return stocks
    
    def get_all_codes(self) -> List[str]:
        """
        获取所有科技股代码
        
        Returns:
            所有科技股代码列表
        """
        codes = []
        for sector_stocks in self._pool.values():
            for stock in sector_stocks:
                codes.append(stock["code"])
        
        # 添加自定义股票代码
        for stock in self._custom_stocks:
            codes.append(stock["code"])
        
        return codes

    def get_stocks_by_sector(self, sector: str) -> List[StockInfo]:
        """
        按行业筛选股票
        
        Args:
            sector: 行业名称
        
        Returns:
            该行业的股票列表
        
        Requirements: 12.4
        """
        if sector not in self._pool:
            return []
        
        stocks = []
        for stock in self._pool[sector]:
            stocks.append(StockInfo(
                code=stock["code"],
                name=stock["name"],
                sector=sector
            ))
        
        return stocks
    
    def get_codes_by_sector(self, sector: str) -> List[str]:
        """
        获取指定行业的股票代码列表
        
        Args:
            sector: 行业名称
        
        Returns:
            该行业的股票代码列表
        """
        if sector not in self._pool:
            return []
        
        return [stock["code"] for stock in self._pool[sector]]
    
    def get_stock_info(self, code: str) -> Optional[StockInfo]:
        """
        获取股票信息
        
        Args:
            code: 股票代码
        
        Returns:
            股票信息，如果不存在返回 None
        """
        # 在预设股票池中查找
        for sector, sector_stocks in self._pool.items():
            for stock in sector_stocks:
                if stock["code"] == code:
                    return StockInfo(
                        code=stock["code"],
                        name=stock["name"],
                        sector=sector
                    )
        
        # 在自定义股票中查找
        for stock in self._custom_stocks:
            if stock["code"] == code:
                return StockInfo(
                    code=stock["code"],
                    name=stock["name"],
                    sector=stock.get("sector", "自定义")
                )
        
        return None
    
    def get_stock_sector(self, code: str) -> Optional[str]:
        """
        获取股票所属行业
        
        Args:
            code: 股票代码
        
        Returns:
            行业名称，如果不存在返回 None
        """
        stock_info = self.get_stock_info(code)
        return stock_info.sector if stock_info else None
    
    def get_stock_name(self, code: str) -> str:
        """
        获取股票名称
        
        Args:
            code: 股票代码
        
        Returns:
            股票名称，如果不存在返回代码本身
        """
        stock_info = self.get_stock_info(code)
        return stock_info.name if stock_info else code

    def add_stock(self, code: str, name: str, sector: Optional[str] = None) -> bool:
        """
        添加股票到股票池
        
        Args:
            code: 股票代码
            name: 股票名称
            sector: 行业名称（可选，如果为 None 则添加到自定义列表）
        
        Returns:
            是否添加成功
        
        Requirements: 12.2, 12.4
        """
        # 检查是否已存在
        if self.get_stock_info(code) is not None:
            return False
        
        stock = {"code": code, "name": name}
        
        if sector and sector in self._pool:
            # 添加到指定行业
            self._pool[sector].append(stock)
        else:
            # 添加到自定义列表
            stock["sector"] = sector if sector else "自定义"
            self._custom_stocks.append(stock)
        
        return True
    
    def remove_stock(self, code: str) -> bool:
        """
        从股票池中删除股票
        
        Args:
            code: 股票代码
        
        Returns:
            是否删除成功
        
        Requirements: 12.2, 12.4
        """
        # 在预设股票池中查找并删除
        for sector, sector_stocks in self._pool.items():
            for i, stock in enumerate(sector_stocks):
                if stock["code"] == code:
                    del self._pool[sector][i]
                    return True
        
        # 在自定义股票中查找并删除
        for i, stock in enumerate(self._custom_stocks):
            if stock["code"] == code:
                del self._custom_stocks[i]
                return True
        
        return False
    
    def get_sectors(self) -> List[str]:
        """
        获取所有行业列表
        
        Returns:
            行业名称列表
        """
        return list(self._pool.keys())
    
    def get_sector_count(self, sector: str) -> int:
        """
        获取指定行业的股票数量
        
        Args:
            sector: 行业名称
        
        Returns:
            股票数量
        """
        if sector not in self._pool:
            return 0
        return len(self._pool[sector])
    
    def get_total_count(self) -> int:
        """
        获取股票池总数量
        
        Returns:
            总股票数量
        """
        count = sum(len(stocks) for stocks in self._pool.values())
        count += len(self._custom_stocks)
        return count
    
    def filter_by_codes(self, codes: List[str]) -> List[StockInfo]:
        """
        根据代码列表筛选股票
        
        Args:
            codes: 股票代码列表
        
        Returns:
            匹配的股票信息列表
        """
        code_set = set(codes)
        stocks = []
        
        for stock in self.get_all_stocks():
            if stock.code in code_set:
                stocks.append(stock)
        
        return stocks
    
    def reset_to_default(self) -> None:
        """
        重置股票池到默认配置
        
        清除所有自定义修改，恢复到初始状态
        """
        self._pool = {
            sector: [stock.copy() for stock in stocks]
            for sector, stocks in TECH_STOCK_POOL.items()
        }
        self._custom_stocks = []


# ==========================================
# 全局实例和辅助函数
# ==========================================

# 全局股票池实例
_tech_stock_pool: Optional[TechStockPool] = None


def get_tech_stock_pool() -> TechStockPool:
    """
    获取科技股池实例（单例模式）
    
    Returns:
        TechStockPool 实例
    """
    global _tech_stock_pool
    if _tech_stock_pool is None:
        _tech_stock_pool = TechStockPool()
    return _tech_stock_pool


def reset_tech_stock_pool() -> None:
    """重置科技股池实例（主要用于测试）"""
    global _tech_stock_pool
    _tech_stock_pool = None


# ==========================================
# 便捷函数（向后兼容）
# ==========================================

def get_all_tech_stocks() -> List[str]:
    """
    获取所有科技股代码
    
    Returns:
        所有科技股代码列表
    """
    return get_tech_stock_pool().get_all_codes()


def get_stock_sector(code: str) -> Optional[str]:
    """
    获取股票所属行业
    
    Args:
        code: 股票代码
    
    Returns:
        行业名称，如果不在科技股池中返回 None
    """
    return get_tech_stock_pool().get_stock_sector(code)


def get_sector_stocks(sector: str) -> List[Dict[str, str]]:
    """
    获取指定行业的股票列表
    
    Args:
        sector: 行业名称
    
    Returns:
        该行业的股票列表（字典格式）
    """
    stocks = get_tech_stock_pool().get_stocks_by_sector(sector)
    return [stock.to_dict() for stock in stocks]


def get_stock_name(code: str) -> str:
    """
    获取股票名称
    
    Args:
        code: 股票代码
    
    Returns:
        股票名称，如果不在科技股池中返回代码本身
    """
    return get_tech_stock_pool().get_stock_name(code)
