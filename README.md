# 📈 MiniQuant-Lite

**轻量级 A 股量化投资辅助系统 —— 5.5 万本金的「运钞车」**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

MiniQuant-Lite 是一套面向 A 股个人投资者的轻量级量化投资辅助系统。系统基于 Python 构建，使用免费开源数据接口（AkShare），提供选股筛选、策略回测和每日交易信号生成功能。

> ⚠️ **风险提示**：本系统仅供学习研究使用，不构成投资建议。股市有风险，投资需谨慎。历史表现不代表未来收益。

---

## ✨ 核心特性

### 🛡️ 保命模块（风控优先）

- **大盘滤网** - 沪深300 < MA20 时强制空仓，规避系统性风险
- **财报窗口期检测** - 财报披露前后 3 天自动剔除，避免财报黑天鹅
- **Smart Sizer** - 5% 现金缓冲、5 元低消预警、最大持仓限制
- **涨跌停板检测** - 一字板禁止交易，避免回测结果虚高

### 💰 盈利模块

- **趋势滤网 MACD 策略** - MA60 + MACD + RSI 组合，只做右侧交易
- **智能止损止盈** - 硬止损 -8%，移动止盈 15%/5%
- **两阶段筛选** - 预剪枝 + 精筛，1 分钟内完成全市场扫描

### 📊 可视化界面

- **Streamlit Dashboard** - 无需编写代码即可使用
- **数据管理** - 一键下载、更新、清空缓存
- **策略回测** - 可视化回测结果，净值曲线对比
- **每日信号** - 早安确认清单，新闻链接快查

---

## 🚀 快速开始

### 环境要求

- Python 3.10+
- Windows / macOS / Linux

### 安装步骤

1. **克隆项目**

```bash
git clone https://github.com/your-username/miniquant-lite.git
cd miniquant-lite
```

2. **创建虚拟环境（推荐）**

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

3. **安装依赖**

```bash
pip install -r requirements.txt
```

4. **启动应用**

```bash
streamlit run app/Home.py
```

5. **访问界面**

打开浏览器访问 `http://localhost:8501`

---

## 📁 项目结构

```
miniquant-lite/
├── app/                          # Streamlit 应用
│   ├── Home.py                   # 首页
│   └── pages/
│       ├── 1_📊_Data_Manager.py  # 数据管理
│       ├── 2_Backtest.py         # 策略回测
│       ├── 3_Daily_Signal.py     # 每日信号
│       └── 4_📝_Logs.py          # 日志查看
├── backtest/                     # 回测引擎
│   └── run_backtest.py
├── config/                       # 配置文件
│   ├── settings.py               # 全局配置
│   └── stock_pool.py             # 股票池配置
├── core/                         # 核心模块
│   ├── data_feed.py              # 数据获取与清洗
│   ├── screener.py               # 选股筛选器
│   ├── sizers.py                 # 仓位管理
│   ├── signal_generator.py       # 信号生成器
│   ├── report_checker.py         # 财报检测器
│   └── logging_config.py         # 日志配置
├── strategies/                   # 交易策略
│   ├── base_strategy.py          # 策略基类
│   └── trend_filtered_macd_strategy.py  # 趋势滤网MACD策略
├── tests/                        # 测试文件
│   ├── test_data_feed_validation.py
│   ├── test_screener_validation.py
│   ├── test_strategy_validation.py
│   ├── test_backtest_validation.py
│   └── test_integration.py       # 集成测试
├── data/                         # 数据目录
│   ├── raw/                      # 原始数据
│   └── processed/                # 处理后数据
├── logs/                         # 日志目录
├── requirements.txt              # 依赖列表
└── README.md                     # 本文件
```

---

## 📖 使用指南

### 标准作业程序 (SOP)

**推荐运行时间：交易日晚上 19:00 - 21:00**

```
晚上 19:00-21:00
    ↓
运行系统生成信号
    ↓
点击新闻链接，人眼扫一遍标题（10秒）
    ↓
将信号放入券商 APP 的"条件单"
    ↓
安心睡觉
    ↓
次日 9:25 前完成早安确认清单
    ↓
开盘自动执行
```

### 1. 数据管理

1. 进入「📊 数据管理」页面
2. 配置股票池（默认使用自选股列表）
3. 设置日期范围（建议下载最近 1 年数据）
4. 点击「开始下载」

> 💡 **提示**：首次使用需要下载历史数据，耗时约 1-5 分钟（取决于股票数量）

### 2. 策略回测

1. 进入「🧪 策略回测」页面
2. 选择策略（默认：趋势滤网 MACD 策略）
3. 配置回测参数（初始资金、日期范围等）
4. 点击「开始回测」
5. 查看回测结果：
   - 核心风控指标（胜率、最大回撤、盈亏比）
   - 收益指标（总收益率、年化收益率、Alpha）
   - 净值曲线对比图
   - 交易明细

### 3. 每日信号

1. 进入「📡 每日信号」页面
2. 查看大盘状态（沪深300 vs MA20）
3. 点击「生成今日信号」
4. 对每个信号：
   - 点击新闻链接，快速扫一眼标题
   - 注意财报窗口期警告
   - 注意高费率预警
5. 将确认无误的信号放入券商条件单

