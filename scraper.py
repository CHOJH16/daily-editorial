import requests
from bs4 import BeautifulSoup
import datetime
import os
import re # 제목 정리를 위한 도구

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
        return # 설정 없으면 조용히 종료

    # 메시지 작성 (군더더기 없이 깔끔하게)
    current_message = ""
    
    for news in news_list:
        # [언론사] 제목
        # 링크
        news_item = f"[{news['press']}] {news['title']}\n{news['link']}\n\n"
        
        # 길이가 넘치면 먼저 보내고 새로 시작 (4000자 제한 안전장치)
        if len(current_message) + len(news_item) > 3500:
            try:
                send_url = f"https://api.telegram.org/bot{token}/sendMessage"
                data = {'chat_id': chat_id, 'text': current_message, 'disable_web_page_preview': True}
                requests.post(send_url, data=data)
                current_message = "" 
            except: pass
        
        current_message += news_item
    
    # 웹사이트 링크 추가 및 마지막 메시지 전송
    current_message += "👉 웹에서 보기: https://chojh16.github.io/daily-editorial/"
    
    try:
        send_url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {'chat_id': chat_id, 'text': current_message, 'disable_web_page_preview': True}
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
        <title>오늘의 사설</title>
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
    
    # 선생님이 신뢰하시는 '모든 ul 찾기' 방식
    all_uls = soup.find_all('ul')
    
    news_data = []
    seen_links = set()

    for ul in all_uls:
        # [중요 수정 1] 기사가 1개라도 있으면 가져오도록 수정 (누락 방지)
        links = ul.find_all('a')
        article_links = [l for l in links if l.get('href') and '/article/' in l.get('href')]
        
        if len(article_links) == 0:
            continue 

        items = ul.find_all('li')
        for item in items:
            try:
                a_tag = item.find('a')
                if not a_tag: continue
                
                link = a_tag['href']
                if link in seen_links: continue
                if '/article/' not in link: continue

                # 태그 청소 (시간 태그 등 미리 삭제)
                for tag in a_tag.find_all(['span', 'em']):
                    tag.decompose()
                
                # 언론사 추출
                press_tag = item.find(class_='press_name') or item.find('strong')
                press = press_tag.get_text(strip=True) if press_tag else "사설"
                
                # 제목 추출
                raw_title = a_tag.get_text(strip=True)

                # [중요 수정 2] 제목 깔끔하게 만들기
                # 1. [사설] 제거
                title = raw_title.replace('[사설]', '').strip()
                # 2. 맨 뒤 시간(22시간전) 제거
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
        # 1. HTML 파일 만들기
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(create_html(news_data))
        
        # 2. 텔레그램 보내기
        send_telegram(news_data)

except Exception:
    pass
