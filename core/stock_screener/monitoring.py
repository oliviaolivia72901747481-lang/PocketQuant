"""
系统监控模块

提供系统运行监控功能，包括：
- 系统运行状态监控
- 日志和告警机制
- 定期维护计划
- 健康检查
- 告警通知集成
- 性能指标监控

Requirements: 5.2, 5.5, 13.2
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Callable
from enum import Enum
from datetime import datetime, timedelta
import logging
import os
import json
import threading
import time
import traceback

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """健康状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class AlertSeverity(Enum):
    """告警严重程度"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ComponentType(Enum):
    """组件类型"""
    DATA_SOURCE = "data_source"
    SCREENER = "screener"
    SCORER = "scorer"
    VALIDATOR = "validator"
    RISK_CONTROLLER = "risk_controller"
    POOL_UPDATER = "pool_updater"
    SYSTEM = "system"


@dataclass
class HealthCheckResult:
    """健康检查结果"""
    component: str
    component_type: ComponentType
    status: HealthStatus
    message: str
    response_time_ms: float = 0.0
    last_check: datetime = field(default_factory=datetime.now)
    details: Optional[Dict[str, Any]] = None


@dataclass
class SystemAlert:
    """系统告警"""
    alert_id: str
    severity: AlertSeverity
    component: str
    title: str
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'alert_id': self.alert_id,
            'severity': self.severity.value,
            'component': self.component,
            'title': self.title,
            'message': self.message,
            'timestamp': self.timestamp.isoformat(),
            'acknowledged': self.acknowledged,
            'resolved': self.resolved,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None
        }


@dataclass
class SystemMetrics:
    """系统指标"""
    timestamp: datetime
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    disk_usage: float = 0.0
    active_processes: int = 0
    pending_tasks: int = 0
    error_count_24h: int = 0
    warning_count_24h: int = 0
    last_update_time: Optional[datetime] = None
    last_update_status: str = ""


@dataclass
class MaintenanceTask:
    """维护任务"""
    task_id: str
    name: str
    description: str
    schedule: str  # cron表达式或描述
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'task_id': self.task_id,
            'name': self.name,
            'description': self.description,
            'schedule': self.schedule,
            'last_run': self.last_run.isoformat() if self.last_run else None,
            'next_run': self.next_run.isoformat() if self.next_run else None,
            'enabled': self.enabled
        }


class HealthChecker:
    """
    健康检查器
    
    检查系统各组件的健康状态
    """
    
    def __init__(self):
        """初始化健康检查器"""
        self.check_results: Dict[str, HealthCheckResult] = {}
        self.check_interval = 60  # 秒
    
    def check_all(self) -> List[HealthCheckResult]:
        """执行所有健康检查"""
        results = []
        
        # 检查数据源
        results.append(self._check_data_source())
        
        # 检查筛选器
        results.append(self._check_screener())
        
        # 检查评分系统
        results.append(self._check_scorer())
        
        # 检查验证器
        results.append(self._check_validator())
        
        # 检查风险控制器
        results.append(self._check_risk_controller())
        
        # 检查系统资源
        results.append(self._check_system_resources())
        
        # 更新缓存
        for result in results:
            self.check_results[result.component] = result
        
        return results
    
    def _check_data_source(self) -> HealthCheckResult:
        """检查数据源"""
        start_time = time.time()
        try:
            from core.stock_screener import get_data_source_manager
            manager = get_data_source_manager()
            
            # 简单的可用性检查
            if manager is not None:
                response_time = (time.time() - start_time) * 1000
                return HealthCheckResult(
                    component="DataSourceManager",
                    component_type=ComponentType.DATA_SOURCE,
                    status=HealthStatus.HEALTHY,
                    message="数据源管理器正常",
                    response_time_ms=response_time
                )
            else:
                return HealthCheckResult(
                    component="DataSourceManager",
                    component_type=ComponentType.DATA_SOURCE,
                    status=HealthStatus.UNHEALTHY,
                    message="数据源管理器不可用"
                )
        except Exception as e:
            return HealthCheckResult(
                component="DataSourceManager",
                component_type=ComponentType.DATA_SOURCE,
                status=HealthStatus.UNHEALTHY,
                message=f"数据源检查失败: {e}"
            )
    
    def _check_screener(self) -> HealthCheckResult:
        """检查筛选器"""
        start_time = time.time()
        try:
            from core.stock_screener import (
                get_industry_screener,
                get_financial_screener,
                get_market_screener
            )
            
            _ = get_industry_screener()
            _ = get_financial_screener()
            _ = get_market_screener()
            
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                component="Screeners",
                component_type=ComponentType.SCREENER,
                status=HealthStatus.HEALTHY,
                message="所有筛选器正常",
                response_time_ms=response_time
            )
        except Exception as e:
            return HealthCheckResult(
                component="Screeners",
                component_type=ComponentType.SCREENER,
                status=HealthStatus.UNHEALTHY,
                message=f"筛选器检查失败: {e}"
            )
    
    def _check_scorer(self) -> HealthCheckResult:
        """检查评分系统"""
        start_time = time.time()
        try:
            from core.stock_screener import get_comprehensive_scorer
            scorer = get_comprehensive_scorer()
            
            if scorer is not None:
                response_time = (time.time() - start_time) * 1000
                return HealthCheckResult(
                    component="ComprehensiveScorer",
                    component_type=ComponentType.SCORER,
                    status=HealthStatus.HEALTHY,
                    message="评分系统正常",
                    response_time_ms=response_time
                )
            else:
                return HealthCheckResult(
                    component="ComprehensiveScorer",
                    component_type=ComponentType.SCORER,
                    status=HealthStatus.UNHEALTHY,
                    message="评分系统不可用"
                )
        except Exception as e:
            return HealthCheckResult(
                component="ComprehensiveScorer",
                component_type=ComponentType.SCORER,
                status=HealthStatus.UNHEALTHY,
                message=f"评分系统检查失败: {e}"
            )
    
    def _check_validator(self) -> HealthCheckResult:
        """检查验证器"""
        start_time = time.time()
        try:
            from core.stock_screener import get_quality_monitor, get_result_validator
            
            _ = get_quality_monitor()
            _ = get_result_validator()
            
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                component="Validators",
                component_type=ComponentType.VALIDATOR,
                status=HealthStatus.HEALTHY,
                message="验证器正常",
                response_time_ms=response_time
            )
        except Exception as e:
            return HealthCheckResult(
                component="Validators",
                component_type=ComponentType.VALIDATOR,
                status=HealthStatus.UNHEALTHY,
                message=f"验证器检查失败: {e}"
            )
    
    def _check_risk_controller(self) -> HealthCheckResult:
        """检查风险控制器"""
        start_time = time.time()
        try:
            from core.stock_screener import get_risk_assessor, get_alert_manager
            
            _ = get_risk_assessor()
            _ = get_alert_manager()
            
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                component="RiskController",
                component_type=ComponentType.RISK_CONTROLLER,
                status=HealthStatus.HEALTHY,
                message="风险控制器正常",
                response_time_ms=response_time
            )
        except Exception as e:
            return HealthCheckResult(
                component="RiskController",
                component_type=ComponentType.RISK_CONTROLLER,
                status=HealthStatus.UNHEALTHY,
                message=f"风险控制器检查失败: {e}"
            )
    
    def _check_system_resources(self) -> HealthCheckResult:
        """检查系统资源"""
        try:
            # 检查磁盘空间
            data_dir = 'data'
            if os.path.exists(data_dir):
                # 简单检查目录是否可写
                test_file = os.path.join(data_dir, '.health_check')
                try:
                    with open(test_file, 'w') as f:
                        f.write('test')
                    os.remove(test_file)
                    disk_ok = True
                except:
                    disk_ok = False
            else:
                disk_ok = False
            
            # 检查日志目录
            log_dir = 'logs'
            log_ok = os.path.exists(log_dir) and os.access(log_dir, os.W_OK)
            
            if disk_ok and log_ok:
                return HealthCheckResult(
                    component="SystemResources",
                    component_type=ComponentType.SYSTEM,
                    status=HealthStatus.HEALTHY,
                    message="系统资源正常"
                )
            else:
                issues = []
                if not disk_ok:
                    issues.append("数据目录不可写")
                if not log_ok:
                    issues.append("日志目录不可写")
                return HealthCheckResult(
                    component="SystemResources",
                    component_type=ComponentType.SYSTEM,
                    status=HealthStatus.DEGRADED,
                    message=f"系统资源问题: {', '.join(issues)}"
                )
        except Exception as e:
            return HealthCheckResult(
                component="SystemResources",
                component_type=ComponentType.SYSTEM,
                status=HealthStatus.UNKNOWN,
                message=f"系统资源检查失败: {e}"
            )
    
    def get_overall_status(self) -> HealthStatus:
        """获取整体健康状态"""
        if not self.check_results:
            return HealthStatus.UNKNOWN
        
        statuses = [r.status for r in self.check_results.values()]
        
        if any(s == HealthStatus.UNHEALTHY for s in statuses):
            return HealthStatus.UNHEALTHY
        elif any(s == HealthStatus.DEGRADED for s in statuses):
            return HealthStatus.DEGRADED
        elif all(s == HealthStatus.HEALTHY for s in statuses):
            return HealthStatus.HEALTHY
        else:
            return HealthStatus.UNKNOWN


class AlertManager:
    """
    告警管理器
    
    管理系统告警的生成、存储和通知
    """
    
    def __init__(self, alert_file: str = "data/system_alerts.json"):
        """初始化告警管理器"""
        self.alert_file = alert_file
        self.alerts: List[SystemAlert] = []
        self.alert_handlers: List[Callable[[SystemAlert], None]] = []
        self._load_alerts()
    
    def create_alert(
        self,
        severity: AlertSeverity,
        component: str,
        title: str,
        message: str
    ) -> SystemAlert:
        """创建告警"""
        alert_id = f"ALERT_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(self.alerts)}"
        
        alert = SystemAlert(
            alert_id=alert_id,
            severity=severity,
            component=component,
            title=title,
            message=message
        )
        
        self.alerts.append(alert)
        self._save_alerts()
        
        # 触发告警处理器
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"告警处理器执行失败: {e}")
        
        # 记录日志
        log_method = {
            AlertSeverity.INFO: logger.info,
            AlertSeverity.WARNING: logger.warning,
            AlertSeverity.ERROR: logger.error,
            AlertSeverity.CRITICAL: logger.critical
        }.get(severity, logger.info)
        
        log_method(f"[{alert_id}] {title}: {message}")
        
        return alert
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """确认告警"""
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                self._save_alerts()
                return True
        return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """解决告警"""
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.resolved = True
                alert.resolved_at = datetime.now()
                self._save_alerts()
                return True
        return False
    
    def get_active_alerts(self) -> List[SystemAlert]:
        """获取活跃告警"""
        return [a for a in self.alerts if not a.resolved]
    
    def get_alerts_by_severity(self, severity: AlertSeverity) -> List[SystemAlert]:
        """按严重程度获取告警"""
        return [a for a in self.alerts if a.severity == severity]
    
    def add_handler(self, handler: Callable[[SystemAlert], None]):
        """添加告警处理器"""
        self.alert_handlers.append(handler)
    
    def _load_alerts(self):
        """加载告警"""
        try:
            if os.path.exists(self.alert_file):
                with open(self.alert_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for item in data:
                        self.alerts.append(SystemAlert(
                            alert_id=item['alert_id'],
                            severity=AlertSeverity(item['severity']),
                            component=item['component'],
                            title=item['title'],
                            message=item['message'],
                            timestamp=datetime.fromisoformat(item['timestamp']),
                            acknowledged=item.get('acknowledged', False),
                            resolved=item.get('resolved', False),
                            resolved_at=datetime.fromisoformat(item['resolved_at']) if item.get('resolved_at') else None
                        ))
        except Exception as e:
            logger.warning(f"加载告警失败: {e}")
    
    def _save_alerts(self):
        """保存告警"""
        try:
            os.makedirs(os.path.dirname(self.alert_file), exist_ok=True)
            with open(self.alert_file, 'w', encoding='utf-8') as f:
                json.dump([a.to_dict() for a in self.alerts[-1000:]], f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"保存告警失败: {e}")
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """获取告警摘要"""
        active = self.get_active_alerts()
        
        return {
            'total': len(self.alerts),
            'active': len(active),
            'by_severity': {
                'critical': len([a for a in active if a.severity == AlertSeverity.CRITICAL]),
                'error': len([a for a in active if a.severity == AlertSeverity.ERROR]),
                'warning': len([a for a in active if a.severity == AlertSeverity.WARNING]),
                'info': len([a for a in active if a.severity == AlertSeverity.INFO])
            }
        }


class MaintenanceScheduler:
    """
    维护调度器
    
    管理定期维护任务
    """
    
    # 预定义维护任务
    DEFAULT_TASKS = [
        MaintenanceTask(
            task_id="cleanup_logs",
            name="清理过期日志",
            description="清理30天前的日志文件",
            schedule="每周日 02:00"
        ),
        MaintenanceTask(
            task_id="cleanup_backups",
            name="清理过期备份",
            description="清理超过10个的旧备份文件",
            schedule="每周日 03:00"
        ),
        MaintenanceTask(
            task_id="validate_data",
            name="数据完整性验证",
            description="验证股票池数据的完整性和准确性",
            schedule="每日 06:00"
        ),
        MaintenanceTask(
            task_id="health_check",
            name="系统健康检查",
            description="执行全面的系统健康检查",
            schedule="每小时"
        ),
        MaintenanceTask(
            task_id="update_pool",
            name="股票池更新",
            description="执行股票池筛选和更新",
            schedule="每周一 18:00"
        ),
    ]
    
    def __init__(self, schedule_file: str = "data/maintenance_schedule.json"):
        """初始化维护调度器"""
        self.schedule_file = schedule_file
        self.tasks: Dict[str, MaintenanceTask] = {}
        self._load_schedule()
        
        # 如果没有任务，使用默认任务
        if not self.tasks:
            for task in self.DEFAULT_TASKS:
                self.tasks[task.task_id] = task
            self._save_schedule()
    
    def get_all_tasks(self) -> List[MaintenanceTask]:
        """获取所有维护任务"""
        return list(self.tasks.values())
    
    def get_task(self, task_id: str) -> Optional[MaintenanceTask]:
        """获取指定任务"""
        return self.tasks.get(task_id)
    
    def enable_task(self, task_id: str) -> bool:
        """启用任务"""
        if task_id in self.tasks:
            self.tasks[task_id].enabled = True
            self._save_schedule()
            return True
        return False
    
    def disable_task(self, task_id: str) -> bool:
        """禁用任务"""
        if task_id in self.tasks:
            self.tasks[task_id].enabled = False
            self._save_schedule()
            return True
        return False
    
    def record_task_run(self, task_id: str) -> bool:
        """记录任务执行"""
        if task_id in self.tasks:
            self.tasks[task_id].last_run = datetime.now()
            self._save_schedule()
            return True
        return False
    
    def get_pending_tasks(self) -> List[MaintenanceTask]:
        """获取待执行的任务"""
        pending = []
        now = datetime.now()
        
        for task in self.tasks.values():
            if not task.enabled:
                continue
            
            # 简单的调度逻辑
            if task.last_run is None:
                pending.append(task)
            elif "每小时" in task.schedule:
                if (now - task.last_run).total_seconds() >= 3600:
                    pending.append(task)
            elif "每日" in task.schedule:
                if (now - task.last_run).days >= 1:
                    pending.append(task)
            elif "每周" in task.schedule:
                if (now - task.last_run).days >= 7:
                    pending.append(task)
        
        return pending
    
    def _load_schedule(self):
        """加载调度配置"""
        try:
            if os.path.exists(self.schedule_file):
                with open(self.schedule_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for item in data:
                        task = MaintenanceTask(
                            task_id=item['task_id'],
                            name=item['name'],
                            description=item['description'],
                            schedule=item['schedule'],
                            last_run=datetime.fromisoformat(item['last_run']) if item.get('last_run') else None,
                            next_run=datetime.fromisoformat(item['next_run']) if item.get('next_run') else None,
                            enabled=item.get('enabled', True)
                        )
                        self.tasks[task.task_id] = task
        except Exception as e:
            logger.warning(f"加载调度配置失败: {e}")
    
    def _save_schedule(self):
        """保存调度配置"""
        try:
            os.makedirs(os.path.dirname(self.schedule_file), exist_ok=True)
            with open(self.schedule_file, 'w', encoding='utf-8') as f:
                json.dump([t.to_dict() for t in self.tasks.values()], f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"保存调度配置失败: {e}")


class SystemMonitor:
    """
    系统监控器
    
    综合管理系统监控功能
    """
    
    def __init__(self):
        """初始化系统监控器"""
        self.health_checker = HealthChecker()
        self.alert_manager = AlertManager()
        self.maintenance_scheduler = MaintenanceScheduler()
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
    
    def start_monitoring(self, interval_seconds: int = 300):
        """
        启动监控
        
        Args:
            interval_seconds: 监控间隔（秒）
        """
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(interval_seconds,),
            daemon=True
        )
        self._monitor_thread.start()
        logger.info(f"系统监控已启动，间隔{interval_seconds}秒")
    
    def stop_monitoring(self):
        """停止监控"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        logger.info("系统监控已停止")
    
    def _monitoring_loop(self, interval: int):
        """监控循环"""
        while self._monitoring:
            try:
                # 执行健康检查
                results = self.health_checker.check_all()
                
                # 检查是否需要告警
                for result in results:
                    if result.status == HealthStatus.UNHEALTHY:
                        self.alert_manager.create_alert(
                            severity=AlertSeverity.ERROR,
                            component=result.component,
                            title=f"{result.component}不健康",
                            message=result.message
                        )
                    elif result.status == HealthStatus.DEGRADED:
                        self.alert_manager.create_alert(
                            severity=AlertSeverity.WARNING,
                            component=result.component,
                            title=f"{result.component}性能下降",
                            message=result.message
                        )
                
                # 检查待执行的维护任务
                pending_tasks = self.maintenance_scheduler.get_pending_tasks()
                if pending_tasks:
                    logger.info(f"有{len(pending_tasks)}个待执行的维护任务")
                
            except Exception as e:
                logger.error(f"监控循环出错: {e}")
            
            time.sleep(interval)
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        # 执行健康检查
        health_results = self.health_checker.check_all()
        overall_health = self.health_checker.get_overall_status()
        
        # 获取告警摘要
        alert_summary = self.alert_manager.get_alert_summary()
        
        # 获取维护任务状态
        tasks = self.maintenance_scheduler.get_all_tasks()
        pending_tasks = self.maintenance_scheduler.get_pending_tasks()
        
        return {
            'timestamp': datetime.now().isoformat(),
            'overall_health': overall_health.value,
            'monitoring_active': self._monitoring,
            'health_checks': [
                {
                    'component': r.component,
                    'status': r.status.value,
                    'message': r.message,
                    'response_time_ms': r.response_time_ms
                }
                for r in health_results
            ],
            'alerts': alert_summary,
            'maintenance': {
                'total_tasks': len(tasks),
                'pending_tasks': len(pending_tasks),
                'enabled_tasks': len([t for t in tasks if t.enabled])
            }
        }
    
    def generate_status_report(self) -> str:
        """生成状态报告"""
        status = self.get_system_status()
        
        lines = [
            "=" * 60,
            "系统状态报告",
            "=" * 60,
            f"报告时间: {status['timestamp']}",
            f"整体健康状态: {status['overall_health']}",
            f"监控状态: {'运行中' if status['monitoring_active'] else '已停止'}",
            "",
            "组件健康状态:",
        ]
        
        for check in status['health_checks']:
            status_icon = {
                'healthy': '✓',
                'degraded': '⚠',
                'unhealthy': '✗',
                'unknown': '?'
            }.get(check['status'], '?')
            lines.append(f"  {status_icon} {check['component']}: {check['message']}")
        
        lines.append("")
        lines.append("告警摘要:")
        alerts = status['alerts']
        lines.append(f"  活跃告警: {alerts['active']}")
        lines.append(f"  严重: {alerts['by_severity']['critical']}")
        lines.append(f"  错误: {alerts['by_severity']['error']}")
        lines.append(f"  警告: {alerts['by_severity']['warning']}")
        
        lines.append("")
        lines.append("维护任务:")
        maint = status['maintenance']
        lines.append(f"  总任务数: {maint['total_tasks']}")
        lines.append(f"  待执行: {maint['pending_tasks']}")
        lines.append(f"  已启用: {maint['enabled_tasks']}")
        
        lines.append("=" * 60)
        
        return "\n".join(lines)


