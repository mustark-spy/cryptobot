import os
from dotenv import load_dotenv
from kucoin.client import Trade

load_dotenv()

# Mode sandbox (test)
SANDBOX = os.getenv("SANDBOX", "false").lower() == "true"

# Niveau de logs à remonter sur Telegram : DEBUG, INFO, ERROR
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# KuCoin API
API_KEY = os.getenv("KUCOIN_API_KEY")
API_SECRET = os.getenv("KUCOIN_API_SECRET")
API_PASSPHRASE = os.getenv("KUCOIN_API_PASSPHRASE")

# Telegram
TG_TOKEN = os.getenv("TELEGRAM_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

# Paramètres de la stratégie
SYMBOL = os.getenv("SYMBOL", "BTC-USDT")
LEVERAGE = int(os.getenv("LEVERAGE", 10))
GRID_SIZE = int(os.getenv("GRID_SIZE", 10))
ADJUST_INTERVAL = int(os.getenv("ADJUST_INTERVAL_MIN", 15))
STOP_LOSS = float(os.getenv("STOP_LOSS", 0.01))
TAKE_PROFIT = float(os.getenv("TAKE_PROFIT", 0.02))
BUDGET = float(os.getenv("BUDGET", 1000.0))

# Répertoire pour stocker les données
DATA_DIR = os.getenv("DATA_DIR", "./data")
os.makedirs(DATA_DIR, exist_ok=True)

# Client KuCoin
REST_CLIENT = Trade(
    key=API_KEY,
    secret=API_SECRET,
    passphrase=API_PASSPHRASE,
    sandbox=SANDBOX
)
