# VERSION: MUMUPLAYER_260313A
# DESCRIPTION: 홀수 시간 정각 실행 스케줄러 + 엄격 검증 모드

import cv2
import numpy as np
import time
import os
import subprocess
import sys
import window_manager
from datetime import datetime, timedelta

# ✅ 한글 출력 깨짐 방지
sys.stdout.reconfigure(encoding='utf-8')

# ================= 1. 기본 설정 =================
ADB_CMD = r"C:\Program Files\Netease\MuMuPlayer\nx_main\adb.exe"
GAME_PACKAGE = "com.nexon.dominations.asia.g"
TARGET_PORT = "16416"
DEVICE_ADDRESS = f"127.0.0.1:{TARGET_PORT}"

# ================= 2. 기본 함수들 =================

def run_adb(command):
    try:
        subprocess.call(f'"{ADB_CMD}" -s {DEVICE_ADDRESS} {command}', shell=True)
    except Exception as e:
        print(f"    ❌ ADB 명령 오류: {e}")

def imread_unicode(path, flags=cv2.IMREAD_COLOR):
    try:
        n = np.fromfile(path, np.uint8)
        return cv2.imdecode(n, flags)
    except: return None

def capture_screen():
    try:
        filename = "view.png"
        run_adb(f'shell screencap -p /sdcard/{filename}')
        run_adb(f'pull /sdcard/{filename} .')
        if os.path.exists(filename):
            return imread_unicode(filename)
        return None
    except: return None

def find_image(target_file, threshold=0.8):
    if not os.path.exists(target_file): return None
    screen = capture_screen()
    if screen is None: return None
    template = imread_unicode(target_file, cv2.IMREAD_UNCHANGED)
    if template is None: return None

    if template.shape[2] == 4:
        result = cv2.matchTemplate(screen, template[:, :, :3], cv2.TM_CCORR_NORMED, mask=template[:, :, 3])
    else:
        result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
    
    _, max_val, _, max_loc = cv2.minMaxLoc(result)
    if max_val >= threshold:
        h, w = template.shape[:2]
        return int(max_loc[0] + w/2), int(max_loc[1] + h/2)
    return None

def click(x, y):
    run_adb(f'shell input swipe {x} {y} {x} {y} 100')
    print(f"    👆 클릭: ({x}, {y})")

def swipe(sx, sy, ex, ey, duration=800):
    run_adb(f'shell input swipe {sx} {sy} {ex} {ey} {duration}')
    time.sleep(1.5)

# ================= 3. 상태 기반 검증 로직 (엄격 모드 유지) =================

def step1_restart_and_popups():
    print(f"\n[Step 1] 게임 재접속 및 팝업 체크")
    run_adb(f'shell am force-stop {GAME_PACKAGE}')
    time.sleep(2.0)
    run_adb('shell input keyevent KEYCODE_HOME')
    
    print("    🚀 게임 실행 중... (초기 로딩 30초)")
    # 이미지 클릭 대신 ADB 명령어로 즉시 게임 실행
    run_adb(f'shell monkey -p {GAME_PACKAGE} -c android.intent.category.LAUNCHER 1')
    time.sleep(30)

    print("    👀 팝업/광고 스캔 중...")
    
    popup_count = 0
    for _ in range(7): 
        close_loc = find_image("close.png", threshold=0.85)
        if close_loc:
            print("    🧹 팝업 발견 -> 닫기")
            click(close_loc[0], close_loc[1])
            popup_count += 1
            print("    ⏳ 연쇄 팝업 대기 (3초)...") 
            time.sleep(3.0) 
        else:
            if popup_count > 0:
                print("    ✨ 추가 팝업 없음 확인 (최종 대기 2초)")
                time.sleep(2.0)
            else:
                print("    ✨ 팝업 없음 -> 즉시 진행")
            break
    return True

