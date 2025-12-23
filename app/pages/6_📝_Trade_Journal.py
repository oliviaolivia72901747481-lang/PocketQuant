"""
MiniQuant-Lite 交易记录页面

提供交易记录管理功能：
- 交易历史表格展示（盈利绿色、亏损红色高亮）
- 添加交易记录表单
- 统计概览（总交易次数、胜率、净利润等）
- 导出 CSV 功能

Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6
"""

import streamlit as st
import sys
import os
from datetime import date, datetime
from typing import List, Optional
import pandas as pd

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.trade_journal import TradeJournal, TradeRecord, TradeAction, TradePerformance
from core.logging_config import get_logger

logger = get_logger(__name__)


def get_trade_journal() -> TradeJournal:
    """获取 TradeJournal 实例"""
    return TradeJournal()


def render_statistics_overview(journal: TradeJournal):
    """
    渲染统计概览区域
    
    Args:
        journal: TradeJournal 实例
        
    Requirements: 6.4
    """
    st.subheader("📊 统计概览")
    
    performance = journal.calculate_performance()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("总交易次数", f"{performance.total_trades} 笔")
    
    with col2:
        win_rate_display = f"{performance.win_rate:.1%}" if performance.closed_trades > 0 else "N/A"
        st.metric("胜率", win_rate_display)
    
    with col3:
        pnl_color = "normal" if performance.net_profit >= 0 else "inverse"
        st.metric(
            "净利润",
            f"¥{performance.net_profit:,.0f}",
            delta=f"毛利 ¥{performance.total_profit:,.0f}",
            delta_color=pnl_color
        )
    
    with col4:
        st.metric("总手续费", f"¥{performance.total_commission:,.0f}")
    
    # 第二行统计
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("买入次数", f"{performance.buy_trades} 笔")
    
    with col2:
        st.metric("卖出次数", f"{performance.sell_trades} 笔")
    
    with col3:
        st.metric("已平仓", f"{performance.closed_trades} 笔")
    
    with col4:
        avg_days = f"{performance.average_holding_days:.1f} 天" if performance.closed_trades > 0 else "N/A"
        st.metric("平均持仓", avg_days)


def render_trade_table(journal: TradeJournal):
    """
    渲染交易记录表格
    
    Args:
        journal: TradeJournal 实例
        
    Requirements: 6.1, 6.3
    """
    st.subheader("📋 交易历史")
    
    trades = journal.get_trades()
    
    if not trades:
        st.info("📭 暂无交易记录，请添加您的第一笔交易")
        return
    
    # 构建表格数据
    data = []
    for trade in trades:
        row = {
            'id': trade.id,
            'trade_date': trade.trade_date.strftime('%Y-%m-%d'),
            'code': trade.code,
            'name': trade.name,
            'action': trade.action.value,
            'price': trade.price,
            'quantity': trade.quantity,
            'total_amount': trade.total_amount,
            'commission': trade.commission,
            'strategy': trade.strategy or '-',
            'reason': trade.reason or '-',
            'slippage': trade.slippage,
            'note': trade.note or '-'
        }
        data.append(row)
    
    df = pd.DataFrame(data)
    
    # 显示用的列
    display_df = df[['trade_date', 'code', 'name', 'action', 'price', 'quantity', 
                     'total_amount', 'commission', 'strategy', 'reason', 'note']].copy()
    
    display_df.columns = ['日期', '代码', '名称', '操作', '价格', '数量', 
                          '金额', '手续费', '策略', '原因', '备注']
    
    # 直接显示表格，不应用背景色样式（保持统一深色背景）
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            '价格': st.column_config.NumberColumn('价格', format='¥%.2f'),
            '金额': st.column_config.NumberColumn('金额', format='¥%.0f'),
            '手续费': st.column_config.NumberColumn('手续费', format='¥%.2f'),
        }
    )
    
    # 删除交易记录
    st.divider()
    st.markdown("**删除交易记录**")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        delete_options = [f"{t.id} - {t.trade_date} {t.code} {t.action.value}" for t in trades]
        delete_selection = st.selectbox(
            "选择要删除的记录",
            options=delete_options,
            key="delete_trade_select"
        )
    with col2:
        if st.button("🗑️ 删除", type="secondary", key="delete_trade_btn"):
            if delete_selection:
                trade_id = delete_selection.split(" - ")[0]
                success, msg = journal.delete_trade(trade_id)
                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)


