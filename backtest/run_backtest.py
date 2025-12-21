"""
MiniQuant-Lite 回测引擎模块

基于 Backtrader 框架的回测引擎，提供：
- 策略回测执行
- 绩效指标计算（总收益率、年化收益率、最大回撤、夏普比率、胜率、Alpha）
- 沪深300基准对比
- 涨跌停板检测
- 资金曲线和交易明细生成

Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9
"""

from dataclasses import dataclass, field
from typing import Type, Optional, List, Dict, Any
from datetime import datetime, date, timedelta
import logging
import math

import backtrader as bt
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class BacktestConfig:
    """
    回测配置
    
    包含回测所需的所有参数配置
    
    Requirements: 3.1, 3.2
    """
    initial_cash: float = 55000.0      # 初始资金
    commission_rate: float = 0.0003    # 手续费率（万三）
    stamp_duty: float = 0.001          # 印花税率（千一，卖出时收取）
    start_date: str = '2023-01-01'     # 回测开始日期
    end_date: str = '2024-12-01'       # 回测结束日期
    benchmark_code: str = '000300'     # 基准指数代码（沪深300）
    check_limit_up_down: bool = True   # 是否检测涨跌停板
    slippage_perc: float = 0.001       # 滑点百分比（0.1%），模拟隔夜跳空和成交滑点
    min_commission: float = 5.0        # 最低手续费（5元低消）


@dataclass
class BacktestResult:
    """
    回测结果
    
    包含回测的所有绩效指标和详细数据
    
    Requirements: 3.3, 3.5, 3.6, 3.9
    """
    # 基本信息
    initial_value: float               # 初始资金
    final_value: float                 # 最终资金
    
    # 收益指标
    total_return: float                # 总收益率
    annual_return: float               # 年化收益率
    
    # 风险指标（小散户重点关注）
    max_drawdown: float                # 最大回撤
    sharpe_ratio: float                # 夏普比率
    
    # 基准对比
    benchmark_return: float            # 基准收益率（沪深300同期收益）
    alpha: float                       # 超额收益（策略收益 - 基准收益）
    
    # 交易统计
    trade_count: int                   # 交易次数
    win_rate: float                    # 胜率（小散户重点关注）
    profit_factor: float               # 盈亏比
    avg_win: float                     # 平均盈利
    avg_loss: float                    # 平均亏损
    
    # 详细数据
    equity_curve: pd.DataFrame = field(default_factory=pd.DataFrame)  # 资金曲线
    benchmark_curve: pd.DataFrame = field(default_factory=pd.DataFrame)  # 基准净值曲线
    trade_log: List[Dict[str, Any]] = field(default_factory=list)  # 交易明细（含止损/止盈原因）


class LimitUpDownChecker:
    """
    涨跌停板检测器
    
    检测是否为一字板（涨停/跌停），一字板时禁止交易，避免回测结果虚高
    
    Requirements: 3.7
    """
    
    @staticmethod
    def is_limit_up_down(open_price: float, high: float, low: float, close: float) -> bool:
        """
        检测是否为涨跌停一字板
        
        判断条件: open == close == high == low
        一字板时禁止交易，避免回测结果虚高
        
        Args:
            open_price: 开盘价
            high: 最高价
            low: 最低价
            close: 收盘价
        
        Returns:
            True 表示为一字板，应禁止交易
        """
        # 使用小数点精度比较（避免浮点数精度问题）
        tolerance = 0.001
        
        return (
            abs(open_price - close) < tolerance and
            abs(open_price - high) < tolerance and
            abs(open_price - low) < tolerance
        )


