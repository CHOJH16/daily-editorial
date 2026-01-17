import requests
from bs4 import BeautifulSoup
import datetime
import os
import time

# --- 설정 ---
# 네이버 뉴스 사설 리스트 페이지 (페이지 번호로 접근 가능)
target_url_base = "https://news.naver.com/main/list.naver?mode=LS2D&mid=shm&sid1=110&sid2=262"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def send_msg(text):
    """텔레그램 메시지 전송 함수"""
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('CHAT_ID')
    
    if not token or not chat_id:
        print("❌ [오류] 텔레그램 설정(TOKEN, CHAT_ID)이 없습니다.")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        data = {'chat_id': chat_id, 'text': text, 'disable_web_page_preview': True}
        requests.post(url, data=data)
    except Exception as e:
        print(f"❌ [오류] 텔레그램 전송 실패: {e}")

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

# === 메인 실행 로직 ===
try:
    print("🚀 로봇 시작!")
    # [진단 1] 로봇이 깨어났음을 알림
    send_msg("🤖 로봇이 작업을 시작했습니다.\n(이 메시지가 오면 설정은 정상입니다.)")

    news_data = []
    seen_links = set()

    # 1페이지 ~ 3페이지 탐색 (약 60개 기사)
    for page in range(1, 4):
        url = f"{target_url_base}&page={page}"
        print(f"📡 {page}페이지 접속 중: {url}")
        
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')

        # 네이버 리스트 페이지 구조: ul.type06_headline 과 ul.type06 안에 기사가 있음
        # 이 두 종류의 ul 안에 있는 모든 li를 찾음
        articles = soup.select('ul.type06_headline li') + soup.select('ul.type06 li')
        
        print(f"   -> {len(articles)}개의 항목 발견")

        for item in articles:
            try:
                # dl 태그 안에 dt(제목/이미지), dd(내용)가 있음
                dt_tags = item.find_all('dt')
                a_tag = None
                
                # dt가 2개면(이미지 포함), 두 번째 dt에 제목이 있음. 1개면 바로 제목.
                if len(dt_tags) == 2:
                    a_tag = dt_tags[1].find('a')
                elif len(dt_tags) == 1:
                    a_tag = dt_tags[0].find('a')
                
                if not a_tag: continue

                link = a_tag['href']
                title = a_tag.get_text(strip=True)
                
                if link in seen_links: continue

                # 언론사 이름 (span class="writing")
                press_span = item.find('span', class_='writing')
                press = press_span.get_text(strip=True) if press_span else "사설"

                # 제목 정리
                if title.startswith(press):
                    title = title[len(press):].lstrip('[] ')

                news_data.append({'title': title, 'link': link, 'press': press})
                seen_links.add(link)

            except Exception as e:
                print(f"   ⚠️ 항목 파싱 중 에러: {e}")
                continue
        
        time.sleep(0.5)

    print(f"✅ 총 {len(news_data)}개 수집 완료")

    if news_data:
        # 파일 저장
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(create_html(news_data))
        
        # [진단 2] 결과 전송
        msg = f"📰 수집 완료! 총 {len(news_data)}개\n\n"
        # 5개만 샘플로 보내고 링크 안내
        for news in news_data[:5]:
            msg += f"[{news['press']}] {news['title']}\n"
        msg += f"\n...외 {len(news_data)-5}개\n👉 https://chojh16.github.io/daily-editorial/"
        
        send_msg(msg)
    else:
        send_msg("❌ 기사를 하나도 못 찾았습니다. (네이버 구조 변경 의심)")

except Exception as e:
    err_msg = f"🔥 치명적 에러 발생: {e}"
    print(err_msg)
    send_msg(err_msg)
    exit(1)
