import os
import requests
import json
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

# === TOKEN & ID自動從 GitHub secrets 讀取 ===
BOT_TOKEN = os.environ.get('BOT_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')
GIST_ID = os.environ.get('GIST_ID')
GIST_TOKEN = os.environ.get('GIST_TOKEN')
GIST_FILE = 'txf_status.json'

TXF_YAHOO_URL = "https://tw.stock.yahoo.com/futures/quote/TXF"
TXF_YAHOO_KLINE_API = "https://query1.finance.yahoo.com/v8/finance/chart/TXF=F?period1={start}&period2={end}&interval=1d"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# === 狀態存取（開關） ===
def set_status_on():
    save_status_to_gist({"status": "on"})

def set_status_off():
    save_status_to_gist({"status": "off"})

def get_status():
    url = f"https://api.github.com/gists/{GIST_ID}"
    r = requests.get(url, headers={"Authorization": f"token {GIST_TOKEN}"})
    if r.status_code == 200:
        files = r.json().get("files", {})
        if GIST_FILE in files:
            content = files[GIST_FILE]["content"]
            try:
                return json.loads(content).get("status", "on")
            except:
                return "on"
    return "on"

def save_status_to_gist(data):
    url = f"https://api.github.com/gists/{GIST_ID}"
    body = {
        "files": {
            GIST_FILE: {
                "content": json.dumps(data)
            }
        }
    }
    requests.patch(url, headers={"Authorization": f"token {GIST_TOKEN}"}, data=json.dumps(body))

# === 取得K線與計算ATR ===
def get_kline_history(days=6):
    end = int(datetime.now().timestamp())
    start = int((datetime.now() - timedelta(days=days+2)).timestamp())
    url = TXF_YAHOO_KLINE_API.format(start=start, end=end)
    res = requests.get(url, headers=headers, timeout=10)
    data = res.json()
    result = data['chart']['result'][0]
    timestamps = result['timestamp']
    quotes = result['indicators']['quote'][0]
    ohlc = []
    for i in range(len(timestamps)):
        item = {
            "date": datetime.fromtimestamp(timestamps[i]).strftime("%Y-%m-%d"),
            "open": quotes['open'][i],
            "high": quotes['high'][i],
            "low": quotes['low'][i],
            "close": quotes['close'][i]
        }
        ohlc.append(item)
    return ohlc

def calc_atr(ohlc, period=5):
    trs = []
    for i in range(1, period+1):
        high = ohlc[-i]['high']
        low = ohlc[-i]['low']
        prev_close = ohlc[-i-1]['close']
        tr = max(
            high - low,
            abs(high - prev_close),
            abs(low - prev_close)
        )
        trs.append(tr)
    atr = sum(trs) / period
    return round(atr, 2)

def get_today_open():
    ohlc = get_kline_history(days=2)
    try:
        return ohlc[-1]['open']
    except:
        return ohlc[-2]['close']

def get_txf_percent():
    try:
        res = requests.get(TXF_YAHOO_URL, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        price_span = soup.find('span', {'data-test': 'change-percent'})
        percent = price_span.text.strip() if price_span else "無法取得"
        return percent
    except Exception:
        return "無法取得"

def get_txf_last():
    try:
        res = requests.get(TXF_YAHOO_URL, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        price = soup.find('span', {'data-test': 'last-price'}).text.strip()
        return price
    except Exception:
        return "無法取得"

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    requests.post(url, data=payload)

def main():
    if get_status() != "on":
        return
    ohlc = get_kline_history()
    today_open = ohlc[-1]['open']
    atr = calc_atr(ohlc)
    pred_high = round(today_open + atr, 2)
    pred_low = round(today_open - atr, 2)
    time_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    msg = (
        f"⏰ {time_str} 台指近 開盤預測\n\n"
        f"今日開盤價：{today_open}\n"
