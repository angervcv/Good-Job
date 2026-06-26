"""
数据库连接管理 - 每次调用创建新连接，避免 Streamlit 全局状态问题
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
import config
from data.db.schema import init_db


def _ensure_db(db_path: Path):
    """确保数据库文件存在并已初始化"""
    if not db_path.exists():
        db_path.parent.mkdir(parents=True, exist_ok=True)
        init_db(db_path)


@contextmanager
def get_cursor(db_path: str | Path = None):
    """获取游标的上下文管理器，自动提交/回滚"""
    if db_path is None:
        db_path = config.DB_PATH
    db_path = Path(db_path)

    _ensure_db(db_path)

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row

    try:
        cursor = conn.cursor()
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_connection(db_path: str | Path = None) -> sqlite3.Connection:
    """获取独立数据库连接（调用者负责关闭）"""
    if db_path is None:
        db_path = config.DB_PATH
    db_path = Path(db_path)

    _ensure_db(db_path)

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_userdata_cursor():
    """获取用户数据库游标（userdata.db，部署时不被覆盖）"""
    from data.db.schema import init_userdata
    db_path = Path(config.USER_DB_PATH)
    if not db_path.exists():
        init_userdata(db_path)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def close_connection():
    """兼容旧接口（新版本每次连接自动关闭，无需此函数）"""
    pass


def reset_connection():
    """兼容旧接口"""
    pass