import requests
from bs4 import BeautifulSoup
import datetime
import os
import re
import time

# ==========================================
# 🕒 [시간 대기 기능] 06:00 정각 배달을 위한 대기실
# ==========================================
def wait_until_6am():
    # 1. 현재 한국 시간 계산 (서버는 UTC이므로 9시간 더함)
    now_utc = datetime.datetime.utcnow()
    now_kst = now_utc + datetime.timedelta(hours=9)
    
    # 2. 목표 시간 설정 (오늘 오전 6시 0분 0초)
    target_time = now_kst.replace(hour=6, minute=0, second=0, microsecond=0)
    
    # 3. 만약 이미 6시가 지났다면? (예: 서버가 너무 늦게 켜져서 6시 5분이 됨)
    # -> 내일 6시를 기다리면 안 되니까, 즉시 실행하도록 패스
    if now_kst > target_time:
        print(f"현재 시각({now_kst.strftime('%H:%M')})이 목표 시간(06:00)을 지났습니다. 즉시 실행합니다.")
        return

    # 4. 남은 시간 계산 (초 단위)
    wait_seconds = (target_time - now_kst).total_seconds()
    
    # 5. 대기 시작
    print(f"현재 한국 시간: {now_kst.strftime('%H:%M:%S')}")
    print(f"목표 실행 시간: 06:00:00")
    print(f"약 {int(wait_seconds // 60)}분 {int(wait_seconds % 60)}초 동안 대기합니다...")
    
    time.sleep(wait_seconds)
    print("⏰ 6시가 되었습니다! 뉴스 수집을 시작합니다.")

# 로봇이 켜지자마자 대기 기능부터 실행
wait_until_6am()

# ==========================================
# 📰 [본체] 뉴스 수집 및 전송 로직
# ==========================================

# --- 설정 ---
url = "https://news.naver.com/opinion/editorial"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# 텔레그램 전송 함수
def send_telegram(news_list):
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('CHAT_ID')
    
    if not token or not chat_id:
        return

    today = datetime.datetime.now().strftime("%Y년 %m월 %d일") # 한국 시간이 아닌 서버 시간 기준일 수 있으나 날짜 표시는 큰 문제 없음
    # 정확한 한국 날짜 표시를 위해 수정
    korea_now = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
    today_str = korea_now.strftime("%Y년 %m월 %d일")
    
    message = f"📰 {today_str} 주요 사설 요약\n\n"
    
    for news in news_list:
        news_item = f"[{news['press']}] {news['title']}\n{news['link']}\n\n"
        
        if len(message) + len(news_item) > 3800:
            try:
                send_url = f"https://api.telegram.org/bot{token}/sendMessage"
                data = {'chat_id': chat_id, 'text': message, 'disable_web_page_preview': True}
                requests.post(send_url, data=data)
                message = "" 
            except: pass
        
        message += news_item
    
    message += "👉 웹에서 보기: https://chojh16.github.io/daily-editorial/"

    try:
        send_url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {'chat_id': chat_id, 'text': message, 'disable_web_page_preview': True}
        requests.post(send_url, data=data)
    except: pass

# HTML 생성 함수
def create_html(news_list):
    korea_now = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
    today_str = korea_now.strftime("%Y년 %m월 %d일")
    update_time_str = korea_now.strftime("%Y-%m-%d %H:%M:%S")

    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>오늘의 사설 ({today_str})</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background-color: #f4f4f9; }}
            h1 {{ color: #333; text-align: center; border-bottom: 2px solid #03c75a; padding-bottom: 10px; }}
            .update-time {{ text-align: right; color: #888; font-size: 0.9em; margin-bottom: 20px; }}
            .card {{ background: white; border-radius: 8px; padding: 15px; margin-bottom: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); transition: transform 0.2s; }}
            .card:hover {{ transform: translateY(-3px); }}
            .press {{ font-weight: bold; color: #03c75a; font-size: 0.9em; margin-bottom: 5px; display: block; }}
            a {{ text-decoration: none; color: #333; font-size: 1.1em; font-weight: bold; display: block; }}
            a:hover {{ color: #0056b3; }}
        </style>
    </head>
    <body>
        <h1>📰 오늘의 주요 사설</h1>
        <div class="update-time">업데이트: {update_time_str}</div>
        <div class="news-container">
    """
    for news in news_list:
        html_content += f"""
        <div class="card">
            <span class="press">{news['press']}</span>
            <a href="{news['link']}" target="_blank">{news['title']}</a>
        </div>
        """
    html_content += "</div></body></html>"
    return html_content

# --- 메인 실행 로직 ---
try:
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    all_uls = soup.find_all('ul')
    
    news_data = []
    seen_links = set() 

    for ul in all_uls:
        links = ul.find_all('a')
        article_links = [l for l in links if l.get('href') and '/article/' in l.get('href')]
        
        if not article_links:
            continue 

        items = ul.find_all('li')
        for item in items:
            try:
                a_tag = item.find('a')
                if not a_tag: continue
                
                link = a_tag['href']
                
                if link in seen_links: continue
                if '/article/' not in link: continue

                for tag in a_tag.find_all(['span', 'em']):
                    tag.decompose()
                
                press_tag = item.find(class_='press_name') or item.find('strong')
                press = press_tag.get_text(strip=True) if press_tag else "사설"
                
                raw_title = a_tag.get_text(strip=True)

                # 제목 정리 로직
                title = raw_title.replace('[사설]', '').strip()
                title = re.sub(r'\d+[시간분]전$', '', title).strip()
                if title.startswith(press):
                    title = title[len(press):].strip()
                title = title.lstrip('[] ')
                
                if len(title) > 2: 
                    news_data.append({'title': title, 'link': link, 'press': press})
                    seen_links.add(link) 
            except:
                continue

    if news_data:
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(create_html(news_data))
        
        send_telegram(news_data)

except Exception:
    pass
