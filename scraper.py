import requests
from bs4 import BeautifulSoup
import datetime
import os
import re

# --- 설정 ---
# 목표 변경: 최신 페이지 대신 '고전 리스트 페이지'를 공략합니다.
# sid1=110(오피니언), sid2=262(사설)
base_url = "https://news.naver.com/main/list.naver?mode=LS2D&mid=shm&sid1=110&sid2=262"
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

    today_str = datetime.datetime.now().strftime("%Y년 %m월 %d일")
    
    # 메시지 시작
    message = f"📰 {today_str} 주요 사설 요약\n"
    message += f"총 {len(news_list)}개의 사설을 모두 가져왔습니다.\n\n"
    
    current_message = message
    
    for news in news_list:
        news_item = f"[{news['press']}] {news['title']}\n{news['link']}\n\n"
        
        # 텔레그램 길이 제한 안전장치 (약 3500자로 설정)
        if len(current_message) + len(news_item) > 3500:
            try:
                send_url = f"https://api.telegram.org/bot{token}/sendMessage"
                data = {'chat_id': chat_id, 'text': current_message, 'disable_web_page_preview': True}
                requests.post(send_url, data=data)
                current_message = "" 
            except Exception as e:
                print(f"전송 중 에러: {e}")
        
        current_message += news_item
    
    # 마지막 내용 전송
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
    today_str = datetime.datetime.now().strftime("%Y년 %m월 %d일")
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>오늘의 사설 ({today_str})</title>
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

# --- 메인 실행 로직 (페이지 순회 방식) ---
try:
    # 오늘 날짜 (YYYYMMDD 형식)
    target_date = datetime.datetime.now().strftime("%Y%m%d")
    
    news_data = []
    seen_links = set() # 중복 제거용
    
    # 1페이지부터 5페이지까지 뒤집니다 (보통 하루 사설은 2~3페이지면 끝납니다)
    for page in range(1, 6):
        # 날짜와 페이지 번호를 넣어서 주소 완성
        target_url = f"{base_url}&date={target_date}&page={page}"
        print(f"탐색 중: {target_url}")
        
        response = requests.get(target_url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 리스트 영역 찾기
        list_body = soup.find('div', class_='list_body')
        if not list_body:
            break # 리스트가 없으면 종료
            
        items = list_body.find_all('li')
        
        # 더 이상 기사가 없으면 종료
        if not items:
            break
            
        found_new = False
        
        for item in items:
            try:
                # 링크와 제목 찾기 (dt 태그 안에 있음)
                dt_tags = item.find_all('dt')
                
                # dt가 2개인 경우(이미지+제목), 1개인 경우(제목만) 처리
                a_tag = None
                for dt in dt_tags:
                    if not dt.find('img'): # 이미지가 없는 dt가 진짜 제목
                        a_tag = dt.find('a')
                        break
                # 만약 위에서 못 찾았으면 첫번째 dt의 a를 씀
                if not a_tag and dt_tags:
                    a_tag = dt_tags[0].find('a')
                    
                if not a_tag: continue
                
                link = a_tag['href']
                title = a_tag.get_text(strip=True)
                
                # 중복 체크
                if link in seen_links:
                    continue
                    
                # 언론사 찾기 (dd 태그 안의 writing 클래스)
                press_tag = item.find('span', class_='writing')
                press = press_tag.get_text(strip=True) if press_tag else "사설"
                
                # 제목 정리 (언론사 이름 제거)
                if title.startswith(press):
                    title = title[len(press):].lstrip('[] ')
                if title.startswith(f"[{press}]"):
                    title = title[len(press)+2:].strip()

                news_data.append({'title': title, 'link': link, 'press': press})
                seen_links.add(link)
                found_new = True
                
            except Exception:
                continue
        
        # 이번 페이지에서 새로운 걸 하나도 못 찾았으면(마지막 페이지 도달) 종료
        if not found_new:
            break

    if news_data:
        # 파일 저장
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(create_html(news_data))
        print(f"총 {len(news_data)}개의 기사 저장 완료")
        
        # 텔레그램 전송
        send_telegram(news_data)
    else:
        print("기사를 찾지 못했습니다.")

except Exception as e:
    print(f"에러 발생: {e}")
