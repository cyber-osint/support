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


def get_resource_path(relative_path):
    """PyInstaller _MEIPASS 경로 처리"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)


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
    """config.ini에서 서버 설정 읽기"""
    config = configparser.ConfigParser()
    config_path = get_resource_path("config.ini")
    config.read(config_path, encoding="utf-8")
    server_ip = config.get("server", "ip", fallback="127.0.0.1")
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
    백그라운드 스레드: RustDesk 수락 버튼 자동 클릭
    pyautogui + pygetwindow 사용
    """
    try:
        import pyautogui
        import pygetwindow as gw
    except ImportError:
        return

    pyautogui.FAILSAFE = False

    while True:
        try:
            # RustDesk 창 탐색
            windows = gw.getWindowsWithTitle("RustDesk")
            if windows:
                for win in windows:
                    try:
                        if win.visible and win.width > 0 and win.height > 0:
                            # 창 활성화 후 수락 버튼 위치 클릭 시도
                            win.activate()
                            time.sleep(0.3)
                            # RustDesk 수락 버튼은 보통 창 하단 중앙 부근
                            center_x = win.left + win.width // 2
                            button_y = win.top + win.height - 60
                            pyautogui.click(center_x, button_y)
                    except Exception:
                        pass
            else:
                # RustDesk 창이 없으면 화면 우상단 영역 클릭 시도
                # (알림 팝업이 우상단에 뜨는 경우)
                screen_w, screen_h = pyautogui.size()
                try:
                    pyautogui.click(screen_w - 150, 80)
                except Exception:
                    pass
        except Exception:
            pass

        time.sleep(3)


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
