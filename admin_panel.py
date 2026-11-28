"""
Default dev account : dev@admin.local / Dev@12345
"""

import os
import csv
import json
import hashlib
import secrets
import datetime
import threading
import traceback
import math
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog

try:
    from pymongo import MongoClient
    MONGO_OK = True
except Exception:
    MONGO_OK = False

try:
    import numpy as np
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
    from sklearn.impute import SimpleImputer
    SKLEARN_OK = True
except Exception:
    np = None
    IsolationForest = StandardScaler = SimpleImputer = None
    SKLEARN_OK = False

try:
    import torch
    from torch import nn
    TORCH_OK = True
except Exception:
    torch = nn = None
    TORCH_OK = False


MONGO_URI = os.environ.get("SMS_MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.environ.get("SMS_DB", "student_management")

# ------------------------------- dark dev theme -------------------------------
DARK = "#0a0f1e"
PANEL = "#131a2e"
PANEL_2 = "#0f1526"
LINE = "#243050"
TEXT = "#e6ecff"
MUT = "#8b97b8"
CYAN = "#22d3ee"
PURPLE = "#a855f7"
GREEN = "#22c55e"
AMBER = "#f59e0b"
RED = "#ef4444"
SIDEBAR_W = 240

NAV = [
    ("overview", "Overview", "◈"),
    ("users", "Users", "◉"),
    ("students", "Students", "◍"),
    ("audit", "Audit Log", "◷"),
    ("broadcast", "Broadcast", "◎"),
    ("flags", "Feature Flags", "⚑"),
    ("data", "Data Tools", "▤"),
    ("console", "Query Console", "⌘"),
    ("ml", "AI / ML Insights", "✦"),
]

COLLECTIONS = ["users", "students", "teachers", "admissions", "courses", "branches",
               "attendance", "fees", "examinations", "results", "timetable",
               "notifications", "settings", "admins"]


# --------------------------------- helpers ------------------------------------
def hash_pwd(p, salt=None):
    salt = salt or secrets.token_hex(16)
    return {"salt": salt, "hash": hashlib.pbkdf2_hmac(
        "sha256", p.encode(), salt.encode(), 180_000).hex()}


def verify_pwd(p, rec):
    try:
        if not rec:
            return False
        if isinstance(rec, str):
            return secrets.compare_digest(p, rec)
        return bool(rec.get("salt") and secrets.compare_digest(
            hash_pwd(p, rec["salt"])["hash"], rec["hash"]))
    except Exception:
        return False


def now_iso():
    return datetime.datetime.now().isoformat()


class MemCol:
    def __init__(self):
        self.d = {}

    def find_one(self, q):
        if "_id" in q:
            direct = self.d.get(str(q["_id"]))
            if direct is not None:
                return direct
            return next((v for k, v in self.d.items() if str(k) == str(q["_id"])), None)
        for v in self.d.values():
            if all(v.get(k) == val for k, val in q.items()):
                return v
        return None

    def find(self, q=None, limit=0):
        out = [v for v in self.d.values() if all(v.get(k) == val for k, val in (q or {}).items())]
        return out[:limit] if limit else out

    def insert_one(self, doc):
        doc = dict(doc)
        doc.setdefault("_id", f"m-{secrets.token_hex(6)}")
        self.d[doc["_id"]] = doc

    def update_one(self, q, upd):
        r = self.find_one(q)
        if r:
            r.update(upd.get("$set", {}))

    def delete_one(self, q):
        r = self.find_one(q)
        if r:
            self.d.pop(r["_id"], None)

    def delete_many(self, q=None):
        if not q:
            self.d.clear()
            return
        for r in self.find(q):
            self.d.pop(r["_id"], None)

    def count_documents(self, q=None):
        return len(self.find(q))

    def create_index(self, *a, **k):
        pass


class DB:
    def __init__(self):
        self.online = False
        self.client = None
        self._mem = {}
        if MONGO_OK:
            try:
                self.client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
                self.client.admin.command("ping")
                self.db = self.client[DB_NAME]
                self.online = True
            except Exception:
                self.online = False

    def col(self, n):
        return self.db[n] if self.online else self._mem.setdefault(n, MemCol())

    def close(self):
        try:
            if self.client:
                self.client.close()
        except Exception:
            pass


# --------------------------------- widgets ------------------------------------
class Card(tk.Frame):
    def __init__(self, master, pad=16, **kw):
        super().__init__(master, bg=PANEL, highlightthickness=1,
                         highlightbackground=LINE, **kw)
        self.body = tk.Frame(self, bg=PANEL)
        self.body.pack(fill="both", expand=True, padx=pad, pady=pad)


class ScrollArea(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=DARK)
        self.canvas = tk.Canvas(self, bg=DARK, highlightthickness=0, bd=0)
        bar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=bar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")
        self.inner = tk.Frame(self.canvas, bg=DARK)
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>",
                        lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>",
                         lambda e: self.canvas.itemconfigure(self._win, width=e.width))

    def scroll(self, u):
        self.canvas.yview_scroll(int(u), "units")


