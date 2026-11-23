import os
import io
import csv
import base64
import random
import hashlib
import secrets
import datetime
import threading
import traceback
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

try:
    from PIL import Image, ImageTk
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
except Exception:
    pass

try:
    import pandas as pd
    PD_OK = True
except Exception:
    PD_OK = False

try:
    from pymongo import MongoClient
    MONGO_OK = True
except Exception:
    MONGO_OK = False

try:
    import torch  # noqa: F401
except Exception:
    pass


# ----------------------------------- theme ------------------------------------
NAVY = "#172554"
NAVY_HOVER = "#1E3A6E"
ROYAL = "#2563EB"
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

# Demo logo — replace with your college logo (local path or URL)
LOGO_PATH = "https://placehold.co/64x64/2563EB/FFFFFF/png?text=GPR"

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

# role -> allowed menu keys (student least, teacher middle, principal all)
ROLE_NAV = {
    "principal": [k for k, _, _ in NAV_ITEMS],
    "teacher": ["dashboard", "students", "courses", "attendance",
                "examinations", "results", "timetable", "reports", "settings"],
    "student": ["dashboard", "courses", "attendance", "fees",
                "results", "timetable", "settings"],
}

MONGO_URI = os.environ.get("SMS_MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.environ.get("SMS_DB", "student_management")


# ------------------------------- password helpers -----------------------------
def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 180_000)
    return {"salt": salt, "hash": digest.hex()}


def verify_password(password, record):
    try:
        if not record or not record.get("salt"):
            return False
        return secrets.compare_digest(
            hash_password(password, record["salt"])["hash"], record["hash"])
    except Exception:
        return False


# -------------------------------- data layer ----------------------------------
class MemCol:
    def __init__(self):
        self.docs = []

    def _m(self, d, q):
        return all(d.get(k) == v for k, v in (q or {}).items())

    def find(self, query=None, limit=0):
        out = [d for d in self.docs if self._m(d, query)]
        return out[:limit] if limit else out

    def insert_one(self, doc):
        doc = dict(doc)
        doc.setdefault("_id", f"mem-{len(self.docs)}-{random.randint(0, 99999)}")
        self.docs.append(doc)
        return doc

    def update_one(self, query, update):
        for d in self.docs:
            if self._m(d, query):
                d.update(update.get("$set", {}))
                return

    def delete_one(self, query):
        for i, d in enumerate(self.docs):
            if self._m(d, query):
                del self.docs[i]
                return

    def count_documents(self, query=None):
        return len(self.find(query))


class DB:
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


# --------------------------------- widgets ------------------------------------
class Card(tk.Canvas):
    def __init__(self, master, bg=CARD, radius=16, pad=16, border=BORDER, **kw):
        super().__init__(master, bg=master.cget("bg"), highlightthickness=0, bd=0, **kw)
        self.radius, self.pad, self.fill, self.border = radius, pad, bg, border
        self.body = tk.Frame(self, bg=bg)
        self._win = self.create_window(0, 0, window=self.body, anchor="nw")
        self.bind("<Configure>", self._redraw)

    def _round(self, x1, y1, x2, y2, r):
        pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
               x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
        self.create_polygon(pts, smooth=True, splinesteps=24,
                            fill=self.fill, outline=self.border)

    def _redraw(self, _e=None):
        w, h = self.winfo_width(), self.winfo_height()
        if w < 4 or h < 4:
            return
        self.delete("all")
        self._win = self.create_window(self.pad, self.pad, window=self.body, anchor="nw")
        self._round(0, 0, w - 1, h - 1, self.radius)
        self.body.configure(width=max(1, w - 2 * self.pad), height=max(1, h - 2 * self.pad))
        self.tag_raise(self._win)


class ScrollArea(tk.Frame):
    """A frame with its own always-visible vertical scrollbar."""
    def __init__(self, master, bg=BG):
        super().__init__(master, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.vbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.vbar.pack(side="right", fill="y")
        self.inner = tk.Frame(self.canvas, bg=bg)
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>",
                        lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>",
                         lambda e: self.canvas.itemconfigure(self._win, width=e.width))

    def scroll(self, units):
        self.canvas.yview_scroll(int(units), "units")

    def reset(self):
        self.canvas.yview_moveto(0)


class Avatar(tk.Canvas):
    def __init__(self, master, name, photo=None, size=38, bg=ROYAL, on_click=None):
        super().__init__(master, width=size, height=size,
                         bg=master.cget("bg"), highlightthickness=0, cursor="hand2")
        self.photo = photo
        if photo:
            self.create_image(size / 2, size / 2, image=photo)
        else:
            self.create_oval(1, 1, size - 1, size - 1, fill=bg, outline="")
            self.create_text(size / 2, size / 2, text=(name or "U")[:1].upper(),
                             fill="white", font=("Segoe UI", int(size / 2.4), "bold"))
        if on_click:
            self.bind("<Button-1>", lambda _e: on_click())


