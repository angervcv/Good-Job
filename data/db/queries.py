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
# 用户查询
# ============================================================
def get_or_create_user(username: str) -> dict:
    """获取或创建用户"""
    with get_userdata_cursor() as cur:
        row = cur.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        if row:
            return dict(row)
        cur.execute(
            "INSERT INTO users (username, display_name) VALUES (?, ?)",
            (username, username),
        )
        row = cur.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        return dict(row)


def get_all_users() -> list[dict]:
    """获取所有用户"""
    with get_userdata_cursor() as cur:
        rows = cur.execute("SELECT * FROM users ORDER BY id").fetchall()
        return [dict(r) for r in rows]


def update_user_stats(user_id: int, is_correct: bool):
    """更新用户统计"""
    with get_userdata_cursor() as cur:
        cur.execute(
            """UPDATE users
               SET total_reviewed = total_reviewed + 1,
                   total_correct = total_correct + ?,
                   last_active = DATE('now', 'localtime')
               WHERE id = ?""",
            (1 if is_correct else 0, user_id),
        )


def update_user_streak(user_id: int):
    """更新连续刷题天数 - 简化版: 直接设 last_active = today"""
    with get_userdata_cursor() as cur:
        cur.execute(
            "UPDATE users SET last_active = DATE('now', 'localtime') WHERE id = ?",
            (user_id,),
        )


# ============================================================
# 作答记录
# ============================================================
def save_answer(
    user_id: int,
    question_id: int,
    user_answer: str,
    is_correct: int | None,
    score: float | None = None,
    feedback: str = None,
    review_session: str = "sequential",
) -> int:
    """保存作答记录"""
    with get_userdata_cursor() as cur:
        cur.execute(
            """INSERT INTO user_answers
               (user_id, question_id, user_answer, is_correct, score, feedback, review_session)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, question_id, user_answer, is_correct, score, feedback, review_session),
        )
        return cur.lastrowid


def get_user_answer_history(user_id: int, limit: int = 10) -> list[dict]:
    """获取用户最近作答记录（跨库查询）"""
    with get_userdata_cursor() as ucur:
        ua_rows = ucur.execute(
            "SELECT * FROM user_answers WHERE user_id=? ORDER BY reviewed_at DESC LIMIT ?",
            (user_id, limit)
        ).fetchall()
    if not ua_rows:
        return []
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
        q = q_map.get(d["question_id"], {})
        d["question_text"] = q.get("question_text", "")
        d["question_type"] = q.get("question_type", "")
        d["category_id"] = q.get("category_id")
        result.append(d)
    return result


def get_user_category_progress(user_id: int) -> list[dict]:
    """获取用户各模块刷题进度（跨库查询）"""
    # 从goodjob获取分类和题目映射
    with get_cursor() as qcur:
        cats = qcur.execute("SELECT id, name, sort_order FROM categories ORDER BY sort_order").fetchall()
        all_qs = qcur.execute("SELECT id, category_id FROM questions WHERE is_active=1").fetchall()
    cat_questions = {}
    for q in all_qs:
        cat_questions.setdefault(q["category_id"], []).append(q["id"])
    # 从userdata获取用户作答
    with get_userdata_cursor() as ucur:
        ua_rows = ucur.execute(
            "SELECT question_id, is_correct FROM user_answers WHERE user_id=?", (user_id,)
        ).fetchall()
    user_correct = {}; user_seen = set()
    for ua in ua_rows:
        user_seen.add(ua["question_id"])
        if ua["is_correct"]:
            user_correct[ua["question_id"]] = True
    result = []
    for c in cats:
        cid = c["id"]; qlist = cat_questions.get(cid, [])
        reviewed = sum(1 for qid in qlist if qid in user_seen)
        correct = sum(1 for qid in qlist if qid in user_correct)
        result.append({"category_id": cid, "category_name": c["name"], "reviewed_count": reviewed, "correct_count": correct})
    return result


def get_daily_question_count(user_id: int, date: str = None) -> int:
    """获取某日刷题数"""
    if date is None:
        date = "DATE('now', 'localtime')"
    else:
        date = f"'{date}'"
    with get_userdata_cursor() as cur:
        row = cur.execute(
            f"""SELECT COUNT(*) as cnt FROM user_answers
                WHERE user_id = ? AND DATE(reviewed_at) = {date}""",
            (user_id,),
        ).fetchone()
        return row["cnt"] if row else 0


# ============================================================
# 每日测验
# ============================================================
def create_daily_quiz(user_id: int, question_ids: list[int]) -> int:
    """创建每日测验记录"""
    with get_userdata_cursor() as cur:
        cur.execute(
            """INSERT INTO daily_quizzes
               (user_id, quiz_date, questions_json, max_score)
               VALUES (?, DATE('now', 'localtime'), ?, ?)""",
            (user_id, json.dumps(question_ids), len(question_ids) * 10),
        )
        return cur.lastrowid


def get_today_quiz(user_id: int) -> dict | None:
    """获取今日测验"""
    with get_userdata_cursor() as cur:
        row = cur.execute(
            """SELECT * FROM daily_quizzes
               WHERE user_id = ? AND quiz_date = DATE('now', 'localtime')
               ORDER BY id DESC LIMIT 1""",
            (user_id,),
        ).fetchone()
        return dict(row) if row else None


def complete_quiz(quiz_id: int, total_score: float, answers_json: str):
    """完成测验"""
    with get_userdata_cursor() as cur:
        cur.execute(
            """UPDATE daily_quizzes
               SET total_score = ?, answers_json = ?, completed = 1,
                   completed_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (total_score, answers_json, quiz_id),
        )


# ============================================================
# 统计查询
# ============================================================
def get_leaderboard_by_count(limit: int = 20) -> list[dict]:
    """刷题数排行榜"""
    with get_userdata_cursor() as cur:
        rows = cur.execute(
            """SELECT username, total_reviewed, total_correct,
                      ROUND(CAST(total_correct AS REAL) / MAX(total_reviewed, 1) * 100, 1) as accuracy
               FROM users
               WHERE total_reviewed > 0
               ORDER BY total_reviewed DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_leaderboard_by_accuracy(min_reviewed: int = 20, limit: int = 20) -> list[dict]:
    """正确率排行榜"""
    with get_userdata_cursor() as cur:
        rows = cur.execute(
            """SELECT username, total_reviewed,
                      ROUND(CAST(total_correct AS REAL) / MAX(total_reviewed, 1) * 100, 1) as accuracy
               FROM users
               WHERE total_reviewed >= ?
               ORDER BY accuracy DESC LIMIT ?""",
            (min_reviewed, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def get_weekly_stats(user_id: int) -> list[dict]:
    """最近 7 天每日刷题统计"""
    with get_userdata_cursor() as cur:
        rows = cur.execute(
            """SELECT DATE(reviewed_at) as date,
                      COUNT(*) as count,
                      SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) as correct
               FROM user_answers
               WHERE user_id = ? AND reviewed_at >= DATE('now', '-7 days', 'localtime')
               GROUP BY DATE(reviewed_at)
               ORDER BY date""",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


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