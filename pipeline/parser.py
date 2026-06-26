"""
题目解析器
基于 LLM 将提取的文本解析为结构化题目
"""

import json
import sys
from pathlib import Path

# 添加项目根目录到 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai.client import get_client
from ai.prompts import QUESTION_PARSE_SYSTEM, QUESTION_PARSE_USER
from pipeline.classifier import auto_classify, get_category_id


def parse_with_llm(text: str, source: str = "") -> list[dict]:
    """使用 LLM 解析文本为结构化题目列表

    Args:
        text: 原始文本
        source: 来源文件名

    Returns:
        [{"question_type": ..., "title": ..., "question_text": ..., ...}, ...]
    """
    client = get_client()

    try:
        result = client.chat_json(
            system_prompt=QUESTION_PARSE_SYSTEM,
            user_message=QUESTION_PARSE_USER.format(source=source, text=text),
            temperature=0.3,
        )
        questions = result.get("questions", [])
        return questions
    except Exception as e:
        print(f"  [解析失败] {source}: {e}")
        return []


def parse_text_blocks(text: str, source: str = "", chunk_size: int = 3000) -> list[dict]:
    """将长文本分块后逐块解析

    当文本太长时，先按自然分隔拆分再逐块发送给 LLM
    """
    # 按 "Solution" / "Answer" / 题目编号 尝试预分割
    import re

    # 尝试按常见题目分隔符拆分
    separators = [
        r'\n(?=Question\s*\d+)',
        r'\n(?=Q\d+[\.\)])',
        r'\n(?=\d+[\.\)]\s*[A-Z])',
        r'\n(?=第[一二三四五六七八九十\d]+题)',
    ]

    blocks = [text]
    for sep in separators:
        new_blocks = []
        for block in blocks:
            parts = re.split(sep, block)
            new_blocks.extend(parts)
        blocks = new_blocks

    # 合并太小的块，拆分太大的块
    merged = []
    current = ""
    for block in blocks:
        if len(current) + len(block) < chunk_size:
            current += "\n\n" + block if current else block
        else:
            if current.strip():
                merged.append(current)
            current = block
    if current.strip():
        merged.append(current)

    # 逐块解析
    all_questions = []
    for i, block in enumerate(merged):
        print(f"  解析块 {i + 1}/{len(merged)} ({len(block)}字符)...")
        questions = parse_with_llm(block, f"{source} (块{i+1}/{len(merged)})")
        all_questions.extend(questions)

    return all_questions


def enrich_question(question: dict) -> dict:
    """为解析出的题目补充分类信息"""
    # 如果 LLM 已给出分类，使用 LLM 的；否则用规则分类
    if not question.get("question_type"):
        # 自动分类
        auto = auto_classify(question.get("question_text", ""))
        question["category"] = auto["category"]
        question["question_type"] = auto["question_type"]
        question["difficulty"] = auto["difficulty"]
        question["keywords"] = question.get("keywords") or auto["keywords"]
    else:
        # 补充分类和难度
        auto = auto_classify(question.get("question_text", ""))
        if not question.get("category"):
            question["category"] = auto["category"]
        if not question.get("difficulty"):
            question["difficulty"] = auto["difficulty"]
        if not question.get("keywords"):
            question["keywords"] = auto["keywords"]

    # 转换分类名为 ID
    question["category_id"] = get_category_id(question["category"])

    return question


def parse_and_enrich(text: str, source: str = "") -> list[dict]:
    """解析文本并自动补充分类信息"""
    questions = parse_text_blocks(text, source)
    return [enrich_question(q) for q in questions]


if __name__ == "__main__":
    # 简单测试
    test_text = """
    1. Please explain what is hot carrier injection (HCI) effect in short channel MOSFET.
    The HCI may give rise to what kind of impact on MOSFET device?

    2. Calculate the threshold voltage of an n-channel MOSFET with the following parameters:
    Na = 1e17 cm^-3, tox = 10 nm, Qox = 5e10 cm^-2.
    """
    result = auto_classify(test_text)
    print(json.dumps(result, ensure_ascii=False, indent=2))