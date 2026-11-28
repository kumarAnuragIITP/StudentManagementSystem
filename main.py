import io
import os
import re
import hashlib
import secrets
import datetime
import calendar
import threading
import urllib.request
import traceback
import tkinter as tk
from tkinter import messagebox


try:
    from PIL import Image, ImageTk, ImageOps, ImageEnhance
    PIL_OK = True
except Exception:
    PIL_OK = False

try:
    from pymongo import MongoClient
    MONGO_OK = True
except Exception:
    MONGO_OK = False



COLLEGE_NAME = "GOVERNMENT POLYTECHNIC CHAPRA"
COLLEGE_TAGLINE = "A smarter, safer campus experience"

APP_TITLE = f"Student Management System | {COLLEGE_NAME.title()}"
MONGO_URI = "mongodb://localhost:27017"
DATABASE_NAME = "student_management"
USERS_COLLECTION = "users"







LOGO_PATH = "C:\\Users\\kanur\\PycharmProjects\\VWSP\\PythonProject\\images\\gpc.png"



BACKGROUND_URL = (
    "https://images.unsplash.com/photo-1523240795612-9a054b0db644"
    "?auto=format&fit=crop&w=2200&q=85"
)


NAVY = "#0B1730"
NAVY_2 = "#122541"
NAVY_3 = "#1B385C"
PANEL = "#FFFFFF"
PANEL_SOFT = "#F5F8FC"
INK = "#17243A"
MUTED = "#718096"
BORDER = "#E4EAF2"
ACCENT = "#2563EB"
ACCENT_HOVER = "#1D4ED8"
TEAL = "#0EA5A4"
SUCCESS = "#168653"
DANGER = "#D64545"
FIELD = "#F7F9FC"
WHITE = "#FFFFFF"

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
MOBILE_RE = re.compile(r"^[6-9]\d{9}$")
ID_RE = re.compile(r"^[A-Za-z0-9]{4,20}$")
PASSWORD_RE = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{8,}$")
USERNAME_RE = re.compile(r"^[a-zA-Z0-9._-]{4,32}$")
CATEGORIES = ("student", "teacher", "principal")

SCROLL_SEQUENCES = ("<MouseWheel>", "<Button-4>", "<Button-5>", "<Shift-MouseWheel>")



def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 180_000
    )
    return {"salt": salt, "hash": digest.hex()}


def verify_password(password, record):
    try:
        if not record or not record.get("salt") or not record.get("hash"):
            return False
        return secrets.compare_digest(
            hash_password(password, record["salt"])["hash"], record["hash"]
        )
    except Exception:
        return False


def make_username(email, collection):
    base = re.sub(r"[^a-zA-Z0-9._-]", "", email.split("@", 1)[0]).lower()
    base = (base[:22] or "student")
    for _ in range(30):
        candidate = f"{base}_{secrets.randbelow(90000) + 10000}"
        if not collection.find_one({"username": candidate}):
            return candidate
    raise RuntimeError("Could not generate a unique username. Please try again.")


def valid_date(value):
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            datetime.datetime.strptime(value, fmt)
            return True
        except ValueError:
            continue
    return False


class MemoryUsers:
    def __init__(self):
        self.records = {}

    def find_one(self, query):
        if "email" in query:
            return self.records.get(str(query["email"]).lower())
        for record in self.records.values():
            if all(record.get(k) == v for k, v in query.items()):
                return record
        return None

    def insert_one(self, document):
        item = dict(document)
        key = str(item.get("email", "")).lower()
        if key in self.records:
            raise ValueError("Email already exists")
        item["_id"] = key
        self.records[key] = item

    def update_one(self, query, update):
        item = self.find_one(query)
        if item and "$set" in update:
            item.update(update["$set"])

    def count_documents(self, query=None):
        return len(self.records)


def connect_database():
    if not MONGO_OK:
        return MemoryUsers(), False, None
    client = None
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=4000)
        client.admin.command("ping")
        collection = client[DATABASE_NAME][USERS_COLLECTION]
        try:
            collection.create_index("emai", unique=True, name="email_unique_auth")
        except Exception:
            pass
        return collection, True, client
    except Exception:
        try:
            if client is not None:
                client.close()
        except Exception:
            pass
        return MemoryUsers(), False, None



