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
    base = "https://www.tradingview.com/chart/"
    if TV_LAYOUT_ID:
        base += f"{TV_LAYOUT_ID}/"
    return f"{base}?symbol=BINANCE:{symbol}&interval={tv_interval}"

# -------------------- Réseau: Binance + fallbacks + Telegram --------------------

def get_klines_bybit(symbol, interval_minutes, limit=200):
    try:
        url = f"https://api.bybit.com/v2/public/kline/list?symbol={symbol}&interval={interval_minutes}&limit={limit}"
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        if not data.get("result"):
            return None
        rows = data["result"]
        klines = []
        for row in rows:
            openTime = row.get("start_at")
            open_p = str(row.get("open"))
            high = str(row.get("high"))
            low = str(row.get("low"))
            close = str(row.get("close"))
            vol = str(row.get("volume"))
            k = [openTime, open_p, high, low, close, vol, openTime + interval_minutes * 60 if isinstance(openTime, int) else None]
            klines.append(k)
        return klines
    except Exception as e:
        print("Bybit kline fetch error:", e)
        return None

def get_klines_kucoin(symbol, interval_type, limit=200):
    try:
        if symbol.endswith("USDT"):
            ku_symbol = symbol[:-4] + "-USDT"
        else:
            ku_symbol = symbol
        url = f"https://api.kucoin.com/api/v1/market/candles?type={interval_type}&symbol={ku_symbol}"
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        rows = data.get("data")
        if not rows:
            return None
        klines = []
        for row in reversed(rows):
            t = int(row[0])
            open_p = row[1]
            close = row[2]
            high = row[3]
            low = row[4]
            vol = row[5]
            k = [t, open_p, high, low, close, vol, t]
            klines.append(k)
        # KuCoin ignore "limit" et renvoie beaucoup de bougies : on garde les plus récentes
        return klines[-limit:]
    except Exception as e:
        print("KuCoin kline fetch error:", e)
        return None

def map_interval_to_bybit_minutes(interval_str):
    if interval_str == "15m":
        return 15
    if interval_str == "1h":
        return 60
    if interval_str.endswith("m"):
        return int(interval_str[:-1])
    if interval_str.endswith("h"):
        return int(interval_str[:-1]) * 60
    return 15

def map_interval_to_kucoin_type(interval_str):
    if interval_str == "15m":
        return "15min"
    if interval_str == "1h":
        return "1hour"
    return "15min"

def get_klines_with_retries(symbol, interval, limit=41, max_retries=3):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    backoff = 1
    for attempt in range(max_retries):
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 451:
                print(f"Binance returned 451 for {symbol} {interval}, trying fallbacks.")
                break
            if r.status_code == 429 or 500 <= r.status_code < 600:
                time.sleep(backoff)
                backoff *= 2
                continue
            print(f"Binance error {r.status_code} for {symbol} {interval}: {r.text[:200]}")
            break
        except requests.RequestException as e:
            print(f"Network error fetching klines {symbol} {interval}: {e}")
            time.sleep(backoff)
            backoff *= 2
    try:
        by_minutes = map_interval_to_bybit_minutes(interval)
        kb = get_klines_bybit(symbol, by_minutes, limit=limit)
        if kb:
            print(f"Using Bybit fallback for {symbol} {interval}")
            return kb
    except Exception as e:
        print("Bybit fallback failed:", e)
    try:
        ku_type = map_interval_to_kucoin_type(interval)
        kk = get_klines_kucoin(symbol, ku_type, limit=limit)
        if kk:
            print(f"Using KuCoin fallback for {symbol} {interval}")
            return kk
    except Exception as e:
        print("KuCoin fallback failed:", e)
    print(f"Failed to fetch klines {symbol} {interval} (Binance + fallbacks)")
    return None

def send_telegram_with_retries(message, max_retries=3):
    if not BOT_TOKEN or not CHAT_ID:
        print("Telegram non configuré : BOT_TOKEN ou CHAT_ID manquant")
        return False
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
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

# -------------------- Anti-doublon (mémoire conservée entre les runs via actions/cache) --------------------

MEMORY_DAYS = 7  # une alerte est oubliée après 7 jours (un BPR 1h sort de la fenêtre analysée bien avant)

def load_sent(filename=ALERTS_FILE):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except FileNotFoundError:
        return {}
    except Exception as e:
        print("Erreur lecture sent_alerts:", e)
        return {}
    now = time.time()
    if isinstance(raw, list):  # ancien format
        return {k: now for k in raw}
    return {k: v for k, v in raw.items() if now - v < MEMORY_DAYS * 86400}

def save_sent(sent, filename=ALERTS_FILE):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(sent, f)
    except Exception as e:
        print("Erreur écriture sent_alerts:", e)

def already_sent(key):
    return key in load_sent()

def remember(keys):
    sent = load_sent()
    now = time.time()
    for k in keys:
        sent[k] = now
    save_sent(sent)

def mark_alert_sent(key):
    """True si l'alerte est nouvelle (et la mémorise), False si déjà envoyée."""
    if already_sent(key):
        return False
    remember([key])
    return True

def candle_ts(k):
    """Heure d'ouverture de la bougie en secondes (Binance en ms, KuCoin/Bybit en s)."""
    ts = int(float(k[0]))
    return ts // 1000 if ts > 10**11 else ts

