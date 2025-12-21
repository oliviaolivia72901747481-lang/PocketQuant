"""
MiniQuant-Lite 参数自动调优 (修复版)

修复内容：
1. 解决了 KeyError: 'datetime' 报错。
2. 增加了对日期列/索引的智能识别，无论数据格式如何都能正常筛选。
"""

import streamlit as st
import sys
import os
import pandas as pd
import backtrader as bt
import plotly.graph_objects as go
import itertools
from datetime import date, timedelta
import time

# 添加项目根目录
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config.settings import get_settings
from config.stock_pool import get_watchlist
from core.data_feed import DataFeed

# ==========================================
# 策略定义
# ==========================================
class OptimizationStrategy(bt.Strategy):
    params = (
        ('buy_threshold', 30),
        ('sell_threshold', 70), 
        ('stop_loss', 0.05),
        ('take_profit', 0.15),
    )

    def __init__(self):
        self.dataclose = self.datas[0].close
        # 使用 RSI_Safe 避免初期数据不足报错
        self.rsi = bt.indicators.RSI_Safe(self.dataclose, period=14)
        self.order = None
        self.buyprice = None

    def next(self):
        if self.order: return
        cash = self.broker.getcash()

        if not self.position:
            if self.rsi[0] < self.params.buy_threshold:
                # 简单全仓模拟
                available_cash = cash * 0.98
                if self.dataclose[0] > 0:
                    size = int(available_cash / self.dataclose[0])
                    if size > 0:
                        self.order = self.buy(size=size)
        else:
            if (self.rsi[0] > self.params.sell_threshold) or \
               (self.dataclose[0] < self.buyprice * (1.0 - self.params.stop_loss)) or \
               (self.dataclose[0] > self.buyprice * (1.0 + self.params.take_profit)):
                self.order = self.close()

# ==========================================
# 核心引擎 (关键修复在这里)
# ==========================================
def get_data_feed():
    settings = get_settings()
    return DataFeed(settings.path.get_raw_path(), settings.path.get_processed_path())

def run_single_backtest_fast(data_feed, code, start_date, end_date, buy_t, sell_t):
    """
    极速回测单元（不画图，只返回结果）
    """
    df = data_feed.load_processed_data(code)
    if df is None or df.empty or len(df) < 60:
        return None

    # ========== 🔧 修复开始：稳健的日期过滤逻辑 ==========
    
    # 1. 尝试将索引重置为列 (如果 datetime 在索引里)
    if 'datetime' not in df.columns:
        df = df.reset_index()
    
    # 2. 兼容性处理：如果列名叫 'date'，重命名为 'datetime'
    if 'date' in df.columns:
        df = df.rename(columns={'date': 'datetime'})
        
    # 3. 再次检查，如果还是没有 datetime 列，说明数据结构异常，跳过
    if 'datetime' not in df.columns:
        return None

    # 4. 确保格式正确并执行筛选
    try:
        df['datetime'] = pd.to_datetime(df['datetime'])
        mask = (df['datetime'] >= pd.to_datetime(start_date)) & (df['datetime'] <= pd.to_datetime(end_date))
        df = df.loc[mask]
        
        if df.empty: return None

        # 5. 筛选完后，必须把 datetime 设回索引 (Backtrader 要求)
        df = df.set_index('datetime')
    except Exception:
        return None
        
    # ========== 🔧 修复结束 ==========

    cerebro = bt.Cerebro(stdstats=False) # 关闭统计以提速
    
    data = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data)
    
    cerebro.addstrategy(
        OptimizationStrategy,
        buy_threshold=buy_t,
        sell_threshold=sell_t
    )
    
    cerebro.broker.setcash(55000)
    cerebro.broker.setcommission(commission=0.0002)
    
    try:
        init_val = cerebro.broker.getvalue()
        cerebro.run()
        final_val = cerebro.broker.getvalue()
        return (final_val - init_val) / init_val # 返回收益率
    except:
        return None

def run_batch_grid_search(stock_list, start_date, end_date, buy_range, sell_range):
    """
    批量全池优选逻辑
    """
    data_feed = get_data_feed()
    
    # 生成所有参数组合
    param_combinations = list(itertools.product(buy_range, sell_range))
    total_steps = len(param_combinations)
    
    results = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    start_time = time.time()
    
    for i, (b, s) in enumerate(param_combinations):
        status_text.text(f"正在测试组合: 买入<{b} / 卖出>{s} ({i+1}/{total_steps})")
        
        returns = []
        for code in stock_list:
            ret = run_single_backtest_fast(data_feed, code, start_date, end_date, b, s)
            if ret is not None:
                returns.append(ret)
        
        if returns:
            avg_ret = sum(returns) / len(returns)
            win_ratio = len([r for r in returns if r > 0]) / len(returns)
            
            results.append({
                '买入阈值': b,
                '卖出阈值': s,
                '平均收益率(%)': round(avg_ret * 100, 2),
                '正收益占比(%)': round(win_ratio * 100, 1),
                '样本数': len(returns)
            })
            
        progress_bar.progress((i + 1) / total_steps)

    elapsed_time = time.time() - start_time
    st.toast(f"✅ 计算完成！耗时 {elapsed_time:.1f} 秒")
    
    return pd.DataFrame(results)

