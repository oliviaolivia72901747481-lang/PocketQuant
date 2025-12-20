"""
MiniQuant-Lite 回测页面

提供策略回测功能：
- 策略选择和参数配置
- 回测结果展示（核心风控指标突出显示）
- 策略净值 vs 沪深300基准对比图
- 回测局限性免责声明

Requirements: 7.4, 7.5, 7.8, 11.1, 11.2, 11.3, 11.4
"""

import streamlit as st
import sys
import os
from datetime import date, timedelta
from typing import Dict, Optional
import pandas as pd

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config.settings import get_settings
from config.stock_pool import get_watchlist
from core.data_feed import DataFeed
from backtest.run_backtest import BacktestConfig, BacktestResult, BacktestEngine
from strategies.trend_filtered_macd_strategy import TrendFilteredMACDStrategy
from core.sizers import SmallCapitalSizer


def get_data_feed() -> DataFeed:
    """获取 DataFeed 实例"""
    settings = get_settings()
    return DataFeed(
        raw_path=settings.path.get_raw_path(),
        processed_path=settings.path.get_processed_path()
    )


def render_disclaimer():
    """
    渲染回测局限性免责声明
    
    Requirements: 11.1, 11.2, 11.3, 11.4
    """
    st.warning("""
    ⚠️ **回测局限性说明（重要！请仔细阅读）**
    
    1. **仅基于技术指标**：本回测结果仅基于技术指标（MACD + MA60 + RSI + 止损止盈），
       **不包含新闻面人工过滤**。实盘中您应该结合新闻链接进行人工判断。
    
    2. **实盘交易次数可能更少**：由于实盘需要人工确认新闻面，实际交易次数可能少于回测显示。
    
    3. **无法模拟市场摩擦**：回测无法模拟真实的滑点、流动性不足、涨跌停无法成交等市场摩擦。
    
    4. **历史不代表未来**：历史表现不代表未来收益，请谨慎决策。
    
    5. **仅供学习研究**：本系统仅供学习研究使用，不构成投资建议。
    """)


