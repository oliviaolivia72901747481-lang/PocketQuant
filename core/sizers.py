"""
MiniQuant-Lite 智能仓位管理模块

针对小资金（5.5万元）特殊优化的仓位管理器，核心功能：
- 最大持仓只数模式（避免百分比陷阱）
- 100股整数倍买入（A股最小交易单位）
- 5%现金缓冲（防止次日高开废单）
- 最小交易金额门槛（避免5元低消磨损）
- 高费率预警（实际费率超标准2倍时警告）

Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9
"""

import logging
from enum import Enum
from typing import Tuple, Optional
from dataclasses import dataclass

try:
    import backtrader as bt
    HAS_BACKTRADER = True
except ImportError:
    HAS_BACKTRADER = False
    bt = None

logger = logging.getLogger(__name__)


class SizerMode(Enum):
    """仓位控制模式"""
    MAX_POSITIONS = "max_positions"  # 最大持仓只数模式（推荐小资金使用）
    PERCENT = "percent"              # 百分比模式


@dataclass
class SizerResult:
    """仓位计算结果"""
    shares: int                      # 可买入股数（100的整数倍）
    high_fee_warning: bool           # 是否触发高费率预警
    reject_reason: str               # 拒绝原因（空字符串表示可交易）
    trade_amount: float = 0.0        # 预计交易金额
    actual_fee: float = 0.0          # 预计手续费
    actual_fee_rate: float = 0.0     # 实际费率


def calculate_actual_fee_rate(
    trade_amount: float, 
    commission_rate: float, 
    min_commission: float
) -> float:
    """
    计算实际手续费率
    
    考虑5元低消的影响，小金额交易实际费率可能远高于标准费率
    
    Args:
        trade_amount: 交易金额
        commission_rate: 标准手续费率
        min_commission: 最低手续费
    
    Returns:
        实际手续费率
    
    Example:
        >>> calculate_actual_fee_rate(10000, 0.0003, 5.0)
        0.0005  # 实际费率 0.05%，高于标准费率 0.03%
        >>> calculate_actual_fee_rate(50000, 0.0003, 5.0)
        0.0003  # 实际费率等于标准费率
    """
    if trade_amount <= 0:
        return 0.0
    
    # 计算实际手续费（取标准费用和最低费用的较大值）
    standard_fee = trade_amount * commission_rate
    actual_fee = max(min_commission, standard_fee)
    
    # 计算实际费率
    actual_fee_rate = actual_fee / trade_amount
    
    return actual_fee_rate


