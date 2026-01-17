import requests
from bs4 import BeautifulSoup
import datetime
import os
import re # [추가] 제목 청소를 위한 도구

# --- 설정 ---
url = "https://news.naver.com/opinion/editorial"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# 텔레그램 전송 함수 (선생님이 좋아하시는 날짜 포맷 유지)
def send_telegram(news_list):
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('CHAT_ID')
    
    if not token or not chat_id:
        return

    # [선생님 취향] 오늘 날짜 헤더
    today = datetime.datetime.now().strftime("%Y년 %m월 %d일")
    
    message = f"📰 {today} 주요 사설 요약\n\n"
    
    # 메시지 내용 채우기
    for news in news_list:
        news_item = f"[{news['press']}] {news['title']}\n{news['link']}\n\n"
        
        # 4000자 넘으면 끊어서 보내기 (안전장치)
        if len(message) + len(news_item) > 3800:
            try:
                send_url = f"https://api.telegram.org/bot{token}/sendMessage"
                data = {'chat_id': chat_id, 'text': message, 'disable_web_page_preview': True}
                requests.post(send_url, data=data)
                message = "" # 초기화
            except: pass
        
        message += news_item
    
    # 마지막에 웹사이트 링크 추가
    message += "👉 웹에서 보기: https://chojh16.github.io/daily-editorial/"

    # 최종 발송
    try:
        send_url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {'chat_id': chat_id, 'text': message, 'disable_web_page_preview': True}
        requests.post(send_url, data=data)
    except: pass

# HTML 생성 함수
def create_html(news_list):
    today = datetime.datetime.now().strftime("%Y년 %m월 %d일")
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>오늘의 사설 ({today})</title>
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
        <div class="update-time">업데이트: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>
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
    
    # [수정 1] 특정 ul 하나만 찾는 게 아니라, 모든 ul을 다 검사합니다 (누락 방지)
    all_uls = soup.find_all('ul')
    
    news_data = []
    seen_links = set() 

    for ul in all_uls:
        # 기사 링크가 있는 목록인지 확인
        links = ul.find_all('a')
        # [수정 2] 3개 이상 조건 삭제 -> 1개라도 있으면 가져옴 (동아일보 등 하단 누락 방지)
        article_links = [l for l in links if l.get('href') and '/article/' in l.get('href')]
        
        if not article_links:
            continue 

        items = ul.find_all('li')
        for item in items:
            try:
                a_tag = item.find('a')
                if not a_tag: continue
                
                link = a_tag['href']
                
                # 필터링
                if link in seen_links: continue
                if '/article/' not in link: continue

                # 태그 청소
                for tag in a_tag.find_all(['span', 'em']):
                    tag.decompose()
                
                # 언론사 추출
                press_tag = item.find(class_='press_name') or item.find('strong')
                press = press_tag.get_text(strip=True) if press_tag else "사설"
                
                # 제목 추출
                raw_title = a_tag.get_text(strip=True)

                # [수정 3] 최신식 제목 청소 로직 적용
                # 1. [사설] 제거
                title = raw_title.replace('[사설]', '').strip()
                # 2. 맨 뒤 시간(22시간전) 제거 (re 모듈 사용)
                title = re.sub(r'\d+[시간분]전$', '', title).strip()
                # 3. 앞쪽 언론사 이름 중복 제거
                if title.startswith(press):
                    title = title[len(press):].strip()
                # 4. 특수문자 정리
                title = title.lstrip('[] ')
                
                if len(title) > 2: 
                    news_data.append({'title': title, 'link': link, 'press': press})
                    seen_links.add(link) 
            except:
                continue

    if news_data:
        # HTML 파일 만들기
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(create_html(news_data))
        
        # 텔레그램 보내기
        send_telegram(news_data)

except Exception:
    pass
