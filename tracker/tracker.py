import cv2
import pytesseract
import numpy as np
import time
import os
import subprocess
import json
from datetime import datetime
import sys
import requests # 👈 디스코드 전송용 라이브러리

# ================= 1. 설정 및 경로 =================
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
ADB_CMD = "adb"

# 트래커 봇은 1번 창(5555) 고정
TARGET_DEVICE = "127.0.0.1:5555"

# 🔄 전체 사이클 주기 (5분 = 300초)
CYCLE_INTERVAL = 300 

# 🔔 [설정] 디스코드 웹후크 URL (적용 완료!)
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1467971942135894127/ydmq_4ECyEQXdGRNe-TrTlQgnJrYDczkjfSMfkcm--bgxzzxUPrxbzX4Peze37VTfVA2"
USE_DISCORD = True 

# 파일 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE_PATH = os.path.join(os.path.dirname(BASE_DIR), "data.json") 
HISTORY_FILE_PATH = os.path.join(BASE_DIR, "history.json")

# ================= 2. OCR 좌표 설정 =================
SCORE_START_X = 1121    
START_Y = 275           
ROW_GAP = 50.8          
SCORE_WIDTH = 100       
HEIGHT = 30             
GUILD_START_X = 445     
GUILD_WIDTH = 250       

# ================= 3. 기본 함수들 =================

def send_discord_msg(message):
    """ 🚀 디스코드 메시지 발송 함수 """
    if not USE_DISCORD: return
    try:
        data = {"content": message}
        headers = {"Content-Type": "application/json"}
        requests.post(DISCORD_WEBHOOK_URL, data=json.dumps(data), headers=headers)
        print("   📨 디스코드 알림 발송 완료")
    except Exception as e:
        print(f"   ⚠️ 디스코드 발송 실패: {e}")

def run_adb(command):
    full_cmd = f'"{ADB_CMD}" -s {TARGET_DEVICE} {command}'
    subprocess.call(full_cmd, shell=True)

def imread_unicode(path, flags=cv2.IMREAD_COLOR):
    try:
        n = np.fromfile(path, np.uint8)
        img = cv2.imdecode(n, flags)
        return img
    except Exception as e:
        print(f"⚠️ 이미지 읽기 실패: {e}")
        return None

def capture_screen(is_ocr=False):
    try:
        filename = "monitor_tracker.png"
        local_path = os.path.join(BASE_DIR, filename)
        run_adb(f'shell screencap -p /sdcard/{filename}')
        run_adb(f'pull /sdcard/{filename} "{local_path}"')
        if os.path.exists(local_path):
            return imread_unicode(local_path, cv2.IMREAD_COLOR)
        return None
    except Exception as e:
        print(f"캡처 오류: {e}")
        return None

# ================= 4. 매크로 기능 =================

def find_image(target_filename, threshold=0.8):
    target_path = os.path.join(BASE_DIR, target_filename)
    if not os.path.exists(target_path): return None

    screen = capture_screen(is_ocr=False) 
    if screen is None: return None

    template = imread_unicode(target_path, cv2.IMREAD_UNCHANGED)
    if template is None: return None
    
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
        return int(max_loc[0] + w / 2), int(max_loc[1] + h / 2)
    return None

def click(x, y):
    run_adb(f'shell input tap {x} {y}')
    print(f"👆 클릭: ({x}, {y})")

def force_close_app():
    print("💀 게임 재시작 프로세스...")
    run_adb('shell input keyevent KEYCODE_HOME')
    time.sleep(1)
    run_adb('shell input keyevent 187') 
    time.sleep(1.5)
    run_adb('shell input swipe 800 450 100 450 300') 
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
    if y+h > image.shape[0] or x+w > image.shape[1]: return 0
    roi = image[y:y+h, x:x+w]
    processed = preprocess_image(roi, is_score=True)
    text = pytesseract.image_to_string(processed, config='--psm 7 outputbase digits')
    try:
        clean = ''.join(filter(str.isdigit, text))
        return int(clean) if clean else 0
    except:
        return 0

