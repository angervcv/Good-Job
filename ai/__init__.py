"""AI 模块"""
from ai.client import get_client, check_connection
from ai.answer_completer import complete_missing_answers
from ai.question_generator import generate_all_questions
from ai.subjective_grader import grade_answer, is_objective_type, is_subjective_type