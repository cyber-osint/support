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


def rustdesk_auto_accept():
    """
    백그라운드 스레드: RustDesk 연결 요청 수락 버튼 자동 클릭.
    RustDesk 창이 실제로 감지된 경우에만 클릭하며,
    창이 없을 때는 마우스를 일절 움직이지 않는다.
    """
    try:
        import pyautogui
        import pygetwindow as gw
    except ImportError:
        return

    pyautogui.FAILSAFE = False
    clicked_ids = set()  # 이미 수락한 창 ID 중복 클릭 방지

    while True:
        try:
            # "연결 요청" 또는 "RustDesk" 제목의 창만 탐색
            candidates = (
                gw.getWindowsWithTitle("연결 요청") +
                gw.getWindowsWithTitle("Connection Request") +
                gw.getWindowsWithTitle("RustDesk")
            )
            for win in candidates:
                try:
                    win_id = (win.left, win.top, win.width, win.height)
                    if not win.visible or win.width <= 0 or win_id in clicked_ids:
                        continue
                    # 수락 버튼: RustDesk 연결 요청 창 하단 중앙
                    win.activate()
                    time.sleep(0.2)
                    center_x = win.left + win.width // 2
                    button_y = win.top + win.height - 55
                    pyautogui.click(center_x, button_y)
                    clicked_ids.add(win_id)
                except Exception:
                    pass
        except Exception:
            pass

        time.sleep(2)


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

        # RustDesk 자동 수락 스레드 시작
        t = threading.Thread(target=rustdesk_auto_accept, daemon=True)
        t.start()


def main():
    root = tk.Tk()
    app = SupportClientApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
