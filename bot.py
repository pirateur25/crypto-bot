import os
import json
import requests

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


def bollinger_signal(symbol, interval):
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit=41"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not isinstance(data, list) or len(data) < 40:
            return None

        closes = [float(candle[4]) for candle in data[:-1]][-20:]
        if len(closes) < 20:
            return None

        mean = sum(closes) / len(closes)
        variance = sum((close - mean) ** 2 for close in closes) / len(closes)
        std = variance ** 0.5

        upper = mean + (2 * std)
        lower = mean - (2 * std)

        last_closed = data[-2]
        low = float(last_closed[3])
        high = float(last_closed[2])

        if low > upper:
            return "bullish"
        if high < lower:
            return "bearish"
        return None
    except Exception as exc:
        print(f"Erreur Bollinger {symbol} {interval}: {exc}")
        return None


def check_bollinger(interval):
    for symbol in SYMBOLS:
        signal = bollinger_signal(symbol, interval)
        if signal is None:
            continue

        key = f"{symbol}:{interval}:bollinger:{signal}"
        message = (
            f"<b>🚨 {interval}</b> | <b>{symbol}</b> | "
            f"<b>Bulle apesanteur {signal.upper()}</b>"
        )
        alert_once("sent_alerts.json", key, message)


def bpr_signal(symbol):
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=80"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not isinstance(data, list) or len(data) < 60:
            return None

        candles = [
            {"high": float(candle[2]), "low": float(candle[3]), "close": float(candle[4])}
            for candle in data[:-1]
        ]
        latest = candles[-1]

        bullish_fvgs = []
        bearish_fvgs = []

        for i in range(2, len(candles) - 1):
            previous = candles[i - 2]
            current = candles[i]
            if previous["high"] < current["low"]:
                bullish_fvgs.append((previous["high"], current["low"], i))
            if previous["low"] > current["high"]:
                bearish_fvgs.append((previous["low"], current["high"], i))

        for low_price, high_price, index in bullish_fvgs:
            if index < len(candles) - 1 and latest["low"] <= high_price and latest["high"] >= low_price:
                return "bullish"

        for low_price, high_price, index in bearish_fvgs:
            if index < len(candles) - 1 and latest["low"] <= high_price and latest["high"] >= low_price:
                return "bearish"

        return None
    except Exception as exc:
        print(f"Erreur BPR/FVG {symbol}: {exc}")
        return None


def check_bpr():
    for symbol in SYMBOLS:
        signal = bpr_signal(symbol)
        if signal is None:
            continue

        key = f"{symbol}:1h:bpr:{signal}"
        message = (
            f"<b>🎯 1H</b> | <b>{symbol}</b> | "
            f"<b>BPR / FVG {signal.upper()}</b>"
        )
        alert_once("sent_alerts.json", key, message)


if __name__ == "__main__":
    check_bollinger("15m")
    check_bollinger("1h")
    check_bpr()
