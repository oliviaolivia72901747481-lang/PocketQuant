"""
MiniQuant-Lite 每日信号页面

提供每日交易信号功能：
- 早安确认清单（Pre-market Checklist）
- 信号表格（含新闻链接、财报窗口期警告）
- 高费率预警红色高亮
- 数据新鲜度检测（Data Freshness Watchdog）
- 交易日历感知（Market Calendar Awareness）

Requirements: 7.6, 7.7, 7.10, 12.1, 12.2, 12.3
"""

import streamlit as st
import sys
import os
import glob
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any
import pandas as pd

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config.settings import get_settings
from config.stock_pool import get_watchlist
from core.data_feed import DataFeed
from core.signal_generator import SignalGenerator, TradingSignal, SignalType
from core.screener import Screener
from core.signal_store import SignalStore
from core.logging_config import get_logger

logger = get_logger(__name__)


def get_data_feed() -> DataFeed:
    """获取 DataFeed 实例"""
    settings = get_settings()
    return DataFeed(
        raw_path=settings.path.get_raw_path(),
        processed_path=settings.path.get_processed_path()
    )


def check_data_freshness() -> Dict[str, Any]:
    """
    检查数据新鲜度（Data Freshness Watchdog）
    
    Returns:
        {
            'is_stale': bool,           # 数据是否过期
            'last_data_date': date,     # 最后数据日期
            'days_old': int,            # 数据已过期天数
            'message': str,             # 状态消息
        }
    """
    settings = get_settings()
    processed_path = settings.path.get_processed_path()
    
    try:
        csv_files = glob.glob(os.path.join(processed_path, "*.csv"))
        
        if not csv_files:
            return {
                'is_stale': True,
                'last_data_date': None,
                'days_old': 999,
                'message': '未找到任何数据文件，请先下载数据'
            }
        
        sample_file = csv_files[0]
        df = pd.read_csv(sample_file)
        
        if df.empty or 'date' not in df.columns:
            return {
                'is_stale': True,
                'last_data_date': None,
                'days_old': 999,
                'message': '数据文件格式异常'
            }
        
        last_date_str = df['date'].iloc[-1]
        last_data_date = datetime.strptime(last_date_str, '%Y-%m-%d').date()
        
        today = date.today()
        days_old = (today - last_data_date).days
        is_stale = days_old > 3
        
        if is_stale:
            message = f"数据已过期：最后更新于 {last_data_date.strftime('%Y-%m-%d')}（{days_old} 天前）"
        else:
            message = f"数据正常：最后更新于 {last_data_date.strftime('%Y-%m-%d')}"
        
        return {
            'is_stale': is_stale,
            'last_data_date': last_data_date,
            'days_old': days_old,
            'message': message
        }
        
    except Exception as e:
        logger.error(f"检查数据新鲜度失败: {e}")
        return {
            'is_stale': True,
            'last_data_date': None,
            'days_old': 999,
            'message': f'检查数据失败: {str(e)}'
        }


def check_trading_day() -> Dict[str, Any]:
    """
    检查今天是否为交易日（Market Calendar Awareness）
    
    Returns:
        {
            'is_trading_day': bool,     # 今天是否为交易日
            'message': str,             # 状态消息
            'next_trading_day': date,   # 下一个交易日
        }
    """
    try:
        import akshare as ak
        
        today = date.today()
        trade_dates_df = ak.tool_trade_date_hist_sina()
        
        if trade_dates_df is None or trade_dates_df.empty:
            return {
                'is_trading_day': True,
                'message': '无法获取交易日历',
                'next_trading_day': None
            }
        
        trade_dates = pd.to_datetime(trade_dates_df['trade_date']).dt.date.tolist()
        is_trading_day = today in trade_dates
        
        if is_trading_day:
            return {
                'is_trading_day': True,
                'message': '今天是交易日',
                'next_trading_day': today
            }
        else:
            next_trading_day = None
            for td in trade_dates:
                if td > today:
                    next_trading_day = td
                    break
            
            weekday = today.weekday()
            reason = "周末" if weekday >= 5 else "节假日"
            
            return {
                'is_trading_day': False,
                'message': f'今天是{reason}休市日',
                'next_trading_day': next_trading_day
            }
            
    except Exception as e:
        logger.error(f"检查交易日历失败: {e}")
        return {
            'is_trading_day': True,
            'message': f'无法获取交易日历: {str(e)}',
            'next_trading_day': None
        }


