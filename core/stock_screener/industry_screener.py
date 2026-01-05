"""
行业筛选模块

提供科技行业的筛选功能，包括：
- 科技行业关键词库
- 基于关键词的行业匹配算法
- 主营业务分析器
- 行业分类置信度评分

Requirements: 2.1, 2.3, 4.2
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set
from enum import Enum
import re
import logging
import pandas as pd

logger = logging.getLogger(__name__)


class TechIndustry(Enum):
    """科技行业分类"""
    SEMICONDUCTOR = "半导体"
    AI = "人工智能"
    COMMUNICATION = "5G通信"
    NEW_ENERGY = "新能源科技"
    CONSUMER_ELECTRONICS = "消费电子"
    SOFTWARE = "软件服务"
    BIOTECH = "生物医药科技"
    SMART_MANUFACTURING = "智能制造"
    UNKNOWN = "未分类"


@dataclass
class IndustryMatchResult:
    """行业匹配结果"""
    code: str
    name: str
    matched_industry: TechIndustry
    confidence: float  # 置信度 0-1
    matched_keywords: List[str] = field(default_factory=list)
    business_description: Optional[str] = None
    secondary_industries: List[TechIndustry] = field(default_factory=list)


@dataclass
class IndustryKeywordConfig:
    """行业关键词配置"""
    # 半导体产业链
    semiconductor: List[str] = field(default_factory=lambda: [
        "芯片", "集成电路", "半导体", "晶圆", "封测", "IC设计",
        "功率器件", "模拟芯片", "存储器", "处理器", "GPU", "CPU",
        "FPGA", "MCU", "SoC", "光刻", "刻蚀", "薄膜", "离子注入",
        "硅片", "光掩模", "电子特气", "CMP", "靶材", "前驱体"
    ])
    
    # 人工智能与大数据
    ai: List[str] = field(default_factory=lambda: [
        "人工智能", "AI", "机器学习", "深度学习", "算法", "神经网络",
        "计算机视觉", "语音识别", "自然语言", "智能驾驶", "大模型",
        "AIGC", "ChatGPT", "大数据", "数据挖掘", "知识图谱",
        "智能推荐", "图像识别", "语义分析", "机器人视觉"
    ])
    
    # 5G与通信技术
    communication: List[str] = field(default_factory=lambda: [
        "5G", "通信", "基站", "光通信", "射频", "天线", "光纤",
        "通信设备", "网络设备", "物联网", "边缘计算", "卫星通信",
        "光模块", "交换机", "路由器", "网络安全", "信息安全",
        "数据中心", "IDC", "CDN", "云网融合"
    ])
    
    # 新能源科技
    new_energy: List[str] = field(default_factory=lambda: [
        "锂电池", "储能", "光伏", "风电", "新能源", "电池管理",
        "充电桩", "氢能", "燃料电池", "智能电网", "逆变器",
        "正极材料", "负极材料", "电解液", "隔膜", "BMS",
        "IGBT", "碳化硅", "氮化镓", "电力电子"
    ])
    
    # 消费电子与智能硬件
    consumer_electronics: List[str] = field(default_factory=lambda: [
        "智能手机", "可穿戴", "电子元器件", "精密制造", "显示屏",
        "摄像头", "传感器", "连接器", "PCB", "声学器件",
        "触控", "指纹识别", "面板", "OLED", "Mini LED",
        "VR", "AR", "智能家居", "TWS耳机", "智能手表"
    ])
    
    # 软件与信息服务
    software: List[str] = field(default_factory=lambda: [
        "软件", "云计算", "大数据", "互联网", "SaaS", "数据库",
        "操作系统", "中间件", "企业软件", "信息安全", "网络安全",
        "ERP", "CRM", "OA", "低代码", "数字化", "信创",
        "国产替代", "工业软件", "CAD", "CAE", "EDA"
    ])
    
    # 生物医药科技
    biotech: List[str] = field(default_factory=lambda: [
        "医疗器械", "体外诊断", "生物制药", "基因", "医疗AI",
        "数字医疗", "远程医疗", "医疗机器人", "精准医疗",
        "基因测序", "细胞治疗", "抗体药物", "疫苗", "创新药",
        "医疗影像", "手术机器人", "康复设备", "IVD"
    ])
    
    # 智能制造与工业互联网
    smart_manufacturing: List[str] = field(default_factory=lambda: [
        "工业自动化", "机器人", "工业软件", "3D打印", "激光设备",
        "数控机床", "工业互联网", "MES系统", "智能装备",
        "伺服系统", "PLC", "工业视觉", "AGV", "协作机器人",
        "智能仓储", "柔性制造", "数字孪生", "工业4.0"
    ])
    
    def to_dict(self) -> Dict[str, List[str]]:
        """转换为字典格式"""
        return {
            TechIndustry.SEMICONDUCTOR.value: self.semiconductor,
            TechIndustry.AI.value: self.ai,
            TechIndustry.COMMUNICATION.value: self.communication,
            TechIndustry.NEW_ENERGY.value: self.new_energy,
            TechIndustry.CONSUMER_ELECTRONICS.value: self.consumer_electronics,
            TechIndustry.SOFTWARE.value: self.software,
            TechIndustry.BIOTECH.value: self.biotech,
            TechIndustry.SMART_MANUFACTURING.value: self.smart_manufacturing,
        }
    
    def get_all_keywords(self) -> Set[str]:
        """获取所有关键词"""
        all_keywords = set()
        for keywords in self.to_dict().values():
            all_keywords.update(keywords)
        return all_keywords


class IndustryScreener:
    """
    行业筛选器
    
    基于关键词匹配和主营业务分析进行科技行业筛选
    
    Requirements: 2.1, 2.3
    """
    
    def __init__(self, keyword_config: Optional[IndustryKeywordConfig] = None):
        """
        初始化行业筛选器
        
        Args:
            keyword_config: 关键词配置，None时使用默认配置
        """
        self.keyword_config = keyword_config or IndustryKeywordConfig()
        self._keyword_dict = self.keyword_config.to_dict()
        self._industry_enum_map = {
            TechIndustry.SEMICONDUCTOR.value: TechIndustry.SEMICONDUCTOR,
            TechIndustry.AI.value: TechIndustry.AI,
            TechIndustry.COMMUNICATION.value: TechIndustry.COMMUNICATION,
            TechIndustry.NEW_ENERGY.value: TechIndustry.NEW_ENERGY,
            TechIndustry.CONSUMER_ELECTRONICS.value: TechIndustry.CONSUMER_ELECTRONICS,
            TechIndustry.SOFTWARE.value: TechIndustry.SOFTWARE,
            TechIndustry.BIOTECH.value: TechIndustry.BIOTECH,
            TechIndustry.SMART_MANUFACTURING.value: TechIndustry.SMART_MANUFACTURING,
        }

    def match_industry(
        self, 
        name: str, 
        business_desc: Optional[str] = None,
        industry_name: Optional[str] = None
    ) -> Tuple[TechIndustry, float, List[str]]:
        """
        匹配股票所属的科技行业
        
        Args:
            name: 股票名称
            business_desc: 主营业务描述
            industry_name: 申万行业分类名称
        
        Returns:
            Tuple[匹配的行业, 置信度, 匹配的关键词列表]
        """
        # 合并所有可用文本
        text_to_match = name or ""
        if business_desc:
            text_to_match += " " + business_desc
        if industry_name:
            text_to_match += " " + industry_name
        
        if not text_to_match.strip():
            return TechIndustry.UNKNOWN, 0.0, []
        
        # 统计各行业的匹配情况
        industry_scores: Dict[str, Tuple[int, List[str]]] = {}
        
        for industry_name_key, keywords in self._keyword_dict.items():
            matched_keywords = []
            for keyword in keywords:
                if keyword in text_to_match:
                    matched_keywords.append(keyword)
            
            if matched_keywords:
                industry_scores[industry_name_key] = (len(matched_keywords), matched_keywords)
        
        if not industry_scores:
            return TechIndustry.UNKNOWN, 0.0, []
        
        # 找到匹配最多的行业
        best_industry = max(industry_scores.keys(), key=lambda x: industry_scores[x][0])
        match_count, matched_keywords = industry_scores[best_industry]
        
        # 计算置信度
        # 基础置信度：匹配关键词数量
        base_confidence = min(1.0, match_count / 3)
        
        # 如果名称中直接包含关键词，增加置信度
        name_match_bonus = 0.0
        for kw in matched_keywords:
            if kw in (name or ""):
                name_match_bonus = 0.2
                break
        
        confidence = min(1.0, base_confidence + name_match_bonus)
        
        industry_enum = self._industry_enum_map.get(best_industry, TechIndustry.UNKNOWN)
        
        return industry_enum, confidence, matched_keywords
    
    def screen_tech_stocks(
        self, 
        df: pd.DataFrame,
        min_confidence: float = 0.3,
        name_col: str = 'name',
        business_col: Optional[str] = None,
        industry_col: Optional[str] = None
    ) -> Tuple[pd.DataFrame, List[IndustryMatchResult]]:
        """
        筛选科技股票
        
        Args:
            df: 股票数据DataFrame
            min_confidence: 最小置信度阈值
            name_col: 股票名称列名
            business_col: 主营业务列名
            industry_col: 行业分类列名
        
        Returns:
            Tuple[筛选后的DataFrame, 匹配结果列表]
        """
        if df is None or df.empty:
            return pd.DataFrame(), []
        
        match_results: List[IndustryMatchResult] = []
        tech_indices = []
        
        for idx, row in df.iterrows():
            code = str(row.get('code', ''))
            name = str(row.get(name_col, ''))
            business_desc = str(row.get(business_col, '')) if business_col and business_col in df.columns else None
            industry_name = str(row.get(industry_col, '')) if industry_col and industry_col in df.columns else None
            
            industry, confidence, matched_keywords = self.match_industry(
                name=name,
                business_desc=business_desc,
                industry_name=industry_name
            )
            
            if industry != TechIndustry.UNKNOWN and confidence >= min_confidence:
                tech_indices.append(idx)
                match_results.append(IndustryMatchResult(
                    code=code,
                    name=name,
                    matched_industry=industry,
                    confidence=confidence,
                    matched_keywords=matched_keywords,
                    business_description=business_desc
                ))
        
        # 筛选出科技股
        tech_df = df.loc[tech_indices].copy()
        
        # 添加行业分类列
        if len(tech_df) > 0:
            industry_map = {r.code: r.matched_industry.value for r in match_results}
            confidence_map = {r.code: r.confidence for r in match_results}
            
            tech_df['tech_industry'] = tech_df['code'].map(industry_map)
            tech_df['industry_confidence'] = tech_df['code'].map(confidence_map)
        
        logger.info(f"从 {len(df)} 只股票中筛选出 {len(tech_df)} 只科技股")
        
        return tech_df, match_results
    
    def get_industry_distribution(
        self, 
        match_results: List[IndustryMatchResult]
    ) -> Dict[str, int]:
        """
        获取行业分布统计
        
        Args:
            match_results: 匹配结果列表
        
        Returns:
            行业分布字典
        """
        distribution: Dict[str, int] = {}
        
        for result in match_results:
            industry_name = result.matched_industry.value
            distribution[industry_name] = distribution.get(industry_name, 0) + 1
        
        return distribution
    
    def add_keyword(self, industry: TechIndustry, keyword: str) -> bool:
        """
        添加行业关键词
        
        Args:
            industry: 行业类型
            keyword: 关键词
        
        Returns:
            是否添加成功
        """
        industry_name = industry.value
        if industry_name not in self._keyword_dict:
            return False
        
        if keyword not in self._keyword_dict[industry_name]:
            self._keyword_dict[industry_name].append(keyword)
            logger.info(f"已添加关键词 '{keyword}' 到行业 '{industry_name}'")
            return True
        
        return False
    
    def get_keywords(self, industry: TechIndustry) -> List[str]:
        """
        获取指定行业的关键词列表
        
        Args:
            industry: 行业类型
        
        Returns:
            关键词列表
        """
        return self._keyword_dict.get(industry.value, [])
    
    def is_tech_stock(
        self, 
        name: str, 
        business_desc: Optional[str] = None,
        min_confidence: float = 0.3
    ) -> bool:
        """
        判断是否为科技股
        
        Args:
            name: 股票名称
            business_desc: 主营业务描述
            min_confidence: 最小置信度
        
        Returns:
            是否为科技股
        """
        industry, confidence, _ = self.match_industry(name, business_desc)
        return industry != TechIndustry.UNKNOWN and confidence >= min_confidence


class BusinessAnalyzer:
    """
    主营业务分析器
    
    解析公司主营业务描述，计算与科技行业的匹配度
    
    Requirements: 2.3, 4.2
    """
    
    def __init__(self, industry_screener: Optional[IndustryScreener] = None):
        """
        初始化主营业务分析器
        
        Args:
            industry_screener: 行业筛选器实例
        """
        self.industry_screener = industry_screener or IndustryScreener()
    
    def analyze_business(
        self, 
        business_desc: str
    ) -> Dict[str, any]:
        """
        分析主营业务描述
        
        Args:
            business_desc: 主营业务描述
        
        Returns:
            分析结果字典
        """
        if not business_desc or not business_desc.strip():
            return {
                'is_tech': False,
                'primary_industry': TechIndustry.UNKNOWN,
                'confidence': 0.0,
                'matched_keywords': [],
                'tech_relevance_score': 0.0
            }
        
        # 使用行业筛选器进行匹配
        industry, confidence, matched_keywords = self.industry_screener.match_industry(
            name="",
            business_desc=business_desc
        )
        
        # 计算科技相关度得分
        all_keywords = self.industry_screener.keyword_config.get_all_keywords()
        keyword_count = sum(1 for kw in all_keywords if kw in business_desc)
        tech_relevance_score = min(1.0, keyword_count / 5)
        
        return {
            'is_tech': industry != TechIndustry.UNKNOWN,
            'primary_industry': industry,
            'confidence': confidence,
            'matched_keywords': matched_keywords,
            'tech_relevance_score': tech_relevance_score
        }
    
    def batch_analyze(
        self, 
        df: pd.DataFrame,
        business_col: str = 'business_desc'
    ) -> pd.DataFrame:
        """
        批量分析主营业务
        
        Args:
            df: 股票数据DataFrame
            business_col: 主营业务列名
        
        Returns:
            添加分析结果的DataFrame
        """
        if df is None or df.empty or business_col not in df.columns:
            return df
        
        result_df = df.copy()
        
        # 分析每只股票的主营业务
        analysis_results = []
        for _, row in df.iterrows():
            business_desc = str(row.get(business_col, ''))
            result = self.analyze_business(business_desc)
            analysis_results.append(result)
        
        # 添加分析结果列
        result_df['is_tech_business'] = [r['is_tech'] for r in analysis_results]
        result_df['business_industry'] = [r['primary_industry'].value for r in analysis_results]
        result_df['business_confidence'] = [r['confidence'] for r in analysis_results]
        result_df['tech_relevance_score'] = [r['tech_relevance_score'] for r in analysis_results]
        
        return result_df


# 全局行业筛选器实例
_industry_screener: Optional[IndustryScreener] = None


def get_industry_screener() -> IndustryScreener:
    """
    获取行业筛选器实例（单例模式）
    
    Returns:
        IndustryScreener: 行业筛选器实例
    """
    global _industry_screener
    if _industry_screener is None:
        _industry_screener = IndustryScreener()
    return _industry_screener
