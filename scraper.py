import requests
from bs4 import BeautifulSoup
import datetime
import os
import time

# --- 설정 ---
# 네이버 뉴스 사설 리스트 페이지
target_url_base = "https://news.naver.com/main/list.naver?mode=LS2D&mid=shm&sid1=110&sid2=262"
headers = {
    # 봇 차단을 막기 위한 일반 사용자 위장 헤더
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
}

def send_msg(text):
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('CHAT_ID')
    if not token or not chat_id: return
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {'chat_id': chat_id, 'text': text, 'disable_web_page_preview': True}
        requests.post(url, data=data)
    except: pass

def create_html(news_list):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    html = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>오늘의 사설</title>
        <style>
            body {{ font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
            h1 {{ border-bottom: 2px solid #03c75a; padding-bottom: 10px; }}
            .card {{ border: 1px solid #ddd; padding: 15px; margin-bottom: 10px; border-radius: 5px; }}
            a {{ text-decoration: none; color: #333; font-weight: bold; font-size: 1.1em; }}
            .press {{ color: #03c75a; font-weight: bold; font-size: 0.9em; }}
        </style>
    </head>
    <body>
        <h1>📰 오늘의 주요 사설</h1>
        <p style="text-align:right">업데이트: {now} (총 {len(news_list)}개)</p>
    """
    for news in news_list:
        html += f"<div class='card'><span class='press'>{news['press']}</span><br><a href='{news['link']}' target='_blank'>{news['title']}</a></div>"
    html += "</body></html>"
    return html

# === 메인 로직 ===
try:
    print("🚀 로봇 시작")
    # 시작 메시지는 생략 (너무 시끄러울 수 있어서)

    news_data = []
    seen_links = set()

    # 1페이지 ~ 3페이지 탐색
    for page in range(1, 4):
        url = f"{target_url_base}&page={page}"
        print(f"접속: {url}")
        
        res = requests.get(url, headers=headers)
        # HTML 텍스트 전체를 가져옵니다.
        soup = BeautifulSoup(res.text, 'html.parser')

        # [핵심 변경] 특정 클래스(ul.type06)를 찾지 않습니다.
        # 페이지 내의 '모든' a 태그를 다 가져와서 검사합니다.
        all_links = soup.find_all('a')
        
        found_count = 0
        
        for a in all_links:
            try:
                link = a.get('href', '')
                title = a.get_text(strip=True)
                
                # 1. 링크가 없거나 제목이 없으면 패스
                if not link or not title: continue
                
                # 2. 링크 주소에 '/article/' (기사 패턴)이 없으면 패스
                if '/article/' not in link: continue
                
                # 3. 이미 저장한 링크면 패스
                if link in seen_links: continue
                
                # 4. 언론사 이름 찾기 (약간의 추측 로직)
                # a 태그 근처의 상위 태그(li)에서 writing 클래스를 찾음
                press = "사설"
                parent_li = a.find_parent('li')
                if parent_li:
                    press_span = parent_li.find('span', class_='writing')
                    if press_span:
                        press = press_span.get_text(strip=True)
                
                # 5. 제목 정리
                if title.startswith(press):
                    title = title[len(press):].lstrip('[] ')
                
                news_data.append({'title': title, 'link': link, 'press': press})
                seen_links.add(link)
                found_count += 1
                
            except: continue
            
        print(f" -> {found_count}개 발견")
        time.sleep(0.5)

    if news_data:
        # 파일 저장
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(create_html(news_data))
        
        # 텔레그램 전송 (최대 3500자씩 끊어서 전송)
        msg_header = f"📰 수집 성공! 총 {len(news_data)}개\n\n"
        current_msg = msg_header
        
        for news in news_data:
            line = f"[{news['press']}] {news['title']}\n{news['link']}\n\n"
            if len(current_msg) + len(line) > 3500:
                send_msg(current_msg)
                current_msg = ""
            current_msg += line
            
        current_msg += f"👉 https://chojh16.github.io/daily-editorial/"
        send_msg(current_msg)
        
    else:
        # [디버깅용] 만약 이번에도 실패하면 네이버가 뭘 보여줬는지 글자수라도 찍어봄
        debug_info = f"❌ 실패.. (페이지 응답 길이: {len(res.text)}자)"
        send_msg(debug_info)

except Exception as e:
    send_msg(f"🔥 에러 발생: {e}")
    exit(1)
