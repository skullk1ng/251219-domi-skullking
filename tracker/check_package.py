import subprocess
import re

ADB_CMD = "adb"
# 포트가 5565라면 아래 주소 사용, 아니면 수정
DEVICE_ADDRESS = "127.0.0.1:5565" 

def get_current_package():
    try:
        # 현재 화면 맨 위에 있는 앱 정보 가져오기
        cmd = f'"{ADB_CMD}" -s {DEVICE_ADDRESS} shell dumpsys window | grep mCurrentFocus'
        result = subprocess.check_output(cmd, shell=True).decode('utf-8')
        
        # 패키지 이름 추출
        match = re.search(r'u0 (.*?)/', result)
        if match:
            return match.group(1)
    except:
        pass
    return "찾지 못함"

print("🔍 현재 실행 중인 게임 패키지 이름 확인 중...")
pkg = get_current_package()
print(f"\n👉 당신의 게임 패키지 이름은: [{pkg}] 입니다.\n")
print("이 이름을 복사해서 macro.py의 GAME_PACKAGE 변수에 넣으세요.")