"""
MiniQuant-Lite 回测页面 (多策略版)

支持两种策略：
1. 趋势滤网 MACD 策略 - 适合趋势行情，让利润奔跑
2. RSI 超卖反弹策略 - 适合震荡行情，快进快出

用户可在 UI 上选择策略类型，确保回测与信号生成使用相同策略。
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
from strategies.rsrs_strategy import RSRSStrategy
from core.parameter_sensitivity import (
    ParameterRange, ParameterGrid, GridSearcher, GridSearchResult,
    RobustnessDiagnostics, HeatmapRenderer, STRATEGY_PARAM_CONFIGS,
    get_default_grid
)


# ==========================================
# 策略定义：RSI 超卖反弹策略
# ==========================================
class RSIMeanReversionStrategy(bt.Strategy):
    """
    RSI 超卖反弹策略
    
    适合震荡行情，快进快出，积累小胜为大胜。
    
    买入条件：RSI < 30（超卖区反弹）
    卖出条件：RSI > 70 或 止损 -5% 或 止盈 +15%
    """
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
        if self.order:
            return
        cash = self.broker.getcash()

        if not self.position:
            # 买入：RSI < 阈值
            if self.rsi[0] < self.params.buy_threshold:
                available_cash = cash * 0.98
                if available_cash > 0 and self.dataclose[0] > 0:
                    size = int(available_cash / self.dataclose[0])
                    if size >= 100:
                        self.order = self.buy(size=size)
        else:
            # 卖出：RSI > 阈值 或 止盈止损
            if self.buyprice and self.buyprice > 0:
                if (self.rsi[0] > self.params.sell_threshold) or \
                   (self.dataclose[0] < self.buyprice * (1.0 - self.params.stop_loss)) or \
                   (self.dataclose[0] > self.buyprice * (1.0 + self.params.take_profit)):
                    self.order = self.close()


# ==========================================
# 策略配置
# ==========================================
# 策略配置（RSI 超卖反弹策略为默认）
STRATEGY_OPTIONS = {
    "RSI 超卖反弹策略": {
        "class": RSIMeanReversionStrategy,
        "description": "适合震荡行情，快进快出。买入：RSI<30超卖；卖出：RSI>70或止损-5%或止盈+15%",
        "min_data_days": 20,
        "params": ["buy_threshold", "sell_threshold", "stop_loss", "take_profit"],
    },
    "RSRS 阻力支撑策略": {
        "class": RSRSStrategy,
        "description": "基于阻力支撑相对强度。买入：RSRS标准分>0.7（市场情绪好）；卖出：RSRS标准分<-0.7或止损-6%",
        "min_data_days": 100,
        "params": ["n_period", "m_period", "buy_threshold", "sell_threshold", "hard_stop_loss"],
    },
}


# ==========================================
# 页面逻辑
# ==========================================

def get_data_feed():
    settings = get_settings()
    return DataFeed(settings.path.get_raw_path(), settings.path.get_processed_path())


def run_single_backtest(config, strategy_name, strategy_config, code, data_feed):
    """运行单只股票回测"""
    strategy_info = STRATEGY_OPTIONS[strategy_name]
    engine = BacktestEngine(config)
    
    # 加载数据
    df = data_feed.load_processed_data(code)
    min_days = strategy_info["min_data_days"]
    if df is None or df.empty or len(df) < min_days:
        return None
        
    engine.add_data(code, df)
    
    # 设置策略
    engine.set_strategy(strategy_info["class"], **strategy_config)
    
    return engine.run()


def run_batch_backtest(config, strategy_name, strategy_config, stock_pool):
    """运行批量回测"""
    data_feed = get_data_feed()
    results = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total = len(stock_pool)
    for i, code in enumerate(stock_pool):
        status_text.text(f"正在回测 {code} ({i+1}/{total})...")
        
        try:
            res = run_single_backtest(config, strategy_name, strategy_config, code, data_feed)
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
        except Exception as e:
            print(f"❌ 股票 {code} 回测出错: {str(e)}")
            
        progress_bar.progress((i + 1) / total)
    
    progress_bar.empty()
    status_text.empty()
    
    return pd.DataFrame(results)


def render_commission_analysis(df_results: pd.DataFrame, initial_cash: float, commission_rate: float = 0.0003, min_commission: float = 5.0):
    """渲染"低消刺客"分析图"""
    st.markdown("##### 💸 低消刺客分析")
    
    total_trades = df_results['交易次数'].sum()
    avg_trade_amount = initial_cash * 0.9
    standard_fee = avg_trade_amount * commission_rate
    actual_fee_per_trade = max(min_commission, standard_fee)
    stamp_duty = avg_trade_amount * 0.001
    total_fee_per_round = actual_fee_per_trade * 2 + stamp_duty
    total_commission = total_fee_per_round * total_trades
    total_profit = df_results['总收益率'].mean() * initial_cash * len(df_results)
    net_profit = total_profit - total_commission
    
    if total_profit > 0:
        commission_ratio = total_commission / total_profit
    else:
        commission_ratio = 1.0 if total_commission > 0 else 0.0
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("总交易次数", f"{total_trades} 次")
    
    with col2:
        st.metric(
            "估算总手续费",
            f"¥{total_commission:,.0f}",
            delta=f"占毛利润 {commission_ratio:.1%}" if total_profit > 0 else "N/A",
            delta_color="inverse"
        )
    
    with col3:
        if total_profit > 0:
            st.metric(
                "手续费磨损率",
                f"{commission_ratio:.1%}",
                delta="过高" if commission_ratio > 0.3 else "正常",
                delta_color="inverse" if commission_ratio > 0.3 else "normal"
            )
        else:
            st.metric("手续费磨损率", "N/A")
    
    # 饼图
    if total_profit > 0:
        import plotly.graph_objects as go
        
        if net_profit > 0:
            labels = ['净利润（你的）', '手续费（券商的）']
            values = [net_profit, total_commission]
            colors = ['#4CAF50', '#f44336']
        else:
            labels = ['亏损', '手续费（券商的）']
            values = [abs(net_profit), total_commission]
            colors = ['#ff9800', '#f44336']
        
        fig = go.Figure(data=[go.Pie(
            labels=labels, values=values, hole=0.4,
            marker_colors=colors, textinfo='label+percent', textposition='outside'
        )])
        fig.update_layout(title_text="利润分配：你 vs 券商", showlegend=True, height=300, margin=dict(t=50, b=20, l=20, r=20))
        st.plotly_chart(fig, use_container_width=True)
    
    # 警告
    if commission_ratio > 0.3:
        st.error(f"⚠️ **策略在该资金量下不可行！** 手续费占毛利润 {commission_ratio:.1%}，超过 30% 警戒线。")
    elif commission_ratio > 0.15:
        st.warning(f"⚠️ **手续费磨损较高** ({commission_ratio:.1%})，建议减少交易频率。")
    else:
        st.success(f"✅ **手续费控制良好** ({commission_ratio:.1%})")


# ==========================================
# 参数敏感性分析
# ==========================================

def render_sensitivity_analysis(strategy_name: str, strategy_config: Dict, backtest_config, selected_stocks: List[str]):
    """渲染参数敏感性分析面板"""
    st.markdown("##### 🔬 参数敏感性分析")
    st.caption("检测策略是否稳健，还是只是蒙的")
    
    # 获取策略的参数配置
    param_config = STRATEGY_PARAM_CONFIGS.get(strategy_name)
    if not param_config:
        st.warning("该策略暂不支持参数敏感性分析")
        return
    
    primary_params = param_config["primary_params"]
    if len(primary_params) < 2:
        st.warning("该策略参数不足，无法进行二维分析")
        return
    
    # 判断参数是否为浮点数类型
    x_is_float = isinstance(primary_params[0].step, float) and primary_params[0].step < 1
    y_is_float = isinstance(primary_params[1].step, float) and primary_params[1].step < 1
    
    # 参数范围配置
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"**横轴: {primary_params[0].display_name}**")
        if x_is_float:
            x_min = st.number_input(
                "最小值", 
                value=float(primary_params[0].min_value),
                format="%.2f",
                key="sens_x_min"
            )
            x_max = st.number_input(
                "最大值", 
                value=float(primary_params[0].max_value),
                format="%.2f",
                key="sens_x_max"
            )
            x_step = st.number_input(
                "步长", 
                value=float(primary_params[0].step),
                min_value=0.01,
                format="%.2f",
                key="sens_x_step"
            )
        else:
            x_min = st.number_input(
                "最小值", 
                value=int(primary_params[0].min_value),
                key="sens_x_min"
            )
            x_max = st.number_input(
                "最大值", 
                value=int(primary_params[0].max_value),
                key="sens_x_max"
            )
            x_step = st.number_input(
                "步长", 
                value=int(primary_params[0].step),
                min_value=1,
                key="sens_x_step"
            )
    
    with col2:
        st.markdown(f"**纵轴: {primary_params[1].display_name}**")
        if y_is_float:
            y_min = st.number_input(
                "最小值", 
                value=float(primary_params[1].min_value),
                format="%.2f",
                key="sens_y_min"
            )
            y_max = st.number_input(
                "最大值", 
                value=float(primary_params[1].max_value),
                format="%.2f",
                key="sens_y_max"
            )
            y_step = st.number_input(
                "步长", 
                value=float(primary_params[1].step),
                min_value=0.01,
                format="%.2f",
                key="sens_y_step"
            )
        else:
            y_min = st.number_input(
                "最小值", 
                value=int(primary_params[1].min_value),
                key="sens_y_min"
            )
            y_max = st.number_input(
                "最大值", 
                value=int(primary_params[1].max_value),
                key="sens_y_max"
            )
            y_step = st.number_input(
                "步长", 
                value=int(primary_params[1].step),
                min_value=1,
                key="sens_y_step"
            )
    
    # 构建参数网格
    param_x = ParameterRange(
        name=primary_params[0].name,
        display_name=primary_params[0].display_name,
        min_value=float(x_min),
        max_value=float(x_max),
        step=float(x_step),
        default=strategy_config.get(primary_params[0].name, primary_params[0].default)
    )
    
    param_y = ParameterRange(
        name=primary_params[1].name,
        display_name=primary_params[1].display_name,
        min_value=float(y_min),
        max_value=float(y_max),
        step=float(y_step),
        default=strategy_config.get(primary_params[1].name, primary_params[1].default)
    )
    
    grid = ParameterGrid(param_x=param_x, param_y=param_y)
    
    # 验证并显示组合数
    valid, error_msg = grid.validate()
    total_combinations = grid.get_total_combinations()
    
    col_info, col_btn = st.columns([3, 1])
    
    with col_info:
        if valid:
            if total_combinations > 50:
                st.warning(f"⚠️ 总组合数: {total_combinations}，预计耗时较长")
            else:
                st.info(f"📊 总组合数: {total_combinations}")
        else:
            st.error(f"❌ {error_msg}")
    
    with col_btn:
        analyze_btn = st.button(
            "🔬 开始分析", 
            disabled=not valid,
            use_container_width=True,
            key="sensitivity_analyze_btn"
        )
    
    # 执行分析
    if analyze_btn and valid:
        run_sensitivity_analysis(
            strategy_name, strategy_config, backtest_config, 
            selected_stocks, grid, param_x, param_y
        )
    
    # 显示已有结果
    if 'sensitivity_result' in st.session_state and st.session_state.sensitivity_result is not None:
        display_sensitivity_results(st.session_state.sensitivity_result, strategy_config)


def run_sensitivity_analysis(
    strategy_name: str, 
    strategy_config: Dict, 
    backtest_config, 
    selected_stocks: List[str],
    grid: ParameterGrid,
    param_x: ParameterRange,
    param_y: ParameterRange
):
    """执行参数敏感性分析"""
    strategy_info = STRATEGY_OPTIONS[strategy_name]
    data_feed = get_data_feed()
    
    # 构建基础参数（排除搜索参数）
    base_params = {k: v for k, v in strategy_config.items() 
                   if k not in [param_x.name, param_y.name]}
    
    # 创建搜索器
    searcher = GridSearcher(
        strategy_class=strategy_info["class"],
        backtest_config=backtest_config,
        stock_codes=selected_stocks[:5],  # 限制股票数量加速
        data_feed=data_feed
    )
    
    # 进度显示
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    def progress_callback(current, total, msg):
        progress_bar.progress(current / total)
        status_text.text(f"正在测试 ({current}/{total}): {msg}")
    
    # 执行搜索
    with st.spinner("正在进行参数敏感性分析..."):
        result = searcher.run(grid, base_params, progress_callback)
    
    progress_bar.empty()
    status_text.empty()
    
    # 保存结果
    st.session_state.sensitivity_result = result
    st.success(f"✅ 分析完成！耗时 {result.elapsed_time:.1f} 秒，成功 {result.success_count}/{result.success_count + result.failure_count}")


def display_sensitivity_results(result: GridSearchResult, strategy_config: Dict):
    """显示参数敏感性分析结果"""
    # 指标选择
    metric = st.selectbox(
        "显示指标",
        options=["total_return", "win_rate", "max_drawdown"],
        format_func=lambda x: {"total_return": "收益率", "win_rate": "胜率", "max_drawdown": "最大回撤"}[x],
        key="sensitivity_metric"
    )
    
    # 热力图
    current_x = strategy_config.get(result.grid.param_x.name)
    current_y = strategy_config.get(result.grid.param_y.name)
    
    fig = HeatmapRenderer.render(
        result, 
        metric=metric,
        highlight_current=True,
        current_x=current_x,
        current_y=current_y
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # 鲁棒性诊断
    diagnosis = RobustnessDiagnostics.diagnose(result)
    
    st.markdown("##### 🩺 鲁棒性诊断")
    
    # 评分显示
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("鲁棒性评分", f"{diagnosis.score}/100")
    with col2:
        st.metric("正收益占比", f"{diagnosis.positive_ratio:.1%}")
    with col3:
        st.metric("收益率波动", f"{diagnosis.return_std:.2%}")
    with col4:
        st.metric("邻近一致性", f"{diagnosis.neighbor_consistency:.1%}")
    
    # 诊断结论
    if diagnosis.score >= 70:
        st.success(diagnosis.message)
    elif diagnosis.score >= 40:
        st.warning(diagnosis.message)
    else:
        st.error(diagnosis.message)
    
    # 最优参数
    optimal = result.get_optimal_cell()
    if optimal:
        st.markdown("##### 🏆 最优参数组合")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(result.grid.param_x.display_name, optimal.param_x_value)
        with col2:
            st.metric(result.grid.param_y.display_name, optimal.param_y_value)
        with col3:
            st.metric("收益率", f"{optimal.total_return:.2%}")


def render_strategy_params(strategy_name: str) -> Dict:
    """根据策略类型渲染参数配置 UI"""
    strategy_config = {}
    
    if strategy_name == "RSI 超卖反弹策略":
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**RSI 参数**")
            strategy_config['rsi_period'] = st.number_input("RSI 周期", value=14, min_value=5, max_value=30)
            strategy_config['buy_threshold'] = st.number_input("买入阈值（RSI<）", value=30, min_value=10, max_value=40)
            strategy_config['sell_threshold'] = st.number_input("卖出阈值（RSI>）", value=70, min_value=60, max_value=90)
            
        with col2:
            st.markdown("**止损止盈参数**")
            strategy_config['stop_loss'] = st.number_input("止损比例", value=0.05, min_value=0.01, max_value=0.15, format="%.2f")
            strategy_config['take_profit'] = st.number_input("止盈比例", value=0.15, min_value=0.05, max_value=0.50, format="%.2f")
    
    elif strategy_name == "RSRS 阻力支撑策略":
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**RSRS 参数**")
            strategy_config['n_period'] = st.number_input("斜率计算窗口(N)", value=18, min_value=10, max_value=30)
            strategy_config['m_period'] = st.number_input("标准化窗口(M)", value=600, min_value=100, max_value=1000)
            
        with col2:
            st.markdown("**信号阈值**")
            strategy_config['buy_threshold'] = st.number_input("买入阈值", value=0.7, min_value=0.3, max_value=1.5, format="%.1f")
            strategy_config['sell_threshold'] = st.number_input("卖出阈值", value=-0.7, min_value=-1.5, max_value=-0.3, format="%.1f")
            strategy_config['hard_stop_loss'] = st.number_input("硬止损比例", value=-0.06, min_value=-0.15, max_value=-0.01, format="%.2f")
    
    return strategy_config


def main():
    st.set_page_config(page_title="策略回测", page_icon="🧪", layout="wide")
    st.title("🧪 策略回测")
    st.caption("验证策略有效性，检测过拟合风险")
    
    # ========== 顶部：策略选择卡片 ==========
    st.markdown("---")
    
    col_strategy, col_info = st.columns([1, 2])
    
    with col_strategy:
        st.markdown("#### 📋 选择策略")
        strategy_name = st.selectbox(
            "策略类型",
            options=list(STRATEGY_OPTIONS.keys()),
            index=0,
            label_visibility="collapsed",
            help="选择要回测的策略类型"
        )
    
    with col_info:
        strategy_info = STRATEGY_OPTIONS[strategy_name]
        st.markdown("#### 💡 策略说明")
        st.info(f"**{strategy_name}**\n\n{strategy_info['description']}\n\n📊 最少需要 **{strategy_info['min_data_days']}** 天数据")
    
    st.markdown("---")
    
    # ========== 中部：配置区（三列布局）==========
    col_date, col_stock, col_params = st.columns([1, 1, 1])
    
    with col_date:
        st.markdown("##### 📅 回测区间")
        start_date = st.date_input(
            "开始日期", 
            value=date.today() - timedelta(days=365),
            key="bt_start_date"
        )
        end_date = st.date_input(
            "结束日期", 
            value=date.today(),
            key="bt_end_date"
        )
        initial_cash = st.number_input(
            "每只初始资金 (¥)", 
            value=55000,
            min_value=10000,
            step=5000,
            key="bt_initial_cash"
        )
    
    with col_stock:
        st.markdown("##### 📈 股票选择")
        stock_pool = get_watchlist()
        
        use_all = st.checkbox(
            f"全选股票池 ({len(stock_pool)} 只)", 
            value=True,
            key="bt_use_all"
        )
        
        if use_all:
            selected_stocks = stock_pool
            st.caption(f"已选择全部 {len(stock_pool)} 只股票")
        else:
            selected_stocks = st.multiselect(
                "选择股票",
                options=stock_pool,
                default=stock_pool[:5] if len(stock_pool) >= 5 else stock_pool,
                key="bt_selected_stocks"
            )
            st.caption(f"已选择 {len(selected_stocks)} 只股票")
    
    with col_params:
        st.markdown("##### ⚙️ 策略参数")
        strategy_config = render_strategy_params_compact(strategy_name)
    
    # ========== 回测按钮 ==========
    st.markdown("---")
    
    col_btn, col_tip = st.columns([1, 3])
    
    with col_btn:
        start_btn = st.button(
            "🚀 开始回测", 
            type="primary", 
            use_container_width=True,
            disabled=not selected_stocks
        )
    
    with col_tip:
        if not selected_stocks:
            st.warning("⚠️ 请选择至少一只股票")
        else:
            st.caption(f"将对 {len(selected_stocks)} 只股票进行回测，预计耗时 {len(selected_stocks) * 2} 秒")
    
    # 构建回测配置
    backtest_config = BacktestConfig(
        initial_cash=float(initial_cash),
        commission_rate=0.0003,
        stamp_duty=0.001,
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d'),
        benchmark_code='000300',
        check_limit_up_down=False,
        slippage_perc=0.001,
    )

    # ========== 结果处理 ==========
    if 'batch_results' not in st.session_state:
        st.session_state.batch_results = None
    if 'last_strategy' not in st.session_state:
        st.session_state.last_strategy = None
    if 'last_config' not in st.session_state:
        st.session_state.last_config = None

    if start_btn:
        if not selected_stocks:
            st.error("请选择至少一只股票")
        else:
            with st.spinner("正在回测中..."):
                st.session_state.batch_results = run_batch_backtest(
                    backtest_config, strategy_name, strategy_config, selected_stocks
                )
                st.session_state.last_strategy = strategy_name
                st.session_state.last_config = strategy_config

    # ========== 结果展示 ==========
    df_results = st.session_state.batch_results
    
    if df_results is not None and not df_results.empty:
        st.markdown("---")
        render_backtest_results(df_results, initial_cash, strategy_config, backtest_config, selected_stocks)
        
    elif df_results is not None and df_results.empty:
        st.warning("回测完成，但没有产生有效结果（可能数据不足）。")


def render_strategy_params_compact(strategy_name: str) -> Dict:
    """紧凑版策略参数配置"""
    strategy_config = {}
    
    if strategy_name == "RSI 超卖反弹策略":
        strategy_config['rsi_period'] = st.number_input(
            "RSI 周期", value=14, min_value=5, max_value=30, key="rsi_period"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            strategy_config['buy_threshold'] = st.number_input(
                "买入 (RSI<)", value=30, min_value=10, max_value=40, key="rsi_buy"
            )
        with col2:
            strategy_config['sell_threshold'] = st.number_input(
                "卖出 (RSI>)", value=70, min_value=60, max_value=90, key="rsi_sell"
            )
        
        col1, col2 = st.columns(2)
        with col1:
            strategy_config['stop_loss'] = st.number_input(
                "止损 %", value=5.0, min_value=1.0, max_value=15.0, key="rsi_sl"
            ) / 100
        with col2:
            strategy_config['take_profit'] = st.number_input(
                "止盈 %", value=15.0, min_value=5.0, max_value=50.0, key="rsi_tp"
            ) / 100
    
    elif strategy_name == "RSRS 阻力支撑策略":
        col1, col2 = st.columns(2)
        with col1:
            strategy_config['n_period'] = st.number_input(
                "斜率窗口(N)", value=18, min_value=10, max_value=30, key="rsrs_n"
            )
        with col2:
            strategy_config['m_period'] = st.number_input(
                "标准化(M)", value=600, min_value=100, max_value=1000, key="rsrs_m"
            )
        
        col1, col2 = st.columns(2)
        with col1:
            strategy_config['buy_threshold'] = st.number_input(
                "买入阈值", value=0.7, min_value=0.3, max_value=1.5, format="%.1f", key="rsrs_buy"
            )
        with col2:
            strategy_config['sell_threshold'] = st.number_input(
                "卖出阈值", value=-0.7, min_value=-1.5, max_value=-0.3, format="%.1f", key="rsrs_sell"
            )
        
        strategy_config['hard_stop_loss'] = st.number_input(
            "硬止损 %", value=-6.0, min_value=-15.0, max_value=-1.0, key="rsrs_sl"
        ) / 100
    
    return strategy_config


def render_backtest_results(df_results: pd.DataFrame, initial_cash: float, strategy_config: Dict, backtest_config, selected_stocks: List[str]):
    """渲染回测结果（优化布局）"""
    st.subheader(f"📊 策略体检报告 - {st.session_state.last_strategy}")
    
    # ========== 核心指标卡片 ==========
    avg_return = df_results['总收益率'].mean()
    win_rate_mean = df_results['胜率'].mean()
    positive_count = len(df_results[df_results['总收益率'] > 0])
    positive_ratio = positive_count / len(df_results)
    avg_drawdown = df_results['最大回撤'].mean()
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        delta_color = "normal" if avg_return >= 0 else "inverse"
        st.metric("平均收益率", f"{avg_return:.2%}", delta_color=delta_color)
    
    with col2:
        st.metric("正收益占比", f"{positive_ratio:.0%}", f"{positive_count}/{len(df_results)}")
    
    with col3:
        st.metric("平均胜率", f"{win_rate_mean:.0%}")
    
    with col4:
        st.metric("平均回撤", f"{avg_drawdown:.1%}")
    
    with col5:
        st.metric("测试样本", f"{len(df_results)} 只")
    
    # ========== 两列布局：图表 + 排行榜 ==========
    col_chart, col_table = st.columns([1, 1])
    
    with col_chart:
        st.markdown("##### 📈 收益率分布")
        fig = px.histogram(
            df_results, x="总收益率", nbins=20, 
            color_discrete_sequence=['#4CAF50']
        )
        fig.add_vline(x=0, line_dash="dash", line_color="red", annotation_text="盈亏线")
        fig.update_layout(
            margin=dict(t=20, b=20, l=20, r=20),
            height=300,
            xaxis_title="收益率",
            yaxis_title="股票数量"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col_table:
        st.markdown("##### 🏆 收益排行榜")
        display_df = df_results.sort_values(by='总收益率', ascending=False).head(10)
        st.dataframe(
            display_df[['代码', '总收益率', '胜率', '最大回撤', '交易次数']],
            column_config={
                "代码": st.column_config.TextColumn("代码", width="small"),
                "总收益率": st.column_config.NumberColumn("收益率", format="%.1f%%"),
                "胜率": st.column_config.NumberColumn("胜率", format="%.0f%%"),
                "最大回撤": st.column_config.NumberColumn("回撤", format="%.1f%%"),
                "交易次数": st.column_config.NumberColumn("交易", width="small"),
            },
            use_container_width=True,
            hide_index=True,
            height=300
        )
    
    # ========== 手续费分析（折叠）==========
    with st.expander("💸 手续费磨损分析", expanded=False):
        render_commission_analysis(df_results, initial_cash)
    
    # ========== 参数敏感性分析（折叠）==========
    with st.expander("🔬 参数敏感性分析（检测过拟合）", expanded=False):
        render_sensitivity_analysis(
            st.session_state.last_strategy, 
            st.session_state.last_config or strategy_config, 
            backtest_config, 
            selected_stocks
        )
    
    # ========== 完整数据（折叠）==========
    with st.expander("📋 完整回测数据", expanded=False):
        st.dataframe(
            df_results.sort_values(by='总收益率', ascending=False),
            column_config={
                "总收益率": st.column_config.NumberColumn(format="%.2f%%"),
                "胜率": st.column_config.NumberColumn(format="%.1f%%"),
                "最大回撤": st.column_config.NumberColumn(format="%.1f%%"),
                "最终资产": st.column_config.NumberColumn(format="¥%.0f"),
                "盈亏比": st.column_config.NumberColumn(format="%.2f"),
            },
            use_container_width=True,
            hide_index=True
        )


if __name__ == "__main__":
    main()
