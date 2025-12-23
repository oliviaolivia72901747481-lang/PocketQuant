"""
MiniQuant-Lite 每日信号页面

提供每日交易信号功能，采用紧凑布局设计：
- 早安确认清单（Pre-market Checklist）
- 信号表格（含新闻链接、财报窗口期警告）
- 高费率预警红色高亮
- 数据新鲜度检测（Data Freshness Watchdog）
- 交易日历感知（Market Calendar Awareness）

紧凑布局特性：
- 使用两列布局充分利用屏幕宽度
- 关键信息使用metrics组件紧凑显示
- 详细内容放在expander中可折叠
- 紧急信息（如止损信号）自动展开
- 所有关键信息在一屏内可见，减少滚动

人机协同设计：
- 系统负责技术分析和信号生成
- 人工负责新闻面判断和最终决策
- 提供便捷的新闻和公告链接
- 早安确认清单提醒开盘前检查

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

# Core imports
from config.settings import get_settings, load_strategy_params
from config.stock_pool import get_watchlist
from core.data_feed import DataFeed
from core.signal_generator import SignalGenerator, TradingSignal, SignalType, StrategyType
from core.screener import Screener
from core.signal_store import SignalStore
from core.position_tracker import PositionTracker
from core.sell_signal_checker import SellSignalChecker
from core.logging_config import get_logger
from core.notification import NotificationConfig, NotificationConfigStore, NotificationService, auto_send_notification

logger = get_logger(__name__)

# ============================================================================
# CONFIGURATION AND CONSTANTS
# ============================================================================


# ============================================================================
# CONFIGURATION AND CONSTANTS
# ============================================================================

# 策略选项配置（RSI 超卖反弹策略为默认）
# 这里定义了页面支持的所有交易策略类型和描述信息
# 与回测页面的策略配置保持一致，确保参数同步
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

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_data_feed() -> DataFeed:
    """
    获取 DataFeed 实例
    
    创建并返回配置好的数据源实例，用于访问股票数据
    从设置中获取原始数据和处理后数据的路径
    
    Returns:
        DataFeed: 配置好的数据源实例
    """
    settings = get_settings()
    return DataFeed(
        raw_path=settings.path.get_raw_path(),
        processed_path=settings.path.get_processed_path()
    )


def format_signal_for_copy(signal: 'TradingSignal') -> str:
    """
    格式化信号为可复制的文本（适合发送到券商APP条件单）
    
    将交易信号格式化为便于复制粘贴的文本格式
    用户可以直接复制到券商APP的条件单或交易备忘录中
    
    格式化内容包括：
    - 信号类型（买入/卖出）
    - 股票基本信息（代码、名称）
    - 价格信息（限价上限）
    - 数量建议（按100股整数倍计算）
    - 交易金额
    - 信号依据
    - 风险提醒（财报窗口期）
    
    计算逻辑：
    - 建议股数 = 交易金额 ÷ 限价上限 ÷ 100 × 100（向下取整到100股倍数）
    - 这样可以确保交易金额不超过预算
    
    Args:
        signal: TradingSignal 对象，包含完整的信号信息
        
    Returns:
        str: 格式化的信号文本，可直接复制使用
    """
    # 确定信号类型的中文描述
    signal_type = "买入" if signal.signal_type == SignalType.BUY else "卖出"
    
    # 计算建议股数（按100股整数倍，向下取整）
    # 这样可以确保实际交易金额不超过预算
    suggested_shares = int(signal.trade_amount / signal.limit_cap / 100) * 100
    
    # 格式化信号文本
    text = f"""【{signal_type}信号】{signal.code} {signal.name}
