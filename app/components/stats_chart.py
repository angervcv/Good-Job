"""
统计图表组件
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from data.db.queries import (
    get_weekly_stats,
    get_leaderboard_by_count,
    get_leaderboard_by_accuracy,
    get_question_type_distribution,
    get_category_distribution,
    get_user_category_progress,
)
import config


def render_weekly_heatmap(user_id: int, key: str = "heatmap"):
    """渲染每周刷题热力图"""
    from datetime import date, timedelta

    stats = get_weekly_stats(user_id)
    today = date.today()
    date_range = [(today - timedelta(days=i)) for i in range(6, -1, -1)]
    stat_map = {}
    if stats:
        for s in stats:
            d = s["date"]
            if hasattr(d, "strftime"):
                d = str(d)
            stat_map[str(d)] = s["count"]

    rows = []
    for d in date_range:
        d_str = str(d)
        rows.append({"date": d, "count": stat_map.get(d_str, 0)})

    df = pd.DataFrame(rows)

    fig = px.bar(
        df,
        x="date",
        y="count",
        title="最近7天刷题数",
        labels={"date": "日期", "count": "刷题数"},
        color="count",
        color_continuous_scale="Blues",
    )
    fig.update_layout(height=300, margin=dict(l=0, r=0, t=30, b=0))
    fig.update_xaxes(dtick=86400000, tickformat="%m-%d")
    st.plotly_chart(fig, use_container_width=True, key=f"plotly_{key}")


def render_category_radar(user_id: int, key: str = "radar"):
    """渲染各模块正确率雷达图"""
    progress = get_user_category_progress(user_id)

    if not progress:
        st.info("暂无数据")
        return

    categories = [p["category_name"] for p in progress]
    accuracies = [
        round(p["correct_count"] / max(p["reviewed_count"], 1) * 100, 1)
        for p in progress
    ]
    reviewed = [p["reviewed_count"] for p in progress]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=accuracies,
        theta=categories,
        fill="toself",
        name="正确率(%)",
        line_color="#1565C0",
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(range=[0, 100])),
        height=350,
        margin=dict(l=20, r=20, t=30, b=20),
    )
    st.plotly_chart(fig, use_container_width=True, key=f"plotly_{key}")


def render_category_progress_bars(user_id: int):
    """渲染各模块刷题进度条"""
    from data.db.queries import get_category_question_count

    progress = get_user_category_progress(user_id)

    for p in progress:
        cat_name = p["category_name"]
        reviewed = p["reviewed_count"]
        total = get_category_question_count(p["category_id"])
        pct = min(reviewed / max(total, 1) * 100, 100)

        col1, col2, col3 = st.columns([2, 5, 1])
        with col1:
            st.markdown(f"**{cat_name}**")
        with col2:
            st.progress(pct / 100, text=f"{reviewed}/{total}")
        with col3:
            acc = round(p["correct_count"] / max(reviewed, 1) * 100, 1) if reviewed > 0 else 0
            st.caption(f"{acc}%")


def render_type_pie(key: str = "pie"):
    """渲染题目类型分布饼图"""
    dist = get_question_type_distribution()

    if not dist:
        return

    type_cn = {
        "single_choice": "单选题",
        "multiple_choice": "多选题",
        "fill_blank": "填空题",
        "calculation": "计算题",
        "short_answer": "简答题",
        "drawing": "画图题",
        "process_flow": "工艺流程题",
    }

    df = pd.DataFrame(dist)
    df["name"] = df["question_type"].map(type_cn)

    fig = px.pie(
        df,
        values="count",
        names="name",
        title="题目类型分布",
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig.update_layout(height=350, margin=dict(l=0, r=0, t=30, b=0))
    st.plotly_chart(fig, use_container_width=True, key=f"plotly_{key}")


def render_leaderboard():
    """渲染排行榜"""
    tab1, tab2 = st.tabs(["刷题数排行", "正确率排行"])

    with tab1:
        leaders = get_leaderboard_by_count(limit=20)
        if leaders:
            df = pd.DataFrame(leaders)
            df["rank"] = range(1, len(df) + 1)
            df = df[["rank", "username", "total_reviewed", "accuracy"]]
            df.columns = ["排名", "用户名", "刷题数", "正确率(%)"]

            st.dataframe(
                df,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "排名": st.column_config.NumberColumn(width="small"),
                    "正确率(%)": st.column_config.NumberColumn(format="%.1f"),
                },
            )
        else:
            st.info("暂无排行数据")

    with tab2:
        leaders = get_leaderboard_by_accuracy(
            min_reviewed=config.LEADERBOARD_MIN_REVIEWED, limit=20
        )
        if leaders:
            df = pd.DataFrame(leaders)
            df["rank"] = range(1, len(df) + 1)
            df = df[["rank", "username", "accuracy", "total_reviewed"]]
            df.columns = ["排名", "用户名", "正确率(%)", "刷题数"]

            st.dataframe(
                df,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "排名": st.column_config.NumberColumn(width="small"),
                    "正确率(%)": st.column_config.NumberColumn(format="%.1f"),
                },
            )
        else:
            st.info(f"暂无排行数据（需至少刷 {config.LEADERBOARD_MIN_REVIEWED} 题）")


def render_overall_stats(user_id: int):
    """渲染用户总体统计卡片"""
    from data.db.queries import get_daily_question_count

    progress = get_user_category_progress(user_id)
    total_reviewed = sum(p["reviewed_count"] for p in progress)
    total_correct = sum(p["correct_count"] for p in progress)
    accuracy = round(total_correct / max(total_reviewed, 1) * 100, 1)
    today_count = get_daily_question_count(user_id)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="number">{total_reviewed}</div>
            <div class="label">总刷题数</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="stat-card">
            <div class="number">{accuracy}%</div>
            <div class="label">总正确率</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="stat-card">
            <div class="number">{today_count}</div>
            <div class="label">今日刷题</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        # 连续天数（简化：只要 last_active 是今天就算）
        # 这里简单处理
        from data.db.supabase_client import _client
        r = _client().table("users").select("streak_days").eq("id", user_id).limit(1).execute()
        streak = r.data[0]["streak_days"] if r.data else 0

        st.markdown(f"""
        <div class="stat-card">
            <div class="number">{streak}</div>
            <div class="label">连续天数</div>
        </div>
        """, unsafe_allow_html=True)