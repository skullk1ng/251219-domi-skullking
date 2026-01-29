import cv2
import pytesseract
import numpy as np
import time
import os
import subprocess
import json
from datetime import datetime

# ================= 1. 경로 설정 =================
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
ADB_CMD = "adb" 

# ================= 2. 좌표 설정 =================
SCORE_START_X = 1121   
START_Y = 275          
ROW_GAP = 50.8         
SCORE_WIDTH = 100      
HEIGHT = 30            
GUILD_START_X = 445    
GUILD_WIDTH = 250      

# 웹사이트용 데이터 (상위 14개만 저장)
DATA_FILE_PATH = "../data.json"
# [NEW] 봇의 장기 기억 저장소 (모든 길드 기록 저장)
HISTORY_FILE_PATH = "history.json"

UPLOAD_INTERVAL = 60 

# =========================================================

def capture_screen():
    try:
        subprocess.call(f'"{ADB_CMD}" shell screencap -p /sdcard/monitor.png', shell=True)
        subprocess.call(f'"{ADB_CMD}" pull /sdcard/monitor.png .', shell=True)
        if os.path.exists("monitor.png"):
            return cv2.imread("monitor.png")
        return None
    except Exception as e:
        print(f"캡처 오류: {e}")
        return None

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

# [NEW] 히스토리 파일 관리 함수
def load_history():
    if os.path.exists(HISTORY_FILE_PATH):
        try:
            with open(HISTORY_FILE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {}

def save_history(history_data):
    with open(HISTORY_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(history_data, f, ensure_ascii=False, indent=4)

def upload_to_github():
    print("☁️ GitHub에 데이터 업로드 중...")
    try:
        parent_dir = ".." 
        subprocess.run(["git", "add", "data.json"], cwd=parent_dir, check=True)
        timestamp = datetime.now().strftime("%H:%M:%S")
        subprocess.run(["git", "commit", "-m", f"Auto update: {timestamp}"], cwd=parent_dir, check=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=parent_dir, check=True)
        print(f"✅ 업로드 성공!")
    except Exception as e:
        print(f"⚠️ 업로드 실패: {e}")

def main():
    print(f"=== 스마트 모니터링 봇 (장기 기억 장착) 가동 ===")
    
    # 봇 시작 시 '장기 기억(history.json)'을 불러옵니다.
    history_db = load_history()
    print(f"📂 히스토리 로드 완료: {len(history_db)}개 길드 기억 중")

    while True:
        try:
            img = capture_screen()
            if img is None:
                time.sleep(5)
                continue

            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n[Check: {current_time}]")

            current_display_data = {} # 웹사이트에 보여줄 이번 턴 데이터
            
            for i in range(14):
                rank = str(i + 1)
                guild_name = extract_guild_name(img, i)
                score = extract_score(img, i)
                
                if score is None: score = 0 
                if guild_name == "": guild_name = "인식실패"

                # 1. 일단 현재 시간으로 가정
                final_time = current_time 

                # 2. 장기 기억(history_db) 뒤져보기
                if guild_name in history_db:
                    record = history_db[guild_name]
                    last_known_score = record['score']
                    last_known_time = record['time']

                    # [핵심 로직] 점수가 기억 속의 점수와 똑같다면?
                    if score == last_known_score and score != 0:
                        # 순위가 바뀌어서 나갔다 왔든 뭐든 상관없이 옛날 시간 유지!
                        final_time = last_known_time
                    
                    # 점수가 다르면? -> 현재 시간으로 확정 (이미 final_time = current_time)
                    elif score != last_known_score and score != 0:
                         print(f"  >>> 🔔 변동: {guild_name} ({last_known_score} -> {score})")

                # 3. 데이터 확정 및 저장
                
                # (1) 웹사이트용 데이터 (현재 순위표)
                current_display_data[rank] = {'name': guild_name, 'score': score, 'time': final_time}
                
                # (2) 장기 기억 업데이트 (순위 상관없이 이름 기준으로 저장)
                # 인식 실패가 아닐 때만 기억
                if guild_name != "인식실패" and guild_name != "":
                    history_db[guild_name] = {'score': score, 'time': final_time}

                print(f"{rank}위 | {guild_name} | {score}")

            # 파일 저장
            
            # 1. 히스토리 저장 (tracker 폴더 안)
            save_history(history_db)
            
            # 2. 웹사이트용 데이터 저장 (상위 폴더)
            with open(DATA_FILE_PATH, "w", encoding="utf-8") as f:
                json.dump(current_display_data, f, ensure_ascii=False, indent=4)
                print("💾 로컬 저장 완료")

            # GitHub 업로드
            upload_to_github()

            print(f"⏳ {UPLOAD_INTERVAL}초 대기...")
            time.sleep(UPLOAD_INTERVAL)

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"에러: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()