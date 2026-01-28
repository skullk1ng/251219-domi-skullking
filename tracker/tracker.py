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

# JSON 파일 경로 (상위 폴더)
DATA_FILE_PATH = "../data.json"

# =================================================================

def capture_screen():
    try:
        subprocess.call(f'"{ADB_CMD}" shell screencap -p /sdcard/monitor.png', shell=True)
        subprocess.call(f'"{ADB_CMD}" pull /sdcard/monitor.png .', shell=True)
        return cv2.imread("monitor.png")
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
    cv2.imwrite(f"debug_score_{rank+1}.png", processed)
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
    cv2.imwrite(f"debug_guild_{rank+1}.png", processed)
    try:
        text = pytesseract.image_to_string(processed, lang='kor+eng+rus+chi_tra+jpn', config='--psm 7')
        return text.strip()
    except pytesseract.TesseractError:
        text = pytesseract.image_to_string(processed, lang='eng', config='--psm 7')
        return text.strip()

def load_previous_data():
    """기존 data.json이 있으면 불러와서 시간 정보를 기억함"""
    if os.path.exists(DATA_FILE_PATH):
        try:
            with open(DATA_FILE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {}

def main():
    print("=== 길드명 & 점수 모니터링 시작 ===")
    
    # [중요] 봇 시작 시 기존 데이터를 불러옵니다.
    prev_scores = load_previous_data()
    print(f"📂 기존 데이터 로드 완료: {len(prev_scores)}개 길드 정보")

    while True:
        try:
            img = capture_screen()
            if img is None:
                time.sleep(5)
                continue

            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n[Check: {current_time}]")

            for i in range(14):
                rank = str(i + 1) # JSON 키는 문자열로 저장됨
                
                guild_name = extract_guild_name(img, i)
                score = extract_score(img, i)
                
                if score is None: score = 0 
                if guild_name == "": guild_name = "인식실패"

                # === [핵심 로직] 시간 갱신 ===
                last_time = current_time # 기본값은 현재 시간
                
                if rank in prev_scores:
                    old_data = prev_scores[rank]
                    old_score = old_data.get('score', 0)
                    old_time = old_data.get('time', current_time)

                    # 점수가 같으면 -> 시간은 '옛날 시간' 그대로 유지
                    if score == old_score and score != 0:
                        last_time = old_time
                    # 점수가 다르면 -> '현재 시간'으로 갱신 (로그 출력)
                    elif score != old_score and score != 0:
                        msg = f"🔔 [변동] {rank}위 ({guild_name}) | {old_score} -> {score} | {current_time}"
                        print("  >>> " + msg)
                        with open("glory_log.txt", "a", encoding="utf-8") as f:
                            f.write(msg + "\n")
                
                # 데이터 업데이트 (시간 정보 'time' 추가됨)
                prev_scores[rank] = {'name': guild_name, 'score': score, 'time': last_time}
                
                print(f"{rank}위 | {guild_name} | {score} | ({last_time})")

            # 파일 저장
            with open(DATA_FILE_PATH, "w", encoding="utf-8") as f:
                json.dump(prev_scores, f, ensure_ascii=False, indent=4)
                print("💾 데이터 업데이트 완료")

            time.sleep(30) # 30초 대기

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"에러: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()