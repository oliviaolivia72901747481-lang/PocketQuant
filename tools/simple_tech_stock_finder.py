#!/usr/bin/env python3
"""
简化版科技股发现工具

基于股票名称和行业关键词快速发现科技股
用于演示筛选策略的有效性

作者: 卓越股票分析师
日期: 2026-01-05
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import akshare as ak
import pandas as pd
from datetime import datetime
from typing import List, Dict, Tuple
from config.tech_stock_pool import get_tech_stock_pool


class SimpleTechStockFinder:
    """简化版科技股发现器"""
    
    def __init__(self):
        self.current_pool = get_tech_stock_pool()
        self.current_codes = set(self.current_pool.get_all_codes())
        
        # 科技关键词库 (更全面和精准)
        self.tech_keywords = {
            "半导体": [
                "芯片", "集成电路", "半导体", "晶圆", "封测", "IC", "电子", "微电子", 
                "光电", "传感器", "器件", "材料", "设备", "华创", "紫光", "韦尔", 
                "华天", "长电", "通富", "兆易", "北方", "中芯", "士兰微"
            ],
            "人工智能": [
                "智能", "AI", "机器人", "自动化", "算法", "数据", "云", "计算", 
                "视觉", "语音", "识别", "学习", "海康", "科大讯飞", "广联达",
                "同花顺", "奇安信", "深信服", "启明星辰"
            ],
            "通信技术": [
                "通信", "网络", "5G", "光纤", "基站", "射频", "天线", "信息", 
                "互联", "物联", "连接", "传输", "中兴", "烽火", "光迅", "新易盛",
                "中际旭创", "亨通", "长飞", "富通"
            ],
            "新能源": [
                "新能源", "锂电", "电池", "储能", "光伏", "风电", "充电", "能源", 
                "电力", "清洁", "绿色", "宁德", "比亚迪", "隆基", "通威", "阳光",
                "汇川", "麦格米特", "英威腾"
            ],
            "消费电子": [
                "电子", "手机", "显示", "屏幕", "摄像", "声学", "精密", "制造", 
                "组件", "配件", "硬件", "立讯", "歌尔", "蓝思", "欧菲", "大族",
                "信维", "水晶光电", "长盈", "领益", "工业富联"
            ],
            "软件服务": [
                "软件", "系统", "平台", "服务", "技术", "科技", "信息", "数字", 
                "互联网", "网络", "应用", "用友", "金蝶", "东软", "中软", "太极",
                "华宇", "超图", "四维图新", "科大国创"
            ],
            "生物医药": [
                "医疗", "生物", "医药", "健康", "诊断", "器械", "基因", "制药", 
                "医学", "临床", "迈瑞", "安图", "万孚", "理邦", "开立", "鱼跃",
                "乐普", "微创", "凯普", "达安"
            ],
            "智能制造": [
                "制造", "工业", "装备", "机械", "自动", "控制", "仪器", "测试", 
                "检测", "精密", "激光", "机器人", "汇川", "信捷", "雷赛", "埃斯顿",
                "拓斯达", "克来机电", "华中数控", "海得控制"
            ]
        }
    
    def find_tech_stocks(self) -> List[Dict]:
        """发现科技股"""
        print("🔍 开始发现科技股...")
        
        try:
            # 获取股票基本信息
            stock_info = ak.stock_zh_a_spot_em()
            
            # 筛选主板和中小板
            mainboard_stocks = stock_info[
                (stock_info['代码'].str.startswith('000')) |
                (stock_info['代码'].str.startswith('001')) |
                (stock_info['代码'].str.startswith('002')) |
                (stock_info['代码'].str.startswith('600')) |
                (stock_info['代码'].str.startswith('601')) |
                (stock_info['代码'].str.startswith('603'))
            ].copy()
            
            print(f"📊 扫描 {len(mainboard_stocks)} 只主板和中小板股票...")
            
            tech_stocks = []
            
            for _, stock in mainboard_stocks.iterrows():
                code = stock['代码']
                name = stock['名称']
                
                # 跳过已在股票池中的股票
                if code in self.current_codes:
                    continue
                
                # 基础筛选条件
                try:
                    market_cap = float(stock['总市值']) / 100000000  # 亿元
                    pe_ratio = float(stock['市盈率-动态']) if stock['市盈率-动态'] > 0 else 0
                    turnover_rate = float(stock['换手率'])
                    change_pct = float(stock['涨跌幅'])
                    
                    # 基础条件筛选 (更宽松)
                    if market_cap < 15 or turnover_rate < 0.05:  # 进一步降低门槛
                        continue
                    
                    # 科技属性评估
                    tech_score, tech_sector = self.evaluate_tech_attributes(name)
                    
                    if tech_score >= 20:  # 降低科技属性得分阈值
                        tech_stocks.append({
                            'code': code,
                            'name': name,
                            'sector': tech_sector,
                            'market_cap': market_cap,
                            'pe_ratio': pe_ratio,
                            'turnover_rate': turnover_rate,
                            'change_pct': change_pct,
                            'tech_score': tech_score
                        })
                
                except:
                    continue
            
            print(f"✅ 发现 {len(tech_stocks)} 只潜在科技股")
            return tech_stocks
            
        except Exception as e:
            print(f"❌ 获取数据失败: {e}")
            return []
    
    def evaluate_tech_attributes(self, stock_name: str) -> Tuple[float, str]:
        """评估股票的科技属性"""
        max_score = 0
        best_sector = "其他"
        
        name_lower = stock_name.lower()
        
        for sector, keywords in self.tech_keywords.items():
            score = 0
            
            for keyword in keywords:
                if keyword in name_lower:
                    # 根据关键词重要性给分
                    if keyword in ["芯片", "半导体", "AI", "智能", "5G", "新能源", "软件"]:
                        score += 20  # 核心关键词
                    else:
                        score += 10  # 一般关键词
            
            if score > max_score:
                max_score = score
                best_sector = sector
        
        return min(100, max_score), best_sector
    
    def display_results(self, tech_stocks: List[Dict]):
        """显示结果"""
        if not tech_stocks:
            print("❌ 未发现符合条件的科技股")
            return
        
        # 按科技得分排序
        tech_stocks.sort(key=lambda x: x['tech_score'], reverse=True)
        
        print(f"\n🏆 发现的科技股清单 (前50名)")
        print("=" * 100)
        
        # 按行业分组
        sector_groups = {}
        for stock in tech_stocks[:50]:
            sector = stock['sector']
            if sector not in sector_groups:
                sector_groups[sector] = []
            sector_groups[sector].append(stock)
        
        for sector, stocks in sector_groups.items():
            print(f"\n📊 {sector} ({len(stocks)}只)")
            print("-" * 80)
            print(f"{'代码':<8} {'名称':<15} {'市值(亿)':<10} {'PE':<8} {'换手率':<8} {'涨幅%':<8} {'科技得分':<8}")
            print("-" * 80)
            
            for stock in stocks:
                pe_str = f"{stock['pe_ratio']:.1f}" if stock['pe_ratio'] > 0 else "N/A"
                print(f"{stock['code']:<8} {stock['name']:<15} {stock['market_cap']:<10.1f} "
                      f"{pe_str:<8} {stock['turnover_rate']:<8.2f} {stock['change_pct']:<8.2f} "
                      f"{stock['tech_score']:<8.1f}")
        
        # 统计信息
        print(f"\n📊 统计信息:")
        print(f"   发现科技股总数: {len(tech_stocks)}")
        print(f"   平均科技得分: {sum(s['tech_score'] for s in tech_stocks) / len(tech_stocks):.1f}")
        print(f"   平均市值: {sum(s['market_cap'] for s in tech_stocks) / len(tech_stocks):.1f}亿元")
        
        print(f"\n🏭 行业分布:")
        for sector, count in sorted(
            [(k, len(v)) for k, v in sector_groups.items()], 
            key=lambda x: x[1], reverse=True
        ):
            print(f"   {sector}: {count}只")
    
    def generate_expansion_suggestions(self, tech_stocks: List[Dict], top_n: int = 30) -> List[Dict]:
        """生成扩充建议"""
        # 选择得分最高的股票
        top_stocks = sorted(tech_stocks, key=lambda x: x['tech_score'], reverse=True)[:top_n]
        
        # 行业平衡
        balanced_stocks = []
        sector_counts = {}
        max_per_sector = 5
        
        for stock in top_stocks:
            sector = stock['sector']
            if sector_counts.get(sector, 0) < max_per_sector:
                balanced_stocks.append(stock)
                sector_counts[sector] = sector_counts.get(sector, 0) + 1
        
        return balanced_stocks
    
    def save_expansion_report(self, suggestions: List[Dict]):
        """保存扩充报告"""
        report = f"""# 科技股池扩充建议报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**分析师**: 卓越股票分析师

