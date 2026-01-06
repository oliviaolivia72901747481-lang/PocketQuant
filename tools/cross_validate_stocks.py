#!/usr/bin/env python3
"""
多源数据交叉验证工具

对指定股票使用多个数据源进行交叉验证，确保数据准确性

作者: Kiro
日期: 2026-01-06
"""

import sys
sys.path.insert(0, '.')

import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional
from config.tech_stock_pool import get_stock_name, get_stock_sector
from core.stock_screener.cross_source_validator import (
    CrossSourceValidator,
    MultiSourceCrossValidator,
    CrossValidationConfig,
    cross_validate_sources
)


class MultiSourceStockDataFetcher:
    """多源股票数据获取器"""
    
    def __init__(self):
        self.sources = {}
    
    def fetch_from_eastmoney(self, codes: List[str]) -> pd.DataFrame:
        """从东方财富获取数据 (stock_zh_a_spot_em)"""
        try:
            df = ak.stock_zh_a_spot_em()
            df = df[df['代码'].isin(codes)].copy()
            # 标准化列名
            df = df.rename(columns={
                '代码': 'code',
                '名称': 'name',
                '最新价': 'price',
                '涨跌幅': 'change_pct',
                '涨跌额': 'change',
                '成交量': 'volume',
                '成交额': 'turnover',
                '振幅': 'amplitude',
                '最高': 'high',
                '最低': 'low',
                '今开': 'open',
                '昨收': 'prev_close',
                '量比': 'volume_ratio',
                '换手率': 'turnover_rate',
                '市盈率-动态': 'pe_ratio',
                '市净率': 'pb_ratio',
                '总市值': 'total_market_cap',
                '流通市值': 'float_market_cap',
            })
            return df
        except Exception as e:
            print(f"东方财富数据获取失败: {e}")
            return pd.DataFrame()

    def fetch_from_sina(self, codes: List[str]) -> pd.DataFrame:
        """从新浪获取数据 (stock_zh_a_spot)"""
        try:
            # 新浪数据源
            df = ak.stock_zh_a_spot()
            df = df[df['代码'].isin(codes)].copy()
            # 标准化列名
            df = df.rename(columns={
                '代码': 'code',
                '名称': 'name',
                '最新价': 'price',
                '涨跌额': 'change',
                '涨跌幅': 'change_pct',
                '买入': 'bid',
                '卖出': 'ask',
                '昨收': 'prev_close',
                '今开': 'open',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume',
                '成交额': 'turnover',
            })
            return df
        except Exception as e:
            print(f"新浪数据获取失败: {e}")
            return pd.DataFrame()
    
    def fetch_from_tencent(self, codes: List[str]) -> pd.DataFrame:
        """从腾讯获取数据 (通过实时行情接口)"""
        try:
            # 使用另一个东方财富接口作为第三数据源
            results = []
            for code in codes:
                try:
                    # 获取个股实时行情
                    df_single = ak.stock_individual_info_em(symbol=code)
                    if df_single is not None and not df_single.empty:
                        # 转换为行格式
                        info_dict = {'code': code}
                        for _, row in df_single.iterrows():
                            key = row['item']
                            value = row['value']
                            if key == '总市值':
                                info_dict['total_market_cap'] = float(value) if value else 0
                            elif key == '流通市值':
                                info_dict['float_market_cap'] = float(value) if value else 0
                            elif key == '市盈率(动态)':
                                info_dict['pe_ratio'] = float(value) if value else 0
                            elif key == '市净率':
                                info_dict['pb_ratio'] = float(value) if value else 0
                        results.append(info_dict)
                except:
                    continue
            
            if results:
                return pd.DataFrame(results)
            return pd.DataFrame()
        except Exception as e:
            print(f"腾讯数据获取失败: {e}")
            return pd.DataFrame()
    
    def fetch_all_sources(self, codes: List[str]) -> Dict[str, pd.DataFrame]:
        """获取所有数据源的数据"""
        sources = {}
        
        print("📡 正在从多个数据源获取数据...")
        
        # 东方财富
        print("  - 获取东方财富数据...")
        df_em = self.fetch_from_eastmoney(codes)
        if not df_em.empty:
            sources['东方财富'] = df_em
            print(f"    ✅ 获取到 {len(df_em)} 条记录")
        
        # 新浪
        print("  - 获取新浪数据...")
        df_sina = self.fetch_from_sina(codes)
        if not df_sina.empty:
            sources['新浪财经'] = df_sina
            print(f"    ✅ 获取到 {len(df_sina)} 条记录")
        
        # 个股详情（作为第三数据源）
        print("  - 获取个股详情数据...")
        df_detail = self.fetch_from_tencent(codes)
        if not df_detail.empty:
            sources['个股详情'] = df_detail
            print(f"    ✅ 获取到 {len(df_detail)} 条记录")
        
        return sources


