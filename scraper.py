import requests
from bs4 import BeautifulSoup
import datetime
import os
import re

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
    res = requests.get(target_url, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')
    
    news_data = []
    seen_links = set()
    all_items = soup.find_all('li')

    for item in all_items:
        try:
            # 1. 언론사 이름부터 확실하게 찾기 (press_name 클래스)
            press = ""
            press_span = item.find('span', class_='press_name')
            if press_span:
                press = press_span.get_text(strip=True)
            else:
                # 못 찾았으면 건너뛰거나, 비상용으로 '사설' 쓰지 말고 빈칸 처리 후 나중에 제목에서 추출 시도
                continue 

            # 2. 링크(a) 찾기
            a_tags = item.find_all('a')
            target_a = None
            for a in a_tags:
                href = a.get('href', '')
                if href and '/article/' in href:
                    target_a = a
                    break
            
            if not target_a: continue
            
            # [중요] a 태그 안에서 시간 정보나 언론사 이름이 또 들어있으면 미리 삭제
            # (이게 없어서 제목이랑 시간이랑 떡져서 나왔던 것임)
            for tag in target_a.find_all(['span', 'em']):
                tag.decompose() # 태그 삭제

            link = target_a['href']
            
            # 3. 제목 추출 (순수 텍스트만)
            raw_title = target_a.get_text(strip=True)
            
            # --- [강력한 제목 청소 시간] ---
            
            # (1) [사설] 제거
            title = raw_title.replace('[사설]', '').strip()
            
            # (2) 제목 맨 앞에 언론사 이름이 붙어있으면 떼어내기 (예: "서울경제낙관론..." -> "낙관론...")
            if title.startswith(press):
                title = title[len(press):].strip()
            
            # (3) 제목 맨 뒤에 시간(22시간전)이 붙어있으면 정규식으로 잘라내기
            title = re.sub(r'\d+[시간분]전$', '', title).strip()
            
            # (4) 혹시 모를 대괄호 정리
            title = title.lstrip('[] ')
            
            if not title: continue
            if link in seen_links: continue

            news_data.append({'title': title, 'link': link, 'press': press})
            seen_links.add(link)
            
        except: continue

    if news_data:
        # 파일 저장
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(create_html(news_data))
        
        # 텔레그램 전송
        current_msg = ""
        for news in news_data:
            # [서울경제] 제목 형태로 출력
            line = f"[{news['press']}] {news['title']}\n{news['link']}\n\n"
            
            if len(current_msg) + len(line) > 3500:
                send_msg(current_msg)
                current_msg = ""
            current_msg += line
            
        current_msg += f"👉 웹에서 보기: https://chojh16.github.io/daily-editorial/"
        send_msg(current_msg)

except Exception:
    pass