class CommissionScheme(bt.CommInfoBase):
    """
    A股佣金方案（含最低手续费）
    
    实现A股的佣金计算规则：
    - 买入：手续费（万三，最低5元）
    - 卖出：手续费（万三，最低5元）+ 印花税（千一）
    
    重要修复：
    - 正确实现5元最低手续费，避免小资金回测收益虚高
    - 小资金交易时，5元低消会显著影响实际费率
    
    Requirements: 3.2
    """
    
    params = (
        ('commission', 0.0003),      # 手续费率（小数形式，如 0.0003 表示万三）
        ('min_commission', 5.0),     # 最低手续费（5元低消）
        ('stamp_duty', 0.001),       # 印花税率
        ('stocklike', True),
        ('commtype', bt.CommInfoBase.COMM_FIXED),  # 使用固定佣金模式，我们自己计算
        ('percabs', True),           # 佣金为绝对值
    )
    
    def _getcommission(self, size, price, pseudoexec):
        """
        计算佣金（含最低手续费）
        
        核心公式：commission = max(trade_value * rate, min_commission)
        
        这是小资金回测准确性的关键！
        例如：交易金额 10000 元
        - 标准费用：10000 × 0.0003 = 3 元
        - 实际费用：max(3, 5) = 5 元
        - 实际费率：5 / 10000 = 0.05%（远高于标准 0.03%）
        
        Args:
            size: 交易数量（正数买入，负数卖出）
            price: 交易价格
            pseudoexec: 是否为模拟执行
        
        Returns:
            佣金金额
        """
        trade_value = abs(size * price)
        
        if trade_value == 0:
            return 0.0
        
        # 使用传入的 commission 参数（小数形式）
        commission_rate = self.p.commission
        min_comm = self.p.min_commission
        stamp = self.p.stamp_duty
        
        # 计算手续费（取标准费用和最低费用的较大值）
        # 这是关键修复：确保最低手续费生效
        standard_fee = trade_value * commission_rate
        commission = max(standard_fee, min_comm)
        
        # 卖出时加收印花税
        if size < 0:
            stamp_duty = trade_value * stamp
            commission += stamp_duty
        
        return commission



class EquityObserver(bt.Observer):
    """
    资金曲线观察器
    
    记录每日的账户价值，用于生成资金曲线
    """
    
    lines = ('value',)
    
    def next(self):
        self.lines.value[0] = self._owner.broker.getvalue()


class TradeAnalyzer(bt.Analyzer):
    """
    交易分析器
    
    记录所有交易的详细信息，包括止损/止盈原因
    """
    
    def __init__(self):
        self.trades = []
        self.current_trade = None
    
    def notify_trade(self, trade):
        """记录交易信息"""
        if trade.isclosed:
            # 获取策略的退出原因（如果有）
            exit_reason = ""
            if hasattr(self.strategy, 'exit_reasons') and self.strategy.exit_reasons:
                # 查找最近的退出原因
                for reason_info in reversed(self.strategy.exit_reasons):
                    if reason_info.get('exit_price') == trade.price:
                        exit_reason = reason_info.get('reason', '')
                        break
            
            trade_info = {
                'datetime': self.data.datetime.date(0),
                'code': trade.data._name if hasattr(trade.data, '_name') else 'unknown',
                'action': 'close',
                'entry_price': trade.price,
                'exit_price': trade.price + (trade.pnl / trade.size if trade.size != 0 else 0),
                'size': abs(trade.size),
                'pnl': trade.pnl,
                'pnlcomm': trade.pnlcomm,
                'commission': trade.commission,
                'exit_reason': exit_reason,
            }
            self.trades.append(trade_info)
    
    def get_analysis(self):
        return {'trades': self.trades}


