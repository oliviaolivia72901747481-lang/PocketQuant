"""
股票池更新机制

提供股票池的动态更新功能，包括：
- 全市场股票扫描
- 多层筛选策略执行
- 候选股票清单生成
- 定期更新调度
- 增量更新算法
- 更新历史记录

Requirements: 1.1, 1.2, 1.5, 5.1, 5.3, 5.4
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Callable
from enum import Enum
from datetime import datetime, timedelta
import logging
import pandas as pd
import numpy as np
import json
import os

from .data_source import DataSourceManager, get_data_source_manager
from .data_cleaner import DataCleaner, get_data_cleaner
from .industry_screener import IndustryScreener, get_industry_screener, TechIndustry
from .financial_screener import FinancialScreener, get_financial_screener
from .market_screener import MarketScreener, get_market_screener
from .comprehensive_scorer import ComprehensiveScorer, get_comprehensive_scorer, ComprehensiveScore
from .quality_validator import DataQualityMonitor, get_quality_monitor
from .risk_controller import RiskAssessor, get_risk_assessor
from .gradual_rollout import (
    GradualRolloutManager,
    RolloutConfig,
    RolloutPhase,
    RolloutStatus,
    get_rollout_manager,
)

logger = logging.getLogger(__name__)


class UpdateStatus(Enum):
    """更新状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScreeningStage(Enum):
    """筛选阶段"""
    DATA_FETCH = "data_fetch"
    DATA_CLEAN = "data_clean"
    INDUSTRY_SCREEN = "industry_screen"
    FINANCIAL_SCREEN = "financial_screen"
    MARKET_SCREEN = "market_screen"
    COMPREHENSIVE_SCORE = "comprehensive_score"
    QUALITY_VALIDATE = "quality_validate"
    RISK_ASSESS = "risk_assess"


@dataclass
class ScreeningProgress:
    """筛选进度"""
    stage: ScreeningStage
    progress: float  # 0-100
    message: str
    stocks_remaining: int = 0


@dataclass
class UpdateHistoryRecord:
    """更新历史记录"""
    update_id: str
    timestamp: datetime
    status: UpdateStatus
    total_scanned: int = 0
    total_passed: int = 0
    added_stocks: List[str] = field(default_factory=list)
    removed_stocks: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'update_id': self.update_id,
            'timestamp': self.timestamp.isoformat(),
            'status': self.status.value,
            'total_scanned': self.total_scanned,
            'total_passed': self.total_passed,
            'added_stocks': self.added_stocks,
            'removed_stocks': self.removed_stocks,
            'duration_seconds': self.duration_seconds,
            'error_message': self.error_message
        }


@dataclass
class PoolUpdateResult:
    """股票池更新结果"""
    success: bool
    timestamp: datetime
    previous_count: int
    current_count: int
    added_stocks: List[str]
    removed_stocks: List[str]
    candidate_stocks: List[ComprehensiveScore]
    screening_summary: Dict[str, int]
    quality_passed: bool
    risk_passed: bool
    warnings: List[str] = field(default_factory=list)
    error: Optional[str] = None


