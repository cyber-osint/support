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

# 추가된 라이브러리 (pip install psutil 필요)
try:
    import psutil
    import uiautomation as auto
    import win32gui
    import win32con
    import win32api
    import ctypes
except ImportError:
    pass


def get_exe_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def load_config():
    config_path = os.path.join(get_exe_dir(), "config.ini")
    if not os.path.exists(config_path):
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
    백그라운드 스레드: scourt_support.exe 프로세스를 찾아 내부의 '수락' 버튼 자동 클릭.
    범위 한정 검색으로 응답 속도를 0.5초 이내로 단축함.
    """
    PROCESS_NAME = "scourt_support.exe"

    # 프로세스를 Per-Monitor DPI Aware로 설정 — 멀티모니터 좌표 정확도 확보
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

    # uiautomation 검색 성능 최적화 설정
    auto.uiautomation.SetGlobalSearchTimeout(0.5)

    last_clicked = {}
    COOLDOWN = 3.0

    print(f"[*] {PROCESS_NAME} 자동 수락 모니터링 활성화")

    while True:
        try:
            # 1. 대상 프로세스의 PID 실시간 확인 (꺼졌다 켜져도 대응)
            target_pid = None
            for proc in psutil.process_iter(['name', 'pid']):
                if proc.info['name'].lower() == PROCESS_NAME.lower():
                    target_pid = proc.info['pid']
                    break
            
            if target_pid:
                # 2. 핵심 최적화: ProcessId를 명시하여 검색 범위를 해당 앱 내부로 제한
                # Flutter 앱 특성에 맞춰 TextControl 탐색 (searchDepth 10은 충분)
                accept_btn = auto.TextControl(searchDepth=10, Name="수락", ProcessId=target_pid)

                if accept_btn.Exists(0):
                    rect = accept_btn.BoundingRectangle
                    cx, cy = rect.centerX(), rect.centerY()
                    
                    key = (cx // 10, cy // 10)
                    if time.time() - last_clicked.get(key, 0) > COOLDOWN:
                        # 좌표 클릭 실행
                        win32api.SetCursorPos((cx, cy))
                        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                        time.sleep(0.05)
                        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                        
                        last_clicked[key] = time.time()
                        print(f"[클릭] {PROCESS_NAME} 연결 수락 완료 ({cx}, {cy})")
            
        except Exception:
            pass

        # 탐색 주기를 짧게 가져가서 반응성을 높임
        time.sleep(0.3)


class SupportClientApp:
    def __init__(self, root):
        self.root = root
        self.root.title("원격지원 요청")
        self.root.geometry("480x360")
        self.root.resizable(False, False)
        self.root.configure(bg="#f0f4f8")

        self.server_ip, self.server_port = load_config()
        self.computer_name = socket.gethostname()
        self.username = getpass.getuser()
        self.ip = get_local_ip()

        self._build_input_ui()

    def _build_input_ui(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        title_font = tkfont.Font(family="맑은 고딕", size=16, weight="bold")
        label_font = tkfont.Font(family="맑은 고딕", size=10)
        btn_font = tkfont.Font(family="맑은 고딕", size=11, weight="bold")

        title_label = tk.Label(self.root, text="원격지원 요청", font=title_font, bg="#f0f4f8", fg="#1a365d")
        title_label.pack(pady=(25, 5))

        info_text = f"PC: {self.computer_name}  |  사용자: {self.username}  |  IP: {self.ip}"
        info_label = tk.Label(self.root, text=info_text, font=label_font, bg="#f0f4f8", fg="#4a5568")
        info_label.pack(pady=(0, 15))

        symptom_label = tk.Label(self.root, text="증상을 입력하세요:", font=label_font, bg="#f0f4f8", fg="#2d3748", anchor="w")
        symptom_label.pack(padx=40, fill="x")

        self.symptom_text = tk.Text(self.root, height=6, width=50, font=("맑은 고딕", 10), relief="solid", bd=1, wrap="word", padx=8, pady=8)
        self.symptom_text.pack(padx=40, pady=(5, 15))

        send_btn = tk.Button(self.root, text="지원 요청 전송", font=btn_font, bg="#3182ce", fg="white", activebackground="#2b6cb0", activeforeground="white", relief="flat", cursor="hand2", padx=30, pady=8, command=self._on_send)
        send_btn.pack()

    def _on_send(self):
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
            # 실제 서버 구축 전 테스트 시에는 아래 API 전송 부분을 주석처리하거나 예외처리 하세요.
            result = send_request(self.server_ip, self.server_port, data)
            if result.get("success"):
                self._show_waiting_screen()
            else:
                messagebox.showerror("전송 실패", result.get("error", "알 수 없는 오류"))
        except Exception as e:
            # 테스트를 위해 서버 연동 없이 화면 전환만 보고 싶다면 _show_waiting_screen() 바로 호출 가능
            messagebox.showerror("연결 실패", f"서버 연결 오류: {e}")

    def _show_waiting_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        wait_font = tkfont.Font(family="맑은 고딕", size=18, weight="bold")
        sub_font = tkfont.Font(family="맑은 고딕", size=10)

        frame = tk.Frame(self.root, bg="#f0f4f8")
        frame.place(relx=0.5, rely=0.5, anchor="center")

        icon_label = tk.Label(frame, text="🖥️", font=("Segoe UI Emoji", 48), bg="#f0f4f8")
        icon_label.pack(pady=(0, 10))

        wait_label = tk.Label(frame, text="원격지원을 대기중입니다...", font=wait_font, bg="#f0f4f8", fg="#2b6cb0")
        wait_label.pack(pady=(0, 10))

        sub_label = tk.Label(frame, text="잠시만 기다려 주세요. 담당자가 곧 연결합니다.", font=sub_font, bg="#f0f4f8", fg="#718096")
        sub_label.pack()

        # 자동 수락 스레드 시작
        t = threading.Thread(target=scourt_auto_accept, daemon=True)
        t.start()


def main():
    root = tk.Tk()
    app = SupportClientApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
