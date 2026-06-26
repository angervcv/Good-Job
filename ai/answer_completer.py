"""
答案补全模块
对缺失答案的题目，调用 LLM 生成参考答案
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from ai.client import get_client
from ai.prompts import ANSWER_COMPLETE_SYSTEM, ANSWER_COMPLETE_USER
from data.db.connection import get_cursor
from data.db.queries import update_question_answer


QUESTION_TYPE_CN = {
    "single_choice": "单选题",
    "multiple_choice": "多选题",
    "fill_blank": "填空题",
    "calculation": "计算题",
    "short_answer": "简答题",
    "drawing": "画图题",
    "process_flow": "工艺流程题",
}


def complete_single_question(question: dict) -> dict | None:
    """为单道题目补全答案

    Args:
        question: 题目字典（需包含 question_text, question_type, category 等）

    Returns:
        {"answer": str, "explanation": str} 或 None
    """
    client = get_client()
    qtype_cn = QUESTION_TYPE_CN.get(question.get("question_type", ""), "题目")

    try:
        result = client.chat_json(
            system_prompt=ANSWER_COMPLETE_SYSTEM,
            user_message=ANSWER_COMPLETE_USER.format(
                question_type=qtype_cn,
                category=question.get("category_name", "未知"),
                question_text=question.get("question_text", ""),
            ),
            temperature=0.3,
        )
        return {
            "answer": result.get("answer", ""),
            "explanation": result.get("explanation", ""),
        }
    except Exception as e:
        print(f"  [答案补全失败] Q{question['id']}: {e}")
        return None


def complete_missing_answers(batch_size: int = 20, dry_run: bool = False) -> dict:
    """批量补全所有缺失答案的题目

    Args:
        batch_size: 每批处理数量
        dry_run: 仅统计不实际执行

    Returns:
        {"total_missing": int, "completed": int, "failed": int}
    """
    with get_cursor() as cur:
        # 查询缺少答案的题目
        rows = cur.execute(
            """SELECT q.id, q.question_text, q.question_type, c.name as category_name
               FROM questions q
               LEFT JOIN categories c ON q.category_id = c.id
               WHERE (q.answer_text IS NULL OR q.answer_text = '' OR q.answer_text = ' ')
                 AND q.is_active = 1
               ORDER BY q.id"""
        ).fetchall()

    questions = [dict(r) for r in rows]
    stats = {"total_missing": len(questions), "completed": 0, "failed": 0}

    print(f"共 {len(questions)} 道题目缺少答案")

    if dry_run:
        for q in questions[:5]:
            print(f"  Q{q['id']}: {q['question_text'][:80]}...")
        return stats

    for i in range(0, len(questions), batch_size):
        batch = questions[i : i + batch_size]
        print(f"\n处理第 {i + 1}-{min(i + batch_size, len(questions))} 题 / 共 {len(questions)}")

        for q in batch:
            print(f"  补全 Q{q['id']}...", end=" ")
            result = complete_single_question(q)

            if result and result["answer"]:
                update_question_answer(
                    question_id=q["id"],
                    answer_text=result["answer"] + "\n\n[AI生成]",
                    explanation=result.get("explanation"),
                    ai_answer_flag=1,
                )
                stats["completed"] += 1
                print("OK")
            else:
                stats["failed"] += 1
                print("FAILED")

    print(f"\n答案补全完成: {stats['completed']} 成功, {stats['failed']} 失败")
    return stats


if __name__ == "__main__":
    complete_missing_answers(dry_run=True)