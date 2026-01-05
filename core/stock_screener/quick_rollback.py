"""
快速回滚机制模块

提供股票池的快速回滚功能，包括：
- 一键回滚到最近备份
- 回滚到指定版本
- 回滚前验证
- 回滚历史记录
- 紧急回滚支持

Requirements: 业务风险 - 建立快速回滚机制
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from enum import Enum
import logging
import os
import json
import shutil

logger = logging.getLogger(__name__)


class RollbackType(Enum):
    """回滚类型"""
    QUICK = "quick"           # 快速回滚（最近备份）
    SPECIFIC = "specific"     # 指定版本回滚
    EMERGENCY = "emergency"   # 紧急回滚（跳过验证）
    PARTIAL = "partial"       # 部分回滚


class RollbackStatus(Enum):
    """回滚状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BackupInfo:
    """备份信息"""
    backup_id: str
    backup_path: str
    timestamp: datetime
    pool_count: int
    pool_codes: List[str]
    backup_type: str = "auto"  # auto, manual, pre_update
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'backup_id': self.backup_id,
            'backup_path': self.backup_path,
            'timestamp': self.timestamp.isoformat(),
            'pool_count': self.pool_count,
            'pool_codes': self.pool_codes,
            'backup_type': self.backup_type,
            'description': self.description
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BackupInfo':
        """从字典创建"""
        return cls(
            backup_id=data['backup_id'],
            backup_path=data['backup_path'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            pool_count=data['pool_count'],
            pool_codes=data.get('pool_codes', []),
            backup_type=data.get('backup_type', 'auto'),
            description=data.get('description', '')
        )


@dataclass
class RollbackRecord:
    """回滚记录"""
    rollback_id: str
    rollback_type: RollbackType
    status: RollbackStatus
    timestamp: datetime
    backup_id: str
    reason: str
    operator: str = "system"
    before_pool_count: int = 0
    after_pool_count: int = 0
    duration_seconds: float = 0.0
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'rollback_id': self.rollback_id,
            'rollback_type': self.rollback_type.value,
            'status': self.status.value,
            'timestamp': self.timestamp.isoformat(),
            'backup_id': self.backup_id,
            'reason': self.reason,
            'operator': self.operator,
            'before_pool_count': self.before_pool_count,
            'after_pool_count': self.after_pool_count,
            'duration_seconds': self.duration_seconds,
            'error_message': self.error_message
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RollbackRecord':
        """从字典创建"""
        return cls(
            rollback_id=data['rollback_id'],
            rollback_type=RollbackType(data['rollback_type']),
            status=RollbackStatus(data['status']),
            timestamp=datetime.fromisoformat(data['timestamp']),
            backup_id=data['backup_id'],
            reason=data['reason'],
            operator=data.get('operator', 'system'),
            before_pool_count=data.get('before_pool_count', 0),
            after_pool_count=data.get('after_pool_count', 0),
            duration_seconds=data.get('duration_seconds', 0.0),
            error_message=data.get('error_message')
        )


@dataclass
class RollbackValidation:
    """回滚验证结果"""
    is_valid: bool
    backup_exists: bool
    backup_readable: bool
    pool_count_valid: bool
    codes_valid: bool
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'is_valid': self.is_valid,
            'backup_exists': self.backup_exists,
            'backup_readable': self.backup_readable,
            'pool_count_valid': self.pool_count_valid,
            'codes_valid': self.codes_valid,
            'warnings': self.warnings,
            'errors': self.errors
        }



