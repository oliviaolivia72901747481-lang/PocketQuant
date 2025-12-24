"""
MiniQuant-Lite 持仓管理页面

提供持仓管理功能：
- 持仓列表展示（含盈亏状态）
- 添加/删除持仓
- 卖出信号展示
- 导出 CSV

Requirements: 4.1, 4.2, 4.3, 4.4
"""

import streamlit as st
import sys
import os
from datetime import date, datetime
from typing import List, Dict, Any
import pandas as pd

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config.settings import get_settings
from config.stock_pool import get_watchlist
from core.data_feed import DataFeed
from core.position_tracker import PositionTracker, Holding, PnLResult
from core.sell_signal_checker import SellSignalChecker, SellSignal
from core.logging_config import get_logger

logger = get_logger(__name__)


def get_data_feed() -> DataFeed:
    """获取 DataFeed 实例"""
    settings = get_settings()
    return DataFeed(
        raw_path=settings.path.get_raw_path(),
        processed_path=settings.path.get_processed_path()
    )


def get_current_prices(data_feed: DataFeed, codes: List[str], use_realtime: bool = True) -> Dict[str, float]:
    """
    获取股票最新价格
    
    Args:
        data_feed: 数据源
        codes: 股票代码列表
        use_realtime: 是否使用实时行情（默认True）
    
    Returns:
        {股票代码: 最新价格}
    """
    prices = {}
    
    if use_realtime:
        # 检查缓存（5分钟内有效）
        cache_key = 'realtime_prices_cache'
        cache_time_key = 'realtime_prices_cache_time'
        
        if cache_key in st.session_state and cache_time_key in st.session_state:
            cache_age = (datetime.now() - st.session_state[cache_time_key]).total_seconds()
            if cache_age < 300:  # 5分钟缓存
                cached_prices = st.session_state[cache_key]
                for code in codes:
                    if code in cached_prices:
                        prices[code] = cached_prices[code]
                
                # 如果所有股票都在缓存中，直接返回
                if len(prices) == len(codes):
                    logger.info(f"使用缓存的实时行情: {len(prices)} 只股票")
                    return prices
        
        # 尝试获取实时行情
        try:
            import akshare as ak
            
            # 获取全市场实时行情
            df = ak.stock_zh_a_spot_em()
            
            if df is not None and not df.empty:
                # 创建代码到价格的映射（缓存全部数据）
                all_prices = {}
                for _, row in df.iterrows():
                    all_prices[row['代码']] = float(row['最新价'])
                
                # 更新缓存
                st.session_state[cache_key] = all_prices
                st.session_state[cache_time_key] = datetime.now()
                
                # 获取需要的股票价格
                for code in codes:
                    if code in all_prices:
                        prices[code] = all_prices[code]
                    else:
                        # 如果实时行情中没有，使用本地数据
                        local_df = data_feed.load_processed_data(code)
                        if local_df is not None and not local_df.empty:
                            prices[code] = float(local_df['close'].iloc[-1])
                
                logger.info(f"获取实时行情成功: {len(prices)} 只股票")
                return prices
                
        except Exception as e:
            logger.warning(f"获取实时行情失败，使用本地数据: {e}")
    
    # 使用本地历史数据的最新收盘价
    for code in codes:
        df = data_feed.load_processed_data(code)
        if df is not None and not df.empty:
            latest_price = float(df['close'].iloc[-1])
            prices[code] = latest_price
    
    return prices


def get_realtime_price_single(code: str) -> float:
    """
    获取单只股票的实时价格
    
    Args:
        code: 股票代码
    
    Returns:
        实时价格，获取失败返回 0
    """
    # 先检查缓存
    cache_key = 'realtime_prices_cache'
    if cache_key in st.session_state:
        cached_prices = st.session_state[cache_key]
        if code in cached_prices:
            return cached_prices[code]
    
    try:
        import akshare as ak
        
        df = ak.stock_zh_a_spot_em()
        if df is not None and not df.empty:
            matches = df[df['代码'] == code]
            if not matches.empty:
                return float(matches['最新价'].iloc[0])
    except Exception as e:
        logger.warning(f"获取 {code} 实时价格失败: {e}")
    
    return 0


