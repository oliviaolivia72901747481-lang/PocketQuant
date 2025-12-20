"""
MiniQuant-Lite 财报窗口期检测模块

财报披露日前后 N 天禁止开仓，避免财报黑天鹅。
这是小资金的保命符，必须保留的硬风控功能。

Requirements: 10.1, 10.2
"""

from datetime import datetime, date, timedelta
from typing import Optional, Tuple, List, Dict
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ReportInfo:
    """财报信息"""
    code: str                    # 股票代码
    report_type: str             # 报告类型（一季报/中报/三季报/年报）
    report_period: str           # 报告期（如 2024-03-31）
    disclosure_date: date        # 披露日期
    days_to_disclosure: int      # 距离披露日的天数（负数表示已过）


class ReportChecker:
    """
    财报窗口期检测器（硬风控）
    
    财报披露日前后 N 天禁止开仓，避免财报黑天鹅。
    这是小资金的保命符，必须保留。
    
    设计原则：
    - 宁可错过，不可做错
    - 财报窗口期内的股票一律剔除
    - 把最终决策权交给用户，系统只做硬风控
    
    Requirements: 10.1, 10.2
    """
    
    # 财报类型映射
    REPORT_TYPES = {
        '一季报': '03-31',
        '中报': '06-30', 
        '半年报': '06-30',
        '三季报': '09-30',
        '年报': '12-31'
    }
    
    def __init__(self, window_days: int = 3):
        """
        初始化财报检测器
        
        Args:
            window_days: 窗口期天数（前后各 N 天），默认 3 天
        """
        self.window_days = window_days
        self._cache: Dict[str, List[ReportInfo]] = {}  # 缓存财报信息
        self._cache_date: Optional[date] = None  # 缓存日期
    
    def check_report_window(
        self, 
        code: str, 
        check_date: Optional[date] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        检查是否处于财报披露窗口期
        
        Args:
            code: 股票代码（6位数字，如 '000001'）
            check_date: 检查日期，默认为今天
        
        Returns:
            (是否在窗口期, 警告信息)
            - 如果在窗口期内，返回 (True, "⚠️ 财报窗口期：xxx将于 YYYY-MM-DD 披露")
            - 如果不在窗口期，返回 (False, None)
            - 如果获取失败，返回 (False, None) 并记录日志
        
        Requirements: 10.1, 10.2
        """
        if check_date is None:
            check_date = date.today()
        
        try:
            # 获取财报披露日期
            report_dates = self._get_report_dates(code)
            
            if not report_dates:
                logger.debug(f"股票 {code} 无财报披露日期信息")
                return False, None
            
            # 检查是否在任一财报的窗口期内
            for report_info in report_dates:
                days_diff = (report_info.disclosure_date - check_date).days
                
                # 在窗口期内：披露日前后 window_days 天
                if abs(days_diff) <= self.window_days:
                    if days_diff > 0:
                        # 披露日在未来
                        warning = (
                            f"⚠️ 财报窗口期：{report_info.report_type}将于 "
                            f"{report_info.disclosure_date.strftime('%Y-%m-%d')} 披露"
                            f"（{days_diff}天后）"
                        )
                    elif days_diff < 0:
                        # 披露日已过
                        warning = (
                            f"⚠️ 财报窗口期：{report_info.report_type}已于 "
                            f"{report_info.disclosure_date.strftime('%Y-%m-%d')} 披露"
                            f"（{abs(days_diff)}天前）"
                        )
                    else:
                        # 今天就是披露日
                        warning = (
                            f"⚠️ 财报窗口期：{report_info.report_type}今日披露"
                        )
                    
                    logger.info(f"股票 {code} 处于财报窗口期: {warning}")
                    return True, warning
            
            return False, None
            
        except Exception as e:
            logger.warning(f"获取股票 {code} 财报日期失败: {e}")
            # 获取失败时不阻止交易，但记录日志
            return False, None
    
    def _get_report_dates(self, code: str) -> List[ReportInfo]:
        """
        获取股票的财报披露日期
        
        使用 AkShare 获取财报预约披露日期
        
        Args:
            code: 股票代码
        
        Returns:
            财报信息列表
        """
        # 检查缓存是否有效（当天有效）
        today = date.today()
        if self._cache_date == today and code in self._cache:
            return self._cache[code]
        
        # 清除过期缓存
        if self._cache_date != today:
            self._cache.clear()
            self._cache_date = today
        
        try:
            import akshare as ak
            
            report_infos: List[ReportInfo] = []
            
            # 尝试获取业绩预告/快报日期
            try:
                # 获取最新一期的业绩预告
                df = ak.stock_yjyg_em(date="")
                if df is not None and not df.empty:
                    # 筛选该股票的记录
                    stock_df = df[df['股票代码'] == code]
                    if not stock_df.empty:
                        for _, row in stock_df.iterrows():
                            disclosure_date_str = row.get('公告日期', '')
                            if disclosure_date_str:
                                try:
                                    disclosure_date = self._parse_date(disclosure_date_str)
                                    if disclosure_date:
                                        report_infos.append(ReportInfo(
                                            code=code,
                                            report_type='业绩预告',
                                            report_period=str(row.get('报告期', '')),
                                            disclosure_date=disclosure_date,
                                            days_to_disclosure=(disclosure_date - today).days
                                        ))
                                except Exception:
                                    pass
            except Exception as e:
                logger.debug(f"获取业绩预告失败: {code}, {e}")
            
            # 尝试获取财报预约披露日期
            try:
                # 获取财报预约披露时间表
                # 注意：AkShare 的接口可能会变化，需要适配
                df = ak.stock_report_disclosure(symbol=code)
                if df is not None and not df.empty:
                    for _, row in df.iterrows():
                        disclosure_date_str = row.get('首次预约时间', '') or row.get('披露日期', '')
                        report_type = row.get('报告类型', '财报')
                        
                        if disclosure_date_str:
                            try:
                                disclosure_date = self._parse_date(disclosure_date_str)
                                if disclosure_date:
                                    report_infos.append(ReportInfo(
                                        code=code,
                                        report_type=report_type,
                                        report_period=str(row.get('报告期', '')),
                                        disclosure_date=disclosure_date,
                                        days_to_disclosure=(disclosure_date - today).days
                                    ))
                            except Exception:
                                pass
            except Exception as e:
                logger.debug(f"获取财报预约披露日期失败: {code}, {e}")
            
            # 如果没有获取到具体日期，使用估算的财报窗口期
            if not report_infos:
                report_infos = self._estimate_report_windows(code, today)
            
            # 缓存结果
            self._cache[code] = report_infos
            
            return report_infos
            
        except Exception as e:
            logger.warning(f"获取财报日期失败: {code}, 错误: {e}")
            return []
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        """
        解析日期字符串
        
        支持多种格式：
        - YYYY-MM-DD
        - YYYYMMDD
        - YYYY/MM/DD
        
        Args:
            date_str: 日期字符串
        
        Returns:
            date 对象或 None
        """
        if not date_str:
            return None
        
        date_str = str(date_str).strip()
        
        formats = ['%Y-%m-%d', '%Y%m%d', '%Y/%m/%d']
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        return None
    
    def _estimate_report_windows(
        self, 
        code: str, 
        check_date: date
    ) -> List[ReportInfo]:
        """
        估算财报窗口期
        
        当无法获取具体披露日期时，使用法定披露截止日期估算
        
        A股财报披露规则：
        - 一季报：4月1日-4月30日
        - 中报：7月1日-8月31日
        - 三季报：10月1日-10月31日
        - 年报：次年1月1日-4月30日
        
        Args:
            code: 股票代码
            check_date: 检查日期
        
        Returns:
            估算的财报窗口期列表
        """
        year = check_date.year
        report_infos: List[ReportInfo] = []
        
        # 定义各季度财报的披露窗口（使用窗口中间日期作为估算披露日）
        report_windows = [
            # (报告类型, 报告期, 估算披露日)
            ('一季报', f'{year}-03-31', date(year, 4, 15)),
            ('中报', f'{year}-06-30', date(year, 8, 15)),
            ('三季报', f'{year}-09-30', date(year, 10, 15)),
            ('年报', f'{year-1}-12-31', date(year, 4, 1)),
        ]
        
        for report_type, report_period, estimated_date in report_windows:
            days_diff = (estimated_date - check_date).days
            
            # 只返回未来 30 天内或过去 7 天内的财报窗口
            if -7 <= days_diff <= 30:
                report_infos.append(ReportInfo(
                    code=code,
                    report_type=f'{report_type}（估算）',
                    report_period=report_period,
                    disclosure_date=estimated_date,
                    days_to_disclosure=days_diff
                ))
        
        return report_infos
    
    def get_upcoming_reports(
        self, 
        codes: List[str], 
        days_ahead: int = 7
    ) -> List[ReportInfo]:
        """
        获取即将披露财报的股票列表
        
        Args:
            codes: 股票代码列表
            days_ahead: 提前天数，默认 7 天
        
        Returns:
            即将披露财报的股票信息列表
        """
        today = date.today()
        upcoming: List[ReportInfo] = []
        
        for code in codes:
            report_dates = self._get_report_dates(code)
            for report_info in report_dates:
                days_diff = (report_info.disclosure_date - today).days
                if 0 <= days_diff <= days_ahead:
                    upcoming.append(report_info)
        
        # 按披露日期排序
        upcoming.sort(key=lambda x: x.disclosure_date)
        
        return upcoming
    
    def clear_cache(self) -> None:
        """清除缓存"""
        self._cache.clear()
        self._cache_date = None
        logger.debug("财报信息缓存已清除")


# 便捷函数
def check_report_window(
    code: str, 
    window_days: int = 3
) -> Tuple[bool, Optional[str]]:
    """
    检查股票是否处于财报窗口期（便捷函数）
    
    Args:
        code: 股票代码
        window_days: 窗口期天数
    
    Returns:
        (是否在窗口期, 警告信息)
    """
    checker = ReportChecker(window_days=window_days)
    return checker.check_report_window(code)
