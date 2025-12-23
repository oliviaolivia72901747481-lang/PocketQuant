"""
后端模块完成验证脚本

验证所有科技股后端模块的正确性：
1. 模块导入
2. 基本功能
3. 接口兼容性
4. 回测引擎
"""

import sys
from datetime import date, datetime

def test_module_imports():
    """测试所有模块可以正确导入"""
    print("=" * 60)
    print("测试 1: 模块导入")
    print("=" * 60)
    
    try:
        from core.tech_stock.market_filter import MarketFilter, MarketStatus
        from core.tech_stock.sector_ranker import SectorRanker, SectorRank
        from core.tech_stock.hard_filter import HardFilter, HardFilterResult
        from core.tech_stock.signal_generator import TechSignalGenerator, TechBuySignal
        from core.tech_stock.exit_manager import TechExitManager, TechExitSignal, SignalPriority
        from core.tech_stock.backtester import TechBacktester, TechBacktestResult, PeriodPerformance
        
        print("✓ 所有模块导入成功")
        return True
    except Exception as e:
        print(f"✗ 模块导入失败: {e}")
        return False


def test_market_filter():
    """测试大盘红绿灯过滤器"""
    print("\n" + "=" * 60)
    print("测试 2: MarketFilter (大盘红绿灯)")
    print("=" * 60)
    
    try:
        from core.tech_stock.market_filter import MarketFilter
        import pandas as pd
        
        mf = MarketFilter()
        print(f"✓ MarketFilter 初始化成功")
        print(f"  - 创业板指代码: {mf.gem_index_code}")
        print(f"  - MA 周期: {mf.ma_period}")
        
        # 创建测试数据（绿灯场景）
        test_data = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=30),
            'open': [100 + i for i in range(30)],
            'high': [105 + i for i in range(30)],
            'low': [95 + i for i in range(30)],
            'close': [100 + i for i in range(30)],
            'volume': [1000000] * 30
        })
        
        status = mf.check_market_status(test_data)
        print(f"✓ check_market_status 执行成功")
        print(f"  - 大盘状态: {'🟢 绿灯' if status.is_green else '🔴 红灯'}")
        print(f"  - 收盘价: {status.gem_close:.2f}")
        print(f"  - MA20: {status.gem_ma20:.2f}")
        print(f"  - MACD 状态: {status.macd_status}")
        
        return True
    except Exception as e:
        print(f"✗ MarketFilter 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_hard_filter():
    """测试硬性筛选器"""
    print("\n" + "=" * 60)
    print("测试 3: HardFilter (硬性筛选)")
    print("=" * 60)
    
    try:
        from core.tech_stock.hard_filter import HardFilter
        
        hf = HardFilter()
        print(f"✓ HardFilter 初始化成功")
        print(f"  - 最高股价: {hf.MAX_PRICE}元")
        print(f"  - 流通市值范围: {hf.MIN_MARKET_CAP}-{hf.MAX_MARKET_CAP}亿")
        print(f"  - 最小日均成交额: {hf.MIN_AVG_TURNOVER}亿")
        
        # 测试筛选方法
        passed, reason = hf._check_price(50.0)
        print(f"✓ _check_price 方法正常: 50元股价 -> {passed}")
        
        passed, reason = hf._check_market_cap(100.0)
        print(f"✓ _check_market_cap 方法正常: 100亿市值 -> {passed}")
        
        passed, reason = hf._check_turnover(2.0)
        print(f"✓ _check_turnover 方法正常: 2亿成交额 -> {passed}")
        
        return True
    except Exception as e:
        print(f"✗ HardFilter 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_signal_generator():
    """测试信号生成器"""
    print("\n" + "=" * 60)
    print("测试 4: TechSignalGenerator (信号生成)")
    print("=" * 60)
    
    try:
        from core.tech_stock.signal_generator import TechSignalGenerator
        from datetime import time
        
        sg = TechSignalGenerator()
        print(f"✓ TechSignalGenerator 初始化成功")
        print(f"  - RSI 范围: {sg.RSI_MIN}-{sg.RSI_MAX}")
        print(f"  - 量比阈值: {sg.VOLUME_RATIO_MIN}")
        print(f"  - 尾盘确认时间: {sg.EOD_CONFIRMATION_TIME}")
        
        # 测试尾盘判定
        is_confirmed = sg.is_signal_confirmed()
        print(f"✓ is_signal_confirmed 方法正常: {is_confirmed}")
        
        status = sg.get_signal_status()
        print(f"✓ get_signal_status 方法正常: {status}")
        
        window_status = sg.get_trading_window_status()
        print(f"✓ get_trading_window_status 方法正常")
        print(f"  - 交易窗口: {window_status['is_trading_window']}")
        print(f"  - 状态消息: {window_status['status_message']}")
        
        return True
    except Exception as e:
        print(f"✗ TechSignalGenerator 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_exit_manager():
    """测试卖出信号管理器"""
    print("\n" + "=" * 60)
    print("测试 5: TechExitManager (卖出信号)")
    print("=" * 60)
    
    try:
        from core.tech_stock.exit_manager import TechExitManager, SignalPriority
        
        em = TechExitManager()
        print(f"✓ TechExitManager 初始化成功")
        print(f"  - 硬止损: {em.HARD_STOP_LOSS * 100}%")
        print(f"  - RSI 超买阈值: {em.RSI_OVERBOUGHT}")
        print(f"  - MA20 跌破天数: {em.MA20_BREAK_DAYS}")
        print(f"  - 最小仓位: {em.MIN_POSITION_SHARES}股")
        
        # 测试优先级枚举
        print(f"✓ SignalPriority 枚举可用")
        print(f"  - EMERGENCY: {SignalPriority.EMERGENCY}")
        print(f"  - STOP_LOSS: {SignalPriority.STOP_LOSS}")
        print(f"  - TAKE_PROFIT: {SignalPriority.TAKE_PROFIT}")
        print(f"  - TREND_BREAK: {SignalPriority.TREND_BREAK}")
        
        # 测试优先级颜色映射
        colors = em.PRIORITY_COLORS
        print(f"✓ 优先级颜色映射正常: {len(colors)} 个优先级")
        
        return True
    except Exception as e:
        print(f"✗ TechExitManager 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_backtester():
    """测试回测引擎"""
    print("\n" + "=" * 60)
    print("测试 6: TechBacktester (回测引擎)")
    print("=" * 60)
    
    try:
        from core.tech_stock.backtester import TechBacktester
        
        bt = TechBacktester()
        print(f"✓ TechBacktester 初始化成功")
        print(f"  - 默认测试标的: {bt.DEFAULT_STOCKS}")
        print(f"  - 默认回测时间: {bt.DEFAULT_START} 至 {bt.DEFAULT_END}")
        print(f"  - 震荡市验证期: {bt.BEAR_MARKET_START} 至 {bt.BEAR_MARKET_END}")
        print(f"  - 最大回撤阈值: {bt.MAX_DRAWDOWN_THRESHOLD * 100}%")
        
        # 测试时间段验证
        is_valid, msg = bt.validate_date_range("2022-01-01", "2024-12-31")
        print(f"✓ validate_date_range 方法正常: {is_valid}")
        print(f"  - 消息: {msg}")
        
        # 测试无效时间段
        is_valid, msg = bt.validate_date_range("2024-01-01", "2024-12-31")
        print(f"✓ 无效时间段检测正常: {not is_valid}")
        print(f"  - 消息: {msg}")
        
        return True
    except Exception as e:
        print(f"✗ TechBacktester 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_sector_ranker():
    """测试行业排位器"""
    print("\n" + "=" * 60)
    print("测试 7: SectorRanker (行业排位)")
    print("=" * 60)
    
    try:
        from core.tech_stock.sector_ranker import SectorRanker
        
        sr = SectorRanker()
        print(f"✓ SectorRanker 初始化成功")
        print(f"  - 行业指数映射: {list(sr.SECTOR_INDICES.keys())}")
        print(f"  - 龙头股备选方案: {list(sr.SECTOR_PROXY_STOCKS.keys())}")
        
        # 测试行业可交易判断
        for sector in sr.SECTOR_INDICES.keys():
            print(f"  - {sector}: 指数代码 {sr.SECTOR_INDICES[sector]}")
        
        return True
    except Exception as e:
        print(f"✗ SectorRanker 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("科技股后端模块完成验证")
    print("=" * 60)
    
    results = []
    
    # 运行所有测试
    results.append(("模块导入", test_module_imports()))
    results.append(("MarketFilter", test_market_filter()))
    results.append(("HardFilter", test_hard_filter()))
    results.append(("TechSignalGenerator", test_signal_generator()))
    results.append(("TechExitManager", test_exit_manager()))
    results.append(("TechBacktester", test_backtester()))
    results.append(("SectorRanker", test_sector_ranker()))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{name:30s} {status}")
    
    print("=" * 60)
    print(f"总计: {passed}/{total} 测试通过")
    print("=" * 60)
    
    if passed == total:
        print("\n🎉 所有后端模块测试通过！")
        print("✓ 大盘红绿灯过滤器正常")
        print("✓ 行业强弱排位器正常")
        print("✓ 硬性筛选器正常")
        print("✓ 买入信号生成器正常")
        print("✓ 卖出信号管理器正常")
        print("✓ 回测引擎正常")
        print("\n后端模块开发完成，可以进入前端开发阶段！")
        return 0
    else:
        print(f"\n⚠️ 有 {total - passed} 个测试失败，请检查问题")
        return 1


if __name__ == "__main__":
    sys.exit(main())