def cross_validate_stocks(codes: List[str]):
    """对指定股票进行多源数据交叉验证"""
    print("=" * 70)
    print("🔍 多源数据交叉验证")
    print(f"📅 验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📊 验证股票: {len(codes)} 只")
    print("=" * 70)
    
    # 获取多源数据
    fetcher = MultiSourceStockDataFetcher()
    sources = fetcher.fetch_all_sources(codes)
    
    if len(sources) < 2:
        print("\n❌ 数据源不足，无法进行交叉验证")
        return
    
    print(f"\n✅ 成功获取 {len(sources)} 个数据源")
    
    # 配置验证器
    config = CrossValidationConfig(
        numeric_tolerance=0.05,
        price_tolerance=0.02,
        min_match_rate=90.0,
        warning_match_rate=95.0,
        key_field='code',
        numeric_fields={
            'price': 0.02,
            'change_pct': 0.1,
            'volume': 0.15,
            'turnover': 0.15,
            'high': 0.02,
            'low': 0.02,
            'open': 0.02,
            'pe_ratio': 0.15,
            'pb_ratio': 0.15,
            'total_market_cap': 0.10,
            'float_market_cap': 0.10,
        }
    )
    
    # 创建多源验证器
    multi_validator = MultiSourceCrossValidator(config)
    
    # 执行验证
    print("\n" + "=" * 70)
    print("📋 交叉验证结果")
    print("=" * 70)
    
    reports = multi_validator.validate_all_sources(sources)
    
    # 输出详细报告
    for pair_name, report in reports.items():
        validator = CrossSourceValidator(config)
        print(validator.generate_report_text(report))
        print()
    
    # 输出汇总
    print(multi_validator.generate_summary_report(reports))
    
    # 输出每只股票的验证结果
    print("\n" + "=" * 70)
    print("📊 各股票数据一致性分析")
    print("=" * 70)
    
    # 获取主数据源
    main_source = sources.get('东方财富', list(sources.values())[0])
    
    for code in codes:
        name = get_stock_name(code)
        sector = get_stock_sector(code)
        
        print(f"\n【{code}】{name} ({sector})")
        
        # 检查各数据源中该股票的数据
        stock_data = {}
        for source_name, df in sources.items():
            if 'code' in df.columns:
                stock_row = df[df['code'] == code]
                if not stock_row.empty:
                    stock_data[source_name] = stock_row.iloc[0]
        
        if len(stock_data) < 2:
            print("  ⚠️ 数据源不足，无法验证")
            continue
        
        # 比较关键字段
        print("  数据源对比:")
        
        # 价格对比
        prices = []
        for source_name, row in stock_data.items():
            if 'price' in row.index and pd.notna(row['price']):
                prices.append((source_name, float(row['price'])))
        
        if len(prices) >= 2:
            price_values = [p[1] for p in prices]
            price_diff = (max(price_values) - min(price_values)) / np.mean(price_values) * 100
            status = "✅" if price_diff < 2 else "⚠️"
            print(f"  {status} 价格: ", end="")
            print(" | ".join([f"{name}: {price:.2f}" for name, price in prices]))
            print(f"      差异: {price_diff:.2f}%")
        
        # 涨跌幅对比
        changes = []
        for source_name, row in stock_data.items():
            if 'change_pct' in row.index and pd.notna(row['change_pct']):
                changes.append((source_name, float(row['change_pct'])))
        
        if len(changes) >= 2:
            change_values = [c[1] for c in changes]
            change_diff = max(change_values) - min(change_values)
            status = "✅" if abs(change_diff) < 0.5 else "⚠️"
            print(f"  {status} 涨跌幅: ", end="")
            print(" | ".join([f"{name}: {change:+.2f}%" for name, change in changes]))
            print(f"      差异: {change_diff:.2f}%")
        
        # PE对比
        pes = []
        for source_name, row in stock_data.items():
            if 'pe_ratio' in row.index and pd.notna(row['pe_ratio']) and row['pe_ratio'] > 0:
                pes.append((source_name, float(row['pe_ratio'])))
        
        if len(pes) >= 2:
            pe_values = [p[1] for p in pes]
            pe_diff = (max(pe_values) - min(pe_values)) / np.mean(pe_values) * 100
            status = "✅" if pe_diff < 15 else "⚠️"
            print(f"  {status} PE: ", end="")
            print(" | ".join([f"{name}: {pe:.1f}" for name, pe in pes]))
            print(f"      差异: {pe_diff:.1f}%")
        
        # 数据一致性评分
        consistency_score = 100
        if len(prices) >= 2 and price_diff > 2:
            consistency_score -= 20
        if len(changes) >= 2 and abs(change_diff) > 0.5:
            consistency_score -= 15
        if len(pes) >= 2 and pe_diff > 15:
            consistency_score -= 15
        
        if consistency_score >= 90:
            print(f"  📊 数据一致性: {consistency_score}分 ✅ 优秀")
        elif consistency_score >= 70:
            print(f"  📊 数据一致性: {consistency_score}分 ⚠️ 良好")
        else:
            print(f"  📊 数据一致性: {consistency_score}分 ❌ 需关注")
    
    # 总结
    print("\n" + "=" * 70)
    print("💡 验证总结")
    print("=" * 70)
    
    passed_count = sum(1 for r in reports.values() if r.is_valid)
    total_count = len(reports)
    
    if passed_count == total_count:
        print("✅ 所有数据源交叉验证通过，数据可信度高")
    elif passed_count > 0:
        print(f"⚠️ 部分数据源验证通过 ({passed_count}/{total_count})，建议以东方财富数据为准")
    else:
        print("❌ 数据源验证未通过，建议谨慎使用数据")
    
    print("\n建议:")
    print("  1. 价格差异<2%视为正常（不同数据源更新时间略有差异）")
    print("  2. 涨跌幅差异<0.5%视为正常")
    print("  3. PE差异<15%视为正常（计算方式可能略有不同）")
    print("  4. 如发现较大差异，建议以东方财富数据为主")


def main():
    """主函数"""
    # 待验证的5只股票
    stocks_to_validate = [
        "002185",  # 华天科技
        "000661",  # 长春高新
        "002273",  # 水晶光电
        "603169",  # 兰石重装
        "002241",  # 歌尔股份
    ]
    
    cross_validate_stocks(stocks_to_validate)


if __name__ == "__main__":
    main()
