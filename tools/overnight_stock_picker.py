#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
隔夜选股命令行工具 (Overnight Stock Picker CLI)

T日选股，T+1执行的隔夜短线选股系统命令行入口。
每天收盘后(15:00后)运行，基于当日完整日线数据，
筛选出明天可以买入的股票，并给出具体的买入价格、仓位和止损止盈建议。

使用方法:
    # 基本使用 (使用默认参数)
    python tools/overnight_stock_picker.py

    # 指定资金和热点
    python tools/overnight_stock_picker.py --capital 100000 --topics "AI眼镜,半导体"

    # 指定输出文件
    python tools/overnight_stock_picker.py --output my_plan.md

    # 查看历史计划
    python tools/overnight_stock_picker.py --history

    # 刷新数据后选股
    python tools/overnight_stock_picker.py --refresh

Requirements: 1.1, 7.5
"""

import argparse
import sys
import os
from datetime import datetime, date, timedelta
from typing import List, Optional

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.overnight_picker import (
    OvernightStockPicker,
    TradingPlan,
    create_overnight_picker,
    TradingPlanGenerator,
)


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='隔夜选股系统 - T日选股，T+1执行',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                          # 使用默认参数运行选股
  %(prog)s --capital 100000         # 指定10万资金
  %(prog)s --topics "AI,半导体"     # 指定当前热点
  %(prog)s --output plan.md         # 输出到指定文件
  %(prog)s --history                # 查看历史计划
  %(prog)s --refresh                # 刷新数据后选股
  %(prog)s --quiet                  # 静默模式，只输出结果
  %(prog)s --tech-pool              # 使用100只科技股池
  %(prog)s --tech-pool --sector "半导体,人工智能"  # 只选半导体和AI股票
        """
    )
    
    # 基本参数
    parser.add_argument(
        '--capital', '-c',
        type=float,
        default=70000,
        help='总资金金额 (默认: 70000元)'
    )
    
    parser.add_argument(
        '--topics', '-t',
        type=str,
        default='',
        help='当前热点题材，用逗号分隔 (如: "AI眼镜,半导体,CES概念")'
    )
    

    
    parser.add_argument(
        '--max-stocks', '-m',
        type=int,
        default=15,
        help='最多推荐股票数量 (默认: 15)'
    )
    
    parser.add_argument(
        '--min-score', '-s',
        type=float,
        default=70,
        help='最低评分阈值 (默认: 70)'
    )
    
    # 输出参数
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='',
        help='输出Markdown文件路径 (默认: data/trading_plans/trading_plan_YYYYMMDD.md)'
    )
    
    parser.add_argument(
        '--no-save',
        action='store_true',
        help='不保存交易计划到历史记录'
    )
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='静默模式，只输出交易计划'
    )
    
    parser.add_argument(
        '--json',
        action='store_true',
        help='以JSON格式输出'
    )
    
    # 数据参数
    parser.add_argument(
        '--refresh', '-r',
        action='store_true',
        help='运行前刷新股票数据'
    )
    
    parser.add_argument(
        '--data-path',
        type=str,
        default='data/processed',
        help='数据文件路径 (默认: data/processed)'
    )
    
    parser.add_argument(
        '--tech-pool',
        action='store_true',
        help='使用科技股池(100只科技股)作为数据源'
    )
    
    parser.add_argument(
        '--sector',
        type=str,
        default='',
        help='指定科技股行业筛选 (如: "半导体,人工智能")，需配合 --tech-pool 使用'
    )
    
    # 市场情绪参数
    parser.add_argument(
        '--limit-up',
        type=int,
        default=50,
        help='涨停家数 (用于情绪分析，默认: 50)'
    )
    
    parser.add_argument(
        '--limit-down',
        type=int,
        default=10,
        help='跌停家数 (用于情绪分析，默认: 10)'
    )
    
    parser.add_argument(
        '--broken-rate',
        type=float,
        default=0.15,
        help='炸板率 (用于情绪分析，默认: 0.15)'
    )
    
    # 其他功能
    parser.add_argument(
        '--history',
        action='store_true',
        help='查看历史交易计划列表'
    )
    
    parser.add_argument(
        '--load-date',
        type=str,
        default='',
        help='加载指定日期的历史计划 (格式: YYYY-MM-DD)'
    )
    
    parser.add_argument(
        '--check-data',
        action='store_true',
        help='检查数据状态'
    )
    
    return parser.parse_args()


