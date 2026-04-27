import tkinter as tk
from tkinter import messagebox
from pymongo import MongoClient
from hashlib import sha256
from PIL import Image, ImageTk
import urllib.request
import io

# MongoDB setup
client = MongoClient("mongodb://localhost:27017/")
db = client["student_management"]
users_collection = db["users"]

def hash_password(password):
    return sha256(password.encode()).hexdigest()

def redirect_to_panel(user_type):
    root.destroy()
    if user_type == "admin":
        import admin_panel
        admin_panel.run_admin_panel()
    elif user_type == "student":
        import student_panel
        student_panel.run_student_panel()

def open_login_modal():
    login_win = tk.Toplevel(root)
    login_win.title("Login")
    login_win.geometry("400x300")
    login_win.configure(bg="white")
    login_win.transient(root)
    login_win.grab_set()

    tk.Label(login_win, text="Username", bg="white", font=("Segoe UI", 12)).pack(pady=(15, 5))
    username_entry = tk.Entry(login_win, font=("Segoe UI", 11), relief="solid", bd=1)
    username_entry.pack(pady=5, ipadx=5, ipady=3)

    tk.Label(login_win, text="Password", bg="white", font=("Segoe UI", 12)).pack(pady=(15, 5))
    password_entry = tk.Entry(login_win, show="*", font=("Segoe UI", 11), relief="solid", bd=1)
    password_entry.pack(pady=5, ipadx=5, ipady=3)

    def handle_login():
        username = username_entry.get()
        password = password_entry.get()
        hashed = hash_password(password)

        user = users_collection.find_one({"username": username, "password": hashed})
        if user:
            messagebox.showinfo("Success", f"Welcome {username}!")
            login_win.destroy()
            root.after(0, redirect_to_panel, user["user_type"])
        else:
            messagebox.showerror("Error", "Invalid credentials")

    tk.Button(login_win, text="Login", font=("Segoe UI", 11), bg="#007bff", fg="white",
              activebackground="#0056b3", relief="flat",
              command=handle_login).pack(pady=25, ipadx=10, ipady=5)

def open_signup_modal():
    signup_win = tk.Toplevel(root)
    signup_win.title("Sign Up")
    signup_win.geometry("400x380")
    signup_win.configure(bg="white")
    signup_win.transient(root)
    signup_win.grab_set()

    tk.Label(signup_win, text="New Username", bg="white", font=("Segoe UI", 12)).pack(pady=(15, 5))
    username_entry = tk.Entry(signup_win, font=("Segoe UI", 11), relief="solid", bd=1)
    username_entry.pack(pady=5, ipadx=5, ipady=3)

    tk.Label(signup_win, text="New Password", bg="white", font=("Segoe UI", 12)).pack(pady=(15, 5))
    password_entry = tk.Entry(signup_win, show="*", font=("Segoe UI", 11), relief="solid", bd=1)
    password_entry.pack(pady=5, ipadx=5, ipady=3)

    tk.Label(signup_win, text="Select Role", bg="white", font=("Segoe UI", 12)).pack(pady=(15, 5))
    role_var = tk.StringVar(value="student")
    roles_frame = tk.Frame(signup_win, bg="white")
    roles_frame.pack()
    tk.Radiobutton(roles_frame, text="Student", variable=role_var, value="student", bg="white",
                   font=("Segoe UI", 11)).pack(side="left", padx=10)
    tk.Radiobutton(roles_frame, text="Admin", variable=role_var, value="admin", bg="white",
                   font=("Segoe UI", 11)).pack(side="left", padx=10)

    def handle_signup():
        username = username_entry.get()
        password = password_entry.get()
        if not username or not password:
            messagebox.showerror("Error", "All fields required")
            return
        hashed = hash_password(password)
        if users_collection.find_one({"username": username}):
            messagebox.showerror("Error", "Username already exists")
        else:
            users_collection.insert_one({
                "username": username,
                "password": hashed,
                "user_type": role_var.get()
            })
            messagebox.showinfo("Success", "User registered")
            signup_win.destroy()

    tk.Button(signup_win, text="Create Account", font=("Segoe UI", 11), bg="#28a745", fg="white",
              activebackground="#1e7e34", relief="flat",
              command=handle_signup).pack(pady=30, ipadx=10, ipady=5)

