"""
Data Fetcher Module

数据获取模块，负责获取股票实时数据、主力资金流向和市场状态检测。
Requirements: 5.1, 5.2, 7.1, 7.2

Performance Optimizations (Task 10.2):
- 数据缓存机制：避免重复获取相同数据
- 批量数据获取：减少API调用次数
- 缓存过期管理：自动清理过期缓存
- 历史数据缓存：减少历史数据重复获取
"""

import logging
from datetime import datetime, time, date, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from threading import Lock
import hashlib

import pandas as pd
import numpy as np

from .config import MONITOR_CONFIG, V114G_STRATEGY_PARAMS
from .models import StockData
from .indicators import TechIndicators

logger = logging.getLogger(__name__)


# ==================== 缓存配置 ====================

@dataclass
class CacheConfig:
    """缓存配置"""
    # 实时数据缓存过期时间（秒）
    realtime_cache_ttl: int = 30
    # 历史数据缓存过期时间（秒）
    historical_cache_ttl: int = 3600  # 1小时
    # 资金流向缓存过期时间（秒）
    fund_flow_cache_ttl: int = 300  # 5分钟
    # 最大缓存条目数
    max_cache_entries: int = 100


CACHE_CONFIG = CacheConfig()


@dataclass
class CacheEntry:
    """缓存条目"""
    data: any
    timestamp: datetime
    ttl: int  # 过期时间（秒）
    
    def is_expired(self) -> bool:
        """检查缓存是否过期"""
        elapsed = (datetime.now() - self.timestamp).total_seconds()
        return elapsed >= self.ttl


