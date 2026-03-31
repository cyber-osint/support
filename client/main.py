"""
원격지원 클라이언트 - tkinter GUI
증상을 입력하고 서버로 전송, RustDesk 자동 수락 기능 포함
"""

import tkinter as tk
from tkinter import messagebox, font as tkfont
import configparser
import socket
import getpass
import json
import os
import sys
import threading
import time
import urllib.request
import urllib.error


def get_exe_dir():
    """EXE 실행 파일이 있는 디렉토리 반환 (개발 중에는 스크립트 위치)"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_local_ip():
    """로컬 IP 주소 자동 감지"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def load_config():
    """EXE와 같은 폴더의 config.ini 읽기. 없으면 기본값으로 생성."""
    config_path = os.path.join(get_exe_dir(), "config.ini")

    if not os.path.exists(config_path):
        # 최초 실행 시 config.ini 자동 생성
        default = configparser.ConfigParser()
        default["server"] = {"ip": "192.168.1.100", "port": "5000"}
        with open(config_path, "w", encoding="utf-8") as f:
            default.write(f)

    config = configparser.ConfigParser()
    config.read(config_path, encoding="utf-8")
    server_ip = config.get("server", "ip", fallback="192.168.1.100")
    server_port = config.get("server", "port", fallback="5000")
    return server_ip, server_port


