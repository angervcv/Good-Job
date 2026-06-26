"""
用户认证组件
"""

import streamlit as st


def require_login():
    """检查是否已登录，未登录显示提示"""
    if not st.session_state.get("user_logged_in"):
        st.warning("请在左侧输入用户名后开始使用")
        st.stop()
    return st.session_state.user
