import requests
from bs4 import BeautifulSoup
import time
import json
import os
from datetime import datetime

# ================= 설정 =================
# 감시할 웹사이트
TARGET_URL = "https://www.dominationsworld.com/news"

# 🔔 디스코드 웹후크 URL
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1467971942135894127/ydmq_4ECyEQXdGRNe-TrTlQgnJrYDczkjfSMfkcm--bgxzzxUPrxbzX4Peze37VTfVA2"

# 🔄 확인 주기 (10분 = 600초)
CHECK_INTERVAL = 600

# 💾 데이터 저장 파일
LOG_FILE = "latest_news_log.txt"

# 🔥 [분석 완료] 개발자 도구 이미지를 바탕으로 만든 최신 글 선택자
# (ID가 아닌 클래스 기반이라 업데이트가 되어도 계속 작동합니다)
CSS_SELECTOR = "div.highlighted-article-card a.stretched-link"

# ================= 기능 =================

def send_discord_msg(title, link):
    """ 디스코드 알림 전송 """
    try:
        embed = {
            "embeds": [{
                "title": "🆕 도미네이션즈 새 소식!",
                "description": f"**[{title}]({link})**",
                "color": 16776960, # 노란색
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
        # 봇 차단 방지를 위한 헤더
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(TARGET_URL, headers=headers)
        
        if response.status_code != 200:
            print(f"   ❌ 사이트 접속 실패: {response.status_code}")
            return None, None

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 🔥 최신 글 요소 찾기
        elements = soup.select(CSS_SELECTOR)
        
        if elements:
            # 가장 첫 번째(최신) 요소를 가져옴
            latest = elements[0]
            
            # 제목 추출 (링크 태그 안에 텍스트가 숨어있거나, aria-label 등에 있을 수 있음)
            # 1. 텍스트 확인
            title = latest.get_text().strip()
            # 2. 텍스트가 비어있으면 aria-label 확인 (접근성 태그)
            if not title:
                title = latest.get('aria-label')
            # 3. 그래도 없으면 ID라도 가져옴
            if not title:
                title = latest.get('id')
            
            # 링크 추출 (href가 상대경로일 경우 처리)
            link = latest.get('href')
            if link and not link.startswith('http'):
                link = "https://www.dominationsworld.com" + link
                
            return title, link
        else:
            print("   ⚠️ 최신 글 요소를 찾을 수 없습니다. (사이트 구조 변경 가능성)")
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
    
    # 시작할 때 현재 최신글을 저장 (첫 실행 시 알림 방지)
    last_title = load_last_title()
    
    # 만약 저장된 기록이 없다면, 현재 최신글을 가져와서 저장만 하고 알림은 안 보냄
    if not last_title:
        print("   📂 첫 실행입니다. 현재 최신글을 기준점으로 잡습니다.")
        curr_title, _ = get_latest_post()
        if curr_title:
            save_last_title(curr_title)
            last_title = curr_title
            print(f"   ✅ 기준점 설정 완료: {last_title}")

    while True:
        print(f"\n🔍 ({datetime.now().strftime('%H:%M')}) 새 글 확인 중...")
        
        current_title, current_link = get_latest_post()
        
        if current_title:
            # 저장된 제목과 다르면 -> 새 글이다!
            if last_title != current_title:
                print(f"   ✨ [NEW] 발견! : {current_title}")
                send_discord_msg(current_title, current_link)
                
                # 파일 갱신
                save_last_title(current_title)
                last_title = current_title
            else:
                print(f"   💤 변동 없음 (최신: {current_title[:20]}...)")
        
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()