def extract_guild_name(image, rank):
    y = int(START_Y + (rank * ROW_GAP))
    x = GUILD_START_X
    w = GUILD_WIDTH
    h = HEIGHT
    if y+h > image.shape[0] or x+w > image.shape[1]: return ""
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
    print("☁️ GitHub 업로드 시도...")
    try:
        repo_dir = os.path.dirname(BASE_DIR) 
        subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
        timestamp = datetime.now().strftime("%H:%M:%S")
        try:
            subprocess.run(["git", "commit", "-m", f"Auto update: {timestamp}"], cwd=repo_dir, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print(f"✅ 커밋 완료: {timestamp}")
        except subprocess.CalledProcessError:
            print("ℹ️ 변경된 내용이 없어 커밋을 건너뜁니다.")
            return
        subprocess.run(["git", "push", "origin", "main"], cwd=repo_dir, check=True)
        print("🚀 GitHub Push 완료!")
    except Exception as e:
        print(f"⚠️ 업로드 중 오류 발생: {e}")

# ================= 6. 메인 로직 =================

def main():
    print(f"=== 🤖 스마트 트래커 (디스코드 알림 + 300초 주기) ===")
    os.system(f"{ADB_CMD} connect {TARGET_DEVICE}")
    history_db = load_history()
    print(f"📂 히스토리 로드: {len(history_db)}개")

    while True:
        start_time = time.time()
        
        force_close_app()
        time.sleep(2)
        
        icon_loc = find_image("icon.png")
        if icon_loc:
            click(icon_loc[0], icon_loc[1])
            print("🚀 게임 실행 (로딩 25초 대기)")
            time.sleep(25)
        else:
            print("⚠️ 아이콘 못 찾음")
            time.sleep(5)
            continue 

        print("🛡️ 토너먼트 아이콘 찾는 중...")
        entered_tournament = False
        
        for _ in range(12): 
            close_loc = find_image("close.png")
            if close_loc:
                print("❌ 광고 닫기")
                click(close_loc[0], close_loc[1])
                time.sleep(2)
                continue

            tour_loc = find_image("tournament.png", threshold=0.7)
            if tour_loc:
                print("🏆 영예의 토너먼트 진입")
                click(tour_loc[0], tour_loc[1])
                entered_tournament = True
                break
            time.sleep(5)

        if not entered_tournament:
            print("⚠️ 토너먼트 진입 실패. 다시 시작합니다.")
        else:
            print("📊 순위표 로딩 대기 (10초)...")
            time.sleep(10)
            
            img = capture_screen(is_ocr=True)
            if img is not None:
                current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"\n[Check: {current_time_str}]")
                current_display_data = {}

                for i in range(14):
                    rank = str(i + 1)
                    guild_name = extract_guild_name(img, i)
                    score = extract_score(img, i)
                    
                    if not guild_name: guild_name = "Unknown"
                    if guild_name not in history_db: history_db[guild_name] = []
                    elif isinstance(history_db[guild_name], dict): history_db[guild_name] = [history_db[guild_name]]

                    guild_logs = history_db[guild_name]
                    last_score = guild_logs[0]['score'] if guild_logs else 0
                    final_time = current_time_str
                    
                    if score != 0:
                        if score != last_score:
                            print(f"  🔔 변동: {guild_name} ({last_score} -> {score})")
                            
                            # 🔥 [디스코드 알림 발송]
                            msg = f"{current_time_str}\n[{guild_name} 점수 변동 발생: {last_score} -> {score}]"
                            send_discord_msg(msg)
                            
                            guild_logs.insert(0, {'score': score, 'time': current_time_str})
                            if len(guild_logs) > 5: guild_logs = guild_logs[:5]
                            history_db[guild_name] = guild_logs
                        else:
                            if guild_logs: final_time = guild_logs[0]['time']

                    current_display_data[rank] = {'name': guild_name, 'score': score, 'time': final_time, 'history': history_db[guild_name]}
                    print(f"#{rank} | {guild_name} | {score}")

                save_history(history_db)
                with open(DATA_FILE_PATH, "w", encoding="utf-8") as f:
                    json.dump(current_display_data, f, ensure_ascii=False, indent=4)
                    print("💾 데이터 저장 완료")
                upload_to_github()
            else:
                print("⚠️ OCR 캡처 실패")

        # 300초 카운트다운
        elapsed_time = time.time() - start_time
        wait_seconds = int(max(0, CYCLE_INTERVAL - elapsed_time))
        
        while wait_seconds > 0:
            print(f"⏳ 다음 사이클까지 {wait_seconds}초 대기...    ", end='\r')
            time.sleep(1)
            wait_seconds -= 1
        print(" " * 50, end='\r')

if __name__ == "__main__":
    main()