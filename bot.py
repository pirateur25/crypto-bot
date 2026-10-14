# bot.py
# Détection Bollinger (15m, 1h) et BPR (15m, 1h)
# - Corps de la bougie uniquement pour la condition "bulle apesanteur"
# - Anti-doublon local via sent_alerts.json (aucune persistance GitHub)
# - Fallback Bybit/KuCoin si Binance est bloqué (erreur 451 sur GitHub Actions)
# - Les alertes Telegram contiennent un lien cliquable vers TradingView (broker Binance)

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

# Récupère token/chat depuis les secrets (ne rien ajouter)
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

ALERTS_FILE = "sent_alerts.json"

# Optionnel : identifiant de ton layout TradingView (pour retrouver tes indicateurs).
# Exemple : si ton lien de graphique est https://www.tradingview.com/chart/AbCd1234/
# alors TV_LAYOUT_ID = "AbCd1234". Laisse vide sinon.
TV_LAYOUT_ID = ""

# -------------------- Lien TradingView --------------------

def tv_link(symbol, interval):
    tv_interval = {"5m": "5", "15m": "15", "1h": "60"}.get(interval, "15")
