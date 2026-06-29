"""
统计排行页面
"""

import streamlit as st
from app.components.navigation import require_login
from app.components.stats_chart import (
    render_overall_stats,
    render_category_progress_bars,
    render_weekly_heatmap,
    render_category_radar,
    render_type_pie,
    render_leaderboard,
)
from app.utils.sampling import check_has_questions


def render_statistics():
    """渲染统计排行页面"""
    st.title("统计排行")

    user = require_login()
    user_id = user["id"]

    if not check_has_questions():
        st.warning("题库中还没有题目，请先在管理后台导入题目数据。")
        return

    # 选项卡
    tab1, tab2, tab3 = st.tabs(["个人统计", "刷题历史", "排行榜"])

    with tab1:
        _render_personal_stats(user_id)

    with tab2:
        _render_history(user_id)

    with tab3:
        st.markdown("## 排行榜")
        render_leaderboard()


def _render_personal_stats(user_id: int):
    """渲染个人统计"""
    # 总体统计
    render_overall_stats(user_id)

    st.divider()

    # 两列布局
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### 各模块进度")
        render_category_progress_bars(user_id)

        st.divider()
        st.markdown("### 各模块正确率")
        render_category_radar(user_id, key="stats_radar")

    with col2:
        st.markdown("### 最近刷题趋势")
        render_weekly_heatmap(user_id, key="stats_heatmap")

        st.divider()
        st.markdown("### 题库分布")
        render_type_pie(key="stats_pie")


def _render_history(user_id: int):
    """渲染刷题历史记录"""
    from data.db.connection import get_cursor
    from app.components.question_card import render_question_card, render_answer_section

    from data.db.supabase_client import _get_all_user_answers

    st.markdown("## 刷题历史")

    all_ua = _get_all_user_answers(user_id)
    total = len(all_ua)

    if total == 0:
        st.info("还没有刷题记录")
        return

    page_size = 20
    page = st.number_input("页码", min_value=1, max_value=max(1, (total + page_size - 1) // page_size), value=1, label_visibility="collapsed")
    offset = (page - 1) * page_size
    st.caption(f"共 {total} 条记录，第 {page} 页")

    # 按 reviewed_at 排序并分页
    all_ua.sort(key=lambda x: str(x.get("reviewed_at", "")), reverse=True)
    ua_rows = all_ua[offset:offset + page_size]
    if not ua_rows:
        st.info("还没有刷题记录")
        return

    # 从 goodjob 取题目和分类信息
    qids = [r["question_id"] for r in ua_rows]
    with get_cursor() as qcur:
        q_rows = qcur.execute(
            f"SELECT q.id, q.question_text, q.question_type, q.answer_text, q.keywords, q.difficulty, q.is_ai_generated, c.name as category_name FROM questions q LEFT JOIN categories c ON q.category_id=c.id WHERE q.id IN ({','.join('?'*len(qids))})",
            qids,
        ).fetchall()
    q_map = {r["id"]: dict(r) for r in q_rows}

    for ua in ua_rows:
        r = dict(ua)
        q = q_map.get(r["question_id"], {})
        r["qid"] = q.get("id", r["question_id"])
        r["question_text"] = q.get("question_text", "")
        r["question_type"] = q.get("question_type", "")
        r["answer_text"] = q.get("answer_text", "")
        r["keywords"] = q.get("keywords", "")
        r["difficulty"] = q.get("difficulty", 3)
        r["is_ai_generated"] = q.get("is_ai_generated", 0)
        r["category_name"] = q.get("category_name", "")
        # 结果标识
        if r["is_correct"] == 1:
            badge = "✅"
        elif r["is_correct"] == 0:
            badge = "❌"
        else:
            badge = f"{r['score']:.0f}/10" if r["score"] else ""

        session_label = {"sequential": "顺序", "random": "随机", "daily_quiz": "测验"}.get(
            r["review_session"], r["review_session"] or ""
        )
        time_str = r["reviewed_at"][:16] if r["reviewed_at"] else ""

        # 题目摘要
        preview = (r["question_text"] or "")[:80].replace("\n", " ")

        with st.expander(f"{badge} [{r['category_name']}] {preview} — {time_str}"):
            # 显示完整题目
            q_data = {
                "id": r["qid"], "question_text": r["question_text"],
                "question_type": r["question_type"], "answer_text": r["answer_text"],
                "keywords": r["keywords"], "difficulty": r["difficulty"],
                "is_ai_generated": r["is_ai_generated"],
            }
            render_question_card(q_data)

            # 用户答案
            if r["user_answer"]:
                st.markdown("### 你的答案")
                st.info(r["user_answer"])

            # 得分
            if r["score"] is not None:
                st.markdown(f"**得分:** {r['score']:.0f}/10")
            if r["feedback"]:
                st.caption(f"评价: {r['feedback']}")

            st.markdown(f"**模式:** {session_label} | **时间:** {time_str}")

            # 参考答案
            render_answer_section(q_data)

