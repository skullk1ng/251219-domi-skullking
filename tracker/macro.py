import cv2
import numpy as np
import time
import os
import subprocess
import sys
import re
import pyautogui  # 물리적 단축키 전송용
import window_manager

# ✅ 한글 출력 깨짐 방지
sys.stdout.reconfigure(encoding='utf-8')

# ================= 1. 기본 설정 =================
ADB_CMD = r"C:\Program Files\BlueStacks_nxt\HD-Adb.exe"
GAME_PACKAGE = "com.nexon.dominations.asia.g"
TARGET_PORT = "5565" 
DEVICE_ADDRESS = f"127.0.0.1:{TARGET_PORT}"
WIN_TITLE = "1"  # 🔥 확인된 매크로용 창 이름 적용
WAIT_TIME = 2 * 60 * 60 

# 해상도 비율 1.0 고정
REAL_RATIO_X = 1.0
REAL_RATIO_Y = 1.0

# ================= 2. 기본 함수들 =================

def run_adb(command):
    try:
        subprocess.call(f'"{ADB_CMD}" -s {DEVICE_ADDRESS} {command}', shell=True)
    except Exception as e:
        print(f"   ❌ ADB 명령 오류: {e}")

def cleanup_bluestacks_memory():
    """지정된 창('1')을 활성화한 후 PyAutoGUI 단축키(Ctrl+Shift+F)로 메모리 정리"""
    print(f"🧹 {WIN_TITLE} 창 메모리 최적화 수행 (빗자루)...")
    try:
        # 1. 담당하는 블루스택 창('1')을 맨 앞으로 가져옴
        window_manager.restore_and_autosave(WIN_TITLE)
        time.sleep(1.0) 
        
        # 2. 윈도우 차원에서 직접 단축키 신호를 보냄
        pyautogui.hotkey('ctrl', 'shift', 'f')
        time.sleep(4.0) 
    except Exception as e:
        print(f"⚠️ {WIN_TITLE} 메모리 정리 실패: {e}")

def capture_screen():
    try:
        filename = "view.png"
        run_adb(f'shell screencap -p /sdcard/{filename}')
        run_adb(f'pull /sdcard/{filename} .')
        if os.path.exists(filename):
            return cv2.imread(filename)
        return None
    except: return None

def find_image(target_file, threshold=0.8):
    if not os.path.exists(target_file):
        return None
    screen = capture_screen()
    if screen is None: return None
    template = cv2.imread(target_file, cv2.IMREAD_UNCHANGED)
    if template is None: return None

    if template.shape[2] == 4:
        result = cv2.matchTemplate(screen, template[:, :, :3], cv2.TM_CCORR_NORMED, mask=template[:, :, 3])
    else:
        result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
    
    _, max_val, _, max_loc = cv2.minMaxLoc(result)
    if max_val >= threshold:
        return int(max_loc[0] + template.shape[1]/2), int(max_loc[1] + template.shape[0]/2)
    return None

def click(x, y):
    run_adb(f'shell input swipe {x} {y} {x} {y} 100')
    print(f"   👆 클릭: ({x}, {y})")

# ================= 3. 핵심 로직 =================

def step1_restart_game():
    print(f"\n[Step 1] 게임 종료 및 재접속")
    run_adb(f'shell am force-stop {GAME_PACKAGE}')
    
    # 🔥 창 '1' 활성화 후 빗자루 기능 실행
    cleanup_bluestacks_memory()
    
    time.sleep(1.0)
    run_adb('shell input keyevent KEYCODE_HOME')
    time.sleep(1.0)
    
    loc = find_image("icon.png", threshold=0.8)
    if loc:
        click(loc[0], loc[1])
        print("   🚀 게임 실행 중... (25초 로딩 대기)")
        time.sleep(25) 
    else:
        print("   ⚠️ 바탕화면에서 아이콘을 찾지 못했습니다.")
        return False

    print("   👀 팝업/광고 확인 중...")
    for _ in range(2):
        close_loc = find_image("close.png", threshold=0.85)
        if close_loc:
            click(close_loc[0], close_loc[1])
            time.sleep(1.5)
        else: break
    return True

# (중략: step2_enter_building 및 step3_go_production 로직은 사용자 코드 유지)

def main():
    window_manager.restore_and_autosave(WIN_TITLE)
    print(f"=== 🏭 제조소 24시간 구동 (창: {WIN_TITLE}) ===")
    
    try:
        subprocess.call(f'"{ADB_CMD}" connect {DEVICE_ADDRESS}', shell=True)
    except: pass
    
    while True:
        if step1_restart_game():
            # (step2, step3 실행 로직...)
            pass
        
        print(f"\n💤 2시간 대기 시작...")
        remaining = WAIT_TIME
        while remaining > 0:
            print(f"   ⏳ {remaining // 60}분 남음...   ", end='\r')
            time.sleep(60)
            remaining -= 60

if __name__ == "__main__":
    main()