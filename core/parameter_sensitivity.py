"""
MiniQuant-Lite 参数敏感性分析模块

提供策略鲁棒性评估能力：
- 参数网格定义与验证
- 网格搜索执行（复用 BacktestEngine）
- 热力图可视化
- 鲁棒性自动诊断

核心价值：将回测从"单次点估计"升级为"参数空间面估计"

Requirements: 参数敏感性分析 spec
"""

import math
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple, Optional, Callable, Type
from enum import Enum

import numpy as np
import pandas as pd
import plotly.graph_objects as go

try:
    import backtrader as bt
    HAS_BACKTRADER = True
except ImportError:
    HAS_BACKTRADER = False
    bt = None

logger = logging.getLogger(__name__)


# ============================================================
# 数据结构定义
# ============================================================

@dataclass
class ParameterRange:
    """
    单个参数的范围定义
    
    Attributes:
        name: 参数名称（如 'ma_period'）
        display_name: 显示名称（如 'MA 周期'）
        min_value: 最小值
        max_value: 最大值
        step: 步长
        default: 默认值（当前使用的值）
    """
    name: str
    display_name: str
    min_value: float
    max_value: float
    step: float
    default: float
    
    def get_values(self) -> List[float]:
        """获取该参数的所有取值"""
        if self.step <= 0:
            return [self.default]
        
        values = []
        current = self.min_value
        while current <= self.max_value + 1e-9:  # 浮点数精度容差
            values.append(round(current, 6))
            current += self.step
        return values
    
    def get_count(self) -> int:
        """获取取值个数"""
        if self.step <= 0:
            return 1
        return math.floor((self.max_value - self.min_value) / self.step) + 1
    
    def validate(self) -> Tuple[bool, str]:
        """
        验证参数范围有效性
        
        Returns:
            (是否有效, 错误信息)
        """
        if self.min_value >= self.max_value:
            return False, f"{self.display_name}: 最小值必须小于最大值"
        if self.step <= 0:
            return False, f"{self.display_name}: 步长必须大于0"
        return True, ""


@dataclass
class ParameterGrid:
    """
    参数网格（二维）
    
    Attributes:
        param_x: 横轴参数
        param_y: 纵轴参数
    """
    param_x: ParameterRange
    param_y: ParameterRange
    
    def get_x_values(self) -> List[float]:
        """获取横轴所有取值"""
        return self.param_x.get_values()
    
    def get_y_values(self) -> List[float]:
        """获取纵轴所有取值"""
        return self.param_y.get_values()
    
    def get_total_combinations(self) -> int:
        """获取总组合数"""
        return self.param_x.get_count() * self.param_y.get_count()
    
    def validate(self) -> Tuple[bool, str]:
        """验证参数网格有效性"""
        valid_x, msg_x = self.param_x.validate()
        if not valid_x:
            return False, msg_x
        
        valid_y, msg_y = self.param_y.validate()
        if not valid_y:
            return False, msg_y
        
        total = self.get_total_combinations()
        if total > 200:
            return False, f"组合数 {total} 超过上限 200，请缩小参数范围或增大步长"
        
        return True, ""


@dataclass
class CellResult:
    """
    单个参数组合的回测结果
    
    Attributes:
        param_x_value: 横轴参数值
        param_y_value: 纵轴参数值
        total_return: 总收益率
        win_rate: 胜率
        max_drawdown: 最大回撤
        trade_count: 交易次数
        success: 是否成功
        error_message: 错误信息
    """
    param_x_value: float
    param_y_value: float
    total_return: float = 0.0
    win_rate: float = 0.0
    max_drawdown: float = 0.0
    trade_count: int = 0
    success: bool = True
    error_message: str = ""