def print_header(quiet: bool = False):
    """打印程序头部信息"""
    if quiet:
        return
    
    print("=" * 60)
    print("📈 隔夜选股系统 v5.0")
    print("   T日选股，T+1执行")
    print("=" * 60)
    print()


def print_section(title: str, quiet: bool = False):
    """打印分节标题"""
    if quiet:
        return
    print(f"\n{'─' * 40}")
    print(f"  {title}")
    print(f"{'─' * 40}")


def run_stock_picker(args) -> Optional[TradingPlan]:
    """
    运行选股流程
    
    Args:
        args: 命令行参数
    
    Returns:
        TradingPlan 或 None
    """
    quiet = args.quiet
    
    # 解析热点题材（仅支持手动指定）
    hot_topics = []
    if args.topics:
        hot_topics = [t.strip() for t in args.topics.split(',') if t.strip()]
    
    # 获取股票池
    stock_pool = None
    pool_name = "默认股票池"
    
    if args.tech_pool:
        # 使用科技股池
        try:
            from config.tech_stock_pool import TechStockPool
            tech_pool = TechStockPool()
            
            if args.sector:
                # 按行业筛选
                sectors = [s.strip() for s in args.sector.split(',') if s.strip()]
                stock_pool = []
                for sector in sectors:
                    codes = tech_pool.get_codes_by_sector(sector)
                    stock_pool.extend(codes)
                pool_name = f"科技股池({', '.join(sectors)})"
            else:
                # 使用全部科技股
                stock_pool = tech_pool.get_all_codes()
                pool_name = f"科技股池(全部{len(stock_pool)}只)"
            
            if not quiet:
                print(f"🔬 使用{pool_name}")
                print(f"   行业分布:")
                for sector in tech_pool.get_sectors():
                    count = tech_pool.get_sector_count(sector)
                    if count > 0:
                        print(f"     - {sector}: {count}只")
                print()
        except ImportError as e:
            print(f"❌ 无法加载科技股池: {e}")
            return None
    
    if not quiet:
        print(f"📊 参数配置:")
        print(f"   - 总资金: {args.capital:,.0f}元")
        print(f"   - 最多推荐: {args.max_stocks}只")
        print(f"   - 最低评分: {args.min_score}分")
        print(f"   - 股票池: {pool_name}")
        if hot_topics:
            print(f"   - 当前热点: {', '.join(hot_topics)}")
        print()
    
    # 创建选股器
    picker = OvernightStockPicker(
        total_capital=args.capital,
        max_recommendations=args.max_stocks,
        min_score=args.min_score,
        data_path=args.data_path,
        stock_pool=stock_pool,
    )
    
    # 刷新数据
    if args.refresh:
        print_section("刷新股票数据", quiet)
        if not quiet:
            print("正在刷新数据，请稍候...")
        results = picker.refresh_stock_data()
        success_count = sum(1 for v in results.values() if v)
        if not quiet:
            print(f"数据刷新完成: 成功 {success_count}/{len(results)}")
    
    # 运行选股
    print_section("运行选股流程", quiet)
    
    plan = picker.run(
        hot_topics=hot_topics,
        limit_up_count=args.limit_up,
        limit_down_count=args.limit_down,
        broken_board_rate=args.broken_rate,
        save_plan=not args.no_save,
    )
    
    return plan


def output_plan(plan: TradingPlan, args):
    """
    输出交易计划
    
    Args:
        plan: 交易计划
        args: 命令行参数
    """
    quiet = args.quiet
    
    if args.json:
        # JSON格式输出
        import json
        print(json.dumps(plan.to_dict(), ensure_ascii=False, indent=2))
        return
    
    # Markdown格式输出
    md_content = plan.to_markdown()
    
    # 输出到控制台
    print_section("交易计划", quiet)
    print(md_content)
    
    # 输出到文件
    if args.output:
        output_path = args.output
    else:
        # 默认输出路径
        date_str = plan.date.replace('-', '')
        output_path = f"data/trading_plans/trading_plan_{date_str}.md"
    
    # 确保目录存在
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(md_content)
    
    if not quiet:
        print(f"\n✅ 交易计划已保存到: {output_path}")


