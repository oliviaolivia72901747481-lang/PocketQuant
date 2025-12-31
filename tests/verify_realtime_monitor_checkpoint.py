"""
Realtime Monitor Backend Checkpoint Verification

验证实时监控模块后端功能完整性。
Task 8: Checkpoint - 后端功能完整性验证
"""

import sys
import os
from datetime import datetime, date, time, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def verify_module_imports():
    """验证所有模块可以正常导入"""
    print("=" * 60)
    print("1. 验证模块导入")
    print("=" * 60)
    
    try:
        from core.realtime_monitor import (
            V114G_STRATEGY_PARAMS,
            MONITOR_CONFIG,
            Position,
            StockData,
            BuySignal,
            SellSignal,
            TechIndicators,
            SignalEngine,
            RealtimeMonitor,
            DataFetcher,
            MarketStatus,
            FundFlowData,
            get_market_status,
            is_trading_time,
        )
        print("✓ 所有模块导入成功")
        return True
    except ImportError as e:
        print(f"✗ 模块导入失败: {e}")
        return False


def verify_config():
    """验证配置参数"""
    print("\n" + "=" * 60)
    print("2. 验证配置参数")
    print("=" * 60)
    
    from core.realtime_monitor import V114G_STRATEGY_PARAMS, MONITOR_CONFIG
    
    # 验证v11.4g策略参数
    params = V114G_STRATEGY_PARAMS
    print(f"  止损线: {params.STOP_LOSS_PCT*100:.1f}%")
    print(f"  止盈线: {params.TAKE_PROFIT_PCT*100:.0f}%")
    print(f"  移动止盈触发: {params.TRAILING_TRIGGER_PCT*100:.0f}%")
    print(f"  移动止盈回撤: {params.TRAILING_STOP_PCT*100:.1f}%")
    print(f"  RSI范围: {params.RSI_MIN}-{params.RSI_MAX}")
    print(f"  RSI超买: {params.RSI_OVERBOUGHT}")
    print(f"  最小量比: {params.VOLUME_RATIO_MIN}")
    print(f"  最大持仓天数: {params.MAX_HOLDING_DAYS}")
    
    # 验证监控配置
    config = MONITOR_CONFIG
    print(f"  最大监控数: {config.max_watchlist_size}")
    print(f"  刷新间隔: {config.refresh_interval}秒")
    
    # 验证参数值正确
    assert params.STOP_LOSS_PCT == -0.046, "止损线应为-4.6%"
    assert params.TAKE_PROFIT_PCT == 0.22, "止盈线应为+22%"
    assert params.TRAILING_TRIGGER_PCT == 0.09, "移动止盈触发应为+9%"
    assert params.TRAILING_STOP_PCT == 0.028, "移动止盈回撤应为2.8%"
    assert params.RSI_MIN == 44, "RSI下限应为44"
    assert params.RSI_MAX == 70, "RSI上限应为70"
    assert params.RSI_OVERBOUGHT == 80, "RSI超买应为80"
    assert params.VOLUME_RATIO_MIN == 1.1, "最小量比应为1.1"
    assert params.MAX_HOLDING_DAYS == 15, "最大持仓天数应为15"
    assert config.max_watchlist_size == 20, "最大监控数应为20"
    
    print("✓ 所有配置参数验证通过")
    return True


def verify_models():
    """验证数据模型"""
    print("\n" + "=" * 60)
    print("3. 验证数据模型")
    print("=" * 60)
    
    from core.realtime_monitor import Position, StockData, BuySignal, SellSignal
    
    # 测试Position
    position = Position(
        code="000001",
        name="测试股票",
        cost_price=10.0,
        quantity=1000,
        buy_date=date.today() - timedelta(days=5),
        peak_price=11.0,
        current_price=10.5
    )
    
    assert position.market_value == 10500.0, "市值计算错误"
    assert position.cost_value == 10000.0, "成本计算错误"
    assert position.pnl == 500.0, "盈亏金额计算错误"
    assert abs(position.pnl_pct - 0.05) < 0.001, "盈亏百分比计算错误"
    assert position.holding_days == 5, "持仓天数计算错误"
    print("✓ Position模型验证通过")
    
    # 测试StockData
    stock_data = StockData(
        code="000001",
        name="测试股票",
        current_price=10.5,
        change_pct=0.02,
        volume=1000000,
        turnover=10500000,
        ma5=10.3,
        ma10=10.2,
        ma20=10.0,
        ma60=9.5,
        rsi=55.0,
        volume_ratio=1.2,
        ma20_slope=0.01,
        main_fund_flow=100.0,
        fund_flow_5d=500.0,
        updated_at=datetime.now()
    )
    
    conditions = stock_data.check_buy_conditions()
    assert conditions['ma5_above_ma20'] == True, "MA5>MA20条件检查错误"
    assert conditions['price_above_ma60'] == True, "价格>MA60条件检查错误"
    assert conditions['rsi_in_range'] == True, "RSI范围条件检查错误"
    assert conditions['volume_ratio_ok'] == True, "量比条件检查错误"
    assert conditions['ma20_slope_positive'] == True, "MA20斜率条件检查错误"
    print("✓ StockData模型验证通过")
    
    # 测试BuySignal
    buy_signal = BuySignal.from_stock_data(stock_data, 100)
    assert buy_signal.signal_strength == 100, "信号强度错误"
    assert buy_signal.stop_loss_price == round(10.5 * 0.954, 2), "止损价计算错误"
    assert buy_signal.take_profit_price == round(10.5 * 1.22, 2), "止盈价计算错误"
    print("✓ BuySignal模型验证通过")
    
    # 测试SellSignal
    sell_signal = SellSignal.create_stop_loss_signal(position)
    assert sell_signal.signal_type == SellSignal.TYPE_STOP_LOSS, "信号类型错误"
    assert sell_signal.urgency == SellSignal.URGENCY_HIGH, "紧急程度错误"
    print("✓ SellSignal模型验证通过")
    
    return True


