#!/usr/bin/env python3
"""
筛选流程性能基准测试工具

验证完整筛选流程耗时 ≤ 30分钟的性能目标

使用方法:
    python tools/benchmark_screening_performance.py [--mock] [--target-minutes N]

参数:
    --mock: 使用模拟数据进行快速测试
    --target-minutes N: 设置目标耗时（分钟），默认30

Requirements: 技术约束 - 筛选过程应在合理时间内完成
"""

import sys
import os
import argparse
import time
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.test_screening_performance import (
    ScreeningPerformanceTester,
    ScreeningPerformanceReport
)


def print_banner():
    """打印横幅"""
    print("=" * 70)
    print("  科技股池筛选性能基准测试")
    print("  Tech Stock Pool Screening Performance Benchmark")
    print("=" * 70)


def print_progress(stage: str, elapsed: float, total_target: float):
    """打印进度"""
    progress = min(100, elapsed / total_target * 100)
    bar_length = 40
    filled = int(bar_length * progress / 100)
    bar = "█" * filled + "░" * (bar_length - filled)
    print(f"\r  [{bar}] {progress:.1f}% - {stage}", end="", flush=True)


def run_benchmark(use_mock: bool = False, target_minutes: float = 30.0) -> bool:
    """
    运行性能基准测试
    
    Args:
        use_mock: 是否使用模拟数据
        target_minutes: 目标耗时（分钟）
    
    Returns:
        bool: 测试是否通过
    """
    print_banner()
    print(f"\n📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 目标耗时: ≤ {target_minutes:.1f} 分钟")
    print(f"📊 测试模式: {'模拟数据' if use_mock else '真实数据'}")
    print("-" * 70)
    
    target_seconds = target_minutes * 60
    tester = ScreeningPerformanceTester(target_duration_seconds=target_seconds)
    
    print("\n🚀 开始筛选流程...")
    start_time = time.time()
    
    try:
        report = tester.run_full_screening_test(use_mock=use_mock)
        
        # 打印详细报告
        print("\n" + report.generate_report())
        
        # 保存报告到文件
        report_path = "tests/SCREENING_PERFORMANCE_REPORT.md"
        save_report(report, report_path)
        print(f"\n📄 报告已保存至: {report_path}")
        
        # 打印最终结果
        print("\n" + "=" * 70)
        if report.passed:
            print("✅ 性能测试通过!")
            print(f"   实际耗时: {report.total_duration_minutes:.2f} 分钟")
            print(f"   目标耗时: {target_minutes:.1f} 分钟")
            margin = target_minutes - report.total_duration_minutes
            print(f"   余量: {margin:.2f} 分钟 ({margin/target_minutes*100:.1f}%)")
        else:
            print("❌ 性能测试未通过!")
            print(f"   实际耗时: {report.total_duration_minutes:.2f} 分钟")
            print(f"   目标耗时: {target_minutes:.1f} 分钟")
            excess = report.total_duration_minutes - target_minutes
            print(f"   超出: {excess:.2f} 分钟")
        print("=" * 70)
        
        return report.passed
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n\n❌ 测试失败: {e}")
        print(f"   已耗时: {elapsed/60:.2f} 分钟")
        return False


def save_report(report: ScreeningPerformanceReport, path: str):
    """保存报告到文件"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write("# 筛选流程性能测试报告\n\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("## 测试结果\n\n")
        f.write(f"- **状态**: {'✅ 通过' if report.passed else '❌ 未通过'}\n")
        f.write(f"- **目标耗时**: ≤ {report.target_duration_minutes:.1f} 分钟\n")
        f.write(f"- **实际耗时**: {report.total_duration_minutes:.2f} 分钟\n\n")
        
        f.write("## 各阶段耗时\n\n")
        f.write("| 阶段 | 耗时(秒) | 记录数 | 状态 |\n")
        f.write("|------|----------|--------|------|\n")
        for result in report.stage_results:
            status = "✅" if result.passed else "❌"
            f.write(f"| {result.stage} | {result.duration_seconds:.2f} | {result.records_processed} | {status} |\n")
        
        f.write("\n## 详细报告\n\n")
        f.write("```\n")
        f.write(report.generate_report())
        f.write("\n```\n")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="科技股池筛选性能基准测试",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 运行真实数据测试（默认30分钟目标）
    python tools/benchmark_screening_performance.py
    
    # 运行模拟数据快速测试
    python tools/benchmark_screening_performance.py --mock
    
    # 设置自定义目标耗时
    python tools/benchmark_screening_performance.py --target-minutes 20
        """
    )
    
    parser.add_argument(
        '--mock',
        action='store_true',
        help='使用模拟数据进行快速测试'
    )
    
    parser.add_argument(
        '--target-minutes',
        type=float,
        default=30.0,
        help='目标耗时（分钟），默认30'
    )
    
    args = parser.parse_args()
    
    success = run_benchmark(
        use_mock=args.mock,
        target_minutes=args.target_minutes
    )
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
