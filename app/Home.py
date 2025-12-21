"""
MiniQuant-Lite 首页

系统概览页面，展示：
- 系统基本信息（初始资金、股票池数量、今日信号）
- 避险战绩看板（大盘滤网生效期间规避的下跌风险）
- 数据新鲜度检测（Data Freshness Watchdog）
- 交易日历感知（Market Calendar Awareness）

Requirements: 7.1, 7.9
"""

import streamlit as st
import sys
import os
import glob
from datetime import date, datetime, timedelta
from typing import Dict, Any, Optional, Tuple

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import get_settings
from config.stock_pool import get_watchlist
from core.logging_config import ensure_logging_initialized, get_logger

# 初始化日志系统
ensure_logging_initialized()
logger = get_logger(__name__)


def get_capital_health_status(available_cash: float) -> Dict[str, Any]:
    """
    获取资金健康度状态（资金红绿灯）
    
    根据可用资金判断当前是否适合交易：
    - 🟢 资金充足 (>1.5W)：可以正常交易
    - 🟡 勉强可做 (0.5W-1.5W)：高磨损风险，谨慎交易
    - 🔴 建议空仓 (<0.5W)：资金不足，建议观望
    
    Args:
        available_cash: 可用现金
    
    Returns:
        {
            'status': str,           # 'green', 'yellow', 'red'
            'emoji': str,            # 🟢, 🟡, 🔴
            'label': str,            # 状态标签
            'message': str,          # 详细说明
            'can_trade': bool,       # 是否建议交易
            'fee_warning': str,      # 费率警告信息
        }
    """
    settings = get_settings()
    min_trade_amount = settings.position.min_trade_amount  # 默认 15000
    
    # 阈值定义
    GREEN_THRESHOLD = 15000.0   # 资金充足阈值
    YELLOW_THRESHOLD = 5000.0  # 勉强可做阈值
    
    if available_cash >= GREEN_THRESHOLD:
        return {
            'status': 'green',
            'emoji': '🟢',
            'label': '资金充足',
            'message': f'可用资金 ¥{available_cash:,.0f}，可以正常交易',
            'can_trade': True,
            'fee_warning': ''
        }
    elif available_cash >= YELLOW_THRESHOLD:
        # 计算实际费率
        actual_fee_rate = 5.0 / available_cash  # 5元低消
        standard_rate = settings.fund.commission_rate
        fee_multiple = actual_fee_rate / standard_rate
        
        return {
            'status': 'yellow',
            'emoji': '🟡',
            'label': '勉强可做',
            'message': f'可用资金 ¥{available_cash:,.0f}，存在高磨损风险',
            'can_trade': True,
            'fee_warning': f'⚠️ 实际费率约为标准费率的 {fee_multiple:.1f} 倍，手续费磨损较高'
        }
    else:
        return {
            'status': 'red',
            'emoji': '🔴',
            'label': '建议空仓',
            'message': f'可用资金 ¥{available_cash:,.0f}，不足以有效交易',
            'can_trade': False,
            'fee_warning': '❌ 资金过少，手续费磨损会吃掉大部分利润，建议先积累本金'
        }


def render_capital_traffic_light():
    """
    渲染资金红绿灯组件
    
    让用户一眼看懂自己能不能玩，而不是等信号生成了才报错
    """
    settings = get_settings()
    available_cash = settings.fund.initial_capital
    
    health = get_capital_health_status(available_cash)
    
    # 根据状态选择颜色
    if health['status'] == 'green':
        st.success(f"""
        {health['emoji']} **{health['label']}**
        
        {health['message']}
        
        ✅ 系统已就绪，可以正常生成交易信号
        """)
    elif health['status'] == 'yellow':
        st.warning(f"""
        {health['emoji']} **{health['label']}**
        
        {health['message']}
        
        {health['fee_warning']}
        
        💡 **建议**：可以交易，但请注意控制交易频率，减少手续费磨损
        """)
    else:
        st.error(f"""
        {health['emoji']} **{health['label']}**
        
        {health['message']}
        
        {health['fee_warning']}
        
        💡 **建议**：暂停交易，先通过工作收入积累本金至 ¥15,000 以上
        """)


