"""
题目自动分类器
基于关键词规则 + LLM 确认
"""

import json
from pathlib import Path
import config
from data.db.connection import get_cursor


def classify_by_keywords(question_text: str) -> str | None:
    """基于关键词规则进行分类

    Returns:
        分类名称，如果无法确定则返回 None
    """
    scores = {cat: 0 for cat in config.CATEGORY_KEYWORDS}

    for cat, keywords in config.CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in question_text.lower():
                # 越长的关键词权重越高
                scores[cat] += len(kw) / 3

    # 选择最高分
    if max(scores.values()) == 0:
        return None

    best_cat = max(scores, key=scores.get)
    return best_cat


def classify_question_type(question_text: str) -> str:
    """基于关键词判断题目类型"""
    text_lower = question_text.lower()

    # 选择题特征
    choice_indicators = ["a.", "b.", "c.", "d.", "a)", "b)", "c)", "d)",
                         "a、", "b、", "c、", "d、", "①", "②", "③", "④"]
    choice_count = sum(1 for ind in choice_indicators if ind in text_lower)

    if choice_count >= 3:
        return "single_choice"

    # 填空题特征
    fill_indicators = ["___", "____", "（", "）", "填空", "fill in"]
    if any(ind in question_text for ind in fill_indicators):
        return "fill_blank"

    # 计算题特征
    calc_indicators = ["计算", "calculate", "compute", "求", "推导",
                       "derive", "=", "公式", "formula", "数值"]
    if any(ind in text_lower for ind in calc_indicators):
        return "calculation"

    # 画图题特征
    draw_indicators = ["画", "draw", "绘制", "plot", "sketch", "波形",
                       "截面", "cross", "能带图", "band diagram", "CV曲线"]
    if any(ind in text_lower for ind in draw_indicators):
        return "drawing"

    # 工艺流程题特征
    process_indicators = ["工艺流程", "process flow", "步骤", "工艺流程",
                          "fabrication", "制造流程"]
    if any(ind in text_lower for ind in process_indicators):
        return "process_flow"

    # 默认简答题
    return "short_answer"


def estimate_difficulty(question_text: str, question_type: str) -> int:
    """估算题目难度 (1-5)"""
    text_lower = question_text.lower()
    length_score = min(len(question_text) / 200, 3)  # 文本长度

    # 复杂概念
    complex_concepts = [
        "super junction", "sj", "resurf", "triple", "dibl", "subthreshold",
        "nbti", "trap", "interface state", "sso", "snapback",
        "safe operating", "soa", "thermal runaway", "second breakdown",
        "quasi", "non-equilibrium", "fermi-dirac", "schrodinger",
    ]
    concept_score = sum(1 for c in complex_concepts if c in text_lower)

    # 计算题通常更难
    type_score = {
        "calculation": 1,
        "process_flow": 1,
        "drawing": 0.5,
        "short_answer": 0,
        "single_choice": -0.5,
        "multiple_choice": 0,
        "fill_blank": -1,
    }

    raw = length_score + concept_score * 0.5 + type_score.get(question_type, 0)
    return max(1, min(5, round(2 + raw)))


def extract_keywords(question_text: str, max_kw: int = 5) -> list[str]:
    """从题目文本中提取关键词"""
    all_keywords = []
    for cat_keywords in config.CATEGORY_KEYWORDS.values():
        all_keywords.extend(cat_keywords)

    found = []
    text_lower = question_text.lower()
    for kw in all_keywords:
        if kw.lower() in text_lower:
            found.append(kw)

    # 去重并按长度排序（长关键词优先）
    found = sorted(set(found), key=len, reverse=True)
    return found[:max_kw]


def auto_classify(question_text: str) -> dict:
    """全自动分类（无需 LLM）

    Returns:
        {"category": str, "question_type": str, "difficulty": int, "keywords": list}
    """
    category = classify_by_keywords(question_text) or "器件设计"  # 默认器件设计
    qtype = classify_question_type(question_text)
    difficulty = estimate_difficulty(question_text, qtype)
    keywords = extract_keywords(question_text)

    return {
        "category": category,
        "question_type": qtype,
        "difficulty": difficulty,
        "keywords": keywords,
    }


def get_category_id(category_name: str) -> int:
    """通过分类名获取 ID"""
    with get_cursor() as cur:
        row = cur.execute(
            "SELECT id FROM categories WHERE name = ?", (category_name,)
        ).fetchone()
        return row["id"] if row else 1