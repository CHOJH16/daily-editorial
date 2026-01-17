import requests
from bs4 import BeautifulSoup
import datetime
import os
import re  # 텍스트 정리를 위한 도구 추가

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
            # 1. 링크 찾기
            a_tags = item.find_all('a')
            target_a = None
            for a in a_tags:
                href = a.get('href', '')
                if href and '/article/' in href:
                    target_a = a
                    break
            
            if not target_a: continue

            # 2. 제목 추출 전, 시간 태그가 섞여있다면 제거 (HTML 구조상)
            # (혹시 a태그 안에 span class='time' 같은게 있으면 미리 지움)
            for tag in target_a.find_all(True):
                if 'time' in tag.get('class', []) or 'date' in tag.get('class', []):
                    tag.decompose()

            link = target_a['href']
            raw_title = target_a.get_text(strip=True)
            
            if not raw_title: continue
            if link in seen_links: continue

            # 3. 언론사 이름 찾기
            press = "사설"
            press_span = item.find('span', class_='press_name')
            if not press_span:
                press_span = item.find('span', class_='writing')
            
            if press_span:
                press = press_span.get_text(strip=True)
            
            # --- [핵심 수정] 제목 대수술 ---
            
            # (1) [사설] 문구 강제 삭제
            title = raw_title.replace('[사설]', '').strip()
            
            # (2) 맨 뒤에 붙은 시간(22시간전, 5분전 등) 강제 삭제 (정규표현식 사용)
            # "숫자" + "시간" or "분" + "전"으로 끝나는 패턴을 찾아서 지움
            title = re.sub(r'\d+[시간분]전$', '', title).strip()
            
            # (3) 제목 앞에 언론사 이름이 또 있으면 삭제 (예: "동아일보 [사설]..." -> "...")
            if title.startswith(press):
                title = title[len(press):].strip()
            
            # (4) 혹시 남은 대괄호 [] 정리
            title = title.lstrip('[] ')
            
            # ---------------------------

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
            # 요청하신 포맷: [언론사] 제목 (시간, 사설 태그 없음)
            line = f"[{news['press']}] {news['title']}\n{news['link']}\n\n"
            
            if len(current_msg) + len(line) > 3500:
                send_msg(current_msg)
                current_msg = ""
            current_msg += line
            
        current_msg += f"👉 웹에서 보기: https://chojh16.github.io/daily-editorial/"
        send_msg(current_msg)

except Exception:
    pass