## 扩充建议

基于关键词匹配和基础筛选，建议将以下股票纳入科技股池：

### 推荐股票清单

| 代码 | 名称 | 行业分类 | 市值(亿) | PE | 科技得分 | 推荐理由 |
|------|------|----------|----------|----|---------|---------|\n"""
        
        for stock in suggestions:
            pe_str = f"{stock['pe_ratio']:.1f}" if stock['pe_ratio'] > 0 else "N/A"
            reason = f"科技属性明显，属于{stock['sector']}领域"
            
            report += f"| {stock['code']} | {stock['name']} | {stock['sector']} | "
            report += f"{stock['market_cap']:.1f} | {pe_str} | {stock['tech_score']:.1f} | {reason} |\n"
        
        report += f"""
### 扩充效果预期

- **原股票池规模**: {len(self.current_codes)}只
- **建议新增**: {len(suggestions)}只  
- **扩充后规模**: {len(self.current_codes) + len(suggestions)}只

### 行业分布优化

"""
        
        # 统计行业分布
        sector_counts = {}
        for stock in suggestions:
            sector = stock['sector']
            sector_counts[sector] = sector_counts.get(sector, 0) + 1
        
        for sector, count in sorted(sector_counts.items(), key=lambda x: x[1], reverse=True):
            report += f"- **{sector}**: 新增{count}只\n"
        
        report += """
