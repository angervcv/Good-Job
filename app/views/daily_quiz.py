"""
每日测验页面
每天一套试卷，10道题，每题10分
"""

import json
from datetime import date
import streamlit as st
from app.components.navigation import require_login
from app.components.question_card import render_question_card, render_answer_section
from app.utils.sampling import select_daily_quiz_questions, check_has_questions
from app.utils.scoring import process_quiz_answer
from app.session_state import reset_quiz
from data.db.queries import (
    get_today_quiz,
    create_daily_quiz,
    complete_quiz,
    get_question_by_id,
)
from data.db.connection import get_cursor


def render_daily_quiz():
    """渲染每日测验页面"""
    st.title("每日测验")

    user = require_login()
    user_id = user["id"]

    if not check_has_questions():
        st.warning("题库中还没有题目，请先在管理后台导入题目数据。")
        return

    today = date.today()

    # 检查今日是否已有测验
    existing_quiz = get_today_quiz(user_id)

    if existing_quiz and existing_quiz.get("completed"):
        _render_completed_quiz(existing_quiz)

    elif st.session_state.quiz_started:
        _render_quiz_in_progress(user_id)

    else:
        _render_quiz_start(user_id, existing_quiz)


def _render_quiz_start(user_id: int, existing_quiz: dict | None):
    """渲染测验开始界面"""
    today = date.today()
    st.markdown(f"### {today.strftime('%Y年%m月%d日')} 每日测验")

    st.markdown("""
    <div style="background: #F0F7FF; border-radius: 12px; padding: 24px; margin: 16px 0;">
        <h4 style="margin-top: 0;">测验规则</h4>
        <ul>
            <li>共 <b>10 道题</b>，每题 <b>10 分</b>，满分 <b>100 分</b></li>
            <li>题目从 4 个模块随机抽取，覆盖所有知识点</li>
            <li>选择题和填空题自动判分，简答/计算/画图题由 AI 评分</li>
            <li>无时间限制，可在今天内随时作答</li>
            <li>每天仅限一次测验</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    if existing_quiz and not existing_quiz.get("completed"):
        st.info("你有一个未完成的测验，可以继续作答。")

    if st.button("开始今日测验", use_container_width=True, type="primary"):
        # 抽取 10 道题
        questions = select_daily_quiz_questions(user_id)

        if len(questions) < 10:
            st.warning(f"题库数量不足，当前只有 {len(questions)} 道题。建议先导入更多题目。")
            if len(questions) == 0:
                return

        # 创建测验记录
        question_ids = [q["id"] for q in questions]
        quiz_id = create_daily_quiz(user_id, question_ids)

        st.session_state.quiz_questions = questions
        st.session_state.quiz_answers = {}
        st.session_state.quiz_current_idx = 0
        st.session_state.quiz_started = True
        st.session_state.quiz_submitted = False
        st.session_state.quiz_results = None
        st.session_state.quiz_id = quiz_id
        st.rerun()


def _render_quiz_in_progress(user_id: int):
    """渲染测验进行中界面"""
    questions = st.session_state.quiz_questions
    current_idx = st.session_state.quiz_current_idx
    total = len(questions)

    if current_idx >= total:
        _render_quiz_review(user_id)
        return

    # 进度条
    st.progress(current_idx / total, text=f"第 {current_idx + 1}/{total} 题")

    question = questions[current_idx]

    # 题目展示
    st.markdown(f"### 第 {current_idx + 1} 题（10 分）")
    render_question_card(question)

    # 作答区
    qtype = question.get("question_type", "short_answer")

    if qtype in ("single_choice", "multiple_choice"):
        from app.components.question_card import render_choice_input
        user_answer = render_choice_input(question)
    else:
        from app.components.question_card import render_text_input
        user_answer = render_text_input(question, key_suffix="_quiz")

    # 导航按钮 - 按下一题/上一题时自动保存答案
    col1, col2 = st.columns([1, 1])

    with col1:
        if current_idx > 0:
            if st.button("上一题", use_container_width=True):
                if user_answer:
                    st.session_state.quiz_answers[current_idx] = user_answer
                st.session_state.quiz_current_idx -= 1
                st.rerun()

    with col2:
        if current_idx < total - 1:
            if st.button("下一题", use_container_width=True, type="primary"):
                if user_answer:
                    st.session_state.quiz_answers[current_idx] = user_answer
                st.session_state.quiz_current_idx += 1
                st.rerun()
        else:
            if st.button("交卷评分", use_container_width=True, type="primary"):
                if user_answer:
                    st.session_state.quiz_answers[current_idx] = user_answer
                unanswered = total - len(st.session_state.quiz_answers)
                if unanswered > 0:
                    st.warning(f"还有 {unanswered} 题未作答，确定交卷吗？")
                st.session_state.quiz_current_idx = total
                st.rerun()


def _render_quiz_review(user_id: int):
    """渲染交卷评分页面"""
    st.markdown("## 提交评分中...")

    questions = st.session_state.quiz_questions
    answers = st.session_state.quiz_answers

    if st.session_state.quiz_results is None:
        results = []
        total_score = 0

        progress_bar = st.progress(0)
        status_text = st.empty()

        with st.spinner("AI 批改中..."):
            for i, question in enumerate(questions):
                status_text.text(f"正在评分: 第 {i + 1}/{len(questions)} 题...")
                progress_bar.progress((i + 1) / len(questions))

                user_answer = answers.get(i, "")

                if not user_answer:
                    result = {"score": 0, "is_correct": False, "feedback": "未作答", "grading_mode": "auto"}
                else:
                    result = process_quiz_answer(user_id, question, user_answer)

                results.append({
                    "question_id": question["id"],
                    "user_answer": user_answer,
                    "result": result,
                })
                total_score += result.get("score", 0)

        st.session_state.quiz_results = {
            "results": results,
            "total_score": round(total_score, 1),
        }

        # 完成测验
        answers_json = json.dumps(
            {str(r["question_id"]): r["user_answer"] for r in results},
            ensure_ascii=False,
        )
        complete_quiz(
            st.session_state.quiz_id,
            st.session_state.quiz_results["total_score"],
            answers_json,
        )

        progress_bar.empty()
        status_text.empty()

    _render_completed_quiz_detail()


def _render_completed_quiz_detail():
    """渲染测验得分详情"""
    results_data = st.session_state.quiz_results
    total_score = results_data["total_score"]
    results = results_data["results"]
    questions = st.session_state.quiz_questions

    # 得分统计
    st.markdown(f"## 得分: {total_score}/100")

    # 等级判定
    if total_score >= 90:
        grade = "夯爆了"
        color = "#2E7D32"
    elif total_score >= 70:
        grade = "人上人"
        color = "#1565C0"
    elif total_score >= 60:
        grade = "NPC"
        color = "#FF8F00"
    else:
        grade = "拉完了"
        color = "#C62828"

    st.markdown(f"<h3 style='color: {color};'>{grade}</h3>", unsafe_allow_html=True)

    # 各题详情
    st.markdown("### 各题详情")

    for i, (question, result_item) in enumerate(zip(questions, results)):
        r = result_item["result"]
        score = r.get("score", 0)
        is_correct = r.get("is_correct", False)
        feedback = r.get("feedback", "")
        grading_mode = r.get("grading_mode", "auto")

        with st.expander(
            f"第 {i + 1} 题 | {'✅' if score >= 6 else '❌'} {score:.0f}/10分 | "
            f"{question.get('question_text', '')[:60]}..."
        ):
            st.markdown(f"**题目：** {question.get('question_text', '')}")

            user_answer = result_item.get("user_answer", "")
            if user_answer:
                st.markdown(f"**你的答案：** {user_answer}")

            st.markdown(f"**得分：** {score}/10")
            st.markdown(f"**评分方式：** {'自动判分' if grading_mode == 'auto' else 'AI评分'}")
            if feedback:
                st.markdown(f"**评价：** {feedback}")

            st.divider()
            from app.components.question_card import render_answer_section
            render_answer_section(question)

            # 评论区
            _render_quiz_comment(question["id"])

    # 重新测验按钮
    st.info("今日测验已完成！明天再来吧。")

    if st.button("返回首页"):
        st.session_state.current_page = "首页"
        st.rerun()


def _render_quiz_comment(qid: int):
    """在测验回顾中渲染单题评论区"""
    from data.db.connection import get_cursor
    from app.components.navigation import require_login

    st.markdown("#### 讨论")
    with get_cursor() as cur:
        rows = cur.execute(
            """SELECT c.content, c.created_at, u.username
               FROM comments c JOIN users u ON c.user_id = u.id
               WHERE c.question_id = ? ORDER BY c.created_at DESC LIMIT 5""",
            (qid,),
        ).fetchall()
    if rows:
        for r in rows:
            st.caption(f"**{r['username']}** · {r['created_at'][:16]}")
            st.markdown(r["content"])
    else:
        st.caption("暂无讨论")

    with st.form(f"quiz_comment_{qid}", clear_on_submit=True):
        c = st.text_input("添加笔记", key=f"qc_{qid}", placeholder="记录思路或疑问...", label_visibility="collapsed")
        if st.form_submit_button("发布"):
            if c.strip():
                user = require_login()
                with get_cursor() as cur:
                    cur.execute(
                        "INSERT INTO comments (user_id, question_id, content) VALUES (?, ?, ?)",
                        (user["id"], qid, c.strip()),
                    )
                st.rerun()


def _render_completed_quiz(existing_quiz: dict):
    """渲染已完成的测验结果（含完整复盘）"""
    from data.db.connection import get_cursor

    total_score = existing_quiz.get('total_score', 0)
    st.markdown(f"## 得分: {total_score}/100")

    if total_score >= 90:
        grade = "夯爆了"; color = "#2E7D32"
    elif total_score >= 70:
        grade = "人上人"; color = "#1565C0"
    elif total_score >= 60:
        grade = "NPC"; color = "#FF8F00"
    else:
        grade = "拉完了"; color = "#C62828"
    st.markdown(f"<h3 style='color: {color};'>{grade}</h3>", unsafe_allow_html=True)

    # 加载题目和答案详情
    try:
        question_ids = json.loads(existing_quiz.get("questions_json", "[]"))
        answers = json.loads(existing_quiz.get("answers_json", "{}"))
    except json.JSONDecodeError:
        st.info("每天仅限一次测验，明天再来吧！")
        return

    with get_cursor() as cur:
        questions = []
        for qid in question_ids:
            row = cur.execute("SELECT * FROM questions WHERE id=?", (int(qid),)).fetchone()
            if row:
                questions.append(dict(row))

    if not questions:
        st.info("每天仅限一次测验，明天再来吧！")
        return

    st.markdown("### 各题详情")
    for i, q in enumerate(questions):
        qid = str(q["id"])
        user_ans = answers.get(qid, "")
        score = 10 if user_ans and q.get("answer_text", "")[:3] == user_ans[:3] else 0  # rough estimate for objective

        with st.expander(
            f"第 {i + 1} 题 | {'✅' if score >= 6 else '❌'} {score:.0f}/10分 | "
            f"{(q.get('question_text', ''))[:60]}..."
        ):
            st.markdown(f"**题目：** {q.get('question_text', '')}")
            if user_ans:
                st.markdown(f"**你的答案：** {user_ans}")
            else:
                st.caption("未作答")
            st.divider()
            from app.components.question_card import render_answer_section
            render_answer_section(q)
            _render_quiz_comment(q["id"])

    st.info("每天仅限一次测验，明天再来吧！")

    if st.button("返回首页"):
        reset_quiz()
        st.session_state.current_page = "首页"
        st.rerun()