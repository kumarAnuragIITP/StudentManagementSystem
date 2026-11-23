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

# ----------------------------- Optional dependencies -------------------------
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


# -------------------------------- Configuration -------------------------------
COLLEGE_NAME = "GOVERNMENT POLYTECHNIC CHAPRA"
COLLEGE_TAGLINE = "A smarter, safer campus experience"

APP_TITLE = f"Student Management System | {COLLEGE_NAME.title()}"
MONGO_URI = "mongodb://localhost:27017"
DATABASE_NAME = "student_management"
USERS_COLLECTION = "users"

# ---------------------------------------------------------------- COLLEGE LOGO
# >>> Replace this DEMO link with your college logo (local path OR image URL).
#     Examples:
#         LOGO_PATH = r"C:\college\gpr_logo.jpg"
#         LOGO_PATH = "https://your-site.edu/logo.png"
#     Leave blank ("") to keep the built-in ✦ mark.
LOGO_PATH = "C:\\Users\\kanur\\PycharmProjects\\VWSP\\PythonProject\\images\\gpc.png"

# A single student/campus-themed photograph. If internet/Pillow is unavailable,
# the app uses ONLY the gradient fallback (never both backgrounds together).
BACKGROUND_URL = (
    "https://images.unsplash.com/photo-1523240795612-9a054b0db644"
    "?auto=format&fit=crop&w=2200&q=85"
)

# Palette
NAVY = "#101B32"
NAVY_2 = "#172744"
NAVY_3 = "#203657"
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
CATEGORIES = ("student", "teacher", "principal")

SCROLL_SEQUENCES = ("<MouseWheel>", "<Button-4>", "<Button-5>", "<Shift-MouseWheel>")


# --------------------------------- Data helpers --------------------------------
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


def valid_date(value):
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            datetime.datetime.strptime(value, fmt)
            return True
        except ValueError:
            continue
    return False


class MemoryUsers:
    """Small Mongo-like fallback used only when MongoDB is unavailable."""
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
    if MONGO_OK:
        try:
            client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=1800)
            client.admin.command("ping")
            collection = client[DATABASE_NAME][USERS_COLLECTION]
            collection.create_index("email", unique=True)
            return collection, True, client
        except Exception:
            pass
    return MemoryUsers(), False, None


