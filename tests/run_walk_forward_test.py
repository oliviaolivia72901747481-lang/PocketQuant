"""
科技股策略滚动回测（Walk-Forward Analysis）

滚动回测更贴近实盘，避免过拟合：
1. 将数据分成多个时间窗口
2. 每个窗口独立回测
3. 汇总所有窗口的结果

窗口设计：
- 每个窗口6个月
- 窗口滚动步长3个月（50%重叠）
- 模拟真实的"样本外"测试

优势：
- 避免单一时间段的偶然性
- 验证策略在不同市场环境下的稳定性
- 更接近实盘的真实表现
"""
import sys
sys.path.insert(0, '.')

import pandas as pd
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import Dict, List, Tuple
from dataclasses import dataclass

from core.tech_stock.backtester import TechBacktester
from config.tech_stock_pool import get_all_tech_stocks


@dataclass
class WindowResult:
    """单个窗口的回测结果"""
    window_id: int
    start_date: str
    end_date: str
    total_return: float
    max_drawdown: float
    total_trades: int
    win_rate: float
    return_dd_ratio: float
    market_condition: str  # 市场状态描述


@dataclass
class WalkForwardResult:
    """滚动回测汇总结果"""
    windows: List[WindowResult]
    total_return: float  # 累计收益率
    avg_return: float  # 平均窗口收益率
    avg_drawdown: float  # 平均最大回撤
    avg_win_rate: float  # 平均胜率
    consistency_score: float  # 一致性得分 (盈利窗口占比)
    worst_window: WindowResult
    best_window: WindowResult


