# bot_5m.py
# Bot pour unité 5 minutes
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
    Envoie un message et logge le retour. Retourne True si ok.
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


def verifier_bulles_5m():
    """
    Vérifie les bulles Bollinger en 5 minutes sur SYMBOLS.
    """
    for symbol in SYMBOLS:
        try:
            url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=5m&limit=41"
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if not isinstance(data, list) or len(data) < 40:
                continue

            closes = [float(c[4]) for c in data[:-1]][-20:]
            if len(closes) < 20:
                continue

            mean = sum(closes) / len(closes)
            variance = sum((c - mean) ** 2 for c in closes) / len(closes)
            std = variance ** 0.5
            upper = mean + 2 * std
            lower = mean - 2 * std

            last_closed = data[-2]
            low = float(last_closed[3])
            high = float(last_closed[2])

            if low > upper:
                msg = f"<b>🚨 5M</b> | <b>{symbol}</b> | <b>Bulle apesanteur HAUSSIÈRE</b>"
                print(f"5m alert bullish: {symbol}")
                envoyer_telegram(msg)
            elif high < lower:
                msg = f"<b>🚨 5M</b> | <b>{symbol}</b> | <b>Bulle apesanteur BAISSIÈRE</b>"
                print(f"5m alert bearish: {symbol}")
                envoyer_telegram(msg)
        except Exception as e:
            print(f"Erreur Bulles 5m {symbol}: {e}")


if __name__ == "__main__":
    # =========================
    # ZONE DE TEST — A SUPPRIMER EN PROD
    print("Test d'envoi Telegram (5m) ... (zone de test, supprimer après vérif)")
    try:
        res = envoyer_telegram("Test alert Telegram 5m ✅ (supprimer ce message après vérif)")
        print("Résultat send test 5m:", res)
    except Exception as e:
        print("Exception lors du test d'envoi 5m:", e)
    # FIN ZONE DE TEST
    # =========================

    verifier_bulles_5m()
