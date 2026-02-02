import cv2
import pytesseract
import numpy as np
import time
import os
import subprocess
import sys
import re
import requests
from collections import Counter # 다수결 원칙을 위해 추가

# ✅ 한글 출력 깨짐 방지
sys.stdout.reconfigure(encoding='utf-8')

# ================= 1. 기본 설정 =================
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

ADB_CMD = "adb"
TARGET_PORT = "5565" 
DEVICE_ADDRESS = f"127.0.0.1:{TARGET_PORT}"

# 🔔 [설정] 디스코드 웹후크 (알림용)
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1467971942135894127/ydmq_4ECyEQXdGRNe-TrTlQgnJrYDczkjfSMfkcm--bgxzzxUPrxbzX4Peze37VTfVA2"
USE_DISCORD = True

# 🕒 반복 주기 (90분)
WAIT_TIME = 90 * 60 

# ================= 2. 재료 및 목표 설정 =================
MATERIAL_INFO = {
    "백금": {"time_min": 240, "amount": 10},
    "티타늄": {"time_min": 30, "amount": 10},
    "철": {"time_min": 40, "amount": 10},
    "탄소": {"time_min": 15, "amount": 10},
    "열 황동": {"time_min": 75, "amount": 10},
    "플라스틱": {"time_min": 25, "amount": 10},
    "폴리카보네이트": {"time_min": 20, "amount": 10},
    "유리": {"time_min": 45, "amount": 10},
    "실리코나이트": {"time_min": 50, "amount": 10},
    "섬유망": {"time_min": 80, "amount": 10},
    "바이오포일": {"time_min": 70, "amount": 10},
}

# ✅ 목표 리스트 (예시 데이터 유지)
PRODUCTION_QUEUE = [
    {"name": "철",           "icon": "res_iron.png",     "target": 10000},
    {"name": "티타늄",       "icon": "res_titanium.png", "target": 10000},
    {"name": "탄소",         "icon": "res_carbon.png",   "target": 20000},
    {"name": "백금",         "icon": "res_platinum.png", "target": 10000},
]

CURRENT_INDEX = 0 

# 👇 좌표 변수
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
SWIPE_OPTS = {
    "start_x": 900,
    "end_x": 100,
    "material_y": 640, 
    "slot_y": 350,     
    "duration": 500
}

# ================= 3. 기본 함수들 =================

def send_discord_msg(message):
    if not USE_DISCORD: return
    try:
        data = {"content": message}
        headers = {"Content-Type": "application/json"}
        requests.post(DISCORD_WEBHOOK_URL, data=json.dumps(data), headers=headers)
        print("   📨 디스코드 알림 발송 완료")
    except: pass

def run_adb(command):
    subprocess.call(f'"{ADB_CMD}" -s {DEVICE_ADDRESS} {command}', shell=True)

def run_adb_output(command):
    try:
        result = subprocess.check_output(f'"{ADB_CMD}" -s {DEVICE_ADDRESS} {command}', shell=True)
        return result.decode('utf-8').strip()
    except:
        return ""

def get_screen_resolution():
    global SCREEN_WIDTH, SCREEN_HEIGHT, SWIPE_OPTS
    print("📏 화면 해상도 확인 중...")
    output = run_adb_output("shell wm size") 
    match = re.search(r'(\d+)x(\d+)', output)
    if match:
        SCREEN_WIDTH = int(match.group(1))
        SCREEN_HEIGHT = int(match.group(2))
        if SCREEN_HEIGHT > SCREEN_WIDTH: SCREEN_WIDTH, SCREEN_HEIGHT = SCREEN_HEIGHT, SCREEN_WIDTH
        print(f"   📺 감지된 해상도: {SCREEN_WIDTH} x {SCREEN_HEIGHT}")
        SWIPE_OPTS["start_x"] = int(SCREEN_WIDTH * 0.8)
        SWIPE_OPTS["end_x"] = int(SCREEN_WIDTH * 0.2)
        SWIPE_OPTS["material_y"] = int(SCREEN_HEIGHT * 0.88)
        SWIPE_OPTS["slot_y"] = int(SCREEN_HEIGHT * 0.48)     
        print(f"   📍 좌표 설정 완료: 목록Y={SWIPE_OPTS['material_y']}, 슬롯Y={SWIPE_OPTS['slot_y']}")
    else:
        print("   ⚠️ 해상도 감지 실패. 기본값(720p) 사용")

def capture_screen(is_color=True):
    try:
        filename = f"macro_view_{TARGET_PORT}.png"
        run_adb(f'shell screencap -p /sdcard/{filename}')
        run_adb(f'pull /sdcard/{filename} .')
        if os.path.exists(filename):
            mode = cv2.IMREAD_COLOR if is_color else cv2.IMREAD_GRAYSCALE
            return cv2.imread(filename, mode)
        return None
    except: return None

