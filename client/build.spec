# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['main.py'],  # 실행 파일명이 main.py가 맞는지 확인하세요
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'win32gui', 'win32con', 'win32process', 'win32api', 'psutil',
        'uiautomation', 'comtypes', 'comtypes.client',
        'comtypes.stream',  # uiautomation 실행 시 누락되는 경우가 많음
        'comtypes.gen',     # 동적 생성되는 comtypes 인터페이스 포함
        'typing_extensions', # 종종 의존성 문제 발생
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

# PYZ, EXE 부분은 기존과 동일하거나 아래처럼 유지
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='support-client',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # 용량을 줄이려면 True, 실행 속도가 중요하다면 False
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False, # GUI 앱이므로 False 유지
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='icon.ico', # 아이콘이 있다면 추가하세요
)