def open_forgot_password_modal():
    forgot_win = tk.Toplevel(root)
    forgot_win.title("Reset Password")
    forgot_win.geometry("400x300")
    forgot_win.configure(bg="white")
    forgot_win.transient(root)
    forgot_win.grab_set()

    tk.Label(forgot_win, text="Username", bg="white", font=("Segoe UI", 12)).pack(pady=(15, 5))
    username_entry = tk.Entry(forgot_win, font=("Segoe UI", 11), relief="solid", bd=1)
    username_entry.pack(pady=5, ipadx=5, ipady=3)

    tk.Label(forgot_win, text="New Password", bg="white", font=("Segoe UI", 12)).pack(pady=(15, 5))
    password_entry = tk.Entry(forgot_win, show="*", font=("Segoe UI", 11), relief="solid", bd=1)
    password_entry.pack(pady=5, ipadx=5, ipady=3)

    def handle_reset():
        username = username_entry.get()
        password = password_entry.get()
        hashed = hash_password(password)
        result = users_collection.update_one({"username": username}, {"$set": {"password": hashed}})
        if result.modified_count:
            messagebox.showinfo("Success", "Password reset")
            forgot_win.destroy()
        else:
            messagebox.showerror("Error", "Username not found")

    tk.Button(forgot_win, text="Reset Password", font=("Segoe UI", 11), bg="#ffc107", fg="black",
              activebackground="#e0a800", relief="flat",
              command=handle_reset).pack(pady=25, ipadx=10, ipady=5)

def run_dashboard():
    global root
    root = tk.Tk()
    root.title("Government Polytechnic, Chapra - Student Dashboard")
    root.geometry("800x600")
    root.configure(bg="white")

    # Load background image
    bg_url = "https://images.unsplash.com/photo-1503676260728-1c00da094a0b"
    u = urllib.request.urlopen(bg_url)
    raw_data = u.read()
    u.close()
    bg_image = Image.open(io.BytesIO(raw_data))
    bg_image = bg_image.resize((1330, 900), Image.Resampling.LANCZOS)
    bg_photo = ImageTk.PhotoImage(bg_image)

    bg_label = tk.Label(root, image=bg_photo)
    bg_label.image = bg_photo
    bg_label.place(x=0, y=0, relwidth=1, relheight=1)

    # Header
    header = tk.Frame(root, bg="#003366", height=110, relief="ridge", bd=2)
    header.pack(fill=tk.X)
    tk.Label(header, text="GOVERNMENT POLYTECHNIC, CHAPRA",
             font=("Segoe UI", 28, "bold"), fg="white", bg="#003366").pack(pady=(15, 0))
    tk.Label(header, text="State Board of Technical Education, Bihar",
             font=("Segoe UI", 16), fg="white", bg="#003366").pack(pady=(0, 15))

    # Main Content Frame
    frame = tk.Frame(root, bg="white", bd=5, relief="groove")
    frame.place(relx=0.5, rely=0.55, anchor="center", width=580, height=520)

    tk.Label(frame, text="Student Management System",
             font=("Segoe UI", 22, "bold"), bg="white", fg="#003366").pack(pady=40)

    btn_style = {"width": 26, "height": 2, "font": ("Segoe UI", 12, "bold"), "relief": "flat"}

    tk.Button(frame, text="Login", bg="#007bff", fg="white", activebackground="#0056b3", **btn_style,
              command=open_login_modal).pack(pady=12)
    tk.Button(frame, text="Sign Up", bg="#28a745", fg="white", activebackground="#1e7e34", **btn_style,
              command=open_signup_modal).pack(pady=12)
    tk.Button(frame, text="Forgot Password", bg="#ffc107", fg="black", activebackground="#e0a800", **btn_style,
              command=open_forgot_password_modal).pack(pady=12)
    tk.Button(frame, text="Exit", bg="#dc3545", fg="white", activebackground="#bd2130", **btn_style,
              command=root.quit).pack(pady=24)

    # Footer
    footer = tk.Frame(root, bg="#000000", height=28)
    footer.pack(side="bottom", fill="x")
    tk.Label(footer, text="© 2025 Govt. Polytechnic, Chapra | Designed by AI-powered GUI",
             font=("Segoe UI", 10), fg="white", bg="#000000").pack(pady=4)

    root.mainloop()

if __name__ == "__main__":
    run_dashboard()
