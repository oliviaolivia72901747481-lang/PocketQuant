"""
MiniQuant-Lite 日志查看页面

提供日志查看功能，支持：
- 查看日志文件列表
- 查看日志内容
- 清理过期日志

Requirements: 9.5
"""

import streamlit as st
import sys
import os
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.logging_config import (
    get_log_files,
    read_log_file,
    clear_old_logs,
    set_log_level,
    ensure_logging_initialized,
    get_logger
)
from config.settings import get_settings

# 初始化日志系统
ensure_logging_initialized()
logger = get_logger(__name__)


def format_file_size(size_bytes: int) -> str:
    """格式化文件大小"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def main():
    """日志页面主函数"""
    logger.info("日志查看页面加载")
    
    st.title("📝 系统日志")
    st.markdown("查看和管理系统运行日志")
    
    st.divider()
    
    # ========== 日志级别设置 ==========
    st.subheader("⚙️ 日志设置")
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        settings = get_settings()
        current_level = settings.log.level
        
        level_options = ['DEBUG', 'INFO', 'WARNING', 'ERROR']
        selected_level = st.selectbox(
            "日志级别",
            options=level_options,
            index=level_options.index(current_level) if current_level in level_options else 1,
            help="DEBUG: 详细调试信息\nINFO: 一般运行信息\nWARNING: 警告信息\nERROR: 错误信息"
        )
        
        if st.button("应用级别", type="primary"):
            set_log_level(selected_level)
            logger.info(f"日志级别已更改为: {selected_level}")
            st.success(f"日志级别已设置为: {selected_level}")
    
    with col2:
        st.info("""
        **日志级别说明：**
        - **DEBUG**: 最详细，包含所有调试信息，适合排查问题
        - **INFO**: 一般运行信息，推荐日常使用
        - **WARNING**: 仅显示警告和错误
        - **ERROR**: 仅显示错误信息
        """)
    
    st.divider()
    
    # ========== 日志文件列表 ==========
    st.subheader("📁 日志文件")
    
    log_files = get_log_files()
    
    if not log_files:
        st.warning("暂无日志文件")
    else:
        # 显示日志文件列表
        col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
        col1.markdown("**文件名**")
        col2.markdown("**大小**")
        col3.markdown("**修改时间**")
        col4.markdown("**操作**")
        
        for i, log_file in enumerate(log_files[:10]):  # 最多显示10个文件
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            
            col1.text(log_file['filename'])
            col2.text(format_file_size(log_file['size']))
            col3.text(log_file['modified'].strftime('%Y-%m-%d %H:%M'))
            
            if col4.button("查看", key=f"view_{i}"):
                st.session_state['selected_log_file'] = log_file['path']
    
    st.divider()
    
    # ========== 日志内容查看 ==========
    st.subheader("📄 日志内容")
    
    selected_file = st.session_state.get('selected_log_file', None)
    
    if selected_file:
        st.caption(f"当前查看: {os.path.basename(selected_file)}")
        
        # 行数选择
        lines_to_show = st.slider("显示行数", min_value=50, max_value=500, value=100, step=50)
        
        # 读取日志内容
        log_content = read_log_file(selected_file, lines=lines_to_show)
        
        if log_content:
            # 日志过滤
            filter_text = st.text_input("过滤关键词", placeholder="输入关键词过滤日志...")
            
            if filter_text:
                log_content = [line for line in log_content if filter_text.lower() in line.lower()]
            
            # 显示日志内容
            log_text = ''.join(log_content)
            
            # 使用代码块显示，支持滚动
            st.code(log_text, language='log')
            
            # 下载按钮
            st.download_button(
                label="下载日志",
                data=log_text,
                file_name=os.path.basename(selected_file),
                mime="text/plain"
            )
        else:
            st.info("日志文件为空或无法读取")
    else:
        if log_files:
            st.info("👆 点击上方「查看」按钮查看日志内容")
        else:
            st.info("系统运行后将自动生成日志文件")
    
    st.divider()
    
    # ========== 日志清理 ==========
    st.subheader("🗑️ 日志清理")
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        days_to_keep = st.number_input(
            "保留天数",
            min_value=1,
            max_value=365,
            value=30,
            help="清理超过指定天数的日志文件"
        )
        
        if st.button("清理过期日志", type="secondary"):
            deleted_count = clear_old_logs(days=days_to_keep)
            if deleted_count > 0:
                logger.info(f"已清理 {deleted_count} 个过期日志文件")
                st.success(f"已清理 {deleted_count} 个过期日志文件")
                st.rerun()
            else:
                st.info("没有需要清理的日志文件")
    
    with col2:
        st.warning("""
        ⚠️ **注意**：清理操作不可恢复！
        
        建议保留至少 7 天的日志，以便排查问题。
        """)


if __name__ == "__main__":
    main()