def stat_card(parent, icon, label, accent):
    card = Card(parent, height=132)
    card.pack(side="left", fill="both", expand=True, padx=(0, 14))
    tk.Label(card.body, text=icon, bg=CARD, fg=accent,
             font=("Segoe UI Emoji", 20)).pack(anchor="w")
    value = tk.Label(card.body, text="0", bg=CARD, fg=INK, font=("Segoe UI", 24, "bold"))
    value.pack(anchor="w", pady=(4, 0))
    tk.Label(card.body, text=label, bg=CARD, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w")
    tk.Frame(card.body, bg=accent, height=4).pack(fill="x", pady=(8, 0))
    return value


# ================================== DASHBOARD =================================
class Dashboard:
    def __init__(self, root, user, app):
        self.root = root
        self.user = user or {"name": "Admin", "category": "principal"}
        self.role = str(self.user.get("category", "principal")).lower()
        self.app = app
        self.db = DB()
        self.active = "dashboard"
        self.nav_buttons = {}
        self.pages = {}
        self.scroll_areas = {}
        self.student_rows = {}
        self.stat_values = {}
        self._acc = {}
        self.alive = True
        self.logo_photo = None
        self.user_photo = None
        self.user_pil = None

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
        self._load_user_avatar()
        self.show_page("dashboard")
        self._tick_clock()
        self._refresh_stats_async()
        self.root.protocol("WM_DELETE_WINDOW", self._logout)

    # -------------------------------- styling ---------------------------------
    def _style(self):
        s = ttk.Style(self.root)
        try:
            s.theme_use("clam")
        except Exception:
            pass
        s.configure("Treeview", background=CARD, fieldbackground=CARD, foreground=INK,
                    rowheight=30, borderwidth=0, font=("Segoe UI", 9))
        s.configure("Treeview.Heading", background=NAVY, foreground="white",
                    font=("Segoe UI", 9, "bold"), borderwidth=0)
        s.map("Treeview", background=[("selected", "#DBEAFE")], foreground=[("selected", INK)])
        s.configure("TScrollbar", background="#CBD5E1", troughcolor=BG, borderwidth=0)

    # --------------------------------- shell ----------------------------------
    def _build_shell(self):
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)
        self._build_sidebar()

        right = tk.Frame(self.root, bg=BG)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)
        self._build_topbar(right)

        self.host = tk.Frame(right, bg=BG)
        self.host.grid(row=1, column=0, sticky="nsew")

        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.root.bind_all(seq, self._on_wheel)

    def _area_at(self, event):
        try:
            w = self.root.winfo_containing(event.x_root, event.y_root)
        except Exception:
            return None
        while w is not None:
            if isinstance(w, ScrollArea):
                return w
            w = getattr(w, "master", None)
        return None

    def _on_wheel(self, event):
        area = self._area_at(event)
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
            thr = 120 if abs(d) >= 120 else 20   # low threshold = responsive trackpad
            acc = self._acc.get(id(area), 0) + d
            step = int(-acc / thr)
            if step == 0:
                self._acc[id(area)] = acc
                if abs(acc) < thr:
                    return "break"
                step = -1 if acc > 0 else 1
                acc = 0
            self._acc[id(area)] = acc
        area.scroll(step)
        return "break"

    def _build_sidebar(self):
        bar = tk.Frame(self.root, bg=NAVY, width=SIDEBAR_W)
        bar.grid(row=0, column=0, sticky="ns")
        bar.grid_propagate(False)

        brand = tk.Frame(bar, bg=NAVY)
        brand.pack(fill="x", pady=(18, 8), padx=16)
        self.logo_box = tk.Frame(brand, bg="white", width=44, height=44)
        self.logo_box.pack(side="left")
        self.logo_box.pack_propagate(False)
        self.logo_lbl = tk.Label(self.logo_box, text="🎓", bg="white", fg=ROYAL,
                                 font=("Segoe UI Emoji", 18))
        self.logo_lbl.pack(expand=True, fill="both")
        self._load_logo()
        tk.Label(brand, text="SMS\nCampus", bg=NAVY, fg="white", justify="left",
                 font=("Segoe UI", 12, "bold")).pack(side="left", padx=8)

        tk.Frame(bar, bg=NAVY_HOVER, height=1).pack(fill="x", padx=14, pady=8)

        nav_host = tk.Frame(bar, bg=NAVY)
        nav_host.pack(fill="x")
        allowed = ROLE_NAV.get(self.role, ROLE_NAV["principal"])
        for key, label, icon in NAV_ITEMS:
            if key not in allowed:
                continue
            btn = tk.Frame(nav_host, bg=NAVY, cursor="hand2")
            btn.pack(fill="x", padx=10, pady=1)
            inner = tk.Frame(btn, bg=NAVY)
            inner.pack(fill="x", padx=8, pady=7)
            ic = tk.Label(inner, text=icon, bg=NAVY, fg="#93A6C6", font=("Segoe UI Emoji", 12))
            ic.pack(side="left")
            tx = tk.Label(inner, text=label, bg=NAVY, fg="#C7D2E4", font=("Segoe UI", 10))
            tx.pack(side="left", padx=10)
            for w in (btn, inner, ic, tx):
                w.bind("<Button-1>", lambda _e, k=key: self.show_page(k))
                w.bind("<Enter>", lambda _e, b=btn: self._hover(b, True))
                w.bind("<Leave>", lambda _e, b=btn: self._hover(b, False))
            self.nav_buttons[key] = (btn, inner, ic, tx)

        bottom = tk.Frame(bar, bg=NAVY)
        bottom.pack(side="bottom", fill="x", pady=14, padx=14)
        tk.Button(bottom, text="⏻  Logout", command=self._logout, bd=0, bg=DANGER,
                  fg="white", activebackground="#B91C1C", activeforeground="white",
                  cursor="hand2", font=("Segoe UI", 10, "bold"), pady=9).pack(fill="x")

    def _load_logo(self):
        if not PIL_OK or not LOGO_PATH:
            return
        def worker():
            try:
                if LOGO_PATH.lower().startswith("http"):
                    import urllib.request
                    req = urllib.request.Request(LOGO_PATH, headers={"User-Agent": "Mozilla/5.0"})
                    data = urllib.request.urlopen(req, timeout=6).read()
                    img = Image.open(io.BytesIO(data))
                else:
                    img = Image.open(LOGO_PATH)
                img = img.convert("RGBA")
                img.thumbnail((40, 40))
                photo = ImageTk.PhotoImage(img)
                if self.alive:
                    self.root.after(0, lambda: self.logo_lbl.configure(image=photo, text=""))
                    self.logo_photo = photo
            except Exception:
                pass
        threading.Thread(target=worker, daemon=True).start()

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
    def _walk(w):
        yield w
        for c in w.winfo_children():
            yield from Dashboard._walk(c)

    def _highlight_nav(self):
        for key, (btn, inner, ic, tx) in self.nav_buttons.items():
            on = key == self.active
            bg = ROYAL if on else NAVY
            for w in (btn, inner):
                w.configure(bg=bg)
            ic.configure(bg=bg, fg="white" if on else "#93A6C6")
            tx.configure(bg=bg, fg="white" if on else "#C7D2E4",
                         font=("Segoe UI", 10, "bold" if on else "normal"))

    def _build_topbar(self, parent):
        bar = tk.Frame(parent, bg=CARD, height=64)
        bar.grid(row=0, column=0, columnspan=2, sticky="ew")
        bar.grid_propagate(False)
        tk.Label(bar, text="Student Management System", bg=CARD, fg=NAVY,
                 font=("Segoe UI", 14, "bold")).pack(side="left", padx=22)

        sw = tk.Frame(bar, bg=BG, highlightthickness=1, highlightbackground=BORDER)
        sw.pack(side="left", padx=24)
        tk.Label(sw, text="🔍", bg=BG, fg=MUTED).pack(side="left", padx=(8, 0))
        self.search = tk.Entry(sw, bg=BG, fg=INK, bd=0, relief="flat", width=30,
                               font=("Segoe UI", 10))
        self.search.pack(side="left", padx=6, pady=6)
        self.search.bind("<Return>", lambda _e: self._global_search())

        self.clock = tk.Label(bar, text="", bg=CARD, fg=INK, font=("Consolas", 11, "bold"))
        self.clock.pack(side="right", padx=12)
        self.date_lbl = tk.Label(bar, text="", bg=CARD, fg=MUTED, font=("Segoe UI", 8))
        self.date_lbl.pack(side="right")

        tk.Button(bar, text="🔔", bg=CARD, bd=0, cursor="hand2",
                  font=("Segoe UI Emoji", 13), command=self._notifications).pack(side="right", padx=8)
        tk.Button(bar, text="⟳", bg=CARD, bd=0, cursor="hand2", fg=ROYAL,
                  font=("Segoe UI", 13, "bold"), command=self._refresh_all).pack(side="right", padx=4)

        prof = tk.Frame(bar, bg=CARD)
        prof.pack(side="right", padx=16)
        self.top_avatar = Avatar(prof, self.user.get("name"), photo=self.user_photo, size=34,
                                 on_click=self._view_user_image)
        self.top_avatar.pack(side="left")
        info = tk.Frame(prof, bg=CARD)
        info.pack(side="left", padx=8)
        tk.Label(info, text=self.user.get("name", "Admin"), bg=CARD, fg=INK,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")
        tk.Label(info, text=self.role.title(), bg=CARD, fg=MUTED,
                 font=("Segoe UI", 8)).pack(anchor="w")
        mb = tk.Button(prof, text="▾", bg=CARD, bd=0, cursor="hand2", fg=MUTED,
                       command=lambda: self._profile_menu(mb))
        mb.pack(side="left", padx=4)

    def _profile_menu(self, anchor):
        m = tk.Menu(self.root, tearoff=0)
        m.add_command(label="My Profile", command=lambda: self.show_page("settings"))
        m.add_command(label="Settings", command=lambda: self.show_page("settings"))
        m.add_separator()
        m.add_command(label="Logout", command=self._logout)
        try:
            m.tk_popup(anchor.winfo_rootx(), anchor.winfo_rooty() + anchor.winfo_height())
        finally:
            m.grab_release()

    # ------------------------------ routing -----------------------------------
    def show_page(self, key):
        self.active = key
        self._highlight_nav()
        for f in self.pages.values():
            f.pack_forget()
        page = self.pages.get(key)
        if page is None:
            page = ScrollArea(self.host)
            self.scroll_areas[key] = page
            builder = getattr(self, f"_page_{key}", None)
            if builder:
                try:
                    builder(page.inner)
                except Exception:
                    traceback.print_exc()
                    tk.Label(page.inner, text="This page failed to load.", bg=BG,
                             fg=DANGER).pack(pady=20)
            self.pages[key] = page
        page.pack(fill="both", expand=True)
        page.reset()

    def _header(self, parent, title, subtitle=""):
        h = tk.Frame(parent, bg=BG)
        h.pack(fill="x", padx=26, pady=(22, 10))
        tk.Label(h, text=title, bg=BG, fg=INK, font=("Segoe UI", 22, "bold")).pack(anchor="w")
        if subtitle:
            tk.Label(h, text=subtitle, bg=BG, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w", pady=(3, 0))

    def _table(self, parent, columns, height=12):
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

    # ---------------------------- dashboard page ------------------------------
    def _page_dashboard(self, parent):
        self._header(parent, f"Good Morning, {self.user.get('name','Admin')}! 👋",
                     "Welcome back to your Student Management System.")

        stats = tk.Frame(parent, bg=BG)
        stats.pack(fill="x", padx=26, pady=(4, 6))
        if self.role == "student":
            self.stat_values["attendance"] = stat_card(stats, "✅", "My Attendance", SUCCESS)
            self.stat_values["fees"] = stat_card(stats, "₹", "Fees Paid", WARN)
            self.stat_values["exams"] = stat_card(stats, "📄", "Upcoming Exams", ROYAL)
            self.stat_values["subjects"] = stat_card(stats, "📚", "My Subjects", "#7C3AED")
        elif self.role == "teacher":
            self.stat_values["students"] = stat_card(stats, "🎓", "My Students", ROYAL)
            self.stat_values["classes"] = stat_card(stats, "📚", "Classes", "#7C3AED")
            self.stat_values["attendance"] = stat_card(stats, "✅", "Attendance Rate", SUCCESS)
            self.stat_values["results"] = stat_card(stats, "🏅", "Pending Results", WARN)
        else:
            self.stat_values["students"] = stat_card(stats, "🎓", "Total Students", ROYAL)
            self.stat_values["teachers"] = stat_card(stats, "🧑‍🏫", "Total Teachers", "#7C3AED")
            self.stat_values["attendance"] = stat_card(stats, "✅", "Attendance Rate", SUCCESS)
            self.stat_values["fees"] = stat_card(stats, "₹", "Fees Collected", WARN)

        charts = tk.Frame(parent, bg=BG)
        charts.pack(fill="x", padx=26, pady=10)
        charts.columnconfigure(0, weight=1)
        charts.columnconfigure(1, weight=1)
        self.chart_frames = {}
        for idx, (ck, title) in enumerate([("enroll", "Student Enrollment (6 months)"),
                                           ("attend", "Attendance Analysis"),
                                           ("fees", "Monthly Fee Collection"),
                                           ("perf", "Academic Performance")]):
            card = Card(charts, height=250)
            card.grid(row=idx // 2, column=idx % 2, sticky="nsew",
                      padx=(0 if idx % 2 == 0 else 12, 0), pady=6)
            tk.Label(card.body, text=title, bg=CARD, fg=INK,
                     font=("Segoe UI", 10, "bold")).pack(anchor="w")
            holder = tk.Frame(card.body, bg=CARD)
            holder.pack(fill="both", expand=True)
            self.chart_frames[ck] = holder
        self._draw_charts()

        lower = tk.Frame(parent, bg=BG)
        lower.pack(fill="both", expand=True, padx=26, pady=12)
        lower.columnconfigure(0, weight=3)
        lower.columnconfigure(1, weight=2)

        tc = Card(lower, height=330)
        tc.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        tk.Label(tc.body, text="Recent Students", bg=CARD, fg=INK,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w")
        cols = ("ID", "Name", "Roll", "Class", "Gender", "Contact", "Status")
        self.recent_tree = self._table(tc.body, cols, height=8)
        self.recent_tree.pack(fill="both", expand=True, pady=6)
        self.recent_tree.bind("<Double-1>", self._open_selected_student)

        side = tk.Frame(lower, bg=BG)
        side.grid(row=0, column=1, sticky="nsew")
        ac = Card(side, height=160)
        ac.grid(row=0, column=0, sticky="nsew", pady=(0, 12))
        tk.Label(ac.body, text="Recent Activities", bg=CARD, fg=INK,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w")
        self.activities_box = tk.Frame(ac.body, bg=CARD)
        self.activities_box.pack(fill="both", expand=True, pady=4)
        ec = Card(side, height=160)
        ec.grid(row=1, column=0, sticky="nsew")
        tk.Label(ec.body, text="Upcoming Events", bg=CARD, fg=INK,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w")
        self.events_box = tk.Frame(ec.body, bg=CARD)
        self.events_box.pack(fill="both", expand=True, pady=4)

        self._load_recent_students()
        self._load_activities()
        self._load_events()

    def _draw_charts(self):
        if not MPL_OK:
            for f in getattr(self, "chart_frames", {}).values():
                tk.Label(f, text="matplotlib not installed", bg=CARD, fg=MUTED).pack(expand=True)
            return
        months = ["Jun", "Jul", "Aug", "Sep", "Oct", "Nov"]
        base = max(4, len(self.db.col("students").find(limit=500)))
        enroll = [int(base * r) + random.randint(2, 9) for r in (0.4, .55, .6, .7, .85, 1.0)]
        fees = [int(sum(enroll) * 900 * r) for r in (.5, .6, .55, .75, .8, .95)]

        for key, kind, y, color in (("enroll", "bar", enroll, ROYAL),
                                    ("fees", "line", fees, SUCCESS)):
            holder = self.chart_frames.get(key)
            if not holder:
                continue
            for w in holder.winfo_children():
                w.destroy()
            fig = Figure(figsize=(4, 2.3), dpi=100)
            ax = fig.add_subplot(111)
            if kind == "bar":
                ax.bar(months, y, color=color, width=0.6)
            else:
                ax.plot(months, y, color=color, marker="o")
                ax.fill_between(months, y, color=color, alpha=0.12)
            ax.tick_params(labelsize=7)
            fig.tight_layout()
            FigureCanvasTkAgg(fig, master=holder).get_tk_widget().pack(fill="both", expand=True)

        holder = self.chart_frames.get("attend")
        if holder:
            for w in holder.winfo_children():
                w.destroy()
            fig = Figure(figsize=(4, 2.3), dpi=100)
            ax = fig.add_subplot(111)
            ax.pie([82, 12, 6], labels=["Present", "Absent", "Leave"], autopct="%1.0f%%",
                   colors=[SUCCESS, DANGER, WARN], textprops={"fontsize": 7},
                   wedgeprops={"width": 0.42})
            ax.set_aspect("equal")
            fig.tight_layout()
            FigureCanvasTkAgg(fig, master=holder).get_tk_widget().pack(fill="both", expand=True)

        holder = self.chart_frames.get("perf")
        if holder:
            for w in holder.winfo_children():
                w.destroy()
            fig = Figure(figsize=(4, 2.3), dpi=100)
            ax = fig.add_subplot(111)
            ax.barh(["Math", "Phys", "Chem", "CS", "Eng"], [72, 65, 78, 88, 81],
                    color=CHART_COLORS[:5])
            ax.set_xlim(0, 100)
            ax.tick_params(labelsize=7)
            fig.tight_layout()
            FigureCanvasTkAgg(fig, master=holder).get_tk_widget().pack(fill="both", expand=True)

    def _load_recent_students(self):
        t = getattr(self, "recent_tree", None)
        if not t:
            return
        t.delete(*t.get_children())
        docs = self.db.col("students").find(limit=8)
        if not docs:
            t.insert("", "end", values=("—", "No students yet", "", "", "", "", ""))
            return
        for d in docs:
            iid = str(d.get("_id"))
            self.student_rows[iid] = d
            t.insert("", "end", iid=iid, values=(
                str(d.get("_id", ""))[:8], d.get("name", ""), d.get("roll", ""),
                d.get("grade", ""), d.get("gender", ""), d.get("contact", ""),
                d.get("status", "Active")))

    def _load_activities(self):
        b = getattr(self, "activities_box", None)
        if not b:
            return
        for w in b.winfo_children():
            w.destroy()
        items = self.db.col("activities").find(limit=6) or [
            {"text": "System ready", "icon": "ℹ"},
            {"text": "Database " + ("connected" if self.db.online else "offline (memory)"), "icon": "🗄"}]
        for a in items:
            row = tk.Frame(b, bg=CARD)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=a.get("icon", "•"), bg=CARD, fg=ROYAL,
                     font=("Segoe UI Emoji", 9)).pack(side="left", padx=(0, 6))
            tk.Label(row, text=a.get("text", ""), bg=CARD, fg=INK, anchor="w",
                     wraplength=210, justify="left", font=("Segoe UI", 8)).pack(side="left", fill="x", expand=True)

    def _load_events(self):
        b = getattr(self, "events_box", None)
        if not b:
            return
        for w in b.winfo_children():
            w.destroy()
        items = self.db.col("events").find(limit=5) or [
            {"title": "Mid-term Exams", "date": "02 Dec", "desc": "All departments"},
            {"title": "Parent-Teacher Meeting", "date": "09 Dec", "desc": "Hall A"}]
        for e in items:
            row = tk.Frame(b, bg="#F8FAFC", highlightthickness=1, highlightbackground=BORDER)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=e.get("date", ""), bg=ROYAL, fg="white",
                     font=("Segoe UI", 8, "bold"), width=7).pack(side="left", padx=5, pady=5)
            col = tk.Frame(row, bg="#F8FAFC")
            col.pack(side="left", fill="x", expand=True, pady=3)
            tk.Label(col, text=e.get("title", ""), bg="#F8FAFC", fg=INK,
                     font=("Segoe UI", 8, "bold")).pack(anchor="w")
            tk.Label(col, text=e.get("desc", ""), bg="#F8FAFC", fg=MUTED,
                     font=("Segoe UI", 7)).pack(anchor="w")

    # ------------------------------ statistics --------------------------------
    def _refresh_stats_async(self):
        threading.Thread(target=self._compute_stats, daemon=True).start()

    def _compute_stats(self):
        try:
            students = self.db.col("students").count_documents()
            teachers = self.db.col("teachers").count_documents()
            fees = sum(float(f.get("amount", 0) or 0) for f in self.db.col("fees").find(limit=1000))
            att = self.db.col("attendance").find(limit=500)
            rate = round(sum(1 for a in att if a.get("status") == "Present") / len(att) * 100) if att else 0
            if self.alive:
                self.root.after(0, lambda: self._apply_stats(students, teachers, rate, fees))
        except Exception:
            traceback.print_exc()

    def _apply_stats(self, students, teachers, rate, fees):
        v = self.stat_values
        if "students" in v:
            v["students"].config(text=str(students))
        if "teachers" in v:
            v["teachers"].config(text=str(teachers))
        if "attendance" in v:
            v["attendance"].config(text=f"{rate}%")
        if "fees" in v:
            v["fees"].config(text=f"₹{fees:,.0f}")
        if "classes" in v:
            v["classes"].config(text=str(self.db.col("courses").count_documents()))
        if "results" in v:
            v["results"].config(text=str(self.db.col("examinations").count_documents()))
        if "exams" in v:
            v["exams"].config(text=str(self.db.col("examinations").count_documents()))
        if "subjects" in v:
            v["subjects"].config(text=str(self.db.col("courses").count_documents()))

    def _refresh_all(self):
        self._refresh_stats_async()
        if self.active == "dashboard":
            self._draw_charts()
            self._load_recent_students()
            self._load_activities()
            self._load_events()
        loader = getattr(self, f"_load_{self.active}", None)
        if loader:
            loader()

    # -------------------------------- search ----------------------------------
    def _global_search(self):
        term = self.search.get().strip().lower()
        if not term:
            return
        results = []
        for coll, label in (("students", "Student"), ("teachers", "Teacher"),
                            ("courses", "Course"), ("examinations", "Exam"),
                            ("results", "Result"), ("fees", "Fee"), ("admissions", "Admission")):
            for d in self.db.col(coll).find(limit=200):
                blob = " ".join(str(x).lower() for x in d.values())
                if term in blob:
                    results.append((label, d))
        self.show_page("search")
        page = self.pages["search"].inner
        for w in page.winfo_children():
            w.destroy()
        self._header(page, f"Search results for “{term}”", f"{len(results)} match(es)")
        if not results:
            tk.Label(page, text="Nothing found.", bg=BG, fg=MUTED).pack(padx=26, pady=20)
            return
        for label, d in results[:80]:
            card = Card(page, height=64)
            card.pack(fill="x", padx=26, pady=4)
            tk.Label(card.body, text=label, bg="#DBEAFE", fg=ROYAL,
                     font=("Segoe UI", 8, "bold"), padx=8).pack(side="left")
            summary = "  ".join(f"{k}: {v}" for k, v in d.items()
                                if k not in ("_id", "password") and v)[:120]
            tk.Label(card.body, text=summary, bg=CARD, fg=INK, anchor="w",
                     font=("Segoe UI", 9)).pack(side="left", padx=10, fill="x", expand=True)
            tk.Button(card.body, text="Open", bg=ROYAL, fg="white", bd=0, cursor="hand2",
                      command=lambda dd=d: self._record_dialog(dd)).pack(side="right", padx=6)

    def _filter_tree(self, tree, term):
        term = term.strip().lower()
        for iid in tree.get_children():
            vals = " ".join(str(v).lower() for v in tree.item(iid, "values"))
            if not term or term in vals:
                tree.reattach(iid, "", "end")
            else:
                tree.detach(iid)

    def _notifications(self):
        win = tk.Toplevel(self.root)
        win.title("Notifications")
        win.geometry("340x400")
        win.configure(bg=CARD)
        tk.Label(win, text="Notifications", bg=CARD, fg=INK,
                 font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=16, pady=14)
        items = self.db.col("activities").find(limit=12) or [
            {"text": "Welcome", "icon": "👋"},
            {"text": "DB " + ("online" if self.db.online else "offline"), "icon": "🗄"}]
        for a in items:
            row = tk.Frame(win, bg=CARD)
            row.pack(fill="x", padx=16, pady=4)
            tk.Label(row, text=a.get("icon", "•"), bg=CARD, fg=ROYAL).pack(side="left")
            tk.Label(row, text=a.get("text", ""), bg=CARD, fg=INK, anchor="w",
                     wraplength=270, justify="left").pack(side="left", padx=6, fill="x", expand=True)

    def _tick_clock(self):
        if not self.alive:
            return
        now = datetime.datetime.now()
        self.clock.configure(text=now.strftime("%I:%M:%S %p"))
        self.date_lbl.configure(text=now.strftime("%a, %d %b %Y"))
        self.root.after(1000, self._tick_clock)

    # --------------------------- avatar / image viewer ------------------------
    def _load_user_avatar(self):
        if not PIL_OK:
            return
        try:
            rec = self.db.col("users").find_one({"email": self.user.get("email")}) if self.user.get("email") else None
            b64 = (rec or {}).get("avatar_b64") or self.user.get("avatar_b64")
            if b64:
                img = Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")
                img.thumbnail((128, 128))
                self.user_pil = img
                self.user_photo = ImageTk.PhotoImage(img)
                self.top_avatar.delete("all")
                self.top_avatar.create_image(17, 17, image=self.user_photo)
        except Exception:
            pass

    def _view_user_image(self):
        if self.user_pil:
            self._view_image(self.user_pil, self.user.get("name", "Profile"))

    def _view_image(self, pil_image, title="Image"):
        win = tk.Toplevel(self.root)
        win.title(title)
        win.configure(bg="#0B1120")
        big = pil_image.copy()
        big.thumbnail((760, 760))
        photo = ImageTk.PhotoImage(big)
        lbl = tk.Label(win, image=photo, bg="#0B1120")
        lbl.image = photo
        lbl.pack(padx=12, pady=12)
        tk.Button(win, text="Close", command=win.destroy, bg=DANGER, fg="white",
                  bd=0, cursor="hand2", padx=16, pady=6).pack(pady=(0, 12))

    # ------------------------------ generic dialogs ---------------------------
    def _dialog_form(self, title, fields, on_save, prefill=None):
        win = tk.Toplevel(self.root)
        win.title(title)
        win.geometry("420x560")
        win.configure(bg=CARD)
        win.transient(self.root)
        area = ScrollArea(win)
        area.pack(fill="both", expand=True)
        tk.Label(area.inner, text=title, bg=CARD, fg=INK,
                 font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=18, pady=14)
        entries = {}
        for key, label in fields:
            tk.Label(area.inner, text=label, bg=CARD, fg=MUTED,
                     font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=18)
            e = tk.Entry(area.inner, bg=BG, fg=INK, relief="flat", highlightthickness=1,
                         highlightbackground=BORDER, font=("Segoe UI", 10))
            e.pack(fill="x", padx=18, pady=(2, 8), ipady=6)
            if prefill and prefill.get(key) is not None:
                e.insert(0, str(prefill.get(key)))
            entries[key] = e

        def save():
            data = {k: v.get().strip() for k, v in entries.items()}
            try:
                on_save(data)
                win.destroy()
            except Exception as exc:
                messagebox.showerror("Error", str(exc), parent=win)

        tk.Button(area.inner, text="Save", bg=ROYAL, fg="white", bd=0, cursor="hand2",
                  font=("Segoe UI", 10, "bold"), command=save).pack(fill="x", padx=18, pady=12, ipady=8)
        return win

    def _record_dialog(self, doc):
        win = tk.Toplevel(self.root)
        win.title("Record")
        win.geometry("440x480")
        win.configure(bg=CARD)
        area = ScrollArea(win)
        area.pack(fill="both", expand=True)
        tk.Label(area.inner, text="Record Details", bg=CARD, fg=INK,
                 font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=18, pady=14)
        for k, v in doc.items():
            if k == "password":
                continue
            row = tk.Frame(area.inner, bg=CARD)
            row.pack(fill="x", padx=18, pady=3)
            tk.Label(row, text=str(k), bg=CARD, fg=MUTED, width=14, anchor="w",
                     font=("Segoe UI", 8, "bold")).pack(side="left")
            tk.Label(row, text=str(v), bg=CARD, fg=INK, anchor="w", wraplength=250,
                     justify="left").pack(side="left")

    # ------------------------------- students page ----------------------------
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

        sf = tk.Frame(bar, bg=BG, highlightthickness=1, highlightbackground=BORDER)
        sf.pack(side="right")
        tk.Label(sf, text="🔍", bg=BG, fg=MUTED).pack(side="left", padx=(6, 0))
        sbox = tk.Entry(sf, bg=BG, fg=INK, bd=0, relief="flat", width=24)
        sbox.pack(side="left", padx=4, pady=5)

        card = Card(parent, height=440)
        card.pack(fill="x", padx=26, pady=12)
        cols = ("ID", "Name", "Roll", "Class", "Gender", "Contact", "Admission", "Status")
        self.students_tree = self._table(card.body, cols, height=14)
        self.students_tree.pack(fill="both", expand=True)
        self.students_tree.bind("<Double-1>", self._open_selected_student)
        sbox.bind("<KeyRelease>", lambda _e: self._filter_tree(self.students_tree, sbox.get()))
        self._load_students()

    def _load_students(self):
        t = getattr(self, "students_tree", None)
        if not t:
            return
        t.delete(*t.get_children())
        docs = self.db.col("students").find()
        if not docs:
            t.insert("", "end", values=("—", "No students found. Click Add Student.", "", "", "", "", "", ""))
            return
        for d in docs:
            iid = str(d.get("_id"))
            self.student_rows[iid] = d
            t.insert("", "end", iid=iid, values=(
                str(d.get("_id", ""))[:8], d.get("name", ""), d.get("roll", ""),
                d.get("grade", ""), d.get("gender", ""), d.get("contact", ""),
                d.get("admission", ""), d.get("status", "Active")))

    def _open_selected_student(self, _e=None):
        sel = self.students_tree.selection() if hasattr(self, "students_tree") else ()
        if not sel:
            return
        doc = self.student_rows.get(sel[0])
        if doc:
            self._record_dialog(doc)

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
        self._log_activity(f"New student: {data['name']}", "🎓")
        self._load_students()
        self._refresh_stats_async()

    def _edit_student(self):
        sel = self.students_tree.selection()
        if not sel:
            return messagebox.showinfo("Edit", "Select a student first.")
        doc = self.student_rows.get(sel[0])
        if not doc:
            return
        fields = [("name", "Full Name"), ("roll", "Roll Number"), ("grade", "Class"),
                  ("gender", "Gender"), ("contact", "Contact"), ("admission", "Admission Date")]
        self._dialog_form("Edit Student", fields,
                          lambda d: self._update_student(doc, d), prefill=doc)

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
        self._export_generic("students")

    def _export_generic(self, collection):
        docs = self.db.col(collection).find()
        if not docs:
            return messagebox.showinfo("Export", "Nothing to export.")
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
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

    def _log_activity(self, text, icon="•"):
        try:
            self.db.col("activities").insert_one(
                {"text": text, "icon": icon, "at": datetime.datetime.now().isoformat()})
            self._load_activities()
        except Exception:
            pass

    # --------------------------- simple form+list pages -----------------------
    def _simple_page(self, parent, title, subtitle, add_label, fields, collection, cols):
        self._header(parent, title, subtitle)
        bar = tk.Frame(parent, bg=BG)
        bar.pack(fill="x", padx=26)

        def add():
            self._dialog_form(add_label, fields,
                              lambda d: self._simple_save(collection, d, tree, cols))
        tk.Button(bar, text="＋ " + add_label, command=add, bg=ROYAL, fg="white", bd=0,
                  cursor="hand2", font=("Segoe UI", 9, "bold"), padx=12, pady=7).pack(side="left")
        tk.Button(bar, text="⟳ Refresh", bg=MUTED, fg="white", bd=0, cursor="hand2",
                  font=("Segoe UI", 9, "bold"), padx=12, pady=7,
                  command=lambda: self._simple_load(tree, collection, cols)).pack(side="left", padx=8)

        sf = tk.Frame(bar, bg=BG, highlightthickness=1, highlightbackground=BORDER)
        sf.pack(side="right")
        tk.Label(sf, text="🔍", bg=BG, fg=MUTED).pack(side="left", padx=(6, 0))
        sbox = tk.Entry(sf, bg=BG, fg=INK, bd=0, relief="flat", width=24)
        sbox.pack(side="left", padx=4, pady=5)

        card = Card(parent, height=440)
        card.pack(fill="x", padx=26, pady=12)
        tree = self._table(card.body, cols, height=14)
        tree.pack(fill="both", expand=True)
        sbox.bind("<KeyRelease>", lambda _e: self._filter_tree(tree, sbox.get()))
        self._simple_load(tree, collection, cols)
        return tree

    def _simple_load(self, tree, collection, cols):
        tree.delete(*tree.get_children())
        docs = self.db.col(collection).find()
        if not docs:
            tree.insert("", "end", values=tuple(["—", "No records yet"] + [""] * (len(cols) - 2)))
            return
        for d in docs:
            tree.insert("", "end", values=tuple(str(d.get(c.lower(), ""))[:40] for c in cols))

    def _simple_save(self, collection, data, tree, cols):
        data["created"] = datetime.date.today().isoformat()
        self.db.col(collection).insert_one(data)
        self._simple_load(tree, collection, cols)
        self._log_activity(f"{collection.title()} record added", "＋")

    def _page_admissions(self, parent):
        self._simple_page(parent, "Admissions", "New admissions and records.", "New Admission",
                          [("name", "Student Name"), ("course", "Course"), ("status", "Status")],
                          "admissions", ("NAME", "COURSE", "STATUS"))

    def _page_courses(self, parent):
        self._simple_page(parent, "Courses & Classes", "Manage courses and classes.", "Add Course",
                          [("name", "Course Name"), ("code", "Code"), ("dept", "Department")],
                          "courses", ("NAME", "CODE", "DEPT"))

    def _page_attendance(self, parent):
        self._simple_page(parent, "Attendance", "Mark and review attendance.", "Mark Attendance",
                          [("name", "Student"), ("status", "Status"), ("date", "Date")],
                          "attendance", ("NAME", "STATUS", "DATE"))

    def _page_fees(self, parent):
        self._simple_page(parent, "Fees & Payments", "Collect fees and history.", "Collect Fee",
                          [("name", "Student"), ("amount", "Amount"), ("mode", "Mode")],
                          "fees", ("NAME", "AMOUNT", "MODE"))

    def _page_examinations(self, parent):
        self._simple_page(parent, "Examinations", "Create and schedule exams.", "Create Exam",
                          [("name", "Exam Name"), ("date", "Date"), ("subject", "Subject")],
                          "examinations", ("NAME", "DATE", "SUBJECT"))

    def _page_results(self, parent):
        self._simple_page(parent, "Results & Grades", "Add and view results.", "Add Result",
                          [("name", "Student"), ("subject", "Subject"), ("marks", "Marks")],
                          "results", ("NAME", "SUBJECT", "MARKS"))

    def _page_teachers(self, parent):
        self._simple_page(parent, "Teachers & Staff", "Manage staff records.", "Add Teacher",
                          [("name", "Name"), ("department", "Department"), ("subject", "Subject")],
                          "teachers", ("NAME", "DEPARTMENT", "SUBJECT"))

    def _page_timetable(self, parent):
        self._simple_page(parent, "Timetable", "Create and view schedules.", "Add Period",
                          [("grade", "Class"), ("subject", "Subject"), ("period", "Period")],
                          "timetable", ("GRADE", "SUBJECT", "PERIOD"))

    def _page_reports(self, parent):
        self._header(parent, "Reports", "Export and analyse campus data.")
        card = Card(parent, height=380)
        card.pack(fill="x", padx=26, pady=12)
        tk.Label(card.body, text="Generate Reports", bg=CARD, fg=INK,
                 font=("Segoe UI", 13, "bold")).pack(anchor="w")
        for label, coll in (("Export Students (CSV)", "students"),
                            ("Export Teachers (CSV)", "teachers"),
                            ("Export Fees (CSV)", "fees"),
                            ("Export Attendance (CSV)", "attendance")):
            tk.Button(card.body, text=label, command=lambda c=coll: self._export_generic(c),
                      bg=BG, fg=INK, bd=0, anchor="w", cursor="hand2",
                      font=("Segoe UI", 10), padx=14, pady=9).pack(fill="x", pady=4)

    # ------------------------------- settings page ----------------------------
    def _page_settings(self, parent):
        self._header(parent, "Settings", "Profile, security and system status.")

        prof = Card(parent, height=210)
        prof.pack(fill="x", padx=26, pady=8)
        row = tk.Frame(prof.body, bg=CARD)
        row.pack(anchor="w")
        self.settings_avatar = Avatar(row, self.user.get("name"), photo=self.user_photo, size=84,
                                      on_click=self._view_user_image)
        self.settings_avatar.pack(side="left")
        col = tk.Frame(row, bg=CARD)
        col.pack(side="left", padx=16)
        tk.Label(col, text=self.user.get("name", "Admin"), bg=CARD, fg=INK,
                 font=("Segoe UI", 15, "bold")).pack(anchor="w")
        tk.Label(col, text=self.role.title(), bg=CARD, fg=MUTED,
                 font=("Segoe UI", 9)).pack(anchor="w")
        tk.Button(col, text="📷 Upload Photo", command=self._upload_photo, bg=ROYAL,
                  fg="white", bd=0, cursor="hand2", font=("Segoe UI", 9, "bold"),
                  padx=12, pady=6).pack(anchor="w", pady=8)

        pw = Card(parent, height=260)
        pw.pack(fill="x", padx=26, pady=8)
        tk.Label(pw.body, text="Change Password", bg=CARD, fg=INK,
                 font=("Segoe UI", 13, "bold")).pack(anchor="w")
        self.pw_old = self._pw_field(pw.body, "Current password")
        self.pw_new = self._pw_field(pw.body, "New password (min 8, letter+digit)")
        self.pw_conf = self._pw_field(pw.body, "Confirm new password")
        tk.Button(pw.body, text="Update Password", command=self._change_password, bg=SUCCESS,
                  fg="white", bd=0, cursor="hand2", font=("Segoe UI", 10, "bold"),
                  padx=14, pady=8).pack(anchor="w", pady=8)

        info = Card(parent, height=230)
        info.pack(fill="x", padx=26, pady=8)
        tk.Label(info.body, text="System Status", bg=CARD, fg=INK,
                 font=("Segoe UI", 13, "bold")).pack(anchor="w")
        for k, v in (("Database", "Connected" if self.db.online else "Offline (memory)"),
                     ("Matplotlib", "Available" if MPL_OK else "Missing"),
                     ("Pandas", "Available" if PD_OK else "Missing")):
            r = tk.Frame(info.body, bg=CARD)
            r.pack(fill="x", pady=3)
            tk.Label(r, text=k, bg=CARD, fg=MUTED, width=14, anchor="w",
                     font=("Segoe UI", 9, "bold")).pack(side="left")
            tk.Label(r, text=v, bg=CARD, fg=INK, font=("Segoe UI", 9)).pack(side="left")

    def _pw_field(self, parent, label):
        tk.Label(parent, text=label, bg=CARD, fg=MUTED,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(6, 1))
        e = tk.Entry(parent, bg=BG, fg=INK, relief="flat", highlightthickness=1,
                     highlightbackground=BORDER, show="●", font=("Segoe UI", 10))
        e.pack(fill="x", ipady=6)
        return e

    def _upload_photo(self):
        if not PIL_OK:
            return messagebox.showinfo("Photo", "Pillow not installed.")
        path = filedialog.askopenfilename(filetypes=[("Images", "*.jpg *.jpeg *.png")])
        if not path:
            return
        try:
            img = Image.open(path).convert("RGB")
            thumb = img.copy()
            thumb.thumbnail((128, 128))
            b64 = base64.b64encode(open(path, "rb").read()).decode()
            self.user_pil = thumb
            self.user_photo = ImageTk.PhotoImage(thumb)
            for av, size in ((self.top_avatar, 34), (getattr(self, "settings_avatar", None), 84)):
                if av:
                    av.delete("all")
                    small = thumb.copy()
                    small.thumbnail((size, size))
                    p = ImageTk.PhotoImage(small)
                    av.create_image(size / 2, size / 2, image=p)
                    av.image = p
            email = self.user.get("email")
            if email:
                if self.db.col("users").find_one({"email": email}):
                    self.db.col("users").update_one({"email": email}, {"$set": {"avatar_b64": b64}})
                else:
                    self.db.col("users").insert_one({"email": email, "avatar_b64": b64,
                                                     "name": self.user.get("name")})
            self.user["avatar_b64"] = b64
            messagebox.showinfo("Photo", "Profile photo updated.")
        except Exception as exc:
            messagebox.showerror("Upload failed", str(exc))

    def _change_password(self):
        old = self.pw_old.get()
        new = self.pw_new.get()
        conf = self.pw_conf.get()
        if len(new) < 8 or not any(c.isalpha() for c in new) or not any(c.isdigit() for c in new):
            return messagebox.showwarning("Password", "Min 8 chars, at least one letter and one digit.")
        if new != conf:
            return messagebox.showwarning("Password", "Passwords do not match.")
        email = self.user.get("email")
        rec = None
        if email:
            try:
                rec = self.db.col("users").find_one({"email": email})
            except Exception:
                rec = None
        stored = (rec or {}).get("password") or self.user.get("password")
        if stored and not verify_password(old, stored):
            return messagebox.showerror("Password", "Current password is incorrect.")
        try:
            if email and rec:
                self.db.col("users").update_one({"email": email}, {"$set": {"password": hash_password(new)}})
            else:
                self.user["password"] = hash_password(new)
            self.pw_old.delete(0, "end")
            self.pw_new.delete(0, "end")
            self.pw_conf.delete(0, "end")
            messagebox.showinfo("Password", "Password updated successfully.")
        except Exception as exc:
            messagebox.showerror("Password", str(exc))

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
                self.root.unbind_all(seq)
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