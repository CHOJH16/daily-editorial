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
    
    current_message = message
    
    for news in news_list:
        news_item = f"[{news['press']}] {news['title']}\n{news['link']}\n\n"
        
        # 텔레그램 글자수 제한(4096자) 방지: 길면 끊어서 보내기
        if len(current_message) + len(news_item) > 3800:
            try:
                send_url = f"https://api.telegram.org/bot{token}/sendMessage"
                data = {'chat_id': chat_id, 'text': current_message, 'disable_web_page_preview': True}
                requests.post(send_url, data=data)
                current_message = "" 
            except Exception as e:
                print(f"전송 중 에러: {e}")
        
        current_message += news_item
    
    # 마지막 조각 전송
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

# --- 메인 실행 로직 (개선된 부분) ---
try:
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    
    news_data = []
    seen_links = set() # 중복 방지용

    # [핵심 변경] ul 태그를 찾지 않습니다. 
    # 페이지 전체에서 'li' 태그를 모두 긁어온 뒤, 기사인지 하나하나 검사합니다.
    all_items = soup.find_all('li')
    
    for item in all_items:
        try:
            a_tag = item.find('a')
            if not a_tag: continue
            
            link = a_tag.get('href', '')
            
            # 1. 링크가 뉴스 기사 형식이 아니면 가차없이 버림
            if '/article/' not in link:
                continue
            
            # 2. 이미 저장한 기사면 패스 (중복 제거)
            if link in seen_links:
                continue

            # 3. 제목 추출
            title = a_tag.get_text(strip=True)
            if len(title) < 4: # 제목이 너무 짧으면(아이콘 등) 버림
                continue

            # 4. 언론사 추출 (여러가지 케이스 대응)
            press = "사설" # 기본값
            press_tag = item.find(class_='press_name')
            if not press_tag:
                press_tag = item.find('strong')
            
            if press_tag:
                press = press_tag.get_text(strip=True)
            else:
                # 태그가 없으면 제목 앞에 [언론사]가 있는지 확인 시도
                pass

            # 5. 시간 태그 제거 (제목 안에 시간이 섞여있을 경우)
            time_tag = a_tag.find('span', class_='time')
            if time_tag: time_tag.decompose()
            # 다시 제목 추출 (시간 제거 후)
            title = a_tag.get_text(strip=True)

            # 6. 제목 정리 (언론사 이름 중복 제거)
            if title.startswith(press):
                title = title[len(press):].lstrip('[] ')

            news_data.append({'title': title, 'link': link, 'press': press})
            seen_links.add(link)

        except Exception:
            continue

    if news_data:
        # 파일 저장
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(create_html(news_data))
        print(f"저장 완료: {len(news_data)}개")
        
        # 텔레그램 전송
        send_telegram(news_data)
    else:
        print("기사를 하나도 못 찾았습니다. (코드 확인 필요)")

except Exception as e:
    print(f"에러 발생: {e}")
