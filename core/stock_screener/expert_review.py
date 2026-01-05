"""
专家审核机制

提供股票筛选结果的专家审核工作流，包括：
- 审核任务创建和管理
- 审核状态跟踪
- 审核意见记录
- 审核结果统计
- 审核历史查询

Requirements: 6.1, 6.4 (建立专家审核工作流)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Tuple
from enum import Enum
from datetime import datetime
import logging
import json
import os
import uuid

logger = logging.getLogger(__name__)


class ReviewStatus(Enum):
    """审核状态"""
    PENDING = "pending"          # 待审核
    IN_REVIEW = "in_review"      # 审核中
    APPROVED = "approved"        # 已批准
    REJECTED = "rejected"        # 已拒绝
    NEEDS_REVISION = "needs_revision"  # 需要修改
    EXPIRED = "expired"          # 已过期


class ReviewPriority(Enum):
    """审核优先级"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class ReviewCategory(Enum):
    """审核类别"""
    NEW_STOCK = "new_stock"              # 新增股票
    REMOVE_STOCK = "remove_stock"        # 移除股票
    INDUSTRY_CLASSIFICATION = "industry_classification"  # 行业分类
    SCORE_ADJUSTMENT = "score_adjustment"  # 评分调整
    POOL_UPDATE = "pool_update"          # 股票池更新
    DATA_QUALITY = "data_quality"        # 数据质量


@dataclass
class ReviewComment:
    """审核意见"""
    reviewer: str
    timestamp: datetime
    content: str
    action: str  # approve, reject, request_revision, comment
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'reviewer': self.reviewer,
            'timestamp': self.timestamp.isoformat(),
            'content': self.content,
            'action': self.action
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReviewComment':
        """从字典创建"""
        return cls(
            reviewer=data['reviewer'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            content=data['content'],
            action=data['action']
        )


@dataclass
class ReviewItem:
    """审核项目"""
    code: str                    # 股票代码
    name: str                    # 股票名称
    category: ReviewCategory     # 审核类别
    reason: str                  # 审核原因
    data: Dict[str, Any] = field(default_factory=dict)  # 相关数据
    recommendation: str = ""     # 系统建议
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'code': self.code,
            'name': self.name,
            'category': self.category.value,
            'reason': self.reason,
            'data': self.data,
            'recommendation': self.recommendation
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReviewItem':
        """从字典创建"""
        return cls(
            code=data['code'],
            name=data['name'],
            category=ReviewCategory(data['category']),
            reason=data['reason'],
            data=data.get('data', {}),
            recommendation=data.get('recommendation', '')
        )


@dataclass
class ReviewTask:
    """审核任务"""
    task_id: str
    title: str
    description: str
    category: ReviewCategory
    priority: ReviewPriority
    status: ReviewStatus
    created_at: datetime
    updated_at: datetime
    created_by: str
    assigned_to: Optional[str] = None
    due_date: Optional[datetime] = None
    items: List[ReviewItem] = field(default_factory=list)
    comments: List[ReviewComment] = field(default_factory=list)
    result: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'task_id': self.task_id,
            'title': self.title,
            'description': self.description,
            'category': self.category.value,
            'priority': self.priority.value,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'created_by': self.created_by,
            'assigned_to': self.assigned_to,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'items': [item.to_dict() for item in self.items],
            'comments': [comment.to_dict() for comment in self.comments],
            'result': self.result
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReviewTask':
        """从字典创建"""
        return cls(
            task_id=data['task_id'],
            title=data['title'],
            description=data['description'],
            category=ReviewCategory(data['category']),
            priority=ReviewPriority(data['priority']),
            status=ReviewStatus(data['status']),
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
            created_by=data['created_by'],
            assigned_to=data.get('assigned_to'),
            due_date=datetime.fromisoformat(data['due_date']) if data.get('due_date') else None,
            items=[ReviewItem.from_dict(item) for item in data.get('items', [])],
            comments=[ReviewComment.from_dict(c) for c in data.get('comments', [])],
            result=data.get('result')
        )


@dataclass
class ReviewStatistics:
    """审核统计"""
    total_tasks: int = 0
    pending_tasks: int = 0
    in_review_tasks: int = 0
    approved_tasks: int = 0
    rejected_tasks: int = 0
    revision_tasks: int = 0
    expired_tasks: int = 0
    avg_review_time_hours: float = 0.0
    approval_rate: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'total_tasks': self.total_tasks,
            'pending_tasks': self.pending_tasks,
            'in_review_tasks': self.in_review_tasks,
            'approved_tasks': self.approved_tasks,
            'rejected_tasks': self.rejected_tasks,
            'revision_tasks': self.revision_tasks,
            'expired_tasks': self.expired_tasks,
            'avg_review_time_hours': self.avg_review_time_hours,
            'approval_rate': self.approval_rate
        }



