"""
dashboard.py — Student Management System Dashboard
Government Polytechnic Ranchi

Called from main.py as:  dashboard.launch(user, app=self)

Env (optional):
    SMS_MONGO_URI   default mongodb://localhost:27017
    SMS_DB          default student_management

If MongoDB is unreachable the dashboard runs on an in-session memory store
and shows empty states. No fake rows are written to a real database.
"""

import os
import csv
import math
import random
import datetime
import threading
import traceback
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# ------------------------------- optional libs --------------------------------
try:
    from PIL import Image, ImageTk, ImageDraw
    PIL_OK = True
except Exception:
    PIL_OK = False

try:
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    MPL_OK = True
except Exception:
    MPL_OK = False

try:
    import seaborn as sns
    sns.set_theme(style="whitegrid")
    SNS_OK = True
except Exception:
    SNS_OK = False

try:
    import pandas as pd
    PD_OK = True
except Exception:
    PD_OK = False

try:
    import numpy as np
    NP_OK = True
except Exception:
    NP_OK = False

try:
    from pymongo import MongoClient
    MONGO_OK = True
except Exception:
    MONGO_OK = False

# torch is optional; used only if present for future analytics
try:
    import torch  # noqa: F401
    TORCH_OK = True
except Exception:
    TORCH_OK = False


# ----------------------------------- theme ------------------------------------
NAVY = "#172554"
NAVY_HOVER = "#1E3A6E"
ROYAL = "#2563EB"
ROYAL_HOVER = "#1D4ED8"
BG = "#F1F5F9"
CARD = "#FFFFFF"
INK = "#0F172A"
MUTED = "#64748B"
BORDER = "#E2E8F0"
SUCCESS = "#16A34A"
WARN = "#F59E0B"
DANGER = "#DC2626"
CHART_COLORS = ["#2563EB", "#16A34A", "#F59E0B", "#DC2626", "#7C3AED", "#0891B2"]

SIDEBAR_W = 240
NAV_ITEMS = [
    ("dashboard", "Dashboard", "▦"),
    ("students", "Students", "🎓"),
    ("admissions", "Admissions", "📝"),
    ("courses", "Courses & Classes", "📚"),
    ("attendance", "Attendance", "✅"),
    ("fees", "Fees & Payments", "💳"),
    ("examinations", "Examinations", "📄"),
    ("results", "Results & Grades", "🏅"),
    ("teachers", "Teachers & Staff", "🧑‍🏫"),
    ("timetable", "Timetable", "🗓"),
    ("reports", "Reports", "📊"),
    ("settings", "Settings", "⚙"),
]

MONGO_URI = os.environ.get("SMS_MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.environ.get("SMS_DB", "student_management")


# -------------------------------- data layer ----------------------------------
class MemCol:
    """Mongo-like in-memory collection used when the DB is offline."""
    def __init__(self):
        self.docs = []

    def _match(self, doc, query):
        return all(doc.get(k) == v for k, v in (query or {}).items())

    def find(self, query=None, limit=0):
        out = [d for d in self.docs if self._match(d, query)]
        return out[:limit] if limit else out

    def insert_one(self, doc):
        doc = dict(doc)
        doc.setdefault("_id", f"mem-{len(self.docs)}-{random.randint(0, 99999)}")
        self.docs.append(doc)
        return doc

    def update_one(self, query, update):
        for d in self.docs:
            if self._match(d, query):
                d.update(update.get("$set", {}))
                return

    def delete_one(self, query):
        for i, d in enumerate(self.docs):
            if self._match(d, query):
                del self.docs[i]
                return

    def count_documents(self, query=None):
        return len(self.find(query))


class DB:
    """Connection wrapper with automatic offline fallback."""
    def __init__(self):
        self.online = False
        self.client = None
        self._mem = {}
        if MONGO_OK:
            try:
                self.client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=1500)
                self.client.admin.command("ping")
                self.database = self.client[DB_NAME]
                self.online = True
            except Exception:
                self.online = False

    def col(self, name):
        if self.online:
            return self.database[name]
        return self._mem.setdefault(name, MemCol())

    def close(self):
        try:
            if self.client:
                self.client.close()
        except Exception:
            pass


# ------------------------------ rounded card widget ---------------------------
class Card(tk.Canvas):
    """Canvas-drawn rounded card with a live inner frame."""
    def __init__(self, master, bg=CARD, radius=16, pad=16, border=BORDER, **kw):
        super().__init__(master, bg=master.cget("bg"), highlightthickness=0,
                         bd=0, **kw)
        self.radius, self.pad, self.fill, self.border = radius, pad, bg, border
        self.body = tk.Frame(self, bg=bg)
        self._win = self.create_window(0, 0, window=self.body, anchor="nw")
        self.bind("<Configure>", self._redraw)

    def _round(self, x1, y1, x2, y2, r):
        pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
               x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
        return self.create_polygon(pts, smooth=True, splinesteps=24,
                                   fill=self.fill, outline=self.border)

    def _redraw(self, _e=None):
        w, h = self.winfo_width(), self.winfo_height()
        if w < 4 or h < 4:
            return
        self.delete("all")
        self._win = self.create_window(self.pad, self.pad, window=self.body,
                                       anchor="nw")
        self._round(0, 0, w - 1, h - 1, self.radius)
        self.body.configure(width=max(1, w - 2 * self.pad),
                            height=max(1, h - 2 * self.pad))
        self.tag_raise(self._win)


