"""
部署管理模块

提供生产环境部署功能，包括：
- 环境检测和验证
- 数据迁移和初始化
- 上线前测试
- 部署状态管理

Requirements: 13.1, 技术约束
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from datetime import datetime
import logging
import os
import sys
import json
import shutil

logger = logging.getLogger(__name__)


class DeploymentStatus(Enum):
    """部署状态"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLBACK = "rollback"


class CheckStatus(Enum):
    """检查状态"""
    PASSED = "passed"
    WARNING = "warning"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class CheckResult:
    """检查结果"""
    name: str
    status: CheckStatus
    message: str
    details: Optional[Dict[str, Any]] = None


@dataclass
class DeploymentResult:
    """部署结果"""
    success: bool
    status: DeploymentStatus
    timestamp: datetime
    checks: List[CheckResult] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0


class EnvironmentChecker:
    """
    环境检查器
    
    检查生产环境的各项配置和依赖
    """
    
    # 必需的目录
    REQUIRED_DIRS = [
        'data',
        'data/processed',
        'data/pool_backups',
        'logs',
        'config',
        'core/stock_screener',
    ]
    
    # 必需的配置文件
    REQUIRED_FILES = [
        'config/settings.py',
        'config/tech_stock_config.py',
        'config/tech_stock_pool.py',
    ]
    
    # 必需的Python包
    REQUIRED_PACKAGES = [
        'pandas',
        'numpy',
    ]
    
    # 可选的Python包
    OPTIONAL_PACKAGES = [
        'akshare',
        'streamlit',
    ]
    
    def check_all(self) -> List[CheckResult]:
        """执行所有检查"""
        results = []
        
        # 1. 检查Python版本
        results.append(self._check_python_version())
        
        # 2. 检查目录结构
        results.extend(self._check_directories())
        
        # 3. 检查配置文件
        results.extend(self._check_config_files())
        
        # 4. 检查Python包
        results.extend(self._check_packages())
        
        # 5. 检查模块导入
        results.append(self._check_module_imports())
        
        # 6. 检查数据完整性
        results.append(self._check_data_integrity())
        
        return results
    
    def _check_python_version(self) -> CheckResult:
        """检查Python版本"""
        version = sys.version_info
        version_str = f"{version.major}.{version.minor}.{version.micro}"
        
        if version.major >= 3 and version.minor >= 8:
            return CheckResult(
                name="Python版本",
                status=CheckStatus.PASSED,
                message=f"Python {version_str}",
                details={'version': version_str}
            )
        else:
            return CheckResult(
                name="Python版本",
                status=CheckStatus.FAILED,
                message=f"Python版本过低: {version_str}，需要3.8+",
                details={'version': version_str, 'required': '3.8+'}
            )
    
    def _check_directories(self) -> List[CheckResult]:
        """检查目录结构"""
        results = []
        
        for dir_path in self.REQUIRED_DIRS:
            if os.path.exists(dir_path):
                results.append(CheckResult(
                    name=f"目录: {dir_path}",
                    status=CheckStatus.PASSED,
                    message="目录存在"
                ))
            else:
                # 尝试创建目录
                try:
                    os.makedirs(dir_path, exist_ok=True)
                    results.append(CheckResult(
                        name=f"目录: {dir_path}",
                        status=CheckStatus.WARNING,
                        message="目录已创建"
                    ))
                except Exception as e:
                    results.append(CheckResult(
                        name=f"目录: {dir_path}",
                        status=CheckStatus.FAILED,
                        message=f"无法创建目录: {e}"
                    ))
        
        return results
    
    def _check_config_files(self) -> List[CheckResult]:
        """检查配置文件"""
        results = []
        
        for file_path in self.REQUIRED_FILES:
            if os.path.exists(file_path):
                results.append(CheckResult(
                    name=f"配置文件: {file_path}",
                    status=CheckStatus.PASSED,
                    message="文件存在"
                ))
            else:
                results.append(CheckResult(
                    name=f"配置文件: {file_path}",
                    status=CheckStatus.FAILED,
                    message="文件不存在"
                ))
        
        return results
    
    def _check_packages(self) -> List[CheckResult]:
        """检查Python包"""
        results = []
        
        for package in self.REQUIRED_PACKAGES:
            try:
                __import__(package)
                results.append(CheckResult(
                    name=f"包: {package}",
                    status=CheckStatus.PASSED,
                    message="已安装"
                ))
            except ImportError:
                results.append(CheckResult(
                    name=f"包: {package}",
                    status=CheckStatus.FAILED,
                    message="未安装"
                ))
        
        for package in self.OPTIONAL_PACKAGES:
            try:
                __import__(package)
                results.append(CheckResult(
                    name=f"可选包: {package}",
                    status=CheckStatus.PASSED,
                    message="已安装"
                ))
            except ImportError:
                results.append(CheckResult(
                    name=f"可选包: {package}",
                    status=CheckStatus.WARNING,
                    message="未安装（可选）"
                ))
        
        return results
    
    def _check_module_imports(self) -> CheckResult:
        """检查模块导入"""
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
            'core.stock_screener.system_integrator',
            'core.stock_screener.performance_optimizer',
        ]
        
        failed_modules = []
        for module in modules_to_check:
            try:
                __import__(module)
            except ImportError as e:
                failed_modules.append(f"{module}: {e}")
        
        if not failed_modules:
            return CheckResult(
                name="模块导入",
                status=CheckStatus.PASSED,
                message=f"所有{len(modules_to_check)}个模块导入成功"
            )
        else:
            return CheckResult(
                name="模块导入",
                status=CheckStatus.FAILED,
                message=f"{len(failed_modules)}个模块导入失败",
                details={'failed': failed_modules}
            )
    
    def _check_data_integrity(self) -> CheckResult:
        """检查数据完整性"""
        data_files = [
            'data/positions.csv',
            'data/signal_history.csv',
        ]
        
        existing = []
        missing = []
        
        for file_path in data_files:
            if os.path.exists(file_path):
                existing.append(file_path)
            else:
                missing.append(file_path)
        
        if not missing:
            return CheckResult(
                name="数据文件",
                status=CheckStatus.PASSED,
                message=f"所有{len(data_files)}个数据文件存在"
            )
        else:
            return CheckResult(
                name="数据文件",
                status=CheckStatus.WARNING,
                message=f"{len(missing)}个数据文件缺失（将在首次运行时创建）",
                details={'missing': missing}
            )