class ExpertReviewManager:
    """
    专家审核管理器
    
    管理审核任务的创建、分配、执行和跟踪
    
    Requirements: 6.1, 6.4
    """
    
    def __init__(
        self,
        storage_file: str = "data/expert_reviews.json",
        max_history: int = 500
    ):
        """
        初始化专家审核管理器
        
        Args:
            storage_file: 存储文件路径
            max_history: 最大历史记录数
        """
        self.storage_file = storage_file
        self.max_history = max_history
        self.tasks: Dict[str, ReviewTask] = {}
        self._callbacks: Dict[str, List[Callable]] = {
            'on_task_created': [],
            'on_task_updated': [],
            'on_task_completed': []
        }
        
        self._load_tasks()
    
    def create_task(
        self,
        title: str,
        description: str,
        category: ReviewCategory,
        items: List[ReviewItem],
        created_by: str = "system",
        priority: ReviewPriority = ReviewPriority.NORMAL,
        assigned_to: Optional[str] = None,
        due_date: Optional[datetime] = None
    ) -> ReviewTask:
        """
        创建审核任务
        
        Args:
            title: 任务标题
            description: 任务描述
            category: 审核类别
            items: 审核项目列表
            created_by: 创建者
            priority: 优先级
            assigned_to: 分配给
            due_date: 截止日期
        
        Returns:
            ReviewTask: 创建的审核任务
        """
        task_id = str(uuid.uuid4())[:8]
        now = datetime.now()
        
        task = ReviewTask(
            task_id=task_id,
            title=title,
            description=description,
            category=category,
            priority=priority,
            status=ReviewStatus.PENDING,
            created_at=now,
            updated_at=now,
            created_by=created_by,
            assigned_to=assigned_to,
            due_date=due_date,
            items=items
        )
        
        self.tasks[task_id] = task
        self._save_tasks()
        self._trigger_callback('on_task_created', task)
        
        logger.info(f"创建审核任务: {task_id} - {title}")
        return task
    
    def get_task(self, task_id: str) -> Optional[ReviewTask]:
        """获取审核任务"""
        return self.tasks.get(task_id)
    
    def get_tasks_by_status(self, status: ReviewStatus) -> List[ReviewTask]:
        """按状态获取任务"""
        return [t for t in self.tasks.values() if t.status == status]
    
    def get_pending_tasks(self) -> List[ReviewTask]:
        """获取待审核任务"""
        return self.get_tasks_by_status(ReviewStatus.PENDING)
    
    def get_tasks_by_category(self, category: ReviewCategory) -> List[ReviewTask]:
        """按类别获取任务"""
        return [t for t in self.tasks.values() if t.category == category]
    
    def assign_task(
        self,
        task_id: str,
        reviewer: str
    ) -> bool:
        """
        分配审核任务
        
        Args:
            task_id: 任务ID
            reviewer: 审核人
        
        Returns:
            bool: 是否成功
        """
        task = self.tasks.get(task_id)
        if not task:
            logger.warning(f"任务不存在: {task_id}")
            return False
        
        if task.status not in [ReviewStatus.PENDING, ReviewStatus.NEEDS_REVISION]:
            logger.warning(f"任务状态不允许分配: {task.status}")
            return False
        
        task.assigned_to = reviewer
        task.status = ReviewStatus.IN_REVIEW
        task.updated_at = datetime.now()
        
        self._save_tasks()
        self._trigger_callback('on_task_updated', task)
        
        logger.info(f"任务 {task_id} 已分配给 {reviewer}")
        return True
    
    def add_comment(
        self,
        task_id: str,
        reviewer: str,
        content: str,
        action: str = "comment"
    ) -> bool:
        """
        添加审核意见
        
        Args:
            task_id: 任务ID
            reviewer: 审核人
            content: 意见内容
            action: 操作类型
        
        Returns:
            bool: 是否成功
        """
        task = self.tasks.get(task_id)
        if not task:
            logger.warning(f"任务不存在: {task_id}")
            return False
        
        comment = ReviewComment(
            reviewer=reviewer,
            timestamp=datetime.now(),
            content=content,
            action=action
        )
        
        task.comments.append(comment)
        task.updated_at = datetime.now()
        
        self._save_tasks()
        self._trigger_callback('on_task_updated', task)
        
        return True
    
    def approve_task(
        self,
        task_id: str,
        reviewer: str,
        comment: str = "",
        result: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        批准审核任务
        
        Args:
            task_id: 任务ID
            reviewer: 审核人
            comment: 审核意见
            result: 审核结果数据
        
        Returns:
            bool: 是否成功
        """
        task = self.tasks.get(task_id)
        if not task:
            logger.warning(f"任务不存在: {task_id}")
            return False
        
        if task.status not in [ReviewStatus.PENDING, ReviewStatus.IN_REVIEW]:
            logger.warning(f"任务状态不允许批准: {task.status}")
            return False
        
        # 添加批准意见
        if comment:
            self.add_comment(task_id, reviewer, comment, "approve")
        
        task.status = ReviewStatus.APPROVED
        task.updated_at = datetime.now()
        task.result = result or {'approved_by': reviewer, 'approved_at': datetime.now().isoformat()}
        
        self._save_tasks()
        self._trigger_callback('on_task_completed', task)
        
        logger.info(f"任务 {task_id} 已被 {reviewer} 批准")
        return True
    
    def reject_task(
        self,
        task_id: str,
        reviewer: str,
        reason: str
    ) -> bool:
        """
        拒绝审核任务
        
        Args:
            task_id: 任务ID
            reviewer: 审核人
            reason: 拒绝原因
        
        Returns:
            bool: 是否成功
        """
        task = self.tasks.get(task_id)
        if not task:
            logger.warning(f"任务不存在: {task_id}")
            return False
        
        if task.status not in [ReviewStatus.PENDING, ReviewStatus.IN_REVIEW]:
            logger.warning(f"任务状态不允许拒绝: {task.status}")
            return False
        
        self.add_comment(task_id, reviewer, reason, "reject")
        
        task.status = ReviewStatus.REJECTED
        task.updated_at = datetime.now()
        task.result = {'rejected_by': reviewer, 'rejected_at': datetime.now().isoformat(), 'reason': reason}
        
        self._save_tasks()
        self._trigger_callback('on_task_completed', task)
        
        logger.info(f"任务 {task_id} 已被 {reviewer} 拒绝: {reason}")
        return True
    
    def request_revision(
        self,
        task_id: str,
        reviewer: str,
        feedback: str
    ) -> bool:
        """
        请求修改
        
        Args:
            task_id: 任务ID
            reviewer: 审核人
            feedback: 修改意见
        
        Returns:
            bool: 是否成功
        """
        task = self.tasks.get(task_id)
        if not task:
            logger.warning(f"任务不存在: {task_id}")
            return False
        
        self.add_comment(task_id, reviewer, feedback, "request_revision")
        
        task.status = ReviewStatus.NEEDS_REVISION
        task.updated_at = datetime.now()
        task.assigned_to = None  # 重置分配
        
        self._save_tasks()
        self._trigger_callback('on_task_updated', task)
        
        logger.info(f"任务 {task_id} 需要修改: {feedback}")
        return True
    
    def get_statistics(self) -> ReviewStatistics:
        """获取审核统计"""
        stats = ReviewStatistics()
        
        stats.total_tasks = len(self.tasks)
        
        for task in self.tasks.values():
            if task.status == ReviewStatus.PENDING:
                stats.pending_tasks += 1
            elif task.status == ReviewStatus.IN_REVIEW:
                stats.in_review_tasks += 1
            elif task.status == ReviewStatus.APPROVED:
                stats.approved_tasks += 1
            elif task.status == ReviewStatus.REJECTED:
                stats.rejected_tasks += 1
            elif task.status == ReviewStatus.NEEDS_REVISION:
                stats.revision_tasks += 1
            elif task.status == ReviewStatus.EXPIRED:
                stats.expired_tasks += 1
        
        # 计算批准率
        completed = stats.approved_tasks + stats.rejected_tasks
        if completed > 0:
            stats.approval_rate = stats.approved_tasks / completed * 100
        
        # 计算平均审核时间
        review_times = []
        for task in self.tasks.values():
            if task.status in [ReviewStatus.APPROVED, ReviewStatus.REJECTED]:
                duration = (task.updated_at - task.created_at).total_seconds() / 3600
                review_times.append(duration)
        
        if review_times:
            stats.avg_review_time_hours = sum(review_times) / len(review_times)
        
        return stats
    
    def register_callback(self, event: str, callback: Callable):
        """注册回调函数"""
        if event in self._callbacks:
            self._callbacks[event].append(callback)
    
    def _trigger_callback(self, event: str, task: ReviewTask):
        """触发回调"""
        for callback in self._callbacks.get(event, []):
            try:
                callback(task)
            except Exception as e:
                logger.error(f"回调执行失败: {e}")
    
    def _load_tasks(self):
        """加载任务"""
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for task_data in data:
                        task = ReviewTask.from_dict(task_data)
                        self.tasks[task.task_id] = task
                logger.info(f"加载了 {len(self.tasks)} 个审核任务")
        except Exception as e:
            logger.warning(f"加载审核任务失败: {e}")
    
    def _save_tasks(self):
        """保存任务"""
        try:
            os.makedirs(os.path.dirname(self.storage_file), exist_ok=True)
            
            # 限制历史记录数量
            if len(self.tasks) > self.max_history:
                # 按更新时间排序，保留最新的
                sorted_tasks = sorted(
                    self.tasks.values(),
                    key=lambda t: t.updated_at,
                    reverse=True
                )
                self.tasks = {t.task_id: t for t in sorted_tasks[:self.max_history]}
            
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(
                    [task.to_dict() for task in self.tasks.values()],
                    f,
                    ensure_ascii=False,
                    indent=2
                )
        except Exception as e:
            logger.error(f"保存审核任务失败: {e}")



class ExpertReviewWorkflow:
    """
    专家审核工作流
    
    提供股票筛选结果的审核工作流程
    
    Requirements: 6.1, 6.4
    """
    
    # 需要审核的置信度阈值
    LOW_CONFIDENCE_THRESHOLD = 0.5
    MEDIUM_CONFIDENCE_THRESHOLD = 0.7
    
    def __init__(self, review_manager: Optional[ExpertReviewManager] = None):
        """
        初始化审核工作流
        
        Args:
            review_manager: 审核管理器实例
        """
        self.review_manager = review_manager or get_expert_review_manager()
    
    def create_pool_update_review(
        self,
        added_stocks: List[Dict[str, Any]],
        removed_stocks: List[Dict[str, Any]],
        screening_summary: Dict[str, Any],
        created_by: str = "system"
    ) -> Optional[ReviewTask]:
        """
        创建股票池更新审核任务
        
        Args:
            added_stocks: 新增股票列表
            removed_stocks: 移除股票列表
            screening_summary: 筛选摘要
            created_by: 创建者
        
        Returns:
            ReviewTask: 审核任务，如果不需要审核则返回None
        """
        items = []
        
        # 添加新增股票审核项
        for stock in added_stocks:
            items.append(ReviewItem(
                code=stock.get('code', ''),
                name=stock.get('name', ''),
                category=ReviewCategory.NEW_STOCK,
                reason=f"新增候选股票，综合评分: {stock.get('score', 'N/A')}",
                data=stock,
                recommendation="建议纳入" if stock.get('score', 0) >= 70 else "建议审核"
            ))
        
        # 添加移除股票审核项
        for stock in removed_stocks:
            items.append(ReviewItem(
                code=stock.get('code', ''),
                name=stock.get('name', ''),
                category=ReviewCategory.REMOVE_STOCK,
                reason=stock.get('reason', '不再符合筛选条件'),
                data=stock,
                recommendation="建议移除"
            ))
        
        if not items:
            logger.info("无需创建审核任务：没有变更")
            return None
        
        # 确定优先级
        priority = ReviewPriority.NORMAL
        if len(items) > 20:
            priority = ReviewPriority.HIGH
        elif len(items) > 50:
            priority = ReviewPriority.URGENT
        
        task = self.review_manager.create_task(
            title=f"股票池更新审核 - {datetime.now().strftime('%Y-%m-%d')}",
            description=f"本次更新涉及 {len(added_stocks)} 只新增股票和 {len(removed_stocks)} 只移除股票",
            category=ReviewCategory.POOL_UPDATE,
            items=items,
            created_by=created_by,
            priority=priority
        )
        
        return task
    
    def create_industry_classification_review(
        self,
        stocks_with_low_confidence: List[Dict[str, Any]],
        created_by: str = "system"
    ) -> Optional[ReviewTask]:
        """
        创建行业分类审核任务
        
        对于置信度较低的行业分类结果，创建人工审核任务
        
        Args:
            stocks_with_low_confidence: 低置信度股票列表
            created_by: 创建者
        
        Returns:
            ReviewTask: 审核任务
        """
        items = []
        
        for stock in stocks_with_low_confidence:
            confidence = stock.get('confidence', 0)
            if confidence < self.LOW_CONFIDENCE_THRESHOLD:
                items.append(ReviewItem(
                    code=stock.get('code', ''),
                    name=stock.get('name', ''),
                    category=ReviewCategory.INDUSTRY_CLASSIFICATION,
                    reason=f"行业分类置信度较低: {confidence:.2f}",
                    data=stock,
                    recommendation=f"系统分类: {stock.get('industry', '未知')}，需人工确认"
                ))
        
        if not items:
            return None
        
        task = self.review_manager.create_task(
            title=f"行业分类审核 - {len(items)} 只股票",
            description="以下股票的行业分类置信度较低，需要人工审核确认",
            category=ReviewCategory.INDUSTRY_CLASSIFICATION,
            items=items,
            created_by=created_by,
            priority=ReviewPriority.NORMAL
        )
        
        return task
    
    def create_data_quality_review(
        self,
        quality_issues: List[Dict[str, Any]],
        created_by: str = "system"
    ) -> Optional[ReviewTask]:
        """
        创建数据质量审核任务
        
        Args:
            quality_issues: 数据质量问题列表
            created_by: 创建者
        
        Returns:
            ReviewTask: 审核任务
        """
        items = []
        
        for issue in quality_issues:
            items.append(ReviewItem(
                code=issue.get('code', ''),
                name=issue.get('name', ''),
                category=ReviewCategory.DATA_QUALITY,
                reason=issue.get('issue', '数据异常'),
                data=issue,
                recommendation=issue.get('suggestion', '建议核实数据')
            ))
        
        if not items:
            return None
        
        task = self.review_manager.create_task(
            title=f"数据质量审核 - {len(items)} 个问题",
            description="发现以下数据质量问题，需要人工审核处理",
            category=ReviewCategory.DATA_QUALITY,
            items=items,
            created_by=created_by,
            priority=ReviewPriority.HIGH
        )
        
        return task
    
    def check_review_required(
        self,
        stock_data: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        检查是否需要审核
        
        Args:
            stock_data: 股票数据
        
        Returns:
            Tuple[是否需要审核, 原因]
        """
        # 检查行业分类置信度
        confidence = stock_data.get('industry_confidence', 1.0)
        if confidence < self.LOW_CONFIDENCE_THRESHOLD:
            return True, f"行业分类置信度低 ({confidence:.2f})"
        
        # 检查评分异常
        score = stock_data.get('comprehensive_score', 0)
        if score < 50 or score > 95:
            return True, f"评分异常 ({score:.1f})"
        
        # 检查数据完整性
        required_fields = ['code', 'name', 'roe', 'pe_ratio', 'total_market_cap']
        missing_fields = [f for f in required_fields if not stock_data.get(f)]
        if missing_fields:
            return True, f"缺少关键数据: {', '.join(missing_fields)}"
        
        return False, ""
    
    def get_review_summary(self) -> Dict[str, Any]:
        """获取审核摘要"""
        stats = self.review_manager.get_statistics()
        pending_tasks = self.review_manager.get_pending_tasks()
        
        return {
            'statistics': stats.to_dict(),
            'pending_count': len(pending_tasks),
            'pending_tasks': [
                {
                    'task_id': t.task_id,
                    'title': t.title,
                    'category': t.category.value,
                    'priority': t.priority.value,
                    'items_count': len(t.items),
                    'created_at': t.created_at.isoformat()
                }
                for t in pending_tasks[:10]  # 只返回前10个
            ]
        }


# 全局实例
_expert_review_manager: Optional[ExpertReviewManager] = None
_expert_review_workflow: Optional[ExpertReviewWorkflow] = None


def get_expert_review_manager() -> ExpertReviewManager:
    """获取专家审核管理器实例"""
    global _expert_review_manager
    if _expert_review_manager is None:
        _expert_review_manager = ExpertReviewManager()
    return _expert_review_manager


def get_expert_review_workflow() -> ExpertReviewWorkflow:
    """获取专家审核工作流实例"""
    global _expert_review_workflow
    if _expert_review_workflow is None:
        _expert_review_workflow = ExpertReviewWorkflow()
    return _expert_review_workflow


def reset_expert_review_manager():
    """重置专家审核管理器（用于测试）"""
    global _expert_review_manager, _expert_review_workflow
    _expert_review_manager = None
    _expert_review_workflow = None
