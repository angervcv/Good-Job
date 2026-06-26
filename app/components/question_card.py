"""
题目卡片组件
用于展示题目的标准化卡片
"""

import streamlit as st
import json

# 题型中文映射
TYPE_CN = {
    "single_choice": "单选题",
    "multiple_choice": "多选题",
    "fill_blank": "填空题",
    "calculation": "计算题",
    "short_answer": "简答题",
    "drawing": "画图题",
    "process_flow": "工艺流程题",
}

# 题型图标（已移除emoji，保留空字典供兼容）
TYPE_ICON = {}


def _render_markdown(text: str):
    """渲染 Markdown 文本，支持 LaTeX 公式 ($...$ 和 $$...$$)"""
    st.markdown(text)


def render_question_card(question: dict, show_meta: bool = True):
    """渲染题目卡片"""
    if not question:
        st.info("没有可显示的题目")
        return

    if show_meta:
        _render_question_meta(question)

    st.markdown("### 题目")
    q_text = question.get("question_text", "")
    # 用 st.markdown 直接渲染文本，支持 $...$ LaTeX
    with st.container(border=True):
        st.markdown(q_text)

    if question.get("options"):
        options = question["options"]
        if isinstance(options, str):
            try:
                options = json.loads(options)
            except json.JSONDecodeError:
                pass
        if isinstance(options, list) and options:
            st.markdown("**选项：**")
            for opt in options:
                st.markdown(f"- {opt}")

    # 显示配图（页面截图兜底）
    _render_question_images(question)

    if question.get("is_ai_generated"):
        st.caption("此题为 AI 生成")


def render_answer_section(question: dict):
    """渲染答案区域，支持 LaTeX 公式"""
    answer = question.get("answer_text", "")
    explanation = question.get("explanation", "")
    is_ai = question.get("ai_answer_flag", 0) or question.get("is_ai_generated", 0)

    if not answer and not explanation:
        st.warning("此题暂无参考答案")
        return

    if answer:
        st.markdown("### 参考答案")
        if is_ai:
            st.caption("AI生成")
        # 选择题：答案若为纯字母，匹配显示对应选项
        qtype = question.get("question_type", "")
        if qtype in ("single_choice", "multiple_choice") and len(answer.strip()) <= 3:
            opts = _parse_inline_options(question.get("question_text", ""))
            ans_letters = [a.strip().upper() for a in answer.split(",") if a.strip()]
            matched = []
            for letter in ans_letters:
                for opt in opts:
                    if opt.strip().startswith(letter + ".") or opt.strip().startswith(letter + ")"):
                        matched.append(opt.strip()); break
            if matched:
                st.markdown(f"**正确答案：{answer}**")
                for m in matched:
                    st.markdown(f"- {m}")
            else:
                st.markdown(answer)
        else:
            st.markdown(answer)

    if explanation:
        st.markdown("### 解析")
        st.markdown(explanation)


def render_self_scoring():
    """渲染主观题自评滑块"""
    st.markdown("### 自我评分")

    score = st.slider(
        "根据参考答案，你的作答能得多少分？",
        min_value=0,
        max_value=100,
        value=st.session_state.get("self_score", 100),
        step=5,
        format="%d%%",
        key="self_score_slider",
        help="0% = 完全不对，100% = 完全正确",
    )
    st.session_state.self_score = score

    col1, col2 = st.columns(2)
    with col1:
        st.caption(f"得分: **{score}%** ({score / 10:.1f}/10分)")
    with col2:
        if score >= 80:
            st.markdown('<span class="correct-badge">优秀</span>', unsafe_allow_html=True)
        elif score >= 60:
            st.markdown('<span class="correct-badge">良好</span>', unsafe_allow_html=True)
        elif score >= 40:
            st.caption("还需努力")
        else:
            st.markdown('<span class="wrong-badge">需要复习</span>', unsafe_allow_html=True)

    return score


def _parse_inline_options(question_text: str) -> list[str]:
    """从题目文本中提取 A. B. C. D. 格式的选项"""
    import re
    # 匹配 A.xxx B.xxx C.xxx D.xxx 或 A) B) C) D) 格式
    patterns = [
        r'([A-D])[\.\)]\s*(.+?)(?=[A-D][\.\)]|$)',  # A. xxx B. xxx
    ]
    for p in patterns:
        matches = re.findall(p, question_text, re.DOTALL)
        if len(matches) >= 3:
            return [f"{m[0]}. {m[1].strip().rstrip('.')}" for m in matches]
    return []


def render_choice_input(question: dict) -> str:
    """渲染选择题输入组件，返回用户答案"""
    qtype = question.get("question_type", "short_answer")
    options = question.get("options", "")

    if isinstance(options, str):
        try:
            options = json.loads(options)
        except json.JSONDecodeError:
            options = []

    # 如果 options 字段为空，尝试从题目文本中解析
    if not options:
        options = _parse_inline_options(question.get("question_text", ""))

    if qtype == "single_choice" and options:
        user_answer = st.radio(
            "请选择：",
            options=options,
            index=None,
            key=f"choice_{question.get('id', 0)}",
        )
    elif qtype == "multiple_choice" and options:
        selected = []
        for opt in options:
            if st.checkbox(opt, key=f"mc_{question.get('id', 0)}_{opt[:20]}"):
                selected.append(opt)
        user_answer = ", ".join(selected) if selected else ""
    else:
        user_answer = None

    return user_answer


def render_text_input(question: dict, key_suffix: str = "") -> str:
    """渲染文本输入组件"""
    return st.text_area(
        "你的答案：",
        height=150,
        placeholder="在此输入你的答案...",
        key=f"answer_{question.get('id', 0)}{key_suffix}",
    )


def _render_question_images(question: dict):
    """显示题目配图"""
    from data.db.connection import get_cursor
    from pathlib import Path

    qid = question.get("id")
    if not qid:
        return
    with get_cursor() as cur:
        rows = cur.execute(
            "SELECT image_path, image_type FROM question_images WHERE question_id=?",
            (qid,),
        ).fetchall()
    for r in rows:
        img_path = Path(r["image_path"])
        if img_path.exists():
            st.caption(f"附图（{r['image_type']}）")
            st.image(str(img_path), use_container_width=True)
        else:
            # Try relative to project root
            alt = Path("d:/GoodJob") / img_path
            if alt.exists():
                st.caption("附图")
                st.image(str(alt), use_container_width=True)


def _render_question_meta(question: dict):
    """渲染题目元信息标签"""
    qtype = question.get("question_type", "short_answer")
    type_cn = TYPE_CN.get(qtype, "简答题")
    difficulty = question.get("difficulty", 3)

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.caption(f"**{type_cn}** | 难度 {'⭐' * difficulty}")
    with col2:
        if question.get("keywords"):
            kws = question["keywords"]
            if isinstance(kws, str):
                kws = kws.split(",")[:3]
            st.caption(" | ".join(kws[:3]))
    with col3:
        if question.get("review_count", 0) > 0:
            st.caption(f"已刷 {question['review_count']} 次")