# ==========================================
# 页面 UI
# ==========================================
def main():
    st.set_page_config(page_title="参数超算中心", page_icon="⚡", layout="wide")
    st.title("⚡ 参数超算中心")
    st.markdown("这里是量化系统的核心大脑。你可以针对单只股票寻找极致参数，也可以针对全市场寻找'万能公式'。")

    tab1, tab2 = st.tabs(["🎯 单股精调 (Single)", "🌍 全池普选 (Batch)"])

    # ---------- TAB 1: 单股优化 ----------
    with tab1:
        st.caption("针对某一只特定的股票，寻找它的性格密码。")
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            stock_pool = get_watchlist()
            target_stock = st.selectbox("选择股票", stock_pool, index=0)
        with col_s2:
            st.info("👈 请切换到【全池普选】标签页使用更强大的批量功能")

    # ---------- TAB 2: 批量全池优选 ----------
    with tab2:
        st.caption("👑 **上帝视角**：寻找一套参数，使得整个股票池的平均收益最大化。这是防止过拟合的最佳手段。")
        
        with st.container():
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown("#### 1. 数据范围")
                batch_start_date = st.date_input("回测开始", value=date.today() - timedelta(days=365*2), key="b_start_d")
                batch_end_date = st.date_input("回测结束", value=date.today(), key="b_end_d")
                
                full_pool = get_watchlist()
                use_sample = st.checkbox("仅使用随机样本 (速度快)", value=True, help="如果勾选，只随机抽20只股票测算；不勾选则测73只(很慢)")
                
                import random
                if use_sample:
                    random.seed(42)
                    test_pool = random.sample(full_pool, min(20, len(full_pool)))
                    st.success(f"已抽样 {len(test_pool)} 只股票进行加速运算")
                else:
                    test_pool = full_pool
                    st.warning(f"即将运算全部 {len(test_pool)} 只股票，可能需要几分钟。")

            with c2:
                st.markdown("#### 2. RSI 买入 (Buy)")
                b_min = st.number_input("Min", 20, 40, 20)
                b_max = st.number_input("Max", 20, 50, 40)
                b_step = st.number_input("步长", 1, 10, 5)

            with c3:
                st.markdown("#### 3. RSI 卖出 (Sell)")
                s_min = st.number_input("Min", 60, 80, 60)
                s_max = st.number_input("Max", 60, 90, 80)
                s_step = st.number_input("步长 (S)", 1, 10, 5)

        # 计算量预估
        b_range = range(b_min, b_max + 1, b_step)
        s_range = range(s_min, s_max + 1, s_step)
        total_combos = len(b_range) * len(s_range)
        total_ops = total_combos * len(test_pool)
        
        st.markdown(f"""
        ---
        📊 **任务量评估**：
        - 参数组合数：**{total_combos}** 组
        - 股票数量：**{len(test_pool)}** 只
        - 总回测次数：**{total_ops}** 次
        """)
        
        if st.button("🚀 启动全市场扫描", type="primary"):
            df_res = run_batch_grid_search(test_pool, batch_start_date, batch_end_date, b_range, s_range)
            
            if not df_res.empty:
                st.divider()
                
                # 1. 最优解
                best = df_res.loc[df_res['平均收益率(%)'].idxmax()]
                st.balloons()
                st.success(f"🏆 **全市场最优参数**：买入 **{best['买入阈值']}** / 卖出 **{best['卖出阈值']}**")
                
                col_m1, col_m2 = st.columns(2)
                col_m1.metric("该组合平均收益率", f"{best['平均收益率(%)']}%")
                col_m2.metric("该组合正收益占比", f"{best['正收益占比(%)']}%")
                
                # 2. 热力图
                st.subheader("🔥 参数地形图")
                pivot = df_res.pivot(index='买入阈值', columns='卖出阈值', values='平均收益率(%)')
                fig = go.Figure(data=go.Heatmap(
                    z=pivot.values,
                    x=pivot.columns,
                    y=pivot.index,
                    colorscale='RdYlGn',
                    colorbar=dict(title='平均收益%')
                ))
                st.plotly_chart(fig, use_container_width=True)
                
                with st.expander("查看详细数据表"):
                    st.dataframe(df_res.sort_values('平均收益率(%)', ascending=False), use_container_width=True)

if __name__ == "__main__":
    main()