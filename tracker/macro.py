import cv2
import numpy as np
import time
import os
import subprocess
import sys

# ✅ 한글 출력 깨짐 방지
sys.stdout.reconfigure(encoding='utf-8')

# ================= 1. 기본 설정 =================
ADB_CMD = r"C:\Program Files\BlueStacks_nxt\HD-Adb.exe"
GAME_PACKAGE = "com.nexon.dominations.asia.g"
TARGET_PORT = "5565" 
DEVICE_ADDRESS = f"127.0.0.1:{TARGET_PORT}"
WAIT_TIME = 2 * 60 * 60  # 2시간 대기

def run_adb(command):
    try:
        subprocess.call(f'"{ADB_CMD}" -s {DEVICE_ADDRESS} {command}', shell=True)
    except Exception as e:
        print(f"   ❌ ADB 명령 오류: {e}")

def imread_unicode(path, flags=cv2.IMREAD_COLOR):
    """한글 경로('바탕 화면') 내 이미지를 읽기 위한 보안 로직"""
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
        return int(max_loc[0] + template.shape[1]/2), int(max_loc[1] + template.shape[0]/2)
    return None

def click(x, y):
    run_adb(f'shell input swipe {x} {y} {x} {y} 100')
    print(f"   👆 클릭: ({x}, {y})")

# ================= 2. 핵심 로직 =================

def step1_restart_game():
    print(f"\n[Step 1] 게임 강제 종료 및 재접속")
    run_adb(f'shell am force-stop {GAME_PACKAGE}')
    time.sleep(1.0)
    run_adb('shell input keyevent KEYCODE_HOME')
    time.sleep(1.0)
    
    loc = find_image("icon.png", threshold=0.8)
    if loc:
        click(loc[0], loc[1])
        print("   🚀 게임 실행 중... (25초 로딩 대기)")
        time.sleep(25) 
    else:
        print("   ⚠️ 바탕화면에서 게임 아이콘을 못 찾았습니다.")
        return False

    print("   👀 팝업/광고 확인 중...")
    for _ in range(2):
        close_loc = find_image("close.png", threshold=0.85)
        if close_loc:
            print("   🧹 팝업 발견 -> 닫기")
            click(close_loc[0], close_loc[1])
            time.sleep(1.5)
        else: break
    return True

def step2_enter_building():
    print("[Step 2] 제조소 찾기 및 진입")
    target_images = ["building_done.png", "building.png"]
    found_loc = None

    for img_name in target_images:
        loc = find_image(img_name, threshold=0.9)
        if loc:
            print(f"   🏭 건물 발견 ({img_name})")
            found_loc = loc; break

    if not found_loc:
        print("   🔭 탐색 스와이프...")
        run_adb(f'shell input swipe 1400 540 500 540 800')
        time.sleep(1.5)
        for img_name in target_images:
            loc = find_image(img_name, threshold=0.9)
            if loc: found_loc = loc; break

    if found_loc:
        click(found_loc[0] + 20, found_loc[1] + 70)
        time.sleep(2.0)
        for _ in range(3):
            btn = find_image("enter_factory.png", threshold=0.85)
            if btn:
                click(btn[0], btn[1]); time.sleep(3); return True
            click(found_loc[0] + 20, found_loc[1] + 70); time.sleep(1.5)
    return False

def step3_go_production():
    print("[Step 3] 생산 탭 이동")
    for _ in range(3):
        loc = find_image("tab.png", threshold=0.8)
        if loc:
            click(loc[0], loc[1])
            print("   ✅ [생산] 탭 클릭")
            return True
        time.sleep(1)
    return False

def main():
    print(f"=== 🏭 제조소 24시간 구동 (롤백 버전) ===")
    try:
        run_adb(f"connect {DEVICE_ADDRESS}")
    except: pass
    
    while True:
        if step1_restart_game():
            if step2_enter_building():
                step3_go_production()
        
        print(f"\n💤 2시간 대기 시작...")
        remaining = WAIT_TIME
        while remaining > 0:
            print(f"   ⏳ {remaining // 60}분 남음...   ", end='\r')
            time.sleep(60); remaining -= 60

if __name__ == "__main__":
    main()