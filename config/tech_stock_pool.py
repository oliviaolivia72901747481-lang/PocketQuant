"""
科技股池配置模块

提供科技股池的完整配置和管理功能，包括：
- 四个科技行业的股票池（半导体、AI应用、算力、消费电子）
- 股票池管理功能（添加、删除、筛选）
- 行业分类查询

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


# 半导体行业股票池
SEMICONDUCTOR_STOCKS = [
    {"code": "002371", "name": "北方华创"},
    {"code": "688981", "name": "中芯国际"},
    {"code": "002049", "name": "紫光国微"},
    {"code": "603501", "name": "韦尔股份"},
    {"code": "688012", "name": "中微公司"},
    {"code": "688008", "name": "澜起科技"},
    {"code": "002185", "name": "华天科技"},
    {"code": "600584", "name": "长电科技"},
    {"code": "002156", "name": "通富微电"},
    {"code": "688396", "name": "华润微"},
    {"code": "603986", "name": "兆易创新"},
    {"code": "300782", "name": "卓胜微"},
]

# AI应用行业股票池
AI_APPLICATION_STOCKS = [
    {"code": "300308", "name": "中际旭创"},
    {"code": "002415", "name": "海康威视"},
    {"code": "300496", "name": "中科创达"},
    {"code": "002230", "name": "科大讯飞"},
    {"code": "300033", "name": "同花顺"},
    {"code": "688099", "name": "晶晨股份"},
    {"code": "300454", "name": "深信服"},
    {"code": "002410", "name": "广联达"},
    {"code": "300418", "name": "昆仑万维"},
    {"code": "688561", "name": "奇安信"},
]

# 算力行业股票池
COMPUTING_POWER_STOCKS = [
    {"code": "000977", "name": "浪潮信息"},
    {"code": "603019", "name": "中科曙光"},
    {"code": "688256", "name": "寒武纪"},
    {"code": "002439", "name": "启明星辰"},
    {"code": "300454", "name": "深信服"},
    {"code": "002916", "name": "深南电路"},
    {"code": "300474", "name": "景嘉微"},
    {"code": "688126", "name": "沪硅产业"},
    {"code": "688041", "name": "海光信息"},
]

# 消费电子行业股票池
CONSUMER_ELECTRONICS_STOCKS = [
    {"code": "002600", "name": "长盈精密"},
    {"code": "002475", "name": "立讯精密"},
    {"code": "601138", "name": "工业富联"},
    {"code": "002241", "name": "歌尔股份"},
    {"code": "300433", "name": "蓝思科技"},
    {"code": "002456", "name": "欧菲光"},
    {"code": "002008", "name": "大族激光"},
    {"code": "300136", "name": "信维通信"},
    {"code": "002273", "name": "水晶光电"},
    {"code": "300115", "name": "长盈精密"},
]

# 科技股池总配置
TECH_STOCK_POOL: Dict[str, List[Dict[str, str]]] = {
    "半导体": SEMICONDUCTOR_STOCKS,
    "AI应用": AI_APPLICATION_STOCKS,
    "算力": COMPUTING_POWER_STOCKS,
    "消费电子": CONSUMER_ELECTRONICS_STOCKS,
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
            sector: 行业名称（"半导体"、"AI应用"、"算力"、"消费电子"）
        
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
