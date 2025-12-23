"""
科技股模块性能监控器

提供性能监控和统计功能：
1. 实时性能指标
2. 缓存命中率统计
3. 操作耗时分析
4. 内存使用监控

Requirements: 12.2 性能优化 - 性能监控
"""

import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import pandas as pd

from core.tech_stock.performance_optimizer import get_performance_stats

logger = logging.getLogger(__name__)


@dataclass
class PerformanceReport:
    """性能报告"""
    timestamp: datetime
    cache_hit_rate: float
    avg_operation_time: float
    total_operations: int
    cache_sizes: Dict[str, int]
    recommendations: List[str]


class PerformanceMonitor:
    """
    性能监控器
    
    监控科技股模块的性能指标，提供优化建议
    """
    
    def __init__(self):
        self.reports: List[PerformanceReport] = []
        self.max_reports = 100  # 保留最近100个报告
    
    def generate_report(self) -> PerformanceReport:
        """
        生成性能报告
        
        Returns:
            性能报告对象
        """
        stats = get_performance_stats()
        
        if not stats:
            return PerformanceReport(
                timestamp=datetime.now(),
                cache_hit_rate=0.0,
                avg_operation_time=0.0,
                total_operations=0,
                cache_sizes={},
                recommendations=["暂无性能数据"]
            )
        
        # 生成优化建议
        recommendations = self._generate_recommendations(stats)
        
        report = PerformanceReport(
            timestamp=datetime.now(),
            cache_hit_rate=stats.get('cache_hit_rate', 0.0),
            avg_operation_time=stats.get('avg_operation_time', 0.0),
            total_operations=stats.get('total_operations', 0),
            cache_sizes=stats.get('cache_sizes', {}),
            recommendations=recommendations
        )
        
        # 保存报告
        self.reports.append(report)
        if len(self.reports) > self.max_reports:
            self.reports = self.reports[-self.max_reports:]
        
        return report
    
    def _generate_recommendations(self, stats: Dict[str, Any]) -> List[str]:
        """
        生成性能优化建议
        
        Args:
            stats: 性能统计数据
            
        Returns:
            优化建议列表
        """
        recommendations = []
        
        cache_hit_rate = stats.get('cache_hit_rate', 0.0)
        avg_time = stats.get('avg_operation_time', 0.0)
        cache_sizes = stats.get('cache_sizes', {})
        
        # 缓存命中率建议
        if cache_hit_rate < 0.5:
            recommendations.append("🔄 缓存命中率较低，建议增加缓存时间或预加载数据")
        elif cache_hit_rate > 0.8:
            recommendations.append("✅ 缓存命中率良好")
        
        # 操作耗时建议
        if avg_time > 0.1:
            recommendations.append("⏱️ 平均操作耗时较长，建议优化数据加载或计算逻辑")
        elif avg_time < 0.05:
            recommendations.append("⚡ 操作响应速度优秀")
        
        # 缓存大小建议
        total_cache_items = sum(cache_sizes.values())
        if total_cache_items > 1000:
            recommendations.append("💾 缓存项目较多，建议定期清理过期数据")
        elif total_cache_items < 10:
            recommendations.append("📈 缓存利用率较低，可以增加预加载")
        
        # 具体缓存建议
        stock_data_count = cache_sizes.get('stock_data', 0)
        if stock_data_count > 100:
            recommendations.append("📊 股票数据缓存较多，建议设置合理的TTL")
        
        if not recommendations:
            recommendations.append("✨ 性能表现良好，无需特别优化")
        
        return recommendations
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """
        获取性能汇总
        
        Returns:
            性能汇总字典
        """
        if not self.reports:
            return {
                "status": "no_data",
                "message": "暂无性能数据"
            }
        
        latest_report = self.reports[-1]
        
        # 计算趋势（与前一个报告比较）
        trend = {}
        if len(self.reports) >= 2:
            prev_report = self.reports[-2]
            
            hit_rate_change = latest_report.cache_hit_rate - prev_report.cache_hit_rate
            time_change = latest_report.avg_operation_time - prev_report.avg_operation_time
            
            trend = {
                "cache_hit_rate_trend": "up" if hit_rate_change > 0.05 else "down" if hit_rate_change < -0.05 else "stable",
                "operation_time_trend": "up" if time_change > 0.01 else "down" if time_change < -0.01 else "stable"
            }
        
        return {
            "status": "ok",
            "latest_report": latest_report,
            "trend": trend,
            "total_reports": len(self.reports)
        }
    
    def get_performance_history(self, hours: int = 24) -> List[PerformanceReport]:
        """
        获取性能历史记录
        
        Args:
            hours: 获取最近几小时的记录
            
        Returns:
            性能报告列表
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [r for r in self.reports if r.timestamp >= cutoff_time]
    
    def format_for_display(self) -> pd.DataFrame:
        """
        格式化性能数据用于显示
        
        Returns:
            格式化的DataFrame
        """
        if not self.reports:
            return pd.DataFrame()
        
        data = []
        for report in self.reports[-10:]:  # 最近10个报告
            data.append({
                "时间": report.timestamp.strftime("%H:%M:%S"),
                "缓存命中率": f"{report.cache_hit_rate:.1%}",
                "平均耗时(ms)": f"{report.avg_operation_time * 1000:.1f}",
                "操作次数": report.total_operations,
                "股票数据缓存": report.cache_sizes.get('stock_data', 0),
                "指标缓存": report.cache_sizes.get('indicators', 0),
                "批量缓存": report.cache_sizes.get('batch_data', 0)
            })
        
        return pd.DataFrame(data)
    
    def clear_history(self) -> None:
        """清空历史记录"""
        self.reports.clear()
        logger.info("性能监控历史记录已清空")


# 全局监控器实例
_performance_monitor = PerformanceMonitor()


def get_performance_monitor() -> PerformanceMonitor:
    """获取性能监控器实例"""
    return _performance_monitor


def generate_performance_report() -> PerformanceReport:
    """生成性能报告"""
    return _performance_monitor.generate_report()


def get_performance_summary() -> Dict[str, Any]:
    """获取性能汇总"""
    return _performance_monitor.get_performance_summary()


def format_performance_for_display() -> pd.DataFrame:
    """格式化性能数据用于显示"""
    return _performance_monitor.format_for_display()


def clear_performance_history() -> None:
    """清空性能历史"""
    _performance_monitor.clear_history()


class PerformanceWidget:
    """
    性能监控组件
    
    用于在Streamlit界面中显示性能信息
    """
    
    @staticmethod
    def render_performance_metrics():
        """渲染性能指标"""
        import streamlit as st
        
        st.subheader("⚡ 性能监控")
        
        # 生成最新报告
        report = generate_performance_report()
        
        # 显示关键指标
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "缓存命中率",
                f"{report.cache_hit_rate:.1%}",
                delta=None
            )
        
        with col2:
            st.metric(
                "平均耗时",
                f"{report.avg_operation_time * 1000:.1f}ms",
                delta=None
            )
        
        with col3:
            st.metric(
                "操作次数",
                report.total_operations,
                delta=None
            )
        
        with col4:
            total_cache = sum(report.cache_sizes.values())
            st.metric(
                "缓存项目",
                total_cache,
                delta=None
            )
        
        # 显示优化建议
        if report.recommendations:
            st.markdown("**优化建议:**")
            for rec in report.recommendations:
                st.markdown(f"- {rec}")
        
        # 显示性能历史
        with st.expander("查看性能历史"):
            df = format_performance_for_display()
            if not df.empty:
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("暂无性能历史数据")
        
        # 清理按钮
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ 清空缓存"):
                from core.tech_stock.performance_optimizer import clear_all_caches
                clear_all_caches()
                st.success("缓存已清空")
        
        with col2:
            if st.button("📊 清空历史"):
                clear_performance_history()
                st.success("性能历史已清空")
    
    @staticmethod
    def render_compact_metrics():
        """渲染紧凑的性能指标"""
        import streamlit as st
        
        summary = get_performance_summary()
        
        if summary["status"] == "no_data":
            st.caption("⚡ 性能监控: 暂无数据")
            return
        
        report = summary["latest_report"]
        
        # 紧凑显示
        st.caption(
            f"⚡ 性能: 缓存命中率 {report.cache_hit_rate:.1%} | "
            f"平均耗时 {report.avg_operation_time * 1000:.1f}ms | "
            f"缓存项目 {sum(report.cache_sizes.values())}"
        )