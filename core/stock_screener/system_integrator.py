"""
系统集成模块

提供与现有系统的集成功能，包括：
- 股票池配置文件更新
- 向后兼容性保持
- 筛选器和评分系统集成
- 端到端功能测试

Requirements: 1.4, 2.2, 2.4
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Set
from datetime import datetime
import logging
import os
import json
import shutil

from .gradual_rollout import (
    GradualRolloutManager,
    RolloutConfig,
    RolloutPhase,
    RolloutStatus,
    RolloutValidator,
    RolloutReporter,
    get_rollout_manager,
    get_rollout_validator,
    get_rollout_reporter,
)

logger = logging.getLogger(__name__)


@dataclass
class StockPoolEntry:
    """股票池条目"""
    code: str
    name: str
    industry: str = ""
    score: float = 0.0
    rating: str = ""
    added_date: str = ""
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'code': self.code,
            'name': self.name,
            'industry': self.industry,
            'score': self.score,
            'rating': self.rating,
            'added_date': self.added_date,
            'notes': self.notes
        }


@dataclass
class PoolUpdateConfig:
    """股票池更新配置"""
    backup_enabled: bool = True
    backup_dir: str = "data/pool_backups"
    max_backups: int = 10
    validate_before_update: bool = True
    require_approval: bool = False


@dataclass
class IntegrationResult:
    """集成结果"""
    success: bool
    message: str
    updated_files: List[str] = field(default_factory=list)
    backup_files: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class StockPoolConfigUpdater:
    """
    股票池配置更新器
    
    更新股票池配置文件，保持向后兼容性
    
    Requirements: 2.2, 2.4
    """
    
    # 配置文件路径
    CONFIG_PATHS = {
        'tech_stock_pool': 'config/tech_stock_pool.py',
        'stock_pool': 'config/stock_pool.py',
    }
    
    def __init__(self, config: Optional[PoolUpdateConfig] = None):
        """
        初始化配置更新器
        
        Args:
            config: 更新配置
        """
        self.config = config or PoolUpdateConfig()
    
    def update_tech_stock_pool(
        self,
        new_stocks: List[StockPoolEntry],
        preserve_existing: bool = True
    ) -> IntegrationResult:
        """
        更新科技股池配置
        
        Args:
            new_stocks: 新股票列表
            preserve_existing: 是否保留现有股票
        
        Returns:
            IntegrationResult: 更新结果
        """
        config_path = self.CONFIG_PATHS['tech_stock_pool']
        
        try:
            # 备份现有配置
            backup_path = None
            if self.config.backup_enabled:
                backup_path = self._backup_config(config_path)
            
            # 读取现有配置
            existing_stocks = self._read_existing_pool(config_path)
            
            # 合并股票池
            if preserve_existing:
                merged_stocks = self._merge_pools(existing_stocks, new_stocks)
            else:
                merged_stocks = new_stocks
            
            # 生成新配置内容
            new_content = self._generate_pool_config(merged_stocks)
            
            # 写入配置文件
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            result = IntegrationResult(
                success=True,
                message=f"成功更新股票池配置，共{len(merged_stocks)}只股票",
                updated_files=[config_path]
            )
            
            if backup_path:
                result.backup_files.append(backup_path)
            
            logger.info(f"股票池配置更新成功: {config_path}")
            return result
            
        except Exception as e:
            logger.error(f"更新股票池配置失败: {e}")
            return IntegrationResult(
                success=False,
                message=f"更新失败: {str(e)}",
                errors=[str(e)]
            )
    
    def _backup_config(self, config_path: str) -> Optional[str]:
        """备份配置文件"""
        if not os.path.exists(config_path):
            return None
        
        try:
            os.makedirs(self.config.backup_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.basename(config_path)
            backup_path = os.path.join(
                self.config.backup_dir, 
                f"{filename}.{timestamp}.bak"
            )
            
            shutil.copy2(config_path, backup_path)
            
            # 清理旧备份
            self._cleanup_old_backups(filename)
            
            return backup_path
            
        except Exception as e:
            logger.warning(f"备份配置文件失败: {e}")
            return None
    
    def _cleanup_old_backups(self, filename: str):
        """清理旧备份"""
        try:
            backups = []
            for f in os.listdir(self.config.backup_dir):
                if f.startswith(filename) and f.endswith('.bak'):
                    path = os.path.join(self.config.backup_dir, f)
                    backups.append((path, os.path.getmtime(path)))
            
            # 按时间排序，删除最旧的
            backups.sort(key=lambda x: x[1], reverse=True)
            for path, _ in backups[self.config.max_backups:]:
                os.remove(path)
                
        except Exception as e:
            logger.warning(f"清理旧备份失败: {e}")
    
    def _read_existing_pool(self, config_path: str) -> List[StockPoolEntry]:
        """读取现有股票池"""
        stocks = []
        
        if not os.path.exists(config_path):
            return stocks
        
        try:
            # 动态导入配置模块
            import importlib.util
            spec = importlib.util.spec_from_file_location("pool_config", config_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # 尝试获取股票池数据
                if hasattr(module, 'TECH_STOCK_POOL'):
                    pool_data = module.TECH_STOCK_POOL
                    for code, info in pool_data.items():
                        stocks.append(StockPoolEntry(
                            code=code,
                            name=info.get('name', ''),
                            industry=info.get('industry', ''),
                            score=info.get('score', 0),
                            rating=info.get('rating', ''),
                            added_date=info.get('added_date', ''),
                            notes=info.get('notes', '')
                        ))
                        
        except Exception as e:
            logger.warning(f"读取现有股票池失败: {e}")
        
        return stocks
    
    def _merge_pools(
        self,
        existing: List[StockPoolEntry],
        new: List[StockPoolEntry]
    ) -> List[StockPoolEntry]:
        """合并股票池"""
        merged = {}
        
        # 先添加现有股票
        for stock in existing:
            merged[stock.code] = stock
        
        # 更新或添加新股票
        for stock in new:
            if stock.code in merged:
                # 更新现有股票的评分和评级
                existing_stock = merged[stock.code]
                existing_stock.score = stock.score
                existing_stock.rating = stock.rating
                if stock.industry:
                    existing_stock.industry = stock.industry
            else:
                # 添加新股票
                stock.added_date = datetime.now().strftime("%Y-%m-%d")
                merged[stock.code] = stock
        
        return list(merged.values())
    
    def _generate_pool_config(self, stocks: List[StockPoolEntry]) -> str:
        """生成股票池配置文件内容"""
        lines = [
            '"""',
            '科技股票池配置',
            '',
            '自动生成，请勿手动修改',
            f'更新时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
            f'股票数量: {len(stocks)}',
            '"""',
            '',
            '# 科技股票池',
            'TECH_STOCK_POOL = {',
        ]
        
        # 按代码排序
        stocks.sort(key=lambda x: x.code)
        
        for stock in stocks:
            lines.append(f'    "{stock.code}": {{')
            lines.append(f'        "name": "{stock.name}",')
            lines.append(f'        "industry": "{stock.industry}",')
            lines.append(f'        "score": {stock.score:.1f},')
            lines.append(f'        "rating": "{stock.rating}",')
            lines.append(f'        "added_date": "{stock.added_date}",')
            lines.append(f'        "notes": "{stock.notes}",')
            lines.append('    },')
        
        lines.append('}')
        lines.append('')
        lines.append('# 股票代码列表（便于快速访问）')
        lines.append('TECH_STOCK_CODES = list(TECH_STOCK_POOL.keys())')
        lines.append('')
        lines.append('# 按行业分组')
        lines.append('def get_stocks_by_industry(industry: str) -> list:')
        lines.append('    """获取指定行业的股票"""')
        lines.append('    return [code for code, info in TECH_STOCK_POOL.items() if info.get("industry") == industry]')
        lines.append('')
        lines.append('# 获取所有行业')
        lines.append('def get_all_industries() -> list:')
        lines.append('    """获取所有行业列表"""')
        lines.append('    return list(set(info.get("industry", "") for info in TECH_STOCK_POOL.values() if info.get("industry")))')
        lines.append('')
        
        return '\n'.join(lines)
    
    def restore_from_backup(self, backup_path: str, target_path: str) -> IntegrationResult:
        """从备份恢复配置"""
        try:
            if not os.path.exists(backup_path):
                return IntegrationResult(
                    success=False,
                    message=f"备份文件不存在: {backup_path}",
                    errors=["备份文件不存在"]
                )
            
            shutil.copy2(backup_path, target_path)
            
            return IntegrationResult(
                success=True,
                message=f"成功从备份恢复: {backup_path}",
                updated_files=[target_path]
            )
            
        except Exception as e:
            return IntegrationResult(
                success=False,
                message=f"恢复失败: {str(e)}",
                errors=[str(e)]
            )


