"""
科技股筛选系统部署脚本

用于执行生产环境部署和验证

使用方法:
    python tools/deploy_screener.py [--check-only] [--no-backup]

参数:
    --check-only: 仅执行检查，不进行部署
    --no-backup: 不备份现有数据

Requirements: 13.1, 13.2
"""

import sys
import os
import argparse
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.logging_config import setup_logging, get_logger
from core.stock_screener.deployment_manager import (
    DeploymentManager,
    EnvironmentChecker,
    CheckStatus,
    get_deployment_manager
)
from core.stock_screener.monitoring import (
    SystemMonitor,
    get_system_monitor
)


def print_header(title: str):
    """打印标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_check_result(name: str, status: CheckStatus, message: str):
    """打印检查结果"""
    icons = {
        CheckStatus.PASSED: "✓",
        CheckStatus.WARNING: "⚠",
        CheckStatus.FAILED: "✗",
        CheckStatus.SKIPPED: "-"
    }
    icon = icons.get(status, "?")
    print(f"  {icon} {name}: {message}")


def run_environment_check():
    """运行环境检查"""
    print_header("环境检查")
    
    checker = EnvironmentChecker()
    results = checker.check_all()
    
    passed = 0
    warnings = 0
    failed = 0
    
    for result in results:
        print_check_result(result.name, result.status, result.message)
        if result.status == CheckStatus.PASSED:
            passed += 1
        elif result.status == CheckStatus.WARNING:
            warnings += 1
        elif result.status == CheckStatus.FAILED:
            failed += 1
    
    print(f"\n  总计: {passed} 通过, {warnings} 警告, {failed} 失败")
    
    return failed == 0


def run_deployment(backup: bool = True):
    """运行部署"""
    print_header("开始部署")
    
    manager = get_deployment_manager()
    result = manager.deploy(backup=backup)
    
    # 打印检查结果
    print("\n检查结果:")
    for check in result.checks:
        print_check_result(check.name, check.status, check.message)
    
    # 打印警告
    if result.warnings:
        print("\n警告:")
        for warning in result.warnings:
            print(f"  ⚠ {warning}")
    
    # 打印错误
    if result.errors:
        print("\n错误:")
        for error in result.errors:
            print(f"  ✗ {error}")
    
    # 打印结果
    print(f"\n部署状态: {result.status.value}")
    print(f"耗时: {result.duration_seconds:.2f}秒")
    print(f"结果: {'成功' if result.success else '失败'}")
    
    return result.success


def run_system_check():
    """运行系统状态检查"""
    print_header("系统状态检查")
    
    monitor = get_system_monitor()
    status = monitor.get_system_status()
    
    print(f"\n整体健康状态: {status['overall_health']}")
    print(f"监控状态: {'运行中' if status['monitoring_active'] else '已停止'}")
    
    print("\n组件状态:")
    for check in status['health_checks']:
        icons = {
            'healthy': '✓',
            'degraded': '⚠',
            'unhealthy': '✗',
            'unknown': '?'
        }
        icon = icons.get(check['status'], '?')
        print(f"  {icon} {check['component']}: {check['message']}")
    
    print("\n告警摘要:")
    alerts = status['alerts']
    print(f"  活跃告警: {alerts['active']}")
    print(f"  严重: {alerts['by_severity']['critical']}")
    print(f"  错误: {alerts['by_severity']['error']}")
    print(f"  警告: {alerts['by_severity']['warning']}")
    
    print("\n维护任务:")
    maint = status['maintenance']
    print(f"  总任务数: {maint['total_tasks']}")
    print(f"  待执行: {maint['pending_tasks']}")
    print(f"  已启用: {maint['enabled_tasks']}")
    
    return status['overall_health'] in ['healthy', 'degraded']


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='科技股筛选系统部署脚本')
    parser.add_argument('--check-only', action='store_true', help='仅执行检查，不进行部署')
    parser.add_argument('--no-backup', action='store_true', help='不备份现有数据')
    parser.add_argument('--status', action='store_true', help='显示系统状态')
    args = parser.parse_args()
    
    # 设置日志
    setup_logging(level='INFO', console_output=True)
    logger = get_logger(__name__)
    
    print_header("科技股筛选系统部署工具")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        if args.status:
            # 仅显示状态
            success = run_system_check()
        elif args.check_only:
            # 仅执行检查
            success = run_environment_check()
        else:
            # 完整部署
            # 1. 环境检查
            if not run_environment_check():
                print("\n环境检查失败，部署中止")
                return 1
            
            # 2. 执行部署
            if not run_deployment(backup=not args.no_backup):
                print("\n部署失败")
                return 1
            
            # 3. 系统状态检查
            success = run_system_check()
        
        print_header("完成")
        
        if success:
            print("所有检查通过！")
            return 0
        else:
            print("存在问题，请检查上述输出")
            return 1
            
    except Exception as e:
        logger.error(f"部署过程出错: {e}")
        print(f"\n错误: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
