"""
科技股池回测脚本

使用评分系统v6对100只科技股进行回测分析
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.tech_stock_pool import get_all_tech_stocks
from core.overnight_picker import run_overnight_backtest

def main():
    # 获取科技股池
    tech_stocks = get_all_tech_stocks()
    print(f'科技股池股票数量: {len(tech_stocks)}')
    print(f'股票代码示例: {tech_stocks[:5]}')

    # 运行回测 (最近30天)
    print('\n开始回测科技股池...')
    # 注意：由于数据中缺少主力资金流、热点概念等信息，评分会偏低
    # 降低最低评分阈值以获得更多选股结果
    result = run_overnight_backtest(
        start_date='2025-12-01',
        end_date='2026-01-06',
        initial_capital=70000,
        min_score=50,  # 降低阈值以适应数据限制
        max_recommendations=15,  # 每日推荐15只股票
        data_path='data/processed',
        stock_pool=tech_stocks,
        save_report=True
    )

    # 输出结果
    print('\n' + '='*60)
    print('📊 科技股池回测结果')
    print('='*60)
    print(f'回测期间: {result.start_date} ~ {result.end_date}')
    print(f'总交易日: {result.total_days}')
    print(f'有选股天数: {result.pick_days}')
    print(f'总选股次数: {result.total_picks}')
    print(f'实际执行次数: {result.executed_picks}')
    print()
    print('📈 核心指标:')
    print(f'  胜率: {result.win_rate:.2%}')
    print(f'  平均收益率: {result.avg_return:.2%}')
    print(f'  总收益率: {result.total_return:.2%}')
    print(f'  盈亏比: {result.profit_factor:.2f}')
    print()
    print('💰 盈亏统计:')
    print(f'  盈利次数: {result.win_count}')
    print(f'  亏损次数: {result.loss_count}')
    print(f'  平均盈利: {result.avg_win:.2%}')
    print(f'  平均亏损: {result.avg_loss:.2%}')
    print(f'  最大单次盈利: {result.max_win:.2%}')
    print(f'  最大单次亏损: {result.max_loss:.2%}')
    print()
    print('📊 评分分组统计:')
    for group, stats in result.score_group_stats.items():
        if stats['count'] > 0:
            count = stats['count']
            win_rate = stats['win_rate']
            avg_return = stats['avg_return']
            print(f'  {group}: 次数={count}, 胜率={win_rate:.1%}, 平均收益={avg_return:.2%}')

if __name__ == '__main__':
    main()