def send_request(server_ip, server_port, data):
    """서버로 지원 요청 전송"""
    url = f"http://{server_ip}:{server_port}/api/request"
    payload = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def scourt_auto_accept():
    """
    백그라운드 스레드: Windows UI Automation으로 '수락' 버튼을 찾아 자동 클릭.
    Flutter 앱 기준 TextControl 탐색, MOUSEEVENTF_ABSOLUTE로 멀티모니터 정확 클릭.
    UI Automation 실패 시 Win32 API 폴백으로 재시도한다.
    """
    try:
        import uiautomation as auto
        import win32gui
        import win32con
        import win32api
        import ctypes
    except ImportError:
        return

    # 프로세스를 Per-Monitor DPI Aware로 설정 — 멀티모니터 좌표 정확도 확보
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

    # 가상 스크린 전체 크기 (모든 모니터 합산)
    def get_virtual_screen():
        SM_XVIRTUALSCREEN, SM_YVIRTUALSCREEN = 76, 77
        SM_CXVIRTUALSCREEN, SM_CYVIRTUALSCREEN = 78, 79
        left   = ctypes.windll.user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
        top    = ctypes.windll.user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
        width  = ctypes.windll.user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
        height = ctypes.windll.user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
        return left, top, width, height

    def abs_click(cx, cy):
        """MOUSEEVENTF_ABSOLUTE — 가상 스크린 기준 정규화 좌표로 클릭 (멀티모니터 안전)"""
        left, top, width, height = get_virtual_screen()
        ax = (cx - left) * 65535 // width
        ay = (cy - top)  * 65535 // height
        ABSOLUTE = win32con.MOUSEEVENTF_ABSOLUTE
        win32api.SetCursorPos((cx, cy))
        win32api.mouse_event(ABSOLUTE | win32con.MOUSEEVENTF_MOVE,       ax, ay, 0, 0)
        win32api.mouse_event(ABSOLUTE | win32con.MOUSEEVENTF_LEFTDOWN,   ax, ay, 0, 0)
        time.sleep(0.05)
        win32api.mouse_event(ABSOLUTE | win32con.MOUSEEVENTF_LEFTUP,     ax, ay, 0, 0)

    # 영구 set 대신 시간 기반 쿨다운 — 창이 닫혔다 다시 열려도 재클릭 가능
    last_clicked = {}  # key -> timestamp
    COOLDOWN = 5.0     # 같은 위치 재클릭 허용 간격(초)

    def can_click(key):
        return time.time() - last_clicked.get(key, 0) > COOLDOWN

    while True:
        try:
            # ── 1차: UI Automation — TextControl '수락' 탐색 ──────────
            # Flutter는 Button 타입 미사용, Text(50020) 타입으로 노출됨.
            # searchDepth=15 로 깊은 Flutter 트리까지 탐색.
            elem = auto.TextControl(searchDepth=15, Name="수락")
            if elem.Exists(maxSearchSeconds=0):
                rect = elem.BoundingRectangle
                cx = (rect.left + rect.right) // 2
                cy = (rect.top + rect.bottom) // 2
                key = (cx // 20, cy // 20)
                if can_click(key):
                    abs_click(cx, cy)
                    last_clicked[key] = time.time()
                    time.sleep(0.5)
                    continue

        except Exception:
            pass

        try:
            # ── 2차 폴백: Win32 창 탐색 ─────────────────────────────
            found_buttons = []

            def enum_child(child_hwnd, _):
                try:
                    if "수락" in win32gui.GetWindowText(child_hwnd):
                        found_buttons.append(child_hwnd)
                except Exception:
                    pass

            def enum_top(hwnd, _):
                if win32gui.IsWindowVisible(hwnd):
                    try:
                        win32gui.EnumChildWindows(hwnd, enum_child, None)
                    except Exception:
                        pass

            win32gui.EnumWindows(enum_top, None)

            for btn_hwnd in found_buttons:
                try:
                    r = win32gui.GetWindowRect(btn_hwnd)
                    cx = (r[0] + r[2]) // 2
                    cy = (r[1] + r[3]) // 2
                    key = (cx // 20, cy // 20)
                    if not can_click(key):
                        continue
                    win32gui.SendMessage(btn_hwnd, win32con.BM_CLICK, 0, 0)
                    abs_click(cx, cy)
                    last_clicked[key] = time.time()
                except Exception:
                    pass

        except Exception:
            pass

        time.sleep(1)


class SupportClientApp:
    def __init__(self, root):
        self.root = root
        self.root.title("원격지원 요청")
        self.root.geometry("480x360")
        self.root.resizable(False, False)

        # 배경색
        self.root.configure(bg="#f0f4f8")

        self.server_ip, self.server_port = load_config()
        self.computer_name = socket.gethostname()
        self.username = getpass.getuser()
        self.ip = get_local_ip()

        self._build_input_ui()

    def _build_input_ui(self):
        """증상 입력 화면 구성"""
        for widget in self.root.winfo_children():
            widget.destroy()

        title_font = tkfont.Font(family="맑은 고딕", size=16, weight="bold")
        label_font = tkfont.Font(family="맑은 고딕", size=10)
        btn_font = tkfont.Font(family="맑은 고딕", size=11, weight="bold")

        # 타이틀
        title_label = tk.Label(
            self.root, text="원격지원 요청", font=title_font,
            bg="#f0f4f8", fg="#1a365d"
        )
        title_label.pack(pady=(25, 5))

        # 정보 표시
        info_text = f"PC: {self.computer_name}  |  사용자: {self.username}  |  IP: {self.ip}"
        info_label = tk.Label(
            self.root, text=info_text, font=label_font,
            bg="#f0f4f8", fg="#4a5568"
        )
        info_label.pack(pady=(0, 15))

        # 증상 입력 안내
        symptom_label = tk.Label(
            self.root, text="증상을 입력하세요:", font=label_font,
            bg="#f0f4f8", fg="#2d3748", anchor="w"
        )
        symptom_label.pack(padx=40, fill="x")

        # 증상 입력 텍스트박스
        self.symptom_text = tk.Text(
            self.root, height=6, width=50, font=("맑은 고딕", 10),
            relief="solid", bd=1, wrap="word",
            padx=8, pady=8
        )
        self.symptom_text.pack(padx=40, pady=(5, 15))

        # 전송 버튼
        send_btn = tk.Button(
            self.root, text="지원 요청 전송", font=btn_font,
            bg="#3182ce", fg="white", activebackground="#2b6cb0",
            activeforeground="white", relief="flat",
            cursor="hand2", padx=30, pady=8,
            command=self._on_send
        )
        send_btn.pack()

    def _on_send(self):
        """전송 버튼 클릭"""
        symptom = self.symptom_text.get("1.0", "end").strip()
        if not symptom:
            messagebox.showwarning("입력 오류", "증상을 입력해 주세요.")
            return

        data = {
            "computer_name": self.computer_name,
            "username": self.username,
            "ip": self.ip,
            "symptom": symptom,
        }

        try:
            result = send_request(self.server_ip, self.server_port, data)
            if result.get("success"):
                self._show_waiting_screen()
            else:
                messagebox.showerror("전송 실패", result.get("error", "알 수 없는 오류"))
        except urllib.error.URLError as e:
            messagebox.showerror("연결 실패", f"서버에 연결할 수 없습니다.\n{e}")
        except Exception as e:
            messagebox.showerror("오류", f"요청 전송 중 오류가 발생했습니다.\n{e}")

    def _show_waiting_screen(self):
        """대기 화면 표시 + RustDesk 자동클릭 시작"""
        for widget in self.root.winfo_children():
            widget.destroy()

        wait_font = tkfont.Font(family="맑은 고딕", size=18, weight="bold")
        sub_font = tkfont.Font(family="맑은 고딕", size=10)

        frame = tk.Frame(self.root, bg="#f0f4f8")
        frame.place(relx=0.5, rely=0.5, anchor="center")

        # 대기 아이콘 (텍스트로 대체)
        icon_label = tk.Label(
            frame, text="🖥️", font=("Segoe UI Emoji", 48),
            bg="#f0f4f8"
        )
        icon_label.pack(pady=(0, 10))

        wait_label = tk.Label(
            frame, text="원격지원을 대기중입니다...",
            font=wait_font, bg="#f0f4f8", fg="#2b6cb0"
        )
        wait_label.pack(pady=(0, 10))

        sub_label = tk.Label(
            frame, text="잠시만 기다려 주세요. 담당자가 곧 연결합니다.",
            font=sub_font, bg="#f0f4f8", fg="#718096"
        )
        sub_label.pack()

        # scourt_help.exe 수락 버튼 자동 클릭 스레드 시작
        t = threading.Thread(target=scourt_auto_accept, daemon=True)
        t.start()


def main():
    root = tk.Tk()
    app = SupportClientApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
