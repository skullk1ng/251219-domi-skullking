@echo off
cd /d "%~dp0"

echo ==========================================
echo       Dominations Tracker Bot Start
echo ==========================================

echo [1] BlueStacks 연결 시도 중...
.\adb connect 127.0.0.1:5555

echo.
echo [2] 봇 프로그램을 실행합니다...
python tracker.py

pause