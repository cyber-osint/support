# 원격지원 시스템

사내 원격지원 요청 및 관리를 위한 클라이언트-서버 시스템입니다.

## 구성

- **client/** - 원격지원 요청 클라이언트 (tkinter GUI)
- **server/** - 관리 서버 및 웹 대시보드 (Flask + Socket.IO)

## 빠른 시작

### 서버 실행
```bash
cd server
pip install -r requirements.txt
python app.py
```
브라우저에서 http://localhost:5000 으로 대시보드에 접속합니다.

### 클라이언트 실행
```bash
cd client
pip install -r requirements.txt
python main.py
```
`config.ini`에서 서버 IP와 포트를 설정한 후 실행합니다.

## EXE 빌드

### 클라이언트
```bash
cd client
pip install -r requirements.txt
pyinstaller build.spec
```

### 서버
```bash
cd server
pip install -r requirements.txt
pyinstaller build.spec
```

## GitHub Actions

`main` 브랜치에 push하면 자동으로 Windows EXE가 빌드됩니다.
Artifacts에서 `support-client.exe`와 `support-server.exe`를 다운로드할 수 있습니다.
