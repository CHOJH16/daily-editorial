import requests
from bs4 import BeautifulSoup
import datetime
import os

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
        print("텔레그램 설정이 없습니다.")
        return

    today = datetime.datetime.now().strftime("%Y년 %m월 %d일")
    
    # 메시지 헤더
    message = f"📰 {today} 주요 사설 요약\n"
    message += f"총 {len(news_list)}개의 사설을 찾았습니다.\n\n"
    
    # 메시지가 너무 길어질 경우를 대비해 나눠서 보낼 준비
    # 텔레그램은 한 번에 약 4096자까지만 보낼 수 있음
    current_message = message
    
    for news in news_list:
        # 각 뉴스 항목 생성
        news_item = f"[{news['press']}] {news['title']}\n{news['link']}\n\n"
        
        # 길이가 넘치면 먼저 보내고 새로 시작
        if len(current_message) + len(news_item) > 4000:
            try:
                send_url = f"https://api.telegram.org/bot{token}/sendMessage"
                data = {'chat_id': chat_id, 'text': current_message, 'disable_web_page_preview': True}
                requests.post(send_url, data=data)
                current_message = "" # 초기화
            except Exception as e:
                print(f"전송 중 에러: {e}")
        
        current_message += news_item
    
    # 웹사이트 링크 추가 및 마지막 메시지 전송
    current_message += "👉 웹에서 보기: https://chojh16.github.io/daily-editorial/"
    
    try:
        send_url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {'chat_id': chat_id, 'text': current_message, 'disable_web_page_preview': True}
        requests.post(send_url, data=data)
        print("텔레그램 전송 완료")
    except Exception as e:
        print(f"텔레그램 전송 실패: {e}")

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
            .count {{ text-align: center; color: #555; margin-bottom: 20px; font-weight: bold; }}
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
        <div class="count">총 {len(news_list)}개의 기사를 수집했습니다.</div>
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
    
    # [수정된 부분] 
    # 특정 ul 하나만 찾는 게 아니라, 페이지 내의 모든 ul을 검사합니다.
    all_uls = soup.find_all('ul')
    
    news_data = []
    seen_links = set() # 중복 기사 방지용 (같은 링크가 두 번 나오면 무시)

    for ul in all_uls:
        # 이 목록(ul) 안에 기사 링크(/article/)가 3개 이상 들어있는지 확인
        # (메뉴나 푸터 같은 쓸데없는 목록을 거르기 위함)
        links = ul.find_all('a')
        article_links = [l for l in links if l.get('href') and '/article/' in l.get('href')]
        
        if len(article_links) < 3:
            continue # 기사 목록이 아닌 것 같으니 패스

        # 기사 목록이 맞다면 하나씩 뜯어봄
        items = ul.find_all('li')
        for item in items:
            try:
                a_tag = item.find('a')
                if not a_tag: continue
                
                link = a_tag['href']
                
                # 이미 저장한 링크면 건너뜀 (중복 방지)
                if link in seen_links:
                    continue
                
                # 필터링: 링크 주소에 '/article/'이 없으면 기사가 아님
                if '/article/' not in link:
                    continue

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
                
                if len(title) > 5: 
                    news_data.append({'title': title, 'link': link, 'press': press})
                    seen_links.add(link) # 저장했다고 표시
            except Exception:
                continue

    if news_data:
        # 1. HTML 파일 만들기
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(create_html(news_data))
        print(f"파일 저장 완료: {len(news_data)}개")
        
        # 2. 텔레그램 보내기
        send_telegram(news_data)
        
    else:
        print("기사를 찾지 못했습니다.")

except Exception as e:
    print(f"에러 발생: {e}")
