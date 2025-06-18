import os
import requests
from datetime import datetime
from bs4 import BeautifulSoup
import json

# 1. Telegram 設定
BOT_TOKEN = '7923487181:AAHicdAJGorw4PJNj48It_3R8e04AuOJfQk'
CHAT_ID = '7782358896'

# 2. 你要追蹤的多檔股票
stocks = [
    {"code": "3013", "name": "晟銘電"},
    {"code": "2449", "name": "京元電子"},
    {"code": "2615", "name": "萬海"}
]

# 3. AI 關鍵字情緒分析（可自行調整）
bullish_keywords = ["得標", "漲停", "訂單", "突破", "創新高", "AI", "增資", "強勢", "利多", "爆量"]
bearish_keywords = ["減產", "裁員", "失火", "罰款", "利空", "跌停", "轉弱", "疲弱"]

# 4. 讀取 OpenAI API Key (從 GitHub secrets)
OPENAI_API_KEY = os.environ.get('OPENAPIKEY')

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    requests.post(url, data=payload)

def get_yahoo_quote(code):
    url = f"https://tw.stock.yahoo.com/quote/{code}.TW"
    res = requests.get(url, timeout=10)
    soup = BeautifulSoup(res.text, "html.parser")
    price = soup.select_one('span[class*="Fz(32px)"]').text if soup.select_one('span[class*="Fz(32px)"]') else "無資料"
    return price

def get_five_level_info(code):
    # 五檔價量抓 Yahoo Finance 頁面
    url = f"https://tw.stock.yahoo.com/quote/{code}.TW"
    res = requests.get(url, timeout=10)
    soup = BeautifulSoup(res.text, "html.parser")
    table = soup.find('div', {'class': 'D(f) Ai(fe) Jc(sb) Mb(12px)'})
    if not table:
        return "五檔資料抓取失敗"
    bids = []
    asks = []
    try:
        for row in table.select('div.Bgc($hoverBgColor)'):
            tds = row.select('span')
            if len(tds) == 4:
                bids.append(f"買{len(bids)+1}:{tds[0].text}@{tds[1].text}")
                asks.append(f"賣{len(asks)+1}:{tds[2].text}@{tds[3].text}")
    except:
        return "五檔資料格式錯誤"
    bids_str = ' '.join(bids)
    asks_str = ' '.join(asks)
    return f"{bids_str}\n{asks_str}"

def get_latest_news(code):
    url = f"https://tw.stock.yahoo.com/quote/{code}.TW/news"
    res = requests.get(url, timeout=10)
    soup = BeautifulSoup(res.text, "html.parser")
    news_list = []
    for n in soup.select('li a h3'):
        news_list.append(n.text.strip())
        if len(news_list) >= 3:
            break
    return news_list if news_list else ["查無新聞"]

def get_news_sentiment(news_list):
    for news in news_list:
        if any(word in news for word in bullish_keywords):
            return "利多"
        if any(word in news for word in bearish_keywords):
            return "利空"
    return "中性"

def ask_chatgpt(prompt):
    api_key = OPENAI_API_KEY
    if not api_key:
        return "❗️[錯誤] 沒有設定 OpenAI API 金鑰"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": "你是台股當沖決策小助手，請根據給定的即時價格、五檔資料、新聞標題，直接回覆建議：多單/空單/觀望，並簡要說明理由。"},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 128,
        "temperature": 0.4
    }
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, data=json.dumps(data))
    if response.status_code == 200:
        reply = response.json()['choices'][0]['message']['content']
        return reply.strip()
    else:
        return f"❗️[ChatGPT 回應錯誤] {response.text}"

def build_prompt(stock, price, five_level, news_list, news_sentiment):
    news_str = "\n".join([f"- {n}" for n in news_list])
    return (
        f"股票：{stock['name']}({stock['code']})\n"
        f"現價：{price}\n"
        f"五檔：\n{five_level}\n"
        f"新聞：\n{news_str}\n"
        f"新聞情緒：{news_sentiment}\n"
        f"請根據上述資訊，判斷當沖進出方向並說明理由。"
    )

def main():
    time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    all_messages = [f"⏰ {time_str} 台股多檔即時AI推播"]
    for stock in stocks:
        price = get_yahoo_quote(stock['code'])
        five_level = get_five_level_info(stock['code'])
        news_list = get_latest_news(stock['code'])
        news_sentiment = get_news_sentiment(news_list)
        prompt = build_prompt(stock, price, five_level, news_list, news_sentiment)
        ai_reply = ask_chatgpt(prompt)
        msg = (
            f"\n———\n"
            f"【{stock['name']}】({stock['code']})\n"
            f"現價：{price}\n"
            f"新聞情緒：{news_sentiment}\n"
            f"五檔：\n{five_level}\n"
            f"新聞：\n" + "\n".join([f"- {n}" for n in news_list]) + "\n"
            f"\n【AI 進場建議】\n{ai_reply}"
        )
        all_messages.append(msg)
    send_telegram_message('\n'.join(all_messages))

if __name__ == "__main__":
    main()
