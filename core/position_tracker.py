"""
MiniQuant-Lite 持仓跟踪模块

提供持仓管理功能：
- 持仓记录的 CRUD 操作
- 盈亏计算
- CSV 持久化存储

Requirements: 1.1, 1.3, 1.5, 2.2, 2.3
"""

import os
import logging
from dataclasses import dataclass, asdict
from datetime import date, datetime
from typing import List, Optional, Dict, Any
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class Holding:
    """
    单个持仓记录
    
    Attributes:
        code: 股票代码（6位）
        name: 股票名称
        buy_price: 买入价格
        buy_date: 买入日期
        quantity: 持仓数量（股）
        strategy: 使用的策略（RSRS/RSI）
        note: 备注（可选）
    """
    code: str
    name: str
    buy_price: float
    buy_date: date
    quantity: int
    strategy: str
    note: str = ""
    
    def validate(self) -> tuple[bool, str]:
        """
        验证持仓数据有效性
        
        Returns:
            (是否有效, 错误信息)
        """
        if not self.code or len(self.code) != 6 or not self.code.isdigit():
            return False, "股票代码必须是6位数字"
        if self.buy_price <= 0:
            return False, "买入价格必须大于0"
        if self.quantity <= 0:
            return False, "持仓数量必须大于0"
        if self.strategy not in ["RSRS", "RSI"]:
            return False, "策略必须是 RSRS 或 RSI"
        return True, ""


@dataclass
class PnLResult:
    """盈亏计算结果"""
    pnl_amount: float      # 盈亏金额
    pnl_pct: float         # 盈亏百分比
    market_value: float    # 当前市值
    cost_value: float      # 成本金额
    holding_days: int      # 持仓天数
    is_stop_loss: bool     # 是否触发止损