# 全局实例
_health_checker: Optional[HealthChecker] = None
_alert_manager: Optional[AlertManager] = None
_maintenance_scheduler: Optional[MaintenanceScheduler] = None
_system_monitor: Optional[SystemMonitor] = None


def get_health_checker() -> HealthChecker:
    """获取健康检查器实例"""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker


def get_system_alert_manager() -> AlertManager:
    """获取告警管理器实例"""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager


def get_maintenance_scheduler() -> MaintenanceScheduler:
    """获取维护调度器实例"""
    global _maintenance_scheduler
    if _maintenance_scheduler is None:
        _maintenance_scheduler = MaintenanceScheduler()
    return _maintenance_scheduler


def get_system_monitor() -> SystemMonitor:
    """获取系统监控器实例"""
    global _system_monitor
    if _system_monitor is None:
        _system_monitor = SystemMonitor()
    return _system_monitor


# ==========================================
# 告警通知配置
# ==========================================

@dataclass
class AlertNotificationConfig:
    """告警通知配置"""
    enabled: bool = True
    min_severity: AlertSeverity = AlertSeverity.WARNING
    notification_channels: List[str] = field(default_factory=lambda: ["log", "file"])
    feishu_enabled: bool = False
    feishu_webhook_url: str = ""
    cooldown_minutes: int = 5  # 同类告警冷却时间
    max_alerts_per_hour: int = 20  # 每小时最大告警数
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'enabled': self.enabled,
            'min_severity': self.min_severity.value,
            'notification_channels': self.notification_channels,
            'feishu_enabled': self.feishu_enabled,
            'feishu_webhook_url': self.feishu_webhook_url[:20] + "..." if len(self.feishu_webhook_url) > 20 else self.feishu_webhook_url,
            'cooldown_minutes': self.cooldown_minutes,
            'max_alerts_per_hour': self.max_alerts_per_hour
        }


