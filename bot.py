import threading
import logging
from datetime import datetime
from telegram.ext import Updater, CommandHandler
from config import TG_TOKEN, TG_CHAT_ID, SANDBOX, LOG_LEVEL
from strategy import AdaptiveGridStrategy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

strategy = AdaptiveGridStrategy()

updater = Updater(token=TG_TOKEN, use_context=True)
dp = updater.dispatcher

def send_telegram(msg, level="INFO"):
    try:
        levels = {"DEBUG":10, "INFO":20, "ERROR":40}
        if levels.get(level, 0) >= levels.get(LOG_LEVEL, 20):
            updater.bot.send_message(chat_id=TG_CHAT_ID, text=msg)
    except Exception as e:
        logger.error(f"Erreur TG: {e}")

import builtins
_orig_print = builtins.print
def print(*args, level="INFO", **kwargs):
    _orig_print(*args, **kwargs)
    send_telegram(" ".join(map(str, args)), level=level)
builtins.print = print

def pnl_command(update, context):
    total_pnl = sum(t['profit'] for t in strategy.fill_history)
    open_pos = len(strategy.pending_positions)
    history = strategy.fill_history[-10:]
    lines = [
        "📊 *Statut PnL*",
        f"Realized PnL : `{total_pnl:.4f}` USDT",
        f"Positions ouvertes : `{open_pos}`",
        "",
        f"*Historique (derniers {len(history)})*"
    ]
    for t in history:
        ot = datetime.fromtimestamp(t['open_time']).strftime('%Y-%m-%d %H:%M')
        lines.append(
            f"{ot} | {t['open_side']} {t['size']:.6f}@{t['open_price']:.2f} → {t['close_price']:.2f}"
            f" (`{t['profit']:.4f}`)"
        )
    update.message.reply_markdown("
".join(lines))

dp.add_handler(CommandHandler('pnl', pnl_command))

if __name__ == "__main__":
    start_msg = "🤖 Démarrage du bot de trading Grid Adaptive"
    if SANDBOX:
        start_msg += " (SANDBOX MODE)"
    print(start_msg)
    threading.Thread(target=strategy.start, daemon=True).start()
    updater.start_polling()
    updater.idle()
