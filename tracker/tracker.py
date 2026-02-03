import cv2
import pytesseract
import numpy as np
import time
import os
import subprocess
import json
from datetime import datetime
import sys
import requests
import window_manager

# ✅ 한글 출력 깨짐 방지
sys.stdout.reconfigure(encoding='utf-8')

# ================= 1. 설정 및 경로 =================
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
ADB_CMD = r"C:\Program Files\BlueStacks_nxt\HD-Adb.exe"
GAME_PACKAGE = "com.nexon.dominations.asia.g"
TARGET_DEVICE = "127.0.0.1:5555"
CYCLE_INTERVAL = 200 
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1467971942135894127/ydmq_4ECyEQXdGRNe-TrTlQgnJrYDczkjfSMfkcm--bgxzzxUPrxbzX4Peze37VTfVA2"
USE_DISCORD = True 

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE_PATH = os.path.join(os.path.dirname(BASE_DIR), "data.json") 
HISTORY_FILE_PATH = os.path.join(BASE_DIR, "history.json")

# ================= 2. OCR 좌표 설정 =================
SCORE_START_X = 1121    
SCORE_WIDTH = 100       

# 월드워 횟수 (점수 왼쪽)
WW_START_X = 990 
WW_WIDTH = 60

# 길드 이름 (왼쪽)
GUILD_START_X = 445     
GUILD_WIDTH = 250       

START_Y = 275           
ROW_GAP = 50.8          
HEIGHT = 30             

# ================= 3. 기본 함수들 =================

def send_discord_msg(title, desc, color=5763719, fields=None, image_path=None):
    if not USE_DISCORD: return
    try:
        embed = {
            "title": title,
            "description": desc,
            "color": color,
            "fields": fields if fields else [],
            "footer": {"text": f"측정 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"},
            "image": {"url": "attachment://capture.png"} if image_path else {}
        }
        
        embed_data = {"embeds": [embed]}

        if image_path and os.path.exists(image_path):
            with open(image_path, "rb") as f:
                files = {
                    "file": ("capture.png", f, "image/png"),
                    "payload_json": (None, json.dumps(embed_data))
                }
                requests.post(DISCORD_WEBHOOK_URL, files=files)
        else:
            headers = {"Content-Type": "application/json"}
            requests.post(DISCORD_WEBHOOK_URL, data=json.dumps(embed_data), headers=headers)
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
            return imread_unicode(local_path, cv2.IMREAD_COLOR), local_path 
        return None, None
    except Exception as e:
        print(f"캡처 오류: {e}")
        return None, None

def find_image(target_filename, threshold=0.8):
    target_path = os.path.join(BASE_DIR, target_filename)
    if not os.path.exists(target_path): return None
    screen, _ = capture_screen(is_ocr=False) 
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
    print(f"💀 게임 강제 종료 (패키지: {GAME_PACKAGE})")
    run_adb(f'shell am force-stop {GAME_PACKAGE}')
    time.sleep(2)
    run_adb('shell input keyevent KEYCODE_HOME')
    print("✨ 종료 및 홈 이동 완료")

