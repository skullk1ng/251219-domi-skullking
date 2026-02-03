import cv2
import numpy as np
import time
import os
import subprocess
import sys
import re
import window_manager

# ✅ 한글 출력 깨짐 방지
sys.stdout.reconfigure(encoding='utf-8')

# ================= 1. 기본 설정 =================
ADB_CMD = r"C:\Program Files\BlueStacks_nxt\HD-Adb.exe"
GAME_PACKAGE = "com.nexon.dominations.asia.g"
TARGET_PORT = "5565" 
DEVICE_ADDRESS = f"127.0.0.1:{TARGET_PORT}"
WAIT_TIME = 2 * 60 * 60 

# 🔥 [핵심 수정] 해상도 비율 자동 계산 삭제 -> 1.0으로 강제 고정
# (미사일 격납고가 눌리는 현상 해결)
REAL_RATIO_X = 1.0
REAL_RATIO_Y = 1.0

# ================= 2. 기본 함수들 =================

def run_adb(command):
    try:
        subprocess.call(f'"{ADB_CMD}" -s {DEVICE_ADDRESS} {command}', shell=True)
    except Exception as e:
        print(f"   ❌ ADB 명령 오류: {e}")

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
    # Swipe로 꾹 누르기 (좌표 변환 없이 입력값 그대로 사용)
    run_adb(f'shell input swipe {x} {y} {x} {y} 100')
    print(f"   👆 클릭: ({x}, {y})")

# ================= 3. 핵심 로직 =================

def step1_restart_game():
    print(f"\n[Step 1] 게임 강제 종료 및 재접속")
    run_adb(f'shell am force-stop {GAME_PACKAGE}')
    time.sleep(2.0)
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

    # 🔥 [수정] 광고 닫기 로직 최적화
    # 5번 반복하지 않고, 1~2번만 빠르게 체크하고 없으면 바로 넘어감
    print("   👀 팝업/광고 확인 중...")
    for _ in range(2):
        # 닫기 버튼은 오인식이 많으므로 정확도(threshold)를 0.85로 높게 설정
        close_loc = find_image("close.png", threshold=0.85)
        if close_loc:
            print("   🧹 팝업 발견 -> 닫기")
            click(close_loc[0], close_loc[1])
            time.sleep(1.5)
        else:
            print("   ✨ 팝업 없음 -> 즉시 진행")
            break # 팝업 없으면 반복문 탈출 -> 바로 Step 2로 이동
    return True

def step2_enter_building():
    print("[Step 2] 제조소 찾기 및 진입")
    
    # 혹시 모를 잔여 팝업 1회 체크 (없으면 통과)
    close_loc = find_image("close.png", threshold=0.85)
    if close_loc:
        print("   🧹 잔여 팝업 닫기")
        click(close_loc[0], close_loc[1])
        time.sleep(1.5)

    target_images = ["building_done.png", "building.png"]
    found_loc = None

    # 1. 1차 탐색
    for img_name in target_images:
        loc = find_image(img_name, threshold=0.9)
        if loc:
            print(f"   🏭 (1차) 건물 발견 ({img_name})")
            found_loc = loc
            break

    # 2. 2차 탐색 (스와이프)
    if not found_loc:
        print("   🔭 4방향 탐색 시작")
        swipe_moves = [
            ("➡️ 오른쪽 보기", 1400, 540, 500, 540), 
            ("⬇️ 아래 보기", 960, 800, 960, 300),   
            ("⬅️ 왼쪽 보기", 500, 540, 1400, 540),
            ("⬆️ 위 보기", 960, 300, 960, 800)
        ]
        for move_name, sx, sy, ex, ey in swipe_moves:
            print(f"   🏃 {move_name}")
            run_adb(f'shell input swipe {sx} {sy} {ex} {ey} 800')
            time.sleep(1.5)
            for img_name in target_images:
                loc = find_image(img_name, threshold=0.9)
                if loc:
                    print(f"   🏭 (2차) 발견!")
                    found_loc = loc
                    break
            if found_loc: break

    # ✅ 클릭 실행
    if found_loc:
        # 🔥 [좌표 보정]
        # 아크로폴리스 회피(+20) + 바닥 클릭(+70)
        target_x = found_loc[0] + 20
        target_y = found_loc[1] + 70

        # 디버깅 저장
        try:
            debug_img = cv2.imread("view.png")
            if debug_img is not None:
                cv2.circle(debug_img, (target_x, target_y), 15, (0, 0, 255), 4)
                cv2.imwrite("debug_click_check.png", debug_img)
                print(f"   📸 [디버깅] 클릭 예정: {target_x}, {target_y}")
        except: pass

        click(target_x, target_y)
        time.sleep(2.0)
    else:
        print("   ❌ 건물을 찾지 못했습니다.")
        return False

    # 진입 버튼 클릭
    for i in range(3):
        enter_btn = find_image("enter_factory.png", threshold=0.85)
        if enter_btn:
            print("   🔘 [진입] 버튼 클릭")
            click(enter_btn[0], enter_btn[1])
            time.sleep(3)
            return True
        else:
            print(f"   ⚠️ 버튼 대기 중... ({i+1}/3)")
            if found_loc:
                print("   ♻️ 건물 재클릭")
                # 재시도 시에도 보정 좌표 사용
                click(found_loc[0] + 20, found_loc[1] + 70)
            time.sleep(1.5)
    
    print("   ❌ 진입 실패")
    return False

def step3_go_production():
    print("[Step 3] 생산 탭 이동")
    for i in range(3):
        loc = find_image("tab.png", threshold=0.8)
        if loc:
            click(loc[0], loc[1])
            print("   ✅ [생산] 탭 클릭")
            return True
        time.sleep(1)
    print("   ⚠️ 생산 탭 못 찾음")
    return False

def main():
    window_manager.restore_and_autosave("제조소 24시간 구동")
    print(f"=== 🏭 제조소 24시간 구동 (해상도 1:1 강제 + 빠른 진행) ===")
    
    try:
        subprocess.call(f'"{ADB_CMD}" connect {DEVICE_ADDRESS}', shell=True)
    except: pass
    
    while True:
        if step1_restart_game():
            if step2_enter_building():
                step3_go_production()
        
        print(f"\n💤 2시간 대기 시작...")
        remaining = WAIT_TIME
        while remaining > 0:
            mins = remaining // 60
            print(f"   ⏳ {mins}분 남음...   ", end='\r')
            time.sleep(60)
            remaining -= 60
        print("\n⏰ 재시작\n")

if __name__ == "__main__":
    main()