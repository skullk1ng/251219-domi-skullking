import cv2
import numpy as np
import time
import os
import subprocess
import sys
import re
import window_manager  # 👈 [추가] 창 관리 모듈

# ✅ 한글 출력 깨짐 방지
sys.stdout.reconfigure(encoding='utf-8')

# ================= 1. 기본 설정 =================

# 🔥 [핵심] 블루스택 전용 ADB 경로로 고정 (버전 충돌 방지)
ADB_CMD = r"C:\Program Files\BlueStacks_nxt\HD-Adb.exe"

# 게임 패키지 이름
GAME_PACKAGE = "com.nexon.dominations.asia.g"

# 포트 번호 (스크린샷에 5565로 확인됨)
TARGET_PORT = "5565" 
DEVICE_ADDRESS = f"127.0.0.1:{TARGET_PORT}"

# 🕒 반복 주기 (2시간)
WAIT_TIME = 2 * 60 * 60 

# 화면 해상도 (자동 감지)
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
SCALE_RATIO = 1.0

# ================= 2. 기본 함수들 =================

def run_adb(command):
    # 경로에 공백이 있으므로 따옴표로 감싸서 실행
    try:
        subprocess.call(f'"{ADB_CMD}" -s {DEVICE_ADDRESS} {command}', shell=True)
    except Exception as e:
        print(f"   ❌ ADB 명령 오류: {e}")

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
    
    # 1. 게임 강제 종료
    run_adb(f'shell am force-stop {GAME_PACKAGE}')
    time.sleep(2.0)
    
    # 2. 홈 화면 이동
    run_adb('shell input keyevent KEYCODE_HOME')
    time.sleep(1.0)
    
    # 3. 게임 실행
    loc = find_image("icon.png", threshold=0.8)
    if loc:
        click(loc[0], loc[1])
        # 🔥 [수정] 대기 시간 25초로 변경
        print("   🚀 게임 실행 중... (25초 로딩 대기)")
        time.sleep(25) 
    else:
        print("   ⚠️ 바탕화면에서 게임 아이콘을 못 찾았습니다.")
        return False

    # 4. 팝업 닫기
    print("   🧹 팝업/광고 닫기 시도...")
    for _ in range(5):
        close_loc = find_image("close.png", threshold=0.8)
        if close_loc:
            click(close_loc[0], close_loc[1])
            time.sleep(1.5)
        else:
            break
    return True

def step2_enter_building():
    print("[Step 2] 제조소 찾기 및 진입")
    
    # 1. 건물 찾기 (수확 가능 or 일반)
    target_img = "building_done.png"
    loc = find_image(target_img, threshold=0.7)
    
    if not loc:
        target_img = "building.png"
        loc = find_image(target_img, threshold=0.7)
        
    if loc:
        print(f"   🏭 건물 발견 ({target_img}) -> 클릭")
        
        # 🔥🔥🔥 [디버깅 추가] 클릭 위치 확인용 이미지 저장 🔥🔥🔥
        try:
            debug_img = cv2.imread("view.png") # find_image가 캡처해둔 이미지 로드
            if debug_img is not None:
                # loc[0], loc[1] 위치에 빨간색 동그라미 그리기
                cv2.circle(debug_img, (loc[0], loc[1]), 20, (0, 0, 255), 5)
                cv2.imwrite("debug_click_check.png", debug_img)
                print("   📸 [디버깅] 클릭 위치 저장됨: debug_click_check.png 확인 필수!")
        except Exception as e:
            print(f"   ⚠️ 디버그 이미지 저장 실패: {e}")
        # ---------------------------------------------------------

        click(loc[0], loc[1]) # 좌표 수정 없이 원본 좌표 클릭
        # 🔥 [수정] 건물 클릭 후 버튼 뜰 때까지 약간 대기
        time.sleep(2.0)
    else:
        print("   🔭 건물이 안 보여서 화면을 살짝 이동합니다.")
        swipe_screen()
        time.sleep(1.5)
        loc = find_image("building.png", threshold=0.7)
        if loc: 
            click(loc[0], loc[1])
            time.sleep(2.0)
    
    # 2. [진입] 버튼 찾기 (재시도 로직 추가)
    for i in range(3): # 3번 시도
        enter_btn = find_image("enter_factory.png", threshold=0.8)
        if enter_btn:
            print("   🔘 [진입] 버튼 발견 -> 클릭")
            click(enter_btn[0], enter_btn[1])
            time.sleep(3) # 화면 전환 대기
            return True
        else:
            print(f"   ⚠️ 진입 버튼 찾는 중... ({i+1}/3)")
            # 혹시 건물이 제대로 안 눌렸을 수 있으니 건물 위치(loc)가 있으면 다시 클릭
            if loc:
                print("   ♻️ 건물 다시 클릭 시도")
                click(loc[0], loc[1])
            time.sleep(1.5)
    
    print("   ❌ 결국 제조소 진입에 실패했습니다.")
    return False

def step3_go_production():
    print("[Step 3] 생산 탭 이동")
    for i in range(3):
        loc = find_image("tab.png", threshold=0.8)
        if loc:
            click(loc[0], loc[1])
            print("   ✅ [생산] 탭 클릭 완료")
            return True
        time.sleep(1)
    
    print("   ⚠️ 생산 탭을 못 찾았습니다.")
    return False

# ================= 4. 메인 실행 =================

def main():
    # 👇 [추가] 창 위치 기억 기능 활성화
    window_manager.restore_and_autosave("제조소 24시간 구동")

    print(f"=== 🏭 제조소 24시간 구동 (2시간 주기 / ADB 수정판) ===")
    
    # ADB 연결 시도
    try:
        subprocess.call(f'"{ADB_CMD}" connect {DEVICE_ADDRESS}', shell=True)
    except Exception as e:
        print(f"❌ ADB 연결 실패: {e}")
        return

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
            print(f"   ⏳ 남은 시간: {mins}분       ", end='\r')
            time.sleep(60) 
            remaining -= 60
        
        print("\n⏰ 대기 종료! 다시 시작합니다.\n")

if __name__ == "__main__":
    main()