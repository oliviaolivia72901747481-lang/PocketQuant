"""
数据质量实时监控模块

提供数据质量的实时监控功能，包括：
- 数据完整性实时监控
- 数据异常自动检测
- 数据质量报告生成
- 实时告警和通知

Requirements: 7.2, 7.5
风险缓解措施: 实现数据质量实时监控
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from datetime import datetime, timedelta
import logging
import threading
import time
import json
import os
import pandas as pd

logger = logging.getLogger(__name__)


class DataQualityAlertLevel(Enum):
    """数据质量告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MonitoringStatus(Enum):
    """监控状态"""
    RUNNING = "running"
    STOPPED = "stopped"
    PAUSED = "paused"
    ERROR = "error"


class DataQualityDimension(Enum):
    """数据质量维度"""
    COMPLETENESS = "completeness"      # 完整性
    ACCURACY = "accuracy"              # 准确性
    CONSISTENCY = "consistency"        # 一致性
    TIMELINESS = "timeliness"          # 时效性
    VALIDITY = "validity"              # 有效性


@dataclass
class DataQualityAlert:
    """数据质量告警"""
    alert_id: str
    level: DataQualityAlertLevel
    dimension: DataQualityDimension
    title: str
    message: str
    affected_records: int = 0
    affected_fields: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'alert_id': self.alert_id,
            'level': self.level.value,
            'dimension': self.dimension.value,
            'title': self.title,
            'message': self.message,
            'affected_records': self.affected_records,
            'affected_fields': self.affected_fields,
            'timestamp': self.timestamp.isoformat(),
            'resolved': self.resolved,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None
        }


@dataclass
class DataQualitySnapshot:
    """数据质量快照"""
    timestamp: datetime
    total_records: int
    completeness_score: float
    accuracy_score: float
    consistency_score: float
    timeliness_score: float
    validity_score: float
    overall_score: float
    alerts_count: int
    issues: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'total_records': self.total_records,
            'completeness_score': self.completeness_score,
            'accuracy_score': self.accuracy_score,
            'consistency_score': self.consistency_score,
            'timeliness_score': self.timeliness_score,
            'validity_score': self.validity_score,
            'overall_score': self.overall_score,
            'alerts_count': self.alerts_count,
            'issues': self.issues
        }


@dataclass
class RealtimeMonitorConfig:
    """实时监控配置"""
    check_interval_seconds: int = 300  # 检查间隔（秒）
    completeness_threshold: float = 95.0  # 完整性阈值
    accuracy_threshold: float = 99.0  # 准确性阈值
    consistency_threshold: float = 98.0  # 一致性阈值
    timeliness_threshold_hours: int = 24  # 时效性阈值（小时）
    validity_threshold: float = 95.0  # 有效性阈值
    alert_cooldown_minutes: int = 30  # 告警冷却时间（分钟）
    max_history_snapshots: int = 1000  # 最大历史快照数
    enable_auto_alert: bool = True  # 启用自动告警
    alert_channels: List[str] = field(default_factory=lambda: ["log", "file"])
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'check_interval_seconds': self.check_interval_seconds,
            'completeness_threshold': self.completeness_threshold,
            'accuracy_threshold': self.accuracy_threshold,
            'consistency_threshold': self.consistency_threshold,
            'timeliness_threshold_hours': self.timeliness_threshold_hours,
            'validity_threshold': self.validity_threshold,
            'alert_cooldown_minutes': self.alert_cooldown_minutes,
            'max_history_snapshots': self.max_history_snapshots,
            'enable_auto_alert': self.enable_auto_alert,
            'alert_channels': self.alert_channels
        }