限价: ¥{signal.limit_cap:.2f}
数量: {suggested_shares}股
金额: ¥{signal.trade_amount:,.0f}
依据: {signal.reason}"""
    
    # 如果在财报窗口期，添加风险提醒
    if signal.in_report_window:
        text += "\n⚠️ 财报窗口期，请注意风险"
    
    return text


def record_trade_from_signal(signal: 'TradingSignal'):
    """
    将信号数据存储到 session_state 以便在交易记录页面预填充
    
    这是信号页面与交易记录页面的重要集成功能
    当用户点击信号后，可以快速跳转到交易记录页面并预填充相关信息
    
    功能特点：
    - 自动生成唯一的信号ID用于追踪
    - 从信号原因中智能提取策略名称
    - 预填充交易记录的关键字段
    - 设置跳转标志以便页面导航
    
    预填充字段：
    - 基本信息：股票代码、名称、操作类型
    - 价格信息：使用限价上限作为默认价格
    - 数量信息：根据交易金额和价格计算建议股数
    - 信号信息：信号ID、日期、价格、策略、原因
    - 默认设置：手续费等
    
    Args:
        signal: TradingSignal 对象，包含完整的信号信息
        
    Requirements: 6.6
    """
    # 生成唯一信号ID（格式：sig_日期_代码_信号类型）
    signal_id = f"sig_{date.today().strftime('%Y%m%d')}_{signal.code}_{signal.signal_type.value}"
    
    # 从信号原因中提取策略名称（智能识别）
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
        strategy = ''  # 未识别的策略
    
    # 存储预填充数据到 session_state
    st.session_state['prefill_trade'] = {
        # 基本交易信息
        'code': signal.code,
        'name': signal.name,
        'action': signal.signal_type.value,  # "买入" 或 "卖出"
        'price': signal.limit_cap,  # 使用限价上限作为默认价格
        'quantity': int(signal.trade_amount / signal.limit_cap) if signal.limit_cap > 0 else 100,
        'trade_date': date.today(),
        
        # 信号追踪信息
        'signal_id': signal_id,
        'signal_date': date.today(),
        'signal_price': signal.limit_cap,
        'strategy': strategy,
        'reason': signal.reason,
        
        # 默认设置
        'commission': 5.0,  # 默认手续费
    }
    
    # 设置跳转标志（用于页面导航）
    st.session_state['redirect_to_trade_journal'] = True


def generate_signals(stock_pool: List[str], strategy_type: StrategyType) -> List[TradingSignal]:
    """
    生成交易信号
    
    根据选定的策略类型和股票池生成交易信号
    使用当前系统配置的资金和持仓信息
    
    Args:
        stock_pool: 股票池代码列表
        strategy_type: 策略类型（RSI、RSRS等）
    
    Returns:
        List[TradingSignal]: 生成的信号列表
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

# ============================================================================
# DATA VALIDATION AND MONITORING FUNCTIONS
# ============================================================================


# ============================================================================
# DATA VALIDATION AND MONITORING FUNCTIONS
# ============================================================================

