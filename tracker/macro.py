import cv2
import numpy as np
import time
import os
import subprocess
import sys

# ================= 설정 =================
ADB_CMD = "adb" 
WAIT_TIME = 8 * 60  # 8분 대기
# ========================================

if len(sys.argv) > 1:
    TARGET_PORT = sys.argv[1]
else:
    TARGET_PORT = "5555"

DEVICE_ADDRESS = f"127.0.0.1:{TARGET_PORT}"

def run_adb(command):
    full_cmd = f'"{ADB_CMD}" -s {DEVICE_ADDRESS} {command}'
    subprocess.call(full_cmd, shell=True)

def capture_screen():
    try:
        filename = f"macro_{TARGET_PORT}.png"
        run_adb(f'shell screencap -p /sdcard/{filename}')
        run_adb(f'pull /sdcard/{filename} .')
        if os.path.exists(filename):
            # [수정됨] 화면은 투명도가 필요 없으니 무조건 3채널(IMREAD_COLOR)로 읽기
            return cv2.imread(filename, cv2.IMREAD_COLOR)
        return None
    except:
        return None

def find_image(target_file, threshold=0.8):
    if not os.path.exists(target_file):
        print(f"[{TARGET_PORT}] ❌ 파일 없음: {target_file}")
        return None

    screen = capture_screen()
    if screen is None: return None

    template = cv2.imread(target_file, cv2.IMREAD_UNCHANGED)
    h, w = template.shape[:2]
    
    if template.shape[2] == 4:
        template_img = template[:, :, :3]
        mask = template[:, :, 3]
        result = cv2.matchTemplate(screen, template_img, cv2.TM_CCORR_NORMED, mask=mask)
        if threshold < 0.9: threshold = 0.9 
    else:
        result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)

    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

    if max_val >= threshold:
        center_x = int(max_loc[0] + w / 2)
        center_y = int(max_loc[1] + h / 2)
        return center_x, center_y
    return None

def click(x, y):
    run_adb(f'shell input tap {x} {y}')
    print(f"[{TARGET_PORT}] 👆 클릭: ({x}, {y})")

def double_click(x, y):
    run_adb(f'shell input tap {x} {y}')
    time.sleep(0.1)
    run_adb(f'shell input tap {x} {y}')
    print(f"[{TARGET_PORT}] ✌️ 더블 클릭: ({x}, {y})")

def drag_screen(start_x, start_y, end_x, end_y):
    print(f"[{TARGET_PORT}] 🖐️ 화면 이동")
    run_adb(f'shell input swipe {start_x} {start_y} {end_x} {end_y} 500')
    time.sleep(1)

def press_home():
    run_adb('shell input keyevent KEYCODE_HOME')
    print(f"[{TARGET_PORT}] 🏠 홈으로 이동")

# [수정됨] 앱 완전 종료 함수 (옆으로 밀기)
def force_close_app():
    print(f"[{TARGET_PORT}] 💀 게임 완전 종료 시도 (옆으로 밀기)...")
    
    # 1. 일단 홈으로
    run_adb('shell input keyevent KEYCODE_HOME')
    time.sleep(1)
    
    # 2. '최근 실행 앱' 목록 열기
    run_adb('shell input keyevent 187')
    time.sleep(1.5)
    
    # 3. [수정] 화면 중앙에서 왼쪽으로 휙 밀기 (Swipe Left)
    # (좌표: 가로 800 -> 100 으로 이동)
    run_adb('shell input swipe 800 450 100 450 300')
    time.sleep(1)
    
    # 4. 깔끔하게 홈으로 복귀
    run_adb('shell input keyevent KEYCODE_HOME')
    print(f"[{TARGET_PORT}] ✨ 종료 완료")

def main():
    print(f"=== 🤖 2번 매크로 (완전 종료: 옆으로 밀기) ===")
    os.system(f"{ADB_CMD} connect {DEVICE_ADDRESS}")

    while True:
        print(f"\n[{TARGET_PORT}] 🔄 재시작 프로세스 시작")
        
        # 완전 종료 수행
        force_close_app()
        time.sleep(2)
        
        # 아이콘 실행
        loc = find_image("icon.png", threshold=0.8)
        if loc:
            click(loc[0], loc[1])
            print(f"[{TARGET_PORT}] 🚀 게임 실행 (30초 대기)")
            time.sleep(30)
            
            drag_screen(800, 450, 200, 100)
            time.sleep(2)
        else:
            print(f"[{TARGET_PORT}] ⚠️ 아이콘 못 찾음. 재시도...")
            time.sleep(5)
            continue

        print(f"[{TARGET_PORT}] 🛡️ 기지 진입 시도")
        retry_count = 0
        success = False
        move_count = 0 

        while retry_count < 60: 
            # 1. 생산 탭
            tab_loc = find_image("tab.png", threshold=0.8)
            if tab_loc:
                print(f"[{TARGET_PORT}] ✅ 제조소 내부! 생산 탭 클릭.")
                click(tab_loc[0], tab_loc[1])
                success = True
                break

            # 2. 팝업 닫기
            close_loc = find_image("close.png", threshold=0.8)
            if close_loc:
                print(f"[{TARGET_PORT}] ❌ 팝업 닫기")
                click(close_loc[0], close_loc[1])
                time.sleep(2)
                continue

            # 3. 건물 찾기 (투명 배경 포함)
            building_loc = find_image("building.png", threshold=0.7)
            if not building_loc:
                building_loc = find_image("building_done.png", threshold=0.7)

            if building_loc:
                print(f"[{TARGET_PORT}] 🏰 제조소 진입 시도")
                double_click(building_loc[0], building_loc[1])
                time.sleep(4)
                continue
            
            # 4. 화면 이동
            print(f"[{TARGET_PORT}] 🔍 찾는 중...")
            if move_count == 0: drag_screen(800, 450, 200, 100)
            elif move_count == 1: drag_screen(200, 450, 800, 100)
            elif move_count == 2: drag_screen(500, 100, 500, 800)
            else:
                print(f"[{TARGET_PORT}] ⚠️ 못 찾음. 재접속.")
                break 
            move_count += 1
            time.sleep(2)
            retry_count += 1

        if success:
            print(f"[{TARGET_PORT}] 🎉 완료! {int(WAIT_TIME/60)}분 대기.")
            time.sleep(WAIT_TIME)
        else:
            print(f"[{TARGET_PORT}] ⚠️ 실패. 재시작.")

if __name__ == "__main__":
    main()