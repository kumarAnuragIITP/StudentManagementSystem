
import tkinter as tk
import os

try:
    from PIL import Image, ImageTk, ImageOps
    PIL_OK = True
except ImportError:
    PIL_OK = False


def splash_screen(root):

    root.title("Welcome to Student Management System")
    root.geometry("1000x650")
    root.resizable(False, False)
    root.configure(bg="#FFFFFF")

    # Center splash window
    root.update_idletasks()

    width = 1000
    height = 650

    x = (root.winfo_screenwidth() - width) // 2
    y = (root.winfo_screenheight() - height) // 2

    root.geometry(f"{width}x{height}+{x}+{y}")

    # Always use the folder containing this Python file
    base_dir = os.path.dirname(os.path.abspath(__file__))
    photo_dir = os.path.join(base_dir, "images")

    image_path1 = os.path.join(photo_dir, "gpc.png")
    image_path2 = os.path.join(photo_dir, "sbte.png")
    bg_image_path = os.path.join(photo_dir, "a.jpg")

    # Keep image references alive
    root.image_references = []

    # ---------------- LEFT PANEL ----------------

    left_frame = tk.Frame(
        root,
        bg="#1769AA",
        width=280
    )

    left_frame.pack(side="left", fill="y")
    left_frame.pack_propagate(False)

    tk.Label(
        left_frame,
        text="STATE BOARD\nOF TECHNICAL\nEDUCATION, BIHAR",
        font=("Arial", 17, "bold"),
        bg="#1769AA",
        fg="white",
        justify="center"
    ).pack(pady=(35, 15))

    # SBTE logo
    if PIL_OK:
        try:
            img1 = Image.open(image_path1).convert("RGBA")
            img1.thumbnail((190, 190), Image.Resampling.LANCZOS)

            tk_img1 = ImageTk.PhotoImage(img1)
            root.image_references.append(tk_img1)

            tk.Label(
                left_frame,
                image=tk_img1,
                bg="#1769AA"
            ).pack(pady=25)

        except Exception as e:
            print("SBTE logo loading error:", e)

    tk.Label(
        left_frame,
        text="STUDENT\nMANAGEMENT\nSYSTEM",
        font=("Arial", 20, "bold"),
        bg="#1769AA",
        fg="white",
        justify="center"
    ).pack(pady=20)

    tk.Frame(
        left_frame,
        bg="#64B5F6",
        height=2
    ).pack(fill="x", padx=35, pady=15)

    tk.Label(
        left_frame,
        text="LEARN  •  GROW  •  SUCCEED",
        font=("Arial", 9, "bold"),
        bg="#1769AA",
        fg="#DCEEFF"
    ).pack(pady=10)

    # ---------------- RIGHT PANEL ----------------

    canvas = tk.Canvas(
        root,
        bg="#172A48",
        highlightthickness=0,
        bd=0
    )

    canvas.pack(side="right", fill="both", expand=True)

    root.update_idletasks()

    canvas_width = canvas.winfo_width()
    canvas_height = canvas.winfo_height()

    # Background image
    if PIL_OK:
        try:
            bg_img = Image.open(bg_image_path).convert("RGB")

            bg_img = ImageOps.fit(
                bg_img,
                (canvas_width, canvas_height),
                method=Image.Resampling.LANCZOS
            )

            bg_tk_img = ImageTk.PhotoImage(bg_img)
            root.image_references.append(bg_tk_img)

            canvas.create_image(
                0, 0,
                anchor="nw",
                image=bg_tk_img
            )

            # Dark overlay for readable text
            canvas.create_rectangle(
                0, 0,
                canvas_width, canvas_height,
                fill="#10233D",
                stipple="gray50",
                outline=""
            )

        except Exception as e:
            print("Background loading error:", e)

    center_x = canvas_width // 2

    canvas.create_text(
        center_x, 65,
        text="GOVERNMENT POLYTECHNIC CHAPRA",
        font=("Arial", 25, "bold"),
        fill="white",
        justify="center"
    )

    canvas.create_text(
        center_x, 105,
        text="BIHAR",
        font=("Arial", 15, "bold"),
        fill="#8EDBD4"
    )

    # College logo
    if PIL_OK:
        try:
            img2 = Image.open(image_path2).convert("RGBA")
            img2.thumbnail((210, 210), Image.Resampling.LANCZOS)

            tk_img2 = ImageTk.PhotoImage(img2)
            root.image_references.append(tk_img2)

            canvas.create_image(
                center_x,
                290,
                image=tk_img2
            )

        except Exception as e:
            print("College logo loading error:", e)

    canvas.create_text(
        center_x, 445,
        text="STUDENT MANAGEMENT SYSTEM",
        font=("Arial", 23, "bold"),
        fill="white"
    )

    canvas.create_text(
        center_x, 495,
        text="A SMARTER AND SAFER CAMPUS EXPERIENCE",
        font=("Arial", 11, "bold"),
        fill="#B8D9F5"
    )

    canvas.create_text(
        center_x, 555,
        text="Loading application...",
        font=("Arial", 13),
        fill="#8EDBD4"
    )

    # Loading animation
    loading_text = canvas.create_text(
        center_x, 585,
        text="● ○ ○",
        font=("Arial", 15, "bold"),
        fill="white"
    )

    def animate(index=0):
        if not root.winfo_exists():
            return

        symbols = ["● ○ ○", "○ ● ○", "○ ○ ●"]

        canvas.itemconfigure(
            loading_text,
            text=symbols[index % len(symbols)]
        )

        root.after(300, lambda: animate(index + 1))

    animate()

    # Automatically close splash after 3 seconds.
    # main.py will open the StudentPortal after this window closes.
    root.after(3000, root.destroy)
