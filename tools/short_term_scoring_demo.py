"""
短线散户评分系统演示工具

演示新开发的短线专用评分系统的使用方法
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.short_term_scoring_system import (
    ShortTermScoringSystem,
    TimingAdvisor,
    create_short_term_scorer,
    quick_score,
    CURRENT_HOT_TOPICS,
    SECTOR_HEAT_RANKING
)


def print_separator(title: str = ""):
    """打印分隔线"""
    print("\n" + "=" * 60)
    if title:
        print(f"  {title}")
        print("=" * 60)


def demo_hot_topics():
    """演示当前热点题材配置"""
    print_separator("📌 当前热点题材配置 (2026年1月)")
    
    for topic in CURRENT_HOT_TOPICS:
        print(f"\n🔥 {topic.name}")
        print(f"   权重加成: {topic.weight}x")
        print(f"   关键词: {', '.join(topic.keywords)}")
        print(f"   有效期: {topic.start_date} ~ {topic.end_date or '持续'}")
        print(f"   说明: {topic.description}")


def demo_sector_heat():
    """演示板块热度排名"""
    print_separator("📊 板块热度排名")
    
    sorted_sectors = sorted(SECTOR_HEAT_RANKING.items(), key=lambda x: x[1], reverse=True)
    for i, (sector, heat) in enumerate(sorted_sectors, 1):
        bar = "█" * (heat // 10) + "░" * (10 - heat // 10)
        print(f"  {i}. {sector:12} {bar} {heat}分")


def demo_single_stock_scoring():
    """演示单只股票评分"""
    print_separator("🎯 单只股票评分演示 - 国轩高科 (002074)")
    
    # 创建评分系统
    scorer = create_short_term_scorer("balanced")
    
    # 模拟国轩高科的数据 (基于之前分析的数据)
    result = scorer.calculate_comprehensive_score(
        stock_code="002074",
        stock_name="国轩高科",
        sector="新能源科技",
        price=40.30,
        change_pct=3.2,
        turnover_rate=4.5,
        volume_ratio=1.8,
        ma5=39.50,
        ma10=38.80,
        ma20=37.50,
        main_net_inflow=2500,  # 主力净流入2500万
        large_order_ratio=55,   # 大单买入占比55%
        sector_rank=6,          # 板块排名第6
        stock_rank_in_sector=2, # 板块内排名第2
        sector_stock_count=15,
        sector_change=1.5,
        recent_changes=[1.2, 2.1, -0.5, 1.8, 3.2],  # 近5日涨跌
        rsi=58,
        macd_status="golden_cross",
        concepts=["新能源", "锂电池", "储能"]
    )
    
    # 打印结果
    print(f"\n📈 股票: {result['stock_name']} ({result['stock_code']})")
    print(f"📊 板块: {result['sector']}")
    print(f"\n🏆 综合得分: {result['comprehensive_score']}分")
    print(f"⭐ 质量等级: {result['quality_grade']}")
    
    print("\n📋 各维度得分:")
    scores = result['scores']
    print(f"   热点题材: {scores['hot_topic']}/25分")
    print(f"   资金流向: {scores['capital_flow']}/20分")
    print(f"   趋势强度: {scores['trend']}/20分")
    print(f"   动量得分: {scores['momentum']}/15分")
    print(f"   成交量: {scores['volume']}/10分")
    print(f"   板块地位: {scores['sector']}/10分")
    
    print("\n🔍 详细分析:")
    details = result['details']
    print(f"   热点: {details['hot_topic']['category']}, 匹配{details['hot_topic']['topic_count']}个热点")
    print(f"   资金: {details['capital_flow']['category']}, 净流入{details['capital_flow']['main_net_inflow']}万")
    print(f"   趋势: {details['trend']['ma_status']}, {details['trend']['trend_status']}")
    print(f"   动量: {details['momentum']['change_status']}, 换手{details['momentum']['turnover_rate']}%")
    
    print("\n💡 交易信号:")
    signal = result['trading_signal']
    print(f"   信号: {signal['signal']}")
    print(f"   建议: {signal['action']}")
    print(f"   置信度: {signal['confidence']}")
    
    if signal['buy_conditions']:
        print(f"   买入理由: {', '.join(signal['buy_conditions'])}")
    if signal['sell_conditions']:
        print(f"   风险提示: {', '.join(signal['sell_conditions'])}")
    
    return result


def demo_timing_advisor(score_result: dict):
    """演示买卖时机顾问"""
    print_separator("⏰ 买卖时机顾问")
    
    # 创建时机顾问 (稳健型，适合新手)
    advisor = TimingAdvisor(risk_tolerance="moderate")
    
    # 获取入场建议
    entry_advice = advisor.get_entry_advice(
        current_price=40.30,
        score_result=score_result,
        support_level=38.50,
        resistance_level=43.00
    )
    
    print("\n📥 入场建议:")
    print(f"   建议: {entry_advice['recommendation']}")
    if entry_advice['recommendation'] == "建议买入":
        print(f"   时机: {entry_advice['entry_timing']}")
        print(f"   当前价: {entry_advice['current_price']}元")
        print(f"   止损价: {entry_advice['stop_loss_price']}元 ({entry_advice['stop_loss_pct']})")
        print(f"   止盈价: {entry_advice['take_profit_price']}元 ({entry_advice['take_profit_pct']})")
        print(f"   风险收益比: 1:{entry_advice['risk_reward_ratio']}")
        print(f"   建议仓位: {entry_advice['position_pct']}% ({entry_advice['position_advice']})")
        
        print("\n   📌 关键要点:")
        for point in entry_advice['key_points']:
            print(f"      • {point}")


def demo_compare_stocks():
    """演示多只股票对比"""
    print_separator("📊 多只股票对比评分")
    
    scorer = create_short_term_scorer("balanced")
    
    # 模拟多只股票数据
    stocks_data = [
        {
            "code": "002074", "name": "国轩高科", "sector": "新能源科技",
            "price": 40.30, "change_pct": 3.2, "turnover_rate": 4.5, "volume_ratio": 1.8,
            "ma5": 39.50, "ma10": 38.80, "ma20": 37.50,
            "main_net_inflow": 2500, "large_order_ratio": 55,
            "sector_rank": 6, "stock_rank_in_sector": 2, "sector_stock_count": 15,
            "recent_changes": [1.2, 2.1, -0.5, 1.8, 3.2], "rsi": 58, "macd_status": "golden_cross",
            "concepts": ["新能源", "锂电池"]
        },
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
    for stock in stocks_data:
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
    
    # 按综合得分排序
    results.sort(key=lambda x: x['comprehensive_score'], reverse=True)
    
    print("\n🏆 股票排名 (按综合得分):\n")
    print(f"{'排名':<4} {'股票':<12} {'得分':<8} {'等级':<16} {'信号':<12} {'建议'}")
    print("-" * 80)
    
    for i, r in enumerate(results, 1):
        signal = r['trading_signal']
        print(f"{i:<4} {r['stock_name']:<10} {r['comprehensive_score']:<8} {r['quality_grade']:<14} {signal['signal']:<10} {signal['action']}")
    
    print("\n📊 各维度得分对比:\n")
    print(f"{'股票':<12} {'热点':<8} {'资金':<8} {'趋势':<8} {'动量':<8} {'成交量':<8} {'板块':<8}")
    print("-" * 70)
    
    for r in results:
        s = r['scores']
        print(f"{r['stock_name']:<10} {s['hot_topic']:<8} {s['capital_flow']:<8} {s['trend']:<8} {s['momentum']:<8} {s['volume']:<8} {s['sector']:<8}")


def demo_quick_score():
    """演示快速评分函数"""
    print_separator("⚡ 快速评分函数演示")
    
    # 使用快速评分函数
    stock_data = {
        'code': '002396',
        'name': '星网锐捷',
        'sector': '5G通信',
        'price': 35.20,
        'change_pct': 1.5,
        'turnover_rate': 3.2,
        'volume_ratio': 1.3,
        'ma5': 34.80,
        'ma10': 34.50,
        'ma20': 34.00,
        'main_net_inflow': 1200,
        'large_order_ratio': 52,
        'sector_rank': 5,
        'stock_rank_in_sector': 3,
        'sector_stock_count': 18,
        'recent_changes': [0.8, 1.2, -0.3, 0.5, 1.5],
        'rsi': 52,
        'macd_status': 'neutral',
        'concepts': ['5G', '通信设备', 'CPO']
    }
    
    result = quick_score(stock_data)
    
    print(f"\n股票: {result['stock_name']} ({result['stock_code']})")
    print(f"综合得分: {result['comprehensive_score']}分")
    print(f"质量等级: {result['quality_grade']}")
    print(f"交易信号: {result['trading_signal']['signal']}")
    print(f"操作建议: {result['trading_signal']['action']}")


def main():
    """主函数"""
    print("\n" + "🚀" * 20)
    print("     短线散户专用评分系统 v3.0 演示")
    print("🚀" * 20)
    
    # 1. 展示热点题材配置
    demo_hot_topics()
    
    # 2. 展示板块热度
    demo_sector_heat()
    
    # 3. 单只股票评分演示
    score_result = demo_single_stock_scoring()
    
    # 4. 买卖时机顾问演示
    demo_timing_advisor(score_result)
    
    # 5. 多只股票对比
    demo_compare_stocks()
    
    # 6. 快速评分演示
    demo_quick_score()
    
    print_separator("✅ 演示完成")
    print("\n💡 使用提示:")
    print("   1. 短线操作重点关注: 热点题材 > 资金流向 > 趋势强度")
    print("   2. 综合得分 ≥85分 才建议买入")
    print("   3. 严格执行止损，不要抱有侥幸心理")
    print("   4. 新手建议使用稳健型配置 (conservative)")
    print("   5. 每天开盘前更新热点题材配置")


if __name__ == "__main__":
    main()
