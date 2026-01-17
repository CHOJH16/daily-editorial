import requests
import datetime
import os
import time

# --- 설정 ---
# 선생님이 원하시는 'https://news.naver.com/opinion/editorial' 페이지가
# 실제로 데이터를 가져오는 '비밀 창고(API)' 주소입니다.
# pageNo만 바꾸면 모든 사설을 다 가져올 수 있습니다.
target_api_url = "https://news.naver.com/opinion/api/editorial"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    # 이 페이지에서 왔다고 거짓말을 해야 네이버가 데이터를 줍니다.
    "Referer": "https://news.naver.com/opinion/editorial"
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
    print("🚀 로봇 시작 (API 모드)")
    
    news_data = []
    seen_ids = set()

    # 1페이지 ~ 3페이지 탐색 (API는 1페이지당 20개씩 줍니다. 3페이지면 60개로 충분)
    for page in range(1, 4):
        # API 요청 파라미터 (네이버가 요구하는 규칙)
        params = {
            'pageNo': page
        }
        
        print(f"📡 데이터 창고 접속 중 (페이지 {page})...")
        
        # HTML이 아니라 JSON 데이터로 요청
        res = requests.get(target_api_url, headers=headers, params=params)
        
        # 데이터가 정상인지 확인
        if res.status_code != 200:
            print(f"❌ 접속 실패: {res.status_code}")
            continue

        # JSON 봉투 뜯기
        data = res.json()
        
        # 기사 목록 꺼내기 (구조: result > articleList)
        articles = data.get('result', {}).get('articleList', [])
        
        if not articles:
            print("  ⚠️ 더 이상 기사가 없습니다.")
            break
            
        print(f"  -> {len(articles)}개의 데이터 발견")

        for item in articles:
            try:
                # API가 주는 정보들 추출
                title = item.get('title', '')
                press = item.get('pressName', '사설')
                # 기사 ID로 링크 만들기
                article_id = item.get('articleId')
                office_id = item.get('pressId')
                
                if not article_id or not office_id: continue
                
                link = f"https://n.news.naver.com/mnews/article/{office_id}/{article_id}"
                
                # 중복 제거
                if link in seen_ids: continue
                
                # 제목 정리 (이미 깔끔하게 오지만 혹시 몰라 추가)
                # API 데이터는 보통 제목에 [사설] 같은 걸 포함하지 않고 깔끔하게 줍니다.
                # 그래도 혹시 모르니 정리 로직 유지
                if title.startswith(press):
                    title = title[len(press):].lstrip('[] ')

                news_data.append({'title': title, 'link': link, 'press': press})
                seen_ids.add(link)
                
            except: continue
            
        time.sleep(0.5)

    print(f"✅ 총 {len(news_data)}개의 진짜 사설 수집 완료")

    if news_data:
        # 파일 저장
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(create_html(news_data))
        
        # 텔레그램 전송
        msg_header = f"📰 수집 성공! 총 {len(news_data)}개\n(순수 사설 데이터)\n\n"
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
        send_msg("❌ 수집된 데이터가 없습니다. (API 주소 확인 필요)")

except Exception as e:
    send_msg(f"🔥 에러 발생: {e}")
    exit(1)
