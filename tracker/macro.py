import cv2
import numpy as np
import time
import os
import subprocess
import sys
import re

# ✅ 한글 출력 깨짐 방지
sys.stdout.reconfigure(encoding='utf-8')

# ================= 1. 기본 설정 =================
ADB_CMD = "adb"
TARGET_PORT = "5565" 
DEVICE_ADDRESS = f"127.0.0.1:{TARGET_PORT}"

# 🔥 [중요] 도미네이션즈 패키지 이름 (한국/아시아 서버 기준)
# 만약 이 이름으로 안 꺼지면, 구글 플레이 스토어 주소 끝부분을 확인해야 함.
GAME_PACKAGE = "com.nexon.dominations.asia.adk" 

# 🕒 반복 주기 (2시간)
WAIT_TIME = 2 * 60 * 60 

# 화면 해상도 (자동 감지)
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
SCALE_RATIO = 1.0

# ================= 2. 기본 함수들 =================

def run_adb(command):
    subprocess.call(f'"{ADB_CMD}" -s {DEVICE_ADDRESS} {command}', shell=True)

def run_adb_output(command):
    try:
        result = subprocess.check_output(f'"{ADB_CMD}" -s {DEVICE_ADDRESS} {command}', shell=True)
        return result.decode('utf-8').strip()
    except: return ""

def get_screen_resolution():
    global SCREEN_WIDTH, SCREEN_HEIGHT, SCALE_RATIO
    print("📏 화면 해상도 확인 중...")
    output = run_adb_output("shell wm size") 
    match = re.search(r'(\d+)x(\d+)', output)
    if match:
        w = int(match.group(1))
        h = int(match.group(2))
        if h > w: SCREEN_WIDTH, SCREEN_HEIGHT = h, w
        else: SCREEN_WIDTH, SCREEN_HEIGHT = w, h
        
        SCALE_RATIO = SCREEN_WIDTH / 1920.0
        print(f"   📺 감지된 해상도: {SCREEN_WIDTH} x {SCREEN_HEIGHT}")
    else:
        print("   ⚠️ 해상도 감지 실패. 1080p 기준으로 진행합니다.")

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
        print(f"   ⚠️ 파일 없음: {target_file}")
        return None
    
    screen = capture_screen()
    if screen is None: return None
    
    template = cv2.imread(target_file, cv2.IMREAD_UNCHANGED)
    if template is None: return None

    if template.shape[2] == 4:
        template_img = template[:, :, :3]
        mask = template[:, :, 3]
        result = cv2.matchTemplate(screen, template_img, cv2.TM_CCORR_NORMED, mask=mask)
    else:
        result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
    
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    
    if max_val >= threshold:
        h, w = template.shape[:2]
        return int(max_loc[0] + w/2), int(max_loc[1] + h/2)
    return None

def click(x, y):
    run_adb(f'shell input tap {x} {y}')
    print(f"   👆 클릭: {x}, {y}")

def swipe_screen():
    start_x = int(SCREEN_WIDTH * 0.6)
    end_x = int(SCREEN_WIDTH * 0.4)
    y = int(SCREEN_HEIGHT * 0.5)
    run_adb(f'shell input swipe {start_x} {y} {end_x} {y} 500')

# ================= 3. 핵심 로직 =================

def step1_restart_game():
    print(f"\n[Step 1] 게임 강제 종료 및 재접속")
    
    # 🔥 1. 게임 강제 종료 (Kill Process)
    print(f"   💀 앱 강제 종료: {GAME_PACKAGE}")
    run_adb(f'shell am force-stop {GAME_PACKAGE}')
    time.sleep(2.0)
    
    # 2. 홈 화면으로 이동 (바탕화면 아이콘 찾기 위해)
    run_adb('shell input keyevent KEYCODE_HOME')
    time.sleep(1.0)
    
    # 3. 게임 아이콘 찾아서 클릭
    loc = find_image("icon.png", threshold=0.8)
    if loc:
        click(loc[0], loc[1])
        print("   🚀 게임 실행 중... (40초 로딩 대기)")
        time.sleep(40) # 로딩 시간 넉넉히
    else:
        print("   ⚠️ 바탕화면에서 게임 아이콘을 못 찾았습니다.")
        return False

    # 4. 팝업 닫기 (최대 5번 시도)
    print("   🧹 팝업/광고 닫기 시도...")
    for _ in range(5):
        close_loc = find_image("close.png", threshold=0.8)
        if close_loc:
            click(close_loc[0], close_loc[1])
            time.sleep(2)
        else:
            break
    return True

def step2_enter_building():
    print("[Step 2] 제조소 찾기 및 진입")
    
    # 1. [우선순위] 완료된 건물(구슬 뜬 것) 찾기
    loc = find_image("building_done.png", threshold=0.7)
    if loc:
        print("   🏭 [수확 가능] 건물 발견!")
        click(loc[0], loc[1])
    else:
        # 2. 없으면 일반 건물 찾기
        loc = find_image("building.png", threshold=0.7)
        if loc:
            print("   🏭 [일반] 건물 발견!")
            click(loc[0], loc[1])
        else:
            print("   🔭 건물이 안 보여서 화면을 살짝 이동합니다.")
            swipe_screen()
            time.sleep(1.5)
            # 이동 후 재시도
            loc = find_image("building.png", threshold=0.7)
            if loc: click(loc[0], loc[1])
    
    time.sleep(1.5)
    
    # 3. [진입] 버튼 누르기
    enter_btn = find_image("enter_factory.png", threshold=0.8)
    if enter_btn:
        print("   🔘 [진입] 버튼 클릭")
        click(enter_btn[0], enter_btn[1])
        time.sleep(3) # 진입 대기
        return True
    
    print("   ⚠️ 건물 진입 실패 (버튼 못 찾음)")
    return False

def step3_go_production():
    print("[Step 3] 생산 탭 이동")
    loc = find_image("tab.png", threshold=0.8)
    if loc:
        click(loc[0], loc[1])
        print("   ✅ [생산] 탭 클릭 완료")
        return True
    print("   ⚠️ 생산 탭을 못 찾았습니다.")
    return False

# ================= 4. 메인 실행 =================

def main():
    print(f"=== 🏭 도미네이션즈 심플 봇 (2시간 주기) ===")
    os.system(f"{ADB_CMD} connect {DEVICE_ADDRESS}")
    get_screen_resolution()

    while True:
        # 1. 게임 끄고 켜기
        if step1_restart_game():
            # 2. 건물 들어가기
            if step2_enter_building():
                # 3. 탭 누르기
                step3_go_production()
        
        # 4. 2시간 대기
        print(f"\n💤 작업 완료. 2시간({WAIT_TIME}초) 동안 대기합니다...")
        remaining = WAIT_TIME
        
        while remaining > 0:
            mins = remaining // 60
            print(f"   ⏳ 남은 시간: {mins}분      ", end='\r')
            time.sleep(60) 
            remaining -= 60
        
        print("\n⏰ 대기 종료! 다시 시작합니다.\n")

if __name__ == "__main__":
    main()