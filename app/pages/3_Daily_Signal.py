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
from core.signal_generator import SignalGenerator, TradingSignal, SignalType, StrategyType
from core.screener import Screener
from core.signal_store import SignalStore
from core.position_tracker import PositionTracker
from core.sell_signal_checker import SellSignalChecker, SellSignal
from core.logging_config import get_logger
from core.notification import NotificationConfig, NotificationConfigStore, NotificationService, auto_send_notification
from config.settings import load_strategy_params

logger = get_logger(__name__)


def format_signal_for_copy(signal: 'TradingSignal') -> str:
    """
    格式化信号为可复制的文本（适合发送到券商APP条件单）
    
    Args:
        signal: TradingSignal 对象
        
    Returns:
        格式化的信号文本
    """
    signal_type = "买入" if signal.signal_type == SignalType.BUY else "卖出"
    
    # 计算建议股数（按100股整数倍）
    suggested_shares = int(signal.trade_amount / signal.limit_cap / 100) * 100
    
    text = f"""【{signal_type}信号】{signal.code} {signal.name}
限价: ¥{signal.limit_cap:.2f}
数量: {suggested_shares}股
金额: ¥{signal.trade_amount:,.0f}
依据: {signal.reason}"""
    
    if signal.in_report_window:
        text += "\n⚠️ 财报窗口期，请注意风险"
    
    return text


def format_all_signals_for_copy(signals: List['TradingSignal']) -> str:
    """
    格式化所有信号为可复制的文本
    
    Args:
        signals: 信号列表
        
    Returns:
        格式化的信号文本
    """
    if not signals:
        return "今日无交易信号"
    
    from datetime import date
    
    lines = [f"📡 MiniQuant 交易信号 ({date.today().strftime('%Y-%m-%d')})", ""]
    
    buy_signals = [s for s in signals if s.signal_type == SignalType.BUY]
    sell_signals = [s for s in signals if s.signal_type == SignalType.SELL]
    
    if buy_signals:
        lines.append("🟢 买入信号:")
        for s in buy_signals:
            shares = int(s.trade_amount / s.limit_cap / 100) * 100
            lines.append(f"  {s.code} {s.name} | ¥{s.limit_cap:.2f} | {shares}股")
        lines.append("")
    
    if sell_signals:
        lines.append("🔴 卖出信号:")
        for s in sell_signals:
            shares = int(s.trade_amount / s.limit_cap / 100) * 100
            lines.append(f"  {s.code} {s.name} | ¥{s.limit_cap:.2f} | {shares}股")
        lines.append("")
    
    lines.append("⚠️ 请在下单前确认新闻面无重大利空")
    
    return "\n".join(lines)


def record_trade_from_signal(signal: 'TradingSignal'):
    """
    将信号数据存储到 session_state 以便在交易记录页面预填充
    
    Args:
        signal: TradingSignal 对象
        
    Requirements: 6.6
    """
    # 生成信号ID（使用日期+代码+信号类型）
    signal_id = f"sig_{date.today().strftime('%Y%m%d')}_{signal.code}_{signal.signal_type.value}"
    
    # 从信号原因中提取策略名称
    reason_lower = signal.reason.lower()
    if 'rsrs' in reason_lower:
        strategy = 'RSRS'
    elif 'rsi' in reason_lower:
        strategy = 'RSI'
    elif 'bollinger' in reason_lower or 'boll' in reason_lower:
        strategy = 'Bollinger'
    elif 'macd' in reason_lower:
        strategy = 'MACD'
    else:
        strategy = ''
    
    # 存储预填充数据到 session_state
    st.session_state['prefill_trade'] = {
        'code': signal.code,
        'name': signal.name,
        'action': signal.signal_type.value,  # "买入" 或 "卖出"
        'price': signal.limit_cap,  # 使用限价上限作为默认价格
        'quantity': int(signal.trade_amount / signal.limit_cap) if signal.limit_cap > 0 else 100,
        'trade_date': date.today(),
        'signal_id': signal_id,
        'signal_date': date.today(),
        'signal_price': signal.limit_cap,
        'strategy': strategy,
        'reason': signal.reason,
        'commission': 5.0,  # 默认手续费
    }
    
    # 设置跳转标志
    st.session_state['redirect_to_trade_journal'] = True


