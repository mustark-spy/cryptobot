import threading
import requests
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from config import TG_TOKEN, TG_CHAT_ID, LOG_LEVEL, SANDBOX
from strategy import AdaptiveGridStrategy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

strategy = AdaptiveGridStrategy()

app = ApplicationBuilder().token(TG_TOKEN).build()

def send_telegram(msg, level="INFO"):
    levels = {"DEBUG":10, "INFO":20, "ERROR":40}
    if levels.get(level, 0) >= levels.get(LOG_LEVEL, 20):
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT_ID, "text": msg}
        )

import builtins
_orig_print = builtins.print
def print(*args, level="INFO", **kwargs):
    _orig_print(*args, **kwargs)
    send_telegram(" ".join(map(str,args)), level=level)
builtins.print = print

async def pnl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total = sum(r['profit'] for r in strategy.fill_history)
    open_count = len(strategy.pending)
    hist = strategy.fill_history[-10:]
    lines = [
        "📊 *Statut PnL*",
        f"Realized PnL: `{total:.4f}` USDT",
        f"Open positions: `{open_count}`",
        "",        "*Derniers trades*"
    ]
    for r in hist:
        ts = datetime.fromtimestamp(r['timestamp']).strftime('%Y-%m-%d %H:%M')
        lines.append(f"{ts} | {r['side']} {r['size']:.6f}@{r['open_price']:.2f}→{r['close_price']:.2f} (`{r['profit']:.4f}`)")    await update.message.reply_markdown("".join(lines))

app.add_handler(CommandHandler("pnl", pnl))

if __name__ == "__main__":
    start = "🤖 Bot démarre" + " (SANDBOX)" if SANDBOX else "🤖 Bot démarre"
    print(start, level="INFO")
    threading.Thread(target=strategy.start, daemon=True).start()    app.run_polling()