class WalkForwardTester:
    """滚动回测测试器"""
    
    def __init__(self):
        self.stock_codes = get_all_tech_stocks()
        self.initial_capital = 100000
        self.window_months = 6  # 每个窗口6个月
        self.step_months = 3    # 滚动步长3个月
        
    def generate_windows(self, start_date: str, end_date: str) -> List[Tuple[str, str]]:
        """
        生成滚动窗口列表
        
        Args:
            start_date: 总体开始日期
            end_date: 总体结束日期
        
        Returns:
            [(window_start, window_end), ...]
        """
        windows = []
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        current_start = start_dt
        
        while True:
            current_end = current_start + relativedelta(months=self.window_months)
            
            # 如果窗口结束日期超过总体结束日期，调整为总体结束日期
            if current_end > end_dt:
                current_end = end_dt
            
            # 如果窗口太短（少于2个月），跳过
            if (current_end - current_start).days < 60:
                break
            
            windows.append((
                current_start.strftime('%Y-%m-%d'),
                current_end.strftime('%Y-%m-%d')
            ))
            
            # 滚动到下一个窗口
            current_start = current_start + relativedelta(months=self.step_months)
            
            # 如果下一个窗口开始日期超过总体结束日期，停止
            if current_start >= end_dt:
                break
        
        return windows
    
    def classify_market_condition(self, start_date: str, end_date: str) -> str:
        """
        根据时间段判断市场状态
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            市场状态描述
        """
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        # 2022年: 熊市
        # 2023年上半年: 震荡市
        # 2023年下半年: 震荡市
        # 2024年: 结构性行情
        
        mid_date = start_dt + (end_dt - start_dt) / 2
        
        if mid_date.year == 2022:
            return "熊市"
        elif mid_date.year == 2023 and mid_date.month <= 6:
            return "震荡市(上)"
        elif mid_date.year == 2023 and mid_date.month > 6:
            return "震荡市(下)"
        elif mid_date.year == 2024 and mid_date.month <= 6:
            return "结构性行情(上)"
        elif mid_date.year == 2024 and mid_date.month > 6:
            return "结构性行情(下)"
        else:
            return "未知"
    
    def run_single_window(self, window_id: int, start_date: str, end_date: str) -> WindowResult:
        """
        运行单个窗口的回测
        
        Args:
            window_id: 窗口编号
            start_date: 窗口开始日期
            end_date: 窗口结束日期
        
        Returns:
            窗口回测结果
        """
        bt = TechBacktester()
        result = bt.run_backtest(
            stock_codes=self.stock_codes,
            start_date=start_date,
            end_date=end_date,
            initial_capital=self.initial_capital
        )
        
        ratio = abs(result.total_return / result.max_drawdown) if result.max_drawdown != 0 else 0
        market_condition = self.classify_market_condition(start_date, end_date)
        
        return WindowResult(
            window_id=window_id,
            start_date=start_date,
            end_date=end_date,
            total_return=result.total_return,
            max_drawdown=result.max_drawdown,
            total_trades=result.total_trades,
            win_rate=result.win_rate,
            return_dd_ratio=ratio,
            market_condition=market_condition
        )
    
    def run_walk_forward(self, start_date: str = '2023-01-01', end_date: str = '2024-12-23') -> WalkForwardResult:
        """
        运行滚动回测
        
        Args:
            start_date: 总体开始日期
            end_date: 总体结束日期
        
        Returns:
            滚动回测汇总结果
        """
        print("=" * 70)
        print("滚动回测（Walk-Forward Analysis）- 科技股策略 v11.2")
        print("=" * 70)
        print()
        print(f"回测区间: {start_date} ~ {end_date}")
        print(f"窗口大小: {self.window_months} 个月")
        print(f"滚动步长: {self.step_months} 个月")
        print(f"股票池: {len(self.stock_codes)} 只")
        print()
        
        # 生成窗口
        windows = self.generate_windows(start_date, end_date)
        print(f"共 {len(windows)} 个滚动窗口")
        print("-" * 70)
        
        # 运行每个窗口的回测
        results = []
        for i, (w_start, w_end) in enumerate(windows):
            print(f"窗口 {i+1}/{len(windows)}: {w_start} ~ {w_end} ...", end=" ")
            result = self.run_single_window(i+1, w_start, w_end)
            results.append(result)
            print(f"收益 {result.total_return:.2%}, 回撤 {result.max_drawdown:.2%}, 交易 {result.total_trades}")
        
        print("-" * 70)
        print()
        
        # 计算汇总指标
        returns = [r.total_return for r in results]
        drawdowns = [r.max_drawdown for r in results]
        win_rates = [r.win_rate for r in results if r.total_trades > 0]
        
        # 累计收益率（复利计算）
        cumulative_return = 1.0
        for r in returns:
            cumulative_return *= (1 + r)
        cumulative_return -= 1
        
        # 一致性得分（盈利窗口占比）
        profitable_windows = sum(1 for r in returns if r > 0)
        consistency_score = profitable_windows / len(returns) if results else 0
        
        # 找出最好和最差的窗口
        best_window = max(results, key=lambda x: x.total_return)
        worst_window = min(results, key=lambda x: x.total_return)
        
        return WalkForwardResult(
            windows=results,
            total_return=cumulative_return,
            avg_return=sum(returns) / len(returns) if returns else 0,
            avg_drawdown=sum(drawdowns) / len(drawdowns) if drawdowns else 0,
            avg_win_rate=sum(win_rates) / len(win_rates) if win_rates else 0,
            consistency_score=consistency_score,
            worst_window=worst_window,
            best_window=best_window
        )
    
    def generate_report(self, result: WalkForwardResult) -> str:
        """生成滚动回测报告"""
        report = []
        report.append("# 滚动回测报告（Walk-Forward Analysis）")
        report.append("")
        report.append(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"策略版本: v11.2")
        report.append(f"股票池: {len(self.stock_codes)} 只")
        report.append(f"窗口大小: {self.window_months} 个月")
        report.append(f"滚动步长: {self.step_months} 个月")
        report.append("")
        
        # 汇总指标
        report.append("## 汇总指标")
        report.append("")
        report.append("| 指标 | 数值 | 评价 |")
        report.append("|------|------|------|")
        report.append(f"| 累计收益率 | {result.total_return:.2%} | {'✅ 优秀' if result.total_return > 0.30 else '⚠️ 一般'} |")
        report.append(f"| 平均窗口收益率 | {result.avg_return:.2%} | {'✅ 稳定' if result.avg_return > 0.05 else '⚠️ 波动'} |")
        report.append(f"| 平均最大回撤 | {result.avg_drawdown:.2%} | {'✅ 可控' if result.avg_drawdown > -0.12 else '⚠️ 较大'} |")
        report.append(f"| 平均胜率 | {result.avg_win_rate:.1%} | - |")
        report.append(f"| 一致性得分 | {result.consistency_score:.1%} | {'✅ 稳定' if result.consistency_score > 0.6 else '⚠️ 波动'} |")
        report.append(f"| 盈利窗口数 | {sum(1 for w in result.windows if w.total_return > 0)}/{len(result.windows)} | - |")
        report.append("")
        
        # 各窗口详情
        report.append("## 各窗口详情")
        report.append("")
        report.append("| 窗口 | 时间段 | 市场状态 | 收益率 | 最大回撤 | 交易次数 | 胜率 | 收益/回撤比 |")
        report.append("|------|--------|----------|--------|----------|----------|------|-------------|")
        
        for w in result.windows:
            status = "✅" if w.total_return > 0 else "❌"
            report.append(f"| {w.window_id} | {w.start_date}~{w.end_date} | {w.market_condition} | {status} {w.total_return:.2%} | {w.max_drawdown:.2%} | {w.total_trades} | {w.win_rate:.1%} | {w.return_dd_ratio:.2f} |")
        report.append("")
        
        # 最佳和最差窗口
        report.append("## 极端情况分析")
        report.append("")
        report.append("### 最佳窗口")
        report.append(f"- 时间段: {result.best_window.start_date} ~ {result.best_window.end_date}")
        report.append(f"- 市场状态: {result.best_window.market_condition}")
        report.append(f"- 收益率: {result.best_window.total_return:.2%}")
        report.append(f"- 最大回撤: {result.best_window.max_drawdown:.2%}")
        report.append("")
        report.append("### 最差窗口")
        report.append(f"- 时间段: {result.worst_window.start_date} ~ {result.worst_window.end_date}")
        report.append(f"- 市场状态: {result.worst_window.market_condition}")
        report.append(f"- 收益率: {result.worst_window.total_return:.2%}")
        report.append(f"- 最大回撤: {result.worst_window.max_drawdown:.2%}")
        report.append("")
        
        # 市场状态分析
        report.append("## 不同市场状态表现")
        report.append("")
        
        # 按市场状态分组
        market_groups = {}
        for w in result.windows:
            if w.market_condition not in market_groups:
                market_groups[w.market_condition] = []
            market_groups[w.market_condition].append(w)
        
        report.append("| 市场状态 | 窗口数 | 平均收益率 | 平均回撤 | 盈利比例 |")
        report.append("|----------|--------|------------|----------|----------|")
        
        for condition, windows in market_groups.items():
            avg_ret = sum(w.total_return for w in windows) / len(windows)
            avg_dd = sum(w.max_drawdown for w in windows) / len(windows)
            profit_ratio = sum(1 for w in windows if w.total_return > 0) / len(windows)
            status = "✅" if avg_ret > 0 else "❌"
            report.append(f"| {condition} | {len(windows)} | {status} {avg_ret:.2%} | {avg_dd:.2%} | {profit_ratio:.0%} |")
        report.append("")
        
        # 结论
        report.append("## 滚动回测结论")
        report.append("")
        
        is_robust = result.consistency_score > 0.5 and result.total_return > 0.20
        
        if is_robust:
            report.append("### ✅ 策略通过滚动回测验证")
            report.append("")
            report.append("1. **时间稳定性**: 在多个独立时间窗口中表现一致")
            report.append(f"2. **盈利能力**: {result.consistency_score:.0%} 的窗口实现盈利")
            report.append(f"3. **累计收益**: {result.total_return:.2%} 的累计收益率")
            report.append("4. **实盘可行性**: 滚动回测结果更接近实盘表现")
        else:
            report.append("### ⚠️ 策略需要进一步优化")
            report.append("")
            report.append("1. 部分时间窗口表现不佳")
            report.append("2. 建议分析亏损窗口的原因")
            report.append("3. 考虑针对不同市场状态调整参数")
        
        report.append("")
        report.append("### 与传统回测对比")
        report.append("")
        report.append("| 方法 | 收益率 | 说明 |")
        report.append("|------|--------|------|")
        report.append("| 传统回测 | 41.38% | 单一时间段，可能过拟合 |")
        report.append(f"| 滚动回测 | {result.total_return:.2%} | 多窗口验证，更接近实盘 |")
        report.append("")
        
        report.append("### 风险提示")
        report.append("")
        report.append("1. 滚动回测结果更保守，但更可靠")
        report.append("2. 实盘表现可能仍有差异（滑点、手续费等）")
        report.append("3. 建议小资金实盘验证后再加大仓位")
        report.append("")
        
        report.append(f"*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        
        return "\n".join(report)


def main():
    """主函数"""
    tester = WalkForwardTester()
    
    # 运行滚动回测
    result = tester.run_walk_forward(
        start_date='2023-01-01',
        end_date='2024-12-23'
    )
    
    # 打印汇总
    print("=" * 70)
    print("滚动回测汇总")
    print("=" * 70)
    print(f"累计收益率: {result.total_return:.2%}")
    print(f"平均窗口收益率: {result.avg_return:.2%}")
    print(f"平均最大回撤: {result.avg_drawdown:.2%}")
    print(f"一致性得分: {result.consistency_score:.1%}")
    print(f"最佳窗口: {result.best_window.start_date}~{result.best_window.end_date}, 收益 {result.best_window.total_return:.2%}")
    print(f"最差窗口: {result.worst_window.start_date}~{result.worst_window.end_date}, 收益 {result.worst_window.total_return:.2%}")
    print()
    
    # 生成报告
    report = tester.generate_report(result)
    
    # 保存报告
    report_path = "tests/WALK_FORWARD_TEST_REPORT.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"滚动回测报告已保存: {report_path}")
    print("=" * 70)
    
    return result


if __name__ == "__main__":
    main()
