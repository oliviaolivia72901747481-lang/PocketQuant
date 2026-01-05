"""
配置管理系统

提供股票筛选引擎的配置管理功能，包括：
- 筛选参数配置
- 数据源配置
- 行业关键词配置
- 配置持久化

Requirements: 1.1, 1.3
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from enum import Enum
from pathlib import Path
import json
import logging
import os

logger = logging.getLogger(__name__)


class MarketType(Enum):
    """市场类型"""
    MAINBOARD = "mainboard"      # 主板 (000, 001, 600, 601, 603)
    SME = "sme"                  # 中小板 (002)
    GEM = "gem"                  # 创业板 (300)
    STAR = "star"               # 科创板 (688)
    ALL = "all"                 # 全部


@dataclass
class FinancialCriteria:
    """财务筛选标准"""
    min_roe: float = 8.0           # 最小ROE (%)
    max_debt_ratio: float = 60.0   # 最大负债率 (%)
    min_revenue_growth: float = 10.0  # 最小营收增长率 (%)
    min_profit_growth: float = 15.0   # 最小净利润增长率 (%)
    min_gross_margin: float = 20.0    # 最小毛利率 (%)
    min_net_margin: float = 5.0       # 最小净利率 (%)


@dataclass
class ValuationCriteria:
    """估值筛选标准"""
    max_pe: float = 50.0           # 最大PE
    max_pb: float = 8.0            # 最大PB
    max_peg: float = 2.0           # 最大PEG


@dataclass
class MarketCriteria:
    """市场表现筛选标准"""
    min_market_cap: float = 50.0   # 最小市值 (亿元)
    max_market_cap: float = 5000.0 # 最大市值 (亿元)
    min_turnover: float = 0.5      # 最小换手率 (%)
    max_turnover: float = 15.0     # 最大换手率 (%)
    min_daily_amount: float = 0.5  # 最小日均成交额 (亿元)
    max_volatility: float = 60.0   # 最大年波动率 (%)


@dataclass
class IndustryKeywords:
    """行业关键词配置"""
    semiconductor: List[str] = field(default_factory=lambda: [
        "芯片", "集成电路", "半导体", "晶圆", "封测", "IC设计",
        "功率器件", "模拟芯片", "存储器", "处理器", "GPU", "CPU"
    ])
    ai: List[str] = field(default_factory=lambda: [
        "人工智能", "AI", "机器学习", "深度学习", "算法", "神经网络",
        "计算机视觉", "语音识别", "自然语言", "智能驾驶", "大模型"
    ])
    communication: List[str] = field(default_factory=lambda: [
        "5G", "通信", "基站", "光通信", "射频", "天线", "光纤",
        "通信设备", "网络设备", "物联网", "边缘计算"
    ])
    new_energy: List[str] = field(default_factory=lambda: [
        "锂电池", "储能", "光伏", "风电", "新能源", "电池管理",
        "充电桩", "氢能", "燃料电池", "智能电网"
    ])
    consumer_electronics: List[str] = field(default_factory=lambda: [
        "智能手机", "可穿戴", "电子元器件", "精密制造", "显示屏",
        "摄像头", "传感器", "连接器", "PCB", "声学器件"
    ])
    software: List[str] = field(default_factory=lambda: [
        "软件", "云计算", "大数据", "互联网", "SaaS", "数据库",
        "操作系统", "中间件", "企业软件", "信息安全", "网络安全"
    ])
    biotech: List[str] = field(default_factory=lambda: [
        "医疗器械", "体外诊断", "生物制药", "基因", "医疗AI",
        "数字医疗", "远程医疗", "医疗机器人", "精准医疗"
    ])
    smart_manufacturing: List[str] = field(default_factory=lambda: [
        "工业自动化", "机器人", "工业软件", "3D打印", "激光设备",
        "数控机床", "工业互联网", "MES系统", "智能装备"
    ])
    
    def to_dict(self) -> Dict[str, List[str]]:
        """转换为字典格式"""
        return {
            "半导体": self.semiconductor,
            "人工智能": self.ai,
            "5G通信": self.communication,
            "新能源科技": self.new_energy,
            "消费电子": self.consumer_electronics,
            "软件服务": self.software,
            "生物医药科技": self.biotech,
            "智能制造": self.smart_manufacturing,
        }


@dataclass
class ScoringWeights:
    """评分权重配置"""
    financial_health: float = 0.35    # 财务健康度权重
    growth_potential: float = 0.25    # 成长潜力权重
    market_performance: float = 0.20  # 市场表现权重
    competitive_advantage: float = 0.20  # 竞争优势权重
    
    def validate(self) -> bool:
        """验证权重总和是否为1"""
        total = (
            self.financial_health + 
            self.growth_potential + 
            self.market_performance + 
            self.competitive_advantage
        )
        return abs(total - 1.0) < 0.001


@dataclass
class ScreenerConfig:
    """
    筛选器总配置
    
    集中管理所有筛选相关的配置参数
    """
    # 目标配置
    target_pool_size: int = 80        # 目标股票池规模
    min_pool_size: int = 60           # 最小股票池规模
    max_pool_size: int = 100          # 最大股票池规模
    
    # 市场类型
    market_types: List[MarketType] = field(default_factory=lambda: [
        MarketType.MAINBOARD, 
        MarketType.SME
    ])
    
    # 筛选标准
    financial: FinancialCriteria = field(default_factory=FinancialCriteria)
    valuation: ValuationCriteria = field(default_factory=ValuationCriteria)
    market: MarketCriteria = field(default_factory=MarketCriteria)
    
    # 行业关键词
    industry_keywords: IndustryKeywords = field(default_factory=IndustryKeywords)
    
    # 评分权重
    scoring_weights: ScoringWeights = field(default_factory=ScoringWeights)
    
    # 风险控制
    max_single_industry_weight: float = 0.25  # 单一行业最大权重
    max_single_stock_weight: float = 0.05     # 单只股票最大权重
    
    # 数据源配置
    primary_data_source: str = "akshare"
    fallback_data_source: str = "eastmoney"
    enable_cross_validation: bool = True
    
    # 更新配置
    update_frequency_days: int = 30   # 更新频率（天）
    
    # 排除配置
    exclude_st: bool = True           # 排除ST股票
    exclude_new_stocks_days: int = 60 # 排除上市不足N天的新股
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'target_pool_size': self.target_pool_size,
            'min_pool_size': self.min_pool_size,
            'max_pool_size': self.max_pool_size,
            'market_types': [mt.value for mt in self.market_types],
            'financial': asdict(self.financial),
            'valuation': asdict(self.valuation),
            'market': asdict(self.market),
            'scoring_weights': asdict(self.scoring_weights),
            'max_single_industry_weight': self.max_single_industry_weight,
            'max_single_stock_weight': self.max_single_stock_weight,
            'primary_data_source': self.primary_data_source,
            'fallback_data_source': self.fallback_data_source,
            'enable_cross_validation': self.enable_cross_validation,
            'update_frequency_days': self.update_frequency_days,
            'exclude_st': self.exclude_st,
            'exclude_new_stocks_days': self.exclude_new_stocks_days,
        }


class ScreenerConfigManager:
    """
    配置管理器
    
    提供配置的加载、保存、验证功能
    
    Requirements: 1.1, 1.3
    """
    
    DEFAULT_CONFIG_PATH = ".kiro/config/screener_config.json"
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径，None时使用默认路径
        """
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self._config: Optional[ScreenerConfig] = None
    
    def get_config(self) -> ScreenerConfig:
        """
        获取配置
        
        如果配置未加载，则尝试从文件加载或使用默认配置
        
        Returns:
            ScreenerConfig: 配置对象
        """
        if self._config is None:
            self._config = self.load_config()
        return self._config
    
    def load_config(self) -> ScreenerConfig:
        """
        从文件加载配置
        
        Returns:
            ScreenerConfig: 配置对象
        """
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                config = self._dict_to_config(data)
                logger.info(f"配置已从 {self.config_path} 加载")
                return config
                
            except Exception as e:
                logger.warning(f"加载配置失败: {e}，使用默认配置")
        
        return ScreenerConfig()
    
    def save_config(self, config: Optional[ScreenerConfig] = None) -> bool:
        """
        保存配置到文件
        
        Args:
            config: 要保存的配置，None时保存当前配置
        
        Returns:
            bool: 是否保存成功
        """
        if config is None:
            config = self.get_config()
        
        try:
            # 确保目录存在
            config_dir = os.path.dirname(self.config_path)
            if config_dir:
                os.makedirs(config_dir, exist_ok=True)
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config.to_dict(), f, ensure_ascii=False, indent=2)
            
            logger.info(f"配置已保存到 {self.config_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False
    
    def update_config(self, **kwargs) -> ScreenerConfig:
        """
        更新配置参数
        
        Args:
            **kwargs: 要更新的配置参数
        
        Returns:
            ScreenerConfig: 更新后的配置
        """
        config = self.get_config()
        
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
            else:
                logger.warning(f"未知配置参数: {key}")
        
        self._config = config
        return config
    
    def validate_config(self, config: Optional[ScreenerConfig] = None) -> List[str]:
        """
        验证配置有效性
        
        Args:
            config: 要验证的配置，None时验证当前配置
        
        Returns:
            List[str]: 验证错误列表，空列表表示验证通过
        """
        if config is None:
            config = self.get_config()
        
        errors = []
        
        # 验证目标规模
        if config.min_pool_size > config.max_pool_size:
            errors.append("最小股票池规模不能大于最大规模")
        
        if config.target_pool_size < config.min_pool_size:
            errors.append("目标规模不能小于最小规模")
        
        if config.target_pool_size > config.max_pool_size:
            errors.append("目标规模不能大于最大规模")
        
        # 验证评分权重
        if not config.scoring_weights.validate():
            errors.append("评分权重总和必须为1")
        
        # 验证风险控制参数
        if config.max_single_industry_weight <= 0 or config.max_single_industry_weight > 1:
            errors.append("单一行业最大权重必须在0-1之间")
        
        if config.max_single_stock_weight <= 0 or config.max_single_stock_weight > 1:
            errors.append("单只股票最大权重必须在0-1之间")
        
        # 验证财务标准
        if config.financial.min_roe < 0:
            errors.append("最小ROE不能为负数")
        
        if config.financial.max_debt_ratio > 100:
            errors.append("最大负债率不能超过100%")
        
        return errors
    
    def reset_to_default(self) -> ScreenerConfig:
        """
        重置为默认配置
        
        Returns:
            ScreenerConfig: 默认配置
        """
        self._config = ScreenerConfig()
        return self._config
    
    def get_industry_keywords(self) -> Dict[str, List[str]]:
        """
        获取行业关键词配置
        
        Returns:
            Dict[str, List[str]]: 行业关键词字典
        """
        config = self.get_config()
        return config.industry_keywords.to_dict()
    
    def add_industry_keyword(self, industry: str, keyword: str) -> bool:
        """
        添加行业关键词
        
        Args:
            industry: 行业名称
            keyword: 关键词
        
        Returns:
            bool: 是否添加成功
        """
        config = self.get_config()
        keywords_dict = config.industry_keywords.to_dict()
        
        if industry not in keywords_dict:
            logger.warning(f"未知行业: {industry}")
            return False
        
        if keyword not in keywords_dict[industry]:
            # 找到对应的属性并添加
            attr_mapping = {
                "半导体": "semiconductor",
                "人工智能": "ai",
                "5G通信": "communication",
                "新能源科技": "new_energy",
                "消费电子": "consumer_electronics",
                "软件服务": "software",
                "生物医药科技": "biotech",
                "智能制造": "smart_manufacturing",
            }
            
            attr_name = attr_mapping.get(industry)
            if attr_name:
                getattr(config.industry_keywords, attr_name).append(keyword)
                return True
        
        return False
    
    def _dict_to_config(self, data: Dict[str, Any]) -> ScreenerConfig:
        """将字典转换为配置对象"""
        config = ScreenerConfig()
        
        # 简单字段
        simple_fields = [
            'target_pool_size', 'min_pool_size', 'max_pool_size',
            'max_single_industry_weight', 'max_single_stock_weight',
            'primary_data_source', 'fallback_data_source',
            'enable_cross_validation', 'update_frequency_days',
            'exclude_st', 'exclude_new_stocks_days'
        ]
        
        for field in simple_fields:
            if field in data:
                setattr(config, field, data[field])
        
        # 市场类型
        if 'market_types' in data:
            config.market_types = [
                MarketType(mt) for mt in data['market_types']
            ]
        
        # 复杂字段
        if 'financial' in data:
            config.financial = FinancialCriteria(**data['financial'])
        
        if 'valuation' in data:
            config.valuation = ValuationCriteria(**data['valuation'])
        
        if 'market' in data:
            config.market = MarketCriteria(**data['market'])
        
        if 'scoring_weights' in data:
            config.scoring_weights = ScoringWeights(**data['scoring_weights'])
        
        return config


# 全局配置管理器实例
_config_manager: Optional[ScreenerConfigManager] = None


def get_screener_config_manager() -> ScreenerConfigManager:
    """
    获取配置管理器实例（单例模式）
    
    Returns:
        ScreenerConfigManager: 配置管理器实例
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ScreenerConfigManager()
    return _config_manager


def get_screener_config() -> ScreenerConfig:
    """
    获取筛选器配置（便捷函数）
    
    Returns:
        ScreenerConfig: 配置对象
    """
    return get_screener_config_manager().get_config()
