import os
from dotenv import load_dotenv
from kucoin_universal_sdk.api import DefaultClient
from kucoin_universal_sdk.model import ClientOptionBuilder, TransportOptionBuilder, GLOBAL_FUTURES_API_ENDPOINT

load_dotenv()

SANDBOX = os.getenv("SANDBOX", "false").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

API_KEY = os.getenv("KUCOIN_API_KEY")
API_SECRET = os.getenv("KUCOIN_API_SECRET")
API_PASSPHRASE = os.getenv("KUCOIN_API_PASSPHRASE")

# Telegram credentials
TG_TOKEN = os.getenv("TELEGRAM_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# SDK setup
transport_option = TransportOptionBuilder().set_keep_alive(True).set_max_pool_size(10).build()
client_option = (
    ClientOptionBuilder()
    .set_key(API_KEY)
    .set_secret(API_SECRET)
    .set_passphrase(API_PASSPHRASE)
    .set_futures_endpoint(GLOBAL_FUTURES_API_ENDPOINT)
    .set_transport_option(transport_option)
    .build()
)
CLIENT = DefaultClient(client_option)

# Strategy parameters
SYMBOL = os.getenv("SYMBOL", "BTC-USDT")
LEVERAGE = int(os.getenv("LEVERAGE", 10))
GRID_SIZE = int(os.getenv("GRID_SIZE", 10))
ADJUST_INTERVAL = int(os.getenv("ADJUST_INTERVAL_MIN", 15))
STOP_LOSS = float(os.getenv("STOP_LOSS", 0.01))
TAKE_PROFIT = float(os.getenv("TAKE_PROFIT", 0.02))
BUDGET = float(os.getenv("BUDGET", 1000.0))

# Persistence directory
DATA_DIR = os.getenv("DATA_DIR", "./data")
os.makedirs(DATA_DIR, exist_ok=True)
