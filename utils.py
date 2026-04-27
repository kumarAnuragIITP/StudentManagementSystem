import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog,ttk
from pymongo import MongoClient
from bson import ObjectId
from PIL import Image, ImageTk  # Import PIL for handling images
import os
import matplotlib.pyplot as plt

# MongoDB Setup (Ensure MongoDB is running locally)
client = MongoClient("mongodb://localhost:27017/")
db = client["student_management"]
students_collection = db["students"]
faculty_collection = db["faculty"]

# Directory to save student photos
PHOTO_DIR = "student_photos"
if not os.path.exists(PHOTO_DIR):
    os.makedirs(PHOTO_DIR)

# Helper function to display messageboxes
def show_message(title, message):
    messagebox.showinfo(title, message)

# Function to upload and store student photo
def upload_photo():
    photo_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.gif")])
    if photo_path:
        # Save the photo in a directory and return the file path
        new_photo_path = os.path.join(PHOTO_DIR, os.path.basename(photo_path))
        os.rename(photo_path, new_photo_path)
        return new_photo_path
    return None

# Add Student Function
def add_student():
    def select_photo():
        nonlocal selected_photo_path
        path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.gif")])
        if path:
            selected_photo_path = os.path.join(PHOTO_DIR, os.path.basename(path))
            img = Image.open(path)
            img.thumbnail((100, 100))
            photo_img = ImageTk.PhotoImage(img)
            photo_label.config(image=photo_img)
            photo_label.image = photo_img

    def save_student():
        name = name_entry.get()
        roll = roll_entry.get()
        mobile = mobile_entry.get()
        department = dept_entry.get()
        address = address_entry.get()

        if not (name and roll and mobile and department and address):
            show_message("Error", "All fields are required!")
            return

        if selected_photo_path:
            # Save image to the folder
            new_photo_path = os.path.join(PHOTO_DIR, os.path.basename(selected_photo_path))
            if selected_photo_path != new_photo_path:
                os.rename(selected_photo_path, new_photo_path)
        else:
            new_photo_path = None

        student_data = {
            "name": name,
            "roll": roll,
            "mobile": mobile,
            "department": department,
            "address": address,
            "photo": new_photo_path
        }
        students_collection.insert_one(student_data)
        show_message("Success", "Student added successfully!")
        add_window.destroy()

    selected_photo_path = None
    add_window = tk.Toplevel(admin_window)
    add_window.title("➕ Add New Student")
    add_window.geometry("500x550")
    add_window.configure(bg="#f0f4f7")

    tk.Label(add_window, text="Add Student Details", font=("Helvetica", 16, "bold"),
             bg="#f0f4f7", fg="#2c3e50").pack(pady=10)

    form_frame = tk.Frame(add_window, bg="#f0f4f7")
    form_frame.pack(pady=10, padx=20, fill="x")

    # Form fields
    labels = ["Name", "Roll No.", "Mobile", "Department", "Address"]
    entries = []
    for idx, label in enumerate(labels):
        tk.Label(form_frame, text=label, bg="#f0f4f7", anchor="w",
                 font=("Arial", 11)).grid(row=idx, column=0, sticky="w", pady=8)
        entry = ttk.Entry(form_frame, width=35)
        entry.grid(row=idx, column=1, pady=8)
        entries.append(entry)

    name_entry, roll_entry, mobile_entry, dept_entry, address_entry = entries

    # Photo
    tk.Label(form_frame, text="Photo", bg="#f0f4f7", font=("Arial", 11)).grid(row=5, column=0, sticky="w", pady=8)
    photo_btn = ttk.Button(form_frame, text="Select Photo", command=select_photo)
    photo_btn.grid(row=5, column=1, sticky="w", pady=8)

    photo_label = tk.Label(form_frame, bg="#f0f4f7")
    photo_label.grid(row=6, column=1, pady=10, sticky="w")

    # Save Button
    ttk.Button(add_window, text="Save Student", command=save_student,
               style="Accent.TButton").pack(pady=20)

# Delete Student Function
def delete_student():
    roll_no = simpledialog.askstring("Delete Student", "Enter Roll No. of the student to delete:")

    if roll_no:
        student = students_collection.find_one({"roll": roll_no})
        if student:
            students_collection.delete_one({"roll": roll_no})
            show_message("Success", f"Student with Roll No. {roll_no} deleted successfully!")
        else:
            show_message("Error", f"No student found with Roll No. {roll_no}")
    else:
        show_message("Error", "Roll No. is required to delete!")