def check_data_freshness() -> Dict[str, Any]:
    """
    检查数据新鲜度（Data Freshness Watchdog）
    
    通过检查本地数据文件的最后更新时间来判断数据是否过期
    如果数据超过3天未更新，则认为数据过期，需要提醒用户更新
    这是防止使用过期数据生成无效信号的重要安全机制
    
    Returns:
        Dict[str, Any]: 包含以下字段的字典
            - is_stale: bool - 数据是否过期
            - last_data_date: date - 最后数据日期
            - days_old: int - 数据已过期天数
            - message: str - 状态消息
    """
    settings = get_settings()
    processed_path = settings.path.get_processed_path()
    
    try:
        # 获取所有CSV数据文件
        csv_files = glob.glob(os.path.join(processed_path, "*.csv"))
        
        if not csv_files:
            return {
                'is_stale': True,
                'last_data_date': None,
                'days_old': 999,
                'message': '未找到任何数据文件，请先下载数据'
            }
        
        # 读取第一个文件作为样本检查数据格式和日期
        sample_file = csv_files[0]
        df = pd.read_csv(sample_file)
        
        if df.empty or 'date' not in df.columns:
            return {
                'is_stale': True,
                'last_data_date': None,
                'days_old': 999,
                'message': '数据文件格式异常'
            }
        
        # 获取最后一行的日期（最新数据日期）
        last_date_str = df['date'].iloc[-1]
        last_data_date = datetime.strptime(last_date_str, '%Y-%m-%d').date()
        
        # 计算数据过期天数
        today = date.today()
        days_old = (today - last_data_date).days
        is_stale = days_old > 3  # 超过3天认为过期
        
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
    
    通过AkShare获取交易日历，判断当前日期是否为交易日
    用于在非交易日显示休市提醒，避免用户在休市时生成无效信号
    
    Returns:
        Dict[str, Any]: 包含以下字段的字典
            - is_trading_day: bool - 今天是否为交易日
            - message: str - 状态消息
            - next_trading_day: date - 下一个交易日
    """
    try:
        import akshare as ak
        
        today = date.today()
        # 获取交易日历数据
        trade_dates_df = ak.tool_trade_date_hist_sina()
        
        if trade_dates_df is None or trade_dates_df.empty:
            return {
                'is_trading_day': True,
                'message': '无法获取交易日历',
                'next_trading_day': None
            }
        
        # 转换为日期列表
        trade_dates = pd.to_datetime(trade_dates_df['trade_date']).dt.date.tolist()
        is_trading_day = today in trade_dates
        
        if is_trading_day:
            return {
                'is_trading_day': True,
                'message': '今天是交易日',
                'next_trading_day': today
            }
        else:
            # 查找下一个交易日
            next_trading_day = None
            for td in trade_dates:
                if td > today:
                    next_trading_day = td
                    break
            
            # 判断休市原因（周末或节假日）
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

# ============================================================================
# UI RENDERING FUNCTIONS - WARNINGS AND NOTICES
# ============================================================================


# ============================================================================
# UI RENDERING FUNCTIONS - WARNINGS AND NOTICES
# ============================================================================

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
    
    这是人机协同交易的重要组件，提醒用户在开盘前进行最后确认
    系统无法预知次日早晨的突发利空，需要人工进行最后把关
    
    设计原则：
    - 晚上的信号无法预知次日早晨的突发利空
    - 提醒用户在 9:25 集合竞价结束前进行最后一次人工确认
    - 列出关键检查项目，帮助用户快速判断
    - 如有异常情况，建议撤销条件单改为观望
    
    检查项目包括：
    1. 美股走势（道指跌幅 > 2% 需警惕）
    2. 集合竞价情况（低开 > 2% 建议观望）
    3. 突发利空新闻
    4. 个股特殊情况（停牌、复牌等）
    
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

# ============================================================================
# UI RENDERING FUNCTIONS - SIGNAL TABLES AND HISTORY
# ============================================================================








# ============================================================================
# UI RENDERING FUNCTIONS - SIGNAL TABLES AND HISTORY
# ============================================================================

def render_signal_summary_table(signals: List[TradingSignal], status_messages: List[str] = None):
    """
    渲染信号汇总表格（简洁版）
    
    这是信号展示的核心组件，以表格形式展示生成的交易信号
    包含人机协同提醒和关键信息展示
    
    功能特点：
    - 集中显示状态信息（数据日期、通知状态等）
    - 人机协同提醒，强调最后一步人工确认的重要性
    - 财报窗口期股票高亮显示以引起注意
    - 提供新闻和公告链接便于快速查看
    - 使用原生Streamlit组件确保兼容性
    
    表格列说明：
    - 股票代码/名称：基本信息
    - 信号类型：买入/卖出
    - 限价上限：建议挂单价格上限（收盘价×1.01）
    - 价格区间：建议交易价格范围
    - 交易金额：建议交易金额
    - 财报窗口期：风险提醒
    - 新闻/公告：快速查看链接
    
    Args:
        signals: 交易信号列表
        status_messages: 状态信息列表（可选）
        
    Requirements: 6.6
    """
    if not signals:
        return
    
    st.subheader("📋 信号汇总表")
    
    # 集中显示状态信息
    freshness = check_data_freshness()
    info_items = []
    
    # 添加数据日期说明（重要：用户需要知道使用的是哪天的数据）
    if freshness['last_data_date']:
        info_items.append(f"数据日期: {freshness['last_data_date'].strftime('%Y-%m-%d')}")
    
    # 添加其他状态信息（如通知发送状态）
    if status_messages:
        info_items.extend(status_messages)
    
    # 在一行中显示所有状态信息
    if info_items:
        st.caption(" | ".join(info_items))
    
    st.divider()
    
    # 人机协同提醒（强调人工确认的重要性）
    st.info("""
    ⚠️ **人机协同提醒**：系统已自动过滤财报窗口期，但请在下单前完成最后一步人工确认：
    1. 点击「新闻」查看资讯（10秒）
    2. 点击「公告」检查有无重大利空
    3. 确认无异常后再将信号放入条件单
    """)
    
    # 转换为 DataFrame 用于表格显示
    data = []
    for signal in signals:
        # 生成公告链接（东方财富公告页面）
        announcement_url = f"https://data.eastmoney.com/notices/stock/{signal.code}.html"
        
        row = {
            '股票代码': signal.code,
            '股票名称': signal.name,
            '信号类型': signal.signal_type.value,
            '限价上限': f"¥{signal.limit_cap:.2f}",
            '价格区间': f"¥{signal.price_range[0]:.2f}-¥{signal.price_range[1]:.2f}",
            '交易金额': f"¥{signal.trade_amount:,.0f}",
            '财报窗口期': '⚠️ 是' if signal.in_report_window else '否',
            '新闻': signal.news_url,  # 新闻链接列放在最后
            '公告': announcement_url  # 公告链接列放在最后
        }
        data.append(row)
    
    df = pd.DataFrame(data)
    
    # 高亮显示财报窗口期股票
    def highlight_warnings(row):
        styles = [''] * len(row)
        
        # 财报窗口期高亮（黄色背景提醒风险）
        if '是' in str(row.get('财报窗口期', '')):
            styles = ['background-color: #fff3cd'] * len(row)
        
        return styles
    
    # 显示表格（使用原生Streamlit组件）
    st.dataframe(
        df.style.apply(highlight_warnings, axis=1),
        use_container_width=True,
        hide_index=True,
        column_config={
            '新闻': st.column_config.LinkColumn('新闻', help='点击查看新闻资讯', display_text='🔗'),
            '限价上限': st.column_config.TextColumn('限价上限', help='建议挂单价格上限（收盘价×1.01）'),
            '价格区间': st.column_config.TextColumn('价格区间', help='建议交易价格区间'),
            '公告': st.column_config.LinkColumn('公告', help='点击查看公告', display_text='📋')
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
    with st.expander("📜 历史信号", expanded=False):
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

# ============================================================================
# UI RENDERING FUNCTIONS - COMPACT LAYOUT COMPONENTS
# ============================================================================





# ============================================================================
# UI RENDERING FUNCTIONS - COMPACT LAYOUT COMPONENTS
# ============================================================================

def render_sell_signals_section_compact():
    """
    渲染卖出信号区域（紧凑版）
    
    这是紧凑布局的核心组件之一，用于显示当前持仓的卖出信号
    采用紧凑的卡片式布局，关键信息使用metrics组件展示
    详细信号内容放在可展开的expander中以节省空间
    
    功能特点：
    - 只有当有持仓时才显示内容
    - 紧急止损信号自动展开以引起注意
    - 使用颜色区分不同紧急程度的信号
    - 显示盈亏情况帮助用户快速决策
    
    Requirements: 5.1, 5.2, 5.3
    """
    st.markdown("#### 🚨 持仓卖出信号")
    
    # 获取当前持仓数据
    tracker = PositionTracker()
    positions = tracker.get_all_positions()
    
    if not positions:
        st.info("当前无持仓")
        return
    
    # 检查所有持仓的卖出信号
    data_feed = get_data_feed()
    checker = SellSignalChecker(data_feed)
    signals = checker.check_all_positions(positions)
    
    if not signals:
        st.success(f"✅ {len(positions)} 只持仓无卖出信号")
        return
    
    # 统计不同紧急程度的信号数量
    high_count = sum(1 for s in signals if s.urgency == "high")
    medium_count = sum(1 for s in signals if s.urgency == "medium")
    
    # 使用metrics组件显示关键统计信息
    col1, col2 = st.columns(2)
    with col1:
        st.metric("持仓", f"{len(positions)} 只")
    with col2:
        if high_count > 0:
            # 紧急止损信号用红色警告显示
            st.metric("🚨 止损", f"{high_count} 个", delta="紧急", delta_color="inverse")
        else:
            st.metric("⚠️ 策略卖出", f"{medium_count} 个")
    
    # 显示详细信号信息（紧凑版）
    # 如果有紧急止损信号，默认展开以引起用户注意
    with st.expander(f"查看 {len(signals)} 个卖出信号", expanded=high_count > 0):
        for signal in signals:
            if signal.urgency == "high":
                # 紧急止损信号用红色错误框显示
                st.error(f"""
                **{signal.code} {signal.name}** - {signal.exit_reason}
                
                买入: ¥{signal.holding.buy_price:.2f} → 现价: ¥{signal.current_price:.2f} | 盈亏: **{signal.pnl_pct:.1%}**
                """)
            elif signal.urgency == "medium":
                # 普通策略卖出信号用黄色警告框显示
                st.warning(f"""
                **{signal.code} {signal.name}** - {signal.exit_reason}
                
                买入: ¥{signal.holding.buy_price:.2f} → 现价: ¥{signal.current_price:.2f} | 盈亏: {signal.pnl_pct:.1%}
                """)


def render_market_status_compact():
    """
    渲染大盘状态（紧凑版）
    
    这是紧凑布局的核心组件之一，用于显示沪深300指数状态和MA均线对比
    通过颜色区分健康/不健康状态，帮助用户快速判断市场环境
    
    功能特点：
    - 显示沪深300当前价格和MA均线对比
    - 健康状态显示绿色成功提示，允许交易
    - 不健康状态显示红色警告，建议空仓观望
    - 使用metric组件紧凑显示关键指标
    - 异常情况有友好的错误处理
    
    大盘滤网机制：
    - 当沪深300指数低于MA均线时，系统建议空仓
    - 这是重要的风险控制机制，避免在弱势市场中交易
    
    Requirements: 大盘滤网功能
    """
    st.markdown("#### 📊 大盘状态")
    
    try:
        # 获取数据源和大盘筛选器
        data_feed = get_data_feed()
        screener = Screener(data_feed)
        market_status = screener.get_market_status()
        
        if market_status['status'] == 'healthy':
            # 大盘健康：绿色成功提示
            st.success("✅ 大盘健康，允许交易")
            st.metric(
                "沪深300", 
                f"{market_status['current_price']:.2f}",
                delta=f"MA{screener.market_filter.ma_period}: {market_status[f'ma{screener.market_filter.ma_period}']:.2f}"
            )
        elif market_status['status'] == 'unhealthy':
            # 大盘不健康：红色错误提示，建议空仓
            st.error("⚠️ 大盘滤网生效，建议空仓")
            st.metric(
                "沪深300", 
                f"{market_status['current_price']:.2f}",
                delta=f"< MA{screener.market_filter.ma_period}",
                delta_color="inverse"  # 红色显示负面信息
            )
            st.caption(market_status['message'])
        else:
            # 未知状态：黄色警告提示
            st.warning(f"大盘状态: {market_status['message']}")
            
    except Exception as e:
        # 异常处理：显示友好的错误信息
        st.warning(f"无法获取大盘状态: {str(e)}")


def render_notification_settings_compact():
    """
    渲染飞书通知配置面板（紧凑版）
    
    这是紧凑布局的核心组件之一，用于显示和配置飞书通知功能
    采用紧凑设计，配置面板默认折叠以节省空间
    
    功能特点：
    - 显示当前通知启用状态（已启用/未配置）
    - 显示脱敏后的Webhook URL以保护隐私
    - 配置面板默认折叠，点击展开进行设置
    - 保存和测试按钮并排显示，提高操作效率
    - 支持实时测试通知功能
    
    安全特性：
    - Webhook URL使用密码输入框保护
    - URL显示时进行脱敏处理
    - 配置保存到本地文件，不上传到服务器
    
    Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7
    """
    st.markdown("#### 🔔 飞书通知")
    
    # 加载已保存的通知配置
    config = NotificationConfigStore.load()
    
    # 显示当前通知状态
    if config.enabled and config.webhook_url:
        st.success("✅ 已启用")
        # 显示脱敏后的URL以保护用户隐私
        masked_url = NotificationConfigStore.mask_webhook_url(config.webhook_url)
        st.caption(f"配置: {masked_url}")
    else:
        st.info("未配置")
    
    # 配置面板（默认折叠以节省空间）
    with st.expander("⚙️ 配置飞书通知", expanded=False):
        st.caption("在信号生成时自动推送到飞书群")
        
        # Webhook URL 输入（使用密码类型保护隐私）
        webhook_url = st.text_input(
            "Webhook URL",
            value=config.webhook_url,
            type="password",  # 密码输入框保护URL隐私
            placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/...",
            help="飞书群机器人 Webhook 地址"
        )
        
        # 启用开关
        enabled = st.checkbox("启用通知", value=config.enabled)
        
        # 按钮区域（并排显示以节省空间）
        col_save, col_test = st.columns(2)
        
        with col_save:
            if st.button("💾 保存", use_container_width=True, key="notif_save_compact"):
                # 创建新的配置对象
                new_config = NotificationConfig(
                    webhook_url=webhook_url,
                    enabled=enabled,
                    notify_on_buy=True,   # 默认启用买入通知
                    notify_on_sell=True   # 默认启用卖出通知
                )
                # 保存配置并显示结果
                if NotificationConfigStore.save(new_config):
                    st.success("✅ 已保存")
                    st.rerun()  # 刷新页面显示最新状态
                else:
                    st.error("❌ 保存失败")
        
        with col_test:
            if st.button("🔔 测试", use_container_width=True, key="notif_test_compact"):
                if not webhook_url:
                    st.error("请先输入 Webhook URL")
                else:
                    # 创建测试配置并发送测试通知
                    test_config = NotificationConfig(
                        webhook_url=webhook_url,
                        enabled=True,
                        notify_on_buy=True,
                        notify_on_sell=True
                    )
                    service = NotificationService(test_config)
                    
                    with st.spinner("发送中..."):
                        success, message = service.send_test_notification()
                    
                    if success:
                        st.success("✅ 发送成功")
                    else:
                        st.error(f"❌ {message}")

# ============================================================================
# MAIN APPLICATION FUNCTION
# ============================================================================


# ============================================================================
# MAIN APPLICATION FUNCTION
# ============================================================================

def main():
    """
    信号页面主函数
    
    这是每日信号页面的入口函数，实现了紧凑布局设计
    通过合理的信息组织和布局优化，使关键信息在一屏内可见
    
    页面布局结构：
    1. 页面标题和基本信息
    2. 数据新鲜度警告和休市提醒（安全检查）
    3. 早安确认清单（人机协同提醒）
    4. 紧凑布局第一行：持仓卖出信号 + 大盘状态
    5. 紧凑布局第二行：策略配置 + 飞书通知
    6. 信号生成配置和按钮
    7. 信号汇总表（生成后显示）
    8. 历史信号查询（可展开）
    9. 使用说明（可展开）
    
    设计原则：
    - 关键信息优先显示，次要信息可折叠
    - 使用两列布局充分利用屏幕宽度
    - 紧急信息（如止损信号）自动展开
    - 保持与回测页面的参数同步
    - 人机协同，系统辅助人工决策
    """
    # 页面基础配置
    st.set_page_config(
        page_title="每日信号 - MiniQuant-Lite",
        page_icon="📡",
        layout="wide"  # 使用宽布局以支持两列显示
    )
    
    # 页面标题和说明
    st.title("📡 每日交易信号")
    st.markdown("基于技术指标生成的交易信号，请结合新闻面人工判断")
    
    st.divider()
    
    # ========== 安全检查区域 ==========
    # 数据新鲜度警告（最高优先级，防止使用过期数据）
    data_stale = render_data_freshness_warning()
    
    # 休市安民告示（避免在非交易日生成无效信号）
    is_holiday = render_market_holiday_notice()
    
    # 如果有警告或提醒，添加分隔线
    if data_stale or is_holiday:
        st.divider()
    
    # ========== 人机协同提醒 ==========
    # 早安确认清单（提醒用户在开盘前进行最后确认）
    render_premarket_checklist()
    
    st.divider()
    
    # ========== 紧凑布局第一行：持仓监控 + 市场状态 ==========
    # 使用两列布局，左列显示持仓卖出信号，右列显示大盘状态
    col_sell, col_market = st.columns(2)
    
    with col_sell:
        # 持仓卖出信号（紧凑版）- 风险控制的重要组件
        render_sell_signals_section_compact()
    
    with col_market:
        # 大盘状态（紧凑版）- 市场环境判断
        render_market_status_compact()
    
    st.divider()
    
    # ========== 紧凑布局第二行：策略配置 + 通知设置 ==========
    # 左列占2/3宽度显示策略配置，右列占1/3宽度显示通知设置
    col_strategy, col_notification = st.columns([2, 1])
    
    with col_strategy:
        st.markdown("#### 📋 策略配置")
        
        # 策略选择下拉框
        strategy_name = st.selectbox(
            "选择策略",
            options=list(STRATEGY_OPTIONS.keys()),
            index=0,  # 默认选择第一个策略
            help="选择要使用的策略类型，与回测页面保持一致",
            label_visibility="collapsed"  # 隐藏标签以节省空间
        )
        
        # 显示策略描述（使用caption而非info box以节省空间）
        strategy_info = STRATEGY_OPTIONS[strategy_name]
        st.caption(f"💡 {strategy_info['description']}")
        
        # 显示当前使用的参数（与回测页面共享配置）
        saved_params = load_strategy_params()
        
        # 参数详情放在expander中以节省空间
        with st.expander("📊 当前策略参数", expanded=False):
            if strategy_name == "RSI 超卖反弹策略":
                # RSI策略参数显示
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("RSI 周期", saved_params.rsi_period)
                with col2:
                    st.metric("买入 (RSI<)", saved_params.rsi_buy_threshold)
                with col3:
                    st.metric("卖出 (RSI>)", saved_params.rsi_sell_threshold)
            
            elif strategy_name == "RSRS 阻力支撑策略":
                # RSRS策略参数显示
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("斜率窗口", saved_params.rsrs_n_period)
                with col2:
                    st.metric("买入阈值", f"{saved_params.rsrs_buy_threshold:.1f}")
                with col3:
                    st.metric("卖出阈值", f"{saved_params.rsrs_sell_threshold:.1f}")
            
            st.caption("💡 参数在回测页面自动同步")
    
    with col_notification:
        # 飞书通知配置（紧凑版）
        render_notification_settings_compact()
    
    st.divider()
    
    # ========== 信号生成配置区域 ==========
    st.subheader("⚙️ 信号生成")
    
    # 获取股票池
    stock_pool = get_watchlist()
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # 股票池选择
        use_all = st.checkbox(
            f"使用全部股票池（{len(stock_pool)} 只）",
            value=True,
            help="勾选后对股票池中所有股票生成信号"
        )
        
        if not use_all:
            # 手动选择股票
            selected_stocks = st.multiselect(
                "选择股票",
                options=stock_pool,
                default=stock_pool[:5] if len(stock_pool) >= 5 else stock_pool,
                help="选择要生成信号的股票"
            )
        else:
            selected_stocks = stock_pool
    
    with col2:
        # 时间提醒
        st.markdown("**信号生成时间**")
        st.caption(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        st.caption("推荐: 交易日 19:00-21:00")
    
    # 信号生成按钮（如果数据过期则禁用）
    button_disabled = not selected_stocks or data_stale
    button_help = "请先更新数据" if data_stale else None
    
    # 生成信号按钮
    if st.button("🚀 生成今日信号", type="primary", disabled=button_disabled, help=button_help):
        if not selected_stocks:
            st.warning("请选择要生成信号的股票")
            return
        
        # 显示生成进度
        with st.spinner(f"正在使用 {strategy_name} 生成交易信号，请稍候..."):
            signals = generate_signals(selected_stocks, strategy_info['type'])
        
        # 收集状态信息用于显示
        status_messages = []
        
        # 保存信号到历史记录（Requirements: 1.1）
        if signals:
            try:
                signal_store = SignalStore()
                # 获取大盘状态用于记录
                data_feed = get_data_feed()
                screener = Screener(data_feed)
                market_status_info = screener.get_market_status()
                market_status = "健康" if market_status_info.get('status') == 'healthy' else "不佳"
                
                # 保存信号
                saved_count = signal_store.save_signals(
                    signals=signals,
                    generated_date=date.today(),
                    market_status=market_status
                )
                status_messages.append(f"已保存 {saved_count} 条信号到历史记录")
            except Exception as e:
                status_messages.append(f"保存信号失败: {str(e)}")
        
        st.divider()
        
        # 显示生成的信号
        if signals:
            # 自动发送飞书通知 (Requirements 5.1)
            notification_config = NotificationConfigStore.load()
            if notification_config.enabled and notification_config.webhook_url:
                # 尝试发送飞书通知
                with st.spinner("正在发送飞书通知..."):
                    notification_success = auto_send_notification(signals)
                if notification_success:
                    status_messages.append("飞书通知已发送")
                else:
                    status_messages.append("飞书通知发送失败")
            
            # 显示信号汇总表（传入状态信息）
            render_signal_summary_table(signals, status_messages)
        else:
            # 无信号时的友好提示
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
    
    # ========== 历史信号区域 ==========
    st.divider()
    render_historical_signals()
    
    # ========== 使用说明区域 ==========
    st.divider()
    st.subheader("📖 使用说明")
    
    # 使用说明内容（可展开以节省空间）
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
        
        **关于限价上限的说明：**
        
        - 限价上限 = 历史收盘价 × 1.01（允许1%的高开滑点）
        - 系统使用的是本地数据文件中的最新收盘价（通常是 T-1 日）
        - 如果与官网实时价格不一致，属于正常现象（数据时效性差异）
        - 建议在实际下单前，参考最新市场价格进行调整
        - 可以在"数据管理"页面更新数据，获取最新收盘价
        """)
    
    with st.expander("为什么限价上限与官网价格不一致？", expanded=False):
        st.markdown("""
        **原因分析：**
        
        1. **数据时效性差异**
           - 系统使用本地数据文件中的历史收盘价
           - 官网显示的是实时价格或最新收盘价
           - 如果数据未及时更新，会存在时间差
        
        2. **计算时间点不同**
           - 系统通常在晚上生成信号（使用 T-1 日收盘价）
           - 官网显示的是当前时刻的价格
           - 次日开盘前，价格可能已经变化
        
        3. **数据来源不同**
           - 系统使用 AkShare 下载的历史数据
           - 官网使用实时行情数据
           - 可能存在微小的数据差异
        
        **解决方案：**
        
        1. **更新数据**：在"数据管理"页面点击"更新数据"，获取最新收盘价
        2. **参考最新价格**：实际下单前，查看券商 APP 中的最新价格
        3. **调整限价**：根据最新市场价格，适当调整挂单价格
        4. **使用价格区间**：参考表格中的"价格区间"列，而不是单一的限价上限
        
        **最佳实践：**
        
        - 晚上生成信号后，次日开盘前再次确认价格
        - 使用券商 APP 的"条件单"功能，设置合理的价格区间
        - 不要盲目追高，宁可错过也不要买贵
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


# ============================================================================
# APPLICATION ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    main()
