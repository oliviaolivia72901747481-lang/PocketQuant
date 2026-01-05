"""
渐进式上线策略模块

提供股票池扩充的渐进式上线功能，包括：
- 分阶段上线控制
- 灰度发布机制
- 上线进度监控
- 回滚支持
- A/B测试支持

Requirements: 业务风险 - 实现渐进式上线策略
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Callable
from enum import Enum
from datetime import datetime, timedelta
import logging
import os
import json
import random
import shutil

logger = logging.getLogger(__name__)


class RolloutPhase(Enum):
    """上线阶段"""
    NOT_STARTED = "not_started"      # 未开始
    CANARY = "canary"                # 金丝雀发布（5-10%）
    EARLY_ADOPTER = "early_adopter"  # 早期采用（25%）
    GRADUAL = "gradual"              # 渐进扩展（50%）
    MAJORITY = "majority"            # 大多数（75%）
    FULL = "full"                    # 全量发布（100%）
    ROLLBACK = "rollback"            # 回滚状态


class RolloutStatus(Enum):
    """上线状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class RolloutConfig:
    """上线配置"""
    # 各阶段的股票比例
    canary_percent: float = 10.0
    early_adopter_percent: float = 25.0
    gradual_percent: float = 50.0
    majority_percent: float = 75.0
    
    # 各阶段最小观察时间（小时）
    canary_observation_hours: int = 24
    early_adopter_observation_hours: int = 48
    gradual_observation_hours: int = 72
    majority_observation_hours: int = 24
    
    # 自动推进条件
    auto_advance: bool = False
    max_error_rate: float = 5.0  # 最大错误率（%）
    min_success_rate: float = 95.0  # 最小成功率（%）
    
    # 回滚条件
    auto_rollback_on_error: bool = True
    rollback_error_threshold: int = 3  # 连续错误次数触发回滚
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'canary_percent': self.canary_percent,
            'early_adopter_percent': self.early_adopter_percent,
            'gradual_percent': self.gradual_percent,
            'majority_percent': self.majority_percent,
            'canary_observation_hours': self.canary_observation_hours,
            'early_adopter_observation_hours': self.early_adopter_observation_hours,
            'gradual_observation_hours': self.gradual_observation_hours,
            'majority_observation_hours': self.majority_observation_hours,
            'auto_advance': self.auto_advance,
            'max_error_rate': self.max_error_rate,
            'min_success_rate': self.min_success_rate,
            'auto_rollback_on_error': self.auto_rollback_on_error,
            'rollback_error_threshold': self.rollback_error_threshold
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RolloutConfig':
        """从字典创建"""
        return cls(
            canary_percent=data.get('canary_percent', 10.0),
            early_adopter_percent=data.get('early_adopter_percent', 25.0),
            gradual_percent=data.get('gradual_percent', 50.0),
            majority_percent=data.get('majority_percent', 75.0),
            canary_observation_hours=data.get('canary_observation_hours', 24),
            early_adopter_observation_hours=data.get('early_adopter_observation_hours', 48),
            gradual_observation_hours=data.get('gradual_observation_hours', 72),
            majority_observation_hours=data.get('majority_observation_hours', 24),
            auto_advance=data.get('auto_advance', False),
            max_error_rate=data.get('max_error_rate', 5.0),
            min_success_rate=data.get('min_success_rate', 95.0),
            auto_rollback_on_error=data.get('auto_rollback_on_error', True),
            rollback_error_threshold=data.get('rollback_error_threshold', 3)
        )


@dataclass
class PhaseMetrics:
    """阶段指标"""
    phase: RolloutPhase
    start_time: datetime
    end_time: Optional[datetime] = None
    stocks_count: int = 0
    success_count: int = 0
    error_count: int = 0
    warning_count: int = 0
    data_quality_score: float = 0.0
    performance_score: float = 0.0
    user_feedback_score: float = 0.0
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        total = self.success_count + self.error_count
        return (self.success_count / total * 100) if total > 0 else 100.0
    
    @property
    def error_rate(self) -> float:
        """错误率"""
        total = self.success_count + self.error_count
        return (self.error_count / total * 100) if total > 0 else 0.0
    
    @property
    def duration_hours(self) -> float:
        """持续时间（小时）"""
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds() / 3600
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'phase': self.phase.value,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'stocks_count': self.stocks_count,
            'success_count': self.success_count,
            'error_count': self.error_count,
            'warning_count': self.warning_count,
            'data_quality_score': self.data_quality_score,
            'performance_score': self.performance_score,
            'user_feedback_score': self.user_feedback_score,
            'success_rate': self.success_rate,
            'error_rate': self.error_rate,
            'duration_hours': self.duration_hours
        }