class BacktestEngine:
    """
    回测引擎
    
    基于 Backtrader 框架的回测引擎，提供：
    - 策略回测执行
    - 绩效指标计算
    - 沪深300基准对比
    - 涨跌停板检测
    
    Requirements: 3.1, 3.2, 3.4, 3.7
    """
    
    def __init__(self, config: BacktestConfig):
        """
        初始化回测配置
        
        Args:
            config: 回测配置对象
        """
        self.config = config
        self.cerebro = bt.Cerebro()
        self.data_feeds = {}
        self.benchmark_data = None
        self.strategy_class = None
        self.strategy_kwargs = {}
        
        # 设置初始资金
        self.cerebro.broker.setcash(config.initial_cash)
        
        # 设置滑点（模拟隔夜跳空和成交滑点）
        if config.slippage_perc > 0:
            self.cerebro.broker.set_slippage_perc(
                perc=config.slippage_perc,
                slip_open=True,   # 开盘价也应用滑点
                slip_limit=True,  # 限价单也应用滑点
                slip_match=True,  # 匹配时应用滑点
                slip_out=False    # 不允许滑出当日价格范围
            )
            logger.info(f"滑点配置: {config.slippage_perc:.2%}")
        
        # 设置佣金方案（含最低手续费）
        commission_scheme = CommissionScheme(
            commission=config.commission_rate,
            min_commission=config.min_commission,
            stamp_duty=config.stamp_duty
        )
        self.cerebro.broker.addcommissioninfo(commission_scheme)
        
        # 添加分析器
        self.cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', riskfreerate=0.03)
        self.cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        self.cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        self.cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        self.cerebro.addanalyzer(TradeAnalyzer, _name='trade_log')
        
        # 添加观察器
        self.cerebro.addobserver(EquityObserver)
        
        logger.info(f"回测引擎初始化完成: 初始资金={config.initial_cash}, "
                   f"手续费率={config.commission_rate}, 最低手续费={config.min_commission}, "
                   f"印花税率={config.stamp_duty}, 滑点={config.slippage_perc:.2%}")
    
    def add_data(self, code: str, df: pd.DataFrame) -> None:
        """
        添加股票数据
        
        Args:
            code: 股票代码
            df: 股票数据 DataFrame，需包含 date, open, high, low, close, volume 列
        """
        if df is None or df.empty:
            logger.warning(f"股票 {code} 数据为空，跳过")
            return
        
        # 确保日期列为 datetime 类型
        df = df.copy()
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
        
        # 过滤日期范围
        start_date = pd.to_datetime(self.config.start_date)
        end_date = pd.to_datetime(self.config.end_date)
        df = df[(df.index >= start_date) & (df.index <= end_date)]
        
        if df.empty:
            logger.warning(f"股票 {code} 在指定日期范围内无数据")
            return
        
        # 创建 Backtrader 数据源
        data = bt.feeds.PandasData(
            dataname=df,
            datetime=None,  # 使用索引作为日期
            open='open',
            high='high',
            low='low',
            close='close',
            volume='volume',
            openinterest=-1
        )
        data._name = code
        
        self.cerebro.adddata(data)
        self.data_feeds[code] = data
        
        logger.info(f"添加股票数据: {code}, 共 {len(df)} 条记录")
    
    def load_benchmark(self, code: str = '000300') -> None:
        """
        加载基准指数数据（沪深300）
        
        用于计算超额收益和对比展示
        
        Args:
            code: 基准指数代码，默认 '000300'（沪深300）
        
        Requirements: 3.4
        """
        try:
            import akshare as ak
            
            # 转换日期格式
            start_date = self.config.start_date.replace('-', '')
            end_date = self.config.end_date.replace('-', '')
            
            logger.info(f"正在加载基准指数数据: {code}")
            
            # 获取沪深300指数数据
            df = ak.index_zh_a_hist(
                symbol=code,
                period="daily",
                start_date=start_date,
                end_date=end_date
            )
            
            if df is None or df.empty:
                logger.warning(f"基准指数 {code} 数据为空")
                return
            
            # 标准化列名
            df = df.rename(columns={
                '日期': 'date',
                '开盘': 'open',
                '最高': 'high',
                '最低': 'low',
                '收盘': 'close',
                '成交量': 'volume'
            })
            
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').reset_index(drop=True)
            
            self.benchmark_data = df
            logger.info(f"基准指数数据加载完成: {code}, 共 {len(df)} 条记录")
            
        except Exception as e:
            logger.error(f"加载基准指数数据失败: {e}")
            self.benchmark_data = None
    
    def set_strategy(
        self, 
        strategy_class: Type[bt.Strategy], 
        **kwargs
    ) -> None:
        """
        设置策略
        
        Args:
            strategy_class: 策略类
            **kwargs: 策略参数
        """
        self.strategy_class = strategy_class
        self.strategy_kwargs = kwargs
        self.cerebro.addstrategy(strategy_class, **kwargs)
        
        logger.info(f"设置策略: {strategy_class.__name__}")
    
    def set_sizer(self, sizer_class: Type[bt.Sizer], **kwargs) -> None:
        """
        设置仓位管理器
        
        Args:
            sizer_class: Sizer 类
            **kwargs: Sizer 参数
        """
        self.cerebro.addsizer(sizer_class, **kwargs)
        logger.info(f"设置仓位管理器: {sizer_class.__name__}")
    
    def _is_limit_up_down(self, data) -> bool:
        """
        检测是否为涨跌停一字板
        
        判断条件: open == close == high == low
        一字板时禁止交易，避免回测结果虚高
        
        Args:
            data: Backtrader 数据对象
        
        Returns:
            True 表示为一字板，应禁止交易
        
        Requirements: 3.7
        """
        return LimitUpDownChecker.is_limit_up_down(
            open_price=data.open[0],
            high=data.high[0],
            low=data.low[0],
            close=data.close[0]
        )
    
    def run(self) -> BacktestResult:
        """
        执行回测
        
        Returns:
            BacktestResult 回测结果对象
        """
        if not self.data_feeds:
            logger.error("未添加任何股票数据，无法执行回测")
            return self._create_empty_result()
        
        if self.strategy_class is None:
            logger.error("未设置策略，无法执行回测")
            return self._create_empty_result()
        
        logger.info("开始执行回测...")
        
        # 执行回测
        results = self.cerebro.run()
        
        if not results:
            logger.error("回测执行失败")
            return self._create_empty_result()
        
        strategy = results[0]
        
        # 计算绩效指标
        return self._calculate_metrics(strategy)
    
    def _create_empty_result(self) -> BacktestResult:
        """创建空的回测结果"""
        return BacktestResult(
            initial_value=self.config.initial_cash,
            final_value=self.config.initial_cash,
            total_return=0.0,
            annual_return=0.0,
            max_drawdown=0.0,
            sharpe_ratio=0.0,
            benchmark_return=0.0,
            alpha=0.0,
            trade_count=0,
            win_rate=0.0,
            profit_factor=0.0,
            avg_win=0.0,
            avg_loss=0.0,
            equity_curve=pd.DataFrame(),
            benchmark_curve=pd.DataFrame(),
            trade_log=[]
        )

    def _calculate_metrics(self, strategy) -> BacktestResult:
        """
        计算绩效指标（含基准对比）
        
        计算指标包括：
        - 总收益率、年化收益率
        - 最大回撤、夏普比率
        - 胜率、盈亏比
        - 超额收益 Alpha
        
        Args:
            strategy: 回测完成后的策略对象
        
        Returns:
            BacktestResult 回测结果对象
        
        Requirements: 3.3, 3.5, 3.6, 3.8, 3.9
        """
        # 获取基本信息
        initial_value = self.config.initial_cash
        final_value = self.cerebro.broker.getvalue()
        
        # 计算总收益率
        total_return = (final_value - initial_value) / initial_value
        
        # 计算年化收益率
        start_date = datetime.strptime(self.config.start_date, '%Y-%m-%d')
        end_date = datetime.strptime(self.config.end_date, '%Y-%m-%d')
        days = (end_date - start_date).days
        years = days / 365.0
        
        if years > 0 and total_return > -1:
            annual_return = (1 + total_return) ** (1 / years) - 1
        else:
            annual_return = 0.0
        
        # 获取分析器结果
        sharpe_analysis = strategy.analyzers.sharpe.get_analysis()
        drawdown_analysis = strategy.analyzers.drawdown.get_analysis()
        trades_analysis = strategy.analyzers.trades.get_analysis()
        trade_log_analysis = strategy.analyzers.trade_log.get_analysis()
        
        # 夏普比率
        sharpe_ratio = sharpe_analysis.get('sharperatio', 0.0)
        if sharpe_ratio is None or math.isnan(sharpe_ratio):
            sharpe_ratio = 0.0
        
        # 最大回撤
        max_drawdown = drawdown_analysis.get('max', {}).get('drawdown', 0.0)
        if max_drawdown is None:
            max_drawdown = 0.0
        max_drawdown = max_drawdown / 100.0  # 转换为小数
        
        # 交易统计
        trade_count = trades_analysis.get('total', {}).get('total', 0)
        
        # 计算胜率
        won_trades = trades_analysis.get('won', {}).get('total', 0)
        lost_trades = trades_analysis.get('lost', {}).get('total', 0)
        total_closed = won_trades + lost_trades
        win_rate = won_trades / total_closed if total_closed > 0 else 0.0
        
        # 计算平均盈利和平均亏损
        avg_win = trades_analysis.get('won', {}).get('pnl', {}).get('average', 0.0)
        avg_loss = trades_analysis.get('lost', {}).get('pnl', {}).get('average', 0.0)
        
        if avg_win is None:
            avg_win = 0.0
        if avg_loss is None:
            avg_loss = 0.0
        
        # 计算盈亏比
        if avg_loss != 0:
            profit_factor = abs(avg_win / avg_loss)
        else:
            profit_factor = float('inf') if avg_win > 0 else 0.0
        
        # 计算基准收益率
        benchmark_return = self._calculate_benchmark_return()
        
        # 计算超额收益 Alpha
        alpha = total_return - benchmark_return
        
        # 生成资金曲线
        equity_curve = self._generate_equity_curve(strategy)
        
        # 生成基准净值曲线
        benchmark_curve = self._generate_benchmark_curve()
        
        # 获取交易明细
        trade_log = trade_log_analysis.get('trades', [])
        
        # 如果策略有退出原因记录，合并到交易明细中
        if hasattr(strategy, 'exit_reasons'):
            trade_log = self._merge_exit_reasons(trade_log, strategy.exit_reasons)
        
        logger.info(f"回测完成: 总收益率={total_return:.2%}, 年化收益率={annual_return:.2%}, "
                   f"最大回撤={max_drawdown:.2%}, 夏普比率={sharpe_ratio:.2f}, "
                   f"胜率={win_rate:.2%}, Alpha={alpha:.2%}")
        
        return BacktestResult(
            initial_value=initial_value,
            final_value=final_value,
            total_return=total_return,
            annual_return=annual_return,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            benchmark_return=benchmark_return,
            alpha=alpha,
            trade_count=trade_count,
            win_rate=win_rate,
            profit_factor=profit_factor,
            avg_win=avg_win,
            avg_loss=avg_loss,
            equity_curve=equity_curve,
            benchmark_curve=benchmark_curve,
            trade_log=trade_log
        )
    
    def _calculate_benchmark_return(self) -> float:
        """
        计算基准收益率
        
        Returns:
            基准收益率（沪深300同期收益）
        """
        if self.benchmark_data is None or self.benchmark_data.empty:
            logger.warning("无基准数据，基准收益率设为0")
            return 0.0
        
        try:
            # 获取起止日期的收盘价
            start_price = self.benchmark_data.iloc[0]['close']
            end_price = self.benchmark_data.iloc[-1]['close']
            
            benchmark_return = (end_price - start_price) / start_price
            return benchmark_return
            
        except Exception as e:
            logger.error(f"计算基准收益率失败: {e}")
            return 0.0
    
    def _generate_equity_curve(self, strategy) -> pd.DataFrame:
        """
        生成资金曲线
        
        Args:
            strategy: 策略对象
        
        Returns:
            资金曲线 DataFrame，包含 date 和 value 列
        """
        try:
            # 从观察器获取资金曲线数据
            equity_data = []
            
            # 获取数据源的日期
            if self.data_feeds:
                first_data = list(self.data_feeds.values())[0]
                
                # 遍历策略的观察器获取资金曲线
                for observer in strategy.observers:
                    if isinstance(observer, EquityObserver):
                        for i in range(len(observer.lines.value)):
                            try:
                                dt = bt.num2date(first_data.datetime[i - len(observer.lines.value) + 1])
                                value = observer.lines.value[i - len(observer.lines.value) + 1]
                                equity_data.append({
                                    'date': dt.date(),
                                    'value': value
                                })
                            except Exception:
                                continue
            
            if equity_data:
                df = pd.DataFrame(equity_data)
                df = df.sort_values('date').reset_index(drop=True)
                return df
            
            return pd.DataFrame(columns=['date', 'value'])
            
        except Exception as e:
            logger.error(f"生成资金曲线失败: {e}")
            return pd.DataFrame(columns=['date', 'value'])
    
    def _generate_benchmark_curve(self) -> pd.DataFrame:
        """
        生成基准净值曲线
        
        Returns:
            基准净值曲线 DataFrame，包含 date 和 value 列
        """
        if self.benchmark_data is None or self.benchmark_data.empty:
            return pd.DataFrame(columns=['date', 'value'])
        
        try:
            # 计算净值（以第一天为基准1）
            df = self.benchmark_data[['date', 'close']].copy()
            initial_price = df.iloc[0]['close']
            df['value'] = df['close'] / initial_price
            df = df[['date', 'value']]
            
            return df
            
        except Exception as e:
            logger.error(f"生成基准净值曲线失败: {e}")
            return pd.DataFrame(columns=['date', 'value'])
    
    def _merge_exit_reasons(
        self, 
        trade_log: List[Dict], 
        exit_reasons: List[Dict]
    ) -> List[Dict]:
        """
        合并退出原因到交易明细
        
        Args:
            trade_log: 交易明细列表
            exit_reasons: 退出原因列表
        
        Returns:
            合并后的交易明细列表
        """
        if not exit_reasons:
            return trade_log
        
        # 创建退出原因索引（按日期和价格）
        reason_map = {}
        for reason in exit_reasons:
            key = (str(reason.get('datetime')), round(reason.get('exit_price', 0), 2))
            reason_map[key] = reason.get('reason', '')
        
        # 合并到交易明细
        for trade in trade_log:
            key = (str(trade.get('datetime')), round(trade.get('exit_price', 0), 2))
            if key in reason_map:
                trade['exit_reason'] = reason_map[key]
        
        return trade_log
    
    def plot(self, filename: str = None) -> None:
        """
        绘制回测结果图表
        
        Args:
            filename: 保存文件名，None 时显示图表
        """
        try:
            self.cerebro.plot(style='candlestick')
        except Exception as e:
            logger.error(f"绘制图表失败: {e}")


