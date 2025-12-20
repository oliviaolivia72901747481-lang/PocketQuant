"""
MiniQuant-Lite 股票池配置模块

提供股票池管理功能：
- 自选股列表配置
- 沪深300成分股获取
- 股票池验证

Requirements: 8.3
"""

from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


# 默认自选股列表（示例）
# 用户可根据自己的偏好修改此列表
DEFAULT_WATCHLIST: List[str] = [
    '000001',  # 平安银行
    '000002',  # 万科A
    '000063',  # 中兴通讯
    '000333',  # 美的集团
    '000651',  # 格力电器
    '000858',  # 五粮液
    '002415',  # 海康威视
    '002594',  # 比亚迪
    '300750',  # 宁德时代
    '600036',  # 招商银行
    '600519',  # 贵州茅台
    '600900',  # 长江电力
]


def get_watchlist() -> List[str]:
    """
    获取自选股列表
    
    Returns:
        自选股代码列表
    """
    return DEFAULT_WATCHLIST.copy()


def set_watchlist(codes: List[str]) -> None:
    """
    设置自选股列表
    
    Args:
        codes: 股票代码列表
    """
    global DEFAULT_WATCHLIST
    DEFAULT_WATCHLIST = codes.copy()
    logger.info(f"自选股列表已更新，共 {len(codes)} 只股票")


def get_hs300_constituents() -> List[str]:
    """
    获取沪深300成分股列表
    
    通过 AkShare 接口获取最新的沪深300成分股
    
    Returns:
        沪深300成分股代码列表
    
    Raises:
        RuntimeError: 当获取数据失败时
    """
    try:
        import akshare as ak
        
        # 获取沪深300成分股
        df = ak.index_stock_cons(symbol='000300')
        
        if df is None or df.empty:
            logger.warning("获取沪深300成分股返回空数据")
            return []
        
        # 提取股票代码列
        # AkShare 返回的列名可能是 '品种代码' 或 'code'
        code_column = None
        for col in ['品种代码', 'code', '股票代码', 'symbol']:
            if col in df.columns:
                code_column = col
                break
        
        if code_column is None:
            logger.error(f"无法识别股票代码列，可用列: {df.columns.tolist()}")
            return []
        
        codes = df[code_column].tolist()
        logger.info(f"获取沪深300成分股成功，共 {len(codes)} 只")
        return codes
        
    except ImportError:
        logger.error("AkShare 未安装，请运行: pip install akshare==1.12.0")
        raise RuntimeError("AkShare 未安装")
    except Exception as e:
        logger.error(f"获取沪深300成分股失败: {e}")
        raise RuntimeError(f"获取沪深300成分股失败: {e}")


def validate_stock_codes(codes: List[str]) -> List[str]:
    """
    验证股票代码格式
    
    A股股票代码规则：
    - 上海主板: 60xxxx
    - 上海科创板: 688xxx
    - 深圳主板: 00xxxx
    - 深圳中小板: 002xxx
    - 深圳创业板: 30xxxx
    
    Args:
        codes: 待验证的股票代码列表
    
    Returns:
        有效的股票代码列表
    """
    valid_codes = []
    invalid_codes = []
    
    for code in codes:
        # 去除空格
        code = str(code).strip()
        
        # 检查长度
        if len(code) != 6:
            invalid_codes.append(code)
            continue
        
        # 检查是否全为数字
        if not code.isdigit():
            invalid_codes.append(code)
            continue
        
        # 检查前缀
        valid_prefixes = ('00', '30', '60', '68')
        if not code.startswith(valid_prefixes):
            invalid_codes.append(code)
            continue
        
        valid_codes.append(code)
    
    if invalid_codes:
        logger.warning(f"以下股票代码格式无效: {invalid_codes}")
    
    return valid_codes


def get_stock_pool(pool_type: str = 'watchlist') -> List[str]:
    """
    获取股票池
    
    Args:
        pool_type: 股票池类型
            - 'watchlist': 自选股列表
            - 'hs300': 沪深300成分股
    
    Returns:
        股票代码列表
    
    Raises:
        ValueError: 当 pool_type 无效时
    """
    if pool_type == 'watchlist':
        return get_watchlist()
    elif pool_type == 'hs300':
        return get_hs300_constituents()
    else:
        raise ValueError(f"无效的股票池类型: {pool_type}，支持 'watchlist' 或 'hs300'")


class StockPool:
    """
    股票池管理类
    
    提供股票池的增删改查功能
    """
    
    def __init__(self, codes: Optional[List[str]] = None):
        """
        初始化股票池
        
        Args:
            codes: 初始股票代码列表，None 时使用默认自选股
        """
        if codes is None:
            self._codes = get_watchlist()
        else:
            self._codes = validate_stock_codes(codes)
    
    @property
    def codes(self) -> List[str]:
        """获取股票代码列表"""
        return self._codes.copy()
    
    @property
    def size(self) -> int:
        """获取股票池大小"""
        return len(self._codes)
    
    def add(self, code: str) -> bool:
        """
        添加股票到股票池
        
        Args:
            code: 股票代码
        
        Returns:
            是否添加成功
        """
        validated = validate_stock_codes([code])
        if not validated:
            return False
        
        code = validated[0]
        if code in self._codes:
            logger.info(f"股票 {code} 已在股票池中")
            return False
        
        self._codes.append(code)
        logger.info(f"股票 {code} 已添加到股票池")
        return True
    
    def remove(self, code: str) -> bool:
        """
        从股票池移除股票
        
        Args:
            code: 股票代码
        
        Returns:
            是否移除成功
        """
        code = str(code).strip()
        if code not in self._codes:
            logger.info(f"股票 {code} 不在股票池中")
            return False
        
        self._codes.remove(code)
        logger.info(f"股票 {code} 已从股票池移除")
        return True
    
    def contains(self, code: str) -> bool:
        """
        检查股票是否在股票池中
        
        Args:
            code: 股票代码
        
        Returns:
            是否在股票池中
        """
        return str(code).strip() in self._codes
    
    def clear(self) -> None:
        """清空股票池"""
        self._codes.clear()
        logger.info("股票池已清空")
    
    def load_hs300(self) -> int:
        """
        加载沪深300成分股到股票池
        
        Returns:
            加载的股票数量
        """
        codes = get_hs300_constituents()
        self._codes = codes
        logger.info(f"已加载沪深300成分股，共 {len(codes)} 只")
        return len(codes)
    
    def __len__(self) -> int:
        return self.size
    
    def __iter__(self):
        return iter(self._codes)
    
    def __contains__(self, code: str) -> bool:
        return self.contains(code)
