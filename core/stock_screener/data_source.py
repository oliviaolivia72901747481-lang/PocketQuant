"""
多数据源获取模块

提供多数据源的股票数据获取功能，支持：
- akshare数据接口
- 东方财富数据源
- 数据源容错和重试机制
- 多源数据交叉验证

Requirements: 7.1, 7.4
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from datetime import datetime
import time
import logging
import pandas as pd

logger = logging.getLogger(__name__)


class DataSourceType(Enum):
    """数据源类型"""
    AKSHARE = "akshare"
    EASTMONEY = "eastmoney"


@dataclass
class DataSourceConfig:
    """数据源配置"""
    source_type: DataSourceType
    enabled: bool = True
    priority: int = 1  # 优先级，数字越小优先级越高
    max_retries: int = 3
    retry_delay: float = 1.0  # 重试延迟（秒）
    timeout: float = 30.0  # 超时时间（秒）
    rate_limit: float = 0.1  # 请求间隔（秒）


@dataclass
class DataSourceResult:
    """数据源获取结果"""
    success: bool
    data: Optional[pd.DataFrame] = None
    source: Optional[DataSourceType] = None
    error_message: Optional[str] = None
    fetch_time: float = 0.0  # 获取耗时（秒）
    retry_count: int = 0


@dataclass
class CrossValidationResult:
    """交叉验证结果"""
    is_valid: bool
    confidence: float  # 置信度 0-1
    discrepancies: List[str] = field(default_factory=list)
    source_results: Dict[str, DataSourceResult] = field(default_factory=dict)


class AkshareDataSource:
    """
    AkShare数据源
    
    提供基于akshare的股票数据获取功能
    """
    
    def __init__(self, config: DataSourceConfig):
        self.config = config
        self._last_request_time = 0.0
    
    def _rate_limit(self):
        """请求频率限制"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.config.rate_limit:
            time.sleep(self.config.rate_limit - elapsed)
        self._last_request_time = time.time()
    
    def get_all_stocks(self) -> DataSourceResult:
        """获取全市场股票列表"""
        start_time = time.time()
        retry_count = 0
        
        for attempt in range(self.config.max_retries):
            try:
                self._rate_limit()
                import akshare as ak
                
                df = ak.stock_zh_a_spot_em()
                
                if df is None or df.empty:
                    retry_count = attempt + 1
                    if attempt < self.config.max_retries - 1:
                        time.sleep(self.config.retry_delay)
                        continue
                    return DataSourceResult(
                        success=False,
                        source=DataSourceType.AKSHARE,
                        error_message="返回数据为空",
                        fetch_time=time.time() - start_time,
                        retry_count=retry_count
                    )
                
                # 标准化列名
                result_df = self._standardize_stock_list(df)
                
                return DataSourceResult(
                    success=True,
                    data=result_df,
                    source=DataSourceType.AKSHARE,
                    fetch_time=time.time() - start_time,
                    retry_count=retry_count
                )
                
            except Exception as e:
                retry_count = attempt + 1
                logger.warning(f"AkShare获取股票列表失败 (尝试 {attempt + 1}/{self.config.max_retries}): {e}")
                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay * (attempt + 1))
                    continue
                
                return DataSourceResult(
                    success=False,
                    source=DataSourceType.AKSHARE,
                    error_message=str(e),
                    fetch_time=time.time() - start_time,
                    retry_count=retry_count
                )
        
        return DataSourceResult(
            success=False,
            source=DataSourceType.AKSHARE,
            error_message="超过最大重试次数",
            fetch_time=time.time() - start_time,
            retry_count=retry_count
        )
    
    def _standardize_stock_list(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化股票列表数据"""
        # AkShare列名映射
        column_mapping = {
            '代码': 'code',
            '名称': 'name',
            '最新价': 'price',
            '涨跌幅': 'change_pct',
            '涨跌额': 'change_amount',
            '成交量': 'volume',
            '成交额': 'turnover',
            '振幅': 'amplitude',
            '最高': 'high',
            '最低': 'low',
            '今开': 'open',
            '昨收': 'prev_close',
            '量比': 'volume_ratio',
            '换手率': 'turnover_rate',
            '市盈率-动态': 'pe_ratio',
            '市净率': 'pb_ratio',
            '总市值': 'total_market_cap',
            '流通市值': 'float_market_cap',
            '涨速': 'change_speed',
            '5分钟涨跌': 'change_5min',
            '60日涨跌幅': 'change_60d',
            '年初至今涨跌幅': 'change_ytd',
        }
        
        result = df.copy()
        
        # 重命名存在的列
        rename_dict = {k: v for k, v in column_mapping.items() if k in result.columns}
        result = result.rename(columns=rename_dict)
        
        # 确保必需列存在
        required_columns = ['code', 'name', 'price', 'total_market_cap', 'float_market_cap', 
                          'turnover_rate', 'pe_ratio', 'pb_ratio']
        for col in required_columns:
            if col not in result.columns:
                result[col] = None
        
        # 添加数据源标识
        result['data_source'] = 'akshare'
        result['fetch_time'] = datetime.now()
        
        return result
    
    def get_stock_industry(self, code: str) -> DataSourceResult:
        """获取股票行业分类"""
        start_time = time.time()
        
        try:
            self._rate_limit()
            import akshare as ak
            
            # 获取个股所属行业
            df = ak.stock_individual_info_em(symbol=code)
            
            if df is None or df.empty:
                return DataSourceResult(
                    success=False,
                    source=DataSourceType.AKSHARE,
                    error_message="无法获取行业信息",
                    fetch_time=time.time() - start_time
                )
            
            # 提取行业信息
            industry_row = df[df['item'] == '行业']
            industry = industry_row['value'].values[0] if not industry_row.empty else None
            
            result_df = pd.DataFrame([{
                'code': code,
                'industry': industry,
                'data_source': 'akshare'
            }])
            
            return DataSourceResult(
                success=True,
                data=result_df,
                source=DataSourceType.AKSHARE,
                fetch_time=time.time() - start_time
            )
            
        except Exception as e:
            return DataSourceResult(
                success=False,
                source=DataSourceType.AKSHARE,
                error_message=str(e),
                fetch_time=time.time() - start_time
            )
    
    def get_financial_indicators(self, code: str) -> DataSourceResult:
        """获取财务指标"""
        start_time = time.time()
        
        try:
            self._rate_limit()
            import akshare as ak
            
            df = ak.stock_financial_analysis_indicator(symbol=code)
            
            if df is None or df.empty:
                return DataSourceResult(
                    success=False,
                    source=DataSourceType.AKSHARE,
                    error_message="无法获取财务指标",
                    fetch_time=time.time() - start_time
                )
            
            # 添加数据源标识
            df['data_source'] = 'akshare'
            df['code'] = code
            
            return DataSourceResult(
                success=True,
                data=df,
                source=DataSourceType.AKSHARE,
                fetch_time=time.time() - start_time
            )
            
        except Exception as e:
            return DataSourceResult(
                success=False,
                source=DataSourceType.AKSHARE,
                error_message=str(e),
                fetch_time=time.time() - start_time
            )


class EastmoneyDataSource:
    """
    东方财富数据源
    
    提供基于东方财富的股票数据获取功能
    作为akshare的备用数据源
    """
    
    def __init__(self, config: DataSourceConfig):
        self.config = config
        self._last_request_time = 0.0
    
    def _rate_limit(self):
        """请求频率限制"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.config.rate_limit:
            time.sleep(self.config.rate_limit - elapsed)
        self._last_request_time = time.time()
    
    def get_all_stocks(self) -> DataSourceResult:
        """获取全市场股票列表（通过akshare的东方财富接口）"""
        start_time = time.time()
        retry_count = 0
        
        for attempt in range(self.config.max_retries):
            try:
                self._rate_limit()
                import akshare as ak
                
                # 使用东方财富的实时行情接口
                df = ak.stock_zh_a_spot_em()
                
                if df is None or df.empty:
                    retry_count = attempt + 1
                    if attempt < self.config.max_retries - 1:
                        time.sleep(self.config.retry_delay)
                        continue
                    return DataSourceResult(
                        success=False,
                        source=DataSourceType.EASTMONEY,
                        error_message="返回数据为空",
                        fetch_time=time.time() - start_time,
                        retry_count=retry_count
                    )
                
                # 标准化列名
                result_df = self._standardize_stock_list(df)
                
                return DataSourceResult(
                    success=True,
                    data=result_df,
                    source=DataSourceType.EASTMONEY,
                    fetch_time=time.time() - start_time,
                    retry_count=retry_count
                )
                
            except Exception as e:
                retry_count = attempt + 1
                logger.warning(f"东方财富获取股票列表失败 (尝试 {attempt + 1}/{self.config.max_retries}): {e}")
                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay * (attempt + 1))
                    continue
                
                return DataSourceResult(
                    success=False,
                    source=DataSourceType.EASTMONEY,
                    error_message=str(e),
                    fetch_time=time.time() - start_time,
                    retry_count=retry_count
                )
        
        return DataSourceResult(
            success=False,
            source=DataSourceType.EASTMONEY,
            error_message="超过最大重试次数",
            fetch_time=time.time() - start_time,
            retry_count=retry_count
        )
    
    def _standardize_stock_list(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化股票列表数据"""
        column_mapping = {
            '代码': 'code',
            '名称': 'name',
            '最新价': 'price',
            '涨跌幅': 'change_pct',
            '成交额': 'turnover',
            '换手率': 'turnover_rate',
            '市盈率-动态': 'pe_ratio',
            '市净率': 'pb_ratio',
            '总市值': 'total_market_cap',
            '流通市值': 'float_market_cap',
        }
        
        result = df.copy()
        rename_dict = {k: v for k, v in column_mapping.items() if k in result.columns}
        result = result.rename(columns=rename_dict)
        
        result['data_source'] = 'eastmoney'
        result['fetch_time'] = datetime.now()
        
        return result
    
    def get_concept_stocks(self, concept_name: str) -> DataSourceResult:
        """获取概念板块股票"""
        start_time = time.time()
        
        try:
            self._rate_limit()
            import akshare as ak
            
            # 获取概念板块成分股
            df = ak.stock_board_concept_cons_em(symbol=concept_name)
            
            if df is None or df.empty:
                return DataSourceResult(
                    success=False,
                    source=DataSourceType.EASTMONEY,
                    error_message=f"无法获取概念板块 {concept_name} 的成分股",
                    fetch_time=time.time() - start_time
                )
            
            df['concept'] = concept_name
            df['data_source'] = 'eastmoney'
            
            return DataSourceResult(
                success=True,
                data=df,
                source=DataSourceType.EASTMONEY,
                fetch_time=time.time() - start_time
            )
            
        except Exception as e:
            return DataSourceResult(
                success=False,
                source=DataSourceType.EASTMONEY,
                error_message=str(e),
                fetch_time=time.time() - start_time
            )


class DataSourceManager:
    """
    数据源管理器
    
    统一管理多个数据源，提供：
    - 数据源优先级管理
    - 自动容错和切换
    - 多源数据交叉验证
    - 健康检查和自动恢复
    - 集成备份管理器支持
    
    Requirements: 7.1, 7.4
    """
    
    def __init__(self, use_backup_manager: bool = True):
        """
        初始化数据源管理器
        
        Args:
            use_backup_manager: 是否使用备份管理器
        """
        # 默认数据源配置
        self._source_configs: Dict[DataSourceType, DataSourceConfig] = {
            DataSourceType.AKSHARE: DataSourceConfig(
                source_type=DataSourceType.AKSHARE,
                enabled=True,
                priority=1,
                max_retries=3,
                retry_delay=1.0,
                rate_limit=0.1
            ),
            DataSourceType.EASTMONEY: DataSourceConfig(
                source_type=DataSourceType.EASTMONEY,
                enabled=True,
                priority=2,
                max_retries=3,
                retry_delay=1.0,
                rate_limit=0.1
            ),
        }
        
        # 初始化数据源实例
        self._sources: Dict[DataSourceType, Any] = {}
        self._init_sources()
        
        # 统计信息
        self._stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'source_usage': {source.value: 0 for source in DataSourceType},
            'last_success_time': {source.value: None for source in DataSourceType},
            'consecutive_failures': {source.value: 0 for source in DataSourceType}
        }
        
        # 健康状态
        self._health_status: Dict[str, bool] = {
            source.value: True for source in DataSourceType
        }
        
        # 备份管理器集成
        self._use_backup_manager = use_backup_manager
        self._backup_manager = None
        if use_backup_manager:
            self._init_backup_manager()
    
    def _init_sources(self):
        """初始化数据源实例"""
        for source_type, config in self._source_configs.items():
            if config.enabled:
                if source_type == DataSourceType.AKSHARE:
                    self._sources[source_type] = AkshareDataSource(config)
                elif source_type == DataSourceType.EASTMONEY:
                    self._sources[source_type] = EastmoneyDataSource(config)
    
    def _init_backup_manager(self):
        """初始化备份管理器"""
        try:
            from .data_source_backup import get_backup_manager
            self._backup_manager = get_backup_manager()
            
            # 注册数据源到备份管理器
            for source_type, config in self._source_configs.items():
                if config.enabled:
                    self._backup_manager.register_source(
                        source_type.value, 
                        config.priority
                    )
            
            logger.info("备份管理器已初始化")
        except Exception as e:
            logger.warning(f"备份管理器初始化失败: {e}")
            self._backup_manager = None
    
    def configure_source(self, source_type: DataSourceType, config: DataSourceConfig):
        """配置数据源"""
        self._source_configs[source_type] = config
        self._init_sources()
    
    def get_enabled_sources(self) -> List[DataSourceType]:
        """获取已启用的数据源列表（按优先级排序）"""
        enabled = [
            (source_type, config) 
            for source_type, config in self._source_configs.items() 
            if config.enabled
        ]
        enabled.sort(key=lambda x: x[1].priority)
        return [source_type for source_type, _ in enabled]
    
    def get_all_stocks(self, use_fallback: bool = True, use_cache: bool = True) -> DataSourceResult:
        """
        获取全市场股票列表
        
        Args:
            use_fallback: 是否在主数据源失败时使用备用数据源
            use_cache: 是否使用缓存
        
        Returns:
            DataSourceResult: 获取结果
        """
        self._stats['total_requests'] += 1
        cache_key = "all_stocks"
        
        # 尝试从缓存获取
        if use_cache and self._backup_manager:
            cached = self._backup_manager.get_cached_data(cache_key)
            if cached:
                data, source_name = cached
                logger.info(f"从缓存获取 {len(data)} 只股票")
                return DataSourceResult(
                    success=True,
                    data=data,
                    source=DataSourceType(source_name) if source_name in [s.value for s in DataSourceType] else None,
                    fetch_time=0.0
                )
        
        enabled_sources = self.get_enabled_sources()
        
        for source_type in enabled_sources:
            source = self._sources.get(source_type)
            if source is None:
                continue
            
            # 检查数据源健康状态
            if not self._health_status.get(source_type.value, True):
                logger.warning(f"数据源 {source_type.value} 当前不健康，跳过")
                continue
            
            logger.info(f"尝试从 {source_type.value} 获取股票列表...")
            result = source.get_all_stocks()
            
            if result.success:
                self._stats['successful_requests'] += 1
                self._stats['source_usage'][source_type.value] += 1
                self._stats['last_success_time'][source_type.value] = datetime.now()
                self._stats['consecutive_failures'][source_type.value] = 0
                self._health_status[source_type.value] = True
                logger.info(f"成功从 {source_type.value} 获取 {len(result.data)} 只股票")
                
                # 更新备份管理器
                if self._backup_manager:
                    self._backup_manager.record_success(
                        source_type.value, 
                        result.fetch_time * 1000
                    )
                    # 缓存数据
                    self._backup_manager.cache_data(
                        cache_key, 
                        result.data, 
                        source_type.value
                    )
                    # 保存本地备份
                    self._backup_manager.save_local_backup(
                        "all_stocks",
                        result.data,
                        source_type.value
                    )
                
                return result
            
            # 记录失败
            self._stats['consecutive_failures'][source_type.value] += 1
            if self._stats['consecutive_failures'][source_type.value] >= 3:
                self._health_status[source_type.value] = False
                logger.warning(f"数据源 {source_type.value} 连续失败3次，标记为不健康")
            
            # 更新备份管理器
            if self._backup_manager:
                self._backup_manager.record_failure(
                    source_type.value,
                    result.error_message or "未知错误"
                )
            
            logger.warning(f"{source_type.value} 获取失败: {result.error_message}")
            
            if not use_fallback:
                break
        
        self._stats['failed_requests'] += 1
        
        # 尝试从本地备份恢复
        if self._backup_manager:
            # 先尝试过期缓存
            cached = self._backup_manager.get_cached_data(cache_key, allow_stale=True)
            if cached:
                data, source_name = cached
                logger.warning(f"使用过期缓存数据: {len(data)} 只股票")
                return DataSourceResult(
                    success=True,
                    data=data,
                    source=None,
                    fetch_time=0.0,
                    error_message="使用过期缓存数据"
                )
            
            # 尝试本地备份
            backup_result = self._backup_manager.load_local_backup("all_stocks")
            if backup_result:
                data, meta = backup_result
                logger.warning(f"从本地备份恢复: {len(data)} 只股票")
                return DataSourceResult(
                    success=True,
                    data=data,
                    source=None,
                    fetch_time=0.0,
                    error_message="从本地备份恢复"
                )
        
        return DataSourceResult(
            success=False,
            error_message="所有数据源均获取失败，且无可用备份"
        )
    
    def get_mainboard_stocks(self, use_fallback: bool = True) -> DataSourceResult:
        """
        获取主板和中小板股票列表
        
        只返回代码以000、001、002、600、601、603、605开头的股票
        
        Args:
            use_fallback: 是否在主数据源失败时使用备用数据源
        
        Returns:
            DataSourceResult: 获取结果
        """
        result = self.get_all_stocks(use_fallback)
        
        if not result.success:
            return result
        
        # 过滤主板和中小板股票
        df = result.data
        mainboard_pattern = r'^(000|001|002|600|601|603|605)\d{3}$'
        mask = df['code'].str.match(mainboard_pattern, na=False)
        filtered_df = df[mask].copy()
        
        logger.info(f"过滤后获得 {len(filtered_df)} 只主板/中小板股票")
        
        return DataSourceResult(
            success=True,
            data=filtered_df,
            source=result.source,
            fetch_time=result.fetch_time,
            retry_count=result.retry_count
        )
    
    def check_health(self) -> Dict[str, Any]:
        """
        检查所有数据源的健康状态
        
        Returns:
            Dict: 健康状态报告
        """
        health_report = {
            'overall_healthy': True,
            'sources': {}
        }
        
        for source_type in DataSourceType:
            source_name = source_type.value
            is_healthy = self._health_status.get(source_name, True)
            consecutive_failures = self._stats['consecutive_failures'].get(source_name, 0)
            last_success = self._stats['last_success_time'].get(source_name)
            
            health_report['sources'][source_name] = {
                'healthy': is_healthy,
                'consecutive_failures': consecutive_failures,
                'last_success_time': last_success.isoformat() if last_success else None,
                'enabled': self._source_configs.get(source_type, DataSourceConfig(source_type)).enabled
            }
            
            if not is_healthy:
                health_report['overall_healthy'] = False
        
        return health_report
    
    def reset_health_status(self, source_type: Optional[DataSourceType] = None):
        """
        重置数据源健康状态
        
        Args:
            source_type: 要重置的数据源类型，None表示重置所有
        """
        if source_type:
            self._health_status[source_type.value] = True
            self._stats['consecutive_failures'][source_type.value] = 0
            logger.info(f"已重置数据源 {source_type.value} 的健康状态")
        else:
            for st in DataSourceType:
                self._health_status[st.value] = True
                self._stats['consecutive_failures'][st.value] = 0
            logger.info("已重置所有数据源的健康状态")
    
    def get_stock_data_with_validation(
        self, 
        fetch_func_name: str,
        *args, 
        **kwargs
    ) -> CrossValidationResult:
        """
        获取数据并进行多源交叉验证
        
        Args:
            fetch_func_name: 获取函数名称
            *args, **kwargs: 传递给获取函数的参数
        
        Returns:
            CrossValidationResult: 交叉验证结果
        """
        source_results = {}
        
        for source_type in self.get_enabled_sources():
            source = self._sources.get(source_type)
            if source is None:
                continue
            
            fetch_func = getattr(source, fetch_func_name, None)
            if fetch_func is None:
                continue
            
            result = fetch_func(*args, **kwargs)
            source_results[source_type.value] = result
        
        # 执行交叉验证
        return self._cross_validate(source_results)
    
    def _cross_validate(
        self, 
        source_results: Dict[str, DataSourceResult]
    ) -> CrossValidationResult:
        """执行交叉验证"""
        successful_results = {
            k: v for k, v in source_results.items() if v.success
        }
        
        if len(successful_results) == 0:
            return CrossValidationResult(
                is_valid=False,
                confidence=0.0,
                discrepancies=["所有数据源均获取失败"],
                source_results=source_results
            )
        
        if len(successful_results) == 1:
            # 只有一个数据源成功，无法交叉验证
            return CrossValidationResult(
                is_valid=True,
                confidence=0.7,  # 单源置信度较低
                discrepancies=[],
                source_results=source_results
            )
        
        # 多源数据比较
        discrepancies = []
        data_frames = [r.data for r in successful_results.values()]
        
        # 比较数据量差异
        row_counts = [len(df) for df in data_frames]
        if max(row_counts) - min(row_counts) > max(row_counts) * 0.1:
            discrepancies.append(
                f"数据量差异较大: {row_counts}"
            )
        
        # 计算置信度
        if len(discrepancies) == 0:
            confidence = 0.95
        elif len(discrepancies) <= 2:
            confidence = 0.8
        else:
            confidence = 0.6
        
        return CrossValidationResult(
            is_valid=len(discrepancies) <= 2,
            confidence=confidence,
            discrepancies=discrepancies,
            source_results=source_results
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取数据源使用统计"""
        return {
            **self._stats,
            'success_rate': (
                self._stats['successful_requests'] / self._stats['total_requests']
                if self._stats['total_requests'] > 0 else 0
            )
        }
    
    def reset_statistics(self):
        """重置统计信息"""
        self._stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'source_usage': {source.value: 0 for source in DataSourceType},
            'last_success_time': {source.value: None for source in DataSourceType},
            'consecutive_failures': {source.value: 0 for source in DataSourceType}
        }
    
    def get_backup_manager(self):
        """
        获取备份管理器实例
        
        Returns:
            DataSourceBackupManager 或 None
        """
        return self._backup_manager
    
    def get_backup_summary(self) -> Dict[str, Any]:
        """
        获取备份摘要
        
        Returns:
            备份状态摘要字典
        """
        if self._backup_manager:
            return self._backup_manager.get_backup_summary()
        return {
            'backup_manager_enabled': False,
            'message': '备份管理器未启用'
        }
    
    def get_failover_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取故障转移历史
        
        Args:
            limit: 返回记录数量限制
        
        Returns:
            故障转移事件列表
        """
        if self._backup_manager:
            return self._backup_manager.get_failover_history(limit)
        return []
    
    def clear_cache(self):
        """清除所有缓存"""
        if self._backup_manager:
            self._backup_manager.clear_cache()
            logger.info("已清除所有数据缓存")


# 全局数据源管理器实例
_data_source_manager: Optional[DataSourceManager] = None


def get_data_source_manager() -> DataSourceManager:
    """
    获取数据源管理器实例（单例模式）
    
    Returns:
        DataSourceManager: 数据源管理器实例
    """
    global _data_source_manager
    if _data_source_manager is None:
        _data_source_manager = DataSourceManager()
    return _data_source_manager


def reset_data_source_manager():
    """重置数据源管理器实例"""
    global _data_source_manager
    _data_source_manager = None
