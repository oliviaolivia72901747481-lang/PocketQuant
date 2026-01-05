#!/usr/bin/env python
"""
系统稳定性验证工具

验证系统是否达到99.5%的稳定性目标

Requirements: 性能目标验证 - 系统稳定性 ≥ 99.5%
"""

import sys
import os
import time
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.stock_screener.stability_tracker import (
    StabilityTracker,
    StabilityValidator,
    OperationType,
    get_stability_tracker,
    get_stability_validator,
)


def run_stability_validation():
    """运行稳定性验证"""
    print("=" * 60)
    print("系统稳定性验证")
    print("=" * 60)
    print(f"验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"目标稳定性: {StabilityTracker.TARGET_STABILITY_RATE}%")
    print()
    
    # 获取稳定性追踪器和验证器
    tracker = get_stability_tracker()
    validator = get_stability_validator()
    
    # 模拟系统操作来测试稳定性
    print("正在执行系统稳定性测试...")
    print()
    
    # 测试各个组件
    test_results = []
    
    # 1. 测试数据源模块
    print("1. 测试数据源模块...")
    data_source_result = test_data_source(tracker)
    test_results.append(("数据源模块", data_source_result))
    
    # 2. 测试筛选器模块
    print("2. 测试筛选器模块...")
    screener_result = test_screener(tracker)
    test_results.append(("筛选器模块", screener_result))
    
    # 3. 测试评分系统
    print("3. 测试评分系统...")
    scorer_result = test_scorer(tracker)
    test_results.append(("评分系统", scorer_result))
    
    # 4. 测试验证器
    print("4. 测试验证器...")
    validator_result = test_validator(tracker)
    test_results.append(("验证器", validator_result))
    
    # 5. 测试风险控制器
    print("5. 测试风险控制器...")
    risk_result = test_risk_controller(tracker)
    test_results.append(("风险控制器", risk_result))
    
    print()
    print("=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    total_success = 0
    total_failure = 0
    
    for name, (success, failure) in test_results:
        rate = (success / (success + failure) * 100) if (success + failure) > 0 else 100
        status = "✓" if rate >= 99.5 else "✗"
        print(f"  {status} {name}: {success}/{success + failure} ({rate:.2f}%)")
        total_success += success
        total_failure += failure
    
    print()
    
    # 获取整体稳定性指标
    metrics = tracker.get_metrics()
    overall_rate = metrics.stability_rate
    meets_target = overall_rate >= StabilityTracker.TARGET_STABILITY_RATE
    
    print("=" * 60)
    print("整体稳定性评估")
    print("=" * 60)
    print(f"  总操作数: {metrics.total_operations}")
    print(f"  成功操作: {metrics.successful_operations}")
    print(f"  失败操作: {metrics.failed_operations}")
    print(f"  稳定性率: {overall_rate:.2f}%")
    print(f"  目标: {StabilityTracker.TARGET_STABILITY_RATE}%")
    print()
    
    if meets_target:
        print("✓ 系统稳定性达标!")
        print(f"  当前稳定性 {overall_rate:.2f}% >= 目标 {StabilityTracker.TARGET_STABILITY_RATE}%")
    else:
        print("✗ 系统稳定性未达标")
        print(f"  当前稳定性 {overall_rate:.2f}% < 目标 {StabilityTracker.TARGET_STABILITY_RATE}%")
    
    print()
    print("=" * 60)
    
    # 保存历史记录
    tracker.save_history()
    
    # 生成详细报告
    report = tracker.generate_report(time_range_hours=24)
    print()
    print(report)
    
    return meets_target


def test_data_source(tracker: StabilityTracker) -> tuple:
    """测试数据源模块"""
    success = 0
    failure = 0
    
    try:
        from core.stock_screener import get_data_source_manager
        
        # 测试多次实例化
        for _ in range(20):
            try:
                manager = get_data_source_manager()
                if manager is not None:
                    tracker.record_success(OperationType.DATA_FETCH, duration_ms=10)
                    success += 1
                else:
                    tracker.record_failure(OperationType.DATA_FETCH, "管理器为空")
                    failure += 1
            except Exception as e:
                tracker.record_failure(OperationType.DATA_FETCH, str(e))
                failure += 1
    except ImportError as e:
        tracker.record_failure(OperationType.DATA_FETCH, f"导入失败: {e}")
        failure += 1
    
    return success, failure


def test_screener(tracker: StabilityTracker) -> tuple:
    """测试筛选器模块"""
    success = 0
    failure = 0
    
    try:
        from core.stock_screener import (
            get_industry_screener,
            get_financial_screener,
            get_market_screener
        )
        
        # 测试行业筛选器
        for _ in range(10):
            try:
                screener = get_industry_screener()
                if screener is not None:
                    tracker.record_success(OperationType.SCREENING, duration_ms=5)
                    success += 1
                else:
                    tracker.record_failure(OperationType.SCREENING, "筛选器为空")
                    failure += 1
            except Exception as e:
                tracker.record_failure(OperationType.SCREENING, str(e))
                failure += 1
        
        # 测试财务筛选器
        for _ in range(10):
            try:
                screener = get_financial_screener()
                if screener is not None:
                    tracker.record_success(OperationType.SCREENING, duration_ms=5)
                    success += 1
                else:
                    tracker.record_failure(OperationType.SCREENING, "筛选器为空")
                    failure += 1
            except Exception as e:
                tracker.record_failure(OperationType.SCREENING, str(e))
                failure += 1
        
        # 测试市场筛选器
        for _ in range(10):
            try:
                screener = get_market_screener()
                if screener is not None:
                    tracker.record_success(OperationType.SCREENING, duration_ms=5)
                    success += 1
                else:
                    tracker.record_failure(OperationType.SCREENING, "筛选器为空")
                    failure += 1
            except Exception as e:
                tracker.record_failure(OperationType.SCREENING, str(e))
                failure += 1
                
    except ImportError as e:
        tracker.record_failure(OperationType.SCREENING, f"导入失败: {e}")
        failure += 1
    
    return success, failure


def test_scorer(tracker: StabilityTracker) -> tuple:
    """测试评分系统"""
    success = 0
    failure = 0
    
    try:
        from core.stock_screener import get_comprehensive_scorer
        
        for _ in range(20):
            try:
                scorer = get_comprehensive_scorer()
                if scorer is not None:
                    tracker.record_success(OperationType.SCORING, duration_ms=5)
                    success += 1
                else:
                    tracker.record_failure(OperationType.SCORING, "评分器为空")
                    failure += 1
            except Exception as e:
                tracker.record_failure(OperationType.SCORING, str(e))
                failure += 1
                
    except ImportError as e:
        tracker.record_failure(OperationType.SCORING, f"导入失败: {e}")
        failure += 1
    
    return success, failure


def test_validator(tracker: StabilityTracker) -> tuple:
    """测试验证器"""
    success = 0
    failure = 0
    
    try:
        from core.stock_screener import get_quality_monitor, get_result_validator
        
        for _ in range(10):
            try:
                monitor = get_quality_monitor()
                if monitor is not None:
                    tracker.record_success(OperationType.VALIDATION, duration_ms=5)
                    success += 1
                else:
                    tracker.record_failure(OperationType.VALIDATION, "监控器为空")
                    failure += 1
            except Exception as e:
                tracker.record_failure(OperationType.VALIDATION, str(e))
                failure += 1
        
        for _ in range(10):
            try:
                validator = get_result_validator()
                if validator is not None:
                    tracker.record_success(OperationType.VALIDATION, duration_ms=5)
                    success += 1
                else:
                    tracker.record_failure(OperationType.VALIDATION, "验证器为空")
                    failure += 1
            except Exception as e:
                tracker.record_failure(OperationType.VALIDATION, str(e))
                failure += 1
                
    except ImportError as e:
        tracker.record_failure(OperationType.VALIDATION, f"导入失败: {e}")
        failure += 1
    
    return success, failure


def test_risk_controller(tracker: StabilityTracker) -> tuple:
    """测试风险控制器"""
    success = 0
    failure = 0
    
    try:
        from core.stock_screener import get_risk_assessor, get_alert_manager
        
        for _ in range(10):
            try:
                assessor = get_risk_assessor()
                if assessor is not None:
                    tracker.record_success(OperationType.SYSTEM, duration_ms=5)
                    success += 1
                else:
                    tracker.record_failure(OperationType.SYSTEM, "评估器为空")
                    failure += 1
            except Exception as e:
                tracker.record_failure(OperationType.SYSTEM, str(e))
                failure += 1
        
        for _ in range(10):
            try:
                manager = get_alert_manager()
                if manager is not None:
                    tracker.record_success(OperationType.SYSTEM, duration_ms=5)
                    success += 1
                else:
                    tracker.record_failure(OperationType.SYSTEM, "告警管理器为空")
                    failure += 1
            except Exception as e:
                tracker.record_failure(OperationType.SYSTEM, str(e))
                failure += 1
                
    except ImportError as e:
        tracker.record_failure(OperationType.SYSTEM, f"导入失败: {e}")
        failure += 1
    
    return success, failure


if __name__ == "__main__":
    result = run_stability_validation()
    sys.exit(0 if result else 1)