def step2_find_building_360():
    print("[Step 2] 제조소 건물 탐색")
    target_images = ["building_done.png", "building.png"]
    
    scan_moves = [
        ("None", 0, 0, 0, 0),
        ("⬆️ 위로 스와이프", 960, 300, 960, 800),
        ("➡️ 오른쪽으로 스와이프", 1400, 540, 500, 540),
        ("⬇️ 아래로 스와이프", 960, 800, 960, 300),
        ("⬅️ 왼쪽으로 스와이프", 500, 540, 1400, 540),
        ("⬆️ 마지막 위로 보정", 960, 300, 960, 800)
    ]

    for move_name, sx, sy, ex, ey in scan_moves:
        if move_name != "None":
            print(f"    🏃 {move_name}")
            swipe(sx, sy, ex, ey)
        
        for img in target_images:
            loc = find_image(img, threshold=0.9)
            if loc:
                print(f"    🏭 건물 발견! ({img})")
                return loc
    return None

def step3_enter_logic(building_loc):
    print("[Step 3] 제조 버튼(enter_factory) 검증")
    tx, ty = building_loc[0] + 20, building_loc[1] + 70

    for i in range(3):
        click(tx, ty)
        time.sleep(2.5) 
        
        btn = find_image("enter_factory.png", threshold=0.95)
        if btn:
            print(f"    🔘 제조 버튼 확실함(95% 일치) -> 진입")
            click(btn[0], btn[1])
            time.sleep(4.0)
            return True
        
        print(f"    ⚠️ 버튼 안 보임 (또는 팝업 가림) -> 재클릭 시도 ({i+1}/3)")
    
    return False

def step4_verify_tab():
    print("[Step 4] 생산 탭 로드 확인")
    for i in range(10):
        loc = find_image("tab.png", threshold=0.92)
        if loc:
            click(loc[0], loc[1])
            print("    ✅ 생산 탭 진입 성공!")
            return True
        print(f"    ⏳ 생산 탭 대기 중... ({i+1}/10)")
        time.sleep(1.0)
    return False

# 🔥 다음 홀수 시간 계산 함수
def get_seconds_until_next_odd_hour():
    now = datetime.now()
    # 0~23시 중 홀수 시간 리스트
    odd_hours = [1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23]
    
    target_dt = None
    for h in odd_hours:
        # 오늘 날짜의 해당 시간(h시 0분 0초)
        candidate = now.replace(hour=h, minute=0, second=0, microsecond=0)
        # 현재 시간보다 미래라면 목표로 설정
        if candidate > now:
            target_dt = candidate
            break
            
    # 오늘의 남은 홀수 시간이 없으면 내일 01시로 설정
    if target_dt is None:
        target_dt = now.replace(hour=1, minute=0, second=0, microsecond=0) + timedelta(days=1)
        
    wait_seconds = (target_dt - now).total_seconds()
    return int(wait_seconds), target_dt.strftime("%H:%M")

def main():
    window_manager.restore_and_autosave("제조소 스케줄러")
    print(f"=== 🏭 제조소 오토 (Ver. 20260206A) ===")
    
    try: run_adb(f"connect {DEVICE_ADDRESS}")
    except: pass
    
    while True:
        # 1. 매크로 작업 수행 (실행 직후 즉시 1회 수행)
        if step1_restart_and_popups():
            b_loc = step2_find_building_360()
            if b_loc:
                if step3_enter_logic(b_loc):
                    step4_verify_tab()
        
        # 2. 다음 홀수 시간까지 대기
        wait_sec, next_time_str = get_seconds_until_next_odd_hour()
        print(f"\n💤 작업 완료. 다음 실행 시간: {next_time_str} (약 {wait_sec//60}분 후)")
        
        while wait_sec > 0:
            mins, secs = divmod(wait_sec, 60)
            print(f"    ⏳ 다음 실행({next_time_str})까지 {mins}분 {secs}초 남음...    ", end='\r')
            time.sleep(1)
            wait_sec -= 1

if __name__ == "__main__":
    main()