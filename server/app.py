"""
원격지원 서버 - Flask + Flask-SocketIO
REST API + 관리자 웹 대시보드
"""

import os
import sys
import threading
import webbrowser

from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO

import database


def get_base_dir():
    """PyInstaller _MEIPASS 또는 스크립트 디렉토리"""
    if hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


# Flask 앱 초기화
app = Flask(
    __name__,
    template_folder=os.path.join(get_base_dir(), "templates")
)
app.config["SECRET_KEY"] = "support-server-secret-key"

# SocketIO 초기화 (threading 모드, eventlet/gevent 사용 안 함)
socketio = SocketIO(app, async_mode="threading", cors_allowed_origins="*")


# ──────────────── 웹 대시보드 ────────────────

@app.route("/")
def index():
    """관리자 대시보드 페이지"""
    return render_template("index.html")


# ──────────────── REST API ────────────────

@app.route("/api/request", methods=["POST"])
def create_request():
    """클라이언트 요청 수신"""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "요청 데이터가 없습니다."}), 400

    required_fields = ["computer_name", "username", "ip", "symptom"]
    for field in required_fields:
        if not data.get(field):
            return jsonify({"success": False, "error": f"{field} 필드가 필요합니다."}), 400

    result = database.create_request(
        data["computer_name"],
        data["username"],
        data["ip"],
        data["symptom"]
    )

    # Socket.IO로 새 요청 알림
    socketio.emit("new_request", result)

    return jsonify({"success": True, "data": result}), 201


@app.route("/api/requests", methods=["GET"])
def get_requests():
    """요청 목록 조회 (상태 필터 지원)"""
    status = request.args.get("status")
    results = database.get_all_requests(status=status)
    return jsonify({"success": True, "data": results})


@app.route("/api/requests/<int:request_id>/start", methods=["POST"])
def start_request(request_id):
    """처리 시작 (상태 -> 처리중)"""
    existing = database.get_request_by_id(request_id)
    if not existing:
        return jsonify({"success": False, "error": "요청을 찾을 수 없습니다."}), 404
    if existing["status"] != "대기중":
        return jsonify({"success": False, "error": "대기중 상태의 요청만 시작할 수 있습니다."}), 400

    result = database.start_request(request_id)

    # Socket.IO로 상태 변경 알림
    socketio.emit("status_update", result)

    return jsonify({"success": True, "data": result})


@app.route("/api/requests/<int:request_id>/complete", methods=["POST"])
def complete_request(request_id):
    """완료 처리 (상태 -> 완료)"""
    existing = database.get_request_by_id(request_id)
    if not existing:
        return jsonify({"success": False, "error": "요청을 찾을 수 없습니다."}), 404
    if existing["status"] != "처리중":
        return jsonify({"success": False, "error": "처리중 상태의 요청만 완료할 수 있습니다."}), 400

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "요청 데이터가 없습니다."}), 400

    handler_name = data.get("handler_name", "")
    notes = data.get("notes", "")

    if not handler_name:
        return jsonify({"success": False, "error": "담당자 이름이 필요합니다."}), 400

    result = database.complete_request(request_id, handler_name, notes)

    # Socket.IO로 상태 변경 알림
    socketio.emit("status_update", result)

    return jsonify({"success": True, "data": result})


@app.route("/api/requests/<int:request_id>/history", methods=["GET"])
def get_request_history(request_id):
    """요청 처리 이력 조회"""
    result = database.get_request_history(request_id)
    if not result:
        return jsonify({"success": False, "error": "요청을 찾을 수 없습니다."}), 404
    return jsonify({"success": True, "data": result})


# ──────────────── Socket.IO 이벤트 ────────────────

@socketio.on("connect")
def handle_connect():
    """클라이언트 연결"""
    pass


@socketio.on("disconnect")
def handle_disconnect():
    """클라이언트 연결 해제"""
    pass


# ──────────────── 메인 실행 ────────────────

def open_browser():
    """브라우저 자동 오픈"""
    webbrowser.open("http://localhost:5000")


if __name__ == "__main__":
    import logging
    # werkzeug 개발 서버 경고 및 접속 로그 억제
    logging.getLogger("werkzeug").setLevel(logging.ERROR)

    # DB 초기화
    database.init_db()

    # 1.5초 후 브라우저 자동 오픈
    threading.Timer(1.5, open_browser).start()

    print("=" * 50)
    print("  원격지원 관리 서버 시작")
    print("  http://localhost:5000")
    print("=" * 50)

    socketio.run(app, host="0.0.0.0", port=5000, debug=False, allow_unsafe_werkzeug=True)
