"""
Supabase 数据层 - 用户数据永久保存
"""
import json
import streamlit as st
from datetime import date, datetime
from supabase import create_client
import config


def _client():
    return create_client(config.SUPABASE_URL, config.SUPABASE_KEY)


# ========================================
# Users
# ========================================
def get_or_create_user(username: str) -> dict:
    c = _client()
    try:
        r = c.table("users").select("*").eq("username", username).execute()
        if r.data:
            return r.data[0]
        r2 = c.table("users").insert({"username": username}).execute()
        if r2.data:
            return r2.data[0]
    except Exception as e:
        print(f"Supabase error: {e}")
    # 回退：返回内存模拟用户
    return {"id": hash(username) % 100000, "username": username, "total_reviewed": 0, "total_correct": 0}


@st.cache_data(ttl=60)
def get_all_users_cached() -> list[dict]:
    try: return _client().table("users").select("*").order("id").execute().data or []
    except: return []

def get_all_users() -> list[dict]:
    return get_all_users_cached()


def update_user_stats(user_id: int, is_correct: bool):
    try:
        c = _client()
        user = c.table("users").select("total_reviewed,total_correct").eq("id", user_id).execute().data[0]
        c.table("users").update({
            "total_reviewed": user["total_reviewed"] + 1,
            "total_correct": user["total_correct"] + (1 if is_correct else 0),
            "last_active": str(date.today()),
        }).eq("id", user_id).execute()
    except: pass


def update_user_streak(user_id: int):
    try: _client().table("users").update({"last_active": str(date.today())}).eq("id", user_id).execute()
    except: pass


# ========================================
# User Answers
# ========================================
def save_answer(user_id: int, question_id: int, user_answer: str,
                is_correct: int | None, score: float, feedback: str,
                review_session: str) -> int:
    try:
        r = _client().table("user_answers").insert({
            "user_id": user_id, "question_id": question_id,
            "user_answer": user_answer, "is_correct": is_correct,
            "score": score, "feedback": feedback, "review_session": review_session,
        }).execute()
        return r.data[0]["id"] if r.data else 0
    except: return 0


def get_user_answer_history(user_id: int, limit: int = 10) -> list[dict]:
    try:
        r = _client().table("user_answers").select("*").eq("user_id", user_id)\
            .order("reviewed_at", desc=True).limit(limit).execute()
        return r.data or []
    except: return []


def get_all_user_answers(user_id: int) -> list[dict]:
    try:
        r = _client().table("user_answers").select("*").eq("user_id", user_id)\
            .order("id").limit(1000).execute()
        return r.data or []
    except: return []


# ========================================
# Daily Quiz
# ========================================
def create_daily_quiz(user_id: int, question_ids: list[int]) -> int:
    try:
        r = _client().table("daily_quizzes").insert({
            "user_id": user_id, "quiz_date": str(date.today()),
            "questions_json": json.dumps(question_ids),
        }).execute()
        return r.data[0]["id"] if r.data else 0
    except: return 0


def get_today_quiz(user_id: int) -> dict | None:
    try:
        r = _client().table("daily_quizzes").select("*")\
            .eq("user_id", user_id).eq("quiz_date", str(date.today()))\
            .limit(1).execute()
        return r.data[0] if r.data else None
    except: return None


def complete_quiz(quiz_id: int, total_score: float, answers_json: str):
    try:
        _client().table("daily_quizzes").update({
            "total_score": total_score, "answers_json": answers_json,
            "completed": 1, "completed_at": datetime.now().isoformat(),
        }).eq("id", quiz_id).execute()
    except: pass


def get_today_scoreboard() -> list[dict]:
    try:
        r = _client().table("daily_quizzes").select("total_score, users(username)")\
            .eq("quiz_date", str(date.today())).eq("completed", 1)\
            .order("total_score", desc=True).execute()
        return r.data or []
    except: return []


def get_past_quizzes(user_id: int) -> list[dict]:
    try:
        r = _client().table("daily_quizzes").select("*")\
            .eq("user_id", user_id).eq("completed", 1)\
            .lt("quiz_date", str(date.today()))\
            .order("quiz_date", desc=True).limit(30).execute()
        return r.data or []
    except: return []


