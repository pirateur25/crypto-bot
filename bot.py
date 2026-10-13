# bot.py
# Bot principal : détection Bollinger 15m/1h et BPR 1h
# NOTE: la zone de test d'envoi Telegram en bas doit être SUPPRIMEE une fois la vérification faite.

import os
import requests

SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "HYPEUSDT",
    "NEARUSDT", "BNBUSDT", "LINKUSDT", "DOGEUSDT", "UNIUSDT",
    "AVAXUSDT", "AAVEUSDT", "TAOUSDT", "ARBUSDT", "SEIUSDT",
    "PENGUUSDT", "WIFUSDT",
]

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")


def envoyer_telegram(message):
    """
    Envoie un message via l'API Telegram et logge le résultat.
    Retourne True si status_code == 200, False sinon.
    """
    if not BOT_TOKEN or not CHAT_ID:
        print("Telegram non configuré : BOT_TOKEN ou CHAT_ID manquant")
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}

    try:
        r = requests.post(url, json=payload, timeout=10)
        print("send_telegram -> status:", r.status_code)
        print("send_telegram -> body:", r.text[:1000])
        return r.status_code == 200
    except Exception as e:
        print("Erreur d'envoi Telegram:", e)
        return False


def bollinger_signal(symbol, interval):
    """
    Retourne 'bullish' / 'bearish' / None en fonction de la position de la dernière bougie
    fermée par rapport aux bandes de Bollinger (période 20, std 2).
    """
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit=41"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, list) or len(data) < 40:
            return None

        closes = [float(c[4]) for c in data[:-1]][-20:]
        if len(closes) < 20:
            return None

        mean = sum(closes) / len(closes)
        variance = sum((c - mean) ** 2 for c in closes) / len(closes)
        std = variance ** 0.5
        upper = mean + 2 * std
        lower = mean - 2 * std

        last_closed = data[-2]
        low = float(last_closed[3])
        high = float(last_closed[2])

        if low > upper:
            return "bullish"
        if high < lower:
            return "bearish"
        return None
    except Exception as e:
        print(f"Erreur Bollinger {symbol} {interval}: {e}")
        return None


def verifier_bulles(interval):
    """
    Parcourt SYMBOLS et envoie un message quand une bulle est détectée.
    """
    for symbol in SYMBOLS:
        sig = bollinger_signal(symbol, interval)
        if sig is None:
            continue
        msg = f"<b>🚨 {interval}</b> | <b>{symbol}</b> | <b>Bulle apesanteur {sig.upper()}</b>"
        print(f"Alert triggered: {symbol} {interval} {sig}")
        envoyer_telegram(msg)


def bpr_signal(symbol):
    """
    Détection simple BPR/FVG sur 1h.
    Retourne 'bullish', 'bearish' ou None.
    """
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=80"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, list) or len(data) < 60:
            return None

        candles = [{"high": float(c[2]), "low": float(c[3]), "close": float(c[4])} for c in data[:-1]]
        latest = candles[-1]

        bullish_fvgs = []
        bearish_fvgs = []

        for i in range(2, len(candles) - 1):
            prev = candles[i - 2]
            cur = candles[i]
            if prev["high"] < cur["low"]:
                bullish_fvgs.append((prev["high"], cur["low"], i))
            if prev["low"] > cur["high"]:
                bearish_fvgs.append((prev["low"], cur["high"], i))

        for low_p, high_p, idx in bullish_fvgs:
            if idx < len(candles) - 1 and latest["low"] <= high_p and latest["high"] >= low_p:
                return "bullish"

        for low_p, high_p, idx in bearish_fvgs:
            if idx < len(candles) - 1 and latest["low"] <= high_p and latest["high"] >= low_p:
                return "bearish"

        return None
    except Exception as e:
        print(f"Erreur BPR/FVG {symbol}: {e}")
        return None


def verifier_bpr():
    for symbol in SYMBOLS:
        sig = bpr_signal(symbol)
        if sig is None:
            continue
        msg = f"<b>🎯 1H</b> | <b>{symbol}</b> | <b>BPR / FVG {sig.upper()}</b>"
        print(f"BPR alert: {symbol} {sig}")
        envoyer_telegram(msg)


if __name__ == "__main__":
    # Exécutions normales
    verifier_bulles("15m")
    verifier_bulles("1h")
    verifier_bpr()
