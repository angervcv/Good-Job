# GoodJob - 半导体功率器件求职笔试刷题平台

面向半导体功率器件方向的求职笔试刷题复习平台，基于 Streamlit 构建。

## 功能

- **模块刷题**：按器件设计、可靠性分析、半导体工艺、电路分析四大模块，支持顺序刷题和随机抽题，AI 自动评分
- **每日测验**：每天一套试卷（10题/100分），客观题自动判分，主观题 AI 评分，支持评论区复盘
- **统计排行**：个人刷题进度、正确率趋势、每日热力图、刷题历史，排行榜

## 本地运行

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API Key

在项目根目录创建 `.env` 文件：

```
DEEPSEEK_API_KEY=你的API密钥
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
```

### 3. 启动

```bash
streamlit run app/main.py
```

浏览器打开 http://localhost:8501，输入用户名即可开始。

## Streamlit Cloud 部署

1. Fork 本仓库到你的 GitHub
2. 在 [Streamlit Community Cloud](https://streamlit.io/cloud) 中部署，入口文件选择 `app/main.py`
3. 在 Streamlit Cloud 的 Secrets 中配置：

```toml
DEEPSEEK_API_KEY = "你的API密钥"
LLM_BASE_URL = "https://api.deepseek.com/v1"
LLM_MODEL = "deepseek-chat"
```

## 项目结构

```
├── config.py              # 全局配置
├── requirements.txt       # 依赖清单
├── ai/                    # AI 模块（LLM客户端、答案补全、题目生成、评分）
├── app/                   # Streamlit 应用（页面、组件、工具）
├── data/db/               # 数据库（Schema、连接、查询）
├── data/goodjob.db        # 题库（357道题，含答案）
├── pipeline/              # 文档处理流水线（PDF/DOCX/图片提取、解析）
└── 题目/                  # 原始题目素材（只读）
```

## 技术栈

- Python 3.12 + Streamlit
- SQLite（WAL 模式）
- PyMuPDF + python-docx（文档提取）
- DeepSeek API（AI 评分）
- Plotly（图表）

## 题库

共 357 道题目，覆盖四大领域：

| 领域 | 题数 | 内容 |
|------|------|------|
| 器件设计 | 134 | MOSFET/IGBT/SiC/GaN/LDMOS/超结等 |
| 可靠性分析 | 50 | HCI/NBTI/TDDB/ESD/UIS/Latch-up等 |
| 半导体工艺 | 113 | BCD/LOCOS/STI/离子注入/CMOS工艺等 |
| 电路分析 | 36 | BUCK/BOOST/LDO/Bandgap/栅驱动等 |

题目来源：矽力杰/杰华特/士兰/MPS/思瑞浦/华为等公司历年笔试真题 + AI 生成补充。
