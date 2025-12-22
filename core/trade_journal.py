"""
Trade Journal Module - 交易记录管理

提供交易记录的数据模型、持久化存储和统计分析功能。
"""

import csv
import logging
import os
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import List, Optional, Tuple
import uuid

logger = logging.getLogger(__name__)


class TradeAction(Enum):
    """交易动作枚举"""
    BUY = "买入"
    SELL = "卖出"


@dataclass
class TradeRecord:
    """
    交易记录数据类
    
    包含单条交易的完整信息，支持必填字段和可选字段。
    """
    # 必填字段
    code: str                           # 股票代码
    name: str                           # 股票名称
    action: TradeAction                 # 买入/卖出
    price: float                        # 成交价格
    quantity: int                       # 成交数量
    trade_date: date                    # 成交日期
    
    # 可选字段
    signal_id: Optional[str] = None     # 关联的信号ID
    signal_date: Optional[date] = None  # 信号生成日期
    signal_price: Optional[float] = None  # 信号建议价格
    strategy: str = ""                  # 使用策略
    reason: str = ""                    # 交易原因
    commission: float = 0.0             # 实际手续费
    note: str = ""                      # 备注
    
    # 自动生成字段
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    
    @property
    def total_amount(self) -> float:
        """成交金额 = price × quantity"""
        return self.price * self.quantity
    
    @property
    def slippage(self) -> Optional[float]:
        """
        滑点（实际价格与信号价格的偏差百分比）
        
        计算公式: (price - signal_price) / signal_price
        如果没有信号价格或信号价格为0，返回 None
        """
        if self.signal_price and self.signal_price > 0:
            return (self.price - self.signal_price) / self.signal_price
        return None
    
    @property
    def execution_delay(self) -> Optional[int]:
        """
        执行延迟（天数）
        
        计算公式: trade_date - signal_date
        如果没有信号日期，返回 None
        """
        if self.signal_date:
            return (self.trade_date - self.signal_date).days
        return None


@dataclass
class TradePerformance:
    """
    交易表现统计数据类
    
    包含交易统计的各项指标。
    """
    total_trades: int = 0               # 总交易次数
    buy_trades: int = 0                 # 买入次数
    sell_trades: int = 0                # 卖出次数
    closed_trades: int = 0              # 已平仓交易数（匹配的买卖对）
    profitable_trades: int = 0          # 盈利交易数
    total_profit: float = 0.0           # 总盈亏金额
    total_commission: float = 0.0       # 总手续费
    net_profit: float = 0.0             # 净利润 = total_profit - total_commission
    win_rate: float = 0.0               # 胜率 = profitable_trades / closed_trades
    average_holding_days: float = 0.0   # 平均持仓天数
    average_slippage: float = 0.0       # 平均滑点
    signal_execution_rate: float = 0.0  # 信号执行率


