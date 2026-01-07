"""
Checkpoint 6: Calculator Verification Script

验证所有计算器模块的核心功能是否正常工作。
"""

import random
import sys

from core.overnight_picker.calculator import (
    EntryPriceCalculator,
    PositionAdvisor,
    StopLossCalculator,
    TakeProfitCalculator,
    SmartStopLoss,
    TrailingStop
)


def test_property_3_entry_price_order():
    """Property 3: 买入价格合理性 - 理想价 < 可接受价 < 放弃价"""
    print("Property 3: 买入价格合理性 (ideal < acceptable < abandon)")
    entry_calc = EntryPriceCalculator()
    
    for i in range(20):
        close = random.uniform(5, 100)
        high = close * random.uniform(1.0, 1.1)
        low = close * random.uniform(0.9, 1.0)
        score = random.uniform(60, 100)
        volatility = random.uniform(0.02, 0.12)
        
        result = entry_calc.calculate_entry_prices(close, high, low, score, volatility)
        
        if not (result['ideal_price'] < result['acceptable_price'] < result['abandon_price']):
            print(f"  FAIL: close={close:.2f}, score={score:.0f}")
            print(f"    ideal={result['ideal_price']}, acceptable={result['acceptable_price']}, abandon={result['abandon_price']}")
            return False
    
    print("  PASS: All 20 random tests passed")
    return True


def test_property_2_position_limits():
    """Property 2: 仓位限制有效性 - 单只股票仓位不超过30%，总仓位不超过80%"""
    print("Property 2: 仓位限制有效性 (single <= 30%, total <= 80%)")
    pos_advisor = PositionAdvisor(total_capital=70000)
    
    # Test single position limit
    for i in range(20):
        score = random.uniform(70, 100)
        price = random.uniform(5, 100)
        env = random.choice(['强势', '震荡', '弱势'])
        sentiment = random.choice(['乐观', '中性', '恐慌'])
        
        result = pos_advisor.calculate_position(score, price, env, sentiment)
        if result['position_ratio'] > 0.30:
            print(f"  FAIL: position_ratio={result['position_ratio']} > 0.30")
            return False
    
    print("  PASS: All 20 random tests passed (single position <= 30%)")
    
    # Test total position validation
    positions = [
        {'ratio': 0.25, 'amount': 17500},
        {'ratio': 0.25, 'amount': 17500},
        {'ratio': 0.25, 'amount': 17500},
        {'ratio': 0.25, 'amount': 17500},  # Total = 100%
    ]
    validation = pos_advisor.validate_total_position(positions)
    if validation['is_valid']:
        print("  FAIL: Total position validation should reject > 80%")
        return False
    
    print("  PASS: Total position validation correctly identifies > 80%")
    return True


def test_property_4_stop_loss_take_profit_order():
    """Property 4: 止损止盈合理性 - 止损价 < 买入价 < 第一止盈 < 第二止盈"""
    print("Property 4: 止损止盈合理性 (stop_loss < entry < first_target < second_target)")
    stop_calc = StopLossCalculator()
    tp_calc = TakeProfitCalculator()
    
    for i in range(20):
        entry_price = random.uniform(5, 100)
        position_amount = random.uniform(5000, 21000)
        volatility = random.uniform(0.02, 0.12)
        score = random.uniform(70, 100)
        
        stop_result = stop_calc.calculate_stop_loss(entry_price, position_amount, volatility)
        tp_result = tp_calc.calculate_take_profit(entry_price, position_amount, score)
        
        if not (stop_result['stop_loss_price'] < entry_price < tp_result['first_target'] < tp_result['second_target']):
            print(f"  FAIL: entry={entry_price:.2f}")
            print(f"    stop_loss={stop_result['stop_loss_price']}, first={tp_result['first_target']}, second={tp_result['second_target']}")
            return False
    
    print("  PASS: All 20 random tests passed")
    return True