def get_quiz_notes(quiz_id: int) -> list[dict]:
    try:
        r = _client().table("daily_quizzes").select("quiz_notes").eq("id", quiz_id).execute()
        if r.data:
            return json.loads(r.data[0].get("quiz_notes", "[]") or "[]")
    except: pass
    return []


def save_quiz_notes(quiz_id: int, notes: list[dict]):
    try:
        _client().table("daily_quizzes").update({
            "quiz_notes": json.dumps(notes, ensure_ascii=False)
        }).eq("id", quiz_id).execute()
    except: pass


# ========================================
# Review Progress
# ========================================
def load_position(user_id: int, category_id: int | None) -> int:
    try:
        c = _client()
        if category_id is None:
            r = c.table("review_progress").select("last_question_id")\
                .eq("user_id", user_id).is_("category_id", "null").limit(1).execute()
        else:
            r = c.table("review_progress").select("last_question_id")\
                .eq("user_id", user_id).eq("category_id", category_id).limit(1).execute()
        return r.data[0]["last_question_id"] if r.data else 0
    except: return 0


def save_position(user_id: int, category_id: int | None, last_id: int):
    try:
        c = _client()
        if category_id is None:
            c.table("review_progress").delete().eq("user_id", user_id)\
                .is_("category_id", "null").execute()
            c.table("review_progress").insert({
                "user_id": user_id, "category_id": None,
                "last_question_id": last_id,
            }).execute()
        else:
            c.table("review_progress").delete().eq("user_id", user_id)\
                .eq("category_id", category_id).execute()
            c.table("review_progress").insert({
                "user_id": user_id, "category_id": category_id,
                "last_question_id": last_id,
            }).execute()
    except: pass


# ========================================
# Daily Stats & Leaderboard
# ========================================
def get_daily_question_count(user_id: int) -> int:
    try:
        r = _client().table("user_answers").select("id")\
            .eq("user_id", user_id).gte("reviewed_at", str(date.today()))\
            .limit(1000).execute()
        return len(r.data) if r.data else 0
    except: return 0


def get_weekly_stats(user_id: int) -> list[dict]:
    try:
        from datetime import timedelta
        today = date.today()
        result = []
        for i in range(6, -1, -1):
            d = str(today - timedelta(days=i))
            r = _client().table("user_answers").select("id")\
                .eq("user_id", user_id).gte("reviewed_at", d)\
                .lt("reviewed_at", str(today - timedelta(days=i-1)) if i < 6 else str(today + timedelta(days=1)))\
                .limit(1000).execute()
            result.append({"date": d, "count": len(r.data) if r.data else 0})
        return result
    except: return [{"date": str(date.today() - __import__('datetime').timedelta(days=i)),
                      "count": 0} for i in range(6, -1, -1)]


@st.cache_data(ttl=60)
def get_leaderboard_by_count(limit: int = 20) -> list[dict]:
    try:
        r = _client().table("users").select("username,total_reviewed,total_correct")\
            .order("total_reviewed", desc=True).limit(limit).execute()
        data = r.data or []
        for d in data:
            d["accuracy"] = round(d.get("total_correct", 0) / max(d.get("total_reviewed", 1), 1) * 100, 1)
        return data
    except: return []


def get_leaderboard_by_accuracy(min_reviewed: int = 20, limit: int = 20) -> list[dict]:
    try:
        r = _client().table("users").select("username,total_reviewed,total_correct")\
            .gte("total_reviewed", min_reviewed).order("total_reviewed", desc=True).limit(200).execute()
        data = r.data or []
        for d in data:
            d["accuracy"] = round(d.get("total_correct", 0) / max(d.get("total_reviewed", 1), 1) * 100, 1)
        data.sort(key=lambda x: x["accuracy"], reverse=True)
        return data[:limit]
    except: return []


# ========================================
# Comments
# ========================================
def get_question_comments(question_id: int, limit: int = 10) -> list[dict]:
    try:
        r = _client().table("comments").select("content, created_at, users(username)")\
            .eq("question_id", question_id)\
            .order("created_at", desc=True).limit(limit).execute()
        return r.data or []
    except: return []


def add_comment(user_id: int, question_id: int, content: str):
    try:
        _client().table("comments").insert({
            "user_id": user_id, "question_id": question_id, "content": content,
        }).execute()
    except: pass
