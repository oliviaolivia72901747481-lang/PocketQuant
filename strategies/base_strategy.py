"""
MiniQuant-Lite 策略基类

提供通用功能：
- 订单状态日志
- 交易记录
- 持仓状态打印

Requirements: 5.1, 5.5
"""

import backtrader as bt
from datetime import date
from typing import Optional
import logging


class BaseStrategy(bt.Strategy):
    """
    策略基类
    
    提供通用功能：
    - 订单状态日志
    - 交易记录
    - 持仓状态打印
    
    所有策略应继承此基类以获得标准的日志记录和订单管理功能。
    """
    
    def __init__(self):
        """初始化基类"""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.order = None  # 当前订单
        self.trade_log = []  # 交易记录
    
    def log(self, txt: str, dt: Optional[date] = None) -> None:
        """
        打印日志
        
        Args:
            txt: 日志内容
            dt: 日期，默认为当前数据日期
        """
        dt = dt or self.datas[0].datetime.date(0)
        self.logger.info(f'{dt.isoformat()} {txt}')
    
    def notify_order(self, order: bt.Order) -> None:
        """
        订单状态通知
        
        处理订单的各种状态变化：
        - Submitted: 订单已提交
        - Accepted: 订单已接受
        - Completed: 订单已完成
        - Canceled/Margin/Rejected: 订单失败
        
        Args:
            order: Backtrader 订单对象
        """
        if order.status in [order.Submitted, order.Accepted]:
            # 订单已提交/接受，等待执行
            return
        
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    f'买入执行: 价格={order.executed.price:.2f}, '
                    f'数量={order.executed.size:.0f}, '
                    f'成本={order.executed.value:.2f}, '
                    f'手续费={order.executed.comm:.2f}'
                )
            else:
                self.log(
                    f'卖出执行: 价格={order.executed.price:.2f}, '
                    f'数量={order.executed.size:.0f}, '
                    f'成本={order.executed.value:.2f}, '
                    f'手续费={order.executed.comm:.2f}'
                )
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            status_name = {
                order.Canceled: '取消',
                order.Margin: '保证金不足',
                order.Rejected: '拒绝'
            }.get(order.status, '未知')
            self.log(f'订单{status_name}')
        
        # 重置订单引用
        self.order = None
    
    def notify_trade(self, trade: bt.Trade) -> None:
        """
        交易完成通知
        
        当一笔交易（开仓+平仓）完成时调用，记录盈亏信息。
        
        Args:
            trade: Backtrader 交易对象
        """
        if not trade.isclosed:
            return
        
        pnl = trade.pnl
        pnl_pct = (trade.pnl / trade.price) * 100 if trade.price > 0 else 0
        
        self.log(
            f'交易完成: 毛利润={trade.pnl:.2f}, '
            f'净利润={trade.pnlcomm:.2f}, '
            f'盈亏比例={pnl_pct:.2f}%'
        )
        
        # 记录交易到日志
        self.trade_log.append({
            'datetime': self.datas[0].datetime.date(0),
            'pnl': trade.pnl,
            'pnlcomm': trade.pnlcomm,
            'price': trade.price,
            'size': trade.size,
        })
    
    def print_position(self) -> None:
        """
        打印当前持仓和资金状态
        
        在每个交易日结束时调用，记录当前持仓和资金状态。
        """
        # 获取当前持仓
        position = self.getposition(self.data)
        
        # 获取账户信息
        cash = self.broker.getcash()
        value = self.broker.getvalue()
        
        if position.size > 0:
            self.log(
                f'持仓状态: 股数={position.size:.0f}, '
                f'成本价={position.price:.2f}, '
                f'现金={cash:.2f}, '
                f'总价值={value:.2f}'
            )
        else:
            self.log(f'空仓状态: 现金={cash:.2f}, 总价值={value:.2f}')
    
    def next(self) -> None:
        """
        每个交易日执行的逻辑
        
        子类应重写此方法实现具体的交易逻辑。
        基类默认在每个交易日结束时打印持仓状态。
        """
        # 子类应重写此方法
        pass
    
    def stop(self) -> None:
        """
        策略结束时调用
        
        打印最终的持仓和资金状态。
        """
        self.log(f'策略结束: 最终资金={self.broker.getvalue():.2f}')