# -------------------------------- Main application -----------------------------
class StudentPortal(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1240x820")
        self.minsize(900, 680)
        self.configure(bg=NAVY)

        self.db, self.mongo_online, self.mongo_client = connect_database()
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
        self._scroll_acc = 0.0          # trackpad delta accumulator

        self._build_background()
        self._build_interface()
        self._seed_demo_user()
        self._update_clock()
        self.protocol("WM_DELETE_WINDOW", self._close)

        # Fetch image away from the Tk main thread. The canvas starts with one
        # fallback background and is replaced atomically after a successful fetch.
        if PIL_OK:
            threading.Thread(target=self._download_background, daemon=True).start()

    # ------------------------------- Background --------------------------------
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
            # Keep the existing gradient. No second background layer is created.
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

        # Delete the previous background completely before drawing a new one.
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
                # One translucent dark overlay over the photograph.
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
        # A clean, single fallback background (not layered with an online image).
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

    # -------------------------------- Main layout -------------------------------
    def _build_interface(self):
        self.shell = tk.Frame(self, bg=NAVY, bd=0)
        self.shell.place(relx=0.5, rely=0.5, anchor="center",
                         relwidth=0.94, relheight=0.92)

        self.header = tk.Frame(self.shell, bg="#14243D",
                               highlightthickness=1,
                               highlightbackground="#40516B")
        self.header.pack(fill="x", pady=(0, 18))

        left_header = tk.Frame(self.header, bg="#14243D")
        left_header.pack(side="left", padx=22, pady=14)

        # ---- COLLEGE LOGO SLOT (loads LOGO_PATH, falls back to ✦) ----
        self.logo_area = tk.Frame(left_header, bg="#FFFFFF",
                                  width=52, height=52)
        self.logo_area.pack(side="left", padx=(0, 13))
        self.logo_area.pack_propagate(False)
        self.logo_label = tk.Label(
            self.logo_area, text="✦", bg="#FFFFFF", fg=ACCENT,
            font=("Segoe UI Symbol", 25, "bold")
        )
        self.logo_label.pack(expand=True, fill="both")
        self._load_logo()

        title_box = tk.Frame(left_header, bg="#14243D")
        title_box.pack(side="left")
        tk.Label(
            title_box, text=COLLEGE_NAME,
            bg="#14243D", fg=WHITE, font=("Segoe UI", 15, "bold")
        ).pack(anchor="w")
        tk.Label(
            title_box, text="STUDENT MANAGEMENT SYSTEM",
            bg="#14243D", fg="#8EDBD4", font=("Segoe UI", 9, "bold")
        ).pack(anchor="w", pady=(3, 0))
        tk.Label(
            title_box, text=COLLEGE_TAGLINE,
            bg="#14243D", fg="#B8C7DA", font=("Segoe UI", 8)
        ).pack(anchor="w", pady=(2, 0))

        right_header = tk.Frame(self.header, bg="#14243D")
        right_header.pack(side="right", padx=22, pady=12)
        self.clock_label = tk.Label(
            right_header, text="", bg="#14243D", fg="#8EDBD4",
            font=("Consolas", 13, "bold")
        )
        self.clock_label.pack(anchor="e")
        self.date_label = tk.Label(
            right_header, text="", bg="#14243D", fg="#B8C7DA",
            font=("Segoe UI", 8)
        )
        self.date_label.pack(anchor="e", pady=(2, 0))

        self.content = tk.Frame(self.shell, bg=NAVY, bd=0)
        self.content.pack(fill="both", expand=True)

        # Left welcome panel
        self.welcome = tk.Frame(
            self.content, bg="#172A48", width=430,
            highlightthickness=1, highlightbackground="#40516B"
        )
        self.welcome.pack(side="left", fill="both", expand=True, padx=(0, 16))
        self.welcome.pack_propagate(False)

        welcome_inner = tk.Frame(self.welcome, bg="#172A48")
        welcome_inner.pack(fill="both", expand=True, padx=38, pady=34)

        tk.Label(
            welcome_inner, text=COLLEGE_NAME,
            bg="#172A48", fg="#8EDBD4", font=("Segoe UI", 9, "bold")
        ).pack(anchor="w", pady=(18, 10))

        tk.Label(
            welcome_inner, text="YOUR FUTURE\nSTARTS HERE.",
            bg="#172A48", fg=WHITE, justify="left",
            font=("Segoe UI", 31, "bold")
        ).pack(anchor="w", pady=(0, 12))

        tk.Label(
            welcome_inner,
            text="One secure place for students, teachers and campus administrators.",
            bg="#172A48", fg="#C7D5E7", justify="left",
            wraplength=340, font=("Segoe UI", 11)
        ).pack(anchor="w", pady=(0, 26))

        self._feature_row(welcome_inner, "01", "Student-first access",
                          "Keep your academic profile in one place.")
        self._feature_row(welcome_inner, "02", "Protected accounts",
                          "Secure password storage and account recovery.")
        self._feature_row(welcome_inner, "03", "One campus community",
                          "Dedicated access for students and staff.")

        tk.Frame(welcome_inner, bg="#344967", height=1).pack(
            fill="x", pady=(24, 14)
        )
        tk.Label(
            welcome_inner, text="LEARN  •  CONNECT  •  ACHIEVE",
            bg="#172A48", fg="#8EDBD4",
            font=("Segoe UI", 9, "bold")
        ).pack(anchor="w")

        # Right authentication card
        self.auth_card = tk.Frame(
            self.content, bg=PANEL, width=470,
            highlightthickness=1, highlightbackground="#DCE5F0"
        )
        self.auth_card.pack(side="right", fill="both", padx=(0, 0))
        self.auth_card.pack_propagate(False)

        self._build_auth_card()

        self.footer = tk.Label(
            self.shell,
            text="© {} {}     •     Student Management System".format(
                datetime.datetime.now().year, COLLEGE_NAME.title()
            ),
            bg="#14243D", fg="#C1CDDC", font=("Segoe UI", 8), pady=9
        )
        self.footer.pack(fill="x", pady=(14, 0))

        self._adapt_layout()

    def _feature_row(self, parent, number, heading, detail):
        row = tk.Frame(parent, bg="#172A48")
        row.pack(fill="x", pady=9)
        number_box = tk.Frame(row, bg="#24466D", width=38, height=38)
        number_box.pack(side="left", padx=(0, 13))
        number_box.pack_propagate(False)
        tk.Label(
            number_box, text=number, bg="#24466D", fg="#8EDBD4",
            font=("Segoe UI", 9, "bold")
        ).pack(expand=True)
        text_box = tk.Frame(row, bg="#172A48")
        text_box.pack(side="left", fill="x", expand=True)
        tk.Label(
            text_box, text=heading, bg="#172A48", fg=WHITE,
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w")
        tk.Label(
            text_box, text=detail, bg="#172A48", fg="#B7C8DC",
            font=("Segoe UI", 8), wraplength=290, justify="left"
        ).pack(anchor="w", pady=(3, 0))

    def _adapt_layout(self):
        width = self.winfo_width()
        if width < 980:
            if self.welcome.winfo_manager():
                self.welcome.pack_forget()
            if not self.auth_card.winfo_manager():
                self.auth_card.pack(side="left", fill="both", expand=True)
            self.auth_card.configure(width=600)
        else:
            if not self.welcome.winfo_manager():
                self.welcome.pack(side="left", fill="both", expand=True,
                                  padx=(0, 16), before=self.auth_card)
            self.auth_card.configure(width=470)

    def _build_auth_card(self):
        heading = tk.Frame(self.auth_card, bg=PANEL)
        heading.pack(fill="x", padx=27, pady=(24, 3))
        tk.Label(
            heading, text="Welcome back",
            bg=PANEL, fg=INK, font=("Segoe UI", 21, "bold")
        ).pack(anchor="w")
        tk.Label(
            heading, text="Sign in or create your campus account below.",
            bg=PANEL, fg=MUTED, font=("Segoe UI", 9)
        ).pack(anchor="w", pady=(4, 0))

        self.tabs_frame = tk.Frame(self.auth_card, bg="#EDF2F8")
        self.tabs_frame.pack(fill="x", padx=25, pady=(18, 12))
        self.tab_buttons = {}
        tabs = [
            ("signin", "Sign in"),
            ("signup", "Register"),
            ("change", "Change password"),
            ("forgot", "Forgot password"),
        ]
        for key, label in tabs:
            button = tk.Button(
                self.tabs_frame, text=label,
                command=lambda selected=key: self.show_tab(selected),
                bd=0, relief="flat", cursor="hand2",
                bg="#EDF2F8", fg=MUTED,
                activebackground="#EDF2F8", activeforeground=ACCENT,
                font=("Segoe UI", 8, "bold"), padx=5, pady=11
            )
            button.pack(side="left", expand=True, fill="x")
            self.tab_buttons[key] = button

        self.active_line = tk.Frame(self.auth_card, bg=ACCENT, height=3)
        self.active_line.pack(fill="x", padx=25)

        # Scrollable form region: long registration forms never run off-screen.
        self.form_canvas = tk.Canvas(
            self.auth_card, bg=PANEL, highlightthickness=0, bd=0
        )
        self.form_scroll = tk.Scrollbar(
            self.auth_card, orient="vertical", command=self.form_canvas.yview
        )
        self.form_canvas.configure(yscrollcommand=self.form_scroll.set)
        self.form_canvas.pack(side="left", fill="both", expand=True,
                              padx=(25, 0), pady=(8, 0))
        self.form_scroll.pack(side="right", fill="y", padx=(0, 13), pady=(8, 0))

        self.form_frame = tk.Frame(self.form_canvas, bg=PANEL)
        self.form_window = self.form_canvas.create_window(
            (0, 0), window=self.form_frame, anchor="nw"
        )
        self.form_frame.bind("<Configure>", self._update_scroll_region)
        self.form_canvas.bind("<Configure>", self._resize_form_width)
        self._bind_scroll()

        self.status_label = tk.Label(
            self.auth_card, textvariable=self.status_text,
            bg=PANEL, fg=MUTED, font=("Segoe UI", 8),
            justify="left", anchor="w", wraplength=420
        )
        self.status_label.pack(side="bottom", fill="x", padx=27, pady=(5, 18))

        self.show_tab("signin")

    def _update_scroll_region(self, _event=None):
        self.form_canvas.configure(scrollregion=self.form_canvas.bbox("all"))

    def _resize_form_width(self, event):
        self.form_canvas.itemconfigure(self.form_window, width=event.width)

    # --------------------------- Scroll (mouse + trackpad) -----------------------
    def _bind_scroll(self):
        # MouseWheel covers Windows/macOS; Button-4/5 cover Linux/X11 trackpads.
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
            if num == 4:                      # Linux scroll up
                step = -1
            elif num == 5:                    # Linux scroll down
                step = 1
            else:
                delta = getattr(event, "delta", 0)
                if delta == 0:
                    return "break"
                # Trackpads send many tiny deltas; accumulate, then step.
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

    # ---------------------------------- Logo load --------------------------------
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

    # -------------------------------- Form widgets ------------------------------
    def _clear_form(self):
        for child in self.form_frame.winfo_children():
            child.destroy()
        self.form_vars = {}
        self._scroll_acc = 0
        self.form_canvas.yview_moveto(0)

    def _field(self, key, label, placeholder="", secret=False):
        group = tk.Frame(self.form_frame, bg=PANEL)
        group.pack(fill="x", pady=(5, 4))
        tk.Label(
            group, text=label.upper(), bg=PANEL, fg="#53647A",
            font=("Segoe UI", 8, "bold")
        ).pack(anchor="w", pady=(0, 5))

        entry_shell = tk.Frame(
            group, bg=FIELD, highlightthickness=1,
            highlightbackground=BORDER, highlightcolor=ACCENT
        )
        entry_shell.pack(fill="x")
        entry = tk.Entry(
            entry_shell, bg=FIELD, fg=INK, insertbackground=INK,
            relief="flat", bd=0, font=("Segoe UI", 10),
            show="●" if secret else ""
        )
        entry.pack(fill="x", padx=12, pady=10, ipady=2)
        if placeholder:
            entry.insert(0, placeholder)
            entry.configure(fg="#9AA7B8")
            entry.bind("<FocusIn>", lambda _e, w=entry, p=placeholder:
                       self._remove_placeholder(w, p))
            entry.bind("<FocusOut>", lambda _e, w=entry, p=placeholder:
                       self._restore_placeholder(w, p))
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
            bg=ACCENT, fg=WHITE, activebackground=ACCENT_HOVER,
            activeforeground=WHITE, bd=0, relief="flat",
            cursor="hand2", font=("Segoe UI", 10, "bold"),
            pady=12
        )
        button.pack(fill="x", pady=(17, 8))
        button.bind("<Enter>", lambda _e: button.configure(bg=ACCENT_HOVER))
        button.bind("<Leave>", lambda _e: button.configure(bg=ACCENT))

    def _set_status(self, message="", kind="info"):
        self.status_text.set(message)
        self.status_label.configure(
            fg={"error": DANGER, "success": SUCCESS}.get(kind, MUTED)
        )

    def show_tab(self, key):
        self.current_tab = key
        for name, button in self.tab_buttons.items():
            selected = name == key
            button.configure(
                bg="#FFFFFF" if selected else "#EDF2F8",
                fg=ACCENT if selected else MUTED
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
        except Exception as exc:
            traceback.print_exc()
            self._set_status("Could not open this form: " + str(exc), "error")

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
            text="Password must contain at least 8 characters, a letter and a number.",
            bg=PANEL, fg=MUTED, wraplength=390, justify="left",
            font=("Segoe UI", 8)
        ).pack(anchor="w", pady=(0, 12))

    def _refresh_category_fields(self):
        if not hasattr(self, "category_fields"):
            return
        for child in self.category_fields.winfo_children():
            child.destroy()
        # Keep the dynamic fields inside their own frame, not mixed with others.
        self.category_vars = {}
        category = self.category.get()
        fields = []
        if category == "student":
            fields = [("roll", "Roll number"), ("branch", "Branch"),
                      ("semester", "Semester")]
        elif category == "teacher":
            fields = [("department", "Department"), ("subject", "Subject")]
        for key, label in fields:
            group = tk.Frame(self.category_fields, bg=PANEL)
            group.pack(fill="x", pady=(5, 4))
            tk.Label(
                group, text=label.upper(), bg=PANEL, fg="#53647A",
                font=("Segoe UI", 8, "bold")
            ).pack(anchor="w", pady=(0, 5))
            shell = tk.Frame(
                group, bg=FIELD, highlightthickness=1,
                highlightbackground=BORDER
            )
            shell.pack(fill="x")
            entry = tk.Entry(
                shell, bg=FIELD, fg=INK, insertbackground=INK,
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

    # --------------------------------- Validation --------------------------------
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

    def _sign_up(self):
        try:
            name = self._value("name")
            idcard = self._value("idcard")
            gender = self._value("gender").upper()[:1]
            dob = self._value("dob")
            mobile = self._value("mobile")
            email = self._value("email").lower()
            password = self.form_vars["password"].get()
            confirm = self.form_vars["confirm"].get()
            category = self.category.get()

            if len(name) < 2:
                return self._set_status("Please enter your full name.", "error")
            if not ID_RE.match(idcard):
                return self._set_status("ID card must be 4–20 letters or digits.", "error")
            if gender not in ("M", "F", "O"):
                return self._set_status("Gender must be M, F or O.", "error")
            if not valid_date(dob):
                return self._set_status("Enter a valid DOB (YYYY-MM-DD).", "error")
            if not MOBILE_RE.match(mobile):
                return self._set_status("Enter a valid 10-digit Indian mobile number.", "error")
            if not EMAIL_RE.match(email):
                return self._set_status("Enter a valid email address.", "error")
            if not self._validate_new_password(password, confirm):
                return
            extra = {}
            for key, widget in getattr(self, "category_vars", {}).items():
                extra[key] = widget.get().strip()
            if any(not value for value in extra.values()):
                return self._set_status("Complete all fields for this account type.", "error")
            if self.db.find_one({"email": email}):
                return self._set_status("This email is already registered. Please sign in.", "error")

            document = {
                "name": name, "idcard": idcard, "gender": gender, "dob": dob,
                "mobile": mobile, "email": email, "category": category,
                "password": hash_password(password),
                "created_at": datetime.datetime.now().isoformat(),
                **extra
            }
            self.db.insert_one(document)
            self.show_tab("signin")
            self.form_vars["email"].delete(0, "end")
            self.form_vars["email"].insert(0, email)
            self._set_status(
                "Account created successfully. You can now sign in.", "success"
            )
        except Exception as exc:
            traceback.print_exc()
            self._set_status("Registration failed: " + self._safe_error(exc), "error")

    def _sign_in(self):
        try:
            email = self._value("email").lower()
            password = self.form_vars["password"].get()
            if not EMAIL_RE.match(email) or not password:
                return self._set_status("Enter a valid email and password.", "error")
            user = self.db.find_one({"email": email})
            if not user:
                return self._set_status("No account found with this email.", "error")
            if not verify_password(password, user.get("password", {})):
                return self._set_status("Incorrect password. Please try again.", "error")
            self._set_status("Signed in successfully. Opening your dashboard…", "success")
            self.after(350, lambda account=dict(user): self._open_dashboard(account))
        except Exception as exc:
            traceback.print_exc()
            self._set_status("Sign in failed: " + self._safe_error(exc), "error")

    def _change_password(self):
        try:
            email = self._value("email").lower()
            old = self.form_vars["old"].get()
            password = self.form_vars["password"].get()
            confirm = self.form_vars["confirm"].get()
            user = self.db.find_one({"email": email})
            if not user:
                return self._set_status("No account found with this email.", "error")
            if not verify_password(old, user.get("password", {})):
                return self._set_status("Current password is incorrect.", "error")
            if not self._validate_new_password(password, confirm):
                return
            self.db.update_one(
                {"email": email}, {"$set": {"password": hash_password(password)}}
            )
            self.show_tab("signin")
            self._set_status("Password updated. Please sign in again.", "success")
        except Exception as exc:
            traceback.print_exc()
            self._set_status("Could not update password: " + self._safe_error(exc), "error")

    def _reset_password(self):
        try:
            email = self._value("email").lower()
            idcard = self._value("idcard")
            password = self.form_vars["password"].get()
            confirm = self.form_vars["confirm"].get()
            user = self.db.find_one({"email": email})
            if not user:
                return self._set_status("No account found with this email.", "error")
            if str(user.get("idcard", "")).lower() != idcard.lower():
                return self._set_status("ID card verification failed.", "error")
            if not self._validate_new_password(password, confirm):
                return
            self.db.update_one(
                {"email": email}, {"$set": {"password": hash_password(password)}}
            )
            self.show_tab("signin")
            self._set_status("Password reset successfully. Please sign in.", "success")
        except Exception as exc:
            traceback.print_exc()
            self._set_status("Password reset failed: " + self._safe_error(exc), "error")

    @staticmethod
    def _safe_error(error):
        message = str(error).strip()
        return message[:160] if message else "Please try again."

    # --------------------------------- Dashboard ----------------------------------
    def _open_dashboard(self, user):
        try:
            import dashboard
            dashboard.launch(user, app=self)
        except Exception:
            traceback.print_exc()
            messagebox.showwarning(
                "Dashboard unavailable",
                "Authentication succeeded, but dashboard.py could not be opened.\n\n"
                "Check that dashboard.py is in the same project folder and that "
                "it defines launch(user, app=self)."
            )

    # ---------------------------------- Utilities --------------------------------
    def _seed_demo_user(self):
        try:
            if self.db.count_documents({}) == 0:
                self.db.insert_one({
                    "name": "Principal Demo",
                    "idcard": "ADMIN001",
                    "gender": "M",
                    "dob": "1980-01-01",
                    "mobile": "9876543210",
                    "email": "principal@school.edu",
                    "category": "principal",
                    "password": hash_password("Admin@123"),
                    "created_at": datetime.datetime.now().isoformat()
                })
        except Exception:
            # Duplicate/index/storage errors should not prevent the UI opening.
            pass

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
        # STEP 1: Import splash screen
        from splash_screen import splash_screen

        # STEP 2: Create splash window
        splash_root = tk.Tk()

        # STEP 3: Display splash screen
        splash_screen(splash_root)

        # STEP 4: Wait until splash screen closes
        splash_root.mainloop()

        # STEP 5: Launch the actual student management application
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
