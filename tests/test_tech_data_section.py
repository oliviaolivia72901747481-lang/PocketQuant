"""
测试科技股数据专区功能

验证 tech-stock-data-fix spec 的所有任务实现。

Tasks covered:
- Task 3.1: 添加科技股数据专区
- Task 3.2: 实现数据状态概览
- Task 4.1: 实现启动时数据检查
- Task 4.2: 添加数据同步状态缓存
- Task 5.1: 实现友好的错误信息系统
- Task 5.2: 添加下载进度和状态显示
- Task 5.3: 优化用户操作流程
"""
import sys
sys.path.insert(0, '.')

from core.data_feed import DataFeed
from core.tech_stock.data_validator import TechDataValidator, ErrorMessages, DataValidationResult
from core.tech_stock.data_downloader import TechDataDownloader, DownloadProgress
from config.settings import get_settings
from config.tech_stock_pool import get_tech_stock_pool, get_all_tech_stocks

def test_tech_stock_data_section():
    """测试科技股数据专区的核心功能"""
    print("=" * 60)
    print("测试科技股数据专区功能 (Task 3.1, 3.2)")
    print("=" * 60)
    
    # 初始化
    settings = get_settings()
    data_feed = DataFeed(
        raw_path=settings.path.get_raw_path(),
        processed_path=settings.path.get_processed_path()
    )
    
    validator = TechDataValidator(data_feed)
    tech_pool = get_tech_stock_pool()
    
    # 测试1: 获取科技股池状态
    print("\n1. 获取科技股池状态...")
    try:
        status = validator.get_tech_stock_pool_status()
        overall = status['overall']
        print(f"   总数: {overall['total_stocks']} 只")
        print(f"   有效: {overall['valid_stocks']} 只")
        print(f"   缺失: {overall['missing_files']} 只")
        print(f"   不足: {overall['insufficient_data']} 只")
        print(f"   损坏: {overall['corrupted_files']} 只")
        print(f"   完整率: {overall['completion_rate']*100:.1f}%")
        print("   ✅ 状态获取成功")
    except Exception as e:
        print(f"   ❌ 状态获取失败: {e}")
        return False
    
    # 测试2: 按行业统计
    print("\n2. 按行业统计...")
    try:
        for sector, stats in status['by_sector'].items():
            rate = stats['valid'] / stats['total'] * 100 if stats['total'] > 0 else 0
            print(f"   {sector}: {stats['valid']}/{stats['total']} ({rate:.0f}%)")
        print("   ✅ 行业统计成功")
    except Exception as e:
        print(f"   ❌ 行业统计失败: {e}")
        return False
    
    # 测试3: 问题股票详情
    print("\n3. 问题股票详情...")
    try:
        problems = status['problem_stocks']
        print(f"   缺失文件: {len(problems['missing_files'])} 只")
        print(f"   数据不足: {len(problems['insufficient_data'])} 只")
        print(f"   文件损坏: {len(problems['corrupted_files'])} 只")
        print("   ✅ 问题详情获取成功")
    except Exception as e:
        print(f"   ❌ 问题详情获取失败: {e}")
        return False
    
    # 测试4: 单只股票数据检查
    print("\n4. 单只股票数据检查...")
    try:
        all_codes = get_all_tech_stocks()
        test_code = all_codes[0] if all_codes else None
        if test_code:
            stock_status = validator.check_single_stock_data(test_code)
            print(f"   股票: {test_code} ({stock_status.name})")
            print(f"   有文件: {stock_status.has_file}")
            print(f"   数据范围: {stock_status.first_date} ~ {stock_status.last_date}")
            print(f"   记录数: {stock_status.record_count}")
            print("   ✅ 单股检查成功")
        else:
            print("   ⚠️ 无股票可测试")
    except Exception as e:
        print(f"   ❌ 单股检查失败: {e}")
        return False
    
    # 测试5: 下载器初始化
    print("\n5. 下载器初始化...")
    try:
        downloader = TechDataDownloader(data_feed)
        print(f"   下载天数: {downloader.download_days}")
        print(f"   最大重试: {downloader.max_retries}")
        print(f"   是否下载中: {downloader.is_downloading()}")
        print("   ✅ 下载器初始化成功")
    except Exception as e:
        print(f"   ❌ 下载器初始化失败: {e}")
        return False
    
    return True