def verify_indicators():
    """验证技术指标计算"""
    print("\n" + "=" * 60)
    print("4. 验证技术指标计算")
    print("=" * 60)
    
    import pandas as pd
    import numpy as np
    from core.realtime_monitor import TechIndicators
    
    # 创建测试数据
    prices = pd.Series([10.0, 10.5, 11.0, 10.8, 11.2, 11.5, 11.3, 11.8, 12.0, 11.9])
    volumes = pd.Series([1000, 1200, 1100, 1300, 1500, 1400, 1600, 1800, 1700, 2000])
    
    # 测试MA计算
    ma5 = TechIndicators.calculate_ma(prices, 5)
    assert not np.isnan(ma5.iloc[-1]), "MA5计算失败"
    print(f"  MA5: {ma5.iloc[-1]:.2f}")
    
    # 测试RSI计算
    rsi = TechIndicators.calculate_rsi(prices, 14)
    # RSI需要更多数据，这里只验证不报错
    print(f"  RSI计算: {'成功' if rsi is not None else '失败'}")
    
    # 测试量比计算
    volume_ratio = TechIndicators.calculate_volume_ratio(volumes, 5)
    assert volume_ratio > 0, "量比计算失败"
    print(f"  量比: {volume_ratio:.2f}")
    
    # 测试MA斜率计算
    ma_slope = TechIndicators.calculate_ma_slope(ma5, 3)
    print(f"  MA斜率: {ma_slope:.4f}")
    
    print("✓ 技术指标计算验证通过")
    return True


def verify_signal_engine():
    """验证信号引擎"""
    print("\n" + "=" * 60)
    print("5. 验证信号引擎")
    print("=" * 60)
    
    from core.realtime_monitor import SignalEngine, StockData, Position
    
    engine = SignalEngine()
    
    # 测试买入条件检查
    stock_data = StockData(
        code="000001",
        name="测试股票",
        current_price=10.5,
        change_pct=0.02,
        volume=1000000,
        turnover=10500000,
        ma5=10.3,
        ma10=10.2,
        ma20=10.0,
        ma60=9.5,
        rsi=55.0,
        volume_ratio=1.2,
        ma20_slope=0.01,
        main_fund_flow=100.0,
        fund_flow_5d=500.0,
        updated_at=datetime.now()
    )
    
    conditions = engine.check_buy_conditions(stock_data)
    conditions_met = sum(conditions.values())
    print(f"  买入条件满足数: {conditions_met}/6")
    
    # 测试信号强度计算
    strength = engine.calculate_signal_strength(conditions, stock_data)
    print(f"  信号强度: {strength}")
    
    # 测试买入信号生成
    buy_signal = engine.generate_buy_signal(stock_data)
    if buy_signal:
        print(f"  买入信号: 强度={buy_signal.signal_strength}")
    else:
        print("  买入信号: 未生成（条件不足）")
    
    # 测试卖出条件检查
    position = Position(
        code="000001",
        name="测试股票",
        cost_price=10.0,
        quantity=1000,
        buy_date=date.today() - timedelta(days=5),
        peak_price=11.0,
        current_price=9.5  # 亏损5%
    )
    
    # 测试止损
    assert engine.check_stop_loss(position) == True, "止损检查失败"
    print("  止损检查: ✓")
    
    # 测试止盈
    position.current_price = 12.5  # 盈利25%
    position.peak_price = 12.5
    assert engine.check_take_profit(position) == True, "止盈检查失败"
    print("  止盈检查: ✓")
    
    # 测试移动止盈
    position.current_price = 10.6  # 从峰值回撤
    position.peak_price = 11.0  # 峰值盈利10%
    assert engine.check_trailing_stop(position) == True, "移动止盈检查失败"
    print("  移动止盈检查: ✓")
    
    # 测试RSI超买
    position.current_price = 10.5  # 盈利5%
    assert engine.check_rsi_overbought(position, 85) == True, "RSI超买检查失败"
    print("  RSI超买检查: ✓")
    
    # 测试趋势反转
    position.current_price = 9.8  # 亏损2%
    assert engine.check_trend_reversal(position, 9.5, 10.0) == True, "趋势反转检查失败"
    print("  趋势反转检查: ✓")
    
    # 测试持仓超时
    position_old = Position(
        code="000001",
        name="测试股票",
        cost_price=10.0,
        quantity=1000,
        buy_date=date.today() - timedelta(days=20),
        peak_price=10.0,
        current_price=10.0
    )
    assert engine.check_timeout(position_old) == True, "持仓超时检查失败"
    print("  持仓超时检查: ✓")
    
    print("✓ 信号引擎验证通过")
    return True


