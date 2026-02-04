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
WIN_TITLE = "[data] RANK TRACKER"
CYCLE_INTERVAL = 150 
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1467971942135894127/ydmq_4ECyEQXdGRNe-TrTlQgnJrYDczkjfSMfkcm--bgxzzxUPrxbzX4Peze37VTfVA2"

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
    """한글 경로('바탕 화면')의 이미지를 읽기 위한 함수"""
    try:
        n = np.fromfile(path, np.uint8)
        return cv2.imdecode(n, flags)
    except: return None

def upload_to_github():
    print("☁️ GitHub 업로드 시도...")
    try:
        repo_dir = os.path.dirname(BASE_DIR)
        subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
        ts = datetime.now().strftime("%H:%M:%S")
        subprocess.run(["git", "commit", "-m", f"Auto update: {ts}"], cwd=repo_dir, check=True, capture_output=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=repo_dir, check=True)
        print("🚀 GitHub Push 완료!")
    except: print("ℹ️ 업로드 실패 (명령 위치 확인 필요)")

def send_discord_msg(title, desc, color=5763719, fields=None, image_path=None, custom_time=None):
    try:
        display_time = custom_time if custom_time else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        embed = {"title": title, "description": desc, "color": color, "fields": fields if fields else [], "footer": {"text": f"측정 시간: {display_time}"}}
        if image_path and os.path.exists(image_path):
            with open(image_path, "rb") as f:
                requests.post(DISCORD_WEBHOOK_URL, files={"file": ("capture.png", f, "image/png"), "payload_json": (None, json.dumps({"embeds": [embed]}))})
        else: requests.post(DISCORD_WEBHOOK_URL, json={"embeds": [embed]})
        print("   📨 디스코드 알림 발송 완료")
    except Exception as e: print(f"   ⚠️ 디스코드 발송 실패: {e}")

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

def get_last_baseline_time(logs):
    for log in logs:
        l_t = log.get('type', 'normal')
        if "manual" in l_t or "abnormal" not in l_t:
            if log['time'] != 'UnKnown': return log['time']
    return None

# ================= 3. 메인 로직 =================

