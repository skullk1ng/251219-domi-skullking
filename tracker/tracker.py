# VERSION: 20260207A
# DESCRIPTION: 별칭(Alias) 시스템 적용 + 수동 감지 + 안정화

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
TARGET_DEVICE = "127.0.0.1:5555" # 사용자의 포트 환경에 맞게 유지
CYCLE_INTERVAL = 150 
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1467971942135894127/ydmq_4ECyEQXdGRNe-TrTlQgnJrYDczkjfSMfkcm--bgxzzxUPrxbzX4Peze37VTfVA2"
USE_DISCORD = True

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE_PATH = os.path.join(os.path.dirname(BASE_DIR), "data.json")
HISTORY_FILE_PATH = os.path.join(BASE_DIR, "history.json")
ALIAS_FILE_PATH = os.path.join(BASE_DIR, "aliases.json")

# OCR 좌표 설정
SCORE_START_X, SCORE_WIDTH = 1121, 100
WW_START_X, WW_WIDTH = 990, 60
GUILD_START_X, GUILD_WIDTH = 445, 250
START_Y, ROW_GAP, HEIGHT = 275, 50.8, 30

# ================= 2. 기본 함수들 =================

def imread_unicode(path, flags=cv2.IMREAD_COLOR):
    try:
        n = np.fromfile(path, np.uint8)
        return cv2.imdecode(n, flags)
    except: return None

def send_discord_msg(guild_name, time_str, fields, is_manual=False, image_path=None):
    if not USE_DISCORD: return
    try:
        title = "📈 순위 변동 감지"
        if is_manual: title += " [수동 입력 데이터]"

        desc = f"# {guild_name}\n"
        if is_manual: desc = f"# {guild_name} #수동 입력 데이터\n"
        
        desc += f"**측정 시간: {time_str}**\n\n"
        score_info = f"기존: {fields[0]['value']}  |  현재: {fields[1]['value']}  |  변동폭: {fields[2]['value']}"
        desc += score_info

        embed = {
            "title": title,
            "description": desc,
            "color": 16776960 if is_manual else 5763719,
            "image": {"url": "attachment://capture.png"} if image_path else {}
        }

        if image_path and os.path.exists(image_path):
            with open(image_path, "rb") as f:
                requests.post(DISCORD_WEBHOOK_URL, files={"file": ("capture.png", f, "image/png"), "payload_json": (None, json.dumps({"embeds": [embed]}))})
        else:
            requests.post(DISCORD_WEBHOOK_URL, json={"embeds": [embed]})
        print(f"   📨 디스코드 알림 완료 ({guild_name})")
    except Exception as e: print(f"   ⚠️ 알림 발송 실패: {e}")

def run_adb(command): subprocess.call(f'"{ADB_CMD}" -s {TARGET_DEVICE} {command}', shell=True)

def capture_screen():
    local_path = os.path.join(BASE_DIR, "monitor_tracker.png")
    run_adb(f'shell screencap -p /sdcard/monitor_tracker.png')
    run_adb(f'pull /sdcard/monitor_tracker.png "{local_path}"')
    return imread_unicode(local_path), local_path

def find_image(target, threshold=0.8):
    target_path = os.path.join(BASE_DIR, target)
    screen, _ = capture_screen()
    template = imread_unicode(target_path, cv2.IMREAD_UNCHANGED)
    if screen is None or template is None: return None
    res = cv2.matchTemplate(screen, template[:,:,:3], cv2.TM_CCORR_NORMED, mask=template[:,:,3]) if template.shape[2]==4 else cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)
    return (int(max_loc[0] + template.shape[1]/2), int(max_loc[1] + template.shape[0]/2)) if max_val >= threshold else None

def extract_number(img, x, y, w, h):
    roi = cv2.bitwise_not(cv2.threshold(cv2.cvtColor(cv2.resize(img[y:y+h, x:x+w], None, fx=2, fy=2), cv2.COLOR_BGR2GRAY), 140, 255, cv2.THRESH_BINARY)[1])
    text = pytesseract.image_to_string(roi, config='--psm 7 outputbase digits')
    clean = ''.join(filter(str.isdigit, text))
    return int(clean) if clean else 0

def extract_guild_name(img, rank):
    y, x, w, h = int(START_Y + (rank * ROW_GAP)), GUILD_START_X, GUILD_WIDTH, HEIGHT
    roi = cv2.bitwise_not(cv2.threshold(cv2.cvtColor(cv2.resize(img[y:y+h, x:x+w], None, fx=2, fy=2), cv2.COLOR_BGR2GRAY), 120, 255, cv2.THRESH_BINARY)[1])
    try: return pytesseract.image_to_string(roi, lang='kor+eng+rus+chi_tra+jpn', config='--psm 7').strip()
    except: return ""

def load_json(path):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f: return json.load(f)
        except: return {}
    return {}

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)

def upload_to_github():
    try:
        repo_dir = os.path.dirname(BASE_DIR)
        subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
        ts = datetime.now().strftime("%H:%M:%S")
        subprocess.run(["git", "commit", "-m", f"Auto update: {ts}"], cwd=repo_dir, check=True, capture_output=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=repo_dir, check=True)
        print("🚀 GitHub Push 완료!")
    except: pass

# ================= 3. 메인 로직 =================

