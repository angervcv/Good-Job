"""
AI 题目生成器
基于已有题库生成类似的新题目
"""

import json
import sys
import random
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from ai.client import get_client
from ai.prompts import QUESTION_GENERATE_SYSTEM, QUESTION_GENERATE_USER
from data.db.connection import get_cursor
from data.db.queries import insert_question, get_questions_by_category
from pipeline.classifier import get_category_id


def get_reference_questions(category_name: str, count: int = 5) -> list[dict]:
    """从题库中随机抽取参考题目（用作 few-shot 示例）"""
    cat_id = get_category_id(category_name)
    with get_cursor() as cur:
        rows = cur.execute(
            """SELECT question_text, question_type, answer_text, keywords
               FROM questions
               WHERE category_id = ? AND is_active = 1
               ORDER BY RANDOM() LIMIT ?""",
            (cat_id, count),
        ).fetchall()
    return [dict(r) for r in rows]


def generate_questions_for_category(
    category_name: str,
    count: int = 125,
    batch_size: int = 10,
) -> list[dict]:
    """为某一分类生成题目

    Args:
        category_name: 分类名称
        count: 需要生成的题目总数
        batch_size: 每批生成数量（每次 LLM 调用生成 batch_size 道题）

    Returns:
        生成的题目列表
    """
    client = get_client()
    all_questions = []

    # 获取参考题目
    refs = get_reference_questions(category_name, count=5)
    ref_text = "\n\n---\n\n".join(
        f"[{r['question_type']}] {r['question_text'][:300]}"
        for r in refs
    )

    batches = (count + batch_size - 1) // batch_size

    for batch_num in range(batches):
        actual_count = min(batch_size, count - len(all_questions))
        print(f"\n  批次 {batch_num + 1}/{batches}: 生成 {actual_count} 道 {category_name} 题目...")

        try:
            result = client.chat_json(
                system_prompt=QUESTION_GENERATE_SYSTEM,
                user_message=QUESTION_GENERATE_USER.format(
                    category=category_name,
                    count=actual_count,
                    reference_questions=ref_text,
                ),
                temperature=0.8,  # 提高温度增加多样性
            )
            questions = result.get("questions", [])
            all_questions.extend(questions)
            print(f"    生成了 {len(questions)} 道题目")

            # 更新参考题目（使用不同样本）
            refs = get_reference_questions(category_name, count=5)
            ref_text = "\n\n---\n\n".join(
                f"[{r['question_type']}] {r['question_text'][:300]}"
                for r in refs
            )

        except Exception as e:
            print(f"    生成失败: {e}")
            continue

    return all_questions


def insert_generated_questions(
    questions: list[dict],
    category_name: str,
    source_file: str = "ai_generated",
) -> int:
    """将 AI 生成的题目批量入库

    Returns:
        成功入库的题目数
    """
    cat_id = get_category_id(category_name)
    inserted = 0

    for q in questions:
        try:
            question_text = q.get("question_text", "")
            if not question_text or len(question_text) < 15:
                continue

            options = q.get("options")
            if options and isinstance(options, list):
                options = json.dumps(options, ensure_ascii=False)

            keywords = q.get("keywords", [])
            if isinstance(keywords, list):
                keywords = ",".join(keywords)

            answer = q.get("answer_text", "")
            if answer and "[AI生成]" not in answer:
                answer += "\n\n[AI生成]"

            qid = insert_question(
                question_type=q.get("question_type", "short_answer"),
                question_text=question_text,
                category_id=cat_id,
                answer_text=answer,
                explanation=q.get("explanation", ""),
                keywords=keywords,
                difficulty=q.get("difficulty", 3),
                title=q.get("title", ""),
                options=options,
                is_ai_generated=1,
                source_file=source_file,
            )
            if qid:
                inserted += 1
        except Exception as e:
            print(f"    [入库失败] {e}")

    return inserted


def generate_all_questions(
    total_per_category: int = 125,
    batch_size: int = 10,
) -> dict:
    """为所有分类生成 AI 题目（总共 500 题 = 4分类 × 125题）

    Returns:
        统计信息
    """
    categories = ["器件设计", "可靠性分析", "半导体工艺", "电路分析"]
    stats = {}

    for cat in categories:
        print(f"\n{'=' * 40}")
        print(f"生成 {cat} 题目 ({total_per_category} 题)")
        print(f"{'=' * 40}")

        generated = generate_questions_for_category(
            category_name=cat,
            count=total_per_category,
            batch_size=batch_size,
        )

        inserted = insert_generated_questions(generated, category_name=cat)
        stats[cat] = {"generated": len(generated), "inserted": inserted}
        print(f"  {cat}: 生成 {len(generated)} 题 -> 入库 {inserted} 题")

    total_gen = sum(s["generated"] for s in stats.values())
    total_ins = sum(s["inserted"] for s in stats.values())
    print(f"\n总计: 生成 {total_gen} 题, 入库 {total_ins} 题")
    return stats


if __name__ == "__main__":
    # 测试：先生成 5 题
    questions = generate_questions_for_category("器件设计", count=5)
    for q in questions:
        print(f"\n[{q.get('question_type')}] {q.get('title')}")
        print(f"  {q.get('question_text', '')[:200]}")
        print(f"  答案: {q.get('answer_text', '')[:150]}")