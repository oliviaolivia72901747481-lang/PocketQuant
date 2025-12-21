"""
MiniQuant-Lite 回测页面 (UI 修复完美版)

修复点：
1. 布局修复：结果展示不再被挤在右侧窄栏，而是全宽显示。
2. 状态保持：引入 session_state，防止筛选/排序表格时结果消失。
3. 视觉优化：调整了指标卡片和图表的比例。
"""

import streamlit as st
import sys
import os
from datetime import date, timedelta
from typing import Dict, Optional, List
import pandas as pd
import backtrader as bt
import plotly.express as px

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config.settings import get_settings
from config.stock_pool import get_watchlist
from core.data_feed import DataFeed
from backtest.run_backtest import BacktestConfig, BacktestResult, BacktestEngine

# ==========================================
# 策略定义 (RSI 梭哈策略)
# ==========================================
class TrendFilteredRSIStrategy(bt.Strategy):
    params = (
        ('rsi_period', 14),
        ('buy_threshold', 30),
        ('sell_threshold', 70),
        ('stop_loss', 0.05),
        ('take_profit', 0.15),
    )

    def __init__(self):
        self.dataclose = self.datas[0].close
        self.rsi = bt.indicators.RSI_Safe(self.dataclose, period=self.params.rsi_period)
        self.order = None
        self.buyprice = None

    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                self.buyprice = order.executed.price
            self.order = None

    def next(self):
        if self.order: return
        cash = self.broker.getcash()

        if not self.position:
            # 买入：RSI < 阈值 -> 全仓梭哈
            if self.rsi[0] < self.params.buy_threshold:
                # 预留 2% 资金防止手续费不够
                available_cash = cash * 0.98
                if available_cash > 0 and self.dataclose[0] > 0:
                    size = int(available_cash / self.dataclose[0])
                    if size >= 100:
                        self.order = self.buy(size=size)
        else:
            # 卖出：RSI > 阈值 或 止盈止损 -> 清仓
            if (self.rsi[0] > self.params.sell_threshold) or \
               (self.dataclose[0] < self.buyprice * (1.0 - self.params.stop_loss)) or \
               (self.dataclose[0] > self.buyprice * (1.0 + self.params.take_profit)):
                self.order = self.close()

# ==========================================
# 页面逻辑
# ==========================================

def get_data_feed():
    settings = get_settings()
    return DataFeed(settings.path.get_raw_path(), settings.path.get_processed_path())

def run_single_backtest(config, strategy_config, code, data_feed):
    """运行单只股票回测"""
    engine = BacktestEngine(config)
    
    # 加载数据
    df = data_feed.load_processed_data(code)
    if df is None or df.empty or len(df) < 20:
        return None
        
    engine.add_data(code, df)
    
    # 设置策略
    engine.set_strategy(
        TrendFilteredRSIStrategy, 
        buy_threshold=strategy_config['buy_threshold'],
        sell_threshold=strategy_config['sell_threshold'],
        stop_loss=strategy_config['stop_loss'],
        take_profit=strategy_config['take_profit']
    )
    
    return engine.run()

def run_batch_backtest(config, strategy_config, stock_pool):
    """运行批量回测"""
    data_feed = get_data_feed()
    results = []
    
    # 进度条
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total = len(stock_pool)
    for i, code in enumerate(stock_pool):
        status_text.text(f"正在回测 {code} ({i+1}/{total})...")
        
        try:
            res = run_single_backtest(config, strategy_config, code, data_feed)
            if res:
                results.append({
                    '代码': code,
                    '交易次数': res.trade_count,
                    '胜率': res.win_rate,
                    '总收益率': res.total_return,
                    '最终资产': res.final_value,
                    '最大回撤': res.max_drawdown,
                    '盈亏比': res.profit_factor
                })
        except Exception:
            pass
            
        progress_bar.progress((i + 1) / total)
    
    progress_bar.empty()
    status_text.empty()
    
    return pd.DataFrame(results)

