import threading
import logging
import os
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from config import TG_TOKEN, TG_CHAT_ID, SANDBOX, LOG_LEVEL
from strategy import AdaptiveGridStrategy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

strategy = AdaptiveGridStrategy()

# Initialise l'application Telegram
app = ApplicationBuilder().token(TG_TOKEN).build()

def send_telegram(msg: str, level: str = "INFO"):
    """Envoie un message sur TG si son niveau >= LOG_LEVEL."""
    levels = {"DEBUG": 10, "INFO": 20, "ERROR": 40}
    if levels.get(level, 0) >= levels.get(LOG_LEVEL, 20):
        app.bot.send_message(chat_id=TG_CHAT_ID, text=msg)

# Détournement de print() pour router vers Telegram
import builtins
_orig_print = builtins.print
def print(*args, level="INFO", **kwargs):
    _orig_print(*args, **kwargs)
    send_telegram(" ".join(map(str, args)), level=level)
builtins.print = print

async def pnl_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler de /pnl : résumé du PnL et historique."""
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

    await update.message.reply_markdown("\n".join(lines))

# Enregistre le handler
app.add_handler(CommandHandler('pnl', pnl_command))

if __name__ == "__main__":
    start_msg = "🤖 Démarrage du bot de trading Grid Adaptive"
    if SANDBOX:
        start_msg += " (SANDBOX MODE)"
    print(start_msg, level="INFO")

    # Lancer la stratégie en arrière-plan
    threading.Thread(target=strategy.start, daemon=True).start()

    # Démarrer le bot Telegram
    app.run_polling()
