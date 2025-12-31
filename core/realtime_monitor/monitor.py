"""
Realtime Monitor Main Class

实时监控器主类，实现监控列表管理、持仓管理和峰值价格跟踪。
Requirements: 1.1, 1.2, 1.3, 2.1, 2.3
"""

import re
from typing import Dict, List, Optional
from datetime import date

from .config import MONITOR_CONFIG
from .models import Position


class RealtimeMonitor:
    """
    实时监控器主类
    
    实现功能:
    - 监控列表管理（添加/删除/验证）- Requirements: 1.1, 1.2, 1.3
    - 持仓管理（添加/更新/删除）- Requirements: 2.1, 2.3
    - 峰值价格跟踪（用于移动止盈）
    
    Property 1: Stock Code Validation
    For any input string, the watchlist add function should accept only valid 
    A-share stock codes (6 digits starting with 0, 3, or 6) and reject all others.
    
    Property 2: Watchlist Size Limit
    For any watchlist with 20 stocks, attempting to add another stock should fail 
    and the watchlist size should remain 20.
    """
    
    def __init__(self, config: Optional[MONITOR_CONFIG.__class__] = None):
        """
        初始化实时监控器
        
        Args:
            config: 监控配置，默认使用MONITOR_CONFIG
        """
        self.config = config or MONITOR_CONFIG
        self._watchlist: List[str] = []
        self._positions: Dict[str, Position] = {}
    
    @property
    def watchlist(self) -> List[str]:
        """获取监控列表（只读副本）"""
        return self._watchlist.copy()
    
    @property
    def positions(self) -> Dict[str, Position]:
        """获取持仓字典（只读副本）"""
        return self._positions.copy()
    
    @property
    def watchlist_size(self) -> int:
        """获取监控列表大小"""
        return len(self._watchlist)
    
    @property
    def position_count(self) -> int:
        """获取持仓数量"""
        return len(self._positions)
    
    # ==================== 股票代码验证 ====================
    
    def validate_stock_code(self, code: str) -> bool:
        """
        验证股票代码格式
        
        Property 1: Stock Code Validation
        Valid A-share stock codes are 6 digits starting with 0, 3, or 6.
        
        Requirements: 1.1
        
        Args:
            code: 股票代码
            
        Returns:
            bool: 是否为有效的A股代码
        """
        if not isinstance(code, str):
            return False
        
        # 检查长度
        if len(code) != self.config.code_length:
            return False
        
        # 检查是否全为数字
        if not code.isdigit():
            return False
        
        # 检查前缀
        if not code.startswith(self.config.valid_code_prefixes):
            return False
        
        return True
    
    # ==================== 监控列表管理 ====================
    
    def add_to_watchlist(self, code: str) -> bool:
        """
        添加股票到监控列表
        
        Property 1: Stock Code Validation
        Property 2: Watchlist Size Limit
        
        Requirements: 1.1, 1.3
        
        Args:
            code: 股票代码
            
        Returns:
            bool: 是否添加成功
        """
        # 验证代码格式
        if not self.validate_stock_code(code):
            return False
        
        # 检查是否已在列表中
        if code in self._watchlist:
            return False
        
        # 检查列表大小限制
        if len(self._watchlist) >= self.config.max_watchlist_size:
            return False
        
        self._watchlist.append(code)
        return True
    
    def remove_from_watchlist(self, code: str) -> bool:
        """
        从监控列表移除股票
        
        Requirements: 1.2
        
        Args:
            code: 股票代码
            
        Returns:
            bool: 是否移除成功
        """
        if code not in self._watchlist:
            return False
        
        self._watchlist.remove(code)
        return True
    
    def is_in_watchlist(self, code: str) -> bool:
        """
        检查股票是否在监控列表中
        
        Args:
            code: 股票代码
            
        Returns:
            bool: 是否在监控列表中
        """
        return code in self._watchlist
    
    def clear_watchlist(self) -> None:
        """清空监控列表"""
        self._watchlist.clear()
    
    # ==================== 持仓管理 ====================
    
    def add_position(
        self, 
        code: str, 
        name: str,
        cost_price: float, 
        quantity: int,
        buy_date: Optional[date] = None
    ) -> bool:
        """
        添加持仓
        
        Requirements: 2.1
        
        Args:
            code: 股票代码
            name: 股票名称
            cost_price: 成本价
            quantity: 持仓数量
            buy_date: 买入日期，默认为今天
            
        Returns:
            bool: 是否添加成功
        """
        # 验证代码格式
        if not self.validate_stock_code(code):
            return False
        
        # 验证成本价和数量
        if cost_price <= 0 or quantity <= 0:
            return False
        
        # 检查是否已有持仓
        if code in self._positions:
            return False
        
        # 创建持仓
        position = Position(
            code=code,
            name=name,
            cost_price=cost_price,
            quantity=quantity,
            buy_date=buy_date or date.today(),
            peak_price=cost_price,  # 初始峰值为成本价
            current_price=cost_price  # 初始当前价为成本价
        )
        
        self._positions[code] = position
        
        # 自动添加到监控列表
        if code not in self._watchlist:
            self.add_to_watchlist(code)
        
        return True
    
    def update_position(
        self, 
        code: str, 
        cost_price: Optional[float] = None, 
        quantity: Optional[int] = None,
        name: Optional[str] = None
    ) -> bool:
        """
        更新持仓信息
        
        Requirements: 2.3
        
        Args:
            code: 股票代码
            cost_price: 新成本价（可选）
            quantity: 新数量（可选）
            name: 新名称（可选）
            
        Returns:
            bool: 是否更新成功
        """
        if code not in self._positions:
            return False
        
        position = self._positions[code]
        
        # 更新成本价
        if cost_price is not None:
            if cost_price <= 0:
                return False
            position.cost_price = cost_price
        
        # 更新数量
        if quantity is not None:
            if quantity <= 0:
                return False
            position.quantity = quantity
        
        # 更新名称
        if name is not None:
            position.name = name
        
        return True
    
    def remove_position(self, code: str) -> bool:
        """
        移除持仓
        
        Args:
            code: 股票代码
            
        Returns:
            bool: 是否移除成功
        """
        if code not in self._positions:
            return False
        
        del self._positions[code]
        return True
    
    def get_position(self, code: str) -> Optional[Position]:
        """
        获取持仓信息
        
        Args:
            code: 股票代码
            
        Returns:
            Position: 持仓信息，不存在时返回None
        """
        return self._positions.get(code)
    
    def has_position(self, code: str) -> bool:
        """
        检查是否有持仓
        
        Args:
            code: 股票代码
            
        Returns:
            bool: 是否有持仓
        """
        return code in self._positions
    
    def clear_positions(self) -> None:
        """清空所有持仓"""
        self._positions.clear()
    
    # ==================== 峰值价格跟踪 ====================
    
    def update_position_price(self, code: str, current_price: float) -> bool:
        """
        更新持仓当前价格（同时更新峰值价格）
        
        用于移动止盈计算。
        
        Args:
            code: 股票代码
            current_price: 当前价格
            
        Returns:
            bool: 是否更新成功
        """
        if code not in self._positions:
            return False
        
        if current_price <= 0:
            return False
        
        position = self._positions[code]
        position.update_current_price(current_price)
        return True
    
    def update_all_position_prices(self, prices: Dict[str, float]) -> Dict[str, bool]:
        """
        批量更新持仓价格
        
        Args:
            prices: 股票代码到价格的映射
            
        Returns:
            Dict[str, bool]: 各股票更新结果
        """
        results = {}
        for code, price in prices.items():
            results[code] = self.update_position_price(code, price)
        return results
    
    def get_peak_price(self, code: str) -> Optional[float]:
        """
        获取持仓峰值价格
        
        Args:
            code: 股票代码
            
        Returns:
            float: 峰值价格，不存在时返回None
        """
        position = self._positions.get(code)
        return position.peak_price if position else None
    
    def reset_peak_price(self, code: str) -> bool:
        """
        重置峰值价格为当前价格
        
        Args:
            code: 股票代码
            
        Returns:
            bool: 是否重置成功
        """
        if code not in self._positions:
            return False
        
        position = self._positions[code]
        position.peak_price = position.current_price
        return True
    
    # ==================== 汇总统计 ====================
    
    def get_total_market_value(self) -> float:
        """
        获取总市值
        
        Returns:
            float: 总市值
        """
        return sum(p.market_value for p in self._positions.values())
    
    def get_total_cost_value(self) -> float:
        """
        获取总成本
        
        Returns:
            float: 总成本
        """
        return sum(p.cost_value for p in self._positions.values())
    
    def get_total_pnl(self) -> float:
        """
        获取总盈亏金额
        
        Returns:
            float: 总盈亏金额
        """
        return sum(p.pnl for p in self._positions.values())
    
    def get_total_pnl_pct(self) -> float:
        """
        获取总盈亏百分比
        
        Returns:
            float: 总盈亏百分比
        """
        total_cost = self.get_total_cost_value()
        if total_cost <= 0:
            return 0.0
        return self.get_total_pnl() / total_cost
    
    def get_position_summary(self) -> Dict:
        """
        获取持仓汇总信息
        
        Returns:
            Dict: 持仓汇总
        """
        return {
            'position_count': self.position_count,
            'total_market_value': self.get_total_market_value(),
            'total_cost_value': self.get_total_cost_value(),
            'total_pnl': self.get_total_pnl(),
            'total_pnl_pct': self.get_total_pnl_pct(),
        }
