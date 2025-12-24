# -*- coding: utf-8 -*-
"""
科技股专属板块页面

提供科技股交易系统的完整界面，包括：
- 大盘红绿灯显示
- 行业强弱排名表
- 硬性筛选结果
- 尾盘交易窗口状态
- 买入信号列表
- 卖出信号和止损位显示
- 特殊持仓标记
- 回测功能入口

Requirements: 1.5, 2.6, 3.6, 4.3, 4.4, 4.5, 7.3, 8.2, 9.6, 10.1-10.4, 11.8, 13.1-13.7
"""

import streamlit as st
import sys
import os
from datetime import datetime, date, time
from typing import List, Dict, Optional, Any
import pandas as pd
import logging

logger = logging.getLogger(__name__)

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config.settings import get_settings
from config.tech_stock_pool import get_tech_stock_pool, TechStockPool
from config.tech_stock_config import (
    get_tech_config, 
    SECTOR_INDEX_MAPPING,
    PRIORITY_COLORS,
)
from core.data_feed import DataFeed
from core.tech_stock.market_filter import MarketFilter, MarketStatus
from core.tech_stock.sector_ranker import SectorRanker, SectorRank
from core.tech_stock.hard_filter import HardFilter, HardFilterResult
from core.tech_stock.signal_generator import TechSignalGenerator, TechBuySignal
from core.tech_stock.exit_manager import TechExitManager, TechExitSignal, SignalPriority
from core.tech_stock.backtester import TechBacktester, TechBacktestResult
from core.tech_stock.data_validator import TechDataValidator
from core.tech_stock.data_downloader import TechDataDownloader
from core.position_tracker import PositionTracker, Holding


def get_data_feed() -> DataFeed:
    """获取 DataFeed 实例"""
    settings = get_settings()
    return DataFeed(
        raw_path=settings.path.get_raw_path(),
        processed_path=settings.path.get_processed_path()
    )


# ==========================================
# 数据状态检查面板 (Requirements: 3.1, 3.2)
# ==========================================

def render_data_status_panel(data_feed: DataFeed, stock_pool):
    """
    渲染数据状态检查面板
    
    显示科技股池数据完整性状态，提供自动下载功能
    
    Requirements: 3.1, 3.2
    """
    st.subheader("📊 数据状态检查")
    
    # 初始化验证器
    validator = TechDataValidator(data_feed)
    
    # 检查数据状态
    with st.spinner("正在检查科技股数据状态..."):
        try:
            status = validator.get_tech_stock_pool_status()
        except Exception as e:
            st.error(f"检查数据状态失败: {e}")
            return
    
    # 显示总体状态
    overall = status["overall"]
    completion_rate = overall["completion_rate"]
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("总股票数", overall["total_stocks"])
    with col2:
        color = "normal" if completion_rate >= 0.8 else "inverse"
        st.metric("数据完整率", f"{completion_rate:.1%}", delta_color=color)
    with col3:
        st.metric("有效数据", overall["valid_stocks"])
    with col4:
        problem_count = overall["missing_files"] + overall["insufficient_data"] + overall["corrupted_files"]
        st.metric("问题数据", problem_count, delta_color="inverse" if problem_count > 0 else "normal")
    
    # 如果有问题数据，显示详细信息和解决方案
    if problem_count > 0:
        st.warning(f"⚠️ 发现 {problem_count} 只股票存在数据问题，可能影响回测功能")
        
        with st.expander("查看问题详情", expanded=True):
            problems = status["problem_stocks"]
            
            if problems["missing_files"]:
                st.markdown("**缺少数据文件的股票:**")
                missing_names = [
                    f"{code}({stock_pool.get_stock_name(code)})" 
                    for code in problems["missing_files"]
                ]
                st.markdown("• " + ", ".join(missing_names))
            
            if problems["insufficient_data"]:
                st.markdown("**数据时间范围不足的股票:**")
                for item in problems["insufficient_data"]:
                    st.markdown(f"• {item['code']}({item['name']}): {item['first_date']} ~ {item['last_date']}")
            
            if problems["corrupted_files"]:
                st.markdown("**数据文件损坏的股票:**")
                corrupted_names = [
                    f"{code}({stock_pool.get_stock_name(code)})" 
                    for code in problems["corrupted_files"]
                ]
                st.markdown("• " + ", ".join(corrupted_names))
        
        # 提供解决方案
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.info("""
            **建议解决方案:**
            1. 点击右侧"下载科技股数据"按钮自动获取所需数据
            2. 或者在"数据管理"页面手动管理股票数据
            3. 对于损坏的文件，系统会自动重新下载
            """)
        
        with col2:
            if st.button("🔄 下载科技股数据", type="primary", use_container_width=True):
                download_tech_stock_data(data_feed, stock_pool)
    
    else:
        st.success("✅ 所有科技股数据完整，可以正常进行回测")