def test_property_5_shares_multiple_of_100():
    """Property 5: 股数为100整数倍"""
    print("Property 5: 股数为100整数倍")
    pos_advisor = PositionAdvisor(total_capital=70000)
    
    for i in range(20):
        score = random.uniform(70, 100)
        price = random.uniform(5, 100)
        
        result = pos_advisor.calculate_position(score, price, '震荡', '中性')
        if result['shares'] > 0 and result['shares'] % 100 != 0:
            print(f"  FAIL: shares={result['shares']} is not multiple of 100")
            return False
    
    print("  PASS: All 20 random tests passed")
    return True


def test_property_10_smart_stop_loss_max_logic():
    """Property 10: 智能止损MAX逻辑 - stop = MAX(entry*0.95, prev_low, ma5)"""
    print("Property 10: 智能止损MAX逻辑 (stop = MAX(entry*0.95, prev_low, ma5))")
    smart_stop = SmartStopLoss()
    
    for i in range(20):
        entry_price = random.uniform(10, 100)
        prev_low = entry_price * random.uniform(0.9, 0.99)
        ma5 = entry_price * random.uniform(0.9, 0.99)
        volatility = 0.05  # Use default volatility
        
        result = smart_stop.calculate_smart_stop(entry_price, prev_low, ma5, volatility=volatility)
        
        # Calculate expected: MAX(entry*0.95, prev_low, ma5)
        fixed_stop = entry_price * 0.95
        expected_stop = max(fixed_stop, prev_low, ma5)
        
        # Allow small floating point difference
        if abs(result['stop_price'] - round(expected_stop, 2)) > 0.01:
            print(f"  FAIL: entry={entry_price:.2f}, prev_low={prev_low:.2f}, ma5={ma5:.2f}")
            print(f"    expected={expected_stop:.2f}, got={result['stop_price']}")
            return False
    
    print("  PASS: All 20 random tests passed")
    return True


def test_property_11_trailing_stop_ladder():
    """Property 11: 移动止盈阶梯逻辑 - 涨幅>=5% -> 止盈线>=成本价"""
    print("Property 11: 移动止盈阶梯逻辑 (涨幅>=5% -> 止盈线>=成本价)")
    trailing = TrailingStop()
    
    for i in range(20):
        entry_price = random.uniform(10, 100)
        # Generate highest_price that is at least 5% above entry
        profit_pct = random.uniform(0.05, 0.20)
        highest_price = entry_price * (1 + profit_pct)
        current_price = highest_price * random.uniform(0.95, 1.0)
        
        result = trailing.calculate_trailing_stop(entry_price, current_price, highest_price)
        
        # Use small epsilon for floating point comparison
        # trailing_stop should be >= entry_price (with small tolerance for rounding)
        if result['trailing_stop'] is not None and result['trailing_stop'] < entry_price - 0.01:
            print(f"  FAIL: entry={entry_price:.2f}, highest={highest_price:.2f}")
            print(f"    trailing_stop={result['trailing_stop']} < entry_price")
            return False
    
    print("  PASS: All 20 random tests passed")
    return True


def main():
    print("=== Checkpoint 6: Calculator Verification ===")
    print()
    
    all_passed = True
    
    # Run all property tests
    all_passed &= test_property_3_entry_price_order()
    print()
    
    all_passed &= test_property_2_position_limits()
    print()
    
    all_passed &= test_property_4_stop_loss_take_profit_order()
    print()
    
    all_passed &= test_property_5_shares_multiple_of_100()
    print()
    
    all_passed &= test_property_10_smart_stop_loss_max_logic()
    print()
    
    all_passed &= test_property_11_trailing_stop_ladder()
    print()
    
    print("=== Checkpoint 6 Verification Complete ===")
    
    if all_passed:
        print("\n✅ All calculator tests PASSED!")
        return 0
    else:
        print("\n❌ Some tests FAILED!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