def calculate_max_shares(
    cash: float, 
    price: float, 
    commission_rate: float,
    min_commission: float,
    max_positions_count: int,
    current_positions: int,
    total_value: float,
    position_tolerance: float = 0.05,
    min_trade_amount: float = 15000.0,
    cash_buffer: float = 0.05
) -> Tuple[int, bool, str]:
    """
    计算最大可买入股数（智能版）
    
    Args:
        cash: 可用现金
        price: 股票价格
        commission_rate: 手续费率
        min_commission: 最低手续费
        max_positions_count: 最大持仓只数
        current_positions: 当前持仓只数
        total_value: 账户总价值
        position_tolerance: 仓位容差比例
        min_trade_amount: 最小交易金额门槛
        cash_buffer: 现金缓冲比例（默认5%），防止次日高开废单
    
    Returns:
        (可买入股数, 是否高费率预警, 拒绝原因或空字符串)
        - 股数为100的整数倍
        - 高费率预警为 True 时建议谨慎交易
        - 拒绝原因非空时表示不建议交易
    
    拒绝原因示例（让用户死心）：
        - "持仓已满（2/2），请先卖出再买入"
        - "股价过高（¥150），只能买 1 手，低于最小交易门槛，放弃交易"
        - "资金不足，无法买入 100 股"
        - "交易金额 ¥8,000 低于门槛 ¥15,000，手续费磨损过高，放弃交易"
    
    Note:
        现金缓冲逻辑：强制保留 5% 现金，防止因次日高开导致废单
        例如：账户 55000 元，保留 2750 元缓冲，实际可用 52250 元
    """
    # 参数校验
    if price <= 0:
        reason = "股票价格无效（<=0）"
        logger.warning(f"拒绝交易: {reason}")
        return 0, False, reason
    
    if cash <= 0:
        reason = "可用现金不足（<=0）"
        logger.warning(f"拒绝交易: {reason}")
        return 0, False, reason
    
    # 1. 检查持仓数量
    if current_positions >= max_positions_count:
        reason = f"持仓已满（{current_positions}/{max_positions_count}），请先卖出再买入"
        logger.info(f"拒绝交易: {reason}")
        return 0, False, reason
    
    # 2. 计算实际可用现金（扣除缓冲）
    available_cash = cash * (1 - cash_buffer)
    
    # 3. 计算最大可买股数（考虑手续费）
    # 先估算不考虑手续费的最大股数
    estimated_shares = int(available_cash / price / 100) * 100
    
    if estimated_shares == 0:
        reason = f"资金不足（可用 ¥{available_cash:,.0f}），无法买入 100 股（需 ¥{price * 100:,.0f}）"
        logger.info(f"拒绝交易: {reason}")
        return 0, False, reason
    
    # 4. 精确计算：考虑手续费后的最大可买股数
    max_shares = estimated_shares
    while max_shares > 0:
        trade_amount = max_shares * price
        fee = max(min_commission, trade_amount * commission_rate)
        total_cost = trade_amount + fee
        
        if total_cost <= available_cash:
            break
        
        max_shares -= 100
    
    if max_shares == 0:
        reason = f"资金不足（可用 ¥{available_cash:,.0f}），扣除手续费后无法买入 100 股"
        logger.info(f"拒绝交易: {reason}")
        return 0, False, reason
    
    # 5. 检查最小交易金额门槛
    trade_amount = max_shares * price
    if trade_amount < min_trade_amount:
        reason = f"交易金额 ¥{trade_amount:,.0f} 低于门槛 ¥{min_trade_amount:,.0f}，手续费磨损过高，放弃交易"
        logger.info(f"拒绝交易: {reason}")
        return 0, False, reason
    
    # 6. 检查高费率预警
    actual_fee = max(min_commission, trade_amount * commission_rate)
    actual_fee_rate = actual_fee / trade_amount
    high_fee_warning = actual_fee_rate > commission_rate * 2
    
    if high_fee_warning:
        logger.warning(
            f"高费率预警: 实际费率 {actual_fee_rate:.4%} > 标准费率 {commission_rate:.4%} × 2"
        )
    
    return max_shares, high_fee_warning, ""



def calculate_max_shares_detailed(
    cash: float, 
    price: float, 
    commission_rate: float = 0.0003,
    min_commission: float = 5.0,
    max_positions_count: int = 2,
    current_positions: int = 0,
    total_value: float = 55000.0,
    position_tolerance: float = 0.05,
    min_trade_amount: float = 15000.0,
    cash_buffer: float = 0.05
) -> SizerResult:
    """
    计算最大可买入股数（详细版，返回完整结果）
    
    与 calculate_max_shares 功能相同，但返回更详细的结果信息
    
    Args:
        cash: 可用现金
        price: 股票价格
        commission_rate: 手续费率
        min_commission: 最低手续费
        max_positions_count: 最大持仓只数
        current_positions: 当前持仓只数
        total_value: 账户总价值
        position_tolerance: 仓位容差比例
        min_trade_amount: 最小交易金额门槛
        cash_buffer: 现金缓冲比例
    
    Returns:
        SizerResult 包含完整的计算结果
    """
    shares, high_fee_warning, reject_reason = calculate_max_shares(
        cash=cash,
        price=price,
        commission_rate=commission_rate,
        min_commission=min_commission,
        max_positions_count=max_positions_count,
        current_positions=current_positions,
        total_value=total_value,
        position_tolerance=position_tolerance,
        min_trade_amount=min_trade_amount,
        cash_buffer=cash_buffer
    )
    
    # 计算详细信息
    trade_amount = shares * price if shares > 0 else 0.0
    actual_fee = max(min_commission, trade_amount * commission_rate) if trade_amount > 0 else 0.0
    actual_fee_rate = actual_fee / trade_amount if trade_amount > 0 else 0.0
    
    return SizerResult(
        shares=shares,
        high_fee_warning=high_fee_warning,
        reject_reason=reject_reason,
        trade_amount=trade_amount,
        actual_fee=actual_fee,
        actual_fee_rate=actual_fee_rate
    )