# ================================ ADMIN PANEL =================================
class AdminPanel(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SMS — Developer Console")
        self.geometry("1440x900")
        self.minsize(1050, 650)
        self.configure(bg=DARK)
        try:
            self.state("zoomed")
        except tk.TclError:
            pass

        self.db = DB()
        self.admin = None
        self.active = None
        self.pages = {}
        self.nav_buttons = {}
        self.acc = {}
        self.alive = True
        self.preview = {}

        self._style()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._ensure_admin()
        self._show_login()

    # ------------------------------- styling ---------------------------------
    def _style(self):
        s = ttk.Style(self)
        try:
            s.theme_use("clam")
        except Exception:
            pass
        s.configure("Treeview", background=PANEL_2, fieldbackground=PANEL_2,
                    foreground=TEXT, rowheight=32, borderwidth=0, font=("Segoe UI", 9))
        s.configure("Treeview.Heading", padding=(8, 9))
        s.configure("TCombobox", fieldbackground=PANEL_2, background=PANEL_2,
                    foreground=TEXT, arrowcolor=CYAN)
        s.configure("Treeview.Heading", background=PANEL, foreground=CYAN,
                    font=("Consolas", 9, "bold"), borderwidth=0)
        s.map("Treeview", background=[("selected", "#1e2b4a")], foreground=[("selected", TEXT)])
        s.configure("TScrollbar", background=LINE, troughcolor=DARK, borderwidth=0)

    # --------------------------- admin bootstrap ------------------------------
    def _ensure_admin(self):
        """Guarantee the default developer account exists AND is usable."""
        email = "dev@admin.local"
        try:
            rec = self.db.col("admins").find_one({"email": email})
            if rec is None:
                self.db.col("admins").insert_one({
                    "email": email, "name": "Developer",
                    "password": hash_pwd("Dev@12345"), "created_at": now_iso(),
                })
                return
            pwd = rec.get("password")
            if not isinstance(pwd, dict) or not pwd.get("salt"):
                self.db.col("admins").update_one(
                    {"email": email}, {"$set": {"password": hash_pwd("Dev@12345")}})
        except Exception:
            traceback.print_exc()

        try:
            if not self.db.col("settings").find_one({"_id": "app"}):
                self.db.col("settings").insert_one({
                    "_id": "app", "maintenance": False,
                    "allow_registration": True, "otp_required": True,
                })
        except Exception:
            pass

    # -------------------------------- login ----------------------------------
    def _show_login(self):
        self.login_frame = tk.Frame(self, bg=DARK)
        self.login_frame.pack(fill="both", expand=True)

        tk.Label(self.login_frame, text="◈  SMS DEVELOPER CONSOLE", bg=DARK, fg=CYAN,
                 font=("Consolas", 20, "bold")).pack(pady=(60, 4))
        tk.Label(self.login_frame, text="High-privilege control over login and dashboard",
                 bg=DARK, fg=MUT, font=("Segoe UI", 9)).pack()

        card = Card(self.login_frame)
        card.configure(width=380, height=310)
        card.pack(pady=24)
        card.pack_propagate(False)

        tk.Label(card.body, text="EMAIL", bg=PANEL, fg=MUT,
                 font=("Consolas", 8, "bold")).pack(anchor="w")
        self.l_email = tk.Entry(card.body, bg=PANEL_2, fg=TEXT, insertbackground=CYAN,
                                relief="flat", font=("Consolas", 11))
        self.l_email.pack(fill="x", ipady=7, pady=(2, 10))
        self.l_email.insert(0, "dev@admin.local")

        tk.Label(card.body, text="PASSWORD", bg=PANEL, fg=MUT,
                 font=("Consolas", 8, "bold")).pack(anchor="w")
        self.l_pass = tk.Entry(card.body, bg=PANEL_2, fg=TEXT, insertbackground=CYAN,
                               relief="flat", font=("Consolas", 11), show="●")
        self.l_pass.pack(fill="x", ipady=7, pady=(2, 10))
        self.l_pass.bind("<Return>", lambda _e: self._login())

        self.l_status = tk.Label(card.body, text="", bg=PANEL, fg=RED,
                                 font=("Consolas", 8), wraplength=330, justify="left")
        self.l_status.pack(anchor="w")

        tk.Button(card.body, text="AUTHENTICATE", command=self._login, bg=CYAN, fg=DARK,
                  bd=0, cursor="hand2", font=("Consolas", 10, "bold")).pack(
            fill="x", pady=(10, 4), ipady=8)

        tk.Label(self.login_frame, text="Use your configured developer administrator credentials.",
                 bg=DARK, fg=MUT, font=("Consolas", 8)).pack()
        tk.Button(self.login_frame, text="Reset default dev account",
                  command=self._repair_admin, bg=PANEL, fg=AMBER, bd=0, cursor="hand2",
                  font=("Consolas", 8)).pack(pady=4)
        tk.Label(self.login_frame, text=f"DB: {'online' if self.db.online else 'offline (memory)'}",
                 bg=DARK, fg=GREEN if self.db.online else RED,
                 font=("Consolas", 8)).pack(pady=6)

    def _login(self):
        email = self.l_email.get().strip().lower()
        pwd = self.l_pass.get()
        if not email or not pwd:
            self.l_status.configure(text="Enter both email and password.")
            return
        rec = self.db.col("admins").find_one({"email": email})
        if not rec:
            self.l_status.configure(
                text=f"No admin with '{email}'. Default is dev@admin.local")
            return
        if not verify_pwd(pwd, rec.get("password", {})):
            self.l_status.configure(text="Password incorrect for this admin.")
            return
        self.admin = rec
        self.login_frame.destroy()
        self._build_shell()
        self.show_page("overview")

    def _repair_admin(self):
        try:
            self.db.col("admins").delete_one({"email": "dev@admin.local"})
        except Exception:
            pass
        self._ensure_admin()
        self.l_email.delete(0, "end")
        self.l_email.insert(0, "dev@admin.local")
        self.l_pass.delete(0, "end")
        self.l_pass.insert(0, "Dev@12345")
        self.l_status.configure(text="Default dev account reset. Press AUTHENTICATE.",
                                fg=GREEN)

    # -------------------------------- shell ----------------------------------
    def _build_shell(self):
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        side = tk.Frame(self, bg=PANEL_2, width=SIDEBAR_W)
        side.grid(row=0, column=0, sticky="ns")
        side.grid_propagate(False)

        brand = tk.Frame(side, bg=PANEL_2)
        brand.pack(fill="x", padx=16, pady=18)
        tk.Label(brand, text="◈", bg=PANEL_2, fg=CYAN, font=("Consolas", 20, "bold")).pack(side="left")
        tk.Label(brand, text="CONSOLE", bg=PANEL_2, fg=TEXT,
                 font=("Consolas", 12, "bold")).pack(side="left", padx=8)

        tk.Frame(side, bg=LINE, height=1).pack(fill="x", padx=12)

        for key, label, icon in NAV:
            row = tk.Frame(side, bg=PANEL_2, cursor="hand2")
            row.pack(fill="x", padx=8, pady=1)
            inner = tk.Frame(row, bg=PANEL_2)
            inner.pack(fill="x", padx=8, pady=7)
            ic = tk.Label(inner, text=icon, bg=PANEL_2, fg=MUT, font=("Consolas", 11))
            ic.pack(side="left")
            tx = tk.Label(inner, text=label, bg=PANEL_2, fg=MUT, font=("Segoe UI", 10))
            tx.pack(side="left", padx=10)
            for w in (row, inner, ic, tx):
                w.bind("<Button-1>", lambda _e, k=key: self.show_page(k))
                w.bind("<Enter>", lambda _e, r=row: self._hover(r, True))
                w.bind("<Leave>", lambda _e, r=row: self._hover(r, False))
            self.nav_buttons[key] = (row, inner, ic, tx)

        bottom = tk.Frame(side, bg=PANEL_2)
        bottom.pack(side="bottom", fill="x", padx=12, pady=14)
        tk.Button(bottom, text="⏻  Sign out", command=self._signout, bg=RED, fg="white",
                  bd=0, cursor="hand2", font=("Consolas", 9, "bold"), pady=7).pack(fill="x")

        right = tk.Frame(self, bg=DARK)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)

        top = tk.Frame(right, bg=PANEL, height=58)
        top.grid(row=0, column=0, sticky="ew")
        top.grid_propagate(False)
        tk.Label(top, text="Developer Console", bg=PANEL, fg=TEXT,
                 font=("Consolas", 12, "bold")).pack(side="left", padx=20)
        self.db_badge = tk.Label(top, text="DB " + ("ONLINE" if self.db.online else "OFFLINE"),
                                 bg=PANEL, fg=GREEN if self.db.online else RED,
                                 font=("Consolas", 9, "bold"))
        self.db_badge.pack(side="right", padx=18)
        tk.Label(top, text=self.admin.get("name", "dev"), bg=PANEL, fg=CYAN,
                 font=("Consolas", 9)).pack(side="right", padx=8)

        self.host = tk.Frame(right, bg=DARK)
        self.host.grid(row=1, column=0, sticky="nsew")
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.bind_all(seq, self._wheel)

    def _hover(self, row, on):
        key = next((k for k, v in self.nav_buttons.items() if v[0] is row), None)
        if key == self.active:
            return
        color = "#1a2340" if on else PANEL_2
        for w in self._walk(row):
            try:
                w.configure(bg=color)
            except Exception:
                pass

    @staticmethod
    def _walk(w):
        yield w
        for c in w.winfo_children():
            yield from AdminPanel._walk(c)

    def _wheel(self, event):
        area = self._area(event)
        if area is None:
            return "break"
        if getattr(event, "num", None) == 4:
            step = -1
        elif getattr(event, "num", None) == 5:
            step = 1
        else:
            d = getattr(event, "delta", 0)
            if not d:
                return "break"
            thr = 120 if abs(d) >= 120 else 20
            acc = self.acc.get(id(area), 0) + d
            step = int(-acc / thr)
            if step == 0:
                self.acc[id(area)] = acc
                if abs(acc) < thr:
                    return "break"
                step = -1 if acc > 0 else 1
                acc = 0
            self.acc[id(area)] = acc
        area.scroll(step)
        return "break"

    def _area(self, event):
        try:
            w = self.winfo_containing(event.x_root, event.y_root)
        except Exception:
            return None
        while w is not None:
            if isinstance(w, ScrollArea):
                return w
            w = getattr(w, "master", None)
        return None

    # ------------------------------- routing ---------------------------------
    def show_page(self, key, rebuild=False):
        self.active = key
        for k, (row, inner, ic, tx) in self.nav_buttons.items():
            on = k == key
            for w in (row, inner):
                w.configure(bg="#1a2340" if on else PANEL_2)
            ic.configure(bg="#1a2340" if on else PANEL_2, fg=CYAN if on else MUT)
            tx.configure(bg="#1a2340" if on else PANEL_2, fg=TEXT if on else MUT,
                         font=("Segoe UI", 10, "bold" if on else "normal"))

        for w in self.host.winfo_children():
            w.pack_forget()
        page = self.pages.get(key)
        if page is not None and rebuild:
            page.destroy()
            page = None
        if page is None:
            page = ScrollArea(self.host)
            builder = getattr(self, f"_page_{key}", None)
            if builder:
                try:
                    builder(page.inner)
                except Exception:
                    traceback.print_exc()
                    tk.Label(page.inner, text="Page failed.", bg=DARK, fg=RED).pack(pady=20)
            self.pages[key] = page
        page.pack(fill="both", expand=True)

    def _rebuild(self, key):
        self.show_page(key, rebuild=True)

    def _header(self, parent, title, sub=""):
        h = tk.Frame(parent, bg=DARK)
        h.pack(fill="x", padx=26, pady=(22, 10))
        tk.Label(h, text=title, bg=DARK, fg=TEXT, font=("Consolas", 20, "bold")).pack(anchor="w")
        if sub:
            tk.Label(h, text=sub, bg=DARK, fg=MUT, font=("Segoe UI", 9)).pack(anchor="w")

    def _table(self, parent, cols, height=12):
        wrap = tk.Frame(parent, bg=PANEL)
        tree = ttk.Treeview(wrap, columns=cols, show="headings", height=height)
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=150, minwidth=90, anchor="w", stretch=True)
        vs = ttk.Scrollbar(wrap, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vs.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vs.grid(row=0, column=1, sticky="ns")
        wrap.rowconfigure(0, weight=1)
        wrap.columnconfigure(0, weight=1)
        wrap.pack(fill="both", expand=True)
        return tree

    def _btn(self, parent, text, cmd, color=CYAN, fg=DARK):
        b = tk.Button(parent, text=text, command=cmd, bg=color, fg=fg, bd=0,
                      cursor="hand2", font=("Consolas", 9, "bold"), padx=10, pady=5)
        b.pack(side="left", padx=(0, 8))
        return b

    def _search(self, parent, tree):
        box = tk.Entry(parent, bg=PANEL_2, fg=TEXT, relief="flat", insertbackground=CYAN)
        box.pack(side="right", ipady=5, ipadx=6)
        box.bind("<KeyRelease>", lambda _e: self._filter(tree, box.get()))

    def _filter(self, tree, term):
        term = term.strip().lower()
        items = getattr(tree, "_all_iids", None)
        if items is None:
            items = list(tree.get_children())
            tree._all_iids = items
        for iid in items:
            try:
                vals = " ".join(str(v).lower() for v in tree.item(iid, "values"))
                if not term or term in vals:
                    tree.reattach(iid, "", "end")
                else:
                    tree.detach(iid)
            except tk.TclError:
                continue

    # ------------------------------- overview --------------------------------
    def _page_overview(self, parent):
        self._header(parent, "System Overview", "Live state of the platform.")
        stats = tk.Frame(parent, bg=DARK)
        stats.pack(fill="x", padx=26, pady=8)

        for label, coll, color in (("Users", "users", CYAN), ("Students", "students", PURPLE),
                                   ("Teachers", "teachers", GREEN), ("Audit events", "notifications", AMBER)):
            c = Card(stats)
            c.pack(side="left", fill="both", expand=True, padx=(0, 12))
            tk.Label(c.body, text=label, bg=PANEL, fg=MUT, font=("Consolas", 8, "bold")).pack(anchor="w")
            try:
                count = self.db.col(coll).count_documents()
            except Exception:
                count = 0
            tk.Label(c.body, text=str(count), bg=PANEL, fg=color,
                     font=("Consolas", 24, "bold")).pack(anchor="w")

        st = self._settings()
        ctl = Card(parent)
        ctl.pack(fill="x", padx=26, pady=10)
        tk.Label(ctl.body, text="MASTER CONTROLS", bg=PANEL, fg=CYAN,
                 font=("Consolas", 10, "bold")).pack(anchor="w")
        row = tk.Frame(ctl.body, bg=PANEL)
        row.pack(fill="x", pady=8)
        self._toggle_btn(row, "Maintenance mode", st.get("maintenance", False),
                         lambda: self._flip("maintenance"))
        self._toggle_btn(row, "Allow registration", st.get("allow_registration", True),
                         lambda: self._flip("allow_registration"))
        self._toggle_btn(row, "Require OTP", st.get("otp_required", True),
                         lambda: self._flip("otp_required"))

        info = Card(parent)
        info.pack(fill="x", padx=26, pady=10)
        tk.Label(info.body, text="ENVIRONMENT", bg=PANEL, fg=CYAN,
                 font=("Consolas", 10, "bold")).pack(anchor="w")
        for k, v in (("Mongo URI", MONGO_URI), ("Database", DB_NAME),
                     ("Driver", "pymongo" if MONGO_OK else "missing"),
                     ("Connection", "online" if self.db.online else "offline")):
            r = tk.Frame(info.body, bg=PANEL)
            r.pack(fill="x", pady=2)
            tk.Label(r, text=k, bg=PANEL, fg=MUT, width=16, anchor="w",
                     font=("Consolas", 9)).pack(side="left")
            tk.Label(r, text=str(v), bg=PANEL, fg=TEXT, font=("Consolas", 9)).pack(side="left")

    def _toggle_btn(self, parent, label, on, cmd):
        tk.Button(parent, text=("● " if on else "○ ") + label,
                  command=cmd, bd=0, cursor="hand2", font=("Consolas", 9, "bold"),
                  bg=("#123a2a" if on else PANEL_2), fg=(GREEN if on else MUT),
                  padx=10, pady=6).pack(side="left", padx=(0, 8))

    def _settings(self):
        return self.db.col("settings").find_one({"_id": "app"}) or {}

    def _flip(self, key):
        st = self._settings()
        self.db.col("settings").update_one({"_id": "app"}, {"$set": {key: not st.get(key, False)}})
        self._log(f"Flag '{key}' set to {not st.get(key, False)}")
        self._rebuild("overview")

    def _log(self, text):
        try:
            self.db.col("notifications").insert_one(
                {"text": "[admin] " + text, "roles": ["principal"], "at": now_iso()})
        except Exception:
            pass

    # --------------------------------- users ---------------------------------
    def _page_users(self, parent):
        self._header(parent, "Users", "Manage every account.")
        bar = tk.Frame(parent, bg=DARK)
        bar.pack(fill="x", padx=26)
        self._btn(bar, "Disable / Enable", self._toggle_user, AMBER, "#111")
        self._btn(bar, "Reset password", self._reset_user, PURPLE, "white")
        self._btn(bar, "Impersonate", self._impersonate, GREEN, "#111")
        self._btn(bar, "Delete", self._delete_user, RED, "white")
        self._btn(bar, "Refresh", lambda: self._load_users(), MUT, "#111")

        card = Card(parent)
        card.pack(fill="both", expand=True, padx=26, pady=10)
        self.user_tree = self._table(card.body, ("Name", "Email", "Role", "Status", "Created"))
        self.user_tree.pack(fill="both", expand=True)
        sbox = tk.Frame(bar, bg=DARK)
        sbox.pack(side="right", padx=(8, 0))
        self._search(sbox, self.user_tree)
        self._load_users()

    def _load_users(self):
        t = getattr(self, "user_tree", None)
        if not t or not t.winfo_exists():
            return
        t.delete(*t.get_children())
        docs = self.db.col("users").find(limit=500)
        if not docs:
            t.insert("", "end", values=("No users found", "", "", "", ""))
            return
        for u in docs:
            t.insert("", "end", iid=str(u.get("_id")), values=(
                u.get("name", ""), u.get("email", ""), u.get("category", ""),
                u.get("account_status", "active"), str(u.get("created_at", ""))[:10]))
        t._all_iids = list(t.get_children())

    def _get_doc_by_iid(self, collection, iid):
        if not iid:
            return None
        try:
            return next((doc for doc in self.db.col(collection).find(limit=5000)
                         if str(doc.get("_id")) == str(iid)), None)
        except Exception:
            return None

    def _sel_user(self):
        sel = self.user_tree.selection()
        if not sel:
            messagebox.showinfo("Users", "Select a user first.")
            return None
        return self._get_doc_by_iid("users", sel[0])

    def _toggle_user(self):
        u = self._sel_user()
        if not u:
            return
        new = "disabled" if u.get("account_status", "active") == "active" else "active"
        try:
            self.db.col("users").update_one({"_id": u["_id"]}, {"$set": {"account_status": new}})
            self._log(f"User {u.get('email')} set {new}")
            self._load_users()
        except Exception as exc:
            messagebox.showerror("Update failed", str(exc))

    def _reset_user(self):
        u = self._sel_user()
        if not u:
            return
        new = simpledialog.askstring("Reset password", f"New password for {u.get('email')}:",
                                     parent=self, show="●")
        if not new:
            return
        if len(new) < 8:
            return messagebox.showwarning("Reset password", "Use at least 8 characters.")
        try:
            self.db.col("users").update_one({"_id": u["_id"]}, {"$set": {"password": hash_pwd(new)}})
            self._log(f"Password reset for {u.get('email')}")
            messagebox.showinfo("Reset", "Password updated.")
        except Exception as exc:
            messagebox.showerror("Reset failed", str(exc))

    def _delete_user(self):
        u = self._sel_user()
        if not u:
            return
        if messagebox.askyesno("Delete", f"Permanently delete {u.get('email')}?"):
            try:
                self.db.col("users").delete_one({"_id": u["_id"]})
                self._log(f"User deleted: {u.get('email')}")
                self._load_users()
            except Exception as exc:
                messagebox.showerror("Delete failed", str(exc))

    def _impersonate(self):
        u = self._sel_user()
        if not u:
            return
        account = dict(u)
        account.pop("password", None)
        account.pop("_id", None)
        try:
            import dashboard
            self.withdraw()
            dashboard.launch(account, app=self)
        except Exception:
            traceback.print_exc()
            messagebox.showwarning("Dashboard", "dashboard.py not importable.")

    # -------------------------------- students -------------------------------
    def _page_students(self, parent):
        self._header(parent, "Student Records", "Inspect and archive records.")
        bar = tk.Frame(parent, bg=DARK)
        bar.pack(fill="x", padx=26)
        self._btn(bar, "Archive selected", self._archive_student, AMBER, "#111")
        self._btn(bar, "Delete selected", self._delete_student, RED, "white")
        self._btn(bar, "Refresh", self._load_students, MUT, "#111")
        card = Card(parent)
        card.pack(fill="both", expand=True, padx=26, pady=10)
        self.stu_tree = self._table(card.body, ("Name", "Course", "Branch", "Sem", "Mobile", "Status"))
        self.stu_tree.pack(fill="both", expand=True)
        sbox = tk.Frame(bar, bg=DARK)
        sbox.pack(side="right", padx=(8, 0))
        self._search(sbox, self.stu_tree)
        self._load_students()

    def _load_students(self):
        t = getattr(self, "stu_tree", None)
        if not t or not t.winfo_exists():
            return
        t.delete(*t.get_children())
        docs = self.db.col("students").find(limit=500)
        if not docs:
            t.insert("", "end", values=("No students", "", "", "", "", ""))
            return
        for d in docs:
            t.insert("", "end", iid=str(d.get("_id")), values=(
                d.get("name", ""), d.get("course", ""), d.get("branch", ""),
                d.get("semester", ""), d.get("mobile", ""), d.get("status", "Active")))
        t._all_iids = list(t.get_children())

    def _archive_student(self):
        sel = self.stu_tree.selection()
        if not sel:
            return
        d = self._get_doc_by_iid("students", sel[0])
        if not d:
            return
        rec = dict(d)
        rec["leave_reason"] = "Archived by developer"
        try:
            self.db.col("student_archive").insert_one(rec)
            self.db.col("students").delete_one({"_id": d["_id"]})
        except Exception as exc:
            messagebox.showerror("Archive failed", str(exc))
            return
        self._log(f"Student archived: {d.get('name')}")
        self._load_students()

    def _delete_student(self):
        sel = self.stu_tree.selection()
        if not sel:
            return
        if messagebox.askyesno("Delete", "Delete this student record?"):
            d = self._get_doc_by_iid("students", sel[0])
            if d:
                self.db.col("students").delete_one({"_id": d["_id"]})
            self._load_students()

    # --------------------------------- audit ---------------------------------
    def _page_audit(self, parent):
        self._header(parent, "Audit Log", "Every recorded event.")
        card = Card(parent)
        card.pack(fill="both", expand=True, padx=26, pady=10)
        tree = self._table(card.body, ("When", "Event", "Audience"), height=18)
        tree.pack(fill="both", expand=True)
        docs = self.db.col("notifications").find(limit=300)
        for n in reversed(docs):
            tree.insert("", "end", values=(str(n.get("at", ""))[:19].replace("T", " "),
                                           n.get("text", ""), ", ".join(n.get("roles", []))))

    # ------------------------------- broadcast -------------------------------
    def _page_broadcast(self, parent):
        self._header(parent, "Broadcast", "Push a notice to chosen audiences.")
        card = Card(parent)
        card.pack(fill="x", padx=26, pady=10)
        tk.Label(card.body, text="MESSAGE", bg=PANEL, fg=MUT, font=("Consolas", 8, "bold")).pack(anchor="w")
        msg = tk.Text(card.body, height=5, bg=PANEL_2, fg=TEXT, relief="flat",
                      insertbackground=CYAN, font=("Segoe UI", 10))
        msg.pack(fill="x", pady=6)
        roles = tk.Frame(card.body, bg=PANEL)
        roles.pack(anchor="w", pady=4)
        self.role_vars = {}
        for r in ("student", "teacher", "principal"):
            var = tk.BooleanVar(value=True)
            self.role_vars[r] = var
            tk.Checkbutton(roles, text=r.title(), variable=var, bg=PANEL, fg=TEXT,
                           selectcolor=PANEL_2, activebackground=PANEL,
                           activeforeground=CYAN, font=("Consolas", 9)).pack(side="left", padx=6)

        def send():
            text = msg.get("1.0", "end").strip()
            chosen = [r for r, v in self.role_vars.items() if v.get()]
            if not text or not chosen:
                return messagebox.showwarning("Broadcast", "Message and audience required.")
            self.db.col("notifications").insert_one(
                {"text": text, "roles": chosen, "at": now_iso()})
            msg.delete("1.0", "end")
            messagebox.showinfo("Broadcast", "Sent.")
        tk.Button(card.body, text="SEND BROADCAST", command=send, bg=CYAN, fg=DARK, bd=0,
                  cursor="hand2", font=("Consolas", 10, "bold")).pack(anchor="w", pady=8, ipadx=14, ipady=6)

    # --------------------------------- flags ---------------------------------
    def _page_flags(self, parent):
        self._header(parent, "Feature Flags", "Impose behaviour on both apps.")
        card = Card(parent)
        card.pack(fill="x", padx=26, pady=10)
        st = self._settings()
        for key, desc in (("maintenance", "Block all logins with a maintenance notice."),
                          ("allow_registration", "Allow new account creation."),
                          ("otp_required", "Force email OTP on registration and reset.")):
            row = tk.Frame(card.body, bg=PANEL)
            row.pack(fill="x", pady=8)
            on = bool(st.get(key, True))
            tk.Button(row, text=("● ON" if on else "○ OFF"), width=6,
                      command=lambda k=key: (self._flip(k), self._rebuild("flags")),
                      bg=("#123a2a" if on else PANEL_2), fg=(GREEN if on else MUT),
                      bd=0, cursor="hand2", font=("Consolas", 9, "bold")).pack(side="left")
            col = tk.Frame(row, bg=PANEL)
            col.pack(side="left", padx=12)
            tk.Label(col, text=key, bg=PANEL, fg=TEXT, font=("Consolas", 10, "bold")).pack(anchor="w")
            tk.Label(col, text=desc, bg=PANEL, fg=MUT, font=("Segoe UI", 8)).pack(anchor="w")

    # ------------------------------- data tools ------------------------------
    def _page_data(self, parent):
        self._header(parent, "Data Tools", "Export, seed and purge.")
        card = Card(parent)
        card.pack(fill="x", padx=26, pady=10)
        tk.Label(card.body, text="EXPORT COLLECTION", bg=PANEL, fg=MUT,
                 font=("Consolas", 8, "bold")).pack(anchor="w")
        row = tk.Frame(card.body, bg=PANEL)
        row.pack(anchor="w", pady=6)
        self.exp_col = ttk.Combobox(row, values=COLLECTIONS, state="readonly", width=22)
        self.exp_col.set("users")
        self.exp_col.pack(side="left")
        self._btn(row, "Export CSV", self._export_csv, CYAN)

        purge = Card(parent)
        purge.pack(fill="x", padx=26, pady=10)
        tk.Label(purge.body, text="PURGE COLLECTION (keeps admins/settings)", bg=PANEL,
                 fg=AMBER, font=("Consolas", 8, "bold")).pack(anchor="w")
        prow = tk.Frame(purge.body, bg=PANEL)
        prow.pack(anchor="w", pady=6)
        self.purge_col = ttk.Combobox(prow, values=COLLECTIONS, state="readonly", width=22)
        self.purge_col.set("notifications")
        self.purge_col.pack(side="left")
        self._btn(prow, "Purge", self._purge, RED, "white")

    def _export_csv(self):
        coll = self.exp_col.get()
        docs = self.db.col(coll).find(limit=2000)
        if not docs:
            return messagebox.showinfo("Export", "Nothing to export.")
        path = filedialog.asksaveasfilename(defaultextension=".csv",
                                            initialfile=f"{coll}.csv",
                                            filetypes=[("CSV", "*.csv")])
        if not path:
            return
        try:
            clean = [{k: (json.dumps(v, default=str) if isinstance(v, (dict, list, tuple)) else v)
                      for k, v in d.items() if k not in ("photo_b64", "password", "salt", "hash")}
                     for d in docs]
            keys = sorted({k for d in clean for k in d})
            with open(path, "w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=keys)
                w.writeheader()
                w.writerows(clean)
            messagebox.showinfo("Export", f"Saved {len(clean)} rows to {path}")
        except Exception as exc:
            messagebox.showerror("Export", str(exc))

    def _purge(self):
        coll = self.purge_col.get()
        if coll in ("admins", "settings"):
            return messagebox.showinfo("Purge", "Admins/settings are protected.")
        if not messagebox.askyesno("Purge", f"Delete ALL documents in '{coll}'?"):
            return
        try:
            n = self.db.col(coll).count_documents()
            if self.db.online:
                self.db.client[DB_NAME][coll].delete_many({})
            else:
                self.db.col(coll).delete_many({})
            self._log(f"Purged {n} docs from {coll}")
            messagebox.showinfo("Purge", f"Removed {n} documents.")
        except Exception as exc:
            messagebox.showerror("Purge", str(exc))

    # ------------------------------- console ---------------------------------
    def _page_console(self, parent):
        self._header(parent, "Query Console", "Run a JSON filter against a collection.")
        card = Card(parent)
        card.pack(fill="x", padx=26, pady=10)
        row = tk.Frame(card.body, bg=PANEL)
        row.pack(fill="x")
        self.q_col = ttk.Combobox(row, values=COLLECTIONS, state="readonly", width=20)
        self.q_col.set("students")
        self.q_col.pack(side="left")
        self.q_text = tk.Entry(row, bg=PANEL_2, fg=TEXT, relief="flat", insertbackground=CYAN)
        self.q_text.pack(side="left", fill="x", expand=True, padx=8, ipady=6)
        self.q_text.insert(0, "{}")
        self._btn(row, "Run", self._run_query, CYAN)

        card2 = Card(parent)
        card2.pack(fill="both", expand=True, padx=26, pady=10)
        self.q_result = tk.Text(card2.body, bg=PANEL_2, fg=TEXT, relief="flat",
                                font=("Consolas", 9), wrap="none")
        self.q_result.pack(fill="both", expand=True)

    def _run_query(self):
        try:
            flt = json.loads(self.q_text.get() or "{}")
        except Exception as exc:
            return messagebox.showerror("Query", f"Invalid JSON: {exc}")
        try:
            docs = self.db.col(self.q_col.get()).find(flt, limit=100)
        except Exception as exc:
            return messagebox.showerror("Query", str(exc))
        self.q_result.delete("1.0", "end")
        if not docs:
            self.q_result.insert("end", "No documents.")
            return
        for i, d in enumerate(docs, 1):
            clean = {k: v for k, v in d.items() if k != "photo_b64"}
            self.q_result.insert("end", f"{i}. {json.dumps(clean, default=str)}\n")


    # ----------------------------- AI / ML insights ----------------------------
    def _page_ml(self, parent):
        self._header(parent, "AI / ML Insights",
                     "Run anomaly detection on real student records. No synthetic rows are generated.")
        intro = Card(parent)
        intro.pack(fill="x", padx=26, pady=8)
        tk.Label(intro.body, text="INTELLIGENCE ENGINE", bg=PANEL, fg=CYAN,
                 font=("Consolas", 10, "bold")).pack(anchor="w")
        availability = (
            f"scikit-learn: {'READY' if SKLEARN_OK else 'NOT INSTALLED'}   •   "
            f"PyTorch: {'READY' if TORCH_OK else 'NOT INSTALLED'}"
        )
        tk.Label(intro.body, text=availability, bg=PANEL, fg=GREEN if SKLEARN_OK else AMBER,
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(5, 2))
        tk.Label(intro.body,
                 text="Isolation Forest identifies unusual numeric student profiles. "
                      "When PyTorch is installed, an autoencoder provides a second anomaly score.",
                 bg=PANEL, fg=MUT, font=("Segoe UI", 9), wraplength=900,
                 justify="left").pack(anchor="w", pady=(2, 8))
        row = tk.Frame(intro.body, bg=PANEL)
        row.pack(fill="x")
        self._btn(row, "RUN ANALYSIS", self._run_ml_analysis, CYAN, DARK)
        self._btn(row, "Refresh data", lambda: self._rebuild("ml"), PANEL_2, TEXT)

        summary = Card(parent)
        summary.pack(fill="x", padx=26, pady=8)
        self.ml_summary = tk.Label(summary.body, text="No analysis has been run.",
                                   bg=PANEL, fg=TEXT, font=("Segoe UI", 10),
                                   justify="left", anchor="w")
        self.ml_summary.pack(fill="x")

        results = Card(parent)
        results.pack(fill="both", expand=True, padx=26, pady=8)
        tk.Label(results.body, text="ANOMALY REVIEW", bg=PANEL, fg=CYAN,
                 font=("Consolas", 10, "bold")).pack(anchor="w", pady=(0, 8))
        self.ml_tree = self._table(results.body,
                                   ("Student", "Course", "Semester", "Risk score", "Model result"),
                                   height=12)
        self.ml_tree.pack(fill="both", expand=True)

    @staticmethod
    def _numeric_value(value):
        if isinstance(value, bool) or value is None:
            return None
        try:
            number = float(str(value).replace(",", "").replace("%", "").strip())
            return number if math.isfinite(number) else None
        except Exception:
            return None

    def _run_ml_analysis(self):
        if not SKLEARN_OK:
            messagebox.showerror(
                "Missing dependency",
                "Install the ML dependencies in your active virtual environment:\n\n"
                "python -m pip install -U numpy scikit-learn")
            return
        try:
            records = self.db.col("students").find(limit=2000)
            if len(records) < 10:
                messagebox.showinfo("Not enough data",
                                    f"Found {len(records)} student records. "
                                    "At least 10 records are needed for meaningful anomaly detection.")
                return

            candidates = (
                "semester", "age", "attendance", "attendance_percentage",
                "attendance_percent", "marks", "percentage", "cgpa",
                "gpa", "fee_due", "fees_due", "total_fees", "fees_paid",
                "backlogs", "credits"
            )
            feature_names = []
            for field in candidates:
                values = [self._numeric_value(doc.get(field)) for doc in records]
                if sum(v is not None for v in values) >= max(5, int(len(records) * 0.25)):
                    if len({round(v, 6) for v in values if v is not None}) > 1:
                        feature_names.append(field)

            if len(feature_names) < 2:
                messagebox.showwarning(
                    "Insufficient numeric data",
                    "Student records need at least two varying numeric fields, such as "
                    "semester, attendance, marks, CGPA or fee_due. Add real values and retry.")
                return

            matrix = []
            valid_records = []
            for doc in records:
                row = [self._numeric_value(doc.get(field)) for field in feature_names]
                if sum(v is not None for v in row) >= 2:
                    matrix.append(row)
                    valid_records.append(doc)

            if len(matrix) < 10:
                messagebox.showinfo("Not enough complete data",
                                    "Fewer than 10 usable student records remain after filtering.")
                return

            imputer = SimpleImputer(strategy="median")
            scaler = StandardScaler()
            X = scaler.fit_transform(imputer.fit_transform(np.asarray(matrix, dtype=float)))

            model = IsolationForest(
                n_estimators=200, contamination="auto", random_state=42
            )
            model.fit(X)
            sklearn_scores = -model.score_samples(X)
            sklearn_flags = model.predict(X) == -1

            torch_scores = None
            torch_flags = None
            if TORCH_OK and len(X) >= 20:
                try:
                    torch.manual_seed(42)
                    torch.set_num_threads(1)
                    tensor = torch.tensor(X, dtype=torch.float32)
                    input_size = tensor.shape[1]
                    hidden = max(2, min(16, input_size * 2))
                    class AutoEncoder(nn.Module):
                        def __init__(self):
                            super().__init__()
                            self.encoder = nn.Sequential(
                                nn.Linear(input_size, hidden), nn.ReLU(),
                                nn.Linear(hidden, max(2, input_size))
                            )
                            self.decoder = nn.Sequential(
                                nn.Linear(max(2, input_size), hidden), nn.ReLU(),
                                nn.Linear(hidden, input_size)
                            )

                        def forward(self, value):
                            return self.decoder(self.encoder(value))

                    network = AutoEncoder()
                    optimizer = torch.optim.Adam(network.parameters(), lr=0.01)
                    loss_fn = nn.MSELoss()
                    network.train()
                    for _ in range(60):
                        optimizer.zero_grad()
                        reconstructed = network(tensor)
                        loss = loss_fn(reconstructed, tensor)
                        loss.backward()
                        optimizer.step()
                    network.eval()
                    with torch.no_grad():
                        errors = torch.mean((network(tensor) - tensor) ** 2, dim=1)
                        torch_scores = errors.cpu().numpy()
                    threshold = float(np.quantile(torch_scores, 0.95))
                    torch_flags = torch_scores >= threshold
                except Exception:
                    torch_scores = torch_flags = None

            combined = []
            for i, doc in enumerate(valid_records):
                # Percentile-normalized model scores keep the combined risk interpretable.
                rank = float((np.argsort(np.argsort(sklearn_scores))[i] + 1) / len(sklearn_scores))
                if torch_scores is not None:
                    trank = float((np.argsort(np.argsort(torch_scores))[i] + 1) / len(torch_scores))
                    risk = 100.0 * (0.65 * rank + 0.35 * trank)
                    flagged = bool(sklearn_flags[i] or torch_flags[i])
                    model_name = "Isolation Forest + PyTorch AE"
                else:
                    risk = 100.0 * rank
                    flagged = bool(sklearn_flags[i])
                    model_name = "Isolation Forest"
                combined.append((risk, flagged, doc, model_name))

            combined.sort(key=lambda item: item[0], reverse=True)
            tree = self.ml_tree
            tree.delete(*tree.get_children())
            for risk, flagged, doc, model_name in combined[:100]:
                tree.insert("", "end", values=(
                    doc.get("name", "Unknown"),
                    doc.get("course", ""),
                    doc.get("semester", ""),
                    f"{risk:.1f}/100",
                    ("REVIEW" if flagged else "Normal") + f" • {model_name}"
                ))
            flagged_count = sum(1 for _, flag, _, _ in combined if flag)
            torch_status = "PyTorch autoencoder included" if torch_scores is not None else (
                "PyTorch unavailable/not enough data; sklearn-only result")
            self.ml_summary.configure(
                text=(f"Records analysed: {len(valid_records)}    •    "
                      f"Numeric features: {', '.join(feature_names)}\n"
                      f"Flagged for human review: {flagged_count}    •    "
                      f"Models: {torch_status}\n"
                      "Risk score is a relative anomaly ranking, not a judgment of student performance.")
            )
            self._log(f"ML analysis completed for {len(valid_records)} student records; "
                      f"{flagged_count} flagged for review.")
        except Exception as exc:
            traceback.print_exc()
            messagebox.showerror("ML analysis failed", str(exc))

    # -------------------------------- session --------------------------------
    def show_tab(self, key):
        """Called by dashboard on logout (ignores unknown names)."""
        try:
            self.deiconify()
            if key in self.pages:
                self.show_page(key)
        except Exception:
            pass

    def _on_close(self):
        self.alive = False
        try:
            self.db.close()
        finally:
            self.destroy()

    def _signout(self):
        if not messagebox.askyesno("Sign out", "Sign out of the console?"):
            return
        self._on_close()


def main():
    try:
        AdminPanel().mainloop()
    except Exception:
        traceback.print_exc()
        try:
            messagebox.showerror("Admin panel", traceback.format_exc()[-1500:])
        except Exception:
            pass


if __name__ == "__main__":
    main()