def find_image(target_file, threshold=0.8, screen=None):
    if not os.path.exists(target_file): return None
    if screen is None: screen = capture_screen(is_color=True)
    if screen is None: return None
    template = cv2.imread(target_file, cv2.IMREAD_UNCHANGED)
    if template.shape[2] == 4:
        template_img = template[:, :, :3]
        mask = template[:, :, 3]
        result = cv2.matchTemplate(screen, template_img, cv2.TM_CCORR_NORMED, mask=mask)
        if threshold < 0.9: threshold = 0.9
    else:
        result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    if max_val >= threshold:
        h, w = template.shape[:2]
        return int(max_loc[0] + w/2), int(max_loc[1] + h/2)
    return None

def click(x, y):
    run_adb(f'shell input tap {x} {y}')

def swipe(start_x, start_y, end_x, end_y):
    run_adb(f'shell input swipe {start_x} {start_y} {end_x} {end_y} 1000')
    time.sleep(1.5)

def find_image_with_scroll(target_file):
    y_pos = SWIPE_OPTS["material_y"]
    start_x = SWIPE_OPTS["start_x"]
    end_x = SWIPE_OPTS["end_x"]
    
    loc = find_image(target_file)
    if loc: return loc
    print(f"🔎 목록에서 {target_file} 찾는 중...")
    
    for i in range(6):
        print(f"   👉 [스크롤 {i+1}/6] 오른쪽 목록 확인 중...")
        swipe(start_x, y_pos, end_x, y_pos)
        time.sleep(1.5)
        loc = find_image(target_file)
        if loc: 
            print(f"   ✨ 발견했습니다!")
            return loc
            
    print("   👈 아이콘이 없어 처음으로 돌아갑니다.")
    for _ in range(7):
        swipe(end_x, y_pos, start_x, y_pos)
        loc = find_image(target_file)
        if loc: return loc
    return None

def check_active_border(center_x, center_y):
    screen_color = capture_screen(is_color=True)
    if screen_color is None: return False
    w, h = 220, 238
    x = int(center_x - w/2)
    y = int(center_y - 110)
    h_img, w_img = screen_color.shape[:2]
    if x < 0: x = 0
    if y < 0: y = 0
    if x + w > w_img: x = w_img - w
    if y + h > h_img: y = h_img - h
    roi = screen_color[y:y+h, x:x+w].copy() 
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    lower_orange_red = np.array([0, 100, 140])
    upper_orange_red = np.array([35, 255, 255])
    lower_deep_red = np.array([160, 100, 140])
    upper_deep_red = np.array([180, 255, 255])
    mask1 = cv2.inRange(hsv, lower_orange_red, upper_orange_red)
    mask2 = cv2.inRange(hsv, lower_deep_red, upper_deep_red)
    mask = mask1 + mask2
    mh, mw = mask.shape
    cy, cx = mh // 2, mw // 2
    gap = 85
    mask[cy-gap-5:cy+gap-5, cx-gap:cx+gap] = 0
    red_pixel_count = cv2.countNonZero(mask)
    if red_pixel_count > 3000: return True
    return False

# 🔥 [수정] 3번 읽어서 다수결로 결정하는 OCR 함수
def read_dynamic_count_robust(center_x, center_y):
    readings = []
    print("   👀 [정밀 검사] 수량 확인 중 (3회 측정)...")
    
    for i in range(3):
        val = _read_single_count(center_x, center_y)
        readings.append(val)
        time.sleep(0.5) # 0.5초 간격
        
    # 빈도수가 가장 높은 숫자 선택 (다수결)
    most_common = Counter(readings).most_common(1)
    final_val = most_common[0][0]
    
    print(f"      👉 측정값들: {readings} -> 최종판단: {final_val}")
    return final_val

