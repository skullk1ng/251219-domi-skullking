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

# 포트 번호
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
    
    # 🚨 [추가 1] 팝업(불가사의 교체 등)이 떠 있다면 먼저 닫기
    close_loc = find_image("close.png", threshold=0.8)
    if close_loc:
        print("   🧹 건물 찾기 전 방해되는 팝업 닫기")
        click(close_loc[0], close_loc[1])
        time.sleep(2.0)

    # 우선순위 이미지 목록
    target_images = ["building_done.png", "building.png"]
    found_loc = None

    # 🔍 [1차 시도] 현재 화면에서 찾기 (정확도 0.9로 상향)
    for img_name in target_images:
        loc = find_image(img_name, threshold=0.9)
        if loc:
            print(f"   🏭 (1차) 건물 발견 ({img_name}) -> 클릭")
            found_loc = loc
            break

    # 🔍 [2차 시도] 못 찾았다면 4방향 스와이프하며 찾기
    if not found_loc:
        print("   🔭 현재 화면에 없음. 4방향 탐색을 시작합니다.")
        
        # 탐색 방향: 오른쪽, 아래, 왼쪽, 위 (화면 기준)
        # (스와이프 제스처는 반대 방향이어야 시야가 이동됨)
        # 좌표: start_x, start_y, end_x, end_y
        swipe_moves = [
            ("➡️ 오른쪽 보기", 1400, 540, 500, 540), 
            ("⬇️ 아래 보기", 960, 800, 960, 300),   
            ("⬅️ 왼쪽 보기", 500, 540, 1400, 540),
            ("⬆️ 위 보기", 960, 300, 960, 800)
        ]

        for move_name, sx, sy, ex, ey in swipe_moves:
            print(f"   🏃 {move_name}...")
            run_adb(f'shell input swipe {sx} {sy} {ex} {ey} 800')
            time.sleep(1.5) # 화면 멈출 때까지 대기

            # 이동 후 다시 찾기
            for img_name in target_images:
                loc = find_image(img_name, threshold=0.9) # 여기서도 높은 정확도 유지
                if loc:
                    print(f"   🏭 (2차) {move_name} 후 발견! -> 클릭")
                    found_loc = loc
                    break
            
            if found_loc: break # 찾았으면 루프 탈출

    # ✅ 건물을 찾았을 때 클릭 로직
    if found_loc:
        # 🔥 [좌표 보정] 건물 중앙(지붕)보다 30px 아래(바닥) 클릭
        target_x = found_loc[0]
        target_y = found_loc[1] + 30 

        # [디버깅] 클릭 위치 저장
        try:
            debug_img = cv2.imread("view.png")
            if debug_img is not None:
                cv2.circle(debug_img, (target_x, target_y), 20, (0, 0, 255), 5)
                cv2.imwrite("debug_click_check.png", debug_img)
        except: pass

        click(target_x, target_y)
        time.sleep(2.0)
    else:
        print("   ❌ 결국 건물을 찾지 못했습니다. (메인 화면으로 복귀 시도)")
        return False

    # 3. [진입] 버튼 찾기
    for i in range(3): # 3번 시도
        enter_btn = find_image("enter_factory.png", threshold=0.85) # 버튼 정확도도 소폭 상향
        if enter_btn:
            print("   🔘 [진입] 버튼 발견 -> 클릭")
            click(enter_btn[0], enter_btn[1])
            time.sleep(3) # 화면 전환 대기
            return True
        else:
            print(f"   ⚠️ 진입 버튼 찾는 중... ({i+1}/3)")
            # 건물을 찾았는데(found_loc) 버튼이 안 떴다면 건물 다시 클릭
            if found_loc:
                print("   ♻️ 건물 다시 클릭 시도")
                # 여기서도 좌표 보정 적용
                click(found_loc[0], found_loc[1] + 30)
            time.sleep(1.5)
    
    print("   ❌ 건물은 찾았으나 [진입] 버튼이 안 뜹니다.")
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
    # 👇 창 위치 기억 기능 활성화
    window_manager.restore_and_autosave("제조소 24시간 구동")

    print(f"=== 🏭 제조소 24시간 구동 (2시간 주기 / 스마트 탐색 적용) ===")
    
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
            # 2. 건물 들어가기 (스마트 탐색)
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