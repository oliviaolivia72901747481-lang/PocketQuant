"""
科技股数据验证器模块

提供科技股数据完整性检查和验证功能，确保回测前数据的可用性。

核心功能：
1. 数据文件存在性检查
2. 数据时间范围验证
3. 数据格式完整性验证
4. 缺失数据报告生成
5. 友好的错误信息系统

Requirements: 1.1, 1.2, 4.1, 4.2, 5.1
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, date
import pandas as pd
import os
import logging

from config.tech_stock_pool import get_tech_stock_pool
from core.data_feed import DataFeed

logger = logging.getLogger(__name__)


# ========== 标准化错误信息模板 (Task 5.1) ==========
class ErrorMessages:
    """
    标准化错误信息模板
    
    提供统一的错误信息格式，支持中文显示。
    
    Requirements: 1.2, 1.3, 5.1
    """
    
    # 数据缺失相关
    MISSING_DATA_FILE = "数据文件不存在"
    MISSING_DATA_FILE_DETAIL = "股票 {code}({name}) 的数据文件不存在，请下载数据"
    
    # 数据不足相关
    INSUFFICIENT_DATA = "数据时间范围不足"
    INSUFFICIENT_DATA_DETAIL = "股票 {code}({name}) 的数据范围 ({first_date} ~ {last_date}) 不满足要求 ({required_start} ~ {required_end})"
    
    # 数据损坏相关
    CORRUPTED_DATA = "数据文件损坏"
    CORRUPTED_DATA_DETAIL = "股票 {code}({name}) 的数据文件损坏: {error}"
    
    # 数据格式相关
    MISSING_COLUMNS = "数据格式错误"
    MISSING_COLUMNS_DETAIL = "股票 {code}({name}) 的数据缺少必需列: {columns}"
    
    EMPTY_DATA = "数据文件为空"
    EMPTY_DATA_DETAIL = "股票 {code}({name}) 的数据文件为空"
    
    # 下载相关
    DOWNLOAD_FAILED = "数据下载失败"
    DOWNLOAD_FAILED_DETAIL = "股票 {code}({name}) 下载失败: {error}"
    
    NETWORK_ERROR = "网络连接错误"
    NETWORK_ERROR_DETAIL = "无法连接到数据源，请检查网络连接"
    
    # 解决方案提示
    SOLUTION_DOWNLOAD = "点击'下载科技股数据'按钮自动获取所需数据"
    SOLUTION_REDOWNLOAD = "删除损坏的数据文件后重新下载"
    SOLUTION_DATA_MANAGER = "前往'数据管理'页面的'科技股数据专区'管理数据"
    SOLUTION_CHECK_NETWORK = "请检查网络连接后重试"
    SOLUTION_RETRY = "稍后重试或联系技术支持"
    
    @classmethod
    def format_missing_data(cls, code: str, name: str) -> str:
        """格式化数据缺失错误信息"""
        return cls.MISSING_DATA_FILE_DETAIL.format(code=code, name=name)
    
    @classmethod
    def format_insufficient_data(
        cls, code: str, name: str, 
        first_date: str, last_date: str,
        required_start: str, required_end: str
    ) -> str:
        """格式化数据不足错误信息"""
        return cls.INSUFFICIENT_DATA_DETAIL.format(
            code=code, name=name,
            first_date=first_date, last_date=last_date,
            required_start=required_start, required_end=required_end
        )
    
    @classmethod
    def format_corrupted_data(cls, code: str, name: str, error: str) -> str:
        """格式化数据损坏错误信息"""
        return cls.CORRUPTED_DATA_DETAIL.format(code=code, name=name, error=error)
    
    @classmethod
    def format_missing_columns(cls, code: str, name: str, columns: List[str]) -> str:
        """格式化缺少列错误信息"""
        return cls.MISSING_COLUMNS_DETAIL.format(
            code=code, name=name, columns=', '.join(columns)
        )
    
    @classmethod
    def get_solution_hints(cls, has_missing: bool, has_insufficient: bool, has_corrupted: bool) -> List[str]:
        """获取解决方案提示列表"""
        hints = []
        
        if has_missing or has_insufficient:
            hints.append(cls.SOLUTION_DOWNLOAD)
        
        if has_corrupted:
            hints.append(cls.SOLUTION_REDOWNLOAD)
        
        hints.append(cls.SOLUTION_DATA_MANAGER)
        
        return hints


@dataclass
class DataValidationResult:
    """数据验证结果"""
    is_valid: bool
    missing_files: List[str]
    insufficient_data: List[Dict[str, str]]
    corrupted_files: List[str]
    total_stocks: int
    valid_stocks: int
    error_message: Optional[str] = None
    solution_hint: Optional[str] = None


@dataclass
class StockDataStatus:
    """单只股票数据状态"""
    code: str
    name: str
    has_file: bool
    file_path: Optional[str]
    first_date: Optional[str]
    last_date: Optional[str]
    record_count: int
    is_sufficient: bool
    error_message: Optional[str] = None


class TechDataValidator:
    """
    科技股数据验证器
    
    负责检查科技股池中所有股票的数据完整性，包括：
    - 数据文件是否存在
    - 数据时间范围是否足够
    - 数据格式是否正确
    - 生成详细的验证报告
    
    Requirements: 1.1, 1.2, 4.1, 4.2
    """
    
    def __init__(self, data_feed: Optional[DataFeed] = None):
        """
        初始化数据验证器
        
        Args:
            data_feed: 数据获取模块实例
        """
        self.data_feed = data_feed
        self.tech_stock_pool = get_tech_stock_pool()
    
    def validate_tech_stock_data(
        self, 
        stock_codes: Optional[List[str]] = None,
        required_start_date: Optional[str] = None,
        required_end_date: Optional[str] = None
    ) -> DataValidationResult:
        """
        验证科技股数据完整性
        
        Args:
            stock_codes: 要验证的股票代码列表，None时验证整个科技股池
            required_start_date: 要求的数据开始日期 (YYYY-MM-DD)
            required_end_date: 要求的数据结束日期 (YYYY-MM-DD)
        
        Returns:
            数据验证结果
            
        Requirements: 1.1, 4.1
        """
        # 使用科技股池中的所有股票（如果未指定）
        if stock_codes is None:
            stock_codes = self.tech_stock_pool.get_all_codes()
        
        logger.info(f"开始验证科技股数据: {len(stock_codes)} 只股票")
        
        missing_files = []
        insufficient_data = []
        corrupted_files = []
        valid_count = 0
        
        for code in stock_codes:
            try:
                status = self.check_single_stock_data(
                    code, 
                    required_start_date, 
                    required_end_date
                )
                
                if not status.has_file:
                    missing_files.append(code)
                elif status.error_message:
                    corrupted_files.append(code)
                elif not status.is_sufficient:
                    stock_name = self.tech_stock_pool.get_stock_name(code)
                    insufficient_data.append({
                        "code": code,
                        "name": stock_name,
                        "first_date": status.first_date or "N/A",
                        "last_date": status.last_date or "N/A",
                        "required_start": required_start_date or "N/A",
                        "required_end": required_end_date or "N/A"
                    })
                else:
                    valid_count += 1
                    
            except Exception as e:
                logger.error(f"验证股票 {code} 数据时出错: {e}")
                corrupted_files.append(code)
        
        # 判断整体验证结果
        is_valid = (len(missing_files) == 0 and 
                   len(insufficient_data) == 0 and 
                   len(corrupted_files) == 0)
        
        # 生成错误信息和解决方案
        error_message, solution_hint = self._generate_error_message(
            missing_files, insufficient_data, corrupted_files
        )
        
        result = DataValidationResult(
            is_valid=is_valid,
            missing_files=missing_files,
            insufficient_data=insufficient_data,
            corrupted_files=corrupted_files,
            total_stocks=len(stock_codes),
            valid_stocks=valid_count,
            error_message=error_message,
            solution_hint=solution_hint
        )
        
        logger.info(f"数据验证完成: {valid_count}/{len(stock_codes)} 只股票数据有效")
        return result
    
    def check_single_stock_data(
        self,
        code: str,
        required_start_date: Optional[str] = None,
        required_end_date: Optional[str] = None
    ) -> StockDataStatus:
        """
        检查单只股票的数据状态
        
        Args:
            code: 股票代码
            required_start_date: 要求的数据开始日期
            required_end_date: 要求的数据结束日期
        
        Returns:
            股票数据状态
            
        Requirements: 1.1, 4.2
        """
        stock_name = self.tech_stock_pool.get_stock_name(code)
        
        # 检查数据文件是否存在
        if not self.data_feed:
            return StockDataStatus(
                code=code,
                name=stock_name,
                has_file=False,
                file_path=None,
                first_date=None,
                last_date=None,
                record_count=0,
                is_sufficient=False,
                error_message="DataFeed 未初始化"
            )
        
        file_path = os.path.join(self.data_feed.processed_path, f"{code}.csv")
        
        if not os.path.exists(file_path):
            return StockDataStatus(
                code=code,
                name=stock_name,
                has_file=False,
                file_path=file_path,
                first_date=None,
                last_date=None,
                record_count=0,
                is_sufficient=False
            )
        
        # 尝试加载和验证数据
        try:
            df = pd.read_csv(file_path)
            
            # 检查必需的列
            required_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                return StockDataStatus(
                    code=code,
                    name=stock_name,
                    has_file=True,
                    file_path=file_path,
                    first_date=None,
                    last_date=None,
                    record_count=len(df),
                    is_sufficient=False,
                    error_message=f"缺少必需列: {missing_columns}"
                )
            
            if df.empty:
                return StockDataStatus(
                    code=code,
                    name=stock_name,
                    has_file=True,
                    file_path=file_path,
                    first_date=None,
                    last_date=None,
                    record_count=0,
                    is_sufficient=False,
                    error_message="数据文件为空"
                )
            
            # 获取数据时间范围
            df['date'] = pd.to_datetime(df['date'])
            first_date = df['date'].min().strftime('%Y-%m-%d')
            last_date = df['date'].max().strftime('%Y-%m-%d')
            
            # 检查时间范围是否足够
            is_sufficient = self.check_data_time_range(
                first_date, last_date, required_start_date, required_end_date
            )
            
            return StockDataStatus(
                code=code,
                name=stock_name,
                has_file=True,
                file_path=file_path,
                first_date=first_date,
                last_date=last_date,
                record_count=len(df),
                is_sufficient=is_sufficient
            )
            
        except Exception as e:
            return StockDataStatus(
                code=code,
                name=stock_name,
                has_file=True,
                file_path=file_path,
                first_date=None,
                last_date=None,
                record_count=0,
                is_sufficient=False,
                error_message=f"数据文件损坏: {str(e)}"
            )
    
    def check_data_time_range(
        self,
        data_start: str,
        data_end: str,
        required_start: Optional[str] = None,
        required_end: Optional[str] = None
    ) -> bool:
        """
        检查数据时间范围是否足够
        
        Args:
            data_start: 数据开始日期
            data_end: 数据结束日期
            required_start: 要求的开始日期
            required_end: 要求的结束日期
        
        Returns:
            时间范围是否足够
            
        Requirements: 4.2
        """
        try:
            data_start_dt = datetime.strptime(data_start, '%Y-%m-%d')
            data_end_dt = datetime.strptime(data_end, '%Y-%m-%d')
            
            # 如果没有指定要求，则认为足够
            if not required_start and not required_end:
                return True
            
            if required_start:
                required_start_dt = datetime.strptime(required_start, '%Y-%m-%d')
                if data_start_dt > required_start_dt:
                    return False
            
            if required_end:
                required_end_dt = datetime.strptime(required_end, '%Y-%m-%d')
                if data_end_dt < required_end_dt:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"检查时间范围时出错: {e}")
            return False
    
    def get_missing_data_report(self, stock_codes: List[str]) -> Dict[str, List[str]]:
        """
        生成缺失数据报告
        
        Args:
            stock_codes: 股票代码列表
        
        Returns:
            缺失数据报告 {类型: [股票代码列表]}
            
        Requirements: 1.2
        """
        validation_result = self.validate_tech_stock_data(stock_codes)
        
        report = {
            "missing_files": validation_result.missing_files,
            "insufficient_data": [item["code"] for item in validation_result.insufficient_data],
            "corrupted_files": validation_result.corrupted_files,
            "valid_stocks": []
        }
        
        # 计算有效股票
        all_problem_codes = set(
            report["missing_files"] + 
            report["insufficient_data"] + 
            report["corrupted_files"]
        )
        
        report["valid_stocks"] = [
            code for code in stock_codes 
            if code not in all_problem_codes
        ]
        
        return report
    
    def get_tech_stock_pool_status(self) -> Dict[str, Any]:
        """
        获取整个科技股池的数据状态概览
        
        Returns:
            科技股池数据状态概览
            
        Requirements: 3.1, 3.3
        """
        all_codes = self.tech_stock_pool.get_all_codes()
        validation_result = self.validate_tech_stock_data(all_codes)
        
        # 按行业统计
        sector_stats = {}
        for sector in self.tech_stock_pool.get_sectors():
            sector_codes = self.tech_stock_pool.get_codes_by_sector(sector)
            sector_validation = self.validate_tech_stock_data(sector_codes)
            
            sector_stats[sector] = {
                "total": len(sector_codes),
                "valid": sector_validation.valid_stocks,
                "missing": len(sector_validation.missing_files),
                "insufficient": len(sector_validation.insufficient_data),
                "corrupted": len(sector_validation.corrupted_files)
            }
        
        return {
            "overall": {
                "total_stocks": validation_result.total_stocks,
                "valid_stocks": validation_result.valid_stocks,
                "missing_files": len(validation_result.missing_files),
                "insufficient_data": len(validation_result.insufficient_data),
                "corrupted_files": len(validation_result.corrupted_files),
                "completion_rate": validation_result.valid_stocks / validation_result.total_stocks if validation_result.total_stocks > 0 else 0
            },
            "by_sector": sector_stats,
            "problem_stocks": {
                "missing_files": validation_result.missing_files,
                "insufficient_data": validation_result.insufficient_data,
                "corrupted_files": validation_result.corrupted_files
            }
        }
    
    def _generate_error_message(
        self,
        missing_files: List[str],
        insufficient_data: List[Dict[str, str]],
        corrupted_files: List[str]
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        生成错误信息和解决方案提示
        
        使用标准化的错误信息模板，提供友好的中文提示。
        
        Args:
            missing_files: 缺失文件的股票代码列表
            insufficient_data: 数据不足的股票信息列表
            corrupted_files: 损坏文件的股票代码列表
        
        Returns:
            (错误信息, 解决方案提示)
            
        Requirements: 1.2, 1.3, 5.1
        """
        if not missing_files and not insufficient_data and not corrupted_files:
            return None, None
        
        error_parts = []
        
        # 缺失数据文件
        if missing_files:
            error_parts.append(f"📁 **{ErrorMessages.MISSING_DATA_FILE}** ({len(missing_files)} 只)")
            for code in missing_files[:5]:  # 只显示前5个
                name = self.tech_stock_pool.get_stock_name(code)
                error_parts.append(f"   • {code} ({name})")
            if len(missing_files) > 5:
                error_parts.append(f"   • ... 还有 {len(missing_files) - 5} 只")
        
        # 数据时间范围不足
        if insufficient_data:
            error_parts.append(f"📅 **{ErrorMessages.INSUFFICIENT_DATA}** ({len(insufficient_data)} 只)")
            for item in insufficient_data[:5]:  # 只显示前5个
                error_parts.append(
                    f"   • {item['code']} ({item['name']}): "
                    f"{item['first_date']} ~ {item['last_date']}"
                )
            if len(insufficient_data) > 5:
                error_parts.append(f"   • ... 还有 {len(insufficient_data) - 5} 只")
        
        # 数据文件损坏
        if corrupted_files:
            error_parts.append(f"⚠️ **{ErrorMessages.CORRUPTED_DATA}** ({len(corrupted_files)} 只)")
            for code in corrupted_files[:5]:  # 只显示前5个
                name = self.tech_stock_pool.get_stock_name(code)
                error_parts.append(f"   • {code} ({name})")
            if len(corrupted_files) > 5:
                error_parts.append(f"   • ... 还有 {len(corrupted_files) - 5} 只")
        
        error_message = "🔬 **科技股数据验证失败**\n\n" + "\n".join(error_parts)
        
        # 生成解决方案提示
        solution_hints = ErrorMessages.get_solution_hints(
            has_missing=len(missing_files) > 0,
            has_insufficient=len(insufficient_data) > 0,
            has_corrupted=len(corrupted_files) > 0
        )
        
        solution_hint = "💡 **建议解决方案**:\n" + "\n".join(f"• {hint}" for hint in solution_hints)
        
        return error_message, solution_hint
    
    def get_friendly_error_summary(self, validation_result: 'DataValidationResult') -> Dict[str, Any]:
        """
        获取友好的错误摘要信息
        
        用于UI显示，提供结构化的错误信息。
        
        Args:
            validation_result: 数据验证结果
        
        Returns:
            友好的错误摘要字典
            
        Requirements: 5.1
        """
        if validation_result.is_valid:
            return {
                'has_error': False,
                'title': '✅ 数据验证通过',
                'summary': f'所有 {validation_result.total_stocks} 只科技股数据完整',
                'details': [],
                'solutions': []
            }
        
        # 统计问题数量
        total_issues = (
            len(validation_result.missing_files) + 
            len(validation_result.insufficient_data) + 
            len(validation_result.corrupted_files)
        )
        
        details = []
        
        if validation_result.missing_files:
            details.append({
                'type': 'missing',
                'icon': '📁',
                'title': ErrorMessages.MISSING_DATA_FILE,
                'count': len(validation_result.missing_files),
                'items': [
                    f"{code} ({self.tech_stock_pool.get_stock_name(code)})"
                    for code in validation_result.missing_files
                ]
            })
        
        if validation_result.insufficient_data:
            details.append({
                'type': 'insufficient',
                'icon': '📅',
                'title': ErrorMessages.INSUFFICIENT_DATA,
                'count': len(validation_result.insufficient_data),
                'items': [
                    f"{item['code']} ({item['name']}): {item['first_date']} ~ {item['last_date']}"
                    for item in validation_result.insufficient_data
                ]
            })
        
        if validation_result.corrupted_files:
            details.append({
                'type': 'corrupted',
                'icon': '⚠️',
                'title': ErrorMessages.CORRUPTED_DATA,
                'count': len(validation_result.corrupted_files),
                'items': [
                    f"{code} ({self.tech_stock_pool.get_stock_name(code)})"
                    for code in validation_result.corrupted_files
                ]
            })
        
        solutions = ErrorMessages.get_solution_hints(
            has_missing=len(validation_result.missing_files) > 0,
            has_insufficient=len(validation_result.insufficient_data) > 0,
            has_corrupted=len(validation_result.corrupted_files) > 0
        )
        
        return {
            'has_error': True,
            'title': f'❌ 数据验证失败 ({total_issues} 个问题)',
            'summary': f'{validation_result.valid_stocks}/{validation_result.total_stocks} 只股票数据有效',
            'details': details,
            'solutions': solutions
        }