# Update Student Function
def update_student():
    roll_no = simpledialog.askstring("Update Student", "Enter Roll No. of the student to update:")
    if not roll_no:
        show_message("Error", "Roll No. is required to update!")
        return

    student = students_collection.find_one({"roll": roll_no})
    if not student:
        show_message("Error", f"No student found with Roll No. {roll_no}")
        return

    update_win = tk.Toplevel(admin_window)
    update_win.title("✏️ Update Student Info")
    update_win.geometry("450x400")
    update_win.configure(bg="#f0f4f7")

    tk.Label(update_win, text="Update Student Information", font=("Helvetica", 14, "bold"),
             bg="#f0f4f7", fg="#2c3e50").pack(pady=10)

    form_frame = tk.Frame(update_win, bg="#f0f4f7")
    form_frame.pack(pady=10, padx=20, fill="x")

    tk.Label(form_frame, text="New Name", bg="#f0f4f7", font=("Arial", 11)).grid(row=0, column=0, pady=10, sticky="w")
    name_entry = ttk.Entry(form_frame, width=35)
    name_entry.grid(row=0, column=1, pady=10)
    name_entry.insert(0, student.get("name", ""))

    tk.Label(form_frame, text="New Department", bg="#f0f4f7", font=("Arial", 11)).grid(row=1, column=0, pady=10, sticky="w")
    dept_entry = ttk.Entry(form_frame, width=35)
    dept_entry.grid(row=1, column=1, pady=10)
    dept_entry.insert(0, student.get("department", ""))

    def apply_update():
        new_name = name_entry.get()
        new_dept = dept_entry.get()
        updates = {}
        if new_name and new_name != student.get("name"):
            updates["name"] = new_name
        if new_dept and new_dept != student.get("department"):
            updates["department"] = new_dept

        if updates:
            students_collection.update_one({"roll": roll_no}, {"$set": updates})
            show_message("Success", "Student updated successfully!")
        else:
            show_message("Info", "No changes detected.")
        update_win.destroy()

    ttk.Button(update_win, text="Apply Changes", command=apply_update).pack(pady=20)

def open_zoomable_image(image_path):
    if not os.path.exists(image_path):
        messagebox.showerror("Image Error", "Image file not found.")
        return

    zoom_window = tk.Toplevel()
    zoom_window.title("Zoomed Photo")
    zoom_window.geometry("800x600")
    zoom_window.configure(bg="black")

    canvas = tk.Canvas(zoom_window, bg="black")
    canvas.pack(fill="both", expand=True)

    pil_img = Image.open(image_path)
    img_scale = 1.0
    tk_img = ImageTk.PhotoImage(pil_img)
    img_container = canvas.create_image(0, 0, anchor="nw", image=tk_img)
    canvas.image = tk_img  # prevent garbage collection

    def zoom(event):
        nonlocal img_scale, tk_img
        if event.delta > 0 or event.num == 4:
            img_scale *= 1.1
        elif event.delta < 0 or event.num == 5:
            img_scale /= 1.1

        new_size = (int(pil_img.width * img_scale), int(pil_img.height * img_scale))
        resized = pil_img.resize(new_size, Image.Resampling.LANCZOS)
        tk_img = ImageTk.PhotoImage(resized)
        canvas.itemconfig(img_container, image=tk_img)
        canvas.image = tk_img

    def start_drag(event):
        canvas.scan_mark(event.x, event.y)

    def do_drag(event):
        canvas.scan_dragto(event.x, event.y, gain=1)

    # Bindings
    canvas.bind("<MouseWheel>", zoom)  # Windows
    canvas.bind("<Button-4>", zoom)    # Linux scroll up
    canvas.bind("<Button-5>", zoom)    # Linux scroll down
    canvas.bind("<ButtonPress-1>", start_drag)
    canvas.bind("<B1-Motion>", do_drag)

