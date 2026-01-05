"""
筛选流程性能测试

验证完整筛选流程耗时 ≤ 30分钟的性能目标

Requirements: 技术约束 - 筛选过程应在合理时间内完成
"""

import pytest
import time
import sys
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@dataclass
class PerformanceResult:
    """性能测试结果"""
    stage: str
    duration_seconds: float
    records_processed: int = 0
    passed: bool = True
    error: Optional[str] = None


@dataclass
class ScreeningPerformanceReport:
    """筛选性能报告"""
    total_duration_seconds: float
    stage_results: List[PerformanceResult] = field(default_factory=list)
    target_duration_seconds: float = 1800.0  # 30分钟
    passed: bool = True
    
    @property
    def total_duration_minutes(self) -> float:
        return self.total_duration_seconds / 60.0
    
    @property
    def target_duration_minutes(self) -> float:
        return self.target_duration_seconds / 60.0
    
    def add_stage(self, result: PerformanceResult):
        self.stage_results.append(result)
    
    def generate_report(self) -> str:
        """生成性能报告"""
        lines = [
            "=" * 70,
            "筛选流程性能测试报告",
            "=" * 70,
            f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"目标耗时: ≤ {self.target_duration_minutes:.1f} 分钟",
            f"实际耗时: {self.total_duration_minutes:.2f} 分钟 ({self.total_duration_seconds:.2f} 秒)",
            f"测试结果: {'✅ 通过' if self.passed else '❌ 未通过'}",
            "",
            "-" * 70,
            "各阶段耗时详情:",
            "-" * 70,
        ]
        
        for result in self.stage_results:
            status = "✅" if result.passed else "❌"
            lines.append(
                f"  {status} {result.stage}: {result.duration_seconds:.2f}秒 "
                f"({result.records_processed}条记录)"
            )
            if result.error:
                lines.append(f"      错误: {result.error}")
        
        lines.append("-" * 70)
        
        # 性能分析
        if self.stage_results:
            slowest = max(self.stage_results, key=lambda x: x.duration_seconds)
            lines.append(f"最慢阶段: {slowest.stage} ({slowest.duration_seconds:.2f}秒)")
        
        # 性能建议
        lines.append("")
        lines.append("性能优化建议:")
        if self.total_duration_seconds > self.target_duration_seconds:
            lines.append("  ⚠️ 总耗时超过目标，建议优化以下方面:")
            for result in sorted(self.stage_results, key=lambda x: x.duration_seconds, reverse=True)[:3]:
                if result.duration_seconds > 60:
                    lines.append(f"    - {result.stage}: 考虑使用缓存或并行处理")
        else:
            margin = self.target_duration_seconds - self.total_duration_seconds
            lines.append(f"  ✅ 性能良好，距离目标还有 {margin/60:.1f} 分钟余量")
        
        lines.append("=" * 70)
        return "\n".join(lines)


