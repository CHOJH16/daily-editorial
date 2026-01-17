import requests
from bs4 import BeautifulSoup
import datetime
import os

# --- 설정 ---
# 선생님이 지정하신 바로 그 주소
target_url = "https://news.naver.com/opinion/editorial"

headers = {
    # 로봇이 아닌 척하기 위한 신분증 (필수)
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
    print(f"🚀 접속 시도: {target_url}")
    
    # 1. 페이지 접속
    res = requests.get(target_url, headers=headers)
    
    if res.status_code != 200:
        send_msg(f"❌ 페이지 접속 실패 (코드: {res.status_code})")
        exit(1)

    # 2. HTML 해석
    soup = BeautifulSoup(res.text, 'html.parser')
    
    news_data = []
    seen_links = set()

    # 3. 사설 목록 찾기
    # 네이버 사설 페이지의 기사들은 'ul' 태그 안에 'li'로 들어있습니다.
    # 특정 클래스 이름을 찾지 않고, 페이지 내의 모든 'li' 태그를 검사해서 기사인지 확인합니다.
    all_items = soup.find_all('li')
    
    print(f"  -> 페이지 내 항목 {len(all_items)}개 검사 중...")

    for item in all_items:
        try:
            # 기사 링크(a) 찾기
            # a 태그 중에 href가 있고, 그 주소에 '/article/'이 들어간 것만 찾음
            a_tags = item.find_all('a')
            target_a = None
            
            for a in a_tags:
                href = a.get('href', '')
                if href and '/article/' in href:
                    target_a = a
                    break
            
            if not target_a: continue

            link = target_a['href']
            title = target_a.get_text(strip=True)
            
            # 썸네일 이미지(img 태그)만 있는 a태그인 경우 제목이 비어있을 수 있음
            if not title: continue
            
            # 이미 저장한 링크면 패스
            if link in seen_links: continue

            # 언론사 이름 찾기
            # 보통 span 태그에 클래스 이름이 'press' 어쩌구로 되어있음
            press = "사설"
            press_span = item.find('span', class_='press_name')
            if not press_span:
                press_span = item.find('span', class_='writing')
            
            if press_span:
                press = press_span.get_text(strip=True)
            
            # 제목 정리 (언론사 이름 중복 제거)
            if title.startswith(press):
                title = title[len(press):].lstrip('[] ')
            if title.startswith(f"[{press}]"):
                title = title[len(press)+2:].strip()

            news_data.append({'title': title, 'link': link, 'press': press})
            seen_links.add(link)
            
        except: continue

    print(f"✅ 유효한 사설 {len(news_data)}개 발견")

    if news_data:
        # 파일 저장
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(create_html(news_data))
        
        # 텔레그램 전송
        msg_header = f"📰 수집 성공! 총 {len(news_data)}개\n(요청하신 페이지 원본)\n\n"
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
        # HTML은 가져왔는데 기사를 못 찾은 경우 (네이버가 봇을 막았거나 페이지 구조가 텅 빈 경우)
        # 디버깅을 위해 HTML 길이 정보를 보냄
        send_msg(f"❌ 기사를 못 찾았습니다.\n페이지 내용 길이: {len(res.text)}자\n(봇 차단 가능성 있음)")

except Exception as e:
    send_msg(f"🔥 에러 발생: {e}")
    exit(1)