# View All Students Function
def view_all_students():
    students_window = tk.Toplevel(admin_window)
    students_window.title("📋 All Students")
    students_window.geometry("1200x600")
    students_window.configure(bg="#f0f4f7")

    tk.Label(students_window, text="Student Records",
             font=("Helvetica", 18, "bold"), fg="#2c3e50", bg="#f0f4f7").pack(pady=10)

    # Scrollable canvas setup
    canvas = tk.Canvas(students_window, bg="#f0f4f7", highlightthickness=0)
    scrollbar = ttk.Scrollbar(students_window, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)

    scroll_frame = tk.Frame(canvas, bg="#f0f4f7")
    canvas.create_window((0, 0), window=scroll_frame, anchor="nw")

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    def on_frame_configure(event):
        canvas.configure(scrollregion=canvas.bbox("all"))
    scroll_frame.bind("<Configure>", on_frame_configure)

    # Define headers
    headers = ["Photo", "Name", "Roll No", "Department", "Mobile", "Address"]
    header_bg = "#1e90ff"
    header_fg = "white"
    font_header = ("Arial", 12, "bold")

    for col, header in enumerate(headers):
        tk.Label(scroll_frame, text=header, font=font_header, bg=header_bg, fg=header_fg,
                 padx=10, pady=6, borderwidth=1, relief="solid").grid(row=0, column=col, sticky="nsew")

    # Fetch student data
    students = list(students_collection.find())

    image_refs = {}

    for row_num, student in enumerate(students, start=1):
        bg_color = "#ffffff" if row_num % 2 else "#eaf3ff"
        row_pad = {"padx": 1, "pady": 1}

        # Student photo
        if student.get("photo") and os.path.exists(student["photo"]):
            img = Image.open(student["photo"])
            img.thumbnail((65, 65))
            photo_img = ImageTk.PhotoImage(img)
            image_refs[student["_id"]] = photo_img

            photo_label = tk.Label(scroll_frame, image=photo_img, bg=bg_color,
                                   borderwidth=1, relief="solid", cursor="hand2")
            photo_label.image = photo_img
            photo_label.grid(row=row_num, column=0, **row_pad)
            photo_label.bind("<Button-1>", lambda e, path=student["photo"]: open_zoomable_image(path))
        else:
            tk.Label(scroll_frame, text="No Photo", bg=bg_color,
                     borderwidth=1, relief="solid", font=("Arial", 10)).grid(row=row_num, column=0, **row_pad)

        # Text fields
        data_fields = [
            student.get("name", ""),
            student.get("roll", ""),
            student.get("department", ""),
            student.get("mobile", ""),
            student.get("address", "")
        ]

        for col_idx, field in enumerate(data_fields, start=1):
            tk.Label(scroll_frame, text=field, bg=bg_color, anchor="w", font=("Arial", 11),
                     padx=8, pady=8, borderwidth=1, relief="solid").grid(row=row_num, column=col_idx, sticky="nsew", **row_pad)

    # Stretch columns equally
    for col in range(len(headers)):
        scroll_frame.grid_columnconfigure(col, weight=1)

    # Instruction label
    tk.Label(students_window, text="📷 Click on student photo to view it full-size.",
             font=("Arial", 10, "italic"), bg="#f0f4f7", fg="#333").pack(pady=5)


def view_statistics():
    try:
        # Query counts from MongoDB
        num_students = students_collection.count_documents({})
        num_faculty = faculty_collection.count_documents({})

        # Text summary (optional popup)
        stats_message = f"Total Students: {num_students}\nTotal Faculty: {num_faculty}"
        messagebox.showinfo("Statistics", stats_message)  # Or show_message()

        # Prepare data for plotting
        categories = ['Students', 'Faculty']
        counts = [num_students, num_faculty]

        # Plot bar chart
        plt.figure(figsize=(6, 4))
        bars = plt.bar(categories, counts, color=['skyblue', 'salmon'])
        plt.title('Institution Statistics')
        plt.ylabel('Count')

        # Add labels on top of each bar
        for bar in bars:
            yval = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2.0, yval + 0.5, int(yval), ha='center', va='bottom', fontsize=10)

        plt.tight_layout()
        plt.show()

    except Exception as e:
        messagebox.showerror("Error", f"Failed to retrieve statistics:\n{e}")
# Search Functionality
def search_student():
    search_criteria = search_criteria_var.get()  # Get the selected criteria
    query = search_query_entry.get()  # Get the search query

    if not query:
        show_message("Error", "Please enter a search query.")
        return

    if search_criteria == "DOB":
        students = students_collection.find({"dob": query})
    elif search_criteria == "Roll No":
        students = students_collection.find({"roll": query})
    elif search_criteria == "Address":
        students = students_collection.find({"address": {"$regex": query, "$options": "i"}})  # Case insensitive search
    elif search_criteria == "ID":
        students = students_collection.find({"_id": ObjectId(query)})
    else:
        show_message("Error", "Invalid search criteria.")
        return

    # Display search results
    search_results_window = tk.Toplevel(admin_window)
    search_results_window.title("Search Results")
    search_results_window.geometry("600x400")

    tk.Label(search_results_window, text=f"Search Results for {search_criteria}: {query}", font=("Arial", 14)).pack(pady=10)

    students_found = list(students)
    if students_found:
        for student in students_found:
            student_info = f"Name: {student['name']} | Roll No: {student['roll']} | Department: {student['department']}"
            tk.Label(search_results_window, text=student_info).pack(pady=5)

            # Display student photo if available
            if student.get("photo"):
                img = Image.open(student["photo"])
                img.thumbnail((100, 100))  # Resize the image to fit the UI
                img = ImageTk.PhotoImage(img)
                img_label = tk.Label(search_results_window, image=img)
                img_label.image = img  # Keep a reference to the image
                img_label.pack()
    else:
        tk.Label(search_results_window, text="No results found.").pack(pady=10)