class PositionTracker:
    """
    持仓跟踪器
    
    负责持仓的 CRUD 操作和盈亏计算
    
    Requirements: 1.1, 1.3, 1.5, 2.2, 2.3
    """
    
    STOP_LOSS_THRESHOLD = -0.06  # 止损线 -6%
    
    def __init__(self, data_path: str = "data"):
        """
        初始化持仓跟踪器
        
        Args:
            data_path: 数据存储目录
        """
        self.data_path = data_path
        self.csv_file = os.path.join(data_path, "positions.csv")
        self._positions: Dict[str, Holding] = {}
        self._load_from_csv()
    
    def add_position(self, holding: Holding) -> tuple[bool, str]:
        """
        添加持仓
        
        Args:
            holding: 持仓记录
        
        Returns:
            (是否成功, 消息)
        """
        # 验证数据
        valid, error = holding.validate()
        if not valid:
            return False, error
        
        # 检查是否已存在
        if holding.code in self._positions:
            return False, f"股票 {holding.code} 已在持仓中，请先删除或更新"
        
        self._positions[holding.code] = holding
        self._save_to_csv()
        
        logger.info(f"添加持仓: {holding.code} {holding.name}")
        return True, "添加成功"
    
    def remove_position(self, code: str) -> tuple[bool, str]:
        """
        删除持仓
        
        Args:
            code: 股票代码
        
        Returns:
            (是否成功, 消息)
        """
        if code not in self._positions:
            return False, f"股票 {code} 不在持仓中"
        
        del self._positions[code]
        self._save_to_csv()
        
        logger.info(f"删除持仓: {code}")
        return True, "删除成功"
    
    def update_position(self, code: str, **kwargs) -> tuple[bool, str]:
        """
        更新持仓信息
        
        Args:
            code: 股票代码
            **kwargs: 要更新的字段
        
        Returns:
            (是否成功, 消息)
        """
        if code not in self._positions:
            return False, f"股票 {code} 不在持仓中"
        
        holding = self._positions[code]
        
        # 更新字段
        for key, value in kwargs.items():
            if hasattr(holding, key):
                setattr(holding, key, value)
        
        # 验证更新后的数据
        valid, error = holding.validate()
        if not valid:
            return False, error
        
        self._save_to_csv()
        
        logger.info(f"更新持仓: {code}")
        return True, "更新成功"
    
    def get_all_positions(self) -> List[Holding]:
        """获取所有持仓"""
        return list(self._positions.values())
    
    def get_position(self, code: str) -> Optional[Holding]:
        """获取单个持仓"""
        return self._positions.get(code)
    
    def get_position_count(self) -> int:
        """获取持仓数量"""
        return len(self._positions)
    
    def calculate_pnl(self, holding: Holding, current_price: float) -> PnLResult:
        """
        计算单个持仓的盈亏
        
        Args:
            holding: 持仓记录
            current_price: 当前价格
        
        Returns:
            PnLResult 盈亏结果
        """
        cost_value = holding.buy_price * holding.quantity
        market_value = current_price * holding.quantity
        pnl_amount = market_value - cost_value
        
        if holding.buy_price > 0:
            pnl_pct = (current_price - holding.buy_price) / holding.buy_price
        else:
            pnl_pct = 0
        
        holding_days = (date.today() - holding.buy_date).days
        is_stop_loss = pnl_pct <= self.STOP_LOSS_THRESHOLD
        
        return PnLResult(
            pnl_amount=pnl_amount,
            pnl_pct=pnl_pct,
            market_value=market_value,
            cost_value=cost_value,
            holding_days=holding_days,
            is_stop_loss=is_stop_loss
        )
    
    def get_holding_days(self, holding: Holding) -> int:
        """计算持仓天数"""
        return max(0, (date.today() - holding.buy_date).days)
    
    def get_portfolio_summary(self, prices: Dict[str, float]) -> Dict[str, Any]:
        """
        获取持仓组合汇总
        
        Args:
            prices: 当前价格字典 {股票代码: 价格}
        
        Returns:
            汇总信息字典
        """
        if not self._positions:
            return {
                'total_cost': 0,
                'total_market_value': 0,
                'total_pnl': 0,
                'total_pnl_pct': 0,
                'position_count': 0,
                'stop_loss_count': 0
            }
        
        total_cost = 0
        total_market_value = 0
        stop_loss_count = 0
        
        for code, holding in self._positions.items():
            current_price = prices.get(code, holding.buy_price)
            pnl = self.calculate_pnl(holding, current_price)
            
            total_cost += pnl.cost_value
            total_market_value += pnl.market_value
            
            if pnl.is_stop_loss:
                stop_loss_count += 1
        
        total_pnl = total_market_value - total_cost
        total_pnl_pct = total_pnl / total_cost if total_cost > 0 else 0
        
        return {
            'total_cost': total_cost,
            'total_market_value': total_market_value,
            'total_pnl': total_pnl,
            'total_pnl_pct': total_pnl_pct,
            'position_count': len(self._positions),
            'stop_loss_count': stop_loss_count
        }
    
    def export_csv(self) -> str:
        """
        导出持仓为 CSV 字符串
        
        Returns:
            CSV 格式字符串
        """
        if not self._positions:
            return "code,name,buy_price,buy_date,quantity,strategy,note\n"
        
        df = self._to_dataframe()
        return df.to_csv(index=False)
    
    def _load_from_csv(self) -> None:
        """从 CSV 文件加载持仓"""
        if not os.path.exists(self.csv_file):
            logger.info(f"持仓文件不存在，将创建新文件: {self.csv_file}")
            return
        
        try:
            df = pd.read_csv(self.csv_file)
            
            for _, row in df.iterrows():
                try:
                    holding = Holding(
                        code=str(row['code']).zfill(6),
                        name=str(row['name']),
                        buy_price=float(row['buy_price']),
                        buy_date=datetime.strptime(str(row['buy_date']), '%Y-%m-%d').date(),
                        quantity=int(row['quantity']),
                        strategy=str(row['strategy']),
                        note=str(row.get('note', '')) if pd.notna(row.get('note')) else ''
                    )
                    self._positions[holding.code] = holding
                except Exception as e:
                    logger.warning(f"解析持仓记录失败: {e}")
                    continue
            
            logger.info(f"加载 {len(self._positions)} 条持仓记录")
            
        except Exception as e:
            logger.error(f"加载持仓文件失败: {e}")
    
    def _save_to_csv(self) -> None:
        """保存持仓到 CSV 文件"""
        try:
            # 确保目录存在
            os.makedirs(self.data_path, exist_ok=True)
            
            df = self._to_dataframe()
            df.to_csv(self.csv_file, index=False)
            
            logger.debug(f"保存 {len(self._positions)} 条持仓记录")
            
        except Exception as e:
            logger.error(f"保存持仓文件失败: {e}")
    
    def _to_dataframe(self) -> pd.DataFrame:
        """转换为 DataFrame"""
        if not self._positions:
            return pd.DataFrame(columns=['code', 'name', 'buy_price', 'buy_date', 'quantity', 'strategy', 'note'])
        
        data = []
        for holding in self._positions.values():
            data.append({
                'code': holding.code,
                'name': holding.name,
                'buy_price': holding.buy_price,
                'buy_date': holding.buy_date.strftime('%Y-%m-%d'),
                'quantity': holding.quantity,
                'strategy': holding.strategy,
                'note': holding.note
            })
        
        return pd.DataFrame(data)
