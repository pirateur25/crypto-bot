import os
import requests

# Vos 17 actifs
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

bot_token = os.environ.get("BOT_TOKEN")
chat_id = os.environ.get("CHAT_ID")


def envoyer_telegram(message):
  if bot_token and chat_id:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": message})


def verifier_bulles_5m():
  for symbole in symboles:
    try:
      # Analyse sur l'unité 5 minutes
      url = f"https://api.binance.com/api/v3/klines?symbol={symbole}&interval=5m&limit=21"
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
              f"⚡ [5m] Bulle Apesanteur HAUSSIÈRE sur {symbole}"
          )
        elif high < bande_inf:
          envoyer_telegram(
              f"🔻 [5m] Bulle Apesanteur BAISSIÈRE sur {symbole}"
          )
    except Exception as e:
      print(f"Erreur Bulles 5m {symbole}: {e}")


if __name__ == "__main__":
  verifier_bulles_5m()
  