class ScreeningPerformanceTester:
    """筛选性能测试器"""
    
    def __init__(self, target_duration_seconds: float = 1800.0):
        """
        初始化性能测试器
        
        Args:
            target_duration_seconds: 目标耗时（秒），默认30分钟
        """
        self.target_duration = target_duration_seconds
        self.report = ScreeningPerformanceReport(
            total_duration_seconds=0,
            target_duration_seconds=target_duration_seconds
        )
    
    def _time_stage(self, stage_name: str, func, *args, **kwargs) -> Any:
        """计时执行阶段"""
        start = time.time()
        result = None
        error = None
        records = 0
        
        try:
            result = func(*args, **kwargs)
            if hasattr(result, '__len__'):
                records = len(result)
            elif isinstance(result, tuple) and len(result) > 0:
                if hasattr(result[0], '__len__'):
                    records = len(result[0])
        except Exception as e:
            error = str(e)
        
        duration = time.time() - start
        
        self.report.add_stage(PerformanceResult(
            stage=stage_name,
            duration_seconds=duration,
            records_processed=records,
            passed=error is None,
            error=error
        ))
        
        return result
    
    def run_full_screening_test(self, use_mock: bool = False) -> ScreeningPerformanceReport:
        """
        运行完整筛选流程性能测试
        
        Args:
            use_mock: 是否使用模拟数据（用于快速测试）
        
        Returns:
            ScreeningPerformanceReport: 性能报告
        """
        start_time = time.time()
        
        try:
            if use_mock:
                self._run_mock_screening()
            else:
                self._run_real_screening()
        except Exception as e:
            self.report.add_stage(PerformanceResult(
                stage="整体流程",
                duration_seconds=time.time() - start_time,
                passed=False,
                error=str(e)
            ))
        
        self.report.total_duration_seconds = time.time() - start_time
        self.report.passed = self.report.total_duration_seconds <= self.target_duration
        
        return self.report
    
    def _run_mock_screening(self):
        """运行模拟筛选（用于快速验证测试框架）"""
        import pandas as pd
        import numpy as np
        
        # 模拟数据获取
        def mock_fetch():
            time.sleep(0.1)  # 模拟网络延迟
            return pd.DataFrame({
                'code': [f'{i:06d}' for i in range(5000)],
                'name': [f'股票{i}' for i in range(5000)],
                'price': np.random.uniform(5, 100, 5000),
                'total_market_cap': np.random.uniform(1e9, 1e12, 5000),
                'float_market_cap': np.random.uniform(5e8, 5e11, 5000),
                'turnover_rate': np.random.uniform(0.1, 10, 5000),
                'pe_ratio': np.random.uniform(5, 100, 5000),
                'pb_ratio': np.random.uniform(0.5, 10, 5000),
            })
        
        # 模拟各阶段
        df = self._time_stage("数据获取", mock_fetch)
        
        def mock_clean(data):
            time.sleep(0.05)
            return data[data['price'] > 0]
        
        df = self._time_stage("数据清洗", mock_clean, df)
        
        def mock_industry_screen(data):
            time.sleep(0.1)
            return data.sample(n=min(1000, len(data)))
        
        df = self._time_stage("行业筛选", mock_industry_screen, df)
        
        def mock_financial_screen(data):
            time.sleep(0.1)
            return data.sample(n=min(500, len(data)))
        
        df = self._time_stage("财务筛选", mock_financial_screen, df)
        
        def mock_market_screen(data):
            time.sleep(0.05)
            return data.sample(n=min(200, len(data)))
        
        df = self._time_stage("市场筛选", mock_market_screen, df)
        
        def mock_scoring(data):
            time.sleep(0.1)
            data['score'] = np.random.uniform(50, 100, len(data))
            return data.nlargest(100, 'score')
        
        df = self._time_stage("综合评分", mock_scoring, df)
        
        return df
    
    def _run_real_screening(self):
        """运行真实筛选流程"""
        from core.stock_screener import (
            get_data_source_manager,
            get_data_cleaner,
            get_industry_screener,
            get_financial_screener,
            get_market_screener,
            get_comprehensive_scorer,
        )
        
        # 阶段1: 数据获取
        data_source = get_data_source_manager()
        result = self._time_stage(
            "数据获取",
            data_source.get_mainboard_stocks
        )
        
        if not result or not result.success:
            raise Exception("数据获取失败")
        
        df = result.data
        
        # 阶段2: 数据清洗
        cleaner = get_data_cleaner()
        
        def clean_data():
            # 使用正确的方法名 clean_stock_data
            cleaned_df, _ = cleaner.clean_stock_data(df)
            cleaned_df = cleaner.remove_st_stocks(cleaned_df)
            cleaned_df = cleaner.filter_mainboard_stocks(cleaned_df)
            return cleaned_df
        
        df = self._time_stage("数据清洗", clean_data)
        
        if df is None or df.empty:
            raise Exception("数据清洗后无有效数据")
        
        # 阶段3: 行业筛选
        industry_screener = get_industry_screener()
        df = self._time_stage(
            "行业筛选",
            lambda: industry_screener.screen_tech_stocks(df)[0]
        )
        
        if df is None or df.empty:
            raise Exception("行业筛选后无科技股")
        
        # 阶段4: 财务筛选
        financial_screener = get_financial_screener()
        df = self._time_stage(
            "财务筛选",
            lambda: financial_screener.screen_stocks(df)[0]
        )
        
        # 阶段5: 市场筛选
        market_screener = get_market_screener()
        df = self._time_stage(
            "市场筛选",
            lambda: market_screener.screen_stocks(df)[0]
        )
        
        # 阶段6: 综合评分
        scorer = get_comprehensive_scorer()
        df = self._time_stage(
            "综合评分",
            lambda: scorer.score_stocks(df, min_score=60, top_n=100)[0]
        )
        
        return df


