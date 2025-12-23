"""
硬性筛选器模块 - 小资金生存基础

对股票进行硬性筛选，过滤掉不符合小资金交易条件的股票。

筛选条件：
1. 股价 <= 80元（小资金可承受）
2. 50亿 <= 流通市值 <= 500亿（避免过大/过小）
3. 日均成交额 >= 1亿（保证流动性）

Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict
import pandas as pd
import logging

from config.tech_stock_config import get_tech_config

logger = logging.getLogger(__name__)


@dataclass
class HardFilterResult:
    """
    硬性筛选结果数据类
    
    Attributes:
        code: 股票代码
        name: 股票名称
        passed: 是否通过筛选
        price: 当前价格（元）
        market_cap: 流通市值（亿元）
        avg_turnover: 日均成交额（亿元）
        reject_reasons: 被拒绝的原因列表
    """
    code: str
    name: str
    passed: bool
    price: float
    market_cap: float
    avg_turnover: float
    reject_reasons: List[str] = field(default_factory=list)


class HardFilter:
    """
    硬性筛选器 - 小资金生存基础
    
    对股票进行硬性筛选，确保股票符合小资金交易条件。
    
    设计原则：
    - 股价限制：避免高价股占用过多资金
    - 市值限制：避免大盘股（流动性差）和小盘股（波动大）
    - 成交额限制：确保足够的流动性
    
    Requirements: 3.1, 3.2, 3.3, 3.4, 3.5
    """
    
    def __init__(self, data_feed=None):
        """
        初始化硬性筛选器
        
        Args:
            data_feed: 数据获取模块实例，用于获取股票数据
        """
        self.config = get_tech_config()
        
        # 从配置获取筛选阈值
        self.MAX_PRICE = self.config.hard_filter.max_price  # 80元
        self.MIN_MARKET_CAP = self.config.hard_filter.min_market_cap  # 50亿
        self.MAX_MARKET_CAP = self.config.hard_filter.max_market_cap  # 500亿
        self.MIN_AVG_TURNOVER = self.config.hard_filter.min_avg_turnover  # 1亿
        
        self._data_feed = data_feed

    def filter_stocks(
        self, 
        stock_codes: List[str],
        stock_data: Optional[Dict[str, Dict]] = None
    ) -> List[HardFilterResult]:
        """
        对股票列表进行硬性筛选
        
        筛选条件：
        1. 股价 <= 80元
        2. 50亿 <= 流通市值 <= 500亿
        3. 日均成交额 >= 1亿
        
        Args:
            stock_codes: 股票代码列表
            stock_data: 可选的股票数据字典，格式为:
                {
                    "code": {
                        "name": "股票名称",
                        "price": 当前价格,
                        "market_cap": 流通市值（亿元）,
                        "avg_turnover": 日均成交额（亿元）
                    }
                }
                如果为 None，则尝试从 data_feed 或 AkShare 获取
        
        Returns:
            筛选结果列表（包含通过和未通过的股票）
            
        Requirements: 3.1, 3.2, 3.3, 3.4, 3.5
        """
        results = []
        
        # 如果没有提供股票数据，尝试获取
        if stock_data is None:
            stock_data = self._get_stock_data_batch(stock_codes)
        
        for code in stock_codes:
            # 获取股票数据
            data = stock_data.get(code)
            
            if data is None:
                logger.warning(f"无法获取股票 {code} 的数据，跳过筛选")
                results.append(HardFilterResult(
                    code=code,
                    name=code,
                    passed=False,
                    price=0.0,
                    market_cap=0.0,
                    avg_turnover=0.0,
                    reject_reasons=["无法获取股票数据"]
                ))
                continue
            
            name = data.get("name", code)
            price = data.get("price", 0.0)
            market_cap = data.get("market_cap", 0.0)
            avg_turnover = data.get("avg_turnover", 0.0)
            
            # 执行筛选检查
            reject_reasons = []
            
            # 检查股价
            price_ok, price_reason = self._check_price(price)
            if not price_ok and price_reason:
                reject_reasons.append(price_reason)
            
            # 检查流通市值
            cap_ok, cap_reason = self._check_market_cap(market_cap)
            if not cap_ok and cap_reason:
                reject_reasons.append(cap_reason)
            
            # 检查日均成交额
            turnover_ok, turnover_reason = self._check_turnover(avg_turnover)
            if not turnover_ok and turnover_reason:
                reject_reasons.append(turnover_reason)
            
            # 综合判断
            passed = price_ok and cap_ok and turnover_ok
            
            results.append(HardFilterResult(
                code=code,
                name=name,
                passed=passed,
                price=price,
                market_cap=market_cap,
                avg_turnover=avg_turnover,
                reject_reasons=reject_reasons
            ))
            
            # 日志输出
            if passed:
                logger.debug(f"✓ {code} {name} 通过硬性筛选")
            else:
                logger.debug(f"✗ {code} {name} 未通过硬性筛选: {', '.join(reject_reasons)}")
        
        # 汇总日志
        passed_count = sum(1 for r in results if r.passed)
        logger.info(f"硬性筛选完成: {passed_count}/{len(results)} 只股票通过")
        
        return results

    def _check_price(self, price: float) -> Tuple[bool, Optional[str]]:
        """
        检查股价是否符合要求
        
        条件：股价 <= 80元
        
        Args:
            price: 当前股价（元）
        
        Returns:
            (是否通过, 拒绝原因)
            
        Requirements: 3.1
        """
        if price <= 0:
            return False, "股价数据无效"
        
        if price > self.MAX_PRICE:
            return False, f"股价 {price:.2f}元 > {self.MAX_PRICE}元"
        
        return True, None
    
    def _check_market_cap(self, market_cap: float) -> Tuple[bool, Optional[str]]:
        """
        检查流通市值是否符合要求
        
        条件：50亿 <= 流通市值 <= 500亿
        
        Args:
            market_cap: 流通市值（亿元）
        
        Returns:
            (是否通过, 拒绝原因)
            
        Requirements: 3.2, 3.3
        """
        if market_cap <= 0:
            return False, "流通市值数据无效"
        
        if market_cap < self.MIN_MARKET_CAP:
            return False, f"流通市值 {market_cap:.1f}亿 < {self.MIN_MARKET_CAP}亿"
        
        if market_cap > self.MAX_MARKET_CAP:
            return False, f"流通市值 {market_cap:.1f}亿 > {self.MAX_MARKET_CAP}亿"
        
        return True, None
    
    def _check_turnover(self, avg_turnover: float) -> Tuple[bool, Optional[str]]:
        """
        检查日均成交额是否符合要求
        
        条件：日均成交额 >= 1亿
        
        Args:
            avg_turnover: 日均成交额（亿元）
        
        Returns:
            (是否通过, 拒绝原因)
            
        Requirements: 3.4
        """
        if avg_turnover < 0:
            return False, "成交额数据无效"
        
        if avg_turnover < self.MIN_AVG_TURNOVER:
            return False, f"日均成交额 {avg_turnover:.2f}亿 < {self.MIN_AVG_TURNOVER}亿"
        
        return True, None
    
    def get_filter_summary(self, results: List[HardFilterResult]) -> Dict:
        """
        获取筛选汇总统计
        
        Args:
            results: 筛选结果列表
        
        Returns:
            统计汇总字典，包含：
            - total: 总数
            - passed: 通过数
            - rejected: 拒绝数
            - reject_by_price: 因股价被拒绝数
            - reject_by_market_cap: 因市值被拒绝数
            - reject_by_turnover: 因成交额被拒绝数
            
        Requirements: 3.6
        """
        passed = [r for r in results if r.passed]
        rejected = [r for r in results if not r.passed]
        
        # 统计各原因被拒绝的数量
        reject_by_price = len([
            r for r in rejected 
            if any("股价" in reason for reason in r.reject_reasons)
        ])
        reject_by_market_cap = len([
            r for r in rejected 
            if any("流通市值" in reason for reason in r.reject_reasons)
        ])
        reject_by_turnover = len([
            r for r in rejected 
            if any("成交额" in reason for reason in r.reject_reasons)
        ])
        reject_by_no_data = len([
            r for r in rejected 
            if any("无法获取" in reason or "无效" in reason for reason in r.reject_reasons)
        ])
        
        summary = {
            "total": len(results),
            "passed": len(passed),
            "rejected": len(rejected),
            "reject_by_price": reject_by_price,
            "reject_by_market_cap": reject_by_market_cap,
            "reject_by_turnover": reject_by_turnover,
            "reject_by_no_data": reject_by_no_data,
            "pass_rate": len(passed) / len(results) * 100 if results else 0.0
        }
        
        logger.info(
            f"筛选汇总: 总数 {summary['total']}, "
            f"通过 {summary['passed']} ({summary['pass_rate']:.1f}%), "
            f"拒绝 {summary['rejected']} "
            f"(股价: {reject_by_price}, 市值: {reject_by_market_cap}, "
            f"成交额: {reject_by_turnover}, 无数据: {reject_by_no_data})"
        )
        
        return summary

    def _get_stock_data_batch(self, codes: List[str]) -> Dict[str, Dict]:
        """
        批量获取股票数据
        
        优先从 data_feed 获取，失败时从 AkShare 实时行情获取
        
        Args:
            codes: 股票代码列表
        
        Returns:
            股票数据字典
        """
        result = {}
        
        # 尝试从 AkShare 实时行情获取
        try:
            import akshare as ak
            
            logger.info(f"从 AkShare 获取 {len(codes)} 只股票的实时数据...")
            df = ak.stock_zh_a_spot_em()
            
            if df is not None and not df.empty:
                for code in codes:
                    stock_row = df[df['代码'] == code]
                    if not stock_row.empty:
                        row = stock_row.iloc[0]
                        
                        # 流通市值：AkShare 返回的单位是元，转换为亿元
                        market_cap_yuan = row.get('流通市值', 0)
                        market_cap = market_cap_yuan / 1e8 if market_cap_yuan else 0.0
                        
                        # 成交额：AkShare 返回的单位是元，转换为亿元
                        turnover_yuan = row.get('成交额', 0)
                        avg_turnover = turnover_yuan / 1e8 if turnover_yuan else 0.0
                        
                        result[code] = {
                            "name": row.get('名称', code),
                            "price": float(row.get('最新价', 0) or 0),
                            "market_cap": market_cap,
                            "avg_turnover": avg_turnover
                        }
                
                logger.info(f"成功获取 {len(result)}/{len(codes)} 只股票的数据")
                return result
                
        except Exception as e:
            logger.warning(f"从 AkShare 获取实时数据失败: {e}")
        
        # 如果有 data_feed，尝试从历史数据计算
        if self._data_feed is not None:
            logger.info("尝试从历史数据计算...")
            for code in codes:
                if code in result:
                    continue
                    
                try:
                    df = self._data_feed.load_processed_data(code)
                    if df is not None and not df.empty:
                        # 使用最新收盘价
                        latest = df.iloc[-1]
                        price = float(latest['close'])
                        
                        # 计算5日平均成交额（需要成交额数据）
                        # 注意：processed_data 可能没有成交额，只有成交量
                        # 这里使用成交量 * 收盘价作为近似
                        if 'volume' in df.columns:
                            recent_5d = df.tail(5)
                            avg_volume = recent_5d['volume'].mean()
                            avg_price = recent_5d['close'].mean()
                            # 成交额 = 成交量 * 平均价格，转换为亿元
                            avg_turnover = (avg_volume * avg_price) / 1e8
                        else:
                            avg_turnover = 0.0
                        
                        result[code] = {
                            "name": code,
                            "price": price,
                            "market_cap": 0.0,  # 历史数据无法获取市值
                            "avg_turnover": avg_turnover
                        }
                except Exception as e:
                    logger.debug(f"从历史数据获取 {code} 失败: {e}")
        
        return result
    
    def get_passed_stocks(self, results: List[HardFilterResult]) -> List[str]:
        """
        获取通过筛选的股票代码列表
        
        Args:
            results: 筛选结果列表
        
        Returns:
            通过筛选的股票代码列表
        """
        return [r.code for r in results if r.passed]
    
    def get_rejected_stocks(self, results: List[HardFilterResult]) -> List[HardFilterResult]:
        """
        获取未通过筛选的股票列表
        
        Args:
            results: 筛选结果列表
        
        Returns:
            未通过筛选的 HardFilterResult 列表
        """
        return [r for r in results if not r.passed]
    
    def format_results_for_display(self, results: List[HardFilterResult]) -> pd.DataFrame:
        """
        将筛选结果格式化为 DataFrame，便于界面显示
        
        Args:
            results: 筛选结果列表
        
        Returns:
            格式化的 DataFrame
        """
        data = []
        for r in results:
            data.append({
                "代码": r.code,
                "名称": r.name,
                "通过": "✓" if r.passed else "✗",
                "股价(元)": f"{r.price:.2f}",
                "流通市值(亿)": f"{r.market_cap:.1f}",
                "日均成交额(亿)": f"{r.avg_turnover:.2f}",
                "拒绝原因": "; ".join(r.reject_reasons) if r.reject_reasons else "-"
            })
        
        return pd.DataFrame(data)
