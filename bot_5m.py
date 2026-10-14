# bot_5m.py
# Détection Bollinger 5m (corps de la bougie uniquement)
# - Anti-doublon local via sent_alerts.json
# - Pas de persistance GitHub / pas de variables supplémentaires

import os
import time
import json
import requests

SYMBOLS = [
    "BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","HYPEUSDT",
    "NEARUSDT","BNBUSDT","LINKUSDT","DOGEUSDT","UNIUSDT",
    "AVAXUSDT","AAVEUSDT","TAOUSDT","ARBUSDT","SEIUSDT",
    "PENGUUSDT","WIFUSDT",
]

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

ALERTS_FILE = "sent_alerts.json"

def get_klines_with_retries(symbol, interval="5m", limit=41, max_retries=4):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    backoff = 1
    for attempt in range(max_retries):
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 429 or 500 <= r.status_code < 600:
                time.sleep(backoff)
                backoff *= 2
                continue
            print(f"Binance error {r.status_code} for {symbol} {interval}: {r.text[:200]}")
            return None
        except requests.RequestException as e:
            print(f"Network error fetching klines {symbol} {interval}: {e}")
            time.sleep(backoff)
            backoff *= 2
    print(f"Failed to fetch klines {symbol} {interval} after {max_retries} attempts")
    return None

def send_telegram_with_retries(message, max_retries=3):
    if not BOT_TOKEN or not CHAT_ID:
        print("Telegram non configuré : BOT_TOKEN ou CHAT_ID manquant")
        return False
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    backoff = 1
    for attempt in range(max_retries):
        try:
            r = requests.post(url, json=payload, timeout=10)
            print("send_telegram -> status:", r.status_code)
            print("send_telegram -> body:", r.text[:400])
            if r.status_code == 200:
                return True
            if r.status_code == 429 or 500 <= r.status_code < 600:
                time.sleep(backoff)
                backoff *= 2
                continue
            return False
        except requests.RequestException as e:
            print("Erreur d'envoi Telegram:", e)
            time.sleep(backoff)
            backoff *= 2
    return False

def load_sent(filename=ALERTS_FILE):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()
    except Exception as e:
        print("Erreur lecture sent_alerts:", e)
        return set()

def save_sent(sent, filename=ALERTS_FILE):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(sorted(list(sent)), f)
    except Exception as e:
        print("Erreur écriture sent_alerts:", e)

def mark_alert_sent(key):
    sent = load_sent()
    if key in sent:
        return False
    sent.add(key)
    save_sent(sent)
    return True
def bollinger_body_signal_5m(symbol):
    """
    Récupère les klines 5m et calcule les bandes Bollinger sur les 20 dernières bougies fermées.
    Affiche des logs DEBUG détaillés (open/high/low/close, upper/lower, body_low/body_high)
    pour aider au diagnostic. Retourne 'bullish' / 'bearish' / None.
    """
    data = get_klines_with_retries(symbol, "5m", limit=41)
    time.sleep(0.12)
    if not isinstance(data, list) or len(data) < 40:
        print(f"DEBUG {symbol} 5m -> no data or insufficient klines (len={len(data) if isinstance(data, list) else 'NA'})")
        return None

    # Utiliser les 20 dernières bougies fermées
    closes = [float(c[4]) for c in data[:-1]][-20:]
    if len(closes) < 20:
        print(f"DEBUG {symbol} 5m -> not enough closed candles for Bollinger (found {len(closes)})")
        return None

    mean = sum(closes) / len(closes)
    variance = sum((c - mean) ** 2 for c in closes) / len(closes)
    std = variance ** 0.5
    upper = mean + 2 * std
    lower = mean - 2 * std

    # Dernière bougie fermée (index -2)
    last = data[-2]
    open_price = float(last[1])
    high_price = float(last[2])
    low_price = float(last[3])
    close_price = float(last[4])

    body_low = min(open_price, close_price)
    body_high = max(open_price, close_price)

    # Debug prints détaillés
    print(
        f"DEBUG {symbol} 5m -> last_closed O:{open_price} H:{high_price} L:{low_price} C:{close_price} | "
        f"upper:{upper:.8f} lower:{lower:.8f} | body_low:{body_low} body_high:{body_high}"
    )

    # Décision basée uniquement sur le corps (ignore les mèches)
    sig = None
    if body_low > upper:
        sig = "bullish"
    elif body_high < lower:
        sig = "bearish"

    print(f"DEBUG {symbol} 5m -> decision: {sig if sig else 'NONE'}")
    return sig

def verifier_bulles_5m():
    for symbol in SYMBOLS:
        try:
            sig = bollinger_body_signal_5m(symbol)
            if sig:
                key = f"{symbol}:5m:bollinger:{sig}"
                if not mark_alert_sent(key):
                    print("Duplicate 5m alert skipped:", key)
                    continue
                msg = f"<b>🚨 5M</b> | <b>{symbol}</b> | <b>Bulle apesanteur {sig.upper()}</b>"
                print("Send 5m alert:", key)
                send_telegram_with_retries(msg)
        except Exception as e:
            print(f"Erreur verifier_bulles_5m {symbol}: {e}")

if __name__ == "__main__":
    verifier_bulles_5m()
