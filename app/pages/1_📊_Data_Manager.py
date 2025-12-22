"""
MiniQuant-Lite 数据管理页面

提供数据管理功能：
- 数据状态概览
- 股票数据下载
- 一键清空缓存

Requirements: 7.2, 7.3
"""

import streamlit as st
import sys
import os
from datetime import date, timedelta
from typing import List, Dict
import pandas as pd

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config.settings import get_settings
from config.stock_pool import get_watchlist, StockPool, validate_stock_codes
from core.data_feed import DataFeed


def get_data_feed() -> DataFeed:
    """获取 DataFeed 实例"""
    settings = get_settings()
    return DataFeed(
        raw_path=settings.path.get_raw_path(),
        processed_path=settings.path.get_processed_path()
    )


def render_data_status(data_feed: DataFeed, stock_pool: List[str]):
    """
    渲染数据状态概览
    
    Args:
        data_feed: DataFeed 实例
        stock_pool: 股票池列表
    """
    st.subheader("📊 数据状态概览")
    
    if not stock_pool:
        st.warning("股票池为空，请先配置股票池")
        return
    
    # 获取数据状态
    status = data_feed.get_data_status(stock_pool)
    
    # 统计信息
    total = len(stock_pool)
    downloaded = sum(1 for s in status.values() if s['exists'])
    missing = total - downloaded
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("股票池总数", f"{total} 只")
    with col2:
        st.metric("已下载", f"{downloaded} 只", delta=None if downloaded == total else f"-{missing}")
    with col3:
        st.metric("待下载", f"{missing} 只")
    
    # 数据状态表格
    if status:
        st.markdown("#### 详细状态")
        
        # 转换为 DataFrame
        data = []
        for code, info in status.items():
            data.append({
                '股票代码': code,
                '状态': '✅ 已下载' if info['exists'] else '❌ 未下载',
                '最后更新': info['last_date'] if info['last_date'] else '-',
                '记录数': info['record_count'] if info['record_count'] else 0
            })
        
        df = pd.DataFrame(data)
        
        # 使用 dataframe 显示，支持排序
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                '股票代码': st.column_config.TextColumn('股票代码', width='small'),
                '状态': st.column_config.TextColumn('状态', width='small'),
                '最后更新': st.column_config.TextColumn('最后更新', width='medium'),
                '记录数': st.column_config.NumberColumn('记录数', width='small')
            }
        )


def render_download_section(data_feed: DataFeed, stock_pool: List[str]):
    """
    渲染数据下载区域
    
    Args:
        data_feed: DataFeed 实例
        stock_pool: 股票池列表
    """
    st.subheader("📥 数据下载")
    
    settings = get_settings()
    
    # 下载参数配置
    col1, col2 = st.columns(2)
    
    with col1:
        # 日期范围
        default_end = date.today()
        default_start = default_end - timedelta(days=365)
        
        start_date = st.date_input(
            "开始日期",
            value=default_start,
            help="数据下载的开始日期"
        )
    
    with col2:
        end_date = st.date_input(
            "结束日期",
            value=default_end,
            help="数据下载的结束日期"
        )
    
    # 下载选项
    st.markdown("#### 下载选项")
    
    col1, col2 = st.columns(2)
    
    with col1:
        download_all = st.checkbox(
            "下载全部股票池",
            value=True,
            help="勾选后下载股票池中所有股票的数据"
        )
    
    with col2:
        overwrite = st.checkbox(
            "覆盖已有数据",
            value=True,
            help="勾选后会覆盖已下载的数据（推荐，确保复权数据准确）"
        )
    
    # 单只股票下载
    if not download_all:
        selected_codes = st.multiselect(
            "选择要下载的股票",
            options=stock_pool,
            default=[],
            help="选择需要下载数据的股票"
        )
    else:
        selected_codes = stock_pool
    
    # 下载按钮
    if st.button("🚀 开始下载", type="primary", disabled=not selected_codes):
        if not selected_codes:
            st.warning("请选择要下载的股票")
            return
        
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        success_count = 0
        fail_count = 0
        total = len(selected_codes)
        
        for i, code in enumerate(selected_codes):
            status_text.text(f"正在下载: {code} ({i+1}/{total})")
            
            try:
                # 下载数据
                df = data_feed.download_stock_data(
                    code=code,
                    start_date=start_str,
                    end_date=end_str,
                    adjust='qfq'
                )
                
                if df is not None and not df.empty:
                    # 清洗并保存数据
                    cleaned = data_feed.clean_data(df)
                    if not cleaned.empty:
                        file_path = os.path.join(
                            settings.path.get_processed_path(),
                            f"{code}.csv"
                        )
                        cleaned.to_csv(file_path, index=False)
                        success_count += 1
                    else:
                        fail_count += 1
                else:
                    fail_count += 1
                    
            except Exception as e:
                fail_count += 1
                st.error(f"下载 {code} 失败: {str(e)}")
            
            progress_bar.progress((i + 1) / total)
        
        status_text.empty()
        progress_bar.empty()
        
        if success_count > 0:
            st.success(f"✅ 下载完成！成功: {success_count} 只，失败: {fail_count} 只")
        else:
            st.error(f"❌ 下载失败！请检查网络连接或 AkShare 版本")
        
        # 刷新页面
        st.rerun()


