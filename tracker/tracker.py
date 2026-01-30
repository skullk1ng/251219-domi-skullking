import cv2
import pytesseract
import numpy as np
import time
import os
import subprocess
import json
from datetime import datetime

# ================= 1. 설정 및 경로 =================
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
ADB_CMD = "adb" 

# 트래커 봇은 무조건 1번 창(5555) 고정
TARGET_DEVICE = "127.0.0.1:5555"

# 🔄 전체 사이클 주기 (초 단위) -> 8분 = 480초
CYCLE_INTERVAL = 480 

# ================= 2. OCR 좌표 설정 =================
SCORE_START_X = 1121   
START_Y = 275          
ROW_GAP = 50.8         
SCORE_WIDTH = 100      
HEIGHT = 30            
GUILD_START_X = 445    
GUILD_WIDTH = 250      

DATA_FILE_PATH = "../data.json"
HISTORY_FILE_PATH = "history.json"

# ================= 3. 기본 함수들 =================

def run_adb(command):
    """ 1번 창에게 명령 내리기 """
    full_cmd = f'"{ADB_CMD}" -s {TARGET_DEVICE} {command}'
    subprocess.call(full_cmd, shell=True)

def capture_screen(is_ocr=False):
    """
    is_ocr=True: OCR용 (일반 컬러)
    is_ocr=False: 이미지 서치용 (일반 컬러) -> 투명도는 템플릿에만 있으면 됨
    """
    try:
        filename = "monitor_tracker.png"
        run_adb(f'shell screencap -p /sdcard/{filename}')
        run_adb(f'pull /sdcard/{filename} .')
        
        if os.path.exists(filename):
            # [수정됨] 무조건 3채널(IMREAD_COLOR)로 읽어서 채널 불일치 방지
            return cv2.imread(filename, cv2.IMREAD_COLOR)
        return None
    except Exception as e:
        print(f"캡처 오류: {e}")
        return None

# ================= 4. 매크로 기능 (찾기, 클릭, 종료) =================

def find_image(target_file, threshold=0.8):
    if not os.path.exists(target_file):
        print(f"❌ 파일 없음: {target_file}")
        return None

    # 화면 캡처 (무조건 3채널)
    screen = capture_screen(is_ocr=False) 
    if screen is None: return None

    # 찾을 이미지(템플릿)는 투명도(알파)를 포함해서 로드
    template = cv2.imread(target_file, cv2.IMREAD_UNCHANGED)
    
    # 템플릿이 투명 배경(4채널)인지 확인
    if template.shape[2] == 4:
        template_img = template[:, :, :3] # 색상 부분 (3채널)
        mask = template[:, :, 3]          # 투명도 부분 (1채널 마스크)
        
        # 투명한 부분은 무시하고 매칭 (Screen 3채널 vs Template 3채널 + Mask)
        result = cv2.matchTemplate(screen, template_img, cv2.TM_CCORR_NORMED, mask=mask)
        if threshold < 0.9: threshold = 0.9 
    else:
        # 일반 이미지 매칭 (Screen 3채널 vs Template 3채널)
        result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)

    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

    if max_val >= threshold:
        h, w = template.shape[:2]
        center_x = int(max_loc[0] + w / 2)
        center_y = int(max_loc[1] + h / 2)
        return center_x, center_y
    return None

def click(x, y):
    run_adb(f'shell input tap {x} {y}')
    print(f"👆 클릭: ({x}, {y})")

def force_close_app():
    print("💀 게임 완전 종료 및 재부팅 시도...")
    run_adb('shell input keyevent KEYCODE_HOME')
    time.sleep(1)
    run_adb('shell input keyevent 187') # 최근 앱
    time.sleep(1.5)
    run_adb('shell input swipe 800 450 100 450 300') # 옆으로 밀어서 끄기
    time.sleep(1)
    run_adb('shell input keyevent KEYCODE_HOME')
    print("✨ 종료 완료")

# ================= 5. OCR 처리 기능 =================