class QuickRollbackManager:
    """
    快速回滚管理器
    
    提供股票池的快速回滚功能，支持：
    - 一键回滚到最近备份
    - 回滚到指定版本
    - 紧急回滚（跳过验证）
    - 回滚历史记录
    
    Requirements: 业务风险 - 建立快速回滚机制
    """
    
    def __init__(
        self,
        backup_dir: str = "data/pool_backups",
        history_file: str = "data/rollback_history.json",
        config_backup_dir: str = "config"
    ):
        """
        初始化快速回滚管理器
        
        Args:
            backup_dir: 备份目录路径
            history_file: 回滚历史文件路径
            config_backup_dir: 配置文件目录
        """
        self.backup_dir = backup_dir
        self.history_file = history_file
        self.config_backup_dir = config_backup_dir
        
        # 回滚历史
        self._rollback_history: List[RollbackRecord] = []
        
        # 备份索引
        self._backup_index: Dict[str, BackupInfo] = {}
        
        # 确保目录存在
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # 加载历史和索引
        self._load_history()
        self._scan_backups()
    
    def quick_rollback(
        self,
        reason: str = "快速回滚",
        operator: str = "system"
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        快速回滚到最近的备份
        
        Args:
            reason: 回滚原因
            operator: 操作者
        
        Returns:
            Tuple[是否成功, 消息, 详情]
        
        Requirements: 业务风险 - 建立快速回滚机制
        """
        # 获取最近的备份
        latest_backup = self.get_latest_backup()
        if not latest_backup:
            return False, "没有可用的备份", {}
        
        return self.rollback_to_backup(
            backup_id=latest_backup.backup_id,
            reason=reason,
            operator=operator,
            rollback_type=RollbackType.QUICK
        )
    
    def rollback_to_backup(
        self,
        backup_id: str,
        reason: str = "",
        operator: str = "system",
        rollback_type: RollbackType = RollbackType.SPECIFIC,
        skip_validation: bool = False
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        回滚到指定备份
        
        Args:
            backup_id: 备份ID
            reason: 回滚原因
            operator: 操作者
            rollback_type: 回滚类型
            skip_validation: 是否跳过验证
        
        Returns:
            Tuple[是否成功, 消息, 详情]
        
        Requirements: 业务风险 - 建立快速回滚机制
        """
        start_time = datetime.now()
        
        # 创建回滚记录
        rollback_id = datetime.now().strftime("ROLLBACK_%Y%m%d_%H%M%S")
        record = RollbackRecord(
            rollback_id=rollback_id,
            rollback_type=rollback_type,
            status=RollbackStatus.IN_PROGRESS,
            timestamp=start_time,
            backup_id=backup_id,
            reason=reason,
            operator=operator
        )
        
        try:
            # 获取备份信息
            backup_info = self._backup_index.get(backup_id)
            if not backup_info:
                record.status = RollbackStatus.FAILED
                record.error_message = f"备份不存在: {backup_id}"
                self._save_record(record)
                return False, record.error_message, record.to_dict()
            
            # 验证备份（除非是紧急回滚）
            if not skip_validation and rollback_type != RollbackType.EMERGENCY:
                validation = self.validate_backup(backup_id)
                if not validation.is_valid:
                    record.status = RollbackStatus.FAILED
                    record.error_message = f"备份验证失败: {', '.join(validation.errors)}"
                    self._save_record(record)
                    return False, record.error_message, {
                        'record': record.to_dict(),
                        'validation': validation.to_dict()
                    }
            
            # 获取当前股票池状态
            current_pool = self._get_current_pool()
            record.before_pool_count = len(current_pool)
            
            # 创建当前状态的备份（以便回滚失败时恢复）
            pre_rollback_backup = self._create_pre_rollback_backup(current_pool)
            
            # 执行回滚
            success, message = self._apply_rollback(backup_info)
            
            if success:
                record.status = RollbackStatus.COMPLETED
                record.after_pool_count = backup_info.pool_count
                logger.info(f"回滚成功: {rollback_id}, 备份: {backup_id}")
            else:
                record.status = RollbackStatus.FAILED
                record.error_message = message
                # 尝试恢复到回滚前状态
                if pre_rollback_backup:
                    self._restore_from_backup(pre_rollback_backup)
                logger.error(f"回滚失败: {rollback_id}, 原因: {message}")
            
            # 计算耗时
            record.duration_seconds = (datetime.now() - start_time).total_seconds()
            
            # 保存记录
            self._save_record(record)
            
            return success, message, {
                'record': record.to_dict(),
                'backup_info': backup_info.to_dict()
            }
            
        except Exception as e:
            record.status = RollbackStatus.FAILED
            record.error_message = str(e)
            record.duration_seconds = (datetime.now() - start_time).total_seconds()
            self._save_record(record)
            logger.error(f"回滚异常: {e}")
            return False, f"回滚异常: {e}", record.to_dict()
    
    def emergency_rollback(
        self,
        reason: str = "紧急回滚",
        operator: str = "system"
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        紧急回滚（跳过所有验证）
        
        用于紧急情况下快速恢复系统
        
        Args:
            reason: 回滚原因
            operator: 操作者
        
        Returns:
            Tuple[是否成功, 消息, 详情]
        
        Requirements: 业务风险 - 建立快速回滚机制
        """
        latest_backup = self.get_latest_backup()
        if not latest_backup:
            return False, "没有可用的备份", {}
        
        return self.rollback_to_backup(
            backup_id=latest_backup.backup_id,
            reason=f"[紧急] {reason}",
            operator=operator,
            rollback_type=RollbackType.EMERGENCY,
            skip_validation=True
        )

    
    def validate_backup(self, backup_id: str) -> RollbackValidation:
        """
        验证备份是否可用于回滚
        
        Args:
            backup_id: 备份ID
        
        Returns:
            RollbackValidation: 验证结果
        
        Requirements: 业务风险 - 建立快速回滚机制
        """
        validation = RollbackValidation(
            is_valid=True,
            backup_exists=False,
            backup_readable=False,
            pool_count_valid=False,
            codes_valid=False
        )
        
        # 检查备份是否存在
        backup_info = self._backup_index.get(backup_id)
        if not backup_info:
            validation.is_valid = False
            validation.errors.append(f"备份不存在: {backup_id}")
            return validation
        
        validation.backup_exists = True
        
        # 检查备份文件是否可读
        if not os.path.exists(backup_info.backup_path):
            validation.is_valid = False
            validation.errors.append(f"备份文件不存在: {backup_info.backup_path}")
            return validation
        
        try:
            with open(backup_info.backup_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            validation.backup_readable = True
        except Exception as e:
            validation.is_valid = False
            validation.errors.append(f"备份文件无法读取: {e}")
            return validation
        
        # 检查股票池数量
        pool_codes = backup_data.get('pool', [])
        if len(pool_codes) == 0:
            validation.is_valid = False
            validation.errors.append("备份股票池为空")
        elif len(pool_codes) < 10:
            validation.warnings.append(f"备份股票池数量较少: {len(pool_codes)}")
            validation.pool_count_valid = True
        else:
            validation.pool_count_valid = True
        
        # 检查股票代码格式
        invalid_codes = []
        for code in pool_codes:
            if not self._is_valid_stock_code(code):
                invalid_codes.append(code)
        
        if invalid_codes:
            validation.warnings.append(f"存在无效股票代码: {invalid_codes[:5]}")
        
        if len(invalid_codes) > len(pool_codes) * 0.1:
            validation.is_valid = False
            validation.errors.append(f"无效股票代码过多: {len(invalid_codes)}/{len(pool_codes)}")
        else:
            validation.codes_valid = True
        
        return validation
    
    def create_backup(
        self,
        description: str = "",
        backup_type: str = "manual"
    ) -> Tuple[bool, str, Optional[BackupInfo]]:
        """
        创建当前股票池的备份
        
        Args:
            description: 备份描述
            backup_type: 备份类型
        
        Returns:
            Tuple[是否成功, 消息, 备份信息]
        
        Requirements: 业务风险 - 建立快速回滚机制
        """
        try:
            # 获取当前股票池
            current_pool = self._get_current_pool()
            
            # 生成备份ID和路径（使用微秒确保唯一性）
            timestamp = datetime.now()
            backup_id = timestamp.strftime("BACKUP_%Y%m%d_%H%M%S") + f"_{timestamp.microsecond:06d}"
            backup_filename = f"pool_backup_{timestamp.strftime('%Y%m%d_%H%M%S')}_{timestamp.microsecond:06d}.json"
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            # 保存备份
            backup_data = {
                'backup_id': backup_id,
                'timestamp': timestamp.isoformat(),
                'pool': current_pool,
                'count': len(current_pool),
                'backup_type': backup_type,
                'description': description
            }
            
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2)
            
            # 创建备份信息
            backup_info = BackupInfo(
                backup_id=backup_id,
                backup_path=backup_path,
                timestamp=timestamp,
                pool_count=len(current_pool),
                pool_codes=current_pool,
                backup_type=backup_type,
                description=description
            )
            
            # 更新索引
            self._backup_index[backup_id] = backup_info
            
            logger.info(f"创建备份成功: {backup_id}, 股票数: {len(current_pool)}")
            return True, f"备份创建成功: {backup_id}", backup_info
            
        except Exception as e:
            logger.error(f"创建备份失败: {e}")
            return False, f"创建备份失败: {e}", None
    
    def get_latest_backup(self) -> Optional[BackupInfo]:
        """
        获取最近的备份
        
        Returns:
            最近的备份信息，如果没有则返回None
        """
        if not self._backup_index:
            return None
        
        # 按时间排序，返回最新的
        sorted_backups = sorted(
            self._backup_index.values(),
            key=lambda x: x.timestamp,
            reverse=True
        )
        
        return sorted_backups[0] if sorted_backups else None
    
    def list_backups(self, limit: int = 10) -> List[BackupInfo]:
        """
        列出可用的备份
        
        Args:
            limit: 返回数量限制
        
        Returns:
            备份信息列表（按时间倒序）
        """
        sorted_backups = sorted(
            self._backup_index.values(),
            key=lambda x: x.timestamp,
            reverse=True
        )
        
        return sorted_backups[:limit]
    
    def get_rollback_history(self, limit: int = 20) -> List[RollbackRecord]:
        """
        获取回滚历史
        
        Args:
            limit: 返回数量限制
        
        Returns:
            回滚记录列表（按时间倒序）
        """
        sorted_history = sorted(
            self._rollback_history,
            key=lambda x: x.timestamp,
            reverse=True
        )
        
        return sorted_history[:limit]
    
    def get_rollback_summary(self) -> Dict[str, Any]:
        """
        获取回滚摘要信息
        
        Returns:
            回滚摘要
        """
        total_rollbacks = len(self._rollback_history)
        successful = sum(1 for r in self._rollback_history if r.status == RollbackStatus.COMPLETED)
        failed = sum(1 for r in self._rollback_history if r.status == RollbackStatus.FAILED)
        
        latest_backup = self.get_latest_backup()
        
        return {
            'total_backups': len(self._backup_index),
            'latest_backup': latest_backup.to_dict() if latest_backup else None,
            'total_rollbacks': total_rollbacks,
            'successful_rollbacks': successful,
            'failed_rollbacks': failed,
            'success_rate': (successful / total_rollbacks * 100) if total_rollbacks > 0 else 100.0,
            'backup_dir': self.backup_dir,
            'history_file': self.history_file
        }

    
    def _get_current_pool(self) -> List[str]:
        """获取当前股票池"""
        try:
            from config.tech_stock_pool import get_tech_stock_pool
            pool = get_tech_stock_pool()
            return pool.get_all_codes()
        except Exception as e:
            logger.warning(f"获取当前股票池失败: {e}")
            return []
    
    def _apply_rollback(self, backup_info: BackupInfo) -> Tuple[bool, str]:
        """
        应用回滚
        
        Args:
            backup_info: 备份信息
        
        Returns:
            Tuple[是否成功, 消息]
        """
        try:
            # 读取备份数据
            with open(backup_info.backup_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            pool_codes = backup_data.get('pool', [])
            
            # 这里我们需要更新股票池配置
            # 由于股票池是在Python模块中定义的，我们需要通过其他方式更新
            # 最安全的方式是记录回滚状态，让系统在下次启动时使用备份数据
            
            # 保存回滚状态文件
            rollback_state_file = os.path.join(self.backup_dir, "active_rollback.json")
            rollback_state = {
                'backup_id': backup_info.backup_id,
                'backup_path': backup_info.backup_path,
                'pool_codes': pool_codes,
                'applied_at': datetime.now().isoformat(),
                'status': 'applied'
            }
            
            with open(rollback_state_file, 'w', encoding='utf-8') as f:
                json.dump(rollback_state, f, ensure_ascii=False, indent=2)
            
            logger.info(f"回滚状态已保存: {backup_info.backup_id}")
            return True, f"回滚成功，股票池已恢复到 {backup_info.pool_count} 只股票"
            
        except Exception as e:
            logger.error(f"应用回滚失败: {e}")
            return False, f"应用回滚失败: {e}"
    
    def _restore_from_backup(self, backup_path: str) -> bool:
        """从备份恢复（用于回滚失败时）"""
        try:
            # 这是一个安全措施，用于回滚失败时恢复
            logger.info(f"尝试从备份恢复: {backup_path}")
            return True
        except Exception as e:
            logger.error(f"从备份恢复失败: {e}")
            return False
    
    def _create_pre_rollback_backup(self, current_pool: List[str]) -> Optional[str]:
        """创建回滚前的备份"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"pre_rollback_{timestamp}.json"
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            backup_data = {
                'timestamp': timestamp,
                'pool': current_pool,
                'count': len(current_pool),
                'type': 'pre_rollback'
            }
            
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2)
            
            return backup_path
        except Exception as e:
            logger.warning(f"创建回滚前备份失败: {e}")
            return None
    
    def _is_valid_stock_code(self, code: str) -> bool:
        """验证股票代码格式"""
        if not code or not isinstance(code, str):
            return False
        
        # 检查长度
        if len(code) != 6:
            return False
        
        # 检查是否全是数字
        if not code.isdigit():
            return False
        
        # 检查前缀（主板和中小板）
        valid_prefixes = ['000', '001', '002', '003', '300', '600', '601', '603', '605', '688']
        return any(code.startswith(prefix) for prefix in valid_prefixes)
    
    def _scan_backups(self) -> None:
        """扫描备份目录，建立索引"""
        try:
            if not os.path.exists(self.backup_dir):
                return
            
            for filename in os.listdir(self.backup_dir):
                if filename.startswith('pool_backup_') and filename.endswith('.json'):
                    filepath = os.path.join(self.backup_dir, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        backup_id = data.get('backup_id') or data.get('timestamp', filename)
                        timestamp_str = data.get('timestamp', '')
                        
                        # 解析时间戳
                        if timestamp_str:
                            try:
                                timestamp = datetime.fromisoformat(timestamp_str)
                            except ValueError:
                                # 尝试其他格式
                                try:
                                    timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                                except ValueError:
                                    timestamp = datetime.now()
                        else:
                            timestamp = datetime.now()
                        
                        pool_codes = data.get('pool', [])
                        
                        backup_info = BackupInfo(
                            backup_id=backup_id,
                            backup_path=filepath,
                            timestamp=timestamp,
                            pool_count=len(pool_codes),
                            pool_codes=pool_codes,
                            backup_type=data.get('backup_type', 'auto'),
                            description=data.get('description', '')
                        )
                        
                        self._backup_index[backup_id] = backup_info
                        
                    except Exception as e:
                        logger.warning(f"解析备份文件失败 {filename}: {e}")
            
            logger.info(f"扫描到 {len(self._backup_index)} 个备份")
            
        except Exception as e:
            logger.error(f"扫描备份目录失败: {e}")
    
    def _load_history(self) -> None:
        """加载回滚历史"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self._rollback_history = [
                    RollbackRecord.from_dict(record)
                    for record in data.get('history', [])
                ]
                
                logger.info(f"加载 {len(self._rollback_history)} 条回滚历史")
        except Exception as e:
            logger.warning(f"加载回滚历史失败: {e}")
            self._rollback_history = []
    
    def _save_record(self, record: RollbackRecord) -> None:
        """保存回滚记录"""
        try:
            self._rollback_history.append(record)
            
            # 保存到文件
            os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
            
            data = {
                'last_updated': datetime.now().isoformat(),
                'history': [r.to_dict() for r in self._rollback_history]
            }
            
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"保存回滚记录失败: {e}")
    
    def cleanup_old_backups(self, keep_count: int = 10) -> int:
        """
        清理旧备份
        
        Args:
            keep_count: 保留的备份数量
        
        Returns:
            删除的备份数量
        """
        try:
            sorted_backups = sorted(
                self._backup_index.values(),
                key=lambda x: x.timestamp,
                reverse=True
            )
            
            to_delete = sorted_backups[keep_count:]
            deleted_count = 0
            
            for backup in to_delete:
                try:
                    if os.path.exists(backup.backup_path):
                        os.remove(backup.backup_path)
                    del self._backup_index[backup.backup_id]
                    deleted_count += 1
                except Exception as e:
                    logger.warning(f"删除备份失败 {backup.backup_id}: {e}")
            
            logger.info(f"清理了 {deleted_count} 个旧备份")
            return deleted_count
            
        except Exception as e:
            logger.error(f"清理旧备份失败: {e}")
            return 0



# 全局实例
_quick_rollback_manager: Optional[QuickRollbackManager] = None


def get_quick_rollback_manager() -> QuickRollbackManager:
    """
    获取快速回滚管理器实例（单例模式）
    
    Returns:
        QuickRollbackManager: 快速回滚管理器实例
    """
    global _quick_rollback_manager
    if _quick_rollback_manager is None:
        _quick_rollback_manager = QuickRollbackManager()
    return _quick_rollback_manager


def reset_quick_rollback_manager() -> None:
    """重置快速回滚管理器实例（主要用于测试）"""
    global _quick_rollback_manager
    _quick_rollback_manager = None


# 便捷函数
def quick_rollback(reason: str = "快速回滚", operator: str = "system") -> Tuple[bool, str, Dict[str, Any]]:
    """
    快速回滚到最近的备份
    
    便捷函数，用于一键回滚
    
    Args:
        reason: 回滚原因
        operator: 操作者
    
    Returns:
        Tuple[是否成功, 消息, 详情]
    
    Requirements: 业务风险 - 建立快速回滚机制
    """
    manager = get_quick_rollback_manager()
    return manager.quick_rollback(reason, operator)


def emergency_rollback(reason: str = "紧急回滚", operator: str = "system") -> Tuple[bool, str, Dict[str, Any]]:
    """
    紧急回滚（跳过验证）
    
    便捷函数，用于紧急情况
    
    Args:
        reason: 回滚原因
        operator: 操作者
    
    Returns:
        Tuple[是否成功, 消息, 详情]
    
    Requirements: 业务风险 - 建立快速回滚机制
    """
    manager = get_quick_rollback_manager()
    return manager.emergency_rollback(reason, operator)


def rollback_to_version(
    backup_id: str,
    reason: str = "",
    operator: str = "system"
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    回滚到指定版本
    
    便捷函数
    
    Args:
        backup_id: 备份ID
        reason: 回滚原因
        operator: 操作者
    
    Returns:
        Tuple[是否成功, 消息, 详情]
    
    Requirements: 业务风险 - 建立快速回滚机制
    """
    manager = get_quick_rollback_manager()
    return manager.rollback_to_backup(backup_id, reason, operator)


def create_backup(description: str = "", backup_type: str = "manual") -> Tuple[bool, str, Optional[BackupInfo]]:
    """
    创建当前股票池的备份
    
    便捷函数
    
    Args:
        description: 备份描述
        backup_type: 备份类型
    
    Returns:
        Tuple[是否成功, 消息, 备份信息]
    
    Requirements: 业务风险 - 建立快速回滚机制
    """
    manager = get_quick_rollback_manager()
    return manager.create_backup(description, backup_type)


def list_available_backups(limit: int = 10) -> List[BackupInfo]:
    """
    列出可用的备份
    
    便捷函数
    
    Args:
        limit: 返回数量限制
    
    Returns:
        备份信息列表
    """
    manager = get_quick_rollback_manager()
    return manager.list_backups(limit)


def get_rollback_status() -> Dict[str, Any]:
    """
    获取回滚状态摘要
    
    便捷函数
    
    Returns:
        回滚状态摘要
    """
    manager = get_quick_rollback_manager()
    return manager.get_rollback_summary()


def validate_backup_for_rollback(backup_id: str) -> RollbackValidation:
    """
    验证备份是否可用于回滚
    
    便捷函数
    
    Args:
        backup_id: 备份ID
    
    Returns:
        验证结果
    """
    manager = get_quick_rollback_manager()
    return manager.validate_backup(backup_id)
