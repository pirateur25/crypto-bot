import os
import requests

# Votre liste d'actifs
symboles = [
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

# Récupération automatique des clés Telegram stockées dans les secrets GitHub
bot_token = os.environ.get("BOT_TOKEN")
chat_id = os.environ.get("CHAT_ID")


def envoyer_telegram(message):
  if bot_token and chat_id:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": message})


# --- FONCTION GÉNÉRIQUE : CALCUL DES BULLES APESANTEUR ---
def verifier_bulles(intervalle):
  for symbole in symboles:
    try:
      url = f"https://api.binance.com/api/v3/klines?symbol={symbole}&interval={intervalle}&limit=21"
      res = requests.get(url).json()
      if isinstance(res, list) and len(res) >= 20:
        bougies = res[:-1]  # Retire la bougie en cours
        closes = [float(b[4]) for b in bougies]
        low = float(bougies[-1][3])
        high = float(bougies[-1][2])

        moyenne = sum(closes) / 20
        variance = sum((c - moyenne) ** 2 for c in closes) / 20
        ecart_type = variance**0.5

        bande_sup = moyenne + (2 * ecart_type)
        bande_inf = moyenne - (2 * ecart_type)

        if low > bande_sup:
          envoyer_telegram(
              f"🚀 Bulle Apesanteur HAUSSIÈRE sur {symbole} ({intervalle})"
          )
        elif high < bande_inf:
          envoyer_telegram(
              f"🔻 Bulle Apesanteur BAISSIÈRE sur {symbole} ({intervalle})"
          )
    except Exception as e:
      print(f"Erreur Bulles {intervalle} {symbole}: {e}")


# --- ANALYSE DES BPR (1h) ---
def verifier_bpr():
  for symbole in symboles:
    try:
      url = f"https://api.binance.com/api/v3/klines?symbol={symbole}&interval=1h&limit=50"
      res = requests.get(url).json()
      if isinstance(res, list) and len(res) >= 40:
        bougies_raw = res[:-1]
        bougies = [{"high": float(b[2]), "low": float(b[3])} for b in bougies_raw]

        bullish_fvgs = []
        bearish_fvgs = []

        for i in range(2, len(bougies)):
          c1 = bougies[i - 2]
          c3 = bougies[i]
          if c1["high"] < c3["low"]:
            bullish_fvgs.append({"top": c3["low"], "bottom": c1["high"], "index": i})
          if c1["low"] > c3["high"]:
            bearish_fvgs.append({"top": c1["low"], "bottom": c3["high"], "index": i})

        bprs = []
        for bull in bullish_fvgs:
          for bear in bearish_fvgs:
            bpr_top = min(bull["top"], bear["top"])
            bpr_bottom = max(bull["bottom"], bear["bottom"])
            if bpr_bottom < bpr_top:
              bprs.append({
                  "top": bpr_top,
                  "bottom": bpr_bottom,
                  "maxIndex": max(bull["index"], bear["index"]),
              })

        derniere_index = len(bougies) - 1
        derniere_bougie = bougies[derniere_index]
        bpr_touche = False

        for bpr in bprs:
          if bpr["maxIndex"] < derniere_index:
            if (
                derniere_bougie["low"] <= bpr["top"]
                and derniere_bougie["high"] >= bpr["bottom"]
            ):
              bpr_touche = True

        if bpr_touche:
          envoyer_telegram(
              f"🎯 Prix de retour dans un BPR détecté sur {symbole} (1h)"
          )
    except Exception as e:
      print(f"Erreur BPR {symbole}: {e}")


if __name__ == "__main__":
  # 1. Bulles en 15 minutes
  verifier_bulles("15m")
  # 2. Bulles en 1 heure
  verifier_bulles("1h")
  # 3. BPR en 1 heure
  verifier_bpr()
