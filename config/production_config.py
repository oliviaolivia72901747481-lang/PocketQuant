"""
生产环境配置模块

提供生产环境所需的配置参数，包括：
- 生产环境参数配置
- 数据迁移和初始化
- 上线前测试配置
- 环境检测和验证

Requirements: 技术约束, 13.1
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime
import logging
import os
import json

logger = logging.getLogger(__name__)


class Environment(Enum):
    """运行环境"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class DatabaseConfig:
    """数据库配置"""
    data_dir: str = "data"
    processed_dir: str = "data/processed"
    backup_dir: str = "data/pool_backups"
    history_file: str = "data/pool_update_history.json"
    signal_history_file: str = "data/signal_history.csv"
    positions_file: str = "data/positions.csv"
    
    def ensure_directories(self):
        """确保所有数据目录存在"""
        dirs = [
            self.data_dir,
            self.processed_dir,
            self.backup_dir,
        ]
        for dir_path in dirs:
            os.makedirs(dir_path, exist_ok=True)


@dataclass
class LoggingConfig:
    """日志配置"""
    log_dir: str = "logs"
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    max_log_files: int = 30
    log_file_prefix: str = "miniquant"
    
    def ensure_directory(self):
        """确保日志目录存在"""
        os.makedirs(self.log_dir, exist_ok=True)


@dataclass
class ScreenerConfig:
    """筛选器配置"""
    # 筛选参数
    min_score: float = 60.0
    target_count: int = 100
    max_single_industry: float = 0.25
    
    # 性能参数
    max_workers: int = 4
    cache_ttl_minutes: int = 30
    max_cache_size: int = 100
    
    # 超时设置
    data_fetch_timeout: int = 60
    screening_timeout: int = 1800  # 30分钟


@dataclass
class AlertConfig:
    """告警配置"""
    enabled: bool = True
    alert_threshold: str = "medium"  # low, medium, high, critical
    notification_channels: List[str] = field(default_factory=lambda: ["log"])
    
    # 告警阈值
    quality_score_threshold: float = 70.0
    risk_score_threshold: float = 50.0


@dataclass
class ScheduleConfig:
    """调度配置"""
    # 定期更新
    auto_update_enabled: bool = False
    update_schedule: str = "0 18 * * 1-5"  # 工作日18:00
    
    # 数据刷新
    data_refresh_interval_hours: int = 24
    
    # 维护窗口
    maintenance_window_start: str = "02:00"
    maintenance_window_end: str = "06:00"


@dataclass
class ProductionConfig:
    """
    生产环境总配置
    
    集中管理生产环境所有配置
    """
    environment: Environment = Environment.PRODUCTION
    version: str = "1.0.0"
    
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    screener: ScreenerConfig = field(default_factory=ScreenerConfig)
    alert: AlertConfig = field(default_factory=AlertConfig)
    schedule: ScheduleConfig = field(default_factory=ScheduleConfig)
    
    # 功能开关
    features: Dict[str, bool] = field(default_factory=lambda: {
        'auto_update': False,
        'risk_monitoring': True,
        'quality_validation': True,
        'performance_tracking': True,
        'backup_enabled': True,
    })
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'environment': self.environment.value,
            'version': self.version,
            'database': {
                'data_dir': self.database.data_dir,
                'processed_dir': self.database.processed_dir,
                'backup_dir': self.database.backup_dir,
            },
            'logging': {
                'log_dir': self.logging.log_dir,
                'log_level': self.logging.log_level,
            },
            'screener': {
                'min_score': self.screener.min_score,
                'target_count': self.screener.target_count,
                'max_single_industry': self.screener.max_single_industry,
            },
            'alert': {
                'enabled': self.alert.enabled,
                'alert_threshold': self.alert.alert_threshold,
            },
            'features': self.features,
        }


# 全局配置实例
_production_config: Optional[ProductionConfig] = None


def get_production_config() -> ProductionConfig:
    """获取生产环境配置实例"""
    global _production_config
    if _production_config is None:
        _production_config = ProductionConfig()
    return _production_config


def reset_production_config() -> None:
    """重置生产环境配置"""
    global _production_config
    _production_config = None


def load_config_from_file(config_path: str) -> ProductionConfig:
    """
    从文件加载配置
    
    Args:
        config_path: 配置文件路径
    
    Returns:
        ProductionConfig: 配置对象
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        config = ProductionConfig()
        
        # 更新环境
        if 'environment' in data:
            config.environment = Environment(data['environment'])
        
        # 更新版本
        if 'version' in data:
            config.version = data['version']
        
        # 更新数据库配置
        if 'database' in data:
            db_data = data['database']
            config.database.data_dir = db_data.get('data_dir', config.database.data_dir)
            config.database.processed_dir = db_data.get('processed_dir', config.database.processed_dir)
            config.database.backup_dir = db_data.get('backup_dir', config.database.backup_dir)
        
        # 更新日志配置
        if 'logging' in data:
            log_data = data['logging']
            config.logging.log_dir = log_data.get('log_dir', config.logging.log_dir)
            config.logging.log_level = log_data.get('log_level', config.logging.log_level)
        
        # 更新筛选器配置
        if 'screener' in data:
            scr_data = data['screener']
            config.screener.min_score = scr_data.get('min_score', config.screener.min_score)
            config.screener.target_count = scr_data.get('target_count', config.screener.target_count)
            config.screener.max_single_industry = scr_data.get('max_single_industry', config.screener.max_single_industry)
        
        # 更新告警配置
        if 'alert' in data:
            alert_data = data['alert']
            config.alert.enabled = alert_data.get('enabled', config.alert.enabled)
            config.alert.alert_threshold = alert_data.get('alert_threshold', config.alert.alert_threshold)
        
        # 更新功能开关
        if 'features' in data:
            config.features.update(data['features'])
        
        return config
        
    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")
        return ProductionConfig()


def save_config_to_file(config: ProductionConfig, config_path: str) -> bool:
    """
    保存配置到文件
    
    Args:
        config: 配置对象
        config_path: 配置文件路径
    
    Returns:
        bool: 是否保存成功
    """
    try:
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config.to_dict(), f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"保存配置文件失败: {e}")
        return False
