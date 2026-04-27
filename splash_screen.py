import tkinter as tk
import time
import threading
import subprocess
import sys
import os
from PIL import Image, ImageTk

def splash_screen(root):
    root.title("Welcome to Student Management System")
    root.geometry("800x600")
    root.configure(bg="white")

    # Center window
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f"{width}x{height}+{x}+{y}")

    # Image paths
    image_path1 = r"C:\Users\kanur\PycharmProjects\PythonProject\student_photos\sbte_logo.png"
    image_path2 = r"C:\Users\kanur\PycharmProjects\PythonProject\student_photos\Gp_chapra_copy.png"
    bg_image_path = r"C:\Users\kanur\PycharmProjects\PythonProject\student_photos\a.jpg"

    # LEFT FRAME
    left_frame = tk.Frame(root, bg="#1e90ff", width=300)
    left_frame.pack(side="left", fill="y")
    left_frame.pack_propagate(False)

    tk.Label(left_frame, text="State Board\nOf Technical\n Education, Bihar",
             font=("Arial", 17, "bold"), bg="#1e90ff", fg="white", justify="center").pack(pady=10)

    try:
        img1 = Image.open(image_path1).resize((220, 220), Image.Resampling.LANCZOS)
        tk_img1 = ImageTk.PhotoImage(img1)
        tk.Label(left_frame, image=tk_img1, bg="#1e90ff").pack(pady=30)
    except Exception as e:
        print("Error loading left image:", e)

    tk.Label(left_frame, text="Student\n Management \nSystem",
             font=("Arial", 18, "bold"), bg="#1e90ff", fg="white", justify="center").pack(pady=10)

    # RIGHT CANVAS
    canvas_width = 1000
    canvas_height = 650
    canvas = tk.Canvas(root, width=canvas_width, height=canvas_height, highlightthickness=0)
    canvas.pack(side="right", fill="both", expand=True)

    try:
        bg_img = Image.open(bg_image_path).resize((canvas_width, canvas_height), Image.Resampling.LANCZOS)
        bg_tk_img = ImageTk.PhotoImage(bg_img)
        canvas.create_image(0, 0, anchor="nw", image=bg_tk_img)
    except Exception as e:
        print("Error loading background image:", e)

    center_x = canvas_width // 2

    canvas.create_text(center_x, 40, text="Government Polytechnic Chapra, Bihar",
                       font=("Arial", 30, "bold"), fill="black", justify="center")

    try:
        img2 = Image.open(image_path2).resize((200, 200), Image.Resampling.LANCZOS)
        tk_img2 = ImageTk.PhotoImage(img2)
        canvas.create_image(center_x, 200, image=tk_img2)
    except Exception as e:
        print("Error loading right image:", e)

    canvas.create_text(center_x, 370, text="Student Management System",
                       font=("Arial", 30, "bold"), fill="white")
    canvas.create_text(center_x, 440, text="Loading...",
                       font=("Arial", 15), fill="white")

    def redirect_to_main():
        time.sleep(3)
        root.after(0, launch_main)

    def launch_main():
        root.destroy()
        # Make sure this path is correct!
        main_script_path = r"C:\Users\kanur\PycharmProjects\PythonProject\main.py"
        python_exe = sys.executable  # gets current Python interpreter
        subprocess.Popen([python_exe, main_script_path])

    threading.Thread(target=redirect_to_main, daemon=True).start()
    root.mainloop()

if __name__ == "__main__":
    root = tk.Tk()
    splash_screen(root)
