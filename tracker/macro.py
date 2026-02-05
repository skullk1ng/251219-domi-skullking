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

def imread_unicode(path, flags=cv2.IMREAD_COLOR):
    """한글 경로 이미지 로딩 에러 방지"""
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

# ================= 2. 핵심 로직 (딜레이 최적화) =================

def step1_restart_game():
    print(f"\n[Step 1] 게임 강제 종료 및 재접속")
    run_adb(f'shell am force-stop {GAME_PACKAGE}')
    time.sleep(2.0)
    run_adb('shell input keyevent KEYCODE_HOME')
    time.sleep(2.0)
    
    loc = find_image("icon.png", threshold=0.8)
    if loc:
        click(loc[0], loc[1])
        print("   🚀 게임 로딩 대기 (30초로 증설)")
        time.sleep(30) # 로딩 시간을 5초 더 늘려 안정성 확보
    else:
        return False

    print("   👀 팝업/광고 확인 중...")
    for _ in range(3): # 팝업 체크 횟수 증가
        close_loc = find_image("close.png", threshold=0.8)
        if close_loc:
            click(close_loc[0], close_loc[1])
            time.sleep(2.0) # 팝업 닫힌 후 대기 시간 증가
        else: break
    return True

def step2_enter_building():
    print("[Step 2] 제조소 찾기 및 진입")
    # 진입 전 잔여 팝업 다시 한 번 체크
    for _ in range(2):
        close = find_image("close.png", threshold=0.8)
        if close: click(close[0], close[1]); time.sleep(2.0)

    target_images = ["building_done.png", "building.png"]
    found_loc = None

    # 건물 탐색 로직 (1차/2차)
    for img_name in target_images:
        loc = find_image(img_name, threshold=0.85)
        if loc: found_loc = loc; break

    if not found_loc:
        print("   🔭 탐색 스와이프...")
        run_adb(f'shell input swipe 1400 540 500 540 800')
        time.sleep(2.0)
        for img_name in target_images:
            loc = find_image(img_name, threshold=0.85)
            if loc: found_loc = loc; break

    if found_loc:
        # 클릭 후 건물이 선택될 때까지의 대기 시간 보강
        click(found_loc[0] + 20, found_loc[1] + 70)
        time.sleep(2.5) 
        
        for i in range(5): # 진입 버튼 탐색 횟수 대폭 강화
            btn = find_image("enter_factory.png", threshold=0.8)
            if btn:
                click(btn[0], btn[1])
                print("   🔘 [진입] 버튼 클릭 성공")
                time.sleep(4.0) # 건물 진입 내부 로딩 대기
                return True
            # 버튼이 안 보이면 건물을 다시 클릭하여 메뉴 활성화 유도
            print(f"   ⚠️ 진입 버튼 대기 중... ({i+1}/5)")
            click(found_loc[0] + 20, found_loc[1] + 70)
            time.sleep(2.0)
    return False

def step3_go_production():
    """생산 탭 이동 로직 강화"""
    print("[Step 3] 생산 탭 이동 시도")
    # 진입 직후 화면이 멈춰있을 수 있으므로 잠시 더 대기
    time.sleep(2.0)
    
    for i in range(5): # 탭 인식 시도 횟수 증가
        loc = find_image("tab.png", threshold=0.75) # 인식률 임계치 살짝 완화
        if loc:
            click(loc[0], loc[1])
            print("   ✅ [생산] 탭 클릭 완료")
            time.sleep(2.0)
            return True
        print(f"   ⚠️ 생산 탭 찾는 중... ({i+1}/5)")
        time.sleep(1.5)
    
    print("   ❌ 생산 탭 진입 실패")
    return False

def main():
    window_manager.restore_and_autosave(WIN_TITLE)
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