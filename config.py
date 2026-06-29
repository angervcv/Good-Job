"""
全局配置模块
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 项目根目录
ROOT_DIR = Path(__file__).parent.absolute()

# 加载 .env 文件
load_dotenv(ROOT_DIR / ".env")

# 数据目录
DATA_DIR = ROOT_DIR / "data"
DB_PATH = DATA_DIR / "goodjob.db"        # 题库（git追踪，部署时覆盖）
USER_DB_PATH = DATA_DIR / "userdata.db"  # 本地回退

# Supabase（云端持久化）
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://mjvreelvdenljvmcdaye.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "sb_publishable_tZ1u7TCR-37Z_-RjMak0xg_vwy2sRBF")
EXTRACTED_DIR = DATA_DIR / "processed" / "extracted"
PARSED_DIR = DATA_DIR / "processed" / "parsed"
BACKUP_DIR = DATA_DIR / "backups"

# 原始题目目录
QUESTIONS_DIR = ROOT_DIR / "题目" / "题目"

# ============================================================
# LLM 配置 - DeepSeek V4 Pro
# ============================================================
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "deepseek")
LLM_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-v4-pro")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "4096"))
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))

# ============================================================
# Streamlit 配置
# ============================================================
STREAMLIT_TITLE = "GoodJob - 半导体功率器件刷题平台"
STREAMLIT_PORT = int(os.getenv("STREAMLIT_PORT", "8501"))

# ============================================================
# 题目分类预设
# ============================================================
CATEGORIES = [
    {
        "name": "器件设计",
        "description": "MOSFET器件结构、LDMOS、IGBT、超结等功率器件设计与优化",
        "sort_order": 1,
    },
    {
        "name": "可靠性分析",
        "description": "HCI、NBTI、TDDB、UIS、ESD等可靠性物理与失效分析",
        "sort_order": 2,
    },
    {
        "name": "半导体工艺",
        "description": "氧化、扩散、注入、刻蚀、CMP、外延等工艺流程与集成",
        "sort_order": 3,
    },
    {
        "name": "电路分析",
        "description": "模拟电路基础、开关电源、栅驱动、运放等应用电路",
        "sort_order": 4,
    },
]

# 关键词 -> 分类映射
CATEGORY_KEYWORDS = {
    "器件设计": [
        "MOSFET", "LDMOS", "IGBT", "超结", "SJ", "阈值电压", "Vth", "VTH",
        "导通电阻", "Ron", "Rds(on)", "击穿电压", "BV", "BVdss", "漏极", "源极", "栅极",
        "沟道", "掺杂", "外延", "RESURF", "场板", "栅氧", "Short Channel",
        "DIBL", "迁移率", "跨导", "亚阈值摆幅", "窄沟道", "JFET",
        "体二极管", "寄生", "SOA", "安全工作区", "CV曲线", "C-V", "Id-Vg",
        "VDMOS", "LIGBT", "SGT", "屏蔽栅", "split gate",
        "SiC", "GaN", "HEMT", "宽禁带", "WBG", "碳化硅", "氮化镓",
    ],
    "可靠性分析": [
        "HCI", "NBTI", "TDDB", "ESD", "UIS", "latch-up", "闩锁",
        "SOA", "安全工作区", "雪崩", "热载流子", "TID", "总剂量",
        "单粒子", "SEB", "SEGR", "HTRB", "HTGB", "H3TRB", "老化", "失效",
        "Burn-in", "老化", "寿命", "退化", "GOI", "栅氧完整性",
        "EM", "电迁移", "应力迁移", "TDDB", "经时击穿",
        "反向恢复", "reverse recovery", "开关损耗",
    ],
    "半导体工艺": [
        "氧化", "扩散", "注入", "刻蚀", "CMP", "光刻", "外延",
        "CVD", "PVD", "ALD", "退火", "RTA", "STI", "LOCOS",
        "硅化物", "接触孔", "金属化", "背金", "减薄", "划片",
        "BCD", "LDD", "spacer", "侧墙", "阱", "well",
        "离子注入", "掺杂浓度", "退火", "silicid", "salicide",
        "lithography", "photo", "掩膜", "mask",
    ],
    "电路分析": [
        "放大器", "运放", "反馈", "频率响应", "开关电源", "BUCK",
        "BOOST", "LDO", "栅驱动", "半桥", "全桥", "PWM",
        "环路补偿", "PSRR", "CMRR", "带隙基准", "比较器",
        "bandgap", "opamp", "开关频率", "占空比", "纹波",
        "死区时间", "dead time", "栅电荷", "Qg", "米勒平台",
    ],
}

# 题目类型
QUESTION_TYPES = [
    "single_choice",    # 单选题
    "multiple_choice",  # 多选题
    "fill_blank",       # 填空题
    "calculation",      # 计算题
    "short_answer",     # 简答题
    "drawing",          # 画图题
    "process_flow",     # 工艺流程题
]

# 每日测验题目数
DAILY_QUIZ_COUNT = 10
# 每日测验每题满分
DAILY_QUIZ_PER_QUESTION_SCORE = 10
# 排行榜最低刷题门槛
LEADERBOARD_MIN_REVIEWED = 20

# 确保必要目录存在
for d in [DATA_DIR, EXTRACTED_DIR, PARSED_DIR, BACKUP_DIR]:
    d.mkdir(parents=True, exist_ok=True)
