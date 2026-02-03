@echo off
chcp 65001 >nul
title 도미네이션즈 뉴스 알림 봇
mode con: cols=80 lines=20

:: 이 파일이 있는 폴더로 이동
cd /d "%~dp0"

cls
echo =================================================
echo        도미네이션즈 뉴스 알림 봇 가동 중
echo =================================================
echo.
echo  [실행 시간] %time%
echo  [상태] 봇을 실행합니다...
echo.

:: 파일이 진짜 있는지 확인하는 안전장치
if not exist "news_checker.py" (
    echo.
    echo  [오류] news_checker.py 파일을 찾을 수 없습니다!
    echo  1. 이 파일이 news_checker.py 와 같은 폴더에 있는지 확인하세요.
    echo  2. 파일 이름 뒤에 .txt 가 붙어있는지 확인하세요.
    echo.
    pause
    exit
)

:: 파이썬 스크립트 실행
python news_checker.py

echo.
echo =================================================
echo  ⚠️ 봇이 종료되었습니다.
echo =================================================
pause