class CandidateScreener:
    """
    候选股票筛选器
    
    执行全市场扫描和多层筛选
    
    Requirements: 1.1, 1.2, 1.5
    """
    
    def __init__(
        self,
        min_score: float = 60.0,
        target_count: int = 100,
        max_single_industry: float = 0.25
    ):
        """
        初始化候选股票筛选器
        
        Args:
            min_score: 最低综合评分
            target_count: 目标股票数量
            max_single_industry: 单一行业最大占比
        """
        self.min_score = min_score
        self.target_count = target_count
        self.max_single_industry = max_single_industry
        
        # 初始化各筛选器
        self.data_source = get_data_source_manager()
        self.data_cleaner = get_data_cleaner()
        self.industry_screener = get_industry_screener()
        self.financial_screener = get_financial_screener()
        self.market_screener = get_market_screener()
        self.comprehensive_scorer = get_comprehensive_scorer()
        self.quality_monitor = get_quality_monitor()
        self.risk_assessor = get_risk_assessor()
    
    def screen_candidates(
        self,
        progress_callback: Optional[Callable[[ScreeningProgress], None]] = None
    ) -> Tuple[pd.DataFrame, List[ComprehensiveScore], Dict[str, int]]:
        """
        执行候选股票筛选
        
        Args:
            progress_callback: 进度回调函数
        
        Returns:
            Tuple[筛选结果DataFrame, 评分列表, 筛选摘要]
        """
        summary = {
            'total_scanned': 0,
            'after_clean': 0,
            'after_industry': 0,
            'after_financial': 0,
            'after_market': 0,
            'final_candidates': 0
        }
        
        def report_progress(stage: ScreeningStage, progress: float, msg: str, remaining: int = 0):
            if progress_callback:
                progress_callback(ScreeningProgress(stage, progress, msg, remaining))
        
        try:
            # 阶段1: 获取全市场数据
            report_progress(ScreeningStage.DATA_FETCH, 0, "正在获取全市场股票数据...")
            df = self._fetch_market_data()
            if df is None or df.empty:
                logger.warning("无法获取市场数据")
                return pd.DataFrame(), [], summary
            
            summary['total_scanned'] = len(df)
            report_progress(ScreeningStage.DATA_FETCH, 100, f"获取到{len(df)}只股票", len(df))
            
            # 阶段2: 数据清洗
            report_progress(ScreeningStage.DATA_CLEAN, 0, "正在清洗数据...")
            df = self.data_cleaner.clean(df)
            df = self.data_cleaner.filter_mainboard_stocks(df)
            df = self.data_cleaner.remove_st_stocks(df)
            summary['after_clean'] = len(df)
            report_progress(ScreeningStage.DATA_CLEAN, 100, f"清洗后剩余{len(df)}只", len(df))
            
            if df.empty:
                return pd.DataFrame(), [], summary
            
            # 阶段3: 行业筛选
            report_progress(ScreeningStage.INDUSTRY_SCREEN, 0, "正在进行行业筛选...")
            df = self.industry_screener.screen_tech_stocks(df)
            summary['after_industry'] = len(df)
            report_progress(ScreeningStage.INDUSTRY_SCREEN, 100, f"科技股{len(df)}只", len(df))
            
            if df.empty:
                return pd.DataFrame(), [], summary
            
            # 阶段4: 财务筛选
            report_progress(ScreeningStage.FINANCIAL_SCREEN, 0, "正在进行财务筛选...")
            df, _ = self.financial_screener.screen_stocks(df)
            summary['after_financial'] = len(df)
            report_progress(ScreeningStage.FINANCIAL_SCREEN, 100, f"财务合格{len(df)}只", len(df))
            
            if df.empty:
                return pd.DataFrame(), [], summary
            
            # 阶段5: 市场表现筛选
            report_progress(ScreeningStage.MARKET_SCREEN, 0, "正在进行市场筛选...")
            df, _ = self.market_screener.screen_stocks(df)
            summary['after_market'] = len(df)
            report_progress(ScreeningStage.MARKET_SCREEN, 100, f"市场合格{len(df)}只", len(df))
            
            if df.empty:
                return pd.DataFrame(), [], summary
            
            # 阶段6: 综合评分
            report_progress(ScreeningStage.COMPREHENSIVE_SCORE, 0, "正在进行综合评分...")
            df, scores = self.comprehensive_scorer.score_stocks(
                df, 
                min_score=self.min_score,
                top_n=self.target_count
            )
            summary['final_candidates'] = len(df)
            report_progress(ScreeningStage.COMPREHENSIVE_SCORE, 100, f"最终候选{len(df)}只", len(df))
            
            # 应用行业分散化
            df, scores = self._apply_industry_diversification(df, scores)
            
            logger.info(f"候选股票筛选完成: {summary}")
            return df, scores, summary
            
        except Exception as e:
            logger.error(f"候选股票筛选失败: {e}")
            return pd.DataFrame(), [], summary
    
    def _fetch_market_data(self) -> pd.DataFrame:
        """获取全市场数据"""
        try:
            # 尝试从数据源获取
            result = self.data_source.fetch_stock_list()
            if result.success and result.data is not None:
                return result.data
            
            # 如果失败，返回空DataFrame
            logger.warning("无法从数据源获取股票列表")
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"获取市场数据失败: {e}")
            return pd.DataFrame()
    
    def _apply_industry_diversification(
        self,
        df: pd.DataFrame,
        scores: List[ComprehensiveScore]
    ) -> Tuple[pd.DataFrame, List[ComprehensiveScore]]:
        """应用行业分散化"""
        if df.empty or not scores:
            return df, scores
        
        # 按行业分组
        industry_groups: Dict[str, List[ComprehensiveScore]] = {}
        for score in scores:
            if score.passed:
                industry = score.tech_industry.value if score.tech_industry else 'unknown'
                if industry not in industry_groups:
                    industry_groups[industry] = []
                industry_groups[industry].append(score)
        
        # 限制单一行业占比
        max_per_industry = int(self.target_count * self.max_single_industry)
        diversified_scores = []
        
        for industry, group in industry_groups.items():
            # 按得分排序，取前N个
            group.sort(key=lambda x: x.total_score, reverse=True)
            diversified_scores.extend(group[:max_per_industry])
        
        # 按总分重新排序
        diversified_scores.sort(key=lambda x: x.total_score, reverse=True)
        
        # 更新DataFrame
        diversified_codes = [s.code for s in diversified_scores]
        df = df[df['code'].isin(diversified_codes)]
        
        return df, diversified_scores


