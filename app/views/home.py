"""
首页 - 仪表盘
"""

import streamlit as st
from app.components.navigation import require_login
from app.components.stats_chart import (
    render_overall_stats,
    render_category_progress_bars,
    render_weekly_heatmap,
)
from data.db.queries import (
    get_user_answer_history,
    get_all_categories,
    get_category_question_count,
    get_total_question_count,
)


def render_home():
    """渲染首页"""
    st.title("欢迎来到 GoodJob")

    user = require_login()
    user_id = user["id"]

    # 总体统计卡片
    st.markdown("### 学习概览")
    render_overall_stats(user_id)

    st.divider()

    # 快捷入口 + 各模块进度
    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("### 题库概览")
        total = get_total_question_count()
        categories = get_all_categories()
        st.markdown(f"**总题数: {total}**")
        for cat in categories:
            count = get_category_question_count(cat["id"])
            st.markdown(f"- {cat['name']}: {count} 题")

    with col2:
        st.markdown("### 模块进度")
        render_category_progress_bars(user_id)

    st.divider()

    # 最近作答记录和刷题热力图
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### 最近刷题记录")
        history = get_user_answer_history(user_id, limit=10)

        if history:
            for h in history:
                qtype = h.get("question_type", "short_answer")
                is_correct = h.get("is_correct")
                score = h.get("score")

                if is_correct == 1:
                    badge = '<span class="correct-badge">正确</span>'
                elif is_correct == 0:
                    badge = '<span class="wrong-badge">错误</span>'
                else:
                    badge = f'<span class="ai-tag">{score:.0f}/10</span>' if score else ""

                text_preview = h.get("question_text", "")[:80]
                st.markdown(
                    f"{badge} {text_preview}...",
                    unsafe_allow_html=True,
                )
        else:
            st.info("还没有刷题记录，快去刷题吧！")

    with col2:
        render_weekly_heatmap(user_id, key="home_heatmap")