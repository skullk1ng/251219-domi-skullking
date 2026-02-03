import requests
from bs4 import BeautifulSoup
import time
import json
import os
from datetime import datetime
import sys

# ✅ 한글 출력 깨짐 방지
sys.stdout.reconfigure(encoding='utf-8')

# ================= 설정 =================
# 감시할 웹사이트
TARGET_URL = "https://www.dominationsworld.com/news"

# 🔥 [수정됨] '#업데이트-알림' 채널 전용 웹후크
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1468066940533866605/4u4WgLUt6zVGvOhcU0ReB311EJ-5XuwwMZOk7UKTRcPUgkHkqlLUNlvdyigxAtnkQSvC"

# 🔄 확인 주기 (10분 = 600초)
CHECK_INTERVAL = 600

# 💾 데이터 저장 파일 (중복 알림 방지용)
LOG_FILE = "latest_news_log.txt"

# 🕵️‍♂️ 최신 글 찾는 규칙 (CSS 선택자)
CSS_SELECTOR = "div.highlighted-article-card a.stretched-link"

# ================= 기능 =================

def send_discord_msg(title, link):
    """ 디스코드 알림 전송 """
    try:
        embed = {
            "embeds": [{
                "title": "🆕 도미네이션즈 새 소식!",
                "description": f"**[{title}]({link})**",
                "color": 16776960, # 노란색 (Gold)
                "footer": {
                    "text": f"감지 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                }
            }]
        }
        headers = {"Content-Type": "application/json"}
        requests.post(DISCORD_WEBHOOK_URL, data=json.dumps(embed), headers=headers)
        print("   📨 디스코드 알림 발송 완료")
    except Exception as e:
        print(f"   ⚠️ 디스코드 전송 실패: {e}")

def get_latest_post():
    """ 웹사이트 크롤링 """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(TARGET_URL, headers=headers)
        
        if response.status_code != 200:
            print(f"   ❌ 사이트 접속 실패: {response.status_code}")
            return None, None

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 최신 글 요소 찾기
        elements = soup.select(CSS_SELECTOR)
        
        if elements:
            latest = elements[0]
            
            # 제목 추출 시도 (텍스트 -> aria-label -> id 순서)
            title = latest.get_text().strip()
            if not title: title = latest.get('aria-label')
            if not title: title = latest.get('id')
            
            # 링크 추출 (상대경로 처리)
            link = latest.get('href')
            if link and not link.startswith('http'):
                link = "https://www.dominationsworld.com" + link
                
            return title, link
        else:
            print("   ⚠️ 최신 글 요소를 찾을 수 없습니다.")
            return None, None

    except Exception as e:
        print(f"   ⚠️ 크롤링 오류: {e}")
        return None, None

def load_last_title():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return None

def save_last_title(title):
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(title)

# ================= 메인 실행 =================

def main():
    print(f"=== 📰 뉴스 알림 봇 시작 ({TARGET_URL}) ===")
    print(f"   👉 알림 채널: #업데이트-알림")
    
    last_title = load_last_title()
    
    # 첫 실행 시 기준점 잡기
    if not last_title:
        print("   📂 첫 실행입니다. 현재 최신글을 기준점으로 잡습니다.")
        curr_title, _ = get_latest_post()
        if curr_title:
            save_last_title(curr_title)
            last_title = curr_title
            print(f"   ✅ 기준점 설정 완료: {last_title}")
    else:
        print(f"   📂 기존 기록 로드됨: {last_title}")

    while True:
        print(f"\n🔍 ({datetime.now().strftime('%H:%M')}) 새 글 확인 중...")
        
        current_title, current_link = get_latest_post()
        
        if current_title:
            if last_title != current_title:
                print(f"   ✨ [NEW] 발견! : {current_title}")
                send_discord_msg(current_title, current_link)
                
                save_last_title(current_title)
                last_title = current_title
            else:
                print(f"   💤 변동 없음 (최신: {current_title[:20]}...)")
        
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()