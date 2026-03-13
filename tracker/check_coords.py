import cv2
import numpy as np
import os
import subprocess
import sys
import traceback

# ✅ 한글 출력 깨짐 방지
sys.stdout.reconfigure(encoding='utf-8')

# ================= 1. 설정 =================
ADB_CMD = r"C:\Program Files\Netease\MuMuPlayer\nx_main\adb.exe"
TARGET_DEVICE = "127.0.0.1:16448" 
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 🔥 8차 보정 좌표: 전체 하단 이동, WW 우측 이동, 점수 좌측 이동 및 축소
SCORE_START_X, SCORE_WIDTH = 1119, 91
WW_START_X, WW_WIDTH = 1002, 60
GUILD_START_X, GUILD_WIDTH = 415, 220
START_Y, ROW_GAP, HEIGHT = 272, 51.0, 36

def run_adb(command):
    subprocess.call(f'"{ADB_CMD}" -s {TARGET_DEVICE} {command}', shell=True)

def imread_unicode(path, flags=cv2.IMREAD_COLOR):
    try:
        n = np.fromfile(path, np.uint8)
        return cv2.imdecode(n, flags)
    except: return None

# 🔥 한글 경로 이미지 저장 특수 함수
def imwrite_unicode(path, img_array):
    try:
        result, encoded_img = cv2.imencode(".png", img_array)
        if result:
            with open(path, mode='w+b') as f:
                encoded_img.tofile(f)
            return True
        return False
    except Exception as e:
        print(f"이미지 저장 오류: {e}")
        return False

def capture_screen():
    local_path = os.path.join(BASE_DIR, "monitor_tracker.png")
    run_adb(f'shell screencap -p /sdcard/monitor_tracker.png')
    run_adb(f'pull /sdcard/monitor_tracker.png "{local_path}"')
    return imread_unicode(local_path)

def main():
    print("=== 📸 좌표 디버깅 스크립트 실행 (8차 보정 좌표) ===")
    run_adb(f"connect {TARGET_DEVICE}")
    print("화면을 캡처합니다...")
    
    img = capture_screen()
    if img is None:
        print("❌ 화면 캡처 실패!")
        return

    # 1위부터 5위까지만 박스 그려보기
    for i in range(5):
        y = int(START_Y + (i * ROW_GAP))
        
        # 길드명 박스 (초록색)
        cv2.rectangle(img, (GUILD_START_X, y), (GUILD_START_X + GUILD_WIDTH, y + HEIGHT), (0, 255, 0), 2)
        # WW 박스 (파란색)
        cv2.rectangle(img, (WW_START_X, y), (WW_START_X + WW_WIDTH, y + HEIGHT), (255, 0, 0), 2)
        # 점수 박스 (빨간색)
        cv2.rectangle(img, (SCORE_START_X, y), (SCORE_START_X + SCORE_WIDTH, y + HEIGHT), (0, 0, 255), 2)

    output_path = os.path.join(BASE_DIR, "debug_coords.png")
    
    # 🔥 한글 경로 저장 함수 사용
    if imwrite_unicode(output_path, img):
        print(f"✅ 디버그 이미지 저장 완료: {output_path}")
        print("👉 폴더를 새로고침(F5)하여 네모 박스가 글자에 잘 맞는지 확인해 보세요!")
    else:
        print("❌ 이미지 파일 생성에 실패했습니다.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("\n🚨 에러가 발생했습니다! 아래 내용을 확인해 주세요:")
        traceback.print_exc()
    finally:
        input("\n엔터 키를 누르면 창이 닫힙니다...")