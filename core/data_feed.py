"""
MiniQuant-Lite 数据获取与清洗模块

负责从 AkShare 获取 A 股历史行情数据并进行清洗转换。

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.8
"""

from dataclasses import dataclass
from typing import Optional, List, Dict
from datetime import date, datetime, timedelta
import pandas as pd
import os
import logging

logger = logging.getLogger(__name__)


@dataclass
class StockData:
    """股票数据结构"""
    code: str                    # 股票代码
    name: str                    # 股票名称
    data: pd.DataFrame           # OHLCV 数据
    last_update: date            # 最后更新日期


@dataclass
class LiquidityFilter:
    """流动性过滤配置"""
    min_market_cap: float = 5e9       # 最小流通市值（50亿）
    max_market_cap: float = 5e10      # 最大流通市值（500亿）
    min_turnover_rate: float = 0.02   # 最小换手率（2%）
    max_turnover_rate: float = 0.15   # 最大换手率（15%）
    exclude_st: bool = True           # 剔除 ST 股
    min_listing_days: int = 60        # 最小上市天数


class DataFeed:
    """
    数据获取与清洗模块
    
    负责从 AkShare 获取数据并进行清洗转换为 Backtrader 兼容格式。
    
    设计原则：
    - 强制使用前复权数据，消除分红送转对技术指标的干扰
    - 采用覆盖更新策略，确保复权数据准确性
    - 提供详细的错误诊断，区分网络问题和接口变更
    """
    
    # 推荐的 AkShare 版本（经过测试验证）
    RECOMMENDED_AKSHARE_VERSION = "1.12.0"
    
    def __init__(self, raw_path: str, processed_path: str):
        """
        初始化数据路径
        
        Args:
            raw_path: 原始数据存储路径
            processed_path: 处理后数据存储路径
        
        启动时检查 AkShare 版本，如果版本不匹配则发出警告
        """
        self.raw_path = raw_path
        self.processed_path = processed_path
        
        # 确保目录存在
        os.makedirs(raw_path, exist_ok=True)
        os.makedirs(processed_path, exist_ok=True)
        
        # 检查 AkShare 版本
        self._check_akshare_version()
    
    def _check_akshare_version(self) -> None:
        """
        检查 AkShare 版本
        
        AkShare 依赖爬虫技术，网页源改版可能导致接口失效
        建议锁定版本，除非万不得已不要随意升级
        """
        try:
            import akshare as ak
            current_version = ak.__version__
            
            if current_version != self.RECOMMENDED_AKSHARE_VERSION:
                logger.warning(
                    f"AkShare 版本不匹配！当前: {current_version}, 推荐: {self.RECOMMENDED_AKSHARE_VERSION}。"
                    f"如遇数据获取问题，请尝试: pip install akshare=={self.RECOMMENDED_AKSHARE_VERSION}"
                )
            else:
                logger.info(f"AkShare 版本检查通过: {current_version}")
        except ImportError:
            logger.error(
                "AkShare 未安装！请运行: pip install akshare=={self.RECOMMENDED_AKSHARE_VERSION}"
            )
            raise
    
    def download_stock_data(
        self, 
        code: str, 
        start_date: str, 
        end_date: str,
        adjust: str = 'qfq'
    ) -> Optional[pd.DataFrame]:
        """
        下载单只股票历史数据（前复权）
        
        Args:
            code: 股票代码（如 '000001'）
            start_date: 开始日期 'YYYY-MM-DD'
            end_date: 结束日期 'YYYY-MM-DD'
            adjust: 复权类型，默认 'qfq'（前复权），消除分红送转影响
        
        Returns:
            DataFrame 或 None（失败时）
            
        Requirements: 1.1, 1.3, 1.4
        """
        import akshare as ak
        
        try:
            # 转换日期格式（AkShare 需要 YYYYMMDD 格式）
            start_fmt = start_date.replace('-', '')
            end_fmt = end_date.replace('-', '')
            
            logger.debug(f"开始下载: {code}, 日期范围: {start_date} ~ {end_date}, 复权: {adjust}")
            
            df = ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date=start_fmt,
                end_date=end_fmt,
                adjust=adjust
            )
            
            if df is None or df.empty:
                logger.warning(f"股票 {code} 无数据返回")
                return None
            
            logger.debug(f"下载成功: {code}, 共 {len(df)} 条记录")
            return df
            
        except Exception as e:
            self._handle_download_error(code, e)
            return None
    
    def _handle_download_error(self, code: str, error: Exception) -> None:
        """
        处理下载错误，提供详细的错误诊断
        
        区分网络问题和接口变更问题，帮助用户快速定位问题
        
        Args:
            code: 股票代码
            error: 异常对象
            
        Requirements: 1.4
        """
        error_msg = str(error)
        error_type = type(error).__name__
        
        # 网络连接问题
        if any(keyword in error_msg.lower() for keyword in 
               ['connection', 'timeout', 'refused', 'reset', 'network']):
            logger.error(
                f"网络连接失败: {code}。\n"
                f"  错误类型: {error_type}\n"
                f"  错误信息: {error_msg}\n"
                f"  建议: 请检查网络连接，或稍后重试。"
            )
        
        # 数据解析问题（可能是 AkShare 接口变更）
        elif any(keyword in error_msg for keyword in 
                 ['KeyError', 'AttributeError', 'IndexError', 'ValueError']):
            logger.error(
                f"数据解析失败: {code}。\n"
                f"  错误类型: {error_type}\n"
                f"  错误信息: {error_msg}\n"
                f"  可能原因: AkShare 接口已更新，数据格式发生变化。\n"
                f"  建议: pip install akshare=={self.RECOMMENDED_AKSHARE_VERSION}"
            )
        
        # HTTP 错误
        elif 'HTTPError' in error_type or '40' in error_msg or '50' in error_msg:
            logger.error(
                f"HTTP 请求失败: {code}。\n"
                f"  错误类型: {error_type}\n"
                f"  错误信息: {error_msg}\n"
                f"  建议: 可能是请求频率过高被限制，请稍后重试。"
            )
        
        # 其他未知错误
        else:
            logger.error(
                f"数据下载失败: {code}。\n"
                f"  错误类型: {error_type}\n"
                f"  错误信息: {error_msg}\n"
                f"  推荐 AkShare 版本: {self.RECOMMENDED_AKSHARE_VERSION}"
            )


    def download_batch(
        self, 
        codes: List[str], 
        start_date: str, 
        end_date: str,
        adjust: str = 'qfq'
    ) -> Dict[str, pd.DataFrame]:
        """
        批量下载股票数据（串行，简单稳定）
        
        设计原则：稳定压倒一切
        - 串行下载几十只股票只需几秒
        - 避免多线程带来的复杂性（死锁、线程安全、IP 封禁）
        - 每次请求间隔 0.5 秒，避免被封 IP
        
        Args:
            codes: 股票代码列表
            start_date: 开始日期 'YYYY-MM-DD'
            end_date: 结束日期 'YYYY-MM-DD'
            adjust: 复权类型，默认 'qfq'（前复权）
        
        Returns:
            {股票代码: DataFrame} 字典
            
        Requirements: 1.2, 1.5
        """
        import time
        
        results = {}
        total = len(codes)
        success_count = 0
        fail_count = 0
        
        logger.info(f"开始批量下载: 共 {total} 只股票")
        
        for i, code in enumerate(codes):
            df = self.download_stock_data(code, start_date, end_date, adjust)
            
            if df is not None and not df.empty:
                results[code] = df
                success_count += 1
                logger.info(f"下载完成: {code} ({i+1}/{total})")
            else:
                fail_count += 1
                logger.warning(f"下载失败: {code} ({i+1}/{total})")
            
            # 简单的请求间隔，避免被封 IP
            if i < total - 1:  # 最后一个不需要等待
                time.sleep(0.5)
        
        logger.info(f"批量下载完成: 成功 {success_count}, 失败 {fail_count}")
        return results
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        清洗数据，转换为 Backtrader 格式
        
        输入: AkShare 返回的原始 DataFrame
        输出: Backtrader 兼容格式，包含列: date, open, high, low, close, volume
        
        注意: 输入数据应为前复权数据
        
        Args:
            df: AkShare 返回的原始数据
        
        Returns:
            清洗后的 DataFrame，Backtrader 兼容格式
            
        Requirements: 1.2
        """
        if df is None or df.empty:
            return pd.DataFrame()
        
        # AkShare 返回的列名（中文）
        # 日期, 开盘, 收盘, 最高, 最低, 成交量, 成交额, 振幅, 涨跌幅, 涨跌额, 换手率
        
        # 创建副本避免修改原数据
        cleaned = df.copy()
        
        # 列名映射（AkShare 中文列名 -> Backtrader 英文列名）
        column_mapping = {
            '日期': 'date',
            '开盘': 'open',
            '最高': 'high',
            '最低': 'low',
            '收盘': 'close',
            '成交量': 'volume'
        }
        
        # 检查必需列是否存在
        missing_cols = [col for col in column_mapping.keys() if col not in cleaned.columns]
        if missing_cols:
            logger.error(f"数据缺少必需列: {missing_cols}")
            return pd.DataFrame()
        
        # 选择并重命名列
        cleaned = cleaned[list(column_mapping.keys())].copy()
        cleaned.columns = list(column_mapping.values())
        
        # 转换日期格式
        cleaned['date'] = pd.to_datetime(cleaned['date'])
        
        # 确保数值类型
        for col in ['open', 'high', 'low', 'close', 'volume']:
            cleaned[col] = pd.to_numeric(cleaned[col], errors='coerce')
        
        # 删除包含 NaN 的行
        cleaned = cleaned.dropna()
        
        # 按日期排序（升序）
        cleaned = cleaned.sort_values('date').reset_index(drop=True)
        
        logger.debug(f"数据清洗完成: {len(cleaned)} 条记录")
        return cleaned
    
    def overwrite_update(self, code: str, days: int = 365) -> bool:
        """
        覆盖更新数据
        
        采用覆盖策略而非增量更新，以确保复权数据准确性。
        每次更新时覆盖重写最近 N 天的数据。
        
        为什么不用增量更新？
        - 前复权数据会因为分红送转而重新计算历史价格
        - 增量更新会导致新旧数据复权基准不一致
        - 覆盖更新虽然多下载一些数据，但保证数据一致性
        
        Args:
            code: 股票代码
            days: 覆盖天数，默认 365 天
        
        Returns:
            是否更新成功
            
        Requirements: 1.6
        """
        # 计算日期范围
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        logger.info(f"开始覆盖更新: {code}, 日期范围: {start_str} ~ {end_str}")
        
        # 下载数据
        df = self.download_stock_data(code, start_str, end_str, adjust='qfq')
        
        if df is None or df.empty:
            logger.error(f"覆盖更新失败: {code}, 无法获取数据")
            return False
        
        # 清洗数据
        cleaned = self.clean_data(df)
        
        if cleaned.empty:
            logger.error(f"覆盖更新失败: {code}, 数据清洗后为空")
            return False
        
        # 保存到处理后数据目录
        file_path = os.path.join(self.processed_path, f"{code}.csv")
        cleaned.to_csv(file_path, index=False)
        
        logger.info(f"覆盖更新成功: {code}, 保存至 {file_path}, 共 {len(cleaned)} 条记录")
        return True
    
    def load_processed_data(self, code: str) -> Optional[pd.DataFrame]:
        """
        加载已处理的数据
        
        Args:
            code: 股票代码
        
        Returns:
            DataFrame 或 None（文件不存在时）
        """
        file_path = os.path.join(self.processed_path, f"{code}.csv")
        
        if not os.path.exists(file_path):
            logger.warning(f"数据文件不存在: {file_path}")
            return None
        
        try:
            df = pd.read_csv(file_path)
            df['date'] = pd.to_datetime(df['date'])
            logger.debug(f"加载数据成功: {code}, 共 {len(df)} 条记录")
            return df
        except Exception as e:
            logger.error(f"加载数据失败: {code}, 错误: {e}")
            return None
    
    def save_raw_data(self, code: str, df: pd.DataFrame) -> bool:
        """
        保存原始数据
        
        Args:
            code: 股票代码
            df: 原始数据 DataFrame
        
        Returns:
            是否保存成功
        """
        if df is None or df.empty:
            return False
        
        file_path = os.path.join(self.raw_path, f"{code}_raw.csv")
        
        try:
            df.to_csv(file_path, index=False)
            logger.debug(f"保存原始数据成功: {file_path}")
            return True
        except Exception as e:
            logger.error(f"保存原始数据失败: {code}, 错误: {e}")
            return False


    def get_market_snapshot(
        self, 
        liquidity_filter: Optional[LiquidityFilter] = None
    ) -> pd.DataFrame:
        """
        获取全市场实时快照并进行预剪枝（性能优化关键）
        
        设计原则：先用实时数据快速过滤，再对候选池下载历史数据
        - 全市场 5000+ 只股票 → 预剪枝后约 100-300 只候选
        - 避免对不符合条件的股票下载历史数据，节省 90%+ 的时间
        
        预剪枝条件（基于实时快照数据）：
        1. 流通市值在 50亿-500亿 之间
        2. 换手率在 2%-15% 之间
        3. 剔除 ST 股票
        
        Args:
            liquidity_filter: 流动性过滤配置，None 时使用默认值
        
        Returns:
            DataFrame，包含列：code, name, price, market_cap, turnover_rate
            
        Requirements: 1.8, 2.13
        """
        import akshare as ak
        
        if liquidity_filter is None:
            liquidity_filter = LiquidityFilter()
        
        try:
            # 获取全市场实时行情快照（单次 API 调用，约 1-2 秒）
            logger.info("正在获取全市场实时快照...")
            df = ak.stock_zh_a_spot_em()
            
            if df is None or df.empty:
                logger.error("获取市场快照失败: 返回数据为空")
                return pd.DataFrame()
            
            original_count = len(df)
            logger.info(f"获取全市场快照: {original_count} 只股票")
            
            # 预剪枝 1: 剔除 ST 股票
            if liquidity_filter.exclude_st:
                df = df[~df['名称'].str.contains('ST', na=False)]
                logger.info(f"剔除 ST 后: {len(df)} 只 (剔除 {original_count - len(df)} 只)")
            
            # 预剪枝 2: 流通市值过滤
            # 注意：AkShare 返回的流通市值单位是元
            before_cap = len(df)
            df = df[
                (df['流通市值'] >= liquidity_filter.min_market_cap) &
                (df['流通市值'] <= liquidity_filter.max_market_cap)
            ]
            logger.info(f"流通市值过滤后: {len(df)} 只 (剔除 {before_cap - len(df)} 只)")
            
            # 预剪枝 3: 换手率过滤
            # 注意：AkShare 返回的换手率是百分比形式（如 5.23 表示 5.23%）
            # 而 LiquidityFilter 中的换手率是小数形式（如 0.02 表示 2%）
            before_turnover = len(df)
            min_turnover_pct = liquidity_filter.min_turnover_rate * 100
            max_turnover_pct = liquidity_filter.max_turnover_rate * 100
            df = df[
                (df['换手率'] >= min_turnover_pct) &
                (df['换手率'] <= max_turnover_pct)
            ]
            logger.info(f"换手率过滤后: {len(df)} 只 (剔除 {before_turnover - len(df)} 只)")
            
            # 标准化输出列
            result = df[['代码', '名称', '最新价', '流通市值', '换手率']].copy()
            result.columns = ['code', 'name', 'price', 'market_cap', 'turnover_rate']
            
            # 转换换手率为小数形式（与 LiquidityFilter 保持一致）
            result['turnover_rate'] = result['turnover_rate'] / 100
            
            logger.info(f"预剪枝完成: {len(result)} 只候选股票 (从 {original_count} 只中筛选)")
            return result
            
        except Exception as e:
            self._handle_snapshot_error(e)
            return pd.DataFrame()
    
    def _handle_snapshot_error(self, error: Exception) -> None:
        """
        处理市场快照获取错误
        
        Args:
            error: 异常对象
        """
        error_msg = str(error)
        error_type = type(error).__name__
        
        if any(keyword in error_msg.lower() for keyword in 
               ['connection', 'timeout', 'refused', 'reset', 'network']):
            logger.error(
                f"获取市场快照失败: 网络连接问题。\n"
                f"  错误类型: {error_type}\n"
                f"  错误信息: {error_msg}\n"
                f"  建议: 请检查网络连接，或稍后重试。"
            )
        elif any(keyword in error_msg for keyword in 
                 ['KeyError', 'AttributeError', 'IndexError']):
            logger.error(
                f"获取市场快照失败: 数据解析问题。\n"
                f"  错误类型: {error_type}\n"
                f"  错误信息: {error_msg}\n"
                f"  可能原因: AkShare 接口已更新。\n"
                f"  建议: pip install akshare=={self.RECOMMENDED_AKSHARE_VERSION}"
            )
        else:
            logger.error(
                f"获取市场快照失败。\n"
                f"  错误类型: {error_type}\n"
                f"  错误信息: {error_msg}"
            )
    
    def get_data_status(self, codes: List[str]) -> Dict[str, dict]:
        """
        获取数据状态概览
        
        Args:
            codes: 股票代码列表
        
        Returns:
            {股票代码: {exists: bool, last_date: str, record_count: int}}
        """
        status = {}
        
        for code in codes:
            file_path = os.path.join(self.processed_path, f"{code}.csv")
            
            if os.path.exists(file_path):
                try:
                    df = pd.read_csv(file_path)
                    last_date = df['date'].max() if 'date' in df.columns else 'N/A'
                    status[code] = {
                        'exists': True,
                        'last_date': str(last_date),
                        'record_count': len(df)
                    }
                except Exception:
                    status[code] = {
                        'exists': True,
                        'last_date': 'Error',
                        'record_count': 0
                    }
            else:
                status[code] = {
                    'exists': False,
                    'last_date': None,
                    'record_count': 0
                }
        
        return status
    
    def clear_cache(self) -> bool:
        """
        清空所有缓存数据
        
        Returns:
            是否清空成功
        """
        import shutil
        
        try:
            # 清空原始数据目录
            if os.path.exists(self.raw_path):
                for file in os.listdir(self.raw_path):
                    file_path = os.path.join(self.raw_path, file)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                logger.info(f"已清空原始数据目录: {self.raw_path}")
            
            # 清空处理后数据目录
            if os.path.exists(self.processed_path):
                for file in os.listdir(self.processed_path):
                    file_path = os.path.join(self.processed_path, file)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                logger.info(f"已清空处理后数据目录: {self.processed_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"清空缓存失败: {e}")
            return False
    
    def get_stock_name(self, code: str) -> Optional[str]:
        """
        获取股票名称
        
        通过 AkShare 获取股票的中文名称
        
        Args:
            code: 股票代码（6位数字，如 '000001'）
        
        Returns:
            股票名称，获取失败时返回 None
        """
        try:
            import akshare as ak
            
            # 尝试从实时行情获取股票名称
            df = ak.stock_zh_a_spot_em()
            if df is not None and not df.empty:
                stock_row = df[df['代码'] == code]
                if not stock_row.empty:
                    return stock_row.iloc[0]['名称']
            
            logger.warning(f"无法获取股票名称: {code}")
            return None
            
        except Exception as e:
            logger.warning(f"获取股票名称失败: {code}, 错误: {e}")
            return None
    
    def get_stock_names_batch(self, codes: List[str]) -> Dict[str, str]:
        """
        批量获取股票名称
        
        一次性获取多只股票的名称，比逐个获取更高效
        
        Args:
            codes: 股票代码列表
        
        Returns:
            {股票代码: 股票名称} 字典
        """
        try:
            import akshare as ak
            
            # 获取全市场实时行情
            df = ak.stock_zh_a_spot_em()
            if df is None or df.empty:
                return {}
            
            # 筛选目标股票
            result = {}
            for code in codes:
                stock_row = df[df['代码'] == code]
                if not stock_row.empty:
                    result[code] = stock_row.iloc[0]['名称']
                else:
                    result[code] = code  # 找不到名称时使用代码作为名称
            
            return result
            
        except Exception as e:
            logger.warning(f"批量获取股票名称失败: {e}")
            return {code: code for code in codes}  # 失败时返回代码作为名称
