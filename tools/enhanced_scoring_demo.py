"""
增强版短线评分系统演示工具

演示8维度评分系统的完整功能:
1. 热点题材智能识别
2. 市场情绪分析
3. 大盘环境分析
4. 综合评分与交易建议
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.short_term import (
    # 热点管理
    get_hot_topic_manager,
    # 情绪分析
    MarketSentimentAnalyzer,
    MarketSentimentData,
    quick_sentiment_check,
    # 大盘分析
    IndexEnvironmentAnalyzer,
    IndexData,
    quick_index_check,
    # 增强评分
    create_enhanced_scorer
)


def print_separator(title: str = ""):
    """打印分隔线"""
    print("\n" + "=" * 60)
    if title:
        print(f"  {title}")
        print("=" * 60)


def demo_hot_topic_manager():
    """演示热点题材管理器"""
    print_separator("📌 热点题材智能管理器")
    
    manager = get_hot_topic_manager()
    manager.print_status()
    
    # 测试股票热点匹配
    print("\n🔍 股票热点匹配测试:")
    
    test_stocks = [
        ("歌尔股份", "消费电子", ["AI眼镜", "VR", "CES"]),
        ("通富微电", "半导体", ["芯片封测", "AMD"]),
        ("国轩高科", "新能源科技", ["锂电池", "储能"]),
        ("中兴通讯", "5G通信", ["通信设备", "5G"]),
    ]
    
    for name, sector, concepts in test_stocks:
        score, details = manager.calculate_hot_topic_score(name, sector, concepts)
        print(f"\n   {name} ({sector})")
        print(f"   热点得分: {score}/20分")
        print(f"   匹配热点: {details['topic_count']}个")
        print(f"   分类: {details['category']}")
        if details['matched_topics']:
            topics = [t['name'] for t in details['matched_topics']]
            print(f"   匹配: {', '.join(topics)}")


def demo_market_sentiment():
    """演示市场情绪分析"""
    print_separator("📊 市场情绪分析器")
    
    # 模拟今日市场数据
    analyzer = MarketSentimentAnalyzer()
    
    data = MarketSentimentData(
        limit_up_count=85,          # 涨停85家
        limit_down_count=12,        # 跌停12家
        failed_limit_up=15,         # 炸板15家
        up_count=3200,              # 上涨3200家
        down_count=1800,            # 下跌1800家
        flat_count=200,             # 平盘200家
        highest_board=6,            # 最高6连板
        continuous_limit_up={2: 25, 3: 12, 4: 5, 5: 2, 6: 1}  # 连板统计
    )
    
    analyzer.update_data(data)
    analyzer.print_status()
    
    # 快速情绪检查
    print("\n⚡ 快速情绪检查:")
    result = quick_sentiment_check(
        limit_up=85, limit_down=12,
        up_count=3200, down_count=1800,
        failed_limit_up=15, highest_board=6
    )
    print(f"   情绪指数: {result['sentiment_index']}")
    print(f"   情绪等级: {result['sentiment_level']}")
    print(f"   仓位建议: {result['position_suggestion']}")


def demo_index_analyzer():
    """演示大盘环境分析"""
    print_separator("📈 大盘环境分析器")
    
    analyzer = IndexEnvironmentAnalyzer()
    
    # 模拟上证指数数据
    shanghai = IndexData(
        code="000001",
        name="上证指数",
        price=3250.50,
        change_pct=0.85,
        ma5=3230.20,
        ma10=3210.50,
        ma20=3180.30,
        ma60=3150.00,
        volume_ratio=1.35,
        recent_changes=[0.5, 0.3, -0.2, 0.8, 0.85]
    )
    
    # 模拟创业板指数据
    chinext = IndexData(
        code="399006",
        name="创业板指",
        price=2050.80,
        change_pct=1.25,
        ma5=2020.50,
        ma10=1990.30,
        ma20=1960.00,
        ma60=1920.00,
        volume_ratio=1.5,
        recent_changes=[0.8, 0.5, 0.2, 1.0, 1.25]
    )
    
    analyzer.update_index_data(shanghai, chinext)
    analyzer.print_status()
    
    # 快速大盘检查
    print("\n⚡ 快速大盘检查:")
    result = quick_index_check(
        sh_price=3250.50, sh_change=0.85,
        sh_ma5=3230.20, sh_ma10=3210.50, sh_ma20=3180.30, sh_ma60=3150.00,
        cy_price=2050.80, cy_change=1.25,
        cy_ma5=2020.50, cy_ma10=1990.30, cy_ma20=1960.00, cy_ma60=1920.00
    )
    print(f"   市场环境: {result['environment']}")
    print(f"   环境得分: {result['environment_score']}")
    print(f"   建议仓位: {result['suggested_position']}%")
    print(f"   策略: {result['strategy']}")


def demo_enhanced_scorer():
    """演示增强版评分系统"""
    print_separator("🎯 增强版8维度评分系统")
    
    # 创建评分系统
    scorer = create_enhanced_scorer()
    
    # 先更新市场数据
    # 1. 更新情绪数据
    sentiment_data = MarketSentimentData(
        limit_up_count=85,
        limit_down_count=12,
        failed_limit_up=15,
        up_count=3200,
        down_count=1800,
        highest_board=6
    )
    scorer.sentiment_analyzer.update_data(sentiment_data)
    
    # 2. 更新大盘数据
    shanghai = IndexData(
        code="000001", name="上证指数",
        price=3250.50, change_pct=0.85,
        ma5=3230.20, ma10=3210.50, ma20=3180.30, ma60=3150.00
    )
    chinext = IndexData(
        code="399006", name="创业板指",
        price=2050.80, change_pct=1.25,
        ma5=2020.50, ma10=1990.30, ma20=1960.00, ma60=1920.00
    )
    scorer.index_analyzer.update_index_data(shanghai, chinext)
    
    # 测试多只股票
    test_stocks = [
        {
            "code": "002241", "name": "歌尔股份", "sector": "消费电子",
            "price": 28.50, "change_pct": 4.5, "turnover_rate": 6.2, "volume_ratio": 2.5,
            "ma5": 27.80, "ma10": 27.00, "ma20": 26.50,
            "main_net_inflow": 8000, "large_order_ratio": 58,
            "sector_rank": 1, "stock_rank_in_sector": 1, "sector_stock_count": 20,
            "recent_changes": [2.5, 3.2, 1.8, 2.0, 4.5], "rsi": 65, "macd_status": "golden_cross",
            "concepts": ["CES", "AI眼镜", "VR", "消费电子"]
        },
        {
            "code": "002156", "name": "通富微电", "sector": "半导体",
            "price": 32.80, "change_pct": 2.8, "turnover_rate": 5.5, "volume_ratio": 2.0,
            "ma5": 32.00, "ma10": 31.50, "ma20": 30.80,
            "main_net_inflow": 5500, "large_order_ratio": 54,
            "sector_rank": 2, "stock_rank_in_sector": 3, "sector_stock_count": 25,
            "recent_changes": [1.5, 2.0, 0.8, 1.2, 2.8], "rsi": 55, "macd_status": "golden_cross",
            "concepts": ["半导体", "芯片封测", "AMD"]
        },
        {
            "code": "002074", "name": "国轩高科", "sector": "新能源科技",
            "price": 40.30, "change_pct": 3.2, "turnover_rate": 4.5, "volume_ratio": 1.8,
            "ma5": 39.50, "ma10": 38.80, "ma20": 37.50,
            "main_net_inflow": 2500, "large_order_ratio": 55,
            "sector_rank": 6, "stock_rank_in_sector": 2, "sector_stock_count": 15,
            "recent_changes": [1.2, 2.1, -0.5, 1.8, 3.2], "rsi": 58, "macd_status": "golden_cross",
            "concepts": ["新能源", "锂电池", "储能"]
        },
        {
            "code": "002185", "name": "华天科技", "sector": "半导体",
            "price": 12.50, "change_pct": -1.2, "turnover_rate": 3.8, "volume_ratio": 1.5,
            "ma5": 12.80, "ma10": 13.00, "ma20": 13.20,
            "main_net_inflow": -3200, "large_order_ratio": 42,
            "sector_rank": 2, "stock_rank_in_sector": 8, "sector_stock_count": 25,
            "recent_changes": [-0.5, 1.2, -1.8, 0.3, -1.2], "rsi": 42, "macd_status": "death_cross",
            "concepts": ["半导体", "芯片封测"]
        }
    ]
    
    results = []
    for stock in test_stocks:
        result = scorer.calculate_comprehensive_score(
            stock_code=stock["code"],
            stock_name=stock["name"],
            sector=stock["sector"],
            price=stock["price"],
            change_pct=stock["change_pct"],
            turnover_rate=stock["turnover_rate"],
            volume_ratio=stock["volume_ratio"],
            ma5=stock["ma5"],
            ma10=stock["ma10"],
            ma20=stock["ma20"],
            main_net_inflow=stock["main_net_inflow"],
            large_order_ratio=stock["large_order_ratio"],
            sector_rank=stock["sector_rank"],
            stock_rank_in_sector=stock["stock_rank_in_sector"],
            sector_stock_count=stock["sector_stock_count"],
            recent_changes=stock["recent_changes"],
            rsi=stock["rsi"],
            macd_status=stock["macd_status"],
            concepts=stock["concepts"]
        )
        results.append(result)
    
    # 按调整后得分排序
    results.sort(key=lambda x: x['adjusted_score'], reverse=True)
    
    # 打印排名
    print("\n🏆 股票排名 (8维度综合评分):\n")
    print(f"{'排名':<4} {'股票':<12} {'基础分':<8} {'调整分':<8} {'等级':<16} {'信号'}")
    print("-" * 80)
    
    for i, r in enumerate(results, 1):
        signal = r['trading_signal']
        print(f"{i:<4} {r['stock_name']:<10} {r['base_score']:<8} {r['adjusted_score']:<8} {r['quality_grade']:<14} {signal['signal']}")
    
    # 打印详细得分
    print("\n📊 8维度得分明细:\n")
    print(f"{'股票':<12} {'热点':<6} {'资金':<6} {'趋势':<6} {'动量':<6} {'成交':<6} {'板块':<6} {'情绪':<6} {'大盘':<6}")
    print("-" * 70)
    
    for r in results:
        s = r['scores']
        print(f"{r['stock_name']:<10} {s['hot_topic']:<6} {s['capital_flow']:<6} {s['trend']:<6} {s['momentum']:<6} {s['volume']:<6} {s['sector']:<6} {s['sentiment']:<6} {s['index_env']:<6}")
    
    # 打印第一名详细信息
    print_separator(f"🥇 第一名详细分析: {results[0]['stock_name']}")
    
    top = results[0]
    print(f"\n📈 股票: {top['stock_name']} ({top['stock_code']})")
    print(f"📊 板块: {top['sector']}")
    print(f"\n🏆 基础得分: {top['base_score']}分")
    print(f"🎯 调整得分: {top['adjusted_score']}分 (环境系数: {top['env_multiplier']})")
    print(f"⭐ 质量等级: {top['quality_grade']}")
    
    print("\n💡 交易信号:")
    signal = top['trading_signal']
    print(f"   信号: {signal['signal']}")
    print(f"   建议: {signal['action']}")
    
    if signal['buy_conditions']:
        print(f"   买入理由: {', '.join(signal['buy_conditions'])}")
    if signal['sell_conditions']:
        print(f"   风险提示: {', '.join(signal['sell_conditions'])}")
    
    if top['risk_warnings']:
        print("\n⚠️ 风险预警:")
        for warning in top['risk_warnings']:
            print(f"   {warning}")


def main():
    """主函数"""
    print("\n" + "🚀" * 20)
    print("     增强版短线评分系统 v4.0 演示")
    print("     8维度评分 + 智能热点 + 情绪分析 + 大盘环境")
    print("🚀" * 20)
    
    # 1. 热点题材管理器
    demo_hot_topic_manager()
    
    # 2. 市场情绪分析
    demo_market_sentiment()
    
    # 3. 大盘环境分析
    demo_index_analyzer()
    
    # 4. 增强版评分系统
    demo_enhanced_scorer()
    
    print_separator("✅ 演示完成")
    print("\n💡 增强版系统改进:")
    print("   1. ✅ 热点题材智能管理 - 自动识别和更新热点")
    print("   2. ✅ 市场情绪分析 - 涨跌停、炸板率、赚钱效应")
    print("   3. ✅ 大盘环境分析 - 上证/创业板趋势判断")
    print("   4. ✅ 8维度综合评分 - 新增情绪和大盘维度")
    print("   5. ✅ 动态调整系数 - 根据市场环境调整评分")
    print("   6. ✅ 风险预警系统 - 极端情况自动预警")


if __name__ == "__main__":
    main()
