"""
SQLite 데이터베이스 관리 모듈
support.db에 원격지원 요청 데이터를 관리
"""

import sqlite3
import os
import sys


def get_db_path():
    """
    DB 파일 경로 결정
    EXE 실행 시: sys.executable 기준 디렉토리
    개발 시: __file__ 기준 디렉토리
    """
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "support.db")


def get_connection():
    """SQLite 연결 생성 (row_factory 설정)"""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """데이터베이스 초기화 - 테이블 생성"""
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS support_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            computer_name TEXT NOT NULL,
            username TEXT NOT NULL,
            ip TEXT NOT NULL,
            symptom TEXT NOT NULL,
            status TEXT DEFAULT '대기중',
            created_at TEXT DEFAULT (datetime('now','localtime')),
            started_at TEXT,
            completed_at TEXT,
            handler_name TEXT,
            notes TEXT
        )
    """)
    conn.commit()
    conn.close()


def dict_from_row(row):
    """sqlite3.Row를 dict로 변환"""
    if row is None:
        return None
    return dict(row)


def create_request(computer_name, username, ip, symptom):
    """새 지원 요청 생성"""
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO support_requests (computer_name, username, ip, symptom) VALUES (?, ?, ?, ?)",
        (computer_name, username, ip, symptom)
    )
    request_id = cursor.lastrowid
    conn.commit()
    # 생성된 요청 반환
    row = conn.execute("SELECT * FROM support_requests WHERE id = ?", (request_id,)).fetchone()
    conn.close()
    return dict_from_row(row)


def get_all_requests(status=None):
    """
    전체 요청 목록 조회
    status가 None이면 전체, 있으면 해당 상태만 필터
    """
    conn = get_connection()
    if status:
        rows = conn.execute(
            "SELECT * FROM support_requests WHERE status = ? ORDER BY created_at DESC",
            (status,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM support_requests ORDER BY created_at DESC"
        ).fetchall()
    conn.close()
    return [dict_from_row(row) for row in rows]


def get_request_by_id(request_id):
    """ID로 요청 조회"""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM support_requests WHERE id = ?", (request_id,)
    ).fetchone()
    conn.close()
    return dict_from_row(row)


def start_request(request_id):
    """요청 처리 시작 (상태: 대기중 -> 처리중)"""
    conn = get_connection()
    conn.execute(
        "UPDATE support_requests SET status = '처리중', started_at = datetime('now','localtime') WHERE id = ?",
        (request_id,)
    )
    conn.commit()
    row = conn.execute("SELECT * FROM support_requests WHERE id = ?", (request_id,)).fetchone()
    conn.close()
    return dict_from_row(row)


def complete_request(request_id, handler_name, notes):
    """요청 완료 처리 (상태: 처리중 -> 완료)"""
    conn = get_connection()
    conn.execute(
        """UPDATE support_requests
           SET status = '완료',
               completed_at = datetime('now','localtime'),
               handler_name = ?,
               notes = ?
           WHERE id = ?""",
        (handler_name, notes, request_id)
    )
    conn.commit()
    row = conn.execute("SELECT * FROM support_requests WHERE id = ?", (request_id,)).fetchone()
    conn.close()
    return dict_from_row(row)


def get_request_history(request_id):
    """요청 처리 이력 조회"""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM support_requests WHERE id = ?", (request_id,)
    ).fetchone()
    conn.close()
    if row is None:
        return None
    data = dict_from_row(row)
    history = []
    history.append({
        "action": "요청 접수",
        "timestamp": data["created_at"],
        "detail": f"증상: {data['symptom']}"
    })
    if data["started_at"]:
        history.append({
            "action": "처리 시작",
            "timestamp": data["started_at"],
            "detail": ""
        })
    if data["completed_at"]:
        history.append({
            "action": "처리 완료",
            "timestamp": data["completed_at"],
            "detail": f"담당자: {data.get('handler_name', '')}, 내역: {data.get('notes', '')}"
        })
    return {"request": data, "history": history}
