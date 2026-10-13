import os
import json
import requests
if __name__ == "__main__":
    print("Test d'envoi Telegram...")
    print(send_telegram("Test alert Telegram ✅"))
    verifier_bulles_5m()

SYMBOLS = [
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "XRPUSDT",
    "HYPEUSDT",
    "NEARUSDT",
    "BNBUSDT",
    "LINKUSDT",
    "DOGEUSDT",
    "UNIUSDT",
    "AVAXUSDT",
    "AAVEUSDT",
    "TAOUSDT",
    "ARBUSDT",
    "SEIUSDT",
    "PENGUUSDT",
    "WIFUSDT",
]

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")


def load_sent(filename):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()


def save_sent(filename, sent):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(sorted(list(sent))[-2000:], f)


def send_telegram(message):
    if not BOT_TOKEN or not CHAT_ID:
        print("Telegram non configuré : BOT_TOKEN ou CHAT_ID manquant")
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}

    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            return True
        print(f"Erreur Telegram ({response.status_code}): {response.text[:200]}")
        return False
    except Exception as exc:
        print(f"Erreur d'envoi Telegram: {exc}")
        return False


def alert_once(filename, key, message):
    sent = load_sent(filename)
    if key in sent:
        return False
    sent.add(key)
    save_sent(filename, sent)
    return send_telegram(message)


def verifier_bulles_5m():
    for symbol in SYMBOLS:
        try:
            url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=5m&limit=41"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            if not isinstance(data, list) or len(data) < 40:
                continue

            closes = [float(candle[4]) for candle in data[:-1]][-20:]
            if len(closes) < 20:
                continue

            mean = sum(closes) / len(closes)
            variance = sum((close - mean) ** 2 for close in closes) / len(closes)
            std = variance ** 0.5

            upper = mean + (2 * std)
            lower = mean - (2 * std)

            last_closed = data[-2]
            low = float(last_closed[3])
            high = float(last_closed[2])

            if low > upper:
                key = f"{symbol}:5m:bollinger:bullish"
                message = f"<b>🚨 5M</b> | <b>{symbol}</b> | <b>Bulle apesanteur HAUSSIÈRE</b>"
                alert_once("sent_alerts_5m.json", key, message)
            elif high < lower:
                key = f"{symbol}:5m:bollinger:bearish"
                message = f"<b>🚨 5M</b> | <b>{symbol}</b> | <b>Bulle apesanteur BAISSIÈRE</b>"
                alert_once("sent_alerts_5m.json", key, message)
        except Exception as exc:
            print(f"Erreur Bulles 5m {symbol}: {exc}")


if __name__ == "__main__":
    verifier_bulles_5m()