def calculate_trade_pnl_status(trades: List[TradeRecord]) -> dict:
    """
    计算每笔交易的盈亏状态
    
    通过匹配买卖对来确定卖出交易是盈利还是亏损
    
    Args:
        trades: 交易记录列表
        
    Returns:
        {trade_id: 'profit'|'loss'|'neutral'}
    """
    pnl_status = {}
    
    # 按股票代码分组
    trades_by_code = {}
    for trade in trades:
        if trade.code not in trades_by_code:
            trades_by_code[trade.code] = []
        trades_by_code[trade.code].append(trade)
    
    for code, code_trades in trades_by_code.items():
        # 按日期排序
        code_trades.sort(key=lambda t: t.trade_date)
        
        buy_queue = []
        
        for trade in code_trades:
            if trade.action == TradeAction.BUY:
                buy_queue.append(trade)
                pnl_status[trade.id] = 'neutral'  # 买入记录标记为中性
            elif trade.action == TradeAction.SELL:
                if buy_queue:
                    # 匹配最早的买入记录
                    buy_trade = buy_queue[0]
                    profit = (trade.price - buy_trade.price) * min(trade.quantity, buy_trade.quantity)
                    
                    if profit > 0:
                        pnl_status[trade.id] = 'profit'
                    elif profit < 0:
                        pnl_status[trade.id] = 'loss'
                    else:
                        pnl_status[trade.id] = 'neutral'
                    
                    # 更新买入队列
                    if trade.quantity >= buy_trade.quantity:
                        buy_queue.pop(0)
                else:
                    pnl_status[trade.id] = 'neutral'
    
    return pnl_status


def render_add_trade_form(journal: TradeJournal):
    """
    渲染添加交易表单
    
    Args:
        journal: TradeJournal 实例
        
    Requirements: 6.2, 6.6
    """
    st.subheader("➕ 添加交易记录")
    
    # 检查是否有预填充数据（从信号页面跳转）
    prefill_data = st.session_state.get('prefill_trade', None)
    
    # 显示预填充提示 (Requirements: 6.6)
    if prefill_data:
        col1, col2 = st.columns([4, 1])
        with col1:
            st.success(f"""
            📝 **已从信号页面预填充数据**
            
            股票: **{prefill_data.get('code', '')} {prefill_data.get('name', '')}** | 
            信号类型: **{prefill_data.get('action', '')}** | 
            建议价格: **¥{prefill_data.get('price', 0):.2f}**
            
            请核对并补充实际成交信息后提交。
            """)
        with col2:
            if st.button("🗑️ 清除预填充", key="clear_prefill"):
                del st.session_state['prefill_trade']
                st.rerun()
    
    with st.form("add_trade_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            code = st.text_input(
                "股票代码 *",
                value=prefill_data.get('code', '') if prefill_data else '',
                placeholder="例如: 600036",
                max_chars=6,
                help="6位股票代码"
            )
            
            name = st.text_input(
                "股票名称 *",
                value=prefill_data.get('name', '') if prefill_data else '',
                placeholder="例如: 招商银行",
                help="股票名称"
            )
            
            action = st.selectbox(
                "交易类型 *",
                options=["买入", "卖出"],
                index=0 if not prefill_data else (0 if prefill_data.get('action') == '买入' else 1),
                help="买入或卖出"
            )
            
            price = st.number_input(
                "成交价格 *",
                min_value=0.01,
                value=prefill_data.get('price', 10.0) if prefill_data else 10.0,
                step=0.01,
                format="%.2f",
                help="实际成交价格"
            )
            
            quantity = st.number_input(
                "成交数量 *",
                min_value=1,
                value=prefill_data.get('quantity', 100) if prefill_data else 100,
                step=100,
                help="成交股数"
            )
        
        with col2:
            trade_date = st.date_input(
                "成交日期 *",
                value=prefill_data.get('trade_date', date.today()) if prefill_data else date.today(),
                max_value=date.today(),
                help="实际成交日期"
            )
            
            # 策略选项
            strategy_options = ["", "RSRS", "RSI", "Bollinger", "MACD", "其他"]
            
            # 确定预填充的策略索引
            prefill_strategy = prefill_data.get('strategy', '') if prefill_data else ''
            strategy_index = 0
            if prefill_strategy:
                # 尝试匹配策略名称
                for i, opt in enumerate(strategy_options):
                    if opt.lower() in prefill_strategy.lower() or prefill_strategy.lower() in opt.lower():
                        strategy_index = i
                        break
                # 如果没有匹配到，设置为"其他"
                if strategy_index == 0 and prefill_strategy:
                    strategy_index = len(strategy_options) - 1  # "其他"
            
            strategy = st.selectbox(
                "使用策略",
                options=strategy_options,
                index=strategy_index,
                help="买入时使用的策略（可选）"
            )
            
            commission = st.number_input(
                "手续费",
                min_value=0.0,
                value=prefill_data.get('commission', 5.0) if prefill_data else 5.0,
                step=0.1,
                format="%.2f",
                help="实际手续费（可选）"
            )
            
            reason = st.text_input(
                "交易原因",
                value=prefill_data.get('reason', '') if prefill_data else '',
                placeholder="例如: RSI超卖反弹",
                help="交易原因（可选）"
            )
            
            note = st.text_input(
                "备注",
                placeholder="例如: 首次建仓",
                help="备注信息（可选）"
            )
        
        # 信号关联字段（可选）
        with st.expander("信号关联（可选）", expanded=bool(prefill_data)):
            signal_col1, signal_col2 = st.columns(2)
            
            with signal_col1:
                signal_id = st.text_input(
                    "信号ID",
                    value=prefill_data.get('signal_id', '') if prefill_data else '',
                    placeholder="例如: sig_001",
                    help="关联的信号ID"
                )
                
                signal_date = st.date_input(
                    "信号日期",
                    value=prefill_data.get('signal_date', None) if prefill_data else None,
                    max_value=date.today(),
                    help="信号生成日期"
                )
            
            with signal_col2:
                signal_price = st.number_input(
                    "信号价格",
                    min_value=0.0,
                    value=prefill_data.get('signal_price', 0.0) if prefill_data else 0.0,
                    step=0.01,
                    format="%.2f",
                    help="信号建议价格"
                )
        
        submitted = st.form_submit_button("✅ 添加交易记录", type="primary")
        
        if submitted:
            # 验证必填字段
            if not code or len(code) != 6 or not code.isdigit():
                st.error("请输入有效的6位股票代码")
                return
            
            if not name:
                st.error("请输入股票名称")
                return
            
            # 创建交易记录
            trade_action = TradeAction.BUY if action == "买入" else TradeAction.SELL
            
            record = TradeRecord(
                code=code,
                name=name,
                action=trade_action,
                price=price,
                quantity=quantity,
                trade_date=trade_date,
                signal_id=signal_id if signal_id else None,
                signal_date=signal_date if signal_id else None,
                signal_price=signal_price if signal_price > 0 else None,
                strategy=strategy if strategy else "",
                reason=reason if reason else "",
                commission=commission,
                note=note if note else ""
            )
            
            success, msg = journal.add_trade(record)
            
            if success:
                st.success(f"✅ {msg}")
                # 清除预填充数据
                if 'prefill_trade' in st.session_state:
                    del st.session_state['prefill_trade']
                st.rerun()
            else:
                st.error(f"❌ {msg}")