def check_data_freshness() -> Dict[str, Any]:
    """
    检查数据新鲜度（Data Freshness Watchdog）
    
    读取 data/processed/ 目录下任意 CSV 的最后日期，
    与当前日期比较，判断数据是否过期。
    
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
        # 查找所有 CSV 文件
        csv_files = glob.glob(os.path.join(processed_path, "*.csv"))
        
        if not csv_files:
            return {
                'is_stale': True,
                'last_data_date': None,
                'days_old': 999,
                'message': '未找到任何数据文件，请先下载数据'
            }
        
        # 读取第一个 CSV 文件的最后一行日期
        import pandas as pd
        sample_file = csv_files[0]
        df = pd.read_csv(sample_file)
        
        if df.empty or 'date' not in df.columns:
            return {
                'is_stale': True,
                'last_data_date': None,
                'days_old': 999,
                'message': '数据文件格式异常'
            }
        
        # 获取最后日期
        last_date_str = df['date'].iloc[-1]
        last_data_date = datetime.strptime(last_date_str, '%Y-%m-%d').date()
        
        # 计算过期天数
        today = date.today()
        days_old = (today - last_data_date).days
        
        # 判断是否过期（超过 3 天视为过期）
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
    
    使用 akshare 获取交易日历，判断今天是否为交易日。
    
    Returns:
        {
            'is_trading_day': bool,     # 今天是否为交易日
            'message': str,             # 状态消息
            'next_trading_day': date,   # 下一个交易日（如果今天休市）
        }
    """
    try:
        import akshare as ak
        
        today = date.today()
        today_str = today.strftime('%Y%m%d')
        
        # 获取交易日历
        trade_dates_df = ak.tool_trade_date_hist_sina()
        
        if trade_dates_df is None or trade_dates_df.empty:
            return {
                'is_trading_day': True,  # 无法判断时默认为交易日
                'message': '无法获取交易日历',
                'next_trading_day': None
            }
        
        # 转换为日期列表
        trade_dates = pd.to_datetime(trade_dates_df['trade_date']).dt.date.tolist()
        
        # 判断今天是否为交易日
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
            
            # 判断休市原因
            weekday = today.weekday()
            if weekday >= 5:
                reason = "周末"
            else:
                reason = "节假日"
            
            return {
                'is_trading_day': False,
                'message': f'今天是{reason}休市日',
                'next_trading_day': next_trading_day
            }
            
    except Exception as e:
        logger.error(f"检查交易日历失败: {e}")
        return {
            'is_trading_day': True,  # 无法判断时默认为交易日
            'message': f'无法获取交易日历: {str(e)}',
            'next_trading_day': None
        }


def render_data_freshness_watchdog():
    """
    渲染数据新鲜度警告横幅
    
    如果数据过期且今天是交易日，显示红色警告横幅
    """
    freshness = check_data_freshness()
    trading_day = check_trading_day()
    
    # 只有在交易日且数据过期时才显示警告
    if freshness['is_stale'] and trading_day['is_trading_day']:
        st.error(f"""
        🚫 **数据已过期**
        
        检测到本地数据最后更新于 **{freshness['last_data_date'].strftime('%Y-%m-%d') if freshness['last_data_date'] else '未知'}**
        （已过期 {freshness['days_old']} 天）
        
        ⚠️ **请先前往"数据管理"页面更新数据，否则信号无效！**
        """)
        return True
    
    return False


