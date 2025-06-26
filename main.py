import requests
import json
import time

# ======= 控制與推播 =======
GIST_ID = '5ea313297e9325c6cb6f3c8e1d167368'
GIST_TOKEN = '你的GIST_TOKEN'
GIST_FILE = 'txf_status.json'

TELEGRAM_BOT_TOKEN = '你的TelegramBotToken'
TELEGRAM_CHAT_ID = '你的ChatID'

def get_status():
    url = f"https://api.github.com/gists/{GIST_ID}"
    headers = {"Authorization": f"token {GIST_TOKEN}"}
    r = requests.get(url, headers=headers)
    content = r.json()["files"][GIST_FILE]["content"]
    status = json.loads(content).get("status", "off")
    return status

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": msg}
    r = requests.post(url, data=data)
    if r.status_code == 200:
        print("✅ 推播成功")
    else:
        print("❌ 推播失敗", r.text)

# ========== 主邏輯（可改為你的台指近分析與預測邏輯） ==========

def main():
    if get_status() == "on":
        # 這裡可填入台指近即時/預測/收盤分析
        msg = "台指近訊號推播範例！\n（這裡插入你的行情分析與策略判斷結果）"
        send_telegram(msg)
    else:
        print("❌ 推播狀態為 off，不發送")

if __name__ == "__main__":
    main()
