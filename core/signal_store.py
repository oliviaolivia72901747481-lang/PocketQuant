"""
MiniQuant-Lite 历史信号存储模块

负责将交易信号持久化到单一 CSV 文件，支持：
- 幂等覆盖更新（每日多次生成只保留最后一次）
- 按日期范围、股票代码、信号类型筛选
- 统计计算和 CSV 导出

设计原则：
- 单文件存储，简单粗暴
- 幂等写入，每日覆盖更新
- Pandas 读取 2.6 万行仅需 0.01 秒

Requirements: 1.1-1.5, 2.1-2.5, 4.2-4.4, 5.2
"""

import logging
from dataclasses import dataclass
from typing import List, Optional, TYPE_CHECKING
from datetime import date
from pathlib import Path
import pandas as pd

if TYPE_CHECKING:
    from core.signal_generator import TradingSignal

# 配置日志
logger = logging.getLogger(__name__)


@dataclass
class SignalRecord:
    """
    历史信号记录数据类
    
    用于表示存储在 CSV 中的单条信号记录
    
    Requirements: 1.2
    """
    generated_date: date          # 生成日期
    code: str                     # 股票代码
    name: str                     # 股票名称
    signal_type: str              # 信号类型（买入/卖出）
    price_low: float              # 建议价格下限
    price_high: float             # 建议价格上限
    limit_cap: float              # 限价上限
    reason: str                   # 信号依据
    in_report_window: bool        # 是否财报窗口期
    high_fee_warning: bool        # 是否高费率预警
    market_status: str            # 大盘状态（健康/不佳）


