#!/usr/bin/env python
"""
数据准确率验证工具

验证股票数据准确率是否达到99%以上的目标

Requirements: 7.2, 7.4, 7.5
成功标准: 数据准确率 ≥ 99%

使用方法:
    python tools/validate_data_accuracy.py
"""

import sys
import os
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.stock_screener.data_accuracy_validator import (
    DataAccuracyValidator,
    get_accuracy_validator,
)
from core.stock_screener import get_data_source_manager


def validate_market_data_accuracy():
    """验证市场数据准确率"""
    print("=" * 60)
    print("数据准确率验证工具")
    print("=" * 60)
    print(f"验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"目标准确率: ≥ 99%")
    print()
    
    # 获取数据源管理器
    print("正在获取市场数据...")
    manager = get_data_source_manager()
    result = manager.get_mainboard_stocks()
    
    if not result.success:
        print(f"❌ 获取市场数据失败: {result.error_message}")
        return False
    
    if result.data is None or result.data.empty:
        print("❌ 市场数据为空")
        return False
    
    print(f"✓ 成功获取 {len(result.data)} 只股票数据")
    print()
    
    # 验证数据准确率
    print("正在验证数据准确率...")
    validator = get_accuracy_validator()
    report = validator.validate_accuracy(result.data)
    
    # 打印验证结果
    print()
    print("-" * 60)
    print("验证结果")
    print("-" * 60)
    print(f"总记录数: {report.total_records}")
    print(f"检查字段数: {report.total_fields_checked}")
    print()
    print(f"总体准确率: {report.overall_accuracy:.2f}%")
    print(f"准确率等级: {report.accuracy_level.value}")
    print(f"是否达标: {'✓ 是' if report.meets_target else '✗ 否'}")
    print()
    
    # 打印各字段准确率
    print("字段准确率详情:")
    for field_result in report.field_results:
        status = "✓" if field_result.is_accurate else "✗"
        print(f"  {status} {field_result.field_name}: {field_result.accuracy_rate:.2f}% "
              f"({field_result.accurate_records}/{field_result.total_records})")
    
    # 打印问题汇总
    if report.issues_summary:
        print()
        print("问题汇总:")
        for issue_type, count in report.issues_summary.items():
            print(f"  - {issue_type}: {count}")
    
    # 打印建议
    if report.recommendations:
        print()
        print("改进建议:")
        for rec in report.recommendations:
            print(f"  - {rec}")
    
    print()
    print("-" * 60)
    
    # 返回是否达标
    if report.meets_target:
        print("✓ 数据准确率验证通过！")
        return True
    else:
        print(f"✗ 数据准确率({report.overall_accuracy:.2f}%)未达到99%目标")
        return False


def validate_tech_stock_pool_accuracy():
    """验证科技股池数据准确率"""
    print()
    print("=" * 60)
    print("科技股池数据准确率验证")
    print("=" * 60)
    
    try:
        from config.tech_stock_pool import get_tech_stock_pool
        import pandas as pd
        
        pool = get_tech_stock_pool()
        all_stocks = pool.get_all_stocks()
        
        if not all_stocks:
            print("科技股池为空")
            return True
        
        # 构建股票池数据
        pool_data = pd.DataFrame([
            {
                'code': stock.code,
                'name': stock.name,
                'industry': stock.sector,
            }
            for stock in all_stocks
        ])
        
        print(f"科技股池股票数量: {len(pool_data)}")
        
        # 验证数据准确率
        validator = get_accuracy_validator()
        report = validator.validate_accuracy(pool_data)
        
        print(f"代码格式准确率: ", end="")
        code_result = next(
            (r for r in report.field_results if r.field_name == 'code'),
            None
        )
        if code_result:
            status = "✓" if code_result.accuracy_rate == 100 else "✗"
            print(f"{status} {code_result.accuracy_rate:.2f}%")
        
        print(f"名称完整性: ", end="")
        name_result = next(
            (r for r in report.field_results if r.field_name == 'name'),
            None
        )
        if name_result:
            status = "✓" if name_result.accuracy_rate == 100 else "✗"
            print(f"{status} {name_result.accuracy_rate:.2f}%")
        
        return code_result and code_result.accuracy_rate == 100
        
    except ImportError as e:
        print(f"无法导入科技股池配置: {e}")
        return True


def main():
    """主函数"""
    try:
        # 验证市场数据准确率
        market_passed = validate_market_data_accuracy()
        
        # 验证科技股池数据准确率
        pool_passed = validate_tech_stock_pool_accuracy()
        
        print()
        print("=" * 60)
        print("验证总结")
        print("=" * 60)
        print(f"市场数据准确率: {'✓ 通过' if market_passed else '✗ 未通过'}")
        print(f"科技股池数据: {'✓ 通过' if pool_passed else '✗ 未通过'}")
        
        if market_passed and pool_passed:
            print()
            print("✓ 所有数据准确率验证通过！")
            return 0
        else:
            print()
            print("✗ 部分验证未通过，请检查数据质量")
            return 1
            
    except Exception as e:
        print(f"验证过程出错: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
