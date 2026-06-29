"""
常用数据库查询封装
"""

import uuid
import json
from typing import Optional
from data.db.connection import get_cursor, get_userdata_cursor


# ============================================================
# 分类查询
# ============================================================
def get_all_categories() -> list[dict]:
    """获取所有分类（排除电路分析）"""
    with get_cursor() as cur:
        rows = cur.execute(
            "SELECT * FROM categories WHERE name != '电路分析' ORDER BY sort_order"
        ).fetchall()
        return [dict(r) for r in rows]


# ============================================================
# 题目查询
# ============================================================
def get_question_by_id(question_id: int) -> dict | None:
    """根据 ID 获取题目"""
    with get_cursor() as cur:
        row = cur.execute(
            "SELECT * FROM questions WHERE id = ? AND is_active = 1", (question_id,)
        ).fetchone()
        return dict(row) if row else None


def get_question_by_uuid(q_uuid: str) -> dict | None:
    """根据 UUID 获取题目"""
    with get_cursor() as cur:
        row = cur.execute(
            "SELECT * FROM questions WHERE uuid = ? AND is_active = 1", (q_uuid,)
        ).fetchone()
        return dict(row) if row else None


def get_questions_by_category(
    category_id: int,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """根据分类获取题目列表"""
    with get_cursor() as cur:
        rows = cur.execute(
            """SELECT * FROM questions
               WHERE category_id = ? AND is_active = 1
               ORDER BY id ASC LIMIT ? OFFSET ?""",
            (category_id, limit, offset),
        ).fetchall()
        return [dict(r) for r in rows]


def get_sequential_question(
    category_id: int,
    last_id: int = 0,
) -> dict | None:
    """顺序取下一题"""
    with get_cursor() as cur:
        row = cur.execute(
            """SELECT * FROM questions
               WHERE category_id = ? AND id > ? AND is_active = 1
               ORDER BY id ASC LIMIT 1""",
            (category_id, last_id),
        ).fetchone()
        return dict(row) if row else None


def get_random_question(category_id: int | None = None) -> dict | None:
    """随机取一题"""
    with get_cursor() as cur:
        if category_id:
            row = cur.execute(
                """SELECT * FROM questions
                   WHERE category_id = ? AND is_active = 1
                   ORDER BY RANDOM() LIMIT 1""",
                (category_id,),
            ).fetchone()
        else:
            row = cur.execute(
                """SELECT * FROM questions
                   WHERE is_active = 1
                   ORDER BY RANDOM() LIMIT 1""",
            ).fetchone()
        return dict(row) if row else None


def get_category_question_count(category_id: int) -> int:
    """获取某分类下题目总数"""
    with get_cursor() as cur:
        row = cur.execute(
            "SELECT COUNT(*) as cnt FROM questions WHERE category_id = ? AND is_active = 1",
            (category_id,),
        ).fetchone()
        return row["cnt"] if row else 0


def get_total_question_count() -> int:
    """获取题目总数"""
    with get_cursor() as cur:
        row = cur.execute(
            "SELECT COUNT(*) as cnt FROM questions WHERE is_active = 1"
        ).fetchone()
        return row["cnt"] if row else 0


def search_questions(keyword: str, limit: int = 50) -> list[dict]:
    """关键词搜索题目"""
    with get_cursor() as cur:
        rows = cur.execute(
            """SELECT * FROM questions
               WHERE is_active = 1
                 AND (question_text LIKE ? OR keywords LIKE ? OR title LIKE ?)
               ORDER BY id DESC LIMIT ?""",
            (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%", limit),
        ).fetchall()
        return [dict(r) for r in rows]


# ============================================================
# 题目写入
# ============================================================
def insert_question(
    question_type: str,
    question_text: str,
    category_id: int = None,
    answer_text: str = None,
    explanation: str = None,
    keywords: str = None,
    difficulty: int = 3,
    title: str = None,
    options: str = None,
    is_ai_generated: int = 0,
    ai_answer_flag: int = 0,
    source_file: str = None,
    source_page: int = None,
) -> int:
    """插入一道题目，返回自增 id"""
    q_uuid = str(uuid.uuid4())
    with get_cursor() as cur:
        cur.execute(
            """INSERT INTO questions
               (uuid, category_id, question_type, difficulty, title,
                question_text, options, answer_text, explanation, keywords,
                is_ai_generated, ai_answer_flag, source_file, source_page)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                q_uuid, category_id, question_type, difficulty, title,
                question_text, options, answer_text, explanation, keywords,
                is_ai_generated, ai_answer_flag, source_file, source_page,
            ),
        )
        return cur.lastrowid


def update_question_answer(
    question_id: int,
    answer_text: str,
    explanation: str = None,
    ai_answer_flag: int = 1,
):
    """更新题目答案"""
    with get_cursor() as cur:
        cur.execute(
            """UPDATE questions
               SET answer_text = ?, explanation = ?, ai_answer_flag = ?, updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (answer_text, explanation, ai_answer_flag, question_id),
        )


def update_question_stats(question_id: int, is_correct: bool):
    """更新题目统计"""
    with get_cursor() as cur:
        cur.execute(
            """UPDATE questions
               SET review_count = review_count + 1,
                   correct_count = correct_count + ?,
                   updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (1 if is_correct else 0, question_id),
        )


# ============================================================
# 用户 / 作答 / 测验 / 统计 → Supabase
# ============================================================
from data.db.supabase_client import *

# 跨库函数：需要同时查 Supabase + goodjob
def get_user_answer_history(user_id: int, limit: int = 10) -> list[dict]:
    ua_rows = _get_all_user_answers(user_id)
    # sort by reviewed_at desc, take top
    ua_rows.sort(key=lambda x: x.get("reviewed_at", ""), reverse=True)
    ua_rows = ua_rows[:limit]
    if not ua_rows: return []
    qids = [r["question_id"] for r in ua_rows]
    with get_cursor() as qcur:
        q_rows = qcur.execute(
            f"SELECT id, question_text, question_type, category_id FROM questions WHERE id IN ({','.join('?'*len(qids))})",
            qids
        ).fetchall()
    q_map = {r["id"]: dict(r) for r in q_rows}
    result = []
    for ua in ua_rows:
        d = dict(ua)
        q = q_map.get(d.get("question_id"), {})
        d["question_text"] = q.get("question_text", "")
        d["question_type"] = q.get("question_type", "")
        d["category_id"] = q.get("category_id")
        result.append(d)
    return result


def get_user_category_progress(user_id: int) -> list[dict]:
    with get_cursor() as qcur:
        cats = qcur.execute("SELECT id, name, sort_order FROM categories WHERE name != '电路分析' ORDER BY sort_order").fetchall()
        all_qs = qcur.execute("SELECT id, category_id FROM questions WHERE is_active=1").fetchall()
    cat_questions = {}
    for q in all_qs: cat_questions.setdefault(q["category_id"], []).append(q["id"])
    ua_rows = _get_all_user_answers(user_id)
    user_correct = {}; user_seen = set()
    for ua in ua_rows:
        user_seen.add(ua.get("question_id"))
        if ua.get("is_correct"): user_correct[ua["question_id"]] = True
    result = []
    for c in cats:
        cid = c["id"]; qlist = cat_questions.get(cid, [])
        reviewed = sum(1 for qid in qlist if qid in user_seen)
        correct = sum(1 for qid in qlist if qid in user_correct)
        result.append({"category_id": cid, "category_name": c["name"], "reviewed_count": reviewed, "correct_count": correct})
    return result


def get_question_type_distribution() -> list[dict]:
    """各题型数量分布"""
    with get_cursor() as cur:
        rows = cur.execute(
            """SELECT question_type, COUNT(*) as count
               FROM questions WHERE is_active = 1
               GROUP BY question_type ORDER BY count DESC"""
        ).fetchall()
        return [dict(r) for r in rows]


def get_category_distribution() -> list[dict]:
    """各分类数量分布"""
    with get_cursor() as cur:
        rows = cur.execute(
            """SELECT c.name, COUNT(q.id) as count
               FROM categories c
               LEFT JOIN questions q ON q.category_id = c.id AND q.is_active = 1
               GROUP BY c.id ORDER BY c.sort_order"""
        ).fetchall()
        return [dict(r) for r in rows]