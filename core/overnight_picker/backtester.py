"""
隔夜选股系统回测引擎 (OvernightBacktestEngine)

用于验证隔夜选股策略的历史表现，计算胜率、平均收益率等关键指标。

核心功能:
1. 模拟历史每日选股
2. 计算策略胜率（次日上涨比例）
3. 计算平均收益率
4. 支持不同时间段回测
5. 生成回测报告

Requirements: 12.1, 12.2, 12.3, 12.4, 12.5
"""

import os
import logging
from datetime import datetime, date, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class BacktestConfig:
    """
    回测配置
    
    包含回测所需的所有参数配置
    """
    start_date: str = ''                # 回测开始日期 (YYYY-MM-DD)
    end_date: str = ''                  # 回测结束日期 (YYYY-MM-DD)
    initial_capital: float = 70000.0    # 初始资金
    max_recommendations: int = 15       # 每日最多推荐股票数
    min_score: float = 70.0             # 最低评分阈值
    commission_rate: float = 0.0003     # 手续费率（万三）
    stamp_duty: float = 0.001           # 印花税率（千一，卖出时收取）
    slippage: float = 0.001             # 滑点（0.1%）
    hold_days: int = 1                  # 持有天数（默认T+1卖出）
    use_ideal_price: bool = True        # 是否使用理想买入价（否则使用开盘价）


@dataclass
class DailyPickResult:
    """
    单日选股结果
    
    记录某一天的选股和次日表现
    """
    pick_date: str                      # 选股日期
    trade_date: str                     # 交易日期（次日）
    stock_code: str                     # 股票代码
    stock_name: str                     # 股票名称
    score: float                        # 评分
    pick_close: float                   # 选股日收盘价
    ideal_price: float                  # 理想买入价
    acceptable_price: float             # 可接受买入价
    abandon_price: float                # 放弃买入价
    trade_open: float                   # 交易日开盘价
    trade_close: float                  # 交易日收盘价
    trade_high: float                   # 交易日最高价
    trade_low: float                    # 交易日最低价
    entry_price: float                  # 实际买入价
    exit_price: float                   # 实际卖出价
    return_pct: float                   # 收益率
    is_win: bool                        # 是否盈利
    is_executed: bool                   # 是否执行买入
    skip_reason: str = ''               # 跳过原因


@dataclass
class BacktestResult:
    """
    回测结果
    
    包含回测的所有绩效指标和详细数据
    """
    # 基本信息
    start_date: str                     # 回测开始日期
    end_date: str                       # 回测结束日期
    total_days: int                     # 总交易日数
    pick_days: int                      # 有选股的天数
    
    # 核心指标
    win_rate: float                     # 胜率（次日上涨比例）
    avg_return: float                   # 平均收益率
    total_return: float                 # 总收益率
    
    # 详细指标
    total_picks: int                    # 总选股次数
    executed_picks: int                 # 实际执行次数
    win_count: int                      # 盈利次数
    loss_count: int                     # 亏损次数
    avg_win: float                      # 平均盈利
    avg_loss: float                     # 平均亏损
    max_win: float                      # 最大单次盈利
    max_loss: float                     # 最大单次亏损
    profit_factor: float                # 盈亏比
    
    # 按评分分组统计
    score_group_stats: Dict[str, Dict] = field(default_factory=dict)
    
    # 详细记录
    daily_results: List[DailyPickResult] = field(default_factory=list)
    
    # 资金曲线
    equity_curve: pd.DataFrame = field(default_factory=pd.DataFrame)