def render_market_calendar_notice():
    """
    渲染休市安民告示
    
    如果今天是非交易日，显示友好的休市提示
    """
    import pandas as pd
    trading_day = check_trading_day()
    
    if not trading_day['is_trading_day']:
        next_day_str = ""
        if trading_day['next_trading_day']:
            next_day_str = f"下一个交易日：**{trading_day['next_trading_day'].strftime('%Y-%m-%d')}**"
        
        st.info(f"""
        ☕ **{trading_day['message']}，好好休息，不用看盘**
        
        {next_day_str}
        
        💡 **休市日建议**：
        - 复盘本周交易，总结经验教训
        - 阅读财经新闻，了解市场动态
        - 学习投资知识，提升交易水平
        - 陪伴家人朋友，享受生活
        """)
        return True
    
    return False


def render_onboarding_modal():
    """
    渲染新手引导弹窗（三大铁律）
    
    首次启动时展示，帮助管理用户预期
    """
    # 使用 session_state 记录是否已显示过
    if 'onboarding_shown' not in st.session_state:
        st.session_state.onboarding_shown = False
    
    if not st.session_state.onboarding_shown:
        with st.expander("🎓 **新手必读：三大铁律**", expanded=True):
            st.markdown("""
            ### 欢迎使用 MiniQuant-Lite！
            
            在开始之前，请牢记以下 **三大铁律**：
            
            ---
            
            #### 1️⃣ 别信回测
            
            > 回测结果 ≠ 实盘收益
            
            - 回测存在**幸存者偏差**（不包含退市股票）
            - 回测无法模拟真实的**滑点和流动性**
            - 历史表现**不代表**未来收益
            
            **正确态度**：把回测当作策略筛选工具，而非收益预测器
            
            ---
            
            #### 2️⃣ 别做超短
            
            > 小资金频繁交易 = 给券商打工
            
            - 5 万本金，每次交易手续费至少 **5 元**（低消）
            - 频繁交易会让手续费**吃掉大部分利润**
            - 本系统设计为**趋势跟踪**，不适合日内交易
            
            **正确态度**：耐心等待信号，减少无效交易
            
            ---
            
            #### 3️⃣ 别忘低消
            
            > 5 元低消是小资金的隐形杀手
            
            - 交易金额 1 万元，实际费率 = 5/10000 = **0.05%**（标准费率的 1.7 倍）
            - 交易金额 5 千元，实际费率 = 5/5000 = **0.1%**（标准费率的 3.3 倍）
            - 系统会自动计算并**预警高费率**交易
            
            **正确态度**：关注系统的高费率预警，避免小额交易
            
            ---
            
            ✅ **我已阅读并理解以上内容**
            """)
            
            if st.button("我已了解，开始使用", type="primary"):
                st.session_state.onboarding_shown = True
                st.rerun()