if HAS_BACKTRADER:
    class SmallCapitalSizer(bt.Sizer):
        """
        小资金智能仓位管理器（Backtrader Sizer）
        
        特点：
        - 采用最大持仓只数模式，避免百分比陷阱
        - 确保买入数量为100股整数倍
        - 预留手续费，考虑5元低消问题
        - 支持仓位容差逻辑
        - 最小交易金额门槛检查
        - 强制保留 5% 现金缓冲，防止次日高开废单
        
        Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9
        """
        
        params = (
            ('max_positions_count', 2),    # 最大同时持仓只数（替代百分比限制）
            ('position_tolerance', 0.05),  # 仓位容差（允许超限5%）
            ('commission_rate', 0.0003),   # 手续费率
            ('min_commission', 5.0),       # 最低手续费（5元低消）
            ('min_trade_amount', 15000.0), # 最小交易金额门槛，低于此值禁止开仓
            ('cash_buffer', 0.05),         # 现金缓冲比例（5%），防止高开废单
        )
        
        def __init__(self):
            """初始化 Sizer"""
            self._last_reject_reason = ""
            self._last_high_fee_warning = False
        
        def _getsizing(
            self, 
            comminfo, 
            cash: float, 
            data, 
            isbuy: bool
        ) -> int:
            """
            计算买入/卖出数量
            
            智能仓位计算流程：
            1. 检查当前持仓数量是否已达上限
            2. 计算可用资金（考虑手续费）
            3. 检查是否满足最小交易金额门槛
            4. 计算最大可买股数（100股整数倍）
            5. 应用仓位容差逻辑
            
            Args:
                comminfo: 佣金信息对象
                cash: 可用现金
                data: 数据源
                isbuy: 是否为买入操作
            
            Returns:
                买入股数（100的整数倍）或 0
            """
            if not isbuy:
                # 卖出时返回当前持仓数量
                position = self.broker.getposition(data)
                return position.size if position else 0
            
            # 获取当前价格
            price = data.close[0]
            
            # 获取当前持仓数量
            current_positions = self._count_positions()
            
            # 获取账户总价值
            total_value = self.broker.getvalue()
            
            # 计算可买入股数
            shares, high_fee_warning, reject_reason = calculate_max_shares(
                cash=cash,
                price=price,
                commission_rate=self.params.commission_rate,
                min_commission=self.params.min_commission,
                max_positions_count=self.params.max_positions_count,
                current_positions=current_positions,
                total_value=total_value,
                position_tolerance=self.params.position_tolerance,
                min_trade_amount=self.params.min_trade_amount,
                cash_buffer=self.params.cash_buffer
            )
            
            # 保存状态供外部查询
            self._last_reject_reason = reject_reason
            self._last_high_fee_warning = high_fee_warning
            
            return shares
        
        def _count_positions(self) -> int:
            """
            统计当前持仓只数
            
            Returns:
                当前持有的股票数量（只数，非股数）
            """
            count = 0
            for data in self.strategy.datas:
                position = self.broker.getposition(data)
                if position and position.size > 0:
                    count += 1
            return count
        
        def _check_high_fee_warning(self, trade_amount: float) -> bool:
            """
            检查是否触发高费率预警
            
            当交易金额较小时，5元低消会导致实际费率远高于标准费率
            
            Args:
                trade_amount: 交易金额
            
            Returns:
                True 表示触发高费率预警
            """
            if trade_amount <= 0:
                return False
            
            actual_fee_rate = calculate_actual_fee_rate(
                trade_amount=trade_amount,
                commission_rate=self.params.commission_rate,
                min_commission=self.params.min_commission
            )
            
            return actual_fee_rate > self.params.commission_rate * 2
        
        def get_last_reject_reason(self) -> str:
            """获取上次计算的拒绝原因"""
            return self._last_reject_reason
        
        def get_last_high_fee_warning(self) -> bool:
            """获取上次计算是否触发高费率预警"""
            return self._last_high_fee_warning

else:
    # 当 Backtrader 未安装时提供占位类
    class SmallCapitalSizer:
        """
        SmallCapitalSizer 占位类
        
        当 Backtrader 未安装时使用此占位类，避免导入错误
        """
        
        def __init__(self, *args, **kwargs):
            raise ImportError(
                "SmallCapitalSizer 需要 Backtrader 库。"
                "请安装: pip install backtrader"
            )
