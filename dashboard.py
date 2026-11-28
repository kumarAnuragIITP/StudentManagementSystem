import os
import io
import csv
import base64
import random
import hashlib
import math
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
    import numpy as np
    NP_OK = True
except Exception:
    NP_OK = False

try:
    from sklearn.linear_model import LinearRegression
    SK_OK = True
except Exception:
    SK_OK = False

try:
    import torch  # noqa: F401
    TORCH_OK = True
except Exception:
    TORCH_OK = False

try:
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.pagesizes import A4
    RL_OK = True
except Exception:
    RL_OK = False

try:
    from pymongo import MongoClient
    from bson import ObjectId
    MONGO_OK = True
except Exception:
    MongoClient = None
    ObjectId = None
    MONGO_OK = False


# ----------------------------------- theme ------------------------------------
NAVY = "#172554"; NAVY_HOVER = "#1E3A6E"; ROYAL = "#2563EB"; BG = "#F1F5F9"
CARD = "#FFFFFF"; INK = "#0F172A"; MUTED = "#64748B"; BORDER = "#E2E8F0"
SUCCESS = "#16A34A"; WARN = "#F59E0B"; DANGER = "#DC2626"
CHART_COLORS = ["#2563EB", "#16A34A", "#F59E0B", "#DC2626", "#7C3AED", "#0891B2"]

SIDEBAR_W = 240
LOGO_PATH = "C:\\Users\\kanur\\PycharmProjects\\VWSP\\PythonProject\\images\\gpc.png"

COLLEGE = "GOVERNMENT POLYTECHNIC CHAPRA"

NAV_ITEMS = [
    ("dashboard", "Dashboard", "▦"), ("students", "Students", "🎓"),
    ("admissions", "Admissions", "📝"), ("courses", "Courses & Branches", "📚"),
    ("attendance", "Attendance", "✅"), ("fees", "Fees & Payments", "💳"),
    ("examinations", "Examinations", "📄"), ("results", "Results & Grades", "🏅"),
    ("teachers", "Teachers & Staff", "🧑‍🏫"), ("timetable", "Timetable", "🗓"),
    ("reports", "Reports & AI", "📊"), ("settings", "Settings", "⚙"),
]
ROLE_NAV = {
    "principal": [k for k, _, _ in NAV_ITEMS],
    "teacher": ["dashboard", "students", "courses", "attendance", "examinations",
                "results", "timetable", "reports", "settings"],
    "student": ["dashboard", "courses", "attendance", "fees", "results",
                "timetable", "settings"],
}
DEFAULT_COURSES = ["Diploma", "Coaching", "Other Skill Course"]
DEFAULT_BRANCHES = ["Computer Science", "Mechanical", "Civil", "Electrical",
                    "Electronics", "Metallurgy", "Automobile"]

MONGO_URI = os.environ.get("SMS_MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.environ.get("SMS_DB", "student_management")


# --------------------------------- helpers ------------------------------------
def hash_password(p, salt=None):
    salt = salt or secrets.token_hex(16)
    d = hashlib.pbkdf2_hmac("sha256", p.encode(), salt.encode(), 180_000)
    return {"salt": salt, "hash": d.hex()}


def verify_password(p, rec):
    try:
        return bool(rec and rec.get("salt") and secrets.compare_digest(
            hash_password(p, rec["salt"])["hash"], rec["hash"]))
    except Exception:
        return False


def today():
    return datetime.date.today().isoformat()


def safe_float(value, default=0.0):
    try:
        number = float(value)
        return number if math.isfinite(number) else default
    except (TypeError, ValueError, OverflowError):
        return default


def _simple_pdf(path, lines):
    """Minimal valid PDF writer used when reportlab is absent."""
    content = ["BT", "/F1 11 Tf", "50 800 Td", "15 TL"]
    for ln in lines:
        esc = str(ln).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        content.append(f"({esc}) Tj T*")
    content.append("ET")
    stream = "\n".join(content).encode("latin-1", "replace")
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offs = []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        out += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs)+1}\n".encode() + b"0000000000 65535 f \n"
    for off in offs:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    with open(path, "wb") as fh:
        fh.write(bytes(out))


def make_pdf(path, title, lines, sign=True):
    """Create a PDF; uses reportlab with logo when available."""
    if RL_OK:
        try:
            c = rl_canvas.Canvas(path, pagesize=A4)
            w, h = A4
            c.setFont("Helvetica-Bold", 15)
            c.drawCentredString(w / 2, h - 50, COLLEGE)
            c.setFont("Helvetica", 10)
            c.drawCentredString(w / 2, h - 68, "Student Management System")
            if LOGO_PATH and not LOGO_PATH.lower().startswith("http") and os.path.isfile(LOGO_PATH):
                try:
                    c.drawImage(LOGO_PATH, 40, h - 80, 46, 46, mask="auto")
                except Exception:
                    pass
            c.setFont("Helvetica-Bold", 13)
            c.drawString(50, h - 110, title)
            c.line(50, h - 116, w - 50, h - 116)
            c.setFont("Helvetica", 10)
            y = h - 140
            for ln in lines:
                c.drawString(50, y, str(ln)[:110])
                y -= 16
                if y < 120:
                    c.showPage(); y = h - 60
            if sign:
                c.line(w - 190, 90, w - 50, 90)
                c.drawString(w - 190, 76, "Principal (Signature)")
            c.save()
            return
        except Exception:
            pass
    _simple_pdf(path, [COLLEGE, "", title, ""] + lines +
                (["", "____________________", "Principal (Signature)"] if sign else []))


# -------------------------------- data layer ----------------------------------
class MemCol:
    def __init__(self):
        self.docs = []

    def _m(self, d, q):
        return all(d.get(k) == v for k, v in (q or {}).items())

    def find(self, query=None, limit=0):
        out = [d for d in self.docs if self._m(d, query)]
        return out[:limit] if limit else out

    def find_one(self, query):
        r = self.find(query, 1)
        return r[0] if r else None

    def insert_one(self, doc):
        doc = dict(doc)
        doc.setdefault("_id", f"mem-{len(self.docs)}-{random.randint(0, 99999)}")
        self.docs.append(doc)
        return doc

    def update_one(self, q, upd):
        for d in self.docs:
            if self._m(d, q):
                d.update(upd.get("$set", {}))
                return

    def delete_one(self, q):
        for i, d in enumerate(self.docs):
            if self._m(d, q):
                del self.docs[i]
                return

    def delete_many(self, q):
        before = len(self.docs)
        self.docs[:] = [d for d in self.docs if not self._m(d, q)]
        return before - len(self.docs)

    def count_documents(self, q=None):
        return len(self.find(q))


class CollectionAdapter:
    """Give MongoDB and the in-memory fallback the same predictable list API."""
    def __init__(self, collection):
        self.collection = collection

    def _query(self, query=None):
        query = dict(query or {})
        value = query.get("_id")
        if isinstance(value, str) and ObjectId is not None:
            try:
                query["_id"] = ObjectId(value)
            except Exception:
                pass
        return query

    def find(self, query=None, limit=0):
        converted = self._query(query)
        result = self.collection.find(converted)
        if isinstance(result, list):
            rows = result[:int(limit)] if limit else result
        else:
            if limit:
                result = result.limit(int(limit))
            rows = list(result)
        if not rows and query and converted != query and "_id" in query:
            result = self.collection.find(dict(query))
            if not isinstance(result, list) and limit:
                result = result.limit(int(limit))
            rows = result if isinstance(result, list) else list(result)
        return rows

    def find_one(self, query=None):
        converted = self._query(query)
        result = self.collection.find_one(converted)
        if result is None and query and converted != query and "_id" in query:
            result = self.collection.find_one(dict(query))
        return result

    def insert_one(self, document):
        return self.collection.insert_one(dict(document))

    def update_one(self, query, update):
        converted = self._query(query)
        result = self.collection.update_one(converted, update)
        if (getattr(result, "matched_count", 1) == 0 and query and
                converted != query and "_id" in query):
            result = self.collection.update_one(dict(query), update)
        return result

    def delete_one(self, query):
        converted = self._query(query)
        result = self.collection.delete_one(converted)
        if (getattr(result, "deleted_count", 1) == 0 and query and
                converted != query and "_id" in query):
            result = self.collection.delete_one(dict(query))
        return result

    def delete_many(self, query):
        converted = self._query(query)
        if hasattr(self.collection, "delete_many"):
            result = self.collection.delete_many(converted)
            if (getattr(result, "deleted_count", 1) == 0 and query and
                    converted != query and "_id" in query):
                result = self.collection.delete_many(dict(query))
            return result
        return self.delete_one(query)

    def count_documents(self, query=None):
        return self.collection.count_documents(self._query(query))


class DB:
    def __init__(self):
        self.online = False
        self.client = None
        self._mem = {}
        self._adapters = {}
        if MONGO_OK:
            try:
                self.client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2500)
                self.client.admin.command("ping")
                self.database = self.client[DB_NAME]
                self.archive_db = self.client[DB_NAME + "_archive"]
                self.online = True
            except Exception:
                self.online = False
                try:
                    if self.client:
                        self.client.close()
                except Exception:
                    pass
                self.client = None

    def col(self, name):
        if name not in self._adapters:
            raw = self.database[name] if self.online else self._mem.setdefault(name, MemCol())
            self._adapters[name] = CollectionAdapter(raw)
        return self._adapters[name]

    def archive_col(self, name):
        key = "archive:" + name
        if key not in self._adapters:
            raw = self.archive_db[name] if self.online else self._mem.setdefault(key, MemCol())
            self._adapters[key] = CollectionAdapter(raw)
        return self._adapters[key]

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

    def _redraw(self, _e=None):
        w, h = self.winfo_width(), self.winfo_height()
        if w < 4 or h < 4:
            return
        self.delete("all")
        self._win = self.create_window(self.pad, self.pad, window=self.body, anchor="nw")
        r = self.radius
        pts = [r, 0, w - r, 0, w, 0, w, r, w, h - r, w, h, w - r, h,
               r, h, 0, h, 0, h - r, 0, r, 0, 0]
        self.create_polygon(pts, smooth=True, splinesteps=24, fill=self.fill, outline=self.border)
        self.body.configure(width=max(1, w - 2 * self.pad), height=max(1, h - 2 * self.pad))
        self.tag_raise(self._win)


class ScrollArea(tk.Frame):
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

    def scroll(self, u):
        self.canvas.yview_scroll(int(u), "units")

    def reset(self):
        self.canvas.yview_moveto(0)


