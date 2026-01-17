import requests
from bs4 import BeautifulSoup
import datetime
import os

# 1. 네이버 사설 페이지 접속 설정
url = "https://news.naver.com/opinion/editorial"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def create_html(news_list):
    # 오늘 날짜
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
        
    html_content += """
        </div>
    </body>
    </html>
    """
    return html_content

try:
    # 2. 페이지 내용 가져오기
    response = requests.get(url, headers=headers)
    response.raise_for_status() # 접속 에러 시 중단
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 3. 사설 목록 찾기
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
                
                # [개선 1] 시간 정보를 담은 태그를 미리 제거
                time_tag = a_tag.find('span', class_='time')
                if time_tag:
                    time_tag.decompose()
                
                # 언론사 이름 찾기
                press_tag = item.find(class_='press_name') or item.find('strong')
                press = press_tag.get_text(strip=True) if press_tag else "사설"
                
                # 제목 텍스트 추출 (이제 시간 정보가 없음)
                title = a_tag.get_text(strip=True)
                
                # [개선 2] 제목이 언론사 이름으로 시작하면 중복 제거
                if title.startswith(press):
                    title = title[len(press):].lstrip('[] ') # '한국경제[사설]...' 같은 경우 앞의 '한국경제'와 괄호, 공백까지 제거

                link = a_tag['href']
                
                if len(title) > 5: 
                    news_data.append({'title': title, 'link': link, 'press': press})
            except Exception as e:
                continue

    # 4. index.html 파일 저장
    if news_data:
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(create_html(news_data))
        print(f"성공: {len(news_data)}개의 기사를 저장했습니다.")
    else:
        print("경고: 기사를 찾지 못했습니다. 네이버 페이지 구조가 바뀌었을 수 있습니다.")

except Exception as e:
    print(f"에러 발생: {e}")