class RealtimeDataQualityMonitor:
    """
    数据质量实时监控器
    
    提供数据质量的实时监控功能，包括：
    - 数据完整性实时监控
    - 数据异常自动检测
    - 数据质量报告生成
    - 实时告警和通知
    
    Requirements: 7.2, 7.5
    """
    
    # 必需字段定义
    REQUIRED_FIELDS = ['code', 'name']
    
    # 关键数值字段
    KEY_NUMERIC_FIELDS = [
        'price', 'close', 'total_market_cap', 'float_market_cap',
        'pe_ratio', 'pb_ratio', 'roe', 'turnover_rate'
    ]
    
    # 数值字段有效范围
    FIELD_RANGES = {
        'price': {'min': 0.01, 'max': 10000},
        'close': {'min': 0.01, 'max': 10000},
        'change_pct': {'min': -20, 'max': 20},
        'turnover_rate': {'min': 0, 'max': 100},
        'pe_ratio': {'min': -10000, 'max': 100000},
        'pb_ratio': {'min': 0, 'max': 1000},
        'total_market_cap': {'min': 0, 'max': 1e15},
        'float_market_cap': {'min': 0, 'max': 1e15},
        'roe': {'min': -500, 'max': 500},
    }
    
    def __init__(self, config: Optional[RealtimeMonitorConfig] = None):
        """
        初始化实时数据质量监控器
        
        Args:
            config: 监控配置
        """
        self.config = config or RealtimeMonitorConfig()
        self._status = MonitoringStatus.STOPPED
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # 数据存储
        self._alerts: List[DataQualityAlert] = []
        self._snapshots: List[DataQualitySnapshot] = []
        self._last_alert_times: Dict[str, datetime] = {}
        self._alert_counter = 0
        
        # 回调函数
        self._alert_handlers: List[Callable[[DataQualityAlert], None]] = []
        self._snapshot_handlers: List[Callable[[DataQualitySnapshot], None]] = []
        
        # 数据源
        self._data_provider: Optional[Callable[[], pd.DataFrame]] = None
        
        # 持久化路径
        self._alerts_file = "data/data_quality_alerts.json"
        self._snapshots_file = "data/data_quality_snapshots.json"
        
        # 加载历史数据
        self._load_history()
    
    @property
    def status(self) -> MonitoringStatus:
        """获取监控状态"""
        return self._status
    
    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._status == MonitoringStatus.RUNNING
    
    def set_data_provider(self, provider: Callable[[], pd.DataFrame]):
        """
        设置数据提供者
        
        Args:
            provider: 返回DataFrame的可调用对象
        """
        self._data_provider = provider
    
    def add_alert_handler(self, handler: Callable[[DataQualityAlert], None]):
        """添加告警处理器"""
        self._alert_handlers.append(handler)
    
    def add_snapshot_handler(self, handler: Callable[[DataQualitySnapshot], None]):
        """添加快照处理器"""
        self._snapshot_handlers.append(handler)
    
    def start(self):
        """启动实时监控"""
        if self._status == MonitoringStatus.RUNNING:
            logger.warning("监控已在运行中")
            return
        
        self._stop_event.clear()
        self._status = MonitoringStatus.RUNNING
        
        self._monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True,
            name="DataQualityMonitor"
        )
        self._monitor_thread.start()
        
        logger.info(f"数据质量实时监控已启动，检查间隔: {self.config.check_interval_seconds}秒")
    
    def stop(self):
        """停止实时监控"""
        if self._status != MonitoringStatus.RUNNING:
            return
        
        self._stop_event.set()
        self._status = MonitoringStatus.STOPPED
        
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        
        # 保存历史数据
        self._save_history()
        
        logger.info("数据质量实时监控已停止")
    
    def pause(self):
        """暂停监控"""
        if self._status == MonitoringStatus.RUNNING:
            self._status = MonitoringStatus.PAUSED
            logger.info("数据质量监控已暂停")
    
    def resume(self):
        """恢复监控"""
        if self._status == MonitoringStatus.PAUSED:
            self._status = MonitoringStatus.RUNNING
            logger.info("数据质量监控已恢复")
    
    def _monitoring_loop(self):
        """监控循环"""
        while not self._stop_event.is_set():
            if self._status == MonitoringStatus.RUNNING:
                try:
                    self._perform_quality_check()
                except Exception as e:
                    logger.error(f"数据质量检查失败: {e}")
                    self._status = MonitoringStatus.ERROR
            
            # 等待下一次检查
            self._stop_event.wait(self.config.check_interval_seconds)
    
    def _perform_quality_check(self):
        """执行数据质量检查"""
        # 获取数据
        df = self._get_data()
        if df is None or df.empty:
            logger.warning("无数据可供检查")
            return
        
        # 计算各维度质量分数
        completeness = self._check_completeness(df)
        accuracy = self._check_accuracy(df)
        consistency = self._check_consistency(df)
        timeliness = self._check_timeliness(df)
        validity = self._check_validity(df)
        
        # 计算综合分数
        overall = (
            completeness * 0.25 +
            accuracy * 0.30 +
            consistency * 0.20 +
            timeliness * 0.10 +
            validity * 0.15
        )
        
        # 创建快照
        snapshot = DataQualitySnapshot(
            timestamp=datetime.now(),
            total_records=len(df),
            completeness_score=completeness,
            accuracy_score=accuracy,
            consistency_score=consistency,
            timeliness_score=timeliness,
            validity_score=validity,
            overall_score=overall,
            alerts_count=len(self.get_active_alerts())
        )
        
        # 保存快照
        self._add_snapshot(snapshot)
        
        # 检查阈值并生成告警
        if self.config.enable_auto_alert:
            self._check_thresholds_and_alert(snapshot, df)
        
        logger.debug(
            f"数据质量检查完成: 总分={overall:.1f}, "
            f"完整性={completeness:.1f}, 准确性={accuracy:.1f}, "
            f"一致性={consistency:.1f}, 时效性={timeliness:.1f}, "
            f"有效性={validity:.1f}"
        )
    
    def _get_data(self) -> Optional[pd.DataFrame]:
        """获取待检查的数据"""
        if self._data_provider:
            try:
                return self._data_provider()
            except Exception as e:
                logger.error(f"获取数据失败: {e}")
                return None
        
        # 默认从processed目录读取数据
        return self._load_processed_data()
    
    def _load_processed_data(self) -> Optional[pd.DataFrame]:
        """从processed目录加载数据"""
        processed_dir = 'data/processed'
        if not os.path.exists(processed_dir):
            return None
        
        all_data = []
        csv_files = [f for f in os.listdir(processed_dir) if f.endswith('.csv')]
        
        for csv_file in csv_files[:100]:  # 限制检查数量
            try:
                filepath = os.path.join(processed_dir, csv_file)
                df = pd.read_csv(filepath)
                if not df.empty:
                    # 添加股票代码
                    code = csv_file.replace('.csv', '')
                    df['code'] = code
                    all_data.append(df.tail(1))  # 只取最新一条
            except Exception:
                pass
        
        if all_data:
            return pd.concat(all_data, ignore_index=True)
        return None
    
    def _check_completeness(self, df: pd.DataFrame) -> float:
        """检查数据完整性"""
        if df.empty:
            return 0.0
        
        total_cells = len(df) * len(df.columns)
        if total_cells == 0:
            return 100.0
        
        missing_cells = df.isna().sum().sum()
        completeness = (1 - missing_cells / total_cells) * 100
        
        return min(100.0, max(0.0, completeness))
    
    def _check_accuracy(self, df: pd.DataFrame) -> float:
        """检查数据准确性"""
        if df.empty:
            return 0.0
        
        total_checks = 0
        passed_checks = 0
        
        for field, limits in self.FIELD_RANGES.items():
            if field not in df.columns:
                continue
            
            values = pd.to_numeric(df[field], errors='coerce')
            valid_mask = values.notna()
            
            if valid_mask.sum() == 0:
                continue
            
            in_range = (
                (values >= limits['min']) & 
                (values <= limits['max'])
            ) | values.isna()
            
            total_checks += valid_mask.sum()
            passed_checks += (valid_mask & in_range).sum()
        
        if total_checks == 0:
            return 100.0
        
        return (passed_checks / total_checks) * 100
    
    def _check_consistency(self, df: pd.DataFrame) -> float:
        """检查数据一致性"""
        if df.empty:
            return 100.0
        
        inconsistent_count = 0
        total_records = len(df)
        
        # 检查市值一致性
        if 'total_market_cap' in df.columns and 'float_market_cap' in df.columns:
            inconsistent = df[
                (df['float_market_cap'].notna()) & 
                (df['total_market_cap'].notna()) &
                (df['float_market_cap'] > df['total_market_cap'] * 1.01)
            ]
            inconsistent_count += len(inconsistent)
        
        # 检查价格一致性
        if 'high' in df.columns and 'low' in df.columns:
            price_inconsistent = df[
                (df['high'].notna()) & 
                (df['low'].notna()) &
                (df['high'] < df['low'])
            ]
            inconsistent_count += len(price_inconsistent)
        
        if total_records == 0:
            return 100.0
        
        return max(0.0, 100.0 - (inconsistent_count / total_records * 100))
    
    def _check_timeliness(self, df: pd.DataFrame) -> float:
        """检查数据时效性"""
        if df.empty:
            return 0.0
        
        # 检查数据文件的更新时间
        processed_dir = 'data/processed'
        if not os.path.exists(processed_dir):
            return 50.0  # 无法判断时返回中等分数
        
        now = datetime.now()
        threshold = timedelta(hours=self.config.timeliness_threshold_hours)
        
        recent_files = 0
        total_files = 0
        
        for f in os.listdir(processed_dir):
            if f.endswith('.csv'):
                filepath = os.path.join(processed_dir, f)
                try:
                    mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                    total_files += 1
                    if now - mtime <= threshold:
                        recent_files += 1
                except Exception:
                    pass
        
        if total_files == 0:
            return 50.0
        
        return (recent_files / total_files) * 100
    
    def _check_validity(self, df: pd.DataFrame) -> float:
        """检查数据有效性"""
        if df.empty:
            return 0.0
        
        total_records = len(df)
        valid_records = total_records
        
        # 检查必需字段
        for field in self.REQUIRED_FIELDS:
            if field in df.columns:
                invalid = df[field].isna() | (df[field].astype(str).str.strip() == '')
                valid_records -= invalid.sum()
        
        # 检查股票代码格式
        if 'code' in df.columns:
            import re
            valid_patterns = [
                r'^000\d{3}$', r'^001\d{3}$', r'^002\d{3}$',
                r'^003\d{3}$', r'^300\d{3}$', r'^600\d{3}$',
                r'^601\d{3}$', r'^603\d{3}$', r'^605\d{3}$',
                r'^688\d{3}$'
            ]
            
            def is_valid_code(code):
                if pd.isna(code):
                    return False
                code_str = str(code).strip().zfill(6)
                return any(re.match(p, code_str) for p in valid_patterns)
            
            invalid_codes = ~df['code'].apply(is_valid_code)
            valid_records -= invalid_codes.sum()
        
        if total_records == 0:
            return 100.0
        
        return max(0.0, (valid_records / total_records) * 100)

    
    def _check_thresholds_and_alert(
        self, 
        snapshot: DataQualitySnapshot,
        df: pd.DataFrame
    ):
        """检查阈值并生成告警"""
        # 检查完整性
        if snapshot.completeness_score < self.config.completeness_threshold:
            self._create_alert_if_needed(
                level=DataQualityAlertLevel.WARNING,
                dimension=DataQualityDimension.COMPLETENESS,
                title="数据完整性不足",
                message=f"数据完整性得分 {snapshot.completeness_score:.1f}% "
                       f"低于阈值 {self.config.completeness_threshold}%",
                affected_records=snapshot.total_records
            )
        
        # 检查准确性
        if snapshot.accuracy_score < self.config.accuracy_threshold:
            level = (DataQualityAlertLevel.ERROR 
                    if snapshot.accuracy_score < 95 
                    else DataQualityAlertLevel.WARNING)
            self._create_alert_if_needed(
                level=level,
                dimension=DataQualityDimension.ACCURACY,
                title="数据准确性不达标",
                message=f"数据准确性得分 {snapshot.accuracy_score:.1f}% "
                       f"低于阈值 {self.config.accuracy_threshold}%",
                affected_records=snapshot.total_records
            )
        
        # 检查一致性
        if snapshot.consistency_score < self.config.consistency_threshold:
            self._create_alert_if_needed(
                level=DataQualityAlertLevel.WARNING,
                dimension=DataQualityDimension.CONSISTENCY,
                title="数据一致性问题",
                message=f"数据一致性得分 {snapshot.consistency_score:.1f}% "
                       f"低于阈值 {self.config.consistency_threshold}%",
                affected_records=snapshot.total_records
            )
        
        # 检查时效性
        if snapshot.timeliness_score < 80:  # 时效性低于80%
            self._create_alert_if_needed(
                level=DataQualityAlertLevel.WARNING,
                dimension=DataQualityDimension.TIMELINESS,
                title="数据时效性不足",
                message=f"数据时效性得分 {snapshot.timeliness_score:.1f}%，"
                       f"部分数据可能已过期",
                affected_records=snapshot.total_records
            )
        
        # 检查有效性
        if snapshot.validity_score < self.config.validity_threshold:
            self._create_alert_if_needed(
                level=DataQualityAlertLevel.WARNING,
                dimension=DataQualityDimension.VALIDITY,
                title="数据有效性问题",
                message=f"数据有效性得分 {snapshot.validity_score:.1f}% "
                       f"低于阈值 {self.config.validity_threshold}%",
                affected_records=snapshot.total_records
            )
        
        # 检查整体质量
        if snapshot.overall_score < 80:
            level = (DataQualityAlertLevel.CRITICAL 
                    if snapshot.overall_score < 60 
                    else DataQualityAlertLevel.ERROR)
            self._create_alert_if_needed(
                level=level,
                dimension=DataQualityDimension.COMPLETENESS,  # 使用完整性作为默认维度
                title="数据质量严重下降",
                message=f"数据质量综合得分 {snapshot.overall_score:.1f}% "
                       f"处于较低水平，需要立即关注",
                affected_records=snapshot.total_records
            )
    
    def _create_alert_if_needed(
        self,
        level: DataQualityAlertLevel,
        dimension: DataQualityDimension,
        title: str,
        message: str,
        affected_records: int = 0,
        affected_fields: Optional[List[str]] = None
    ) -> Optional[DataQualityAlert]:
        """创建告警（如果需要）"""
        # 检查冷却时间
        alert_key = f"{dimension.value}:{title}"
        if alert_key in self._last_alert_times:
            elapsed = datetime.now() - self._last_alert_times[alert_key]
            if elapsed.total_seconds() < self.config.alert_cooldown_minutes * 60:
                return None
        
        # 创建告警
        self._alert_counter += 1
        alert = DataQualityAlert(
            alert_id=f"DQ_{datetime.now().strftime('%Y%m%d%H%M%S')}_{self._alert_counter}",
            level=level,
            dimension=dimension,
            title=title,
            message=message,
            affected_records=affected_records,
            affected_fields=affected_fields or []
        )
        
        self._alerts.append(alert)
        self._last_alert_times[alert_key] = datetime.now()
        
        # 触发告警处理器
        for handler in self._alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"告警处理器执行失败: {e}")
        
        # 记录日志
        log_method = {
            DataQualityAlertLevel.INFO: logger.info,
            DataQualityAlertLevel.WARNING: logger.warning,
            DataQualityAlertLevel.ERROR: logger.error,
            DataQualityAlertLevel.CRITICAL: logger.critical
        }.get(level, logger.info)
        
        log_method(f"[数据质量告警] [{level.value.upper()}] {title}: {message}")
        
        # 写入告警文件
        if "file" in self.config.alert_channels:
            self._write_alert_to_file(alert)
        
        return alert
    
    def _write_alert_to_file(self, alert: DataQualityAlert):
        """写入告警到文件"""
        try:
            alert_log_file = "data/data_quality_alert.log"
            os.makedirs(os.path.dirname(alert_log_file), exist_ok=True)
            
            with open(alert_log_file, 'a', encoding='utf-8') as f:
                f.write(
                    f"{alert.timestamp.isoformat()} | "
                    f"{alert.level.value.upper()} | "
                    f"{alert.dimension.value} | "
                    f"{alert.title} | "
                    f"{alert.message}\n"
                )
        except Exception as e:
            logger.warning(f"写入告警文件失败: {e}")
    
    def _add_snapshot(self, snapshot: DataQualitySnapshot):
        """添加快照"""
        self._snapshots.append(snapshot)
        
        # 限制历史快照数量
        if len(self._snapshots) > self.config.max_history_snapshots:
            self._snapshots = self._snapshots[-self.config.max_history_snapshots:]
        
        # 触发快照处理器
        for handler in self._snapshot_handlers:
            try:
                handler(snapshot)
            except Exception as e:
                logger.error(f"快照处理器执行失败: {e}")
    
    def check_now(self) -> Optional[DataQualitySnapshot]:
        """
        立即执行一次数据质量检查
        
        Returns:
            DataQualitySnapshot: 质量快照
        """
        try:
            self._perform_quality_check()
            return self._snapshots[-1] if self._snapshots else None
        except Exception as e:
            logger.error(f"数据质量检查失败: {e}")
            return None
    
    def get_latest_snapshot(self) -> Optional[DataQualitySnapshot]:
        """获取最新快照"""
        return self._snapshots[-1] if self._snapshots else None
    
    def get_snapshots(self, limit: int = 100) -> List[DataQualitySnapshot]:
        """获取历史快照"""
        return self._snapshots[-limit:]
    
    def get_active_alerts(self) -> List[DataQualityAlert]:
        """获取活跃告警"""
        return [a for a in self._alerts if not a.resolved]
    
    def get_alerts(self, limit: int = 100) -> List[DataQualityAlert]:
        """获取告警列表"""
        return self._alerts[-limit:]
    
    def resolve_alert(self, alert_id: str) -> bool:
        """解决告警"""
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                alert.resolved = True
                alert.resolved_at = datetime.now()
                return True
        return False
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """获取告警摘要"""
        active = self.get_active_alerts()
        
        return {
            'total': len(self._alerts),
            'active': len(active),
            'by_level': {
                'critical': len([a for a in active if a.level == DataQualityAlertLevel.CRITICAL]),
                'error': len([a for a in active if a.level == DataQualityAlertLevel.ERROR]),
                'warning': len([a for a in active if a.level == DataQualityAlertLevel.WARNING]),
                'info': len([a for a in active if a.level == DataQualityAlertLevel.INFO])
            },
            'by_dimension': {
                'completeness': len([a for a in active if a.dimension == DataQualityDimension.COMPLETENESS]),
                'accuracy': len([a for a in active if a.dimension == DataQualityDimension.ACCURACY]),
                'consistency': len([a for a in active if a.dimension == DataQualityDimension.CONSISTENCY]),
                'timeliness': len([a for a in active if a.dimension == DataQualityDimension.TIMELINESS]),
                'validity': len([a for a in active if a.dimension == DataQualityDimension.VALIDITY])
            }
        }
    
    def get_quality_trend(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        获取质量趋势
        
        Args:
            hours: 时间范围（小时）
        
        Returns:
            质量趋势数据
        """
        cutoff = datetime.now() - timedelta(hours=hours)
        recent_snapshots = [
            s for s in self._snapshots 
            if s.timestamp >= cutoff
        ]
        
        return [s.to_dict() for s in recent_snapshots]
    
    def _load_history(self):
        """加载历史数据"""
        # 加载告警历史
        try:
            if os.path.exists(self._alerts_file):
                with open(self._alerts_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for item in data[-100:]:  # 只加载最近100条
                        self._alerts.append(DataQualityAlert(
                            alert_id=item['alert_id'],
                            level=DataQualityAlertLevel(item['level']),
                            dimension=DataQualityDimension(item['dimension']),
                            title=item['title'],
                            message=item['message'],
                            affected_records=item.get('affected_records', 0),
                            affected_fields=item.get('affected_fields', []),
                            timestamp=datetime.fromisoformat(item['timestamp']),
                            resolved=item.get('resolved', False),
                            resolved_at=datetime.fromisoformat(item['resolved_at']) if item.get('resolved_at') else None
                        ))
        except Exception as e:
            logger.debug(f"加载告警历史失败: {e}")
        
        # 加载快照历史
        try:
            if os.path.exists(self._snapshots_file):
                with open(self._snapshots_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for item in data[-100:]:  # 只加载最近100条
                        self._snapshots.append(DataQualitySnapshot(
                            timestamp=datetime.fromisoformat(item['timestamp']),
                            total_records=item['total_records'],
                            completeness_score=item['completeness_score'],
                            accuracy_score=item['accuracy_score'],
                            consistency_score=item['consistency_score'],
                            timeliness_score=item['timeliness_score'],
                            validity_score=item['validity_score'],
                            overall_score=item['overall_score'],
                            alerts_count=item.get('alerts_count', 0),
                            issues=item.get('issues', {})
                        ))
        except Exception as e:
            logger.debug(f"加载快照历史失败: {e}")
    
    def _save_history(self):
        """保存历史数据"""
        try:
            os.makedirs(os.path.dirname(self._alerts_file), exist_ok=True)
            
            # 保存告警
            with open(self._alerts_file, 'w', encoding='utf-8') as f:
                json.dump(
                    [a.to_dict() for a in self._alerts[-500:]],
                    f, ensure_ascii=False, indent=2
                )
            
            # 保存快照
            with open(self._snapshots_file, 'w', encoding='utf-8') as f:
                json.dump(
                    [s.to_dict() for s in self._snapshots[-500:]],
                    f, ensure_ascii=False, indent=2
                )
        except Exception as e:
            logger.warning(f"保存历史数据失败: {e}")

    
    def generate_quality_report(self) -> str:
        """
        生成数据质量报告
        
        Returns:
            报告文本
        """
        snapshot = self.get_latest_snapshot()
        alert_summary = self.get_alert_summary()
        
        lines = [
            "=" * 60,
            "数据质量实时监控报告",
            "=" * 60,
            f"报告时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"监控状态: {self._status.value}",
            "",
        ]
        
        if snapshot:
            lines.extend([
                "【最新质量快照】",
                f"  检查时间: {snapshot.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
                f"  记录数量: {snapshot.total_records}",
                f"  综合得分: {snapshot.overall_score:.1f}%",
                "",
                "【各维度得分】",
                f"  完整性: {snapshot.completeness_score:.1f}% "
                f"(阈值: {self.config.completeness_threshold}%)",
                f"  准确性: {snapshot.accuracy_score:.1f}% "
                f"(阈值: {self.config.accuracy_threshold}%)",
                f"  一致性: {snapshot.consistency_score:.1f}% "
                f"(阈值: {self.config.consistency_threshold}%)",
                f"  时效性: {snapshot.timeliness_score:.1f}%",
                f"  有效性: {snapshot.validity_score:.1f}% "
                f"(阈值: {self.config.validity_threshold}%)",
                "",
            ])
        else:
            lines.append("暂无质量快照数据")
            lines.append("")
        
        lines.extend([
            "【告警摘要】",
            f"  总告警数: {alert_summary['total']}",
            f"  活跃告警: {alert_summary['active']}",
            f"    - 严重: {alert_summary['by_level']['critical']}",
            f"    - 错误: {alert_summary['by_level']['error']}",
            f"    - 警告: {alert_summary['by_level']['warning']}",
            f"    - 信息: {alert_summary['by_level']['info']}",
            "",
        ])
        
        # 显示活跃告警
        active_alerts = self.get_active_alerts()
        if active_alerts:
            lines.append("【活跃告警详情】")
            for alert in active_alerts[:5]:  # 只显示前5条
                lines.append(
                    f"  [{alert.level.value.upper()}] {alert.title}"
                )
                lines.append(f"    {alert.message}")
            if len(active_alerts) > 5:
                lines.append(f"  ... 还有 {len(active_alerts) - 5} 条告警")
            lines.append("")
        
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取监控状态
        
        Returns:
            状态信息字典
        """
        snapshot = self.get_latest_snapshot()
        
        return {
            'status': self._status.value,
            'is_running': self.is_running,
            'config': self.config.to_dict(),
            'latest_snapshot': snapshot.to_dict() if snapshot else None,
            'alerts': self.get_alert_summary(),
            'snapshots_count': len(self._snapshots),
            'last_check': self._snapshots[-1].timestamp.isoformat() if self._snapshots else None
        }


# 全局实例
_realtime_monitor: Optional[RealtimeDataQualityMonitor] = None


def get_realtime_data_quality_monitor(
    config: Optional[RealtimeMonitorConfig] = None
) -> RealtimeDataQualityMonitor:
    """
    获取实时数据质量监控器实例
    
    Args:
        config: 监控配置
    
    Returns:
        RealtimeDataQualityMonitor: 监控器实例
    """
    global _realtime_monitor
    if _realtime_monitor is None:
        _realtime_monitor = RealtimeDataQualityMonitor(config)
    return _realtime_monitor


def reset_realtime_monitor() -> None:
    """重置实时监控器"""
    global _realtime_monitor
    if _realtime_monitor is not None:
        _realtime_monitor.stop()
    _realtime_monitor = None


def start_realtime_quality_monitoring(
    config: Optional[RealtimeMonitorConfig] = None
) -> RealtimeDataQualityMonitor:
    """
    启动实时数据质量监控
    
    便捷函数，用于快速启动监控
    
    Args:
        config: 监控配置
    
    Returns:
        RealtimeDataQualityMonitor: 监控器实例
    """
    monitor = get_realtime_data_quality_monitor(config)
    monitor.start()
    return monitor


def stop_realtime_quality_monitoring() -> None:
    """停止实时数据质量监控"""
    global _realtime_monitor
    if _realtime_monitor is not None:
        _realtime_monitor.stop()


def check_data_quality_now() -> Optional[DataQualitySnapshot]:
    """
    立即执行数据质量检查
    
    便捷函数
    
    Returns:
        DataQualitySnapshot: 质量快照
    """
    monitor = get_realtime_data_quality_monitor()
    return monitor.check_now()


def get_data_quality_status() -> Dict[str, Any]:
    """
    获取数据质量状态
    
    便捷函数
    
    Returns:
        状态信息字典
    """
    monitor = get_realtime_data_quality_monitor()
    return monitor.get_status()


def generate_data_quality_report() -> str:
    """
    生成数据质量报告
    
    便捷函数
    
    Returns:
        报告文本
    """
    monitor = get_realtime_data_quality_monitor()
    return monitor.generate_quality_report()
