"""
行业强弱排位器模块

计算各科技行业的相对强度，按20日涨幅排名。
只在排名第1和第2的行业中选股。

支持两种数据源：
1. 行业指数（优先）：使用深证/中证行业指数
2. 龙头股平均涨幅（备选）：当指数数据不可用时使用

Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6
"""

from dataclasses import dataclass
from typing import List, Optional, Dict
import pandas as pd
import logging

from config.tech_stock_config import (
    SECTOR_INDEX_MAPPING,
    SECTOR_PROXY_STOCKS,
)

logger = logging.getLogger(__name__)


@dataclass
class SectorRank:
    """
    行业排名数据类
    
    Attributes:
        sector_name: 行业名称
        index_code: 行业指数代码
        return_20d: 20日涨幅（百分比，如 5.23 表示 5.23%）
        rank: 排名 (1-4)
        is_tradable: 是否可交易（排名1-2为可交易）
        data_source: 数据来源 ("index" / "proxy_stocks")
    """
    sector_name: str
    index_code: str
    return_20d: float
    rank: int
    is_tradable: bool
    data_source: str


class SectorRanker:
    """
    行业强弱排位器
    
    跟踪四个科技行业指数：半导体、AI应用、算力、消费电子
    计算各行业20日涨幅并排名，只在排名1-2的行业中选股。
    
    设计原则：
    - 优先使用行业指数数据
    - 指数数据不可用时，使用龙头股平均涨幅作为备选
    - 排名1-2的行业可交易，排名3-4的行业不可交易
    
    Requirements: 2.1, 2.2, 2.3, 2.4
    """
    
    # 科技行业指数映射
    SECTOR_INDICES: Dict[str, str] = {
        sector: info["code"] 
        for sector, info in SECTOR_INDEX_MAPPING.items()
    }
    
    # 备选方案：行业龙头股
    SECTOR_PROXY_STOCKS: Dict[str, List[str]] = SECTOR_PROXY_STOCKS
    
    # 可交易行业排名阈值
    TRADABLE_RANK_THRESHOLD = 2
    
    # 计算涨幅的周期
    RETURN_PERIOD = 20
    
    def __init__(self, data_feed=None):
        """
        初始化行业排位器
        
        Args:
            data_feed: 数据获取模块实例，如果为 None 则使用 AkShare 直接获取
        """
        self._data_feed = data_feed
        self._cached_rankings: Optional[List[SectorRank]] = None
    
    def get_sector_rankings(self, use_proxy_stocks: bool = False) -> List[SectorRank]:
        """
        获取行业排名
        
        计算各行业指数的20日涨幅，按涨幅降序排序。
        
        Args:
            use_proxy_stocks: 是否强制使用龙头股替代指数
                             False: 优先使用指数，失败时自动切换到龙头股
                             True: 强制使用龙头股
        
        Returns:
            排序后的行业排名列表（按涨幅降序）
            
        Requirements: 2.1, 2.2, 2.3
        """
        sector_returns = []
        
        for sector_name, index_code in self.SECTOR_INDICES.items():
            return_20d = None
            data_source = "index"
            
            # 尝试获取指数涨幅
            if not use_proxy_stocks:
                return_20d = self._get_index_return(index_code)
            
            # 如果指数数据不可用，使用龙头股备选方案
            if return_20d is None:
                return_20d = self._get_proxy_return(sector_name)
                data_source = "proxy_stocks"
                if return_20d is not None:
                    logger.info(f"行业 {sector_name} 使用龙头股平均涨幅作为替代")
            
            # 如果仍然无法获取，使用 0
            if return_20d is None:
                logger.warning(f"无法获取行业 {sector_name} 的涨幅数据，使用 0")
                return_20d = 0.0
            
            sector_returns.append({
                "sector_name": sector_name,
                "index_code": index_code,
                "return_20d": return_20d,
                "data_source": data_source
            })
        
        # 按涨幅降序排序
        sector_returns.sort(key=lambda x: x["return_20d"], reverse=True)
        
        # 生成排名结果
        rankings = []
        for i, sector in enumerate(sector_returns):
            rank = i + 1
            is_tradable = rank <= self.TRADABLE_RANK_THRESHOLD
            
            rankings.append(SectorRank(
                sector_name=sector["sector_name"],
                index_code=sector["index_code"],
                return_20d=sector["return_20d"],
                rank=rank,
                is_tradable=is_tradable,
                data_source=sector["data_source"]
            ))
        
        # 缓存结果
        self._cached_rankings = rankings
        
        # 日志输出
        logger.info("行业强弱排名:")
        for r in rankings:
            status = "✓ 可交易" if r.is_tradable else "✗ 不可交易"
            logger.info(f"  {r.rank}. {r.sector_name}: {r.return_20d:.2f}% ({r.data_source}) {status}")
        
        return rankings
    
    def _get_index_return(self, index_code: str) -> Optional[float]:
        """
        获取指数20日涨幅
        
        Args:
            index_code: 指数代码
        
        Returns:
            涨幅百分比（如 5.23 表示 5.23%），获取失败返回 None
        """
        try:
            import akshare as ak
            from datetime import datetime, timedelta
            
            # 获取最近 60 天的数据（确保有足够数据计算 20 日涨幅）
            end_date = datetime.now()
            start_date = end_date - timedelta(days=90)
            
            logger.debug(f"获取指数数据: {index_code}")
            
            # 根据指数代码前缀判断交易所
            # 399xxx: 深交所指数
            # 930xxx, 931xxx: 中证指数
            if index_code.startswith("399"):
                # 深交所指数
                df = ak.stock_zh_index_daily(symbol=f"sz{index_code}")
            elif index_code.startswith("93"):
                # 中证指数 - 使用 index_zh_a_hist 接口
                df = ak.index_zh_a_hist(
                    symbol=index_code,
                    period="daily",
                    start_date=start_date.strftime('%Y%m%d'),
                    end_date=end_date.strftime('%Y%m%d')
                )
            else:
                logger.warning(f"未知指数代码格式: {index_code}")
                return None
            
            if df is None or df.empty:
                logger.warning(f"指数 {index_code} 无数据返回")
                return None
            
            # 标准化列名
            if '日期' in df.columns:
                df = df.rename(columns={'日期': 'date', '收盘': 'close'})
            elif 'date' not in df.columns:
                # 尝试其他可能的列名
                for col in df.columns:
                    if 'date' in col.lower() or '日期' in col:
                        df = df.rename(columns={col: 'date'})
                        break
            
            if 'close' not in df.columns:
                for col in df.columns:
                    if 'close' in col.lower() or '收盘' in col:
                        df = df.rename(columns={col: 'close'})
                        break
            
            if 'close' not in df.columns:
                logger.warning(f"指数 {index_code} 数据缺少收盘价列")
                return None
            
            # 确保按日期排序
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').reset_index(drop=True)
            
            # 计算 20 日涨幅
            if len(df) < self.RETURN_PERIOD + 1:
                logger.warning(f"指数 {index_code} 数据不足 {self.RETURN_PERIOD + 1} 天")
                return None
            
            current_close = float(df.iloc[-1]['close'])
            past_close = float(df.iloc[-self.RETURN_PERIOD - 1]['close'])
            
            if past_close <= 0:
                logger.warning(f"指数 {index_code} 历史收盘价异常: {past_close}")
                return None
            
            return_20d = (current_close - past_close) / past_close * 100
            
            logger.debug(f"指数 {index_code} 20日涨幅: {return_20d:.2f}%")
            return return_20d
            
        except Exception as e:
            logger.warning(f"获取指数 {index_code} 数据失败: {e}")
            return None
    
    def _get_proxy_return(self, sector_name: str) -> Optional[float]:
        """
        使用龙头股平均涨幅替代行业涨幅（备选方案）
        
        计算该行业前3大权重股的20日平均涨幅。
        
        Args:
            sector_name: 行业名称
        
        Returns:
            龙头股平均涨幅（百分比），获取失败返回 None
        """
        stocks = self.SECTOR_PROXY_STOCKS.get(sector_name, [])
        
        if not stocks:
            logger.warning(f"行业 {sector_name} 无龙头股配置")
            return None
        
        returns = []
        for code in stocks:
            ret = self._get_stock_return(code)
            if ret is not None:
                returns.append(ret)
        
        if not returns:
            logger.warning(f"行业 {sector_name} 所有龙头股数据获取失败")
            return None
        
        avg_return = sum(returns) / len(returns)
        logger.debug(f"行业 {sector_name} 龙头股平均涨幅: {avg_return:.2f}% (基于 {len(returns)} 只股票)")
        
        return avg_return
    
    def _get_stock_return(self, code: str) -> Optional[float]:
        """
        获取单只股票的20日涨幅
        
        Args:
            code: 股票代码
        
        Returns:
            涨幅百分比，获取失败返回 None
        """
        # 优先从 data_feed 获取
        if self._data_feed is not None:
            try:
                df = self._data_feed.load_processed_data(code)
                if df is not None and not df.empty and len(df) >= self.RETURN_PERIOD + 1:
                    df = df.sort_values('date').reset_index(drop=True)
                    current_close = float(df.iloc[-1]['close'])
                    past_close = float(df.iloc[-self.RETURN_PERIOD - 1]['close'])
                    
                    if past_close > 0:
                        return (current_close - past_close) / past_close * 100
            except Exception as e:
                logger.debug(f"从 data_feed 获取 {code} 数据失败: {e}")
        
        # 从 AkShare 获取
        try:
            import akshare as ak
            from datetime import datetime, timedelta
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=60)
            
            df = ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date=start_date.strftime('%Y%m%d'),
                end_date=end_date.strftime('%Y%m%d'),
                adjust="qfq"
            )
            
            if df is None or df.empty:
                logger.debug(f"股票 {code} 无数据返回")
                return None
            
            # 标准化列名
            if '日期' in df.columns:
                df = df.rename(columns={'日期': 'date', '收盘': 'close'})
            
            if 'close' not in df.columns:
                logger.debug(f"股票 {code} 数据缺少收盘价列")
                return None
            
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').reset_index(drop=True)
            
            if len(df) < self.RETURN_PERIOD + 1:
                logger.debug(f"股票 {code} 数据不足")
                return None
            
            current_close = float(df.iloc[-1]['close'])
            past_close = float(df.iloc[-self.RETURN_PERIOD - 1]['close'])
            
            if past_close <= 0:
                return None
            
            return (current_close - past_close) / past_close * 100
            
        except Exception as e:
            logger.debug(f"获取股票 {code} 数据失败: {e}")
            return None
    
    def is_sector_tradable(self, sector_name: str) -> bool:
        """
        判断行业是否可交易（排名1-2）
        
        Args:
            sector_name: 行业名称
        
        Returns:
            True 表示可交易（排名1-2），False 表示不可交易（排名3-4）
            
        Requirements: 2.4
        """
        # 如果没有缓存的排名，先获取排名
        if self._cached_rankings is None:
            self.get_sector_rankings()
        
        # 查找行业排名
        for ranking in self._cached_rankings:
            if ranking.sector_name == sector_name:
                return ranking.is_tradable
        
        # 未找到行业，默认不可交易
        logger.warning(f"未找到行业 {sector_name} 的排名信息，默认不可交易")
        return False
    
    def get_tradable_sectors(self) -> List[str]:
        """
        获取可交易的行业列表
        
        Returns:
            可交易行业名称列表（排名1-2的行业）
        """
        if self._cached_rankings is None:
            self.get_sector_rankings()
        
        return [r.sector_name for r in self._cached_rankings if r.is_tradable]
    
    def get_sector_rank(self, sector_name: str) -> Optional[SectorRank]:
        """
        获取指定行业的排名信息
        
        Args:
            sector_name: 行业名称
        
        Returns:
            SectorRank 对象，未找到返回 None
        """
        if self._cached_rankings is None:
            self.get_sector_rankings()
        
        for ranking in self._cached_rankings:
            if ranking.sector_name == sector_name:
                return ranking
        
        return None
    
    def clear_cache(self) -> None:
        """清除缓存的排名数据"""
        self._cached_rankings = None
        logger.debug("行业排名缓存已清除")
