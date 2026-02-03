import subprocess
import re
import os
import time

# ==========================================
# 👇 만약 자동으로 못 찾으면, 여기에 adb.exe 경로를 직접 넣으세요.
# 예시: r"C:\Program Files\BlueStacks_nxt\HD-Adb.exe"
MANUAL_ADB_PATH = "" 
# ==========================================

TARGET_PORT = "5565"
DEVICE_ADDRESS = f"127.0.0.1:{TARGET_PORT}"

def find_adb_command():
    # 1. 사용자가 직접 입력한 경로 확인
    if MANUAL_ADB_PATH and os.path.exists(MANUAL_ADB_PATH):
        return f'"{MANUAL_ADB_PATH}"'

    # 2. 시스템 환경변수(PATH)에 있는지 확인
    try:
        subprocess.check_output("adb version", shell=True, stderr=subprocess.STDOUT)
        return "adb"
    except:
        pass

    # 3. 흔한 앱플레이어 설치 경로 탐색
    common_paths = [
        r"C:\Program Files\BlueStacks_nxt\HD-Adb.exe",  # 블루스택 5
        r"C:\Program Files\BlueStacks\HD-Adb.exe",      # 블루스택 4
        r"C:\LDPlayer\LDPlayer9\adb.exe",               # LD플레이어 9
        r"C:\LDPlayer\LDPlayer4\adb.exe",               # LD플레이어 4
        r"C:\Program Files (x86)\Nox\bin\adb.exe",      # 녹스
        r"platform-tools\adb.exe",                      # 현재 폴더 내 platform-tools
        r"adb.exe"                                      # 현재 폴더
    ]

    print("🕵️ ADB 명령어를 찾는 중...")
    for path in common_paths:
        if os.path.exists(path):
            print(f"   ✨ 찾았다!: {path}")
            return f'"{path}"'
    
    return None

def get_current_package(adb_cmd):
    try:
        print(f"📡 연결 시도: {adb_cmd} connect {DEVICE_ADDRESS}")
        subprocess.call(f'{adb_cmd} connect {DEVICE_ADDRESS}', shell=True)
        
        print("🔍 현재 실행 중인 앱 확인 중...")
        # 덤프 명령어로 현재 포커스된 윈도우 정보 가져오기
        cmd = f'{adb_cmd} -s {DEVICE_ADDRESS} shell dumpsys window | findstr mCurrentFocus'
        result = subprocess.check_output(cmd, shell=True).decode('utf-8', errors='ignore')
        
        # 패키지 이름 추출 (u0 com.nexon.../...)
        match = re.search(r'u0 (.*?)/', result)
        if match:
            return match.group(1)
        else:
            return f"실패 (결과값: {result.strip()})"
    except Exception as e:
        return f"오류 발생: {e}"

# --- 메인 실행 ---
print("\n" + "="*50)
print("   🔍 게임 패키지 이름 확인기 v2")
print("="*50)

adb_cmd = find_adb_command()

if adb_cmd is None:
    print("\n[❌ 오류] 'adb.exe'를 찾을 수 없습니다!")
    print("해결 방법:")
    print("1. 이 파일을 adb.exe가 있는 폴더(또는 앱플레이어 설치 폴더)로 옮겨서 실행하세요.")
    print("2. 또는 코드 상단 'MANUAL_ADB_PATH'에 경로를 직접 적어주세요.")
else:
    pkg = get_current_package(adb_cmd)
    print("\n" + "="*50)
    print(f"✅ 당신의 게임 패키지 이름: {pkg}")
    print("="*50)
    print("👉 위 이름을 복사해서 simple_macro.py의 GAME_PACKAGE 변수에 붙여넣으세요.")

print("\n(종료하려면 엔터 키를 누르세요)")
input()