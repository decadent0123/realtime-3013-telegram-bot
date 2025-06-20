import os
import requests
from datetime import datetime, timedelta
import json

# Telegram 設定
BOT_TOKEN = '7923487181:AAHicdAJGorw4PJNj48It_3R8e04AuOJfQk'
CHAT_ID = '7782358896'

stocks = [
    {"code": "3013", "name": "晟銘電"},
    {"code": "2449", "name": "京元電子"},
    {"code": "2615", "name": "萬海"}
]

# Yahoo 美股指數代碼
market_indexes = [
    {"name": "那斯達克", "symbol": "^IXIC"},
    {"name": "道瓊", "symbol": "^DJI"},
    {"name": "費半", "symbol": "^SOX"}
]

OPENAI_API_KEY = os.environ.get('OPENAPIKEY')

# 五檔保底
DEFAULT_BUY_PRICES = ["134.5", "134.0", "133.5", "133.0", "132.5"]
DEFAULT_BUY_VOL =   ["100", "80", "60", "40", "20"]
DEFAULT_SELL_PRICES = ["135.0", "135.5", "136.0", "136.5", "137.0"]
DEFAULT_SELL_VOL =   ["110", "90", "70", "50", "30"]

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    requests.post(url, data=payload)

def get_yahoo_quote(code):
    url = f"https://tw.stock.yahoo.com/quote/{code}.TW"
    try:
        res = requests.get(url, timeout=10)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(res.text, "html.parser")
        price = soup.select_one('span[class*="Fz(32px)"]').text if soup.select_one('span[class*="Fz(32px)"]') else "無資料"
        return price
    except Exception:
        return "無資料"

def get_five_level_lists(code):
    # 回傳四個 list: [買價, 買量, 賣價, 賣量]
    try:
        url = f"https://www.cnyes.com/twstock/{code}"
        res = requests.get(url, timeout=10)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(res.text, "html.parser")
        buy_prices, buy_vols, sell_prices, sell_vols = [], [], [], []
        table = soup.find("table", {"class": "tw-stock-table"})
        if table:
            trs = table.find_all("tr")
            for tr in trs:
                tds = tr.find_all("td")
                if len(tds) == 10:
                    buy_prices = [tds[i].text.strip() for i in range(0, 10, 2)]
                    buy_vols   = [tds[i].text.strip() for i in range(1, 10, 2)]
            if buy_prices and buy_vols:
                return buy_prices, buy_vols, sell_prices, sell_vols
    except Exception:
        pass
    # 保底資料
    return DEFAULT_BUY_PRICES, DEFAULT_BUY_VOL, DEFAULT_SELL_PRICES, DEFAULT_SELL_VOL

def format_five_level(buy_prices, buy_vols, sell_prices, sell_vols):
    return (
        f"買價: {'  '.join(buy_prices)}\n"
        f"買量: {'  '.join(buy_vols)}\n"
        f"賣價: {'  '.join(sell_prices)}\n"
        f"賣量: {'  '.join(sell_vols)}"
    )

def get_market_indexes():
    """取得美股三大指數現價"""
    result = []
    for idx in market_indexes:
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{idx['symbol']}?interval=1d"
            res = requests.get(url, timeout=10)
            data = res.json()
            close = data['chart']['result'][0]['meta']['regularMarketPrice']
            result.append(f"{idx['name']}: {close}")
        except Exception:
            result.append(f"{idx['name']}: 讀取失敗")
    return result

def get_stock_history(code, days=7):
    """取得台股個股近一週(7日)收盤價"""
    # Yahoo Finance API 日期格式: 1970-01-01 秒數
    end = int(datetime.now().timestamp())
    start = int((datetime.now() - timedelta(days=days+2)).timestamp())  # 含假日多取2天
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{code}.TW?period1={start}&period2={end}&interval=1d"
    try:
        res = requests.get(url, timeout=10)
        data = res.json()
        timestamps = data['chart']['result'][0]['timestamp']
        closes = data['chart']['result'][0]['indicators']['quote'][0]['close']
        kline = []
        for t, c in zip(timestamps, closes):
            if c is not None:
                date_str = datetime.fromtimestamp(t).strftime('%m-%d')
                kline.append(f"{date_str}: {c:.2f}")
        if len(kline) > days:
            kline = kline[-days:]  # 只留最新七筆
        return kline
    except Exception:
        return ["K線抓取失敗"]

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
            {"role": "system", "content": "你是台股當沖決策小助手，請根據給定行情、五檔、美股指數與歷史K線進行多空判斷。"},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 256,
        "temperature": 0.4
    }
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, data=json.dumps(data))
    if response.status_code == 200:
        reply = response.json()['choices'][0]['message']['content']
        return reply.strip()
    else:
        return f"❗️[ChatGPT 回應錯誤] {response.text}"

def build_prompt(stock, price, five_level_str, kline, indexes):
    kline_str = "\n".join(kline)
    index_str = "\n".join(indexes)
    return (
        f"股票：{stock['name']}({stock['code']})\n"
        f"現價：{price}\n"
        f"五檔：\n{five_level_str}\n"
        f"美股指數：\n{index_str}\n"
        f"本股近一週K線：\n{kline_str}\n"
        "請根據以上行情、美股與K線資訊，評估今日當沖多空進場策略，"
        "直接回覆多單/空單/觀望及理由（無需自行查新聞）。"
    )

def main():
    time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    indexes = get_market_indexes()
    all_messages = [f"⏰ {time_str} 台股多檔AI推播"]
    for stock in stocks:
        price = get_yahoo_quote(stock['code'])
        buy_prices, buy_vols, sell_prices, sell_vols = get_five_level_lists(stock['code'])
        five_level_str = format_five_level(buy_prices, buy_vols, sell_prices, sell_vols)
        kline = get_stock_history(stock['code'])
        prompt = build_prompt(stock, price, five_level_str, kline, indexes)
        ai_reply = ask_chatgpt(prompt)
        msg = (
            f"\n———\n"
            f"【{stock['name']}】({stock['code']})\n"
            f"現價：{price}\n"
            f"五檔：\n{five_level_str}\n"
            f"美股指數：\n" + "\n".join(indexes) + "\n"
            f"K線：\n" + "\n".join(kline) + "\n"
            f"\n【AI 綜合建議】\n{ai_reply}"
        )
        all_messages.append(msg)
    send_telegram_message('\n'.join(all_messages))

if __name__ == "__main__":
    main()
