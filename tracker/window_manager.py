import ctypes
import json
import os
import threading
import time

# 윈도우 API 설정
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

CONFIG_FILE = "window_positions.json"

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
            # 최소 크기 등 예외 처리
            if w > 0 and h > 0:
                data = load_config()
                
                # 기존 값과 다를 때만 저장 (디스크 쓰기 최소화)
                if name not in data or data[name] != [x, y, w, h]:
                    data[name] = [x, y, w, h]
                    save_config(data)
        except:
            pass
        time.sleep(3) # 3초마다 위치 확인

def restore_and_autosave(script_name):
    """
    이 함수를 호출하면:
    1. 저장된 위치가 있으면 거기로 이동합니다.
    2. 없으면 기본 위치에 뜹니다.
    3. 백그라운드에서 3초마다 현재 위치를 저장합니다.
    """
    hwnd = get_console_window()
    
    # 1. 제목 설정
    kernel32.SetConsoleTitleW(script_name)
    
    # 2. 위치 복구
    data = load_config()
    if script_name in data:
        x, y, w, h = data[script_name]
        move_window(hwnd, x, y, w, h)
        print(f"🪟 창 위치 복구 완료: {x}, {y}")
    else:
        print("🪟 저장된 위치가 없어 기본 위치를 사용합니다.")

    # 3. 자동 저장 스레드 시작
    t = threading.Thread(target=_auto_save_loop, args=(script_name,), daemon=True)
    t.start()