@dataclass
class RolloutState:
    """上线状态"""
    rollout_id: str
    status: RolloutStatus
    current_phase: RolloutPhase
    config: RolloutConfig
    created_at: datetime
    updated_at: datetime
    
    # 股票池信息
    original_pool: List[str] = field(default_factory=list)
    new_pool: List[str] = field(default_factory=list)
    active_pool: List[str] = field(default_factory=list)
    
    # 阶段历史
    phase_history: List[PhaseMetrics] = field(default_factory=list)
    
    # 错误追踪
    consecutive_errors: int = 0
    last_error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'rollout_id': self.rollout_id,
            'status': self.status.value,
            'current_phase': self.current_phase.value,
            'config': self.config.to_dict(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'original_pool': self.original_pool,
            'new_pool': self.new_pool,
            'active_pool': self.active_pool,
            'phase_history': [p.to_dict() for p in self.phase_history],
            'consecutive_errors': self.consecutive_errors,
            'last_error': self.last_error
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RolloutState':
        """从字典创建"""
        phase_history = []
        for ph in data.get('phase_history', []):
            phase_history.append(PhaseMetrics(
                phase=RolloutPhase(ph['phase']),
                start_time=datetime.fromisoformat(ph['start_time']),
                end_time=datetime.fromisoformat(ph['end_time']) if ph.get('end_time') else None,
                stocks_count=ph.get('stocks_count', 0),
                success_count=ph.get('success_count', 0),
                error_count=ph.get('error_count', 0),
                warning_count=ph.get('warning_count', 0),
                data_quality_score=ph.get('data_quality_score', 0.0),
                performance_score=ph.get('performance_score', 0.0),
                user_feedback_score=ph.get('user_feedback_score', 0.0)
            ))
        
        return cls(
            rollout_id=data['rollout_id'],
            status=RolloutStatus(data['status']),
            current_phase=RolloutPhase(data['current_phase']),
            config=RolloutConfig.from_dict(data.get('config', {})),
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
            original_pool=data.get('original_pool', []),
            new_pool=data.get('new_pool', []),
            active_pool=data.get('active_pool', []),
            phase_history=phase_history,
            consecutive_errors=data.get('consecutive_errors', 0),
            last_error=data.get('last_error')
        )



class GradualRolloutManager:
    """
    渐进式上线管理器
    
    管理股票池扩充的渐进式上线过程
    
    Requirements: 业务风险 - 实现渐进式上线策略
    """
    
    def __init__(
        self,
        state_file: str = "data/rollout_state.json",
        backup_dir: str = "data/pool_backups"
    ):
        """
        初始化渐进式上线管理器
        
        Args:
            state_file: 状态文件路径
            backup_dir: 备份目录路径
        """
        self.state_file = state_file
        self.backup_dir = backup_dir
        self.current_state: Optional[RolloutState] = None
        self._load_state()
    
    def start_rollout(
        self,
        original_pool: List[str],
        new_pool: List[str],
        config: Optional[RolloutConfig] = None
    ) -> RolloutState:
        """
        开始渐进式上线
        
        Args:
            original_pool: 原始股票池
            new_pool: 新股票池
            config: 上线配置
        
        Returns:
            RolloutState: 上线状态
        """
        if self.current_state and self.current_state.status == RolloutStatus.IN_PROGRESS:
            raise ValueError("已有正在进行的上线任务，请先完成或取消")
        
        # 创建备份
        self._backup_current_pool(original_pool)
        
        # 创建新的上线状态
        rollout_id = datetime.now().strftime("ROLLOUT_%Y%m%d_%H%M%S")
        config = config or RolloutConfig()
        
        self.current_state = RolloutState(
            rollout_id=rollout_id,
            status=RolloutStatus.IN_PROGRESS,
            current_phase=RolloutPhase.NOT_STARTED,
            config=config,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            original_pool=original_pool.copy(),
            new_pool=new_pool.copy(),
            active_pool=original_pool.copy()
        )
        
        self._save_state()
        logger.info(f"开始渐进式上线: {rollout_id}")
        
        return self.current_state
    
    def advance_to_next_phase(self) -> Tuple[bool, str]:
        """
        推进到下一阶段
        
        Returns:
            Tuple[是否成功, 消息]
        """
        if not self.current_state:
            return False, "没有正在进行的上线任务"
        
        if self.current_state.status != RolloutStatus.IN_PROGRESS:
            return False, f"上线状态不正确: {self.current_state.status.value}"
        
        # 检查当前阶段是否满足推进条件
        can_advance, reason = self._check_advance_conditions()
        if not can_advance:
            return False, reason
        
        # 结束当前阶段
        if self.current_state.phase_history:
            self.current_state.phase_history[-1].end_time = datetime.now()
        
        # 确定下一阶段
        next_phase = self._get_next_phase()
        if next_phase is None:
            return False, "已经是最后阶段"
        
        # 计算新阶段的股票池
        new_active_pool = self._calculate_phase_pool(next_phase)
        
        # 创建新阶段指标
        phase_metrics = PhaseMetrics(
            phase=next_phase,
            start_time=datetime.now(),
            stocks_count=len(new_active_pool)
        )
        
        # 更新状态
        self.current_state.current_phase = next_phase
        self.current_state.active_pool = new_active_pool
        self.current_state.phase_history.append(phase_metrics)
        self.current_state.updated_at = datetime.now()
        
        # 如果是全量发布，标记完成
        if next_phase == RolloutPhase.FULL:
            self.current_state.status = RolloutStatus.COMPLETED
        
        self._save_state()
        logger.info(f"推进到阶段: {next_phase.value}, 股票数: {len(new_active_pool)}")
        
        return True, f"成功推进到 {next_phase.value} 阶段"
    
    def pause_rollout(self) -> Tuple[bool, str]:
        """
        暂停上线
        
        Returns:
            Tuple[是否成功, 消息]
        """
        if not self.current_state:
            return False, "没有正在进行的上线任务"
        
        if self.current_state.status != RolloutStatus.IN_PROGRESS:
            return False, f"无法暂停: 当前状态为 {self.current_state.status.value}"
        
        self.current_state.status = RolloutStatus.PAUSED
        self.current_state.updated_at = datetime.now()
        self._save_state()
        
        logger.info(f"上线已暂停: {self.current_state.rollout_id}")
        return True, "上线已暂停"
    
    def resume_rollout(self) -> Tuple[bool, str]:
        """
        恢复上线
        
        Returns:
            Tuple[是否成功, 消息]
        """
        if not self.current_state:
            return False, "没有正在进行的上线任务"
        
        if self.current_state.status != RolloutStatus.PAUSED:
            return False, f"无法恢复: 当前状态为 {self.current_state.status.value}"
        
        self.current_state.status = RolloutStatus.IN_PROGRESS
        self.current_state.updated_at = datetime.now()
        self._save_state()
        
        logger.info(f"上线已恢复: {self.current_state.rollout_id}")
        return True, "上线已恢复"
    
    def rollback(self, reason: str = "") -> Tuple[bool, str]:
        """
        回滚到原始状态
        
        Args:
            reason: 回滚原因
        
        Returns:
            Tuple[是否成功, 消息]
        """
        if not self.current_state:
            return False, "没有正在进行的上线任务"
        
        # 恢复原始股票池
        self.current_state.active_pool = self.current_state.original_pool.copy()
        self.current_state.current_phase = RolloutPhase.ROLLBACK
        self.current_state.status = RolloutStatus.ROLLED_BACK
        self.current_state.last_error = reason
        self.current_state.updated_at = datetime.now()
        
        # 结束当前阶段
        if self.current_state.phase_history:
            self.current_state.phase_history[-1].end_time = datetime.now()
        
        self._save_state()
        logger.warning(f"上线已回滚: {self.current_state.rollout_id}, 原因: {reason}")
        
        return True, f"已回滚到原始状态: {reason}"
    
    def record_success(self) -> None:
        """记录成功操作"""
        if self.current_state and self.current_state.phase_history:
            self.current_state.phase_history[-1].success_count += 1
            self.current_state.consecutive_errors = 0
            self._save_state()
    
    def record_error(self, error_msg: str) -> Tuple[bool, str]:
        """
        记录错误操作
        
        Args:
            error_msg: 错误消息
        
        Returns:
            Tuple[是否触发回滚, 消息]
        """
        if not self.current_state:
            return False, "没有正在进行的上线任务"
        
        if self.current_state.phase_history:
            self.current_state.phase_history[-1].error_count += 1
        
        self.current_state.consecutive_errors += 1
        self.current_state.last_error = error_msg
        self._save_state()
        
        # 检查是否需要自动回滚
        if (self.current_state.config.auto_rollback_on_error and 
            self.current_state.consecutive_errors >= self.current_state.config.rollback_error_threshold):
            self.rollback(f"连续错误达到阈值: {error_msg}")
            return True, "已触发自动回滚"
        
        return False, "错误已记录"
    
    def record_warning(self) -> None:
        """记录警告"""
        if self.current_state and self.current_state.phase_history:
            self.current_state.phase_history[-1].warning_count += 1
            self._save_state()
    
    def update_metrics(
        self,
        data_quality_score: Optional[float] = None,
        performance_score: Optional[float] = None,
        user_feedback_score: Optional[float] = None
    ) -> None:
        """
        更新阶段指标
        
        Args:
            data_quality_score: 数据质量评分
            performance_score: 性能评分
            user_feedback_score: 用户反馈评分
        """
        if not self.current_state or not self.current_state.phase_history:
            return
        
        current_metrics = self.current_state.phase_history[-1]
        
        if data_quality_score is not None:
            current_metrics.data_quality_score = data_quality_score
        if performance_score is not None:
            current_metrics.performance_score = performance_score
        if user_feedback_score is not None:
            current_metrics.user_feedback_score = user_feedback_score
        
        self._save_state()
    
    def get_current_pool(self) -> List[str]:
        """
        获取当前活跃的股票池
        
        Returns:
            当前活跃的股票代码列表
        """
        if self.current_state:
            return self.current_state.active_pool.copy()
        return []
    
    def get_rollout_progress(self) -> Dict[str, Any]:
        """
        获取上线进度
        
        Returns:
            上线进度信息
        """
        if not self.current_state:
            return {
                'has_active_rollout': False,
                'message': '没有正在进行的上线任务'
            }
        
        phase_order = [
            RolloutPhase.NOT_STARTED,
            RolloutPhase.CANARY,
            RolloutPhase.EARLY_ADOPTER,
            RolloutPhase.GRADUAL,
            RolloutPhase.MAJORITY,
            RolloutPhase.FULL
        ]
        
        current_idx = phase_order.index(self.current_state.current_phase) if self.current_state.current_phase in phase_order else 0
        total_phases = len(phase_order) - 1  # 不包括 NOT_STARTED
        progress_percent = (current_idx / total_phases) * 100 if total_phases > 0 else 0
        
        return {
            'has_active_rollout': True,
            'rollout_id': self.current_state.rollout_id,
            'status': self.current_state.status.value,
            'current_phase': self.current_state.current_phase.value,
            'progress_percent': progress_percent,
            'original_pool_size': len(self.current_state.original_pool),
            'new_pool_size': len(self.current_state.new_pool),
            'active_pool_size': len(self.current_state.active_pool),
            'created_at': self.current_state.created_at.isoformat(),
            'updated_at': self.current_state.updated_at.isoformat(),
            'consecutive_errors': self.current_state.consecutive_errors,
            'last_error': self.current_state.last_error,
            'phase_history': [p.to_dict() for p in self.current_state.phase_history]
        }
    
    def _check_advance_conditions(self) -> Tuple[bool, str]:
        """检查是否满足推进条件"""
        if not self.current_state.phase_history:
            return True, "首次推进"
        
        current_metrics = self.current_state.phase_history[-1]
        config = self.current_state.config
        
        # 获取当前阶段的最小观察时间
        observation_hours = {
            RolloutPhase.CANARY: config.canary_observation_hours,
            RolloutPhase.EARLY_ADOPTER: config.early_adopter_observation_hours,
            RolloutPhase.GRADUAL: config.gradual_observation_hours,
            RolloutPhase.MAJORITY: config.majority_observation_hours,
        }.get(self.current_state.current_phase, 0)
        
        # 检查观察时间
        if current_metrics.duration_hours < observation_hours:
            return False, f"观察时间不足: {current_metrics.duration_hours:.1f}/{observation_hours}小时"
        
        # 检查错误率
        if current_metrics.error_rate > config.max_error_rate:
            return False, f"错误率过高: {current_metrics.error_rate:.1f}% > {config.max_error_rate}%"
        
        # 检查成功率
        if current_metrics.success_rate < config.min_success_rate:
            return False, f"成功率不足: {current_metrics.success_rate:.1f}% < {config.min_success_rate}%"
        
        return True, "满足推进条件"
    
    def _get_next_phase(self) -> Optional[RolloutPhase]:
        """获取下一阶段"""
        phase_sequence = [
            RolloutPhase.NOT_STARTED,
            RolloutPhase.CANARY,
            RolloutPhase.EARLY_ADOPTER,
            RolloutPhase.GRADUAL,
            RolloutPhase.MAJORITY,
            RolloutPhase.FULL
        ]
        
        try:
            current_idx = phase_sequence.index(self.current_state.current_phase)
            if current_idx < len(phase_sequence) - 1:
                return phase_sequence[current_idx + 1]
        except ValueError:
            return RolloutPhase.CANARY
        
        return None
    
    def _calculate_phase_pool(self, phase: RolloutPhase) -> List[str]:
        """计算指定阶段的股票池"""
        if not self.current_state:
            return []
        
        original = set(self.current_state.original_pool)
        new = set(self.current_state.new_pool)
        
        # 计算新增股票
        added_stocks = list(new - original)
        
        # 根据阶段确定比例
        percent = {
            RolloutPhase.CANARY: self.current_state.config.canary_percent,
            RolloutPhase.EARLY_ADOPTER: self.current_state.config.early_adopter_percent,
            RolloutPhase.GRADUAL: self.current_state.config.gradual_percent,
            RolloutPhase.MAJORITY: self.current_state.config.majority_percent,
            RolloutPhase.FULL: 100.0
        }.get(phase, 0)
        
        # 计算要包含的新增股票数量
        num_to_include = int(len(added_stocks) * percent / 100)
        
        # 随机选择新增股票（保持一致性，使用排序后的列表）
        added_stocks.sort()
        selected_new = added_stocks[:num_to_include]
        
        # 合并原始股票和选中的新增股票
        result = list(original) + selected_new
        result.sort()
        
        return result
    
    def _backup_current_pool(self, pool: List[str]) -> str:
        """备份当前股票池"""
        os.makedirs(self.backup_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(self.backup_dir, f"pool_backup_{timestamp}.json")
        
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': timestamp,
                'pool': pool,
                'count': len(pool)
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"股票池已备份: {backup_file}")
        return backup_file
    
    def _load_state(self) -> None:
        """加载状态"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.current_state = RolloutState.from_dict(data)
                    logger.info(f"加载上线状态: {self.current_state.rollout_id}")
        except Exception as e:
            logger.warning(f"加载上线状态失败: {e}")
            self.current_state = None
    
    def _save_state(self) -> None:
        """保存状态"""
        if not self.current_state:
            return
        
        try:
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.current_state.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存上线状态失败: {e}")



class RolloutValidator:
    """
    上线验证器
    
    验证各阶段的上线效果
    """
    
    def __init__(self):
        """初始化上线验证器"""
        pass
    
    def validate_phase(
        self,
        phase: RolloutPhase,
        active_pool: List[str],
        original_pool: List[str]
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        验证阶段效果
        
        Args:
            phase: 当前阶段
            active_pool: 活跃股票池
            original_pool: 原始股票池
        
        Returns:
            Tuple[是否通过, 验证详情]
        """
        results = {
            'phase': phase.value,
            'timestamp': datetime.now().isoformat(),
            'checks': []
        }
        
        passed = True
        
        # 检查1: 股票池完整性
        integrity_check = self._check_pool_integrity(active_pool, original_pool)
        results['checks'].append(integrity_check)
        if not integrity_check['passed']:
            passed = False
        
        # 检查2: 数据可用性
        data_check = self._check_data_availability(active_pool)
        results['checks'].append(data_check)
        if not data_check['passed']:
            passed = False
        
        # 检查3: 配置一致性
        config_check = self._check_config_consistency(active_pool)
        results['checks'].append(config_check)
        if not config_check['passed']:
            passed = False
        
        results['passed'] = passed
        return passed, results
    
    def _check_pool_integrity(
        self,
        active_pool: List[str],
        original_pool: List[str]
    ) -> Dict[str, Any]:
        """检查股票池完整性"""
        # 确保原始股票都在活跃池中
        original_set = set(original_pool)
        active_set = set(active_pool)
        
        missing = original_set - active_set
        
        return {
            'name': '股票池完整性',
            'passed': len(missing) == 0,
            'message': f"原始股票全部保留" if len(missing) == 0 else f"缺失{len(missing)}只原始股票",
            'details': {
                'original_count': len(original_pool),
                'active_count': len(active_pool),
                'missing_count': len(missing),
                'missing_stocks': list(missing)[:10]  # 最多显示10只
            }
        }
    
    def _check_data_availability(self, active_pool: List[str]) -> Dict[str, Any]:
        """检查数据可用性"""
        data_dir = 'data/processed'
        available = 0
        missing = []
        
        for code in active_pool:
            file_path = os.path.join(data_dir, f"{code}.csv")
            if os.path.exists(file_path):
                available += 1
            else:
                missing.append(code)
        
        availability_rate = (available / len(active_pool) * 100) if active_pool else 100
        
        return {
            'name': '数据可用性',
            'passed': availability_rate >= 90,  # 90%以上数据可用
            'message': f"数据可用率: {availability_rate:.1f}%",
            'details': {
                'total': len(active_pool),
                'available': available,
                'missing': len(missing),
                'missing_stocks': missing[:10]
            }
        }
    
    def _check_config_consistency(self, active_pool: List[str]) -> Dict[str, Any]:
        """检查配置一致性"""
        try:
            from config.tech_stock_pool import get_tech_stock_pool
            pool = get_tech_stock_pool()
            
            # 检查股票池是否可以正常访问
            all_codes = pool.get_all_codes()
            
            return {
                'name': '配置一致性',
                'passed': True,
                'message': f"配置正常，共{len(all_codes)}只股票",
                'details': {
                    'config_count': len(all_codes),
                    'active_count': len(active_pool)
                }
            }
        except Exception as e:
            return {
                'name': '配置一致性',
                'passed': False,
                'message': f"配置检查失败: {e}",
                'details': {'error': str(e)}
            }


class RolloutReporter:
    """
    上线报告生成器
    
    生成上线进度和状态报告
    """
    
    def __init__(self, manager: GradualRolloutManager):
        """初始化报告生成器"""
        self.manager = manager
    
    def generate_progress_report(self) -> str:
        """生成进度报告"""
        progress = self.manager.get_rollout_progress()
        
        if not progress.get('has_active_rollout'):
            return "当前没有正在进行的上线任务"
        
        lines = [
            "=" * 60,
            "渐进式上线进度报告",
            "=" * 60,
            f"上线ID: {progress['rollout_id']}",
            f"状态: {progress['status']}",
            f"当前阶段: {progress['current_phase']}",
            f"进度: {progress['progress_percent']:.1f}%",
            "",
            "股票池信息:",
            f"  原始股票数: {progress['original_pool_size']}",
            f"  目标股票数: {progress['new_pool_size']}",
            f"  当前活跃数: {progress['active_pool_size']}",
            "",
            f"创建时间: {progress['created_at']}",
            f"更新时间: {progress['updated_at']}",
        ]
        
        if progress['consecutive_errors'] > 0:
            lines.append("")
            lines.append(f"⚠️ 连续错误: {progress['consecutive_errors']}")
            if progress['last_error']:
                lines.append(f"最后错误: {progress['last_error']}")
        
        if progress['phase_history']:
            lines.append("")
            lines.append("阶段历史:")
            for ph in progress['phase_history']:
                status_icon = "✓" if ph.get('end_time') else "→"
                lines.append(f"  {status_icon} {ph['phase']}: {ph['stocks_count']}只股票")
                lines.append(f"      成功率: {ph['success_rate']:.1f}%, 持续: {ph['duration_hours']:.1f}小时")
        
        lines.append("=" * 60)
        return "\n".join(lines)
    
    def generate_phase_report(self, phase_metrics: PhaseMetrics) -> str:
        """生成阶段报告"""
        lines = [
            f"阶段报告: {phase_metrics.phase.value}",
            "-" * 40,
            f"开始时间: {phase_metrics.start_time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"持续时间: {phase_metrics.duration_hours:.1f}小时",
            f"股票数量: {phase_metrics.stocks_count}",
            "",
            "操作统计:",
            f"  成功: {phase_metrics.success_count}",
            f"  错误: {phase_metrics.error_count}",
            f"  警告: {phase_metrics.warning_count}",
            f"  成功率: {phase_metrics.success_rate:.1f}%",
            "",
            "质量指标:",
            f"  数据质量: {phase_metrics.data_quality_score:.1f}",
            f"  性能评分: {phase_metrics.performance_score:.1f}",
            f"  用户反馈: {phase_metrics.user_feedback_score:.1f}",
        ]
        
        return "\n".join(lines)
    
    def generate_summary_report(self) -> str:
        """生成总结报告"""
        if not self.manager.current_state:
            return "没有上线记录"
        
        state = self.manager.current_state
        
        lines = [
            "=" * 60,
            "渐进式上线总结报告",
            "=" * 60,
            f"上线ID: {state.rollout_id}",
            f"最终状态: {state.status.value}",
            "",
            "股票池变化:",
            f"  原始: {len(state.original_pool)}只",
            f"  目标: {len(state.new_pool)}只",
            f"  最终: {len(state.active_pool)}只",
            f"  新增: {len(set(state.active_pool) - set(state.original_pool))}只",
            "",
            "阶段统计:",
        ]
        
        total_success = 0
        total_error = 0
        total_duration = 0
        
        for ph in state.phase_history:
            total_success += ph.success_count
            total_error += ph.error_count
            total_duration += ph.duration_hours
            lines.append(f"  {ph.phase.value}: {ph.success_rate:.1f}%成功率, {ph.duration_hours:.1f}小时")
        
        lines.append("")
        lines.append("总体统计:")
        lines.append(f"  总成功操作: {total_success}")
        lines.append(f"  总错误操作: {total_error}")
        lines.append(f"  总耗时: {total_duration:.1f}小时")
        
        overall_success_rate = (total_success / (total_success + total_error) * 100) if (total_success + total_error) > 0 else 100
        lines.append(f"  总体成功率: {overall_success_rate:.1f}%")
        
        lines.append("=" * 60)
        return "\n".join(lines)


# 全局实例
_rollout_manager: Optional[GradualRolloutManager] = None
_rollout_validator: Optional[RolloutValidator] = None
_rollout_reporter: Optional[RolloutReporter] = None


def get_rollout_manager() -> GradualRolloutManager:
    """获取渐进式上线管理器实例"""
    global _rollout_manager
    if _rollout_manager is None:
        _rollout_manager = GradualRolloutManager()
    return _rollout_manager


def get_rollout_validator() -> RolloutValidator:
    """获取上线验证器实例"""
    global _rollout_validator
    if _rollout_validator is None:
        _rollout_validator = RolloutValidator()
    return _rollout_validator


def get_rollout_reporter() -> RolloutReporter:
    """获取上线报告生成器实例"""
    global _rollout_reporter
    if _rollout_reporter is None:
        _rollout_reporter = RolloutReporter(get_rollout_manager())
    return _rollout_reporter


def reset_rollout_manager() -> None:
    """重置渐进式上线管理器（主要用于测试）"""
    global _rollout_manager, _rollout_validator, _rollout_reporter
    _rollout_manager = None
    _rollout_validator = None
    _rollout_reporter = None


# 便捷函数
def start_gradual_rollout(
    original_pool: List[str],
    new_pool: List[str],
    config: Optional[RolloutConfig] = None
) -> RolloutState:
    """
    开始渐进式上线
    
    便捷函数，用于快速启动上线流程
    
    Args:
        original_pool: 原始股票池
        new_pool: 新股票池
        config: 上线配置
    
    Returns:
        RolloutState: 上线状态
    """
    manager = get_rollout_manager()
    return manager.start_rollout(original_pool, new_pool, config)


def advance_rollout() -> Tuple[bool, str]:
    """
    推进上线到下一阶段
    
    便捷函数
    
    Returns:
        Tuple[是否成功, 消息]
    """
    manager = get_rollout_manager()
    return manager.advance_to_next_phase()


def rollback_rollout(reason: str = "") -> Tuple[bool, str]:
    """
    回滚上线
    
    便捷函数
    
    Args:
        reason: 回滚原因
    
    Returns:
        Tuple[是否成功, 消息]
    """
    manager = get_rollout_manager()
    return manager.rollback(reason)


def get_rollout_status() -> Dict[str, Any]:
    """
    获取上线状态
    
    便捷函数
    
    Returns:
        上线状态信息
    """
    manager = get_rollout_manager()
    return manager.get_rollout_progress()


def get_active_pool() -> List[str]:
    """
    获取当前活跃的股票池
    
    便捷函数
    
    Returns:
        当前活跃的股票代码列表
    """
    manager = get_rollout_manager()
    return manager.get_current_pool()
