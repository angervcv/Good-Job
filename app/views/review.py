"""
刷题页面 - 核心功能
支持顺序刷题和随机抽题两种模式
"""

import streamlit as st
from app.components.navigation import require_login
from app.components.question_card import (
    render_question_card,
    render_answer_section,
    render_self_scoring,
    render_choice_input,
    render_text_input,
)
from app.utils.sampling import (
    get_next_question_sequential,
    get_next_question_random,
    get_occurrence_count,
    check_has_questions,
)
from app.utils.scoring import process_answer
from app.session_state import reset_review
from data.db.queries import get_all_categories


def render_review():
    """渲染刷题页面"""
    st.title("模块刷题")

    user = require_login()
    user_id = user["id"]

    if not check_has_questions():
        st.warning("题库中还没有题目，请先在管理后台导入题目数据。")
        return

    # === 顶部控制栏 ===
    _render_controls()

    # === 题目展示区 ===
    if st.session_state.current_question is None:
        _load_next_question()

    question = st.session_state.current_question

    if question is None:
        st.info("该模块已无更多题目，请切换模块或模式。")
        if st.button("重置进度"):
            reset_review()
            st.session_state.sequential_pos = {}
            st.rerun()
        return

    st.divider()

    # 显示题目
    render_question_card(question)

    # 随机模式：显示出现次数
    if st.session_state.review_mode == "random":
        occ = get_occurrence_count(question["id"])
        if occ > 0:
            st.info(f"本题在本次刷题中已出现 **{occ}** 次")

    st.divider()

    # === 作答区域 ===
    qtype = question.get("question_type", "short_answer")

    # 显示答案前的状态
    if not st.session_state.answer_submitted:
        _render_answer_input(question, user_id)

    # 显示答案的状态
    if st.session_state.show_answer:
        _render_result(question)


def _render_controls():
    """渲染顶部控制栏"""
    categories = get_all_categories()

    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        # 模块选择
        cat_options = {None: "全部模块"}
        for c in categories:
            cat_options[c["id"]] = c["name"]

        selected_cat = st.selectbox(
            "选择模块",
            options=list(cat_options.keys()),
            format_func=lambda x: cat_options[x],
            key="cat_selector",
            on_change=_on_category_change,
        )

    with col2:
        # 模式选择
        mode = st.radio(
            "刷题模式",
            options=["sequential", "random"],
            format_func=lambda x: "顺序刷题" if x == "sequential" else "随机抽题",
            horizontal=True,
            key="mode_selector",
            on_change=_on_mode_change,
        )

    with col3:
        if st.button("换一题", use_container_width=True, key="skip_btn"):
            reset_review()
            st.session_state.current_question = None
            st.rerun()


def _render_answer_input(question: dict, user_id: int):
    """渲染作答输入区"""
    qtype = question.get("question_type", "short_answer")

    # 选择题：渲染选项
    if qtype in ("single_choice", "multiple_choice"):
        user_answer = render_choice_input(question)
    else:
        user_answer = render_text_input(question)

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("提交答案", use_container_width=True, type="primary"):
            if user_answer is None or not user_answer.strip():
                st.warning("请先作答")
                return

            # 所有题型统一通过 process_answer 评分
            # 客观题自动判分，主观题 AI 评分
            with st.spinner("AI 批改中..."):
                result = process_answer(
                    user_id=user_id,
                    question=question,
                    user_answer=user_answer,
                    review_session=st.session_state.review_mode,
                    self_score=None,
                )
            st.session_state.last_result = result

            # 保存用户答案用于展示
            st.session_state.last_user_answer = user_answer
            st.session_state.answer_submitted = True
            st.session_state.show_answer = True
            st.rerun()

    with col2:
        if st.button("直接看答案", use_container_width=True):
            st.session_state.answer_submitted = True
            st.session_state.show_answer = True
            st.session_state.skipped = True
            st.rerun()


def _render_result(question: dict):
    """渲染答案和评分结果"""
    skipped = st.session_state.get("skipped", False)
    result = st.session_state.get("last_result", {})

    # 显示用户作答
    if not skipped:
        user_answer = st.session_state.get("last_user_answer", "")
        if user_answer:
            st.markdown("### 你的答案")
            st.info(user_answer)

    # 显示评分结果
    if not skipped and result:
        score = result.get("score", 0)
        is_correct = result.get("is_correct", False)
        feedback = result.get("feedback", "")
        grading_mode = result.get("grading_mode", "auto")

        st.markdown(f"### 评分: {score:.0f}/10")
        if is_correct:
            st.success("正确")
        elif score >= 6:
            st.warning("部分正确")
        else:
            st.error("错误")
        if feedback:
            st.caption(f"评价: {feedback}")
        st.caption(f"评分方式: {'自动判分' if grading_mode == 'auto' else 'AI评分'}")

    # 显示参考答案
    render_answer_section(question)

    if skipped:
        st.info("已跳过此题")

    # 评论区
    st.divider()
    _render_comment_section(question)

    if st.button("下一题", use_container_width=True, type="primary"):
        _go_next_question()


def _load_next_question():
    """加载下一题"""
    user_id = require_login()["id"]
    mode = st.session_state.review_mode
    cat_id = st.session_state.get("review_category_id")

    if mode == "sequential":
        question = get_next_question_sequential(user_id, cat_id)
    else:
        question = get_next_question_random(cat_id)

    st.session_state.current_question = question


def _render_comment_section(question: dict):
    """渲染题目评论区"""
    from data.db.connection import get_cursor

    st.markdown("### 讨论区")
    qid = question["id"]

    # 加载已有评论
    with get_cursor() as cur:
        rows = cur.execute(
            """SELECT c.content, c.created_at, u.username
               FROM comments c JOIN users u ON c.user_id = u.id
               WHERE c.question_id = ? ORDER BY c.created_at DESC LIMIT 10""",
            (qid,),
        ).fetchall()

    if rows:
        for r in rows:
            st.caption(f"**{r['username']}** · {r['created_at'][:16]}")
            st.markdown(r["content"])
            st.divider()
    else:
        st.caption("暂无讨论，留下你的笔记吧")

    # 添加评论
    with st.form(f"comment_form_{qid}", clear_on_submit=True):
        comment = st.text_input("添加笔记或讨论", placeholder="记录你的思路、疑问或总结...", label_visibility="collapsed")
        if st.form_submit_button("发布", use_container_width=True):
            if comment.strip():
                user = require_login()
                with get_cursor() as cur:
                    cur.execute(
                        "INSERT INTO comments (user_id, question_id, content) VALUES (?, ?, ?)",
                        (user["id"], qid, comment.strip()),
                    )
                st.rerun()


def _go_next_question():
    """跳转到下一题"""
    reset_review()
    st.session_state.current_question = None
    st.rerun()


def _on_category_change():
    """模块切换回调"""
    reset_review()
    st.session_state.current_question = None
    st.session_state.sequential_pos = {}
    st.session_state.random_history = []


def _on_mode_change():
    """模式切换回调"""
    reset_review()
    st.session_state.current_question = None
    st.session_state.sequential_pos = {}
    st.session_state.random_history = []