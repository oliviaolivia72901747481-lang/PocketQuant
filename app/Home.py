"""
MiniQuant-Lite 首页

系统概览页面，展示：
- 系统基本信息（初始资金、股票池数量、今日信号）
- 避险战绩看板（大盘滤网生效期间规避的下跌风险）

Requirements: 7.1, 7.9
"""

import streamlit as st
import sys
import os
from datetime import date, datetime, timedelta
from typing import Dict, Any

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import get_settings
from config.stock_pool import get_watchlist
from core.logging_config import ensure_logging_initialized, get_logger

# 初始化日志系统
ensure_logging_initialized()
logger = get_logger(__name__)


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