class DataCache:
    """
    数据缓存管理器
    
    提供线程安全的缓存操作，支持TTL过期机制。
    """
    
    def __init__(self, config: CacheConfig = None):
        self.config = config or CACHE_CONFIG
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = Lock()
        self._hit_count = 0
        self._miss_count = 0
    
    def get(self, key: str) -> Optional[any]:
        """
        获取缓存数据
        
        Args:
            key: 缓存键
            
        Returns:
            缓存数据，不存在或过期返回None
        """
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._miss_count += 1
                return None
            
            if entry.is_expired():
                del self._cache[key]
                self._miss_count += 1
                return None
            
            self._hit_count += 1
            return entry.data
    
    def set(self, key: str, data: any, ttl: int = None) -> None:
        """
        设置缓存数据
        
        Args:
            key: 缓存键
            data: 缓存数据
            ttl: 过期时间（秒），默认使用实时数据TTL
        """
        with self._lock:
            # 检查缓存大小限制
            if len(self._cache) >= self.config.max_cache_entries:
                self._evict_expired()
            
            self._cache[key] = CacheEntry(
                data=data,
                timestamp=datetime.now(),
                ttl=ttl or self.config.realtime_cache_ttl
            )
    
    def delete(self, key: str) -> bool:
        """
        删除缓存数据
        
        Args:
            key: 缓存键
            
        Returns:
            是否删除成功
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self) -> None:
        """清空所有缓存"""
        with self._lock:
            self._cache.clear()
            self._hit_count = 0
            self._miss_count = 0
    
    def _evict_expired(self) -> None:
        """清理过期缓存"""
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]
        for key in expired_keys:
            del self._cache[key]
        
        # 如果仍然超过限制，删除最旧的条目
        if len(self._cache) >= self.config.max_cache_entries:
            oldest_key = min(
                self._cache.keys(),
                key=lambda k: self._cache[k].timestamp
            )
            del self._cache[oldest_key]
    
    @property
    def stats(self) -> Dict[str, any]:
        """获取缓存统计信息"""
        with self._lock:
            total = self._hit_count + self._miss_count
            hit_rate = self._hit_count / total if total > 0 else 0
            return {
                'size': len(self._cache),
                'hit_count': self._hit_count,
                'miss_count': self._miss_count,
                'hit_rate': hit_rate,
            }


@dataclass
class MarketStatus:
    """
    市场状态
    
    Property 11: Market Status Detection
    For any time T:
    - If T is within trading hours (9:30-11:30 or 13:00-15:00), market status should be "open"
    - Otherwise, market status should be "closed"
    
    Requirements: 5.2
    """
    is_open: bool
    status: str  # "open", "closed", "pre_market", "lunch_break", "after_hours"
    message: str
    checked_at: datetime = field(default_factory=datetime.now)
    
    # 状态常量
    STATUS_OPEN = "open"
    STATUS_CLOSED = "closed"
    STATUS_PRE_MARKET = "pre_market"
    STATUS_LUNCH_BREAK = "lunch_break"
    STATUS_AFTER_HOURS = "after_hours"


@dataclass
class FundFlowData:
    """
    主力资金流向数据
    
    Requirements: 7.1, 7.2
    """
    code: str
    name: str
    main_net_inflow: float      # 今日主力净流入（万元）
    main_net_inflow_5d: float   # 5日累计主力净流入（万元）
    updated_at: datetime = field(default_factory=datetime.now)


class DataFetcher:
    """
    数据获取器
    
    负责获取股票实时数据、主力资金流向和市场状态检测。
    
    Performance Optimizations (Task 10.2):
    - 使用DataCache进行数据缓存
    - 批量获取减少API调用
    - 历史数据缓存避免重复计算
    
    Requirements: 5.1, 5.2, 7.1, 7.2
    """
    
    def __init__(self, config: Optional[MONITOR_CONFIG.__class__] = None):
        """
        初始化数据获取器
        
        Args:
            config: 监控配置，默认使用MONITOR_CONFIG
        """
        self.config = config or MONITOR_CONFIG
        self._last_update: Optional[datetime] = None
        
        # 使用新的缓存系统
        self._realtime_cache = DataCache()
        self._historical_cache = DataCache()
        self._fund_flow_cache_obj = DataCache()
        
        # 保留旧的缓存字典以保持向后兼容
        self._cache: Dict[str, StockData] = {}
        self._fund_flow_cache: Dict[str, FundFlowData] = {}
        
        # 批量数据缓存（用于减少API调用）
        self._batch_quote_cache: Optional[pd.DataFrame] = None
        self._batch_quote_timestamp: Optional[datetime] = None
        self._batch_quote_ttl: int = 10  # 批量行情缓存10秒
    
    @property
    def last_update(self) -> Optional[datetime]:
        """获取最后更新时间"""
        return self._last_update
    
    @property
    def cache_stats(self) -> Dict[str, Dict]:
        """获取缓存统计信息"""
        return {
            'realtime': self._realtime_cache.stats,
            'historical': self._historical_cache.stats,
            'fund_flow': self._fund_flow_cache_obj.stats,
        }
    
    # ==================== 市场状态检测 ====================
    
    def get_market_status(self, check_time: Optional[datetime] = None) -> MarketStatus:
        """
        获取市场状态
        
        Property 11: Market Status Detection
        For any time T:
        - If T is within trading hours (9:30-11:30 or 13:00-15:00), market status should be "open"
        - Otherwise, market status should be "closed"
        
        Requirements: 5.2
        
        Args:
            check_time: 检查时间，默认为当前时间
            
        Returns:
            MarketStatus: 市场状态
        """
        if check_time is None:
            check_time = datetime.now()
        
        current_time = check_time.time()
        weekday = check_time.weekday()
        
        # 周末休市
        if weekday >= 5:  # 5=Saturday, 6=Sunday
            return MarketStatus(
                is_open=False,
                status=MarketStatus.STATUS_CLOSED,
                message="周末休市",
                checked_at=check_time
            )
        
        # 检查交易时段
        trading_hours = self.config.trading_hours
        
        # 上午交易时段 9:30-11:30
        morning_start, morning_end = trading_hours[0]
        # 下午交易时段 13:00-15:00
        afternoon_start, afternoon_end = trading_hours[1]
        
        # 盘前 (9:30之前)
        if current_time < morning_start:
            return MarketStatus(
                is_open=False,
                status=MarketStatus.STATUS_PRE_MARKET,
                message="盘前，等待开盘",
                checked_at=check_time
            )
        
        # 上午交易时段
        if morning_start <= current_time <= morning_end:
            return MarketStatus(
                is_open=True,
                status=MarketStatus.STATUS_OPEN,
                message="上午交易时段",
                checked_at=check_time
            )
        
        # 午休时段 (11:30-13:00)
        if morning_end < current_time < afternoon_start:
            return MarketStatus(
                is_open=False,
                status=MarketStatus.STATUS_LUNCH_BREAK,
                message="午休时段",
                checked_at=check_time
            )
        
        # 下午交易时段
        if afternoon_start <= current_time <= afternoon_end:
            return MarketStatus(
                is_open=True,
                status=MarketStatus.STATUS_OPEN,
                message="下午交易时段",
                checked_at=check_time
            )
        
        # 盘后 (15:00之后)
        return MarketStatus(
            is_open=False,
            status=MarketStatus.STATUS_AFTER_HOURS,
            message="已收盘",
            checked_at=check_time
        )
    
    def is_trading_time(self, check_time: Optional[datetime] = None) -> bool:
        """
        检查是否为交易时间
        
        Args:
            check_time: 检查时间，默认为当前时间
            
        Returns:
            bool: 是否为交易时间
        """
        status = self.get_market_status(check_time)
        return status.is_open
    
    # ==================== 实时数据获取 ====================
    
    def fetch_realtime_quote(self, code: str) -> Optional[Dict]:
        """
        获取单只股票实时行情
        
        Requirements: 5.1
        
        Args:
            code: 股票代码
            
        Returns:
            Dict: 实时行情数据，失败返回None
        """
        try:
            import akshare as ak
            
            # 获取实时行情
            df = ak.stock_zh_a_spot_em()
            
            if df is None or df.empty:
                logger.warning(f"获取实时行情失败: 返回数据为空")
                return None
            
            # 查找目标股票
            stock_row = df[df['代码'] == code]
            
            if stock_row.empty:
                logger.warning(f"未找到股票: {code}")
                return None
            
            row = stock_row.iloc[0]
            
            return {
                'code': code,
                'name': row.get('名称', ''),
                'current_price': float(row.get('最新价', 0)),
                'change_pct': float(row.get('涨跌幅', 0)) / 100,  # 转换为小数
                'volume': int(row.get('成交量', 0)),
                'turnover': float(row.get('成交额', 0)),
                'high': float(row.get('最高', 0)),
                'low': float(row.get('最低', 0)),
                'open': float(row.get('开盘', 0)),
                'prev_close': float(row.get('昨收', 0)),
            }
            
        except ImportError:
            logger.error("AkShare 未安装，无法获取实时数据")
            return None
        except Exception as e:
            logger.error(f"获取实时行情失败: {code}, 错误: {e}")
            return None
    
    def fetch_realtime_quotes_batch(self, codes: List[str]) -> Dict[str, Dict]:
        """
        批量获取股票实时行情
        
        Performance Optimization: 使用批量缓存减少API调用
        
        Requirements: 5.1
        
        Args:
            codes: 股票代码列表
            
        Returns:
            Dict[str, Dict]: 股票代码到行情数据的映射
        """
        results = {}
        
        try:
            import akshare as ak
            
            # 检查批量缓存是否有效
            if self._is_batch_cache_valid():
                df = self._batch_quote_cache
                logger.debug("使用批量行情缓存")
            else:
                # 一次性获取全市场行情
                df = ak.stock_zh_a_spot_em()
                
                if df is None or df.empty:
                    logger.warning("获取实时行情失败: 返回数据为空")
                    return results
                
                # 更新批量缓存
                self._batch_quote_cache = df
                self._batch_quote_timestamp = datetime.now()
                logger.debug("更新批量行情缓存")
            
            # 筛选目标股票
            for code in codes:
                # 先检查单个缓存
                cache_key = f"quote_{code}"
                cached = self._realtime_cache.get(cache_key)
                if cached:
                    results[code] = cached
                    continue
                
                stock_row = df[df['代码'] == code]
                
                if stock_row.empty:
                    logger.warning(f"未找到股票: {code}")
                    continue
                
                row = stock_row.iloc[0]
                
                quote_data = {
                    'code': code,
                    'name': row.get('名称', ''),
                    'current_price': float(row.get('最新价', 0)),
                    'change_pct': float(row.get('涨跌幅', 0)) / 100,
                    'volume': int(row.get('成交量', 0)),
                    'turnover': float(row.get('成交额', 0)),
                    'high': float(row.get('最高', 0)),
                    'low': float(row.get('最低', 0)),
                    'open': float(row.get('开盘', 0)),
                    'prev_close': float(row.get('昨收', 0)),
                }
                
                results[code] = quote_data
                
                # 缓存单个结果
                self._realtime_cache.set(cache_key, quote_data, CACHE_CONFIG.realtime_cache_ttl)
            
            self._last_update = datetime.now()
            logger.info(f"批量获取实时行情成功: {len(results)}/{len(codes)} 只股票")
            
        except ImportError:
            logger.error("AkShare 未安装，无法获取实时数据")
        except Exception as e:
            logger.error(f"批量获取实时行情失败: {e}")
        
        return results
    
    def _is_batch_cache_valid(self) -> bool:
        """检查批量缓存是否有效"""
        if self._batch_quote_cache is None or self._batch_quote_timestamp is None:
            return False
        
        elapsed = (datetime.now() - self._batch_quote_timestamp).total_seconds()
        return elapsed < self._batch_quote_ttl
    
    def fetch_historical_data(self, code: str, days: int = 100) -> Optional[pd.DataFrame]:
        """
        获取历史数据（用于计算技术指标）
        
        Performance Optimization: 使用缓存避免重复获取历史数据
        
        Args:
            code: 股票代码
            days: 获取天数
            
        Returns:
            DataFrame: 历史数据，失败返回None
        """
        # 检查缓存
        cache_key = f"hist_{code}_{days}"
        cached = self._historical_cache.get(cache_key)
        if cached is not None:
            logger.debug(f"使用历史数据缓存: {code}")
            return cached
        
        try:
            import akshare as ak
            
            end_date = date.today()
            start_date = end_date - timedelta(days=days + 30)  # 多获取一些数据
            
            df = ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date=start_date.strftime('%Y%m%d'),
                end_date=end_date.strftime('%Y%m%d'),
                adjust="qfq"
            )
            
            if df is None or df.empty:
                logger.warning(f"获取历史数据失败: {code}")
                return None
            
            # 标准化列名
            df = df.rename(columns={
                '日期': 'date',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume',
            })
            
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').reset_index(drop=True)
            
            # 缓存历史数据（1小时过期）
            self._historical_cache.set(cache_key, df, CACHE_CONFIG.historical_cache_ttl)
            logger.debug(f"缓存历史数据: {code}")
            
            return df
            
        except ImportError:
            logger.error("AkShare 未安装，无法获取历史数据")
            return None
        except Exception as e:
            logger.error(f"获取历史数据失败: {code}, 错误: {e}")
            return None
    
    def fetch_stock_data(self, code: str) -> Optional[StockData]:
        """
        获取完整的股票数据（包含技术指标）
        
        Requirements: 5.1, 8.1
        
        Args:
            code: 股票代码
            
        Returns:
            StockData: 股票数据，失败返回None
        """
        # 获取实时行情
        quote = self.fetch_realtime_quote(code)
        if quote is None:
            return None
        
        # 获取历史数据
        hist_df = self.fetch_historical_data(code)
        if hist_df is None or len(hist_df) < 60:
            logger.warning(f"历史数据不足: {code}")
            return None
        
        # 计算技术指标
        prices = hist_df['close']
        volumes = hist_df['volume']
        
        indicators = TechIndicators.calculate_all_indicators(prices, volumes)
        
        # 获取资金流向
        fund_flow = self.fetch_fund_flow(code)
        main_fund_flow = fund_flow.main_net_inflow if fund_flow else 0.0
        fund_flow_5d = fund_flow.main_net_inflow_5d if fund_flow else 0.0
        
        return StockData(
            code=code,
            name=quote['name'],
            current_price=quote['current_price'],
            change_pct=quote['change_pct'],
            volume=quote['volume'],
            turnover=quote['turnover'],
            ma5=indicators['ma5'],
            ma10=indicators['ma10'],
            ma20=indicators['ma20'],
            ma60=indicators['ma60'],
            rsi=indicators['rsi'],
            volume_ratio=indicators['volume_ratio'],
            ma20_slope=indicators['ma20_slope'],
            main_fund_flow=main_fund_flow,
            fund_flow_5d=fund_flow_5d,
            updated_at=datetime.now()
        )
    
    def fetch_stock_data_batch(self, codes: List[str]) -> Dict[str, StockData]:
        """
        批量获取股票数据
        
        Args:
            codes: 股票代码列表
            
        Returns:
            Dict[str, StockData]: 股票代码到数据的映射
        """
        results = {}
        
        for code in codes:
            stock_data = self.fetch_stock_data(code)
            if stock_data:
                results[code] = stock_data
                self._cache[code] = stock_data
        
        self._last_update = datetime.now()
        logger.info(f"批量获取股票数据成功: {len(results)}/{len(codes)} 只股票")
        
        return results
    
    # ==================== 主力资金流向 ====================
    
    def fetch_fund_flow(self, code: str) -> Optional[FundFlowData]:
        """
        获取主力资金流向
        
        Requirements: 7.1, 7.2
        
        Args:
            code: 股票代码
            
        Returns:
            FundFlowData: 资金流向数据，失败返回None
        """
        try:
            import akshare as ak
            
            # 获取个股资金流向
            df = ak.stock_individual_fund_flow(stock=code, market="sh" if code.startswith('6') else "sz")
            
            if df is None or df.empty:
                logger.warning(f"获取资金流向失败: {code}")
                return None
            
            # 获取最新一天的数据
            latest = df.iloc[-1] if len(df) > 0 else None
            
            if latest is None:
                return None
            
            # 计算5日累计
            recent_5d = df.tail(5)
            main_net_5d = recent_5d['主力净流入-净额'].sum() if '主力净流入-净额' in df.columns else 0.0
            
            return FundFlowData(
                code=code,
                name='',  # 名称从其他接口获取
                main_net_inflow=float(latest.get('主力净流入-净额', 0)) / 10000,  # 转换为万元
                main_net_inflow_5d=float(main_net_5d) / 10000,
                updated_at=datetime.now()
            )
            
        except ImportError:
            logger.error("AkShare 未安装，无法获取资金流向")
            return None
        except Exception as e:
            logger.debug(f"获取资金流向失败: {code}, 错误: {e}")
            return None
    
    def fetch_fund_flow_batch(self, codes: List[str]) -> Dict[str, FundFlowData]:
        """
        批量获取主力资金流向
        
        Requirements: 7.1, 7.2
        
        Args:
            codes: 股票代码列表
            
        Returns:
            Dict[str, FundFlowData]: 股票代码到资金流向的映射
        """
        results = {}
        
        for code in codes:
            fund_flow = self.fetch_fund_flow(code)
            if fund_flow:
                results[code] = fund_flow
                self._fund_flow_cache[code] = fund_flow
        
        logger.info(f"批量获取资金流向成功: {len(results)}/{len(codes)} 只股票")
        
        return results
    
    # ==================== 缓存管理 ====================
    
    def get_cached_data(self, code: str) -> Optional[StockData]:
        """
        获取缓存的股票数据
        
        Args:
            code: 股票代码
            
        Returns:
            StockData: 缓存的数据，不存在返回None
        """
        return self._cache.get(code)
    
    def get_cached_fund_flow(self, code: str) -> Optional[FundFlowData]:
        """
        获取缓存的资金流向数据
        
        Args:
            code: 股票代码
            
        Returns:
            FundFlowData: 缓存的数据，不存在返回None
        """
        return self._fund_flow_cache.get(code)
    
    def clear_cache(self) -> None:
        """清空所有缓存"""
        self._cache.clear()
        self._fund_flow_cache.clear()
        self._realtime_cache.clear()
        self._historical_cache.clear()
        self._fund_flow_cache_obj.clear()
        self._batch_quote_cache = None
        self._batch_quote_timestamp = None
        self._last_update = None
        logger.info("数据缓存已清空")
    
    def should_refresh(self) -> bool:
        """
        检查是否需要刷新数据
        
        Requirements: 5.1
        
        Returns:
            bool: 是否需要刷新
        """
        if self._last_update is None:
            return True
        
        elapsed = (datetime.now() - self._last_update).total_seconds()
        return elapsed >= self.config.refresh_interval


# 便捷函数
def get_market_status(check_time: Optional[datetime] = None) -> MarketStatus:
    """
    获取市场状态（便捷函数）
    
    Args:
        check_time: 检查时间，默认为当前时间
        
    Returns:
        MarketStatus: 市场状态
    """
    fetcher = DataFetcher()
    return fetcher.get_market_status(check_time)


def is_trading_time(check_time: Optional[datetime] = None) -> bool:
    """
    检查是否为交易时间（便捷函数）
    
    Args:
        check_time: 检查时间，默认为当前时间
        
    Returns:
        bool: 是否为交易时间
    """
    fetcher = DataFetcher()
    return fetcher.is_trading_time(check_time)
