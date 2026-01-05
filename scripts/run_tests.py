#!/usr/bin/env python
"""
MiniQuant-Lite 本地测试运行器

科技股池扩充项目的自动化测试脚本
支持多种测试模式和选项

使用方法:
    python scripts/run_tests.py              # 运行所有测试
    python scripts/run_tests.py --unit       # 仅运行单元测试
    python scripts/run_tests.py --integration # 仅运行集成测试
    python scripts/run_tests.py --screener   # 仅运行筛选器测试
    python scripts/run_tests.py --fast       # 快速测试（跳过慢速测试）
    python scripts/run_tests.py --coverage   # 运行测试并生成覆盖率报告
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime


# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
TESTS_DIR = PROJECT_ROOT / "tests"


def run_command(cmd: list, description: str = "") -> int:
    """运行命令并返回退出码"""
    if description:
        print(f"\n{'='*60}")
        print(f"🔄 {description}")
        print(f"{'='*60}")
        print(f"命令: {' '.join(cmd)}\n")
    
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    return result.returncode


def run_all_tests(verbose: bool = True) -> int:
    """运行所有测试"""
    cmd = ["python", "-m", "pytest", "tests/", "-v" if verbose else ""]
    cmd = [c for c in cmd if c]  # 移除空字符串
    return run_command(cmd, "运行所有测试")


def run_unit_tests(verbose: bool = True) -> int:
    """运行单元测试"""
    cmd = [
        "python", "-m", "pytest", "tests/",
        "-v" if verbose else "",
        "-m", "not slow and not integration",
        "--tb=short"
    ]
    cmd = [c for c in cmd if c]
    return run_command(cmd, "运行单元测试")


def run_integration_tests(verbose: bool = True) -> int:
    """运行集成测试"""
    cmd = [
        "python", "-m", "pytest", "tests/",
        "-v" if verbose else "",
        "-m", "integration",
        "--tb=short"
    ]
    cmd = [c for c in cmd if c]
    return run_command(cmd, "运行集成测试")


def run_screener_tests(verbose: bool = True) -> int:
    """运行筛选器相关测试"""
    test_files = [
        "tests/test_stock_screener_framework.py",
        "tests/test_stock_screener_advanced.py",
        "tests/test_hard_filter.py",
        "tests/test_market_filter.py",
    ]
    
    # 只运行存在的测试文件
    existing_files = [f for f in test_files if (PROJECT_ROOT / f).exists()]
    
    if not existing_files:
        print("⚠️ 未找到筛选器测试文件")
        return 1
    
    cmd = ["python", "-m", "pytest"] + existing_files + [
        "-v" if verbose else "",
        "--tb=short"
    ]
    cmd = [c for c in cmd if c]
    return run_command(cmd, "运行筛选器测试")


def run_fast_tests(verbose: bool = True) -> int:
    """运行快速测试（跳过慢速测试）"""
    cmd = [
        "python", "-m", "pytest", "tests/",
        "-v" if verbose else "",
        "-m", "not slow",
        "--tb=short",
        "-x"  # 遇到第一个失败就停止
    ]
    cmd = [c for c in cmd if c]
    return run_command(cmd, "运行快速测试")


def run_coverage_tests(verbose: bool = True) -> int:
    """运行测试并生成覆盖率报告"""
    # 检查是否安装了 pytest-cov
    try:
        import pytest_cov
    except ImportError:
        print("⚠️ 需要安装 pytest-cov: pip install pytest-cov")
        return 1
    
    cmd = [
        "python", "-m", "pytest", "tests/",
        "-v" if verbose else "",
        "--cov=core",
        "--cov-report=html",
        "--cov-report=term-missing",
        "--tb=short"
    ]
    cmd = [c for c in cmd if c]
    return run_command(cmd, "运行测试并生成覆盖率报告")


def run_specific_tests(test_pattern: str, verbose: bool = True) -> int:
    """运行特定测试"""
    cmd = [
        "python", "-m", "pytest",
        "-v" if verbose else "",
        "-k", test_pattern,
        "--tb=short"
    ]
    cmd = [c for c in cmd if c]
    return run_command(cmd, f"运行匹配 '{test_pattern}' 的测试")


def run_ci_tests() -> int:
    """运行 CI 测试（模拟 GitHub Actions）"""
    print("\n" + "="*60)
    print("🚀 模拟 CI 测试流程")
    print("="*60)
    
    results = []
    
    # 1. 单元测试
    print("\n📋 步骤 1/3: 单元测试")
    result = run_unit_tests()
    results.append(("单元测试", result))
    
    # 2. 筛选器测试
    print("\n📋 步骤 2/3: 筛选器测试")
    result = run_screener_tests()
    results.append(("筛选器测试", result))
    
    # 3. 集成测试
    print("\n📋 步骤 3/3: 集成测试")
    result = run_integration_tests()
    results.append(("集成测试", result))
    
    # 汇总结果
    print("\n" + "="*60)
    print("📊 CI 测试结果汇总")
    print("="*60)
    
    all_passed = True
    for name, code in results:
        status = "✅ 通过" if code == 0 else "❌ 失败"
        print(f"  {name}: {status}")
        if code != 0:
            all_passed = False
    
    print("="*60)
    if all_passed:
        print("🎉 所有 CI 测试通过!")
        return 0
    else:
        print("⚠️ 部分测试失败，请检查上述输出")
        return 1


def list_tests() -> int:
    """列出所有可用测试"""
    cmd = ["python", "-m", "pytest", "tests/", "--collect-only", "-q"]
    return run_command(cmd, "列出所有测试")


def main():
    parser = argparse.ArgumentParser(
        description="MiniQuant-Lite 测试运行器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/run_tests.py              # 运行所有测试
  python scripts/run_tests.py --unit       # 仅运行单元测试
  python scripts/run_tests.py --fast       # 快速测试
  python scripts/run_tests.py -k "screener" # 运行包含 'screener' 的测试
  python scripts/run_tests.py --ci         # 模拟 CI 流程
        """
    )
    
    # 测试类型选项
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--all", action="store_true", help="运行所有测试（默认）")
    group.add_argument("--unit", action="store_true", help="仅运行单元测试")
    group.add_argument("--integration", action="store_true", help="仅运行集成测试")
    group.add_argument("--screener", action="store_true", help="仅运行筛选器测试")
    group.add_argument("--fast", action="store_true", help="快速测试（跳过慢速测试）")
    group.add_argument("--coverage", action="store_true", help="运行测试并生成覆盖率报告")
    group.add_argument("--ci", action="store_true", help="模拟 CI 测试流程")
    group.add_argument("--list", action="store_true", help="列出所有测试")
    
    # 其他选项
    parser.add_argument("-k", "--keyword", type=str, help="运行匹配关键词的测试")
    parser.add_argument("-q", "--quiet", action="store_true", help="安静模式（减少输出）")
    
    args = parser.parse_args()
    verbose = not args.quiet
    
    # 打印标题
    print("\n" + "="*60)
    print("🧪 MiniQuant-Lite 测试运行器")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # 根据参数运行相应测试
    if args.keyword:
        exit_code = run_specific_tests(args.keyword, verbose)
    elif args.unit:
        exit_code = run_unit_tests(verbose)
    elif args.integration:
        exit_code = run_integration_tests(verbose)
    elif args.screener:
        exit_code = run_screener_tests(verbose)
    elif args.fast:
        exit_code = run_fast_tests(verbose)
    elif args.coverage:
        exit_code = run_coverage_tests(verbose)
    elif args.ci:
        exit_code = run_ci_tests()
    elif args.list:
        exit_code = list_tests()
    else:
        exit_code = run_all_tests(verbose)
    
    # 打印最终结果
    print("\n" + "="*60)
    if exit_code == 0:
        print("✅ 测试完成 - 全部通过")
    else:
        print(f"❌ 测试完成 - 退出码: {exit_code}")
    print("="*60 + "\n")
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