@dataclass
class GridSearchResult:
    """
    网格搜索完整结果
    
    Attributes:
        grid: 参数网格
        results: 二维结果矩阵 [y_index][x_index]
        elapsed_time: 总耗时（秒）
        success_count: 成功数
        failure_count: 失败数
    """
    grid: ParameterGrid
    results: List[List[CellResult]] = field(default_factory=list)
    elapsed_time: float = 0.0
    success_count: int = 0
    failure_count: int = 0
    
    def get_return_matrix(self) -> np.ndarray:
        """获取收益率矩阵（用于热力图）"""
        if not self.results:
            return np.array([])
        
        matrix = []
        for row in self.results:
            matrix.append([cell.total_return if cell.success else np.nan for cell in row])
        return np.array(matrix)
    
    def get_win_rate_matrix(self) -> np.ndarray:
        """获取胜率矩阵"""
        if not self.results:
            return np.array([])
        
        matrix = []
        for row in self.results:
            matrix.append([cell.win_rate if cell.success else np.nan for cell in row])
        return np.array(matrix)
    
    def get_drawdown_matrix(self) -> np.ndarray:
        """获取最大回撤矩阵"""
        if not self.results:
            return np.array([])
        
        matrix = []
        for row in self.results:
            matrix.append([cell.max_drawdown if cell.success else np.nan for cell in row])
        return np.array(matrix)
    
    def get_optimal_cell(self) -> Optional[CellResult]:
        """获取最优参数组合（收益率最高）"""
        best_cell = None
        best_return = float('-inf')
        
        for row in self.results:
            for cell in row:
                if cell.success and cell.total_return > best_return:
                    best_return = cell.total_return
                    best_cell = cell
        
        return best_cell


# ============================================================
# 策略参数配置映射
# ============================================================

STRATEGY_PARAM_CONFIGS = {
    "RSRS 阻力支撑策略": {
        "primary_params": [
            ParameterRange("n_period", "斜率窗口(N)", 14, 24, 2, 18),
            ParameterRange("buy_threshold", "买入阈值", 0.5, 1.0, 0.1, 0.7),
        ],
        "secondary_params": [
            ParameterRange("sell_threshold", "卖出阈值", -1.0, -0.5, 0.1, -0.7),
            ParameterRange("hard_stop_loss", "硬止损", -0.10, -0.04, 0.02, -0.06),
        ],
    },
    "RSI 超卖反弹策略": {
        "primary_params": [
            ParameterRange("buy_threshold", "买入阈值", 20, 40, 5, 30),
            ParameterRange("sell_threshold", "卖出阈值", 60, 80, 5, 70),
        ],
        "secondary_params": [
            ParameterRange("stop_loss", "止损比例", 0.03, 0.10, 0.01, 0.05),
            ParameterRange("take_profit", "止盈比例", 0.10, 0.30, 0.05, 0.15),
        ],
    },
}


def get_default_grid(strategy_name: str) -> Optional[ParameterGrid]:
    """
    获取策略的默认参数网格
    
    Args:
        strategy_name: 策略名称
    
    Returns:
        ParameterGrid 或 None
    """
    config = STRATEGY_PARAM_CONFIGS.get(strategy_name)
    if not config or len(config["primary_params"]) < 2:
        return None
    
    return ParameterGrid(
        param_x=config["primary_params"][0],
        param_y=config["primary_params"][1]
    )


# ============================================================
# 网格搜索执行器
# ============================================================