---

## ⚙️ 配置说明

### 资金配置 (`config/settings.py`)

```python
# 初始资金
initial_capital = 55000.0

# 手续费率（万分之三）
commission_rate = 0.0003

# 最低手续费（5元低消）
min_commission = 5.0

# 印花税率（千分之一，仅卖出收取）
stamp_tax_rate = 0.001
```

### 仓位配置

```python
# 最大持仓只数
max_positions_count = 2

# 最小交易金额门槛
min_trade_amount = 15000.0

# 现金缓冲比例（防止高开废单）
cash_buffer = 0.05
```

### 策略配置

```python
# 趋势均线周期
ma_period = 60

# RSI 上限（超过不买入）
rsi_upper = 80

# 硬止损比例
hard_stop_loss = -0.08

# 移动止盈启动阈值
trailing_start = 0.15

# 移动止盈回撤比例
trailing_stop = 0.05
```

### 股票池配置 (`config/stock_pool.py`)

```python
# 自选股列表
WATCHLIST = [
    '000001',  # 平安银行
    '600036',  # 招商银行
    '300750',  # 宁德时代
    # ... 添加更多股票
]
```

---

## 📊 策略说明

### 趋势滤网 MACD 策略

**核心理念**：5.5 万本金亏不起，必须放弃"抄底"幻想，只做"右侧交易"

#### 买入条件（全部满足）

1. **趋势滤网**：股价 > MA60（只做右侧交易）
2. **MACD 金叉**：DIF 上穿 DEA
3. **RSI 过滤**：RSI < 80（避免追高，RSI > 90 绝对不追）

#### 卖出条件（任一满足）

1. **硬止损**：亏损达到 -8%，无条件市价止损
2. **移动止盈**：盈利超过 15% 后，从最高点回撤 5% 止盈
3. **MACD 死叉**：DIF 下穿 DEA

#### 风控机制

- **大盘滤网**：沪深300 < MA20 时，返回空信号，建议空仓观望
- **财报窗口期**：财报披露前后 3 天自动剔除
- **流动性过滤**：流通市值 50-500 亿，换手率 2%-15%
- **行业互斥**：同一行业最多选取 1 只股票

---

## 🔧 技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| 数据获取 | AkShare | 免费开源 A 股数据接口 |
| 数据处理 | Pandas | 数据清洗与分析 |
| 回测引擎 | Backtrader | 专业量化回测框架 |
| 可视化 | Streamlit | 快速构建 Web 应用 |
| 图表 | Plotly | 交互式图表 |
| 测试 | pytest + hypothesis | 单元测试 + 属性测试 |

---

## 🧪 测试

运行所有测试：

```bash
python -m pytest tests/ -v
```

运行特定测试文件：

```bash
# 数据层测试
python -m pytest tests/test_data_feed_validation.py -v

# 筛选层测试
python -m pytest tests/test_screener_validation.py -v

# 策略层测试
python -m pytest tests/test_strategy_validation.py -v

# 回测层测试
python -m pytest tests/test_backtest_validation.py -v

# 集成测试
python -m pytest tests/test_integration.py -v
```

---

## ❓ 常见问题

### Q: AkShare 数据获取失败怎么办？

A: 
1. 检查网络连接
2. 确认 AkShare 版本：`pip install akshare==1.12.0`
3. 避免在交易时段频繁请求
4. 如果持续失败，可能是接口临时维护，稍后重试

### Q: 回测结果和实盘差异大怎么办？

A: 回测存在以下局限性：
1. 无法模拟真实滑点和流动性
2. 不包含新闻面人工过滤
3. 涨跌停可能无法成交

建议：
- 回测结果仅供参考
- 实盘时结合新闻链接人工判断
- 使用条件单而非市价单

### Q: 为什么信号页面显示"今日无操作建议"？

A: 可能的原因：
1. 大盘滤网生效（沪深300 < MA20）
2. 没有股票满足买入条件
3. 股票数据未下载或数据不足

### Q: 如何添加自己的股票到股票池？

A: 编辑 `config/stock_pool.py` 文件，在 `WATCHLIST` 列表中添加股票代码：

```python
WATCHLIST = [
    '000001',
    '600036',
    '你的股票代码',  # 添加这里
]
```

---

## 📝 更新日志

### v1.0.0 (2024-12)

- ✅ 初始版本发布
- ✅ 数据获取与清洗模块
- ✅ 两阶段选股筛选器
- ✅ 趋势滤网 MACD 策略
- ✅ 智能仓位管理器
- ✅ 回测引擎（含涨跌停检测）
- ✅ 每日信号生成器
- ✅ 财报窗口期检测
- ✅ Streamlit 可视化界面
- ✅ 完整测试套件（117 个测试用例）

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交 Pull Request

---

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

---

## 🙏 致谢

- [AkShare](https://github.com/akfamily/akshare) - 免费开源的 A 股数据接口
- [Backtrader](https://www.backtrader.com/) - 专业的量化回测框架
- [Streamlit](https://streamlit.io/) - 快速构建数据应用的框架

---

<p align="center">
  <b>MiniQuant-Lite</b> - 让量化投资更简单
  <br>
  Made with ❤️ for A股个人投资者
</p>
