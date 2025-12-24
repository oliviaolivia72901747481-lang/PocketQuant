"""
科技股策略参数敏感性测试

测试各个关键参数的变化对策略表现的影响，验证策略鲁棒性。
"""

import sys
sys.path.insert(0, '.')

from core.tech_stock.backtester import TechBacktester
from config.tech_stock_pool import get_all_tech_stocks
import json

# 基准参数 (v11.2)
BASE_PARAMS = {
    'position_size_pct': 0.12,
    'max_positions': 5,
    'stop_loss_pct': -0.045,
    'take_profit_pct': 0.20,
    'max_holding_days': 15,
    'trailing_stop_trigger': 0.09,
    'trailing_stop_pct': 0.028,
    'rsi_low': 45,
    'rsi_high': 72,
    'signal_strength_threshold': 85
}

def run_backtest_with_params(params_override=None):
    """运行回测并返回结果"""
    bt = TechBacktester()
    all_stocks = get_all_tech_stocks()
    
    result = bt.run_backtest(
        stock_codes=all_stocks,
        start_date='2022-12-26',
        end_date='2025-12-23',
        initial_capital=100000
    )
    
    return {
        'return': result.total_return,
        'max_dd': result.max_drawdown,
        'trades': result.total_trades,
        'win_rate': result.win_rate
    }

def print_result(name, result, is_base=False):
    """打印结果"""
    marker = " [BASE]" if is_base else ""
    print(f"{name}{marker}:")
    print(f"  Return: {result['return']:.2%}, MaxDD: {result['max_dd']:.2%}, "
          f"Trades: {result['trades']}, WinRate: {result['win_rate']:.1%}")

# 运行基准测试
print("=" * 70)
print("PARAMETER SENSITIVITY TEST - Tech Stock Strategy v11.2")
print("=" * 70)
print()

print("Running baseline test...")
base_result = run_backtest_with_params()
print_result("Baseline (v11.2)", base_result, is_base=True)
print()

results = {'baseline': base_result}