# Admin Panel Interface
def run_admin_panel():
    global admin_window
    admin_window = tk.Tk()
    admin_window.title("Admin Panel - Student Management System")
    admin_window.geometry("1200x700")
    admin_window.configure(bg="#f0f4f7")

    # Load background and logo images
    try:
        left_logo_path = "student_photos/sbte_logo.png"
        right_logo_path = "student_photos/Gp_chapra_copy.png"
        background_path = "student_photos/a.jpg"

        left_logo = Image.open(left_logo_path).resize((180, 180), Image.Resampling.LANCZOS)
        right_logo = Image.open(right_logo_path).resize((180, 180), Image.Resampling.LANCZOS)
        bg_img = Image.open(background_path).resize((1000, 650), Image.Resampling.LANCZOS)

        bg_photo = ImageTk.PhotoImage(bg_img)
        left_logo_img = ImageTk.PhotoImage(left_logo)
        right_logo_img = ImageTk.PhotoImage(right_logo)
    except Exception as e:
        print("Error loading image:", e)

    # ---------------------- Left Sidebar ------------------------
    sidebar = tk.Frame(admin_window, bg="#1e90ff", width=280)
    sidebar.pack(side="left", fill="y")
    sidebar.pack_propagate(False)

    tk.Label(sidebar, text="State Board\nOf Technical\nEducation, Bihar",
             font=("Helvetica", 16, "bold"), bg="#1e90ff", fg="white", justify="center").pack(pady=20)

    tk.Label(sidebar, image=left_logo_img, bg="#1e90ff").pack(pady=10)

    tk.Label(sidebar, text="Student\nManagement\nSystem",
             font=("Helvetica", 18, "bold"), bg="#1e90ff", fg="white").pack(pady=30)

    # ---------------------- Main Canvas ------------------------
    main_canvas = tk.Canvas(admin_window, width=980, height=700, bg="white", highlightthickness=0)
    main_canvas.pack(side="left", fill="both", expand=True)
    main_canvas.create_image(0, 0, anchor="nw", image=bg_photo)

    # ---------------------- Title Texts ------------------------
    main_canvas.create_text(460, 30, text="Admin Panel", font=("Arial", 30, "bold"), fill="#ffffff")
    main_canvas.create_text(460, 80, text="Government Polytechnic Chapra, Bihar",
                            font=("Arial", 24, "bold"), fill="green")

    # ---------------------- Search Area ------------------------
    search_frame = tk.Frame(main_canvas, bg="#ffffff")
    main_canvas.create_window(460, 150, window=search_frame)

    tk.Label(search_frame, text="Search By:", font=("Arial", 12), bg="#ffffff").grid(row=0, column=0, padx=5)
    global search_criteria_var, search_query_entry
    search_criteria_var = tk.StringVar()
    search_criteria_var.set("Roll No")
    tk.OptionMenu(search_frame, search_criteria_var, "DOB", "Roll No", "Address", "ID").grid(row=0, column=1, padx=5)

    search_query_entry = tk.Entry(search_frame, width=30)
    search_query_entry.grid(row=0, column=2, padx=5)

    tk.Button(search_frame, text="Search", font=("Arial", 10, "bold"), bg="#1e90ff", fg="white",
              command=search_student).grid(row=0, column=3, padx=5)

    # ---------------------- Buttons ------------------------


    buttons = [
        ("➕ Add Student", add_student),
        ("🗑️ Delete Student", delete_student),
        ("✏️ Update Student", update_student),
        ("📋 View All Students", view_all_students),
        ("📊 View Statistics", view_statistics),
    ]

    for idx, (label, command) in enumerate(buttons):
        main_canvas.create_window(
            460, 250 + (idx * 60),  # Position buttons with spacing
            window=tk.Button(
                main_canvas,
                text=label,
                command=command,
                font=("Arial", 12, "bold"),
                bg="#4caf50",
                fg="white",
                width=20,
                pady=5,
                relief="raised",
                bd=2
            )
        )

    # ---------------------- Footer Logo ------------------------
    main_canvas.create_image(820, 600, anchor="se", image=right_logo_img)

    admin_window.mainloop()


if __name__ == "__main__":
    run_admin_panel()