def download_tech_stock_data(data_feed: DataFeed, stock_pool):
    """
    下载科技股数据
    
    Args:
        data_feed: 数据获取模块实例
        stock_pool: 科技股池实例
    """
    # 初始化下载器
    downloader = TechDataDownloader(data_feed)
    
    # 获取所有科技股代码
    all_codes = stock_pool.get_all_codes()
    
    st.info(f"开始下载 {len(all_codes)} 只科技股数据，请稍候...")
    
    # 创建进度条
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    def progress_callback(progress):
        """进度回调函数"""
        if progress.total_stocks > 0:
            completion = progress.completed_stocks / progress.total_stocks
            progress_bar.progress(completion)
            
            if progress.current_stock:
                status_text.text(f"正在下载: {progress.current_stock} ({progress.current_stock_name})")
            
            if progress.is_completed:
                status_text.text("下载完成!")
    
    try:
        # 执行下载
        result = downloader.download_tech_stock_pool(
            progress_callback=progress_callback,
            force_update=False  # 不强制更新已存在的数据
        )
        
        # 显示结果
        if result.success:
            st.success(f"✅ 下载完成! 成功: {len(result.successful_downloads)} 只, 跳过: {len(result.skipped_downloads)} 只")
        else:
            st.warning(f"⚠️ 部分下载失败: 成功 {len(result.successful_downloads)} 只, 失败 {len(result.failed_downloads)} 只")
            
            if result.failed_downloads:
                with st.expander("查看失败详情"):
                    for failed in result.failed_downloads:
                        st.text(f"• {failed['code']} ({failed['name']}): {failed.get('error', '未知错误')}")
        
        # 建议刷新页面
        st.info("💡 数据下载完成后，建议刷新页面以更新数据状态")
        
    except Exception as e:
        st.error(f"下载过程中出现错误: {e}")
        logger.error(f"科技股数据下载失败: {e}")
    
    finally:
        # 清理进度显示
        progress_bar.empty()
        status_text.empty()


# ==========================================
# 大盘红绿灯显示区域 (Requirements: 1.5, 13.2)
# ==========================================