def render_sell_signals(tracker: PositionTracker, data_feed: DataFeed):
    """
    渲染卖出信号区域
    
    Args:
        tracker: 持仓跟踪器
        data_feed: 数据源
    """
    positions = tracker.get_all_positions()
    
    if not positions:
        return
    
    st.subheader("🚨 卖出信号")
    
    # 检查卖出信号
    checker = SellSignalChecker(data_feed)
    signals = checker.check_all_positions(positions)
    
    if not signals:
        st.success("✅ 当前持仓无卖出信号")
        return
    
    # 按紧急程度分组显示
    high_urgency = [s for s in signals if s.urgency == "high"]
    medium_urgency = [s for s in signals if s.urgency == "medium"]
    low_urgency = [s for s in signals if s.urgency == "low"]
    
    # 高紧急度信号（止损）
    if high_urgency:
        for signal in high_urgency:
            st.error(f"""
            🚨 **紧急卖出 - {signal.code} {signal.name}**
            
            {signal.exit_reason}
            
            - 买入价: ¥{signal.holding.buy_price:.2f}
            - 当前价: ¥{signal.current_price:.2f}
            - 盈亏: {signal.pnl_pct:.1%}
            - 持仓: {signal.holding.quantity} 股
            
            ⚠️ **建议立即止损卖出！**
            """)
    
    # 中等紧急度信号（策略卖出）
    if medium_urgency:
        for signal in medium_urgency:
            st.warning(f"""
            ⚠️ **策略卖出 - {signal.code} {signal.name}**
            
            {signal.exit_reason}
            
            - 买入价: ¥{signal.holding.buy_price:.2f}
            - 当前价: ¥{signal.current_price:.2f}
            - 盈亏: {signal.pnl_pct:.1%}
            - 指标值: {signal.indicator_value:.2f}
            """)
    
    # 低紧急度信号
    if low_urgency:
        for signal in low_urgency:
            st.info(f"""
            💡 **建议关注 - {signal.code} {signal.name}**
            
            {signal.exit_reason}
            """)


