#!/usr/bin/env python3
"""
科技股池扩充至80-100只工具

基于现有筛选框架，系统性扩充科技股池
目标：将股票池从27只扩充至80-100只高质量主板和中小板科技股

作者: 卓越股票分析师
版本: 1.0
日期: 2026-01-05
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass, field

from config.tech_stock_pool import get_tech_stock_pool, TECH_STOCK_POOL


@dataclass
class ExpandedStock:
    """扩充股票数据结构"""
    code: str
    name: str
    sector: str
    market_cap: float = 0.0
    pe_ratio: float = 0.0
    tech_score: float = 0.0
    final_score: float = 0.0
    source: str = "screening"  # existing, screening, manual


class TechStockPoolExpansion:
    """科技股池扩充器 - 目标80-100只"""
    
    def __init__(self):
        """初始化扩充器"""
        self.current_pool = get_tech_stock_pool()
        self.current_codes = set(self.current_pool.get_all_codes())
        
        # 扩展的科技行业关键词库 - 更宽松的匹配
        self.tech_keywords = {
            "半导体": [
                "芯片", "集成电路", "半导体", "晶圆", "封测", "IC", 
                "功率器件", "模拟芯片", "存储", "处理器", "电子",
                "微电子", "光电", "显示", "LED", "OLED"
            ],
            "人工智能": [
                "人工智能", "AI", "机器学习", "深度学习", "算法", 
                "智能", "自动化", "机器人", "视觉", "语音",
                "数据", "云", "计算"
            ],
            "5G通信": [
                "5G", "通信", "基站", "光通信", "射频", "天线", 
                "光纤", "网络", "物联网", "信息", "电信",
                "移动", "联通", "电讯"
            ],
            "新能源科技": [
                "锂电", "储能", "光伏", "风电", "新能源", "电池",
                "充电", "氢能", "燃料电池", "智能电网", "太阳能",
                "清洁能源", "绿色能源"
            ],
            "消费电子": [
                "智能手机", "可穿戴", "电子元器件", "精密制造", "显示",
                "摄像头", "传感器", "连接器", "PCB", "声学",
                "电子", "科技", "数码", "智能家居"
            ],
            "软件服务": [
                "软件", "云计算", "大数据", "互联网", "SaaS", "数据库",
                "操作系统", "中间件", "企业软件", "信息安全", "网络安全",
                "信息技术", "IT", "系统集成"
            ],
            "生物医药科技": [
                "医疗器械", "体外诊断", "生物制药", "基因", "医疗",
                "数字医疗", "远程医疗", "医疗机器人", "精准医疗",
                "健康", "诊断", "检测", "制药"
            ],
            "智能制造": [
                "工业自动化", "机器人", "工业软件", "3D打印", "激光",
                "数控机床", "工业互联网", "MES", "智能装备",
                "自动化", "控制", "仪器", "仪表"
            ]
        }
        
        # 更宽松的筛选标准
        self.screening_criteria = {
            'min_market_cap': 20,      # 最小市值20亿
            'max_pe': 150,             # 最大PE 150倍
            'min_turnover': 0.2,       # 最小换手率0.2%
            'min_tech_score': 15       # 最小科技属性得分15分
        }
        
        self.expanded_stocks: List[ExpandedStock] = []
        
    def get_existing_stocks(self) -> List[ExpandedStock]:
        """获取现有股票池中的股票"""
        existing = []
        for sector, stocks in TECH_STOCK_POOL.items():
            for stock in stocks:
                existing.append(ExpandedStock(
                    code=stock["code"],
                    name=stock["name"],
                    sector=sector,
                    tech_score=100.0,
                    final_score=100.0,
                    source="existing"
                ))
        return existing
    
    def get_all_mainboard_stocks(self) -> pd.DataFrame:
        """获取所有主板和中小板股票"""
        print("📊 获取全市场主板和中小板股票...")
        
        try:
            stock_info = ak.stock_zh_a_spot_em()
            
            # 筛选主板和中小板股票
            mainboard_stocks = stock_info[
                (stock_info['代码'].str.startswith('000')) |
                (stock_info['代码'].str.startswith('001')) |
                (stock_info['代码'].str.startswith('002')) |
                (stock_info['代码'].str.startswith('600')) |
                (stock_info['代码'].str.startswith('601')) |
                (stock_info['代码'].str.startswith('603')) |
                (stock_info['代码'].str.startswith('605'))
            ].copy()
            
            # 排除ST股票
            mainboard_stocks = mainboard_stocks[
                ~mainboard_stocks['名称'].str.contains('ST|退', na=False)
            ]
            
            print(f"✅ 获取到 {len(mainboard_stocks)} 只主板和中小板股票")
            return mainboard_stocks
            
        except Exception as e:
            print(f"❌ 获取股票数据失败: {e}")
            return pd.DataFrame()
    
    def calculate_tech_score(self, stock_name: str, industry: str = "") -> Tuple[float, str]:
        """计算股票的科技属性得分"""
        max_score = 0
        best_sector = "其他"
        
        text_to_check = f"{stock_name} {industry}".lower()
        
        for sector, keywords in self.tech_keywords.items():
            score = 0
            
            for keyword in keywords:
                if keyword.lower() in text_to_check:
                    score += 10
            
            # 核心关键词加权
            core_keywords = keywords[:5]
            for keyword in core_keywords:
                if keyword.lower() in text_to_check:
                    score += 5
            
            if score > max_score:
                max_score = score
                best_sector = sector
        
        return min(100, max_score), best_sector
    
    def screen_new_candidates(self, stocks_df: pd.DataFrame, target_count: int = 80) -> List[ExpandedStock]:
        """筛选新的候选股票"""
        print(f"\n🔍 筛选新候选股票，目标: {target_count}只...")
        candidates = []
        
        for _, stock in stocks_df.iterrows():
            code = stock['代码']
            name = stock['名称']
            
            # 跳过已在股票池中的股票
            if code in self.current_codes:
                continue
            
            try:
                market_cap = float(stock['总市值']) / 100000000 if pd.notna(stock['总市值']) else 0
                pe_ratio = float(stock['市盈率-动态']) if pd.notna(stock['市盈率-动态']) and stock['市盈率-动态'] > 0 else 30
                turnover_rate = float(stock['换手率']) if pd.notna(stock['换手率']) else 0
                
                # 基础筛选
                if market_cap < self.screening_criteria['min_market_cap']:
                    continue
                if pe_ratio > self.screening_criteria['max_pe']:
                    continue
                if turnover_rate < self.screening_criteria['min_turnover']:
                    continue
                
                # 计算科技属性得分
                industry = stock.get('所属行业', '') if '所属行业' in stock else ''
                tech_score, tech_sector = self.calculate_tech_score(name, industry)
                
                if tech_score < self.screening_criteria['min_tech_score']:
                    continue
                
                # 计算综合得分
                final_score = self._calculate_final_score(
                    tech_score, market_cap, pe_ratio, turnover_rate
                )
                
                candidate = ExpandedStock(
                    code=code,
                    name=name,
                    sector=tech_sector,
                    market_cap=market_cap,
                    pe_ratio=pe_ratio,
                    tech_score=tech_score,
                    final_score=final_score,
                    source="screening"
                )
                
                candidates.append(candidate)
                
            except Exception as e:
                continue
        
        # 按综合得分排序
        candidates.sort(key=lambda x: x.final_score, reverse=True)
        
        print(f"✅ 找到 {len(candidates)} 只候选股票")
        return candidates
    
    def _calculate_final_score(self, tech_score: float, market_cap: float, 
                              pe_ratio: float, turnover_rate: float) -> float:
        """计算最终综合得分"""
        # 科技属性得分 (40%)
        tech_component = tech_score * 0.40
        
        # 市值得分 (20%) - 市值越大越好，但有上限
        cap_score = min(100, market_cap / 3)
        cap_component = cap_score * 0.20
        
        # 估值得分 (20%) - PE越低越好
        valuation_score = max(0, 100 - pe_ratio * 0.8)
        valuation_component = valuation_score * 0.20
        
        # 流动性得分 (20%)
        liquidity_score = min(100, turnover_rate * 15)
        liquidity_component = liquidity_score * 0.20
        
        return tech_component + cap_component + valuation_component + liquidity_component
    
    def balance_industry_distribution(self, candidates: List[ExpandedStock], 
                                     existing: List[ExpandedStock],
                                     target_total: int = 100) -> List[ExpandedStock]:
        """平衡行业分布"""
        print("\n⚖️ 平衡行业分布...")
        
        # 计算现有行业分布
        industry_counts = {}
        for stock in existing:
            industry_counts[stock.sector] = industry_counts.get(stock.sector, 0) + 1
        
        # 目标每个行业的股票数量
        num_industries = len(self.tech_keywords)
        target_per_industry = target_total // num_industries
        max_per_industry = int(target_total * 0.20)  # 单一行业最多20%
        
        # 需要新增的数量
        needed = target_total - len(existing)
        
        selected = []
        industry_added = {sector: 0 for sector in self.tech_keywords.keys()}
        
        # 按得分排序候选股票
        sorted_candidates = sorted(candidates, key=lambda x: x.final_score, reverse=True)
        
        # 第一轮：优先填充股票数量少的行业
        for candidate in sorted_candidates:
            if len(selected) >= needed:
                break
            
            sector = candidate.sector
            current_count = industry_counts.get(sector, 0) + industry_added.get(sector, 0)
            
            if current_count < target_per_industry:
                selected.append(candidate)
                industry_added[sector] = industry_added.get(sector, 0) + 1
        
        # 第二轮：按得分继续选择，但限制单一行业
        for candidate in sorted_candidates:
            if len(selected) >= needed:
                break
            
            if candidate in selected:
                continue
            
            sector = candidate.sector
            current_count = industry_counts.get(sector, 0) + industry_added.get(sector, 0)
            
            if current_count < max_per_industry:
                selected.append(candidate)
                industry_added[sector] = industry_added.get(sector, 0) + 1
        
        print(f"✅ 选择了 {len(selected)} 只新股票")
        return selected
    
    def expand_pool(self, target_count: int = 100) -> Tuple[List[ExpandedStock], Dict]:
        """执行股票池扩充"""
        print("🚀 开始科技股池扩充...")
        print(f"🎯 目标: 扩充至 {target_count} 只股票")
        print("=" * 60)
        
        # 1. 获取现有股票
        existing_stocks = self.get_existing_stocks()
        print(f"📌 现有股票池: {len(existing_stocks)} 只")
        
        # 2. 获取全市场股票
        all_stocks = self.get_all_mainboard_stocks()
        if all_stocks.empty:
            print("❌ 无法获取股票数据")
            return existing_stocks, {}
        
        # 3. 筛选新候选股票
        candidates = self.screen_new_candidates(all_stocks, target_count)
        
        # 4. 平衡行业分布
        selected_new = self.balance_industry_distribution(
            candidates, existing_stocks, target_count
        )
        
        # 5. 合并股票池
        final_pool = existing_stocks + selected_new
        
        # 6. 生成统计信息
        stats = self._generate_stats(final_pool, existing_stocks, selected_new)
        
        return final_pool, stats
    
    def _generate_stats(self, final_pool: List[ExpandedStock], 
                       existing: List[ExpandedStock],
                       new_stocks: List[ExpandedStock]) -> Dict:
        """生成统计信息"""
        # 行业分布
        industry_dist = {}
        for stock in final_pool:
            industry_dist[stock.sector] = industry_dist.get(stock.sector, 0) + 1
        
        return {
            'total_count': len(final_pool),
            'existing_count': len(existing),
            'new_count': len(new_stocks),
            'industry_distribution': industry_dist,
            'avg_tech_score': np.mean([s.tech_score for s in final_pool]),
            'avg_final_score': np.mean([s.final_score for s in final_pool])
        }
    
    def display_results(self, final_pool: List[ExpandedStock], stats: Dict):
        """显示扩充结果"""
        print(f"\n🏆 科技股池扩充结果")
        print("=" * 80)
        
        print(f"\n📊 总体统计:")
        print(f"   原有股票: {stats['existing_count']} 只")
        print(f"   新增股票: {stats['new_count']} 只")
        print(f"   扩充后总数: {stats['total_count']} 只")
        print(f"   平均科技得分: {stats['avg_tech_score']:.1f}")
        
        print(f"\n🏭 行业分布:")
        for industry, count in sorted(stats['industry_distribution'].items(), 
                                      key=lambda x: x[1], reverse=True):
            pct = count / stats['total_count'] * 100
            print(f"   {industry}: {count}只 ({pct:.1f}%)")
        
        # 按行业分组显示新增股票
        new_stocks = [s for s in final_pool if s.source == "screening"]
        if new_stocks:
            print(f"\n📈 新增股票清单 ({len(new_stocks)}只):")
            print("-" * 70)
            
            industry_groups = {}
            for stock in new_stocks:
                if stock.sector not in industry_groups:
                    industry_groups[stock.sector] = []
                industry_groups[stock.sector].append(stock)
            
            for industry, stocks in sorted(industry_groups.items()):
                print(f"\n【{industry}】({len(stocks)}只)")
                for stock in sorted(stocks, key=lambda x: x.final_score, reverse=True)[:10]:
                    print(f"   {stock.code} {stock.name:<12} "
                          f"市值:{stock.market_cap:.0f}亿 "
                          f"科技分:{stock.tech_score:.0f} "
                          f"综合分:{stock.final_score:.1f}")
    
    def generate_config_update(self, final_pool: List[ExpandedStock]) -> str:
        """生成配置文件更新内容"""
        # 按行业分组
        industry_groups = {}
        for stock in final_pool:
            if stock.sector not in industry_groups:
                industry_groups[stock.sector] = []
            industry_groups[stock.sector].append(stock)
        
        lines = [
            '"""',
            '科技股池配置模块',
            '',
            '提供科技股池的完整配置和管理功能，包括：',
            '- 八个科技行业的股票池',
            '- 股票池管理功能（添加、删除、筛选）',
            '- 行业分类查询',
            '',
            f'更新时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
            f'股票总数: {len(final_pool)}只',
            '',
            'Requirements: 12.1, 12.2, 12.3, 12.4',
            '"""',
            '',
            'from typing import Dict, List, Optional, Set',
            'from dataclasses import dataclass',
            '',
            '',
            '# ==========================================',
            '# 科技股池配置',
            '# ==========================================',
            '',
            '@dataclass',
            'class StockInfo:',
            '    """股票信息"""',
            '    code: str',
            '    name: str',
            '    sector: str',
            '    ',
            '    def to_dict(self) -> Dict[str, str]:',
            '        """转换为字典"""',
            '        return {',
            '            "code": self.code,',
            '            "name": self.name,',
            '            "sector": self.sector',
            '        }',
            '',
            '',
        ]
        
        # 生成各行业股票池
        sector_var_names = {
            "半导体": "SEMICONDUCTOR_STOCKS",
            "人工智能": "AI_APPLICATION_STOCKS", 
            "5G通信": "COMMUNICATION_STOCKS",
            "新能源科技": "NEW_ENERGY_TECH_STOCKS",
            "消费电子": "CONSUMER_ELECTRONICS_STOCKS",
            "软件服务": "SOFTWARE_SERVICE_STOCKS",
            "生物医药科技": "BIOMEDICAL_TECH_STOCKS",
            "智能制造": "SMART_MANUFACTURING_STOCKS",
            "AI应用": "AI_APPLICATION_STOCKS",
            "算力": "COMPUTING_POWER_STOCKS",
            "其他": "OTHER_TECH_STOCKS"
        }
        
        for sector, stocks in sorted(industry_groups.items()):
            var_name = sector_var_names.get(sector, f"{sector.upper()}_STOCKS")
            lines.append(f'# {sector}行业股票池')
            lines.append(f'{var_name} = [')
            for stock in sorted(stocks, key=lambda x: x.code):
                lines.append(f'    {{"code": "{stock.code}", "name": "{stock.name}"}},')
            lines.append(']')
            lines.append('')
        
        return '\n'.join(lines)


