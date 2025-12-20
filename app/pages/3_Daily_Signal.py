"""
MiniQuant-Lite 每日信号页面

提供每日交易信号功能：
- 早安确认清单（Pre-market Checklist）
- 信号表格（含新闻链接、财报窗口期警告）
- 高费率预警红色高亮

Requirements: 7.6, 7.7, 7.10, 12.1, 12.2, 12.3
"""

import streamlit as st
import sys
import os
from datetime import date, datetime
from typing import List, Optional
import pandas as pd

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config.settings import get_settings
from config.stock_pool import get_watchlist
from core.data_feed import DataFeed
from core.signal_generator import SignalGenerator, TradingSignal, SignalType
from core.screener import Screener


def get_data_feed() -> DataFeed:
    """获取 DataFeed 实例"""
    settings = get_settings()
    return DataFeed(
        raw_path=settings.path.get_raw_path(),
        processed_path=settings.path.get_processed_path()
    )


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
    
    # 转换为 DataFrame
    data = []
    for signal in signals:
        row = {
            '股票代码': signal.code,
            '股票名称': signal.name,
            '信号类型': signal.signal_type.value,
            '限价上限': f"¥{signal.limit_cap:.2f}",
            '交易金额': f"¥{signal.trade_amount:,.0f}",
            '费率': f"{signal.actual_fee_rate:.4%}",
            '财报窗口期': '⚠️ 是' if signal.in_report_window else '否',
            '高费率预警': '⚠️ 是' if signal.high_fee_warning else '否',
            '新闻链接': signal.news_url
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
            '新闻链接': st.column_config.LinkColumn('新闻链接', display_text='🔗 查看')
        }
    )


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
    
    # 生成信号按钮
    if st.button("🚀 生成今日信号", type="primary", disabled=not selected_stocks):
        if not selected_stocks:
            st.warning("请选择要生成信号的股票")
            return
        
        with st.spinner("正在生成交易信号，请稍候..."):
            signals = generate_signals(selected_stocks)
        
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
    
    # 历史信号（简化版，仅显示提示）
    st.divider()
    st.subheader("📜 历史信号")
    st.info("历史信号功能开发中，敬请期待...")
    
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
