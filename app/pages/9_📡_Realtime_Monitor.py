# -*- coding: utf-8 -*-
"""
实时监控页面

基于v11.4g科技股策略提供实时买卖信号监控，包括：
- 监控列表管理
- 持仓输入和管理
- 买入信号展示
- 卖出信号展示
- 技术指标面板
- 自动刷新功能

Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 6.2, 7.3, 7.4, 8.2, 8.3
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

from core.realtime_monitor import (
    RealtimeMonitor,
    SignalEngine,
    DataFetcher,
    Position,
    StockData,
    BuySignal,
    SellSignal,
    V114G_STRATEGY_PARAMS,
    MONITOR_CONFIG,
    get_market_status,
    is_trading_time,
    MarketStatus,
)


# ==========================================
# 颜色映射函数 (Requirements: 6.2, 7.3, 7.4, 8.2, 8.3)
# ==========================================

def get_signal_strength_color(strength: int) -> str:
    """
    获取信号强度对应的颜色
    
    Property 12: Signal Strength Color Mapping
    For any signal strength S:
    - S >= 80: color = "green"
    - 60 <= S < 80: color = "yellow"
    - S < 60: color = "red"
    
    Requirements: 6.2
    
    Args:
        strength: 信号强度 0-100
        
    Returns:
        str: 颜色名称
    """
    if strength >= MONITOR_CONFIG.signal_strength_high:  # 80
        return "green"
    elif strength >= MONITOR_CONFIG.signal_strength_medium:  # 60
        return "yellow"
    else:
        return "red"


def get_signal_strength_hex_color(strength: int) -> str:
    """
    获取信号强度对应的十六进制颜色（深色主题）
    
    Args:
        strength: 信号强度 0-100
        
    Returns:
        str: 十六进制颜色代码
    """
    color = get_signal_strength_color(strength)
    color_map = {
        "green": "#28a745",
        "yellow": "#ffc107",
        "red": "#dc3545",
    }
    return color_map.get(color, "#6c757d")


def get_fund_flow_color(fund_flow: float) -> str:
    """
    获取资金流向对应的颜色
    
    Property 13: Fund Flow Color Mapping
    For any fund flow value F:
    - F > 0: color = "green" (inflow)
    - F < 0: color = "red" (outflow)
    - F = 0: color = "gray" (neutral)
    
    Requirements: 7.3, 7.4
    
    Args:
        fund_flow: 资金流向值
        
    Returns:
        str: 颜色名称
    """
    if fund_flow > 0:
        return "green"
    elif fund_flow < 0:
        return "red"
    else:
        return "gray"


def get_fund_flow_hex_color(fund_flow: float) -> str:
    """
    获取资金流向对应的十六进制颜色
    
    Args:
        fund_flow: 资金流向值
        
    Returns:
        str: 十六进制颜色代码
    """
    color = get_fund_flow_color(fund_flow)
    color_map = {
        "green": "#28a745",
        "red": "#dc3545",
        "gray": "#6c757d",
    }
    return color_map.get(color, "#6c757d")


def get_condition_color(is_met: bool) -> str:
    """
    获取条件满足状态对应的颜色
    
    Requirements: 8.2, 8.3
    
    Args:
        is_met: 条件是否满足
        
    Returns:
        str: 十六进制颜色代码
    """
    return "#28a745" if is_met else "#dc3545"


# ==========================================
# Session State 初始化
# ==========================================

def init_session_state():
    """初始化 session state"""
    if 'realtime_monitor' not in st.session_state:
        st.session_state.realtime_monitor = RealtimeMonitor()
    
    if 'signal_engine' not in st.session_state:
        st.session_state.signal_engine = SignalEngine()
    
    if 'data_fetcher' not in st.session_state:
        st.session_state.data_fetcher = DataFetcher()
    
    if 'stock_data_cache' not in st.session_state:
        st.session_state.stock_data_cache = {}
    
    if 'last_refresh_time' not in st.session_state:
        st.session_state.last_refresh_time = None
    
    if 'auto_refresh' not in st.session_state:
        st.session_state.auto_refresh = False


def get_monitor() -> RealtimeMonitor:
    """获取监控器实例"""
    return st.session_state.realtime_monitor


def get_signal_engine() -> SignalEngine:
    """获取信号引擎实例"""
    return st.session_state.signal_engine


def get_data_fetcher() -> DataFetcher:
    """获取数据获取器实例"""
    return st.session_state.data_fetcher


# ==========================================
# 市场状态显示 (Requirements: 5.2)
# ==========================================

def render_market_status_section():
    """渲染市场状态显示区域"""
    market_status = get_market_status()
    
    # 状态颜色和图标
    if market_status.is_open:
        status_color = "#28a745"
        status_icon = "🟢"
        bg_color = "#1a4d3a"
        text_color = "#d4edda"
    else:
        status_color = "#ffc107"
        status_icon = "🟡"
        bg_color = "#4d3d1a"
        text_color = "#fff3cd"
    
    st.markdown(f"""
    <div style="background-color: {bg_color}; padding: 15px; border-radius: 10px; 
                border-left: 5px solid {status_color}; margin-bottom: 15px;">
        <h4 style="margin: 0; color: {status_color};">
            {status_icon} {market_status.message}
        </h4>
        <p style="margin: 5px 0 0 0; font-size: 12px; color: {text_color};">
            检查时间: {market_status.checked_at.strftime('%Y-%m-%d %H:%M:%S')}
        </p>
    </div>
    """, unsafe_allow_html=True)



# ==========================================
# 监控列表管理 (Requirements: 10.2, 10.3)
# ==========================================

def render_watchlist_management_section():
    """渲染监控列表管理区域"""
    st.subheader("📋 监控列表")
    
    monitor = get_monitor()
    
    # 添加股票
    col1, col2 = st.columns([3, 1])
    
    with col1:
        new_code = st.text_input(
            "添加股票代码",
            placeholder="输入6位股票代码，如 600036",
            max_chars=6,
            key="add_watchlist_code"
        )
    
    with col2:
        st.write("")  # 占位
        st.write("")  # 占位
        if st.button("➕ 添加", key="add_watchlist_btn", use_container_width=True):
            if new_code:
                if monitor.add_to_watchlist(new_code):
                    st.success(f"✅ 已添加 {new_code} 到监控列表")
                    st.rerun()
                else:
                    if not monitor.validate_stock_code(new_code):
                        st.error("❌ 无效的股票代码格式（需要6位数字，以0/3/6开头）")
                    elif new_code in monitor.watchlist:
                        st.warning("⚠️ 该股票已在监控列表中")
                    elif monitor.watchlist_size >= MONITOR_CONFIG.max_watchlist_size:
                        st.error(f"❌ 监控列表已满（最多{MONITOR_CONFIG.max_watchlist_size}只）")
            else:
                st.warning("⚠️ 请输入股票代码")
    
    # 显示监控列表
    watchlist = monitor.watchlist
    
    if not watchlist:
        st.info("📭 监控列表为空，请添加股票")
        return
    
    st.markdown(f"**当前监控: {len(watchlist)}/{MONITOR_CONFIG.max_watchlist_size} 只**")
    
    # 获取股票数据
    stock_data_cache = st.session_state.stock_data_cache
    
    # 构建表格数据
    data = []
    for code in watchlist:
        stock_data = stock_data_cache.get(code)
        if stock_data:
            data.append({
                "代码": code,
                "名称": stock_data.name,
                "现价": f"¥{stock_data.current_price:.2f}",
                "涨跌幅": f"{stock_data.change_pct*100:.2f}%",
            })
        else:
            data.append({
                "代码": code,
                "名称": "-",
                "现价": "-",
                "涨跌幅": "-",
            })
    
    if data:
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)
    
    # 删除股票
    st.markdown("**删除股票**")
    col1, col2 = st.columns([3, 1])
    
    with col1:
        delete_code = st.selectbox(
            "选择要删除的股票",
            options=watchlist,
            key="delete_watchlist_select"
        )
    
    with col2:
        st.write("")  # 占位
        st.write("")  # 占位
        if st.button("🗑️ 删除", key="delete_watchlist_btn", type="secondary"):
            if delete_code:
                if monitor.remove_from_watchlist(delete_code):
                    st.success(f"✅ 已从监控列表移除 {delete_code}")
                    st.rerun()


# ==========================================
# 持仓管理 (Requirements: 10.2, 10.3)
# ==========================================

def render_position_management_section():
    """渲染持仓管理区域"""
    st.subheader("💼 持仓管理")
    
    monitor = get_monitor()
    
    # 添加持仓表单
    with st.expander("➕ 添加持仓", expanded=False):
        with st.form("add_position_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                pos_code = st.text_input(
                    "股票代码",
                    placeholder="例如: 600036",
                    max_chars=6
                )
                
                pos_cost = st.number_input(
                    "成本价",
                    min_value=0.01,
                    value=10.0,
                    step=0.01,
                    format="%.2f"
                )
            
            with col2:
                pos_name = st.text_input(
                    "股票名称",
                    placeholder="例如: 招商银行"
                )
                
                pos_quantity = st.number_input(
                    "持仓数量（股）",
                    min_value=100,
                    value=100,
                    step=100
                )
            
            pos_date = st.date_input(
                "买入日期",
                value=date.today(),
                max_value=date.today()
            )
            
            submitted = st.form_submit_button("✅ 添加持仓", type="primary")
            
            if submitted:
                if not pos_code or len(pos_code) != 6:
                    st.error("请输入有效的6位股票代码")
                elif not pos_name:
                    st.error("请输入股票名称")
                else:
                    success = monitor.add_position(
                        code=pos_code,
                        name=pos_name,
                        cost_price=pos_cost,
                        quantity=pos_quantity,
                        buy_date=pos_date
                    )
                    if success:
                        st.success(f"✅ 成功添加持仓: {pos_code} {pos_name}")
                        st.rerun()
                    else:
                        st.error("❌ 添加失败，请检查输入")
    
    # 显示持仓列表
    positions = monitor.positions
    
    if not positions:
        st.info("📭 暂无持仓记录")
        return
    
    # 持仓汇总
    summary = monitor.get_position_summary()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("持仓数量", f"{summary['position_count']} 只")
    with col2:
        st.metric("总成本", f"¥{summary['total_cost_value']:,.0f}")
    with col3:
        st.metric("总市值", f"¥{summary['total_market_value']:,.0f}")
    with col4:
        pnl_color = "normal" if summary['total_pnl'] >= 0 else "inverse"
        st.metric(
            "总盈亏",
            f"¥{summary['total_pnl']:,.0f}",
            delta=f"{summary['total_pnl_pct']*100:.2f}%",
            delta_color=pnl_color
        )
    
    st.divider()
    
    # 持仓表格
    pos_data = []
    for code, position in positions.items():
        pnl_pct = position.pnl_pct * 100
        pos_data.append({
            "代码": position.code,
            "名称": position.name,
            "成本价": f"¥{position.cost_price:.2f}",
            "现价": f"¥{position.current_price:.2f}",
            "数量": position.quantity,
            "盈亏%": f"{pnl_pct:.2f}%",
            "持仓天数": position.holding_days,
            "买入日期": position.buy_date.strftime('%Y-%m-%d'),
        })
    
    df = pd.DataFrame(pos_data)
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # 删除持仓
    st.markdown("**删除持仓**")
    col1, col2 = st.columns([3, 1])
    
    with col1:
        delete_pos = st.selectbox(
            "选择要删除的持仓",
            options=[f"{p.code} - {p.name}" for p in positions.values()],
            key="delete_position_select"
        )
    
    with col2:
        st.write("")
        st.write("")
        if st.button("🗑️ 删除", key="delete_position_btn", type="secondary"):
            if delete_pos:
                code = delete_pos.split(" - ")[0]
                if monitor.remove_position(code):
                    st.success(f"✅ 已删除持仓 {code}")
                    st.rerun()



# ==========================================
# 买入信号展示 (Requirements: 10.4)
# ==========================================

def render_buy_signals_section():
    """渲染买入信号展示区域"""
    st.subheader("🟢 买入信号")
    
    monitor = get_monitor()
    signal_engine = get_signal_engine()
    stock_data_cache = st.session_state.stock_data_cache
    
    # 检查监控列表中的买入信号
    buy_signals = []
    
    for code in monitor.watchlist:
        stock_data = stock_data_cache.get(code)
        if stock_data:
            signal = signal_engine.generate_buy_signal(stock_data)
            if signal:
                buy_signals.append(signal)
    
    if not buy_signals:
        st.info("📭 当前无买入信号")
        return
    
    # 按信号强度排序
    buy_signals.sort(key=lambda x: x.signal_strength, reverse=True)
    
    # 信号统计
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("信号数量", len(buy_signals))
    with col2:
        strong_count = sum(1 for s in buy_signals if s.signal_strength >= 80)
        st.metric("强信号", strong_count)
    with col3:
        avg_strength = sum(s.signal_strength for s in buy_signals) / len(buy_signals)
        st.metric("平均强度", f"{avg_strength:.0f}")
    
    st.divider()
    
    # 显示每个买入信号
    for signal in buy_signals:
        render_buy_signal_card(signal)


def render_buy_signal_card(signal: BuySignal):
    """渲染单个买入信号卡片"""
    strength_color = get_signal_strength_hex_color(signal.signal_strength)
    
    # 信号卡片
    st.markdown(f"""
    <div style="background-color: #1a4d3a; padding: 15px; border-radius: 10px; 
                border-left: 5px solid {strength_color}; margin-bottom: 15px;">
        <h4 style="margin: 0; color: {strength_color};">
            🟢 {signal.code} {signal.name} - 信号强度: {signal.signal_strength}
        </h4>
    </div>
    """, unsafe_allow_html=True)
    
    # 价格信息
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("当前价格", f"¥{signal.current_price:.2f}")
    with col2:
        st.metric("止损价", f"¥{signal.stop_loss_price:.2f}")
    with col3:
        st.metric("止盈价", f"¥{signal.take_profit_price:.2f}")
    with col4:
        st.metric("移动止盈触发", f"¥{signal.trailing_trigger_price:.2f}")
    
    # 条件满足情况
    st.markdown("**买入条件检查:**")
    
    condition_names = {
        'ma5_above_ma20': 'MA5 > MA20 (金叉)',
        'price_above_ma60': '价格 > MA60 (中期趋势)',
        'rsi_in_range': f'RSI在{V114G_STRATEGY_PARAMS.RSI_MIN}-{V114G_STRATEGY_PARAMS.RSI_MAX}区间',
        'volume_ratio_ok': f'量比 > {V114G_STRATEGY_PARAMS.VOLUME_RATIO_MIN}',
        'ma20_slope_positive': 'MA20斜率 > 0 (趋势向上)',
        'price_not_too_high': '价格未追高 (< MA5×1.05)',
    }
    
    cols = st.columns(3)
    for i, (key, name) in enumerate(condition_names.items()):
        is_met = signal.conditions_met.get(key, False)
        icon = "✅" if is_met else "❌"
        color = get_condition_color(is_met)
        with cols[i % 3]:
            st.markdown(f"<span style='color: {color};'>{icon} {name}</span>", unsafe_allow_html=True)
    
    st.caption(f"生成时间: {signal.generated_at.strftime('%Y-%m-%d %H:%M:%S')}")
    st.divider()


# ==========================================
# 卖出信号展示 (Requirements: 10.4)
# ==========================================

def render_sell_signals_section():
    """渲染卖出信号展示区域"""
    st.subheader("🔴 卖出信号")
    
    monitor = get_monitor()
    signal_engine = get_signal_engine()
    stock_data_cache = st.session_state.stock_data_cache
    
    positions = monitor.positions
    
    if not positions:
        st.info("📭 暂无持仓，无需检查卖出信号")
        return
    
    # 检查所有持仓的卖出信号
    all_sell_signals = []
    
    for code, position in positions.items():
        stock_data = stock_data_cache.get(code)
        if stock_data:
            signals = signal_engine.generate_sell_signals(position, stock_data)
            all_sell_signals.extend(signals)
    
    if not all_sell_signals:
        st.success("✅ 当前持仓无卖出信号")
        return
    
    # 按紧急程度分组
    high_urgency = [s for s in all_sell_signals if s.urgency == SellSignal.URGENCY_HIGH]
    medium_urgency = [s for s in all_sell_signals if s.urgency == SellSignal.URGENCY_MEDIUM]
    low_urgency = [s for s in all_sell_signals if s.urgency == SellSignal.URGENCY_LOW]
    
    # 统计
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("信号总数", len(all_sell_signals))
    with col2:
        if high_urgency:
            st.metric("🔴 紧急", len(high_urgency), delta="立即处理!", delta_color="inverse")
        else:
            st.metric("🔴 紧急", 0)
    with col3:
        st.metric("🟡 中等", len(medium_urgency))
    with col4:
        st.metric("🟢 低", len(low_urgency))
    
    st.divider()
    
    # 显示高紧急度信号
    if high_urgency:
        for signal in high_urgency:
            render_sell_signal_card(signal, "high")
    
    # 显示中等紧急度信号
    if medium_urgency:
        for signal in medium_urgency:
            render_sell_signal_card(signal, "medium")
    
    # 显示低紧急度信号
    if low_urgency:
        for signal in low_urgency:
            render_sell_signal_card(signal, "low")


def render_sell_signal_card(signal: SellSignal, urgency_level: str):
    """渲染单个卖出信号卡片"""
    signal_engine = get_signal_engine()
    recommendation = signal_engine.get_sell_recommendation(signal)
    
    # 紧急程度颜色配置
    urgency_config = {
        "high": {"icon": "🔴", "color": "#dc3545", "bg": "#4d1a1a"},
        "medium": {"icon": "🟡", "color": "#ffc107", "bg": "#4d3d1a"},
        "low": {"icon": "🟢", "color": "#28a745", "bg": "#1a4d3a"},
    }
    
    config = urgency_config.get(urgency_level, urgency_config["medium"])
    
    # 信号类型显示名称
    signal_type_names = {
        SellSignal.TYPE_STOP_LOSS: "止损",
        SellSignal.TYPE_TAKE_PROFIT: "止盈",
        SellSignal.TYPE_TRAILING_STOP: "移动止盈",
        SellSignal.TYPE_RSI_OVERBOUGHT: "RSI超买",
        SellSignal.TYPE_TREND_REVERSAL: "趋势反转",
        SellSignal.TYPE_TIMEOUT: "持仓超时",
    }
    
    signal_type_name = signal_type_names.get(signal.signal_type, signal.signal_type)
    
    # 信号卡片
    st.markdown(f"""
    <div style="background-color: {config['bg']}; padding: 15px; border-radius: 10px; 
                border-left: 5px solid {config['color']}; margin-bottom: 15px;">
        <h4 style="margin: 0; color: {config['color']};">
            {config['icon']} {signal.code} {signal.name} - {signal_type_name}
        </h4>
        <p style="margin: 5px 0 0 0; color: #fafafa;">{signal.reason}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 详细信息
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        pnl_color = "normal" if signal.pnl_pct >= 0 else "inverse"
        st.metric("盈亏", f"{signal.pnl_pct*100:.2f}%", delta_color=pnl_color)
    with col2:
        st.metric("当前价", f"¥{signal.current_price:.2f}")
    with col3:
        st.metric("成本价", f"¥{signal.cost_price:.2f}")
    with col4:
        st.metric("紧急程度", recommendation['urgency_description'])
    
    # 建议操作
    st.markdown(f"**建议操作:** {recommendation['action_description']}")
    st.markdown(f"**原因说明:** {recommendation['reason_explanation']}")
    
    st.caption(f"生成时间: {signal.generated_at.strftime('%Y-%m-%d %H:%M:%S')}")
    st.divider()