class PoolUpdater:
    """
    股票池更新器
    
    管理股票池的动态更新
    
    Requirements: 5.1, 5.3, 5.4
    """
    
    def __init__(
        self,
        history_file: str = "data/pool_update_history.json",
        max_history: int = 100
    ):
        """
        初始化股票池更新器
        
        Args:
            history_file: 历史记录文件路径
            max_history: 最大历史记录数
        """
        self.history_file = history_file
        self.max_history = max_history
        self.screener = CandidateScreener()
        self.quality_monitor = get_quality_monitor()
        self.risk_assessor = get_risk_assessor()
        self.update_history: List[UpdateHistoryRecord] = []
        
        self._load_history()
    
    def update_pool(
        self,
        current_pool: List[str],
        progress_callback: Optional[Callable[[ScreeningProgress], None]] = None
    ) -> PoolUpdateResult:
        """
        更新股票池
        
        Args:
            current_pool: 当前股票池代码列表
            progress_callback: 进度回调函数
        
        Returns:
            PoolUpdateResult: 更新结果
        """
        start_time = datetime.now()
        update_id = start_time.strftime("%Y%m%d_%H%M%S")
        
        try:
            # 执行筛选
            df, scores, summary = self.screener.screen_candidates(progress_callback)
            
            if df.empty:
                return PoolUpdateResult(
                    success=False,
                    timestamp=start_time,
                    previous_count=len(current_pool),
                    current_count=len(current_pool),
                    added_stocks=[],
                    removed_stocks=[],
                    candidate_stocks=[],
                    screening_summary=summary,
                    quality_passed=False,
                    risk_passed=False,
                    error="筛选结果为空"
                )
            
            # 质量验证
            quality_result = self.quality_monitor.validate(df)
            
            # 风险评估
            risk_result = self.risk_assessor.assess(df)
            
            # 计算变更
            new_codes = set(df['code'].tolist())
            old_codes = set(current_pool)
            
            added = list(new_codes - old_codes)
            removed = list(old_codes - new_codes)
            
            # 记录历史
            duration = (datetime.now() - start_time).total_seconds()
            history_record = UpdateHistoryRecord(
                update_id=update_id,
                timestamp=start_time,
                status=UpdateStatus.COMPLETED,
                total_scanned=summary.get('total_scanned', 0),
                total_passed=len(df),
                added_stocks=added,
                removed_stocks=removed,
                duration_seconds=duration
            )
            self._add_history(history_record)
            
            # 收集警告
            warnings = []
            if not quality_result.passed:
                warnings.extend(quality_result.warnings)
            if not risk_result.passed:
                warnings.extend([w.description for w in risk_result.warnings])
            
            return PoolUpdateResult(
                success=True,
                timestamp=start_time,
                previous_count=len(current_pool),
                current_count=len(df),
                added_stocks=added,
                removed_stocks=removed,
                candidate_stocks=scores,
                screening_summary=summary,
                quality_passed=quality_result.passed,
                risk_passed=risk_result.passed,
                warnings=warnings
            )
            
        except Exception as e:
            logger.error(f"股票池更新失败: {e}")
            
            # 记录失败历史
            history_record = UpdateHistoryRecord(
                update_id=update_id,
                timestamp=start_time,
                status=UpdateStatus.FAILED,
                error_message=str(e)
            )
            self._add_history(history_record)
            
            return PoolUpdateResult(
                success=False,
                timestamp=start_time,
                previous_count=len(current_pool),
                current_count=len(current_pool),
                added_stocks=[],
                removed_stocks=[],
                candidate_stocks=[],
                screening_summary={},
                quality_passed=False,
                risk_passed=False,
                error=str(e)
            )
    
    def get_incremental_changes(
        self,
        current_pool: List[str],
        new_candidates: List[ComprehensiveScore],
        max_changes: int = 10
    ) -> Tuple[List[str], List[str]]:
        """
        计算增量变更
        
        Args:
            current_pool: 当前股票池
            new_candidates: 新候选股票
            max_changes: 最大变更数量
        
        Returns:
            Tuple[新增列表, 移除列表]
        """
        # 按得分排序候选股票
        sorted_candidates = sorted(new_candidates, key=lambda x: x.total_score, reverse=True)
        
        # 获取当前池中股票的得分
        current_scores = {c.code: c.total_score for c in sorted_candidates if c.code in current_pool}
        
        # 找出不在当前池中的高分股票
        potential_adds = [c for c in sorted_candidates if c.code not in current_pool and c.passed]
        
        # 找出当前池中的低分股票
        current_in_candidates = [c for c in sorted_candidates if c.code in current_pool]
        potential_removes = sorted(current_in_candidates, key=lambda x: x.total_score)
        
        # 计算变更
        adds = []
        removes = []
        
        for add_candidate in potential_adds[:max_changes]:
            # 找一个得分更低的股票替换
            for remove_candidate in potential_removes:
                if remove_candidate.code not in removes:
                    if add_candidate.total_score > remove_candidate.total_score + 5:  # 至少高5分
                        adds.append(add_candidate.code)
                        removes.append(remove_candidate.code)
                        break
        
        return adds[:max_changes], removes[:max_changes]
    
    def _load_history(self):
        """加载历史记录"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for record in data:
                        self.update_history.append(UpdateHistoryRecord(
                            update_id=record['update_id'],
                            timestamp=datetime.fromisoformat(record['timestamp']),
                            status=UpdateStatus(record['status']),
                            total_scanned=record.get('total_scanned', 0),
                            total_passed=record.get('total_passed', 0),
                            added_stocks=record.get('added_stocks', []),
                            removed_stocks=record.get('removed_stocks', []),
                            duration_seconds=record.get('duration_seconds', 0),
                            error_message=record.get('error_message')
                        ))
        except Exception as e:
            logger.warning(f"加载历史记录失败: {e}")
    
    def _save_history(self):
        """保存历史记录"""
        try:
            os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump([r.to_dict() for r in self.update_history], f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"保存历史记录失败: {e}")
    
    def _add_history(self, record: UpdateHistoryRecord):
        """添加历史记录"""
        self.update_history.append(record)
        
        # 限制历史记录数量
        if len(self.update_history) > self.max_history:
            self.update_history = self.update_history[-self.max_history:]
        
        self._save_history()
    
    def get_update_history(self, limit: int = 10) -> List[UpdateHistoryRecord]:
        """获取更新历史"""
        return self.update_history[-limit:]
    
    def start_gradual_update(
        self,
        current_pool: List[str],
        new_pool: List[str],
        config: Optional[RolloutConfig] = None,
        progress_callback: Optional[Callable[[ScreeningProgress], None]] = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        启动渐进式股票池更新
        
        使用渐进式上线策略更新股票池，分阶段逐步引入新股票
        
        Args:
            current_pool: 当前股票池代码列表
            new_pool: 新股票池代码列表
            config: 渐进式上线配置
            progress_callback: 进度回调函数
        
        Returns:
            Tuple[是否成功, 消息, 详情]
        
        Requirements: 业务风险 - 实现渐进式上线策略
        """
        try:
            rollout_manager = get_rollout_manager()
            
            # 检查是否有正在进行的上线
            progress = rollout_manager.get_rollout_progress()
            if progress.get('has_active_rollout') and progress.get('status') == 'in_progress':
                return False, "已有正在进行的渐进式上线任务", progress
            
            # 启动渐进式上线
            state = rollout_manager.start_rollout(current_pool, new_pool, config)
            
            logger.info(f"启动渐进式股票池更新: {state.rollout_id}")
            
            return True, f"渐进式上线已启动: {state.rollout_id}", {
                'rollout_id': state.rollout_id,
                'status': state.status.value,
                'current_phase': state.current_phase.value,
                'original_count': len(current_pool),
                'target_count': len(new_pool),
                'added_count': len(set(new_pool) - set(current_pool))
            }
            
        except Exception as e:
            logger.error(f"启动渐进式更新失败: {e}")
            return False, f"启动失败: {str(e)}", {'error': str(e)}
    
    def advance_gradual_update(self) -> Tuple[bool, str, Dict[str, Any]]:
        """
        推进渐进式更新到下一阶段
        
        Returns:
            Tuple[是否成功, 消息, 详情]
        
        Requirements: 业务风险 - 实现渐进式上线策略
        """
        try:
            rollout_manager = get_rollout_manager()
            
            # 检查是否有正在进行的上线
            progress = rollout_manager.get_rollout_progress()
            if not progress.get('has_active_rollout'):
                return False, "没有正在进行的渐进式上线任务", {}
            
            # 推进到下一阶段
            success, message = rollout_manager.advance_to_next_phase()
            
            # 获取更新后的进度
            new_progress = rollout_manager.get_rollout_progress()
            
            if success:
                logger.info(f"渐进式更新推进成功: {new_progress.get('current_phase')}")
            
            return success, message, new_progress
            
        except Exception as e:
            logger.error(f"推进渐进式更新失败: {e}")
            return False, f"推进失败: {str(e)}", {'error': str(e)}
    
    def rollback_gradual_update(self, reason: str = "") -> Tuple[bool, str, Dict[str, Any]]:
        """
        回滚渐进式更新
        
        Args:
            reason: 回滚原因
        
        Returns:
            Tuple[是否成功, 消息, 详情]
        
        Requirements: 业务风险 - 建立快速回滚机制
        """
        try:
            rollout_manager = get_rollout_manager()
            
            # 检查是否有正在进行的上线
            progress = rollout_manager.get_rollout_progress()
            if not progress.get('has_active_rollout'):
                return False, "没有正在进行的渐进式上线任务", {}
            
            # 执行回滚
            success, message = rollout_manager.rollback(reason)
            
            # 获取更新后的进度
            new_progress = rollout_manager.get_rollout_progress()
            
            if success:
                logger.warning(f"渐进式更新已回滚: {reason}")
            
            return success, message, new_progress
            
        except Exception as e:
            logger.error(f"回滚渐进式更新失败: {e}")
            return False, f"回滚失败: {str(e)}", {'error': str(e)}
    
    def get_gradual_update_status(self) -> Dict[str, Any]:
        """
        获取渐进式更新状态
        
        Returns:
            渐进式更新状态信息
        
        Requirements: 业务风险 - 实现渐进式上线策略
        """
        try:
            rollout_manager = get_rollout_manager()
            return rollout_manager.get_rollout_progress()
        except Exception as e:
            logger.error(f"获取渐进式更新状态失败: {e}")
            return {
                'has_active_rollout': False,
                'error': str(e)
            }
    
    def get_active_pool_from_rollout(self) -> List[str]:
        """
        从渐进式上线获取当前活跃的股票池
        
        如果有正在进行的渐进式上线，返回当前阶段的活跃股票池
        否则返回空列表
        
        Returns:
            当前活跃的股票代码列表
        
        Requirements: 业务风险 - 实现渐进式上线策略
        """
        try:
            rollout_manager = get_rollout_manager()
            progress = rollout_manager.get_rollout_progress()
            
            if progress.get('has_active_rollout'):
                return rollout_manager.get_current_pool()
            
            return []
            
        except Exception as e:
            logger.error(f"获取活跃股票池失败: {e}")
            return []
    
    def record_rollout_success(self) -> None:
        """
        记录渐进式上线成功操作
        
        用于跟踪上线过程中的成功操作
        
        Requirements: 业务风险 - 实现渐进式上线策略
        """
        try:
            rollout_manager = get_rollout_manager()
            rollout_manager.record_success()
        except Exception as e:
            logger.warning(f"记录成功操作失败: {e}")
    
    def record_rollout_error(self, error_msg: str) -> Tuple[bool, str]:
        """
        记录渐进式上线错误操作
        
        用于跟踪上线过程中的错误，可能触发自动回滚
        
        Args:
            error_msg: 错误消息
        
        Returns:
            Tuple[是否触发回滚, 消息]
        
        Requirements: 业务风险 - 实现渐进式上线策略
        """
        try:
            rollout_manager = get_rollout_manager()
            triggered, message = rollout_manager.record_error(error_msg)
            return triggered, message
        except Exception as e:
            logger.warning(f"记录错误操作失败: {e}")
            return False, str(e)


# 全局实例
_candidate_screener: Optional[CandidateScreener] = None
_pool_updater: Optional[PoolUpdater] = None


def get_candidate_screener() -> CandidateScreener:
    """获取候选股票筛选器实例"""
    global _candidate_screener
    if _candidate_screener is None:
        _candidate_screener = CandidateScreener()
    return _candidate_screener


def get_pool_updater() -> PoolUpdater:
    """获取股票池更新器实例"""
    global _pool_updater
    if _pool_updater is None:
        _pool_updater = PoolUpdater()
    return _pool_updater