class OvernightBacktestEngine:
    """
    隔夜选股回测引擎
    
    模拟历史每日选股，验证策略有效性
    
    使用流程:
    ```python
    engine = OvernightBacktestEngine(config)
    result = engine.run()
    print(result.win_rate, result.avg_return)
    ```
    
    Requirements: 12.1
    """
    
    def __init__(self, 
                 config: BacktestConfig = None,
                 data_path: str = "data/processed",
                 stock_pool: List[str] = None):
        """
        初始化回测引擎
        
        Args:
            config: 回测配置
            data_path: 数据文件路径
            stock_pool: 股票池列表
        """
        self.config = config or BacktestConfig()
        self.data_path = data_path
        
        # 初始化股票池
        self.stock_pool = stock_pool or self._load_stock_pool()
        
        # 数据缓存
        self._stock_data_cache: Dict[str, pd.DataFrame] = {}
        
        # 交易日历
        self._trading_days: List[str] = []
        
        logger.info(f"回测引擎初始化: 股票池={len(self.stock_pool)}只")
    
    def _load_stock_pool(self) -> List[str]:
        """加载股票池"""
        try:
            from config.stock_pool import STOCK_POOL
            return STOCK_POOL
        except ImportError:
            pass
        
        if os.path.exists(self.data_path):
            codes = []
            for f in os.listdir(self.data_path):
                if f.endswith('.csv'):
                    code = f.replace('.csv', '')
                    codes.append(code)
            return codes
        
        return []
    
    def load_stock_data(self, code: str) -> Optional[pd.DataFrame]:
        """
        加载单只股票数据
        
        Args:
            code: 股票代码
        
        Returns:
            DataFrame 或 None
        """
        if code in self._stock_data_cache:
            return self._stock_data_cache[code]
        
        file_path = os.path.join(self.data_path, f"{code}.csv")
        
        if not os.path.exists(file_path):
            return None
        
        try:
            df = pd.read_csv(file_path)
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').reset_index(drop=True)
            
            # 计算技术指标
            df = self._calculate_indicators(df)
            
            self._stock_data_cache[code] = df
            return df
        except Exception as e:
            logger.warning(f"加载数据失败: {code}, 错误: {e}")
            return None
    
    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算技术指标"""
        if df is None or df.empty:
            return df
        
        df = df.copy()
        
        # 均线
        df['ma5'] = df['close'].rolling(window=5).mean()
        df['ma10'] = df['close'].rolling(window=10).mean()
        df['ma20'] = df['close'].rolling(window=20).mean()
        df['ma60'] = df['close'].rolling(window=60).mean()
        
        # 成交量均线
        df['ma5_vol'] = df['volume'].rolling(window=5).mean()
        df['ma10_vol'] = df['volume'].rolling(window=10).mean()
        
        # 涨跌幅
        df['change_pct'] = df['close'].pct_change()
        
        # 波动率
        df['amplitude'] = (df['high'] - df['low']) / df['close'].shift(1)
        df['volatility'] = df['amplitude'].rolling(window=5).mean()
        
        return df
    
    def _build_trading_calendar(self) -> List[str]:
        """
        构建交易日历
        
        从数据中提取所有交易日
        """
        all_dates = set()
        
        for code in self.stock_pool[:10]:  # 使用前10只股票构建日历
            df = self.load_stock_data(code)
            if df is not None and not df.empty:
                dates = df['date'].dt.strftime('%Y-%m-%d').tolist()
                all_dates.update(dates)
        
        trading_days = sorted(list(all_dates))
        return trading_days
    
    def _get_next_trading_day(self, current_date: str) -> Optional[str]:
        """获取下一个交易日"""
        if not self._trading_days:
            self._trading_days = self._build_trading_calendar()
        
        try:
            idx = self._trading_days.index(current_date)
            if idx + 1 < len(self._trading_days):
                return self._trading_days[idx + 1]
        except ValueError:
            pass
        
        return None
    
    def _get_stock_data_on_date(self, code: str, target_date: str) -> Optional[Dict]:
        """
        获取股票在指定日期的数据
        
        Args:
            code: 股票代码
            target_date: 目标日期
        
        Returns:
            数据字典或None
        """
        df = self.load_stock_data(code)
        if df is None or df.empty:
            return None
        
        target_dt = pd.to_datetime(target_date)
        row = df[df['date'] == target_dt]
        
        if row.empty:
            return None
        
        row = row.iloc[0]
        
        # 获取前一天数据
        idx = df[df['date'] == target_dt].index[0]
        prev_row = df.iloc[idx - 1] if idx > 0 else row
        
        return {
            'date': target_date,
            'open': row['open'],
            'high': row['high'],
            'low': row['low'],
            'close': row['close'],
            'volume': row['volume'],
            'prev_close': prev_row['close'],
            'ma5': row.get('ma5', row['close']),
            'ma10': row.get('ma10', row['close']),
            'ma20': row.get('ma20', row['close']),
            'ma60': row.get('ma60', row['close']),
            'ma5_vol': row.get('ma5_vol', row['volume']),
            'volatility': row.get('volatility', 0.05),
        }
    
    def _score_stock_on_date(self, code: str, pick_date: str) -> Optional[Tuple[float, Dict]]:
        """
        对股票在指定日期进行评分
        
        Args:
            code: 股票代码
            pick_date: 选股日期
        
        Returns:
            (评分, 详情) 或 None
        """
        from .scorer import TomorrowPotentialScorer
        
        data = self._get_stock_data_on_date(code, pick_date)
        if data is None:
            return None
        
        scorer = TomorrowPotentialScorer(total_capital=self.config.initial_capital)
        
        stock_data = {
            'code': code,
            'name': code,
            'open': data['open'],
            'high': data['high'],
            'low': data['low'],
            'close': data['close'],
            'prev_close': data['prev_close'],
            'volume': data['volume'],
            'ma5': data['ma5'],
            'ma10': data['ma10'],
            'ma20': data['ma20'],
            'ma60': data['ma60'],
            'ma5_vol': data['ma5_vol'],
            'ma10_vol': data.get('ma10_vol', data['ma5_vol']),
            'main_net_inflow': 0,
            'concepts': [],
            'sector': '',
            'sector_rank': 10,
            'sector_size': 50,
            'sector_change': 0,
            'sector_market_rank': 20,
            'has_breakout': False,
            'has_macd_golden': False,
            'has_ma_golden': False,
        }
        
        total_score, details = scorer.score_stock(stock_data, {})
        return total_score, details
    
    def _calculate_entry_prices(self, close: float, score: float, 
                                volatility: float = 0.05) -> Dict:
        """
        计算买入价格区间
        
        Args:
            close: 收盘价
            score: 评分
            volatility: 波动率
        
        Returns:
            买入价格字典
        """
        # 基础计算
        ideal_price = close * 0.98      # 低开2%
        acceptable_price = close * 1.01  # 高开1%以内
        abandon_price = close * 1.03     # 高开3%以上不追
        
        # 根据评分调整
        if score >= 85:
            acceptable_price = close * 1.02
            abandon_price = close * 1.04
        elif score < 75:
            acceptable_price = close * 1.00
            abandon_price = close * 1.02
        
        return {
            'ideal_price': round(ideal_price, 2),
            'acceptable_price': round(acceptable_price, 2),
            'abandon_price': round(abandon_price, 2),
        }
    
    def _simulate_trade(self, 
                        pick_date: str,
                        trade_date: str,
                        code: str,
                        score: float,
                        pick_data: Dict,
                        trade_data: Dict,
                        entry_prices: Dict) -> DailyPickResult:
        """
        模拟单次交易
        
        Args:
            pick_date: 选股日期
            trade_date: 交易日期
            code: 股票代码
            score: 评分
            pick_data: 选股日数据
            trade_data: 交易日数据
            entry_prices: 买入价格
        
        Returns:
            DailyPickResult
        """
        trade_open = trade_data['open']
        trade_close = trade_data['close']
        trade_high = trade_data['high']
        trade_low = trade_data['low']
        
        ideal_price = entry_prices['ideal_price']
        acceptable_price = entry_prices['acceptable_price']
        abandon_price = entry_prices['abandon_price']
        
        # 判断是否执行买入
        is_executed = True
        skip_reason = ''
        entry_price = 0.0
        
        # 检查开盘价是否超过放弃价
        if trade_open > abandon_price:
            is_executed = False
            skip_reason = f'开盘价{trade_open:.2f}超过放弃价{abandon_price:.2f}'
        else:
            # 确定买入价
            if self.config.use_ideal_price:
                # 使用理想价买入（如果开盘价低于理想价）
                if trade_open <= ideal_price:
                    entry_price = trade_open
                elif trade_low <= ideal_price:
                    entry_price = ideal_price
                elif trade_open <= acceptable_price:
                    entry_price = trade_open
                else:
                    entry_price = trade_open
            else:
                # 直接使用开盘价
                entry_price = trade_open
            
            # 加入滑点
            entry_price = entry_price * (1 + self.config.slippage)
        
        # 计算收益
        if is_executed:
            # 默认收盘卖出
            exit_price = trade_close * (1 - self.config.slippage)
            
            # 计算收益率（扣除手续费）
            buy_cost = entry_price * (1 + self.config.commission_rate)
            sell_revenue = exit_price * (1 - self.config.commission_rate - self.config.stamp_duty)
            return_pct = (sell_revenue - buy_cost) / buy_cost
            is_win = return_pct > 0
        else:
            exit_price = 0.0
            return_pct = 0.0
            is_win = False
        
        return DailyPickResult(
            pick_date=pick_date,
            trade_date=trade_date,
            stock_code=code,
            stock_name=code,
            score=score,
            pick_close=pick_data['close'],
            ideal_price=ideal_price,
            acceptable_price=acceptable_price,
            abandon_price=abandon_price,
            trade_open=trade_open,
            trade_close=trade_close,
            trade_high=trade_high,
            trade_low=trade_low,
            entry_price=entry_price,
            exit_price=exit_price,
            return_pct=return_pct,
            is_win=is_win,
            is_executed=is_executed,
            skip_reason=skip_reason,
        )


    def run_single_day(self, pick_date: str) -> List[DailyPickResult]:
        """
        运行单日选股模拟
        
        Args:
            pick_date: 选股日期
        
        Returns:
            当日选股结果列表
        
        Requirements: 12.1
        """
        results = []
        
        # 获取下一个交易日
        trade_date = self._get_next_trading_day(pick_date)
        if trade_date is None:
            logger.debug(f"无法获取{pick_date}的下一个交易日")
            return results
        
        # 对所有股票评分
        scored_stocks = []
        for code in self.stock_pool:
            try:
                result = self._score_stock_on_date(code, pick_date)
                if result is not None:
                    score, details = result
                    if score >= self.config.min_score:
                        scored_stocks.append({
                            'code': code,
                            'score': score,
                            'details': details,
                        })
            except Exception as e:
                logger.debug(f"评分失败 {code} on {pick_date}: {e}")
        
        # 按评分排序，取前N只
        scored_stocks.sort(key=lambda x: x['score'], reverse=True)
        top_stocks = scored_stocks[:self.config.max_recommendations]
        
        # 模拟交易
        for stock in top_stocks:
            code = stock['code']
            score = stock['score']
            
            # 获取选股日和交易日数据
            pick_data = self._get_stock_data_on_date(code, pick_date)
            trade_data = self._get_stock_data_on_date(code, trade_date)
            
            if pick_data is None or trade_data is None:
                continue
            
            # 计算买入价格
            entry_prices = self._calculate_entry_prices(
                close=pick_data['close'],
                score=score,
                volatility=pick_data.get('volatility', 0.05),
            )
            
            # 模拟交易
            result = self._simulate_trade(
                pick_date=pick_date,
                trade_date=trade_date,
                code=code,
                score=score,
                pick_data=pick_data,
                trade_data=trade_data,
                entry_prices=entry_prices,
            )
            
            results.append(result)
        
        return results
    
    def run(self) -> BacktestResult:
        """
        执行完整回测
        
        Returns:
            BacktestResult 回测结果
        
        Requirements: 12.1
        """
        logger.info("=" * 50)
        logger.info("开始执行隔夜选股回测...")
        logger.info(f"回测期间: {self.config.start_date} ~ {self.config.end_date}")
        logger.info("=" * 50)
        
        # 构建交易日历
        self._trading_days = self._build_trading_calendar()
        
        if not self._trading_days:
            logger.error("无法构建交易日历")
            return self._create_empty_result()
        
        # 过滤日期范围
        start_dt = pd.to_datetime(self.config.start_date) if self.config.start_date else None
        end_dt = pd.to_datetime(self.config.end_date) if self.config.end_date else None
        
        trading_days = []
        for day in self._trading_days:
            day_dt = pd.to_datetime(day)
            if start_dt and day_dt < start_dt:
                continue
            if end_dt and day_dt > end_dt:
                continue
            trading_days.append(day)
        
        if not trading_days:
            logger.error("指定日期范围内无交易日")
            return self._create_empty_result()
        
        logger.info(f"交易日数: {len(trading_days)}")
        
        # 逐日运行选股
        all_results: List[DailyPickResult] = []
        pick_days = 0
        
        for i, pick_date in enumerate(trading_days[:-1]):  # 最后一天无法交易
            if (i + 1) % 20 == 0:
                logger.info(f"回测进度: {i+1}/{len(trading_days)-1}")
            
            day_results = self.run_single_day(pick_date)
            
            if day_results:
                pick_days += 1
                all_results.extend(day_results)
        
        logger.info(f"回测完成: 共{len(all_results)}次选股")
        
        # 计算统计指标
        return self._calculate_metrics(
            all_results=all_results,
            total_days=len(trading_days) - 1,
            pick_days=pick_days,
        )
    
    def _calculate_metrics(self, 
                           all_results: List[DailyPickResult],
                           total_days: int,
                           pick_days: int) -> BacktestResult:
        """
        计算回测指标
        
        Args:
            all_results: 所有选股结果
            total_days: 总交易日数
            pick_days: 有选股的天数
        
        Returns:
            BacktestResult
        
        Requirements: 12.2, 12.3
        """
        if not all_results:
            return self._create_empty_result()
        
        # 筛选已执行的交易
        executed_results = [r for r in all_results if r.is_executed]
        
        if not executed_results:
            return BacktestResult(
                start_date=self.config.start_date,
                end_date=self.config.end_date,
                total_days=total_days,
                pick_days=pick_days,
                win_rate=0.0,
                avg_return=0.0,
                total_return=0.0,
                total_picks=len(all_results),
                executed_picks=0,
                win_count=0,
                loss_count=0,
                avg_win=0.0,
                avg_loss=0.0,
                max_win=0.0,
                max_loss=0.0,
                profit_factor=0.0,
                score_group_stats={},
                daily_results=all_results,
            )
        
        # 基本统计
        total_picks = len(all_results)
        executed_picks = len(executed_results)
        
        returns = [r.return_pct for r in executed_results]
        wins = [r for r in executed_results if r.is_win]
        losses = [r for r in executed_results if not r.is_win]
        
        win_count = len(wins)
        loss_count = len(losses)
        
        # 胜率
        win_rate = win_count / executed_picks if executed_picks > 0 else 0.0
        
        # 平均收益率
        avg_return = np.mean(returns) if returns else 0.0
        
        # 总收益率（假设等权重投资）
        total_return = np.sum(returns) / max(1, executed_picks / self.config.max_recommendations)
        
        # 平均盈利/亏损
        avg_win = np.mean([r.return_pct for r in wins]) if wins else 0.0
        avg_loss = np.mean([r.return_pct for r in losses]) if losses else 0.0
        
        # 最大盈利/亏损
        max_win = max([r.return_pct for r in wins]) if wins else 0.0
        max_loss = min([r.return_pct for r in losses]) if losses else 0.0
        
        # 盈亏比
        if avg_loss != 0:
            profit_factor = abs(avg_win / avg_loss)
        else:
            profit_factor = float('inf') if avg_win > 0 else 0.0
        
        # 按评分分组统计
        score_group_stats = self._calculate_score_group_stats(executed_results)
        
        # 生成资金曲线
        equity_curve = self._generate_equity_curve(executed_results)
        
        logger.info(f"胜率: {win_rate:.2%}")
        logger.info(f"平均收益率: {avg_return:.2%}")
        logger.info(f"总收益率: {total_return:.2%}")
        logger.info(f"盈亏比: {profit_factor:.2f}")
        
        return BacktestResult(
            start_date=self.config.start_date,
            end_date=self.config.end_date,
            total_days=total_days,
            pick_days=pick_days,
            win_rate=win_rate,
            avg_return=avg_return,
            total_return=total_return,
            total_picks=total_picks,
            executed_picks=executed_picks,
            win_count=win_count,
            loss_count=loss_count,
            avg_win=avg_win,
            avg_loss=avg_loss,
            max_win=max_win,
            max_loss=max_loss,
            profit_factor=profit_factor,
            score_group_stats=score_group_stats,
            daily_results=all_results,
            equity_curve=equity_curve,
        )
    
    def _calculate_score_group_stats(self, 
                                     results: List[DailyPickResult]) -> Dict[str, Dict]:
        """
        按评分分组统计
        
        Args:
            results: 已执行的交易结果
        
        Returns:
            分组统计字典
        """
        groups = {
            '90-100': [],
            '85-90': [],
            '80-85': [],
            '75-80': [],
            '70-75': [],
        }
        
        for r in results:
            if r.score >= 90:
                groups['90-100'].append(r)
            elif r.score >= 85:
                groups['85-90'].append(r)
            elif r.score >= 80:
                groups['80-85'].append(r)
            elif r.score >= 75:
                groups['75-80'].append(r)
            else:
                groups['70-75'].append(r)
        
        stats = {}
        for group_name, group_results in groups.items():
            if group_results:
                wins = [r for r in group_results if r.is_win]
                returns = [r.return_pct for r in group_results]
                
                stats[group_name] = {
                    'count': len(group_results),
                    'win_rate': len(wins) / len(group_results),
                    'avg_return': np.mean(returns),
                    'max_return': max(returns),
                    'min_return': min(returns),
                }
            else:
                stats[group_name] = {
                    'count': 0,
                    'win_rate': 0.0,
                    'avg_return': 0.0,
                    'max_return': 0.0,
                    'min_return': 0.0,
                }
        
        return stats
    
    def _generate_equity_curve(self, 
                               results: List[DailyPickResult]) -> pd.DataFrame:
        """
        生成资金曲线
        
        Args:
            results: 已执行的交易结果
        
        Returns:
            资金曲线DataFrame
        """
        if not results:
            return pd.DataFrame(columns=['date', 'value', 'return'])
        
        # 按交易日期分组
        daily_returns = {}
        for r in results:
            if r.trade_date not in daily_returns:
                daily_returns[r.trade_date] = []
            daily_returns[r.trade_date].append(r.return_pct)
        
        # 计算每日平均收益
        equity_data = []
        cumulative_value = self.config.initial_capital
        
        for trade_date in sorted(daily_returns.keys()):
            returns = daily_returns[trade_date]
            avg_daily_return = np.mean(returns)
            
            # 假设每日投入固定比例资金
            daily_pnl = cumulative_value * 0.8 * avg_daily_return  # 80%仓位
            cumulative_value += daily_pnl
            
            equity_data.append({
                'date': trade_date,
                'value': cumulative_value,
                'return': avg_daily_return,
            })
        
        return pd.DataFrame(equity_data)
    
    def _create_empty_result(self) -> BacktestResult:
        """创建空的回测结果"""
        return BacktestResult(
            start_date=self.config.start_date,
            end_date=self.config.end_date,
            total_days=0,
            pick_days=0,
            win_rate=0.0,
            avg_return=0.0,
            total_return=0.0,
            total_picks=0,
            executed_picks=0,
            win_count=0,
            loss_count=0,
            avg_win=0.0,
            avg_loss=0.0,
            max_win=0.0,
            max_loss=0.0,
            profit_factor=0.0,
            score_group_stats={},
            daily_results=[],
        )


    def generate_report(self, result: BacktestResult) -> str:
        """
        生成回测报告
        
        Args:
            result: 回测结果
        
        Returns:
            Markdown格式的回测报告
        
        Requirements: 12.5
        """
        lines = []
        lines.append("# 📊 隔夜选股策略回测报告")
        lines.append("")
        lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # 回测概览
        lines.append("## 📋 回测概览")
        lines.append("")
        lines.append("| 指标 | 数值 |")
        lines.append("|------|------|")
        lines.append(f"| 回测期间 | {result.start_date} ~ {result.end_date} |")
        lines.append(f"| 总交易日 | {result.total_days} |")
        lines.append(f"| 有选股天数 | {result.pick_days} |")
        lines.append(f"| 总选股次数 | {result.total_picks} |")
        lines.append(f"| 实际执行次数 | {result.executed_picks} |")
        lines.append("")
        
        # 核心指标
        lines.append("## 📈 核心指标")
        lines.append("")
        lines.append("| 指标 | 数值 | 说明 |")
        lines.append("|------|------|------|")
        
        # 胜率评级
        if result.win_rate >= 0.6:
            win_rate_icon = "🟢"
            win_rate_comment = "优秀"
        elif result.win_rate >= 0.5:
            win_rate_icon = "🟡"
            win_rate_comment = "良好"
        else:
            win_rate_icon = "🔴"
            win_rate_comment = "需改进"
        
        lines.append(f"| 胜率 | {win_rate_icon} {result.win_rate:.2%} | {win_rate_comment} |")
        lines.append(f"| 平均收益率 | {result.avg_return:.2%} | 单次交易平均收益 |")
        lines.append(f"| 总收益率 | {result.total_return:.2%} | 累计收益 |")
        lines.append(f"| 盈亏比 | {result.profit_factor:.2f} | 平均盈利/平均亏损 |")
        lines.append("")
        
        # 盈亏统计
        lines.append("## 💰 盈亏统计")
        lines.append("")
        lines.append("| 指标 | 数值 |")
        lines.append("|------|------|")
        lines.append(f"| 盈利次数 | {result.win_count} |")
        lines.append(f"| 亏损次数 | {result.loss_count} |")
        lines.append(f"| 平均盈利 | {result.avg_win:.2%} |")
        lines.append(f"| 平均亏损 | {result.avg_loss:.2%} |")
        lines.append(f"| 最大单次盈利 | {result.max_win:.2%} |")
        lines.append(f"| 最大单次亏损 | {result.max_loss:.2%} |")
        lines.append("")
        
        # 评分分组统计
        if result.score_group_stats:
            lines.append("## 📊 评分分组统计")
            lines.append("")
            lines.append("| 评分区间 | 次数 | 胜率 | 平均收益 | 最大收益 | 最小收益 |")
            lines.append("|----------|------|------|----------|----------|----------|")
            
            for group_name in ['90-100', '85-90', '80-85', '75-80', '70-75']:
                stats = result.score_group_stats.get(group_name, {})
                count = stats.get('count', 0)
                win_rate = stats.get('win_rate', 0)
                avg_ret = stats.get('avg_return', 0)
                max_ret = stats.get('max_return', 0)
                min_ret = stats.get('min_return', 0)
                
                lines.append(
                    f"| {group_name} | {count} | {win_rate:.1%} | "
                    f"{avg_ret:.2%} | {max_ret:.2%} | {min_ret:.2%} |"
                )
            lines.append("")
        
        # 策略建议
        lines.append("## 💡 策略建议")
        lines.append("")
        
        if result.win_rate >= 0.55 and result.avg_return > 0:
            lines.append("✅ 策略整体表现良好，可以考虑实盘应用")
        elif result.win_rate >= 0.5:
            lines.append("⚠️ 策略胜率尚可，建议优化选股条件")
        else:
            lines.append("❌ 策略胜率较低，需要重新调整参数")
        
        # 根据评分分组给出建议
        if result.score_group_stats:
            high_score_stats = result.score_group_stats.get('90-100', {})
            if high_score_stats.get('win_rate', 0) > result.win_rate:
                lines.append("")
                lines.append(f"📌 高分股(90-100分)胜率{high_score_stats.get('win_rate', 0):.1%}，"
                           f"建议提高评分阈值")
        
        lines.append("")
        
        # 风险提示
        lines.append("## ⚠️ 风险提示")
        lines.append("")
        lines.append("1. 回测结果基于历史数据，不代表未来表现")
        lines.append("2. 实盘交易存在滑点、流动性等额外风险")
        lines.append("3. 建议小仓位试验后再逐步加仓")
        lines.append("4. 严格执行止损纪律，控制单次亏损")
        lines.append("")
        
        return "\n".join(lines)
    
    def save_report(self, result: BacktestResult, 
                    output_dir: str = "data/backtest_reports") -> str:
        """
        保存回测报告
        
        Args:
            result: 回测结果
            output_dir: 输出目录
        
        Returns:
            保存的文件路径
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"overnight_backtest_{timestamp}.md"
        filepath = os.path.join(output_dir, filename)
        
        # 生成报告
        report = self.generate_report(result)
        
        # 保存
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"回测报告已保存: {filepath}")
        return filepath
    
    def save_details(self, result: BacktestResult,
                     output_dir: str = "data/backtest_reports") -> str:
        """
        保存详细交易记录
        
        Args:
            result: 回测结果
            output_dir: 输出目录
        
        Returns:
            保存的文件路径
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"overnight_backtest_details_{timestamp}.csv"
        filepath = os.path.join(output_dir, filename)
        
        # 转换为DataFrame
        records = []
        for r in result.daily_results:
            records.append({
                'pick_date': r.pick_date,
                'trade_date': r.trade_date,
                'stock_code': r.stock_code,
                'score': r.score,
                'pick_close': r.pick_close,
                'ideal_price': r.ideal_price,
                'acceptable_price': r.acceptable_price,
                'abandon_price': r.abandon_price,
                'trade_open': r.trade_open,
                'trade_close': r.trade_close,
                'entry_price': r.entry_price,
                'exit_price': r.exit_price,
                'return_pct': r.return_pct,
                'is_win': r.is_win,
                'is_executed': r.is_executed,
                'skip_reason': r.skip_reason,
            })
        
        df = pd.DataFrame(records)
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        
        logger.info(f"详细记录已保存: {filepath}")
        return filepath


# 便捷函数
def run_overnight_backtest(
    start_date: str = None,
    end_date: str = None,
    initial_capital: float = 70000,
    min_score: float = 70,
    max_recommendations: int = 15,
    data_path: str = "data/processed",
    stock_pool: List[str] = None,
    save_report: bool = True,
) -> BacktestResult:
    """
    便捷函数：运行隔夜选股回测
    
    Args:
        start_date: 开始日期
        end_date: 结束日期
        initial_capital: 初始资金
        min_score: 最低评分
        max_recommendations: 每日最多推荐数
        data_path: 数据路径
        stock_pool: 股票池
        save_report: 是否保存报告
    
    Returns:
        BacktestResult
    
    Requirements: 12.4
    """
    # 默认日期范围
    if end_date is None:
        end_date = date.today().strftime('%Y-%m-%d')
    if start_date is None:
        start_dt = date.today() - timedelta(days=30)
        start_date = start_dt.strftime('%Y-%m-%d')
    
    config = BacktestConfig(
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital,
        min_score=min_score,
        max_recommendations=max_recommendations,
    )
    
    engine = OvernightBacktestEngine(
        config=config,
        data_path=data_path,
        stock_pool=stock_pool,
    )
    
    result = engine.run()
    
    if save_report:
        engine.save_report(result)
        engine.save_details(result)
    
    return result


def quick_backtest(days: int = 30) -> BacktestResult:
    """
    快速回测（最近N天）
    
    Args:
        days: 回测天数
    
    Returns:
        BacktestResult
    """
    end_date = date.today().strftime('%Y-%m-%d')
    start_date = (date.today() - timedelta(days=days)).strftime('%Y-%m-%d')
    
    return run_overnight_backtest(
        start_date=start_date,
        end_date=end_date,
        save_report=False,
    )
