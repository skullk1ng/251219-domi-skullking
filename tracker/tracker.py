import cv2
import pytesseract
import numpy as np
import time
import os
import subprocess
import json
from datetime import datetime, timedelta
import sys
import requests
import pyautogui  # 물리적 단축키 전송용
import window_manager

# ✅ 한글 출력 깨짐 방지
sys.stdout.reconfigure(encoding='utf-8')

# ================= 1. 설정 및 경로 =================
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
ADB_CMD = r"C:\Program Files\BlueStacks_nxt\HD-Adb.exe"
GAME_PACKAGE = "com.nexon.dominations.asia.g"
TARGET_DEVICE = "127.0.0.1:5555"
CYCLE_INTERVAL = 150 # 2분 30초
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1467971942135894127/ydmq_4ECyEQXdGRNe-TrTlQgnJrYDczkjfSMfkcm--bgxzzxUPrxbzX4Peze37VTfVA2"
USE_DISCORD = True 

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE_PATH = os.path.join(os.path.dirname(BASE_DIR), "data.json") 
HISTORY_FILE_PATH = os.path.join(BASE_DIR, "history.json")
ALIAS_FILE_PATH = os.path.join(BASE_DIR, "aliases.json")

# ================= 2. OCR 좌표 설정 =================
SCORE_START_X = 1121    
SCORE_WIDTH = 100       
WW_START_X = 990 
WW_WIDTH = 60
GUILD_START_X = 445     
GUILD_WIDTH = 250       
START_Y = 275           
ROW_GAP = 50.8          
HEIGHT = 30             

# ================= 3. 기본 함수들 =================

def cleanup_bluestacks_memory():
    """PyAutoGUI를 이용해 Windows 단축키(Ctrl+Shift+F)로 메모리 정리 수행"""
    print("🧹 블루스택 메모리 최적화 수행 (10회 주기)...")
    try:
        # 실제 키보드 신호 전송
        pyautogui.hotkey('ctrl', 'shift', 'f')
        time.sleep(4.0) # 정리 대기 시간
    except Exception as e:
        print(f"⚠️ 단축키 전송 오류: {e}")

def send_discord_msg(title, desc, color=5763719, fields=None, image_path=None):
    if not USE_DISCORD: return
    try:
        embed = {
            "title": title, "description": desc, "color": color,
            "fields": fields if fields else [],
            "footer": {"text": f"측정 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"},
            "image": {"url": "attachment://capture.png"} if image_path else {}
        }
        embed_data = {"embeds": [embed]}
        if image_path and os.path.exists(image_path):
            with open(image_path, "rb") as f:
                files = {"file": ("capture.png", f, "image/png"), "payload_json": (None, json.dumps(embed_data))}
                requests.post(DISCORD_WEBHOOK_URL, files=files)
        else:
            requests.post(DISCORD_WEBHOOK_URL, json=embed_data)
        print("   📨 디스코드 알림 발송 완료")
    except Exception as e: print(f"   ⚠️ 디스코드 발송 실패: {e}")

def run_adb(command):
    full_cmd = f'"{ADB_CMD}" -s {TARGET_DEVICE} {command}'
    subprocess.call(full_cmd, shell=True)

def force_close_app(should_cleanup):
    print(f"💀 게임 강제 종료 (패키지: {GAME_PACKAGE})")
    run_adb(f'shell am force-stop {GAME_PACKAGE}')
    
    # 🔥 10회 주기에 해당하면 메모리 정리 실행
    if should_cleanup:
        cleanup_bluestacks_memory()
        
    time.sleep(2)
    run_adb('shell input keyevent KEYCODE_HOME')
    print("✨ 종료 및 홈 이동 완료")

def imread_unicode(path, flags=cv2.IMREAD_COLOR):
    try:
        n = np.fromfile(path, np.uint8)
        return cv2.imdecode(n, flags)
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
        res = cv2.matchTemplate(screen, template[:,:,:3], cv2.TM_CCORR_NORMED, mask=template[:,:,3])
        if threshold < 0.9: threshold = 0.9 
    else:
        res = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)
    if max_val >= threshold:
        return int(max_loc[0] + template.shape[1]/2), int(max_loc[1] + template.shape[0]/2)
    return None

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
            with open(HISTORY_FILE_PATH, "r", encoding="utf-8") as f: return json.load(f)
        except Exception as e: 
            print(f"🚨 [치명적 오류] history.json 손상! {e}"); sys.exit(1)
    return {}