class SignalStore:
    """
    信号存储模块
    
    设计原则：
    - 单文件存储，简单粗暴
    - 幂等写入，每日覆盖更新
    
    Requirements: 1.1-1.5, 2.1-2.5, 4.2-4.4, 5.2
    """
    
    DEFAULT_PATH = Path("data/signal_history.csv")
    
    # CSV 列定义
    COLUMNS = [
        'generated_date', 'code', 'name', 'signal_type',
        'price_low', 'price_high', 'limit_cap', 'reason',
        'in_report_window', 'high_fee_warning', 'market_status'
    ]
    
    def __init__(self, file_path: Path = None):
        """
        初始化信号存储
        
        Args:
            file_path: CSV 文件路径，默认为 data/signal_history.csv
            
        Requirements: 1.4
        """
        self.file_path = file_path or self.DEFAULT_PATH
        self._ensure_file_exists()
    
    def _ensure_file_exists(self) -> None:
        """
        确保 CSV 文件存在，不存在则创建空文件并写入表头
        
        Requirements: 1.4
        """
        if not self.file_path.exists():
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            pd.DataFrame(columns=self.COLUMNS).to_csv(
                self.file_path, index=False
            )
            logger.info(f"创建信号历史文件: {self.file_path}")
    
    def save_signals(
        self, 
        signals: List['TradingSignal'], 
        generated_date: date,
        market_status: str = "健康"
    ) -> int:
        """
        保存信号（幂等覆盖更新）
        
        逻辑：
        1. 读取现有数据
        2. 删除该日期的旧数据
        3. 追加新数据
        4. 写回文件
        
        Args:
            signals: 交易信号列表
            generated_date: 生成日期
            market_status: 大盘状态
        
        Returns:
            保存的信号数量
            
        Requirements: 1.1, 1.2, 1.3, 1.5
        """
        # 如果没有信号，直接返回
        if not signals:
            logger.info(f"无信号需要保存: {generated_date}")
            return 0
        
        # 1. 读取现有数据
        try:
            # 指定 code 列为字符串类型，保留前导零
            existing_df = pd.read_csv(self.file_path, parse_dates=['generated_date'], dtype={'code': str})
        except (pd.errors.EmptyDataError, FileNotFoundError):
            existing_df = pd.DataFrame(columns=self.COLUMNS)
        
        # 2. 删除该日期的旧数据（幂等覆盖更新）
        date_str = generated_date.isoformat()
        if not existing_df.empty and 'generated_date' in existing_df.columns:
            # 转换为字符串进行比较
            existing_df['generated_date'] = pd.to_datetime(existing_df['generated_date']).dt.date.astype(str)
            existing_df = existing_df[existing_df['generated_date'] != date_str]
        
        # 3. 转换新信号为 DataFrame 记录
        new_records = []
        for signal in signals:
            record = {
                'generated_date': date_str,
                'code': signal.code,
                'name': signal.name,
                'signal_type': signal.signal_type.value,  # SignalType enum -> str
                'price_low': signal.price_range[0],
                'price_high': signal.price_range[1],
                'limit_cap': signal.limit_cap,
                'reason': signal.reason,
                'in_report_window': signal.in_report_window,
                'high_fee_warning': signal.high_fee_warning,
                'market_status': market_status
            }
            new_records.append(record)
        
        new_df = pd.DataFrame(new_records, columns=self.COLUMNS)
        
        # 4. 合并并写回文件
        if existing_df.empty:
            combined_df = new_df
        else:
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        combined_df.to_csv(self.file_path, index=False)
        
        logger.info(f"保存 {len(signals)} 条信号: {generated_date}")
        return len(signals)
    
    def load_signals(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        code: Optional[str] = None,
        signal_type: Optional[str] = None
    ) -> pd.DataFrame:
        """
        加载历史信号
        
        Args:
            start_date: 开始日期（含）
            end_date: 结束日期（含）
            code: 股票代码筛选
            signal_type: 信号类型筛选（买入/卖出）
        
        Returns:
            筛选后的信号 DataFrame
            
        Requirements: 2.1, 2.2, 2.3, 2.4, 2.5
        """
        try:
            # 指定 code 列为字符串类型，保留前导零
            df = pd.read_csv(self.file_path, dtype={'code': str})
        except (pd.errors.EmptyDataError, FileNotFoundError):
            logger.warning(f"信号文件为空或不存在: {self.file_path}")
            return pd.DataFrame(columns=self.COLUMNS)
        
        if df.empty:
            return df
        
        # 转换日期列
        df['generated_date'] = pd.to_datetime(df['generated_date']).dt.date
        
        # 应用日期范围筛选
        if start_date is not None:
            df = df[df['generated_date'] >= start_date]
        
        if end_date is not None:
            df = df[df['generated_date'] <= end_date]
        
        # 应用股票代码筛选
        if code is not None and code.strip():
            df = df[df['code'].astype(str).str.contains(code.strip(), na=False)]
        
        # 应用信号类型筛选
        if signal_type is not None and signal_type.strip():
            df = df[df['signal_type'] == signal_type.strip()]
        
        # 按日期降序排列（最新的在前）
        df = df.sort_values('generated_date', ascending=False)
        
        return df.reset_index(drop=True)
    
    def get_statistics(self, df: pd.DataFrame) -> dict:
        """
        计算统计指标
        
        Args:
            df: 信号 DataFrame
        
        Returns:
            {
                'total_count': int,      # 总信号数
                'buy_count': int,        # 买入信号数
                'sell_count': int,       # 卖出信号数
                'stock_count': int,      # 涉及股票数
            }
            
        Requirements: 4.2, 4.3, 4.4
        """
        if df.empty:
            return {
                'total_count': 0,
                'buy_count': 0,
                'sell_count': 0,
                'stock_count': 0
            }
        
        return {
            'total_count': len(df),
            'buy_count': int((df['signal_type'] == '买入').sum()),
            'sell_count': int((df['signal_type'] == '卖出').sum()),
            'stock_count': df['code'].nunique()
        }
    
    def export_csv(self, df: pd.DataFrame) -> bytes:
        """
        导出 CSV 数据
        
        Args:
            df: 要导出的 DataFrame
        
        Returns:
            CSV 文件的字节内容
            
        Requirements: 5.2
        """
        return df.to_csv(index=False).encode('utf-8-sig')
