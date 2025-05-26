import os
import json
import time
import threading
import traceback
from ta.volatility import AverageTrueRange
import pandas as pd
from kucoin.ws_client import KucoinWsClient

from config import REST_CLIENT, SYMBOL, GRID_SIZE, BUDGET, ADJUST_INTERVAL, LEVERAGE, STOP_LOSS, TAKE_PROFIT, DATA_DIR, SANDBOX

HISTORY_FILE = os.path.join(DATA_DIR, "fill_history.json")

class AdaptiveGridStrategy:
    def __init__(self):
        # Charge l'historique existant
        if os.path.isdir(DATA_DIR) and os.path.isfile(HISTORY_FILE):
            with open(HISTORY_FILE, 'r') as f:
                self.fill_history = json.load(f)
        else:
            self.fill_history = []

        self.orders = {}
        self.pending_positions = {}
        self.running = False

    def save_history(self):
        try:
            with open(HISTORY_FILE, 'w') as f:
                json.dump(self.fill_history, f, indent=2)
        except Exception as e:
            print(f"Erreur écriture historique: {e}")

    def fetch_klines(self, interval='1min', limit=50):
        data = REST_CLIENT.get_kline_data(symbol=SYMBOL, klineType=interval, limit=limit)
        df = pd.DataFrame(data, columns=['time','open','high','low','close','volume']).astype(float)
        return df

    def calc_bounds(self):
        df = self.fetch_klines()
        atr = AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=14).average_true_range().iloc[-1]
        mid = df['close'].iloc[-1]
        lower = mid - atr * GRID_SIZE / 2
        upper = mid + atr * GRID_SIZE / 2
        return lower, upper

    def build_grid(self):
        lower, upper = self.calc_bounds()
        step = (upper - lower) / GRID_SIZE
        mid = (lower + upper) / 2
        qty = BUDGET / mid
        print(
            f"💡 Grille définie :\n"
            f"  • Borne basse = {lower:.2f}  • Borne haute = {upper:.2f}\n"
            f"  • Spread = {upper-lower:.2f}  • Increment = {step:.2f}\n"
            f"  • Orders = {GRID_SIZE+1}  • Qty/order = {qty:.6f}"
        )
        for i in range(GRID_SIZE + 1):
            price = lower + step * i
            side = 'buy' if i < GRID_SIZE/2 else 'sell'
            self.place_order(price, qty, side)

    def place_order(self, price, size, side, mirror=False, parent_id=None):
        try:
            resp = REST_CLIENT.create_limit_order(
                symbol=SYMBOL, side=side,
                size=str(size), price=str(price),
                leverage=LEVERAGE, stop=False
            )
            oid = resp['orderId']
            ts = time.time()
            self.orders[oid] = {
                'side': side, 'price': price, 'size': size,
                'timestamp': ts, 'mirror': mirror, 'parent_id': parent_id
            }
            print(f"Placed {side} @ {price:.2f} (mirror={mirror}), id={oid}")
            return oid
        except Exception as e:
            print(f"Error placing {side} order @ {price}: {e}")
            traceback.print_exc()

    def on_filled(self, order_id, side, price, size):
        info = self.orders.pop(order_id, None)
        if not info:
            return
        ts = time.time()
        if not info['mirror']:
            self.pending_positions[order_id] = {
                'side': side, 'price': price, 'size': size, 'timestamp': info['timestamp']
            }
            mirror_side = 'sell' if side=='buy' else 'buy'
            mirror_price = price * (1 + TAKE_PROFIT) if mirror_side=='sell' else price * (1 - TAKE_PROFIT)
            self.place_order(mirror_price, size, mirror_side, mirror=True, parent_id=order_id)
        else:
            pid = info['parent_id']
            open_info = self.pending_positions.pop(pid, None)
            if open_info:
                profit = (price - open_info['price']) * size if open_info['side']=='buy' else (open_info['price'] - price) * size
                trade = {
                    'open_order_id': pid, 'open_side': open_info['side'],
                    'open_price': open_info['price'], 'open_time': open_info['timestamp'],
                    'close_price': price, 'close_time': ts,
                    'size': size, 'profit': profit
                }
                self.fill_history.append(trade)
                self.save_history()
                print(f"✅ Trade clos: profit {profit:.4f} USDT")

    def run_ws(self):
        def message_handler(msg):
            try:
                if msg.get('type') == 'match':
                    data = msg['data']
                    if data['symbol'] == SYMBOL and data['side'] in ['buy','sell']:
                        oid = data['orderId']
                        if oid in self.orders:
                            self.on_filled(oid, data['side'], float(data['price']), float(data['size']))
            except Exception as e:
                print(f"WS handler error: {e}")
                traceback.print_exc()

        ku_ws = KucoinWsClient(on_message=message_handler, is_sandbox=SANDBOX)
        ku_ws.subscribe_trade(symbol=SYMBOL)

    def start(self):
        self.running = True
        print("🔄 Initialisation de la grille")
        threading.Thread(target=self.run_ws, daemon=True).start()
        self.build_grid()
        while self.running:
            time.sleep(ADJUST_INTERVAL * 60)
            print("🔄 Mise à jour de la grille (recalcul ATR)")
            for oid in list(self.orders.keys()):
                try:
                    REST_CLIENT.cancel_order(order_id=oid)
                except:
                    pass
            self.orders.clear()
            self.build_grid()

    def stop(self):
        self.running = False
        print("Strategy stopped.")
