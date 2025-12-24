"""
普通股策略优化测试脚本

测试 RSRS 和布林带策略的优化效果
"""

import sys
sys.path.insert(0, '.')

import pandas as pd
from config.stock_pool import get_watchlist
from config.settings import get_settings
from core.data_feed import DataFeed
from backtest.run_backtest import BacktestConfig, run_backtest
from strategies.rsrs_strategy import RSRSStrategy
from strategies.bollinger_reversion_strategy import BollingerReversionStrategy


def run_optimization_test():
    """运行策略优化测试"""
    settings = get_settings()
    
    config = BacktestConfig(
        initial_cash=55000.0,
        start_date='2024-12-24',
        end_date='2025-12-20',
        commission_rate=0.0003,
        stamp_duty=0.001,
        slippage_perc=0.001
    )
    
    stocks = get_watchlist()
    print(f'测试股票数量: {len(stocks)}')
    
    data_feed = DataFeed(settings.path.get_raw_path(), settings.path.get_processed_path())
    stock_data = {}
    for code in stocks:
        df = data_feed.get_stock_data(code)
        if df is not None and not df.empty:
            stock_data[code] = df
    
    print(f'成功加载数据: {len(stock_data)} 只股票')
    print(f'回测时间范围: {config.start_date} ~ {config.end_date}')
    
    # RSRS 策略回测
    print('\n' + '='*60)
    print('RSRS 策略回测（优化版 v2.0）')
    print('='*60)
    result_rsrs = run_backtest(
        stock_data=stock_data,
        strategy_class=RSRSStrategy,
        config=config,
        load_benchmark=True
    )
    print(f'总收益率: {result_rsrs.total_return:.2%}')
    print(f'年化收益率: {result_rsrs.annual_return:.2%}')
    print(f'最大回撤: {result_rsrs.max_drawdown:.2%}')
    print(f'夏普比率: {result_rsrs.sharpe_ratio:.2f}')
    print(f'胜率: {result_rsrs.win_rate:.2%}')
    print(f'交易次数: {result_rsrs.trade_count}')
    print(f'基准收益率: {result_rsrs.benchmark_return:.2%}')
    print(f'Alpha: {result_rsrs.alpha:.2%}')
    
    # 布林带策略回测
    print('\n' + '='*60)
    print('布林带均值回归策略回测（优化版 v2.0）')
    print('='*60)
    result_boll = run_backtest(
        stock_data=stock_data,
        strategy_class=BollingerReversionStrategy,
        config=config,
        load_benchmark=True
    )
    print(f'总收益率: {result_boll.total_return:.2%}')
    print(f'年化收益率: {result_boll.annual_return:.2%}')
    print(f'最大回撤: {result_boll.max_drawdown:.2%}')
    print(f'夏普比率: {result_boll.sharpe_ratio:.2f}')
    print(f'胜率: {result_boll.win_rate:.2%}')
    print(f'交易次数: {result_boll.trade_count}')
    print(f'基准收益率: {result_boll.benchmark_return:.2%}')
    print(f'Alpha: {result_boll.alpha:.2%}')
    
    # 交易明细
    print('\n' + '='*60)
    print('RSRS 策略交易明细')
    print('='*60)
    if result_rsrs.trade_log:
        for trade in result_rsrs.trade_log[:10]:
            print(f"日期: {trade.get('datetime')}, 代码: {trade.get('code')}, "
                  f"盈亏: {trade.get('pnl', 0):.2f}, 盈亏%: {trade.get('profit_pct', 0):.2%}, "
                  f"原因: {trade.get('exit_reason', 'N/A')}")
    else:
        print('无交易记录')
    
    # 优化总结
    print('\n' + '='*60)
    print('优化总结')
    print('='*60)
    print('RSRS 策略优化内容:')
    print('  - 买入阈值: 0.7 -> 0.5 (放宽)')
    print('  - 卖出阈值: -0.7 -> -0.5 (放宽)')
    print('  - 硬止损: -8% -> -5%')
    print('  - 新增止盈: +20%')
    print('  - 新增移动止盈: 触发+8%, 回撤3%')
    print('  - 新增最大持仓天数: 15天')
    print('  - 新增趋势反转卖出')
    print('')
    print('布林带策略优化内容:')
    print('  - RSI买入阈值: 35 -> 45 (放宽)')
    print('  - 硬止损: -8% -> -5%')
    print('  - 新增止盈: +18%')
    print('  - 新增移动止盈: 触发+8%, 回撤3%')
    print('  - 最大持仓天数: 10 -> 12天')
    print('  - 成交量过滤: 必选 -> 可选')
    print('  - 新增趋势反转卖出')
    
    return result_rsrs, result_boll


if __name__ == '__main__':
    run_optimization_test()