def preprocess_image(roi, is_score=False):
    roi = cv2.resize(roi, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    threshold_value = 140 if is_score else 120
    _, thresh = cv2.threshold(gray, threshold_value, 255, cv2.THRESH_BINARY)
    thresh = cv2.bitwise_not(thresh)
    return thresh

def extract_score(image, rank):
    y = int(START_Y + (rank * ROW_GAP))
    x = SCORE_START_X
    w = SCORE_WIDTH
    h = HEIGHT
    if y+h > image.shape[0] or x+w > image.shape[1]: return None
    roi = image[y:y+h, x:x+w]
    processed = preprocess_image(roi, is_score=True)
    text = pytesseract.image_to_string(processed, config='--psm 7 outputbase digits')
    try:
        return int(''.join(filter(str.isdigit, text)))
    except:
        return None

def extract_guild_name(image, rank):
    y = int(START_Y + (rank * ROW_GAP))
    x = GUILD_START_X
    w = GUILD_WIDTH
    h = HEIGHT
    if y+h > image.shape[0] or x+w > image.shape[1]: return None
    roi = image[y:y+h, x:x+w]
    processed = preprocess_image(roi, is_score=False)
    try:
        text = pytesseract.image_to_string(processed, lang='kor+eng+rus+chi_tra+jpn', config='--psm 7')
        return text.strip()
    except:
        return ""

def load_history():
    if os.path.exists(HISTORY_FILE_PATH):
        try:
            with open(HISTORY_FILE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {}

def save_history(history_data):
    with open(HISTORY_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(history_data, f, ensure_ascii=False, indent=4)

def upload_to_github():
    print("☁️ GitHub 업로드...")
    try:
        parent_dir = ".." 
        subprocess.run(["git", "add", "data.json"], cwd=parent_dir, check=True)
        timestamp = datetime.now().strftime("%H:%M:%S")
        subprocess.run(["git", "commit", "-m", f"Auto update: {timestamp}"], cwd=parent_dir, check=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=parent_dir, check=True)
        print(f"✅ 업로드 성공!")
    except Exception as e:
        print(f"⚠️ 업로드 실패: {e}")

# ================= 6. 메인 로직 =================

def main():
    print(f"=== 🤖 스마트 트래커 (재접속+OCR+히스토리) ===")
    os.system(f"{ADB_CMD} connect {TARGET_DEVICE}")
    
    history_db = load_history()
    print(f"📂 히스토리 로드: {len(history_db)}개")

    while True:
        start_time = time.time() # 시작 시간
        
        # [단계 1] 게임 완전 재시작
        force_close_app()
        time.sleep(2)
        
        # 아이콘 찾아서 실행
        icon_loc = find_image("icon.png")
        if icon_loc:
            click(icon_loc[0], icon_loc[1])
            print("🚀 게임 실행 (로딩 40초 대기)")
            time.sleep(40)
        else:
            print("⚠️ 아이콘 못 찾음. 재시도...")
            time.sleep(5)
            continue 

        # [단계 2] 영예의 토너먼트 진입 (최대 1분간 시도)
        print("🛡️ 토너먼트 아이콘 찾는 중...")
        entered_tournament = False
        
        for _ in range(12): # 5초 * 12회 = 60초 시도
            # 1. 팝업 광고 있으면 닫기
            close_loc = find_image("close.png")
            if close_loc:
                print("❌ 광고 닫기")
                click(close_loc[0], close_loc[1])
                time.sleep(2)
                continue

            # 2. 토너먼트 아이콘 찾기
            tour_loc = find_image("tournament.png", threshold=0.7)
            if tour_loc:
                print("🏆 영예의 토너먼트 발견! 진입")
                click(tour_loc[0], tour_loc[1])
                entered_tournament = True
                break
            
            time.sleep(5)

        if not entered_tournament:
            print("⚠️ 토너먼트 진입 실패. 다음 사이클로 넘어갑니다.")
        else:
            # [단계 3] 순위 화면 로딩 대기 및 OCR 스캔
            print("📊 순위표 로딩 대기 (10초)...")
            time.sleep(10)
            
            # OCR용 스크린샷 캡처 (is_ocr=True)
            img = capture_screen(is_ocr=True) 
            
            if img is not None:
                current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"\n[Check: {current_time_str}]")
                current_display_data = {}

                for i in range(14):
                    rank = str(i + 1)
                    guild_name = extract_guild_name(img, i)
                    score = extract_score(img, i)
                    if score is None: score = 0 
                    if guild_name == "": guild_name = "인식실패"
                    
                    # [히스토리 로직 시작]
                    # 1. DB 초기화 및 구버전 데이터(딕셔너리) 마이그레이션
                    if guild_name not in history_db:
                        history_db[guild_name] = [] 
                    elif isinstance(history_db[guild_name], dict):
                        # 옛날 포맷이면 리스트로 감싸줌
                        history_db[guild_name] = [history_db[guild_name]]

                    guild_logs = history_db[guild_name]

                    # 2. 가장 최근 기록(last_score) 확인
                    last_score = 0
                    if len(guild_logs) > 0:
                        last_score = guild_logs[0]['score']

                    # 3. 점수 변동 체크
                    final_time = current_time_str
                    
                    if score != 0: # 읽기 성공 시에만
                        if score != last_score:
                            print(f"  >>> 🔔 변동: {guild_name} ({last_score} -> {score})")
                            # 새 기록 맨 앞에 추가
                            guild_logs.insert(0, {'score': score, 'time': current_time_str})
                            # 5개까지만 유지
                            if len(guild_logs) > 5:
                                guild_logs = guild_logs[:5]
                            history_db[guild_name] = guild_logs
                        else:
                            # 점수 같으면 시간은 예전 시간 유지
                            if len(guild_logs) > 0:
                                final_time = guild_logs[0]['time']

                    # 4. 웹 표시용 데이터 (history 필드 추가됨)
                    current_display_data[rank] = {
                        'name': guild_name, 
                        'score': score, 
                        'time': final_time,
                        'history': history_db[guild_name] 
                    }

                    print(f"{rank}위 | {guild_name} | {score}")

                save_history(history_db)
                with open(DATA_FILE_PATH, "w", encoding="utf-8") as f:
                    json.dump(current_display_data, f, ensure_ascii=False, indent=4)
                    print("💾 데이터 저장 및 업로드")
                
                upload_to_github()
            else:
                print("⚠️ OCR 캡처 실패")

        # [단계 4] 남은 시간 계산 및 대기
        elapsed_time = time.time() - start_time
        wait_time = CYCLE_INTERVAL - elapsed_time
        
        if wait_time < 0: wait_time = 0
        
        print(f"⏳ 다음 사이클까지 {int(wait_time)}초 대기...")
        time.sleep(wait_time)

if __name__ == "__main__":
    main()