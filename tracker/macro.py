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

# 해상도 비율 (자동 계산됨)
REAL_RATIO_X = 1.0
REAL_RATIO_Y = 1.0

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

def update_screen_ratio(image_shape):
    """
    캡처된 이미지 크기와 실제 ADB 입력 해상도를 비교하여 비율을 계산합니다.
    """
    global REAL_RATIO_X, REAL_RATIO_Y
    
    # 1. 이미지 해상도 (OpenCV는 H, W 순서)
    img_h, img_w = image_shape[:2]
    
    # 2. ADB 해상도 가져오기
    output = run_adb_output("shell wm size")
    match = re.search(r'(\d+)x(\d+)', output)
    
    if match:
        # wm size는 보통 "Physical size: WxH" 형식
        # 하지만 가로/세로 모드에 따라 값이 뒤집힐 수 있으므로 큰 값을 너비로 간주
        val1 = int(match.group(1))
        val2 = int(match.group(2))
        
        adb_w = max(val1, val2) # 가로 모드 강제 가정 (1920)
        adb_h = min(val1, val2) # (1080)
        
        # 3. 비율 계산
        REAL_RATIO_X = adb_w / img_w
        REAL_RATIO_Y = adb_h / img_h
        
        print(f"   📏 [해상도 보정] 이미지({img_w}x{img_h}) vs 기기({adb_w}x{adb_h})")
        print(f"   ✨ 보정 비율: X={REAL_RATIO_X:.4f}, Y={REAL_RATIO_Y:.4f}")
    else:
        print("   ⚠️ ADB 해상도 확인 실패, 비율 1.0 유지")

def capture_screen():
    try:
        filename = "view.png"
        run_adb(f'shell screencap -p /sdcard/{filename}')
        run_adb(f'pull /sdcard/{filename} .')
        if os.path.exists(filename):
            img = cv2.imread(filename)
            # 이미지를 처음 읽었을 때 해상도 비율 갱신
            if img is not None:
                update_screen_ratio(img.shape)
            return img
        return None
    except: return None

def find_image(target_file, threshold=0.8):
    if not os.path.exists(target_file):
        print(f"   ⚠️ 파일 없음: {target_file}")
        return None
    
    screen = capture_screen() # 여기서 비율 계산됨
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
        # 이미지 상의 좌표 (아직 클릭 좌표 아님)
        return int(max_loc[0] + w/2), int(max_loc[1] + h/2)
    return None

def click(x, y):
    # 🔥 [핵심 수정] 비율을 적용하여 실제 클릭 좌표 계산
    real_x = int(x * REAL_RATIO_X)
    real_y = int(y * REAL_RATIO_Y)
    
    # Swipe로 클릭 (정확도 향상)
    run_adb(f'shell input swipe {real_x} {real_y} {real_x} {real_y} 100')
    print(f"   👆 클릭: ({real_x}, {real_y}) [원본: {x}, {y}]")

def swipe_screen():
    # 스와이프는 비율 계산 안 해도 대충 밀면 됨
    run_adb('shell input swipe 1200 540 800 540 500')

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
    
    close_loc = find_image("close.png", threshold=0.8)
    if close_loc:
        print("   🧹 팝업 닫기")
        click(close_loc[0], close_loc[1])
        time.sleep(2.0)

    target_images = ["building_done.png", "building.png"]
    found_loc = None

    # 1차 탐색
    for img_name in target_images:
        loc = find_image(img_name, threshold=0.9)
        if loc:
            print(f"   🏭 (1차) 건물 발견 ({img_name})")
            found_loc = loc
            break

    # 2차 탐색 (4방향)
    if not found_loc:
        print("   🔭 4방향 탐색 시작")
        # 스와이프는 대략적인 좌표라 하드코딩 유지 (비율 영향 적음)
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
        # 🚨 [임의 보정 삭제] 사용자 요청대로 보정 없이 원본 좌표 사용
        target_x = found_loc[0]
        target_y = found_loc[1]

        # 디버깅 이미지 저장
        try:
            debug_img = cv2.imread("view.png")
            if debug_img is not None:
                cv2.circle(debug_img, (target_x, target_y), 15, (0, 0, 255), 4)
                cv2.imwrite("debug_click_check.png", debug_img)
                print("   📸 [디버깅] 클릭 위치 저장됨")
        except: pass

        # 여기 click() 함수 안에서 비율(Scale) 보정이 자동으로 일어납니다.
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
                click(found_loc[0], found_loc[1])
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
    print(f"=== 🏭 제조소 24시간 구동 (자동 스케일링 적용) ===")
    
    try:
        subprocess.call(f'"{ADB_CMD}" connect {DEVICE_ADDRESS}', shell=True)
    except: pass
    
    # 캡처 한 번 떠서 해상도 비율 초기화
    capture_screen()

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