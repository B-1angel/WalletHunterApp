# main.py
from kivy.core.window import Window
Window.clearcolor = (0.09, 0.09, 0.09, 1)  # dark background

from kivy.lang import Builder
from kivy.clock import Clock
from kivy.properties import StringProperty, BooleanProperty, NumericProperty, ListProperty
from kivy.uix.recycleview import RecycleView
from kivy.utils import platform

from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.snackbar import Snackbar

import threading
import queue
import time
import os
import logging
import sys
import traceback
import requests
from mnemonic import Mnemonic
import bip32utils
from concurrent.futures import ThreadPoolExecutor
from collections import deque

# ---------- Core logic globals ----------
log_queue = queue.Queue()
found_wallets = []
checked_count = 0
counter_lock = threading.Lock()
running = False
seen_phrases = deque(maxlen=100000)
btc_price_usd = None
session = requests.Session()

# ---------- Logger (sends to queue) ----------
logger = logging.getLogger("WalletHunter")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%H:%M:%S | %(levelname)s | %(message)s")

class QueueHandler(logging.Handler):
    def emit(self, record):
        try:
            msg = self.format(record)
            log_queue.put((record.levelno, msg))
        except Exception:
            log_queue.put((logging.ERROR, "Logging failure:\n" + traceback.format_exc()))

qhandler = QueueHandler()
qhandler.setFormatter(formatter)
logger.addHandler(qhandler)

# redirect stdout/stderr to logger
class StdoutToLogger:
    def __init__(self, logger_func):
        self.logger_func = logger_func
        self._buffer = ""

    def write(self, s):
        self._buffer += s
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            if line.strip():
                self.logger_func(line)

    def flush(self):
        if self._buffer.strip():
            self.logger_func(self._buffer.strip())
        self._buffer = ""

sys.stdout = StdoutToLogger(lambda s: logger.info(f"[print] {s}"))
sys.stderr = StdoutToLogger(lambda s: logger.error(f"[stderr] {s}"))

# ---------- Blockchain helper funcs ----------
def fetch_btc_price():
    global btc_price_usd
    try:
        r = session.get("https://api.coindesk.com/v1/bpi/currentprice/BTC.json", timeout=7)
        if r.status_code == 200:
            btc_price_usd = r.json()["bpi"]["USD"]["rate_float"]
            logger.info(f"BTC price updated: ${btc_price_usd:.2f}")
    except Exception as e:
        btc_price_usd = None
        logger.warning(f"BTC price fetch failed: {e}")

def check_balance_blockstream(address):
    try:
        r = session.get(f"https://blockstream.info/api/address/{address}", timeout=7)
        if r.status_code == 200:
            data = r.json()
            return data.get("chain_stats", {}).get("funded_txo_sum", 0) - data.get("chain_stats", {}).get("spent_txo_sum", 0)
    except Exception:
        pass
    return 0

def save_wallet(log):
    try:
        with open("found_wallets.txt", "a", encoding="utf-8") as f:
            f.write(log + "\n")
    except Exception as e:
        logger.error(f"Failed to save wallet: {e}")

def check_address_balance(seed_phrase, child_index):
    global checked_count, seen_phrases
    try:
        if seed_phrase in seen_phrases:
            return
        seen_phrases.append(seed_phrase)

        mnemo = Mnemonic("english")
        seed_bytes = mnemo.to_seed(seed_phrase, passphrase="")
        root_key = bip32utils.BIP32Key.fromEntropy(seed_bytes)
        child_key = (
            root_key.ChildKey(44 + bip32utils.BIP32_HARDEN)
            .ChildKey(0 + bip32utils.BIP32_HARDEN)
            .ChildKey(0 + bip32utils.BIP32_HARDEN)
            .ChildKey(0)
            .ChildKey(child_index)
        )
        address = child_key.Address()
        privkey = child_key.WalletImportFormat()

        balance = check_balance_blockstream(address)
        with counter_lock:
            checked_count += 1

        logger.info(f"Wallet Checked: {seed_phrase} | Balance: {balance or 0}")

        if balance and balance > 0:
            now = time.time()
            if not hasattr(check_address_balance, "_last_price") or now - check_address_balance._last_price > 60:
                fetch_btc_price()
                check_address_balance._last_price = now

            usd_val = f"${(balance/1e8)*btc_price_usd:.2f}" if btc_price_usd else "USD N/A"
            log = f"FOUND | {address} | {balance/1e8:.8f} BTC ({usd_val}) | Seed: {seed_phrase}"
            found_wallets.append(log)
            save_wallet(log)
            logger.info(log)

    except Exception:
        tb = traceback.format_exc()
        logger.error(f"Failed to check balance:\n{tb}")

