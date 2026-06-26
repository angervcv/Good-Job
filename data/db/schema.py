"""
数据库 Schema 定义与初始化
"""

import sqlite3
from pathlib import Path
import config


SCHEMA_SQL = """
-- 领域分类表
CREATE TABLE IF NOT EXISTS categories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    description TEXT,
    sort_order  INTEGER DEFAULT 0
);

-- 题目表 (核心表)
CREATE TABLE IF NOT EXISTS questions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid            TEXT NOT NULL UNIQUE,
    category_id     INTEGER REFERENCES categories(id),
    question_type   TEXT NOT NULL CHECK(question_type IN (
                        'single_choice', 'multiple_choice', 'fill_blank',
                        'calculation', 'short_answer', 'drawing',
                        'process_flow'
                    )),
    difficulty      INTEGER DEFAULT 3 CHECK(difficulty BETWEEN 1 AND 5),
    title           TEXT,
    question_text   TEXT NOT NULL,
    options         TEXT,
    answer_text     TEXT,
    explanation     TEXT,
    keywords        TEXT,
    is_ai_generated INTEGER DEFAULT 0,
    ai_answer_flag  INTEGER DEFAULT 0,
    source_file     TEXT,
    source_page     INTEGER,
    review_count    INTEGER DEFAULT 0,
    correct_count   INTEGER DEFAULT 0,
    is_active       INTEGER DEFAULT 1,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 题目关联图片表
CREATE TABLE IF NOT EXISTS question_images (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id     INTEGER REFERENCES questions(id),
    image_path      TEXT NOT NULL,
    image_type      TEXT CHECK(image_type IN ('question', 'answer', 'attachment')),
    sort_order      INTEGER DEFAULT 0,
    ocr_text        TEXT
);

-- 标签表
CREATE TABLE IF NOT EXISTS tags (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL UNIQUE,
    category_id     INTEGER REFERENCES categories(id)
);

CREATE TABLE IF NOT EXISTS question_tags (
    question_id     INTEGER REFERENCES questions(id),
    tag_id          INTEGER REFERENCES tags(id),
    PRIMARY KEY (question_id, tag_id)
);

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT NOT NULL UNIQUE,
    display_name    TEXT,
    total_reviewed  INTEGER DEFAULT 0,
    total_correct   INTEGER DEFAULT 0,
    streak_days     INTEGER DEFAULT 0,
    last_active     DATE,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 用户作答记录
CREATE TABLE IF NOT EXISTS user_answers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER REFERENCES users(id),
    question_id     INTEGER REFERENCES questions(id),
    user_answer     TEXT,
    is_correct      INTEGER,
    score           REAL,
    feedback        TEXT,
    answer_time_sec INTEGER,
    review_session  TEXT CHECK(review_session IN ('sequential', 'random', 'daily_quiz')),
    reviewed_at     DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 每日测验记录
CREATE TABLE IF NOT EXISTS daily_quizzes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER REFERENCES users(id),
    quiz_date       DATE NOT NULL,
    total_score     REAL DEFAULT 0,
    max_score       REAL DEFAULT 100,
    questions_json  TEXT,
    answers_json    TEXT,
    completed       INTEGER DEFAULT 0,
    completed_at    DATETIME,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 刷题进度 (按模块)
CREATE TABLE IF NOT EXISTS review_progress (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER REFERENCES users(id),
    category_id     INTEGER REFERENCES categories(id),
    reviewed_count  INTEGER DEFAULT 0,
    correct_count   INTEGER DEFAULT 0,
    last_question_id INTEGER DEFAULT 0,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, category_id)
);

-- 每日统计快照
CREATE TABLE IF NOT EXISTS daily_stats (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER REFERENCES users(id),
    stat_date       DATE NOT NULL,
    questions_done  INTEGER DEFAULT 0,
    correct_count   INTEGER DEFAULT 0,
    time_spent_sec  INTEGER DEFAULT 0,
    UNIQUE(user_id, stat_date)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_questions_category ON questions(category_id);
CREATE INDEX IF NOT EXISTS idx_questions_type ON questions(question_type);
CREATE INDEX IF NOT EXISTS idx_questions_active ON questions(is_active);
CREATE INDEX IF NOT EXISTS idx_user_answers_user ON user_answers(user_id);
CREATE INDEX IF NOT EXISTS idx_user_answers_question ON user_answers(question_id);
CREATE INDEX IF NOT EXISTS idx_user_answers_session ON user_answers(review_session);
CREATE INDEX IF NOT EXISTS idx_daily_quizzes_user_date ON daily_quizzes(user_id, quiz_date);
CREATE INDEX IF NOT EXISTS idx_daily_stats_user_date ON daily_stats(user_id, stat_date);
CREATE INDEX IF NOT EXISTS idx_review_progress_user ON review_progress(user_id);
"""


# 用户数据库 DDL（独立文件，部署时不覆盖）
USER_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    display_name TEXT,
    total_reviewed INTEGER DEFAULT 0,
    total_correct INTEGER DEFAULT 0,
    streak_days INTEGER DEFAULT 0,
    last_active DATE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS user_answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),
    question_id INTEGER,
    user_answer TEXT,
    is_correct INTEGER,
    score REAL,
    feedback TEXT,
    answer_time_sec INTEGER,
    review_session TEXT,
    reviewed_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS daily_quizzes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),
    quiz_date DATE NOT NULL,
    total_score REAL DEFAULT 0,
    max_score REAL DEFAULT 100,
    questions_json TEXT,
    answers_json TEXT,
    completed INTEGER DEFAULT 0,
    completed_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS review_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),
    category_id INTEGER,
    reviewed_count INTEGER DEFAULT 0,
    correct_count INTEGER DEFAULT 0,
    last_question_id INTEGER DEFAULT 0,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, category_id)
);
CREATE TABLE IF NOT EXISTS daily_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),
    stat_date DATE NOT NULL,
    questions_done INTEGER DEFAULT 0,
    correct_count INTEGER DEFAULT 0,
    time_spent_sec INTEGER DEFAULT 0,
    UNIQUE(user_id, stat_date)
);
CREATE TABLE IF NOT EXISTS comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),
    question_id INTEGER,
    content TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""


def init_userdata(db_path=None):
    """初始化用户数据库"""
    if db_path is None:
        db_path = config.USER_DB_PATH
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.executescript(USER_SCHEMA_SQL)
    conn.commit()
    conn.close()


def init_db(db_path: str | Path = None) -> sqlite3.Connection:
    """初始化数据库：创建所有表并插入预设分类"""
    if db_path is None:
        db_path = config.DB_PATH

    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    conn.executescript(SCHEMA_SQL)

    # 插入预设分类
    for cat in config.CATEGORIES:
        conn.execute(
            """INSERT OR IGNORE INTO categories (name, description, sort_order)
               VALUES (?, ?, ?)""",
            (cat["name"], cat["description"], cat["sort_order"]),
        )

    conn.commit()
    return conn


if __name__ == "__main__":
    conn = init_db()
    print(f"数据库已初始化: {config.DB_PATH}")

    # 验证表结构
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    print(f"已创建 {len(tables)} 张表: {[t[0] for t in tables]}")

    cats = conn.execute("SELECT * FROM categories").fetchall()
    print(f"预设分类: {[(c[1], c[2]) for c in cats]}")

    conn.close()