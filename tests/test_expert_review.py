"""
专家审核机制测试

验证专家审核工作流的功能：
- 审核任务创建和管理
- 审核状态跟踪
- 审核意见记录
- 审核结果统计

Requirements: 6.1, 6.4
"""

import pytest
import os
import sys
import tempfile
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.stock_screener.expert_review import (
    ExpertReviewManager,
    ExpertReviewWorkflow,
    ReviewTask,
    ReviewItem,
    ReviewComment,
    ReviewStatus,
    ReviewPriority,
    ReviewCategory,
    ReviewStatistics,
    get_expert_review_manager,
    get_expert_review_workflow,
    reset_expert_review_manager,
)


class TestReviewItem:
    """审核项目测试"""
    
    def test_create_review_item(self):
        """测试创建审核项目"""
        item = ReviewItem(
            code="000001",
            name="测试股票",
            category=ReviewCategory.NEW_STOCK,
            reason="新增候选股票",
            data={'score': 75.5},
            recommendation="建议纳入"
        )
        
        assert item.code == "000001"
        assert item.name == "测试股票"
        assert item.category == ReviewCategory.NEW_STOCK
        assert item.reason == "新增候选股票"
        assert item.data['score'] == 75.5
        assert item.recommendation == "建议纳入"
    
    def test_review_item_serialization(self):
        """测试审核项目序列化"""
        item = ReviewItem(
            code="000001",
            name="测试股票",
            category=ReviewCategory.NEW_STOCK,
            reason="测试原因",
            data={'key': 'value'}
        )
        
        # 转换为字典
        item_dict = item.to_dict()
        assert item_dict['code'] == "000001"
        assert item_dict['category'] == "new_stock"
        
        # 从字典恢复
        restored = ReviewItem.from_dict(item_dict)
        assert restored.code == item.code
        assert restored.category == item.category


class TestReviewComment:
    """审核意见测试"""
    
    def test_create_comment(self):
        """测试创建审核意见"""
        comment = ReviewComment(
            reviewer="expert1",
            timestamp=datetime.now(),
            content="同意纳入",
            action="approve"
        )
        
        assert comment.reviewer == "expert1"
        assert comment.content == "同意纳入"
        assert comment.action == "approve"
    
    def test_comment_serialization(self):
        """测试审核意见序列化"""
        now = datetime.now()
        comment = ReviewComment(
            reviewer="expert1",
            timestamp=now,
            content="测试意见",
            action="comment"
        )
        
        # 转换为字典
        comment_dict = comment.to_dict()
        assert comment_dict['reviewer'] == "expert1"
        
        # 从字典恢复
        restored = ReviewComment.from_dict(comment_dict)
        assert restored.reviewer == comment.reviewer
        assert restored.content == comment.content