def preprocess_image(roi, is_number=False):
    roi = cv2.resize(roi, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    threshold_value = 140 if is_number else 120
    _, thresh = cv2.threshold(gray, threshold_value, 255, cv2.THRESH_BINARY)
    thresh = cv2.bitwise_not(thresh)
    return thresh

def extract_number(image, x, y, w, h):
    if y+h > image.shape[0] or x+w > image.shape[1]: return 0
    roi = image[y:y+h, x:x+w]
    processed = preprocess_image(roi, is_number=True)
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
    processed = preprocess_image(roi, is_number=False)
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
    window_manager.restore_and_autosave("영예점수 모니터링 실행")
    print(f"=== 🤖 스마트 트래커 (원래 이름 유지 기능 탑재) ===")
    
    try:
        subprocess.call(f'"{ADB_CMD}" connect {TARGET_DEVICE}', shell=True)
    except Exception as e:
        print(f"❌ ADB 연결 오류: {e}")
        return

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
            print("📊 순위표 스캔 및 분석 중 (10초)...")
            time.sleep(10)
            
            img, captured_path = capture_screen(is_ocr=True)
            
            if img is not None:
                current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"\n[Check: {current_time_str}]")
                
                # 1. 현재 화면의 14개 데이터를 모두 읽어옴
                scanned_items = []
                for i in range(14):
                    rank = int(i + 1)
                    raw_name = extract_guild_name(img, i)
                    if not raw_name: raw_name = "Unknown"
                    
                    y_pos = int(START_Y + (i * ROW_GAP))
                    score = extract_number(img, SCORE_START_X, y_pos, SCORE_WIDTH, HEIGHT)
                    ww = extract_number(img, WW_START_X, y_pos, WW_WIDTH, HEIGHT)

                    # 일단 임시 딕셔너리에 저장
                    scanned_items.append({
                        'rank': rank,
                        'display_name': raw_name, # 화면에 보이는 이름 (예: ESH OK)
                        'score': score,
                        'ww': ww,
                        'real_key': None # 우리가 찾아내야 할 진짜 이름
                    })

                # 2. 매칭 알고리즘 시작 (소거법)
                
                # [단계 1] 이름이 똑같은 애들 먼저 매칭 (변동 없는 길드)
                matched_db_keys = set()
                
                for item in scanned_items:
                    if item['display_name'] in history_db:
                        item['real_key'] = item['display_name']
                        matched_db_keys.add(item['display_name'])

                # [단계 2] 이름은 다르지만 점수+월드워가 같은 애들 매칭 (이름 바꾼 길드)
                for item in scanned_items:
                    if item['real_key'] is None: # 아직 짝을 못 찾은 경우
                        
                        found_original_name = None
                        
                        # DB를 뒤져서 "점수랑 월드워가 똑같은데, 아직 화면에 안 나온 애"를 찾음
                        for db_key, logs in history_db.items():
                            if not logs: continue
                            if db_key in matched_db_keys: continue # 이미 다른 놈이랑 매칭됨
                            
                            last_log = logs[0] # 가장 최근 기록(직전 기록)
                            last_score = last_log.get('score', 0)
                            last_ww = last_log.get('ww', -1)
                            
                            if last_ww == -1: continue # 정보 부족하면 패스

                            # 🔥 핵심: 점수와 월드워가 직전 기록과 완전 일치하면 동일 길드로 간주
                            if (item['score'] == last_score) and (item['ww'] == last_ww):
                                found_original_name = db_key
                                break
                        
                        if found_original_name:
                            item['real_key'] = found_original_name # 원래 이름 부여!
                            matched_db_keys.add(found_original_name)
                            print(f"  🕵️‍♂️ [신분 확인] {item['display_name']} -> {found_original_name} (변장 감지)")
                        else:
                            # 매칭 실패하면 그냥 화면에 보이는 이름이 진짜 이름임
                            item['real_key'] = item['display_name']

                # 3. 결과 처리 및 저장
                current_display_data = {}
                
                for item in scanned_items:
                    final_key = item['real_key'] # 이게 진짜 이름 (예: 百分百戰爭 1)
                    score = item['score']
                    ww = item['ww']
                    rank = item['rank']
                    display_name = item['display_name'] # (예: ESH OK)

                    # DB 초기화 (처음 본 길드일 경우)
                    if final_key not in history_db: history_db[final_key] = []
                    
                    guild_logs = history_db[final_key]
                    last_score = guild_logs[0]['score'] if guild_logs else 0
                    
                    # 변동 감지 로직
                    if score != 0:
                        if score != last_score:
                            print(f"  🔔 변동: {final_key} ({last_score} -> {score})")
                            
                            # 알림 내용 구성
                            desc_text = f"**{final_key}**"
                            # 만약 화면 이름과 진짜 이름이 다르면 각주 추가
                            if final_key != display_name:
                                desc_text += f"\n(현재 닉네임: {display_name})"

                            fields = [
                                {"name": "기존 점수", "value": f"{last_score}", "inline": True},
                                {"name": "현재 점수", "value": f"**{score}**", "inline": True},
                                {"name": "변동폭", "value": f"+{score - last_score}", "inline": True}
                            ]
                            send_discord_msg("📈 순위 변동 감지", desc_text, fields=fields, image_path=captured_path)
                            
                            # 로그 저장 (진짜 이름인 final_key 아래에 저장됨)
                            guild_logs.insert(0, {'score': score, 'ww': ww, 'time': current_time_str})
                            if len(guild_logs) > 5: guild_logs = guild_logs[:5]
                            history_db[final_key] = guild_logs
                        else:
                            # 점수는 그대로지만, 혹시 이름만 바꼈을 때 정보 갱신을 위해 ww 업데이트 (메모리만)
                            if guild_logs:
                                guild_logs[0]['ww'] = ww

                    # 데이터 파일 저장 (웹사이트 업로드용) -> 여기서도 final_key(원래이름) 사용
                    current_display_data[rank] = {
                        'name': final_key, 
                        'score': score, 
                        'ww': ww, 
                        'time': current_time_str, 
                        'history': history_db[final_key],
                        'current_alias': display_name # 참고용으로 현재 닉네임도 넣어둠
                    }
                    
                    log_text = f"#{rank} | {final_key} | {score}"
                    if final_key != display_name:
                        log_text += f" (Alias: {display_name})"
                    print(log_text)

                save_history(history_db)
                with open(DATA_FILE_PATH, "w", encoding="utf-8") as f:
                    json.dump(current_display_data, f, ensure_ascii=False, indent=4)
                    print("💾 데이터 저장 완료")
                upload_to_github()
            else:
                print("⚠️ OCR 캡처 실패")

        elapsed_time = time.time() - start_time
        wait_seconds = int(max(0, CYCLE_INTERVAL - elapsed_time))
        while wait_seconds > 0:
            print(f"⏳ 다음 사이클까지 {wait_seconds}초 대기...    ", end='\r')
            time.sleep(1)
            wait_seconds -= 1
        print(" " * 50, end='\r')

if __name__ == "__main__":
    main()