class TestScreeningPerformance:
    """筛选性能测试类"""
    
    def test_mock_screening_performance(self):
        """测试模拟筛选性能（快速验证测试框架）"""
        tester = ScreeningPerformanceTester(target_duration_seconds=60)  # 1分钟目标
        report = tester.run_full_screening_test(use_mock=True)
        
        print("\n" + report.generate_report())
        
        # 模拟测试应该很快完成
        assert report.total_duration_seconds < 60, "模拟筛选应在1分钟内完成"
        assert report.passed, "模拟筛选性能测试应通过"
    
    def test_screening_stages_exist(self):
        """测试筛选阶段存在性"""
        tester = ScreeningPerformanceTester()
        report = tester.run_full_screening_test(use_mock=True)
        
        stage_names = [r.stage for r in report.stage_results]
        
        expected_stages = ["数据获取", "数据清洗", "行业筛选", "财务筛选", "市场筛选", "综合评分"]
        for stage in expected_stages:
            assert stage in stage_names, f"缺少阶段: {stage}"
    
    def test_performance_report_generation(self):
        """测试性能报告生成"""
        report = ScreeningPerformanceReport(
            total_duration_seconds=600,
            target_duration_seconds=1800
        )
        report.add_stage(PerformanceResult("测试阶段", 100, 1000))
        
        report_text = report.generate_report()
        
        assert "筛选流程性能测试报告" in report_text
        assert "测试阶段" in report_text
        assert "✅ 通过" in report_text
    
    @pytest.mark.slow
    def test_real_screening_performance(self):
        """
        测试真实筛选性能
        
        注意: 此测试需要网络连接，可能耗时较长
        使用 pytest -m slow 运行此测试
        """
        tester = ScreeningPerformanceTester(target_duration_seconds=1800)  # 30分钟目标
        
        try:
            report = tester.run_full_screening_test(use_mock=False)
            print("\n" + report.generate_report())
            
            # 验证性能目标
            assert report.total_duration_seconds <= 1800, \
                f"筛选耗时 {report.total_duration_minutes:.2f} 分钟，超过30分钟目标"
            
            # 验证各阶段都成功
            for stage_result in report.stage_results:
                assert stage_result.passed, f"阶段 {stage_result.stage} 失败: {stage_result.error}"
                
        except ImportError as e:
            pytest.skip(f"缺少必要模块: {e}")
        except Exception as e:
            # 如果是网络问题，跳过测试
            if "网络" in str(e) or "connection" in str(e).lower():
                pytest.skip(f"网络问题: {e}")
            raise


class TestPerformanceOptimization:
    """性能优化测试"""
    
    def test_cache_effectiveness(self):
        """测试缓存有效性"""
        from core.stock_screener.performance_optimizer import DataCache
        
        cache = DataCache(max_size=100, default_ttl_minutes=30)
        
        # 第一次访问（缓存未命中）
        result1 = cache.get("test_key")
        assert result1 is None
        
        # 设置缓存
        cache.set("test_key", {"data": "test"})
        
        # 第二次访问（缓存命中）
        result2 = cache.get("test_key")
        assert result2 is not None
        assert result2["data"] == "test"
        
        # 验证命中率
        stats = cache.get_stats()
        assert stats['hit_count'] == 1
        assert stats['miss_count'] == 1
        assert stats['hit_rate'] == 50.0
    
    def test_parallel_processing(self):
        """测试并行处理"""
        from core.stock_screener.performance_optimizer import ParallelProcessor
        import time
        
        processor = ParallelProcessor(max_workers=4)
        
        # 创建测试数据
        items = list(range(100))
        
        def slow_process(x):
            time.sleep(0.01)  # 模拟耗时操作
            return x * 2
        
        # 串行处理时间估计
        serial_estimate = len(items) * 0.01
        
        # 并行处理
        start = time.time()
        results = processor.process_in_parallel(items, slow_process, chunk_size=25)
        parallel_time = time.time() - start
        
        # 验证结果正确
        assert len(results) == len(items)
        
        # 并行处理应该更快（至少快2倍）
        assert parallel_time < serial_estimate / 2, \
            f"并行处理 ({parallel_time:.2f}s) 应该比串行 ({serial_estimate:.2f}s) 快"
    
    def test_performance_monitor(self):
        """测试性能监控"""
        from core.stock_screener.performance_optimizer import PerformanceMonitor
        
        monitor = PerformanceMonitor()
        
        # 记录操作
        monitor.start_operation("test_op")
        time.sleep(0.1)
        metrics = monitor.end_operation(records_processed=100)
        
        assert metrics.operation == "test_op"
        assert metrics.duration_ms >= 100
        assert metrics.records_processed == 100
        assert metrics.success == True
        
        # 获取摘要
        summary = monitor.get_summary()
        assert summary['total_operations'] == 1
        assert summary['success_rate'] == 100.0


def run_performance_benchmark():
    """运行性能基准测试（独立脚本）"""
    print("=" * 70)
    print("科技股池筛选性能基准测试")
    print("=" * 70)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"目标: 完整筛选流程 ≤ 30分钟")
    print("=" * 70)
    
    tester = ScreeningPerformanceTester(target_duration_seconds=1800)
    
    # 首先运行模拟测试验证框架
    print("\n[1/2] 运行模拟测试验证框架...")
    mock_report = tester.run_full_screening_test(use_mock=True)
    print(f"模拟测试完成: {mock_report.total_duration_seconds:.2f}秒")
    
    # 重置测试器
    tester = ScreeningPerformanceTester(target_duration_seconds=1800)
    
    # 运行真实测试
    print("\n[2/2] 运行真实筛选测试...")
    try:
        report = tester.run_full_screening_test(use_mock=False)
        print("\n" + report.generate_report())
        
        # 保存报告
        report_path = "tests/SCREENING_PERFORMANCE_REPORT.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# 筛选流程性能测试报告\n\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("```\n")
            f.write(report.generate_report())
            f.write("\n```\n")
        print(f"\n报告已保存至: {report_path}")
        
        return report.passed
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        return False


if __name__ == '__main__':
    success = run_performance_benchmark()
    sys.exit(0 if success else 1)