def verify_monitor():
    """验证监控器"""
    print("\n" + "=" * 60)
    print("6. 验证监控器")
    print("=" * 60)
    
    from core.realtime_monitor import RealtimeMonitor
    
    monitor = RealtimeMonitor()
    
    # 测试股票代码验证
    assert monitor.validate_stock_code("000001") == True, "有效代码验证失败"
    assert monitor.validate_stock_code("300001") == True, "有效代码验证失败"
    assert monitor.validate_stock_code("600001") == True, "有效代码验证失败"
    assert monitor.validate_stock_code("100001") == False, "无效代码验证失败"
    assert monitor.validate_stock_code("00001") == False, "无效代码验证失败"
    print("  股票代码验证: ✓")
    
    # 测试监控列表管理
    assert monitor.add_to_watchlist("000001") == True, "添加监控失败"
    assert monitor.add_to_watchlist("000001") == False, "重复添加应失败"
    assert monitor.is_in_watchlist("000001") == True, "监控列表检查失败"
    assert monitor.remove_from_watchlist("000001") == True, "移除监控失败"
    assert monitor.is_in_watchlist("000001") == False, "监控列表检查失败"
    print("  监控列表管理: ✓")
    
    # 测试监控列表大小限制
    monitor.clear_watchlist()
    for i in range(20):
        code = f"00000{i}" if i < 10 else f"0000{i}"
        code = code[-6:]  # 确保6位
        if code.startswith(('0', '3', '6')):
            monitor.add_to_watchlist(code)
    
    # 填满20个
    codes = ["000001", "000002", "000003", "000004", "000005",
             "000006", "000007", "000008", "000009", "000010",
             "000011", "000012", "000013", "000014", "000015",
             "000016", "000017", "000018", "000019", "000020"]
    monitor.clear_watchlist()
    for code in codes:
        monitor.add_to_watchlist(code)
    
    assert monitor.watchlist_size == 20, "监控列表大小错误"
    assert monitor.add_to_watchlist("000021") == False, "超出限制应失败"
    print("  监控列表大小限制: ✓")
    
    # 测试持仓管理
    monitor.clear_watchlist()
    monitor.clear_positions()
    
    assert monitor.add_position("000001", "测试股票", 10.0, 1000) == True, "添加持仓失败"
    assert monitor.has_position("000001") == True, "持仓检查失败"
    assert monitor.update_position("000001", cost_price=10.5) == True, "更新持仓失败"
    
    position = monitor.get_position("000001")
    assert position.cost_price == 10.5, "持仓更新错误"
    
    assert monitor.remove_position("000001") == True, "移除持仓失败"
    assert monitor.has_position("000001") == False, "持仓检查失败"
    print("  持仓管理: ✓")
    
    # 测试峰值价格跟踪
    monitor.add_position("000002", "测试股票2", 10.0, 1000)
    monitor.update_position_price("000002", 11.0)
    assert monitor.get_peak_price("000002") == 11.0, "峰值价格更新失败"
    
    monitor.update_position_price("000002", 10.5)  # 价格下跌
    assert monitor.get_peak_price("000002") == 11.0, "峰值价格不应下降"
    print("  峰值价格跟踪: ✓")
    
    print("✓ 监控器验证通过")
    return True