class StudentPortal(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1240x820")
        self.minsize(900, 680)
        self.configure(bg=NAVY)

        self.db, self.mongo_online, self.mongo_client = connect_database()
        self.auth_busy = False
        self.dashboard_opening = False
        self.login_failures = {}
        self.login_locked_until = {}
        self.background_source = None
        self.background_photo = None
        self.logo_photo = None
        self.alive = True
        self.current_tab = "signin"
        self.form_vars = {}
        self.category = tk.StringVar(value="student")
        self.status_text = tk.StringVar(value="")
        self.status_kind = "info"
        self._resize_job = None
        self._scroll_acc = 0.0

        self._build_background()
        self._build_interface()
        if not self.mongo_online:
            self._set_status(
                "DATABASE OFFLINE: MongoDB is unavailable. Accounts cannot be saved or authenticated until the database is running.",
                "error"
            )
        self._update_clock()
        self.protocol("WM_DELETE_WINDOW", self._close)



        if PIL_OK:
            threading.Thread(target=self._download_background, daemon=True).start()


    def _build_background(self):
        self.bg_canvas = tk.Canvas(
            self, bg=NAVY, highlightthickness=0, bd=0
        )
        self.bg_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self.bind("<Configure>", self._on_resize, add="+")

    def _download_background(self):
        try:
            request = urllib.request.Request(
                BACKGROUND_URL, headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(request, timeout=7) as response:
                raw = response.read()
            image = Image.open(io.BytesIO(raw)).convert("RGB")
            self.background_source = image
            if self.alive:
                self.after(0, self._render_background)
        except Exception:

            self.background_source = None

    def _on_resize(self, _event=None):
        if self._resize_job:
            try:
                self.after_cancel(self._resize_job)
            except Exception:
                pass
        self._resize_job = self.after(70, self._render_background)
        try:
            self.after_idle(self._adapt_layout)
        except Exception:
            pass

    def _render_background(self):
        if not self.winfo_exists():
            return
        width = max(1, self.winfo_width())
        height = max(1, self.winfo_height())
        canvas = self.bg_canvas


        canvas.delete("background")
        self.background_photo = None

        if self.background_source is not None and PIL_OK:
            try:
                image = ImageOps.fit(
                    self.background_source, (width, height),
                    method=Image.Resampling.LANCZOS
                )
                image = ImageEnhance.Brightness(image).enhance(0.48)
                self.background_photo = ImageTk.PhotoImage(image)
                canvas.create_image(
                    0, 0, image=self.background_photo, anchor="nw",
                    tags="background"
                )

                canvas.create_rectangle(
                    0, 0, width, height, fill="#0B1730",
                    stipple="gray50", outline="", tags="background"
                )
            except Exception:
                self.background_source = None
                self._draw_gradient(width, height)
        else:
            self._draw_gradient(width, height)

        canvas.tag_lower("background")

    def _draw_gradient(self, width, height):

        c = self.bg_canvas
        top = (12, 25, 49)
        bottom = (30, 59, 91)
        strips = 100
        strip_h = max(1, height // strips + 1)
        for index in range(strips):
            ratio = index / max(1, strips - 1)
            rgb = tuple(
                int(top[i] + (bottom[i] - top[i]) * ratio) for i in range(3)
            )
            color = "#%02x%02x%02x" % rgb
            y = index * strip_h
            c.create_rectangle(
                0, y, width, y + strip_h + 1,
                fill=color, outline=color, tags="background"
            )


    def _build_interface(self):
        # Main application shell
        self.shell = tk.Frame(
            self, bg="#0B1730",
            highlightthickness=1, highlightbackground="#526985"
        )
        self.shell.place(
            relx=0.5, rely=0.5, anchor="center",
            relwidth=0.95, relheight=0.94
        )

        # Slim accent line
        tk.Frame(self.shell, bg="#35D0C8", height=4).pack(fill="x")

        self.header = tk.Frame(
            self.shell, bg="#122541",
            highlightthickness=1, highlightbackground="#2C4566"
        )
        self.header.pack(fill="x", padx=16, pady=(14, 14))

        left_header = tk.Frame(self.header, bg="#122541")
        left_header.pack(side="left", padx=20, pady=13)

        self.logo_area = tk.Frame(
            left_header, bg="#FFFFFF", width=58, height=58
        )
        self.logo_area.pack(side="left", padx=(0, 14))
        self.logo_area.pack_propagate(False)

        self.logo_label = tk.Label(
            self.logo_area, text="GPC", bg="#FFFFFF", fg="#2563EB",
            font=("Segoe UI", 17, "bold")
        )
        self.logo_label.pack(expand=True, fill="both")
        self._load_logo()

        title_box = tk.Frame(left_header, bg="#122541")
        title_box.pack(side="left")

        tk.Label(
            title_box, text=COLLEGE_NAME,
            bg="#122541", fg="#FFFFFF",
            font=("Segoe UI", 15, "bold")
        ).pack(anchor="w")

        tk.Label(
            title_box, text="STUDENT MANAGEMENT SYSTEM",
            bg="#122541", fg="#50DED5",
            font=("Segoe UI", 9, "bold")
        ).pack(anchor="w", pady=(3, 0))

        tk.Label(
            title_box, text=COLLEGE_TAGLINE,
            bg="#122541", fg="#AFC2D9",
            font=("Segoe UI", 8)
        ).pack(anchor="w", pady=(3, 0))

        right_header = tk.Frame(self.header, bg="#122541")
        right_header.pack(side="right", padx=20, pady=12)

        tk.Label(
            right_header, text="CAMPUS PORTAL",
            bg="#122541", fg="#8CA6C2",
            font=("Segoe UI", 8, "bold")
        ).pack(anchor="e")

        self.clock_label = tk.Label(
            right_header, text="", bg="#122541", fg="#65E4DC",
            font=("Consolas", 15, "bold")
        )
        self.clock_label.pack(anchor="e", pady=(3, 0))

        self.date_label = tk.Label(
            right_header, text="", bg="#122541", fg="#B8C7DA",
            font=("Segoe UI", 8)
        )
        self.date_label.pack(anchor="e", pady=(2, 0))

        # Two-column content area
        self.content = tk.Frame(self.shell, bg="#0B1730", bd=0)
        self.content.pack(fill="both", expand=True, padx=16)

        self.welcome = tk.Frame(
            self.content, bg="#142B4B", width=430,
            highlightthickness=1, highlightbackground="#345273"
        )
        self.welcome.pack(
            side="left", fill="both", expand=True, padx=(0, 15)
        )
        self.welcome.pack_propagate(False)

        # Decorative accent at the top of welcome panel
        tk.Frame(self.welcome, bg="#35D0C8", height=4).pack(fill="x")

        welcome_inner = tk.Frame(self.welcome, bg="#142B4B")
        welcome_inner.pack(fill="both", expand=True, padx=34, pady=25)

        tk.Label(
            welcome_inner, text="WELCOME TO YOUR CAMPUS",
            bg="#142B4B", fg="#62E4DC",
            font=("Segoe UI", 9, "bold")
        ).pack(anchor="w", pady=(8, 12))

        tk.Label(
            welcome_inner, text="YOUR FUTURE\nSTARTS HERE.",
            bg="#142B4B", fg="#FFFFFF", justify="left",
            font=("Segoe UI", 31, "bold")
        ).pack(anchor="w", pady=(0, 12))

        tk.Label(
            welcome_inner,
            text="Everything you need to manage your academic journey, all in one secure place.",
            bg="#142B4B", fg="#C5D5E8", justify="left",
            wraplength=340, font=("Segoe UI", 10)
        ).pack(anchor="w", pady=(0, 17))

        # Compact feature cards
        self._feature_row(
            welcome_inner, "01", "Student-first access",
            "Academic profile and student services in one place."
        )
        self._feature_row(
            welcome_inner, "02", "Protected accounts",
            "Secure password storage and account recovery."
        )
        self._feature_row(
            welcome_inner, "03", "Connected campus",
            "Dedicated access for students and institutional staff."
        )

        tk.Frame(
            welcome_inner, bg="#385473", height=1
        ).pack(fill="x", pady=(17, 12))

        tk.Label(
            welcome_inner, text="LEARN  •  CONNECT  •  ACHIEVE",
            bg="#142B4B", fg="#62E4DC",
            font=("Segoe UI", 9, "bold")
        ).pack(anchor="w")

        # Authentication card
        self.auth_card = tk.Frame(
            self.content, bg="#FFFFFF", width=475,
            highlightthickness=1, highlightbackground="#DCE6F2"
        )
        self.auth_card.pack(side="right", fill="both")
        self.auth_card.pack_propagate(False)

        tk.Frame(self.auth_card, bg="#2563EB", height=5).pack(fill="x")
        self._build_auth_card()

        self.footer = tk.Label(
            self.shell,
            text="© {} {}     •     SECURE STUDENT PORTAL".format(
                datetime.datetime.now().year, COLLEGE_NAME.title()
            ),
            bg="#122541", fg="#B9C9DC",
            font=("Segoe UI", 8, "bold"), pady=9
        )
        self.footer.pack(fill="x", padx=16, pady=(12, 12))

        self._adapt_layout()

    def _feature_row(self, parent, number, heading, detail):
        row = tk.Frame(
            parent, bg="#1B385C",
            highlightthickness=1, highlightbackground="#294969"
        )
        row.pack(fill="x", pady=6)

        number_box = tk.Frame(
            row, bg="#24517B", width=42, height=42
        )
        number_box.pack(side="left", padx=10, pady=9)
        number_box.pack_propagate(False)

        tk.Label(
            number_box, text=number, bg="#24517B", fg="#70E7DF",
            font=("Segoe UI", 10, "bold")
        ).pack(expand=True)

        text_box = tk.Frame(row, bg="#1B385C")
        text_box.pack(
            side="left", fill="x", expand=True, padx=(2, 10), pady=8
        )

        tk.Label(
            text_box, text=heading, bg="#1B385C", fg="#FFFFFF",
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w")

        tk.Label(
            text_box, text=detail, bg="#1B385C", fg="#B7C9DE",
            font=("Segoe UI", 8), wraplength=285, justify="left"
        ).pack(anchor="w", pady=(3, 0))

    def _adapt_layout(self):
        width = self.winfo_width()

        if width < 980:
            if self.welcome.winfo_manager():
                self.welcome.pack_forget()

            if not self.auth_card.winfo_manager():
                self.auth_card.pack(
                    side="left", fill="both", expand=True
                )

            self.auth_card.configure(width=600)
        else:
            if not self.welcome.winfo_manager():
                self.welcome.pack(
                    side="left", fill="both", expand=True,
                    padx=(0, 15), before=self.auth_card
                )
            self.auth_card.configure(width=475)

    def _build_auth_card(self):
        heading = tk.Frame(self.auth_card, bg="#FFFFFF")
        heading.pack(fill="x", padx=29, pady=(23, 2))

        tk.Label(
            heading, text="Welcome back",
            bg="#FFFFFF", fg="#14243A",
            font=("Segoe UI", 22, "bold")
        ).pack(anchor="w")

        tk.Label(
            heading,
            text="Access your student and campus account.",
            bg="#FFFFFF", fg="#718096",
            font=("Segoe UI", 9)
        ).pack(anchor="w", pady=(4, 0))

        # Tab navigation
        self.tabs_frame = tk.Frame(
            self.auth_card, bg="#F0F4FA",
            highlightthickness=1, highlightbackground="#E1E8F1"
        )
        self.tabs_frame.pack(fill="x", padx=25, pady=(18, 10))

        self.tab_buttons = {}
        tabs = [
            ("signin", "Sign in"),
            ("signup", "Register"),
            ("change", "Change"),
            ("forgot", "Forgot"),
        ]

        for key, label in tabs:
            button = tk.Button(
                self.tabs_frame, text=label,
                command=lambda selected=key: self.show_tab(selected),
                bd=0, relief="flat", cursor="hand2",
                bg="#F0F4FA", fg="#718096",
                activebackground="#FFFFFF",
                activeforeground="#2563EB",
                font=("Segoe UI", 8, "bold"),
                padx=4, pady=12
            )
            button.pack(side="left", expand=True, fill="x", padx=2, pady=2)
            self.tab_buttons[key] = button

        self.active_line = tk.Frame(
            self.auth_card, bg="#2563EB", height=2
        )
        self.active_line.pack(fill="x", padx=25)

        # Scrollable form area
        form_area = tk.Frame(self.auth_card, bg="#FFFFFF")
        form_area.pack(fill="both", expand=True, padx=(25, 12), pady=(8, 0))

        self.form_canvas = tk.Canvas(
            form_area, bg="#FFFFFF", highlightthickness=0, bd=0
        )
        self.form_scroll = tk.Scrollbar(
            form_area, orient="vertical", command=self.form_canvas.yview,
            relief="flat", bd=0, width=8
        )
        self.form_canvas.configure(
            yscrollcommand=self.form_scroll.set
        )
        self.form_canvas.pack(side="left", fill="both", expand=True)
        self.form_scroll.pack(side="right", fill="y", padx=(5, 0))

        self.form_frame = tk.Frame(self.form_canvas, bg="#FFFFFF")
        self.form_window = self.form_canvas.create_window(
            (0, 0), window=self.form_frame, anchor="nw"
        )
        self.form_frame.bind(
            "<Configure>", self._update_scroll_region
        )
        self.form_canvas.bind(
            "<Configure>", self._resize_form_width
        )
        self._bind_scroll()

        self.status_label = tk.Label(
            self.auth_card, textvariable=self.status_text,
            bg="#F7F9FC", fg="#718096",
            font=("Segoe UI", 8, "bold"),
            justify="left", anchor="w", wraplength=420,
            padx=12, pady=9
        )
        self.status_label.pack(
            side="bottom", fill="x", padx=25, pady=(6, 15)
        )

        self.show_tab("signin")

    def _update_scroll_region(self, _event=None):
        self.form_canvas.configure(scrollregion=self.form_canvas.bbox("all"))

    def _resize_form_width(self, event):
        self.form_canvas.itemconfigure(self.form_window, width=event.width)


    def _bind_scroll(self):

        for sequence in SCROLL_SEQUENCES:
            try:
                self.form_canvas.bind_all(sequence, self._on_scroll)
            except Exception:
                pass

    def _on_scroll(self, event):
        try:
            if not self.form_canvas.winfo_exists():
                return "break"

            num = getattr(event, "num", None)
            if num == 4:
                step = -1
            elif num == 5:
                step = 1
            else:
                delta = getattr(event, "delta", 0)
                if delta == 0:
                    return "break"

                self._scroll_acc += delta
                threshold = 120 if abs(delta) >= 120 else 40
                step = int(-self._scroll_acc / threshold)
                if step == 0:
                    if abs(self._scroll_acc) >= threshold:
                        step = -1 if self._scroll_acc > 0 else 1
                        self._scroll_acc = 0
                    else:
                        return "break"
                else:
                    self._scroll_acc = 0

            self.form_canvas.yview_scroll(int(step), "units")
            return "break"
        except Exception:
            return "break"


    def _load_logo(self):
        """Load LOGO_PATH from a local file or a URL (fallback = ✦ mark)."""
        if not LOGO_PATH or not PIL_OK:
            return
        try:
            if LOGO_PATH.lower().startswith(("http://", "https://")):
                threading.Thread(target=self._fetch_logo, daemon=True).start()
            elif os.path.isfile(LOGO_PATH):
                self._set_logo_image(Image.open(LOGO_PATH))
        except Exception:
            pass

    def _fetch_logo(self):
        try:
            request = urllib.request.Request(
                LOGO_PATH, headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(request, timeout=7) as response:
                raw = response.read()
            image = Image.open(io.BytesIO(raw))
            if self.alive:
                self.after(0, lambda img=image: self._set_logo_image(img))
        except Exception:
            pass

    def _set_logo_image(self, image):
        try:
            image = image.convert("RGBA")
            image.thumbnail((48, 48), Image.Resampling.LANCZOS)
            self.logo_photo = ImageTk.PhotoImage(image)
            self.logo_label.configure(image=self.logo_photo, text="")
        except Exception:
            pass


    def _clear_form(self):
        for child in self.form_frame.winfo_children():
            child.destroy()
        self.form_vars = {}
        self._scroll_acc = 0
        self.form_canvas.yview_moveto(0)

    def _field(self, key, label, placeholder="", secret=False):
        group = tk.Frame(self.form_frame, bg="#FFFFFF")
        group.pack(fill="x", pady=(8, 5))

        tk.Label(
            group, text=label.upper(),
            bg="#FFFFFF", fg="#52647B",
            font=("Segoe UI", 8, "bold")
        ).pack(anchor="w", pady=(0, 6))

        entry_shell = tk.Frame(
            group, bg="#F7F9FC",
            highlightthickness=1,
            highlightbackground="#DCE5F0",
            highlightcolor="#2563EB"
        )
        entry_shell.pack(fill="x")

        entry = tk.Entry(
            entry_shell, bg="#F7F9FC", fg="#17243A",
            insertbackground="#2563EB",
            relief="flat", bd=0,
            font=("Segoe UI", 10),
            show="●" if secret else ""
        )
        entry.pack(fill="x", padx=14, pady=12, ipady=2)

        def focus_in(_event=None, shell=entry_shell):
            shell.configure(
                bg="#EFF6FF",
                highlightbackground="#2563EB",
                highlightcolor="#2563EB"
            )
            entry.configure(bg="#EFF6FF")

        def focus_out(_event=None, shell=entry_shell):
            shell.configure(
                bg="#F7F9FC",
                highlightbackground="#DCE5F0",
                highlightcolor="#2563EB"
            )
            entry.configure(bg="#F7F9FC")

        entry.bind("<FocusIn>", focus_in)
        entry.bind("<FocusOut>", focus_out)

        if placeholder:
            entry.insert(0, placeholder)
            entry.configure(fg="#9AA7B8")
            entry.bind(
                "<FocusIn>",
                lambda _e, w=entry, p=placeholder:
                self._remove_placeholder(w, p),
                add="+"
            )
            entry.bind(
                "<FocusOut>",
                lambda _e, w=entry, p=placeholder:
                self._restore_placeholder(w, p),
                add="+"
            )

        self.form_vars[key] = entry
        return entry

    @staticmethod
    def _remove_placeholder(entry, placeholder):
        if entry.get() == placeholder:
            entry.delete(0, "end")
            entry.configure(fg=INK)

    @staticmethod
    def _restore_placeholder(entry, placeholder):
        if not entry.get():
            entry.insert(0, placeholder)
            entry.configure(fg="#9AA7B8")

    def _value(self, key):
        widget = self.form_vars[key]
        value = widget.get().strip()
        if widget.cget("fg") == "#9AA7B8":
            return ""
        return value

    def _primary_button(self, label, callback):
        button = tk.Button(
            self.form_frame, text=label, command=callback,
            bg="#2563EB", fg="#FFFFFF",
            activebackground="#1D4ED8",
            activeforeground="#FFFFFF",
            bd=0, relief="flat", cursor="hand2",
            font=("Segoe UI", 10, "bold"),
            pady=13
        )
        button.pack(fill="x", pady=(19, 10))

        button.bind(
            "<Enter>",
            lambda _e: button.configure(bg="#1D4ED8")
        )
        button.bind(
            "<Leave>",
            lambda _e: button.configure(bg="#2563EB")
        )
        button.bind(
            "<ButtonPress-1>",
            lambda _e: button.configure(bg="#1746A2")
        )
        button.bind(
            "<ButtonRelease-1>",
            lambda _e: button.configure(bg="#1D4ED8")
        )

    def _set_status(self, message="", kind="info"):
        self.status_text.set(message)
        colors = {
            "error": "#C62828",
            "success": "#168653",
            "info": "#718096"
        }
        self.status_label.configure(
            fg=colors.get(kind, "#718096"),
            bg="#FFF4F3" if kind == "error"
               else "#EFFAF4" if kind == "success"
               else "#F7F9FC"
        )

    def show_tab(self, key):
        self.current_tab = key

        for name, button in self.tab_buttons.items():
            selected = name == key
            button.configure(
                bg="#FFFFFF" if selected else "#F0F4FA",
                fg="#2563EB" if selected else "#718096",
                activebackground="#FFFFFF" if selected else "#F0F4FA",
                activeforeground="#2563EB"
            )

        self._set_status("")
        self._clear_form()

        forms = {
            "signin": self._form_signin,
            "signup": self._form_signup,
            "change": self._form_change,
            "forgot": self._form_forgot,
        }

        try:
            forms[key]()
            self.form_canvas.yview_moveto(0)
        except Exception as exc:
            traceback.print_exc()
            self._set_status(
                "Could not open this form: " + str(exc), "error"
            )

    def _form_signin(self):
        self._field("email", "Email address", "name@example.com")
        self._field("password", "Password", secret=True)
        self._primary_button("SIGN IN  →", self._sign_in)
        tk.Label(
            self.form_frame, text="Demo principal: principal@school.edu",
            bg=PANEL, fg=MUTED, font=("Segoe UI", 8)
        ).pack(anchor="w", pady=(2, 0))
        tk.Label(
            self.form_frame, text="Demo password: Admin@123",
            bg=PANEL, fg=MUTED, font=("Segoe UI", 8)
        ).pack(anchor="w", pady=(2, 0))

    def _form_signup(self):
        self._field("name", "Full name", "Your full name")
        self._field("idcard", "ID card number", "Alphanumeric ID")
        category_row = tk.Frame(self.form_frame, bg=PANEL)
        category_row.pack(fill="x", pady=(9, 5))
        tk.Label(
            category_row, text="ACCOUNT TYPE", bg=PANEL, fg="#53647A",
            font=("Segoe UI", 8, "bold")
        ).pack(anchor="w", pady=(0, 5))
        choices = tk.Frame(category_row, bg=PANEL)
        choices.pack(anchor="w")
        for category in CATEGORIES:
            tk.Radiobutton(
                choices, text=category.title(), value=category,
                variable=self.category, command=self._refresh_category_fields,
                bg=PANEL, fg=INK, selectcolor="#E7F0FF",
                activebackground=PANEL, activeforeground=ACCENT,
                font=("Segoe UI", 9)
            ).pack(side="left", padx=(0, 12))

        self.category_fields = tk.Frame(self.form_frame, bg=PANEL)
        self.category_fields.pack(fill="x")
        self._refresh_category_fields()

        self._field("gender", "Gender (M / F / O)", "M, F or O")
        self._field("dob", "Date of birth", "YYYY-MM-DD")
        self._field("mobile", "Mobile number", "10-digit mobile number")
        self._field("email", "Email address", "name@example.com")
        self._field("password", "Password", secret=True)
        self._field("confirm", "Confirm password", secret=True)
        self._primary_button("CREATE ACCOUNT  →", self._sign_up)
        tk.Label(
            self.form_frame,
            text="A unique username is generated automatically. Password: 8+ characters, with a letter and a number.",
            bg=PANEL, fg=MUTED, wraplength=390, justify="left",
            font=("Segoe UI", 8)
        ).pack(anchor="w", pady=(0, 12))

    def _refresh_category_fields(self):
        if not hasattr(self, "category_fields"):
            return
        for child in self.category_fields.winfo_children():
            child.destroy()

        self.category_vars = {}
        category = self.category.get()
        fields = []
        if category == "student":
            fields = [("roll", "Roll number"), ("branch", "Branch"),
                      ("semester", "Semester")]
        elif category == "teacher":
            fields = [("department", "Department"), ("subject", "Subject")]
        for key, label in fields:
            group = tk.Frame(self.category_fields, bg="#FFFFFF")
            group.pack(fill="x", pady=(5, 4))
            tk.Label(
                group, text=label.upper(), bg="#FFFFFF", fg="#52647B",
                font=("Segoe UI", 8, "bold")
            ).pack(anchor="w", pady=(0, 5))
            shell = tk.Frame(
                group, bg="#F7F9FC", highlightthickness=1,
                highlightbackground="#DCE5F0"
            )
            shell.pack(fill="x")
            entry = tk.Entry(
                shell, bg="#F7F9FC", fg="#17243A", insertbackground="#2563EB",
                relief="flat", bd=0, font=("Segoe UI", 10)
            )
            entry.pack(fill="x", padx=12, pady=10, ipady=2)
            self.category_vars[key] = entry

    def _form_change(self):
        self._field("email", "Registered email", "name@example.com")
        self._field("old", "Current password", secret=True)
        self._field("password", "New password", secret=True)
        self._field("confirm", "Confirm new password", secret=True)
        self._primary_button("UPDATE PASSWORD", self._change_password)

    def _form_forgot(self):
        tk.Label(
            self.form_frame,
            text="Enter your registered email and ID card number to verify your account.",
            bg=PANEL, fg=MUTED, wraplength=390, justify="left",
            font=("Segoe UI", 9)
        ).pack(anchor="w", pady=(0, 8))
        self._field("email", "Registered email", "name@example.com")
        self._field("idcard", "ID card number")
        self._field("password", "New password", secret=True)
        self._field("confirm", "Confirm new password", secret=True)
        self._primary_button("RESET PASSWORD", self._reset_password)


    def _validate_new_password(self, password, confirm):
        if not PASSWORD_RE.match(password):
            self._set_status(
                "Password needs 8+ characters, at least one letter and one number.",
                "error"
            )
            return False
        if password != confirm:
            self._set_status("Passwords do not match.", "error")
            return False
        return True

    def _database_ready(self):
        if not self.mongo_online:
            self._set_status(
                "MongoDB is not connected. Start MongoDB and restart this application. No account has been saved.",
                "error"
            )
            return False
        return True

    def _show_success(self, title, message):
        self._set_status(message, "success")
        try:
            messagebox.showinfo(title, message, parent=self)
        except Exception:
            pass

    def _show_failure(self, title, message):
        self._set_status(message, "error")
        try:
            messagebox.showerror(title, message, parent=self)
        except Exception:
            pass

    def _sign_up(self):
        if self.auth_busy:
            return self._set_status("Please wait. Your previous request is still being processed.", "error")
        if not self._database_ready():
            return

        self.auth_busy = True
        try:
            name = self._value("name")
            idcard = self._value("idcard").strip()
            gender = self._value("gender").upper()[:1]
            dob = self._value("dob")
            mobile = re.sub(r"\\s+", "", self._value("mobile"))
            email = self._value("email").lower().strip()
            password = self.form_vars["password"].get()
            confirm = self.form_vars["confirm"].get()
            category = self.category.get()

            if len(name) < 2:
                return self._set_status("Full name is required (at least 2 characters).", "error")
            if not ID_RE.fullmatch(idcard):
                return self._set_status("Invalid ID card: use 4–20 letters or digits only.", "error")
            if gender not in ("M", "F", "O"):
                return self._set_status("Select a valid gender: M, F or O.", "error")
            if not valid_date(dob):
                return self._set_status("Invalid date of birth. Use YYYY-MM-DD, DD-MM-YYYY or DD/MM/YYYY.", "error")
            if not MOBILE_RE.fullmatch(mobile):
                return self._set_status("Invalid mobile number. Enter a 10-digit Indian mobile number starting with 6–9.", "error")
            if not EMAIL_RE.fullmatch(email):
                return self._set_status("Invalid email address. Example: name@example.com.", "error")
            if category not in CATEGORIES:
                return self._set_status("Please select a valid account type.", "error")
            if not self._validate_new_password(password, confirm):
                return

            extra = {}
            for key, widget in getattr(self, "category_vars", {}).items():
                extra[key] = widget.get().strip()
            if any(not value for value in extra.values()):
                return self._set_status("Complete every required field for the selected account type.", "error")

            if self.db.find_one({"email": email}):
                return self._set_status("This email address is already registered. Use Sign in or Forgot password.", "error")
            if self.db.find_one({"idcard": idcard}):
                return self._set_status("This ID card number is already linked to another account.", "error")
            if self.db.find_one({"mobile": mobile}):
                return self._set_status("This mobile number is already registered.", "error")

            username = make_username(email, self.db)
            document = {
                "name": name,
                "username": username,
                "idcard": idcard,
                "gender": gender,
                "dob": dob,
                "mobile": mobile,
                "email": email,
                "category": category,
                "password": hash_password(password),
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "account_status": "active",
                **extra
            }

            result = self.db.insert_one(document)
            if not getattr(result, "acknowledged", True):
                return self._set_status("MongoDB did not acknowledge the registration. The account may not have been saved.", "error")

            self.show_tab("signin")
            self.form_vars["email"].delete(0, "end")
            self.form_vars["email"].insert(0, email)
            success_message = (
                f"Account created successfully!\n\n"
                f"Name: {name}\nUsername: {username}\nEmail: {email}\n"
                f"Account type: {category.title()}\n\n"
                f"You can now sign in using your email and password."
            )
            self._show_success("Account created successfully", success_message)

        except Exception as exc:
            traceback.print_exc()
            error_name = type(exc).__name__.lower()
            error_text = str(exc).lower()
            if "duplicatekey" in error_name or "e11000" in error_text:
                detail = "A duplicate value was rejected by MongoDB. Check whether this email, username, ID card or mobile number is already registered. If this continues, inspect the users collection's unique indexes."
            elif "serverselection" in error_name or "connection" in error_name or "timeout" in error_name:
                detail = "MongoDB connection failed during registration. Start MongoDB and verify MONGO_URI."
            else:
                detail = f"Registration failed ({type(exc).__name__}): {self._safe_error(exc)}"
            self._show_failure("Account creation failed", detail)
        finally:
            self.auth_busy = False

    def _sign_in(self):
        if self.dashboard_opening:
            return self._set_status("A dashboard session is already being opened. Please wait.", "error")
        if self.auth_busy:
            return self._set_status("Please wait. Your previous request is still being processed.", "error")
        if not self._database_ready():
            return

        self.auth_busy = True
        try:
            email = self._value("email").lower().strip()
            password = self.form_vars["password"].get()

            if not EMAIL_RE.fullmatch(email):
                return self._set_status("Enter a valid registered email address.", "error")
            if not password:
                return self._set_status("Password is required.", "error")

            now = datetime.datetime.now().timestamp()
            locked_until = self.login_locked_until.get(email, 0)
            if now < locked_until:
                remaining = max(1, int(locked_until - now))
                return self._set_status(f"Too many failed attempts. Try again in {remaining} seconds.", "error")

            user = self.db.find_one({"email": email})
            if not user:
                failures = self.login_failures.get(email, 0) + 1
                self.login_failures[email] = failures
                if failures >= 5:
                    self.login_locked_until[email] = now + 60
                    self.login_failures[email] = 0
                    return self._set_status("Account temporarily locked after 5 failed attempts. Try again in 60 seconds.", "error")
                return self._set_status(f"No account found for this email. Check the email or create an account. Attempt {failures}/5.", "error")

            if user.get("account_status", "active") != "active":
                return self._set_status("This account is disabled. Contact the campus administrator.", "error")

            if not verify_password(password, user.get("password", {})):
                failures = self.login_failures.get(email, 0) + 1
                self.login_failures[email] = failures
                if failures >= 5:
                    self.login_locked_until[email] = now + 60
                    self.login_failures[email] = 0
                    return self._set_status("Too many incorrect passwords. Login is locked for 60 seconds.", "error")
                return self._set_status(f"Incorrect password. Please try again. Attempt {failures}/5.", "error")

            self.login_failures.pop(email, None)
            self.login_locked_until.pop(email, None)
            account = dict(user)
            account.pop("password", None)
            account.pop("_id", None)
            self.dashboard_opening = True
            self._set_status("Login successful. Opening your dashboard…", "success")
            try:
                messagebox.showinfo(
                    "Login successful",
                    f"Welcome, {user.get('name', 'User')}!\nYou are signed in as {user.get('category', 'user').title()}.",
                    parent=self
                )
            except Exception:
                pass
            self.after(250, self._open_dashboard, account)

        except Exception as exc:
            traceback.print_exc()
            error_name = type(exc).__name__.lower()
            if "serverselection" in error_name or "connection" in error_name or "timeout" in error_name:
                detail = "Cannot reach MongoDB. Check that the MongoDB service is running."
            else:
                detail = f"Login failed ({type(exc).__name__}): {self._safe_error(exc)}"
            self._show_failure("Sign-in failed", detail)
        finally:
            self.auth_busy = False

    def _change_password(self):
        if not self._database_ready():
            return
        try:
            email = self._value("email").lower().strip()
            old = self.form_vars["old"].get()
            password = self.form_vars["password"].get()
            confirm = self.form_vars["confirm"].get()
            if not EMAIL_RE.fullmatch(email):
                return self._set_status("Enter a valid registered email address.", "error")
            if not old:
                return self._set_status("Enter your current password.", "error")
            user = self.db.find_one({"email": email})
            if not user:
                return self._set_status("No account exists with this email address.", "error")
            if not verify_password(old, user.get("password", {})):
                return self._set_status("Current password is incorrect. Nothing was changed.", "error")
            if not self._validate_new_password(password, confirm):
                return
            result = self.db.update_one(
                {"email": email}, {"$set": {"password": hash_password(password),
                "password_updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}}
            )
            if getattr(result, "matched_count", 1) == 0:
                return self._set_status("Account was not found during update. Please retry.", "error")
            self.show_tab("signin")
            self._show_success("Password updated", "Your password was updated successfully. Sign in with your new password.")
        except Exception as exc:
            traceback.print_exc()
            self._show_failure("Password update failed", f"{type(exc).__name__}: {self._safe_error(exc)}")

    def _reset_password(self):
        if not self._database_ready():
            return
        try:
            email = self._value("email").lower().strip()
            idcard = self._value("idcard").strip()
            password = self.form_vars["password"].get()
            confirm = self.form_vars["confirm"].get()
            if not EMAIL_RE.fullmatch(email) or not idcard:
                return self._set_status("Enter both a valid registered email and your ID card number.", "error")
            user = self.db.find_one({"email": email})
            if not user:
                return self._set_status("No account exists with this email address.", "error")
            if not secrets.compare_digest(str(user.get("idcard", "")).lower(), idcard.lower()):
                return self._set_status("ID card verification failed. Check the ID card number.", "error")
            if not self._validate_new_password(password, confirm):
                return
            result = self.db.update_one(
                {"email": email}, {"$set": {"password": hash_password(password),
                "password_updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}}
            )
            if getattr(result, "matched_count", 1) == 0:
                return self._set_status("Account was not found during reset. Please retry.", "error")
            self.show_tab("signin")
            self._show_success("Password reset successful", "Your password has been reset. You can now sign in.")
        except Exception as exc:
            traceback.print_exc()
            self._show_failure("Password reset failed", f"{type(exc).__name__}: {self._safe_error(exc)}")

    @staticmethod
    def _safe_error(error):
        message = str(error).strip().replace("\n", " ")
        return message[:220] if message else "Please try again."


    def _open_dashboard(self, user):
        try:
            import dashboard
            dashboard.launch(user, app=self)
        except Exception:
            self.dashboard_opening = False
            traceback.print_exc()
            messagebox.showwarning(
                "Dashboard unavailable",
                "Authentication succeeded, but dashboard.py could not be opened.\n\n"
                "Check that dashboard.py is in the same project folder and that "
                "it defines launch(user, app=self)."
            )


    def _update_clock(self):
        if not self.alive:
            return
        now = datetime.datetime.now()
        self.clock_label.configure(text=now.strftime("%I:%M:%S %p"))
        self.date_label.configure(text=now.strftime("%A, %d %B %Y"))
        self.after(1000, self._update_clock)

    def _close(self):
        self.alive = False
        for sequence in SCROLL_SEQUENCES:
            try:
                self.form_canvas.unbind_all(sequence)
            except Exception:
                pass
        try:
            if self.mongo_client:
                self.mongo_client.close()
        except Exception:
            pass
        self.destroy()



def main():
    try:

        from splash_screen import splash_screen


        splash_root = tk.Tk()


        splash_screen(splash_root)


        splash_root.mainloop()


        app = StudentPortal()
        app.mainloop()

    except Exception:
        details = traceback.format_exc()
        print(details)

        try:
            messagebox.showerror(
                "Application error",
                details[-1800:]
            )
        except Exception:
            pass


if __name__ == "__main__":
    main()
