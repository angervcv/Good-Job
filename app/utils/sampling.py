"""
抽题算法
"""

import random
from data.db.queries import (
    get_sequential_question,
    get_random_question,
    get_category_question_count,
)
from data.db.connection import get_cursor
import config


def _load_position(user_id: int, category_id: int | None) -> int:
    """从数据库加载顺序刷题位置"""
    with get_cursor() as cur:
        if category_id is None:
            row = cur.execute(
                "SELECT last_question_id FROM review_progress WHERE user_id = ? AND category_id IS NULL",
                (user_id,),
            ).fetchone()
        else:
            row = cur.execute(
                "SELECT last_question_id FROM review_progress WHERE user_id = ? AND category_id = ?",
                (user_id, category_id),
            ).fetchone()
        return row["last_question_id"] if row else 0


def _save_position(user_id: int, category_id: int | None, last_id: int):
    """保存顺序刷题位置到数据库"""
    with get_cursor() as cur:
        if category_id is None:
            cur.execute(
                "DELETE FROM review_progress WHERE user_id = ? AND category_id IS NULL",
                (user_id,),
            )
            cur.execute(
                "INSERT INTO review_progress (user_id, category_id, last_question_id, updated_at) VALUES (?, NULL, ?, CURRENT_TIMESTAMP)",
                (user_id, last_id),
            )
        else:
            cur.execute(
                "DELETE FROM review_progress WHERE user_id = ? AND category_id = ?",
                (user_id, category_id),
            )
            cur.execute(
                "INSERT INTO review_progress (user_id, category_id, last_question_id, updated_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
                (user_id, category_id, last_id),
            )


def get_next_question_sequential(user_id: int, category_id: int | None) -> dict | None:
    """顺序刷题模式：取下一道题，从数据库恢复进度"""
    import streamlit as st

    # 优先从数据库读取上次进度
    last_id = _load_position(user_id, category_id)
    # 如果 session_state 中有更新的位置（本次会话刷的），用 session 的
    pos_key = str(category_id) if category_id else "all"
    session_last = st.session_state.sequential_pos.get(pos_key, 0)
    if session_last > last_id:
        last_id = session_last

    # 尝试取下一题
    if category_id:
        question = get_sequential_question(category_id, last_id)
    else:
        question = _get_sequential_all_categories(last_id)

    if question:
        st.session_state.sequential_pos[pos_key] = question["id"]
        _save_position(user_id, category_id, question["id"])
        return question

    # 如果到达末尾，回到开头
    st.session_state.sequential_pos[pos_key] = 0
    _save_position(user_id, category_id, 0)
    if category_id:
        question = get_sequential_question(category_id, 0)
    else:
        question = _get_sequential_all_categories(0)

    if question:
        st.session_state.sequential_pos[pos_key] = question["id"]
        _save_position(user_id, category_id, question["id"])

    return question


def _get_sequential_all_categories(last_id: int) -> dict | None:
    """跨分类顺序取题"""
    with get_cursor() as cur:
        row = cur.execute(
            """SELECT * FROM questions
               WHERE id > ? AND is_active = 1
               ORDER BY id ASC LIMIT 1""",
            (last_id,),
        ).fetchone()
        return dict(row) if row else None


def get_next_question_random(category_id: int | None) -> dict | None:
    """随机抽题模式：从指定分类随机抽取

    题目可以重复出现，标注第几次出现
    """
    question = get_random_question(category_id)

    if question:
        import streamlit as st
        # 记录出现次数
        qid = question["id"]
        history = st.session_state.random_history
        # history: [(question_id, occurrence_count), ...]
        found = False
        for i, (hqid, count) in enumerate(history):
            if hqid == qid:
                history[i] = (hqid, count + 1)
                found = True
                break
        if not found:
            history.append((qid, 1))
        st.session_state.random_history = history

    return question


def get_occurrence_count(question_id: int) -> int:
    """获取某题在本次随机刷题中出现的次数"""
    import streamlit as st
    for qid, count in st.session_state.random_history:
        if qid == question_id:
            return count
    return 0


def select_daily_quiz_questions(user_id: int = None) -> list[dict]:
    """为每日测验抽取 10 道题

    确保覆盖所有 4 个分类，每个分类至少 2 题
    """
    total_count = config.DAILY_QUIZ_COUNT
    questions = []

    with get_cursor() as cur:
        # 获取所有分类
        categories = cur.execute("SELECT id, name FROM categories ORDER BY sort_order").fetchall()
        cats = [dict(c) for c in categories]

    if not cats:
        return []

    base_per_cat = total_count // len(cats)  # 2
    extra = total_count - base_per_cat * len(cats)  # 2

    for i, cat in enumerate(cats):
        # 剩余题数分给前面几个分类
        count = base_per_cat + (1 if i < extra else 0)

        with get_cursor() as cur:
            rows = cur.execute(
                """SELECT * FROM questions
                   WHERE category_id = ? AND is_active = 1
                   ORDER BY RANDOM() LIMIT ?""",
                (cat["id"], count),
            ).fetchall()
            questions.extend([dict(r) for r in rows])

    # 如果不够 10 题（题库不足），补充
    if len(questions) < total_count:
        existing_ids = [q["id"] for q in questions]
        with get_cursor() as cur:
            rows = cur.execute(
                f"""SELECT * FROM questions
                   WHERE is_active = 1 AND id NOT IN ({','.join('?'*len(existing_ids))})
                   ORDER BY RANDOM() LIMIT ?""",
                (*existing_ids, total_count - len(questions)),
            ).fetchall()
            questions.extend([dict(r) for r in rows])

    random.shuffle(questions)
    return questions[:total_count]


def check_has_questions() -> bool:
    """检查题库是否有题目"""
    with get_cursor() as cur:
        row = cur.execute(
            "SELECT COUNT(*) as cnt FROM questions WHERE is_active = 1"
        ).fetchone()
        return (row["cnt"] if row else 0) > 0