def main():
    window_manager.restore_and_autosave(WIN_TITLE)
    print(f"=== 🤖 스마트 트래커 (전체 기능 복구 버전) ===")
    run_adb(f"connect {TARGET_DEVICE}")
    
    history_db = {}
    try:
        if os.path.exists(HISTORY_FILE_PATH):
            with open(HISTORY_FILE_PATH, "r", encoding="utf-8") as f: history_db = json.load(f)
    except: pass
    
    previous_active_guilds = set()
    INITIAL_TIME = "2026-01-29 10:48:43"

    while True:
        start_loop = time.time()
        run_adb(f'shell am force-stop {GAME_PACKAGE}')
        time.sleep(2)
        
        icon = find_image("icon.png")
        if not icon: 
            print("⚠️ 아이콘 못 찾음 - 대기 중"); time.sleep(5); continue
            
        run_adb(f'shell input tap {icon[0]} {icon[1]}')
        time.sleep(25)

        entered = False
        for _ in range(12):
            close = find_image("close.png")
            if close: run_adb(f"shell input tap {close[0]} {close[1]}"), time.sleep(2)
            tour = find_image("tournament.png", threshold=0.7)
            if tour:
                run_adb(f"shell input tap {tour[0]} {tour[1]}")
                entered = True
                break
            time.sleep(5)

        if entered:
            time.sleep(5)
            img, cap_path = capture_screen()
            if img is not None:
                curr_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                scanned = []
                for i in range(14):
                    y_p = int(START_Y + (i * ROW_GAP))
                    scanned.append({
                        'rank': i+1, 'display_name': extract_guild_name(img, i) or "Unknown",
                        'score': extract_number(img, SCORE_START_X, y_p, SCORE_WIDTH, HEIGHT),
                        'ww': extract_number(img, WW_START_X, y_p, WW_WIDTH, HEIGHT),
                        'real_key': None
                    })

                if scanned[0]['score'] != 0:
                    matched_keys = set()
                    for item in scanned:
                        if item['display_name'] in history_db:
                            item['real_key'] = item['display_name']
                            matched_keys.add(item['display_name'])
                    
                    for item in scanned:
                        if not item['real_key']:
                            for k, logs in history_db.items():
                                if k in matched_keys or not logs: continue
                                if item['score'] == logs[0]['score'] and item['ww'] == logs[0]['ww']:
                                    item['real_key'] = k
                                    matched_keys.add(k)
                                    break
                            if not item['real_key']: item['real_key'] = item['display_name']

                    website_display = {}
                    for item in scanned:
                        key = item['real_key']
                        score, ww, rank, d_name = item['score'], item['ww'], item['rank'], item['display_name']
                        
                        if key not in history_db: 
                            history_db[key] = []
                            is_new, is_re = True, False
                        else: 
                            is_new = False
                            is_re = (key not in previous_active_guilds and len(previous_active_guilds) > 0)

                        logs = history_db[key]
                        
                        # 🔥 수동 입력 감지 및 알림 (사용자님 수정 단어 반영)
                        if logs and "manual" in logs[0].get('type', '') and not logs[0].get('announced', False):
                            is_ab = "abnormal" in logs[0]['type']
                            d_title = "⚠️ [비정상] 순위 변동 감지 [수동 체크 건]" if is_ab else "📈 순위 변동 감지 [수동 체크 건]"
                            prev_s = logs[1]['score'] if len(logs) > 1 else 0
                            fields = [{"name":"이전 점수","value":str(prev_s),"inline":True},
                                      {"name":"수동입력","value":f"**{logs[0]['score']}**","inline":True},
                                      {"name":"변동폭","value":f"**{logs[0]['score']-prev_s:+}**","inline":True}]
                            send_discord_msg(d_title, f"**{key}** [수동 입력 데이터]", fields=fields, custom_time=logs[0]['time'])
                            logs[0]['announced'] = True

                        last_s = logs[0]['score'] if logs else 0
                        if score != 0 and score != last_s:
                            c_type, title, pref = "normal", "📈 순위 변동 감지", ""
                            if is_new: c_type, title, pref = "new", "🆕 신규 길드 진입", "(신규)"
                            elif is_re: c_type, title, pref = "re_entry", "🔄 [재진입] 복귀", "(재진입)"
                            else:
                                base = get_last_baseline_time(logs)
                                if base and base != INITIAL_TIME:
                                    try:
                                        diff_h = (datetime.now() - datetime.strptime(base, "%Y-%m-%d %H:%M:%S")).total_seconds()/3600
                                        if diff_h < 48: c_type, title, pref = "abnormal", "⚠️ [비정상] 순위 변동 감지", "[비정상]"
                                    except: pass

                            fields = [{"name":"기존","value":str(last_s),"inline":True}, {"name":"현재","value":f"**{score}**","inline":True}, {"name":"변동","value":f"**{score-last_s:+}**","inline":True}]
                            send_discord_msg(title, f"**{key}** {pref}", fields=fields, image_path=cap_path)
                            logs.insert(0, {'score':score, 'ww':ww, 'time':curr_ts if c_type!="new" else "UnKnown", 'type':c_type})
                            history_db[key] = logs[:10]
                        elif logs: logs[0]['ww'] = ww

                        patched = []
                        for l in logs:
                            t_str, l_t = l['time'], l.get('type', 'normal')
                            if "abnormal" in l_t: t_str += " [비정상 감지⚠️]"
                            if "manual" in l_t: t_str += " [수동 체크 건]"
                            elif l_t == 'new': t_str += " [신규]"
                            elif l_t == 're_entry': t_str += " [재진입]"
                            patched.append({'score': l['score'], 'time': t_str})

                        website_display[rank] = {'name': key, 'score': score, 'ww': ww, 'time': patched[0]['time'] if patched else "UnKnown", 'history': patched, 'current_alias': d_name}
                    
                    previous_active_guilds = matched_keys.copy()
                    with open(HISTORY_FILE_PATH, "w", encoding="utf-8") as f: json.dump(history_db, f, ensure_ascii=False, indent=4)
                    with open(DATA_FILE_PATH, "w", encoding="utf-8") as f: json.dump(website_display, f, ensure_ascii=False, indent=4)
                    upload_to_github()

        wait = int(max(0, CYCLE_INTERVAL - (time.time() - start_loop)))
        while wait > 0:
            print(f"⏳ 다음 사이클까지 {wait}초 대기...", end='\r'); time.sleep(1); wait -= 1

if __name__ == "__main__":
    main()