### 风险提示

1. 本报告基于股票名称关键词匹配，需要进一步验证业务实质
2. 建议结合财务数据和基本面分析进行最终筛选
3. 注意控制单一行业集中度风险
4. 定期评估和调整股票池构成

### 后续建议

1. 对推荐股票进行详细的财务分析
2. 评估各股票的流动性和交易活跃度
3. 考虑与现有股票池的协同效应
4. 建立动态调整机制
"""
        
        filename = f"TECH_STOCK_EXPANSION_SUGGESTIONS_{datetime.now().strftime('%Y%m%d')}.md"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\n📄 扩充建议报告已保存: {filename}")


def main():
    """主函数"""
    print("🚀 科技股发现与扩充建议系统")
    print(f"📅 运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🎯 目标: 基于关键词匹配发现潜在科技股")
    print("=" * 60)
    
    finder = SimpleTechStockFinder()
    
    # 发现科技股
    tech_stocks = finder.find_tech_stocks()
    
    if tech_stocks:
        # 显示结果
        finder.display_results(tech_stocks)
        
        # 生成扩充建议
        suggestions = finder.generate_expansion_suggestions(tech_stocks, top_n=40)
        
        print(f"\n💡 扩充建议: 推荐新增 {len(suggestions)} 只优质科技股")
        
        # 保存报告
        finder.save_expansion_report(suggestions)
        
        print(f"\n✅ 分析完成! 发现 {len(tech_stocks)} 只潜在科技股")
    else:
        print("\n❌ 未发现符合条件的科技股")


if __name__ == "__main__":
    main()