def render_position_list(tracker: PositionTracker, data_feed: DataFeed):
    """
    渲染持仓列表
    
    Args:
        tracker: 持仓跟踪器
        data_feed: 数据源
    """
    st.subheader("📊 持仓列表")
    
    positions = tracker.get_all_positions()
    
    if not positions:
        st.info("📭 暂无持仓记录，请添加持仓")
        return
    
    # 添加刷新按钮和实时行情开关
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        # 显示数据更新时间
        if 'last_price_update' not in st.session_state:
            st.session_state['last_price_update'] = datetime.now()
        
        update_time = st.session_state['last_price_update'].strftime('%Y-%m-%d %H:%M:%S')
        
        # 判断数据来源
        use_realtime = st.session_state.get('use_realtime_price', True)
        data_source = "实时行情" if use_realtime else "本地历史数据"
        st.caption(f"💡 现价更新时间: {update_time} | 数据来源: {data_source}")
    
    with col2:
        # 实时行情开关
        use_realtime = st.checkbox(
            "🔴 刷新价格", 
            value=st.session_state.get('use_realtime_price', True),
            key="use_realtime_checkbox",
            help="勾选后使用 AkShare 实时行情，取消勾选使用本地历史数据"
        )
        st.session_state['use_realtime_price'] = use_realtime
    
    with col3:
        if st.button("🔄 刷新价格", key="refresh_prices", help="重新加载最新价格"):
            st.session_state['last_price_update'] = datetime.now()
            st.rerun()
    
    # 获取当前价格
    codes = [p.code for p in positions]
    
    with st.spinner("正在获取最新价格..."):
        prices = get_current_prices(data_feed, codes, use_realtime=use_realtime)
    
    # 构建表格数据
    data = []
    for holding in positions:
        # 使用最新价格
        current_price = prices.get(holding.code, holding.buy_price)
        pnl = tracker.calculate_pnl(holding, current_price)
        
        data.append({
            'code': holding.code,
            'name': holding.name,
            'buy_price': holding.buy_price,
            'current_price': current_price,
            'quantity': holding.quantity,
            'cost_value': pnl.cost_value,
            'market_value': pnl.market_value,
            'pnl_amount': pnl.pnl_amount,
            'pnl_pct': pnl.pnl_pct,
            'holding_days': pnl.holding_days,
            'strategy': holding.strategy,
            'buy_date': holding.buy_date.strftime('%Y-%m-%d'),
            'is_stop_loss': pnl.is_stop_loss,
            'note': holding.note
        })
    
    df = pd.DataFrame(data)
    
    # 组合汇总
    summary = tracker.get_portfolio_summary(prices)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("持仓数量", f"{summary['position_count']} 只")
    with col2:
        st.metric("总成本", f"¥{summary['total_cost']:,.0f}")
    with col3:
        st.metric("总市值", f"¥{summary['total_market_value']:,.0f}")
    with col4:
        pnl_color = "normal" if summary['total_pnl'] >= 0 else "inverse"
        st.metric(
            "总盈亏", 
            f"¥{summary['total_pnl']:,.0f}",
            delta=f"{summary['total_pnl_pct']:.1%}",
            delta_color=pnl_color
        )
    
    if summary['stop_loss_count'] > 0:
        st.error(f"⚠️ 有 {summary['stop_loss_count']} 只股票触发止损线！")
    
    st.divider()
    
    # 显示持仓表格（移除背景色高亮，保持统一深色背景）
    display_df = df[['code', 'name', 'buy_price', 'current_price', 'quantity', 
                     'pnl_amount', 'pnl_pct', 'holding_days', 'strategy', 'buy_date']].copy()
    
    # 将盈亏百分比转换为百分比形式（0.05 -> 5.0）
    display_df['pnl_pct'] = display_df['pnl_pct'] * 100
    
    display_df.columns = ['代码', '名称', '买入价', '现价', '数量', 
                          '盈亏金额', '盈亏%', '持仓天数', '策略', '买入日期']
    
    # 直接显示表格，不应用背景色样式
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            '买入价': st.column_config.NumberColumn('买入价', format='¥%.2f'),
            '现价': st.column_config.NumberColumn('现价', format='¥%.2f'),
            '盈亏金额': st.column_config.NumberColumn('盈亏金额', format='¥%.0f'),
            '盈亏%': st.column_config.NumberColumn('盈亏%', format='%.2f%%'),
        }
    )
    
    # 删除持仓
    st.divider()
    st.markdown("**删除持仓**")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        delete_code = st.selectbox(
            "选择要删除的股票",
            options=[f"{p.code} - {p.name}" for p in positions],
            key="delete_position_select"
        )
    with col2:
        if st.button("🗑️ 删除", type="secondary", key="delete_position_btn"):
            if delete_code:
                code = delete_code.split(" - ")[0]
                success, msg = tracker.remove_position(code)
                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)


