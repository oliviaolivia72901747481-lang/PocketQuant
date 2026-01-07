"""
热点题材智能管理器 - Hot Topic Manager

功能:
1. 从配置文件加载热点题材
2. 基于涨停板数据自动识别热点
3. 自动管理热点有效期
4. 支持手动添加/删除热点

作者: 卓越股票分析师
版本: 1.0
日期: 2026-01-06
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from pathlib import Path


@dataclass
class HotTopic:
    """热点题材数据类"""
    name: str                          # 题材名称
    keywords: List[str]                # 关键词列表
    weight: float                      # 权重加成 (1.0-2.0)
    start_date: str                    # 开始日期 YYYY-MM-DD
    end_date: Optional[str] = None     # 结束日期 (None表示持续)
    description: str = ""              # 描述
    source: str = "manual"             # 来源: manual/auto
    heat_score: float = 50.0           # 热度分数 (0-100)
    related_stocks: List[str] = field(default_factory=list)  # 相关股票代码
    
    def is_active(self) -> bool:
        """检查热点是否在有效期内"""
        today = datetime.now().strftime("%Y-%m-%d")
        if self.start_date > today:
            return False
        if self.end_date and self.end_date < today:
            return False
        return True
    
    def days_remaining(self) -> int:
        """计算剩余有效天数"""
        if not self.end_date:
            return 999  # 持续有效
        end = datetime.strptime(self.end_date, "%Y-%m-%d")
        today = datetime.now()
        return max(0, (end - today).days)


class HotTopicManager:
    """
    热点题材智能管理器
    
    核心功能:
    1. 配置文件管理 - 持久化存储热点配置
    2. 自动识别 - 基于涨停板数据识别热点
    3. 有效期管理 - 自动过期和续期
    4. 热度排名 - 动态计算热点热度
    """
    
    # 默认配置文件路径
    DEFAULT_CONFIG_PATH = "config/hot_topics.json"
    
    # 预设热点模板 (2026年1月)
    PRESET_TOPICS = [
        HotTopic(
            name="CES科技展",
            keywords=["CES", "消费电子", "AI眼镜", "VR", "AR", "智能穿戴", "XR"],
            weight=1.5,
            start_date="2026-01-01",
            end_date="2026-01-15",
            description="CES 2026消费电子展，AI眼镜、VR/AR设备是焦点",
            source="preset",
            heat_score=95
        ),
        HotTopic(
            name="AI人工智能",
            keywords=["AI", "人工智能", "大模型", "ChatGPT", "算力", "GPU", "英伟达"],
            weight=1.4,
            start_date="2025-01-01",
            end_date=None,
            description="AI长期主线，持续受资金关注",
            source="preset",
            heat_score=90
        ),
        HotTopic(
            name="半导体国产替代",
            keywords=["半导体", "芯片", "封测", "光刻", "国产替代", "先进封装"],
            weight=1.35,
            start_date="2025-01-01",
            end_date=None,
            description="半导体国产替代，政策持续支持",
            source="preset",
            heat_score=88
        ),
        HotTopic(
            name="人形机器人",
            keywords=["机器人", "人形机器人", "特斯拉", "Optimus", "减速器", "伺服"],
            weight=1.3,
            start_date="2025-10-01",
            end_date=None,
            description="人形机器人概念，特斯拉Optimus带动",
            source="preset",
            heat_score=82
        ),
        HotTopic(
            name="低空经济",
            keywords=["低空", "eVTOL", "飞行汽车", "无人机", "空中交通"],
            weight=1.25,
            start_date="2025-11-01",
            end_date=None,
            description="低空经济政策支持，eVTOL商业化加速",
            source="preset",
            heat_score=78
        ),
        HotTopic(
            name="新能源汽车",
            keywords=["新能源", "电动车", "锂电池", "充电桩", "固态电池"],
            weight=1.1,
            start_date="2024-01-01",
            end_date=None,
            description="新能源汽车，长期赛道但短期热度一般",
            source="preset",
            heat_score=65
        ),
    ]
    
    def __init__(self, config_path: str = None):
        """
        初始化热点管理器
        
        Args:
            config_path: 配置文件路径，默认使用 config/hot_topics.json
        """
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self.topics: List[HotTopic] = []
        self._load_or_init_config()
    
    def _load_or_init_config(self):
        """加载配置文件，如果不存在则初始化"""
        if os.path.exists(self.config_path):
            self._load_config()
        else:
            self._init_default_config()
    
    def _load_config(self):
        """从配置文件加载热点"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.topics = []
            for item in data.get('topics', []):
                topic = HotTopic(
                    name=item['name'],
                    keywords=item['keywords'],
                    weight=item['weight'],
                    start_date=item['start_date'],
                    end_date=item.get('end_date'),
                    description=item.get('description', ''),
                    source=item.get('source', 'manual'),
                    heat_score=item.get('heat_score', 50),
                    related_stocks=item.get('related_stocks', [])
                )
                self.topics.append(topic)
            
            print(f"✅ 已加载 {len(self.topics)} 个热点题材")
        except Exception as e:
            print(f"⚠️ 加载配置失败: {e}，使用默认配置")
            self._init_default_config()
    
    def _init_default_config(self):
        """初始化默认配置"""
        self.topics = self.PRESET_TOPICS.copy()
        self._save_config()
        print(f"✅ 已初始化 {len(self.topics)} 个预设热点题材")
    
    def _save_config(self):
        """保存配置到文件"""
        # 确保目录存在
        Path(self.config_path).parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'last_updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'topics': [asdict(t) for t in self.topics]
        }
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def get_active_topics(self) -> List[HotTopic]:
        """获取当前有效的热点题材"""
        return [t for t in self.topics if t.is_active()]
    
    def get_topic_by_name(self, name: str) -> Optional[HotTopic]:
        """根据名称获取热点"""
        for topic in self.topics:
            if topic.name == name:
                return topic
        return None
    
    def add_topic(self, topic: HotTopic) -> bool:
        """
        添加新热点
        
        Args:
            topic: 热点题材对象
        
        Returns:
            是否添加成功
        """
        # 检查是否已存在
        if self.get_topic_by_name(topic.name):
            print(f"⚠️ 热点 '{topic.name}' 已存在")
            return False
        
        self.topics.append(topic)
        self._save_config()
        print(f"✅ 已添加热点: {topic.name}")
        return True
    
    def remove_topic(self, name: str) -> bool:
        """
        删除热点
        
        Args:
            name: 热点名称
        
        Returns:
            是否删除成功
        """
        topic = self.get_topic_by_name(name)
        if not topic:
            print(f"⚠️ 热点 '{name}' 不存在")
            return False
        
        self.topics.remove(topic)
        self._save_config()
        print(f"✅ 已删除热点: {name}")
        return True
    
    def update_topic_heat(self, name: str, heat_score: float) -> bool:
        """
        更新热点热度
        
        Args:
            name: 热点名称
            heat_score: 新的热度分数 (0-100)
        
        Returns:
            是否更新成功
        """
        topic = self.get_topic_by_name(name)
        if not topic:
            return False
        
        topic.heat_score = max(0, min(100, heat_score))
        self._save_config()
        return True
    
    def extend_topic(self, name: str, days: int = 7) -> bool:
        """
        延长热点有效期
        
        Args:
            name: 热点名称
            days: 延长天数
        
        Returns:
            是否延长成功
        """
        topic = self.get_topic_by_name(name)
        if not topic:
            return False
        
        if topic.end_date:
            end = datetime.strptime(topic.end_date, "%Y-%m-%d")
            new_end = end + timedelta(days=days)
        else:
            new_end = datetime.now() + timedelta(days=days)
        
        topic.end_date = new_end.strftime("%Y-%m-%d")
        self._save_config()
        print(f"✅ 已延长热点 '{name}' 至 {topic.end_date}")
        return True
    
    def match_stock_topics(self, 
                          stock_name: str, 
                          sector: str,
                          concepts: List[str] = None) -> List[Dict]:
        """
        匹配股票所属的热点题材
        
        Args:
            stock_name: 股票名称
            sector: 所属板块
            concepts: 概念标签列表
        
        Returns:
            匹配到的热点列表
        """
        search_text = f"{stock_name} {sector} {' '.join(concepts or [])}"
        matched = []
        
        for topic in self.get_active_topics():
            for keyword in topic.keywords:
                if keyword in search_text:
                    matched.append({
                        'name': topic.name,
                        'keyword': keyword,
                        'weight': topic.weight,
                        'heat_score': topic.heat_score,
                        'days_remaining': topic.days_remaining()
                    })
                    break
        
        # 按热度排序
        matched.sort(key=lambda x: x['heat_score'], reverse=True)
        return matched
    
    def calculate_hot_topic_score(self,
                                 stock_name: str,
                                 sector: str,
                                 concepts: List[str] = None,
                                 max_score: float = 25.0) -> Tuple[float, Dict]:
        """
        计算热点题材得分
        
        Args:
            stock_name: 股票名称
            sector: 所属板块
            concepts: 概念标签
            max_score: 最高分
        
        Returns:
            (得分, 详细信息)
        """
        matched = self.match_stock_topics(stock_name, sector, concepts)
        
        if not matched:
            return max_score * 0.3, {
                'matched_topics': [],
                'topic_count': 0,
                'is_hot': False,
                'category': '冷门题材'
            }
        
        # 取最高权重
        max_weight = max(m['weight'] for m in matched)
        max_heat = max(m['heat_score'] for m in matched)
        
        # 基础分 = 最高权重映射
        base_score = max_score * (0.6 + 0.4 * (max_weight - 1) / 0.5)
        
        # 多重热点加成
        if len(matched) > 1:
            bonus = min(0.2, (len(matched) - 1) * 0.05)
            base_score *= (1 + bonus)
        
        # 热度调整
        heat_multiplier = 0.8 + 0.4 * (max_heat / 100)
        final_score = min(max_score, base_score * heat_multiplier)
        
        # 分类
        if len(matched) >= 2 and max_heat >= 80:
            category = "超级热点"
        elif len(matched) >= 1 and max_heat >= 70:
            category = "当前热点"
        elif len(matched) >= 1 or max_heat >= 60:
            category = "潜在热点"
        else:
            category = "一般题材"
        
        return round(final_score, 2), {
            'matched_topics': matched,
            'topic_count': len(matched),
            'max_weight': max_weight,
            'max_heat': max_heat,
            'is_hot': len(matched) > 0,
            'category': category
        }
    
    def auto_detect_hot_topics(self, 
                              limit_up_stocks: List[Dict],
                              min_count: int = 3) -> List[HotTopic]:
        """
        基于涨停板数据自动识别热点
        
        Args:
            limit_up_stocks: 涨停股票列表，每个包含 {code, name, sector, concepts}
            min_count: 最少涨停数量才算热点
        
        Returns:
            新识别的热点列表
        """
        # 统计板块涨停数量
        sector_counts = {}
        concept_counts = {}
        
        for stock in limit_up_stocks:
            sector = stock.get('sector', '')
            if sector:
                sector_counts[sector] = sector_counts.get(sector, 0) + 1
            
            for concept in stock.get('concepts', []):
                concept_counts[concept] = concept_counts.get(concept, 0) + 1
        
        new_topics = []
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 识别板块热点
        for sector, count in sector_counts.items():
            if count >= min_count:
                # 检查是否已存在
                existing = self.get_topic_by_name(f"{sector}板块")
                if existing:
                    # 更新热度
                    new_heat = min(100, existing.heat_score + count * 5)
                    self.update_topic_heat(existing.name, new_heat)
                else:
                    # 创建新热点
                    topic = HotTopic(
                        name=f"{sector}板块",
                        keywords=[sector],
                        weight=min(1.5, 1.0 + count * 0.05),
                        start_date=today,
                        end_date=(datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"),
                        description=f"自动识别: {count}只涨停",
                        source="auto",
                        heat_score=min(100, 50 + count * 10)
                    )
                    new_topics.append(topic)
        
        # 识别概念热点
        for concept, count in concept_counts.items():
            if count >= min_count:
                existing = self.get_topic_by_name(concept)
                if existing:
                    new_heat = min(100, existing.heat_score + count * 5)
                    self.update_topic_heat(existing.name, new_heat)
                else:
                    topic = HotTopic(
                        name=concept,
                        keywords=[concept],
                        weight=min(1.5, 1.0 + count * 0.05),
                        start_date=today,
                        end_date=(datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"),
                        description=f"自动识别: {count}只涨停",
                        source="auto",
                        heat_score=min(100, 50 + count * 10)
                    )
                    new_topics.append(topic)
        
        # 添加新热点
        for topic in new_topics:
            self.add_topic(topic)
        
        return new_topics
    
    def get_heat_ranking(self) -> List[Dict]:
        """获取热点热度排名"""
        active = self.get_active_topics()
        ranking = []
        
        for topic in active:
            ranking.append({
                'name': topic.name,
                'heat_score': topic.heat_score,
                'weight': topic.weight,
                'days_remaining': topic.days_remaining(),
                'source': topic.source
            })
        
        ranking.sort(key=lambda x: x['heat_score'], reverse=True)
        return ranking
    
    def print_status(self):
        """打印热点状态"""
        print("\n" + "=" * 50)
        print("📌 当前热点题材状态")
        print("=" * 50)
        
        ranking = self.get_heat_ranking()
        for i, item in enumerate(ranking, 1):
            status = "🔥" if item['heat_score'] >= 80 else "⭐" if item['heat_score'] >= 60 else "📍"
            remaining = f"{item['days_remaining']}天" if item['days_remaining'] < 999 else "持续"
            print(f"{i}. {status} {item['name']:<15} 热度:{item['heat_score']:<5} 权重:{item['weight']:.2f} 剩余:{remaining}")
        
        print("=" * 50)


# 便捷函数
def get_hot_topic_manager() -> HotTopicManager:
    """获取热点管理器单例"""
    if not hasattr(get_hot_topic_manager, '_instance'):
        get_hot_topic_manager._instance = HotTopicManager()
    return get_hot_topic_manager._instance
