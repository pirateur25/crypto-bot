# bot_5m.py
# Détection Bollinger 5m (corps de la bougie uniquement)
# Anti-doublon local via sent_alerts.json, fallback Bybit/KuCoin si Binance bloqué
# Les alertes Telegram contiennent un lien cliquable vers TradingView (broker Binance, 5m)

import os
import time
import json
import html
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

# Optionnel : identifiant de ton layout TradingView (pour retrouver tes indicateurs).
# Exemple : si ton lien de graphique est https://www.tradingview.com/chart/AbCd1234/
# alors TV_LAYOUT_ID = "AbCd1234". Laisse vide sinon.
TV_LAYOUT_ID = ""

# ---------------- lien TradingView ----------------

def tv_link(symbol, interval):
    tv_interval = {"5m": "5", "15m": "15", "1h": "60"}.get(interval, "5")
    base = "https://www.tradingview.com/chart/"
    if TV_LAYOUT_ID:
        base += f"{TV_LAYOUT_ID}/"
    return f"{base}?symbol=BINANCE:{symbol}&interval={tv_interval}"