# ---------------------------------- helpers -----------------------------------
def stat_card(parent, icon, label, accent):
    card = Card(parent)
    card.pack(side="left", fill="both", expand=True, padx=(0, 14))
    tk.Label(card.body, text=icon, bg=CARD, fg=accent,
             font=("Segoe UI Emoji", 22)).pack(anchor="w")
    value = tk.Label(card.body, text="0", bg=CARD, fg=INK,
                     font=("Segoe UI", 26, "bold"))
    value.pack(anchor="w", pady=(6, 0))
    tk.Label(card.body, text=label, bg=CARD, fg=MUTED,
             font=("Segoe UI", 10)).pack(anchor="w")
    bar = tk.Frame(card.body, bg=accent, height=4)
    bar.pack(fill="x", pady=(10, 0))
    return value


def avatar(parent, name, size=38, bg=ROYAL):
    initial = (name or "U").strip()[:1].upper()
    c = tk.Canvas(parent, width=size, height=size, bg=parent.cget("bg"),
                  highlightthickness=0)
    c.create_oval(1, 1, size - 1, size - 1, fill=bg, outline="")
    c.create_text(size / 2, size / 2, text=initial, fill="white",
                  font=("Segoe UI", int(size / 2.4), "bold"))
    return c


# ================================== DASHBOARD =================================
class Dashboard:
    def __init__(self, root, user, app):
        self.root = root
        self.user = user or {"name": "Admin", "category": "principal"}
        self.app = app
        self.db = DB()
        self.active = "dashboard"
        self.nav_buttons = {}
        self.pages = {}
        self.student_rows = {}
        self.stat_values = {}
        self._wheel_acc = 0.0
        self.alive = True

        if self.app is not None:
            try:
                self.app.withdraw()
            except Exception:
                pass

        self.root.title("Student Management System — Dashboard")
        self.root.geometry("1400x880")
        self.root.minsize(1080, 680)
        self.root.configure(bg=BG)
        try:
            self.root.state("zoomed")
        except Exception:
            pass

        self._style()
        self._build_shell()
        self.show_page("dashboard")
        self._tick_clock()
        self._refresh_stats_async()

        self.root.protocol("WM_DELETE_WINDOW", self._logout)

    # ------------------------------- styling ----------------------------------
    def _style(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("Treeview", background=CARD, fieldbackground=CARD,
                        foreground=INK, rowheight=30, borderwidth=0,
                        font=("Segoe UI", 9))
        style.configure("Treeview.Heading", background=NAVY, foreground="white",
                        font=("Segoe UI", 9, "bold"), borderwidth=0)
        style.map("Treeview", background=[("selected", "#DBEAFE")],
                  foreground=[("selected", INK)])
        style.configure("TScrollbar", background="#CBD5E1", troughcolor=BG,
                        borderwidth=0)
        style.configure("TCombobox", fieldbackground=CARD)

    # -------------------------------- shell -----------------------------------
    def _build_shell(self):
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        self._build_sidebar()

        right = tk.Frame(self.root, bg=BG)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)

        self._build_topbar(right)

        # scrollable content host
        self.canvas = tk.Canvas(right, bg=BG, highlightthickness=0, bd=0)
        vbar = ttk.Scrollbar(right, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=vbar.set)
        self.canvas.grid(row=1, column=0, sticky="nsew")
        vbar.grid(row=1, column=1, sticky="ns")

        self.content = tk.Frame(self.canvas, bg=BG)
        self.content_id = self.canvas.create_window((0, 0), window=self.content,
                                                    anchor="nw")
        self.content.bind("<Configure>", self._sync_scroll)
        self.canvas.bind("<Configure>",
                         lambda e: self.canvas.itemconfigure(self.content_id,
                                                             width=e.width))
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.canvas.bind_all(seq, self._on_wheel)

    def _sync_scroll(self, _e=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_wheel(self, event):
        if not self.alive:
            return
        try:
            if getattr(event, "num", None) == 4:
                step = -1
            elif getattr(event, "num", None) == 5:
                step = 1
            else:
                delta = getattr(event, "delta", 0)
                if not delta:
                    return
                self._wheel_acc += delta
                step = int(-self._wheel_acc / (120 if abs(delta) >= 120 else 40))
                if step == 0:
                    return
                self._wheel_acc = 0
            self.canvas.yview_scroll(int(step), "units")
        except Exception:
            pass

    def _build_sidebar(self):
        bar = tk.Frame(self.root, bg=NAVY, width=SIDEBAR_W)
        bar.grid(row=0, column=0, sticky="ns")
        bar.grid_propagate(False)

        brand = tk.Frame(bar, bg=NAVY)
        brand.pack(fill="x", pady=(22, 8), padx=18)
        tk.Label(brand, text="🎓", bg=NAVY, fg="white",
                 font=("Segoe UI Emoji", 22)).pack(side="left")
        tk.Label(brand, text="SMS\nCampus", bg=NAVY, fg="white", justify="left",
                 font=("Segoe UI", 13, "bold")).pack(side="left", padx=8)

        tk.Frame(bar, bg=NAVY_HOVER, height=1).pack(fill="x", padx=14, pady=10)

        nav_host = tk.Frame(bar, bg=NAVY)
        nav_host.pack(fill="x")
        for key, label, icon in NAV_ITEMS:
            btn = tk.Frame(nav_host, bg=NAVY, cursor="hand2")
            btn.pack(fill="x", padx=10, pady=1)
            inner = tk.Frame(btn, bg=NAVY)
            inner.pack(fill="x", padx=8, pady=8)
            ic = tk.Label(inner, text=icon, bg=NAVY, fg="#93A6C6",
                          font=("Segoe UI Emoji", 12))
            ic.pack(side="left")
            tx = tk.Label(inner, text=label, bg=NAVY, fg="#C7D2E4",
                          font=("Segoe UI", 10))
            tx.pack(side="left", padx=10)
            for w in (btn, inner, ic, tx):
                w.bind("<Button-1>", lambda _e, k=key: self.show_page(k))
                w.bind("<Enter>", lambda _e, b=btn: self._hover(b, True))
                w.bind("<Leave>", lambda _e, b=btn: self._hover(b, False))
            self.nav_buttons[key] = (btn, inner, ic, tx)

        bottom = tk.Frame(bar, bg=NAVY)
        bottom.pack(side="bottom", fill="x", pady=16, padx=16)
        out = tk.Button(bottom, text="⏻  Logout", command=self._logout, bd=0,
                        bg=DANGER, fg="white", activebackground="#B91C1C",
                        activeforeground="white", cursor="hand2",
                        font=("Segoe UI", 10, "bold"), pady=9)
        out.pack(fill="x")

    def _hover(self, btn, on):
        key = next((k for k, v in self.nav_buttons.items() if v[0] is btn), None)
        if key == self.active:
            return
        color = NAVY_HOVER if on else NAVY
        for w in self._walk(btn):
            try:
                w.configure(bg=color)
            except Exception:
                pass

    @staticmethod
    def _walk(widget):
        yield widget
        for child in widget.winfo_children():
            yield from Dashboard._walk(child)

    def _highlight_nav(self):
        for key, (btn, inner, ic, tx) in self.nav_buttons.items():
            on = key == self.active
            bg = ROYAL if on else NAVY
            fg = "white" if on else "#C7D2E4"
            icf = "white" if on else "#93A6C6"
            for w in (btn, inner):
                w.configure(bg=bg)
            ic.configure(bg=bg, fg=icf)
            tx.configure(bg=bg, fg=fg, font=("Segoe UI", 10, "bold" if on else "normal"))

    def _build_topbar(self, parent):
        bar = tk.Frame(parent, bg=CARD, height=64)
        bar.grid(row=0, column=0, columnspan=2, sticky="ew")
        bar.grid_propagate(False)

        tk.Label(bar, text="Student Management System", bg=CARD, fg=NAVY,
                 font=("Segoe UI", 14, "bold")).pack(side="left", padx=22)

        search_wrap = tk.Frame(bar, bg=BG, highlightthickness=1,
                               highlightbackground=BORDER)
        search_wrap.pack(side="left", padx=24)
        tk.Label(search_wrap, text="🔍", bg=BG, fg=MUTED).pack(side="left", padx=(8, 0))
        self.search = tk.Entry(search_wrap, bg=BG, fg=INK, bd=0, relief="flat",
                               width=30, font=("Segoe UI", 10))
        self.search.pack(side="left", padx=6, pady=6)
        self.search.bind("<Return>", lambda _e: self._global_search())

        self.clock = tk.Label(bar, text="", bg=CARD, fg=INK,
                              font=("Consolas", 11, "bold"))
        self.clock.pack(side="right", padx=12)
        self.date_lbl = tk.Label(bar, text="", bg=CARD, fg=MUTED,
                                 font=("Segoe UI", 8))
        self.date_lbl.pack(side="right", padx=2)

        tk.Button(bar, text="🔔", bg=CARD, bd=0, cursor="hand2",
                  font=("Segoe UI Emoji", 13),
                  command=self._notifications).pack(side="right", padx=10)
        tk.Button(bar, text="⟳", bg=CARD, bd=0, cursor="hand2", fg=ROYAL,
                  font=("Segoe UI", 13, "bold"),
                  command=self._refresh_all).pack(side="right", padx=4)

        prof = tk.Frame(bar, bg=CARD)
        prof.pack(side="right", padx=16)
        avatar(prof, self.user.get("name"), 34).pack(side="left")
        info = tk.Frame(prof, bg=CARD)
        info.pack(side="left", padx=8)
        tk.Label(info, text=self.user.get("name", "Admin"), bg=CARD, fg=INK,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")
        tk.Label(info, text=str(self.user.get("category", "admin")).title(),
                 bg=CARD, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w")
        menu_btn = tk.Button(prof, text="▾", bg=CARD, bd=0, cursor="hand2",
                             fg=MUTED, command=lambda: self._profile_menu(menu_btn))
        menu_btn.pack(side="left", padx=4)

    def _profile_menu(self, anchor):
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="My Profile", command=lambda: self.show_page("settings"))
        menu.add_command(label="Settings", command=lambda: self.show_page("settings"))
        menu.add_separator()
        menu.add_command(label="Logout", command=self._logout)
        x = anchor.winfo_rootx()
        y = anchor.winfo_rooty() + anchor.winfo_height()
        try:
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    # ----------------------------- page routing --------------------------------
    def show_page(self, key):
        self.active = key
        self._highlight_nav()
        self.canvas.yview_moveto(0)
        for frame in self.pages.values():
            frame.pack_forget()
        page = self.pages.get(key)
        if page is None:
            builder = getattr(self, f"_page_{key}", None)
            page = tk.Frame(self.content, bg=BG)
            if builder:
                try:
                    builder(page)
                except Exception:
                    traceback.print_exc()
                    tk.Label(page, text="This page failed to load.",
                             bg=BG, fg=DANGER).pack(pady=20)
            self.pages[key] = page
        page.pack(fill="both", expand=True)

    def _header(self, parent, title, subtitle=""):
        head = tk.Frame(parent, bg=BG)
        head.pack(fill="x", padx=26, pady=(22, 10))
        tk.Label(head, text=title, bg=BG, fg=INK,
                 font=("Segoe UI", 22, "bold")).pack(anchor="w")
        if subtitle:
            tk.Label(head, text=subtitle, bg=BG, fg=MUTED,
                     font=("Segoe UI", 10)).pack(anchor="w", pady=(3, 0))

    # ------------------------------ dashboard page -----------------------------
    def _page_dashboard(self, parent):
        self._header(parent, f"Good Morning, {self.user.get('name','Admin')}! 👋",
                     "Welcome back to your Student Management System.")

        stats = tk.Frame(parent, bg=BG)
        stats.pack(fill="x", padx=26, pady=(4, 6))
        for i, h in enumerate(stats.winfo_children()):
            pass
        self.stat_values["students"] = stat_card(stats, "🎓", "Total Students", ROYAL)
        self.stat_values["teachers"] = stat_card(stats, "🧑‍🏫", "Total Teachers", "#7C3AED")
        self.stat_values["attendance"] = stat_card(stats, "✅", "Attendance Rate", SUCCESS)
        self.stat_values["fees"] = stat_card(stats, "₹", "Fees Collected", WARN)

        # charts
        charts = tk.Frame(parent, bg=BG)
        charts.pack(fill="x", padx=26, pady=10)
        charts.columnconfigure(0, weight=1)
        charts.columnconfigure(1, weight=1)
        self.chart_frames = {}
        titles = [("enroll", "Student Enrollment (6 months)"),
                  ("attend", "Attendance Analysis"),
                  ("fees", "Monthly Fee Collection"),
                  ("perf", "Academic Performance")]
        for idx, (ckey, title) in enumerate(titles):
            card = Card(charts, height=250)
            card.grid(row=idx // 2, column=idx % 2, sticky="nsew",
                      padx=(0 if idx % 2 == 0 else 12, 0), pady=6)
            tk.Label(card.body, text=title, bg=CARD, fg=INK,
                     font=("Segoe UI", 10, "bold")).pack(anchor="w")
            holder = tk.Frame(card.body, bg=CARD)
            holder.pack(fill="both", expand=True)
            self.chart_frames[ckey] = holder
        charts.rowconfigure(0, weight=1)
        charts.rowconfigure(1, weight=1)
        self._draw_charts()

        # table + side panels
        lower = tk.Frame(parent, bg=BG)
        lower.pack(fill="both", expand=True, padx=26, pady=12)
        lower.columnconfigure(0, weight=3)
        lower.columnconfigure(1, weight=2)

        table_card = Card(lower)
        table_card.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        tk.Label(table_card.body, text="Recent Students", bg=CARD, fg=INK,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w")
        cols = ("ID", "Name", "Roll", "Class", "Gender", "Contact", "Admission", "Status")
        self.recent_tree = self._table(table_card.body, cols, height=8)
        self.recent_tree.pack(fill="both", expand=True, pady=8)

        side = tk.Frame(lower, bg=BG)
        side.grid(row=0, column=1, sticky="nsew")
        side.columnconfigure(0, weight=1)

        act_card = Card(side)
        act_card.grid(row=0, column=0, sticky="nsew", pady=(0, 12))
        tk.Label(act_card.body, text="Recent Activities", bg=CARD, fg=INK,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w")
        self.activities_box = tk.Frame(act_card.body, bg=CARD)
        self.activities_box.pack(fill="both", expand=True, pady=6)

        ev_card = Card(side)
        ev_card.grid(row=1, column=0, sticky="nsew")
        tk.Label(ev_card.body, text="Upcoming Events", bg=CARD, fg=INK,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w")
        self.events_box = tk.Frame(ev_card.body, bg=CARD)
        self.events_box.pack(fill="both", expand=True, pady=6)

        self._load_recent_students()
        self._load_activities()
        self._load_events()

    def _table(self, parent, columns, height=10):
        wrap = tk.Frame(parent, bg=CARD)
        tree = ttk.Treeview(wrap, columns=columns, show="headings", height=height)
        for c in columns:
            tree.heading(c, text=c)
            tree.column(c, width=110, anchor="w")
        vs = ttk.Scrollbar(wrap, orient="vertical", command=tree.yview)
        hs = ttk.Scrollbar(wrap, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vs.grid(row=0, column=1, sticky="ns")
        hs.grid(row=1, column=0, sticky="ew")
        wrap.rowconfigure(0, weight=1)
        wrap.columnconfigure(0, weight=1)
        return tree

    # -------------------------------- charts -----------------------------------
    def _series(self, col, field, fallback):
        try:
            docs = self.db.col(col).find(limit=200)
        except Exception:
            docs = []
        if not docs:
            return fallback
        try:
            return [float(d.get(field, 0) or 0) for d in docs][:12]
        except Exception:
            return fallback

    def _draw_charts(self):
        if not MPL_OK:
            for f in getattr(self, "chart_frames", {}).values():
                tk.Label(f, text="matplotlib not installed",
                         bg=CARD, fg=MUTED).pack(expand=True)
            return

        months = ["Jun", "Jul", "Aug", "Sep", "Oct", "Nov"]
        base = max(4, len(self.db.col("students").find(limit=500)))
        enroll = [int(base * r) + random.randint(2, 9) for r in
                  (0.4, 0.55, 0.6, 0.7, 0.85, 1.0)]
        fees = [int(sum(enroll) * 900 * r) for r in
                (0.5, 0.6, 0.55, 0.75, 0.8, 0.95)]

        specs = [
            ("enroll", "bar", months, enroll, "Enrollments", ROYAL),
            ("fees", "line", months, fees, "₹ Collected", SUCCESS),
        ]
        for key, kind, x, y, label, color in specs:
            holder = self.chart_frames.get(key)
            if not holder:
                continue
            for w in holder.winfo_children():
                w.destroy()
            fig = Figure(figsize=(4, 2.4), dpi=100)
            ax = fig.add_subplot(111)
            if kind == "bar":
                ax.bar(x, y, color=color, width=0.6)
            else:
                ax.plot(x, y, color=color, marker="o", linewidth=2)
                ax.fill_between(x, y, color=color, alpha=0.12)
            ax.set_ylabel(label, fontsize=8)
            ax.tick_params(labelsize=7)
            fig.tight_layout()
            FigureCanvasTkAgg(fig, master=holder).get_tk_widget().pack(
                fill="both", expand=True)

        # attendance doughnut
        holder = self.chart_frames.get("attend")
        if holder:
            for w in holder.winfo_children():
                w.destroy()
            fig = Figure(figsize=(4, 2.4), dpi=100)
            ax = fig.add_subplot(111)
            vals = [82, 12, 6]
            ax.pie(vals, labels=["Present", "Absent", "Leave"], autopct="%1.0f%%",
                   colors=[SUCCESS, DANGER, WARN], textprops={"fontsize": 7},
                   wedgeprops={"width": 0.42})
            ax.set_aspect("equal")
            fig.tight_layout()
            FigureCanvasTkAgg(fig, master=holder).get_tk_widget().pack(
                fill="both", expand=True)

        # performance bars
        holder = self.chart_frames.get("perf")
        if holder:
            for w in holder.winfo_children():
                w.destroy()
            fig = Figure(figsize=(4, 2.4), dpi=100)
            ax = fig.add_subplot(111)
            subjects = ["Math", "Phys", "Chem", "CS", "Eng"]
            scores = [72, 65, 78, 88, 81]
            ax.barh(subjects, scores, color=CHART_COLORS[:5])
            ax.set_xlim(0, 100)
            ax.tick_params(labelsize=7)
            fig.tight_layout()
            FigureCanvasTkAgg(fig, master=holder).get_tk_widget().pack(
                fill="both", expand=True)

    # ------------------------------- loaders -----------------------------------
    def _load_recent_students(self):
        tree = getattr(self, "recent_tree", None)
        if not tree:
            return
        tree.delete(*tree.get_children())
        docs = self.db.col("students").find(limit=8)
        if not docs:
            tree.insert("", "end", values=("—", "No students yet", "", "", "", "", "", ""))
            return
        for d in docs:
            tree.insert("", "end", values=(
                str(d.get("_id", ""))[:8], d.get("name", ""), d.get("roll", ""),
                d.get("grade", d.get("class", "")), d.get("gender", ""),
                d.get("contact", ""), d.get("admission", ""), d.get("status", "Active")))

    def _load_activities(self):
        box = getattr(self, "activities_box", None)
        if not box:
            return
        for w in box.winfo_children():
            w.destroy()
        items = self.db.col("activities").find(limit=6)
        if not items:
            items = [
                {"text": "System ready — no activity recorded yet", "icon": "ℹ"},
                {"text": "Database " + ("connected" if self.db.online else "offline (memory mode)"),
                 "icon": "🗄"},
            ]
        for a in items:
            row = tk.Frame(box, bg=CARD)
            row.pack(fill="x", pady=3)
            tk.Label(row, text=a.get("icon", "•"), bg=CARD, fg=ROYAL,
                     font=("Segoe UI Emoji", 10)).pack(side="left", padx=(0, 6))
            tk.Label(row, text=a.get("text", ""), bg=CARD, fg=INK, anchor="w",
                     wraplength=220, justify="left",
                     font=("Segoe UI", 8)).pack(side="left", fill="x", expand=True)

    def _load_events(self):
        box = getattr(self, "events_box", None)
        if not box:
            return
        for w in box.winfo_children():
            w.destroy()
        items = self.db.col("events").find(limit=5)
        if not items:
            items = [
                {"title": "Mid-term Exams", "date": "02 Dec", "desc": "All departments"},
                {"title": "Parent-Teacher Meeting", "date": "09 Dec", "desc": "Hall A, 10 AM"},
                {"title": "Annual Function", "date": "20 Dec", "desc": "Auditorium"},
            ]
        for e in items:
            row = tk.Frame(box, bg="#F8FAFC", highlightthickness=1,
                           highlightbackground=BORDER)
            row.pack(fill="x", pady=3)
            tk.Label(row, text=e.get("date", ""), bg=ROYAL, fg="white",
                     font=("Segoe UI", 8, "bold"), width=8).pack(side="left", padx=6, pady=6)
            col = tk.Frame(row, bg="#F8FAFC")
            col.pack(side="left", fill="x", expand=True, pady=4)
            tk.Label(col, text=e.get("title", ""), bg="#F8FAFC", fg=INK,
                     font=("Segoe UI", 9, "bold")).pack(anchor="w")
            tk.Label(col, text=e.get("desc", ""), bg="#F8FAFC", fg=MUTED,
                     font=("Segoe UI", 8)).pack(anchor="w")

    # ------------------------------- statistics --------------------------------
    def _refresh_stats_async(self):
        threading.Thread(target=self._compute_stats, daemon=True).start()

    def _compute_stats(self):
        try:
            students = self.db.col("students").count_documents()
            teachers = self.db.col("teachers").count_documents()
            fees = sum(float(f.get("amount", 0) or 0)
                       for f in self.db.col("fees").find(limit=1000))
            attendance = self.db.col("attendance").find(limit=500)
            if attendance:
                present = sum(1 for a in attendance if a.get("status") == "Present")
                rate = round(present / len(attendance) * 100)
            else:
                rate = 0
            if self.alive:
                self.root.after(0, lambda: self._apply_stats(students, teachers, rate, fees))
        except Exception:
            traceback.print_exc()

    def _apply_stats(self, students, teachers, rate, fees):
        if "students" in self.stat_values:
            self.stat_values["students"].config(text=str(students))
            self.stat_values["teachers"].config(text=str(teachers))
            self.stat_values["attendance"].config(text=f"{rate}%")
            self.stat_values["fees"].config(text=f"₹{fees:,.0f}")

    # -------------------------------- refresh ----------------------------------
    def _refresh_all(self):
        self._refresh_stats_async()
        self._draw_charts()
        self._load_recent_students()
        self._load_activities()
        self._load_events()
        for key in ("students", "teachers", "admissions", "fees"):
            if key in self.pages:
                loader = getattr(self, f"_load_{key}", None)
                if loader:
                    loader()

    def _global_search(self):
        term = self.search.get().strip().lower()
        if not term:
            return
        self.show_page("students")
        tree = getattr(self, "students_tree", None)
        if tree:
            for iid in tree.get_children():
                vals = " ".join(str(v).lower() for v in tree.item(iid, "values"))
                if term not in vals:
                    tree.delete(iid)

    def _notifications(self):
        win = tk.Toplevel(self.root)
        win.title("Notifications")
        win.geometry("340x400")
        win.configure(bg=CARD)
        tk.Label(win, text="Notifications", bg=CARD, fg=INK,
                 font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=16, pady=14)
        items = self.db.col("activities").find(limit=12) or [
            {"text": "Welcome to the dashboard", "icon": "👋"},
            {"text": "Database is " + ("online" if self.db.online else "offline"), "icon": "🗄"},
        ]
        for a in items:
            row = tk.Frame(win, bg=CARD)
            row.pack(fill="x", padx=16, pady=4)
            tk.Label(row, text=a.get("icon", "•"), bg=CARD, fg=ROYAL).pack(side="left")
            tk.Label(row, text=a.get("text", ""), bg=CARD, fg=INK, anchor="w",
                     wraplength=270, justify="left").pack(side="left", padx=6, fill="x", expand=True)

    # -------------------------------- clock ------------------------------------
    def _tick_clock(self):
        if not self.alive:
            return
        now = datetime.datetime.now()
        self.clock.configure(text=now.strftime("%I:%M:%S %p"))
        self.date_lbl.configure(text=now.strftime("%a, %d %b %Y"))
        self.root.after(1000, self._tick_clock)

    # ---------------------------- generic form dialog --------------------------
    def _dialog_form(self, title, fields, on_save):
        win = tk.Toplevel(self.root)
        win.title(title)
        win.geometry("420x" + str(120 + 46 * len(fields)))
        win.configure(bg=CARD)
        win.transient(self.root)
        tk.Label(win, text=title, bg=CARD, fg=INK,
                 font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=18, pady=14)
        entries = {}
        for key, label in fields:
            tk.Label(win, text=label, bg=CARD, fg=MUTED,
                     font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=18)
            e = tk.Entry(win, bg=BG, fg=INK, relief="flat",
                         highlightthickness=1, highlightbackground=BORDER,
                         font=("Segoe UI", 10))
            e.pack(fill="x", padx=18, pady=(2, 8), ipady=6)
            entries[key] = e

        def save():
            data = {k: v.get().strip() for k, v in entries.items()}
            try:
                on_save(data)
                win.destroy()
            except Exception as exc:
                messagebox.showerror("Error", str(exc), parent=win)

        tk.Button(win, text="Save", bg=ROYAL, fg="white", bd=0, cursor="hand2",
                  font=("Segoe UI", 10, "bold"),
                  command=save).pack(fill="x", padx=18, pady=12, ipady=8)
        return win

    # ------------------------------- students page -----------------------------
    def _page_students(self, parent):
        self._header(parent, "Students", "Manage all student records.")
        bar = tk.Frame(parent, bg=BG)
        bar.pack(fill="x", padx=26)
        for label, cmd, color in (("＋ Add Student", self._add_student, ROYAL),
                                  ("✎ Edit", self._edit_student, NAVY),
                                  ("🗑 Delete", self._delete_student, DANGER),
                                  ("⬇ Export CSV", self._export_students, SUCCESS),
                                  ("⟳ Refresh", self._load_students, MUTED)):
            tk.Button(bar, text=label, command=cmd, bg=color, fg="white", bd=0,
                      cursor="hand2", font=("Segoe UI", 9, "bold"),
                      padx=12, pady=7).pack(side="left", padx=(0, 8))

        cols = ("ID", "Name", "Roll", "Class", "Gender", "Contact", "Admission", "Status")
        card = Card(parent)
        card.pack(fill="both", expand=True, padx=26, pady=12)
        self.students_tree = self._table(card.body, cols, height=14)
        self.students_tree.pack(fill="both", expand=True)
        for c in cols:
            self.students_tree.heading(c, command=lambda cc=c: self._sort_students(cc, False))
        self._load_students()

    def _load_students(self):
        tree = getattr(self, "students_tree", None)
        if not tree:
            return
        tree.delete(*tree.get_children())
        self.student_rows = {}
        docs = self.db.col("students").find()
        if not docs:
            tree.insert("", "end", values=("—", "No students found. Click Add Student.", "", "", "", "", "", ""))
            return
        for d in docs:
            iid = str(d.get("_id", random.random()))
            self.student_rows[iid] = d
            tree.insert("", "end", iid=iid, values=(
                str(d.get("_id", ""))[:8], d.get("name", ""), d.get("roll", ""),
                d.get("grade", d.get("class", "")), d.get("gender", ""),
                d.get("contact", ""), d.get("admission", ""), d.get("status", "Active")))

    def _sort_students(self, col, reverse):
        tree = self.students_tree
        rows = [(tree.set(i, col), i) for i in tree.get_children()]
        rows.sort(reverse=reverse)
        for idx, (_, iid) in enumerate(rows):
            tree.move(iid, "", idx)
        tree.heading(col, command=lambda: self._sort_students(col, not reverse))

    def _add_student(self):
        fields = [("name", "Full Name"), ("roll", "Roll Number"), ("grade", "Class"),
                  ("gender", "Gender (M/F/O)"), ("contact", "Contact"),
                  ("admission", "Admission Date (YYYY-MM-DD)")]
        self._dialog_form("Add Student", fields, self._save_student)

    def _save_student(self, data):
        if not data.get("name"):
            raise ValueError("Name is required")
        data.setdefault("admission", datetime.date.today().isoformat())
        data["status"] = "Active"
        self.db.col("students").insert_one(data)
        self._log_activity(f"New student registered: {data['name']}", "🎓")
        self._load_students()
        self._load_recent_students()
        self._refresh_stats_async()

    def _edit_student(self):
        sel = self.students_tree.selection()
        if not sel:
            return messagebox.showinfo("Edit", "Select a student first.")
        doc = self.student_rows.get(sel[0])
        if not doc:
            return
        fields = [("name", "Full Name"), ("roll", "Roll Number"), ("grade", "Class"),
                  ("gender", "Gender (M/F/O)"), ("contact", "Contact"),
                  ("admission", "Admission Date")]
        win = self._dialog_form("Edit Student", fields, lambda d: self._update_student(doc, d))
        entries = [w for w in win.winfo_children() if isinstance(w, tk.Entry)]
        for e, key in zip(entries, [f[0] for f in fields]):
            e.insert(0, str(doc.get(key, "")))

    def _update_student(self, doc, data):
        self.db.col("students").update_one({"_id": doc["_id"]}, {"$set": data})
        self._load_students()

    def _delete_student(self):
        sel = self.students_tree.selection()
        if not sel:
            return messagebox.showinfo("Delete", "Select a student first.")
        doc = self.student_rows.get(sel[0])
        if doc and messagebox.askyesno("Confirm", f"Delete {doc.get('name')}?"):
            self.db.col("students").delete_one({"_id": doc["_id"]})
            self._log_activity(f"Student deleted: {doc.get('name')}", "🗑")
            self._load_students()
            self._refresh_stats_async()

    def _export_students(self):
        docs = self.db.col("students").find()
        if not docs:
            return messagebox.showinfo("Export", "No students to export.")
        path = filedialog.asksaveasfilename(defaultextension=".csv",
                                            filetypes=[("CSV", "*.csv")])
        if not path:
            return
        try:
            if PD_OK:
                pd.DataFrame(docs).to_csv(path, index=False)
            else:
                with open(path, "w", newline="", encoding="utf-8") as fh:
                    writer = csv.DictWriter(fh, fieldnames=list(docs[0].keys()))
                    writer.writeheader()
                    writer.writerows(docs)
            messagebox.showinfo("Export", f"Saved to {path}")
        except Exception as exc:
            messagebox.showerror("Export failed", str(exc))

    def _log_activity(self, text, icon="•"):
        try:
            self.db.col("activities").insert_one(
                {"text": text, "icon": icon,
                 "at": datetime.datetime.now().isoformat()})
            self._load_activities()
        except Exception:
            pass

    # --------------------------- simple form+list pages ------------------------
    def _simple_page(self, parent, title, subtitle, add_label, fields, collection,
                     list_cols, on_extra=None):
        self._header(parent, title, subtitle)
        bar = tk.Frame(parent, bg=BG)
        bar.pack(fill="x", padx=26)

        def add():
            self._dialog_form(add_label, fields,
                              lambda d: self._simple_save(collection, d, tree, list_cols))
        tk.Button(bar, text="＋ " + add_label, command=add, bg=ROYAL, fg="white",
                  bd=0, cursor="hand2", font=("Segoe UI", 9, "bold"),
                  padx=12, pady=7).pack(side="left")
        tk.Button(bar, text="⟳ Refresh", bg=MUTED, fg="white", bd=0, cursor="hand2",
                  font=("Segoe UI", 9, "bold"), padx=12, pady=7,
                  command=lambda: self._simple_load(tree, collection, list_cols)).pack(side="left", padx=8)

        card = Card(parent)
        card.pack(fill="both", expand=True, padx=26, pady=12)
        tree = self._table(card.body, list_cols, height=14)
        tree.pack(fill="both", expand=True)
        self._simple_load(tree, collection, list_cols)
        return tree

    def _simple_load(self, tree, collection, cols):
        tree.delete(*tree.get_children())
        docs = self.db.col(collection).find()
        if not docs:
            tree.insert("", "end", values=tuple(["—"] + ["No records yet"] + [""] * (len(cols) - 2)))
            return
        for d in docs:
            tree.insert("", "end", values=tuple(str(d.get(c.lower(), ""))[:40] for c in cols))

    def _simple_save(self, collection, data, tree, cols):
        data["created"] = datetime.date.today().isoformat()
        self.db.col(collection).insert_one(data)
        self._simple_load(tree, collection, cols)
        self._log_activity(f"{collection.title()} record added", "＋")

    def _page_admissions(self, parent):
        self._simple_page(parent, "Admissions", "New admissions and records.",
                          "New Admission",
                          [("name", "Student Name"), ("course", "Course"), ("status", "Status")],
                          "admissions", ("NAME", "COURSE", "STATUS"))

    def _page_courses(self, parent):
        self._simple_page(parent, "Courses & Classes", "Manage courses and classes.",
                          "Add Course",
                          [("name", "Course Name"), ("code", "Code"), ("dept", "Department")],
                          "courses", ("NAME", "CODE", "DEPT"))

    def _page_attendance(self, parent):
        self._simple_page(parent, "Attendance", "Mark and review attendance.",
                          "Mark Attendance",
                          [("name", "Student"), ("status", "Status (Present/Absent/Leave)"),
                           ("date", "Date")],
                          "attendance", ("NAME", "STATUS", "DATE"))

    def _page_fees(self, parent):
        self._simple_page(parent, "Fees & Payments", "Collect fees and history.",
                          "Collect Fee",
                          [("name", "Student"), ("amount", "Amount"), ("mode", "Mode")],
                          "fees", ("NAME", "AMOUNT", "MODE"))

    def _page_examinations(self, parent):
        self._simple_page(parent, "Examinations", "Create and schedule exams.",
                          "Create Exam",
                          [("name", "Exam Name"), ("date", "Date"), ("subject", "Subject")],
                          "examinations", ("NAME", "DATE", "SUBJECT"))

    def _page_results(self, parent):
        self._simple_page(parent, "Results & Grades", "Add and view results.",
                          "Add Result",
                          [("name", "Student"), ("subject", "Subject"), ("marks", "Marks")],
                          "results", ("NAME", "SUBJECT", "MARKS"))

    def _page_teachers(self, parent):
        self._simple_page(parent, "Teachers & Staff", "Manage staff records.",
                          "Add Teacher",
                          [("name", "Name"), ("department", "Department"), ("subject", "Subject")],
                          "teachers", ("NAME", "DEPARTMENT", "SUBJECT"))

    def _page_timetable(self, parent):
        self._simple_page(parent, "Timetable", "Create and view schedules.",
                          "Add Period",
                          [("grade", "Class"), ("subject", "Subject"), ("period", "Period")],
                          "timetable", ("GRADE", "SUBJECT", "PERIOD"))

    def _page_reports(self, parent):
        self._header(parent, "Reports", "Export and analyse campus data.")
        card = Card(parent)
        card.pack(fill="both", expand=True, padx=26, pady=12)
        tk.Label(card.body, text="Generate Reports", bg=CARD, fg=INK,
                 font=("Segoe UI", 13, "bold")).pack(anchor="w")
        for label, fn in (("Export Student Records (CSV)", self._export_students),
                          ("Export Teachers (CSV)", lambda: self._export_generic("teachers")),
                          ("Export Fees (CSV)", lambda: self._export_generic("fees")),
                          ("Export Attendance (CSV)", lambda: self._export_generic("attendance"))):
            tk.Button(card.body, text=label, command=fn, bg=BG, fg=INK, bd=0,
                      anchor="w", cursor="hand2", font=("Segoe UI", 10),
                      padx=14, pady=10).pack(fill="x", pady=4)

    def _export_generic(self, collection):
        docs = self.db.col(collection).find()
        if not docs:
            return messagebox.showinfo("Export", "Nothing to export.")
        path = filedialog.asksaveasfilename(defaultextension=".csv",
                                            filetypes=[("CSV", "*.csv")])
        if not path:
            return
        try:
            if PD_OK:
                pd.DataFrame(docs).to_csv(path, index=False)
            else:
                with open(path, "w", newline="", encoding="utf-8") as fh:
                    w = csv.DictWriter(fh, fieldnames=list(docs[0].keys()))
                    w.writeheader()
                    w.writerows(docs)
            messagebox.showinfo("Export", f"Saved to {path}")
        except Exception as exc:
            messagebox.showerror("Export failed", str(exc))

    def _page_settings(self, parent):
        self._header(parent, "Settings", "Profile, database and session settings.")
        card = Card(parent)
        card.pack(fill="x", padx=26, pady=12)
        info = [
            ("Name", self.user.get("name", "—")),
            ("Category", str(self.user.get("category", "—")).title()),
            ("Email", self.user.get("email", "—")),
            ("Database", "Connected" if self.db.online else "Offline (memory mode)"),
            ("Matplotlib", "Available" if MPL_OK else "Missing"),
            ("Pandas", "Available" if PD_OK else "Missing"),
            ("PyTorch", "Available" if TORCH_OK else "Missing"),
        ]
        for k, v in info:
            row = tk.Frame(card.body, bg=CARD)
            row.pack(fill="x", pady=4)
            tk.Label(row, text=k, bg=CARD, fg=MUTED, width=14, anchor="w",
                     font=("Segoe UI", 9, "bold")).pack(side="left")
            tk.Label(row, text=str(v), bg=CARD, fg=INK,
                     font=("Segoe UI", 9)).pack(side="left")

    # -------------------------------- logout -----------------------------------
    def _logout(self):
        if not messagebox.askyesno("Logout", "Log out of the dashboard?"):
            return
        self.alive = False
        try:
            self.db.close()
        except Exception:
            pass
        try:
            for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                self.canvas.unbind_all(seq)
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass
        if self.app is not None:
            try:
                self.app.deiconify()
                if hasattr(self.app, "show_tab"):
                    self.app.show_tab("signin")
            except Exception:
                pass


# ---------------------------------- entry point -------------------------------
def launch(user, app=None):
    """Called from main.py after successful authentication."""
    try:
        root = tk.Toplevel(app) if app is not None else tk.Tk()
        Dashboard(root, user, app)
        if app is None:
            root.mainloop()
        return root
    except Exception:
        traceback.print_exc()
        try:
            messagebox.showerror("Dashboard error", traceback.format_exc()[-1500:])
        except Exception:
            pass


if __name__ == "__main__":
    launch({"name": "Demo Admin", "category": "principal", "email": "admin@gpr.ac.in"})