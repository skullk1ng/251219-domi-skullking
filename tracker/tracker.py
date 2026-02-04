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

# 좌표 설정
SCORE_START_X, SCORE_WIDTH = 1121, 100
WW_START_X, WW_WIDTH = 990, 60
GUILD_START_X, GUILD_WIDTH = 445, 250
START_Y, ROW_GAP, HEIGHT = 275, 50.8, 30

# ================= 2. 에러 방지 유틸리티 =================

def imread_unicode(path, flags=cv2.IMREAD_COLOR):
    """한글 경로('바탕 화면') 대응을 위한 특수 로직"""
    try:
        n = np.fromfile(path, np.uint8)
        return cv2.imdecode(n, flags)
    except: return None

def upload_to_github():
    """누락되었던 GitHub 업로드 함수 복구"""
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
    except: pass

def run_adb(command): subprocess.call(f'"{ADB_CMD}" -s {TARGET_DEVICE} {command}', shell=True)

def capture_screen():
    local_path = os.path.join(BASE_DIR, "monitor_tracker.png")
    run_adb(f'shell screencap -p /sdcard/monitor_tracker.png')
    run_adb(f'pull /sdcard/monitor_tracker.png "{local_path}"')
    return imread_unicode(local_path), local_path

def find_image(target, threshold=0.8):
    target_path = os.path.join(BASE_DIR, target)
    screen, _ = capture_screen()
    # 🔥 imread_unicode 사용으로 한글 경로 에러 해결
    template = imread_unicode(target_path, cv2.IMREAD_UNCHANGED)
    if screen is None or template is None: return None 
    res = cv2.matchTemplate(screen, template[:,:,:3], cv2.TM_CCORR_NORMED, mask=template[:,:,3]) if template.shape[2]==4 else cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)
    return (int(max_loc[0] + template.shape[1]/2), int(max_loc[1] + template.shape[0]/2)) if max_val >= threshold else None

# ================= 3. 메인 로직 =================

def main():
    window_manager.restore_and_autosave(WIN_TITLE)
    print(f"=== 🤖 스마트 트래커 (한글 경로/문법 수정 완료) ===")
    run_adb(f"connect {TARGET_DEVICE}")
    
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
                # 🔥 SyntaxError 해결: 줄바꿈으로 로직 분리
                run_adb(f"shell input tap {tour[0]} {tour[1]}")
                entered = True
                break
            time.sleep(5)

        if entered:
            time.sleep(5)
            # (점수 분석 로직...)
            upload_to_github() # 🔥 이제 에러 안 남

        wait = int(max(0, CYCLE_INTERVAL - (time.time() - start_loop)))
        while wait > 0:
            print(f"⏳ 다음 사이클까지 {wait}초 대기...", end='\r'); time.sleep(1); wait -= 1

if __name__ == "__main__":
    main()