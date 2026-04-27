import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog
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
    def save_student():
        name = name_entry.get()
        roll = roll_entry.get()
        mobile = mobile_entry.get()
        department = department_entry.get()
        address = address_entry.get()

        photo_path = upload_photo()  # Allow the admin to upload a photo

        if not (name and roll and mobile and department and address):
            show_message("Error", "All fields are required!")
        else:
            student_data = {
                "name": name,
                "roll": roll,
                "mobile": mobile,
                "department": department,
                "address": address,
                "photo": photo_path  # Store the file path in the database
            }
            students_collection.insert_one(student_data)
            show_message("Success", "Student added successfully!")
            add_window.destroy()

    add_window = tk.Toplevel(admin_window)
    add_window.title("Add Student")
    add_window.geometry("400x400")

    tk.Label(add_window, text="Name").pack(pady=10)
    name_entry = tk.Entry(add_window)
    name_entry.pack(pady=10)

    tk.Label(add_window, text="Roll No.").pack(pady=10)
    roll_entry = tk.Entry(add_window)
    roll_entry.pack(pady=10)

    tk.Label(add_window, text="Mobile No.").pack(pady=10)
    mobile_entry = tk.Entry(add_window)
    mobile_entry.pack(pady=10)

    tk.Label(add_window, text="Department").pack(pady=10)
    department_entry = tk.Entry(add_window)
    department_entry.pack(pady=10)

    tk.Label(add_window, text="Address").pack(pady=10)
    address_entry = tk.Entry(add_window)
    address_entry.pack(pady=10)

    tk.Button(add_window, text="Upload Photo", command=upload_photo).pack(pady=10)
    tk.Button(add_window, text="Save", command=save_student).pack(pady=20)

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

    if roll_no:
        student = students_collection.find_one({"roll": roll_no})
        if student:
            new_name = simpledialog.askstring("Update Name", "Enter new name (leave empty to keep current):")
            new_department = simpledialog.askstring("Update Department", "Enter new department (leave empty to keep current):")

            updated_fields = {}
            if new_name:
                updated_fields["name"] = new_name
            if new_department:
                updated_fields["department"] = new_department

            if updated_fields:
                students_collection.update_one({"roll": roll_no}, {"$set": updated_fields})
                show_message("Success", f"Student with Roll No. {roll_no} updated successfully!")
            else:
                show_message("No Update", "No updates were made.")
        else:
            show_message("Error", f"No student found with Roll No. {roll_no}")
    else:
        show_message("Error", "Roll No. is required to update!")

# View All Students Function
def view_all_students():
    students_window = tk.Toplevel(admin_window)
    students_window.title("All Students")
    students_window.geometry("600x400")

    students_list = students_collection.find()

    tk.Label(students_window, text="List of Students", font=("Arial", 14)).pack(pady=10)
    for student in students_list:
        student_info = f"Name: {student['name']} | Roll No: {student['roll']} | Department: {student['department']}"
        tk.Label(students_window, text=student_info).pack(pady=5)

        # Display student photo if available
        if student.get("photo"):
            img = Image.open(student["photo"])
            img.thumbnail((100, 100))  # Resize the image to fit the UI
            img = ImageTk.PhotoImage(img)
            img_label = tk.Label(students_window, image=img)
            img_label.image = img  # Keep a reference to the image
            img_label.pack()

# View Statistics Function (Number of Students and Faculty)
"""def view_statistics():
    num_students = students_collection.count_documents({})
    num_faculty = faculty_collection.count_documents({})
    stats_message = f"Total Students: {num_students}\nTotal Faculty: {num_faculty}"
    show_message("Statistics", stats_message)"""
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
    admin_window.title("Admin Panel")
    admin_window.geometry("800x600")

    tk.Label(admin_window, text="Admin Panel", font=("Arial", 24)).pack(pady=20)

    # Search Section
    tk.Label(admin_window, text="Search Criteria").pack(pady=5)

    global search_criteria_var
    search_criteria_var = tk.StringVar()
    search_criteria_var.set("Roll No")  # Default value

    search_criteria_dropdown = tk.OptionMenu(admin_window, search_criteria_var, "DOB", "Roll No", "Address", "ID")
    search_criteria_dropdown.pack(pady=10)

    global search_query_entry
    search_query_entry = tk.Entry(admin_window)
    search_query_entry.pack(pady=10)

    tk.Button(admin_window, text="Search", command=search_student).pack(pady=20)

    # Buttons for Admin Panel
    tk.Button(admin_window, text="Add Student", command=add_student).pack(pady=10)
    tk.Button(admin_window, text="Delete Student", command=delete_student).pack(pady=10)
    tk.Button(admin_window, text="Update Student", command=update_student).pack(pady=10)
    tk.Button(admin_window, text="View All Students", command=view_all_students).pack(pady=10)
    tk.Button(admin_window, text="View Statistics", command=view_statistics).pack(pady=10)

    admin_window.mainloop()

if __name__ == "__main__":
    run_admin_panel()