@dataclass
class AlertThresholds:
    """告警阈值配置"""
    # 健康检查阈值
    response_time_warning_ms: float = 5000.0
    response_time_critical_ms: float = 10000.0
    
    # 系统资源阈值
    disk_usage_warning_percent: float = 80.0
    disk_usage_critical_percent: float = 95.0
    
    # 数据质量阈值
    data_quality_warning_score: float = 70.0
    data_quality_critical_score: float = 50.0
    
    # 筛选性能阈值
    screening_time_warning_minutes: float = 20.0
    screening_time_critical_minutes: float = 30.0
    
    # 错误率阈值
    error_rate_warning_percent: float = 5.0
    error_rate_critical_percent: float = 10.0


class AlertNotifier:
    """
    告警通知器
    
    负责将告警发送到各种通知渠道
    """
    
    def __init__(self, config: Optional[AlertNotificationConfig] = None):
        """初始化告警通知器"""
        self.config = config or AlertNotificationConfig()
        self._last_alert_times: Dict[str, datetime] = {}
        self._alert_count_hour: int = 0
        self._hour_start: datetime = datetime.now()
    
    def should_notify(self, alert: SystemAlert) -> bool:
        """
        判断是否应该发送通知
        
        考虑因素：
        - 告警严重程度
        - 冷却时间
        - 每小时告警限制
        """
        if not self.config.enabled:
            return False
        
        # 检查严重程度
        severity_order = {
            AlertSeverity.INFO: 0,
            AlertSeverity.WARNING: 1,
            AlertSeverity.ERROR: 2,
            AlertSeverity.CRITICAL: 3
        }
        if severity_order.get(alert.severity, 0) < severity_order.get(self.config.min_severity, 1):
            return False
        
        # 检查冷却时间
        alert_key = f"{alert.component}:{alert.title}"
        if alert_key in self._last_alert_times:
            elapsed = (datetime.now() - self._last_alert_times[alert_key]).total_seconds()
            if elapsed < self.config.cooldown_minutes * 60:
                return False
        
        # 检查每小时限制
        now = datetime.now()
        if (now - self._hour_start).total_seconds() >= 3600:
            self._hour_start = now
            self._alert_count_hour = 0
        
        if self._alert_count_hour >= self.config.max_alerts_per_hour:
            return False
        
        return True
    
    def notify(self, alert: SystemAlert) -> bool:
        """
        发送告警通知
        
        Returns:
            是否成功发送
        """
        if not self.should_notify(alert):
            return False
        
        success = False
        
        # 记录到日志
        if "log" in self.config.notification_channels:
            self._notify_log(alert)
            success = True
        
        # 写入文件
        if "file" in self.config.notification_channels:
            self._notify_file(alert)
            success = True
        
        # 发送飞书通知
        if self.config.feishu_enabled and self.config.feishu_webhook_url:
            feishu_success = self._notify_feishu(alert)
            success = success or feishu_success
        
        # 更新统计
        if success:
            alert_key = f"{alert.component}:{alert.title}"
            self._last_alert_times[alert_key] = datetime.now()
            self._alert_count_hour += 1
        
        return success
    
    def _notify_log(self, alert: SystemAlert):
        """记录到日志"""
        log_method = {
            AlertSeverity.INFO: logger.info,
            AlertSeverity.WARNING: logger.warning,
            AlertSeverity.ERROR: logger.error,
            AlertSeverity.CRITICAL: logger.critical
        }.get(alert.severity, logger.info)
        
        log_method(f"[ALERT] [{alert.severity.value.upper()}] {alert.component}: {alert.title} - {alert.message}")
    
    def _notify_file(self, alert: SystemAlert):
        """写入告警文件"""
        try:
            alert_file = "data/alert_notifications.log"
            os.makedirs(os.path.dirname(alert_file), exist_ok=True)
            
            with open(alert_file, 'a', encoding='utf-8') as f:
                f.write(f"{alert.timestamp.isoformat()} | {alert.severity.value.upper()} | {alert.component} | {alert.title} | {alert.message}\n")
        except Exception as e:
            logger.warning(f"写入告警文件失败: {e}")
    
    def _notify_feishu(self, alert: SystemAlert) -> bool:
        """发送飞书通知"""
        try:
            import requests
            
            severity_emoji = {
                AlertSeverity.INFO: "ℹ️",
                AlertSeverity.WARNING: "⚠️",
                AlertSeverity.ERROR: "❌",
                AlertSeverity.CRITICAL: "🚨"
            }.get(alert.severity, "📢")
            
            content = f"""{severity_emoji} **系统告警**

组件: {alert.component}
级别: {alert.severity.value.upper()}
标题: {alert.title}
详情: {alert.message}
时间: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"""
            
            payload = {
                "msg_type": "text",
                "content": {"text": content}
            }
            
            response = requests.post(
                self.config.feishu_webhook_url,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("code") == 0 or result.get("StatusCode") == 0:
                    return True
            
            logger.warning(f"飞书告警发送失败: {response.text[:100]}")
            return False
            
        except ImportError:
            logger.warning("requests库未安装，无法发送飞书通知")
            return False
        except Exception as e:
            logger.warning(f"发送飞书告警失败: {e}")
            return False


class MetricsCollector:
    """
    指标收集器
    
    收集系统运行指标
    """
    
    def __init__(self):
        """初始化指标收集器"""
        self._metrics_history: List[Dict[str, Any]] = []
        self._max_history = 1000
    
    def collect_metrics(self) -> Dict[str, Any]:
        """收集当前系统指标"""
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'disk': self._collect_disk_metrics(),
            'data': self._collect_data_metrics(),
            'screening': self._collect_screening_metrics(),
            'errors': self._collect_error_metrics()
        }
        
        # 保存到历史
        self._metrics_history.append(metrics)
        if len(self._metrics_history) > self._max_history:
            self._metrics_history = self._metrics_history[-self._max_history:]
        
        return metrics
    
    def _collect_disk_metrics(self) -> Dict[str, Any]:
        """收集磁盘指标"""
        try:
            data_dir = 'data'
            if os.path.exists(data_dir):
                total_size = 0
                file_count = 0
                for root, dirs, files in os.walk(data_dir):
                    for f in files:
                        filepath = os.path.join(root, f)
                        try:
                            total_size += os.path.getsize(filepath)
                            file_count += 1
                        except:
                            pass
                
                return {
                    'data_dir_size_mb': round(total_size / (1024 * 1024), 2),
                    'file_count': file_count,
                    'status': 'ok'
                }
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
        
        return {'status': 'unknown'}
    
    def _collect_data_metrics(self) -> Dict[str, Any]:
        """收集数据指标"""
        try:
            processed_dir = 'data/processed'
            if os.path.exists(processed_dir):
                csv_files = [f for f in os.listdir(processed_dir) if f.endswith('.csv')]
                return {
                    'stock_data_files': len(csv_files),
                    'status': 'ok'
                }
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
        
        return {'status': 'unknown'}
    
    def _collect_screening_metrics(self) -> Dict[str, Any]:
        """收集筛选指标"""
        try:
            history_file = 'data/pool_update_history.json'
            if os.path.exists(history_file):
                with open(history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
                
                if history:
                    last_update = history[-1] if isinstance(history, list) else history
                    return {
                        'last_update': last_update.get('timestamp', 'unknown'),
                        'last_status': last_update.get('status', 'unknown'),
                        'status': 'ok'
                    }
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
        
        return {'status': 'unknown'}
    
    def _collect_error_metrics(self) -> Dict[str, Any]:
        """收集错误指标"""
        try:
            log_dir = 'logs'
            if os.path.exists(log_dir):
                error_count = 0
                warning_count = 0
                
                # 检查最新的日志文件
                log_files = sorted([f for f in os.listdir(log_dir) if f.endswith('.log')], reverse=True)
                if log_files:
                    latest_log = os.path.join(log_dir, log_files[0])
                    try:
                        with open(latest_log, 'r', encoding='utf-8') as f:
                            for line in f:
                                if ' ERROR ' in line:
                                    error_count += 1
                                elif ' WARNING ' in line:
                                    warning_count += 1
                    except:
                        pass
                
                return {
                    'error_count': error_count,
                    'warning_count': warning_count,
                    'status': 'ok'
                }
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
        
        return {'status': 'unknown'}
    
    def get_metrics_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取指标历史"""
        return self._metrics_history[-limit:]


class EnhancedSystemMonitor(SystemMonitor):
    """
    增强版系统监控器
    
    在基础监控功能上增加：
    - 告警通知集成
    - 指标收集
    - 阈值监控
    """
    
    def __init__(
        self,
        notification_config: Optional[AlertNotificationConfig] = None,
        thresholds: Optional[AlertThresholds] = None
    ):
        """初始化增强版系统监控器"""
        super().__init__()
        self.notifier = AlertNotifier(notification_config)
        self.thresholds = thresholds or AlertThresholds()
        self.metrics_collector = MetricsCollector()
        
        # 注册告警处理器
        self.alert_manager.add_handler(self._on_alert)
    
    def _on_alert(self, alert: SystemAlert):
        """告警处理回调"""
        self.notifier.notify(alert)
    
    def check_thresholds(self) -> List[SystemAlert]:
        """
        检查阈值并生成告警
        
        Returns:
            生成的告警列表
        """
        alerts = []
        
        # 收集指标
        metrics = self.metrics_collector.collect_metrics()
        
        # 检查磁盘使用
        disk_metrics = metrics.get('disk', {})
        if disk_metrics.get('status') == 'ok':
            size_mb = disk_metrics.get('data_dir_size_mb', 0)
            # 假设数据目录限制为10GB
            usage_percent = (size_mb / 10240) * 100
            
            if usage_percent >= self.thresholds.disk_usage_critical_percent:
                alert = self.alert_manager.create_alert(
                    severity=AlertSeverity.CRITICAL,
                    component="DiskUsage",
                    title="磁盘空间严重不足",
                    message=f"数据目录使用率达到 {usage_percent:.1f}%，请及时清理"
                )
                alerts.append(alert)
            elif usage_percent >= self.thresholds.disk_usage_warning_percent:
                alert = self.alert_manager.create_alert(
                    severity=AlertSeverity.WARNING,
                    component="DiskUsage",
                    title="磁盘空间不足",
                    message=f"数据目录使用率达到 {usage_percent:.1f}%"
                )
                alerts.append(alert)
        
        # 检查错误率
        error_metrics = metrics.get('errors', {})
        if error_metrics.get('status') == 'ok':
            error_count = error_metrics.get('error_count', 0)
            warning_count = error_metrics.get('warning_count', 0)
            
            if error_count > 100:  # 超过100个错误
                alert = self.alert_manager.create_alert(
                    severity=AlertSeverity.ERROR,
                    component="ErrorRate",
                    title="错误数量过多",
                    message=f"日志中发现 {error_count} 个错误，{warning_count} 个警告"
                )
                alerts.append(alert)
        
        return alerts
    
    def get_enhanced_status(self) -> Dict[str, Any]:
        """获取增强版系统状态"""
        base_status = self.get_system_status()
        
        # 添加指标信息
        metrics = self.metrics_collector.collect_metrics()
        base_status['metrics'] = metrics
        
        # 添加通知配置
        base_status['notification'] = self.notifier.config.to_dict()
        
        # 添加阈值配置
        base_status['thresholds'] = {
            'response_time_warning_ms': self.thresholds.response_time_warning_ms,
            'disk_usage_warning_percent': self.thresholds.disk_usage_warning_percent,
            'error_rate_warning_percent': self.thresholds.error_rate_warning_percent
        }
        
        return base_status
    
    def generate_enhanced_report(self) -> str:
        """生成增强版状态报告"""
        status = self.get_enhanced_status()
        
        lines = [
            "=" * 70,
            "系统监控状态报告（增强版）",
            "=" * 70,
            f"报告时间: {status['timestamp']}",
            f"整体健康状态: {status['overall_health']}",
            f"监控状态: {'运行中' if status['monitoring_active'] else '已停止'}",
            "",
            "【组件健康状态】",
        ]
        
        for check in status['health_checks']:
            status_icon = {
                'healthy': '✓',
                'degraded': '⚠',
                'unhealthy': '✗',
                'unknown': '?'
            }.get(check['status'], '?')
            lines.append(f"  {status_icon} {check['component']}: {check['message']}")
            if check.get('response_time_ms', 0) > 0:
                lines.append(f"      响应时间: {check['response_time_ms']:.1f}ms")
        
        lines.append("")
        lines.append("【告警摘要】")
        alerts = status['alerts']
        lines.append(f"  活跃告警: {alerts['active']}")
        lines.append(f"  - 严重: {alerts['by_severity']['critical']}")
        lines.append(f"  - 错误: {alerts['by_severity']['error']}")
        lines.append(f"  - 警告: {alerts['by_severity']['warning']}")
        lines.append(f"  - 信息: {alerts['by_severity']['info']}")
        
        lines.append("")
        lines.append("【系统指标】")
        metrics = status.get('metrics', {})
        
        disk = metrics.get('disk', {})
        if disk.get('status') == 'ok':
            lines.append(f"  数据目录大小: {disk.get('data_dir_size_mb', 0):.2f} MB")
            lines.append(f"  文件数量: {disk.get('file_count', 0)}")
        
        data = metrics.get('data', {})
        if data.get('status') == 'ok':
            lines.append(f"  股票数据文件: {data.get('stock_data_files', 0)}")
        
        errors = metrics.get('errors', {})
        if errors.get('status') == 'ok':
            lines.append(f"  日志错误数: {errors.get('error_count', 0)}")
            lines.append(f"  日志警告数: {errors.get('warning_count', 0)}")
        
        lines.append("")
        lines.append("【维护任务】")
        maint = status['maintenance']
        lines.append(f"  总任务数: {maint['total_tasks']}")
        lines.append(f"  待执行: {maint['pending_tasks']}")
        lines.append(f"  已启用: {maint['enabled_tasks']}")
        
        lines.append("")
        lines.append("【通知配置】")
        notif = status.get('notification', {})
        lines.append(f"  通知启用: {'是' if notif.get('enabled') else '否'}")
        lines.append(f"  最低告警级别: {notif.get('min_severity', 'warning')}")
        lines.append(f"  飞书通知: {'已配置' if notif.get('feishu_enabled') else '未配置'}")
        
        lines.append("=" * 70)
        
        return "\n".join(lines)


# 增强版全局实例
_enhanced_monitor: Optional[EnhancedSystemMonitor] = None
_alert_notifier: Optional[AlertNotifier] = None
_metrics_collector: Optional[MetricsCollector] = None


def get_enhanced_system_monitor(
    notification_config: Optional[AlertNotificationConfig] = None,
    thresholds: Optional[AlertThresholds] = None
) -> EnhancedSystemMonitor:
    """获取增强版系统监控器实例"""
    global _enhanced_monitor
    if _enhanced_monitor is None:
        _enhanced_monitor = EnhancedSystemMonitor(notification_config, thresholds)
    return _enhanced_monitor


def get_alert_notifier(config: Optional[AlertNotificationConfig] = None) -> AlertNotifier:
    """获取告警通知器实例"""
    global _alert_notifier
    if _alert_notifier is None:
        _alert_notifier = AlertNotifier(config)
    return _alert_notifier


def get_metrics_collector() -> MetricsCollector:
    """获取指标收集器实例"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def reset_enhanced_monitor() -> None:
    """重置增强版监控器"""
    global _enhanced_monitor, _alert_notifier, _metrics_collector
    _enhanced_monitor = None
    _alert_notifier = None
    _metrics_collector = None


def start_system_monitoring(
    interval_seconds: int = 300,
    notification_config: Optional[AlertNotificationConfig] = None,
    thresholds: Optional[AlertThresholds] = None
) -> EnhancedSystemMonitor:
    """
    启动系统监控
    
    便捷函数，用于快速启动监控
    
    Args:
        interval_seconds: 监控间隔（秒）
        notification_config: 告警通知配置
        thresholds: 告警阈值配置
    
    Returns:
        增强版系统监控器实例
    """
    monitor = get_enhanced_system_monitor(notification_config, thresholds)
    monitor.start_monitoring(interval_seconds)
    return monitor


def stop_system_monitoring() -> None:
    """停止系统监控"""
    global _enhanced_monitor
    if _enhanced_monitor is not None:
        _enhanced_monitor.stop_monitoring()


def get_system_health_summary() -> Dict[str, Any]:
    """
    获取系统健康摘要
    
    便捷函数，用于快速获取系统状态
    """
    monitor = get_enhanced_system_monitor()
    return monitor.get_enhanced_status()


def generate_monitoring_report() -> str:
    """
    生成监控报告
    
    便捷函数，用于快速生成报告
    """
    monitor = get_enhanced_system_monitor()
    return monitor.generate_enhanced_report()
