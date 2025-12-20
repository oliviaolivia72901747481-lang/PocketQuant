"""
MiniQuant-Lite 日志配置模块

提供统一的日志配置，支持：
- 按日期分文件存储
- 可配置的日志级别
- 详细的错误堆栈记录
- 控制台和文件双输出

Requirements: 9.1, 9.2, 9.3, 9.4, 9.5
"""

import logging
import os
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from typing import Optional

from config.settings import get_settings


def setup_logging(
    level: Optional[str] = None,
    log_dir: Optional[str] = None,
    file_prefix: Optional[str] = None,
    console_output: bool = True
) -> logging.Logger:
    """
    配置全局日志系统
    
    Args:
        level: 日志级别 ('DEBUG', 'INFO', 'WARNING', 'ERROR')，默认从配置读取
        log_dir: 日志目录，默认从配置读取
        file_prefix: 日志文件前缀，默认从配置读取
        console_output: 是否输出到控制台，默认 True
    
    Returns:
        根日志记录器
    
    Example:
        >>> setup_logging(level='DEBUG')
        >>> logger = logging.getLogger(__name__)
        >>> logger.info('系统启动')
    """
    settings = get_settings()
    
    # 使用参数或配置值
    log_level = level or settings.log.level
    log_path = log_dir or settings.path.get_log_path()
    prefix = file_prefix or settings.log.file_prefix
    
    # 确保日志目录存在
    os.makedirs(log_path, exist_ok=True)
    
    # 获取根日志记录器
    root_logger = logging.getLogger()
    
    # 清除已有的处理器（避免重复添加）
    root_logger.handlers.clear()
    
    # 设置日志级别
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger.setLevel(numeric_level)
    
    # 日志格式
    log_format = settings.log.format
    date_format = settings.log.date_format
    formatter = logging.Formatter(log_format, datefmt=date_format)
    
    # 文件处理器 - 按日期分文件存储
    log_filename = os.path.join(log_path, f'{prefix}.log')
    file_handler = TimedRotatingFileHandler(
        filename=log_filename,
        when='midnight',      # 每天午夜轮转
        interval=1,           # 间隔1天
        backupCount=30,       # 保留30天的日志
        encoding='utf-8'
    )
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(formatter)
    file_handler.suffix = '%Y-%m-%d'  # 日志文件后缀格式
    root_logger.addHandler(file_handler)
    
    # 控制台处理器
    if console_output:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的日志记录器
    
    Args:
        name: 日志记录器名称，通常使用 __name__
    
    Returns:
        日志记录器实例
    
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info('数据下载完成')
    """
    return logging.getLogger(name)


def set_log_level(level: str) -> None:
    """
    动态设置日志级别
    
    Args:
        level: 日志级别 ('DEBUG', 'INFO', 'WARNING', 'ERROR')
    
    Example:
        >>> set_log_level('DEBUG')  # 开启调试模式
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    for handler in root_logger.handlers:
        handler.setLevel(numeric_level)


def log_exception(logger: logging.Logger, message: str, exc: Exception) -> None:
    """
    记录异常信息（包含完整堆栈）
    
    Args:
        logger: 日志记录器
        message: 错误描述
        exc: 异常对象
    
    Example:
        >>> try:
        ...     risky_operation()
        ... except Exception as e:
        ...     log_exception(logger, '操作失败', e)
    """
    logger.error(f'{message}: {exc}', exc_info=True)


def get_log_files(log_dir: Optional[str] = None) -> list[dict]:
    """
    获取日志文件列表（供 Dashboard 使用）
    
    Args:
        log_dir: 日志目录，默认从配置读取
    
    Returns:
        日志文件信息列表，每个元素包含:
        - filename: 文件名
        - path: 完整路径
        - size: 文件大小（字节）
        - modified: 最后修改时间
    
    Example:
        >>> files = get_log_files()
        >>> for f in files:
        ...     print(f['filename'], f['size'])
    """
    settings = get_settings()
    log_path = log_dir or settings.path.get_log_path()
    
    if not os.path.exists(log_path):
        return []
    
    log_files = []
    for filename in os.listdir(log_path):
        if filename.endswith('.log') or '.log.' in filename:
            filepath = os.path.join(log_path, filename)
            stat = os.stat(filepath)
            log_files.append({
                'filename': filename,
                'path': filepath,
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime)
            })
    
    # 按修改时间降序排序
    log_files.sort(key=lambda x: x['modified'], reverse=True)
    return log_files


def read_log_file(filepath: str, lines: int = 100) -> list[str]:
    """
    读取日志文件内容（最后 N 行）
    
    Args:
        filepath: 日志文件路径
        lines: 读取的行数，默认100行
    
    Returns:
        日志内容列表
    
    Example:
        >>> content = read_log_file('logs/miniquant.log', lines=50)
        >>> for line in content:
        ...     print(line)
    """
    if not os.path.exists(filepath):
        return []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            return all_lines[-lines:] if len(all_lines) > lines else all_lines
    except Exception:
        return []


def clear_old_logs(days: int = 30, log_dir: Optional[str] = None) -> int:
    """
    清理过期日志文件
    
    Args:
        days: 保留天数，默认30天
        log_dir: 日志目录，默认从配置读取
    
    Returns:
        删除的文件数量
    
    Example:
        >>> deleted = clear_old_logs(days=7)
        >>> print(f'已删除 {deleted} 个过期日志文件')
    """
    settings = get_settings()
    log_path = log_dir or settings.path.get_log_path()
    
    if not os.path.exists(log_path):
        return 0
    
    deleted_count = 0
    cutoff_time = datetime.now().timestamp() - (days * 24 * 60 * 60)
    
    for filename in os.listdir(log_path):
        if filename.endswith('.log') or '.log.' in filename:
            filepath = os.path.join(log_path, filename)
            if os.stat(filepath).st_mtime < cutoff_time:
                try:
                    os.remove(filepath)
                    deleted_count += 1
                except OSError:
                    pass
    
    return deleted_count


# 模块级别的初始化标志
_logging_initialized = False


def ensure_logging_initialized() -> None:
    """
    确保日志系统已初始化（幂等操作）
    
    在应用启动时调用，确保日志系统只初始化一次
    """
    global _logging_initialized
    if not _logging_initialized:
        setup_logging()
        _logging_initialized = True
