import requests
from datetime import datetime
from bs4 import BeautifulSoup

BOT_TOKEN = '7923487181:AAHicdAJGorw4PJNj48It_3R8e04AuOJfQk'
CHAT_ID = '7782358896'

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    requests.post(url, data=payload)

def get_stock_info():
    url = "https://tw.stock.yahoo.com/quote/3013.TW"
    res = requests.get(url, timeout=10)
    soup = BeautifulSoup(res.text, "html.parser")
    price = soup.select_one('span[class*="Fz(32px)"]').text if soup.select_one('span[class*="Fz(32px)"]') else "無資料"
    time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"晟銘電(3013)\n現價: {price}\n時間: {time_str}"

def get_latest_news():
    url = "https://tw.stock.yahoo.com/quote/3013.TW/news"
    res = requests.get(url, timeout=10)
    soup = BeautifulSoup(res.text, "html.parser")
    news_list = []
    for n in soup.select('li a h3'):
        news_list.append(n.text.strip())
        if len(news_list) >= 3:
            break
    return news_list if news_list else ["查無新聞"]

def main():
    info = get_stock_info()
    news = get_latest_news()
    news_str = '\n'.join([f"- {n}" for n in news])
    msg = f"{info}\n\n最新新聞:\n{news_str}"
    send_telegram_message(msg)

if __name__ == "__main__":
    main()