def render_cache_management(data_feed: DataFeed):
    """
    渲染缓存管理区域
    
    Args:
        data_feed: DataFeed 实例
    """
    st.subheader("🗑️ 缓存管理")
    
    # ========== 内存缓存状态 ==========
    st.markdown("#### 💾 内存缓存")
    
    cache_stats = data_feed.get_cache_stats()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("股票数据缓存", f"{cache_stats['stock_data_count']} 只")
    with col2:
        snapshot_status = "✅ 已缓存" if cache_stats['has_market_snapshot'] else "❌ 未缓存"
        st.metric("市场快照", snapshot_status)
    with col3:
        names_status = "✅ 已缓存" if cache_stats['has_stock_names'] else "❌ 未缓存"
        st.metric("股票名称", names_status)
    
    st.caption("💡 内存缓存可加速重复数据访问，TTL: 股票数据 5分钟 / 市场快照 1分钟 / 股票名称 1小时")
    
    # 清空内存缓存按钮
    if st.button("🧹 清空内存缓存", help="仅清空内存缓存，不影响已下载的文件"):
        data_feed.clear_memory_cache()
        st.success("✅ 内存缓存已清空")
        st.rerun()
    
    st.divider()
    
    # ========== 文件缓存状态 ==========
    st.markdown("#### 📁 文件缓存")
    
    st.warning("""
    **注意**：清空文件缓存将删除所有已下载的股票数据，需要重新下载。
    
    适用场景：
    - 数据出现异常或损坏
    - 需要完全重新下载数据
    - 磁盘空间不足
    """)
    
    # 显示缓存大小
    settings = get_settings()
    raw_path = settings.path.get_raw_path()
    processed_path = settings.path.get_processed_path()
    
    def get_dir_size(path: str) -> int:
        """获取目录大小（字节）"""
        total = 0
        if os.path.exists(path):
            for file in os.listdir(path):
                file_path = os.path.join(path, file)
                if os.path.isfile(file_path):
                    total += os.path.getsize(file_path)
        return total
    
    raw_size = get_dir_size(raw_path)
    processed_size = get_dir_size(processed_path)
    total_size = raw_size + processed_size
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("原始数据", f"{raw_size / 1024 / 1024:.2f} MB")
    with col2:
        st.metric("处理后数据", f"{processed_size / 1024 / 1024:.2f} MB")
    with col3:
        st.metric("总计", f"{total_size / 1024 / 1024:.2f} MB")
    
    # 一键清空缓存按钮
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("🗑️ 一键清空缓存", type="secondary"):
            st.session_state['confirm_clear'] = True
    
    # 确认对话框
    if st.session_state.get('confirm_clear', False):
        st.error("⚠️ 确定要清空所有缓存数据吗？此操作不可恢复！")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ 确认清空", type="primary"):
                success = data_feed.clear_cache()
                if success:
                    st.success("✅ 缓存已清空！")
                else:
                    st.error("❌ 清空缓存失败，请检查文件权限")
                st.session_state['confirm_clear'] = False
                st.rerun()
        with col2:
            if st.button("❌ 取消"):
                st.session_state['confirm_clear'] = False
                st.rerun()


def render_stock_pool_management():
    """渲染股票池管理区域"""
    st.subheader("📋 股票池管理")
    
    # 当前股票池
    current_pool = get_watchlist()
    
    st.markdown(f"**当前股票池**: {len(current_pool)} 只股票")
    
    # 显示当前股票池
    with st.expander("查看当前股票池", expanded=False):
        if current_pool:
            # 每行显示 6 个股票代码
            cols = st.columns(6)
            for i, code in enumerate(current_pool):
                cols[i % 6].code(code)
        else:
            st.info("股票池为空")
    
    # 添加股票
    st.markdown("#### 添加股票")
    new_codes = st.text_input(
        "输入股票代码（多个代码用逗号分隔）",
        placeholder="例如: 000001, 600036, 300750",
        help="输入要添加到股票池的股票代码"
    )
    
    if st.button("➕ 添加到股票池"):
        if new_codes:
            codes = [c.strip() for c in new_codes.split(',') if c.strip()]
            valid_codes = validate_stock_codes(codes)
            
            if valid_codes:
                added = 0
                for code in valid_codes:
                    if code not in current_pool:
                        StockPool.add_code(code)
                        added += 1
                
                if added > 0:
                    st.success(f"✅ 成功添加 {added} 只股票")
                    st.rerun()
                else:
                    st.info("所有股票已在股票池中")
            else:
                st.error("输入的股票代码格式无效")
        else:
            st.warning("请输入股票代码")


def main():
    """数据管理页面主函数"""
    st.set_page_config(
        page_title="数据管理 - MiniQuant-Lite",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("📊 数据管理")
    st.markdown("管理股票数据的下载、更新和缓存")
    
    st.divider()
    
    # 初始化
    data_feed = get_data_feed()
    stock_pool = get_watchlist()
    
    # 数据状态概览
    render_data_status(data_feed, stock_pool)
    
    st.divider()
    
    # 数据下载
    render_download_section(data_feed, stock_pool)
    
    st.divider()
    
    # 股票池管理
    render_stock_pool_management()
    
    st.divider()
    
    # 缓存管理
    render_cache_management(data_feed)


if __name__ == "__main__":
    main()
