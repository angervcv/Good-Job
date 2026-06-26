"""
主观题评分模块
用于每日测验中对简答/计算/画图等主观题进行 AI 评分
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from ai.client import get_client
from ai.prompts import SUBJECTIVE_GRADE_SYSTEM, SUBJECTIVE_GRADE_USER


OBJECTIVE_TYPES = {"single_choice", "multiple_choice", "fill_blank", "true_false"}
SUBJECTIVE_TYPES = {"calculation", "short_answer", "drawing", "process_flow"}


def is_objective_type(question_type: str) -> bool:
    """判断是否为客观题（可自动判分）"""
    return question_type in OBJECTIVE_TYPES


def is_subjective_type(question_type: str) -> bool:
    """判断是否为主观题（需 AI 评分）"""
    return question_type in SUBJECTIVE_TYPES


def grade_objective(user_answer: str, reference_answer: str, question_type: str) -> dict:
    """客观题自动判分

    Returns:
        {"score": float (0或10), "is_correct": bool, "feedback": str}
    """
    if not user_answer or not user_answer.strip():
        return {"score": 0, "is_correct": False, "feedback": "未作答"}

    user = user_answer.strip().upper()
    ref = reference_answer.strip().upper()

    if question_type in ("single_choice", "multiple_choice"):
        # 选择题：直接比对
        # 清理格式：A. xxx -> A
        user_clean = _clean_choice(user)
        ref_clean = _clean_choice(ref)

        # 多选题：转集合比较
        if question_type == "multiple_choice":
            user_set = set(user_clean.replace(" ", ""))
            ref_set = set(ref_clean.replace(" ", ""))
            is_correct = user_set == ref_set
        else:
            is_correct = user_clean == ref_clean

        score = 10 if is_correct else 0
        feedback = "正确" if is_correct else f"错误，正确答案是 {ref.strip()}"
        return {"score": score, "is_correct": is_correct, "feedback": feedback}

    elif question_type == "fill_blank":
        # 填空题：包含匹配
        is_correct = user.strip().lower() == ref.strip().lower()
        if not is_correct:
            # 宽松匹配：用户答案包含在参考答案中
            is_correct = user.strip().lower() in ref.strip().lower() or \
                         ref.strip().lower() in user.strip().lower()

        score = 10 if is_correct else 0
        feedback = "正确" if is_correct else f"不准确，参考答案: {ref.strip()}"
        return {"score": score, "is_correct": is_correct, "feedback": feedback}

    else:
        # 其他客观题型
        is_correct = user.strip().lower() == ref.strip().lower()
        score = 10 if is_correct else 0
        feedback = "正确" if is_correct else f"参考答案: {ref.strip()}"
        return {"score": score, "is_correct": is_correct, "feedback": feedback}


def grade_subjective(
    question_text: str,
    reference_answer: str,
    user_answer: str,
    question_type: str,
) -> dict:
    """主观题 AI 评分

    Returns:
        {"score": float (0-10), "feedback": str, "is_fully_correct": bool}
    """
    if not user_answer or not user_answer.strip():
        return {"score": 0, "is_fully_correct": False, "feedback": "未作答"}

    client = get_client()

    try:
        result = client.chat_json(
            system_prompt=SUBJECTIVE_GRADE_SYSTEM,
            user_message=SUBJECTIVE_GRADE_USER.format(
                question_type=question_type,
                question_text=question_text,
                reference_answer=reference_answer,
                user_answer=user_answer,
            ),
            temperature=0.1,  # 低温度保证评分稳定
        )
        return {
            "score": result.get("score", 0),
            "feedback": result.get("feedback", ""),
            "is_fully_correct": result.get("is_fully_correct", False),
        }
    except Exception as e:
        print(f"  [AI评分失败] {e}")
        return {"score": 5, "is_fully_correct": False, "feedback": f"AI评分异常: {e}"}


def grade_answer(
    question: dict,
    user_answer: str,
) -> dict:
    """统一的评分入口：自动判断题型并选择评分方式

    Args:
        question: 题目字典 (需包含 question_type, question_text, answer_text)
        user_answer: 用户提交的答案

    Returns:
        {"score": float (0-10), "is_correct": bool, "feedback": str, "grading_mode": "auto"|"ai"}
    """
    qtype = question.get("question_type", "short_answer")

    if is_objective_type(qtype):
        result = grade_objective(
            user_answer=user_answer,
            reference_answer=question.get("answer_text", ""),
            question_type=qtype,
        )
        result["grading_mode"] = "auto"
        return result
    else:
        result = grade_subjective(
            question_text=question.get("question_text", ""),
            reference_answer=question.get("answer_text", ""),
            user_answer=user_answer,
            question_type=qtype,
        )
        result["grading_mode"] = "ai"
        # 主观题得分缩放到 0-10（AI 返回的 score 已经在 0-10 范围）
        return result


def _clean_choice(text: str) -> str:
    """清理选择题答案格式：'A. xxx' -> 'A', 'B) yyy' -> 'B'"""
    text = text.strip()
    if text and (text[0].isalpha()):
        return text[0].upper()
    return text