def generator_worker():
    global running
    mnemo = Mnemonic("english")
    with ThreadPoolExecutor(max_workers=12) as executor:
        while running:
            seed_phrase = mnemo.generate(128)
            # submit multiple child indices per seed phrase
            for i in range(20):
                executor.submit(check_address_balance, seed_phrase, i)
            time.sleep(0.05)  # small pacing to avoid runaway submit

# ---------- UI KV ----------
KV = '''
ScreenManager:
    LoginScreen:
    MainScreen:

<LoginScreen>:
    name: "login"
    md_bg_color: app.theme_cls.primary_dark
    BoxLayout:
        orientation: "vertical"
        padding: dp(20)
        spacing: dp(18)
        MDCard:
            size_hint: None, None
            size: dp(220), dp(220)
            pos_hint: {"center_x": .5}
            elevation: 6
            padding: dp(12)
            BoxLayout:
                orientation: "vertical"
                spacing: dp(8)
                Image:
                    source: "logo.png"
                    allow_stretch: True
                MDLabel:
                    text: "Wallet Hunter"
                    halign: "center"
                    theme_text_color: "Custom"
                    text_color: (1,1,1,1)
                    font_style: "H5"
        MDTextField:
            id: username
            hint_text: "Username"
            icon_right: "account"
            pos_hint: {"center_x": .5}
            size_hint_x: 0.9
        MDTextField:
            id: password
            hint_text: "Password"
            password: True
            icon_right: "lock"
            pos_hint: {"center_x": .5}
            size_hint_x: 0.9
        MDRaisedButton:
            text: "Login"
            pos_hint: {"center_x": .5}
            on_release: app.do_login(username.text, password.text)
        Widget:
            size_hint_y: None
            height: dp(20)

<MainScreen>:
    name: "main"
    BoxLayout:
        orientation: "vertical"
        MDToolbar:
            title: "Wallet Hunter"
            md_bg_color: app.theme_cls.primary_dark
            left_action_items: [["menu", lambda x: None]]
        BoxLayout:
            orientation: "vertical"
            padding: dp(8)
            spacing: dp(6)

            BoxLayout:
                size_hint_y: None
                height: dp(40)
                spacing: dp(8)
                MDLabel:
                    id: checked_label
                    text: "Checked: 0"
                    halign: "left"
                MDLabel:
                    id: found_label
                    text: "Found: 0"
                    halign: "right"

            BoxLayout:
                size_hint_y: None
                height: dp(40)
                spacing: dp(8)
                MDIconButton:
                    icon: "play-circle"
                    user_font_size: "28sp"
                    on_release: app.start_scan()
                    theme_text_color: "Custom"
                    text_color: (0,1,0,1)
                MDIconButton:
                    icon: "stop-circle"
                    user_font_size: "28sp"
                    on_release: app.stop_scan()
                    theme_text_color: "Custom"
                    text_color: (1,0,0,1)
                MDIconButton:
                    icon: "download"
                    user_font_size: "22sp"
                    on_release: app.open_found_wallets()
                MDIconButton:
                    icon: "logout"
                    user_font_size: "22sp"
                    on_release: app.logout()

            BoxLayout:
                orientation: "horizontal"
                spacing: dp(8)

                MDCard:
                    size_hint_x: .6
                    md_bg_color: (0.12,0.12,0.12,1)
                    padding: dp(8)
                    ScrollView:
                        do_scroll_x: False
                        GridLayout:
                            id: log_grid
                            cols: 1
                            size_hint_y: None
                            height: self.minimum_height
                            row_default_height: None

                MDCard:
                    size_hint_x: .4
                    md_bg_color: (0.12,0.12,0.12,1)
                    padding: dp(8)
                    BoxLayout:
                        orientation: "vertical"
                        spacing: dp(6)
                        MDLabel:
                            text: "Found Items"
                            halign: "center"
                        ScrollView:
                            do_scroll_x: False
                            RecycleView:
                                id: found_rv
                                viewclass: "MDLabel"
                                RecycleBoxLayout:
                                    default_size: None, dp(40)
                                    default_size_hint: 1, None
                                    size_hint_y: None
                                    height: self.minimum_height
                                    orientation: "vertical"
                                    spacing: dp(4)

        Widget:
            size_hint_y: None
            height: dp(8)
'''