class TestExpertReviewManager:
    """专家审核管理器测试"""
    
    @pytest.fixture
    def temp_storage(self):
        """创建临时存储文件"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('[]')
            temp_path = f.name
        yield temp_path
        # 清理
        if os.path.exists(temp_path):
            os.remove(temp_path)
    
    @pytest.fixture
    def manager(self, temp_storage):
        """创建测试用管理器"""
        return ExpertReviewManager(storage_file=temp_storage)
    
    def test_create_task(self, manager):
        """测试创建审核任务"""
        items = [
            ReviewItem(
                code="000001",
                name="股票A",
                category=ReviewCategory.NEW_STOCK,
                reason="新增"
            )
        ]
        
        task = manager.create_task(
            title="测试任务",
            description="测试描述",
            category=ReviewCategory.POOL_UPDATE,
            items=items,
            created_by="test_user"
        )
        
        assert task is not None
        assert task.title == "测试任务"
        assert task.status == ReviewStatus.PENDING
        assert len(task.items) == 1
        assert task.created_by == "test_user"
    
    def test_get_task(self, manager):
        """测试获取任务"""
        items = [
            ReviewItem(
                code="000001",
                name="股票A",
                category=ReviewCategory.NEW_STOCK,
                reason="新增"
            )
        ]
        
        created_task = manager.create_task(
            title="测试任务",
            description="测试",
            category=ReviewCategory.POOL_UPDATE,
            items=items
        )
        
        retrieved_task = manager.get_task(created_task.task_id)
        assert retrieved_task is not None
        assert retrieved_task.task_id == created_task.task_id
    
    def test_assign_task(self, manager):
        """测试分配任务"""
        items = [
            ReviewItem(
                code="000001",
                name="股票A",
                category=ReviewCategory.NEW_STOCK,
                reason="新增"
            )
        ]
        
        task = manager.create_task(
            title="测试任务",
            description="测试",
            category=ReviewCategory.POOL_UPDATE,
            items=items
        )
        
        result = manager.assign_task(task.task_id, "expert1")
        assert result == True
        
        updated_task = manager.get_task(task.task_id)
        assert updated_task.assigned_to == "expert1"
        assert updated_task.status == ReviewStatus.IN_REVIEW
    
    def test_approve_task(self, manager):
        """测试批准任务"""
        items = [
            ReviewItem(
                code="000001",
                name="股票A",
                category=ReviewCategory.NEW_STOCK,
                reason="新增"
            )
        ]
        
        task = manager.create_task(
            title="测试任务",
            description="测试",
            category=ReviewCategory.POOL_UPDATE,
            items=items
        )
        
        result = manager.approve_task(
            task.task_id,
            reviewer="expert1",
            comment="同意"
        )
        assert result == True
        
        updated_task = manager.get_task(task.task_id)
        assert updated_task.status == ReviewStatus.APPROVED
        assert updated_task.result is not None
    
    def test_reject_task(self, manager):
        """测试拒绝任务"""
        items = [
            ReviewItem(
                code="000001",
                name="股票A",
                category=ReviewCategory.NEW_STOCK,
                reason="新增"
            )
        ]
        
        task = manager.create_task(
            title="测试任务",
            description="测试",
            category=ReviewCategory.POOL_UPDATE,
            items=items
        )
        
        result = manager.reject_task(
            task.task_id,
            reviewer="expert1",
            reason="不符合条件"
        )
        assert result == True
        
        updated_task = manager.get_task(task.task_id)
        assert updated_task.status == ReviewStatus.REJECTED
        assert len(updated_task.comments) > 0
    
    def test_request_revision(self, manager):
        """测试请求修改"""
        items = [
            ReviewItem(
                code="000001",
                name="股票A",
                category=ReviewCategory.NEW_STOCK,
                reason="新增"
            )
        ]
        
        task = manager.create_task(
            title="测试任务",
            description="测试",
            category=ReviewCategory.POOL_UPDATE,
            items=items
        )
        
        manager.assign_task(task.task_id, "expert1")
        
        result = manager.request_revision(
            task.task_id,
            reviewer="expert1",
            feedback="需要补充数据"
        )
        assert result == True
        
        updated_task = manager.get_task(task.task_id)
        assert updated_task.status == ReviewStatus.NEEDS_REVISION
        assert updated_task.assigned_to is None
    
    def test_add_comment(self, manager):
        """测试添加意见"""
        items = [
            ReviewItem(
                code="000001",
                name="股票A",
                category=ReviewCategory.NEW_STOCK,
                reason="新增"
            )
        ]
        
        task = manager.create_task(
            title="测试任务",
            description="测试",
            category=ReviewCategory.POOL_UPDATE,
            items=items
        )
        
        result = manager.add_comment(
            task.task_id,
            reviewer="expert1",
            content="这是一条意见",
            action="comment"
        )
        assert result == True
        
        updated_task = manager.get_task(task.task_id)
        assert len(updated_task.comments) == 1
        assert updated_task.comments[0].content == "这是一条意见"
    
    def test_get_tasks_by_status(self, manager):
        """测试按状态获取任务"""
        items = [
            ReviewItem(
                code="000001",
                name="股票A",
                category=ReviewCategory.NEW_STOCK,
                reason="新增"
            )
        ]
        
        # 创建多个任务
        task1 = manager.create_task(
            title="任务1",
            description="测试",
            category=ReviewCategory.POOL_UPDATE,
            items=items
        )
        task2 = manager.create_task(
            title="任务2",
            description="测试",
            category=ReviewCategory.POOL_UPDATE,
            items=items
        )
        
        # 批准一个任务
        manager.approve_task(task1.task_id, "expert1")
        
        pending_tasks = manager.get_tasks_by_status(ReviewStatus.PENDING)
        approved_tasks = manager.get_tasks_by_status(ReviewStatus.APPROVED)
        
        assert len(pending_tasks) == 1
        assert len(approved_tasks) == 1
    
    def test_get_statistics(self, manager):
        """测试获取统计"""
        items = [
            ReviewItem(
                code="000001",
                name="股票A",
                category=ReviewCategory.NEW_STOCK,
                reason="新增"
            )
        ]
        
        # 创建并处理任务
        task1 = manager.create_task(
            title="任务1",
            description="测试",
            category=ReviewCategory.POOL_UPDATE,
            items=items
        )
        task2 = manager.create_task(
            title="任务2",
            description="测试",
            category=ReviewCategory.POOL_UPDATE,
            items=items
        )
        
        manager.approve_task(task1.task_id, "expert1")
        manager.reject_task(task2.task_id, "expert1", "拒绝")
        
        stats = manager.get_statistics()
        
        assert stats.total_tasks == 2
        assert stats.approved_tasks == 1
        assert stats.rejected_tasks == 1
        assert stats.approval_rate == 50.0


class TestExpertReviewWorkflow:
    """专家审核工作流测试"""
    
    @pytest.fixture
    def temp_storage(self):
        """创建临时存储文件"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('[]')
            temp_path = f.name
        yield temp_path
        if os.path.exists(temp_path):
            os.remove(temp_path)
    
    @pytest.fixture
    def workflow(self, temp_storage):
        """创建测试用工作流"""
        manager = ExpertReviewManager(storage_file=temp_storage)
        return ExpertReviewWorkflow(review_manager=manager)
    
    def test_create_pool_update_review(self, workflow):
        """测试创建股票池更新审核"""
        added_stocks = [
            {'code': '000001', 'name': '股票A', 'score': 75.5},
            {'code': '000002', 'name': '股票B', 'score': 80.0}
        ]
        removed_stocks = [
            {'code': '000003', 'name': '股票C', 'reason': '评分下降'}
        ]
        
        task = workflow.create_pool_update_review(
            added_stocks=added_stocks,
            removed_stocks=removed_stocks,
            screening_summary={'total': 100}
        )
        
        assert task is not None
        assert task.category == ReviewCategory.POOL_UPDATE
        assert len(task.items) == 3
    
    def test_create_pool_update_review_empty(self, workflow):
        """测试空变更不创建审核"""
        task = workflow.create_pool_update_review(
            added_stocks=[],
            removed_stocks=[],
            screening_summary={}
        )
        
        assert task is None
    
    def test_create_industry_classification_review(self, workflow):
        """测试创建行业分类审核"""
        low_confidence_stocks = [
            {'code': '000001', 'name': '股票A', 'confidence': 0.3, 'industry': '半导体'},
            {'code': '000002', 'name': '股票B', 'confidence': 0.4, 'industry': '软件'}
        ]
        
        task = workflow.create_industry_classification_review(
            stocks_with_low_confidence=low_confidence_stocks
        )
        
        assert task is not None
        assert task.category == ReviewCategory.INDUSTRY_CLASSIFICATION
        assert len(task.items) == 2
    
    def test_create_data_quality_review(self, workflow):
        """测试创建数据质量审核"""
        quality_issues = [
            {'code': '000001', 'name': '股票A', 'issue': 'ROE数据异常', 'suggestion': '核实数据'}
        ]
        
        task = workflow.create_data_quality_review(
            quality_issues=quality_issues
        )
        
        assert task is not None
        assert task.category == ReviewCategory.DATA_QUALITY
        assert task.priority == ReviewPriority.HIGH
    
    def test_check_review_required_low_confidence(self, workflow):
        """测试低置信度需要审核"""
        stock_data = {
            'code': '000001',
            'name': '股票A',
            'industry_confidence': 0.3
        }
        
        required, reason = workflow.check_review_required(stock_data)
        
        assert required == True
        assert "置信度" in reason
    
    def test_check_review_required_abnormal_score(self, workflow):
        """测试异常评分需要审核"""
        stock_data = {
            'code': '000001',
            'name': '股票A',
            'industry_confidence': 0.8,
            'comprehensive_score': 98
        }
        
        required, reason = workflow.check_review_required(stock_data)
        
        assert required == True
        assert "评分" in reason
    
    def test_check_review_required_missing_data(self, workflow):
        """测试缺少数据需要审核"""
        stock_data = {
            'code': '000001',
            'name': '股票A',
            'industry_confidence': 0.8,
            'comprehensive_score': 75
            # 缺少 roe, pe_ratio, total_market_cap
        }
        
        required, reason = workflow.check_review_required(stock_data)
        
        assert required == True
        assert "缺少" in reason
    
    def test_check_review_not_required(self, workflow):
        """测试正常数据不需要审核"""
        stock_data = {
            'code': '000001',
            'name': '股票A',
            'industry_confidence': 0.8,
            'comprehensive_score': 75,
            'roe': 15.0,
            'pe_ratio': 25.0,
            'total_market_cap': 100e8
        }
        
        required, reason = workflow.check_review_required(stock_data)
        
        assert required == False
        assert reason == ""
    
    def test_get_review_summary(self, workflow):
        """测试获取审核摘要"""
        # 创建一些任务
        workflow.create_pool_update_review(
            added_stocks=[{'code': '000001', 'name': '股票A', 'score': 75}],
            removed_stocks=[],
            screening_summary={}
        )
        
        summary = workflow.get_review_summary()
        
        assert 'statistics' in summary
        assert 'pending_count' in summary
        assert 'pending_tasks' in summary


class TestSingletonPattern:
    """单例模式测试"""
    
    def setup_method(self):
        """每个测试前重置"""
        reset_expert_review_manager()
    
    def teardown_method(self):
        """每个测试后重置"""
        reset_expert_review_manager()
    
    def test_manager_singleton(self):
        """测试管理器单例"""
        manager1 = get_expert_review_manager()
        manager2 = get_expert_review_manager()
        
        assert manager1 is manager2
    
    def test_workflow_singleton(self):
        """测试工作流单例"""
        workflow1 = get_expert_review_workflow()
        workflow2 = get_expert_review_workflow()
        
        assert workflow1 is workflow2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
