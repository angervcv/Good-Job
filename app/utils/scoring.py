"""
评分逻辑
"""

from data.db.queries import save_answer, update_question_stats, update_user_stats
from ai.subjective_grader import grade_answer, is_objective_type


def process_answer(
    user_id: int,
    question: dict,
    user_answer: str,
    review_session: str = "sequential",
    self_score: int = None,
) -> dict:
    """处理用户作答：评分、保存记录、更新统计

    Args:
        user_id: 用户 ID
        question: 题目字典
        user_answer: 用户提交的答案
        review_session: sequential / random / daily_quiz
        self_score: 自我评分 (0-100, 仅主观题自评模式使用)

    Returns:
        {"score": float, "is_correct": bool, "feedback": str, "grading_mode": str}
    """
    qtype = question.get("question_type", "short_answer")

    if is_objective_type(qtype):
        # 客观题：自动判分
        result = grade_answer(question, user_answer)
        is_correct = 1 if result.get("is_correct") else 0

        # 保存作答记录
        save_answer(
            user_id=user_id,
            question_id=question["id"],
            user_answer=user_answer,
            is_correct=is_correct,
            score=result["score"],
            feedback=result.get("feedback", ""),
            review_session=review_session,
        )

        # 更新统计
        update_question_stats(question["id"], bool(is_correct))
        update_user_stats(user_id, bool(is_correct))

    else:
        # 主观题：使用自评分数
        if self_score is not None:
            final_score = self_score / 10.0  # 转换为 0-10
            is_correct = 1 if self_score >= 60 else 0
            result = {
                "score": final_score,
                "is_correct": is_correct,
                "feedback": f"自评: {self_score}%",
                "grading_mode": "self",
            }
        else:
            # AI 评分（每日测验模式）
            result = grade_answer(question, user_answer)
            is_correct = 1 if result.get("is_correct") else 0

        save_answer(
            user_id=user_id,
            question_id=question["id"],
            user_answer=user_answer,
            is_correct=is_correct,
            score=result["score"],
            feedback=result.get("feedback", ""),
            review_session=review_session,
        )

        update_question_stats(question["id"], bool(is_correct))
        update_user_stats(user_id, bool(is_correct))

    return result


def process_quiz_answer(
    user_id: int,
    question: dict,
    user_answer: str,
) -> dict:
    """处理每日测验作答（始终使用 AI 评分）"""
    return process_answer(
        user_id=user_id,
        question=question,
        user_answer=user_answer,
        review_session="daily_quiz",
        self_score=None,  # 不接受自评
    )