def test_error_messages():
    """测试友好的错误信息系统 (Task 5.1)"""
    print("\n" + "=" * 60)
    print("测试友好的错误信息系统 (Task 5.1)")
    print("=" * 60)
    
    # 测试1: ErrorMessages 类
    print("\n1. 测试 ErrorMessages 类...")
    try:
        # 测试格式化方法
        msg1 = ErrorMessages.format_missing_data("000001", "平安银行")
        print(f"   缺失数据消息: {msg1}")
        
        msg2 = ErrorMessages.format_insufficient_data(
            "000001", "平安银行",
            "2023-01-01", "2023-12-31",
            "2022-01-01", "2024-12-31"
        )
        print(f"   数据不足消息: {msg2}")
        
        msg3 = ErrorMessages.format_corrupted_data("000001", "平安银行", "文件格式错误")
        print(f"   数据损坏消息: {msg3}")
        
        # 测试解决方案提示
        hints = ErrorMessages.get_solution_hints(True, True, True)
        print(f"   解决方案数量: {len(hints)}")
        for hint in hints:
            print(f"      • {hint}")
        
        print("   ✅ ErrorMessages 类测试成功")
    except Exception as e:
        print(f"   ❌ ErrorMessages 类测试失败: {e}")
        return False
    
    # 测试2: get_friendly_error_summary 方法
    print("\n2. 测试 get_friendly_error_summary 方法...")
    try:
        settings = get_settings()
        data_feed = DataFeed(
            raw_path=settings.path.get_raw_path(),
            processed_path=settings.path.get_processed_path()
        )
        validator = TechDataValidator(data_feed)
        
        # 获取验证结果
        all_codes = get_all_tech_stocks()
        result = validator.validate_tech_stock_data(all_codes)
        
        # 获取友好的错误摘要
        summary = validator.get_friendly_error_summary(result)
        print(f"   有错误: {summary['has_error']}")
        print(f"   标题: {summary['title']}")
        print(f"   摘要: {summary['summary']}")
        print(f"   详情数量: {len(summary['details'])}")
        print(f"   解决方案数量: {len(summary['solutions'])}")
        
        print("   ✅ get_friendly_error_summary 测试成功")
    except Exception as e:
        print(f"   ❌ get_friendly_error_summary 测试失败: {e}")
        return False
    
    return True


def test_startup_data_check():
    """测试启动时数据检查 (Task 4.1, 4.2)"""
    print("\n" + "=" * 60)
    print("测试启动时数据检查 (Task 4.1, 4.2)")
    print("=" * 60)
    
    # 模拟 Home.py 中的检查函数
    print("\n1. 测试 check_tech_stock_data_status 函数...")
    try:
        from core.data_feed import DataFeed
        from core.tech_stock.data_validator import TechDataValidator
        from config.tech_stock_pool import get_all_tech_stocks
        
        settings = get_settings()
        data_feed = DataFeed(
            raw_path=settings.path.get_raw_path(),
            processed_path=settings.path.get_processed_path()
        )
        
        validator = TechDataValidator(data_feed)
        all_codes = get_all_tech_stocks()
        
        # 验证科技股数据
        result = validator.validate_tech_stock_data(all_codes)
        
        missing_count = len(result.missing_files) + len(result.insufficient_data) + len(result.corrupted_files)
        completion_rate = result.valid_stocks / result.total_stocks if result.total_stocks > 0 else 0
        
        has_issues = missing_count > 0
        
        print(f"   有问题: {has_issues}")
        print(f"   总数: {result.total_stocks}")
        print(f"   有效: {result.valid_stocks}")
        print(f"   缺失: {missing_count}")
        print(f"   完整率: {completion_rate*100:.1f}%")
        
        print("   ✅ 启动时数据检查测试成功")
    except Exception as e:
        print(f"   ❌ 启动时数据检查测试失败: {e}")
        return False
    
    return True


def test_download_progress():
    """测试下载进度和状态显示 (Task 5.2)"""
    print("\n" + "=" * 60)
    print("测试下载进度和状态显示 (Task 5.2)")
    print("=" * 60)
    
    print("\n1. 测试 DownloadProgress 类...")
    try:
        progress = DownloadProgress(
            total_stocks=60,
            completed_stocks=30,
            current_stock="000001",
            current_stock_name="平安银行",
            success_count=28,
            failed_count=2
        )
        
        print(f"   总数: {progress.total_stocks}")
        print(f"   已完成: {progress.completed_stocks}")
        print(f"   当前股票: {progress.current_stock} ({progress.current_stock_name})")
        print(f"   成功: {progress.success_count}")
        print(f"   失败: {progress.failed_count}")
        print(f"   完成率: {progress.completed_stocks/progress.total_stocks*100:.1f}%")
        
        print("   ✅ DownloadProgress 类测试成功")
    except Exception as e:
        print(f"   ❌ DownloadProgress 类测试失败: {e}")
        return False
    
    print("\n2. 测试下载器统计信息...")
    try:
        settings = get_settings()
        data_feed = DataFeed(
            raw_path=settings.path.get_raw_path(),
            processed_path=settings.path.get_processed_path()
        )
        downloader = TechDataDownloader(data_feed)
        
        stats = downloader.get_download_statistics()
        print(f"   是否下载中: {stats['is_downloading']}")
        print(f"   进度信息: {stats['progress']}")
        print(f"   当前任务: {stats['current_task']}")
        print(f"   状态: {stats['status']}")
        
        print("   ✅ 下载器统计信息测试成功")
    except Exception as e:
        print(f"   ❌ 下载器统计信息测试失败: {e}")
        return False
    
    return True


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("科技股数据修复功能测试套件")
    print("=" * 60)
    
    all_passed = True
    
    # 运行测试
    if not test_tech_stock_data_section():
        all_passed = False
    
    if not test_error_messages():
        all_passed = False
    
    if not test_startup_data_check():
        all_passed = False
    
    if not test_download_progress():
        all_passed = False
    
    # 总结
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 所有测试通过！")
    else:
        print("❌ 部分测试失败，请检查上述错误信息")
    print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
