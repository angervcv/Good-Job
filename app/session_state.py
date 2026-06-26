"""
Session State 管理
"""

import streamlit as st

# 默认值定义
DEFAULTS = {
    # 用户
    "user": None,
    "username": "",
    "user_logged_in": False,
    # 导航
    "current_page": "首页",
    # 刷题状态
    "review_mode": "sequential",  # sequential | random
    "review_category_id": None,  # None = 全部
    "current_question": None,
    "answer_submitted": False,
    "show_answer": False,
    "last_user_answer": "",
    "last_result": None,
    "skipped": False,
    "self_score": 100,
    "question_history": [],  # 已做题目的ID栈，支持上一题
    "sequential_pos": {},  # {category_id: last_question_id}
    "random_history": [],  # [(question_id, occurrence_count), ...]
    # 每日测验
    "quiz_questions": [],
    "quiz_answers": {},
    "quiz_current_idx": 0,
    "quiz_started": False,
    "quiz_submitted": False,
    "quiz_results": None,
    "quiz_id": None,
    # 管理
    "admin_tab": "overview",
}


def init_session():
    """初始化 session state，只设置缺失的 key"""
    for key, default in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = default


def reset_review():
    """重置刷题状态"""
    st.session_state.answer_submitted = False
    st.session_state.show_answer = False
    st.session_state.last_user_answer = ""
    st.session_state.last_result = None
    st.session_state.skipped = False
    st.session_state.self_score = 100
    st.session_state.current_question = None


def reset_quiz():
    """重置每日测验状态"""
    st.session_state.quiz_questions = []
    st.session_state.quiz_answers = {}
    st.session_state.quiz_current_idx = 0
    st.session_state.quiz_started = False
    st.session_state.quiz_submitted = False
    st.session_state.quiz_results = None
    st.session_state.quiz_id = None


def switch_mode(mode: str):
    """切换刷题模式"""
    st.session_state.review_mode = mode
    reset_review()
    st.session_state.sequential_pos = {}
    st.session_state.random_history = []


def set_category(category_id: int | None):
    """切换刷题模块"""
    st.session_state.review_category_id = category_id
    reset_review()
    st.session_state.sequential_pos = {}
    st.session_state.random_history = []