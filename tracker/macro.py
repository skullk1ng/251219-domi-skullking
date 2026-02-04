import cv2
import numpy as np
import time
import os
import subprocess
import sys
import window_manager

# ✅ 한글 출력 깨짐 방지
sys.stdout.reconfigure(encoding='utf-8')

# ================= 1. 기본 설정 =================
ADB_CMD = r"C:\Program Files\BlueStacks_nxt\HD-Adb.exe"
GAME_PACKAGE = "com.nexon.dominations.asia.g"
TARGET_PORT = "5565" 
DEVICE_ADDRESS = f"127.0.0.1:{TARGET_PORT}"
WIN_TITLE = "1"
WAIT_TIME = 2 * 60 * 60 

def run_adb(command):
    subprocess.call(f'"{ADB_CMD}" -s {DEVICE_ADDRESS} {command}', shell=True)

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
    if not os.path.exists(target_file): return None
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
    print(f"\n[Step 1] 게임 강제 종료 및 재접속")
    run_adb(f'shell am force-stop {GAME_PACKAGE}')
    
    # 🔥 메모리 정리(cleanup_bluestacks_memory) 함수 호출 삭제됨
    
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

def step2_enter_building():
    print("[Step 2] 제조소 찾기 및 진입")
    close_loc = find_image("close.png", threshold=0.85)
    if close_loc:
        click(close_loc[0], close_loc[1])
        time.sleep(1.5)

    target_images = ["building_done.png", "building.png"]
    found_loc = None

    for img_name in target_images:
        loc = find_image(img_name, threshold=0.9)
        if loc:
            found_loc = loc; break

    if not found_loc:
        print("   🔭 4방향 탐색 시작")
        swipe_moves = [
            ("➡️ 우", 1400, 540, 500, 540), ("⬇️ 하", 960, 800, 960, 300),
            ("⬅️ 좌", 500, 540, 1400, 540), ("⬆️ 상", 960, 300, 960, 800)
        ]
        for move_name, sx, sy, ex, ey in swipe_moves:
            run_adb(f'shell input swipe {sx} {sy} {ex} {ey} 800'); time.sleep(1.5)
            for img_name in target_images:
                loc = find_image(img_name, threshold=0.9)
                if loc: found_loc = loc; break
            if found_loc: break

    if found_loc:
        click(found_loc[0] + 20, found_loc[1] + 70)
        time.sleep(2.0)
        for _ in range(3):
            btn = find_image("enter_factory.png", threshold=0.85)
            if btn: click(btn[0], btn[1]); return True
            click(found_loc[0] + 20, found_loc[1] + 70); time.sleep(1.5)
    return False

def step3_go_production():
    print("[Step 3] 생산 탭 이동")
    for _ in range(3):
        loc = find_image("tab.png", threshold=0.8)
        if loc: click(loc[0], loc[1]); return True
        time.sleep(1)
    return False

def main():
    window_manager.restore_and_autosave(WIN_TITLE)
    while True:
        if step1_restart_game():
            if step2_enter_building(): step3_go_production()
        
        print(f"\n💤 2시간 대기 시작...")
        remaining = WAIT_TIME
        while remaining > 0:
            print(f"   ⏳ {remaining // 60}분 남음...   ", end='\r')
            time.sleep(60); remaining -= 60

if __name__ == "__main__":
    main()