def show_history(args):
    """显示历史交易计划列表"""
    generator = TradingPlanGenerator()
    plans = generator.list_history_plans(limit=30)
    
    if not plans:
        print("📭 暂无历史交易计划")
        return
    
    print("📋 历史交易计划列表:")
    print()
    print(f"{'日期':<12} {'文件路径'}")
    print("-" * 60)
    
    for p in plans:
        print(f"{p['date']:<12} {p['md_path']}")
    
    print()
    print(f"共 {len(plans)} 条记录")
    print("使用 --load-date YYYY-MM-DD 查看具体计划")


def load_history_plan(date_str: str, args):
    """加载并显示历史计划"""
    generator = TradingPlanGenerator()
    plan = generator.load_plan(date_str)
    
    if plan is None:
        print(f"❌ 未找到 {date_str} 的交易计划")
        return
    
    if args.json:
        import json
        print(json.dumps(plan.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(plan.to_markdown())


def check_data_status(args):
    """检查数据状态"""
    # 获取股票池
    stock_pool = None
    pool_name = "默认股票池"
    
    if args.tech_pool:
        try:
            from config.tech_stock_pool import TechStockPool
            tech_pool = TechStockPool()
            
            if args.sector:
                sectors = [s.strip() for s in args.sector.split(',') if s.strip()]
                stock_pool = []
                for sector in sectors:
                    codes = tech_pool.get_codes_by_sector(sector)
                    stock_pool.extend(codes)
                pool_name = f"科技股池({', '.join(sectors)})"
            else:
                stock_pool = tech_pool.get_all_codes()
                pool_name = f"科技股池(全部{len(stock_pool)}只)"
        except ImportError as e:
            print(f"❌ 无法加载科技股池: {e}")
            return
    
    picker = OvernightStockPicker(
        total_capital=args.capital,
        data_path=args.data_path,
        stock_pool=stock_pool,
    )
    
    # 如果需要刷新数据
    if args.refresh:
        print("🔄 正在刷新股票数据...")
        print(f"   股票池: {pool_name}")
        print()
        results = picker.refresh_stock_data()
        success_count = sum(1 for v in results.values() if v)
        print(f"✅ 数据刷新完成: 成功 {success_count}/{len(results)}")
        print()
    
    print("📊 数据状态检查")
    print(f"   股票池: {pool_name}")
    print()
    
    # 检查数据新鲜度
    fresh, stale = picker.check_data_freshness(max_days=3)
    
    print(f"股票池总数: {len(picker.stock_pool)}")
    print(f"数据新鲜: {len(fresh)} 只")
    print(f"数据过期: {len(stale)} 只")
    print()
    
    if stale:
        print("过期股票 (最近3天无数据):")
        for code in stale[:20]:
            print(f"  - {code}")
        if len(stale) > 20:
            print(f"  ... 还有 {len(stale) - 20} 只")
        print()
        if not args.refresh:
            print("建议使用 --refresh 参数刷新数据")


def print_summary(plan: TradingPlan, quiet: bool = False):
    """打印选股摘要"""
    if quiet:
        return
    
    print()
    print("=" * 60)
    print("📊 选股摘要")
    print("=" * 60)
    print(f"计划日期: {plan.date}")
    print(f"大盘环境: {plan.market_env}")
    print(f"市场情绪: {plan.market_sentiment} ({plan.sentiment_phase})")
    print(f"推荐股票: {len(plan.recommendations)} 只")
    print(f"建议总仓位: {plan.total_position * 100:.0f}%")
    
    if plan.recommendations:
        print()
        print("推荐列表:")
        for i, rec in enumerate(plan.recommendations, 1):
            print(f"  {i}. {rec.name}({rec.code}) "
                  f"评分:{rec.total_score:.0f} "
                  f"买入:{rec.ideal_price:.2f}-{rec.acceptable_price:.2f} "
                  f"仓位:{rec.position_ratio*100:.0f}%")
    else:
        print()
        print("⚠️ 今日无推荐股票，建议观望")
    
    print()


def main():
    """主函数"""
    args = parse_args()
    
    # 打印头部
    print_header(args.quiet)
    
    try:
        # 查看历史计划
        if args.history:
            show_history(args)
            return 0
        
        # 加载历史计划
        if args.load_date:
            load_history_plan(args.load_date, args)
            return 0
        
        # 检查数据状态
        if args.check_data:
            check_data_status(args)
            return 0
        
        # 运行选股
        plan = run_stock_picker(args)
        
        if plan is None:
            print("❌ 选股失败")
            return 1
        
        # 输出计划
        output_plan(plan, args)
        
        # 打印摘要
        print_summary(plan, args.quiet)
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断")
        return 130
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
