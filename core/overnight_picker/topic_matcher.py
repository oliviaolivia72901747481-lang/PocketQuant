"""
智能题材匹配器 (SmartTopicMatcher)

解决题材匹配僵化问题，智能识别真龙头与蹭热点股

功能:
1. 公司主营业务数据库 - 分析公司与题材的真实关联度
2. 历史龙头记录 - 记录每个题材的历史龙头
3. 龙头指数计算 - 涨停时间、封单量、连板天数、市场认可度
4. 龙头类型识别 - 真龙头、二线龙头、跟风股、蹭热点

Requirements: 3.1, 3.2, 3.3, 3.4
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from pathlib import Path


@dataclass
class CompanyBusiness:
    """公司主营业务信息"""
    code: str                          # 股票代码
    name: str                          # 股票名称
    main_business: str                 # 主营业务描述
    products: List[str]                # 主要产品/服务
    industry: str                      # 所属行业
    concepts: List[str]                # 概念标签
    keywords: List[str] = field(default_factory=list)  # 业务关键词


@dataclass
class LeaderRecord:
    """龙头记录"""
    code: str                          # 股票代码
    name: str                          # 股票名称
    topic: str                         # 题材名称
    date: str                          # 成为龙头的日期
    leader_index: float                # 龙头指数
    leader_type: str                   # 龙头类型
    limit_up_time: str = ""            # 涨停时间
    seal_amount: float = 0             # 封单金额(万元)
    continuous_boards: int = 0         # 连板天数
    market_cap: float = 0              # 流通市值(亿元)


class SmartTopicMatcher:
    """
    智能题材匹配器 - 解决题材匹配僵化问题
    
    核心功能:
    1. 公司主营业务数据库 - 分析公司与题材的真实关联度
    2. 历史龙头记录 - 记录每个题材的历史龙头
    3. 龙头指数计算 - 涨停时间、封单量、连板天数、市场认可度
    4. 龙头类型识别 - 真龙头、二线龙头、跟风股、蹭热点
    """
    
    # 默认数据文件路径
    DEFAULT_BUSINESS_DB_PATH = "data/company_business.json"
    DEFAULT_LEADER_HISTORY_PATH = "data/leader_history.json"
    
    # 题材关键词映射 (用于匹配主营业务)
    TOPIC_KEYWORDS = {
        "AI人工智能": ["人工智能", "AI", "大模型", "机器学习", "深度学习", "算法", "智能", "ChatGPT", "语言模型"],
        "半导体": ["芯片", "半导体", "集成电路", "封测", "晶圆", "光刻", "存储", "GPU", "CPU", "MCU"],
        "CES科技展": ["消费电子", "VR", "AR", "XR", "智能穿戴", "眼镜", "头显", "元宇宙"],
        "人形机器人": ["机器人", "人形", "减速器", "伺服", "电机", "传感器", "关节", "执行器"],
        "低空经济": ["无人机", "飞行", "航空", "eVTOL", "空中", "通航", "飞控"],
        "新能源汽车": ["电动车", "新能源", "锂电池", "充电桩", "电池", "储能", "光伏"],
        "光伏储能": ["光伏", "太阳能", "储能", "逆变器", "组件", "硅片"],
        "医药生物": ["医药", "生物", "制药", "疫苗", "医疗", "器械", "诊断"],
        "军工": ["军工", "国防", "航天", "航空", "导弹", "雷达", "卫星"],
        "数字经济": ["数字", "数据", "云计算", "大数据", "信息化", "软件", "互联网"],
    }
    
    def __init__(self, 
                 business_db_path: str = None,
                 leader_history_path: str = None):
        """
        初始化智能题材匹配器
        
        Args:
            business_db_path: 公司主营业务数据库路径
            leader_history_path: 历史龙头记录路径
        """
        self.business_db_path = business_db_path or self.DEFAULT_BUSINESS_DB_PATH
        self.leader_history_path = leader_history_path or self.DEFAULT_LEADER_HISTORY_PATH
        
        # 公司主营业务数据库 {code: CompanyBusiness}
        self.company_business: Dict[str, CompanyBusiness] = {}
        
        # 历史龙头记录 {topic: [LeaderRecord]}
        self.leader_history: Dict[str, List[LeaderRecord]] = {}
        
        # 加载数据
        self._load_business_db()
        self._load_leader_history()
    
    def _load_business_db(self):
        """加载公司主营业务数据库"""
        if os.path.exists(self.business_db_path):
            try:
                with open(self.business_db_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for code, info in data.items():
                    self.company_business[code] = CompanyBusiness(
                        code=code,
                        name=info.get('name', ''),
                        main_business=info.get('main_business', ''),
                        products=info.get('products', []),
                        industry=info.get('industry', ''),
                        concepts=info.get('concepts', []),
                        keywords=info.get('keywords', [])
                    )
            except Exception as e:
                print(f"⚠️ 加载公司业务数据库失败: {e}")
    
    def _load_leader_history(self):
        """加载历史龙头记录"""
        if os.path.exists(self.leader_history_path):
            try:
                with open(self.leader_history_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for topic, records in data.items():
                    self.leader_history[topic] = [
                        LeaderRecord(
                            code=r.get('code', ''),
                            name=r.get('name', ''),
                            topic=topic,
                            date=r.get('date', ''),
                            leader_index=r.get('leader_index', 0),
                            leader_type=r.get('leader_type', ''),
                            limit_up_time=r.get('limit_up_time', ''),
                            seal_amount=r.get('seal_amount', 0),
                            continuous_boards=r.get('continuous_boards', 0),
                            market_cap=r.get('market_cap', 0)
                        )
                        for r in records
                    ]
            except Exception as e:
                print(f"⚠️ 加载龙头历史记录失败: {e}")
    
    def _save_business_db(self):
        """保存公司主营业务数据库"""
        Path(self.business_db_path).parent.mkdir(parents=True, exist_ok=True)
        data = {
            code: asdict(info) 
            for code, info in self.company_business.items()
        }
        with open(self.business_db_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _save_leader_history(self):
        """保存历史龙头记录"""
        Path(self.leader_history_path).parent.mkdir(parents=True, exist_ok=True)
        data = {
            topic: [asdict(r) for r in records]
            for topic, records in self.leader_history.items()
        }
        with open(self.leader_history_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    
    def add_company_business(self, business: CompanyBusiness) -> bool:
        """
        添加公司主营业务信息
        
        Args:
            business: 公司主营业务信息
        
        Returns:
            是否添加成功
        """
        self.company_business[business.code] = business
        self._save_business_db()
        return True
    
    def get_company_business(self, code: str) -> Optional[CompanyBusiness]:
        """
        获取公司主营业务信息
        
        Args:
            code: 股票代码
        
        Returns:
            公司主营业务信息，不存在返回None
        """
        return self.company_business.get(code)
    
    def add_leader_record(self, record: LeaderRecord) -> bool:
        """
        添加龙头记录
        
        Args:
            record: 龙头记录
        
        Returns:
            是否添加成功
        """
        topic = record.topic
        if topic not in self.leader_history:
            self.leader_history[topic] = []
        
        # 检查是否已存在同一天的记录
        existing = [r for r in self.leader_history[topic] 
                   if r.code == record.code and r.date == record.date]
        if existing:
            # 更新现有记录
            idx = self.leader_history[topic].index(existing[0])
            self.leader_history[topic][idx] = record
        else:
            self.leader_history[topic].append(record)
        
        # 只保留最近30天的记录
        cutoff_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        self.leader_history[topic] = [
            r for r in self.leader_history[topic] if r.date >= cutoff_date
        ]
        
        self._save_leader_history()
        return True
    
    def get_topic_leaders(self, topic: str, days: int = 7) -> List[LeaderRecord]:
        """
        获取题材的历史龙头
        
        Args:
            topic: 题材名称
            days: 查询天数
        
        Returns:
            龙头记录列表
        """
        if topic not in self.leader_history:
            return []
        
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        records = [r for r in self.leader_history[topic] if r.date >= cutoff_date]
        
        # 按龙头指数排序
        records.sort(key=lambda x: x.leader_index, reverse=True)
        return records
    
    def match_topic_relevance(self, 
                              stock_code: str,
                              stock_name: str,
                              topic_name: str,
                              concepts: List[str] = None) -> float:
        """
        计算股票与题材的真实关联度
        
        不仅看名字，还看:
        - 公司主营业务描述
        - 公司产品/服务
        - 历史上该股与该题材的表现
        
        Args:
            stock_code: 股票代码
            stock_name: 股票名称
            topic_name: 题材名称
            concepts: 概念标签列表
        
        Returns:
            关联度 (0-1)
            - 1.0: 主营业务高度相关
            - 0.7: 有相关业务
            - 0.3: 名字相关但业务不相关(蹭热点)
            - 0.0: 完全无关
        """
        if concepts is None:
            concepts = []
        
        relevance = 0.0
        
        # 1. 检查公司主营业务数据库
        business = self.get_company_business(stock_code)
        if business:
            # 获取题材关键词
            topic_keywords = self.TOPIC_KEYWORDS.get(topic_name, [topic_name])
            
            # 检查主营业务匹配
            main_business_text = f"{business.main_business} {' '.join(business.products)}"
            keyword_matches = sum(1 for kw in topic_keywords if kw in main_business_text)
            
            if keyword_matches >= 3:
                relevance = 1.0  # 主营业务高度相关
            elif keyword_matches >= 1:
                relevance = 0.7  # 有相关业务
            
            # 检查行业匹配
            if business.industry and topic_name in business.industry:
                relevance = max(relevance, 0.8)
        
        # 2. 检查概念标签匹配
        if concepts:
            topic_keywords = self.TOPIC_KEYWORDS.get(topic_name, [topic_name])
            concept_text = ' '.join(concepts)
            concept_matches = sum(1 for kw in topic_keywords if kw in concept_text)
            
            if concept_matches >= 2:
                relevance = max(relevance, 0.8)
            elif concept_matches >= 1:
                relevance = max(relevance, 0.5)
        
        # 3. 检查股票名称匹配 (可能是蹭热点)
        topic_keywords = self.TOPIC_KEYWORDS.get(topic_name, [topic_name])
        name_matches = sum(1 for kw in topic_keywords if kw in stock_name)
        
        if name_matches > 0 and relevance < 0.5:
            # 名字相关但业务不相关，可能是蹭热点
            relevance = 0.3
        
        # 4. 检查历史龙头记录
        leaders = self.get_topic_leaders(topic_name, days=30)
        for leader in leaders:
            if leader.code == stock_code:
                # 曾经是该题材龙头，提高关联度
                relevance = max(relevance, 0.9)
                break
        
        return round(relevance, 2)
    
    def calculate_leader_index(self,
                               stock_code: str,
                               limit_up_time: str = "",
                               seal_amount: float = 0,
                               market_cap: float = 0,
                               continuous_boards: int = 0,
                               follower_count: int = 0) -> float:
        """
        计算龙头指数
        
        Args:
            stock_code: 股票代码
            limit_up_time: 涨停时间 (如 "09:35")
            seal_amount: 封单金额 (万元)
            market_cap: 流通市值 (亿元)
            continuous_boards: 连板天数
            follower_count: 跟风股数量
        
        Returns:
            龙头指数 (0-100)
        
        计算逻辑:
        - 涨停时间 (30%): 9:30-10:00=30分, 10:00-11:00=20分, 午后=10分
        - 封单比例 (25%): 封单/市值 > 5%=25分, 3-5%=20分, 1-3%=15分
        - 连板天数 (25%): 3板以上=25分, 2板=20分, 首板=15分
        - 市场认可 (20%): 跟风股数量
        """
        score = 0.0
        
        # 1. 涨停时间评分 (30分)
        time_score = 0
        if limit_up_time:
            try:
                hour, minute = map(int, limit_up_time.split(':'))
                total_minutes = hour * 60 + minute
                
                if total_minutes <= 9 * 60 + 35:  # 9:35前
                    time_score = 30
                elif total_minutes <= 10 * 60:  # 10:00前
                    time_score = 25
                elif total_minutes <= 10 * 60 + 30:  # 10:30前
                    time_score = 20
                elif total_minutes <= 11 * 60 + 30:  # 上午
                    time_score = 15
                elif total_minutes <= 14 * 60:  # 14:00前
                    time_score = 10
                else:  # 尾盘
                    time_score = 5
            except (ValueError, AttributeError):
                time_score = 10  # 默认值
        
        score += time_score
        
        # 2. 封单比例评分 (25分)
        seal_score = 0
        if market_cap > 0 and seal_amount > 0:
            seal_ratio = seal_amount / (market_cap * 10000)  # 转换为比例
            
            if seal_ratio >= 0.05:  # 封单/市值 > 5%
                seal_score = 25
            elif seal_ratio >= 0.03:  # 3-5%
                seal_score = 20
            elif seal_ratio >= 0.01:  # 1-3%
                seal_score = 15
            elif seal_ratio > 0:
                seal_score = 10
        elif seal_amount > 10000:  # 封单金额大于1亿
            seal_score = 20
        elif seal_amount > 5000:  # 封单金额大于5000万
            seal_score = 15
        elif seal_amount > 1000:  # 封单金额大于1000万
            seal_score = 10
        
        score += seal_score
        
        # 3. 连板天数评分 (25分)
        board_score = 0
        if continuous_boards >= 5:
            board_score = 25
        elif continuous_boards >= 3:
            board_score = 22
        elif continuous_boards == 2:
            board_score = 18
        elif continuous_boards == 1:
            board_score = 15
        else:
            board_score = 5  # 非涨停
        
        score += board_score
        
        # 4. 市场认可度评分 (20分)
        follower_score = 0
        if follower_count >= 10:
            follower_score = 20
        elif follower_count >= 5:
            follower_score = 15
        elif follower_count >= 3:
            follower_score = 10
        elif follower_count >= 1:
            follower_score = 5
        
        score += follower_score
        
        return round(min(100, max(0, score)), 1)

    
    def identify_leader_type(self, 
                             leader_index: float, 
                             relevance: float) -> str:
        """
        识别龙头类型
        
        Args:
            leader_index: 龙头指数 (0-100)
            relevance: 题材关联度 (0-1)
        
        Returns:
            龙头类型:
            - "真龙头": 龙头指数>70 且 关联度>0.7
            - "二线龙头": 龙头指数50-70 且 关联度>0.5
            - "跟风股": 龙头指数30-50
            - "蹭热点": 关联度<0.3
        """
        # 先检查是否蹭热点
        if relevance < 0.3:
            return "蹭热点"
        
        # 根据龙头指数和关联度判断
        if leader_index >= 70 and relevance >= 0.7:
            return "真龙头"
        elif leader_index >= 50 and relevance >= 0.5:
            return "二线龙头"
        elif leader_index >= 30:
            return "跟风股"
        else:
            return "弱势股"
    
    def analyze_stock_topic(self,
                           stock_code: str,
                           stock_name: str,
                           topic_name: str,
                           concepts: List[str] = None,
                           limit_up_time: str = "",
                           seal_amount: float = 0,
                           market_cap: float = 0,
                           continuous_boards: int = 0,
                           follower_count: int = 0) -> Dict:
        """
        综合分析股票与题材的关系
        
        Args:
            stock_code: 股票代码
            stock_name: 股票名称
            topic_name: 题材名称
            concepts: 概念标签列表
            limit_up_time: 涨停时间
            seal_amount: 封单金额(万元)
            market_cap: 流通市值(亿元)
            continuous_boards: 连板天数
            follower_count: 跟风股数量
        
        Returns:
            分析结果字典
        """
        # 计算关联度
        relevance = self.match_topic_relevance(
            stock_code=stock_code,
            stock_name=stock_name,
            topic_name=topic_name,
            concepts=concepts
        )
        
        # 计算龙头指数
        leader_index = self.calculate_leader_index(
            stock_code=stock_code,
            limit_up_time=limit_up_time,
            seal_amount=seal_amount,
            market_cap=market_cap,
            continuous_boards=continuous_boards,
            follower_count=follower_count
        )
        
        # 识别龙头类型
        leader_type = self.identify_leader_type(leader_index, relevance)
        
        # 生成分析结果
        result = {
            'stock_code': stock_code,
            'stock_name': stock_name,
            'topic_name': topic_name,
            'relevance': relevance,
            'leader_index': leader_index,
            'leader_type': leader_type,
            'is_real_leader': leader_type == "真龙头",
            'is_fake_hot': leader_type == "蹭热点",
            'recommendation': self._get_recommendation(leader_type, leader_index, relevance),
            'details': {
                'limit_up_time': limit_up_time,
                'seal_amount': seal_amount,
                'market_cap': market_cap,
                'continuous_boards': continuous_boards,
                'follower_count': follower_count,
            }
        }
        
        return result
    
    def _get_recommendation(self, leader_type: str, leader_index: float, relevance: float) -> str:
        """
        根据龙头类型生成操作建议
        
        Args:
            leader_type: 龙头类型
            leader_index: 龙头指数
            relevance: 关联度
        
        Returns:
            操作建议
        """
        if leader_type == "真龙头":
            return "🔥 核心龙头，可重点关注，适合追涨或低吸"
        elif leader_type == "二线龙头":
            return "⭐ 二线龙头，可适当参与，注意控制仓位"
        elif leader_type == "跟风股":
            return "📍 跟风股，谨慎参与，建议等回调低吸"
        elif leader_type == "蹭热点":
            return "⚠️ 蹭热点股，主营业务与题材关联度低，建议回避"
        else:
            return "❌ 弱势股，不建议参与"
    
    def find_topic_leaders(self, 
                          topic_name: str,
                          stocks: List[Dict]) -> List[Dict]:
        """
        从股票列表中找出题材龙头
        
        Args:
            topic_name: 题材名称
            stocks: 股票列表，每个包含 {code, name, concepts, limit_up_time, seal_amount, market_cap, continuous_boards}
        
        Returns:
            按龙头指数排序的分析结果列表
        """
        results = []
        
        for stock in stocks:
            analysis = self.analyze_stock_topic(
                stock_code=stock.get('code', ''),
                stock_name=stock.get('name', ''),
                topic_name=topic_name,
                concepts=stock.get('concepts', []),
                limit_up_time=stock.get('limit_up_time', ''),
                seal_amount=stock.get('seal_amount', 0),
                market_cap=stock.get('market_cap', 0),
                continuous_boards=stock.get('continuous_boards', 0),
                follower_count=len(stocks) - 1  # 其他股票作为跟风
            )
            results.append(analysis)
        
        # 按龙头指数排序
        results.sort(key=lambda x: x['leader_index'], reverse=True)
        
        return results
    
    def record_today_leaders(self, 
                            topic_name: str,
                            leaders: List[Dict],
                            date: str = None) -> int:
        """
        记录今日龙头
        
        Args:
            topic_name: 题材名称
            leaders: 龙头分析结果列表
            date: 日期，默认今天
        
        Returns:
            记录的龙头数量
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        count = 0
        for leader in leaders:
            if leader.get('leader_type') in ['真龙头', '二线龙头']:
                record = LeaderRecord(
                    code=leader.get('stock_code', ''),
                    name=leader.get('stock_name', ''),
                    topic=topic_name,
                    date=date,
                    leader_index=leader.get('leader_index', 0),
                    leader_type=leader.get('leader_type', ''),
                    limit_up_time=leader.get('details', {}).get('limit_up_time', ''),
                    seal_amount=leader.get('details', {}).get('seal_amount', 0),
                    continuous_boards=leader.get('details', {}).get('continuous_boards', 0),
                    market_cap=leader.get('details', {}).get('market_cap', 0)
                )
                self.add_leader_record(record)
                count += 1
        
        return count
    
    def predict_tomorrow_leader(self, topic_name: str) -> Optional[Dict]:
        """
        预测明日龙头
        
        基于历史龙头记录，预测明日可能的龙头
        
        Args:
            topic_name: 题材名称
        
        Returns:
            预测结果，包含最可能的龙头股票
        """
        leaders = self.get_topic_leaders(topic_name, days=7)
        
        if not leaders:
            return None
        
        # 统计各股票出现次数和平均龙头指数
        stock_stats = {}
        for leader in leaders:
            code = leader.code
            if code not in stock_stats:
                stock_stats[code] = {
                    'code': code,
                    'name': leader.name,
                    'count': 0,
                    'total_index': 0,
                    'max_index': 0,
                    'latest_date': '',
                    'continuous_boards': 0
                }
            
            stock_stats[code]['count'] += 1
            stock_stats[code]['total_index'] += leader.leader_index
            stock_stats[code]['max_index'] = max(stock_stats[code]['max_index'], leader.leader_index)
            
            if leader.date > stock_stats[code]['latest_date']:
                stock_stats[code]['latest_date'] = leader.date
                stock_stats[code]['continuous_boards'] = leader.continuous_boards
        
        # 计算综合得分
        for code, stats in stock_stats.items():
            avg_index = stats['total_index'] / stats['count']
            # 综合得分 = 平均龙头指数 * 0.4 + 出现次数 * 10 * 0.3 + 连板天数 * 10 * 0.3
            stats['score'] = (
                avg_index * 0.4 + 
                min(stats['count'] * 10, 30) * 0.3 + 
                min(stats['continuous_boards'] * 10, 30) * 0.3
            )
            stats['avg_index'] = round(avg_index, 1)
        
        # 按综合得分排序
        sorted_stocks = sorted(stock_stats.values(), key=lambda x: x['score'], reverse=True)
        
        if sorted_stocks:
            top = sorted_stocks[0]
            return {
                'predicted_leader': {
                    'code': top['code'],
                    'name': top['name'],
                    'avg_leader_index': top['avg_index'],
                    'appearance_count': top['count'],
                    'continuous_boards': top['continuous_boards'],
                    'confidence': min(top['score'], 100)
                },
                'alternatives': [
                    {
                        'code': s['code'],
                        'name': s['name'],
                        'avg_leader_index': s['avg_index'],
                        'confidence': min(s['score'], 100)
                    }
                    for s in sorted_stocks[1:3]  # 备选龙头
                ],
                'topic': topic_name
            }
        
        return None
    
    def get_leader_index_score(self, leader_index: float, max_score: float = 12) -> Tuple[float, Dict]:
        """
        将龙头指数转换为评分
        
        用于与TomorrowPotentialScorer集成
        
        Args:
            leader_index: 龙头指数 (0-100)
            max_score: 最高分
        
        Returns:
            (评分, 详情)
        """
        # 龙头指数映射到评分
        if leader_index >= 80:
            score = max_score
            leader_type = "核心龙头"
        elif leader_index >= 60:
            score = max_score * 0.85
            leader_type = "二线龙头"
        elif leader_index >= 40:
            score = max_score * 0.6
            leader_type = "板块强势股"
        elif leader_index >= 20:
            score = max_score * 0.35
            leader_type = "跟风股"
        else:
            score = max_score * 0.1
            leader_type = "弱势股"
        
        return round(score, 1), {
            'score': round(score, 1),
            'max_score': max_score,
            'leader_index': leader_index,
            'leader_type': leader_type
        }


# 便捷函数
def get_smart_topic_matcher() -> SmartTopicMatcher:
    """获取智能题材匹配器单例"""
    if not hasattr(get_smart_topic_matcher, '_instance'):
        get_smart_topic_matcher._instance = SmartTopicMatcher()
    return get_smart_topic_matcher._instance