def render_export_section(journal: TradeJournal):
    """
    渲染导出区域
    
    Args:
        journal: TradeJournal 实例
        
    Requirements: 6.5
    """
    st.subheader("📥 导出交易记录")
    
    trades = journal.get_trades()
    
    if not trades:
        st.info("暂无交易记录可导出")
        return
    
    csv_data = journal.export_csv()
    
    st.download_button(
        label="📥 导出 CSV",
        data=csv_data,
        file_name=f"trade_journal_{date.today().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        key="export_trades"
    )


def render_backtest_comparison(journal: TradeJournal):
    """
    渲染回测对比区域
    
    Args:
        journal: TradeJournal 实例
        
    Requirements: 7.3, 7.5
    """
    st.subheader("📊 回测对比")
    st.caption("对比实盘交易与回测结果，验证策略有效性")
    
    trades = journal.get_trades()
    
    if not trades:
        st.info("📭 暂无交易记录，无法进行回测对比")
        return
    
    # 获取可用的策略列表（从交易记录中提取）
    strategies_in_trades = list(set(t.strategy for t in trades if t.strategy))
    
    if not strategies_in_trades:
        st.warning("⚠️ 交易记录中没有关联策略信息，请在添加交易时选择策略")
        return
    
    # 策略和日期范围选择
    col1, col2, col3 = st.columns([2, 2, 2])
    
    with col1:
        # 添加"全部策略"选项
        strategy_options = ["全部策略"] + strategies_in_trades
        selected_strategy = st.selectbox(
            "选择策略",
            options=strategy_options,
            index=0,
            key="backtest_compare_strategy",
            help="选择要对比的策略"
        )
    
    with col2:
        # 获取交易记录的日期范围
        trade_dates = [t.trade_date for t in trades]
        min_date = min(trade_dates)
        max_date = max(trade_dates)
        
        start_date = st.date_input(
            "开始日期",
            value=min_date,
            min_value=min_date,
            max_value=max_date,
            key="backtest_compare_start",
            help="对比开始日期"
        )
    
    with col3:
        end_date = st.date_input(
            "结束日期",
            value=max_date,
            min_value=min_date,
            max_value=max_date,
            key="backtest_compare_end",
            help="对比结束日期"
        )
    
    # 执行对比按钮
    if st.button("🔍 执行对比", type="primary", key="run_backtest_compare"):
        with st.spinner("正在计算对比数据..."):
            # 确定要对比的策略
            compare_strategy = "" if selected_strategy == "全部策略" else selected_strategy
            
            # 调用对比方法
            comparison = journal.compare_with_backtest(
                strategy=compare_strategy,
                start_date=start_date,
                end_date=end_date
            )
            
            # 保存结果到 session_state
            st.session_state['backtest_comparison'] = comparison
    
    # 显示对比结果
    if 'backtest_comparison' in st.session_state and st.session_state['backtest_comparison']:
        comparison = st.session_state['backtest_comparison']
        
        st.divider()
        st.markdown("##### 📈 对比结果")
        
        # 显示对比指标
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            actual_return = comparison['actual_return']
            st.metric(
                "实盘收益率",
                f"{actual_return:.2%}",
                delta=f"{comparison['actual_trades']} 笔交易"
            )
        
        with col2:
            backtest_return = comparison['backtest_return']
            st.metric(
                "回测收益率",
                f"{backtest_return:.2%}",
                delta=f"{comparison['backtest_trades']} 笔交易"
            )
        
        with col3:
            performance_gap = comparison['performance_gap']
            gap_color = "normal" if performance_gap >= 0 else "inverse"
            st.metric(
                "性能差距",
                f"{performance_gap:.2%}",
                delta="实盘优于回测" if performance_gap >= 0 else "实盘落后回测",
                delta_color=gap_color
            )
        
        with col4:
            st.metric(
                "对比期间",
                comparison['comparison_period'],
                delta=f"策略: {comparison['strategy'] or '全部'}"
            )
        
        # 可视化对比图表
        render_comparison_chart(comparison)
        
        # 性能差距警告 (Requirements: 7.5)
        render_performance_gap_warning(comparison)