# 策略选项配置（RSI 超卖反弹策略为默认）
STRATEGY_OPTIONS = {
    "RSI 超卖反弹策略": {
        "type": StrategyType.RSI_REVERSAL,
        "description": "适合震荡行情，快进快出。买入：RSI<30超卖；卖出：RSI>70超买",
    },
    "RSRS 阻力支撑策略": {
        "type": StrategyType.RSRS,
        "description": "基于阻力支撑相对强度。买入：RSRS标准分>0.7（市场情绪好）；卖出：RSRS标准分<-0.7",
    },
}


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
        
    Requirements: 7.6, 7.7, 12.1, 12.2, 12.3, 6.6
    """
    # 信号类型图标
    signal_emoji = "🟢" if signal.signal_type == SignalType.BUY else "🔴" if signal.signal_type == SignalType.SELL else "⚪"
    
    # 创建卡片容器
    with st.container():
        # 标题行
        col1, col2, col3, col4, col5 = st.columns([3, 2, 1, 1, 1])
        
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
        
        with col4:
            # 一键复制按钮
            copy_text = format_signal_for_copy(signal)
            st.code(copy_text, language=None)
            st.caption("👆 选中复制")
        
        with col5:
            # 记录交易按钮 (Requirements: 6.6)
            if st.button(
                "📝 记录交易",
                key=f"record_trade_{signal.code}_{index}",
                help="点击跳转到交易记录页面，自动填充信号信息"
            ):
                record_trade_from_signal(signal)
                st.switch_page("pages/6_📝_Trade_Journal.py")
        
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
        
    Requirements: 6.6
    """
    if not signals:
        return
    
    st.subheader("📋 信号汇总表")
    
    # 一键复制所有信号
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info("""
        ⚠️ **人机协同提醒**：系统已自动过滤财报窗口期，但请在下单前完成最后一步人工确认：
        1. 点击「新闻链接」扫一眼标题（10秒）
        2. 点击「公告确认」检查有无重大利空
        3. 确认无异常后再将信号放入条件单
        """)
    with col2:
        st.markdown("**📋 一键复制所有信号**")
        all_signals_text = format_all_signals_for_copy(signals)
        st.code(all_signals_text, language=None)
        st.caption("👆 选中全部文本复制")
    
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
    
    # 快速记录交易按钮区域 (Requirements: 6.6)
    st.markdown("**📝 快速记录交易**")
    st.caption("执行交易后，点击对应按钮跳转到交易记录页面，自动填充信号信息")
    
    # 每行显示4个按钮
    cols_per_row = 4
    for i in range(0, len(signals), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, col in enumerate(cols):
            idx = i + j
            if idx < len(signals):
                signal = signals[idx]
                signal_emoji = "🟢" if signal.signal_type == SignalType.BUY else "🔴"
                with col:
                    if st.button(
                        f"{signal_emoji} {signal.code}",
                        key=f"quick_record_{signal.code}_{idx}",
                        help=f"{signal.name} - {signal.signal_type.value}"
                    ):
                        record_trade_from_signal(signal)
                        st.switch_page("pages/6_📝_Trade_Journal.py")


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


def generate_signals(stock_pool: List[str], strategy_type: StrategyType) -> List[TradingSignal]:
    """
    生成交易信号
    
    Args:
        stock_pool: 股票池
        strategy_type: 策略类型
    
    Returns:
        信号列表
    """
    data_feed = get_data_feed()
    settings = get_settings()
    
    # 创建信号生成器（使用指定策略）
    signal_generator = SignalGenerator(data_feed=data_feed, strategy_type=strategy_type)
    
    # 生成信号
    signals = signal_generator.generate_signals(
        stock_pool=stock_pool,
        current_cash=settings.fund.initial_capital,
        current_positions=0
    )
    
    return signals


def render_sell_signals_section():
    """
    渲染卖出信号区域（在每日信号页面）
    
    只有当有持仓时才显示
    
    Requirements: 5.1, 5.2, 5.3
    """
    tracker = PositionTracker()
    positions = tracker.get_all_positions()
    
    if not positions:
        return
    
    st.subheader("🚨 持仓卖出信号")
    
    data_feed = get_data_feed()
    checker = SellSignalChecker(data_feed)
    signals = checker.check_all_positions(positions)
    
    if not signals:
        st.success(f"✅ 当前 {len(positions)} 只持仓无卖出信号")
        st.divider()
        return
    
    # 统计
    high_count = sum(1 for s in signals if s.urgency == "high")
    medium_count = sum(1 for s in signals if s.urgency == "medium")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("持仓数量", f"{len(positions)} 只")
    with col2:
        if high_count > 0:
            st.metric("🚨 止损信号", f"{high_count} 个", delta="紧急", delta_color="inverse")
        else:
            st.metric("🚨 止损信号", "0 个")
    with col3:
        st.metric("⚠️ 策略卖出", f"{medium_count} 个")
    
    # 显示信号
    for signal in signals:
        if signal.urgency == "high":
            st.error(f"""
            🚨 **紧急止损 - {signal.code} {signal.name}**
            
            {signal.exit_reason}
            
            买入价: ¥{signal.holding.buy_price:.2f} → 现价: ¥{signal.current_price:.2f} | 盈亏: **{signal.pnl_pct:.1%}**
            
            ⚠️ **建议立即止损卖出！**
            """)
        elif signal.urgency == "medium":
            st.warning(f"""
            ⚠️ **策略卖出 - {signal.code} {signal.name}**
            
            {signal.exit_reason}
            
            买入价: ¥{signal.holding.buy_price:.2f} → 现价: ¥{signal.current_price:.2f} | 盈亏: {signal.pnl_pct:.1%}
            """)
    
    # 链接到持仓管理页面
    st.info("💡 前往 **持仓管理** 页面查看详细持仓信息和管理持仓")
    
    st.divider()


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


def render_notification_settings():
    """
    渲染飞书通知配置面板
    
    Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7
    """
    with st.expander("🔔 飞书通知设置", expanded=False):
        # 加载已保存配置 (Requirements 4.3)
        config = NotificationConfigStore.load()
        
        st.markdown("""
        配置飞书群机器人，在信号生成时自动推送到手机。
        
        **获取 Webhook URL**：
        1. 在飞书群中点击「设置」→「群机器人」→「添加机器人」
        2. 选择「自定义机器人」
        3. 复制机器人的 Webhook 地址
        """)
        
        # Webhook URL 输入（密码框形式）(Requirements 4.7)
        webhook_url = st.text_input(
            "Webhook URL",
            value=config.webhook_url,
            type="password",
            placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/...",
            help="飞书群机器人 Webhook 地址"
        )
        
        # 显示脱敏的当前配置
        if config.webhook_url:
            masked_url = NotificationConfigStore.mask_webhook_url(config.webhook_url)
            st.caption(f"当前配置: {masked_url}")
        
        # 启用开关
        enabled = st.checkbox("启用微信通知", value=config.enabled)
        
        # 买入/卖出通知选项
        col1, col2 = st.columns(2)
        with col1:
            notify_on_buy = st.checkbox("买入信号通知", value=config.notify_on_buy)
        with col2:
            notify_on_sell = st.checkbox("卖出信号通知", value=config.notify_on_sell)
        
        # 按钮区域
        col_save, col_test = st.columns(2)
        
        with col_save:
            # 保存按钮 (Requirements 4.2)
            if st.button("💾 保存配置", use_container_width=True):
                new_config = NotificationConfig(
                    webhook_url=webhook_url,
                    enabled=enabled,
                    notify_on_buy=notify_on_buy,
                    notify_on_sell=notify_on_sell
                )
                if NotificationConfigStore.save(new_config):
                    st.success("✅ 配置已保存")
                else:
                    st.error("❌ 保存失败")
        
        with col_test:
            # 测试按钮 (Requirements 4.4, 4.5, 4.6)
            if st.button("🔔 发送测试通知", use_container_width=True):
                if not webhook_url:
                    st.error("请先输入 Webhook URL")
                else:
                    # 使用当前输入的配置进行测试
                    test_config = NotificationConfig(
                        webhook_url=webhook_url,
                        enabled=True,
                        notify_on_buy=notify_on_buy,
                        notify_on_sell=notify_on_sell
                    )
                    service = NotificationService(test_config)
                    
                    with st.spinner("正在发送测试通知..."):
                        success, message = service.send_test_notification()
                    
                    if success:
                        st.success("✅ 测试通知发送成功！请检查飞书群")
                    else:
                        st.error(f"❌ 发送失败: {message}")


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
    
    # ========== 卖出信号（持仓检查）==========
    render_sell_signals_section()
    
    # 大盘状态
    render_market_status()
    
    st.divider()
    
    # ========== 微信通知设置 ==========
    render_notification_settings()
    
    st.divider()
    
    # ========== 策略选择 ==========
    st.subheader("📋 策略选择")
    
    strategy_name = st.selectbox(
        "选择策略",
        options=list(STRATEGY_OPTIONS.keys()),
        index=0,
        help="选择要使用的策略类型，与回测页面保持一致"
    )
    
    strategy_info = STRATEGY_OPTIONS[strategy_name]
    st.info(f"💡 **{strategy_name}**：{strategy_info['description']}")
    
    # 显示当前使用的参数（与回测页面共享）
    saved_params = load_strategy_params()
    
    with st.expander("📊 当前策略参数（与回测页面共享）", expanded=False):
        if strategy_name == "RSI 超卖反弹策略":
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("RSI 周期", saved_params.rsi_period)
            with col2:
                st.metric("买入阈值 (RSI<)", saved_params.rsi_buy_threshold)
            with col3:
                st.metric("卖出阈值 (RSI>)", saved_params.rsi_sell_threshold)
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("止损比例", f"{saved_params.rsi_stop_loss:.0%}")
            with col2:
                st.metric("止盈比例", f"{saved_params.rsi_take_profit:.0%}")
        
        elif strategy_name == "RSRS 阻力支撑策略":
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("斜率窗口 (N)", saved_params.rsrs_n_period)
            with col2:
                st.metric("标准化窗口 (M)", saved_params.rsrs_m_period)
            with col3:
                st.metric("硬止损", f"{saved_params.rsrs_hard_stop_loss:.0%}")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("买入阈值", f"{saved_params.rsrs_buy_threshold:.1f}")
            with col2:
                st.metric("卖出阈值", f"{saved_params.rsrs_sell_threshold:.1f}")
        
        st.caption("💡 参数在回测页面运行回测时自动同步，无需手动设置")
    
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
        
        with st.spinner(f"正在使用 {strategy_name} 生成交易信号，请稍候..."):
            signals = generate_signals(selected_stocks, strategy_info['type'])
        
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
            # 自动发送飞书通知 (Requirements 5.1)
            notification_config = NotificationConfigStore.load()
            if notification_config.enabled and notification_config.webhook_url:
                with st.spinner("正在发送飞书通知..."):
                    notification_success = auto_send_notification(signals)
                if notification_success:
                    st.success("📱 飞书通知已发送")
                else:
                    st.warning("📱 飞书通知发送失败，请检查配置")
            
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
        ### RSRS 阻力支撑策略
        
        **核心理念**：
        - 最高价 = 多头进攻极限 = 阻力位
        - 最低价 = 空头打压极限 = 支撑位
        - 阻力位和支撑位的变化关系，比价格本身更能反映市场情绪
        
        **计算步骤**：
        1. 取过去 18 天的 High/Low 数据，做线性回归，得到斜率 Beta
        2. 将 Beta 标准化（Z-Score），与过去 600 天的历史比较
        3. 得到 RSRS 标准分
        
        **买入信号**：RSRS 标准分 > 0.7（市场情绪处于历史最好的 25%）
        
        **卖出信号**：RSRS 标准分 < -0.7（市场情绪处于历史最差的 25%）
        
        ---
        
        ### RSI 超卖反弹策略
        
        **买入信号条件**：
        - RSI < 30（超卖区反弹）
        - 或 RSI 上穿 30（右侧买点）
        
        **卖出信号条件**：
        - RSI > 70（超买区止盈）
        
        ---
        
        **限价上限**：
        - 计算公式：收盘价 × 1.01
        - 作用：防止次日高开时盲目追高
        """)


if __name__ == "__main__":
    main()
