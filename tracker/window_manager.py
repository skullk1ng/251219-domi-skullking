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

# 파일 경로 설정 (OneDrive 경로 문제 방지)
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
        return True
    except Exception as e:
        print(f"❌ [치명적 오류] 파일 저장 실패: {e}")
        return False

def _auto_save_loop(name):
    hwnd = get_console_window()
    print(f"✅ 위치 저장 시스템 가동 중... (핸들: {hwnd})")
    print(f"📂 저장 파일 경로: {CONFIG_FILE}")
    
    while True:
        try:
            x, y, w, h = get_window_rect(hwnd)
            
            # 🔥 [디버그] 현재 감지된 창 정보를 3초마다 출력
            print(f"🔍 [상태체크] X={x}, Y={y}, W={w}, H={h} (창이름: {name})")

            # 너비(W)와 높이(H)가 100보다 커야 정상 창으로 인식
            if w > 100 and h > 100:
                data = load_config()
                # 위치가 바뀌었을 때만 저장
                if name not in data or data[name] != [x, y, w, h]:
                    print(f"📝 감지된 위치가 다릅니다! 저장 시도...")
                    data[name] = [x, y, w, h]
                    if save_config(data):
                        print(f"💾 [저장 성공] {x}, {y} 크기: {w}x{h}")
                else:
                    # 위치가 같으면 저장 안 함 (조용히 넘어감)
                    pass 
            else:
                print("⚠️ [경고] 창 크기가 0이거나 너무 작습니다. (윈도우 터미널 호환성 문제 가능성)")
        
        except Exception as e:
            print(f"❌ 루프 에러: {e}")
        
        time.sleep(3)

def restore_and_autosave(script_name):
    hwnd = get_console_window()
    kernel32.SetConsoleTitleW(script_name)
    
    data = load_config()
    if script_name in data:
        x, y, w, h = data[script_name]
        try:
            move_window(hwnd, x, y, w, h)
            print(f"🪟 [복구 완료] 저장된 위치: {x}, {y}")
        except: pass
    else:
        print(f"🪟 저장된 위치가 없습니다.")

    t = threading.Thread(target=_auto_save_loop, args=(script_name,), daemon=True)
    t.start()