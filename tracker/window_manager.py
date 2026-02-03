import ctypes
import json
import os
import threading
import time
import sys

# 윈도우 API 설정
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

# 파일 경로 설정 (절대 경로 유지)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "window_positions.json")

def get_console_window():
    return kernel32.GetConsoleWindow()

def get_window_rect(hwnd):
    rect = RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top

def move_window(hwnd, x, y, w, h):
    user32.MoveWindow(hwnd, x, y, w, h, True)

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_config(data):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except:
        pass

def _auto_save_loop(name):
    hwnd = get_console_window()
    while True:
        try:
            x, y, w, h = get_window_rect(hwnd)
            
            # 창 크기가 정상일 때만 조용히 저장
            if w > 100 and h > 100:
                data = load_config()
                if name not in data or data[name] != [x, y, w, h]:
                    data[name] = [x, y, w, h]
                    save_config(data)
        except:
            pass
        
        time.sleep(3) # 3초마다 확인 (출력 없음)

def restore_and_autosave(script_name):
    hwnd = get_console_window()
    kernel32.SetConsoleTitleW(script_name)
    
    data = load_config()
    if script_name in data:
        x, y, w, h = data[script_name]
        try:
            move_window(hwnd, x, y, w, h)
            print(f"🪟 [창 위치 복구] 기존 위치로 이동했습니다.")
        except: pass
    else:
        # 처음 실행이라 저장된 위치가 없을 때만 표시
        print(f"🪟 [창 위치 저장] 창을 옮기면 3초 뒤 자동 저장됩니다.")

    t = threading.Thread(target=_auto_save_loop, args=(script_name,), daemon=True)
    t.start()