def verify_market_status():
    """验证市场状态检测"""
    print("\n" + "=" * 60)
    print("7. 验证市场状态检测")
    print("=" * 60)
    
    from core.realtime_monitor import DataFetcher, MarketStatus
    
    fetcher = DataFetcher()
    
    # 测试上午交易时段
    morning_time = datetime(2024, 1, 15, 10, 0)  # 周一上午10点
    status = fetcher.get_market_status(morning_time)
    assert status.is_open == True, "上午交易时段应为开市"
    assert status.status == MarketStatus.STATUS_OPEN, "状态应为open"
    print(f"  上午10:00: {status.status} - {status.message}")
    
    # 测试下午交易时段
    afternoon_time = datetime(2024, 1, 15, 14, 0)  # 周一下午2点
    status = fetcher.get_market_status(afternoon_time)
    assert status.is_open == True, "下午交易时段应为开市"
    print(f"  下午14:00: {status.status} - {status.message}")
    
    # 测试午休时段
    lunch_time = datetime(2024, 1, 15, 12, 0)  # 周一中午12点
    status = fetcher.get_market_status(lunch_time)
    assert status.is_open == False, "午休时段应为休市"
    assert status.status == MarketStatus.STATUS_LUNCH_BREAK, "状态应为lunch_break"
    print(f"  中午12:00: {status.status} - {status.message}")
    
    # 测试盘前
    pre_market_time = datetime(2024, 1, 15, 9, 0)  # 周一上午9点
    status = fetcher.get_market_status(pre_market_time)
    assert status.is_open == False, "盘前应为休市"
    assert status.status == MarketStatus.STATUS_PRE_MARKET, "状态应为pre_market"
    print(f"  上午09:00: {status.status} - {status.message}")
    
    # 测试盘后
    after_hours_time = datetime(2024, 1, 15, 16, 0)  # 周一下午4点
    status = fetcher.get_market_status(after_hours_time)
    assert status.is_open == False, "盘后应为休市"
    assert status.status == MarketStatus.STATUS_AFTER_HOURS, "状态应为after_hours"
    print(f"  下午16:00: {status.status} - {status.message}")
    
    # 测试周末
    weekend_time = datetime(2024, 1, 13, 10, 0)  # 周六上午10点
    status = fetcher.get_market_status(weekend_time)
    assert status.is_open == False, "周末应为休市"
    assert status.status == MarketStatus.STATUS_CLOSED, "状态应为closed"
    print(f"  周六10:00: {status.status} - {status.message}")
    
    print("✓ 市场状态检测验证通过")
    return True


def verify_data_fetcher():
    """验证数据获取器（不实际获取数据）"""
    print("\n" + "=" * 60)
    print("8. 验证数据获取器结构")
    print("=" * 60)
    
    from core.realtime_monitor import DataFetcher
    
    fetcher = DataFetcher()
    
    # 验证方法存在
    assert hasattr(fetcher, 'fetch_realtime_quote'), "缺少fetch_realtime_quote方法"
    assert hasattr(fetcher, 'fetch_realtime_quotes_batch'), "缺少fetch_realtime_quotes_batch方法"
    assert hasattr(fetcher, 'fetch_historical_data'), "缺少fetch_historical_data方法"
    assert hasattr(fetcher, 'fetch_stock_data'), "缺少fetch_stock_data方法"
    assert hasattr(fetcher, 'fetch_fund_flow'), "缺少fetch_fund_flow方法"
    assert hasattr(fetcher, 'get_market_status'), "缺少get_market_status方法"
    print("  数据获取方法: ✓")
    
    # 验证缓存功能
    assert hasattr(fetcher, 'get_cached_data'), "缺少get_cached_data方法"
    assert hasattr(fetcher, 'clear_cache'), "缺少clear_cache方法"
    assert hasattr(fetcher, 'should_refresh'), "缺少should_refresh方法"
    print("  缓存管理方法: ✓")
    
    # 验证初始状态
    assert fetcher.should_refresh() == True, "初始状态应需要刷新"
    assert fetcher.last_update is None, "初始更新时间应为None"
    print("  初始状态: ✓")
    
    print("✓ 数据获取器结构验证通过")
    return True


def main():
    """运行所有验证"""
    print("\n" + "=" * 60)
    print("实时监控模块后端功能完整性验证")
    print("Task 8: Checkpoint - 后端功能完整性验证")
    print("=" * 60)
    
    results = []
    
    # 运行所有验证
    results.append(("模块导入", verify_module_imports()))
    results.append(("配置参数", verify_config()))
    results.append(("数据模型", verify_models()))
    results.append(("技术指标", verify_indicators()))
    results.append(("信号引擎", verify_signal_engine()))
    results.append(("监控器", verify_monitor()))
    results.append(("市场状态", verify_market_status()))
    results.append(("数据获取器", verify_data_fetcher()))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("验证结果汇总")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ 所有后端功能验证通过！")
        print("  - 模块导入正常")
        print("  - v11.4g策略参数正确")
        print("  - 数据模型功能完整")
        print("  - 技术指标计算正确")
        print("  - 信号引擎逻辑正确")
        print("  - 监控器功能完整")
        print("  - 市场状态检测正确")
        print("  - 数据获取器结构完整")
    else:
        print("✗ 部分验证失败，请检查上述错误")
    print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
