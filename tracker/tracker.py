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

def load_aliases():
    if os.path.exists(ALIAS_FILE_PATH):
        try:
            with open(ALIAS_FILE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {}

def save_aliases(data):
    with open(ALIAS_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

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

def get_last_baseline_time(logs):
    for log in logs:
        log_type = log.get('type', 'normal')
        if log_type != 'abnormal' and log['time'] != 'UnKnown':
            return log['time']
    return None

# ================= 6. 메인 로직 =================
def main():
    window_manager.restore_and_autosave("영예점수 모니터링 실행")
    print(f"=== 🤖 스마트 트래커 (빈 화면 방지 & 안전장치 적용) ===")
    
    try:
        subprocess.call(f'"{ADB_CMD}" connect {TARGET_DEVICE}', shell=True)
    except Exception as e:
        print(f"❌ ADB 연결 오류: {e}")
        return

    history_db = load_history()
    print(f"📂 히스토리 로드: {len(history_db)}개")
    
    known_aliases = load_aliases() 
    print(f"📂 알림 내역 로드: {len(known_aliases)}개")

    previous_active_guilds = set()

    INITIAL_COLLECT_TIME = "2026-01-29 10:48:43"

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
            print("📊 상위 14개 길드 스캔 및 분석 중...")
            time.sleep(5)
            
            img, captured_path = capture_screen(is_ocr=True)
            
            if img is not None:
                current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"\n[Check: {current_time_str}]")
                
                scanned_items = []
                
                # 데이터 수집
                for i in range(14):
                    rank = int(i + 1)
                    raw_name = extract_guild_name(img, i)
                    if not raw_name: raw_name = "Unknown"
                    y_pos = int(START_Y + (i * ROW_GAP))
                    score = extract_number(img, SCORE_START_X, y_pos, SCORE_WIDTH, HEIGHT)
                    ww = extract_number(img, WW_START_X, y_pos, WW_WIDTH, HEIGHT)

                    scanned_items.append({
                        'rank': rank,
                        'display_name': raw_name,
                        'score': score,
                        'ww': ww,
                        'real_key': None
                    })

                # 🔥🔥🔥 [핵심 수정] 유효성 검사 (Sanity Check) 🔥🔥🔥
                # 조건 1: 1위 점수가 0이면 로딩 실패로 간주
                if scanned_items[0]['score'] == 0:
                    print("⚠️ [오류] 1위 길드 점수가 0점입니다. (화면 로딩 실패 추정)")
                    print("   ⏭️ 이번 사이클은 저장하지 않고 건너뜁니다.")
                    continue
                
                # 조건 2: 'Unknown'이 아니고 '0점'이 아닌 유효 데이터가 최소 5개 이상이어야 함
                valid_count = 0
                for item in scanned_items:
                    if item['display_name'] != "Unknown" and item['score'] > 0:
                        valid_count += 1
                
                if valid_count < 5:
                    print(f"⚠️ [오류] 유효한 데이터가 너무 적습니다. ({valid_count}/14개)")
                    print("   ⏭️ 화면 오류 가능성이 높아 이번 업데이트를 건너뜁니다.")
                    continue
                # -------------------------------------------------------

                current_cycle_guilds = set()
                matched_db_keys = set()
                
                # 1. 이름 매칭
                for item in scanned_items:
                    if item['display_name'] in history_db:
                        item['real_key'] = item['display_name']
                        matched_db_keys.add(item['display_name'])

                # 2. 지문(점수+WW) 매칭
                for item in scanned_items:
                    if item['real_key'] is None:
                        found_original_name = None
                        for db_key, logs in history_db.items():
                            if not logs: continue
                            if db_key in matched_db_keys: continue
                            last_log = logs[0]
                            last_score = last_log.get('score', 0)
                            last_ww = last_log.get('ww', -1)
                            if last_ww == -1: continue

                            if (item['score'] == last_score) and (item['ww'] == last_ww):
                                found_original_name = db_key
                                break
                        
                        if found_original_name:
                            item['real_key'] = found_original_name
                            matched_db_keys.add(found_original_name)
                            print(f"  🕵️‍♂️ [신분 확인] {item['display_name']} -> {found_original_name}")
                        else:
                            item['real_key'] = item['display_name']

                # 3. 중복 처리
                key_counts = {}
                for item in scanned_items:
                    k = item['real_key']
                    if k not in key_counts: key_counts[k] = []
                    key_counts[k].append(item)
                
                for k, items in key_counts.items():
                    if len(items) > 1:
                        items.sort(key=lambda x: x['score'], reverse=True)
                        for idx, item in enumerate(items):
                            suffix = chr(65 + idx)
                            item['real_key'] = f"{k} ({suffix})"

                # 4. 결과 처리 및 저장
                current_display_data = {}
                for item in scanned_items:
                    final_key = item['real_key']
                    score = item['score']
                    ww = item['ww']
                    rank = item['rank']
                    display_name = item['display_name']
                    
                    current_cycle_guilds.add(final_key)

                    # 닉네임 변경 감지
                    if final_key != display_name:
                        if (final_key not in known_aliases) or (known_aliases[final_key] != display_name):
                            print(f"  🔔 [알림] 이름 변경 감지: {final_key} -> {display_name}")
                            fields = [
                                {"name": "원래 이름 (DB)", "value": f"**{final_key}**", "inline": True},
                                {"name": "현재 표시 이름", "value": f"**{display_name}**", "inline": True},
                                {"name": "판단 근거", "value": f"점수({score})와 월드워({ww}회)가 일치함", "inline": False}
                            ]
                            send_discord_msg("🏷️ 길드명 변경 감지", f"봇이 **{final_key}** 길드가 이름을 변경한 것으로 판단했습니다.", color=3447003, fields=fields, image_path=captured_path)
                            known_aliases[final_key] = display_name
                            save_aliases(known_aliases)
                    else:
                        if final_key in known_aliases:
                            del known_aliases[final_key]
                            save_aliases(known_aliases)

                    # 상태 판단 및 로그 업데이트
                    is_new_entry = False
                    is_re_entry = False

                    if final_key not in history_db: 
                        history_db[final_key] = []
                        is_new_entry = True
                    elif final_key not in previous_active_guilds and len(previous_active_guilds) > 0:
                        is_re_entry = True
                    
                    guild_logs = history_db[final_key]
                    last_score = guild_logs[0]['score'] if guild_logs else 0
                    
                    # 점수 변동 발생 시
                    if score != 0:
                        if score != last_score:
                            print(f"  🔔 변동: {final_key} ({last_score} -> {score})")
                            
                            log_time = current_time_str
                            change_type = "normal"
                            discord_title = "📈 순위 변동 감지"
                            desc_prefix = ""

                            if is_new_entry:
                                change_type = "new"
                                log_time = "UnKnown"
                                discord_title = "🆕 신규 길드 진입"
                                desc_prefix = "(신규)"
                            elif is_re_entry:
                                change_type = "re_entry"
                                log_time = current_time_str
                                discord_title = "🔄 [재진입] 순위권 복귀"
                                desc_prefix = "(재진입)"
                            else:
                                last_baseline = get_last_baseline_time(guild_logs)
                                if last_baseline and last_baseline != "UnKnown":
                                    if last_baseline == INITIAL_COLLECT_TIME:
                                        pass
                                    else:
                                        try:
                                            last_dt = datetime.strptime(last_baseline, "%Y-%m-%d %H:%M:%S")
                                            curr_dt = datetime.strptime(current_time_str, "%Y-%m-%d %H:%M:%S")
                                            diff_hours = (curr_dt - last_dt).total_seconds() / 3600
                                            
                                            if diff_hours < 48:
                                                change_type = "abnormal"
                                                discord_title = "⚠️ [비정상] 순위 변동 (48시간 미달)"
                                                desc_prefix = "(비정상)"
                                                print(f"   ⚠️ 48시간 내 변동 감지! (경과: {int(diff_hours)}시간)")
                                        except: pass

                            desc_text = f"**{final_key}** {desc_prefix}"
                            if final_key != display_name:
                                desc_text += f"\n(현재 닉네임: {display_name})"
                            
                            diff_val = score - last_score
                            diff_str = f"{diff_val:+}"

                            fields = [
                                {"name": "기존 점수", "value": f"{last_score}", "inline": True},
                                {"name": "현재 점수", "value": f"**{score}**", "inline": True},
                                {"name": "변동폭", "value": f"**{diff_str}**", "inline": True}
                            ]
                            send_discord_msg(discord_title, desc_text, fields=fields, image_path=captured_path)
                            
                            new_log = {'score': score, 'ww': ww, 'time': log_time, 'type': change_type}
                            guild_logs.insert(0, new_log)
                            if len(guild_logs) > 10: guild_logs = guild_logs[:10]
                            history_db[final_key] = guild_logs
                        else:
                            if guild_logs: guild_logs[0]['ww'] = ww

                    # 웹사이트 표시용 데이터 가공
                    display_history = []
                    if history_db[final_key]:
                        for log in history_db[final_key]:
                            t_str = log['time']
                            t_type = log.get('type', 'normal')
                            
                            if t_type == 'abnormal': t_str += " [비정상 감지⚠️]" 
                            elif t_type == 'new': t_str += "[순위권 신규 진입)"
                            elif t_type == 're_entry': t_str += " [순위권 재진입]"
                            
                            display_history.append({
                                'score': log['score'],
                                'time': t_str
                            })

                    main_display_time = "UnKnown"
                    if display_history:
                        main_display_time = display_history[0]['time']

                    current_display_data[rank] = {
                        'name': final_key, 
                        'score': score, 
                        'ww': ww, 
                        'time': main_display_time, 
                        'history': history_db[final_key],
                        'display_history_patched': display_history,
                        'current_alias': display_name
                    }
                    
                    log_text = f"#{rank} | {final_key} | {score}"
                    if final_key != display_name:
                        log_text += f" (Alias: {display_name})"
                    print(log_text)
                
                previous_active_guilds = current_cycle_guilds.copy()

                save_history(history_db)
                
                website_data = {}
                for r, d in current_display_data.items():
                    d_copy = d.copy()
                    d_copy['history'] = d.pop('display_history_patched')
                    website_data[r] = d_copy

                with open(DATA_FILE_PATH, "w", encoding="utf-8") as f:
                    json.dump(website_data, f, ensure_ascii=False, indent=4)
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