def get_risk_avoidance_stats() -> Dict[str, Any]:
    """
    获取避险统计数据
    
    检查大盘滤网状态，计算规避的下跌风险
    
    Returns:
        {
            'is_market_filter_active': bool,  # 大盘滤网是否生效
            'avoidance_days': int,            # 连续空仓天数
            'benchmark_drop': float,          # 空仓期间基准跌幅
            'monthly_avoidance_days': int,    # 本月累计空仓天数
            'benchmark_price': float,         # 当前沪深300价格
            'ma20': float,                    # MA20 值
            'status_message': str,            # 状态消息
        }
    """
    try:
        import akshare as ak
        
        settings = get_settings()
        
        # 获取沪深300指数数据
        end_date = date.today()
        start_date = end_date - timedelta(days=60)
        
        df = ak.index_zh_a_hist(
            symbol='000300',
            period='daily',
            start_date=start_date.strftime('%Y%m%d'),
            end_date=end_date.strftime('%Y%m%d')
        )
        
        if df is None or df.empty:
            return {
                'is_market_filter_active': False,
                'avoidance_days': 0,
                'benchmark_drop': 0.0,
                'monthly_avoidance_days': 0,
                'benchmark_price': 0.0,
                'ma20': 0.0,
                'status_message': '无法获取大盘数据'
            }
        
        # 获取收盘价列
        close_col = '收盘' if '收盘' in df.columns else 'close'
        close_prices = df[close_col].astype(float)
        
        # 计算 MA20
        ma20 = close_prices.rolling(window=20).mean().iloc[-1]
        current_price = close_prices.iloc[-1]
        
        # 判断大盘滤网是否生效
        is_filter_active = current_price < ma20
        
        # 计算连续空仓天数（大盘低于 MA20 的天数）
        avoidance_days = 0
        if is_filter_active:
            ma20_series = close_prices.rolling(window=20).mean()
            for i in range(len(close_prices) - 1, -1, -1):
                if close_prices.iloc[i] < ma20_series.iloc[i]:
                    avoidance_days += 1
                else:
                    break
        
        # 计算空仓期间基准跌幅
        benchmark_drop = 0.0
        if avoidance_days > 0 and avoidance_days < len(close_prices):
            start_price = close_prices.iloc[-avoidance_days - 1]
            benchmark_drop = (current_price - start_price) / start_price
        
        # 计算本月累计空仓天数
        monthly_avoidance_days = 0
        current_month = date.today().month
        date_col = '日期' if '日期' in df.columns else 'date'
        df['date_parsed'] = pd.to_datetime(df[date_col])
        ma20_series = close_prices.rolling(window=20).mean()
        
        for i in range(len(df)):
            if df['date_parsed'].iloc[i].month == current_month:
                if close_prices.iloc[i] < ma20_series.iloc[i]:
                    monthly_avoidance_days += 1
        
        # 生成状态消息
        if is_filter_active:
            status_message = f"大盘滤网生效中，沪深300 ({current_price:.2f}) < MA20 ({ma20:.2f})"
        else:
            status_message = f"大盘环境健康，沪深300 ({current_price:.2f}) > MA20 ({ma20:.2f})"
        
        return {
            'is_market_filter_active': is_filter_active,
            'avoidance_days': avoidance_days,
            'benchmark_drop': benchmark_drop,
            'monthly_avoidance_days': monthly_avoidance_days,
            'benchmark_price': current_price,
            'ma20': ma20,
            'status_message': status_message
        }
        
    except Exception as e:
        return {
            'is_market_filter_active': False,
            'avoidance_days': 0,
            'benchmark_drop': 0.0,
            'monthly_avoidance_days': 0,
            'benchmark_price': 0.0,
            'ma20': 0.0,
            'status_message': f'获取数据失败: {str(e)}'
        }


def get_today_signal_count() -> int:
    """
    获取今日信号数量
    
    Returns:
        今日信号数量
    """
    # 简化实现：返回 0，实际信号在信号页面生成
    return 0