def run_backtest(
    stock_data: Dict[str, pd.DataFrame],
    strategy_class: Type[bt.Strategy],
    config: BacktestConfig = None,
    sizer_class: Type[bt.Sizer] = None,
    sizer_kwargs: Dict = None,
    strategy_kwargs: Dict = None,
    load_benchmark: bool = True
) -> BacktestResult:
    """
    便捷函数：执行回测
    
    Args:
        stock_data: 股票数据字典 {股票代码: DataFrame}
        strategy_class: 策略类
        config: 回测配置，None 时使用默认配置
        sizer_class: 仓位管理器类
        sizer_kwargs: 仓位管理器参数
        strategy_kwargs: 策略参数
        load_benchmark: 是否加载基准数据
    
    Returns:
        BacktestResult 回测结果
    """
    if config is None:
        config = BacktestConfig()
    
    if strategy_kwargs is None:
        strategy_kwargs = {}
    
    if sizer_kwargs is None:
        sizer_kwargs = {}
    
    # 创建回测引擎
    engine = BacktestEngine(config)
    
    # 添加股票数据
    for code, df in stock_data.items():
        engine.add_data(code, df)
    
    # 加载基准数据
    if load_benchmark:
        engine.load_benchmark(config.benchmark_code)
    
    # 设置策略
    engine.set_strategy(strategy_class, **strategy_kwargs)
    
    # 设置仓位管理器
    if sizer_class:
        engine.set_sizer(sizer_class, **sizer_kwargs)
    
    # 执行回测
    return engine.run()