def main():
    window_manager.restore_and_autosave("영예점수 모니터링 실행")
    print(f"=== 🤖 스마트 트래커 (Ver. 20260207A: Alias 적용) ===")
    run_adb(f"connect {TARGET_DEVICE}")
    
    cycle_count = 0
    previous_active_guilds = set()
    
    while True:
        try:
            cycle_count += 1
            start_loop = time.time()
            
            # 0. 설정 파일 로드
            history_db = load_json(HISTORY_FILE_PATH)
            alias_db = load_json(ALIAS_FILE_PATH) # 🔥 Alias 로드 추가

            # 1. 수동 입력 체크
            updated_manual = False
            for guild, logs in history_db.items():
                if logs and logs[0].get('type') == "manual" and not logs[0].get('announced'):
                    prev_s = logs[1]['score'] if len(logs) > 1 else 0
                    fields = [{"value": str(prev_s)}, {"value": f"**{logs[0]['score']}**"}, {"value": f"**{logs[0]['score']-prev_s:+}**"}]
                    send_discord_msg(guild, logs[0]['time'], fields, is_manual=True)
                    logs[0]['announced'] = True
                    updated_manual = True
            
            if updated_manual: save_json(HISTORY_FILE_PATH, history_db)

            # 2. 게임 실행 및 자동 스캔
            run_adb(f'shell am force-stop {GAME_PACKAGE}')
            time.sleep(2)
            icon = find_image("icon.png")
            if not icon: 
                print(f"⚠️ 아이콘 못 찾음 (사이클 {cycle_count})"); time.sleep(5); continue

            run_adb(f'shell input tap {icon[0]} {icon[1]}'); time.sleep(25)

            entered = False
            for _ in range(12):
                close = find_image("close.png")
                if close: run_adb(f"shell input tap {close[0]} {close[1]}"), time.sleep(2)
                tour = find_image("tournament.png", threshold=0.7)
                if tour:
                    run_adb(f"shell input tap {tour[0]} {tour[1]}")
                    entered = True; break
                time.sleep(5)

            if entered:
                time.sleep(5)
                img, cap_path = capture_screen()
                if img is not None and extract_number(img, SCORE_START_X, START_Y, SCORE_WIDTH, HEIGHT) != 0:
                    curr_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    scanned = []
                    
                    for i in range(14):
                        # 🔥 이름 추출 및 Alias 즉시 적용
                        raw_name = extract_guild_name(img, i) or f"Unknown ({chr(65+i)})"
                        display_name = alias_db.get(raw_name, raw_name) # 별칭이 있으면 교체, 없으면 그대로
                        
                        y_p = int(START_Y + (i * ROW_GAP))
                        scanned.append({
                            'rank': i+1, 
                            'display_name': display_name,
                            'score': extract_number(img, SCORE_START_X, y_p, SCORE_WIDTH, HEIGHT),
                            'ww': extract_number(img, WW_START_X, y_p, WW_WIDTH, HEIGHT)
                        })

                    current_keys = set()
                    website_display = {}
                    
                    for item in scanned:
                        real_key = item['display_name']
                        
                        # 지문 매칭 (이름이 달라도 점수+WW가 같으면 기존 길드로 인정)
                        if real_key not in history_db:
                            for k, l in history_db.items():
                                if l and item['score'] == l[0]['score'] and item['ww'] == l[0]['ww']:
                                    real_key = k
                                    # 🔥 지문 매칭 성공 시, Alias 자동 등록 시도
                                    if item['display_name'] != k:
                                        print(f"   💡 자동 매칭 발견: {item['display_name']} -> {k}")
                                    break
                        
                        if real_key not in history_db: history_db[real_key] = []
                        logs = history_db[real_key]
                        last_s = logs[0]['score'] if logs else 0
                        
                        change_type = "normal"
                        if not logs: change_type = "new"
                        elif real_key not in previous_active_guilds and len(previous_active_guilds) > 0: change_type = "re_entry"

                        if item['score'] != last_s:
                            fields = [{"value": str(last_s)}, {"value": f"**{item['score']}**"}, {"value": f"**{item['score']-last_s:+}**"}]
                            send_discord_msg(real_key, curr_ts, fields, image_path=cap_path)
                            logs.insert(0, {'score': item['score'], 'ww': item['ww'], 'time': curr_ts, 'type': change_type})
                            history_db[real_key] = logs[:10]
                        
                        patched = []
                        for l in logs:
                            t_str, l_t = l['time'], l.get('type', 'normal')
                            if l_t == "manual": t_str += " #수동 입력 데이터"
                            elif l_t == "new": t_str += " [신규]"
                            elif l_t == "re_entry": t_str += " [재진입]"
                            patched.append({'score': l['score'], 'time': t_str})
                        
                        # 🔥 data.json 생성 시 올바른 이름(real_key) 사용
                        website_display[item['rank']] = {
                            'name': real_key, 
                            'score': item['score'], 
                            'ww': item['ww'], 
                            'history': patched, 
                            'time': patched[0]['time'] if patched else "Unknown"
                        }
                        current_keys.add(real_key)

                    previous_active_guilds = current_keys.copy()
                    save_json(HISTORY_FILE_PATH, history_db)
                    with open(DATA_FILE_PATH, "w", encoding="utf-8") as f: json.dump(website_display, f, ensure_ascii=False, indent=4)
                    upload_to_github()

            elapsed = time.time() - start_loop
            wait_seconds = int(max(0, CYCLE_INTERVAL - elapsed))
            while wait_seconds > 0:
                print(f"⏳ 다음 사이클까지 {wait_seconds}초 대기... (사이클: {cycle_count})", end='\r'); time.sleep(1); wait_seconds -= 1
        
        except Exception as e:
            print(f"\n🚨 사이클 도중 에러 발생: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()