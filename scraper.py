import requests
from bs4 import BeautifulSoup
import datetime
import os

# --- 설정 ---
target_url = "https://news.naver.com/opinion/editorial"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
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
    # 1. 페이지 접속
    res = requests.get(target_url, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')
    
    news_data = []
    seen_links = set()

    # 2. 기사 추출 (페이지에 보이는 모든 li 태그 검사)
    all_items = soup.find_all('li')

    for item in all_items:
        try:
            # 링크(a) 찾기
            a_tags = item.find_all('a')
            target_a = None
            
            # href에 '/article/'이 있는 진짜 기사 링크만 찾음
            for a in a_tags:
                href = a.get('href', '')
                if href and '/article/' in href:
                    target_a = a
                    break
            
            if not target_a: continue

            link = target_a['href']
            title = target_a.get_text(strip=True)
            
            if not title: continue
            if link in seen_links: continue

            # 언론사 이름 찾기
            press = "사설"
            press_span = item.find('span', class_='press_name')
            if not press_span:
                press_span = item.find('span', class_='writing')
            
            if press_span:
                press = press_span.get_text(strip=True)
            
            # 제목 정리 (앞에 언론사 이름 중복 제거)
            if title.startswith(press):
                title = title[len(press):].lstrip('[] ')
            if title.startswith(f"[{press}]"):
                title = title[len(press)+2:].strip()

            news_data.append({'title': title, 'link': link, 'press': press})
            seen_links.add(link)
            
        except: continue

    if news_data:
        # 파일 저장
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(create_html(news_data))
        
        # 텔레그램 전송 (군더더기 없이 깔끔하게)
        # 메시지 시작 부분에 아무런 멘트 없이 바로 기사부터 나옵니다.
        current_msg = ""
        
        for news in news_data:
            # 요청하신 깔끔한 포맷
            line = f"[{news['press']}] {news['title']}\n{news['link']}\n\n"
            
            # 길이가 길어지면 잘라서 보내기
            if len(current_msg) + len(line) > 3500:
                send_msg(current_msg)
                current_msg = ""
            current_msg += line
            
        # 마지막에 웹 링크만 하나 딱 붙여줍니다.
        current_msg += f"👉 웹에서 보기: https://chojh16.github.io/daily-editorial/"
        send_msg(current_msg)

except Exception:
    pass # 에러가 나도 조용히 종료 (필요하면 주석 제거)