# ---------- Screens ----------
class LoginScreen(MDScreen):
    pass

class MainScreen(MDScreen):
    pass

# ---------- App ----------
class WalletHunterApp(MDApp):
    username = StringProperty("")
    logged_in = BooleanProperty(False)
    checked = NumericProperty(0)
    found_count = NumericProperty(0)
    logs = ListProperty([])
    found_list = ListProperty([])

    def build(self):
        self.title = "Wallet Hunter"
        # Dark theme
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "BlueGray"
        screen = Builder.load_string(KV)
        # Schedule log flush
        Clock.schedule_interval(self.flush_logs, 0.25)
        return screen

    def do_login(self, user, pwd):
        # fake login (visual only) - accept any non-empty or set a fixed pair
        if (user and pwd) or (user == "user" and pwd == "1234"):
            self.logged_in = True
            self.root.current = "main"
            Snackbar(text="Welcome!").open()
        else:
            Snackbar(text="Enter username and password").open()

    def logout(self):
        self.logged_in = False
        self.root.current = "login"

    def start_scan(self):
        global running
        if running:
            Snackbar(text="Already running").open()
            return
        running = True
        threading.Thread(target=generator_worker, daemon=True).start()
        logger.info("[+] Started scanning")

    def stop_scan(self):
        global running
        if not running:
            Snackbar(text="Not running").open()
            return
        running = False
        logger.info("[-] Stopped scanning")

    def open_found_wallets(self):
        try:
            if os.path.exists("found_wallets.txt"):
                # On Android, open with default app is platform dependent; just show path
                Snackbar(text="Saved found_wallets.txt to app folder").open()
            else:
                Snackbar(text="No found wallets saved yet").open()
        except Exception:
            Snackbar(text="Cannot open file").open()

    def flush_logs(self, dt):
        # update counters
        global checked_count, found_wallets
        try:
            self.root.get_screen("main").ids.checked_label.text = f"Checked: {checked_count}"
            self.root.get_screen("main").ids.found_label.text = f"Found: {len(found_wallets)}"
        except Exception:
            pass

        # flush log_queue into grid
        grid = self.root.get_screen("main").ids.log_grid
        updated = False
        while not log_queue.empty():
            level, msg = log_queue.get()
            # create label entry
            from kivymd.uix.label import MDLabel
            color = (0.8,0.8,0.8,1)
            if "FOUND" in msg:
                color = (0.4,1,0.4,1)
            elif level >= logging.ERROR:
                color = (1,0.4,0.4,1)
            lbl = MDLabel(text=msg, size_hint_y=None, height=dp(28) if hasattr(self, 'dp') else 28, theme_text_color="Custom", text_color=color)
            grid.add_widget(lbl)
            updated = True

        # limit log lines to last N
        if updated and grid.children:
            # keep only last 200 logs for memory
            while len(grid.children) > 200:
                grid.remove_widget(grid.children[-1])

        # update found rv
        rv = self.root.get_screen("main").ids.found_rv
        rv.data = [{"text": s} for s in found_wallets[-200:][::-1]]

# helper for dp usage in label height
def dp(x):
    try:
        from kivy.metrics import dp as _dp
        return _dp(x)
    except Exception:
        return x

if __name__ == "__main__":
    WalletHunterApp().run()