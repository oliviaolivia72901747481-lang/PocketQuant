"""
科技股数据下载器模块

提供科技股数据的批量下载和管理功能，支持进度跟踪和错误处理。

核心功能：
1. 科技股池批量下载
2. 缺失股票数据下载
3. 下载进度跟踪
4. 下载结果报告

Requirements: 2.1, 2.2, 2.3
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Any
from datetime import datetime, date, timedelta
import threading
import time
import os
import logging

from config.tech_stock_pool import get_tech_stock_pool
from core.data_feed import DataFeed

logger = logging.getLogger(__name__)


@dataclass
class DownloadProgress:
    """下载进度信息"""
    total_stocks: int
    completed_stocks: int
    current_stock: Optional[str] = None
    current_stock_name: Optional[str] = None
    success_count: int = 0
    failed_count: int = 0
    start_time: Optional[datetime] = None
    estimated_remaining: Optional[int] = None  # 秒
    is_completed: bool = False
    is_cancelled: bool = False


@dataclass
class DownloadResult:
    """下载结果"""
    success: bool
    total_requested: int
    successful_downloads: List[str] = field(default_factory=list)
    failed_downloads: List[Dict[str, str]] = field(default_factory=list)
    skipped_downloads: List[str] = field(default_factory=list)
    total_time: float = 0.0
    error_message: Optional[str] = None


class TechDataDownloader:
    """
    科技股数据下载器
    
    负责下载科技股池中所有股票的历史数据，支持：
    - 批量下载整个科技股池
    - 下载指定的缺失股票
    - 实时进度跟踪和状态更新
    - 详细的下载结果报告
    
    Requirements: 2.1, 2.2, 2.3
    """
    
    def __init__(self, data_feed: DataFeed):
        """
        初始化数据下载器
        
        Args:
            data_feed: 数据获取模块实例
        """
        self.data_feed = data_feed
        self.tech_stock_pool = get_tech_stock_pool()
        
        # 下载状态管理
        self._progress = DownloadProgress(total_stocks=0, completed_stocks=0)
        self._is_downloading = False
        self._cancel_requested = False
        self._download_thread: Optional[threading.Thread] = None
        
        # 下载配置
        self.download_days = 1095  # 默认下载3年数据
        self.max_retries = 3
        self.retry_delay = 2  # 秒
    
    def download_tech_stock_pool(
        self, 
        progress_callback: Optional[Callable[[DownloadProgress], None]] = None,
        force_update: bool = False
    ) -> DownloadResult:
        """
        下载整个科技股池的数据
        
        Args:
            progress_callback: 进度回调函数
            force_update: 是否强制更新已存在的数据
        
        Returns:
            下载结果
            
        Requirements: 2.1, 2.2
        """
        all_codes = self.tech_stock_pool.get_all_codes()
        logger.info(f"开始下载科技股池数据: {len(all_codes)} 只股票")
        
        return self.download_stocks(
            stock_codes=all_codes,
            progress_callback=progress_callback,
            force_update=force_update
        )
    
    def download_missing_stocks(
        self,
        missing_codes: List[str],
        progress_callback: Optional[Callable[[DownloadProgress], None]] = None
    ) -> DownloadResult:
        """
        下载缺失的股票数据
        
        Args:
            missing_codes: 缺失数据的股票代码列表
            progress_callback: 进度回调函数
        
        Returns:
            下载结果
            
        Requirements: 2.2
        """
        logger.info(f"开始下载缺失股票数据: {len(missing_codes)} 只股票")
        
        return self.download_stocks(
            stock_codes=missing_codes,
            progress_callback=progress_callback,
            force_update=True  # 缺失数据总是需要下载
        )
    
    def download_stocks(
        self,
        stock_codes: List[str],
        progress_callback: Optional[Callable[[DownloadProgress], None]] = None,
        force_update: bool = False
    ) -> DownloadResult:
        """
        下载指定股票的数据
        
        Args:
            stock_codes: 股票代码列表
            progress_callback: 进度回调函数
            force_update: 是否强制更新已存在的数据
        
        Returns:
            下载结果
            
        Requirements: 2.2, 2.3
        """
        if self._is_downloading:
            return DownloadResult(
                success=False,
                total_requested=len(stock_codes),
                error_message="已有下载任务在进行中"
            )
        
        # 初始化下载状态
        self._is_downloading = True
        self._cancel_requested = False
        self._progress = DownloadProgress(
            total_stocks=len(stock_codes),
            completed_stocks=0,
            start_time=datetime.now()
        )
        
        successful_downloads = []
        failed_downloads = []
        skipped_downloads = []
        
        start_time = time.time()
        
        try:
            for i, code in enumerate(stock_codes):
                if self._cancel_requested:
                    logger.info("下载被用户取消")
                    break
                
                # 更新进度
                stock_name = self.tech_stock_pool.get_stock_name(code)
                self._progress.current_stock = code
                self._progress.current_stock_name = stock_name
                self._progress.completed_stocks = i
                
                # 计算预估剩余时间
                if i > 0:
                    elapsed = time.time() - start_time
                    avg_time_per_stock = elapsed / i
                    remaining_stocks = len(stock_codes) - i
                    self._progress.estimated_remaining = int(avg_time_per_stock * remaining_stocks)
                
                # 调用进度回调
                if progress_callback:
                    progress_callback(self._progress)
                
                # 检查是否需要下载
                if not force_update and self._should_skip_download(code):
                    skipped_downloads.append(code)
                    logger.debug(f"跳过 {code} ({stock_name}): 数据已存在且较新")
                    continue
                
                # 下载股票数据
                success = self._download_single_stock(code)
                
                if success:
                    successful_downloads.append(code)
                    self._progress.success_count += 1
                    logger.info(f"✅ {code} ({stock_name}) 下载成功")
                else:
                    failed_downloads.append({
                        "code": code,
                        "name": stock_name,
                        "error": "下载失败"
                    })
                    self._progress.failed_count += 1
                    logger.error(f"❌ {code} ({stock_name}) 下载失败")
            
            # 完成下载
            self._progress.completed_stocks = len(stock_codes)
            self._progress.is_completed = True
            
            if progress_callback:
                progress_callback(self._progress)
            
            total_time = time.time() - start_time
            
            result = DownloadResult(
                success=len(failed_downloads) == 0 and not self._cancel_requested,
                total_requested=len(stock_codes),
                successful_downloads=successful_downloads,
                failed_downloads=failed_downloads,
                skipped_downloads=skipped_downloads,
                total_time=total_time
            )
            
            logger.info(f"下载完成: 成功 {len(successful_downloads)}, 失败 {len(failed_downloads)}, 跳过 {len(skipped_downloads)}")
            return result
            
        except Exception as e:
            logger.error(f"下载过程中出现异常: {e}")
            return DownloadResult(
                success=False,
                total_requested=len(stock_codes),
                successful_downloads=successful_downloads,
                failed_downloads=failed_downloads,
                skipped_downloads=skipped_downloads,
                total_time=time.time() - start_time,
                error_message=str(e)
            )
        
        finally:
            self._is_downloading = False
    
    def download_stocks_async(
        self,
        stock_codes: List[str],
        progress_callback: Optional[Callable[[DownloadProgress], None]] = None,
        completion_callback: Optional[Callable[[DownloadResult], None]] = None,
        force_update: bool = False
    ) -> bool:
        """
        异步下载股票数据
        
        Args:
            stock_codes: 股票代码列表
            progress_callback: 进度回调函数
            completion_callback: 完成回调函数
            force_update: 是否强制更新已存在的数据
        
        Returns:
            是否成功启动下载任务
            
        Requirements: 2.3
        """
        if self._is_downloading:
            return False
        
        def download_worker():
            try:
                result = self.download_stocks(
                    stock_codes=stock_codes,
                    progress_callback=progress_callback,
                    force_update=force_update
                )
                if completion_callback:
                    completion_callback(result)
            except Exception as e:
                logger.error(f"异步下载出错: {e}")
                if completion_callback:
                    completion_callback(DownloadResult(
                        success=False,
                        total_requested=len(stock_codes),
                        error_message=str(e)
                    ))
        
        self._download_thread = threading.Thread(target=download_worker)
        self._download_thread.daemon = True
        self._download_thread.start()
        
        return True
    
    def cancel_download(self) -> bool:
        """
        取消当前下载任务
        
        Returns:
            是否成功取消
        """
        if not self._is_downloading:
            return False
        
        self._cancel_requested = True
        self._progress.is_cancelled = True
        logger.info("下载取消请求已发送")
        return True
    
    def get_download_progress(self) -> DownloadProgress:
        """
        获取当前下载进度
        
        Returns:
            下载进度信息
            
        Requirements: 2.3
        """
        return self._progress
    
    def is_downloading(self) -> bool:
        """
        检查是否正在下载
        
        Returns:
            是否正在下载
        """
        return self._is_downloading
    
    def _download_single_stock(self, code: str) -> bool:
        """
        下载单只股票数据（带重试机制）
        
        Args:
            code: 股票代码
        
        Returns:
            是否下载成功
        """
        for attempt in range(self.max_retries):
            try:
                # 计算日期范围
                end_date = date.today()
                start_date = end_date - timedelta(days=self.download_days)
                
                start_str = start_date.strftime('%Y-%m-%d')
                end_str = end_date.strftime('%Y-%m-%d')
                
                # 下载数据
                df = self.data_feed.download_stock_data(
                    code=code,
                    start_date=start_str,
                    end_date=end_str,
                    adjust='qfq'
                )
                
                if df is None or df.empty:
                    logger.warning(f"股票 {code} 第 {attempt + 1} 次尝试: 无数据返回")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                        continue
                    return False
                
                # 清洗数据
                cleaned = self.data_feed.clean_data(df)
                
                if cleaned.empty:
                    logger.warning(f"股票 {code} 第 {attempt + 1} 次尝试: 数据清洗后为空")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                        continue
                    return False
                
                # 保存数据
                file_path = os.path.join(self.data_feed.processed_path, f"{code}.csv")
                cleaned.to_csv(file_path, index=False)
                
                logger.debug(f"股票 {code} 下载成功: {len(cleaned)} 条记录")
                return True
                
            except Exception as e:
                logger.warning(f"股票 {code} 第 {attempt + 1} 次尝试失败: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                return False
        
        return False
    
    def _should_skip_download(self, code: str) -> bool:
        """
        检查是否应该跳过下载（数据已存在且较新）
        
        Args:
            code: 股票代码
        
        Returns:
            是否应该跳过
        """
        import os
        
        file_path = os.path.join(self.data_feed.processed_path, f"{code}.csv")
        
        if not os.path.exists(file_path):
            return False
        
        try:
            # 检查文件修改时间
            file_mtime = os.path.getmtime(file_path)
            file_date = datetime.fromtimestamp(file_mtime).date()
            
            # 如果文件是今天修改的，跳过下载
            if file_date == date.today():
                return True
            
            # 检查数据内容的最新日期
            import pandas as pd
            df = pd.read_csv(file_path)
            
            if df.empty or 'date' not in df.columns:
                return False
            
            df['date'] = pd.to_datetime(df['date'])
            last_data_date = df['date'].max().date()
            
            # 如果数据最新日期是最近3天内，跳过下载
            days_old = (date.today() - last_data_date).days
            return days_old <= 3
            
        except Exception as e:
            logger.debug(f"检查 {code} 数据新旧程度时出错: {e}")
            return False
    
    def get_download_statistics(self) -> Dict[str, Any]:
        """
        获取下载统计信息
        
        Returns:
            下载统计信息
        """
        return {
            "is_downloading": self._is_downloading,
            "progress": {
                "total_stocks": self._progress.total_stocks,
                "completed_stocks": self._progress.completed_stocks,
                "success_count": self._progress.success_count,
                "failed_count": self._progress.failed_count,
                "completion_rate": (
                    self._progress.completed_stocks / self._progress.total_stocks 
                    if self._progress.total_stocks > 0 else 0
                )
            },
            "current_task": {
                "stock_code": self._progress.current_stock,
                "stock_name": self._progress.current_stock_name,
                "estimated_remaining": self._progress.estimated_remaining
            },
            "status": {
                "is_completed": self._progress.is_completed,
                "is_cancelled": self._progress.is_cancelled
            }
        }
    
    def format_download_result(self, result: DownloadResult) -> str:
        """
        格式化下载结果为可读字符串
        
        Args:
            result: 下载结果
        
        Returns:
            格式化的结果字符串
        """
        if not result.success and result.error_message:
            return f"下载失败: {result.error_message}"
        
        lines = [
            f"下载完成 {'✅' if result.success else '⚠️'}",
            f"总计: {result.total_requested} 只股票",
            f"成功: {len(result.successful_downloads)} 只",
            f"失败: {len(result.failed_downloads)} 只",
            f"跳过: {len(result.skipped_downloads)} 只",
            f"用时: {result.total_time:.1f} 秒"
        ]
        
        if result.failed_downloads:
            lines.append("\n失败的股票:")
            for failed in result.failed_downloads[:5]:  # 只显示前5个
                lines.append(f"  • {failed['code']} ({failed['name']})")
            if len(result.failed_downloads) > 5:
                lines.append(f"  • ... 还有 {len(result.failed_downloads) - 5} 只")
        
        return "\n".join(lines)