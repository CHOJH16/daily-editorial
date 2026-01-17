import requests
from bs4 import BeautifulSoup
import datetime
import os
import time

# --- 설정 ---
# 네이버 뉴스 '사설' 전용 리스트 페이지 (기사가 시간순으로 빠짐없이 들어있는 창고)
target_url_base = "https://news.naver.com/main/list.naver?mode=LS2D&mid=shm&sid1=110&sid2=262"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def send_telegram(news_list):
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('CHAT_ID')
    
    if not token or not chat_id:
        print("❌ 텔레그램 설정이 없습니다. (Secrets 확인 필요)")
        return

    # 오늘 날짜
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # 메시지 작성
    message = f"📰 주요 사설 모음 ({now_str})\n"
    message += f"총 {len(news_list)}개의 기사를 수집했습니다.\n\n"
    
    current_msg = message
    
    for news in news_list:
        # 보기 좋게 포맷팅
        item_str = f"[{news['press']}] {news['title']}\n{news['link']}\n\n"
        
        # 텔레그램 글자수 제한(4096자) 안전하게 끊어 보내기
        if len(current_msg) + len(item_str) > 3500:
            try:
                url = f"https://api.telegram.org/bot{token}/sendMessage"
                data = {'chat_id': chat_id, 'text': current_msg, 'disable_web_page_preview': True}
                requests.post(url, data=data)
                current_msg = "" # 초기화
            except Exception as e:
                print(f"텔레그램 전송 중 에러: {e}")
        
        current_msg += item_str
    
    # 마지막 링크 추가
    current_msg += "👉 웹에서 보기: https://chojh16.github.io/daily-editorial/"
    
    # 최종 발송
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {'chat_id': chat_id, 'text': current_msg, 'disable_web_page_preview': True}
        requests.post(url, data=data)
        print("✅ 텔레그램 전송 완료")
    except Exception as e:
        print(f"❌ 텔레그램 전송 실패: {e}")

def create_html(news_list):
    today = datetime.datetime.now().strftime("%Y년 %m월 %d일")
    html = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>오늘의 사설</title>
        <style>
            body {{ font-family: -apple-system, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #f9f9f9; }}
            h1 {{ text-align: center; color: #333; border-bottom: 3px solid #03c75a; padding-bottom: 15px; }}
            .info {{ text-align: right; color: #666; font-size: 0.8em; margin-bottom: 20px; }}
            .card {{ background: white; padding: 15px; margin-bottom: 10px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
            .press {{ color: #03c75a; font-weight: bold; font-size: 0.9em; }}
            a {{ text-decoration: none; color: #333; font-weight: bold; font-size: 1.1em; display: block; margin-top: 5px; }}
            a:hover {{ color: #0056b3; }}
        </style>
    </head>
    <body>
        <h1>📰 오늘의 주요 사설</h1>
        <div class="info">업데이트: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} | 기사: {len(news_list)}개</div>
    """
    
    for news in news_list:
        html += f"""
        <div class="card">
            <span class="press">{news['press']}</span>
            <a href="{news['link']}" target="_blank">{news['title']}</a>
        </div>
        """
        
    html += "</body></html>"
    return html

# === 메인 실행 로직 ===
try:
    print("🚀 크롤링 시작...")
    news_data = []
    seen_links = set()
    
    # 1페이지와 2페이지를 무조건 긁습니다. (약 40개 기사)
    # 날짜 필터를 없애고, 최신순으로 긁어오기 때문에 누락이 없습니다.
    for page in range(1, 3):
        url = f"{target_url_base}&page={page}"
        print(f"📡 페이지 {page} 접속 중... ({url})")
        
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 기사가 담긴 리스트 찾기 (type06_headline, type06)
        # 네이버 뉴스 리스트 페이지의 표준 구조입니다.
        articles = soup.select('.list_body ul li')
        
        print(f"   -> 기사 {len(articles)}개 발견")
        
        for item in articles:
            try:
                # 링크와 제목 추출
                dt = item.find_all('dt')
                # dt가 2개면 첫번째는 이미지, 두번째가 텍스트임. dt가 1개면 바로 텍스트.
                target_dt = dt[-1] if dt else None
                
                if not target_dt: continue
                
                a_tag = target_dt.find('a')
                if not a_tag: continue
                
                link = a_tag['href']
                title = a_tag.get_text(strip=True)
                
                # 중복 제거
                if link in seen_links: continue
                
                # 언론사 추출
                press_span = item.find('span', class_='writing')
                press = press_span.get_text(strip=True) if press_span else "사설"
                
                # 제목 정리 (언론사 이름 중복 제거)
                if title.startswith(press):
                    title = title[len(press):].lstrip('[] ')
                if title.startswith(f"[{press}]"):
                    title = title[len(press)+2:].strip()
                
                news_data.append({'title': title, 'link': link, 'press': press})
                seen_links.add(link)
                
            except Exception as e:
                print(f"   ⚠️ 기사 파싱 에러: {e}")
                continue
                
        time.sleep(0.5) # 차단 방지

    print(f"📊 총 {len(news_data)}개의 기사 수집 완료")

    if news_data:
        # 파일 저장
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(create_html(news_data))
        print("💾 index.html 저장 완료")
        
        # 텔레그램 전송
        send_telegram(news_data)
    else:
        print("❌ 수집된 기사가 없습니다. (사이트 구조 변경 의심)")

except Exception as e:
    print(f"🔥 치명적인 에러 발생: {e}")
    # 에러가 나도 스크립트가 멈추지 않게 처리
    exit(1)