def render_data_freshness_warning() -> bool:
    """
    渲染数据新鲜度警告
    
    Returns:
        True 如果数据过期且今天是交易日
    """
    freshness = check_data_freshness()
    trading_day = check_trading_day()
    
    if freshness['is_stale'] and trading_day['is_trading_day']:
        st.error(f"""
        🚫 **数据已过期，信号可能无效！**
        
        本地数据最后更新于 **{freshness['last_data_date'].strftime('%Y-%m-%d') if freshness['last_data_date'] else '未知'}**
        （已过期 {freshness['days_old']} 天）
        
        ⚠️ **请先前往"数据管理"页面更新数据后再生成信号！**
        """)
        return True
    
    return False


def render_market_holiday_notice() -> bool:
    """
    渲染休市安民告示
    
    Returns:
        True 如果今天是非交易日
    """
    trading_day = check_trading_day()
    
    if not trading_day['is_trading_day']:
        next_day_str = ""
        if trading_day['next_trading_day']:
            next_day_str = f"下一个交易日：**{trading_day['next_trading_day'].strftime('%Y-%m-%d')}**"
        
        st.info(f"""
        ☕ **{trading_day['message']}，好好休息，不用看盘**
        
        {next_day_str}
        
        💡 今天生成的信号将用于下一个交易日，请注意时效性。
        """)
        return True
    
    return False


def render_premarket_checklist():
    """
    渲染早安确认清单（Pre-market Checklist）
    
    设计原则：晚上的信号无法预知次日早晨的突发利空
    提醒用户在 9:25 分前进行最后一次人工确认
    
    Requirements: 7.10
    """
    st.warning("""
    ☀️ **早安确认清单 (Pre-market Checklist)**
    
    在 **9:25 集合竞价结束前**，请完成以下确认：
    
    - [ ] 昨夜美股是否大跌？（道指跌幅 > 2% 需警惕）
    - [ ] 集合竞价是否大幅低开？（低开 > 2% 建议观望）
    - [ ] 是否有突发利空新闻？（点击下方新闻链接快速扫一眼）
    - [ ] 个股是否有停牌、复牌等特殊情况？
    
    ⚠️ **如有异常，建议撤销条件单，改为观望**
    """)


