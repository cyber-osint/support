# 원격지원 시스템

사내 원격지원 요청 및 관리를 위한 클라이언트-서버 시스템입니다.

## 프로젝트 구조

- **client/** -- tkinter GUI 클라이언트 (Windows EXE)
  - `main.py` -- 증상 입력, 서버 전송, 대기화면 표시, 원격지원 자동 수락
  - `config.ini` -- 서버 IP/포트 설정 (배포 시 수정 필요)
  - `requirements.txt` -- pywin32, psutil, uiautomation, pyinstaller
- **server/** -- Flask + Socket.IO 웹서버 (Windows EXE)
  - `app.py` -- REST API + Socket.IO + 브라우저 자동 오픈
  - `templates/index.html` -- 관리자 대시보드 (Bootstrap + Socket.IO 인라인 포함, CDN 불필요)
  - `requirements.txt` -- flask, flask-socketio, waitress, pyinstaller

## 주요 기능

### 클라이언트

- 증상 입력 후 서버로 전송, 전송 후 대기 화면 표시
- 백그라운드에서 법원 원격지원 프로그램(scourt_help.exe)의 "수락" 버튼 자동 클릭
  - 1차: Windows UI Automation (uiautomation) -- 멀티모니터 지원, 접근성 트리 탐색
  - 2차 폴백: Win32 API (win32gui)

### 서버

- 실행 시 자동으로 브라우저 열림 (`http://localhost:5000`)
- 실시간 대시보드 (Socket.IO)
- 요청 상태 관리: 대기중 -> 처리중 -> 완료
- 담당자 이름 + 처리 내역 기록
- 처리 이력 조회

## 배포

- **서버**: `support-server.exe` 실행 (DB 자동 생성, 브라우저 자동 오픈)
- **클라이언트**: `config.ini`에서 `ip =` 값을 서버 PC의 IP로 수정 후 `support-client.exe` 배포
- GitHub Release에서 최신 EXE 다운로드 가능

## 빌드

### 직접 빌드

```bash
cd client
pip install -r requirements.txt
pyinstaller build.spec
```

```bash
cd server
pip install -r requirements.txt
pyinstaller build.spec
```

### CI/CD (GitHub Actions)

- `.github/workflows/ci.yml` -- 모든 브랜치 push/PR 시 빌드 검증 (artifact 7일 보관)
- `.github/workflows/build.yml` -- `v*` 태그 push 또는 수동 실행 시 GitHub Release에 EXE 업로드

태그 push로 Release를 생성하려면:

```bash
git tag v1.0.0
git push origin v1.0.0
```