def render_market_status_section(market_status: MarketStatus):
    """
    渲染大盘红绿灯显示区域
    
    Requirements: 1.5, 13.2
    """
    st.subheader("🚦 大盘红绿灯")
    
    # 深色主题状态颜色和图标
    if market_status.is_green:
        status_color = "#28a745"
        status_icon = "🟢"
        status_text = "绿灯 - 允许买入"
        container_style = "background-color: #1a4d3a; border: 2px solid #28a745; color: #d4edda;"
    else:
        status_color = "#dc3545"
        status_icon = "🔴"
        status_text = "红灯 - 禁止买入"
        container_style = "background-color: #4d1a1a; border: 2px solid #dc3545; color: #f8d7da;"
    
    # 显示状态卡片（深色主题）
    st.markdown(f"""
    <div style="{container_style} padding: 20px; border-radius: 10px; margin-bottom: 20px;">
        <h2 style="margin: 0; color: {status_color};">{status_icon} {status_text}</h2>
        <p style="margin: 10px 0 0 0; font-size: 14px; opacity: 0.8;">检查日期: {market_status.check_date}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 详细指标
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "创业板指收盘价",
            f"{market_status.gem_close:.2f}",
            delta=f"{'>' if market_status.gem_close > market_status.gem_ma20 else '<'} MA20"
        )
    
    with col2:
        st.metric(
            "MA20",
            f"{market_status.gem_ma20:.2f}"
        )
    
    with col3:
        macd_display = {
            "golden_cross": "🟢 金叉",
            "death_cross": "🔴 死叉",
            "neutral": "⚪ 中性",
            "unknown": "❓ 未知"
        }
        st.metric(
            "MACD 状态",
            macd_display.get(market_status.macd_status, market_status.macd_status)
        )
    
    # 状态原因
    with st.expander("查看详细判断依据"):
        st.info(market_status.reason)


# ==========================================
# 行业强弱排名表 (Requirements: 2.6, 13.3)
# ==========================================

def render_sector_rankings_section(sector_rankings: List[SectorRank]):
    """
    渲染行业强弱排名表
    
    Requirements: 2.6, 13.3
    """
    st.subheader("📊 行业强弱排名")
    
    if not sector_rankings:
        st.warning("无法获取行业排名数据")
        return
    
    # 转换为 DataFrame
    data = []
    for rank in sector_rankings:
        data.append({
            "排名": rank.rank,
            "行业": rank.sector_name,
            "20日涨幅": f"{rank.return_20d:.2f}%",
            "指数代码": rank.index_code,
            "数据来源": "指数" if rank.data_source == "index" else "龙头股",
            "可交易": "✅ 是" if rank.is_tradable else "❌ 否"
        })
    
    df = pd.DataFrame(data)
    
    # 高亮可交易行业（排名1-2）- 深色主题
    def highlight_tradable(row):
        if row["排名"] <= 2:
            return ['background-color: #1a4d3a; color: #d4edda'] * len(row)
        return ['background-color: #1e1e1e; color: #fafafa'] * len(row)
    
    st.dataframe(
        df.style.apply(highlight_tradable, axis=1),
        use_container_width=True,
        hide_index=True
    )
    
    # 可交易行业提示
    tradable_sectors = [r.sector_name for r in sector_rankings if r.is_tradable]
    if tradable_sectors:
        st.success(f"✅ 当前可交易行业: {', '.join(tradable_sectors)}")
    else:
        st.warning("⚠️ 当前无可交易行业")


# ==========================================
# 硬性筛选结果显示 (Requirements: 3.6)
# ==========================================

def render_hard_filter_section(filter_results: List[HardFilterResult]):
    """
    渲染硬性筛选结果显示
    
    Requirements: 3.6
    """
    st.subheader("🔍 硬性筛选结果")
    
    if not filter_results:
        st.info("暂无筛选结果")
        return
    
    # 获取筛选汇总
    hard_filter = HardFilter()
    summary = hard_filter.get_filter_summary(filter_results)
    
    # 显示统计汇总
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("总数", summary["total"])
    with col2:
        st.metric("通过", summary["passed"], delta=f"{summary['pass_rate']:.1f}%")
    with col3:
        st.metric("拒绝", summary["rejected"])
    with col4:
        st.metric("无数据", summary.get("reject_by_no_data", 0))
    
    # 拒绝原因分布
    if summary["rejected"] > 0:
        st.markdown("**拒绝原因分布:**")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("股价过高", summary["reject_by_price"])
        with col2:
            st.metric("市值不符", summary["reject_by_market_cap"])
        with col3:
            st.metric("成交额不足", summary["reject_by_turnover"])
    
    # 显示被过滤的股票及原因
    rejected_results = [r for r in filter_results if not r.passed]
    if rejected_results:
        with st.expander(f"查看被过滤的股票 ({len(rejected_results)} 只)"):
            rejected_data = []
            for r in rejected_results:
                rejected_data.append({
                    "代码": r.code,
                    "名称": r.name,
                    "股价(元)": f"{r.price:.2f}",
                    "流通市值(亿)": f"{r.market_cap:.1f}",
                    "日均成交额(亿)": f"{r.avg_turnover:.2f}",
                    "拒绝原因": "; ".join(r.reject_reasons)
                })
            st.dataframe(pd.DataFrame(rejected_data), use_container_width=True, hide_index=True)
    
    # 显示通过筛选的股票
    passed_results = [r for r in filter_results if r.passed]
    if passed_results:
        with st.expander(f"查看通过筛选的股票 ({len(passed_results)} 只)", expanded=True):
            passed_data = []
            for r in passed_results:
                passed_data.append({
                    "代码": r.code,
                    "名称": r.name,
                    "股价(元)": f"{r.price:.2f}",
                    "流通市值(亿)": f"{r.market_cap:.1f}",
                    "日均成交额(亿)": f"{r.avg_turnover:.2f}"
                })
            st.dataframe(pd.DataFrame(passed_data), use_container_width=True, hide_index=True)


# ==========================================
# 尾盘交易窗口状态显示 (Requirements: 4.3, 4.4, 4.5)
# ==========================================

def render_trading_window_section():
    """
    渲染尾盘交易窗口状态显示
    
    Requirements: 4.3, 4.4, 4.5
    """
    st.subheader("⏰ 尾盘交易窗口")
    
    signal_generator = TechSignalGenerator()
    
    # 获取交易窗口状态
    window_status = signal_generator.get_trading_window_status()
    signal_status = signal_generator.get_signal_status()
    
    # 显示状态
    col1, col2 = st.columns(2)
    
    with col1:
        # 信号确认状态
        if signal_generator.is_signal_confirmed():
            st.success(f"✅ {signal_status}")
        else:
            st.warning(f"⏳ {signal_status}")
    
    with col2:
        # 交易窗口状态
        if window_status["is_trading_window"]:
            st.success(window_status["status_message"])
        else:
            st.info(window_status["status_message"])
    
    # 显示时间信息
    current_time = datetime.now()
    st.caption(f"当前时间: {current_time.strftime('%H:%M:%S')} | 信号判定时间: 14:45 | 交易窗口: 14:45-15:00")
    
    # 提醒信息
    if window_status["is_trading_window"]:
        st.info(f"""
        ⚡ **交易窗口已开启**
        
        剩余 {window_status['minutes_remaining']} 分钟，请在 15:00 前完成交易确认。
        
        建议操作：
        1. 确认买入信号已生效
        2. 检查新闻面无重大利空
        3. 在券商APP下单
        """)
    elif current_time.time() < time(14, 45):
        st.info("""
        ⏳ **等待尾盘确认**
        
        当前信号为"待确认"状态，14:45 后信号将自动确认。
        
        T+1 制度下，尾盘判定可以：
        - 避免日内波动干扰
        - 获得更准确的收盘价信号
        - 为次日交易做好准备
        """)


# ==========================================
# 买入信号列表 (Requirements: 13.4)
# ==========================================

def render_buy_signals_section(signals: List[TechBuySignal]):
    """
    渲染买入信号列表
    
    Requirements: 13.4
    """
    st.subheader("🟢 买入信号")
    
    if not signals:
        st.info("📭 当前无买入信号")
        return
    
    # 信号统计
    confirmed_count = sum(1 for s in signals if s.is_confirmed)
    pending_count = len(signals) - confirmed_count
    avg_strength = sum(s.signal_strength for s in signals) / len(signals)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("信号总数", len(signals))
    with col2:
        st.metric("已确认", confirmed_count)
    with col3:
        st.metric("待确认", pending_count)
    with col4:
        st.metric("平均强度", f"{avg_strength:.0f}")
    
    st.divider()
    
    # 显示每个信号
    for signal in signals:
        render_buy_signal_card(signal)


def render_buy_signal_card(signal: TechBuySignal):
    """渲染单个买入信号卡片"""
    # 确认状态
    status_icon = "✅" if signal.is_confirmed else "⏳"
    status_text = "已确认" if signal.is_confirmed else "待确认"
    
    with st.container():
        # 标题行
        col1, col2, col3 = st.columns([3, 2, 1])
        
        with col1:
            st.markdown(f"### {status_icon} {signal.code} {signal.name}")
            st.caption(f"行业: {signal.sector} | 信号强度: {signal.signal_strength:.0f}")
        
        with col2:
            st.metric("当前价格", f"¥{signal.price:.2f}")
        
        with col3:
            st.metric("状态", status_text)
        
        # 技术指标
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("RSI(14)", f"{signal.rsi:.1f}", delta="55-80" if 55 <= signal.rsi <= 80 else None)
        with col2:
            st.metric("量比", f"{signal.volume_ratio:.2f}", delta=">1.5" if signal.volume_ratio >= 1.5 else None)
        with col3:
            st.metric("MA5", f"{signal.ma5:.2f}")
        with col4:
            st.metric("MA20", f"{signal.ma20:.2f}")
        
        # 条件满足状态
        st.markdown("**满足条件:**")
        for condition in signal.conditions_met:
            st.markdown(f"- ✅ {condition}")
        
        # 基本面信息
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"营收增长: {'✅' if signal.revenue_growth else '❌'}")
        with col2:
            st.markdown(f"净利增长: {'✅' if signal.profit_growth else '❌'}")
        with col3:
            st.markdown(f"大额解禁: {'⚠️ 有' if signal.has_unlock else '✅ 无'}")
        
        # 生成时间
        st.caption(f"生成时间: {signal.generated_at.strftime('%Y-%m-%d %H:%M:%S')}")
        
        st.divider()


# ==========================================
# 卖出信号和止损位显示 (Requirements: 7.3, 8.2, 9.6, 13.5, 13.7)
# ==========================================

def render_exit_signals_section(exit_signals: List[TechExitSignal]):
    """
    渲染卖出信号和止损位显示
    
    Requirements: 7.3, 8.2, 9.6, 13.5, 13.7
    """
    st.subheader("🔴 卖出信号")
    
    if not exit_signals:
        st.success("✅ 当前持仓无卖出信号")
        return
    
    # 按优先级统计
    emergency_count = sum(1 for s in exit_signals if s.priority == SignalPriority.EMERGENCY)
    stop_loss_count = sum(1 for s in exit_signals if s.priority == SignalPriority.STOP_LOSS)
    take_profit_count = sum(1 for s in exit_signals if s.priority == SignalPriority.TAKE_PROFIT)
    trend_break_count = sum(1 for s in exit_signals if s.priority == SignalPriority.TREND_BREAK)
    
    # 统计显示
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if emergency_count > 0:
            st.metric("🔴 紧急避险", emergency_count, delta="紧急!", delta_color="inverse")
        else:
            st.metric("🔴 紧急避险", 0)
    with col2:
        st.metric("🟠 止损", stop_loss_count)
    with col3:
        st.metric("🟡 止盈", take_profit_count)
    with col4:
        st.metric("🔵 趋势断裂", trend_break_count)
    
    st.divider()
    
    # 按优先级排序显示
    for signal in exit_signals:
        render_exit_signal_card(signal)


def render_exit_signal_card(signal: TechExitSignal):
    """渲染单个卖出信号卡片"""
    # 深色主题优先级颜色和图标
    priority_config = {
        SignalPriority.EMERGENCY: {"icon": "🔴", "color": "#dc3545", "bg": "#4d1a1a"},
        SignalPriority.STOP_LOSS: {"icon": "🟠", "color": "#fd7e14", "bg": "#4d2d1a"},
        SignalPriority.TAKE_PROFIT: {"icon": "🟡", "color": "#ffc107", "bg": "#4d3d1a"},
        SignalPriority.TREND_BREAK: {"icon": "🔵", "color": "#007bff", "bg": "#1a2d4d"},
    }
    
    config = priority_config.get(signal.priority, {"icon": "⚪", "color": "#6c757d", "bg": "#2d2d2d"})
    
    # 特殊持仓标记
    special_marker = ""
    if signal.is_min_position:
        special_marker = " 🔸 严格止盈"
    
    # 卡片容器（深色主题）
    st.markdown(f"""
    <div style="background-color: {config['bg']}; padding: 15px; border-radius: 10px; 
                border-left: 5px solid {config['color']}; margin-bottom: 15px;">
        <h4 style="margin: 0; color: {config['color']};">
            {config['icon']} {signal.code} {signal.name}{special_marker}
        </h4>
    </div>
    """, unsafe_allow_html=True)
    
    # 详细信息
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        pnl_color = "green" if signal.pnl_pct >= 0 else "red"
        st.metric("盈亏", f"{signal.pnl_pct:.1%}")
    with col2:
        st.metric("当前价", f"¥{signal.current_price:.2f}")
    with col3:
        st.metric("止损价", f"¥{signal.stop_loss_price:.2f}")
    with col4:
        st.metric("成本价", f"¥{signal.cost_price:.2f}")
    
    # RSI 和 MA20 跌破天数
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        rsi_delta = "超买!" if signal.rsi > 85 else None
        st.metric("RSI", f"{signal.rsi:.1f}", delta=rsi_delta, delta_color="inverse" if rsi_delta else "normal")
    with col2:
        st.metric("MA5", f"¥{signal.ma5:.2f}")
    with col3:
        st.metric("MA20", f"¥{signal.ma20:.2f}")
    with col4:
        break_delta = f"{signal.ma20_break_days}天" if signal.ma20_break_days > 0 else None
        st.metric("MA20跌破", f"{signal.ma20_break_days}天", delta=break_delta, delta_color="inverse" if break_delta else "normal")
    
    # 持仓信息
    st.markdown(f"**持仓:** {signal.shares}股 | **建议操作:** {signal.suggested_action}")
    
    st.divider()


# ==========================================
# 特殊持仓标记显示 (Requirements: 10.1, 10.2, 10.3, 10.4)
# ==========================================

def render_special_positions_section(holdings: List[Holding]):
    """
    渲染特殊持仓标记显示
    
    Requirements: 10.1, 10.2, 10.3, 10.4
    """
    if not holdings:
        return
    
    exit_manager = TechExitManager()
    marked_positions = exit_manager.mark_special_positions(holdings)
    
    # 筛选出100股持仓
    min_positions = [p for p in marked_positions if p["is_min_position"]]
    
    if not min_positions:
        return
    
    st.subheader("🔸 特殊持仓提醒")
    
    st.warning(f"""
    ⚠️ **发现 {len(min_positions)} 只 100股持仓**
    
    100股为最小仓位，需要执行**严格止盈**策略：
    - RSI > 85 时，止损紧贴 MA5
    - 不可分仓卖出，需一次性处理
    """)
    
    # 显示特殊持仓列表
    for p in min_positions:
        holding = p["holding"]
        st.markdown(f"""
        <div style="background-color: #4d3d1a; padding: 10px; border-radius: 5px; 
                    border-left: 4px solid #ffc107; margin-bottom: 10px; color: #fff3cd;">
            <b>🔸 {holding.code} {holding.name}</b> - 100股 | 
            成本: ¥{holding.buy_price:.2f} | 
            买入日期: {holding.buy_date}
            <br><small>⚠️ 严格止盈：RSI>85时止损紧贴MA5</small>
        </div>
        """, unsafe_allow_html=True)


# ==========================================
# 策略参数显示 (v11.2 最佳参数)
# ==========================================

def render_strategy_params_section():
    """
    渲染当前策略参数显示区域
    
    显示 v11.4g 平衡版策略的核心参数配置
    """
    st.subheader("⚙️ 当前策略参数 (v11.4g 平衡版)")
    
    # 参数定义（与 backtester.py 保持一致）
    params = {
        "止损": {"value": "-4.6%", "desc": "硬性止损线"},
        "止盈": {"value": "+22%", "desc": "固定止盈目标"},
        "移动止盈触发": {"value": "+9%", "desc": "盈利达到后启用移动止盈"},
        "移动止盈回撤": {"value": "2.8%", "desc": "从最高点回撤卖出"},
        "RSI范围": {"value": "44-70", "desc": "买入信号RSI区间"},
        "RSI超买": {"value": ">80", "desc": "触发卖出（仅盈利时）"},
        "最大持仓天数": {"value": "15天", "desc": "超时强制卖出"},
        "信号强度门槛": {"value": "≥83", "desc": "买入信号最低分数"},
        "单只仓位上限": {"value": "≤11%", "desc": "单只股票最大仓位"},
        "最大持仓数": {"value": "≤5只", "desc": "同时持有股票上限"},
    }
    
    # 使用两列布局显示参数
    col1, col2 = st.columns(2)
    
    # 风控参数
    with col1:
        st.markdown("**🛡️ 风控参数**")
        st.markdown(f"""
        | 参数 | 值 | 说明 |
        |------|-----|------|
        | 止损 | `{params['止损']['value']}` | {params['止损']['desc']} |
        | 止盈 | `{params['止盈']['value']}` | {params['止盈']['desc']} |
        | 移动止盈触发 | `{params['移动止盈触发']['value']}` | {params['移动止盈触发']['desc']} |
        | 移动止盈回撤 | `{params['移动止盈回撤']['value']}` | {params['移动止盈回撤']['desc']} |
        | 最大持仓天数 | `{params['最大持仓天数']['value']}` | {params['最大持仓天数']['desc']} |
        """)
    
    # 买入参数
    with col2:
        st.markdown("**📈 买入参数**")
        st.markdown(f"""
        | 参数 | 值 | 说明 |
        |------|-----|------|
        | RSI范围 | `{params['RSI范围']['value']}` | {params['RSI范围']['desc']} |
        | RSI超买 | `{params['RSI超买']['value']}` | {params['RSI超买']['desc']} |
        | 信号强度门槛 | `{params['信号强度门槛']['value']}` | {params['信号强度门槛']['desc']} |
        | 单只仓位上限 | `{params['单只仓位上限']['value']}` | {params['单只仓位上限']['desc']} |
        | 最大持仓数 | `{params['最大持仓数']['value']}` | {params['最大持仓数']['desc']} |
        """)
    
    # 策略说明
    with st.expander("📖 策略说明", expanded=False):
        st.markdown("""
        **v11.4g 平衡版策略特点：**
        
        1. **趋势过滤**：MA20斜率检查，只在上升趋势中买入
        2. **价格位置过滤**：避免追高，价格不能高于MA5超过5%
        3. **更高止盈目标**：止盈提升至22%，捕捉更大行情
        4. **移动止盈保护**：+9%触发，回撤2.8%卖出
        5. **RSI超买仅盈利卖出**：避免亏损时因RSI超买被迫卖出
        
        **卖出优先级：**
        1. 🔴 止损（-4.6%）
        2. 🟡 移动止盈（+9%触发，回撤2.8%）
        3. 🟢 固定止盈（+22%）
        4. 📊 RSI超买（>80且盈利）
        5. 🔵 趋势反转（MA5<MA20且亏损）
        6. ⏰ 持仓超时（≥15天）
        """)
    
    # 版本对比
    with st.expander("📊 v11.2 vs v11.4g 对比", expanded=False):
        st.markdown("""
        | 参数 | v11.2 | v11.4g | 变化 |
        |------|-------|--------|------|
        | 止损 | -4.5% | -4.6% | 略放宽 |
        | 止盈 | +20% | +22% | 提高2% |
        | 移动止盈触发 | +9% | +9% | 不变 |
        | 移动止盈回撤 | 2.8% | 2.8% | 不变 |
        | RSI范围 | 45-72 | 44-70 | 略调整 |
        | 最大持仓天数 | 15天 | 15天 | 不变 |
        | 趋势过滤 | ❌ | ✅ | 新增 |
        | 价格位置过滤 | ❌ | ✅ | 新增 |
        | RSI超买仅盈利卖 | ❌ | ✅ | 新增 |
        
        **回测对比（2022-12-26 ~ 2024-12-20）：**
        | 指标 | v11.2 | v11.4g | 改善 |
        |------|-------|--------|------|
        | 收益率 | 39.70% | 33.51% | -16% |
        | 最大回撤 | -11.39% | -4.81% | -58% |
        | 胜率 | 21.9% | 24.5% | +12% |
        | 收益/回撤比 | 3.48 | 6.96 | +100% |
        
        **v11.4g 是收益与风险的最佳平衡版本**
        """)


# ==========================================
# 回测功能入口 (Requirements: 11.8, 13.6)
# ==========================================

def render_backtest_section():
    """
    渲染回测功能入口
    
    Requirements: 11.8, 13.6
    """
    st.subheader("📈 回测验证")
    
    with st.expander("🔬 运行回测", expanded=False):
        st.info("""
        **震荡市强制验证**
        
        回测将强制包含 2022-2023 震荡市时间段，验证策略在不利市场环境下的表现。
        """)
        
        # 回测参数配置
        col1, col2 = st.columns(2)
        
        with col1:
            start_date = st.date_input(
                "开始日期",
                value=date(2022, 1, 1),
                min_value=date(2020, 1, 1),
                max_value=date.today()
            )
        
        with col2:
            end_date = st.date_input(
                "结束日期",
                value=date(2024, 12, 1),
                min_value=date(2020, 1, 1),
                max_value=date.today()
            )
        
        # 股票选择
        stock_pool = get_tech_stock_pool()
        all_stocks = stock_pool.get_all_stocks()
        
        # 默认选择测试标的
        default_codes = ["002600", "300308", "002371"]
        
        selected_stocks = st.multiselect(
            "选择回测股票",
            options=[f"{s.code} {s.name}" for s in all_stocks],
            default=[f"{s.code} {s.name}" for s in all_stocks if s.code in default_codes],
            help="默认使用长盈精密、中际旭创、北方华创作为测试标的"
        )
        
        # 提取股票代码
        selected_codes = [s.split()[0] for s in selected_stocks]
        
        # 初始资金
        initial_capital = st.number_input(
            "初始资金",
            min_value=10000,
            max_value=10000000,
            value=100000,
            step=10000
        )
        
        # 运行回测按钮
        if st.button("🚀 运行回测", type="primary", use_container_width=True):
            if not selected_codes:
                st.error("请至少选择一只股票")
                return
            
            with st.spinner("正在运行回测..."):
                run_backtest_and_display(
                    selected_codes,
                    start_date.strftime("%Y-%m-%d"),
                    end_date.strftime("%Y-%m-%d"),
                    initial_capital
                )


def run_backtest_and_display(
    stock_codes: List[str],
    start_date: str,
    end_date: str,
    initial_capital: float
):
    """运行回测并显示结果"""
    data_feed = get_data_feed()
    backtester = TechBacktester(data_feed)
    
    # 运行回测
    result = backtester.run_backtest(
        stock_codes=stock_codes,
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital
    )
    
    # 显示回测结果
    st.success("✅ 回测完成")
    
    # 主要指标
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        return_color = "green" if result.total_return >= 0 else "red"
        st.metric("总收益率", f"{result.total_return:.2%}")
    with col2:
        st.metric("最大回撤", f"{result.max_drawdown:.2%}")
    with col3:
        st.metric("总交易次数", result.total_trades)
    with col4:
        st.metric("胜率", f"{result.win_rate:.1%}")
    
    # 警告信息
    if result.drawdown_warning:
        st.error("⚠️ 最大回撤超过 -15% 阈值，策略风险较高！")
    
    if not result.market_filter_effective:
        st.warning("⚠️ 大盘风控效果不明显，建议优化参数")
    
    # 数据警告
    if result.data_warnings:
        with st.expander(f"⚠️ 数据警告 ({len(result.data_warnings)} 条)"):
            for warning in result.data_warnings:
                st.warning(warning["message"])
    
    # 震荡市独立报告
    st.markdown("### 📊 震荡市验证报告")
    st.code(result.bear_market_report, language=None)
    
    # 大盘风控有效性分析
    effectiveness_report = backtester.analyze_market_filter_effectiveness(result)
    st.markdown("### 🛡️ 大盘风控有效性分析")
    st.code(effectiveness_report, language=None)
    
    # 各时间段绩效
    if result.period_performances:
        st.markdown("### 📅 各时间段绩效")
        
        period_data = []
        for perf in result.period_performances:
            period_data.append({
                "时间段": perf.period_name,
                "收益率": f"{perf.total_return:.2%}",
                "最大回撤": f"{perf.max_drawdown:.2%}",
                "交易次数": perf.trade_count,
                "胜率": f"{perf.win_rate:.1%}",
                "震荡市": "是" if perf.is_bear_market else "否"
            })
        
        st.dataframe(pd.DataFrame(period_data), use_container_width=True, hide_index=True)


# ==========================================
# 股票池管理
# ==========================================

def render_stock_pool_section():
    """渲染股票池管理区域"""
    st.subheader("📋 科技股池")
    
    stock_pool = get_tech_stock_pool()
    
    # 行业选择
    sectors = stock_pool.get_sectors()
    selected_sector = st.selectbox(
        "选择行业",
        options=["全部"] + sectors,
        index=0
    )
    
    # 获取股票列表
    if selected_sector == "全部":
        stocks = stock_pool.get_all_stocks()
    else:
        stocks = stock_pool.get_stocks_by_sector(selected_sector)
    
    # 显示统计
    st.caption(f"共 {len(stocks)} 只股票")
    
    # 显示股票列表
    if stocks:
        stock_data = []
        for s in stocks:
            stock_data.append({
                "代码": s.code,
                "名称": s.name,
                "行业": s.sector
            })
        
        st.dataframe(pd.DataFrame(stock_data), use_container_width=True, hide_index=True)


# ==========================================
# 主页面
# ==========================================

def main():
    """主页面入口"""
    st.set_page_config(
        page_title="科技股专属板块 - MiniQuant-Lite",
        page_icon="🔬",
        layout="wide"
    )
    
    # 添加深色主题CSS
    st.markdown("""
    <style>
    /* 深色主题样式 */
    .stApp {
        background-color: #0e1117;
        color: #fafafa;
    }
    
    /* 主容器深色背景 */
    .main .block-container {
        background-color: #0e1117;
        color: #fafafa;
    }
    
    /* 侧边栏深色 */
    .css-1d391kg {
        background-color: #262730;
    }
    
    /* 卡片和容器深色 */
    .stContainer, .element-container {
        background-color: #1e1e1e;
        border-radius: 10px;
    }
    
    /* 表格深色主题 */
    .stDataFrame {
        background-color: #1e1e1e;
        color: #fafafa;
    }
    
    /* 按钮深色主题 */
    .stButton > button {
        background-color: #262730;
        color: #fafafa;
        border: 1px solid #404040;
    }
    
    .stButton > button:hover {
        background-color: #404040;
        border-color: #606060;
    }
    
    /* 输入框深色主题 */
    .stSelectbox > div > div {
        background-color: #262730;
        color: #fafafa;
    }
    
    .stTextInput > div > div > input {
        background-color: #262730;
        color: #fafafa;
        border: 1px solid #404040;
    }
    
    /* 标签页深色主题 */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #262730;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: #262730;
        color: #fafafa;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #404040;
    }
    
    /* 指标卡片深色主题 */
    .metric-container {
        background-color: #1e1e1e;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #404040;
    }
    
    /* 展开器深色主题 */
    .streamlit-expanderHeader {
        background-color: #262730;
        color: #fafafa;
    }
    
    .streamlit-expanderContent {
        background-color: #1e1e1e;
        border: 1px solid #404040;
    }
    
    /* 深色主题文本颜色 */
    h1, h2, h3, h4, h5, h6, p, span, div {
        color: #fafafa !important;
    }
    
    /* 成功/错误/警告消息深色主题 */
    .stSuccess {
        background-color: #1a4d3a;
        border: 1px solid #28a745;
        color: #d4edda;
    }
    
    .stError {
        background-color: #4d1a1a;
        border: 1px solid #dc3545;
        color: #f8d7da;
    }
    
    .stWarning {
        background-color: #4d3d1a;
        border: 1px solid #ffc107;
        color: #fff3cd;
    }
    
    .stInfo {
        background-color: #1a3d4d;
        border: 1px solid #17a2b8;
        color: #d1ecf1;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.title("🔬 科技股专属板块")
    st.markdown("科技股筛选和交易系统 - 小资金生存优先 | T+1 尾盘判定 | 风险控制优先")
    
    st.divider()
    
    # 初始化数据
    data_feed = get_data_feed()
    stock_pool = get_tech_stock_pool()
    all_codes = stock_pool.get_all_codes()
    
    # 数据状态检查面板
    render_data_status_panel(data_feed, stock_pool)
    
    st.divider()
    
    # 创建标签页
    tab1, tab2, tab3, tab4 = st.tabs(["📊 市场概览", "🎯 交易信号", "📈 回测验证", "📋 股票池"])
    
    # ==========================================
    # Tab 1: 市场概览
    # ==========================================
    with tab1:
        st.markdown("### 市场环境分析")
        
        # 大盘红绿灯
        with st.spinner("正在检查大盘状态..."):
            market_filter = MarketFilter(data_feed)
            try:
                market_status = market_filter.check_market_status()
            except Exception as e:
                st.error(f"获取大盘状态失败: {e}")
                market_status = MarketStatus(
                    is_green=False,
                    gem_close=0.0,
                    gem_ma20=0.0,
                    macd_status="unknown",
                    check_date=date.today(),
                    reason="无法获取数据"
                )
        
        render_market_status_section(market_status)
        
        st.divider()
        
        # 行业强弱排名
        with st.spinner("正在计算行业排名..."):
            sector_ranker = SectorRanker(data_feed)
            try:
                sector_rankings = sector_ranker.get_sector_rankings(use_proxy_stocks=True)
            except Exception as e:
                st.error(f"获取行业排名失败: {e}")
                sector_rankings = []
        
        render_sector_rankings_section(sector_rankings)
        
        st.divider()
        
        # 尾盘交易窗口状态
        render_trading_window_section()
    
    # ==========================================
    # Tab 2: 交易信号
    # ==========================================
    with tab2:
        st.markdown("### 交易信号生成")
        
        # 生成信号按钮
        col1, col2 = st.columns([3, 1])
        with col1:
            st.info("点击下方按钮生成科技股交易信号（包含硬性筛选、买入信号、卖出信号）")
        with col2:
            generate_signals = st.button("🔄 生成信号", type="primary", use_container_width=True)
        
        if generate_signals or st.session_state.get("tech_signals_generated", False):
            st.session_state["tech_signals_generated"] = True
            
            # 获取市场状态（如果还没有）
            if 'market_status' not in locals():
                market_filter = MarketFilter(data_feed)
                try:
                    market_status = market_filter.check_market_status()
                except:
                    market_status = MarketStatus(
                        is_green=False, gem_close=0.0, gem_ma20=0.0,
                        macd_status="unknown", check_date=date.today(),
                        reason="无法获取数据"
                    )
            
            # 获取行业排名（如果还没有）
            if 'sector_rankings' not in locals():
                sector_ranker = SectorRanker(data_feed)
                try:
                    sector_rankings = sector_ranker.get_sector_rankings(use_proxy_stocks=True)
                except:
                    sector_rankings = []
            
            # 硬性筛选
            with st.spinner("正在进行硬性筛选..."):
                hard_filter = HardFilter(data_feed)
                try:
                    filter_results = hard_filter.filter_stocks(all_codes)
                except Exception as e:
                    st.error(f"硬性筛选失败: {e}")
                    filter_results = []
            
            render_hard_filter_section(filter_results)
            
            st.divider()
            
            # 买入信号
            with st.spinner("正在生成买入信号..."):
                signal_generator = TechSignalGenerator(data_feed)
                try:
                    buy_signals = signal_generator.generate_signals(
                        stock_pool=all_codes,
                        market_status=market_status,
                        sector_rankings=sector_rankings,
                        hard_filter_results=filter_results
                    )
                except Exception as e:
                    st.error(f"生成买入信号失败: {e}")
                    buy_signals = []
            
            render_buy_signals_section(buy_signals)
            
            st.divider()
            
            # 卖出信号（基于持仓）
            tracker = PositionTracker()
            holdings = tracker.get_all_positions()
            
            if holdings:
                with st.spinner("正在检查卖出信号..."):
                    exit_manager = TechExitManager(data_feed)
                    try:
                        exit_signals = exit_manager.check_exit_signals(
                            holdings=holdings,
                            market_status=market_status
                        )
                    except Exception as e:
                        st.error(f"检查卖出信号失败: {e}")
                        exit_signals = []
                
                render_exit_signals_section(exit_signals)
                
                st.divider()
                
                # 特殊持仓标记
                render_special_positions_section(holdings)
            else:
                st.info("📭 当前无持仓，无需检查卖出信号")
    
    # ==========================================
    # Tab 3: 回测验证
    # ==========================================
    with tab3:
        # 显示当前策略参数
        render_strategy_params_section()
        
        st.divider()
        
        # 回测功能
        render_backtest_section()
    
    # ==========================================
    # Tab 4: 股票池
    # ==========================================
    with tab4:
        render_stock_pool_section()


if __name__ == "__main__":
    main()
