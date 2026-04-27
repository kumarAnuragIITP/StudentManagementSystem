import tkinter as tk
from tkinter import messagebox
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["student_management"]
students_collection = db["students"]

def run_student_panel():
    student_window = tk.Tk()
    student_window.title("Student Panel")
    student_window.geometry("800x600")

    def view_details():
        # View student details
        pass

    tk.Button(student_window, text="View Student Details", command=view_details).pack(pady=10)
    student_window.mainloop()
if __name__ == "__main__":
    run_student_panel()