class SystemIntegrator:
    """
    系统集成器
    
    集成筛选系统与现有系统
    
    Requirements: 1.4
    """
    
    def __init__(self):
        """初始化系统集成器"""
        self.config_updater = StockPoolConfigUpdater()
    
    def integrate_screening_results(
        self,
        screening_results: List[Any],
        update_config: bool = True
    ) -> IntegrationResult:
        """
        集成筛选结果到现有系统
        
        Args:
            screening_results: 筛选结果列表（ComprehensiveScore对象）
            update_config: 是否更新配置文件
        
        Returns:
            IntegrationResult: 集成结果
        """
        try:
            # 转换为股票池条目
            pool_entries = []
            for result in screening_results:
                if hasattr(result, 'passed') and result.passed:
                    entry = StockPoolEntry(
                        code=result.code,
                        name=result.name,
                        industry=result.tech_industry.value if result.tech_industry else '',
                        score=result.total_score,
                        rating=result.rating.value if result.rating else '',
                        added_date=datetime.now().strftime("%Y-%m-%d")
                    )
                    pool_entries.append(entry)
            
            if not pool_entries:
                return IntegrationResult(
                    success=False,
                    message="没有通过筛选的股票",
                    warnings=["筛选结果为空"]
                )
            
            # 更新配置文件
            if update_config:
                result = self.config_updater.update_tech_stock_pool(pool_entries)
                return result
            
            return IntegrationResult(
                success=True,
                message=f"准备集成{len(pool_entries)}只股票",
                warnings=["配置文件未更新（update_config=False）"]
            )
            
        except Exception as e:
            logger.error(f"集成筛选结果失败: {e}")
            return IntegrationResult(
                success=False,
                message=f"集成失败: {str(e)}",
                errors=[str(e)]
            )
    
    def validate_integration(self) -> Tuple[bool, List[str]]:
        """
        验证系统集成
        
        Returns:
            Tuple[是否通过, 问题列表]
        """
        issues = []
        
        # 检查配置文件是否存在
        for name, path in StockPoolConfigUpdater.CONFIG_PATHS.items():
            if not os.path.exists(path):
                issues.append(f"配置文件不存在: {path}")
        
        # 检查模块导入
        try:
            from core.stock_screener import (
                DataSourceManager,
                DataCleaner,
                IndustryScreener,
                FinancialScreener,
                MarketScreener,
                ComprehensiveScorer
            )
        except ImportError as e:
            issues.append(f"模块导入失败: {e}")
        
        # 检查数据目录
        data_dirs = ['data', 'data/pool_backups']
        for dir_path in data_dirs:
            if not os.path.exists(dir_path):
                try:
                    os.makedirs(dir_path, exist_ok=True)
                except Exception as e:
                    issues.append(f"无法创建目录 {dir_path}: {e}")
        
        return len(issues) == 0, issues
    
    def get_integration_status(self) -> Dict[str, Any]:
        """获取集成状态"""
        status = {
            'config_files': {},
            'modules': {},
            'data_dirs': {},
            'gradual_rollout': {}
        }
        
        # 检查配置文件
        for name, path in StockPoolConfigUpdater.CONFIG_PATHS.items():
            status['config_files'][name] = {
                'path': path,
                'exists': os.path.exists(path)
            }
        
        # 检查模块
        modules_to_check = [
            'core.stock_screener.data_source',
            'core.stock_screener.data_cleaner',
            'core.stock_screener.industry_screener',
            'core.stock_screener.financial_screener',
            'core.stock_screener.market_screener',
            'core.stock_screener.comprehensive_scorer',
            'core.stock_screener.quality_validator',
            'core.stock_screener.risk_controller',
            'core.stock_screener.pool_updater',
            'core.stock_screener.gradual_rollout',
        ]
        
        for module_name in modules_to_check:
            try:
                __import__(module_name)
                status['modules'][module_name] = True
            except ImportError:
                status['modules'][module_name] = False
        
        # 检查数据目录
        data_dirs = ['data', 'data/pool_backups', 'logs']
        for dir_path in data_dirs:
            status['data_dirs'][dir_path] = os.path.exists(dir_path)
        
        # 检查渐进式上线状态
        try:
            rollout_manager = get_rollout_manager()
            status['gradual_rollout'] = rollout_manager.get_rollout_progress()
        except Exception as e:
            status['gradual_rollout'] = {'error': str(e)}
        
        return status
    
    def integrate_with_gradual_rollout(
        self,
        screening_results: List[Any],
        current_pool: List[str],
        rollout_config: Optional[RolloutConfig] = None
    ) -> IntegrationResult:
        """
        使用渐进式上线策略集成筛选结果
        
        Args:
            screening_results: 筛选结果列表（ComprehensiveScore对象）
            current_pool: 当前股票池代码列表
            rollout_config: 渐进式上线配置
        
        Returns:
            IntegrationResult: 集成结果
        
        Requirements: 业务风险 - 实现渐进式上线策略
        """
        try:
            # 转换为股票代码列表
            new_pool = []
            for result in screening_results:
                if hasattr(result, 'passed') and result.passed:
                    new_pool.append(result.code)
            
            if not new_pool:
                return IntegrationResult(
                    success=False,
                    message="没有通过筛选的股票",
                    warnings=["筛选结果为空"]
                )
            
            # 启动渐进式上线
            rollout_manager = get_rollout_manager()
            
            # 检查是否有正在进行的上线
            progress = rollout_manager.get_rollout_progress()
            if progress.get('has_active_rollout') and progress.get('status') == 'in_progress':
                return IntegrationResult(
                    success=False,
                    message="已有正在进行的渐进式上线任务",
                    warnings=["请先完成或取消当前上线任务"]
                )
            
            # 启动渐进式上线
            state = rollout_manager.start_rollout(current_pool, new_pool, rollout_config)
            
            logger.info(f"渐进式上线已启动: {state.rollout_id}")
            
            return IntegrationResult(
                success=True,
                message=f"渐进式上线已启动: {state.rollout_id}，目标{len(new_pool)}只股票",
                warnings=[
                    f"当前阶段: {state.current_phase.value}",
                    f"原始股票: {len(current_pool)}只",
                    f"目标股票: {len(new_pool)}只",
                    f"新增股票: {len(set(new_pool) - set(current_pool))}只"
                ]
            )
            
        except Exception as e:
            logger.error(f"渐进式上线集成失败: {e}")
            return IntegrationResult(
                success=False,
                message=f"集成失败: {str(e)}",
                errors=[str(e)]
            )
    
    def advance_gradual_rollout(self) -> IntegrationResult:
        """
        推进渐进式上线到下一阶段
        
        Returns:
            IntegrationResult: 推进结果
        
        Requirements: 业务风险 - 实现渐进式上线策略
        """
        try:
            rollout_manager = get_rollout_manager()
            
            # 检查是否有正在进行的上线
            progress = rollout_manager.get_rollout_progress()
            if not progress.get('has_active_rollout'):
                return IntegrationResult(
                    success=False,
                    message="没有正在进行的渐进式上线任务"
                )
            
            # 推进到下一阶段
            success, message = rollout_manager.advance_to_next_phase()
            
            # 获取更新后的进度
            new_progress = rollout_manager.get_rollout_progress()
            
            if success:
                # 如果推进到全量阶段，更新配置文件
                if new_progress.get('current_phase') == 'full':
                    active_pool = rollout_manager.get_current_pool()
                    # 这里可以触发配置文件更新
                    logger.info(f"渐进式上线完成，最终股票池: {len(active_pool)}只")
            
            return IntegrationResult(
                success=success,
                message=message,
                warnings=[
                    f"当前阶段: {new_progress.get('current_phase')}",
                    f"进度: {new_progress.get('progress_percent', 0):.1f}%",
                    f"活跃股票: {new_progress.get('active_pool_size', 0)}只"
                ]
            )
            
        except Exception as e:
            logger.error(f"推进渐进式上线失败: {e}")
            return IntegrationResult(
                success=False,
                message=f"推进失败: {str(e)}",
                errors=[str(e)]
            )
    
    def rollback_gradual_rollout(self, reason: str = "") -> IntegrationResult:
        """
        回滚渐进式上线
        
        Args:
            reason: 回滚原因
        
        Returns:
            IntegrationResult: 回滚结果
        
        Requirements: 业务风险 - 建立快速回滚机制
        """
        try:
            rollout_manager = get_rollout_manager()
            
            # 检查是否有正在进行的上线
            progress = rollout_manager.get_rollout_progress()
            if not progress.get('has_active_rollout'):
                return IntegrationResult(
                    success=False,
                    message="没有正在进行的渐进式上线任务"
                )
            
            # 执行回滚
            success, message = rollout_manager.rollback(reason)
            
            if success:
                logger.warning(f"渐进式上线已回滚: {reason}")
            
            return IntegrationResult(
                success=success,
                message=message,
                warnings=[f"回滚原因: {reason}"] if reason else []
            )
            
        except Exception as e:
            logger.error(f"回滚渐进式上线失败: {e}")
            return IntegrationResult(
                success=False,
                message=f"回滚失败: {str(e)}",
                errors=[str(e)]
            )
    
    def validate_gradual_rollout_phase(self) -> IntegrationResult:
        """
        验证当前渐进式上线阶段
        
        Returns:
            IntegrationResult: 验证结果
        
        Requirements: 业务风险 - 实现渐进式上线策略
        """
        try:
            rollout_manager = get_rollout_manager()
            rollout_validator = get_rollout_validator()
            
            # 检查是否有正在进行的上线
            progress = rollout_manager.get_rollout_progress()
            if not progress.get('has_active_rollout'):
                return IntegrationResult(
                    success=False,
                    message="没有正在进行的渐进式上线任务"
                )
            
            # 获取当前状态
            state = rollout_manager.current_state
            if not state:
                return IntegrationResult(
                    success=False,
                    message="无法获取上线状态"
                )
            
            # 验证当前阶段
            passed, results = rollout_validator.validate_phase(
                state.current_phase,
                state.active_pool,
                state.original_pool
            )
            
            warnings = []
            for check in results.get('checks', []):
                if not check.get('passed'):
                    warnings.append(f"{check.get('name')}: {check.get('message')}")
            
            return IntegrationResult(
                success=passed,
                message="阶段验证通过" if passed else "阶段验证未通过",
                warnings=warnings
            )
            
        except Exception as e:
            logger.error(f"验证渐进式上线阶段失败: {e}")
            return IntegrationResult(
                success=False,
                message=f"验证失败: {str(e)}",
                errors=[str(e)]
            )
    
    def get_gradual_rollout_report(self) -> str:
        """
        获取渐进式上线报告
        
        Returns:
            报告文本
        
        Requirements: 业务风险 - 实现渐进式上线策略
        """
        try:
            rollout_reporter = get_rollout_reporter()
            return rollout_reporter.generate_progress_report()
        except Exception as e:
            logger.error(f"生成渐进式上线报告失败: {e}")
            return f"生成报告失败: {str(e)}"


# 全局实例
_config_updater: Optional[StockPoolConfigUpdater] = None
_system_integrator: Optional[SystemIntegrator] = None


def get_config_updater() -> StockPoolConfigUpdater:
    """获取配置更新器实例"""
    global _config_updater
    if _config_updater is None:
        _config_updater = StockPoolConfigUpdater()
    return _config_updater


def get_system_integrator() -> SystemIntegrator:
    """获取系统集成器实例"""
    global _system_integrator
    if _system_integrator is None:
        _system_integrator = SystemIntegrator()
    return _system_integrator
