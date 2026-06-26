"""
GoodJob - 半导体功率器件刷题平台
Streamlit 主入口
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import config
from app.session_state import init_session


def main():
    st.set_page_config(
        page_title=config.STREAMLIT_TITLE,
        page_icon="📚",  # keep: sidebar logo
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            "Get Help": None,
            "Report a bug": None,
            "About": "GoodJob - 半导体功率器件求职笔试刷题平台",
        },
    )

    _load_css()
    init_session()

    # 侧边栏：仅保留 Logo + 用户登录
    _render_sidebar()

    # 顶部 Tab 导航
    tab_home, tab_review, tab_quiz, tab_stats = st.tabs([
        "首页", "模块刷题", "每日测验", "统计排行"
    ])

    with tab_home:
        from app.views.home import render_home
        render_home()

    with tab_review:
        from app.views.review import render_review
        render_review()

    with tab_quiz:
        from app.views.daily_quiz import render_daily_quiz
        render_daily_quiz()

    with tab_stats:
        from app.views.statistics import render_statistics
        render_statistics()


def _render_sidebar():
    """侧边栏：Logo + 用户登录"""
    from data.db.queries import get_or_create_user

    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; padding: 16px 0;">
            <h1 style="margin: 0; font-size: 1.6rem;">📚 GoodJob</h1>
            <p style="color: #888; font-size: 0.8rem; margin: 4px 0;">半导体功率器件刷题平台</p>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        if st.session_state.get("user_logged_in"):
            user = st.session_state.user
            st.markdown(f"👤 **{user['username']}**")
            st.caption(f"已刷 {user.get('total_reviewed', 0)} 题")
            if st.button("退出", key="logout_btn", use_container_width=True):
                st.session_state.user = None
                st.session_state.username = ""
                st.session_state.user_logged_in = False
                st.rerun()
        else:
            with st.form("login_form"):
                username = st.text_input(
                    "用户名",
                    placeholder="输入用户名即可开始",
                    label_visibility="collapsed",
                )
                if st.form_submit_button("进入", use_container_width=True) and username.strip():
                    user = get_or_create_user(username.strip())
                    st.session_state.user = user
                    st.session_state.username = username.strip()
                    st.session_state.user_logged_in = True
                    st.rerun()

        st.divider()

        st.markdown("""
        <div style="text-align: center; padding: 8px 0;">
            <p style="margin: 0; font-size: 1.1rem; font-weight: 700; color: #1565C0;">GoodJob</p>
            <p style="margin: 2px 0; font-size: 0.75rem; color: #888;">v0.1 beta</p>
            <p style="margin: 2px 0; font-size: 0.7rem; color: #aaa;">Copyright @Xiang Y_UESTC</p>
        </div>
        """, unsafe_allow_html=True)


def _load_css():
    st.markdown("""
    <style>
        html, body, [class*="css"] {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        }
        .question-card {
            background: #FFFFFF;
            border: 1px solid #E0E0E0;
            border-radius: 12px;
            padding: 24px;
            margin: 12px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        }
        .question-card h3 { color: #1565C0; margin-top: 0; }
        .answer-box {
            background: #F0F7FF;
            border-left: 4px solid #1565C0;
            border-radius: 8px;
            padding: 16px;
            margin: 12px 0;
        }
        .answer-box-ai {
            background: #FFF8E1;
            border-left: 4px solid #FF8F00;
        }
        .stat-card {
            background: #FFFFFF;
            border: 1px solid #E0E0E0;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 1px 4px rgba(0,0,0,0.04);
        }
        .stat-card .number { font-size: 2rem; font-weight: 700; color: #1565C0; }
        .stat-card .label { font-size: 0.85rem; color: #666; margin-top: 4px; }
        .correct-badge { background: #E8F5E9; color: #2E7D32; padding: 4px 12px; border-radius: 16px; font-weight: 600; font-size: 0.85rem; }
        .wrong-badge { background: #FFEBEE; color: #C62828; padding: 4px 12px; border-radius: 16px; font-weight: 600; font-size: 0.85rem; }
        .ai-tag { background: #FFF3E0; color: #E65100; padding: 2px 8px; border-radius: 10px; font-size: 0.75rem; font-weight: 500; }
        @media (max-width: 768px) {
            .stat-card .number { font-size: 1.5rem; }
        }
    </style>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