def save_history(data):
    with open(HISTORY_FILE_PATH, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)

def load_aliases():
    if os.path.exists(ALIAS_FILE_PATH):
        try:
            with open(ALIAS_FILE_PATH, "r", encoding="utf-8") as f: return json.load(f)
        except: pass
    return {}

def save_aliases(data):
    with open(ALIAS_FILE_PATH, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)

def upload_to_github():
    print("☁️ GitHub 업로드 시도...")
    try:
        repo_dir = os.path.dirname(BASE_DIR)
        subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
        ts = datetime.now().strftime("%H:%M:%S")
        subprocess.run(["git", "commit", "-m", f"Auto update: {ts}"], cwd=repo_dir, check=True, capture_output=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=repo_dir, check=True)
        print("🚀 GitHub Push 완료!")
    except: print("ℹ️ 변경사항 없음 혹은 업로드 실패")

def get_last_baseline_time(logs):
    for log in logs:
        if log.get('type', 'normal') != 'abnormal' and log['time'] != 'UnKnown':
            return log['time']
    return None

# ================= 4. 메인 로직 =================

def main():
    window_manager.restore_and_autosave("영예점수 모니터링 실행")
    print(f"=== 🤖 스마트 트래커 (PyAutoGUI 10회 주기 메모리 정리) ===")
    
    try: run_adb(f"connect {TARGET_DEVICE}")
    except: return

    history_db = load_history()
    known_aliases = load_aliases()
    previous_active_guilds = set()
    cycle_count = 0
    INITIAL_COLLECT_TIME = "2026-01-29 10:48:43"

    while True:
        cycle_count += 1
        start_loop = time.time()
        
        # 🔥 10회 주기에 맞춰 메모리 정리 여부 결정
        should_cleanup = (cycle_count % 10 == 0)
        
        force_close_app(should_cleanup)
        time.sleep(2)
        
        icon_loc = find_image("icon.png")
        if icon_loc:
            run_adb(f'shell input tap {icon_loc[0]} {icon_loc[1]}')
            print(f"🚀 게임 실행 (로딩 대기 / 정리수행: {should_cleanup})")
            time.sleep(25)
        else:
            print("⚠️ 아이콘 못 찾음"); time.sleep(5); continue 

        # 토너먼트 진입 로직
        entered_tournament = False
        for _ in range(12): 
            close_loc = find_image("close.png")
            if close_loc: run_adb(f"shell input tap {close_loc[0]} {close_loc[1]}"), time.sleep(2)
            tour_loc = find_image("tournament.png", threshold=0.7)
            if tour_loc:
                run_adb(f"shell input tap {tour_loc[0]} {tour_loc[1]}")
                entered_tournament = True; break
            time.sleep(5)

        if entered_tournament:
            print("📊 상위 14개 길드 스캔 및 분석 중...")
            time.sleep(5)
            img, captured_path = capture_screen(is_ocr=True)
            
            if img is not None:
                current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"\n[Check: {current_time_str}]")
                scanned_items = []

                for i in range(14):
                    y_pos = int(START_Y + (i * ROW_GAP))
                    scanned_items.append({
                        'rank': i + 1,
                        'display_name': extract_guild_name(img, i) or "Unknown",
                        'score': extract_number(img, SCORE_START_X, y_pos, SCORE_WIDTH, HEIGHT),
                        'ww': extract_number(img, WW_START_X, y_pos, WW_WIDTH, HEIGHT),
                        'real_key': None
                    })

                # ✅ 유효성 검사 (화면 로딩 실패 방지)
                if scanned_items[0]['score'] == 0:
                    print("⚠️ 1위 점수 0점 -> 스킵"); continue
                
                valid_count = sum(1 for item in scanned_items if item['display_name'] != "Unknown" and item['score'] > 0)
                if valid_count < 5:
                    print(f"⚠️ 유효 데이터 부족({valid_count}) -> 스킵"); continue

                current_cycle_guilds = set()
                matched_db_keys = set()
                
                # 매칭 로직 (이름/지문)
                for item in scanned_items:
                    if item['display_name'] in history_db:
                        item['real_key'] = item['display_name']
                        matched_db_keys.add(item['display_name'])

                for item in scanned_items:
                    if item['real_key'] is None:
                        for db_key, logs in history_db.items():
                            if not logs or db_key in matched_db_keys: continue
                            if item['score'] == logs[0]['score'] and item['ww'] == logs[0]['ww']:
                                item['real_key'] = db_key; matched_db_keys.add(db_key); break
                        if not item['real_key']: item['real_key'] = item['display_name']

                # 데이터 처리 및 디스코드 알림
                current_display_data = {}
                for item in scanned_items:
                    final_key = item['real_key']
                    score, ww, rank, display_name = item['score'], item['ww'], item['rank'], item['display_name']
                    current_cycle_guilds.add(final_key)

                    # 닉네임 감지
                    if final_key != display_name:
                        if (final_key not in known_aliases) or (known_aliases[final_key] != display_name):
                            fields = [{"name": "원래 이름", "value": f"**{final_key}**", "inline": True},
                                      {"name": "현재 표시", "value": f"**{display_name}**", "inline": True}]
                            send_discord_msg("🏷️ 길드명 변경 감지", f"**{final_key}** 길드 이름 변경됨", color=3447003, fields=fields, image_path=captured_path)
                            known_aliases[final_key] = display_name; save_aliases(known_aliases)
                    elif final_key in known_aliases:
                        del known_aliases[final_key]; save_aliases(known_aliases)

                    # 로그 업데이트
                    if final_key not in history_db: history_db[final_key] = []; is_new, is_re = True, False
                    else: is_new, is_re = False, (final_key not in previous_active_guilds and len(previous_active_guilds) > 0)
                    
                    guild_logs = history_db[final_key]
                    last_score = guild_logs[0]['score'] if guild_logs else 0
                    
                    if score != 0 and score != last_score:
                        change_type, d_title, pref = "normal", "📈 순위 변동 감지", ""
                        log_time = current_time_str
                        
                        if is_new: change_type, d_title, pref, log_time = "new", "🆕 신규 길드 진입", "(신규)", "UnKnown"
                        elif is_re: change_type, d_title, pref = "re_entry", "🔄 [재진입] 복귀", "(재진입)"
                        else:
                            baseline = get_last_baseline_time(guild_logs)
                            if baseline and baseline not in ["UnKnown", INITIAL_COLLECT_TIME]:
                                diff_h = (datetime.now() - datetime.strptime(baseline, "%Y-%m-%d %H:%M:%S")).total_seconds()/3600
                                if diff_h < 48: change_type, d_title, pref = "abnormal", "⚠️ [비정상] 변동", "(비정상)"
                        
                        diff_str = f"{score - last_score:+}"
                        fields = [{"name": "기존", "value": str(last_score), "inline": True},
                                  {"name": "현재", "value": f"**{score}**", "inline": True},
                                  {"name": "변동", "value": f"**{diff_str}**", "inline": True}]
                        send_discord_msg(d_title, f"**{final_key}** {pref}", fields=fields, image_path=captured_path)
                        
                        guild_logs.insert(0, {'score': score, 'ww': ww, 'time': log_time, 'type': change_type})
                        history_db[final_key] = guild_logs[:10]

                    # 웹사이트용 패치
                    patched_hist = []
                    for log in history_db[final_key]:
                        t = log['time']
                        if log.get('type') == 'abnormal': t += " [비정상 감지⚠️]"
                        elif log.get('type') == 'new': t += " [순위권 신규 진입)"
                        elif log.get('type') == 're_entry': t += " [순위권 재진입]"
                        patched_hist.append({'score': log['score'], 'time': t})

                    current_display_data[rank] = {
                        'name': final_key, 'score': score, 'ww': ww,
                        'time': patched_hist[0]['time'] if patched_hist else "UnKnown",
                        'history': patched_hist, 'current_alias': display_name
                    }
                    print(f"#{rank} | {final_key} | {score}")
                
                previous_active_guilds = current_cycle_guilds.copy()
                save_history(history_db)
                with open(DATA_FILE_PATH, "w", encoding="utf-8") as f: json.dump(current_display_data, f, ensure_ascii=False, indent=4)
                upload_to_github()

        elapsed = time.time() - start_loop
        wait = int(max(0, CYCLE_INTERVAL - elapsed))
        while wait > 0:
            print(f"⏳ 다음 사이클까지 {wait}초 대기... (사이클: {cycle_count})", end='\r')
            time.sleep(1); wait -= 1

if __name__ == "__main__":
    main()