class GridSearcher:
    """
    网格搜索执行器
    
    复用现有 BacktestEngine 执行批量回测
    """
    
    def __init__(
        self,
        strategy_class,
        backtest_config,
        stock_codes: List[str],
        data_feed
    ):
        """
        初始化网格搜索器
        
        Args:
            strategy_class: 策略类
            backtest_config: 回测配置
            stock_codes: 股票代码列表
            data_feed: 数据源
        """
        self.strategy_class = strategy_class
        self.backtest_config = backtest_config
        self.stock_codes = stock_codes
        self.data_feed = data_feed
    
    def run(
        self,
        grid: ParameterGrid,
        base_params: Dict[str, Any],
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> GridSearchResult:
        """
        执行网格搜索
        
        Args:
            grid: 参数网格
            base_params: 基础参数（非搜索参数）
            progress_callback: 进度回调函数 (current, total, message)
        
        Returns:
            GridSearchResult 完整结果
        """
        import time
        from backtest.run_backtest import BacktestEngine
        
        start_time = time.time()
        
        x_values = grid.get_x_values()
        y_values = grid.get_y_values()
        total = len(x_values) * len(y_values)
        
        results = []
        success_count = 0
        failure_count = 0
        current = 0
        
        for y_idx, y_val in enumerate(y_values):
            row_results = []
            
            for x_idx, x_val in enumerate(x_values):
                current += 1
                
                # 构建参数
                params = base_params.copy()
                params[grid.param_x.name] = x_val
                params[grid.param_y.name] = y_val
                
                # 进度回调
                if progress_callback:
                    msg = f"{grid.param_x.display_name}={x_val}, {grid.param_y.display_name}={y_val}"
                    progress_callback(current, total, msg)
                
                # 执行回测
                try:
                    cell_result = self._run_single_backtest(x_val, y_val, params)
                    if cell_result.success:
                        success_count += 1
                    else:
                        failure_count += 1
                except Exception as e:
                    logger.error(f"回测失败: {e}")
                    cell_result = CellResult(
                        param_x_value=x_val,
                        param_y_value=y_val,
                        success=False,
                        error_message=str(e)
                    )
                    failure_count += 1
                
                row_results.append(cell_result)
            
            results.append(row_results)
        
        elapsed_time = time.time() - start_time
        
        return GridSearchResult(
            grid=grid,
            results=results,
            elapsed_time=elapsed_time,
            success_count=success_count,
            failure_count=failure_count
        )
    
    def _run_single_backtest(
        self,
        x_val: float,
        y_val: float,
        params: Dict[str, Any]
    ) -> CellResult:
        """执行单次回测"""
        from backtest.run_backtest import BacktestEngine
        
        # 聚合多只股票的回测结果
        total_returns = []
        win_rates = []
        max_drawdowns = []
        trade_counts = []
        
        for code in self.stock_codes:
            try:
                engine = BacktestEngine(self.backtest_config)
                
                df = self.data_feed.load_processed_data(code)
                if df is None or df.empty or len(df) < 60:
                    continue
                
                engine.add_data(code, df)
                engine.set_strategy(self.strategy_class, **params)
                
                result = engine.run()
                
                if result and result.trade_count > 0:
                    total_returns.append(result.total_return)
                    win_rates.append(result.win_rate)
                    max_drawdowns.append(result.max_drawdown)
                    trade_counts.append(result.trade_count)
                    
            except Exception as e:
                logger.debug(f"股票 {code} 回测失败: {e}")
                continue
        
        if not total_returns:
            return CellResult(
                param_x_value=x_val,
                param_y_value=y_val,
                success=False,
                error_message="无有效回测结果"
            )
        
        # 计算平均值
        return CellResult(
            param_x_value=x_val,
            param_y_value=y_val,
            total_return=np.mean(total_returns),
            win_rate=np.mean(win_rates),
            max_drawdown=np.mean(max_drawdowns),
            trade_count=int(np.sum(trade_counts)),
            success=True
        )


# ============================================================
# 鲁棒性诊断器
# ============================================================

class RobustnessLevel(Enum):
    """鲁棒性等级"""
    ROBUST = "robust"           # 稳健
    SENSITIVE = "sensitive"     # 敏感
    OVERFITTING = "overfitting" # 过拟合


@dataclass
class DiagnosisResult:
    """
    诊断结果
    
    Attributes:
        score: 鲁棒性评分 (0-100)
        level: 等级
        message: 诊断信息
        positive_ratio: 正收益区域占比
        return_std: 收益率标准差
        neighbor_consistency: 最优点与邻近点一致性
    """
    score: float
    level: RobustnessLevel
    message: str
    positive_ratio: float
    return_std: float
    neighbor_consistency: float


class RobustnessDiagnostics:
    """
    鲁棒性诊断器
    
    评分算法：
    1. 正收益区域占比 (40分)：正收益格子数 / 总格子数 × 40
    2. 收益率稳定性 (30分)：1 - min(std/|mean|, 1) × 30
    3. 邻近一致性 (30分)：最优点周围8格的平均收益 / 最优收益 × 30
    """
    
    @staticmethod
    def diagnose(result: GridSearchResult) -> DiagnosisResult:
        """对网格搜索结果进行鲁棒性诊断"""
        matrix = result.get_return_matrix()
        
        if matrix.size == 0:
            return DiagnosisResult(
                score=0,
                level=RobustnessLevel.OVERFITTING,
                message="无有效数据，无法诊断",
                positive_ratio=0,
                return_std=0,
                neighbor_consistency=0
            )
        
        # 1. 正收益区域占比 (40分)
        valid_mask = ~np.isnan(matrix)
        valid_count = np.sum(valid_mask)
        
        if valid_count == 0:
            return DiagnosisResult(
                score=0,
                level=RobustnessLevel.OVERFITTING,
                message="所有回测都失败，无法诊断",
                positive_ratio=0,
                return_std=0,
                neighbor_consistency=0
            )
        
        positive_count = np.sum(matrix[valid_mask] > 0)
        positive_ratio = positive_count / valid_count
        score_positive = positive_ratio * 40
        
        # 2. 收益率稳定性 (30分)
        valid_returns = matrix[valid_mask]
        mean_return = np.mean(valid_returns)
        std_return = np.std(valid_returns)
        
        if abs(mean_return) > 1e-9:
            cv = std_return / abs(mean_return)  # 变异系数
            stability = max(0, 1 - min(cv, 2) / 2)  # 归一化到 [0, 1]
        else:
            stability = 0.5  # 平均收益接近0时，给中等分
        
        score_stability = stability * 30
        
        # 3. 邻近一致性 (30分)
        neighbor_consistency = RobustnessDiagnostics._calculate_neighbor_consistency(matrix)
        score_neighbor = neighbor_consistency * 30
        
        # 总分
        total_score = score_positive + score_stability + score_neighbor
        total_score = max(0, min(100, total_score))  # 限制在 [0, 100]
        
        # 等级判定
        if total_score >= 70:
            level = RobustnessLevel.ROBUST
            message = "🟢 参数高原：策略稳健，参数微调不影响表现"
        elif total_score >= 40:
            level = RobustnessLevel.SENSITIVE
            message = "🟡 参数敏感：策略对参数有一定依赖，建议谨慎使用"
        else:
            level = RobustnessLevel.OVERFITTING
            message = "🔴 过拟合风险：策略表现高度依赖特定参数，可能是蒙的"
        
        return DiagnosisResult(
            score=round(total_score, 1),
            level=level,
            message=message,
            positive_ratio=round(positive_ratio, 3),
            return_std=round(std_return, 4),
            neighbor_consistency=round(neighbor_consistency, 3)
        )
    
    @staticmethod
    def _calculate_neighbor_consistency(matrix: np.ndarray) -> float:
        """
        计算最优点与邻近点的一致性
        
        如果最优点是孤立的高点（周围都是低收益），说明可能是过拟合
        """
        if matrix.size == 0:
            return 0
        
        # 找到最优点位置
        valid_matrix = np.where(np.isnan(matrix), float('-inf'), matrix)
        max_idx = np.unravel_index(np.argmax(valid_matrix), matrix.shape)
        max_return = matrix[max_idx]
        
        if np.isnan(max_return) or max_return <= 0:
            return 0
        
        # 获取邻近点（8邻域）
        neighbors = []
        for dy in [-1, 0, 1]:
            for dx in [-1, 0, 1]:
                if dy == 0 and dx == 0:
                    continue
                ny, nx = max_idx[0] + dy, max_idx[1] + dx
                if 0 <= ny < matrix.shape[0] and 0 <= nx < matrix.shape[1]:
                    val = matrix[ny, nx]
                    if not np.isnan(val):
                        neighbors.append(val)
        
        if not neighbors:
            return 0.5  # 边界点，给中等分
        
        # 计算邻近点平均收益与最优收益的比值
        neighbor_mean = np.mean(neighbors)
        
        if max_return > 0:
            consistency = max(0, neighbor_mean / max_return)
            consistency = min(1, consistency)  # 限制在 [0, 1]
        else:
            consistency = 0
        
        return consistency


# ============================================================
# 热力图渲染器
# ============================================================

class HeatmapRenderer:
    """
    热力图渲染器
    
    使用 Plotly 生成参数敏感性热力图
    """
    
    @staticmethod
    def render(
        result: GridSearchResult,
        metric: str = 'total_return',
        highlight_current: bool = True,
        current_x: Optional[float] = None,
        current_y: Optional[float] = None
    ) -> go.Figure:
        """
        渲染热力图
        
        Args:
            result: 网格搜索结果
            metric: 显示指标 ('total_return', 'win_rate', 'max_drawdown')
            highlight_current: 是否高亮当前参数
            current_x: 当前横轴参数值
            current_y: 当前纵轴参数值
        
        Returns:
            Plotly Figure 对象
        """
        # 获取数据矩阵
        if metric == 'total_return':
            matrix = result.get_return_matrix()
            title = "收益率热力图"
            colorbar_title = "收益率"
            format_func = lambda x: f"{x:.1%}"
        elif metric == 'win_rate':
            matrix = result.get_win_rate_matrix()
            title = "胜率热力图"
            colorbar_title = "胜率"
            format_func = lambda x: f"{x:.1%}"
        elif metric == 'max_drawdown':
            matrix = result.get_drawdown_matrix()
            title = "最大回撤热力图"
            colorbar_title = "最大回撤"
            format_func = lambda x: f"{x:.1%}"
        else:
            matrix = result.get_return_matrix()
            title = "收益率热力图"
            colorbar_title = "收益率"
            format_func = lambda x: f"{x:.1%}"
        
        x_values = result.grid.get_x_values()
        y_values = result.grid.get_y_values()
        
        # 构建 hover 文本
        hover_text = []
        for y_idx, y_val in enumerate(y_values):
            row_text = []
            for x_idx, x_val in enumerate(x_values):
                cell = result.results[y_idx][x_idx]
                if cell.success:
                    text = (
                        f"{result.grid.param_x.display_name}: {x_val}<br>"
                        f"{result.grid.param_y.display_name}: {y_val}<br>"
                        f"收益率: {cell.total_return:.2%}<br>"
                        f"胜率: {cell.win_rate:.1%}<br>"
                        f"最大回撤: {cell.max_drawdown:.1%}<br>"
                        f"交易次数: {cell.trade_count}"
                    )
                else:
                    text = f"回测失败: {cell.error_message}"
                row_text.append(text)
            hover_text.append(row_text)
        
        # 颜色映射：绿色=亏损，红色=盈利
        if metric == 'max_drawdown':
            # 回撤用反向颜色（回撤小=好=红色）
            colorscale = [[0, '#4CAF50'], [0.5, '#FFEB3B'], [1, '#f44336']]
        else:
            # 收益率/胜率：负=绿，正=红
            colorscale = [[0, '#4CAF50'], [0.5, '#FFFFFF'], [1, '#f44336']]
        
        # 创建热力图
        fig = go.Figure(data=go.Heatmap(
            z=matrix,
            x=[str(v) for v in x_values],
            y=[str(v) for v in y_values],
            colorscale=colorscale,
            hovertext=hover_text,
            hoverinfo='text',
            colorbar=dict(title=colorbar_title),
            zmid=0 if metric != 'max_drawdown' else None,
        ))
        
        # 高亮当前参数点
        if highlight_current and current_x is not None and current_y is not None:
            # 找到最接近的索引
            x_idx = min(range(len(x_values)), key=lambda i: abs(x_values[i] - current_x))
            y_idx = min(range(len(y_values)), key=lambda i: abs(y_values[i] - current_y))
            
            fig.add_annotation(
                x=str(x_values[x_idx]),
                y=str(y_values[y_idx]),
                text="★",
                showarrow=False,
                font=dict(size=20, color='black'),
            )
        
        # 标注最优点
        optimal = result.get_optimal_cell()
        if optimal:
            x_idx = x_values.index(optimal.param_x_value) if optimal.param_x_value in x_values else 0
            y_idx = y_values.index(optimal.param_y_value) if optimal.param_y_value in y_values else 0
            
            fig.add_annotation(
                x=str(optimal.param_x_value),
                y=str(optimal.param_y_value),
                text="最优",
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=2,
                arrowcolor='#333',
                font=dict(size=10, color='#333'),
                bgcolor='white',
                bordercolor='#333',
                borderwidth=1,
            )
        
        # 布局
        fig.update_layout(
            title=title,
            xaxis_title=result.grid.param_x.display_name,
            yaxis_title=result.grid.param_y.display_name,
            height=400,
            margin=dict(t=50, b=50, l=50, r=50),
        )
        
        return fig
    
    @staticmethod
    def render_diagnosis_card(diagnosis: DiagnosisResult) -> str:
        """
        生成诊断结果的 HTML 卡片
        
        Args:
            diagnosis: 诊断结果
        
        Returns:
            HTML 字符串
        """
        if diagnosis.level == RobustnessLevel.ROBUST:
            bg_color = "#E8F5E9"
            border_color = "#4CAF50"
        elif diagnosis.level == RobustnessLevel.SENSITIVE:
            bg_color = "#FFF8E1"
            border_color = "#FFC107"
        else:
            bg_color = "#FFEBEE"
            border_color = "#f44336"
        
        html = f"""
        <div style="
            background-color: {bg_color};
            border-left: 4px solid {border_color};
            padding: 15px;
            border-radius: 4px;
            margin: 10px 0;
        ">
            <h4 style="margin: 0 0 10px 0;">鲁棒性评分: {diagnosis.score}/100</h4>
            <p style="margin: 0; font-size: 16px;">{diagnosis.message}</p>
            <hr style="margin: 10px 0; border: none; border-top: 1px solid #ddd;">
            <div style="font-size: 12px; color: #666;">
                <span>正收益占比: {diagnosis.positive_ratio:.1%}</span> |
                <span>收益率波动: {diagnosis.return_std:.2%}</span> |
                <span>邻近一致性: {diagnosis.neighbor_consistency:.1%}</span>
            </div>
        </div>
        """
        return html