# 내부용 단일 측정 함수 (기존 로직)
def _read_single_count(center_x, center_y):
    screen_color = capture_screen(is_color=True)
    if screen_color is None: return 0
    screen_gray = cv2.cvtColor(screen_color, cv2.COLOR_BGR2GRAY)
    x = int(center_x - 45); y = int(center_y + 50)
    w = 135; h = 42
    h_img, w_img = screen_gray.shape[:2]
    if x < 0: x = 0
    if y < 0: y = 0
    if x + w > w_img: x = w_img - w
    if y + h > h_img: y = h_img - h
    roi = screen_gray[y:y+h, x:x+w]
    roi = cv2.resize(roi, None, fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
    _, roi_thresh = cv2.threshold(roi, 160, 255, cv2.THRESH_BINARY) 
    text = pytesseract.image_to_string(roi_thresh, config='--psm 7 outputbase digits')
    numbers = re.findall(r'\d+', text)
    if numbers: return int(numbers[0])
    return 0

def calculate_eta(name, current, target):
    if name not in MATERIAL_INFO: return "정보없음"
    needed = target - current
    if needed <= 0: return "완료"
    items_per_min = (MATERIAL_INFO[name]["amount"] / MATERIAL_INFO[name]["time_min"]) * 8
    minutes_left = needed / items_per_min
    return f"{int(minutes_left//60)}시간 {int(minutes_left%60)}분"

# ================= 4. 시나리오 단계별 함수 =================

def step1_restart_game():
    print("\n[Step 1] 게임 강제 종료 및 재실행")
    run_adb('shell input keyevent KEYCODE_HOME')
    time.sleep(1)
    run_adb('shell input keyevent 187') 
    time.sleep(1)
    run_adb('shell input swipe 800 360 100 360 300') 
    time.sleep(1)
    run_adb('shell input keyevent KEYCODE_HOME')
    loc = find_image("icon.png")
    if loc:
        click(loc[0], loc[1])
        print("🚀 게임 실행... (25초 로딩 대기)")
        time.sleep(25)
    else:
        print("⚠️ 게임 아이콘을 못 찾았습니다.")

def step2_close_popups():
    print("[Step 2] 공지 및 광고 배너 닫기")
    for i in range(4):
        loc = find_image("close.png", threshold=0.8)
        if loc:
            click(loc[0], loc[1])
            time.sleep(2)
        else:
            break

def check_and_enter_building():
    target_btn = "enter_factory.png" 
    def try_click_sequence(x, y):
        print("   👉 [1/2] 건물 정중앙 클릭")
        click(x, y) 
        time.sleep(2.0)
        loc_btn = find_image(target_btn, threshold=0.7)
        if loc_btn:
            print(f"   🔘 [진입] 버튼 발견! ({target_btn})")
            click(loc_btn[0], loc_btn[1])
            time.sleep(2)
            return True
        print("   👉 [2/2] 재클릭")
        click(x, y)
        time.sleep(2.0)
        loc_btn_retry = find_image(target_btn, threshold=0.7)
        if loc_btn_retry:
            print(f"   🔘 [진입] 버튼 발견! ({target_btn})")
            click(loc_btn_retry[0], loc_btn_retry[1])
            time.sleep(2)
            return True
        print("   ⚠️ [제조] 버튼을 못 찾았습니다.")
        return False
    loc_done = find_image("building_done.png", threshold=0.7)
    if loc_done:
        print("   🏭 [수확 대기] 발견")
        return try_click_sequence(loc_done[0], loc_done[1])
    loc_normal = find_image("building.png", threshold=0.7)
    if loc_normal:
        print("   🏭 [일반] 발견")
        return try_click_sequence(loc_normal[0], loc_normal[1])
    return False

def step3_4_enter_factory():
    print("[Step 3~4] 제조소 찾기 (사선 진입 후 360도 탐색)")
    if check_and_enter_building(): return True
    search_path = ["diag_down_right", "move_left", "move_left", "move_up", "move_up", "move_right", "move_right", "move_right", "move_down", "move_down"]
    for action in search_path:
        print(f"   🔭 화면 이동: {action}")
        if action == "diag_down_right": swipe(700, 500, 300, 200) 
        elif action == "move_left": swipe(300, 400, 700, 400)
        elif action == "move_up": swipe(500, 200, 500, 600)
        elif action == "move_right": swipe(700, 400, 300, 400)
        elif action == "move_down": swipe(500, 600, 500, 200)
        time.sleep(2) 
        if check_and_enter_building(): return True
    print("⚠️ 모든 구역을 돌았으나 제조소를 못 찾았습니다.")
    return False

def step5_open_production_tab():
    print("[Step 5] 생산 탭 확인")
    loc = find_image("tab.png")
    if loc:
        click(loc[0], loc[1]); time.sleep(2)
    return True

def step8_clear_slots():
    print("[Step 8] 슬롯 비우기 (전체 취소)")
    def clear_routine():
        retry = 0
        while retry < 10:
            loc_cancel = find_image("cancel.png", threshold=0.85)
            if loc_cancel:
                click(loc_cancel[0], loc_cancel[1])
                time.sleep(0.8) 
                loc_confirm = find_image("confirm.png", threshold=0.8)
                if loc_confirm:
                    click(loc_confirm[0], loc_confirm[1])
                    print("      🗑️ 취소 확인 클릭")
                    time.sleep(1.0)
            else:
                break
            retry += 1
    y = SWIPE_OPTS["slot_y"]
    sx = SWIPE_OPTS["start_x"]
    ex = SWIPE_OPTS["end_x"]
    clear_routine()
    swipe(sx, y, ex, y) 
    time.sleep(1)
    clear_routine()
    swipe(ex, y, sx, y) 
    time.sleep(1)

def step9_fill_slots(icon_loc):
    print("[Step 9] 슬롯 채우기 (12연타)")
    if icon_loc:
        for i in range(12): 
            click(icon_loc[0], icon_loc[1])
            time.sleep(0.3) 
        print("   ✅ 완료")

# ================= 5. 메인 루프 =================

def main():
    global CURRENT_INDEX
    print(f"=== 🏭 도미네이션즈 봇 (OCR정밀 + 즉시전환) ===")
    os.system(f"{ADB_CMD} connect {DEVICE_ADDRESS}")
    get_screen_resolution()
    
    # 🔥 [핵심 수정] 게임이 켜져 있는 상태를 기억하는 변수
    is_game_ready = False 

    while True:
        if CURRENT_INDEX >= len(PRODUCTION_QUEUE):
            print("🎉 모든 목표 달성! (대기 중...)")
            send_discord_msg("🎉 [전체 완료] 모든 생산 목표를 달성했습니다!")
            time.sleep(60); continue
            
        target_info = PRODUCTION_QUEUE[CURRENT_INDEX]
        target_name = target_info['name']
        target_amount = target_info['target']
        
        print(f"\n🎯 목표: {target_name} ({target_amount}개)")

        # 🔥 게임이 준비되지 않았을 때만 재시작 수행
        if not is_game_ready:
            step1_restart_game()
            step2_close_popups()
            
            if not step3_4_enter_factory():
                print("⚠️ 제조소 진입 실패. 재시도...")
                is_game_ready = False # 실패했으니 다시 시도하도록 설정
                continue
                
            if not step5_open_production_tab():
                print("⚠️ 생산 탭 열기 실패.")
                is_game_ready = False
                continue
                
            # 여기까지 무사히 오면 게임 준비 완료
            is_game_ready = True

        # --- 여기서부터는 게임이 켜져 있는 상태에서 반복 ---
        
        icon_loc = find_image_with_scroll(target_info['icon'])
        if icon_loc:
            print(f"   🧐 '{target_name}' 선택 여부 확인 중...")
            is_active = check_active_border(icon_loc[0], icon_loc[1])
            
            if is_active:
                print("   ✅ [활성 확인] 현재 이 재료가 선택되어 있습니다.")
            else:
                print("   ❌ [비활성] 이 재료가 선택되지 않았습니다.")
            
            # 🔥 [수정] 정밀 OCR 함수 사용
            current_cnt = read_dynamic_count_robust(icon_loc[0], icon_loc[1])
            eta = calculate_eta(target_name, current_cnt, target_amount)
            print(f"[Step 6] 현황: {current_cnt}개 / 남은 시간: {eta}")

            if current_cnt >= target_amount and current_cnt > 0:
                print(f"🎊 목표 달성! 다음 단계로 즉시 이동")
                send_discord_msg(f"🎊 [목표 달성] {target_name} 완료! 다음 재료로 넘어갑니다.")
                
                step8_clear_slots() # 생산 취소
                CURRENT_INDEX += 1  # 다음 목표 설정
                
                # 🔥 [핵심] continue를 하면 위로 올라가는데, 
                # is_game_ready가 True이므로 재시작 없이 바로 다음 아이콘을 찾으러 갑니다!
                continue 

            if not is_active:
                print(f"[Step 8] 다른 재료 생산 중 -> 전체 취소 후 변경")
                step8_clear_slots()
                print(f"[Step 9] 새 목표({target_name}) 생산 시작")
                step9_fill_slots(icon_loc)
            else:
                print(f"[Step 7] 생산 유지 (수집/보충)")
                click(300, 350); click(600, 350)
                step9_fill_slots(icon_loc)
        else:
            print(f"⚠️ {target_name} 아이콘을 목록에서 못 찾았습니다.")
            # 아이콘을 못 찾으면 혹시 오류일 수 있으니 재시작하도록 유도
            is_game_ready = False 
            continue

        # 대기 시간 (생산 중일 때만 대기)
        remaining_time = WAIT_TIME
        while remaining_time > 0:
            mins = remaining_time // 60
            print(f"⏳ {mins}분 대기 ({remaining_time}초)...    ", end='\r')
            time.sleep(1)
            remaining_time -= 1
        print("") 
        
        # 90분 대기 후에는 혹시 모를 렉 방지를 위해 재부팅을 하는 것이 안전합니다.
        # 즉시 전환을 원하면 아래 줄을 주석 처리하세요.
        is_game_ready = False 

if __name__ == "__main__":
    main()