def render_comparison_chart(comparison: dict):
    """
    渲染对比图表
    
    Args:
        comparison: 对比结果字典
    """
    import plotly.graph_objects as go
    
    actual_return = comparison['actual_return']
    backtest_return = comparison['backtest_return']
    
    # 创建柱状图
    fig = go.Figure()
    
    # 实盘收益柱
    fig.add_trace(go.Bar(
        name='实盘收益',
        x=['收益率对比'],
        y=[actual_return * 100],
        marker_color='#4CAF50' if actual_return >= 0 else '#f44336',
        text=[f'{actual_return:.2%}'],
        textposition='outside'
    ))
    
    # 回测收益柱
    fig.add_trace(go.Bar(
        name='回测收益',
        x=['收益率对比'],
        y=[backtest_return * 100],
        marker_color='#2196F3' if backtest_return >= 0 else '#ff9800',
        text=[f'{backtest_return:.2%}'],
        textposition='outside'
    ))
    
    fig.update_layout(
        title='实盘 vs 回测收益率对比',
        yaxis_title='收益率 (%)',
        barmode='group',
        height=300,
        margin=dict(t=50, b=20, l=20, r=20),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    # 添加零线
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    
    st.plotly_chart(fig, use_container_width=True)


def render_performance_gap_warning(comparison: dict):
    """
    渲染性能差距警告
    
    如果 performance_gap < -5%，显示警告并提供可能原因分析
    
    Args:
        comparison: 对比结果字典
        
    Requirements: 7.5
    """
    performance_gap = comparison['performance_gap']
    
    # 如果性能差距显著为负（< -5%），显示警告
    if performance_gap < -0.05:
        st.error(f"""
        ⚠️ **性能差距警告**
        
        实盘收益率 ({comparison['actual_return']:.2%}) 显著低于回测收益率 ({comparison['backtest_return']:.2%})，
        差距达到 **{abs(performance_gap):.2%}**。
        """)
        
        st.markdown("##### 🔍 可能原因分析")
        
        with st.expander("查看详细分析", expanded=True):
            st.markdown("""
            **1. 滑点影响** 📉
            - 实际成交价格与信号价格存在偏差
            - 建议：检查交易记录中的滑点数据，优化下单时机
            
            **2. 执行延迟** ⏰
            - 信号产生后未能及时执行
            - 建议：缩短从信号到执行的时间间隔
            
            **3. 手续费差异** 💰
            - 实际手续费可能高于回测假设
            - 建议：核实实际手续费率，调整回测参数
            
            **4. 市场冲击** 📊
            - 大额交易可能影响市场价格
            - 建议：分批建仓，减少单次交易量
            
            **5. 选择性执行** 🎯
            - 可能只执行了部分信号
            - 建议：检查信号执行率，保持执行一致性
            
            **6. 数据差异** 📋
            - 回测使用的历史数据可能与实际有差异
            - 建议：确保数据源一致性
            """)
        
        # 提供改进建议
        st.info("""
        💡 **改进建议**：
        1. 记录每笔交易的滑点和执行延迟
        2. 定期检查信号执行率
        3. 优化下单策略，减少市场冲击
        """)
    
    elif performance_gap < 0:
        # 轻微落后，显示提示
        st.warning(f"""
        📊 **性能提示**
        
        实盘收益率略低于回测收益率，差距为 **{abs(performance_gap):.2%}**。
        这在正常范围内，但建议关注滑点和执行延迟。
        """)
    
    else:
        # 实盘优于回测
        st.success(f"""
        🎉 **表现优秀**
        
        实盘收益率 ({comparison['actual_return']:.2%}) 达到或超过回测收益率 ({comparison['backtest_return']:.2%})！
        继续保持良好的执行纪律。
        """)


def main():
    """交易记录页面主函数"""
    st.set_page_config(
        page_title="交易记录 - MiniQuant-Lite",
        page_icon="📝",
        layout="wide"
    )
    
    st.title("📝 交易记录")
    st.markdown("记录您的实盘交易，追踪交易表现，与回测结果对比验证")
    
    st.divider()
    
    # 初始化
    journal = get_trade_journal()
    
    # ========== 统计概览 ==========
    render_statistics_overview(journal)
    
    st.divider()
    
    # ========== 交易历史表格 ==========
    render_trade_table(journal)
    
    st.divider()
    
    # ========== 添加交易表单 ==========
    render_add_trade_form(journal)
    
    st.divider()
    
    # ========== 导出功能 ==========
    render_export_section(journal)
    
    st.divider()
    
    # ========== 回测对比 ==========
    render_backtest_comparison(journal)
    
    # ========== 使用说明 ==========
    st.divider()
    st.subheader("📖 使用说明")
    
    with st.expander("如何使用交易记录？", expanded=False):
        st.markdown("""
        **添加交易记录：**
        1. 在"添加交易记录"区域填写交易信息
        2. 必填字段：股票代码、名称、交易类型、价格、数量、日期
        3. 可选字段：策略、手续费、原因、备注、信号关联
        4. 点击"添加交易记录"按钮
        
        **查看统计：**
        - 统计概览显示总交易次数、胜率、净利润等指标
        - 胜率 = 盈利交易数 / 已平仓交易数
        - 净利润 = 总盈亏 - 总手续费
        
        **表格说明：**
        - 表格按交易日期降序排列（最新的在前）
        - 通过"操作"列区分买入/卖出交易
        - 盈亏情况可在统计概览中查看
        
        **导出数据：**
        - 点击"导出 CSV"按钮下载交易记录
        """)
    
    with st.expander("从信号页面记录交易", expanded=False):
        st.markdown("""
        **快速记录信号执行：**
        
        1. 在"每日信号"页面查看交易信号
        2. 执行交易后，点击信号卡片中的"记录交易"按钮
        3. 系统会自动跳转到本页面，并预填充信号相关字段
        4. 补充实际成交价格、数量等信息
        5. 点击"添加交易记录"完成记录
        
        **信号关联的好处：**
        - 追踪信号执行率
        - 计算滑点（实际价格与信号价格的偏差）
        - 分析执行延迟（信号日期到成交日期的天数）
        """)
    
    with st.expander("回测对比功能说明", expanded=False):
        st.markdown("""
        **回测对比功能：**
        
        1. 在"回测对比"区域选择策略和日期范围
        2. 点击"执行对比"按钮
        3. 系统会计算实盘收益率和回测收益率
        4. 显示性能差距（实盘 - 回测）
        
        **性能差距解读：**
        - 🟢 **正值**：实盘表现优于回测，执行良好
        - 🟡 **小幅负值（0~-5%）**：正常范围，注意滑点和延迟
        - 🔴 **大幅负值（<-5%）**：需要关注，系统会提供原因分析
        
        **提高实盘表现的建议：**
        - 及时执行信号，减少延迟
        - 优化下单时机，减少滑点
        - 保持执行纪律，避免选择性执行
        """)


if __name__ == "__main__":
    main()
