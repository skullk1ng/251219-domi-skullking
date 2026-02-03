import requests
import json
import os
from datetime import datetime

# ✅ 사용자님의 디스코드 웹후크 URL
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1467971942135894127/ydmq_4ECyEQXdGRNe-TrTlQgnJrYDczkjfSMfkcm--bgxzzxUPrxbzX4Peze37VTfVA2"

# 🔥 [핵심 수정] 현재 파일(test_discord.py)이 있는 폴더의 절대 경로를 구합니다.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def send_test_msg(guild_name, old_score, new_score, image_path=None):
    print(f"📨 디스코드 전송 시도 중...")
    print(f"   👉 이미지 경로 확인: {image_path}")
    
    try:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 1. 임베드 데이터 생성
        embed_data = {
            "embeds": [{
                "title": "🔔 테스트 메시지입니다",
                "description": f"**{guild_name}**",
                "color": 5763719,
                "fields": [
                    {"name": "기존 점수", "value": f"{old_score}", "inline": True},
                    {"name": "현재 점수", "value": f"**{new_score}**", "inline": True},
                    {"name": "변동폭", "value": f"+{new_score - old_score}", "inline": True}
                ],
                "footer": {"text": f"테스트 시간: {current_time}"},
                "image": {"url": "attachment://test_image.png"} if image_path else {}
            }]
        }

        # 2. 전송 (이미지 유무에 따라 분기)
        if image_path and os.path.exists(image_path):
            print("   📸 이미지를 첨부하여 전송합니다.")
            with open(image_path, "rb") as f:
                files = {
                    "file": ("test_image.png", f, "image/png"),
                    "payload_json": (None, json.dumps(embed_data))
                }
                response = requests.post(DISCORD_WEBHOOK_URL, files=files)
        else:
            print("   ⚠️ 이미지가 없거나 경로가 틀려 텍스트만 전송합니다.")
            headers = {"Content-Type": "application/json"}
            response = requests.post(DISCORD_WEBHOOK_URL, data=json.dumps(embed_data), headers=headers)

        if response.status_code == 204 or response.status_code == 200:
            print("✅ 전송 성공! 디스코드를 확인하세요.")
        else:
            print(f"❌ 전송 실패: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"⚠️ 오류 발생: {e}")

if __name__ == "__main__":
    # 🔥 [수정] 무조건 현재 폴더 기준으로 파일을 찾습니다.
    target_filename = "monitor_tracker.png"
    target_image_path = os.path.join(BASE_DIR, target_filename)
    
    print(f"📂 현재 작업 폴더: {BASE_DIR}")
    print(f"🔎 찾는 파일: {target_image_path}")

    if not os.path.exists(target_image_path):
        print(f"\n[❌ 실패] '{target_filename}' 파일이 없습니다!")
        print(" -> 파일명이 정확한지, 확장자(.png)가 맞는지 확인해주세요.")
        target_image_path = None
    else:
        print(f"[✅ 성공] 파일을 찾았습니다!")

    # 가짜 데이터로 테스트 발송
    send_test_msg("테스트 길드", 15000, 15500, target_image_path)
    
    input("\n엔터 키를 누르면 종료합니다...")