def render_add_position_form(tracker: PositionTracker, data_feed: DataFeed):
    """
    渲染添加持仓表单
    
    Args:
        tracker: 持仓跟踪器
        data_feed: 数据源
    """
    st.subheader("➕ 添加持仓")
    
    with st.form("add_position_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            code = st.text_input(
                "股票代码",
                placeholder="例如: 600036",
                max_chars=6,
                help="6位股票代码"
            )
            
            buy_price = st.number_input(
                "买入价格",
                min_value=0.01,
                value=10.0,
                step=0.01,
                format="%.2f",
                help="买入时的成交价格"
            )
            
            quantity = st.number_input(
                "持仓数量（股）",
                min_value=100,
                value=100,
                step=100,
                help="持仓股数，通常为100的整数倍"
            )
        
        with col2:
            # 尝试获取股票名称
            name = st.text_input(
                "股票名称",
                placeholder="例如: 招商银行",
                help="股票名称，可手动输入"
            )
            
            buy_date = st.date_input(
                "买入日期",
                value=date.today(),
                max_value=date.today(),
                help="买入成交日期"
            )
            
            strategy = st.selectbox(
                "使用策略",
                options=["RSRS", "RSI"],
                help="买入时使用的策略，用于判断卖出信号"
            )
        
        note = st.text_input(
            "备注（可选）",
            placeholder="例如: 突破买入",
            help="可选的备注信息"
        )
        
        submitted = st.form_submit_button("✅ 添加持仓", type="primary")
        
        if submitted:
            if not code or len(code) != 6 or not code.isdigit():
                st.error("请输入有效的6位股票代码")
                return
            
            if not name:
                # 尝试从数据中获取名称
                df = data_feed.load_processed_data(code)
                if df is not None and 'name' in df.columns:
                    name = df['name'].iloc[0]
                else:
                    name = f"股票{code}"
            
            holding = Holding(
                code=code,
                name=name,
                buy_price=buy_price,
                buy_date=buy_date,
                quantity=quantity,
                strategy=strategy,
                note=note
            )
            
            success, msg = tracker.add_position(holding)
            
            if success:
                st.success(f"✅ 成功添加持仓: {code} {name}")
                st.rerun()
            else:
                st.error(f"❌ 添加失败: {msg}")


def render_export_section(tracker: PositionTracker):
    """
    渲染导出区域
    
    Args:
        tracker: 持仓跟踪器
    """
    st.subheader("📥 导出持仓")
    
    positions = tracker.get_all_positions()
    
    if not positions:
        st.info("暂无持仓可导出")
        return
    
    csv_data = tracker.export_csv()
    
    st.download_button(
        label="📥 导出 CSV",
        data=csv_data,
        file_name=f"positions_{date.today().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        key="export_positions"
    )


def main():
    """持仓管理页面主函数"""
    st.set_page_config(
        page_title="持仓管理 - MiniQuant-Lite",
        page_icon="💼",
        layout="wide"
    )
    
    st.title("💼 持仓管理")
    st.markdown("管理您的持仓，跟踪盈亏，获取卖出信号")
    
    st.divider()
    
    # 初始化
    data_feed = get_data_feed()
    tracker = PositionTracker()
    
    # ========== 卖出信号（最高优先级）==========
    render_sell_signals(tracker, data_feed)
    
    st.divider()
    
    # ========== 持仓列表 ==========
    render_position_list(tracker, data_feed)
    
    st.divider()
    
    # ========== 添加持仓 ==========
    render_add_position_form(tracker, data_feed)
    
    st.divider()
    
    # ========== 导出 ==========
    render_export_section(tracker)
    
    # ========== 使用说明 ==========
    st.divider()
    st.subheader("📖 使用说明")
    
    with st.expander("如何使用持仓管理？", expanded=False):
        st.markdown("""
        **添加持仓：**
        1. 在"添加持仓"区域输入股票代码、买入价格、数量等信息
        2. 选择买入时使用的策略（RSRS 或 RSI）
        3. 点击"添加持仓"按钮
        
        **查看卖出信号：**
        - 系统会自动检查所有持仓的卖出条件
        - 🚨 红色警告：触发止损线（亏损 ≥ 6%），建议立即卖出
        - ⚠️ 黄色警告：策略卖出信号（RSRS < -0.7 或 RSI > 70）
        
        **删除持仓：**
        - 在持仓列表下方选择要删除的股票
        - 点击"删除"按钮
        
        **导出数据：**
        - 点击"导出 CSV"按钮下载持仓记录
        """)
    
    with st.expander("卖出信号说明", expanded=False):
        st.markdown("""
        **止损信号（高优先级）：**
        - 当持仓亏损 ≥ 6% 时触发
        - 建议立即止损卖出，控制风险
        
        **RSRS 卖出信号：**
        - 当 RSRS 标准分 < -0.7 时触发
        - 表示市场情绪转弱，建议卖出
        
        **RSI 卖出信号：**
        - 当 RSI > 70 时触发
        - 表示股票超买，建议止盈
        """)


if __name__ == "__main__":
    main()