class TradeJournal:
    """
    交易日志管理器
    
    负责交易记录的增删改查和持久化存储。
    """
    
    # CSV 文件的列名（顺序很重要）
    CSV_COLUMNS = [
        'id', 'code', 'name', 'action', 'price', 'quantity', 'trade_date',
        'signal_id', 'signal_date', 'signal_price', 'strategy', 'reason',
        'commission', 'note'
    ]
    
    def __init__(self, file_path: str = "data/trade_journal.csv"):
        """
        初始化交易日志管理器
        
        Args:
            file_path: CSV 文件路径，默认为 data/trade_journal.csv
        """
        self.file_path = file_path
        self._records: List[TradeRecord] = []
        self._load_from_csv()
    
    def _load_from_csv(self) -> None:
        """
        从 CSV 文件加载交易记录
        
        如果文件不存在，创建空列表。
        如果文件存在但有错误行，跳过错误行并记录警告。
        """
        self._records = []
        
        if not os.path.exists(self.file_path):
            logger.info(f"交易记录文件不存在，将在首次添加时创建: {self.file_path}")
            return
        
        try:
            with open(self.file_path, 'r', encoding='utf-8', newline='') as f:
                reader = csv.DictReader(f)
                for row_num, row in enumerate(reader, start=2):  # 从2开始，因为第1行是表头
                    try:
                        record = self._row_to_record(row)
                        self._records.append(record)
                    except Exception as e:
                        logger.warning(f"跳过第 {row_num} 行，解析错误: {e}")
                        continue
            
            logger.info(f"成功加载 {len(self._records)} 条交易记录")
        except Exception as e:
            logger.error(f"加载交易记录文件失败: {e}")
            self._records = []
    
    def _row_to_record(self, row: dict) -> TradeRecord:
        """
        将 CSV 行转换为 TradeRecord 对象
        
        Args:
            row: CSV 行数据字典
            
        Returns:
            TradeRecord 对象
            
        Raises:
            ValueError: 如果必填字段缺失或格式错误
        """
        # 解析必填字段
        code = row.get('code', '').strip()
        name = row.get('name', '').strip()
        action_str = row.get('action', '').strip()
        price_str = row.get('price', '').strip()
        quantity_str = row.get('quantity', '').strip()
        trade_date_str = row.get('trade_date', '').strip()
        
        if not all([code, name, action_str, price_str, quantity_str, trade_date_str]):
            raise ValueError("必填字段缺失")
        
        # 解析 action
        action = TradeAction.BUY if action_str == "买入" else TradeAction.SELL
        
        # 解析数值
        price = float(price_str)
        quantity = int(quantity_str)
        
        # 解析日期
        trade_date = datetime.strptime(trade_date_str, '%Y-%m-%d').date()
        
        # 解析可选字段
        signal_id = row.get('signal_id', '').strip() or None
        
        signal_date = None
        signal_date_str = row.get('signal_date', '').strip()
        if signal_date_str:
            signal_date = datetime.strptime(signal_date_str, '%Y-%m-%d').date()
        
        signal_price = None
        signal_price_str = row.get('signal_price', '').strip()
        if signal_price_str:
            signal_price = float(signal_price_str)
        
        strategy = row.get('strategy', '').strip()
        reason = row.get('reason', '').strip()
        
        commission = 0.0
        commission_str = row.get('commission', '').strip()
        if commission_str:
            commission = float(commission_str)
        
        note = row.get('note', '').strip()
        
        # 获取 ID（如果存在）
        record_id = row.get('id', '').strip() or str(uuid.uuid4())[:8]
        
        return TradeRecord(
            code=code,
            name=name,
            action=action,
            price=price,
            quantity=quantity,
            trade_date=trade_date,
            signal_id=signal_id,
            signal_date=signal_date,
            signal_price=signal_price,
            strategy=strategy,
            reason=reason,
            commission=commission,
            note=note,
            id=record_id
        )
    
    def _record_to_row(self, record: TradeRecord) -> dict:
        """
        将 TradeRecord 对象转换为 CSV 行字典
        
        Args:
            record: TradeRecord 对象
            
        Returns:
            CSV 行数据字典
        """
        return {
            'id': record.id,
            'code': record.code,
            'name': record.name,
            'action': record.action.value,
            'price': str(record.price),
            'quantity': str(record.quantity),
            'trade_date': record.trade_date.strftime('%Y-%m-%d'),
            'signal_id': record.signal_id or '',
            'signal_date': record.signal_date.strftime('%Y-%m-%d') if record.signal_date else '',
            'signal_price': str(record.signal_price) if record.signal_price else '',
            'strategy': record.strategy,
            'reason': record.reason,
            'commission': str(record.commission) if record.commission else '',
            'note': record.note
        }
    
    def _save_to_csv(self) -> None:
        """
        将所有交易记录保存到 CSV 文件
        
        如果目录不存在，会自动创建。
        """
        # 确保目录存在
        dir_path = os.path.dirname(self.file_path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path)
        
        with open(self.file_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.CSV_COLUMNS)
            writer.writeheader()
            for record in self._records:
                writer.writerow(self._record_to_row(record))
        
        logger.debug(f"保存 {len(self._records)} 条交易记录到 {self.file_path}")
    
    def _append_to_csv(self, record: TradeRecord) -> None:
        """
        追加单条交易记录到 CSV 文件
        
        如果文件不存在，会创建新文件并写入表头。
        
        Args:
            record: 要追加的交易记录
        """
        # 确保目录存在
        dir_path = os.path.dirname(self.file_path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path)
        
        file_exists = os.path.exists(self.file_path)
        
        with open(self.file_path, 'a', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.CSV_COLUMNS)
            
            # 如果文件不存在或为空，写入表头
            if not file_exists or os.path.getsize(self.file_path) == 0:
                writer.writeheader()
            
            writer.writerow(self._record_to_row(record))
        
        logger.debug(f"追加交易记录: {record.id}")
    
    def add_trade(self, record: TradeRecord) -> Tuple[bool, str]:
        """
        添加交易记录
        
        验证必填字段、价格、数量和日期后，追加到 CSV 文件。
        
        Args:
            record: 要添加的交易记录
            
        Returns:
            (成功, 消息) 元组
        """
        # 验证必填字段
        if not record.code or not record.code.strip():
            return False, "缺少必填字段: code"
        if not record.name or not record.name.strip():
            return False, "缺少必填字段: name"
        if not record.action:
            return False, "缺少必填字段: action"
        if record.price is None:
            return False, "缺少必填字段: price"
        if record.quantity is None:
            return False, "缺少必填字段: quantity"
        if not record.trade_date:
            return False, "缺少必填字段: trade_date"
        
        # 验证 price > 0
        if record.price <= 0:
            return False, "成交价格必须大于0"
        
        # 验证 quantity > 0
        if record.quantity <= 0:
            return False, "成交数量必须大于0"
        
        # 验证 trade_date 不是未来日期
        if record.trade_date > date.today():
            return False, "成交日期不能是未来日期"
        
        # 添加到内存列表
        self._records.append(record)
        
        # 追加到 CSV 文件
        try:
            self._append_to_csv(record)
            logger.info(f"添加交易记录成功: {record.id} - {record.code} {record.action.value}")
            return True, f"交易记录添加成功: {record.id}"
        except Exception as e:
            # 如果写入失败，从内存中移除
            self._records.remove(record)
            logger.error(f"添加交易记录失败: {e}")
            return False, f"保存交易记录失败: {e}"
    
    def get_all_trades(self) -> List[TradeRecord]:
        """
        获取所有交易记录
        
        Returns:
            所有交易记录列表
        """
        return list(self._records)
    
    @property
    def records(self) -> List[TradeRecord]:
        """获取所有交易记录（只读）"""
        return list(self._records)
    
    def get_trades(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        code: Optional[str] = None,
        action: Optional[TradeAction] = None,
        strategy: Optional[str] = None
    ) -> List[TradeRecord]:
        """
        查询交易记录，支持多种筛选条件
        
        Args:
            start_date: 开始日期（包含），None 表示不限制
            end_date: 结束日期（包含），None 表示不限制
            code: 股票代码筛选，None 表示不限制
            action: 交易动作筛选（买入/卖出），None 表示不限制
            strategy: 策略名称筛选，None 表示不限制
            
        Returns:
            符合条件的交易记录列表，按 trade_date 降序排序（最新的在前）
        """
        result = []
        
        for record in self._records:
            # 日期范围筛选
            if start_date is not None and record.trade_date < start_date:
                continue
            if end_date is not None and record.trade_date > end_date:
                continue
            
            # 股票代码筛选
            if code is not None and record.code != code:
                continue
            
            # 交易动作筛选
            if action is not None and record.action != action:
                continue
            
            # 策略名称筛选
            if strategy is not None and record.strategy != strategy:
                continue
            
            result.append(record)
        
        # 按 trade_date 降序排序（最新的在前）
        result.sort(key=lambda r: r.trade_date, reverse=True)
        
        return result
    
    def delete_trade(self, trade_id: str) -> Tuple[bool, str]:
        """
        删除交易记录
        
        根据 trade_id 删除记录，并更新 CSV 文件。
        
        Args:
            trade_id: 要删除的交易记录 ID
            
        Returns:
            (成功, 消息) 元组
        """
        # 查找要删除的记录
        record_to_delete = None
        for record in self._records:
            if record.id == trade_id:
                record_to_delete = record
                break
        
        if record_to_delete is None:
            return False, f"未找到交易记录: {trade_id}"
        
        # 从内存中移除
        self._records.remove(record_to_delete)
        
        # 重新保存整个 CSV 文件
        try:
            self._save_to_csv()
            logger.info(f"删除交易记录成功: {trade_id}")
            return True, f"交易记录删除成功: {trade_id}"
        except Exception as e:
            # 如果保存失败，恢复内存中的记录
            self._records.append(record_to_delete)
            logger.error(f"删除交易记录失败: {e}")
            return False, f"删除交易记录失败: {e}"
    
    def calculate_performance(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> TradePerformance:
        """
        计算交易表现统计
        
        通过匹配买卖对来计算已平仓交易的盈亏。
        匹配逻辑：对于每只股票，按时间顺序匹配买入和卖出记录（FIFO）。
        
        Args:
            start_date: 开始日期（包含），None 表示不限制
            end_date: 结束日期（包含），None 表示不限制
            
        Returns:
            TradePerformance 对象，包含各项统计指标
            
        Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7
        """
        # 获取指定日期范围内的交易记录
        trades = self.get_trades(start_date=start_date, end_date=end_date)
        
        # 初始化统计数据
        performance = TradePerformance()
        
        if not trades:
            return performance
        
        # 基础统计
        performance.total_trades = len(trades)
        performance.buy_trades = sum(1 for t in trades if t.action == TradeAction.BUY)
        performance.sell_trades = sum(1 for t in trades if t.action == TradeAction.SELL)
        performance.total_commission = sum(t.commission for t in trades)
        
        # 按股票代码分组，用于匹配买卖对
        # 使用 FIFO（先进先出）方式匹配买入和卖出
        trades_by_code: dict = {}
        for trade in trades:
            if trade.code not in trades_by_code:
                trades_by_code[trade.code] = []
            trades_by_code[trade.code].append(trade)
        
        # 计算已平仓交易的盈亏
        closed_trades = 0
        profitable_trades = 0
        total_profit = 0.0
        total_holding_days = 0
        
        for code, code_trades in trades_by_code.items():
            # 按交易日期升序排序（用于 FIFO 匹配）
            code_trades.sort(key=lambda t: t.trade_date)
            
            # 分离买入和卖出记录
            buy_queue: List[TradeRecord] = []
            
            for trade in code_trades:
                if trade.action == TradeAction.BUY:
                    buy_queue.append(trade)
                elif trade.action == TradeAction.SELL:
                    # 尝试匹配买入记录
                    remaining_sell_qty = trade.quantity
                    
                    while remaining_sell_qty > 0 and buy_queue:
                        buy_trade = buy_queue[0]
                        
                        # 计算可匹配的数量
                        match_qty = min(buy_trade.quantity, remaining_sell_qty)
                        
                        # 计算这笔匹配的盈亏
                        profit = (trade.price - buy_trade.price) * match_qty
                        total_profit += profit
                        
                        # 计算持仓天数
                        holding_days = (trade.trade_date - buy_trade.trade_date).days
                        total_holding_days += holding_days
                        
                        # 记录已平仓交易
                        closed_trades += 1
                        if profit > 0:
                            profitable_trades += 1
                        
                        # 更新剩余数量
                        remaining_sell_qty -= match_qty
                        
                        if match_qty >= buy_trade.quantity:
                            # 买入记录完全匹配，移除
                            buy_queue.pop(0)
                        else:
                            # 买入记录部分匹配，更新剩余数量
                            # 创建新的买入记录替换原记录
                            buy_queue[0] = TradeRecord(
                                code=buy_trade.code,
                                name=buy_trade.name,
                                action=buy_trade.action,
                                price=buy_trade.price,
                                quantity=buy_trade.quantity - match_qty,
                                trade_date=buy_trade.trade_date,
                                signal_id=buy_trade.signal_id,
                                signal_date=buy_trade.signal_date,
                                signal_price=buy_trade.signal_price,
                                strategy=buy_trade.strategy,
                                reason=buy_trade.reason,
                                commission=buy_trade.commission,
                                note=buy_trade.note,
                                id=buy_trade.id
                            )
        
        # 填充统计结果
        performance.closed_trades = closed_trades
        performance.profitable_trades = profitable_trades
        performance.total_profit = total_profit
        performance.net_profit = total_profit - performance.total_commission
        
        # 计算胜率（如果没有已平仓交易，胜率为 0）
        if closed_trades > 0:
            performance.win_rate = profitable_trades / closed_trades
            performance.average_holding_days = total_holding_days / closed_trades
        else:
            performance.win_rate = 0.0
            performance.average_holding_days = 0.0
        
        return performance
    
    def get_signal_execution_stats(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> dict:
        """
        获取信号执行统计
        
        计算信号执行率、平均滑点，并返回未执行信号列表。
        
        Args:
            start_date: 开始日期（包含），None 表示不限制
            end_date: 结束日期（包含），None 表示不限制
            
        Returns:
            {
                'signal_execution_rate': float,  # 信号执行率
                'average_slippage': float,       # 平均滑点
                'executed_signals': int,         # 已执行信号数
                'total_signals': int,            # 总信号数
                'unexecuted_signals': List[str]  # 未执行信号ID列表
            }
            
        Requirements: 5.2, 5.3, 5.5
        """
        # 获取指定日期范围内的交易记录
        trades = self.get_trades(start_date=start_date, end_date=end_date)
        
        # 统计有信号关联的交易
        trades_with_signal = [t for t in trades if t.signal_id]
        
        # 计算平均滑点（只计算有滑点数据的交易）
        slippages = [t.slippage for t in trades_with_signal if t.slippage is not None]
        average_slippage = sum(slippages) / len(slippages) if slippages else 0.0
        
        # 获取已执行的信号ID集合
        executed_signal_ids = {t.signal_id for t in trades_with_signal}
        
        # 尝试从 SignalStore 获取总信号数
        # 如果 SignalStore 不可用，则只基于交易记录计算
        total_signals = len(executed_signal_ids)
        unexecuted_signals: List[str] = []
        
        try:
            from core.signal_store import SignalStore
            signal_store = SignalStore()
            signals_df = signal_store.load_signals(
                start_date=start_date,
                end_date=end_date
            )
            
            if not signals_df.empty:
                # 生成信号ID（使用日期+代码作为唯一标识）
                all_signal_ids = set()
                for _, row in signals_df.iterrows():
                    signal_id = f"{row['generated_date']}_{row['code']}"
                    all_signal_ids.add(signal_id)
                
                total_signals = len(all_signal_ids)
                unexecuted_signals = list(all_signal_ids - executed_signal_ids)
        except Exception as e:
            logger.warning(f"无法获取信号存储数据: {e}")
            # 如果无法获取信号数据，使用已执行信号数作为总数
            total_signals = len(executed_signal_ids)
        
        # 计算信号执行率
        signal_execution_rate = len(executed_signal_ids) / total_signals if total_signals > 0 else 0.0
        
        return {
            'signal_execution_rate': signal_execution_rate,
            'average_slippage': average_slippage,
            'executed_signals': len(executed_signal_ids),
            'total_signals': total_signals,
            'unexecuted_signals': unexecuted_signals
        }
    
    def compare_with_backtest(
        self,
        strategy: str,
        start_date: date,
        end_date: date
    ) -> dict:
        """
        与回测结果对比
        
        计算实盘收益率与回测收益率的差距，帮助用户验证系统有效性。
        
        Args:
            strategy: 策略名称
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            {
                'actual_return': float,      # 实盘收益率
                'backtest_return': float,    # 回测收益率
                'performance_gap': float,    # 性能差距 (actual - backtest)
                'actual_trades': int,        # 实盘交易次数
                'backtest_trades': int,      # 回测交易次数
                'comparison_period': str,    # 对比期间
                'strategy': str              # 策略名称
            }
            
        Requirements: 7.1, 7.2, 7.4
        """
        result = {
            'actual_return': 0.0,
            'backtest_return': 0.0,
            'performance_gap': 0.0,
            'actual_trades': 0,
            'backtest_trades': 0,
            'comparison_period': f"{start_date} ~ {end_date}",
            'strategy': strategy
        }
        
        # 计算实盘收益率
        actual_return, actual_trades = self._calculate_actual_return(
            strategy=strategy,
            start_date=start_date,
            end_date=end_date
        )
        result['actual_return'] = actual_return
        result['actual_trades'] = actual_trades
        
        # 获取回测收益率
        backtest_return, backtest_trades = self._get_backtest_return(
            strategy=strategy,
            start_date=start_date,
            end_date=end_date
        )
        result['backtest_return'] = backtest_return
        result['backtest_trades'] = backtest_trades
        
        # 计算性能差距
        result['performance_gap'] = actual_return - backtest_return
        
        logger.info(f"回测对比完成: 策略={strategy}, 实盘收益={actual_return:.2%}, "
                   f"回测收益={backtest_return:.2%}, 差距={result['performance_gap']:.2%}")
        
        return result
    
    def _calculate_actual_return(
        self,
        strategy: str,
        start_date: date,
        end_date: date
    ) -> Tuple[float, int]:
        """
        计算实盘收益率
        
        基于已平仓交易计算实际收益率。
        
        Args:
            strategy: 策略名称
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            (收益率, 交易次数) 元组
        """
        # 获取指定策略和日期范围内的交易记录
        trades = self.get_trades(
            start_date=start_date,
            end_date=end_date,
            strategy=strategy if strategy else None
        )
        
        if not trades:
            return 0.0, 0
        
        # 按股票代码分组，计算已平仓交易的盈亏
        trades_by_code: dict = {}
        for trade in trades:
            if trade.code not in trades_by_code:
                trades_by_code[trade.code] = []
            trades_by_code[trade.code].append(trade)
        
        total_investment = 0.0  # 总投入资金
        total_profit = 0.0      # 总盈亏
        trade_count = 0
        
        for code, code_trades in trades_by_code.items():
            # 按交易日期升序排序（用于 FIFO 匹配）
            code_trades.sort(key=lambda t: t.trade_date)
            
            # 分离买入和卖出记录
            buy_queue: List[TradeRecord] = []
            
            for trade in code_trades:
                if trade.action == TradeAction.BUY:
                    buy_queue.append(trade)
                elif trade.action == TradeAction.SELL:
                    # 尝试匹配买入记录
                    remaining_sell_qty = trade.quantity
                    
                    while remaining_sell_qty > 0 and buy_queue:
                        buy_trade = buy_queue[0]
                        
                        # 计算可匹配的数量
                        match_qty = min(buy_trade.quantity, remaining_sell_qty)
                        
                        # 计算这笔匹配的投入和盈亏
                        investment = buy_trade.price * match_qty
                        profit = (trade.price - buy_trade.price) * match_qty
                        
                        # 扣除手续费
                        profit -= (buy_trade.commission + trade.commission) * (match_qty / trade.quantity)
                        
                        total_investment += investment
                        total_profit += profit
                        trade_count += 1
                        
                        # 更新剩余数量
                        remaining_sell_qty -= match_qty
                        
                        if match_qty >= buy_trade.quantity:
                            buy_queue.pop(0)
                        else:
                            # 部分匹配，更新剩余数量
                            buy_queue[0] = TradeRecord(
                                code=buy_trade.code,
                                name=buy_trade.name,
                                action=buy_trade.action,
                                price=buy_trade.price,
                                quantity=buy_trade.quantity - match_qty,
                                trade_date=buy_trade.trade_date,
                                signal_id=buy_trade.signal_id,
                                signal_date=buy_trade.signal_date,
                                signal_price=buy_trade.signal_price,
                                strategy=buy_trade.strategy,
                                reason=buy_trade.reason,
                                commission=buy_trade.commission,
                                note=buy_trade.note,
                                id=buy_trade.id
                            )
        
        # 计算收益率
        if total_investment > 0:
            actual_return = total_profit / total_investment
        else:
            actual_return = 0.0
        
        return actual_return, trade_count
    
    def _get_backtest_return(
        self,
        strategy: str,
        start_date: date,
        end_date: date
    ) -> Tuple[float, int]:
        """
        获取回测收益率
        
        尝试从回测引擎获取指定策略和日期范围的回测结果。
        
        Args:
            strategy: 策略名称
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            (收益率, 交易次数) 元组
        """
        try:
            from backtest.run_backtest import BacktestConfig, BacktestEngine
            from core.data_feed import DataFeed
            
            # 获取策略类
            strategy_class = self._get_strategy_class(strategy)
            if strategy_class is None:
                logger.warning(f"未找到策略类: {strategy}")
                return 0.0, 0
            
            # 创建回测配置
            config = BacktestConfig(
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d')
            )
            
            # 创建回测引擎
            engine = BacktestEngine(config)
            
            # 加载数据 - 使用默认路径
            data_feed = DataFeed(
                raw_path='data/raw',
                processed_path='data/processed'
            )
            
            # 获取交易过的股票代码
            trades = self.get_trades(
                start_date=start_date,
                end_date=end_date,
                strategy=strategy if strategy else None
            )
            codes = list(set(t.code for t in trades))
            
            if not codes:
                logger.warning("没有找到相关交易记录")
                return 0.0, 0
            
            # 添加股票数据
            for code in codes:
                df = data_feed.get_stock_data(code)
                if df is not None and not df.empty:
                    engine.add_data(code, df)
            
            # 设置策略
            engine.set_strategy(strategy_class)
            
            # 执行回测
            result = engine.run()
            
            return result.total_return, result.trade_count
            
        except Exception as e:
            logger.warning(f"获取回测收益率失败: {e}")
            return 0.0, 0
    
    def _get_strategy_class(self, strategy_name: str):
        """
        根据策略名称获取策略类
        
        Args:
            strategy_name: 策略名称
            
        Returns:
            策略类，如果未找到返回 None
        """
        try:
            # 策略名称到类的映射
            strategy_map = {}
            
            # 尝试导入已知策略
            try:
                from strategies.rsrs_strategy import RSRSStrategy
                strategy_map['RSRS'] = RSRSStrategy
                strategy_map['rsrs'] = RSRSStrategy
                strategy_map['RSI'] = RSRSStrategy  # 兼容旧名称
            except ImportError:
                pass
            
            try:
                from strategies.bollinger_reversion_strategy import BollingerReversionStrategy
                strategy_map['Bollinger'] = BollingerReversionStrategy
                strategy_map['bollinger'] = BollingerReversionStrategy
                strategy_map['布林带'] = BollingerReversionStrategy
            except ImportError:
                pass
            
            try:
                from strategies.trend_filtered_macd_strategy import TrendFilteredMACDStrategy
                strategy_map['MACD'] = TrendFilteredMACDStrategy
                strategy_map['macd'] = TrendFilteredMACDStrategy
                strategy_map['TrendMACD'] = TrendFilteredMACDStrategy
            except ImportError:
                pass
            
            return strategy_map.get(strategy_name)
            
        except Exception as e:
            logger.warning(f"获取策略类失败: {e}")
            return None
    
    def export_csv(self, trades: Optional[List[TradeRecord]] = None) -> str:
        """
        导出交易记录为 CSV 字符串
        
        Args:
            trades: 要导出的交易记录列表，None 时导出所有记录
            
        Returns:
            CSV 格式的字符串
            
        Requirements: 6.5
        """
        import io
        
        if trades is None:
            trades = self._records
        
        if not trades:
            # 返回只有表头的 CSV
            return ','.join(self.CSV_COLUMNS) + '\n'
        
        # 使用 StringIO 创建内存中的 CSV
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=self.CSV_COLUMNS)
        writer.writeheader()
        
        for record in trades:
            writer.writerow(self._record_to_row(record))
        
        csv_string = output.getvalue()
        output.close()
        
        return csv_string
