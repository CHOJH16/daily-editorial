import requests
from bs4 import BeautifulSoup
import datetime
import os
import time

# --- 설정 ---
# 네이버 뉴스의 '고전 리스트 페이지' (페이지 번호가 있어서 크롤링이 확실함)
# sid1=110(오피니언), sid2=262(사설)
base_url = "https://news.naver.com/main/list.naver?mode=LS2D&mid=shm&sid1=110&sid2=262"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def send_telegram(news_list):
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('CHAT_ID')
    
    if not token or not chat_id:
        print("텔레그램 설정이 없습니다.")
        return

    today_str = datetime.datetime.now().strftime("%Y년 %m월 %d일")
    message = f"📰 {today_str} 주요 사설 요약\n"
    message += f"총 {len(news_list)}개의 사설을 수집했습니다.\n\n"
    
    current_message = message
    
    for news in news_list:
        news_item = f"[{news['press']}] {news['title']}\n{news['link']}\n\n"
        
        # 텔레그램 메시지 길이 제한 안전장치
        if len(current_message) + len(news_item) > 3500:
            try:
                send_url = f"https://api.telegram.org/bot{token}/sendMessage"
                data = {'chat_id': chat_id, 'text': current_message, 'disable_web_page_preview': True}
                requests.post(send_url, data=data)
                current_message = ""
            except Exception as e:
                print(f"전송 중 에러: {e}")
        
        current_message += news_item
    
    current_message += "👉 웹에서 보기: https://chojh16.github.io/daily-editorial/"
    
    try:
        send_url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {'chat_id': chat_id, 'text': current_message, 'disable_web_page_preview': True}
        requests.post(send_url, data=data)
        print("텔레그램 전송 완료")
    except Exception as e:
        print(f"텔레그램 전송 실패: {e}")

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

# --- 메인 실행 로직 ---
try:
    # 오늘 날짜 (YYYYMMDD) - 이 날짜의 기사만 가져옵니다.
    target_date = datetime.datetime.now().strftime("%Y%m%d")
    
    news_data = []
    seen_links = set()
    
    print(f"[{target_date}] 크롤링 시작...")
    
    # 1페이지부터 5페이지까지 탐색
    for page in range(1, 6):
        target_url = f"{base_url}&date={target_date}&page={page}"
        print(f"페이지 {page} 탐색 중: {target_url}")
        
        try:
            response = requests.get(target_url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 메인 리스트 영역 찾기
            main_content = soup.find('div', id='main_content')
            if not main_content:
                print("메인 콘텐츠를 찾을 수 없습니다.")
                break
                
            # 리스트 안의 모든 기사 덩어리(li) 찾기
            items = main_content.find_all('li')
            
            if not items:
                print("기사가 더 이상 없습니다.")
                break
            
            found_in_page = 0
            
            for item in items:
                # 링크(a)와 제목 찾기
                # 보통 dt 태그 안에 있거나, dl 없이 바로 a가 있을 수도 있음
                a_tags = item.find_all('a')
                valid_a = None
                
                for a in a_tags:
                    # 텍스트가 있고, href가 있는 a 태그 찾기
                    if a.get_text(strip=True) and a.get('href'):
                        valid_a = a
                        break
                
                if not valid_a: continue
                
                link = valid_a['href']
                title = valid_a.get_text(strip=True)
                
                # 중복 및 비기사 필터링
                if link in seen_links: continue
                if '/article/' not in link and '/read.nhn' not in link: continue
                
                # 언론사 이름 찾기 (span class="writing")
                press_span = item.find('span', class_='writing')
                press = press_span.get_text(strip=True) if press_span else "사설"
                
                # 제목 정리
                if title.startswith(press):
                    title = title[len(press):].lstrip('[] ')
                
                news_data.append({'title': title, 'link': link, 'press': press})
                seen_links.add(link)
                found_in_page += 1
                
            print(f" -> {found_in_page}개 발견")
            
            # 페이지 로딩 매너 지키기
            time.sleep(0.5)
            
        except Exception as e:
            print(f"페이지 {page} 처리 중 에러: {e}")
            continue

    if news_data:
        # 파일 저장
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(create_html(news_data))
        print(f"최종 저장 완료: {len(news_data)}개")
        
        # 텔레그램 전송
        send_telegram(news_data)
    else:
        print("수집된 기사가 없습니다.")

except Exception as e:
    print(f"치명적 에러 발생: {e}")