def main():
    """首页主函数"""
    import pandas as pd
    
    logger.info("MiniQuant-Lite 首页加载")
    
    # 页面配置
    st.set_page_config(
        page_title="MiniQuant-Lite",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # 标题
    st.title("📈 MiniQuant-Lite")
    st.markdown("轻量级 A 股量化投资辅助系统 —— 5.5 万本金的「运钞车」")
    
    st.divider()
    
    # ========== 数据新鲜度警告（最高优先级）==========
    data_stale = render_data_freshness_watchdog()
    
    # ========== 休市安民告示 ==========
    is_holiday = render_market_calendar_notice()
    
    if data_stale or is_holiday:
        st.divider()
    
    # ========== 新手引导弹窗（三大铁律）==========
    render_onboarding_modal()
    
    # ========== 资金红绿灯 ==========
    st.subheader("🚦 资金红绿灯")
    render_capital_traffic_light()
    
    st.divider()
    
    # ========== 系统概览 ==========
    st.subheader("📊 系统概览")
    
    settings = get_settings()
    stock_pool = get_watchlist()
    signal_count = get_today_signal_count()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="初始资金",
            value=f"¥{settings.fund.initial_capital:,.0f}",
            help="配置的初始投资资金"
        )
    
    with col2:
        st.metric(
            label="股票池数量",
            value=f"{len(stock_pool)} 只",
            help="当前自选股池中的股票数量"
        )
    
    with col3:
        st.metric(
            label="最大持仓",
            value=f"{settings.position.max_positions_count} 只",
            help="同时最多持有的股票数量"
        )
    
    with col4:
        st.metric(
            label="今日信号",
            value=f"{signal_count} 个",
            help="今日生成的交易信号数量（请前往信号页面查看）"
        )
    
    # ========== 避险战绩看板 ==========
    st.divider()
    st.subheader("🛡️ 避险战绩看板")
    
    with st.spinner("正在获取大盘数据..."):
        risk_stats = get_risk_avoidance_stats()
    
    if risk_stats['is_market_filter_active']:
        # 当前处于空仓期
        st.warning(f"""
        **当前状态：大盘滤网生效中，建议空仓观望** ⚠️
        
        📊 沪深300: **{risk_stats['benchmark_price']:.2f}** < MA20: **{risk_stats['ma20']:.2f}**
        
        🛡️ 风控系统已为您规避下跌风险 **{risk_stats['avoidance_days']} 天**
        """)
        
        if risk_stats['benchmark_drop'] < 0:
            st.error(f"""
            📉 空仓期间沪深300下跌 **{abs(risk_stats['benchmark_drop']):.1%}**
            
            💡 **空仓也是一种盈利** —— 别人亏钱的时候，你没亏就是赚了！
            """)
        else:
            st.info(f"""
            📈 空仓期间沪深300上涨 **{risk_stats['benchmark_drop']:.1%}**
            
            💡 虽然错过了上涨，但风控纪律比短期收益更重要
            """)
    else:
        # 当前允许交易
        st.success(f"""
        **当前状态：大盘环境健康，允许交易** ✅
        
        📊 沪深300: **{risk_stats['benchmark_price']:.2f}** > MA20: **{risk_stats['ma20']:.2f}**
        
        🛡️ 本月风控系统已帮您规避 **{risk_stats['monthly_avoidance_days']} 天** 的下跌风险
        """)
    
    # ========== 标准作业程序 (SOP) ==========
    st.divider()
    st.subheader("📋 标准作业程序 (SOP)")
    
    st.info("""
    **推荐运行时间：交易日晚上 19:00 - 21:00**
    
    理由：
    1. 此时日线数据已完全归档（收盘数据通常在 16:30 后稳定）
    2. 上市公司当天的盘后公告（利空/利好）基本发布完毕
    3. 能读取到最完整的新闻信息
    """)
    
    st.markdown("""
    **标准操作流程：**
    
    ```
    晚上 19:00-21:00
        ↓
    运行系统生成信号
        ↓
    点击新闻链接，人眼扫一遍标题（10秒）
        ↓
    将信号放入券商 APP 的"条件单"
        ↓
    安心睡觉
        ↓
    次日开盘自动执行
    ```
    """)
    
    # ========== 核心功能说明 ==========
    st.divider()
    st.subheader("🎯 核心功能")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **保命模块：**
        - 🛡️ **大盘滤网** - 沪深300 < MA20 时强制空仓
        - 📊 **财报窗口期检测** - 财报披露前后 3 天自动剔除
        - 💰 **Smart Sizer** - 5% 现金缓冲、5 元低消预警
        """)
    
    with col2:
        st.markdown("""
        **盈利模块：**
        - 📈 **趋势策略** - MA60 + MACD + RSI 组合
        - 🎯 **止损止盈** - 硬止损 -8%，移动止盈 15%/5%
        - 🔍 **两阶段筛选** - 预剪枝 + 精筛，1 分钟内完成
        """)
    
    # ========== 风险提示 ==========
    st.divider()
    st.caption("""
    ⚠️ **风险提示**：本系统仅供学习研究使用，不构成投资建议。
    股市有风险，投资需谨慎。历史表现不代表未来收益。
    """)


if __name__ == "__main__":
    main()
