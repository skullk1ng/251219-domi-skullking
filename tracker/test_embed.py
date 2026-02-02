import requests
import json
from datetime import datetime

# 사용자님의 웹후크 URL
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1467971942135894127/ydmq_4ECyEQXdGRNe-TrTlQgnJrYDczkjfSMfkcm--bgxzzxUPrxbzX4Peze37VTfVA2"

def send_test_msg():
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 보낼 메시지 내용
    message = f"{current_time}\n[🔔 이것은 테스트 메시지입니다. 로그에 남지 않습니다.]"
    
    data = {"content": message}
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, data=json.dumps(data), headers=headers)
        
        if response.status_code == 204:
            print("✅ [성공] 디스코드를 확인해보세요! 메시지가 도착했을 겁니다.")
        else:
            print(f"❌ [실패] 코드: {response.status_code}\n내용: {response.text}")
            
    except Exception as e:
        print(f"⚠️ [에러] 발송 중 문제 발생: {e}")

if __name__ == "__main__":
    print("🚀 디스코드 테스트 메시지 발송 중...")
    send_test_msg()