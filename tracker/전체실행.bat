@echo off
chcp 65001 >nul
title 도미네이션즈 완전 자동화 시스템
cd /d "%~dp0"

echo ==========================================
echo    🤖 시스템 가동! 블루스택과 봇을 실행합니다.
echo ==========================================
echo.

:: 1. 블루스택 실행 (게임 자동 실행 포함)
echo  [1/4] 블루스택 인스턴스 2개 동시 기동 중...
echo        (게임이 자동으로 실행됩니다)

:: RANK TRACKER용 (Pie64) 실행 -> 영예점수 모니터링
start "" "C:\Program Files\BlueStacks_nxt\HD-Player.exe" --instance Pie64 --cmd launchApp --package "com.nexon.dominations.asia.g"

:: MACRO용 (Pie64_1) 실행 -> 제조소 24시간 구동
start "" "C:\Program Files\BlueStacks_nxt\HD-Player.exe" --instance Pie64_1 --cmd launchApp --package "com.nexon.dominations.asia.g"

echo.
echo  ⏳ 게임 로딩 및 안정화를 위해 60초간 대기합니다...
echo     (컴퓨터가 느리다면 이 시간을 더 늘려주세요)
timeout /t 60 >nul

:: 2. 업데이트 알림봇 실행
echo.
echo  [2/4] 업데이트 알림봇 시작...
start "NewsBot" "업데이트 알림봇.bat"
timeout /t 2 >nul

:: 3. 영예점수 트래커 실행
echo  [3/4] 영예점수 모니터링 시작...
start "Tracker" "영예점수 모니터링.bat"
timeout /t 2 >nul

:: 4. 매크로 실행
echo  [4/4] 제조소 매크로 시작...
start "Macro" "제조소 24시간 구동.bat"

echo.
echo ==========================================
echo    ✅ 모든 시스템 가동 완료!
echo       오늘도 편안한 하루 되세요!
echo ==========================================
timeout /t 5
exit