def render_strategy_config() -> Dict:
    """
    渲染策略配置区域
    
    Returns:
        策略配置字典
    """
    st.subheader("⚙️ 策略配置")
    
    settings = get_settings()
    
    # 策略选择
    strategy_options = {
        "趋势滤网 MACD 策略（推荐）": "trend_filtered_macd",
    }
    
    selected_strategy = st.selectbox(
        "选择策略",
        options=list(strategy_options.keys()),
        help="选择要回测的交易策略"
    )
    
    strategy_type = strategy_options[selected_strategy]
    
    # 策略参数
    with st.expander("策略参数", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            ma_period = st.number_input(
                "MA 周期",
                min_value=10,
                max_value=120,
                value=settings.strategy.ma_period,
                help="趋势均线周期（默认 MA60）"
            )
            
            rsi_upper = st.number_input(
                "RSI 上限",
                min_value=50,
                max_value=95,
                value=settings.strategy.rsi_upper,
                help="RSI 超过此值不买入"
            )
        
        with col2:
            hard_stop_loss = st.slider(
                "硬止损比例",
                min_value=-0.15,
                max_value=-0.03,
                value=settings.strategy.hard_stop_loss,
                step=0.01,
                format="%.0f%%",
                help="亏损达到此比例时无条件止损"
            )
            
            trailing_start = st.slider(
                "移动止盈启动",
                min_value=0.05,
                max_value=0.30,
                value=settings.strategy.trailing_start,
                step=0.01,
                format="%.0f%%",
                help="盈利达到此比例后启动移动止盈"
            )
    
    return {
        'strategy_type': strategy_type,
        'ma_period': ma_period,
        'rsi_upper': rsi_upper,
        'hard_stop_loss': hard_stop_loss,
        'trailing_start': trailing_start
    }


def render_backtest_config() -> BacktestConfig:
    """
    渲染回测配置区域
    
    Returns:
        BacktestConfig 对象
    """
    st.subheader("📅 回测配置")
    
    settings = get_settings()
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 日期范围
        default_end = date.today()
        default_start = default_end - timedelta(days=365)
        
        start_date = st.date_input(
            "开始日期",
            value=default_start,
            help="回测开始日期"
        )
        
        initial_cash = st.number_input(
            "初始资金（元）",
            min_value=10000,
            max_value=1000000,
            value=int(settings.fund.initial_capital),
            step=5000,
            help="回测初始资金"
        )
    
    with col2:
        end_date = st.date_input(
            "结束日期",
            value=default_end,
            help="回测结束日期"
        )
        
        commission_rate = st.number_input(
            "手续费率（万分之）",
            min_value=1,
            max_value=30,
            value=int(settings.fund.commission_rate * 10000),
            help="券商手续费率"
        )
    
    return BacktestConfig(
        initial_cash=float(initial_cash),
        commission_rate=commission_rate / 10000,
        stamp_duty=settings.fund.stamp_tax_rate,
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d'),
        benchmark_code='000300',
        check_limit_up_down=True
    )


def render_backtest_result(result: BacktestResult):
    """
    渲染回测结果
    
    Args:
        result: BacktestResult 对象
        
    Requirements: 7.4, 7.5, 7.8
    """
    st.subheader("📊 回测结果")
    
    # ========== 核心风控指标（突出显示）==========
    st.markdown("#### 🛡️ 核心风控指标（小散户重点关注）")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # 胜率
        win_rate_color = "normal" if result.win_rate >= 0.5 else "inverse"
        st.metric(
            label="胜率 Winning Rate",
            value=f"{result.win_rate:.1%}",
            delta="良好" if result.win_rate >= 0.5 else "偏低",
            delta_color=win_rate_color,
            help="盈利交易次数 / 总交易次数，建议 > 50%"
        )
    
    with col2:
        # 最大回撤
        dd_color = "normal" if result.max_drawdown <= 0.15 else "inverse"
        st.metric(
            label="最大回撤 Max Drawdown",
            value=f"{result.max_drawdown:.1%}",
            delta="可控" if result.max_drawdown <= 0.15 else "偏高",
            delta_color="inverse" if result.max_drawdown > 0.15 else "off",
            help="资金曲线从峰值到谷值的最大跌幅，建议 < 15%"
        )
    
    with col3:
        # 盈亏比
        pf_color = "normal" if result.profit_factor >= 1.5 else "inverse"
        pf_display = f"{result.profit_factor:.2f}" if result.profit_factor < float('inf') else "∞"
        st.metric(
            label="盈亏比 Profit Factor",
            value=pf_display,
            delta="良好" if result.profit_factor >= 1.5 else "偏低",
            delta_color=pf_color,
            help="平均盈利 / 平均亏损，建议 > 1.5"
        )
    
    # ========== 收益指标 ==========
    st.markdown("#### 💰 收益指标")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="总收益率",
            value=f"{result.total_return:.2%}",
            help="回测期间的总收益率"
        )
    
    with col2:
        st.metric(
            label="年化收益率",
            value=f"{result.annual_return:.2%}",
            help="折算为年化的收益率"
        )
    
    with col3:
        st.metric(
            label="基准收益率",
            value=f"{result.benchmark_return:.2%}",
            help="同期沪深300指数收益率"
        )
    
    with col4:
        alpha_color = "normal" if result.alpha > 0 else "inverse"
        st.metric(
            label="超额收益 Alpha",
            value=f"{result.alpha:.2%}",
            delta="跑赢大盘" if result.alpha > 0 else "跑输大盘",
            delta_color=alpha_color,
            help="策略收益 - 基准收益"
        )
    
    # ========== 交易统计 ==========
    st.markdown("#### 📈 交易统计")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="交易次数",
            value=f"{result.trade_count} 次",
            help="回测期间的总交易次数"
        )
    
    with col2:
        st.metric(
            label="夏普比率",
            value=f"{result.sharpe_ratio:.2f}",
            help="风险调整后收益，建议 > 1"
        )
    
    with col3:
        st.metric(
            label="平均盈利",
            value=f"¥{result.avg_win:,.0f}",
            help="盈利交易的平均盈利金额"
        )
    
    with col4:
        st.metric(
            label="平均亏损",
            value=f"¥{abs(result.avg_loss):,.0f}",
            help="亏损交易的平均亏损金额"
        )

    
    # ========== 资金曲线对比图 ==========
    st.markdown("#### 📉 策略净值 vs 沪深300基准")
    
    if not result.equity_curve.empty and not result.benchmark_curve.empty:
        try:
            import plotly.graph_objects as go
            
            # 计算策略净值
            equity_df = result.equity_curve.copy()
            equity_df['net_value'] = equity_df['value'] / result.initial_value
            
            # 创建图表
            fig = go.Figure()
            
            # 策略净值曲线
            fig.add_trace(go.Scatter(
                x=equity_df['date'],
                y=equity_df['net_value'],
                name='策略净值',
                line=dict(color='#1f77b4', width=2),
                hovertemplate='日期: %{x}<br>净值: %{y:.4f}<extra></extra>'
            ))
            
            # 基准净值曲线
            fig.add_trace(go.Scatter(
                x=result.benchmark_curve['date'],
                y=result.benchmark_curve['value'],
                name='沪深300基准',
                line=dict(color='#7f7f7f', width=2, dash='dash'),
                hovertemplate='日期: %{x}<br>净值: %{y:.4f}<extra></extra>'
            ))
            
            # 图表布局
            fig.update_layout(
                title='策略净值 vs 沪深300基准对比',
                xaxis_title='日期',
                yaxis_title='净值',
                hovermode='x unified',
                legend=dict(
                    yanchor="top",
                    y=0.99,
                    xanchor="left",
                    x=0.01
                ),
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
        except ImportError:
            st.warning("请安装 plotly 以显示图表: pip install plotly")
            
            # 使用 Streamlit 原生图表作为备选
            chart_data = pd.DataFrame({
                '策略净值': result.equity_curve['value'] / result.initial_value,
                '基准净值': result.benchmark_curve['value'].values[:len(result.equity_curve)]
            })
            st.line_chart(chart_data)
    else:
        st.info("无法生成净值曲线图（数据不足）")
    
    # ========== 交易明细 ==========
    st.markdown("#### 📝 交易明细")
    
    if result.trade_log:
        trade_df = pd.DataFrame(result.trade_log)
        
        # 格式化列
        if 'pnl' in trade_df.columns:
            trade_df['盈亏'] = trade_df['pnl'].apply(lambda x: f"¥{x:,.2f}")
        if 'exit_reason' in trade_df.columns:
            trade_df['退出原因'] = trade_df['exit_reason'].fillna('-')
        
        # 高亮止损交易
        def highlight_stop_loss(row):
            if 'exit_reason' in row and '止损' in str(row.get('exit_reason', '')):
                return ['background-color: #ffcccc'] * len(row)
            return [''] * len(row)
        
        # 选择显示的列
        display_cols = ['datetime', 'code', 'entry_price', 'exit_price', 'size', '盈亏', '退出原因']
        display_cols = [c for c in display_cols if c in trade_df.columns]
        
        if display_cols:
            st.dataframe(
                trade_df[display_cols].style.apply(highlight_stop_loss, axis=1),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.dataframe(trade_df, use_container_width=True, hide_index=True)
    else:
        st.info("回测期间无交易记录")


def run_backtest(
    config: BacktestConfig,
    strategy_config: Dict,
    stock_pool: list
) -> Optional[BacktestResult]:
    """
    执行回测
    
    Args:
        config: 回测配置
        strategy_config: 策略配置
        stock_pool: 股票池
    
    Returns:
        BacktestResult 或 None
    """
    data_feed = get_data_feed()
    settings = get_settings()
    
    # 创建回测引擎
    engine = BacktestEngine(config)
    
    # 加载股票数据
    loaded_count = 0
    for code in stock_pool:
        df = data_feed.load_processed_data(code)
        if df is not None and not df.empty:
            engine.add_data(code, df)
            loaded_count += 1
    
    if loaded_count == 0:
        st.error("没有可用的股票数据，请先下载数据")
        return None
    
    # 加载基准数据
    engine.load_benchmark(config.benchmark_code)
    
    # 设置策略
    strategy_kwargs = {
        'ma_period': strategy_config['ma_period'],
        'rsi_upper': strategy_config['rsi_upper'],
        'hard_stop_loss': strategy_config['hard_stop_loss'],
        'trailing_start': strategy_config['trailing_start'],
    }
    engine.set_strategy(TrendFilteredMACDStrategy, **strategy_kwargs)
    
    # 设置仓位管理器
    engine.set_sizer(
        SmallCapitalSizer,
        max_positions_count=settings.position.max_positions_count,
        min_trade_amount=settings.position.min_trade_amount,
        cash_buffer=settings.position.cash_buffer
    )
    
    # 执行回测
    return engine.run()



def main():
    """回测页面主函数"""
    st.set_page_config(
        page_title="策略回测 - MiniQuant-Lite",
        page_icon="🧪",
        layout="wide"
    )
    
    st.title("🧪 策略回测")
    st.markdown("回测交易策略，评估历史表现")
    
    st.divider()
    
    # 回测局限性免责声明（显著位置）
    render_disclaimer()
    
    st.divider()
    
    # 策略配置
    strategy_config = render_strategy_config()
    
    st.divider()
    
    # 回测配置
    backtest_config = render_backtest_config()
    
    st.divider()
    
    # 股票池选择
    st.subheader("📋 股票池")
    
    stock_pool = get_watchlist()
    
    use_all = st.checkbox(
        f"使用全部股票池（{len(stock_pool)} 只）",
        value=True,
        help="勾选后使用股票池中所有股票进行回测"
    )
    
    if not use_all:
        selected_stocks = st.multiselect(
            "选择回测股票",
            options=stock_pool,
            default=stock_pool[:3] if len(stock_pool) >= 3 else stock_pool,
            help="选择要参与回测的股票"
        )
    else:
        selected_stocks = stock_pool
    
    st.divider()
    
    # 执行回测按钮
    if st.button("🚀 开始回测", type="primary", disabled=not selected_stocks):
        if not selected_stocks:
            st.warning("请选择要回测的股票")
            return
        
        with st.spinner("正在执行回测，请稍候..."):
            result = run_backtest(
                config=backtest_config,
                strategy_config=strategy_config,
                stock_pool=selected_stocks
            )
        
        if result:
            st.divider()
            render_backtest_result(result)
        else:
            st.error("回测执行失败，请检查数据和配置")


if __name__ == "__main__":
    main()