# -------------------- Bollinger (corps seulement) --------------------

def bollinger_body_signal(symbol, interval):
    data = get_klines_with_retries(symbol, interval, limit=41)
    time.sleep(0.12)  # courte pause entre requêtes pour limiter la cadence globale
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
    last = data[-2]
    open_price = float(last[1])
    close_price = float(last[4])
    body_low = min(open_price, close_price)
    body_high = max(open_price, close_price)
    ts = candle_ts(last)
    if body_low > upper:
        return "bullish", ts
    if body_high < lower:
        return "bearish", ts
    return None

def verifier_bulles(interval):
    for symbol in SYMBOLS:
        try:
            res = bollinger_body_signal(symbol, interval)
            if res:
                sig, ts = res
                key = f"{symbol}:{interval}:bollinger:{sig}:{ts}"
                if not mark_alert_sent(key):
                    print("Duplicate alert skipped:", key)
                    continue
                url = html.escape(tv_link(symbol, interval), quote=True)
                msg = (
                    f"<b>🚨 {interval}</b> | <b>{symbol}</b> | <b>Bulle apesanteur {sig.upper()}</b>\n"
                    f'<a href="{url}">📈 Ouvrir {symbol} sur TradingView (Binance)</a>'
                )
                print("Send alert:", key)
                send_telegram_with_retries(msg)
        except Exception as e:
            print(f"Erreur verifier_bulles {symbol} {interval}: {e}")

# -------------------- BPR / FVG --------------------
# BPR = zone d'intersection entre un FVG haussier et un FVG baissier.
# Alerte quand la dernière bougie FERMÉE (15m ou 1h), mèche ou corps, touche un BPR (15m ou 1h).
# Un BPR donné n'est signalé qu'une seule fois.

TF_SECONDS = {"15m": 900, "1h": 3600}

def analyse_tf(symbol, interval):
    data = get_klines_with_retries(symbol, interval, limit=80)
    time.sleep(0.12)
    if not isinstance(data, list) or len(data) < 60:
        return None
    candles = [{"ts": candle_ts(c), "high": float(c[2]), "low": float(c[3]), "close": float(c[4])}
               for c in data[:-1]]  # bougies fermées uniquement
    bull, bear = [], []
    for i in range(2, len(candles)):
        c1, c3 = candles[i - 2], candles[i]
        if c1["high"] < c3["low"]:
            bull.append({"top": c3["low"], "bottom": c1["high"], "ts": c3["ts"]})
        if c1["low"] > c3["high"]:
            bear.append({"top": c1["low"], "bottom": c3["high"], "ts": c3["ts"]})
    bprs = []
    for b in bull:
        for r in bear:
            top = min(b["top"], r["top"])
            bottom = max(b["bottom"], r["bottom"])
            if bottom < top:
                bprs.append({
                    "top": top, "bottom": bottom,
                    # le BPR est complet quand la 3e bougie du dernier FVG est fermée
                    "end": max(b["ts"], r["ts"]) + TF_SECONDS[interval],
                    "id": f"{interval}:{b['ts']}:{r['ts']}",  # identifiant stable d'un BPR
                })
    return {"bprs": bprs, "last": candles[-1]}

def fmt(x):
    return f"{x:.8g}"

def verifier_bpr_all():
    for symbol in SYMBOLS:
        try:
            tfs = {}
            for tf in ("15m", "1h"):
                res = analyse_tf(symbol, tf)
                if res:
                    tfs[tf] = res
            for candle_tf, cdata in tfs.items():
                last = cdata["last"]
                for bpr_tf, bdata in tfs.items():
                    touched = [
                        b for b in bdata["bprs"]
                        if b["end"] <= last["ts"]                      # BPR formé avant la bougie
                        and last["low"] <= b["top"] and last["high"] >= b["bottom"]  # mèche ou corps dans la zone
                    ]
                    new = [b for b in touched if not already_sent(f"{symbol}:bpr:{b['id']}")]
                    if not new:
                        continue
                    b = max(new, key=lambda x: x["end"])  # le plus récent (un seul message par cas)
                    mid = (b["top"] + b["bottom"]) / 2
                    sig = "bullish" if last["close"] >= mid else "bearish"
                    url = html.escape(tv_link(symbol, bpr_tf), quote=True)
                    msg = (
                        f"<b>🎯 BPR {bpr_tf}</b> | <b>{symbol}</b> | <b>{sig.upper()}</b>\n"
                        f"Bougie {candle_tf} dans la zone {fmt(b['bottom'])} - {fmt(b['top'])}\n"
                        f'<a href="{url}">📈 Ouvrir {symbol} sur TradingView (Binance)</a>'
                    )
                    print("Send BPR alert:", symbol, bpr_tf, b["id"], "candle", candle_tf)
                    if send_telegram_with_retries(msg):
                        remember([f"{symbol}:bpr:{x['id']}" for x in new])
        except Exception as e:
            print(f"Erreur verifier_bpr {symbol}: {e}")

# -------------------- MAIN --------------------

if __name__ == "__main__":
    print("START bot")
    verifier_bulles("15m")
    verifier_bulles("1h")
    verifier_bpr_all()
    print("END bot")