def main():
    """主函数"""
    print("🚀 科技股池扩充系统 - 目标80-100只")
    print(f"📅 运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 创建扩充器
    expander = TechStockPoolExpansion()
    
    # 执行扩充
    final_pool, stats = expander.expand_pool(target_count=100)
    
    if final_pool:
        # 显示结果
        expander.display_results(final_pool, stats)
        
        # 检查是否达到目标
        if stats['total_count'] >= 80:
            print(f"\n✅ 扩充成功! 股票池规模: {stats['total_count']}只 (目标: 80-100只)")
        else:
            print(f"\n⚠️ 扩充完成，但未达到目标。当前: {stats['total_count']}只")
        
        # 生成报告
        report_file = f"TECH_STOCK_POOL_EXPANSION_FINAL_{datetime.now().strftime('%Y%m%d')}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"# 科技股池扩充最终报告\n\n")
            f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"## 扩充结果\n\n")
            f.write(f"- 原有股票: {stats['existing_count']}只\n")
            f.write(f"- 新增股票: {stats['new_count']}只\n")
            f.write(f"- **扩充后总数: {stats['total_count']}只**\n\n")
            f.write(f"## 行业分布\n\n")
            f.write("| 行业 | 数量 | 占比 |\n")
            f.write("|------|------|------|\n")
            for industry, count in sorted(stats['industry_distribution'].items(), 
                                          key=lambda x: x[1], reverse=True):
                pct = count / stats['total_count'] * 100
                f.write(f"| {industry} | {count} | {pct:.1f}% |\n")
            
            f.write(f"\n## 新增股票清单\n\n")
            new_stocks = [s for s in final_pool if s.source == "screening"]
            
            # 按行业分组
            industry_groups = {}
            for stock in new_stocks:
                if stock.sector not in industry_groups:
                    industry_groups[stock.sector] = []
                industry_groups[stock.sector].append(stock)
            
            for industry, stocks in sorted(industry_groups.items()):
                f.write(f"\n### {industry} ({len(stocks)}只)\n\n")
                f.write("| 代码 | 名称 | 市值(亿) | 科技得分 | 综合得分 |\n")
                f.write("|------|------|----------|----------|----------|\n")
                for stock in sorted(stocks, key=lambda x: x.final_score, reverse=True):
                    f.write(f"| {stock.code} | {stock.name} | {stock.market_cap:.1f} | "
                           f"{stock.tech_score:.0f} | {stock.final_score:.1f} |\n")
        
        print(f"\n📄 报告已保存至: {report_file}")
        
        return final_pool, stats
    else:
        print("\n❌ 扩充失败")
        return [], {}


if __name__ == "__main__":
    main()
