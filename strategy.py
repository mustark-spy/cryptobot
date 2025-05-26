import os
import json
import time
import threading
from datetime import datetime
import pandas as pd
from ta.volatility import AverageTrueRange

from config import CLIENT, SYMBOL, GRID_SIZE, BUDGET, ADJUST_INTERVAL, LEVERAGE, STOP_LOSS, TAKE_PROFIT, DATA_DIR
from kucoin_universal_sdk.generate.futures.trade.create_order import CreateOrderReqBuilder
from kucoin_universal_sdk.generate.futures.trade.cancel_order import CancelOrderReqBuilder
from kucoin_universal_sdk.generate.futures.market.get_candles import GetHistoricCandlesReqBuilder

HISTORY_FILE = os.path.join(DATA_DIR, "fill_history.json")

class AdaptiveGridStrategy:
    def __init__(self):
        if os.path.isfile(HISTORY_FILE):
            with open(HISTORY_FILE, 'r') as f:
                self.fill_history = json.load(f)
        else:
            self.fill_history = []

        self.orders = {}
        self.pending = {}
        self.running = False

    def save_history(self):
        with open(HISTORY_FILE, 'w') as f:
            json.dump(self.fill_history, f, indent=2)

    def fetch_klines(self):
        now = int(time.time())
        past = now - ADJUST_INTERVAL * 60 * 2
        market_api = CLIENT.rest_service().get_futures_market_api()
        req = GetHistoricCandlesReqBuilder()             .set_symbol(SYMBOL)             .set_start_at(str(past))             .set_end_at(str(now))             .set_granularity("60")             .build()
        resp = market_api.get_historic_candles(req)
        df = pd.DataFrame(resp.data, columns=['time','open','close','high','low','volume']).astype(float)
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
        print(f"💡 Grille définie : Basse={lower:.2f}, Haute={upper:.2f}, Spread={(upper-lower):.2f}, Increment={step:.2f}, Orders={GRID_SIZE+1}, Qty/order={qty:.6f}")
        for i in range(GRID_SIZE + 1):
            price = lower + step * i
            side = 'buy' if i < GRID_SIZE/2 else 'sell'
            self.place_order(price, qty, side)

    def place_order(self, price, size, side, mirror=False, parent_id=None):
        order_api = CLIENT.rest_service().get_futures_trade_api()
        req = CreateOrderReqBuilder()             .set_client_oid(str(int(time.time()*1000)))             .set_symbol(SYMBOL)             .set_side(side)             .set_type("limit")             .set_price(str(price))             .set_size(str(size))             .set_leverage(str(LEVERAGE))             .build()
        resp = order_api.create_order(req)
        oid = resp.order_id
        self.orders[oid] = {'side': side, 'price': price, 'size': size, 'mirror': mirror, 'parent_id': parent_id}
        print(f"Placed {side}@{price:.2f} id={oid}")

    def on_filled(self, trade):
        oid = trade['order_id']
        info = self.orders.pop(oid, None)
        if not info:
            return
        if not info['mirror']:
            self.pending[oid] = info
            mirror_side = 'sell' if info['side']=='buy' else 'buy'
            mirror_price = info['price']*(1+TAKE_PROFIT) if mirror_side=='sell' else info['price']*(1-TAKE_PROFIT)
            self.place_order(mirror_price, info['size'], mirror_side, mirror=True, parent_id=oid)
        else:
            open_info = self.pending.pop(info['parent_id'], None)
            if open_info:
                profit = (info['price'] - open_info['price']) * info['size'] if open_info['side']=='buy' else (open_info['price'] - info['price']) * info['size']
                record = {
                    'order_id': oid,
                    'side': open_info['side'],
                    'open_price': open_info['price'],
                    'close_price': info['price'],
                    'size': info['size'],
                    'profit': profit,
                    'timestamp': int(time.time())
                }
                self.fill_history.append(record)
                self.save_history()
                print(f"✅ Trade clos: profit={profit:.4f} USDT")

    def poll_fills(self):
        seen = set()
        trade_api = CLIENT.rest_service().get_futures_trade_api()
        while self.running:
            trades = trade_api.get_fills({"symbol": SYMBOL}).data
            for t in trades:
                tid = t['trade_id']
                if tid not in seen:
                    seen.add(tid)
                    self.on_filled({'order_id': t['order_id'], 'price': float(t['price']), 'size': float(t['size']), 'side': t['side']})
            time.sleep(5)

    def start(self):
        self.running = True
        threading.Thread(target=self.poll_fills, daemon=True).start()
        self.build_grid()
        while self.running:
            time.sleep(ADJUST_INTERVAL * 60)
            print("🔄 Rebuild grille")
            cancel_api = CLIENT.rest_service().get_futures_trade_api()
            for oid in list(self.orders):
                req = CancelOrderReqBuilder().set_symbol(SYMBOL).set_order_id(oid).build()
                cancel_api.cancel_order(req)
            self.orders.clear()
            self.build_grid()

    def stop(self):
        self.running = False
        print("Strategy stopped")