# ==========================================
# 技术指标面板 (Requirements: 8.1, 8.2, 8.3)
# ==========================================

def render_technical_indicators_section():
    """渲染技术指标面板"""
    st.subheader("📊 技术指标面板")
    
    monitor = get_monitor()
    stock_data_cache = st.session_state.stock_data_cache
    
    watchlist = monitor.watchlist
    
    if not watchlist:
        st.info("📭 监控列表为空，请先添加股票")
        return
    
    # 选择股票
    selected_code = st.selectbox(
        "选择股票查看详细指标",
        options=watchlist,
        key="tech_indicator_select"
    )
    
    if not selected_code:
        return
    
    stock_data = stock_data_cache.get(selected_code)
    
    if not stock_data:
        st.warning(f"⚠️ 暂无 {selected_code} 的数据，请刷新")
        return
    
    # 基本信息
    st.markdown(f"### {stock_data.code} {stock_data.name}")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        change_color = "normal" if stock_data.change_pct >= 0 else "inverse"
        st.metric(
            "当前价格",
            f"¥{stock_data.current_price:.2f}",
            delta=f"{stock_data.change_pct*100:.2f}%",
            delta_color=change_color
        )
    with col2:
        st.metric("成交量", f"{stock_data.volume:,}")
    with col3:
        st.metric("成交额", f"¥{stock_data.turnover/10000:.0f}万")
    with col4:
        st.metric("更新时间", stock_data.updated_at.strftime('%H:%M:%S'))
    
    st.divider()
    
    # 均线指标
    st.markdown("**均线指标**")
    
    # 检查v11.4g条件
    conditions = stock_data.check_buy_conditions()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        ma5_color = get_condition_color(conditions['ma5_above_ma20'])
        st.markdown(f"<span style='color: {ma5_color};'>MA5: ¥{stock_data.ma5:.2f}</span>", unsafe_allow_html=True)
    with col2:
        st.metric("MA10", f"¥{stock_data.ma10:.2f}")
    with col3:
        ma20_color = get_condition_color(conditions['ma20_slope_positive'])
        st.markdown(f"<span style='color: {ma20_color};'>MA20: ¥{stock_data.ma20:.2f}</span>", unsafe_allow_html=True)
    with col4:
        ma60_color = get_condition_color(conditions['price_above_ma60'])
        st.markdown(f"<span style='color: {ma60_color};'>MA60: ¥{stock_data.ma60:.2f}</span>", unsafe_allow_html=True)
    
    st.divider()
    
    # 动量指标
    st.markdown("**动量指标**")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        rsi_color = get_condition_color(conditions['rsi_in_range'])
        rsi_status = "适中" if conditions['rsi_in_range'] else ("超买" if stock_data.rsi > V114G_STRATEGY_PARAMS.RSI_MAX else "超卖")
        st.markdown(f"<span style='color: {rsi_color};'>RSI(14): {stock_data.rsi:.1f} ({rsi_status})</span>", unsafe_allow_html=True)
    with col2:
        vr_color = get_condition_color(conditions['volume_ratio_ok'])
        st.markdown(f"<span style='color: {vr_color};'>量比: {stock_data.volume_ratio:.2f}</span>", unsafe_allow_html=True)
    with col3:
        slope_color = get_condition_color(conditions['ma20_slope_positive'])
        slope_status = "向上" if stock_data.ma20_slope > 0 else "向下"
        st.markdown(f"<span style='color: {slope_color};'>MA20斜率: {stock_data.ma20_slope:.4f} ({slope_status})</span>", unsafe_allow_html=True)
    
    st.divider()
    
    # 资金流向
    st.markdown("**主力资金流向**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        flow_color = get_fund_flow_hex_color(stock_data.main_fund_flow)
        flow_status = "净流入" if stock_data.main_fund_flow > 0 else ("净流出" if stock_data.main_fund_flow < 0 else "持平")
        st.markdown(f"<span style='color: {flow_color};'>今日主力: {stock_data.main_fund_flow:.2f}万 ({flow_status})</span>", unsafe_allow_html=True)
    with col2:
        flow_5d_color = get_fund_flow_hex_color(stock_data.fund_flow_5d)
        flow_5d_status = "净流入" if stock_data.fund_flow_5d > 0 else ("净流出" if stock_data.fund_flow_5d < 0 else "持平")
        st.markdown(f"<span style='color: {flow_5d_color};'>5日累计: {stock_data.fund_flow_5d:.2f}万 ({flow_5d_status})</span>", unsafe_allow_html=True)
    
    st.divider()
    
    # v11.4g条件汇总
    st.markdown("**v11.4g买入条件检查**")
    
    conditions_met = sum(conditions.values())
    total_conditions = len(conditions)
    
    if conditions_met >= 6:
        st.success(f"✅ 满足 {conditions_met}/{total_conditions} 个条件 - 强买入信号 (强度100)")
    elif conditions_met >= 5:
        st.warning(f"⚠️ 满足 {conditions_met}/{total_conditions} 个条件 - 买入信号 (强度83)")
    else:
        st.info(f"📊 满足 {conditions_met}/{total_conditions} 个条件 - 暂无买入信号")
    
    # 条件详情
    condition_names = {
        'ma5_above_ma20': 'MA5 > MA20 (金叉)',
        'price_above_ma60': '价格 > MA60 (中期趋势)',
        'rsi_in_range': f'RSI在{V114G_STRATEGY_PARAMS.RSI_MIN}-{V114G_STRATEGY_PARAMS.RSI_MAX}区间',
        'volume_ratio_ok': f'量比 > {V114G_STRATEGY_PARAMS.VOLUME_RATIO_MIN}',
        'ma20_slope_positive': 'MA20斜率 > 0 (趋势向上)',
        'price_not_too_high': '价格未追高 (< MA5×1.05)',
    }
    
    cols = st.columns(3)
    for i, (key, name) in enumerate(condition_names.items()):
        is_met = conditions.get(key, False)
        icon = "✅" if is_met else "❌"
        color = get_condition_color(is_met)
        with cols[i % 3]:
            st.markdown(f"<span style='color: {color};'>{icon} {name}</span>", unsafe_allow_html=True)


# ==========================================
# 数据刷新功能 (Requirements: 10.5)
# ==========================================

def refresh_data():
    """刷新所有数据"""
    monitor = get_monitor()
    data_fetcher = get_data_fetcher()
    
    watchlist = monitor.watchlist
    positions = monitor.positions
    
    # 合并需要获取数据的股票代码
    all_codes = list(set(watchlist) | set(positions.keys()))
    
    if not all_codes:
        return
    
    # 获取股票数据
    stock_data_dict = data_fetcher.fetch_stock_data_batch(all_codes)
    
    # 更新缓存
    st.session_state.stock_data_cache = stock_data_dict
    
    # 更新持仓价格
    for code, stock_data in stock_data_dict.items():
        if code in positions:
            monitor.update_position_price(code, stock_data.current_price)
    
    st.session_state.last_refresh_time = datetime.now()


def render_refresh_section():
    """渲染刷新控制区域"""
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        last_refresh = st.session_state.last_refresh_time
        if last_refresh:
            st.caption(f"🕐 最后刷新: {last_refresh.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            st.caption("🕐 尚未刷新数据")
    
    with col2:
        auto_refresh = st.checkbox(
            "自动刷新",
            value=st.session_state.auto_refresh,
            key="auto_refresh_checkbox",
            help=f"每{MONITOR_CONFIG.refresh_interval}秒自动刷新"
        )
        st.session_state.auto_refresh = auto_refresh
    
    with col3:
        if st.button("🔄 手动刷新", key="manual_refresh_btn", type="primary"):
            with st.spinner("正在刷新数据..."):
                try:
                    refresh_data()
                    st.success("✅ 数据刷新成功")
                except Exception as e:
                    st.error(f"❌ 刷新失败: {e}")
                    logger.error(f"数据刷新失败: {e}")


# ==========================================
# 策略参数显示
# ==========================================

def render_strategy_params_section():
    """渲染策略参数显示区域"""
    with st.expander("⚙️ v11.4g策略参数", expanded=False):
        params = V114G_STRATEGY_PARAMS
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**风控参数**")
            st.markdown(f"""
            | 参数 | 值 |
            |------|-----|
            | 止损 | `{params.STOP_LOSS_PCT*100:.1f}%` |
            | 止盈 | `+{params.TAKE_PROFIT_PCT*100:.0f}%` |
            | 移动止盈触发 | `+{params.TRAILING_TRIGGER_PCT*100:.0f}%` |
            | 移动止盈回撤 | `{params.TRAILING_STOP_PCT*100:.1f}%` |
            | 最大持仓天数 | `{params.MAX_HOLDING_DAYS}天` |
            """)
        
        with col2:
            st.markdown("**买入参数**")
            st.markdown(f"""
            | 参数 | 值 |
            |------|-----|
            | RSI范围 | `{params.RSI_MIN}-{params.RSI_MAX}` |
            | RSI超买 | `>{params.RSI_OVERBOUGHT}` |
            | 最小量比 | `>{params.VOLUME_RATIO_MIN}` |
            | 追高限制 | `<MA5×{1+params.MAX_PRICE_ABOVE_MA5_PCT:.2f}` |
            | 最少条件数 | `{params.MIN_CONDITIONS_FOR_SIGNAL}个` |
            """)



# ==========================================
# 主函数
# ==========================================

def main():
    """实时监控页面主函数"""
    st.set_page_config(
        page_title="实时监控 - MiniQuant-Lite",
        page_icon="📡",
        layout="wide"
    )
    
    st.title("📡 实时监控")
    st.markdown("基于v11.4g科技股策略的实时买卖信号监控")
    
    # 初始化 session state
    init_session_state()
    
    st.divider()
    
    # ========== 市场状态 ==========
    render_market_status_section()
    
    # ========== 刷新控制 ==========
    render_refresh_section()
    
    st.divider()
    
    # ========== 主要内容区域 - 使用标签页 ==========
    tab1, tab2, tab3, tab4 = st.tabs(["📋 监控列表", "💼 持仓管理", "📊 信号面板", "🔧 技术指标"])
    
    with tab1:
        render_watchlist_management_section()
    
    with tab2:
        render_position_management_section()
    
    with tab3:
        # 信号面板 - 买入和卖出信号
        col1, col2 = st.columns(2)
        
        with col1:
            render_buy_signals_section()
        
        with col2:
            render_sell_signals_section()
    
    with tab4:
        render_technical_indicators_section()
    
    st.divider()
    
    # ========== 策略参数 ==========
    render_strategy_params_section()
    
    # ========== 使用说明 ==========
    st.divider()
    
    with st.expander("📖 使用说明", expanded=False):
        st.markdown("""
        **实时监控使用指南**
        
        **1. 添加监控股票**
        - 在"监控列表"标签页输入6位股票代码
        - 支持沪深A股（以0、3、6开头）
        - 最多监控20只股票
        
        **2. 添加持仓**
        - 在"持仓管理"标签页添加您的持仓信息
        - 输入股票代码、名称、成本价、数量和买入日期
        - 系统会自动计算盈亏和检查卖出信号
        
        **3. 查看信号**
        - "信号面板"显示买入和卖出信号
        - 买入信号：满足v11.4g策略条件的股票
        - 卖出信号：触发止损、止盈等条件的持仓
        
        **4. 技术指标**
        - "技术指标"标签页显示详细的技术分析
        - 包括均线、RSI、量比、资金流向等
        - 绿色表示满足买入条件，红色表示不满足
        
        **5. 数据刷新**
        - 点击"手动刷新"获取最新数据
        - 开启"自动刷新"每30秒自动更新
        - 交易时间外显示最后可用数据
        
        **v11.4g策略买入条件（需满足至少5个）：**
        1. MA5 > MA20（金叉）
        2. 价格 > MA60（中期趋势向上）
        3. RSI在44-70区间（动量适中）
        4. 量比 > 1.1（放量确认）
        5. MA20斜率 > 0（趋势向上）
        6. 价格 < MA5×1.05（避免追高）
        
        **卖出条件：**
        - 🔴 止损：亏损达到-4.6%
        - 🟢 止盈：盈利达到+22%
        - 🟡 移动止盈：盈利+9%后回撤2.8%
        - 📊 RSI超买：RSI>80且盈利
        - 📉 趋势反转：MA5<MA20且亏损
        - ⏰ 持仓超时：持仓≥15天
        """)
    
    # ========== 自动刷新逻辑 ==========
    if st.session_state.auto_refresh:
        market_status = get_market_status()
        if market_status.is_open:
            # 检查是否需要刷新
            last_refresh = st.session_state.last_refresh_time
            if last_refresh is None or (datetime.now() - last_refresh).total_seconds() >= MONITOR_CONFIG.refresh_interval:
                try:
                    refresh_data()
                except Exception as e:
                    logger.error(f"自动刷新失败: {e}")
            
            # 设置自动刷新
            import time as time_module
            time_module.sleep(0.1)  # 短暂延迟避免过于频繁
            st.rerun()


if __name__ == "__main__":
    main()