class Avatar(tk.Canvas):
    def __init__(self, master, name, photo=None, size=38, bg=ROYAL, on_click=None):
        super().__init__(master, width=size, height=size, bg=master.cget("bg"),
                         highlightthickness=0, cursor="hand2")
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
    tk.Label(card.body, text=icon, bg=CARD, fg=accent, font=("Segoe UI Emoji", 20)).pack(anchor="w")
    v = tk.Label(card.body, text="0", bg=CARD, fg=INK, font=("Segoe UI", 24, "bold"))
    v.pack(anchor="w", pady=(4, 0))
    tk.Label(card.body, text=label, bg=CARD, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w")
    tk.Frame(card.body, bg=accent, height=4).pack(fill="x", pady=(8, 0))
    return v


# ================================== DASHBOARD =================================
class Dashboard:
    def __init__(self, root, user, app):
        self.root = root
        self.user = user or {"name": "Admin", "category": "principal"}
        self.role = str(self.user.get("category", "principal")).lower()
        self.staff = self.role in ("principal", "teacher")
        self.app = app
        self.db = DB()
        self.active = "dashboard"
        self.nav_buttons = {}
        self.pages = {}
        self._acc = {}
        self.alive = True
        self.logo_photo = None
        self.user_photo = None
        self.user_pil = None
        self.row_maps = {}
        self.course_lists = {}
        self._closing = False

        if self.app is not None:
            try:
                self.app.withdraw()
            except Exception:
                pass

        self.root.title("Student Management System — Dashboard")
        self.root.geometry("1400x880")
        self.root.minsize(980, 640)
        self.root.configure(bg=BG)
        try:
            self.root.state("zoomed")
        except Exception:
            pass

        self._style()
        self._seed_lookups()
        self._build_shell()
        self._load_user_avatar()
        self.show_page("dashboard")
        self._tick_clock()
        self._refresh_stats_async()
        self._notify(f"{self.user.get('name')} logged in",
                     roles=("principal", "teacher"), email=self.user.get("email"))
        self.root.protocol("WM_DELETE_WINDOW", self._logout)

    # ------------------------------ bootstrap ---------------------------------
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

    def _seed_lookups(self):
        try:
            for coll, defaults in (("courses", DEFAULT_COURSES), ("branches", DEFAULT_BRANCHES)):
                existing = {str(d.get("name", "")).strip().casefold()
                            for d in self.db.col(coll).find()}
                for name in defaults:
                    if name.casefold() not in existing:
                        self.db.col(coll).insert_one({"name": name})
                        existing.add(name.casefold())
        except Exception:
            traceback.print_exc()

    def _values(self, coll):
        values, seen = [], set()
        for doc in self.db.col(coll).find():
            name = str(doc.get("name", "")).strip()
            key = name.casefold()
            if name and key not in seen:
                values.append(name)
                seen.add(key)
        return values

    def _make_username(self, email):
        local = str(email or "student").split("@", 1)[0].lower()
        base = "".join(ch for ch in local if ch.isalnum() or ch in "._-").strip("._-")
        base = base or "student"
        candidate = base
        while self._find_ci("users", "username", candidate):
            candidate = f"{base}{secrets.randbelow(90000) + 10000}"
        return candidate

    def _find_ci(self, collection, field, value):
        target = str(value or "").strip().casefold()
        if not target:
            return None
        return next((doc for doc in self.db.col(collection).find()
                     if str(doc.get(field, "")).strip().casefold() == target), None)

    def _student_record(self):
        email = str(self.user.get("email", "")).strip().casefold()
        if email:
            record = self._find_ci("students", "email", email)
            if record:
                return record
        user_id = self.user.get("_id")
        if user_id is not None:
            return self.db.col("students").find_one({"_id": str(user_id)})
        return None

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
        self.host = tk.Frame(right, bg=BG)
        self.host.grid(row=1, column=0, sticky="nsew")
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.root.bind_all(seq, self._on_wheel)

    def _area_at(self, e):
        try:
            w = self.root.winfo_containing(e.x_root, e.y_root)
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
            return None
        if getattr(event, "num", None) == 4:
            step = -1
        elif getattr(event, "num", None) == 5:
            step = 1
        else:
            d = getattr(event, "delta", 0)
            if not d:
                return "break"
            thr = 120 if abs(d) >= 120 else 20
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

        nav = tk.Frame(bar, bg=NAVY)
        nav.pack(fill="x")
        for key, label, icon in NAV_ITEMS:
            if key not in ROLE_NAV.get(self.role, ROLE_NAV["principal"]):
                continue
            btn = tk.Frame(nav, bg=NAVY, cursor="hand2")
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
                  fg="white", cursor="hand2", font=("Segoe UI", 10, "bold"),
                  pady=9).pack(fill="x")

    def _load_logo(self):
        if not PIL_OK or not LOGO_PATH:
            return

        def worker():
            try:
                if LOGO_PATH.lower().startswith("http"):
                    import urllib.request
                    req = urllib.request.Request(LOGO_PATH, headers={"User-Agent": "Mozilla/5.0"})
                    img = Image.open(io.BytesIO(urllib.request.urlopen(req, timeout=6).read()))
                else:
                    img = Image.open(LOGO_PATH)
                img = img.convert("RGBA")
                img.thumbnail((40, 40))
                if self.alive:
                    self.root.after(0, lambda image=img.copy(): self._apply_logo(image))
            except Exception:
                pass
        threading.Thread(target=worker, daemon=True).start()

    def _apply_logo(self, image):
        if not self.alive or not self.root.winfo_exists():
            return
        try:
            ph = ImageTk.PhotoImage(image)
            self.logo_lbl.configure(image=ph, text="")
            self.logo_photo = ph
        except tk.TclError:
            pass

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
        self.search = tk.Entry(sw, bg=BG, fg=INK, bd=0, relief="flat", width=18,
                               font=("Segoe UI", 10))
        self.search.pack(side="left", padx=6, pady=6)
        self.search.bind("<Return>", lambda _e: self._global_search())
        self.search_wrap = sw
        self.root.bind("<Configure>", self._resize_topbar, add="+")
        if not self.db.online:
            tk.Label(bar, text="OFFLINE • data is temporary", bg="#FEF3C7", fg="#92400E",
                     font=("Segoe UI", 8, "bold"), padx=8, pady=5).pack(side="right", padx=8)
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
        tk.Label(info, text=self.role.title(), bg=CARD, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w")
        mb = tk.Button(prof, text="▾", bg=CARD, bd=0, cursor="hand2", fg=MUTED,
                       command=lambda: self._profile_menu(mb))
        mb.pack(side="left", padx=4)

    def _resize_topbar(self, event=None):
        if event is not None and event.widget is not self.root:
            return
        if not hasattr(self, "search"):
            return
        width = max(0, self.root.winfo_width() - SIDEBAR_W)
        try:
            self.search.configure(width=12 if width < 900 else (18 if width < 1120 else 24))
            if width < 900:
                self.date_lbl.pack_forget()
            elif not self.date_lbl.winfo_manager():
                self.date_lbl.pack(side="right")
        except tk.TclError:
            pass

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
            builder = getattr(self, f"_page_{key}", None)
            if builder:
                try:
                    builder(page.inner)
                except Exception:
                    traceback.print_exc()
                    tk.Label(page.inner, text="Page failed to load.", bg=BG, fg=DANGER).pack(pady=20)
            self.pages[key] = page
        page.pack(fill="both", expand=True)
        page.reset()

    def _header(self, parent, title, subtitle=""):
        h = tk.Frame(parent, bg=BG)
        h.pack(fill="x", padx=26, pady=(22, 10))
        tk.Label(h, text=title, bg=BG, fg=INK, font=("Segoe UI", 22, "bold")).pack(anchor="w")
        if subtitle:
            tk.Label(h, text=subtitle, bg=BG, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w", pady=(3, 0))

    def _table(self, parent, columns, height=12, widths=None):
        wrap = tk.Frame(parent, bg=CARD)
        wrap.pack(fill="both", expand=True)
        wrap.rowconfigure(0, weight=1)
        wrap.columnconfigure(0, weight=1)
        tree = ttk.Treeview(wrap, columns=columns, show="headings", height=height)
        for i, column in enumerate(columns):
            tree.heading(column, text=column)
            tree.column(column, width=(widths[i] if widths and i < len(widths) else 110),
                        minwidth=55, anchor="w", stretch=True)
        vs = ttk.Scrollbar(wrap, orient="vertical", command=tree.yview)
        hs = ttk.Scrollbar(wrap, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)
        vs.pack(side="right", fill="y")
        hs.pack(side="bottom", fill="x")
        return tree

    def _search_bar(self, parent, tree):
        sf = tk.Frame(parent, bg=BG, highlightthickness=1, highlightbackground=BORDER)
        sf.pack(side="right")
        tk.Label(sf, text="🔍", bg=BG, fg=MUTED).pack(side="left", padx=(6, 0))
        box = tk.Entry(sf, bg=BG, fg=INK, bd=0, relief="flat", width=24)
        box.pack(side="left", padx=4, pady=5)
        box.bind("<KeyRelease>", lambda _e: self._filter_tree(tree, box.get()))
        return box

    def _clear_tree(self, tree):
        if tree is None:
            return
        all_iids = set(getattr(tree, "_filter_all_iids", []))
        all_iids.update(tree.get_children(""))
        for iid in all_iids:
            if tree.exists(iid):
                tree.delete(iid)
        tree._filter_all_iids = []

    def _filter_tree(self, tree, term):
        term = term.strip().casefold()
        all_iids = list(getattr(tree, "_filter_all_iids", []))
        for iid in tree.get_children(""):
            if iid not in all_iids:
                all_iids.append(iid)
        all_iids = [iid for iid in all_iids if tree.exists(iid)]
        tree._filter_all_iids = all_iids
        for iid in all_iids:
            values = " ".join(str(v).casefold() for v in tree.item(iid, "values"))
            if not term or term in values:
                tree.reattach(iid, "", "end")
            else:
                tree.detach(iid)

    def _combo(self, parent, values, width=30):
        cb = ttk.Combobox(parent, values=values, state="readonly", width=width)
        return cb

    def _labeled_combo(self, parent, label, values, row):
        tk.Label(parent, text=label, bg=CARD, fg=MUTED,
                 font=("Segoe UI", 8, "bold")).grid(row=row, column=0, sticky="w", pady=4)
        cb = self._combo(parent, values)
        cb.grid(row=row, column=1, sticky="ew", pady=4)
        return cb

    # ------------------------------ statistics --------------------------------
    def _refresh_stats_async(self):
        threading.Thread(target=self._compute_stats, daemon=True).start()

    def _compute_stats(self):
        try:
            students = self.db.col("students").count_documents()
            teachers = self.db.col("teachers").count_documents()
            fees = sum(safe_float(f.get("amount", 0)) for f in self.db.col("fees").find(limit=2000))
            att = self.db.col("attendance").find(limit=500)
            rate = round(sum(1 for a in att if a.get("status") == "Present") / len(att) * 100) if att else 0
            if self.alive:
                self.root.after(0, lambda: self._apply_stats(students, teachers, rate, fees))
        except Exception:
            traceback.print_exc()

    def _apply_stats(self, students, teachers, rate, fees):
        v = self.stat_values
        if "students" in v: v["students"].config(text=str(students))
        if "teachers" in v: v["teachers"].config(text=str(teachers))
        if self.role == "student":
            own = self._student_record() or {}
            sid = str(own.get("_id", ""))
            own_attendance = self.db.col("attendance").find({"student": sid}) if sid else []
            own_rate = round(
                sum(1 for item in own_attendance if item.get("status") == "Present") /
                len(own_attendance) * 100) if own_attendance else 0
            if "attendance" in v:
                v["attendance"].config(text=f"{own_rate}%")
            balance = max(0.0, safe_float(own.get("total_fee", 0)) -
                          safe_float(own.get("paid", 0)))
            if "balance" in v:
                v["balance"].config(text=f"₹{balance:,.0f}")
            scheduled = self.db.col("examinations").find(
                {"branch": own.get("branch"), "semester": str(own.get("semester", ""))})
            result_rows = self.db.col("results").find({"student": sid}) if sid else []
            if "exams" in v:
                v["exams"].config(text=str(len(result_rows)))
            if "results" in v:
                v["results"].config(text=str(len(scheduled)))
        else:
            if "attendance" in v:
                v["attendance"].config(text=f"{rate}%")
            if "fees" in v:
                v["fees"].config(text=f"₹{fees:,.0f}")
            if "balance" in v:
                v["balance"].config(text=f"₹{self._total_balance():,.0f}")
            if "classes" in v:
                v["classes"].config(text=str(self.db.col("courses").count_documents({})))
            if "results" in v:
                v["results"].config(text=str(self.db.col("examinations").count_documents({})))
            if "exams" in v:
                v["exams"].config(text=str(self.db.col("examinations").count_documents({})))

    def _total_balance(self):
        total = 0.0
        for s in self.db.col("students").find(limit=2000):
            total += max(0.0, safe_float(s.get("total_fee", 0)) - safe_float(s.get("paid", 0)))
        return total

    def _refresh_all(self):
        try:
            self._refresh_stats_async()
            if self.active == "dashboard":
                self._draw_charts()
                self._load_recent_students()
                self._load_activities()
            loader = getattr(self, f"_load_{self.active}", None)
            if loader:
                loader()
        except Exception as exc:
            traceback.print_exc()
            messagebox.showerror("Refresh failed", str(exc), parent=self.root)

    # ------------------------------ notifications -----------------------------
    def _notify(self, text, roles=("principal",), email=None):
        try:
            self.db.col("notifications").insert_one({
                "text": text, "roles": list(roles), "email": email,
                "at": datetime.datetime.now().isoformat()})
            if self.active == "dashboard":
                self._load_activities()
        except Exception:
            traceback.print_exc()

    def _visible_notifications(self):
        out = []
        for n in self.db.col("notifications").find(limit=60):
            roles = n.get("roles", [])
            if self.role == "principal" or self.role in roles or n.get("email") == self.user.get("email"):
                out.append(n)
        return list(reversed(out))

    def _notifications(self):
        win = tk.Toplevel(self.root)
        win.title("Notifications")
        win.geometry("380x460")
        win.configure(bg=CARD)
        tk.Label(win, text="Notifications", bg=CARD, fg=INK,
                 font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=16, pady=14)
        area = ScrollArea(win)
        area.pack(fill="both", expand=True)
        items = self._visible_notifications()
        if not items:
            tk.Label(area.inner, text="No notifications.", bg=CARD, fg=MUTED).pack(padx=16, pady=20)
        for n in items:
            row = tk.Frame(area.inner, bg=CARD)
            row.pack(fill="x", padx=16, pady=4)
            tk.Label(row, text="•", bg=CARD, fg=ROYAL).pack(side="left")
            col = tk.Frame(row, bg=CARD)
            col.pack(side="left", fill="x", expand=True)
            tk.Label(col, text=n.get("text", ""), bg=CARD, fg=INK, anchor="w",
                     wraplength=290, justify="left", font=("Segoe UI", 9)).pack(anchor="w")
            tk.Label(col, text=str(n.get("at", ""))[:19].replace("T", " "), bg=CARD,
                     fg=MUTED, font=("Segoe UI", 7)).pack(anchor="w")

    def _load_activities(self):
        b = getattr(self, "activities_box", None)
        if not b:
            return
        for w in b.winfo_children():
            w.destroy()
        items = self._visible_notifications()[:6] or [{"text": "No activity yet"}]
        for a in items:
            row = tk.Frame(b, bg=CARD)
            row.pack(fill="x", pady=2)
            tk.Label(row, text="•", bg=CARD, fg=ROYAL).pack(side="left", padx=(0, 6))
            tk.Label(row, text=a.get("text", ""), bg=CARD, fg=INK, anchor="w",
                     wraplength=210, justify="left", font=("Segoe UI", 8)).pack(side="left", fill="x", expand=True)

    def _tick_clock(self):
        if not self.alive:
            return
        now = datetime.datetime.now()
        self.clock.configure(text=now.strftime("%I:%M:%S %p"))
        self.date_lbl.configure(text=now.strftime("%a, %d %b %Y"))
        self.root.after(1000, self._tick_clock)

    # ------------------------------ dashboard page ----------------------------
    def _page_dashboard(self, parent):
        self._header(parent, f"Good Morning, {self.user.get('name','Admin')}! 👋",
                     "Welcome back to your Student Management System.")
        stats = tk.Frame(parent, bg=BG)
        stats.pack(fill="x", padx=26, pady=(4, 6))
        self.stat_values = {}
        if self.role == "student":
            self.stat_values["attendance"] = stat_card(stats, "✅", "My Attendance", SUCCESS)
            self.stat_values["balance"] = stat_card(stats, "₹", "Fee Balance", WARN)
            self.stat_values["exams"] = stat_card(stats, "📄", "Exams", ROYAL)
            self.stat_values["results"] = stat_card(stats, "🏅", "Exams Scheduled", "#7C3AED")
        elif self.role == "teacher":
            self.stat_values["students"] = stat_card(stats, "🎓", "Students", ROYAL)
            self.stat_values["classes"] = stat_card(stats, "📚", "Courses", "#7C3AED")
            self.stat_values["attendance"] = stat_card(stats, "✅", "Attendance Rate", SUCCESS)
            self.stat_values["balance"] = stat_card(stats, "₹", "Outstanding", WARN)
        else:
            self.stat_values["students"] = stat_card(stats, "🎓", "Total Students", ROYAL)
            self.stat_values["teachers"] = stat_card(stats, "🧑‍🏫", "Total Teachers", "#7C3AED")
            self.stat_values["attendance"] = stat_card(stats, "✅", "Attendance Rate", SUCCESS)
            self.stat_values["balance"] = stat_card(stats, "₹", "Outstanding Fees", WARN)

        charts = tk.Frame(parent, bg=BG)
        charts.pack(fill="x", padx=26, pady=10)
        charts.columnconfigure(0, weight=1); charts.columnconfigure(1, weight=1)
        self.chart_frames = {}
        for idx, (ck, title) in enumerate([("enroll", "Enrollment"), ("attend", "Attendance"),
                                           ("fees", "Fee Collection"), ("perf", "Performance")]):
            card = Card(charts, height=240)
            card.grid(row=idx // 2, column=idx % 2, sticky="nsew",
                      padx=(0 if idx % 2 == 0 else 12, 0), pady=6)
            tk.Label(card.body, text=title, bg=CARD, fg=INK,
                     font=("Segoe UI", 10, "bold")).pack(anchor="w")
            h = tk.Frame(card.body, bg=CARD)
            h.pack(fill="both", expand=True)
            self.chart_frames[ck] = h
        self._draw_charts()

        lower = tk.Frame(parent, bg=BG)
        lower.pack(fill="both", expand=True, padx=26, pady=12)
        lower.columnconfigure(0, weight=3); lower.columnconfigure(1, weight=2)
        tc = Card(lower, height=320)
        tc.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        tk.Label(tc.body, text="Recent Students", bg=CARD, fg=INK,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w")
        self.recent_tree = self._table(tc.body, ("Name", "Course", "Branch", "Sem", "Status"),
                                       height=8, widths=(160, 110, 120, 60, 80))
        self.recent_tree.pack(fill="both", expand=True, pady=6)
        side = tk.Frame(lower, bg=BG)
        side.grid(row=0, column=1, sticky="nsew")
        ac = Card(side, height=150)
        ac.grid(row=0, column=0, sticky="nsew", pady=(0, 12))
        tk.Label(ac.body, text="Recent Activity", bg=CARD, fg=INK,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w")
        self.activities_box = tk.Frame(ac.body, bg=CARD)
        self.activities_box.pack(fill="both", expand=True)
        ai = Card(side, height=150)
        ai.grid(row=1, column=0, sticky="nsew")
        tk.Label(ai.body, text="AI Insights", bg=CARD, fg=INK,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w")
        self.ai_box = tk.Frame(ai.body, bg=CARD)
        self.ai_box.pack(fill="both", expand=True)
        self._load_recent_students()
        self._load_activities()
        self._load_ai()

    def _draw_charts(self):
        if not hasattr(self, "chart_frames"):
            return
        holders = self.chart_frames
        for holder in holders.values():
            for widget in holder.winfo_children():
                widget.destroy()

        if self.role == "student":
            for holder in holders.values():
                tk.Label(holder, text="Institution analytics are not shown in student view.",
                         bg=CARD, fg=MUTED, wraplength=260).pack(expand=True)
            return

        if not MPL_OK:
            for holder in holders.values():
                tk.Label(holder, text="Install matplotlib to view charts.",
                         bg=CARD, fg=MUTED).pack(expand=True)
            return

        months = []
        today_date = datetime.date.today().replace(day=1)
        for offset in range(5, -1, -1):
            month_index = today_date.month - offset
            year = today_date.year + (month_index - 1) // 12
            month = (month_index - 1) % 12 + 1
            months.append(datetime.date(year, month, 1))
        labels = [d.strftime("%b") for d in months]
        keys = [d.strftime("%Y-%m") for d in months]

        def month_key(value):
            try:
                return datetime.date.fromisoformat(str(value)[:10]).strftime("%Y-%m")
            except (TypeError, ValueError):
                return None

        students_by_month = {key: 0 for key in keys}
        for student in self.db.col("students").find():
            key = month_key(student.get("admission") or student.get("created_at"))
            if key in students_by_month:
                students_by_month[key] += 1

        fees_by_month = {key: 0.0 for key in keys}
        for fee in self.db.col("fees").find():
            key = month_key(fee.get("date") or fee.get("created_at"))
            if key in fees_by_month:
                try:
                    fees_by_month[key] += float(fee.get("amount", 0) or 0)
                except (TypeError, ValueError):
                    continue

        attendance_counts = {"Present": 0, "Absent": 0, "Leave": 0}
        for record in self.db.col("attendance").find():
            status = str(record.get("status", "")).title()
            if status in attendance_counts:
                attendance_counts[status] += 1

        subject_marks = {}
        for result in self.db.col("results").find():
            subject = str(result.get("subject", "")).strip() or "Other"
            try:
                subject_marks.setdefault(subject, []).append(float(result.get("marks", 0)))
            except (TypeError, ValueError):
                continue
        performance = sorted(
            ((subject, sum(values) / len(values)) for subject, values in subject_marks.items()),
            key=lambda item: item[1], reverse=True)[:6]

        def show_empty(holder, message="No records available for this chart yet."):
            tk.Label(holder, text=message, bg=CARD, fg=MUTED,
                     wraplength=260, justify="center").pack(expand=True)

        def draw(holder, draw_fn):
            if not holder:
                return
            try:
                fig = Figure(figsize=(4.0, 2.15), dpi=90)
                ax = fig.add_subplot(111)
                draw_fn(ax)
                fig.tight_layout()
                canvas = FigureCanvasTkAgg(fig, master=holder)
                canvas.draw()
                canvas.get_tk_widget().pack(fill="both", expand=True)
                holder._figure_canvas = canvas
            except Exception:
                traceback.print_exc()
                show_empty(holder, "Chart could not be rendered.")

        holder = holders.get("enroll")
        if holder:
            if any(students_by_month.values()):
                draw(holder, lambda ax: (
                    ax.bar(labels, [students_by_month[k] for k in keys], color=ROYAL),
                    ax.set_ylabel("Students", fontsize=8),
                    ax.tick_params(labelsize=7)))
            else:
                show_empty(holder)

        holder = holders.get("fees")
        if holder:
            if any(fees_by_month.values()):
                draw(holder, lambda ax: (
                    ax.plot(labels, [fees_by_month[k] for k in keys],
                            color=SUCCESS, marker="o", linewidth=2),
                    ax.set_ylabel("₹ collected", fontsize=8),
                    ax.tick_params(labelsize=7)))
            else:
                show_empty(holder)

        holder = holders.get("attend")
        if holder:
            counts = [attendance_counts[k] for k in ("Present", "Absent", "Leave")]
            if sum(counts):
                draw(holder, lambda ax: (
                    ax.pie(counts, labels=["Present", "Absent", "Leave"],
                           autopct="%1.0f%%", textprops={"fontsize": 7},
                           colors=[SUCCESS, DANGER, WARN],
                           wedgeprops={"width": 0.42}),
                    ax.set_aspect("equal")))
            else:
                show_empty(holder)

        holder = holders.get("perf")
        if holder:
            if performance:
                draw(holder, lambda ax: (
                    ax.barh([x[0] for x in reversed(performance)],
                            [x[1] for x in reversed(performance)], color=CHART_COLORS[:len(performance)]),
                    ax.set_xlim(0, 100),
                    ax.set_xlabel("Average marks", fontsize=8),
                    ax.tick_params(labelsize=7)))
            else:
                show_empty(holder)

    def _load_recent_students(self):
        t = getattr(self, "recent_tree", None)
        if not t:
            return
        self._clear_tree(t)
        if self.role == "student":
            own = self._student_record()
            docs = [own] if own else []
        else:
            docs = self.db.col("students").find(limit=8)
        if not docs:
            t.insert("", "end", values=("No students yet", "", "", "", ""))
            return
        for d in docs:
            t.insert("", "end", values=(d.get("name", ""), d.get("course", ""),
                                        d.get("branch", ""), d.get("semester", ""),
                                        d.get("status", "Active")))

    def _load_ai(self):
        box = getattr(self, "ai_box", None)
        if not box:
            return
        for w in box.winfo_children():
            w.destroy()
        if self.role == "student":
            tk.Label(box, text="Performance insights are available through your faculty.",
                     bg=CARD, fg=MUTED, wraplength=210, justify="left",
                     font=("Segoe UI", 8)).pack(anchor="w")
            return
        rows = self._ai_risk()
        if not rows:
            tk.Label(box, text="Add data to generate insights.", bg=CARD, fg=MUTED,
                     wraplength=210, justify="left", font=("Segoe UI", 8)).pack(anchor="w")
            return
        for name, score in rows[:4]:
            tk.Label(box, text=f"{name}  —  risk {score:.0f}%", bg=CARD,
                     fg=DANGER if score > 60 else (WARN if score > 30 else SUCCESS),
                     anchor="w", font=("Segoe UI", 8)).pack(fill="x")

    def _ai_risk(self):
        """Risk = weighted attendance deficit + fee default (sklearn/numpy when present)."""
        rows = []
        for s in self.db.col("students").find(limit=500):
            sid = s.get("_id")
            recs = self.db.col("attendance").find({"student": str(sid)}, limit=400)
            if recs:
                present = sum(1 for a in recs if a.get("status") == "Present")
                att = present / len(recs) * 100
            else:
                att = 100.0
            total = safe_float(s.get("total_fee", 0))
            bal = max(0.0, total - safe_float(s.get("paid", 0)))
            fee_def = (bal / total * 100) if total else 0
            if NP_OK:
                score = float(np.clip(0.6 * (100 - att) + 0.4 * fee_def, 0, 100))
            else:
                score = 0.6 * (100 - att) + 0.4 * fee_def
            rows.append((s.get("name", "?"), score))
        rows.sort(key=lambda r: -r[1])
        return rows

    # ------------------------------ AI reports --------------------------------
    def _page_reports(self, parent):
        self._header(parent, "Reports & AI", "Automated analysis and exports.")
        if not self.staff:
            tk.Label(parent, text="This section is available to authorized staff only.",
                     bg=BG, fg=MUTED).pack(padx=26, pady=20)
            return
        card = Card(parent, height=340)
        card.pack(fill="x", padx=26, pady=8)
        tk.Label(card.body, text="At-Risk Students (AI)", bg=CARD, fg=INK,
                 font=("Segoe UI", 13, "bold")).pack(anchor="w")
        tk.Label(card.body, text="Based on attendance deficit and fee balance.",
                 bg=CARD, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w", pady=(0, 8))
        rows = self._ai_risk()[:8]
        if not rows:
            tk.Label(card.body, text="No data.", bg=CARD, fg=MUTED).pack(anchor="w")
        for name, score in rows:
            r = tk.Frame(card.body, bg=CARD)
            r.pack(fill="x", pady=2)
            tk.Label(r, text=name, bg=CARD, fg=INK, width=26, anchor="w").pack(side="left")
            bar = tk.Frame(r, bg="#E2E8F0", height=12, width=200)
            bar.pack(side="left", padx=8)
            fill = tk.Frame(bar, bg=DANGER if score > 60 else (WARN if score > 30 else SUCCESS),
                            height=12, width=max(4, int(score * 2)))
            fill.place(x=0, y=0)
            tk.Label(r, text=f"{score:.0f}%", bg=CARD, fg=MUTED).pack(side="left")
        card2 = Card(parent, height=260)
        card2.pack(fill="x", padx=26, pady=8)
        tk.Label(card2.body, text="Export", bg=CARD, fg=INK,
                 font=("Segoe UI", 13, "bold")).pack(anchor="w")
        for label, coll in (("Students", "students"), ("Teachers", "teachers"),
                            ("Fees", "fees"), ("Attendance", "attendance")):
            tk.Button(card2.body, text=f"Export {label} (CSV)", command=lambda c=coll: self._export(c),
                      bg=BG, fg=INK, bd=0, anchor="w", cursor="hand2",
                      font=("Segoe UI", 10), padx=14, pady=8).pack(fill="x", pady=3)

    def _export(self, coll):
        docs = self.db.col(coll).find()
        if not docs:
            return messagebox.showinfo("Export", "Nothing to export.")
        private_fields = {"password", "salt", "hash", "photo_b64", "avatar_b64"}
        docs = [{key: value for key, value in document.items()
                 if key not in private_fields} for document in docs]
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not path:
            return
        try:
            if PD_OK:
                pd.DataFrame(docs).to_csv(path, index=False)
            else:
                with open(path, "w", newline="", encoding="utf-8") as fh:
                    w = csv.DictWriter(fh, fieldnames=list(docs[0].keys()))
                    w.writeheader(); w.writerows(docs)
            messagebox.showinfo("Export", f"Saved to {path}")
        except Exception as exc:
            messagebox.showerror("Export failed", str(exc))

    # ------------------------------ global search -----------------------------
    def _global_search(self):
        term = self.search.get().strip().lower()
        if not term:
            return
        results = []
        collections = (("students", "Student"), ("teachers", "Teacher"), ("courses", "Course"),
                       ("examinations", "Exam"), ("results", "Result"), ("fees", "Fee"))
        own = self._student_record() if self.role == "student" else None
        for coll, label in collections:
            if self.role == "student" and coll in ("teachers", "fees"):
                continue
            docs = self.db.col(coll).find(limit=200)
            if self.role == "student":
                if coll == "students":
                    docs = [own] if own else []
                elif coll == "results":
                    docs = [d for d in docs if own and str(d.get("student")) == str(own.get("_id"))]
                elif coll == "examinations":
                    docs = [d for d in docs if own and d.get("branch") == own.get("branch")
                            and str(d.get("semester")) == str(own.get("semester"))]
            for d in docs:
                searchable = " ".join(
                    str(value).lower() for key, value in d.items()
                    if key not in ("password", "salt", "hash", "photo_b64", "avatar_b64"))
                if term in searchable:
                    results.append((label, d))
        self.show_page("search")
        page = self.pages["search"].inner
        for w in page.winfo_children():
            w.destroy()
        self._header(page, f"Results for “{term}”", f"{len(results)} match(es)")
        for label, d in results[:60]:
            c = Card(page, height=60)
            c.pack(fill="x", padx=26, pady=4)
            tk.Label(c.body, text=label, bg="#DBEAFE", fg=ROYAL, padx=8,
                     font=("Segoe UI", 8, "bold")).pack(side="left")
            summ = "  ".join(f"{k}: {v}" for k, v in d.items()
                             if k not in ("_id", "password", "salt", "hash", "photo_b64", "avatar_b64") and v)[:110]
            tk.Label(c.body, text=summ, bg=CARD, fg=INK, anchor="w",
                     font=("Segoe UI", 9)).pack(side="left", padx=10, fill="x", expand=True)

    # ------------------------------ image viewer ------------------------------
    def _load_user_avatar(self):
        if not PIL_OK:
            return
        try:
            rec = self._find_ci("users", "email", self.user.get("email")) if self.user.get("email") else None
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
        big = pil_image.copy(); big.thumbnail((760, 760))
        ph = ImageTk.PhotoImage(big)
        lbl = tk.Label(win, image=ph, bg="#0B1120"); lbl.image = ph
        lbl.pack(padx=12, pady=12)
        tk.Button(win, text="Close", command=win.destroy, bg=DANGER, fg="white",
                  bd=0, cursor="hand2", padx=16, pady=6).pack(pady=(0, 12))

    def _b64_image(self, b64, size=(64, 64)):
        try:
            img = Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")
            img.thumbnail(size)
            return img
        except Exception:
            return None

    # ------------------------------ student dialog ----------------------------
    STUDENT_FIELDS = [
        ("name", "Full Name"), ("email", "Email"), ("password", "Password"),
        ("idcard", "ID Card Number"), ("gender", "Gender (M/F/O)"), ("age", "Age"),
        ("dob", "Date of Birth"), ("father", "Father's Name"), ("mother", "Mother's Name"),
        ("mobile", "Mobile"), ("alt_mobile", "Alternate Mobile"), ("marital", "Marital Status"),
        ("basis", "Admission Basis (BCECE/Other)"), ("prev_qual", "Previous Qualification"),
        ("address", "Full Address"), ("pin", "PIN Code"), ("reputation", "Reputation / Remarks"),
        ("semester", "Semester"), ("admission", "Admission Date (YYYY-MM-DD)"),
        ("total_fee", "Total Course Fee (₹)"),
    ]

    def _student_dialog(self, title, prefill, on_save, collection="students"):
        win = tk.Toplevel(self.root)
        win.title(title)
        win.geometry("520x640")
        win.configure(bg=CARD)
        win.transient(self.root)
        area = ScrollArea(win)
        area.pack(fill="both", expand=True)
        tk.Label(area.inner, text=title, bg=CARD, fg=INK,
                 font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=18, pady=10)

        photo_holder = {"b64": (prefill or {}).get("photo_b64", "")}
        prow = tk.Frame(area.inner, bg=CARD)
        prow.pack(fill="x", padx=18, pady=6)
        plabel = tk.Label(prow, text="No photo", bg=BG, width=12, height=5,
                          fg=MUTED, relief="flat")
        plabel.pack(side="left")
        if photo_holder["b64"] and PIL_OK:
            img = self._b64_image(photo_holder["b64"], (90, 90))
            if img:
                ph = ImageTk.PhotoImage(img); plabel.configure(image=ph, text=""); plabel.image = ph

        def pick():
            if not PIL_OK:
                return
            p = filedialog.askopenfilename(filetypes=[("Images", "*.jpg *.jpeg *.png")])
            if not p:
                return
            try:
                img = Image.open(p).convert("RGB")
                t = img.copy(); t.thumbnail((90, 90))
                ph = ImageTk.PhotoImage(t)
                plabel.configure(image=ph, text=""); plabel.image = ph
                with open(p, "rb") as photo_file:
                    photo_holder["b64"] = base64.b64encode(photo_file.read()).decode()
            except Exception as exc:
                messagebox.showerror("Photo", str(exc))
        tk.Button(prow, text="📷 Upload Passport Photo", command=pick, bg=ROYAL, fg="white",
                  bd=0, cursor="hand2", padx=10, pady=6).pack(side="left", padx=12)

        grid = tk.Frame(area.inner, bg=CARD)
        grid.pack(fill="x", padx=18, pady=6)
        grid.columnconfigure(1, weight=1)
        entries = {}
        row = 0
        course_cb = self._labeled_combo(grid, "Course", self._values("courses"), row); row += 1
        branch_cb = self._labeled_combo(grid, "Branch", self._values("branches"), row); row += 1
        self.course_cb, self.branch_cb = course_cb, branch_cb
        for key, label in self.STUDENT_FIELDS:
            tk.Label(grid, text=label, bg=CARD, fg=MUTED,
                     font=("Segoe UI", 8, "bold")).grid(row=row, column=0, sticky="w", pady=3)
            e = tk.Entry(grid, bg=BG, fg=INK, relief="flat", highlightthickness=1,
                         highlightbackground=BORDER, font=("Segoe UI", 10),
                         show="●" if key == "password" else "")
            e.grid(row=row, column=1, sticky="ew", pady=3, ipady=5)
            if prefill and key != "password" and prefill.get(key) is not None:
                e.insert(0, str(prefill.get(key)))
            entries[key] = e
            row += 1
        if prefill:
            if prefill.get("course") in course_cb["values"]:
                course_cb.set(prefill.get("course"))
            if prefill.get("branch") in branch_cb["values"]:
                branch_cb.set(prefill.get("branch"))

        def save():
            data = {k: v.get().strip() for k, v in entries.items()}
            data["course"] = course_cb.get()
            data["branch"] = branch_cb.get()
            data["photo_b64"] = photo_holder["b64"]
            if not data.get("name"):
                return messagebox.showwarning("Required", "Full name is required.", parent=win)
            if not data.get("course") or not data.get("branch"):
                return messagebox.showwarning("Required", "Select course and branch.", parent=win)
            if data.get("email"):
                email = data["email"].strip()
                if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
                    return messagebox.showwarning("Email", "Enter a valid email address.", parent=win)
                data["email"] = email.casefold()
            if data.get("mobile") and not data["mobile"].replace("+", "").replace("-", "").replace(" ", "").isdigit():
                return messagebox.showwarning("Mobile", "Enter a valid mobile number.", parent=win)
            if data.get("age"):
                try:
                    if not 1 <= int(data["age"]) <= 120:
                        raise ValueError
                except ValueError:
                    return messagebox.showwarning("Age", "Enter a valid age between 1 and 120.", parent=win)
            if data.get("dob"):
                try:
                    datetime.date.fromisoformat(data["dob"])
                except ValueError:
                    return messagebox.showwarning("Date of birth", "Use YYYY-MM-DD.", parent=win)
            if data.get("admission"):
                try:
                    datetime.date.fromisoformat(data["admission"])
                except ValueError:
                    return messagebox.showwarning("Admission date", "Use YYYY-MM-DD.", parent=win)
            try:
                on_save(data)
                win.destroy()
            except Exception as exc:
                messagebox.showerror("Error", str(exc), parent=win)
        tk.Button(area.inner, text="Save", command=save, bg=SUCCESS, fg="white", bd=0,
                  cursor="hand2", font=("Segoe UI", 10, "bold")).pack(fill="x", padx=18, pady=12, ipady=8)
        return win

    # ------------------------------ students page -----------------------------
    def _page_students(self, parent):
        self._header(parent, "Students", "Complete student records.")
        bar = tk.Frame(parent, bg=BG)
        bar.pack(fill="x", padx=26)
        for label, cmd, color in (("＋ Add Student", lambda: self._add_student("students"), ROYAL),
                                  ("✎ Edit", self._edit_student, NAVY),
                                  ("🗑 Delete", self._delete_student, DANGER),
                                  ("⬇ Export", lambda: self._export("students"), SUCCESS),
                                  ("⟳ Refresh", self._load_students, MUTED)):
            tk.Button(bar, text=label, command=cmd, bg=color, fg="white", bd=0,
                      cursor="hand2", font=("Segoe UI", 9, "bold"),
                      padx=12, pady=7).pack(side="left", padx=(0, 8))
        card = Card(parent, height=440)
        card.pack(fill="x", padx=26, pady=12)
        cols = ("Photo", "Name", "Course", "Branch", "Sem", "Contact", "Fee Bal", "Status")
        self.students_tree = self._table(card.body, cols, height=14,
                                         widths=(60, 170, 100, 120, 50, 110, 90, 80))
        self.students_tree.pack(fill="both", expand=True)
        self.students_tree.bind("<Double-1>", lambda _e: self._open_student())
        self._search_bar(bar, self.students_tree)
        self._load_students()

    def _load_students(self):
        t = getattr(self, "students_tree", None)
        if not t:
            return
        self._clear_tree(t)
        self.row_maps["students"] = {}
        docs = self.db.col("students").find()
        if not docs:
            t.insert("", "end", values=("", "No students. Click Add Student.", "", "", "", "", "", ""))
            return
        for d in docs:
            iid = str(d.get("_id"))
            self.row_maps["students"][iid] = d
            bal = max(0.0, safe_float(d.get("total_fee", 0)) - float(d.get("paid", 0) or 0))
            t.insert("", "end", iid=iid, values=(
                "🖼" if d.get("photo_b64") else "—", d.get("name", ""), d.get("course", ""),
                d.get("branch", ""), d.get("semester", ""), d.get("mobile", ""),
                f"₹{bal:,.0f}", d.get("status", "Active")))

    def _open_student(self):
        sel = self.students_tree.selection()
        if not sel:
            return
        d = self.row_maps["students"].get(sel[0])
        if d:
            self._student_profile(d)

    def _student_profile(self, d):
        win = tk.Toplevel(self.root)
        win.title(d.get("name", "Student"))
        win.geometry("480x620")
        win.configure(bg=CARD)
        area = ScrollArea(win)
        area.pack(fill="both", expand=True)
        if d.get("photo_b64") and PIL_OK:
            img = self._b64_image(d["photo_b64"], (150, 150))
            if img:
                ph = ImageTk.PhotoImage(img)
                lbl = tk.Label(area.inner, image=ph, bg=CARD); lbl.image = ph
                lbl.pack(pady=10)
                lbl.bind("<Button-1>", lambda _e: self._view_image(img, d.get("name")))
        tk.Label(area.inner, text=d.get("name", ""), bg=CARD, fg=INK,
                 font=("Segoe UI", 16, "bold")).pack()
        for key, label in self.STUDENT_FIELDS + [("course", "Course"), ("branch", "Branch")]:
            if key == "password":
                continue
            r = tk.Frame(area.inner, bg=CARD)
            r.pack(fill="x", padx=18, pady=2)
            tk.Label(r, text=label, bg=CARD, fg=MUTED, width=22, anchor="w",
                     font=("Segoe UI", 8, "bold")).pack(side="left")
            tk.Label(r, text=str(d.get(key, "")), bg=CARD, fg=INK, anchor="w",
                     wraplength=250, justify="left").pack(side="left")

    def _add_student(self, collection="students"):
        self._student_dialog("Add Student", None,
                             lambda d: self._save_student(d, collection), collection)

    def _save_student(self, data, collection="students"):
        data.setdefault("admission", today())
        data.setdefault("status", "Active")
        data.setdefault("paid", 0)
        email = data.get("email", "").strip().casefold()
        idcard = data.get("idcard", "").strip()
        if email and self._find_ci(collection, "email", email):
            raise ValueError("This email is already present in this record list.")
        if idcard and self._find_ci(collection, "idcard", idcard):
            raise ValueError("This ID card number is already present.")
        if collection == "students":
            raw_password = data.pop("password", "").strip()
            existing_user = self._find_ci("users", "email", email) if email else None
            if existing_user and str(existing_user.get("category", "")).lower() not in ("", "student"):
                raise ValueError("This email is already linked to a non-student account.")
            if raw_password and len(raw_password) < 8:
                raise ValueError("Password must contain at least 8 characters.")
            if data.get("total_fee"):
                try:
                    total_fee = float(data["total_fee"])
                    if not math.isfinite(total_fee) or total_fee < 0:
                        raise ValueError
                    data["total_fee"] = total_fee
                except (TypeError, ValueError):
                    raise ValueError("Course fee must be a valid non-negative number.")
            data["email"] = email
            student_result = self.db.col("students").insert_one(data)
            student_id = (student_result.get("_id") if isinstance(student_result, dict)
                          else getattr(student_result, "inserted_id", data.get("_id")))
            if email and raw_password and not existing_user:
                try:
                    user_record = {
                        "name": data.get("name", ""),
                        "email": email,
                        "username": self._make_username(email),
                        "category": "student",
                        "password": hash_password(raw_password),
                        "mobile": data.get("mobile", ""),
                        "created_at": datetime.datetime.now().isoformat()
                    }
                    self.db.col("users").insert_one(user_record)
                except Exception:
                    if student_id is not None:
                        self.db.col("students").delete_one({"_id": student_id})
                    raise
        else:
            data.pop("password", None)
            self.db.col(collection).insert_one(data)
        self._notify(f"New {'student' if collection=='students' else 'admission'}: {data.get('name')}",
                     roles=("principal", "teacher"))
        if collection == "students" and email and not raw_password and not existing_user:
            messagebox.showinfo(
                "Student saved",
                "Student record saved. No portal login was created because no password was supplied.")
        if collection == "students":
            self._load_students()
        else:
            self._load_admissions()
        self._refresh_stats_async()

    def _edit_student(self):
        sel = self.students_tree.selection()
        if not sel:
            return messagebox.showinfo("Edit", "Select a student first.")
        d = self.row_maps["students"].get(sel[0])
        if not d:
            return
        self._student_dialog("Edit Student", d, lambda nd: self._update_student(d, nd))

    def _update_student(self, d, nd):
        email = nd.get("email", "").strip().casefold()
        idcard = nd.get("idcard", "").strip()
        for other in self.db.col("students").find():
            if str(other.get("_id")) == str(d.get("_id")):
                continue
            if email and str(other.get("email", "")).strip().casefold() == email:
                raise ValueError("Another student already uses this email address.")
            if idcard and str(other.get("idcard", "")).strip().casefold() == idcard.casefold():
                raise ValueError("Another student already uses this ID card number.")

        new_password = nd.pop("password", "").strip()
        old_email = str(d.get("email", "")).strip().casefold()
        linked_user = self._find_ci("users", "email", old_email) if old_email else None
        if email and not linked_user:
            candidate_user = self._find_ci("users", "email", email)
            if candidate_user and str(candidate_user.get("category", "")).lower() not in ("", "student"):
                raise ValueError("The new email address belongs to a non-student account.")
        if email != old_email and linked_user:
            other_user = self._find_ci("users", "email", email) if email else None
            if other_user and str(other_user.get("_id")) != str(linked_user.get("_id")):
                raise ValueError("The new email address is already linked to another account.")
            if not email:
                raise ValueError("A linked student login cannot have its email cleared.")
        if new_password:
            if len(new_password) < 8:
                raise ValueError("Password must contain at least 8 characters.")
            if not linked_user:
                raise ValueError("No linked login account exists for this student.")
        nd["email"] = email
        nd.pop("password", None)
        self.db.col("students").update_one({"_id": d["_id"]}, {"$set": nd})
        if linked_user:
            user_update = {"email": email, "name": nd.get("name", d.get("name", ""))}
            if new_password:
                user_update["password"] = hash_password(new_password)
            self.db.col("users").update_one(
                {"_id": linked_user["_id"]}, {"$set": user_update})
        self._load_students()
        self._refresh_stats_async()

    def _delete_student(self):
        sel = self.students_tree.selection()
        if not sel:
            return messagebox.showinfo("Delete", "Select a student first.")
        d = self.row_maps["students"].get(sel[0])
        if d and messagebox.askyesno(
                "Confirm",
                f"Delete {d.get('name')} and the linked student login account, if present?"):
            try:
                self.db.col("students").delete_one({"_id": d["_id"]})
                linked = self._find_ci("users", "email", d.get("email"))
                if linked and str(linked.get("category", "")).lower() == "student":
                    self.db.col("users").delete_one({"_id": linked["_id"]})
                self._notify(f"Student deleted: {d.get('name')}", roles=("principal", "teacher"))
                self._load_students()
                self._refresh_stats_async()
            except Exception as exc:
                messagebox.showerror("Delete failed", str(exc), parent=self.root)

    # ------------------------------ admissions page ---------------------------
    def _page_admissions(self, parent):
        self._header(parent, "Admissions", "New admission applications.")
        bar = tk.Frame(parent, bg=BG)
        bar.pack(fill="x", padx=26)
        tk.Button(bar, text="＋ New Admission", bg=ROYAL, fg="white", bd=0, cursor="hand2",
                  font=("Segoe UI", 9, "bold"), padx=12, pady=7,
                  command=lambda: self._add_student("admissions")).pack(side="left")
        card = Card(parent, height=440)
        card.pack(fill="x", padx=26, pady=12)
        self.admissions_tree = self._table(card.body, ("Name", "Course", "Branch", "Basis", "Contact", "Status"),
                                           height=14)
        self.admissions_tree.pack(fill="both", expand=True)
        self._search_bar(bar, self.admissions_tree)
        self._load_admissions()

    def _load_admissions(self):
        t = self.admissions_tree
        self._clear_tree(t)
        docs = self.db.col("admissions").find()
        if not docs:
            t.insert("", "end", values=("No admissions yet", "", "", "", "", ""))
            return
        for d in docs:
            t.insert("", "end", values=(d.get("name", ""), d.get("course", ""), d.get("branch", ""),
                                        d.get("basis", ""), d.get("mobile", ""), d.get("status", "Pending")))

    # --------------------------- courses & branches ---------------------------
    def _page_courses(self, parent):
        self._header(parent, "Courses & Branches",
                     "Add, review and remove the lookup values used by student forms.")
        self.course_lists = {}
        grid = tk.Frame(parent, bg=BG)
        grid.pack(fill="both", expand=True, padx=26, pady=10)
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)
        grid.rowconfigure(0, weight=1)

        for column, (title, collection) in enumerate(
                (("Courses", "courses"), ("Branches", "branches"))):
            panel = Card(grid, height=440)
            panel.grid(row=0, column=column, sticky="nsew",
                       padx=(0, 10) if column == 0 else (10, 0), pady=4)
            tk.Label(panel.body, text=title, bg=CARD, fg=INK,
                     font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(2, 8))
            controls = tk.Frame(panel.body, bg=CARD)
            controls.pack(fill="x", pady=(0, 8))
            entry = tk.Entry(controls, bg=BG, fg=INK, relief="flat",
                             highlightthickness=1, highlightbackground=BORDER,
                             font=("Segoe UI", 10))
            entry.pack(side="left", fill="x", expand=True, ipady=7)
            listing = tk.Listbox(panel.body, height=14, bg=BG, fg=INK,
                                 relief="flat", activestyle="none",
                                 selectbackground=ROYAL, selectforeground="white",
                                 highlightthickness=1, highlightbackground=BORDER,
                                 font=("Segoe UI", 10))
            listing.pack(fill="both", expand=True, pady=4)
            self.course_lists[collection] = listing

            def add_item(c=collection, e=entry, label=title):
                value = e.get().strip()
                if not value:
                    messagebox.showwarning(label, f"Enter a {label[:-1].lower()} name.",
                                           parent=self.root)
                    e.focus_set()
                    return
                existing = self._values(c)
                if any(value.casefold() == item.casefold() for item in existing):
                    messagebox.showinfo(label, f'"{value}" already exists.', parent=self.root)
                    e.focus_set()
                    e.selection_range(0, "end")
                    return
                try:
                    self.db.col(c).insert_one({"name": value, "created_at": today()})
                    e.delete(0, "end")
                    self._refresh_course_lists()
                    self._refresh_course_combos()
                    self._notify(f"{label[:-1]} added: {value}", roles=("principal",))
                    messagebox.showinfo(label, f'"{value}" added successfully.',
                                         parent=self.root)
                except Exception as exc:
                    messagebox.showerror("Save failed", str(exc), parent=self.root)

            def remove_item(c=collection, lb=listing, label=title):
                selected = lb.curselection()
                if not selected:
                    messagebox.showinfo(label, "Select an item to remove.", parent=self.root)
                    return
                value = lb.get(selected[0])
                field = "course" if c == "courses" else "branch"
                related = ("students", "admissions", "timetable", "examinations", "results")
                references = sum(len(self.db.col(collection).find({field: value}))
                                 for collection in related)
                if references:
                    messagebox.showwarning(
                        "Cannot remove",
                        f'"{value}" is referenced by {references} record(s). '
                        "Update or remove those records first.",
                        parent=self.root)
                    return
                if not messagebox.askyesno("Confirm removal",
                                           f"Remove {value} from {label.lower()}?",
                                           parent=self.root):
                    return
                try:
                    self.db.col(c).delete_many({"name": value})
                    self._refresh_course_lists()
                    self._refresh_course_combos()
                    self._notify(f"{label[:-1]} removed: {value}", roles=("principal",))
                except Exception as exc:
                    messagebox.showerror("Remove failed", str(exc), parent=self.root)

            add_button = tk.Button(controls, text="＋ Add", command=add_item, bg=SUCCESS, fg="white",
                                   activebackground="#15803D", activeforeground="white", bd=0,
                                   cursor="hand2", padx=13, pady=7,
                                   font=("Segoe UI", 9, "bold"))
            add_button.pack(side="left", padx=(7, 0))
            remove_button = tk.Button(panel.body, text="Remove selected", command=remove_item,
                                      bg="#FEE2E2", fg=DANGER, activebackground="#FECACA",
                                      bd=0, cursor="hand2", padx=12, pady=7,
                                      font=("Segoe UI", 9, "bold"))
            remove_button.pack(anchor="e", pady=(6, 0))
            if self.role != "principal":
                add_button.configure(state="disabled")
                remove_button.configure(state="disabled")
        self._refresh_course_lists()

    def _refresh_course_lists(self):
        for collection, listing in getattr(self, "course_lists", {}).items():
            if not listing.winfo_exists():
                continue
            listing.delete(0, "end")
            for value in self._values(collection):
                listing.insert("end", value)

    def _refresh_course_combos(self):
        for name in ("course_cb", "branch_cb", "res_branch", "tt_branch", "ex_branch"):
            widget = getattr(self, name, None)
            if widget is not None:
                try:
                    collection = "courses" if name == "course_cb" else "branches"
                    widget.configure(values=self._values(collection))
                except tk.TclError:
                    pass

    # ------------------------------ attendance --------------------------------
    def _page_attendance(self, parent):
        if self.staff:
            self._header(parent, "Attendance", "Mark attendance (staff only).")
            card = Card(parent, height=460)
            card.pack(fill="x", padx=26, pady=12)
            top = tk.Frame(card.body, bg=CARD)
            top.pack(fill="x")
            self.att_student = self._combo(top, [f"{s.get('name')} | {s.get('_id')}"
                                                 for s in self.db.col("students").find()], 34)
            self.att_student.pack(side="left", padx=4)
            self.att_status = self._combo(top, ["Present", "Absent", "Leave"], 12)
            self.att_status.set("Present")
            self.att_status.pack(side="left", padx=4)
            self.att_date = tk.Entry(top, bg=BG, relief="flat", width=14)
            self.att_date.insert(0, today())
            self.att_date.pack(side="left", padx=4)
            tk.Button(top, text="Mark", command=self._mark_attendance, bg=ROYAL, fg="white",
                      bd=0, cursor="hand2", padx=12, pady=6).pack(side="left", padx=4)
            self.att_tree = self._table(card.body, ("Student", "Date", "Status"), height=12)
            self.att_tree.pack(fill="both", expand=True, pady=8)
            self._load_attendance()
        else:
            self._header(parent, "My Attendance", "Read-only view.")
            self.att_tree = None
            self._load_student_attendance(parent)

    def _mark_attendance(self):
        sel = self.att_student.get().strip()
        status = self.att_status.get().strip()
        date_value = self.att_date.get().strip() or today()
        if not sel or " | " not in sel:
            return messagebox.showwarning("Attendance", "Select a student.", parent=self.root)
        if status not in ("Present", "Absent", "Leave"):
            return messagebox.showwarning("Attendance", "Select an attendance status.", parent=self.root)
        try:
            datetime.date.fromisoformat(date_value)
        except ValueError:
            return messagebox.showwarning("Attendance", "Use date format YYYY-MM-DD.", parent=self.root)
        sid, name = sel.split(" | ", 1)[1], sel.split(" | ", 1)[0]
        record = {"student": sid, "name": name, "date": date_value, "status": status}
        try:
            existing = self.db.col("attendance").find_one({"student": sid, "date": date_value})
            if existing:
                self.db.col("attendance").update_one(
                    {"_id": existing["_id"]}, {"$set": {"status": status, "name": name}})
            else:
                self.db.col("attendance").insert_one(record)
            self._notify(f"Attendance marked: {name} — {status} ({date_value})",
                         roles=("principal", "teacher"))
            self._load_attendance()
            messagebox.showinfo("Attendance", "Attendance saved successfully.")
        except Exception as exc:
            messagebox.showerror("Attendance failed", str(exc), parent=self.root)

    def _load_attendance(self):
        if not self.att_tree:
            return
        self._clear_tree(self.att_tree)
        for a in self.db.col("attendance").find(limit=300):
            self.att_tree.insert("", "end", values=(a.get("name", ""), a.get("date", ""), a.get("status", "")))

    def _load_student_attendance(self, parent):
        student = self._student_record()
        sid = str(student.get("_id")) if student else ""
        recs = self.db.col("attendance").find({"student": sid}) if sid else []
        now = datetime.date.today()
        def safe_date(record):
            try:
                return datetime.date.fromisoformat(str(record.get("date", ""))[:10])
            except (TypeError, ValueError):
                return None

        buckets = {
            "Today": [r for r in recs if safe_date(r) == now],
            "This week": [r for r in recs if safe_date(r) and
                          0 <= (now - safe_date(r)).days < 7],
            "This month": [r for r in recs if safe_date(r) and
                           safe_date(r).strftime("%Y-%m") == now.strftime("%Y-%m")],
            "Semester": recs,
        }
        card = Card(parent, height=340)
        card.pack(fill="x", padx=26, pady=10)
        for label, rows in buckets.items():
            total = len(rows)
            present = sum(1 for r in rows if r.get("status") == "Present")
            pct = round(present / total * 100) if total else 0
            r = tk.Frame(card.body, bg=CARD)
            r.pack(fill="x", pady=4)
            tk.Label(r, text=label, bg=CARD, fg=INK, width=14, anchor="w").pack(side="left")
            tk.Label(r, text=f"{present}/{total}", bg=CARD, fg=MUTED, width=10).pack(side="left")
            tk.Label(r, text=f"{pct}%", bg=CARD,
                     fg=SUCCESS if pct >= 75 else (WARN if pct >= 50 else DANGER),
                     font=("Segoe UI", 10, "bold")).pack(side="left")

    # -------------------------------- fees ------------------------------------
    def _page_fees(self, parent):
        self._header(parent, "Fees & Payments", "Semester fee tracking.")
        if not self.staff:
            self._load_student_fees(parent)
            return
        toolbar = tk.Frame(parent, bg=BG)
        toolbar.pack(fill="x", padx=26, pady=(4, 0))
        tk.Button(toolbar, text="＋ Record Payment", command=self._record_fee_payment,
                  bg=SUCCESS, fg="white", bd=0, cursor="hand2",
                  font=("Segoe UI", 9, "bold"), padx=13, pady=8).pack(side="left")
        tk.Button(toolbar, text="⟳ Refresh", command=self._load_fees,
                  bg=NAVY, fg="white", bd=0, cursor="hand2",
                  font=("Segoe UI", 9, "bold"), padx=13, pady=8).pack(side="left", padx=8)
        card = Card(parent, height=460)
        card.pack(fill="x", padx=26, pady=12)
        self.fee_tree = self._table(card.body, ("Student", "Total", "Paid", "Balance"), height=14)
        self.fee_tree.pack(fill="both", expand=True)
        self._load_fees()

    def _load_fees(self):
        self._clear_tree(self.fee_tree)
        docs = self.db.col("students").find()
        if not docs:
            self.fee_tree.insert("", "end", values=("No students", "", "", ""))
        for s in docs:
            total = safe_float(s.get("total_fee", 0))
            paid = safe_float(s.get("paid", 0))
            self.fee_tree.insert("", "end", values=(s.get("name", ""), f"₹{total:,.0f}",
                                                    f"₹{paid:,.0f}", f"₹{max(0,total-paid):,.0f}"))

    def _load_student_fees(self, parent):
        student = self._student_record()
        if not student:
            tk.Label(parent, text="No fee record linked to your account.", bg=BG,
                     fg=MUTED).pack(padx=26, pady=20)
            return
        total = safe_float(student.get("total_fee", 0))
        paid = safe_float(student.get("paid", 0))
        card = Card(parent, height=220)
        card.pack(fill="x", padx=26, pady=10)
        tk.Label(card.body, text=f"Total: ₹{total:,.0f}    Paid: ₹{paid:,.0f}    "
                                 f"Balance: ₹{max(0,total-paid):,.0f}",
                 bg=CARD, fg=INK, font=("Segoe UI", 12, "bold")).pack(anchor="w")
        tk.Label(card.body,
                 text="For payment posting and an official receipt, please contact the college fee office.",
                 bg=CARD, fg=MUTED, wraplength=650, justify="left").pack(anchor="w", pady=8)

        hist = self.db.col("fees").find({"student": str(student.get("_id"))})[-8:]
        for h in hist:
            tk.Label(card.body, text=f"₹{h.get('amount')} — Sem {h.get('semester')} — {h.get('date')}",
                     bg=CARD, fg=MUTED).pack(anchor="w")

    def _record_fee_payment(self):
        students = self.db.col("students").find()
        if not students:
            return messagebox.showinfo("Fee payment", "Add a student record first.")
        win = tk.Toplevel(self.root)
        win.title("Record Fee Payment")
        win.geometry("460x330")
        win.minsize(400, 300)
        win.configure(bg=CARD)
        win.transient(self.root)
        win.grab_set()

        tk.Label(win, text="Record a fee payment", bg=CARD, fg=INK,
                 font=("Segoe UI", 15, "bold")).pack(anchor="w", padx=22, pady=(18, 12))
        form = tk.Frame(win, bg=CARD)
        form.pack(fill="both", expand=True, padx=22)
        tk.Label(form, text="Student", bg=CARD, fg=MUTED,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")
        student_options = [f"{s.get('name', 'Student')} | {s.get('_id')}" for s in students]
        student_cb = ttk.Combobox(form, values=student_options, state="readonly")
        student_cb.pack(fill="x", pady=(3, 10), ipady=4)
        if student_options:
            student_cb.current(0)
        tk.Label(form, text="Amount (₹)", bg=CARD, fg=MUTED,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")
        amount_entry = tk.Entry(form, bg=BG, fg=INK, relief="flat")
        amount_entry.pack(fill="x", pady=(3, 10), ipady=7)
        tk.Label(form, text="Semester", bg=CARD, fg=MUTED,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")
        semester_cb = ttk.Combobox(form, values=[str(i) for i in range(1, 9)],
                                   state="readonly")
        semester_cb.pack(fill="x", pady=(3, 14), ipady=4)
        semester_cb.set("1")

        def save():
            selected = student_cb.get()
            if " | " not in selected:
                return messagebox.showwarning("Fee payment", "Select a student.", parent=win)
            try:
                amount = float(amount_entry.get().strip())
            except ValueError:
                return messagebox.showwarning("Fee payment", "Enter a valid amount.", parent=win)
            student_id = selected.split(" | ", 1)[1]
            student = self.db.col("students").find_one({"_id": student_id})
            if not student:
                return messagebox.showerror("Fee payment", "Student record no longer exists.", parent=win)
            try:
                self._post_fee_payment(student, amount, semester_cb.get() or "1")
                win.destroy()
            except Exception as exc:
                messagebox.showerror("Fee payment failed", str(exc), parent=win)

        tk.Button(win, text="Save Payment & Generate Receipt", command=save,
                  bg=SUCCESS, fg="white", bd=0, cursor="hand2",
                  font=("Segoe UI", 10, "bold"), padx=14, pady=9).pack(
                      fill="x", padx=22, pady=(4, 18))

    def _post_fee_payment(self, student, amount, semester):
        if not math.isfinite(amount) or amount <= 0:
            raise ValueError("Payment amount must be a finite number greater than zero.")
        total = safe_float(student.get("total_fee", 0))
        paid = safe_float(student.get("paid", 0))
        balance = max(0.0, total - paid)
        if balance <= 0:
            raise ValueError("This student has no outstanding fee balance.")
        if amount > balance:
            raise ValueError(f"Payment exceeds the outstanding balance of ₹{balance:,.2f}.")
        payment = {
            "student": str(student.get("_id")), "name": student.get("name", ""),
            "amount": amount, "semester": semester, "date": today(),
            "recorded_by": self.user.get("email", self.user.get("name", "staff"))
        }
        inserted = self.db.col("fees").insert_one(payment)
        payment_id = (inserted.get("_id") if isinstance(inserted, dict)
                      else getattr(inserted, "inserted_id", None))
        try:
            result = self.db.col("students").update_one(
                {"_id": student["_id"]},
                {"$set": {"paid": paid + amount}})
            if self.db.online and getattr(result, "matched_count", 1) == 0:
                raise RuntimeError("Student balance was changed by another operation. Refresh and retry.")
        except Exception:
            try:
                if payment_id is not None:
                    self.db.col("fees").delete_one({"_id": payment_id})
            except Exception:
                pass
            raise
        self._notify(f"Fee paid ₹{amount:,.2f} by {student.get('name')} (Sem {semester})",
                     roles=("principal", "teacher"), email=student.get("email"))
        self._load_fees()
        self._refresh_stats_async()
        self._receipt(student, amount, semester)
        messagebox.showinfo("Fee payment", "Payment recorded successfully.")

    def _receipt(self, student, amt, sem):
        path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")],
                                            initialfile=f"receipt_{student.get('name','student')}.pdf")
        if not path:
            return
        lines = [f"Name: {student.get('name')}", f"ID: {student.get('idcard','')}",
                 f"Course: {student.get('course','')}  Branch: {student.get('branch','')}",
                 f"Semester: {sem}", f"Amount Paid: Rs {amt:,.0f}", f"Date: {today()}",
                 "", "This is a computer-generated receipt."]
        make_pdf(path, "FEE RECEIPT", lines)
        messagebox.showinfo("Receipt", f"Saved to {path}")

    # ------------------------------ examinations ------------------------------
    def _page_examinations(self, parent):
        self._header(parent, "Examinations", "Schedule exams and generate admit cards.")
        if self.staff:
            form = Card(parent, height=300)
            form.pack(fill="x", padx=26, pady=8)
            g = tk.Frame(form.body, bg=CARD)
            g.pack(fill="x")
            g.columnconfigure(1, weight=1)
            self.ex_branch = self._labeled_combo(g, "Branch", self._values("branches"), 0)
            self.ex_subject = self._entry_row(g, "Subject", 1)
            self.ex_sem = self._labeled_combo(g, "Semester", [str(i) for i in range(1, 9)], 2)
            self.ex_date = self._entry_row(g, "Date (YYYY-MM-DD)", 3)
            self.ex_shift = self._labeled_combo(g, "Shift", ["Morning", "Afternoon", "Evening"], 4)
            self.ex_time = self._entry_row(g, "Time (e.g. 10:00)", 5)
            self.ex_dur = self._entry_row(g, "Duration (e.g. 3h)", 6)
            tk.Button(form.body, text="Schedule Exam", command=self._schedule_exam, bg=ROYAL,
                      fg="white", bd=0, cursor="hand2", padx=14, pady=8).pack(anchor="w", pady=8)
        card = Card(parent, height=400)
        card.pack(fill="x", padx=26, pady=8)
        self.exam_tree = self._table(card.body, ("Date", "Branch", "Sem", "Subject", "Shift", "Time", "Duration"),
                                     height=12)
        self.exam_tree.pack(fill="both", expand=True)
        self.exam_tree.bind("<Double-1>", lambda _e: self._admit_card())
        self._load_exams()

    def _entry_row(self, parent, label, row):
        tk.Label(parent, text=label, bg=CARD, fg=MUTED,
                 font=("Segoe UI", 8, "bold")).grid(row=row, column=0, sticky="w", pady=3)
        e = tk.Entry(parent, bg=BG, relief="flat", highlightthickness=1,
                     highlightbackground=BORDER)
        e.grid(row=row, column=1, sticky="ew", pady=3, ipady=5)
        return e

    def _schedule_exam(self):
        record = {"branch": self.ex_branch.get().strip(), "subject": self.ex_subject.get().strip(),
                  "semester": self.ex_sem.get().strip(), "date": self.ex_date.get().strip() or today(),
                  "shift": self.ex_shift.get().strip(), "time": self.ex_time.get().strip(),
                  "duration": self.ex_dur.get().strip()}
        if not all(record.values()):
            return messagebox.showwarning("Exam", "Complete all examination fields.")
        try:
            datetime.date.fromisoformat(record["date"])
        except ValueError:
            return messagebox.showwarning("Exam", "Date must use YYYY-MM-DD.")
        if self.db.col("examinations").find_one(
                {k: record[k] for k in ("branch", "semester", "subject", "date", "shift")}):
            return messagebox.showinfo("Exam", "A matching examination is already scheduled.")
        try:
            self.db.col("examinations").insert_one(record)
            self._notify(f"Exam scheduled: {record['subject']} ({record['branch']})",
                         roles=("principal", "teacher"))
            self._load_exams()
            messagebox.showinfo("Exam", "Examination scheduled successfully.")
        except Exception as exc:
            messagebox.showerror("Exam", str(exc), parent=self.root)

    def _load_exams(self):
        if not hasattr(self, "exam_tree"):
            return
        self._clear_tree(self.exam_tree)
        if self.role == "student":
            own = self._student_record() or {}
            docs = self.db.col("examinations").find(
                {"branch": own.get("branch"), "semester": str(own.get("semester", ""))})
        else:
            docs = self.db.col("examinations").find()
        if not docs:
            self.exam_tree.insert("", "end", values=("No exams scheduled", "", "", "", "", "", ""))
        for i, d in enumerate(docs):
            self.exam_tree.insert("", "end", iid=str(d.get("_id")), values=(
                d.get("date", ""), d.get("branch", ""), d.get("semester", ""),
                d.get("subject", ""), d.get("shift", ""), d.get("time", ""), d.get("duration", "")))

    def _admit_card(self):
        selected = self.exam_tree.selection()
        if not selected:
            return messagebox.showinfo("Admit Card", "Select an exam row first.")
        exam = self.db.col("examinations").find_one({"_id": selected[0]}) or {}
        if self.staff:
            students = self.db.col("students").find(
                {"branch": exam.get("branch"), "semester": str(exam.get("semester", ""))})
            if not students:
                return messagebox.showinfo("Admit Card", "No students match this exam's branch and semester.")
            win = tk.Toplevel(self.root)
            win.title("Select Student")
            win.geometry("420x170")
            win.configure(bg=CARD)
            win.transient(self.root)
            win.grab_set()
            tk.Label(win, text="Choose the student for this admit card",
                     bg=CARD, fg=INK, font=("Segoe UI", 11, "bold")).pack(
                         anchor="w", padx=18, pady=(18, 10))
            choices = [f"{s.get('name', 'Student')} | {s.get('_id')}" for s in students]
            cb = ttk.Combobox(win, values=choices, state="readonly")
            cb.pack(fill="x", padx=18, pady=4)
            if choices:
                cb.current(0)

            def generate():
                value = cb.get()
                if " | " not in value:
                    return messagebox.showwarning("Admit Card", "Select a student.", parent=win)
                student = self.db.col("students").find_one({"_id": value.split(" | ", 1)[1]})
                if not student:
                    return messagebox.showerror("Admit Card", "Student record not found.", parent=win)
                win.destroy()
                self._create_admit_card(student, exam)

            tk.Button(win, text="Generate Admit Card", command=generate, bg=ROYAL,
                      fg="white", bd=0, cursor="hand2", padx=14, pady=7).pack(
                          anchor="e", padx=18, pady=12)
            return
        student = self._student_record()
        if not student:
            return messagebox.showinfo("Admit Card", "No student record is linked to your account.")
        if student.get("branch") != exam.get("branch") or str(student.get("semester")) != str(exam.get("semester")):
            return messagebox.showinfo("Admit Card", "This examination is not assigned to your branch and semester.")
        self._create_admit_card(student, exam)

    def _create_admit_card(self, student, exam):
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf", filetypes=[("PDF", "*.pdf")],
            initialfile=f"admit_{student.get('name', 'student')}.pdf")
        if not path:
            return
        lines = [f"Student: {student.get('name')}", f"ID: {student.get('idcard', '')}",
                 f"Branch: {exam.get('branch')}  Sem: {exam.get('semester')}",
                 f"Subject: {exam.get('subject')}", f"Date: {exam.get('date')}",
                 f"Shift: {exam.get('shift')}  Time: {exam.get('time')}  Duration: {exam.get('duration')}"]
        make_pdf(path, "ADMIT CARD", lines)
        self._notify(f"Admit card downloaded by {student.get('name')}",
                     roles=("principal", "teacher"), email=student.get("email"))
        messagebox.showinfo("Admit Card", f"Saved to {path}")

    # -------------------------------- results ---------------------------------
    def _page_results(self, parent):
        self._header(parent, "Results & Grades", "Enter and download results.")
        if self.staff:
            form = Card(parent, height=260)
            form.pack(fill="x", padx=26, pady=8)
            g = tk.Frame(form.body, bg=CARD)
            g.pack(fill="x")
            g.columnconfigure(1, weight=1)
            self.res_branch = self._labeled_combo(g, "Branch", self._values("branches"), 0)
            self.res_sem = self._labeled_combo(g, "Semester", [str(i) for i in range(1, 9)], 1)
            self.res_subject = self._entry_row(g, "Subject", 2)
            self.res_marks = self._entry_row(g, "Marks (0-100)", 3)
            self.res_student = self._labeled_combo(g, "Student", [f"{s.get('name')} | {s.get('_id')}"
                                                                  for s in self.db.col("students").find()], 4)
            tk.Button(form.body, text="Save Result", command=self._save_result, bg=ROYAL,
                      fg="white", bd=0, cursor="hand2", padx=14, pady=8).pack(anchor="w", pady=8)
        card = Card(parent, height=380)
        card.pack(fill="x", padx=26, pady=8)
        self.res_tree = self._table(card.body, ("Student", "Sem", "Subject", "Marks"), height=12)
        self.res_tree.pack(fill="both", expand=True)
        self.res_tree.bind("<Double-1>", lambda _e: self._result_pdf())
        self._load_results()

    def _save_result(self):
        selected = self.res_student.get().strip()
        subject = self.res_subject.get().strip()
        if not selected or not subject or not self.res_sem.get():
            return messagebox.showwarning("Result", "Select a student and semester, and enter a subject.")
        try:
            marks = float(self.res_marks.get().strip())
            if not 0 <= marks <= 100:
                raise ValueError
        except ValueError:
            return messagebox.showwarning("Result", "Marks must be a number from 0 to 100.")
        name, sid = selected.split(" | ", 1)
        record = {"student": sid, "name": name, "branch": self.res_branch.get(),
                  "semester": self.res_sem.get(), "subject": subject, "marks": marks}
        existing = self.db.col("results").find_one(
            {"student": sid, "semester": record["semester"], "subject": subject})
        try:
            if existing:
                self.db.col("results").update_one({"_id": existing["_id"]}, {"$set": record})
                action = "updated"
            else:
                self.db.col("results").insert_one(record)
                action = "added"
            self._notify(f"Result {action}: {name} — {subject}", roles=("principal", "teacher"))
            self._load_results()
            messagebox.showinfo("Result", f"Result {action} successfully.")
        except Exception as exc:
            messagebox.showerror("Result", str(exc), parent=self.root)

    def _load_results(self):
        if not hasattr(self, "res_tree"):
            return
        self._clear_tree(self.res_tree)
        if self.role == "student":
            own = self._student_record()
            docs = self.db.col("results").find({"student": str(own.get("_id"))}) if own else []
        else:
            docs = self.db.col("results").find()
        if not docs:
            self.res_tree.insert("", "end", values=("No results yet", "", "", ""))
        for d in docs:
            self.res_tree.insert("", "end", iid=str(d.get("_id")), values=(
                d.get("name", ""), d.get("semester", ""), d.get("subject", ""), d.get("marks", "")))

    def _result_pdf(self):
        sel = self.res_tree.selection()
        if not sel:
            return
        d = self.db.col("results").find_one({"_id": sel[0]})
        if not d:
            return
        path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")],
                                            initialfile=f"result_{d.get('name')}.pdf")
        if not path:
            return
        lines = [f"Student: {d.get('name')}", f"Semester: {d.get('semester')}",
                 f"Branch: {d.get('branch')}", f"Subject: {d.get('subject')}",
                 f"Marks: {d.get('marks')}", f"Date: {today()}"]
        make_pdf(path, "RESULT SHEET", lines)
        self._notify(f"Result downloaded by {d.get('name')}",
                     roles=("principal", "teacher"), email=self.user.get("email"))
        messagebox.showinfo("Result", f"Saved to {path}")

    # -------------------------------- teachers --------------------------------
    def _page_teachers(self, parent):
        self._header(parent, "Teachers & Staff", "Staff records (principal only).")
        bar = tk.Frame(parent, bg=BG)
        bar.pack(fill="x", padx=26)
        tk.Button(bar, text="＋ Add Teacher", command=self._add_teacher, bg=ROYAL, fg="white",
                  bd=0, cursor="hand2", padx=12, pady=7,
                  font=("Segoe UI", 9, "bold")).pack(side="left")
        card = Card(parent, height=420)
        card.pack(fill="x", padx=26, pady=12)
        self.teacher_tree = self._table(card.body, ("Name", "Department", "Subject", "Contact", "Status"),
                                        height=14)
        self.teacher_tree.pack(fill="both", expand=True)
        self._search_bar(bar, self.teacher_tree)
        self._load_teachers()

    def _load_teachers(self):
        self._clear_tree(self.teacher_tree)
        docs = self.db.col("teachers").find()
        if not docs:
            self.teacher_tree.insert("", "end", values=("No teachers yet", "", "", "", ""))
        for d in docs:
            self.teacher_tree.insert("", "end", values=(d.get("name", ""), d.get("department", ""),
                                                        d.get("subject", ""), d.get("mobile", ""),
                                                        d.get("status", "Active")))

    def _add_teacher(self):
        win = tk.Toplevel(self.root); win.title("Add Teacher"); win.geometry("420x360")
        win.configure(bg=CARD)
        area = ScrollArea(win); area.pack(fill="both", expand=True)
        entries = {}
        for key, label in (("name", "Name"), ("email", "Email"), ("department", "Department"),
                           ("subject", "Subject"), ("mobile", "Mobile")):
            tk.Label(area.inner, text=label, bg=CARD, fg=MUTED,
                     font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=18, pady=(6, 1))
            e = tk.Entry(area.inner, bg=BG, relief="flat", highlightthickness=1,
                         highlightbackground=BORDER)
            e.pack(fill="x", padx=18, ipady=6)
            entries[key] = e

        def save():
            data = {k: v.get().strip() for k, v in entries.items()}
            if not data.get("name"):
                return messagebox.showwarning("Teacher", "Name required.", parent=win)
            if data.get("email") and self._find_ci("teachers", "email", data["email"]):
                return messagebox.showwarning("Teacher", "This email is already registered.", parent=win)
            data["email"] = data.get("email", "").strip().casefold()
            data["status"] = "Active"
            try:
                self.db.col("teachers").insert_one(data)
                self._notify(f"Teacher added: {data['name']}", roles=("principal",))
                win.destroy()
                self._load_teachers()
                messagebox.showinfo("Teacher", "Teacher added successfully.")
            except Exception as exc:
                messagebox.showerror("Teacher", str(exc), parent=win)
        tk.Button(area.inner, text="Save", command=save, bg=SUCCESS, fg="white", bd=0,
                  cursor="hand2").pack(fill="x", padx=18, pady=10, ipady=8)

    # -------------------------------- timetable -------------------------------
    def _page_timetable(self, parent):
        self._header(parent, "Timetable", "Generate and download schedules.")
        if self.staff:
            form = Card(parent, height=230)
            form.pack(fill="x", padx=26, pady=8)
            g = tk.Frame(form.body, bg=CARD); g.pack(fill="x"); g.columnconfigure(1, weight=1)
            self.tt_branch = self._labeled_combo(g, "Branch", self._values("branches"), 0)
            self.tt_sem = self._labeled_combo(g, "Semester", [str(i) for i in range(1, 9)], 1)
            self.tt_day = self._labeled_combo(g, "Day", ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"], 2)
            self.tt_period = self._entry_row(g, "Period / Time", 3)
            self.tt_subject = self._entry_row(g, "Subject", 4)
            tk.Button(form.body, text="Add Period", command=self._add_period, bg=ROYAL, fg="white",
                      bd=0, cursor="hand2", padx=14, pady=8).pack(anchor="w", pady=8)
        card = Card(parent, height=380)
        card.pack(fill="x", padx=26, pady=8)
        self.tt_tree = self._table(card.body, ("Branch", "Sem", "Day", "Period", "Subject"), height=12)
        self.tt_tree.pack(fill="both", expand=True)
        self.tt_tree.bind("<Double-1>", lambda _e: self._timetable_pdf())
        self._load_tt()

    def _add_period(self):
        record = {"branch": self.tt_branch.get().strip(), "semester": self.tt_sem.get().strip(),
                  "day": self.tt_day.get().strip(), "period": self.tt_period.get().strip(),
                  "subject": self.tt_subject.get().strip()}
        if not all(record.values()):
            return messagebox.showwarning("Timetable", "Complete all timetable fields.")
        if self.db.col("timetable").find_one(record):
            return messagebox.showinfo("Timetable", "This period already exists.")
        try:
            self.db.col("timetable").insert_one(record)
            self._notify(f"Timetable period added ({record['branch']} Sem {record['semester']})",
                         roles=("principal", "teacher"))
            self._load_tt()
            messagebox.showinfo("Timetable", "Period added successfully.")
        except Exception as exc:
            messagebox.showerror("Timetable", str(exc), parent=self.root)

    def _load_tt(self):
        if not hasattr(self, "tt_tree"):
            return
        self._clear_tree(self.tt_tree)
        if self.role == "student":
            own = self._student_record() or {}
            docs = self.db.col("timetable").find(
                {"branch": own.get("branch"), "semester": str(own.get("semester", ""))})
        else:
            docs = self.db.col("timetable").find()
        if not docs:
            self.tt_tree.insert("", "end", values=("No timetable yet", "", "", "", ""))
        for d in docs:
            self.tt_tree.insert("", "end", iid=str(d.get("_id")), values=(
                d.get("branch", ""), d.get("semester", ""), d.get("day", ""),
                d.get("period", ""), d.get("subject", "")))

    def _timetable_pdf(self):
        sel = self.tt_tree.selection()
        if not sel:
            return
        d = self.db.col("timetable").find_one({"_id": sel[0]})
        if not d:
            return
        rows = self.db.col("timetable").find({"branch": d.get("branch"), "semester": d.get("semester")})
        lines = [f"Branch: {d.get('branch')}  Semester: {d.get('semester')}", ""]
        for r in rows:
            lines.append(f"{r.get('day')}  {r.get('period')}  {r.get('subject')}")
        path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")],
                                            initialfile="timetable.pdf")
        if not path:
            return
        make_pdf(path, "CLASS TIMETABLE", lines, sign=False)
        messagebox.showinfo("Timetable", f"Saved to {path}")

    # -------------------------------- settings --------------------------------
    def _page_settings(self, parent):
        self._header(parent, "Settings", "Profile, security and status.")
        prof = Card(parent, height=200)
        prof.pack(fill="x", padx=26, pady=8)
        row = tk.Frame(prof.body, bg=CARD); row.pack(anchor="w")
        self.settings_avatar = Avatar(row, self.user.get("name"), photo=self.user_photo, size=84,
                                      on_click=self._view_user_image)
        self.settings_avatar.pack(side="left")
        col = tk.Frame(row, bg=CARD); col.pack(side="left", padx=16)
        tk.Label(col, text=self.user.get("name", "Admin"), bg=CARD, fg=INK,
                 font=("Segoe UI", 15, "bold")).pack(anchor="w")
        tk.Label(col, text=self.role.title(), bg=CARD, fg=MUTED).pack(anchor="w")
        tk.Button(col, text="📷 Upload Photo", command=self._upload_photo, bg=ROYAL, fg="white",
                  bd=0, cursor="hand2", padx=12, pady=6).pack(anchor="w", pady=8)

        pw = Card(parent, height=250)
        pw.pack(fill="x", padx=26, pady=8)
        tk.Label(pw.body, text="Change Password", bg=CARD, fg=INK,
                 font=("Segoe UI", 13, "bold")).pack(anchor="w")
        self.pw_old = self._pw_field(pw.body, "Current password")
        self.pw_new = self._pw_field(pw.body, "New password (min 8, letter+digit)")
        self.pw_conf = self._pw_field(pw.body, "Confirm new password")
        tk.Button(pw.body, text="Update Password", command=self._change_password, bg=SUCCESS,
                  fg="white", bd=0, cursor="hand2").pack(anchor="w", pady=8, ipadx=10, ipady=6)

        if self.role == "principal":
            leave = Card(parent, height=200)
            leave.pack(fill="x", padx=26, pady=8)
            tk.Label(leave.body, text="Leave College (Archive)", bg=CARD, fg=INK,
                     font=("Segoe UI", 13, "bold")).pack(anchor="w")
            self.leave_reason = tk.Entry(leave.body, bg=BG, relief="flat",
                                         highlightthickness=1, highlightbackground=BORDER)
            self.leave_reason.pack(fill="x", pady=6, ipady=5)
            tk.Button(leave.body, text="Archive Students (matching reason)",
                      command=self._archive_students, bg=DANGER, fg="white", bd=0,
                      cursor="hand2").pack(anchor="w", pady=4, ipadx=10, ipady=6)

    def _pw_field(self, parent, label):
        tk.Label(parent, text=label, bg=CARD, fg=MUTED,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(6, 1))
        e = tk.Entry(parent, bg=BG, relief="flat", highlightthickness=1,
                     highlightbackground=BORDER, show="●")
        e.pack(fill="x", ipady=6)
        return e

    def _upload_photo(self):
        if not PIL_OK:
            return messagebox.showinfo("Photo", "Pillow not installed.")
        p = filedialog.askopenfilename(filetypes=[("Images", "*.jpg *.jpeg *.png")])
        if not p:
            return
        try:
            img = Image.open(p).convert("RGB")
            t = img.copy(); t.thumbnail((128, 128))
            with open(p, "rb") as photo_file:
                b64 = base64.b64encode(photo_file.read()).decode()
            self.user_pil = t; self.user_photo = ImageTk.PhotoImage(t)
            for av, size in ((self.top_avatar, 34), (self.settings_avatar, 84)):
                if av:
                    av.delete("all")
                    s = t.copy(); s.thumbnail((size, size))
                    ph = ImageTk.PhotoImage(s)
                    av.create_image(size / 2, size / 2, image=ph); av.image = ph
            email = self.user.get("email")
            if email:
                account = self._find_ci("users", "email", email)
                if account:
                    self.db.col("users").update_one(
                        {"_id": account["_id"]}, {"$set": {"avatar_b64": b64}})
                else:
                    self.db.col("users").insert_one({"email": email, "avatar_b64": b64})
            self.user["avatar_b64"] = b64
            messagebox.showinfo("Photo", "Updated.")
        except Exception as exc:
            messagebox.showerror("Upload", str(exc))

    def _change_password(self):
        old, new, conf = self.pw_old.get(), self.pw_new.get(), self.pw_conf.get()
        if len(new) < 8 or not any(c.isalpha() for c in new) or not any(c.isdigit() for c in new):
            return messagebox.showwarning("Password", "Min 8 chars, letter + digit.")
        if new != conf:
            return messagebox.showwarning("Password", "Passwords do not match.")
        email = self.user.get("email")
        rec = self._find_ci("users", "email", email) if email else None
        stored = (rec or {}).get("password") or self.user.get("password")
        if not stored or not verify_password(old, stored):
            return messagebox.showerror("Password", "Current password could not be verified. Please sign in again.")
        if not email or not rec:
            return messagebox.showerror("Password", "No linked account record was found. Password was not changed.")
        try:
            self.db.col("users").update_one({"_id": rec["_id"]},
                                            {"$set": {"password": hash_password(new)}})
            self.user["password"] = hash_password(new)
            for field in (self.pw_old, self.pw_new, self.pw_conf):
                field.delete(0, "end")
            messagebox.showinfo("Password", "Password updated.")
        except Exception as exc:
            messagebox.showerror("Password", str(exc))

    def _archive_students(self):
        reason = self.leave_reason.get().strip() or "Left college"
        docs = self.db.col("students").find()
        if not docs:
            return messagebox.showinfo("Archive", "No students to archive.")
        if not messagebox.askyesno("Archive", f"Move {len(docs)} student(s) to archive DB?"):
            return
        archived = 0
        try:
            for original in docs:
                d = dict(original)
                d["leave_reason"] = reason
                d["left_at"] = today()
                for private_field in ("password", "salt", "hash"):
                    d.pop(private_field, None)
                self.db.archive_col("students").insert_one(d)
                self.db.col("students").delete_one({"_id": d["_id"]})
                linked = self._find_ci("users", "email", d.get("email"))
                if linked and str(linked.get("category", "")).lower() == "student":
                    self.db.col("users").delete_one({"_id": linked["_id"]})
                archived += 1
        except Exception as exc:
            messagebox.showerror(
                "Archive partially completed",
                f"{archived} student(s) archived before the error:\n{exc}",
                parent=self.root)
        if archived:
            self._notify(f"{archived} student(s) archived — reason: {reason}", roles=("principal",))
            self._load_students()
            self._refresh_stats_async()

    # -------------------------------- logout ----------------------------------
    def _logout(self):
        if self._closing:
            return
        if not messagebox.askyesno("Logout", "Log out of the dashboard?"):
            return
        self._closing = True
        self.alive = False
        try:
            self.db.close()
        except Exception:
            pass
        try:
            for s in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                self.root.unbind_all(s)
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
