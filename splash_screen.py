import tkinter as tk
import os
import math

try:
    from PIL import Image, ImageTk, ImageOps, ImageDraw
    PIL_OK = True
except ImportError:
    PIL_OK = False


def splash_screen(root):

    WIDTH = 1200
    HEIGHT = 720

    root.title("Government Polytechnic Chapra | Student Management System")
    root.geometry(f"{WIDTH}x{HEIGHT}")
    root.resizable(False, False)
    root.configure(bg="#0B1830")

    root.update_idletasks()

    x = (root.winfo_screenwidth() - WIDTH) // 2
    y = (root.winfo_screenheight() - HEIGHT) // 2

    root.geometry(f"{WIDTH}x{HEIGHT}+{x}+{y}")

    root.image_references = []

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    PHOTO_DIR = os.path.join(BASE_DIR, "images")

    gpc_path = os.path.join(PHOTO_DIR, "gpc.png")
    sbte_path = os.path.join(PHOTO_DIR, "sbte.png")
    bg_path = os.path.join(PHOTO_DIR, "a.jpg")

    # ================= COLOR THEME =================

    COLORS = {
        "navy": "#102747",
        "navy_dark": "#09172C",
        "blue": "#1769AA",
        "cyan": "#38D6D0",
        "white": "#FFFFFF",
        "muted": "#B7CBE3",
        "light": "#EAF5FF",
        "panel": "#172F50",
        "accent": "#63E6DF",
    }

    # ================= HELPER FUNCTIONS =================

    def load_image(path, size, fit=False):
        if not PIL_OK or not os.path.exists(path):
            return None

        try:
            img = Image.open(path).convert("RGBA")

            if fit:
                img = ImageOps.fit(
                    img,
                    size,
                    method=Image.Resampling.LANCZOS
                )
            else:
                img.thumbnail(
                    size,
                    Image.Resampling.LANCZOS
                )

            photo = ImageTk.PhotoImage(img)
            root.image_references.append(photo)

            return photo

        except Exception as error:
            print("Image loading error:", path, error)
            return None

    def rounded_rectangle(canvas, x1, y1, x2, y2, radius=20,
                          fill="#FFFFFF", outline=""):

        points = [
            x1 + radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
            x1, y1 + radius,
            x1, y1
        ]

        return canvas.create_polygon(
            points,
            smooth=True,
            fill=fill,
            outline=outline
        )

    # ================= MAIN BACKGROUND =================

    main = tk.Frame(root, bg=COLORS["navy_dark"])
    main.pack(fill="both", expand=True)

    # ================= LEFT BRANDING PANEL =================

    left = tk.Frame(
        main,
        bg=COLORS["navy"],
        width=290
    )

    left.pack(side="left", fill="y")
    left.pack_propagate(False)

    # Decorative top strip
    tk.Frame(
        left,
        bg=COLORS["cyan"],
        height=6
    ).pack(fill="x")

    # Institution heading
    tk.Label(
        left,
        text="GOVERNMENT",
        font=("Segoe UI", 12, "bold"),
        bg=COLORS["navy"],
        fg=COLORS["cyan"]
    ).pack(pady=(38, 3))

    tk.Label(
        left,
        text="POLYTECHNIC",
        font=("Segoe UI", 23, "bold"),
        bg=COLORS["navy"],
        fg="white"
    ).pack()

    tk.Label(
        left,
        text="CHAPRA, BIHAR",
        font=("Segoe UI", 12, "bold"),
        bg=COLORS["navy"],
        fg=COLORS["muted"]
    ).pack(pady=(3, 25))

    # College logo
    logo_frame = tk.Frame(
        left,
        bg="#FFFFFF",
        width=170,
        height=170
    )
    logo_frame.pack(pady=8)
    logo_frame.pack_propagate(False)

    gpc_logo = load_image(gpc_path, (150, 150))

    if gpc_logo:
        tk.Label(
            logo_frame,
            image=gpc_logo,
            bg="white"
        ).place(relx=0.5, rely=0.5, anchor="center")
    else:
        tk.Label(
            logo_frame,
            text="GPC",
            font=("Segoe UI", 37, "bold"),
            fg=COLORS["blue"],
            bg="white"
        ).place(relx=0.5, rely=0.5, anchor="center")

    tk.Label(
        left,
        text="STUDENT",
        font=("Segoe UI", 25, "bold"),
        bg=COLORS["navy"],
        fg="white"
    ).pack(pady=(30, 0))

    tk.Label(
        left,
        text="MANAGEMENT SYSTEM",
        font=("Segoe UI", 12, "bold"),
        bg=COLORS["navy"],
        fg=COLORS["cyan"]
    ).pack(pady=(1, 20))

    # Divider
    tk.Frame(
        left,
        bg="#345577",
        height=1
    ).pack(fill="x", padx=35)

    tk.Label(
        left,
        text="STATE BOARD OF TECHNICAL\nEDUCATION, BIHAR",
        font=("Segoe UI", 10, "bold"),
        justify="center",
        bg=COLORS["navy"],
        fg=COLORS["muted"]
    ).pack(pady=(20, 10))

    sbte_logo = load_image(sbte_path, (100, 75))

    if sbte_logo:
        tk.Label(
            left,
            image=sbte_logo,
            bg=COLORS["navy"]
        ).pack(pady=5)

    tk.Label(
        left,
        text="LEARN  •  GROW  •  SUCCEED",
        font=("Segoe UI", 9, "bold"),
        bg=COLORS["navy"],
        fg=COLORS["cyan"]
    ).pack(side="bottom", pady=25)

    # ================= RIGHT CONTENT PANEL =================

    right = tk.Canvas(
        main,
        bg=COLORS["navy_dark"],
        highlightthickness=0,
        bd=0
    )

    right.pack(side="right", fill="both", expand=True)

    root.update_idletasks()

    CW = right.winfo_width()
    CH = right.winfo_height()

    background = load_image(
        bg_path,
        (CW, CH),
        fit=True
    )

    if background:

        right.create_image(
            0, 0,
            anchor="nw",
            image=background
        )

        # Dark overlay
        right.create_rectangle(
            0, 0, CW, CH,
            fill="#07172C",
            stipple="gray50",
            outline=""
        )

    else:
        # Fallback if background image is missing
        right.configure(bg="#102B4D")

        for i in range(0, CH, 3):
            ratio = i / max(CH, 1)

            r = int(12 + ratio * 8)
            g = int(35 + ratio * 15)
            b = int(65 + ratio * 30)

            color = f"#{r:02x}{g:02x}{b:02x}"

            right.create_rectangle(
                0, i, CW, i + 3,
                fill=color,
                outline=""
            )

    CENTER = CW // 2

    # ================= DECORATIVE ELEMENTS =================

    right.create_oval(
        CW - 180, -110,
        CW + 100, 170,
        outline="#315B7C",
        width=2
    )

    right.create_oval(
        CW - 140, -70,
        CW + 60, 130,
        outline="#244967",
        width=2
    )

    right.create_oval(
        -100, CH - 170,
        150, CH + 80,
        outline="#315B7C",
        width=2
    )

    # ================= HEADER =================

    right.create_text(
        CENTER,
        65,
        text="WELCOME TO",
        font=("Segoe UI", 12, "bold"),
        fill=COLORS["cyan"]
    )

    right.create_text(
        CENTER,
        105,
        text="GOVERNMENT POLYTECHNIC",
        font=("Segoe UI", 26, "bold"),
        fill="white"
    )

    right.create_text(
        CENTER,
        143,
        text="CHAPRA  •  BIHAR",
        font=("Segoe UI", 13, "bold"),
        fill="#B9DDF7"
    )

    # Header underline
    right.create_rectangle(
        CENTER - 45, 166,
        CENTER + 45, 169,
        fill=COLORS["cyan"],
        outline=""
    )

    # ================= COLLEGE LOGO =================

    logo2 = load_image(
        sbte_path,
        (175, 145)
    )

    if logo2:

        rounded_rectangle(
            right,
            CENTER - 95, 190,
            CENTER + 95, 345,
            radius=18,
            fill="#FFFFFF"
        )

        right.create_image(
            CENTER,
            267,
            image=logo2
        )

    else:

        rounded_rectangle(
            right,
            CENTER - 80, 200,
            CENTER + 80, 330,
            radius=18,
            fill="#FFFFFF"
        )

        right.create_text(
            CENTER,
            265,
            text="GPC",
            font=("Segoe UI", 42, "bold"),
            fill=COLORS["blue"]
        )

    # ================= MAIN TITLE CARD =================

    rounded_rectangle(
        right,
        45, 365,
        CW - 45, 525,
        radius=20,
        fill="#102747"
    )

    right.create_text(
        CENTER,
        400,
        text="STUDENT MANAGEMENT SYSTEM",
        font=("Segoe UI", 23, "bold"),
        fill="white"
    )

    right.create_text(
        CENTER,
        440,
        text="A SMARTER AND SAFER CAMPUS EXPERIENCE",
        font=("Segoe UI", 10, "bold"),
        fill="#B9DDF7"
    )

    # Small feature labels
    features = [
        "ACADEMICS",
        "ATTENDANCE",
        "EXAMINATIONS",
        "RESULTS"
    ]

    feature_width = 125
    gap = 12
    total_width = len(features) * feature_width + (len(features) - 1) * gap
    start_x = CENTER - total_width // 2

    for i, feature in enumerate(features):

        fx = start_x + i * (feature_width + gap)

        rounded_rectangle(
            right,
            fx, 470,
            fx + feature_width, 500,
            radius=9,
            fill="#21466B"
        )

        right.create_text(
            fx + feature_width // 2,
            485,
            text=feature,
            font=("Segoe UI", 8, "bold"),
            fill=COLORS["cyan"]
        )

    # ================= LOADING SECTION =================

    right.create_text(
        CENTER,
        565,
        text="INITIALIZING APPLICATION",
        font=("Segoe UI", 10, "bold"),
        fill="#D7E8F8"
    )

    loading_status = right.create_text(
        CENTER,
        590,
        text="Preparing your workspace...",
        font=("Segoe UI", 9),
        fill=COLORS["cyan"]
    )


    bar_width = 340
    bar_x = CENTER - bar_width // 2

    rounded_rectangle(
        right,
        bar_x, 615,
        bar_x + bar_width, 625,
        radius=5,
        fill="#34516D"
    )

    progress = right.create_rectangle(
        bar_x, 615,
        bar_x, 625,
        fill=COLORS["cyan"],
        outline=""
    )

    # Loading dots
    loading_dots = right.create_text(
        CENTER,
        647,
        text="●  ○  ○",
        font=("Segoe UI", 10, "bold"),
        fill="white"
    )

    animation_state = {
        "progress": 0,
        "dots": 0,
        "active": True
    }

    status_messages = [
        "Preparing your workspace...",
        "Loading academic resources...",
        "Initializing student portal...",
        "Almost ready..."
    ]

    def animate():

        if not animation_state["active"]:
            return

        try:
            if not root.winfo_exists():
                return

            animation_state["progress"] += 2

            if animation_state["progress"] > 100:
                animation_state["progress"] = 0

            animation_state["dots"] += 1

            p = animation_state["progress"]

            right.coords(
                progress,
                bar_x,
                615,
                bar_x + (bar_width * p / 100),
                625
            )

            dots = ["●  ○  ○", "○  ●  ○", "○  ○  ●"]

            right.itemconfigure(
                loading_dots,
                text=dots[animation_state["dots"] % 3]
            )

            message_index = min(
                animation_state["progress"] // 25,
                3
            )

            right.itemconfigure(
                loading_status,
                text=status_messages[message_index]
            )

            root.after(35, animate)

        except tk.TclError:
            animation_state["active"] = False

    animate()

    def close_splash():

        animation_state["active"] = False

        try:
            if root.winfo_exists():
                root.destroy()
        except tk.TclError:
            pass


    root.after(5000, close_splash)
