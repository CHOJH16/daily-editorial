import requests
from bs4 import BeautifulSoup
import datetime
import os

# --- 설정 ---
url = "https://news.naver.com/opinion/editorial"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# 텔레그램 전송 함수 (새로 추가된 기능)
def send_telegram(news_list):
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('CHAT_ID')
    
    if not token or not chat_id:
        print("텔레그램 설정이 없습니다. (GitHub Secrets를 확인하세요)")
        return

    # 오늘 날짜
    today = datetime.datetime.now().strftime("%Y년 %m월 %d일")
    
    # 메시지 만들기
    message = f"📰 {today} 주요 사설 요약\n\n"
    
    for news in news_list:
        # 제목과 링크를 깔끔하게 정리해서 메시지에 추가
        message += f"[{news['press']}] {news['title']}\n"
        message += f"{news['link']}\n\n"
    
    # 내 웹사이트 링크도 마지막에 추가
    message += "👉 웹에서 보기: https://chojh16.github.io/daily-editorial/"

    # 텔레그램 서버로 발송 요청
    send_url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {'chat_id': chat_id, 'text': message, 'disable_web_page_preview': True}
    
    try:
        response = requests.post(send_url, data=data)
        print(f"텔레그램 전송 결과: {response.status_code}")
    except Exception as e:
        print(f"텔레그램 전송 실패: {e}")

# HTML 생성 함수 (기존 기능 유지)
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
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    
    candidates = soup.find_all('ul')
    target_ul = None
    max_links = 0
    for ul in candidates:
        links = ul.find_all('a')
        count = sum(1 for a in links if a.get('href') and '/article/' in a.get('href'))
        if count > max_links:
            max_links = count
            target_ul = ul
            
    news_data = []
    if target_ul:
        items = target_ul.find_all('li')
        for item in items:
            try:
                a_tag = item.find('a')
                if not a_tag: continue
                
                # 시간 태그 제거
                time_tag = a_tag.find('span', class_='time')
                if time_tag: time_tag.decompose()
                
                # 언론사 추출
                press_tag = item.find(class_='press_name') or item.find('strong')
                press = press_tag.get_text(strip=True) if press_tag else "사설"
                
                # 제목 추출 및 정리
                title = a_tag.get_text(strip=True)
                if title.startswith(press):
                    title = title[len(press):].lstrip('[] ')
                
                link = a_tag['href']
                if len(title) > 5: 
                    news_data.append({'title': title, 'link': link, 'press': press})
            except Exception:
                continue

    if news_data:
        # 1. HTML 파일 만들기
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(create_html(news_data))
        print(f"파일 저장 완료: {len(news_data)}개")
        
        # 2. 텔레그램 보내기 (여기가 핵심!)
        send_telegram(news_data)
        
    else:
        print("기사를 찾지 못했습니다.")

except Exception as e:
    print(f"에러 발생: {e}")