def render_signal_card(signal: TradingSignal, index: int):
    """
    渲染单个信号卡片
    
    Args:
        signal: TradingSignal 对象
        index: 信号索引
        
    Requirements: 7.6, 7.7, 12.1, 12.2, 12.3
    """
    # 信号类型图标
    signal_emoji = "🟢" if signal.signal_type == SignalType.BUY else "🔴" if signal.signal_type == SignalType.SELL else "⚪"
    
    # 创建卡片容器
    with st.container():
        # 标题行
        col1, col2, col3 = st.columns([3, 2, 1])
        
        with col1:
            st.markdown(f"### {signal_emoji} {signal.code} {signal.name}")
            st.markdown(f"**信号类型**: {signal.signal_type.value}")
        
        with col2:
            st.markdown(f"**建议价格**: ¥{signal.price_range[0]:.2f} - ¥{signal.price_range[1]:.2f}")
            st.markdown(f"**📌 限价上限**: ¥{signal.limit_cap:.2f}")
            st.caption("（建议挂单价格，防止追高）")
        
        with col3:
            st.markdown(f"**交易金额**: ¥{signal.trade_amount:,.0f}")
            st.markdown(f"**费率**: {signal.actual_fee_rate:.4%}")
        
        # 信号依据
        st.markdown(f"**信号依据**: {signal.reason}")
        
        # 警告区域
        col1, col2 = st.columns(2)
        
        with col1:
            # 新闻链接（替代 AI 分析）
            st.markdown(f"""
            <div style="background-color: #f0f8ff; padding: 15px; border-radius: 8px; margin: 10px 0;">
                <b>📰 新闻快查</b><br>
                <a href="{signal.news_url}" target="_blank">🔗 东方财富个股资讯</a><br>
                <small>人眼扫一遍标题只需 10 秒</small>
            </div>
            """, unsafe_allow_html=True)
            
            # 新增：查看最新公告链接（手动确认机制）
            announcement_url = f"https://data.eastmoney.com/notices/stock/{signal.code}.html"
            st.markdown(f"""
            <div style="background-color: #fff8e1; padding: 15px; border-radius: 8px; margin: 10px 0;">
                <b>📋 公告确认</b><br>
                <a href="{announcement_url}" target="_blank">🔗 查看最新公告</a><br>
                <small>⚠️ 请确认无重大利空公告后再下单</small>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            # 财报窗口期警告
            if signal.in_report_window:
                st.error(f"""
                ⚠️ **财报窗口期警告**
                
                {signal.report_warning if signal.report_warning else '该股票处于财报披露窗口期，建议规避'}
                """)
            
            # 高费率预警
            if signal.high_fee_warning:
                st.markdown(f"""
                <div style="background-color: #ffcccc; padding: 15px; border-radius: 8px; margin: 10px 0;">
                    ⚠️ <b>高费率预警</b><br>
                    交易金额: ¥{signal.trade_amount:,.0f}<br>
                    实际费率: {signal.actual_fee_rate:.4%}<br>
                    <small>低于最小交易门槛，手续费磨损较高</small>
                </div>
                """, unsafe_allow_html=True)
        
        st.divider()


def render_signal_table(signals: List[TradingSignal]):
    """
    渲染信号表格
    
    Args:
        signals: 信号列表
        
    Requirements: 7.6, 7.7
    """
    if not signals:
        st.info("📭 今日无操作建议")
        return
    
    st.subheader(f"📡 今日交易信号（共 {len(signals)} 个）")
    
    # 统计信息
    buy_count = sum(1 for s in signals if s.signal_type == SignalType.BUY)
    sell_count = sum(1 for s in signals if s.signal_type == SignalType.SELL)
    report_window_count = sum(1 for s in signals if s.in_report_window)
    high_fee_count = sum(1 for s in signals if s.high_fee_warning)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("买入信号", f"{buy_count} 个")
    with col2:
        st.metric("卖出信号", f"{sell_count} 个")
    with col3:
        st.metric("财报窗口期", f"{report_window_count} 个", delta="需注意" if report_window_count > 0 else None, delta_color="inverse")
    with col4:
        st.metric("高费率预警", f"{high_fee_count} 个", delta="需注意" if high_fee_count > 0 else None, delta_color="inverse")
    
    st.divider()
    
    # 渲染每个信号卡片
    for i, signal in enumerate(signals):
        render_signal_card(signal, i)


def render_signal_summary_table(signals: List[TradingSignal]):
    """
    渲染信号汇总表格（简洁版）
    
    Args:
        signals: 信号列表
    """
    if not signals:
        return
    
    st.subheader("📋 信号汇总表")
    
    # 人机协同提示
    st.info("""
    ⚠️ **人机协同提醒**：系统已自动过滤财报窗口期，但请在下单前完成最后一步人工确认：
    1. 点击「新闻链接」扫一眼标题（10秒）
    2. 点击「公告确认」检查有无重大利空
    3. 确认无异常后再将信号放入条件单
    """)
    
    # 转换为 DataFrame
    data = []
    for signal in signals:
        # 生成公告链接
        announcement_url = f"https://data.eastmoney.com/notices/stock/{signal.code}.html"
        
        row = {
            '股票代码': signal.code,
            '股票名称': signal.name,
            '信号类型': signal.signal_type.value,
            '限价上限': f"¥{signal.limit_cap:.2f}",
            '交易金额': f"¥{signal.trade_amount:,.0f}",
            '费率': f"{signal.actual_fee_rate:.4%}",
            '财报窗口期': '⚠️ 是' if signal.in_report_window else '否',
            '高费率预警': '⚠️ 是' if signal.high_fee_warning else '否',
            '新闻链接': signal.news_url,
            '公告确认': announcement_url
        }
        data.append(row)
    
    df = pd.DataFrame(data)
    
    # 高亮显示
    def highlight_warnings(row):
        styles = [''] * len(row)
        
        # 财报窗口期高亮
        if '是' in str(row.get('财报窗口期', '')):
            styles = ['background-color: #fff3cd'] * len(row)
        
        # 高费率预警高亮（红色）
        if '是' in str(row.get('高费率预警', '')):
            styles = ['background-color: #ffcccc'] * len(row)
        
        return styles
    
    # 显示表格
    st.dataframe(
        df.style.apply(highlight_warnings, axis=1),
        use_container_width=True,
        hide_index=True,
        column_config={
            '新闻链接': st.column_config.LinkColumn('新闻链接', display_text='🔗 新闻'),
            '公告确认': st.column_config.LinkColumn('公告确认', display_text='📋 公告')
        }
    )


def render_historical_signal_table(df: pd.DataFrame):
    """
    渲染历史信号表格
    
    使用 Streamlit 原生 column_config 实现样式
    
    Args:
        df: 历史信号 DataFrame
        
    Requirements: 3.1, 3.2, 3.3, 3.4, 3.5
    """
    # 添加显示用的列
    display_df = df.copy()
    
    # 信号类型添加 emoji
    display_df['信号'] = display_df['signal_type'].apply(
        lambda x: f"🟢 {x}" if x == "买入" else f"🔴 {x}"
    )
    
    # 警告标识
    display_df['警告'] = display_df.apply(
        lambda row: "⚠️ 财报" if row['in_report_window'] else (
            "⚠️ 高费率" if row['high_fee_warning'] else ""
        ),
        axis=1
    )
    
    # 选择显示列
    display_columns = [
        'generated_date', 'code', 'name', '信号', 
        'limit_cap', 'reason', '警告'
    ]
    
    st.dataframe(
        display_df[display_columns],
        use_container_width=True,
        hide_index=True,
        column_config={
            'generated_date': st.column_config.DateColumn('日期', format='YYYY-MM-DD'),
            'code': st.column_config.TextColumn('代码'),
            'name': st.column_config.TextColumn('名称'),
            '信号': st.column_config.TextColumn('信号类型'),
            'limit_cap': st.column_config.NumberColumn('限价上限', format='¥%.2f'),
            'reason': st.column_config.TextColumn('信号依据'),
            '警告': st.column_config.TextColumn('警告'),
        }
    )


def render_historical_signals():
    """
    渲染历史信号区域
    
    使用 Streamlit 原生组件，不搞复杂 HTML
    
    Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 3.1-3.5, 4.1-4.4, 5.1, 5.2
    """
    st.subheader("📜 历史信号")
    
    signal_store = SignalStore()
    
    # ========== 筛选条件 ==========
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # 日期范围选择（默认最近 30 天）
        default_start = date.today() - timedelta(days=30)
        default_end = date.today()
        date_range = st.date_input(
            "日期范围",
            value=(default_start, default_end),
            max_value=date.today(),
            key="historical_date_range"
        )
    
    with col2:
        # 股票代码筛选
        code_filter = st.text_input(
            "股票代码",
            placeholder="输入代码筛选，留空显示全部",
            key="historical_code_filter"
        )
    
    with col3:
        # 信号类型筛选
        signal_type_filter = st.selectbox(
            "信号类型",
            options=["全部", "买入", "卖出"],
            key="historical_signal_type"
        )
    
    # ========== 加载数据 ==========
    # 处理日期范围（可能是单个日期或元组）
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date = date_range if not isinstance(date_range, tuple) else date_range[0]
        end_date = start_date
    
    df = signal_store.load_signals(
        start_date=start_date,
        end_date=end_date,
        code=code_filter if code_filter else None,
        signal_type=signal_type_filter if signal_type_filter != "全部" else None
    )
    
    # ========== 统计概览 ==========
    if not df.empty:
        stats = signal_store.get_statistics(df)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("总信号数", stats['total_count'])
        with col2:
            st.metric("买入信号", stats['buy_count'])
        with col3:
            st.metric("卖出信号", stats['sell_count'])
        with col4:
            st.metric("涉及股票", stats['stock_count'])
        
        st.divider()
        
        # ========== 信号表格 ==========
        render_historical_signal_table(df)
        
        # ========== 导出按钮 ==========
        csv_data = signal_store.export_csv(df)
        st.download_button(
            label="📥 导出 CSV",
            data=csv_data,
            file_name=f"signals_export_{date.today().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            key="export_historical_signals"
        )
    else:
        st.info("📭 暂无历史信号记录")


def generate_signals(stock_pool: List[str]) -> List[TradingSignal]:
    """
    生成交易信号
    
    Args:
        stock_pool: 股票池
    
    Returns:
        信号列表
    """
    data_feed = get_data_feed()
    settings = get_settings()
    
    # 创建信号生成器
    signal_generator = SignalGenerator(data_feed=data_feed)
    
    # 生成信号
    signals = signal_generator.generate_signals(
        stock_pool=stock_pool,
        current_cash=settings.fund.initial_capital,
        current_positions=0
    )
    
    return signals


def render_market_status():
    """渲染大盘状态"""
    st.subheader("📊 大盘状态")
    
    try:
        data_feed = get_data_feed()
        screener = Screener(data_feed)
        market_status = screener.get_market_status()
        
        if market_status['status'] == 'healthy':
            st.success(f"""
            ✅ **大盘环境健康，允许交易**
            
            沪深300: **{market_status['current_price']:.2f}** > MA{screener.market_filter.ma_period}: **{market_status[f'ma{screener.market_filter.ma_period}']:.2f}**
            """)
        elif market_status['status'] == 'unhealthy':
            st.error(f"""
            ⚠️ **大盘滤网生效，建议空仓观望**
            
            沪深300: **{market_status['current_price']:.2f}** < MA{screener.market_filter.ma_period}: **{market_status[f'ma{screener.market_filter.ma_period}']:.2f}**
            
            {market_status['message']}
            """)
        else:
            st.warning(f"大盘状态: {market_status['message']}")
            
    except Exception as e:
        st.warning(f"无法获取大盘状态: {str(e)}")


def main():
    """信号页面主函数"""
    st.set_page_config(
        page_title="每日信号 - MiniQuant-Lite",
        page_icon="📡",
        layout="wide"
    )
    
    st.title("📡 每日交易信号")
    st.markdown("基于技术指标生成的交易信号，请结合新闻面人工判断")
    
    st.divider()
    
    # ========== 数据新鲜度警告（最高优先级）==========
    data_stale = render_data_freshness_warning()
    
    # ========== 休市安民告示 ==========
    is_holiday = render_market_holiday_notice()
    
    if data_stale or is_holiday:
        st.divider()
    
    # 早安确认清单
    render_premarket_checklist()
    
    st.divider()
    
    # 大盘状态
    render_market_status()
    
    st.divider()
    
    # 信号生成配置
    st.subheader("⚙️ 信号生成")
    
    stock_pool = get_watchlist()
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        use_all = st.checkbox(
            f"使用全部股票池（{len(stock_pool)} 只）",
            value=True,
            help="勾选后对股票池中所有股票生成信号"
        )
        
        if not use_all:
            selected_stocks = st.multiselect(
                "选择股票",
                options=stock_pool,
                default=stock_pool[:5] if len(stock_pool) >= 5 else stock_pool,
                help="选择要生成信号的股票"
            )
        else:
            selected_stocks = stock_pool
    
    with col2:
        st.markdown("**信号生成时间**")
        st.caption(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        st.caption("推荐: 交易日 19:00-21:00")
    
    # 如果数据过期，禁用信号生成按钮
    button_disabled = not selected_stocks or data_stale
    button_help = "请先更新数据" if data_stale else None
    
    # 生成信号按钮
    if st.button("🚀 生成今日信号", type="primary", disabled=button_disabled, help=button_help):
        if not selected_stocks:
            st.warning("请选择要生成信号的股票")
            return
        
        with st.spinner("正在生成交易信号，请稍候..."):
            signals = generate_signals(selected_stocks)
        
        # 保存信号到历史记录（Requirements: 1.1）
        if signals:
            try:
                signal_store = SignalStore()
                # 获取大盘状态
                data_feed = get_data_feed()
                screener = Screener(data_feed)
                market_status_info = screener.get_market_status()
                market_status = "健康" if market_status_info.get('status') == 'healthy' else "不佳"
                
                saved_count = signal_store.save_signals(
                    signals=signals,
                    generated_date=date.today(),
                    market_status=market_status
                )
                st.success(f"✅ 已保存 {saved_count} 条信号到历史记录")
            except Exception as e:
                st.warning(f"保存信号到历史记录失败: {str(e)}")
        
        st.divider()
        
        # 显示信号
        if signals:
            # 信号汇总表
            render_signal_summary_table(signals)
            
            st.divider()
            
            # 详细信号卡片
            render_signal_table(signals)
        else:
            st.info("📭 今日无操作建议")
            st.markdown("""
            可能的原因：
            - 大盘滤网生效（沪深300 < MA20）
            - 没有股票满足买入条件
            - 股票数据不足或未下载
            
            建议：
            1. 检查大盘状态
            2. 确保已下载股票数据
            3. 耐心等待机会
            """)
    
    # 历史信号区域
    st.divider()
    render_historical_signals()
    
    # 使用说明
    st.divider()
    st.subheader("📖 使用说明")
    
    with st.expander("如何使用交易信号？", expanded=False):
        st.markdown("""
        **标准操作流程：**
        
        1. **晚上 19:00-21:00** 运行系统生成信号
        2. **点击新闻链接**，人眼扫一遍标题（10秒）
        3. **确认无重大利空**后，将信号放入券商 APP 的"条件单"
        4. **次日 9:25 前**，完成早安确认清单
        5. **如有异常**，撤销条件单，改为观望
        
        **注意事项：**
        
        - ⚠️ 财报窗口期的股票建议规避
        - ⚠️ 高费率预警的股票交易成本较高
        - ⚠️ 限价上限是建议的最高挂单价格，防止追高
        - ⚠️ 本系统仅供参考，最终决策权在您手中
        """)
    
    with st.expander("信号指标说明", expanded=False):
        st.markdown("""
        **买入信号条件：**
        - 股价 > MA60（趋势滤网，只做右侧交易）
        - MACD 金叉（DIF 上穿 DEA）
        - RSI < 80（避免追高）
        
        **卖出信号条件：**
        - 硬止损：亏损达到 -8%
        - 移动止盈：盈利超过 15% 后，从最高点回撤 5%
        - MACD 死叉
        
        **限价上限：**
        - 计算公式：收盘价 × 1.01
        - 作用：防止次日高开时盲目追高
        """)


if __name__ == "__main__":
    main()