def main():
    st.set_page_config(page_title="批量回测", page_icon="🧪", layout="wide")
    st.title("🧪 策略回测 (批量独立版)")
    st.markdown("💡 **说明**：本模式会对选中的每一只股票单独进行'全仓梭哈'测试，最后统计策略在整个股票池的普适性。")
    
    # 1. 参数配置区 (使用 expander 收纳)
    with st.expander("⚙️ 参数配置", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("开始日期", value=date.today() - timedelta(days=365))
            buy_threshold = st.number_input("RSI 买入阈值", value=30)
            initial_cash = st.number_input("每只初始资金", value=55000)
        with col2:
            end_date = st.date_input("结束日期", value=date.today())
            sell_threshold = st.number_input("RSI 卖出阈值", value=70)
            
    strategy_config = {
        'buy_threshold': buy_threshold, 'sell_threshold': sell_threshold, 
        'stop_loss': 0.05, 'take_profit': 0.15
    }
    
    backtest_config = BacktestConfig(
        initial_cash=float(initial_cash),
        commission_rate=0.0002, stamp_duty=0.001,
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d'),
        benchmark_code='000300', check_limit_up_down=False
    )
    
    # 2. 选股与控制区
    stock_pool = get_watchlist()
    
    # 布局修复：操作区独立
    col_sel, col_btn = st.columns([4, 1])
    
    with col_sel:
        use_all = st.checkbox(f"全选 ({len(stock_pool)}只)", value=True)
        if use_all:
            selected_stocks = stock_pool
        else:
            selected_stocks = st.multiselect("选择股票", stock_pool, default=stock_pool[:5])
    
    with col_btn:
        st.write("") # 占位对齐
        st.write("") 
        start_btn = st.button("🚀 开始批量回测", type="primary", use_container_width=True)

    # 3. 结果处理 (使用 session_state 防止刷新丢失)
    if 'batch_results' not in st.session_state:
        st.session_state.batch_results = None

    if start_btn:
        if not selected_stocks:
            st.error("请选择至少一只股票")
        else:
            with st.spinner("正在全力运算中..."):
                # 运行回测并保存到 session
                st.session_state.batch_results = run_batch_backtest(backtest_config, strategy_config, selected_stocks)

    # 4. 结果展示区 (布局修复：完全独立于上面的列)
    df_results = st.session_state.batch_results
    
    if df_results is not None and not df_results.empty:
        st.divider()
        st.subheader("📊 策略体检报告")
        
        # A. 核心统计指标 (4列布局，全宽显示)
        avg_return = df_results['总收益率'].mean()
        win_rate_mean = df_results['胜率'].mean()
        positive_count = len(df_results[df_results['总收益率'] > 0])
        positive_ratio = positive_count / len(df_results)
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("平均收益率", f"{avg_return:.2%}", delta="策略期望")
        m2.metric("正收益股票占比", f"{positive_ratio:.1%}", f"{positive_count}/{len(df_results)} 只")
        m3.metric("平均胜率", f"{win_rate_mean:.1%}")
        m4.metric("测试样本数", f"{len(df_results)} 只")
        
        # B. 收益分布图 (全宽)
        st.markdown("##### 📈 收益率分布直方图")
        fig = px.histogram(
            df_results, 
            x="总收益率", 
            nbins=20, 
            title=None, # 去掉标题节省空间
            labels={'总收益率': '收益率 (小数)'},
            color_discrete_sequence=['#4CAF50'] # 使用绿色
        )
        fig.add_vline(x=0, line_dash="dash", line_color="red", annotation_text="盈亏平衡线")
        fig.update_layout(margin=dict(t=10, b=10)) # 减少留白
        st.plotly_chart(fig, use_container_width=True)
        
        # C. 详细排名表 (全宽)
        st.markdown("##### 🏆 详细战绩排行榜")
        
        # 数据处理：数值转格式化字符串
        display_df = df_results.copy()
        
        # 排序：按收益率降序
        display_df = display_df.sort_values(by='总收益率', ascending=False)
        
        # 交互式表格
        st.dataframe(
            display_df,
            column_config={
                "总收益率": st.column_config.NumberColumn(format="%.2f%%"),
                "胜率": st.column_config.NumberColumn(format="%.1f%%"),
                "最大回撤": st.column_config.NumberColumn(format="%.1f%%"),
                "最终资产": st.column_config.NumberColumn(format="¥%.0f"),
                "盈亏比": st.column_config.NumberColumn(format="%.2f"),
                "代码": st.column_config.TextColumn(width="small"),
            },
            use_container_width=True,
            hide_index=True
        )
        
    elif df_results is not None and df_results.empty:
        st.warning("回测完成，但没有产生有效结果（可能数据不足）。")

if __name__ == "__main__":
    main()