class DataMigrator:
    """
    数据迁移器
    
    处理数据迁移和初始化
    """
    
    def __init__(self, backup_dir: str = "data/pool_backups"):
        """初始化数据迁移器"""
        self.backup_dir = backup_dir
    
    def backup_current_data(self) -> Tuple[bool, str]:
        """
        备份当前数据
        
        Returns:
            Tuple[是否成功, 备份路径或错误信息]
        """
        try:
            os.makedirs(self.backup_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(self.backup_dir, f"backup_{timestamp}")
            os.makedirs(backup_path, exist_ok=True)
            
            # 备份配置文件
            config_files = [
                'config/tech_stock_pool.py',
                'config/tech_stock_config.py',
            ]
            
            for file_path in config_files:
                if os.path.exists(file_path):
                    dest = os.path.join(backup_path, os.path.basename(file_path))
                    shutil.copy2(file_path, dest)
            
            # 备份数据文件
            data_files = [
                'data/positions.csv',
                'data/signal_history.csv',
                'data/pool_update_history.json',
            ]
            
            for file_path in data_files:
                if os.path.exists(file_path):
                    dest = os.path.join(backup_path, os.path.basename(file_path))
                    shutil.copy2(file_path, dest)
            
            logger.info(f"数据备份完成: {backup_path}")
            return True, backup_path
            
        except Exception as e:
            logger.error(f"数据备份失败: {e}")
            return False, str(e)
    
    def initialize_data(self) -> Tuple[bool, List[str]]:
        """
        初始化数据
        
        Returns:
            Tuple[是否成功, 初始化的文件列表]
        """
        initialized = []
        
        try:
            # 确保目录存在
            os.makedirs('data', exist_ok=True)
            os.makedirs('data/processed', exist_ok=True)
            os.makedirs('data/pool_backups', exist_ok=True)
            
            # 初始化positions.csv
            if not os.path.exists('data/positions.csv'):
                with open('data/positions.csv', 'w', encoding='utf-8') as f:
                    f.write('code,name,buy_date,buy_price,shares,current_price,profit_pct,status\n')
                initialized.append('data/positions.csv')
            
            # 初始化signal_history.csv
            if not os.path.exists('data/signal_history.csv'):
                with open('data/signal_history.csv', 'w', encoding='utf-8') as f:
                    f.write('date,code,name,signal_type,price,strategy,notes\n')
                initialized.append('data/signal_history.csv')
            
            # 初始化pool_update_history.json
            if not os.path.exists('data/pool_update_history.json'):
                with open('data/pool_update_history.json', 'w', encoding='utf-8') as f:
                    json.dump([], f)
                initialized.append('data/pool_update_history.json')
            
            logger.info(f"数据初始化完成: {initialized}")
            return True, initialized
            
        except Exception as e:
            logger.error(f"数据初始化失败: {e}")
            return False, []
    
    def restore_from_backup(self, backup_path: str) -> Tuple[bool, str]:
        """
        从备份恢复数据
        
        Args:
            backup_path: 备份路径
        
        Returns:
            Tuple[是否成功, 消息]
        """
        try:
            if not os.path.exists(backup_path):
                return False, f"备份路径不存在: {backup_path}"
            
            # 恢复配置文件
            for filename in os.listdir(backup_path):
                src = os.path.join(backup_path, filename)
                if filename.endswith('.py'):
                    dest = os.path.join('config', filename)
                else:
                    dest = os.path.join('data', filename)
                
                if os.path.isfile(src):
                    shutil.copy2(src, dest)
            
            logger.info(f"数据恢复完成: {backup_path}")
            return True, "恢复成功"
            
        except Exception as e:
            logger.error(f"数据恢复失败: {e}")
            return False, str(e)


class PreDeploymentTester:
    """
    上线前测试器
    
    执行上线前的各项测试
    """
    
    def run_all_tests(self) -> List[CheckResult]:
        """运行所有测试"""
        results = []
        
        # 1. 测试配置加载
        results.append(self._test_config_loading())
        
        # 2. 测试模块功能
        results.append(self._test_module_functions())
        
        # 3. 测试数据访问
        results.append(self._test_data_access())
        
        # 4. 测试日志系统
        results.append(self._test_logging())
        
        return results
    
    def _test_config_loading(self) -> CheckResult:
        """测试配置加载"""
        try:
            from config.settings import get_settings
            settings = get_settings()
            
            if settings is not None:
                return CheckResult(
                    name="配置加载测试",
                    status=CheckStatus.PASSED,
                    message="配置加载成功"
                )
            else:
                return CheckResult(
                    name="配置加载测试",
                    status=CheckStatus.FAILED,
                    message="配置加载返回None"
                )
        except Exception as e:
            return CheckResult(
                name="配置加载测试",
                status=CheckStatus.FAILED,
                message=f"配置加载失败: {e}"
            )
    
    def _test_module_functions(self) -> CheckResult:
        """测试模块功能"""
        try:
            from core.stock_screener import (
                get_data_source_manager,
                get_data_cleaner,
                get_industry_screener,
                get_financial_screener,
                get_market_screener,
                get_comprehensive_scorer,
                get_quality_monitor,
                get_risk_assessor,
            )
            
            # 测试实例化
            _ = get_data_source_manager()
            _ = get_data_cleaner()
            _ = get_industry_screener()
            _ = get_financial_screener()
            _ = get_market_screener()
            _ = get_comprehensive_scorer()
            _ = get_quality_monitor()
            _ = get_risk_assessor()
            
            return CheckResult(
                name="模块功能测试",
                status=CheckStatus.PASSED,
                message="所有模块实例化成功"
            )
        except Exception as e:
            return CheckResult(
                name="模块功能测试",
                status=CheckStatus.FAILED,
                message=f"模块功能测试失败: {e}"
            )
    
    def _test_data_access(self) -> CheckResult:
        """测试数据访问"""
        try:
            import pandas as pd
            
            # 测试读取股票池
            from config.tech_stock_pool import get_tech_stock_pool
            pool = get_tech_stock_pool()
            
            if pool is not None:
                codes = pool.get_all_codes()
                return CheckResult(
                    name="数据访问测试",
                    status=CheckStatus.PASSED,
                    message=f"股票池访问成功，共{len(codes)}只股票"
                )
            else:
                return CheckResult(
                    name="数据访问测试",
                    status=CheckStatus.WARNING,
                    message="股票池为空"
                )
        except Exception as e:
            return CheckResult(
                name="数据访问测试",
                status=CheckStatus.FAILED,
                message=f"数据访问测试失败: {e}"
            )
    
    def _test_logging(self) -> CheckResult:
        """测试日志系统"""
        try:
            from core.logging_config import setup_logging, get_logger
            
            # 测试日志配置
            setup_logging(console_output=False)
            test_logger = get_logger("deployment_test")
            test_logger.info("部署测试日志")
            
            return CheckResult(
                name="日志系统测试",
                status=CheckStatus.PASSED,
                message="日志系统正常"
            )
        except Exception as e:
            return CheckResult(
                name="日志系统测试",
                status=CheckStatus.FAILED,
                message=f"日志系统测试失败: {e}"
            )


class DeploymentManager:
    """
    部署管理器
    
    管理整个部署流程
    """
    
    def __init__(self):
        """初始化部署管理器"""
        self.env_checker = EnvironmentChecker()
        self.data_migrator = DataMigrator()
        self.tester = PreDeploymentTester()
        self.status = DeploymentStatus.NOT_STARTED
    
    def deploy(self, backup: bool = True) -> DeploymentResult:
        """
        执行部署
        
        Args:
            backup: 是否备份现有数据
        
        Returns:
            DeploymentResult: 部署结果
        """
        start_time = datetime.now()
        self.status = DeploymentStatus.IN_PROGRESS
        
        all_checks = []
        warnings = []
        errors = []
        
        try:
            # 阶段1: 环境检查
            logger.info("开始环境检查...")
            env_checks = self.env_checker.check_all()
            all_checks.extend(env_checks)
            
            # 检查是否有失败项
            failed_checks = [c for c in env_checks if c.status == CheckStatus.FAILED]
            if failed_checks:
                errors.extend([f"{c.name}: {c.message}" for c in failed_checks])
                self.status = DeploymentStatus.FAILED
                return DeploymentResult(
                    success=False,
                    status=self.status,
                    timestamp=start_time,
                    checks=all_checks,
                    warnings=warnings,
                    errors=errors,
                    duration_seconds=(datetime.now() - start_time).total_seconds()
                )
            
            # 阶段2: 数据备份
            if backup:
                logger.info("开始数据备份...")
                success, backup_result = self.data_migrator.backup_current_data()
                if success:
                    all_checks.append(CheckResult(
                        name="数据备份",
                        status=CheckStatus.PASSED,
                        message=f"备份完成: {backup_result}"
                    ))
                else:
                    warnings.append(f"数据备份失败: {backup_result}")
                    all_checks.append(CheckResult(
                        name="数据备份",
                        status=CheckStatus.WARNING,
                        message=f"备份失败: {backup_result}"
                    ))
            
            # 阶段3: 数据初始化
            logger.info("开始数据初始化...")
            success, initialized = self.data_migrator.initialize_data()
            if success:
                all_checks.append(CheckResult(
                    name="数据初始化",
                    status=CheckStatus.PASSED,
                    message=f"初始化完成: {len(initialized)}个文件"
                ))
            else:
                errors.append("数据初始化失败")
                all_checks.append(CheckResult(
                    name="数据初始化",
                    status=CheckStatus.FAILED,
                    message="初始化失败"
                ))
            
            # 阶段4: 上线前测试
            logger.info("开始上线前测试...")
            test_results = self.tester.run_all_tests()
            all_checks.extend(test_results)
            
            # 检查测试结果
            failed_tests = [t for t in test_results if t.status == CheckStatus.FAILED]
            if failed_tests:
                errors.extend([f"{t.name}: {t.message}" for t in failed_tests])
            
            # 收集警告
            warning_checks = [c for c in all_checks if c.status == CheckStatus.WARNING]
            warnings.extend([f"{c.name}: {c.message}" for c in warning_checks])
            
            # 确定最终状态
            if errors:
                self.status = DeploymentStatus.FAILED
                success = False
            else:
                self.status = DeploymentStatus.COMPLETED
                success = True
            
            logger.info(f"部署完成: {'成功' if success else '失败'}")
            
            return DeploymentResult(
                success=success,
                status=self.status,
                timestamp=start_time,
                checks=all_checks,
                warnings=warnings,
                errors=errors,
                duration_seconds=(datetime.now() - start_time).total_seconds()
            )
            
        except Exception as e:
            logger.error(f"部署过程出错: {e}")
            self.status = DeploymentStatus.FAILED
            errors.append(str(e))
            
            return DeploymentResult(
                success=False,
                status=self.status,
                timestamp=start_time,
                checks=all_checks,
                warnings=warnings,
                errors=errors,
                duration_seconds=(datetime.now() - start_time).total_seconds()
            )
    
    def generate_deployment_report(self, result: DeploymentResult) -> str:
        """生成部署报告"""
        lines = [
            "=" * 60,
            "生产环境部署报告",
            "=" * 60,
            f"部署时间: {result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            f"部署状态: {result.status.value}",
            f"耗时: {result.duration_seconds:.2f}秒",
            "",
            "检查结果:",
        ]
        
        # 按状态分组
        passed = [c for c in result.checks if c.status == CheckStatus.PASSED]
        warnings = [c for c in result.checks if c.status == CheckStatus.WARNING]
        failed = [c for c in result.checks if c.status == CheckStatus.FAILED]
        
        lines.append(f"  ✓ 通过: {len(passed)}")
        lines.append(f"  ⚠ 警告: {len(warnings)}")
        lines.append(f"  ✗ 失败: {len(failed)}")
        lines.append("")
        
        if failed:
            lines.append("失败项:")
            for check in failed:
                lines.append(f"  - {check.name}: {check.message}")
            lines.append("")
        
        if warnings:
            lines.append("警告项:")
            for check in warnings:
                lines.append(f"  - {check.name}: {check.message}")
            lines.append("")
        
        if result.errors:
            lines.append("错误:")
            for error in result.errors:
                lines.append(f"  - {error}")
            lines.append("")
        
        lines.append(f"部署结果: {'成功' if result.success else '失败'}")
        lines.append("=" * 60)
        
        return "\n".join(lines)


# 全局实例
_deployment_manager: Optional[DeploymentManager] = None


def get_deployment_manager() -> DeploymentManager:
    """获取部署管理器实例"""
    global _deployment_manager
    if _deployment_manager is None:
        _deployment_manager = DeploymentManager()
    return _deployment_manager
