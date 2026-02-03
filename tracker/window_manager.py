import ctypes
import json
import os
import threading
import time
import sys

# 윈도우 API 설정
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# 구조체 정의
class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

# 🔥 [수정] 파일 경로를 절대 경로로 고정 (파일 생성 위치 문제 해결)
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
    except Exception as e:
        print(f"⚠️ 저장 실패: {e}")

def _auto_save_loop(name):
    hwnd = get_console_window()
    if not hwnd:
        print("❌ [오류] 창 핸들(ID)을 찾지 못했습니다.")
        return

    print(f"✅ 위치 저장 시스템 가동 중... (핸들: {hwnd})")
    
    while True:
        try:
            x, y, w, h = get_window_rect(hwnd)
            
            # 창 크기가 정상일 때만 저장
            if w > 100 and h > 100:
                data = load_config()
                
                # 기존 위치와 다를 때만 저장 (불필요한 쓰기 방지)
                if name not in data or data[name] != [x, y, w, h]:
                    data[name] = [x, y, w, h]
                    save_config(data)
                    # 🔥 [확인용] 저장이 되면 이 메시지가 뜹니다!
                    print(f"💾 창 위치 저장됨: {x}, {y} ({w}x{h})")
        except Exception as e:
            print(f"⚠️ 위치 감지 오류: {e}")
            
        time.sleep(3) # 3초마다 확인

def restore_and_autosave(script_name):
    """
    이 함수를 호출하면:
    1. 저장된 위치가 있으면 거기로 이동합니다.
    2. 없으면 기본 위치에 뜹니다.
    3. 백그라운드에서 3초마다 현재 위치를 저장합니다.
    """
    hwnd = get_console_window()
    
    # 1. 제목 설정 (제목으로 구분하므로 중요)
    kernel32.SetConsoleTitleW(script_name)
    
    # 2. 위치 복구
    data = load_config()
    if script_name in data:
        x, y, w, h = data[script_name]
        try:
            move_window(hwnd, x, y, w, h)
            print(f"🪟 [복구 완료] 저장된 위치: {x}, {y}")
        except:
            print("⚠️ 위치 복구 실패")
    else:
        print(f"🪟 저장된 위치가 없습니다. ({CONFIG_FILE})")

    # 3. 자동 저장 스레드 시작
    t = threading.Thread(target=_auto_save_loop, args=(script_name,), daemon=True)
    t.start()